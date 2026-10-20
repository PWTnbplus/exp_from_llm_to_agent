"""Independent read-only audit for a completed V10 single-Kimi run.

This process does not call the provider and does not use the runner's score
tables as evidence of completion.  It checks the frozen plan, append-only
response lineage, ledger terminality, private/public separation, certificate
replay, and model identity from raw artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.v9.common import read_jsonl, sha256_file, write_json

from .machine_truth import replay_certificate


MODEL_ID = "kimi-k2.5"
TERMINAL = {"COMPLETED", "EXPLICIT_FAILURE"}
FORBIDDEN_PUBLIC_KEYS = {
    "expected_action_truth", "machine_certificate", "real_certificate", "expected_relation",
    "truth_key", "answer_key", "private_truth", "private_Y", "expected_action",
}
FORBIDDEN_PROMPT_MARKERS = {
    "expected_action_truth", "machine_certificate", "real_certificate", "truth_key_sent_to_model",
    "answer_key", "private_truth", "private_y_injected",
}
GENERATED_OUTPUT_FIELDS = {
    "checkpoint_output", "shared_checkpoint_output", "d3_candidate", "prior_D0",
    "V", "L", "first_action", "frozen_plan",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha_obj(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _walk_keys(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        found.update(str(k) for k in value)
        for child in value.values():
            found.update(_walk_keys(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_walk_keys(child))
    return found


def _remove_generated_outputs(value: Any) -> Any:
    """Remove prior model outputs before checking executor-supplied payload."""
    if isinstance(value, dict):
        return {key: _remove_generated_outputs(child) for key, child in value.items() if key not in GENERATED_OUTPUT_FIELDS}
    if isinstance(value, list):
        return [_remove_generated_outputs(child) for child in value]
    return value


def _ledger_rows(path: Path) -> list[dict[str, Any]]:
    connection = sqlite3.connect(path)
    try:
        return [
            {"unit_id": row[0], "namespace": row[1], "status": row[2], "attempts": row[3], "last_error": row[4]}
            for row in connection.execute("SELECT unit_id,namespace,status,attempts,last_error FROM units ORDER BY unit_id")
        ]
    finally:
        connection.close()


def _response_rows(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    rows = read_jsonl(path)
    ids = [str(row.get("unit_id")) for row in rows]
    duplicates = sorted({unit_id for unit_id in ids if ids.count(unit_id) > 1})
    return rows, duplicates


def _certificate_checks(run_root: Path) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    for namespace, key in [("q", "task_id"), ("g7", "task_id"), ("lu", "task_id")]:
        truth_path = run_root / "private_truth" / f"{namespace}.jsonl"
        for row in read_jsonl(truth_path):
            claim = row.get("claim_ir")
            if not claim:
                continue
            replay = replay_certificate(claim["expression"], claim["relation"], claim["domain"])
            cert = row.get("machine_certificate") or row.get("real_certificate") or {}
            checks.append({"namespace": namespace, "id": row.get(key), "certificate_status": cert.get("status"), "replay_status": replay.get("status"), "match": cert.get("status") == replay.get("status"), "replay": replay})
    return {"n": len(checks), "matched": sum(int(row["match"]) for row in checks), "all_match": bool(checks) and all(row["match"] for row in checks), "rows": checks}


def audit(repo: Path, run_root: Path, audit_root: Path) -> dict[str, Any]:
    prereg = json.loads((run_root / "preregistration.json").read_text(encoding="utf-8"))
    plan = read_jsonl(run_root / "frozen_plan.jsonl")
    public = read_jsonl(run_root / "public_cases.jsonl")
    responses, duplicate_response_ids = _response_rows(run_root / "model_responses.jsonl")
    raw_events = read_jsonl(run_root / "raw_model_events.jsonl")
    ledger = _ledger_rows(run_root / "execution_ledger.sqlite")
    plan_ids = [str(row["unit_id"]) for row in plan]
    ledger_by_id = {row["unit_id"]: row for row in ledger}
    response_by_id = {str(row.get("unit_id")): row for row in responses}
    terminal = all(row.get("status") in TERMINAL for row in ledger) and set(plan_ids) == set(ledger_by_id)
    response_terminal = all(unit_id in response_by_id and response_by_id[unit_id].get("final") is True for unit_id in plan_ids)

    public_keys = sorted(_walk_keys(public))
    forbidden_public = sorted(set(public_keys) & FORBIDDEN_PUBLIC_KEYS)
    prompt_markers: list[dict[str, Any]] = []
    model_ids: set[str] = set()
    for event in raw_events:
        model_ids.add(str(event.get("model_id")))
        # System messages necessarily state the blind-folding rule (for
        # example, "never access private truth").  Leakage auditing applies
        # to the public task payload, not to that protocol instruction.
        user_messages = []
        for message in (event.get("request_messages") or []):
            if message.get("role") != "user":
                continue
            content = message.get("content")
            try:
                content = _remove_generated_outputs(json.loads(content))
            except (TypeError, json.JSONDecodeError):
                content = content
            user_messages.append({"role": "user", "content": content})
        text = json.dumps(user_messages, ensure_ascii=False, sort_keys=True).lower()
        hits = sorted(marker for marker in FORBIDDEN_PROMPT_MARKERS if marker.lower() in text)
        if hits:
            prompt_markers.append({"unit_id": event.get("unit_id"), "attempt_id": event.get("attempt_id"), "markers": hits})
    for row in responses:
        model_ids.add(str(row.get("model_id")))
    for trace in read_jsonl(run_root / "logs/provider_traces.jsonl"):
        model_ids.add(str((trace.get("trace") or {}).get("model", trace.get("model_id", MODEL_ID))))

    attempts_ok = all(1 <= int(row.get("attempts", 0)) <= 2 for row in ledger)
    planned_hash_ok = prereg.get("prospective_plan_hash") == sha256_file(run_root / "frozen_plan.jsonl")
    public_hash_ok = prereg.get("public_cases_sha256") == sha256_file(run_root / "public_cases.jsonl")
    certificates = _certificate_checks(run_root)
    artifact_requirements = {
        "G6_LEGACY_LINEAGE_276.jsonl": (audit_root / "G6_LEGACY_LINEAGE_276.jsonl").exists(),
        "G6_CLAIM_IR.jsonl": (audit_root / "G6_CLAIM_IR.jsonl").exists(),
        "G6_MACHINE_CERTS": (audit_root / "G6_MACHINE_CERTS").is_dir(),
        "G6_NEW_FROZEN_PLAN.jsonl": (audit_root / "G6_NEW_FROZEN_PLAN.jsonl").exists(),
        "G6_NEW_RAW_EVENTS": (audit_root / "G6_NEW_RAW_EVENTS").is_dir(),
        "G7_CHECKPOINTS.jsonl": (audit_root / "G7_CHECKPOINTS.jsonl").exists(),
        "G7_FORK_PLAN.jsonl": (audit_root / "G7_FORK_PLAN.jsonl").exists(),
        "G7_TRACE_LINEAGE.jsonl": (audit_root / "G7_TRACE_LINEAGE.jsonl").exists(),
        "Q_MACHINE_FIRST_TRUTH_CERTS": (audit_root / "Q_MACHINE_FIRST_TRUTH_CERTS").is_dir(),
        "LU_PAIR_PLAN.jsonl": (audit_root / "LU_PAIR_PLAN.jsonl").exists(),
    }
    checks = {
        "single_model": model_ids <= {MODEL_ID} and MODEL_ID in model_ids,
        "plan_hash": planned_hash_ok,
        "public_hash": public_hash_ok,
        "all_plan_units_in_ledger": set(plan_ids) == set(ledger_by_id),
        "all_plan_units_terminal": terminal,
        "all_plan_units_have_final_response": response_terminal,
        "no_duplicate_final_response_ids": not duplicate_response_ids,
        "attempt_bounds": attempts_ok,
        "no_forbidden_public_keys": not forbidden_public,
        "no_private_prompt_markers": not prompt_markers,
        "machine_certificates_replay": certificates["all_match"],
        "required_v10_artifacts": all(artifact_requirements.values()),
    }
    result = {
        "audit_type": "INDEPENDENT_READ_ONLY_AUDIT",
        "generated_at_utc": now_utc(),
        "repo": str(repo),
        "run_root": str(run_root),
        "audit_root": str(audit_root),
        "model_ids_observed": sorted(model_ids),
        "plan_units": len(plan),
        "response_rows": len(responses),
        "raw_event_rows": len(raw_events),
        "ledger_status_counts": dict(Counter(row["status"] for row in ledger)),
        "provider_call_rows": len(read_jsonl(run_root / "logs/provider_traces.jsonl")),
        "checks": checks,
        "forbidden_public_keys": forbidden_public,
        "prompt_markers": prompt_markers,
        "duplicate_response_ids": duplicate_response_ids,
        "certificate_checks": certificates,
        "artifact_requirements": artifact_requirements,
        "historical_denominators_unchanged": prereg.get("historical_denominators_unchanged"),
        "audit_pass": all(checks.values()),
    }
    write_json(audit_root / "INDEPENDENT_READ_ONLY_AUDIT.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--audit-root", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.repo.resolve(), args.run_root.resolve(), args.audit_root.resolve())
    print(json.dumps({"audit_pass": result["audit_pass"], "checks": result["checks"]}, ensure_ascii=False, indent=2))
    return 0 if result["audit_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
