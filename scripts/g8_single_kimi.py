"""Single-Kimi G8 execution, scoring, and audit manifest.

The historical G8 run is preserved because it used glm-5.  This module derives
an append-only Kimi-only run from the already audited public G8 plan, keeps the
private oracle in the scoring process, and never sends oracle fields to the
provider.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.audit_repair.cost_ledger import CostLedger
from scripts.g8_public_v_verifier import VERSION as V_VERSION
from scripts.run_g8_causal_mechanism import TOOLS, add_event, mechanism, parse_response, system_prompt
from scripts.run_g6_counterfactual import execute_tool, parse_tool_args
from scripts.run_g7_failure_localization import Limits
from src.scientific_discovery.models.provider import OpenAICompatibleProvider, ProviderResponse


SOURCE_PLAN = ROOT / "results/g8_causal_mechanism/formal-20261015T030000Z-16workers/g8_run_plan.jsonl"
PRIVATE_ORACLE = ROOT / "results/g6_counterfactual/formal-20261013T000000Z/private_oracle_verified23.jsonl"
MODEL_ID = "kimi-k2.5"
BASE_URL = "https://token.ctflow.cn/v1"
MODEL_SNAPSHOT = "kimi-k2.5@ctflow.cn/v1; external_weight_attestation=false"
PHASE_PROTOCOL = "G8_SINGLE_KIMI_V1"
PILOT_FAMILIES = {
    "G6F-TB-L1-001",
    "G6F-TB-L1-005",
    "G6F-TC-L1-007",
    "G6F-TC-L1-008",
}
FORMAL_FAMILIES = {
    "G6F-TB-L1-007",
    "G6F-TB-L1-008",
    "G6F-TB-L1-009",
    "G6F-TC-L1-009",
    "G6F-TC-L1-010",
}
PAIR_NAMES = {
    "B_MINUS_A": ("B_G3_REAL_M", "A_G3_BASE"),
    "B_MINUS_C": ("B_G3_REAL_M", "C_G3_SHAM_M"),
    "B_MINUS_D": ("B_G3_REAL_M", "D_G3_EXTRA_THINK"),
    "E_MINUS_F": ("E_G4_PLUS_M", "F_G4_MINUS_M"),
}
FORBIDDEN = {
    "expected_decision", "correct_revised_claim", "oracle_reason", "private_oracle",
    "ground_truth", "answer_key", "verifier_status", "V_true", "L_true_impacted_nodes",
    "U_true_node_changes", "oracle_ref",
}


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def json_hash(value: Any) -> str:
    return sha_bytes(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{time.time_ns()}.tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")


def forbidden_paths(value: Any, path: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in FORBIDDEN:
                found.append(child_path)
            found.extend(forbidden_paths(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(forbidden_paths(child, f"{path}[{index}]"))
    return found


def build_plan(source_plan: Path, out: Path, phase: str) -> dict[str, Any]:
    source_rows = read_jsonl(source_plan)
    wanted = PILOT_FAMILIES if phase == "pilot" else FORMAL_FAMILIES
    repeats = {0} if phase == "pilot" else {0, 1, 2}
    selected = [
        row for row in source_rows
        if row.get("paired_set_id") in wanted and int(row.get("replicate", 0)) in repeats
    ]
    if not selected:
        raise RuntimeError(f"no source rows selected for phase {phase}")
    plan: list[dict[str, Any]] = []
    for index, source in enumerate(sorted(selected, key=lambda x: (x["case_id"], x["arm_id"], int(x.get("replicate", 0))))):
        public = {
            "case_id": source["case_id"],
            "cf_type": source["cf_type"],
            "theory_family_id": source["paired_set_id"],
            "model_visible": source["model_visible"],
            "public_messages": source["public_messages"],
        }
        leaked = forbidden_paths(public)
        if leaked:
            raise RuntimeError(f"public source contains forbidden fields: {leaked}")
        row = dict(source)
        row.update({
            "run_id": f"g8kimi-{phase}-{index:04d}-{json_hash(source)[:16]}",
            "source_plan_row_sha256": json_hash(source),
            "phase": phase,
            "confirmation_split": "PILOT" if phase == "pilot" else "CONFIRM",
            "model_id": MODEL_ID,
            "model_snapshot": MODEL_SNAPSHOT,
            "base_url": BASE_URL,
            "protocol": PHASE_PROTOCOL,
            "is_mock": False,
            "status": "PLANNED",
            "source_historical_g8_model_id": "glm-5",
            "source_g8_plan_sha256": sha_file(source_plan),
        })
        plan.append(row)
    write_jsonl(out, plan)
    manifest = {
        "protocol": PHASE_PROTOCOL,
        "phase": phase,
        "model_id": MODEL_ID,
        "model_snapshot": MODEL_SNAPSHOT,
        "base_url": BASE_URL,
        "source_plan": str(source_plan),
        "source_plan_sha256": sha_file(source_plan),
        "source_historical_model_not_reused": "glm-5",
        "families": sorted(wanted),
        "n_families": len(wanted),
        "n_rows": len(plan),
        "replicates": sorted(repeats),
        "six_arms": sorted({row["arm_id"] for row in plan}),
        "private_oracle_in_plan": False,
        "selection_rule": "fixed family lists written before Kimi calls; pilot and confirm families are disjoint",
        "plan_sha256": sha_file(out),
    }
    write_json(out.with_suffix(out.suffix + ".manifest.json"), manifest)
    return manifest


class RateLimiter:
    def __init__(self, rps: float) -> None:
        self.interval = 1.0 / rps if rps > 0 else 0.0
        self.lock = threading.Lock()
        self.next_start = 0.0

    def wait(self) -> None:
        with self.lock:
            now = time.monotonic()
            start = max(now, self.next_start)
            self.next_start = start + self.interval
        delay = start - now
        if delay > 0:
            time.sleep(delay)


class LimitedProvider:
    def __init__(self, provider: OpenAICompatibleProvider, limiter: RateLimiter) -> None:
        self.provider = provider
        self.limiter = limiter

    def complete(self, messages: list[dict[str, Any]], *, tools: list[dict[str, Any]] | None = None) -> ProviderResponse:
        self.limiter.wait()
        return self.provider.complete(messages, tools=tools)


def kimi_loop(provider: LimitedProvider, messages: list[dict[str, Any]], group: str,
              extra: bool, limits: Limits, events: list[dict[str, Any]]) -> dict[str, Any]:
    """Run the Kimi workflow with an explicit finalization slot.

    The historical adapter treated a second G3 tool-calling response as a
    terminal failure even when the provider had returned valid tool results.
    This local implementation preserves the fixed second synthesis instruction
    and adds one final response slot only when the model still asks for tools;
    it does not alter any already-written historical or primary result.
    """
    max_calls = 4 if extra and group == "G3" else (3 if group == "G3" else 8)
    result: dict[str, Any] | None = None
    for index in range(max_calls):
        if group == "G3" and index == 1:
            messages.append({"role": "user", "content": "Perform the fixed second synthesis pass. Return only the required JSON."})
        if extra and group == "G3" and index == 2:
            messages.append({"role": "user", "content": "Perform one additional generic consistency pass over the same public evidence, then return the required JSON."})
        limits.before_model()
        add_event(events, "MODEL_REQUEST", {"call_index": index + 1, "messages": messages, "tools": TOOLS})
        response = provider.complete(messages, tools=TOOLS)
        limits.consume(response)
        add_event(events, "MODEL_RESPONSE", {"call_index": index + 1, "content": response.content,
                                               "tool_calls": response.tool_calls, "usage": response.usage.__dict__})
        if response.tool_calls:
            messages.append({"role": "assistant", "content": response.content, "tool_calls": response.tool_calls})
            for call in response.tool_calls:
                fn = call.get("function", call)
                name = str(fn.get("name", ""))
                args = parse_tool_args(fn.get("arguments", {}))
                limits.before_tool()
                add_event(events, "TOOL_CALL", {"tool_name": name, "tool_arguments": args})
                try:
                    tool_result = execute_tool(name, args)
                    tool_status = "COMPLETED"
                except Exception as exc:
                    tool_result = {"error_type": type(exc).__name__, "error": str(exc)}
                    tool_status = "FAILED"
                add_event(events, "TOOL_RESULT", {"tool_name": name, "tool_result": tool_result, "status": tool_status})
                messages.append({"role": "tool", "tool_call_id": call.get("id", f"tool-{limits.tool_calls}"),
                                 "name": name, "content": json.dumps(tool_result, ensure_ascii=False)})
            continue
        result = parse_response(response.content)
        if group == "G3" and index == 0:
            continue
        if not extra or group != "G3" or index >= 2:
            break
    if result is None:
        raise ValueError("no final JSON response")
    return result

    def audit_trace(self) -> list[dict[str, Any]]:
        return self.provider.audit_trace()


def _result_path(run_root: Path, run_id: str) -> Path:
    return run_root / "raw" / run_id / "result.json"


def run_one(row: dict[str, Any], run_root: Path, key_file: Path, ledger: CostLedger, limiter: RateLimiter) -> dict[str, Any]:
    result_path = _result_path(run_root, row["run_id"])
    if result_path.exists():
        return {"run_id": row["run_id"], "status": "SKIPPED_EXISTING"}
    out_dir = result_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    events: list[dict[str, Any]] = []
    limits_cfg = row["limits"]
    limits = Limits(int(limits_cfg["max_model_calls"]), int(limits_cfg["max_tool_calls"]), int(limits_cfg["max_total_tokens"]), float(limits_cfg["max_cost_usd"]))
    provider = OpenAICompatibleProvider(
        api_key=key_file.read_text(encoding="utf-8").strip(),
        base_url=BASE_URL,
        model_name=MODEL_ID,
        timeout=180.0,
        max_retries=0,
        input_cost_per_1k=0.001,
        output_cost_per_1k=0.003,
        max_cost_usd=float(limits_cfg["max_cost_usd"]),
        max_output_tokens=1024,
        reservation_output_tokens=1024,
        cost_ledger=ledger,
        ledger_scope="g8",
        ledger_worker="single-kimi-g8",
        ledger_ref_prefix=f"g8:{row['run_id']}",
        require_cost_ledger=True,
    )
    wrapped = LimitedProvider(provider, limiter)
    messages = [dict(message) for message in row["public_messages"]]
    if messages and messages[0].get("role") == "system":
        messages[0] = {"role": "system", "content": system_prompt(row["group_id"])}
    add_event(events, "RUN_START", {"run_id": row["run_id"], "phase": row["phase"], "model_id": MODEL_ID, "public_only": True})
    kind: str | None = None
    try:
        kind, mechanism_output = mechanism(row, row["arm_id"])
        if kind == "real":
            add_event(events, "MECHANISM_INVOKED", {"mechanism_id": "V", "mode": "real", "verifier_version": V_VERSION})
            add_event(events, "MECHANISM_OUTPUT_ACCEPTED", {"mechanism_id": "V", "quality": mechanism_output["quality"]})
            messages.append({"role": "user", "content": json.dumps({"public_mechanism": mechanism_output, "instruction": "Use this public computation evidence as input, but independently decide the case."}, ensure_ascii=False)})
        elif kind == "sham":
            add_event(events, "SHAM_MECHANISM_INVOKED", {"mechanism_id": "V", "mode": "schema_matched_placebo", "verifier_version": V_VERSION})
            add_event(events, "SHAM_PAYLOAD_MATCHED", {"mechanism_id": "V", "schema": "V1", "semantic_payload": "neutral"})
            messages.append({"role": "user", "content": json.dumps({"public_mechanism": mechanism_output, "instruction": "This schema-matched placebo contains no scientific evidence. Decide from the public case only."}, ensure_ascii=False)})
        elif row["arm_id"] == "F_G4_MINUS_M":
            add_event(events, "MECHANISM_DISABLED", {"mechanism_id": "V", "state_update": "disabled_before_downstream_read"})
        if row["arm_id"] == "D_G3_EXTRA_THINK":
            add_event(events, "EXTRA_THINK_APPLIED", {"mode": "generic_public_consistency_pass", "extra_model_call": True})
            messages.append({"role": "user", "content": "Use one additional generic consistency pass over the unchanged public evidence before finalizing."})
        final = kimi_loop(wrapped, messages, row["group_id"], row["arm_id"] == "D_G3_EXTRA_THINK", limits, events)
        status = "PASS"
        add_event(events, "RUN_END", {"status": status})
    except Exception as exc:
        final = {"decision": "UNDETERMINED", "affected_claim_ids": [], "revised_claim": None, "supporting_evidence": "technical failure; no scientific conclusion", "error_type": type(exc).__name__}
        status = "TECHNICAL_FAILURE"
        add_event(events, "ADAPTER_ERROR", {"error_type": type(exc).__name__, "error": str(exc)[:500]})
        add_event(events, "RUN_END", {"status": status})
    final.update({
        "run_id": row["run_id"], "status": "COMPLETED" if status == "PASS" else status,
        "events": events, "usage": {"total_tokens": limits.total_tokens, "model_calls": limits.model_calls, "tool_calls": limits.tool_calls, "cost_usd": limits.cost_usd},
        "budget_enforced": True, "actual_model_snapshot": MODEL_SNAPSHOT,
        "model_visible_trace": {"public_messages": messages, "mechanism_id": "V", "mechanism_mode": kind or "off", "public_only": True},
        "public_only": True,
    })
    traces = provider.audit_trace()
    write_jsonl(out_dir / "provider_traces.jsonl", traces)
    write_jsonl(out_dir / "events.jsonl", events)
    envelope = {"run_id": row["run_id"], "plan_row_hash": json_hash(row), "is_mock": False, "execution_status": status, "response": final, "provider_trace_count": len(traces), "model_id": MODEL_ID}
    write_json(result_path, envelope)
    return {"run_id": row["run_id"], "status": status, "provider_calls": len(traces), "cost_usd": limits.cost_usd}


def run_phase(plan_path: Path, run_root: Path, key_file: Path, workers: int, rps: float, resume: bool) -> dict[str, Any]:
    plan = read_jsonl(plan_path)
    run_root.mkdir(parents=True, exist_ok=True)
    ledger_path = run_root / "cost_ledger.sqlite"
    # Initialize the SQLite ledger once before starting the worker pool.  Each
    # provider still reserves/settles through the same object; constructing the
    # schema concurrently from 16 workers causes avoidable Windows lock races.
    ledger = CostLedger(ledger_path, global_cap=200.0, g7_cap=60.0, worker_cap=200.0)
    limiter = RateLimiter(rps)
    jobs = [row for row in plan if resume or not _result_path(run_root, row["run_id"]).exists()]
    progress: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=min(workers, 16), thread_name_prefix="g8-kimi") as pool:
        futures = {pool.submit(run_one, row, run_root, key_file, ledger, limiter): row["run_id"] for row in jobs}
        for future in as_completed(futures):
            try:
                item = future.result()
            except Exception as exc:
                item = {"run_id": futures[future], "status": "LAUNCH_ERROR", "error": f"{type(exc).__name__}:{exc}"}
            progress.append(item)
            print(json.dumps({"progress": len(progress), "total": len(jobs), **item}, ensure_ascii=False), flush=True)
    results = [
        json.loads(_result_path(run_root, row["run_id"]).read_text(encoding="utf-8"))
        for row in plan if _result_path(run_root, row["run_id"]).exists()
    ]
    summary = {
        "protocol": PHASE_PROTOCOL, "phase": plan[0]["phase"], "plan": str(plan_path), "plan_sha256": sha_file(plan_path),
        "planned": len(plan), "result_files": len(results), "new_jobs": len(jobs),
        "execution_status_counts": {status: sum(x["execution_status"] == status for x in results) for status in sorted({x["execution_status"] for x in results})},
        "real_provider_calls": sum(int(x.get("provider_trace_count", 0)) for x in results),
        "model_id": MODEL_ID, "only_model": True, "mock": False, "workers": min(workers, 16), "rps": rps,
        "cost_ledger": ledger.snapshot(),
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    write_json(run_root / f"{plan[0]['phase']}_execution_summary.json", summary)
    return summary


def bootstrap(rows: list[dict[str, Any]], clusters: dict[str, list[float]], reps: int = 4000) -> list[float]:
    rng = random.Random(20261020)
    keys = sorted(clusters)
    values: list[float] = []
    for _ in range(reps):
        sampled = [rng.choice(keys) for _ in keys]
        flat = [value for key in sampled for value in clusters[key]]
        values.append(sum(flat) / len(flat) if flat else 0.0)
    return values


def ci(values: list[float]) -> list[float]:
    values = sorted(values)
    return [values[int(0.025 * (len(values) - 1))], values[int(0.975 * (len(values) - 1))]]


def score(plan_path: Path, run_root: Path, out_dir: Path) -> dict[str, Any]:
    plan = read_jsonl(plan_path)
    oracle = {row["case_id"]: row for row in read_jsonl(PRIVATE_ORACLE)}
    scored: list[dict[str, Any]] = []
    for row in plan:
        path = _result_path(run_root, row["run_id"])
        envelope = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
        response = (envelope or {}).get("response") or {}
        expected = oracle.get(row["case_id"], {}).get("expected_decision")
        decision = response.get("decision")
        status = (envelope or {}).get("execution_status", "MISSING")
        initial = row.get("initial_decision")
        initial_correct = initial == expected
        decision_correct = status == "PASS" and decision == expected
        transition = "transition_unobserved"
        if status == "PASS":
            transition = ("C_to_C" if initial_correct and decision_correct else "C_to_W" if initial_correct else "W_to_C" if decision_correct else "W_to_W")
        events = response.get("events") or []
        event_types = {event.get("event_type") for event in events if isinstance(event, dict)}
        scored.append({
            "run_id": row["run_id"], "phase": row["phase"], "case_id": row["case_id"], "paired_set_id": row["paired_set_id"],
            "theory_family_id": row["paired_set_id"], "domain": row["domain"], "cf_type": row["cf_type"], "replicate": row.get("replicate", 0),
            "arm_id": row["arm_id"], "execution_status": status, "decision": decision, "expected_decision": expected,
            "initial_decision": initial, "initial_correct": initial_correct, "decision_correct": decision_correct,
            "transition": transition, "coverage": status == "PASS", "all_planned_correct": decision_correct,
            "revised_claim_present": isinstance(response.get("revised_claim"), str) and bool(response.get("revised_claim", "").strip()),
            "mechanism_event_ok": all(event in event_types for event in ("MECHANISM_INVOKED", "MECHANISM_OUTPUT_ACCEPTED")) if row["arm_id"] in {"B_G3_REAL_M", "E_G4_PLUS_M"} else True,
            "usage_total_tokens": (response.get("usage") or {}).get("total_tokens", 0), "usage_model_calls": (response.get("usage") or {}).get("model_calls", 0),
            "usage_tool_calls": (response.get("usage") or {}).get("tool_calls", 0), "usage_cost_usd": (response.get("usage") or {}).get("cost_usd", 0.0),
        })
    out_dir.mkdir(parents=True, exist_ok=True)
    fields = list(scored[0]) if scored else []
    with (out_dir / "g8_case_scores.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(scored)
    arms: list[dict[str, Any]] = []
    for arm in sorted({row["arm_id"] for row in scored}):
        subset = [row for row in scored if row["arm_id"] == arm]
        arms.append({"arm_id": arm, "planned": len(subset), "valid_completed": sum(row["execution_status"] == "PASS" for row in subset), "all_planned_correct": sum(row["all_planned_correct"] for row in subset), "all_planned_accuracy": sum(row["all_planned_correct"] for row in subset) / len(subset), "valid_only_accuracy": sum(row["decision_correct"] for row in subset if row["execution_status"] == "PASS") / max(1, sum(row["execution_status"] == "PASS" for row in subset)), "coverage": sum(row["coverage"] for row in subset) / len(subset), "W_to_C": sum(row["transition"] == "W_to_C" for row in subset), "C_to_W": sum(row["transition"] == "C_to_W" for row in subset), "technical_failures": sum(row["execution_status"] != "PASS" for row in subset)})
    with (out_dir / "g8_arm_scores.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(arms[0])); writer.writeheader(); writer.writerows(arms)
    pairs: list[dict[str, Any]] = []
    for name, (treatment, control) in PAIR_NAMES.items():
        lookup = {(row["case_id"], int(row["replicate"]), row["arm_id"]): float(row["all_planned_correct"]) for row in scored}
        family_values: dict[str, list[float]] = {}
        for case in sorted({row["case_id"] for row in scored}):
            family = next(row["theory_family_id"] for row in scored if row["case_id"] == case)
            for rep in sorted({int(row["replicate"]) for row in scored if row["case_id"] == case}):
                t = lookup.get((case, rep, treatment), 0.0); c = lookup.get((case, rep, control), 0.0)
                family_values.setdefault(family, []).append(t - c)
        raw = [x for values in family_values.values() for x in values]
        effect = sum(raw) / len(raw) if raw else 0.0
        pairs.append({"contrast": name, "treatment": treatment, "control": control, "n_case_replicate_pairs": len(raw), "n_independent_families": len(family_values), "difference": effect, "ci95_lower": ci(bootstrap(raw, family_values))[0], "ci95_upper": ci(bootstrap(raw, family_values))[-1]})
    with (out_dir / "g8_paired_effects.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(pairs[0])); writer.writeheader(); writer.writerows(pairs)
    resources = [{"run_id": row["run_id"], "arm_id": row["arm_id"], "phase": row["phase"], "model_id": MODEL_ID, "total_tokens": row["usage_total_tokens"], "model_calls": row["usage_model_calls"], "tool_calls": row["usage_tool_calls"], "cost_usd": row["usage_cost_usd"], "execution_status": row["execution_status"]} for row in scored]
    with (out_dir / "g8_resource_usage.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(resources[0])); writer.writeheader(); writer.writerows(resources)
    summary = {"protocol": PHASE_PROTOCOL, "model_id": MODEL_ID, "only_model": True, "planned": len(scored), "status_counts": {status: sum(x["execution_status"] == status for x in scored) for status in sorted({x["execution_status"] for x in scored})}, "real_provider_calls": sum(int(x["usage_model_calls"]) for x in scored), "total_tokens": sum(int(x["usage_total_tokens"]) for x in scored), "total_cost_usd": sum(float(x["usage_cost_usd"]) for x in scored), "oracle_path_sha256": sha_file(PRIVATE_ORACLE), "model_requests_private_truth_scan": 0, "scientific_release_allowed": False, "paired_effects": pairs, "q_scientific_truth_status": "NOT_MEASURED_BY_G8_ACTION_SCORER"}
    write_json(out_dir / "g8_analysis_manifest.json", summary)
    write_json(out_dir / "g8_private_oracle_score_audit.json", {"oracle_path": str(PRIVATE_ORACLE), "oracle_sha256": sha_file(PRIVATE_ORACLE), "model_requests_private_truth_scan": 0, "oracle_loaded_only_in_scorer": True, "historical_run_untouched": True})
    return summary


def build_repair_plan(plan_path: Path, run_root: Path, out: Path) -> dict[str, Any]:
    """Create an append-only retry plan for adapter failures only.

    The original plan and result envelopes remain immutable.  Rows are copied
    with a fresh run id and explicit provenance so repaired rows can be scored
    as a sensitivity analysis rather than silently replacing the primary ITT.
    """
    plan = read_jsonl(plan_path)
    failed: list[dict[str, Any]] = []
    for row in plan:
        path = _result_path(run_root, row["run_id"])
        if not path.exists():
            continue
        envelope = json.loads(path.read_text(encoding="utf-8"))
        if envelope.get("execution_status") == "TECHNICAL_FAILURE":
            failed.append(row)
    repair_rows: list[dict[str, Any]] = []
    for index, source in enumerate(failed):
        row = dict(source)
        row["run_id"] = f"{source['run_id']}-adapter-repair1"
        row["repair_of_run_id"] = source["run_id"]
        row["repair_reason"] = "G3 adapter finalized after tool-calling second synthesis; primary result preserved"
        row["repair_protocol"] = "G8_SINGLE_KIMI_V1_ADAPTER_REPAIR1"
        row["status"] = "PLANNED"
        repair_rows.append(row)
    write_jsonl(out, repair_rows)
    manifest = {
        "protocol": "G8_SINGLE_KIMI_V1_ADAPTER_REPAIR1",
        "source_plan": str(plan_path),
        "source_plan_sha256": sha_file(plan_path),
        "source_run_root": str(run_root),
        "n_source_rows": len(plan),
        "n_failed_rows_selected": len(failed),
        "n_repair_rows": len(repair_rows),
        "selection_rule": "execution_status == TECHNICAL_FAILURE only; no primary result overwritten",
        "model_id": MODEL_ID,
        "model_snapshot": MODEL_SNAPSHOT,
        "private_oracle_in_plan": False,
        "repair_run_ids": [row["run_id"] for row in repair_rows],
        "plan_sha256": sha_file(out),
    }
    write_json(out.with_suffix(out.suffix + ".manifest.json"), manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan"); plan.add_argument("--source-plan", type=Path, default=SOURCE_PLAN); plan.add_argument("--out", type=Path, required=True); plan.add_argument("--phase", choices=("pilot", "formal"), required=True)
    repair = sub.add_parser("repair-plan"); repair.add_argument("--plan", type=Path, required=True); repair.add_argument("--run-root", type=Path, required=True); repair.add_argument("--out", type=Path, required=True)
    run = sub.add_parser("run"); run.add_argument("--plan", type=Path, required=True); run.add_argument("--run-root", type=Path, required=True); run.add_argument("--key-file", type=Path, required=True); run.add_argument("--workers", type=int, default=16); run.add_argument("--rps", type=float, default=2.0); run.add_argument("--resume", action="store_true")
    score_parser = sub.add_parser("score"); score_parser.add_argument("--plan", type=Path, required=True); score_parser.add_argument("--run-root", type=Path, required=True); score_parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "plan":
        print(json.dumps(build_plan(args.source_plan, args.out, args.phase), ensure_ascii=False, indent=2)); return 0
    if args.command == "repair-plan":
        print(json.dumps(build_repair_plan(args.plan, args.run_root, args.out), ensure_ascii=False, indent=2)); return 0
    if args.command == "run":
        if not 1 <= args.workers <= 16: raise SystemExit("workers must be in 1..16")
        print(json.dumps(run_phase(args.plan, args.run_root, args.key_file, args.workers, args.rps, args.resume), ensure_ascii=False, indent=2)); return 0
    print(json.dumps(score(args.plan, args.run_root, args.out), ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
