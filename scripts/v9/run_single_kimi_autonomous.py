"""V9 bounded autonomous runner; real mode uses only kimi-k2.5."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

from .build_cohorts import build_agent_comparison, build_g6, build_g7, build_lu, build_q
from .common import append_jsonl, extract_json, read_jsonl, sha_obj, write_json
from .g7_checkpoint_fork_runner import run_g7
from .provider import SingleKimiProvider
from .protocol_namespace_lock import lock


def _g6_messages(case: dict[str, Any]) -> list[dict[str, Any]]:
    arm = case["arm_id"]
    workflow = "fixed two-pass public review" if arm == "G6_A_G3_GIVEN" else "bounded adaptive public review with one self-check"
    return [{"role": "system", "content": f"You are the {workflow} arm of V9 G6. Use only the public case. Do not access truth, files, network, or private answers. Return compact JSON with decision (MAINTAIN, REJECT, REVISE, or UNDETERMINED), affected_claim_ids (array), revised_claim (string or null), supporting_evidence (string)."}, {"role": "user", "content": json.dumps({"g6_case": case}, ensure_ascii=False, sort_keys=True)}]


def _q_messages(task: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"role": "system", "content": "You are a blinded independent claim auditor. Use only the public proposition. Return compact JSON with claim_id, proposition_DSL, verification_intent, proposed_final_action. proposed_final_action must be PROVEN_TRUE, PROVEN_FALSE, or UNKNOWN. Do not access any answer key."}, {"role": "user", "content": json.dumps({"public_task": task}, ensure_ascii=False, sort_keys=True)}]


def _lu_initial(task: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"role": "system", "content": "You are a checkpointed scientific reasoning agent. Return compact JSON with claim_id, state_before, intermediate_status, evidence. The claim is non-final; do not infer hidden truth."}, {"role": "user", "content": json.dumps({"public_checkpoint": task["checkpoint_nodes"], "control_claim": task["control_public_claim"]}, ensure_ascii=False, sort_keys=True)}]


def _lu_fork(task: dict[str, Any], arm: str) -> str:
    evidence = task["real_intervention"] if arm == "REAL" else task["sham_intervention"] if arm == "SHAM" else {"kind": "CONTROL", "evidence": "No intervention; re-evaluate the same public checkpoint."}
    return json.dumps({"arm": arm, "public_intervention": evidence, "instruction": "Update only the non-final U1 claim and return compact JSON with state_after and evidence."}, ensure_ascii=False, sort_keys=True)


def run_g6(provider: SingleKimiProvider, base: Path) -> dict[str, Any]:
    public = read_jsonl(base / "public_cases.jsonl"); out = base / "records.jsonl"; out.parent.mkdir(parents=True, exist_ok=True); out.touch(exist_ok=True)
    existing = {r.get("case_id") for r in read_jsonl(out)}
    for case in public:
        if case["case_id"] in existing: continue
        result = provider.call("G6_V9", case["case_id"], case["arm_id"], _g6_messages(case)); candidate = extract_json(result["content"])
        append_jsonl(out, {"protocol_id": "G6_KIMI_V9_MACHINE_VERIFIABLE", "cohort_id": case["cohort_id"], "source_task_id": case["source_task_id"], "case_id": case["case_id"], "family_id": case["family_id"], "cf_type": case["cf_type"], "arm_id": case["arm_id"], "candidate": candidate, "raw_content_present": bool(result["content"]), "provider_error": result["error"], "call_number": result["call_number"], "truth_key_sent_to_model": False})
    rows = read_jsonl(out); return {"planned": len(public), "records": len(rows), "structured": sum(r.get("candidate") is not None for r in rows)}


def run_q(provider: SingleKimiProvider, base: Path) -> dict[str, Any]:
    public = read_jsonl(base / "public_cases.jsonl"); out = base / "records.jsonl"; out.parent.mkdir(parents=True, exist_ok=True); out.touch(exist_ok=True); existing = {r.get("task_id") for r in read_jsonl(out)}
    for task in public:
        if task["task_id"] in existing: continue
        result = provider.call("Q_V9", task["task_id"], "Q_INDEPENDENT_CANDIDATE", _q_messages(task)); candidate = extract_json(result["content"])
        append_jsonl(out, {"protocol_id": "Q_KIMI_V9_TRUTH_FIRST", "cohort_id": task["cohort_id"], "task_id": task["task_id"], "candidate": candidate, "raw_content_present": bool(result["content"]), "provider_error": result["error"], "call_number": result["call_number"], "truth_key_sent_to_model": False})
    rows = read_jsonl(out); return {"planned": len(public), "records": len(rows), "structured": sum(r.get("candidate") is not None for r in rows)}


def run_lu(provider: SingleKimiProvider, base: Path) -> dict[str, Any]:
    public = read_jsonl(base / "public_cases.jsonl"); out = base / "records.jsonl"; out.parent.mkdir(parents=True, exist_ok=True); out.touch(exist_ok=True); existing = {(r.get("task_id"), r.get("arm")) for r in read_jsonl(out)}
    rng = random.Random(20261019); rows = read_jsonl(out)
    for task in public:
        initial = next((r for r in rows if r.get("task_id") == task["task_id"] and r.get("arm") == "INITIAL_CHECKPOINT"), None)
        if initial is None:
            result = provider.call("LU_U_V9", task["task_id"], "INITIAL_CHECKPOINT", _lu_initial(task)); initial_content = result["content"] or ""; initial = {"protocol_id": "LU_V9_PROSPECTIVE", "cohort_id": task["cohort_id"], "task_id": task["task_id"], "arm": "INITIAL_CHECKPOINT", "candidate": extract_json(initial_content), "raw_content_present": bool(initial_content), "provider_error": result["error"], "call_number": result["call_number"], "checkpoint_id": task["checkpoint_id"], "shared_checkpoint_messages_sha256": sha_obj(_lu_initial(task)), "truth_key_sent_to_model": False}; append_jsonl(out, initial); rows.append(initial)
        else: initial_content = json.dumps(initial.get("candidate") or {}, ensure_ascii=False)
        order = ["CONTROL", "REAL", "SHAM"]; rng.shuffle(order)
        for position, arm in enumerate(order):
            if (task["task_id"], arm) in existing: continue
            messages = [*_lu_initial(task), {"role": "assistant", "content": initial_content}, {"role": "user", "content": _lu_fork(task, arm)}]
            result = provider.call("LU_U_V9", task["task_id"], arm, messages); candidate = extract_json(result["content"])
            append_jsonl(out, {"protocol_id": "LU_V9_PROSPECTIVE", "cohort_id": task["cohort_id"], "task_id": task["task_id"], "arm": arm, "randomized_position": position, "checkpoint_id": task["checkpoint_id"], "shared_checkpoint_messages_sha256": sha_obj(_lu_initial(task)), "candidate": candidate, "raw_content_present": bool(result["content"]), "provider_error": result["error"], "call_number": result["call_number"], "truth_key_sent_to_model": False}); existing.add((task["task_id"], arm))
    rows = read_jsonl(out); return {"planned_forks": len(public) * 3, "records_including_initial": len(rows), "arm_counts": {a: sum(r.get("arm") == a for r in rows) for a in ["CONTROL", "REAL", "SHAM"]}}


def run_agent_comparison(provider: SingleKimiProvider, base: Path) -> dict[str, Any]:
    public = read_jsonl(base / "public_cases.jsonl"); out = base / "records.jsonl"; out.parent.mkdir(parents=True, exist_ok=True); out.touch(exist_ok=True); existing = {(r.get("task_id"), r.get("workflow"), r.get("step")) for r in read_jsonl(out)}
    for task in public:
        # LLM-only: fixed plan before observations; final analysis is after the
        # batch, with no model call in between.
        key = (task["task_id"], "LLM_ONLY", 1)
        if key not in existing:
            result = provider.call("AGENT_COMPARISON_V9", task["task_id"], "LLM_ONLY_PLAN", [{"role": "system", "content": "You are the LLM-only arm. Freeze the complete two-action plan before seeing any new observation. Return JSON with actions."}, {"role": "user", "content": json.dumps(task, ensure_ascii=False, sort_keys=True)}]); append_jsonl(out, {"protocol_id": "AGENT_COMPARISON_KIMI_V9", "task_id": task["task_id"], "workflow": "LLM_ONLY", "step": 1, "candidate": extract_json(result["content"]), "call_number": result["call_number"], "provider_error": result["error"], "observation_feedback_received": False, "frozen_plan": True}); existing.add(key)
        key = (task["task_id"], "LLM_ONLY", 2)
        if key not in existing:
            result = provider.call("AGENT_COMPARISON_V9", task["task_id"], "LLM_ONLY_FINAL", [{"role": "system", "content": "You are the LLM-only arm final analysis. Do not change the frozen action plan or add actions. Return JSON with conclusion."}, {"role": "user", "content": json.dumps({"task": task, "batch_observations": [task["initial_observation"], task["observations_after_first_action"]]}, ensure_ascii=False, sort_keys=True)}]); append_jsonl(out, {"protocol_id": "AGENT_COMPARISON_KIMI_V9", "task_id": task["task_id"], "workflow": "LLM_ONLY", "step": 2, "candidate": extract_json(result["content"]), "call_number": result["call_number"], "provider_error": result["error"], "observation_feedback_received": False, "frozen_plan": True}); existing.add(key)
        # Agent: same two calls and same public action domain, but the second
        # action is selected after the public executor observation.
        key = (task["task_id"], "AGENT", 1)
        if key not in existing:
            result = provider.call("AGENT_COMPARISON_V9", task["task_id"], "AGENT_STEP1", [{"role": "system", "content": "You are the adaptive single-agent arm. Select one allowed public action from the task. Return JSON with action."}, {"role": "user", "content": json.dumps({"task": task, "observation": task["initial_observation"]}, ensure_ascii=False, sort_keys=True)}]); append_jsonl(out, {"protocol_id": "AGENT_COMPARISON_KIMI_V9", "task_id": task["task_id"], "workflow": "AGENT", "step": 1, "candidate": extract_json(result["content"]), "call_number": result["call_number"], "provider_error": result["error"], "observation_feedback_received": True, "frozen_plan": False}); existing.add(key)
        key = (task["task_id"], "AGENT", 2)
        if key not in existing:
            result = provider.call("AGENT_COMPARISON_V9", task["task_id"], "AGENT_STEP2_ADAPTIVE", [{"role": "system", "content": "You are the adaptive single-agent arm. Choose the next allowed action after public feedback. Return JSON with action and adaptation_reason."}, {"role": "user", "content": json.dumps({"task": task, "new_public_observation": task["observations_after_first_action"]}, ensure_ascii=False, sort_keys=True)}]); append_jsonl(out, {"protocol_id": "AGENT_COMPARISON_KIMI_V9", "task_id": task["task_id"], "workflow": "AGENT", "step": 2, "candidate": extract_json(result["content"]), "call_number": result["call_number"], "provider_error": result["error"], "observation_feedback_received": True, "frozen_plan": False}); existing.add(key)
    rows = read_jsonl(out); return {"records": len(rows), "llm_only_records": sum(r.get("workflow") == "LLM_ONLY" for r in rows), "agent_records": sum(r.get("workflow") == "AGENT" for r in rows), "same_model": True}


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--model-id", default="kimi-k2.5"); parser.add_argument("--profile", default="auto-from-frozen-plans"); parser.add_argument("--work", choices=["all", "g6", "g7", "q", "lu", "agent-comparison", "stats"], default="all"); parser.add_argument("--resume", action="store_true"); parser.add_argument("--mode", choices=["real"], default="real"); parser.add_argument("--cohort", required=True); parser.add_argument("--max-workers", type=int, default=1); parser.add_argument("--out", type=Path, required=True); parser.add_argument("--key-file", type=Path, default=Path("api_key/kimi/kimi-k2.5.txt")); parser.add_argument("--base-url", default="https://token.ctflow.cn/v1"); parser.add_argument("--max-cost", type=float, default=20.0); parser.add_argument("--timeout", type=float, default=90.0)
    args = parser.parse_args()
    if args.model_id != "kimi-k2.5": raise SystemExit("only kimi-k2.5 is permitted")
    root = args.out; root.mkdir(parents=True, exist_ok=True)
    if not (root / "g6/public_cases.jsonl").exists():
        build_g6(root / "g6"); build_q(root / "q"); build_lu(root / "lu"); build_g7(root / "g7"); build_agent_comparison(root / "agent_comparison")
    if not (root / "PROTOCOL_NAMESPACE_MATRIX.json").exists(): lock(root, args.cohort, args.model_id)
    write_json(root / "manifest.json", {"cohort_id": args.cohort, "model_id": args.model_id, "profile": args.profile, "mode": args.mode, "base_url": args.base_url, "max_workers": min(max(args.max_workers, 1), 2), "historical_denominators_unchanged": True})
    provider = SingleKimiProvider(root, args.key_file, args.base_url, args.model_id, args.max_cost, args.timeout)
    result: dict[str, Any] = {}
    if args.work in {"all", "g6"}: result["g6"] = run_g6(provider, root / "g6")
    if args.work in {"all", "g7"}: result["g7"] = run_g7(provider, root / "g7")
    if args.work in {"all", "q"}: result["q"] = run_q(provider, root / "q")
    if args.work in {"all", "lu"}: result["lu"] = run_lu(provider, root / "lu")
    if args.work in {"all", "agent-comparison"}: result["agent_comparison"] = run_agent_comparison(provider, root / "agent_comparison")
    result["call_count"] = provider.call_no; result["only_model"] = args.model_id; write_json(root / "execution_summary.json", result); print(json.dumps(result, ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
