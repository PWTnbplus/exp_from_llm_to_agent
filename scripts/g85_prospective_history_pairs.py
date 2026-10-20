#!/usr/bin/env python3
"""Generate a real-Kimi prospective clean/recovery history-pair cohort.

This cohort is controlled prospective evidence, not historical provenance.  It
is intentionally isolated so it can exercise the G8.5 consumer without
silently upgrading the blocked confirmatory status.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.v9.common import append_jsonl, extract_json, read_jsonl, sha_obj, write_json, write_jsonl
from scripts.v9.provider import SingleKimiProvider

MODEL_ID = "kimi-k2.5"
BASE_URL = "https://token.ctflow.cn/v1"
PROTOCOL = "G7_PROSPECTIVE_HISTORY_PAIR_V1"


def build_plan(out: Path) -> dict[str, Any]:
    cases = [
        {"pair_id": "HP-AFFINE", "canonical_state_id": "S-AFFINE-MONO", "evidence_id": "E-AFFINE-DERIVATIVE", "problem": "Determine whether f(x)=2*x+1 is nondecreasing on x>=0.", "evidence": "Public derivative evidence states f'(x)=2>=0 on x>=0.", "expected_decision": "ACCEPT"},
        {"pair_id": "HP-QUADRATIC", "canonical_state_id": "S-QUADRATIC-MONO", "evidence_id": "E-QUADRATIC-DERIVATIVE", "problem": "Determine whether f(x)=x^2 is nondecreasing on x>=0.", "evidence": "Public derivative evidence states f'(x)=2*x>=0 on x>=0.", "expected_decision": "ACCEPT"},
    ]
    rows = []
    for case in cases:
        for history_kind in ("H_CLEAN", "H_RECOVERED"):
            row = dict(case)
            row.update({"history_kind": history_kind, "history_provenance": "prospective_controlled", "model_id": MODEL_ID, "protocol": PROTOCOL, "private_truth_injected": False, "status": "PLANNED"})
            if history_kind == "H_CLEAN":
                row["public_history_instruction"] = "Produce a clean auditable history: observe_state, apply_evidence, validate_update, commit."
            else:
                row["public_history_instruction"] = "A public execution interruption occurred after evidence application. Recover the visible history by replaying the public evidence, record the recovery event, validate the update, and commit."
            rows.append(row)
    write_jsonl(out, rows)
    manifest = {"protocol": PROTOCOL, "model_id": MODEL_ID, "only_model": True, "pair_count": len(cases), "row_count": len(rows), "history_kinds": ["H_CLEAN", "H_RECOVERED"], "history_provenance": "prospective_controlled", "private_truth_in_plan": False, "plan_sha256": sha_obj(rows)}
    write_json(out.with_suffix(out.suffix + ".manifest.json"), manifest)
    return manifest


def run(plan_path: Path, run_root: Path, key_file: Path, max_cost: float, max_output_tokens: int = 1024) -> dict[str, Any]:
    plan = read_jsonl(plan_path)
    run_root.mkdir(parents=True, exist_ok=True)
    provider = SingleKimiProvider(run_root, key_file, BASE_URL, MODEL_ID, max_cost, 180.0, max_output_tokens=max_output_tokens)
    records_path = run_root / "history_records.jsonl"
    existing = {(row.get("pair_id"), row.get("history_kind")) for row in read_jsonl(records_path)}
    statuses: dict[str, int] = {}
    for row in plan:
        key = (row["pair_id"], row["history_kind"])
        if key in existing:
            continue
        system = "You are a public scientific-history recorder using only the supplied problem and evidence. Never access private truth, files, network, hidden answers, or prior hidden tasks. Return JSON only with history_events, state_after, evidence_used, and recovery_status."
        user = {"pair_id": row["pair_id"], "canonical_state_id": row["canonical_state_id"], "evidence_id": row["evidence_id"], "problem": row["problem"], "public_evidence": row["evidence"], "history_kind": row["history_kind"], "instruction": row["public_history_instruction"]}
        result = provider.call(PROTOCOL, f"{row['pair_id']}:{row['history_kind']}", row["history_kind"], [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(user, ensure_ascii=False, sort_keys=True)}])
        candidate = None
        status = "SUCCESS"
        if result.get("content"):
            try:
                candidate = extract_json(result["content"])
            except Exception:
                status = "INVALID_OR_TRUNCATED_RESPONSE"
        else:
            status = "PROVIDER_ERROR"
        record = {"protocol": PROTOCOL, "pair_id": row["pair_id"], "canonical_state_id": row["canonical_state_id"], "evidence_id": row["evidence_id"], "history_kind": row["history_kind"], "history_provenance": "prospective_controlled", "candidate": candidate, "raw_content_present": bool(result.get("content")), "provider_error": result.get("error"), "call_number": result["call_number"], "private_truth_injected": False, "input_sha256": sha_obj(user), "terminal_status": status, "created_at_utc": datetime.now(timezone.utc).isoformat()}
        append_jsonl(records_path, record)
        statuses[status] = statuses.get(status, 0) + 1
    rows = read_jsonl(records_path)
    traces = read_jsonl(run_root / "logs/provider_traces.jsonl")
    total_cost = sum(float(((row.get("trace") or {}).get("response") or {}).get("usage", {}).get("cost_usd", 0.0)) for row in traces)
    total_tokens = sum(int(((row.get("trace") or {}).get("response") or {}).get("usage", {}).get("total_tokens", 0) or 0) for row in traces)
    summary = {"protocol": PROTOCOL, "model_id": MODEL_ID, "only_model": True, "planned": len(plan), "recorded": len(rows), "new_status_counts": statuses, "real_provider_calls": provider.call_no, "total_tokens": total_tokens, "total_cost_usd": total_cost, "history_provenance": "prospective_controlled", "private_truth_injected": False, "science_status": "PROSPECTIVE_NOT_HISTORICAL_CONFIRMATION"}
    write_json(run_root / "execution_summary.json", summary)
    return summary


def build_repair_plan(plan_path: Path, out: Path) -> dict[str, Any]:
    rows = [row for row in read_jsonl(plan_path) if row.get("history_kind") == "H_RECOVERED"]
    for row in rows:
        row["repair_protocol"] = "G7_PROSPECTIVE_HISTORY_PAIR_V1_OUTPUT_REPAIR1"
        row["repair_reason"] = "primary recovered history response was truncated at the original output ceiling; primary record preserved"
    write_jsonl(out, rows)
    manifest = {"protocol": "G7_PROSPECTIVE_HISTORY_PAIR_V1_OUTPUT_REPAIR1", "source_plan": str(plan_path), "source_plan_sha256": sha_obj(read_jsonl(plan_path)), "rows": len(rows), "selection_rule": "H_RECOVERED rows only; primary records untouched", "model_id": MODEL_ID, "max_output_tokens": 1024, "plan_sha256": sha_obj(rows)}
    write_json(out.with_suffix(out.suffix + ".manifest.json"), manifest)
    return manifest


def audit(run_root: Path, out: Path, supplemental_root: Path | None = None) -> dict[str, Any]:
    rows = read_jsonl(run_root / "history_records.jsonl")
    if supplemental_root is not None:
        merged = {(row.get("pair_id"), row.get("history_kind")): row for row in rows}
        for row in read_jsonl(supplemental_root / "history_records.jsonl"):
            merged[(row.get("pair_id"), row.get("history_kind"))] = row
        rows = list(merged.values())
    by_pair: dict[str, dict[str, dict[str, Any]]] = {}
    for row in rows:
        by_pair.setdefault(row["pair_id"], {})[row["history_kind"]] = row
    findings = []
    for pair_id, pair in by_pair.items():
        clean = pair.get("H_CLEAN")
        recovered = pair.get("H_RECOVERED")
        ok = bool(clean and recovered and clean["canonical_state_id"] == recovered["canonical_state_id"] and clean["evidence_id"] == recovered["evidence_id"] and clean["history_provenance"] == "prospective_controlled" and recovered["history_provenance"] == "prospective_controlled" and clean["private_truth_injected"] is False and recovered["private_truth_injected"] is False and clean.get("candidate") and recovered.get("candidate"))
        findings.append({"pair_id": pair_id, "same_state": bool(clean and recovered and clean["canonical_state_id"] == recovered["canonical_state_id"]), "same_evidence": bool(clean and recovered and clean["evidence_id"] == recovered["evidence_id"]), "both_structured": bool(clean and recovered and clean.get("candidate") and recovered.get("candidate")), "history_provenance": "prospective_controlled", "private_truth_injected": False, "eligible_for_confirmatory_history_claim": False, "audit_status": "PASS" if ok else "FAIL"})
    result = {"protocol": PROTOCOL, "model_id": MODEL_ID, "only_model": True, "base_run_root": str(run_root), "supplemental_run_root": str(supplemental_root) if supplemental_root else None, "pair_count": len(by_pair), "record_count": len(rows), "pair_findings": findings, "all_structural_checks_pass": all(x["audit_status"] == "PASS" for x in findings), "confirmatory_eligibility": "NO_PROSPECTIVE_NOT_HISTORICAL", "private_truth_injected": False}
    write_json(out, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("plan"); p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("repair-plan"); p.add_argument("--plan", type=Path, required=True); p.add_argument("--out", type=Path, required=True)
    p = sub.add_parser("run"); p.add_argument("--plan", type=Path, required=True); p.add_argument("--run-root", type=Path, required=True); p.add_argument("--key-file", type=Path, required=True); p.add_argument("--max-cost", type=float, default=20.0); p.add_argument("--max-output-tokens", type=int, default=1024)
    p = sub.add_parser("audit"); p.add_argument("--run-root", type=Path, required=True); p.add_argument("--supplemental-root", type=Path); p.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "plan": result = build_plan(args.out)
    elif args.command == "repair-plan": result = build_repair_plan(args.plan, args.out)
    elif args.command == "run": result = run(args.plan, args.run_root, args.key_file, args.max_cost, args.max_output_tokens)
    else: result = audit(args.run_root, args.out, args.supplemental_root)
    print(json.dumps(result, ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
