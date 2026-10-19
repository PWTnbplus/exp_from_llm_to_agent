#!/usr/bin/env python3
"""G8.5 mechanism-identification preflight and Kimi-only engineering pilot.

The pilot is deliberately unable to claim science: the current G7/G8 evidence
does not provide real paired clean/recovered histories.  It exists to exercise
the frozen state/history design, real provider path, private scorer boundary,
and append-only audit before a qualified upstream pair is available.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
MODEL_ID = "kimi-k2.5"
BASE_URL = "https://token.ctflow.cn/v1"
MODEL_SNAPSHOT = "kimi-k2.5@ctflow.cn/v1; external_weight_attestation=false"
PROTOCOL = "G8_5_SINGLE_KIMI_V1"
FORBIDDEN = {"expected_decision", "private_truth", "answer_key", "ground_truth", "oracle", "correct_state", "truth_key"}
ARMS = ("A_CLEAN_FULL", "B_RECOVERED_FULL", "C_CLEAN_STATE_ONLY", "D_RECOVERED_STATE_ONLY")
FAMILIES = ("SYN_AFFINE_MONOTONICITY", "SYN_QUADRATIC_MONOTONICITY")


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_file(path: Path) -> str:
    return sha(path.read_bytes())


def jhash(value: Any) -> str:
    return sha(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode())


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")


def forbidden_paths(value: Any, path: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in FORBIDDEN:
                found.append(f"{path}.{key}")
            found.extend(forbidden_paths(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for i, child in enumerate(value):
            found.extend(forbidden_paths(child, f"{path}[{i}]"))
    return found


def _jsonl_files(root: Path) -> list[Path]:
    return sorted(root.rglob("*.jsonl")) if root.exists() else []


def preflight(g8_manifest: Path, g7_roots: list[Path], out: Path) -> dict[str, Any]:
    g8 = load(g8_manifest) if g8_manifest.exists() else {}
    history_rows = 0
    pair_markers = 0
    observed_keys: set[str] = set()
    source_files: list[str] = []
    for root in g7_roots:
        for path in _jsonl_files(root):
            source_files.append(str(path))
            try:
                rows = load_jsonl(path)
            except Exception:
                continue
            for row in rows:
                history_rows += 1
                observed_keys.update(str(key) for key in row)
                text = json.dumps(row, ensure_ascii=False).lower()
                if ("h_clean" in text and "h_recovered" in text) or ("clean_history" in text and "recovered_history" in text):
                    pair_markers += 1
    upstream_go = g8.get("scientific_release_status") == "GO" and g8.get("review_status") == "GO"
    qualifying_pairs = 0 if pair_markers == 0 else pair_markers
    result = {
        "protocol": PROTOCOL,
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_id": MODEL_ID,
        "only_model": True,
        "g8_manifest": str(g8_manifest),
        "g8_manifest_sha256": sha_file(g8_manifest) if g8_manifest.exists() else None,
        "g8_upstream_scientific_go": upstream_go,
        "g8_scientific_release_status": g8.get("scientific_release_status"),
        "g7_source_roots": [str(path) for path in g7_roots],
        "g7_jsonl_files_scanned": len(source_files),
        "g7_history_rows_scanned": history_rows,
        "g7_clean_recovered_pair_markers": pair_markers,
        "qualifying_real_history_pairs": qualifying_pairs,
        "required_fields_not_seen": sorted({"canonical_state_id", "evidence_id", "history_provenance", "visible_history"} - observed_keys),
        "status": "BLOCKED_MISSING_REAL_UPSTREAM",
        "science_blockers": [
            "G8 has no independent scientific GO handoff.",
            "No same-state/same-evidence real H_CLEAN/H_RECOVERED history pair was found in the scanned G7 artifacts.",
        ],
        "engineering_pilot_allowed": True,
        "synthetic_history_science_use": "FORBIDDEN",
    }
    write_json(out, result)
    return result


def _case(family: str, evidence: str) -> dict[str, Any]:
    if family == "SYN_AFFINE_MONOTONICITY":
        state = "f(x)=2*x+1 is nondecreasing on x>=0"
        problem = "Determine whether f(x)=2*x+1 is nondecreasing on x>=0."
        evidence_text = "Derivative evidence: f'(x)=2, which is nonnegative on x>=0."
    else:
        state = "f(x)=x^2 is nondecreasing on x>=0"
        problem = "Determine whether f(x)=x^2 is nondecreasing on x>=0."
        evidence_text = "Derivative evidence: f'(x)=2*x, which is nonnegative on x>=0."
    return {"family_id": family, "evidence_id": evidence, "canonical_state": state, "problem": problem, "new_evidence": evidence_text}


def build_plan(out: Path, preflight_path: Path) -> dict[str, Any]:
    pre = load(preflight_path)
    rows: list[dict[str, Any]] = []
    index = 0
    for family in FAMILIES:
        for evidence in ("E_DERIVATIVE", "E_DOMAIN_CHECK"):
            case = _case(family, evidence)
            clean_history = ["observe_public_state", "validate_new_evidence", "commit_state_update"]
            recovered_history = ["trace_recovery_notice", "replay_public_evidence", "validate_new_evidence", "commit_state_update"]
            for arm in ARMS:
                visible_history = clean_history if arm == "A_CLEAN_FULL" else recovered_history if arm == "B_RECOVERED_FULL" else []
                public = {
                    "case": case,
                    "visible_history": visible_history,
                    "history_visibility": "full" if arm in {"A_CLEAN_FULL", "B_RECOVERED_FULL"} else "state_only",
                    "instruction": "Return JSON only with decision, state_after, evidence_use, and history_role. Do not expose chain-of-thought.",
                }
                if arm in {"C_CLEAN_STATE_ONLY", "D_RECOVERED_STATE_ONLY"}:
                    public["visible_history"] = []
                if public["case"] != case:
                    raise AssertionError("state mismatch")
                leaked = forbidden_paths(public)
                if leaked:
                    raise RuntimeError(f"forbidden public fields: {leaked}")
                row = {
                    "run_id": f"g85-eng-{index:04d}-{jhash([family, evidence, arm])[:16]}",
                    "phase": "ENGINEERING_PILOT",
                    "protocol": PROTOCOL,
                    "model_id": MODEL_ID,
                    "model_snapshot": MODEL_SNAPSHOT,
                    "base_url": BASE_URL,
                    "family_id": family,
                    "evidence_id": evidence,
                    "arm_id": arm,
                    "history_provenance": "synthetic_engineering_only",
                    "scientific_use": "FORBIDDEN",
                    "public_messages": [
                        {"role": "system", "content": "You are a scientific state-update participant. Use only the public state, public evidence, and visible history. Never access hidden answers, files, network, or private truth."},
                        {"role": "user", "content": json.dumps(public, ensure_ascii=False, sort_keys=True)},
                    ],
                    "public_input_sha256": jhash(public),
                    "status": "PLANNED",
                    "preflight_sha256": sha_file(preflight_path),
                    "source_upstream_status": pre["status"],
                }
                rows.append(row)
                index += 1
    # C/D must be byte-equivalent by design; assert before any model call.
    for family in FAMILIES:
        for evidence in ("E_DERIVATIVE", "E_DOMAIN_CHECK"):
            c = next(r for r in rows if r["family_id"] == family and r["evidence_id"] == evidence and r["arm_id"] == "C_CLEAN_STATE_ONLY")
            d = next(r for r in rows if r["family_id"] == family and r["evidence_id"] == evidence and r["arm_id"] == "D_RECOVERED_STATE_ONLY")
            if c["public_messages"] != d["public_messages"]:
                raise AssertionError("C/D public request is not byte-equivalent")
    write_jsonl(out, rows)
    manifest = {"protocol": PROTOCOL, "model_id": MODEL_ID, "only_model": True, "phase": "ENGINEERING_PILOT", "n_rows": len(rows), "families": list(FAMILIES), "arms": list(ARMS), "history_provenance": "synthetic_engineering_only", "scientific_use": "FORBIDDEN", "preflight_sha256": sha_file(preflight_path), "plan_sha256": sha_file(out), "private_truth_in_plan": False}
    write_json(out.with_suffix(out.suffix + ".manifest.json"), manifest)
    return manifest


def _extract_json(text: str) -> dict[str, Any]:
    from scripts.run_g6_counterfactual import extract_json
    value = extract_json(text)
    if not isinstance(value, dict):
        raise ValueError("provider response was not an object")
    return value


def run(plan_path: Path, run_root: Path, key_file: Path, rps: float) -> dict[str, Any]:
    from scripts.audit_repair.cost_ledger import CostLedger
    from src.scientific_discovery.models.provider import OpenAICompatibleProvider
    plan = load_jsonl(plan_path)
    run_root.mkdir(parents=True, exist_ok=True)
    ledger = CostLedger(run_root / "cost_ledger.sqlite", global_cap=200.0, g7_cap=60.0, worker_cap=200.0)
    next_call = 0.0
    counts: dict[str, int] = {}
    calls = 0
    cost = 0.0
    for row in plan:
        result_path = run_root / "raw" / row["run_id"] / "result.json"
        if result_path.exists():
            continue
        delay = next_call - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        next_call = time.monotonic() + (1.0 / rps if rps > 0 else 0.0)
        out_dir = result_path.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        provider = OpenAICompatibleProvider(api_key=key_file.read_text(encoding="utf-8").strip(), base_url=BASE_URL, model_name=MODEL_ID, timeout=180.0, max_retries=0, input_cost_per_1k=0.001, output_cost_per_1k=0.003, max_cost_usd=0.25, max_output_tokens=512, reservation_output_tokens=512, cost_ledger=ledger, ledger_scope="g8_5", ledger_worker="single-kimi-g8-5", ledger_ref_prefix=f"g85:{row['run_id']}", require_cost_ledger=True)
        events = [{"event_type": "RUN_START", "status": "COMPLETED", "payload": {"run_id": row["run_id"], "model_id": MODEL_ID, "history_provenance": row["history_provenance"]}}]
        status = "PASS"
        try:
            response = provider.complete(row["public_messages"])
            usage = response.usage.__dict__
            events.append({"event_type": "MODEL_RESPONSE", "status": "COMPLETED", "payload": {"content": response.content, "usage": usage}})
            answer = _extract_json(response.content)
            if str(answer.get("decision", "")).upper() not in {"ACCEPT", "REJECT", "UNCERTAIN"}:
                raise ValueError("invalid decision")
            answer["decision"] = str(answer["decision"]).upper()
        except Exception as exc:
            status = "TECHNICAL_FAILURE"
            answer = {"decision": "UNCERTAIN", "error_type": type(exc).__name__, "supporting_evidence": "technical failure; no scientific conclusion"}
            events.append({"event_type": "ADAPTER_ERROR", "status": "COMPLETED", "payload": {"error_type": type(exc).__name__, "error": str(exc)[:500]}})
            usage = getattr(locals().get("response", None), "usage", None)
            usage = usage.__dict__ if usage is not None else {"total_tokens": 0, "cost_usd": 0.0}
        trace = provider.audit_trace()
        answer.update({"run_id": row["run_id"], "events": events, "usage": usage, "actual_model_snapshot": MODEL_SNAPSHOT, "public_only": True, "history_provenance": row["history_provenance"]})
        envelope = {"run_id": row["run_id"], "plan_row_hash": jhash(row), "is_mock": False, "execution_status": status, "model_id": MODEL_ID, "provider_trace_count": len(trace), "response": answer}
        write_json(result_path, envelope)
        write_jsonl(out_dir / "provider_traces.jsonl", trace)
        write_jsonl(out_dir / "events.jsonl", events)
        counts[status] = counts.get(status, 0) + 1
        calls += len(trace)
        cost += float(usage.get("cost_usd", 0.0))
    summary = {"protocol": PROTOCOL, "model_id": MODEL_ID, "only_model": True, "planned": len(plan), "new_result_status_counts": counts, "real_provider_calls": calls, "total_cost_usd": cost, "scientific_use": "FORBIDDEN", "status": "ENGINEERING_ONLY_SCIENCE_BLOCKED"}
    write_json(run_root / "execution_summary.json", summary)
    return summary


def score(plan_path: Path, run_root: Path, private_truth_path: Path, out: Path) -> dict[str, Any]:
    plan = load_jsonl(plan_path)
    truth = {row["run_id"]: row for row in load_jsonl(private_truth_path)}
    rows: list[dict[str, Any]] = []
    private_scan_hits = 0
    for row in plan:
        env_path = run_root / "raw" / row["run_id"] / "result.json"
        env = load(env_path) if env_path.exists() else {"execution_status": "MISSING", "response": {}}
        response = env.get("response") or {}
        visible = json.dumps(row.get("public_messages", []), ensure_ascii=False).lower()
        private_scan_hits += sum(1 for token in FORBIDDEN if token in visible)
        expected = truth[row["run_id"]]["expected_decision"]
        decision = str(response.get("decision", "UNCERTAIN")).upper()
        rows.append({"run_id": row["run_id"], "family_id": row["family_id"], "evidence_id": row["evidence_id"], "arm_id": row["arm_id"], "execution_status": env.get("execution_status", "MISSING"), "decision": decision, "expected_decision": expected, "correct": int(decision == expected and env.get("execution_status") == "PASS"), "history_provenance": row["history_provenance"]})
    out.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else []
    with (out / "g85_case_scores.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    arm_rows = []
    for arm in ARMS:
        subset = [x for x in rows if x["arm_id"] == arm]
        arm_rows.append({"arm_id": arm, "planned": len(subset), "correct": sum(x["correct"] for x in subset), "all_planned_accuracy": sum(x["correct"] for x in subset) / len(subset) if subset else 0.0, "technical_failures": sum(x["execution_status"] != "PASS" for x in subset)})
    with (out / "g85_arm_scores.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(arm_rows[0])); writer.writeheader(); writer.writerows(arm_rows)
    audit = {"protocol": PROTOCOL, "planned": len(plan), "result_files": sum(1 for row in plan if (run_root / "raw" / row["run_id"] / "result.json").exists()), "private_truth_loaded_only_in_scorer": True, "model_requests_private_truth_scan_hits": private_scan_hits, "scientific_use": "FORBIDDEN", "status": "ENGINEERING_ONLY_SCIENCE_BLOCKED", "history_provenance": "synthetic_engineering_only"}
    write_json(out / "g85_private_truth_audit.json", audit)
    write_json(out / "g85_results_manifest.json", {"protocol": PROTOCOL, "model_id": MODEL_ID, "only_model": True, "status": "ENGINEERING_ONLY_SCIENCE_BLOCKED", "arm_scores": arm_rows, "private_truth_sha256": sha_file(private_truth_path), "private_truth_scan_hits": private_scan_hits})
    return audit


def make_truth(plan_path: Path, out: Path) -> dict[str, Any]:
    rows = load_jsonl(plan_path)
    truth = [{"run_id": row["run_id"], "expected_decision": "ACCEPT", "expected_state_after": "VERIFIED", "truth_source": "machine_generated_from_public_case_definition", "science_use": "engineering_only"} for row in rows]
    write_jsonl(out, truth)
    return {"rows": len(truth), "sha256": sha_file(out), "not_in_plan": True}


def build_repair_plan(plan_path: Path, run_root: Path, out: Path) -> dict[str, Any]:
    plan = load_jsonl(plan_path)
    rows: list[dict[str, Any]] = []
    for source in plan:
        result_path = run_root / "raw" / source["run_id"] / "result.json"
        if not result_path.exists() or load(result_path).get("execution_status") != "TECHNICAL_FAILURE":
            continue
        row = json.loads(json.dumps(source, ensure_ascii=False))
        row["run_id"] = f"{source['run_id']}-adapter-repair1"
        row["repair_of_run_id"] = source["run_id"]
        row["repair_reason"] = "freeze the decision enum after primary schema failure; primary result preserved"
        row["repair_protocol"] = "G8_5_SINGLE_KIMI_V1_ADAPTER_REPAIR1"
        row["public_messages"][-1]["content"] += " Decision must be exactly one of ACCEPT, REJECT, or UNCERTAIN."
        rows.append(row)
    write_jsonl(out, rows)
    manifest = {"protocol": "G8_5_SINGLE_KIMI_V1_ADAPTER_REPAIR1", "source_plan": str(plan_path), "source_plan_sha256": sha_file(plan_path), "source_run_root": str(run_root), "n_repair_rows": len(rows), "selection_rule": "primary TECHNICAL_FAILURE only; no primary result overwritten", "model_id": MODEL_ID, "private_truth_in_plan": False, "plan_sha256": sha_file(out)}
    write_json(out.with_suffix(out.suffix + ".manifest.json"), manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("preflight"); p.add_argument("--g8-manifest", type=Path, required=True); p.add_argument("--g7-root", type=Path, action="append", required=True); p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("plan"); p.add_argument("--preflight", type=Path, required=True); p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("truth"); p.add_argument("--plan", type=Path, required=True); p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("repair-plan"); p.add_argument("--plan", type=Path, required=True); p.add_argument("--run-root", type=Path, required=True); p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("run"); p.add_argument("--plan", type=Path, required=True); p.add_argument("--run-root", type=Path, required=True); p.add_argument("--key-file", type=Path, required=True); p.add_argument("--rps", type=float, default=2.0)
    p = sub.add_parser("score"); p.add_argument("--plan", type=Path, required=True); p.add_argument("--run-root", type=Path, required=True); p.add_argument("--truth", type=Path, required=True); p.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "preflight": result = preflight(args.g8_manifest, args.g7_root, args.out)
    elif args.command == "plan": result = build_plan(args.out, args.preflight)
    elif args.command == "truth": result = make_truth(args.plan, args.out)
    elif args.command == "repair-plan": result = build_repair_plan(args.plan, args.run_root, args.out)
    elif args.command == "run": result = run(args.plan, args.run_root, args.key_file, args.rps)
    else: result = score(args.plan, args.run_root, args.truth, args.out)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
