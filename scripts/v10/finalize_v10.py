"""Finalize a completed V10 machine experiment without changing its data."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.v9.common import read_jsonl, sha256_file, write_json


MODEL_ID = "kimi-k2.5"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_files(root: Path, exclude: set[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    if not root.exists():
        return result
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name not in exclude:
            result[path.relative_to(root).as_posix()] = sha256_file(path)
    return result


def finalize(repo: Path, run_root: Path, audit_root: Path, test_exit_code: int | None) -> dict[str, Any]:
    manifest = json.loads((run_root / "manifest.json").read_text(encoding="utf-8"))
    summary = json.loads((run_root / "execution_summary.json").read_text(encoding="utf-8"))
    audit = json.loads((audit_root / "INDEPENDENT_READ_ONLY_AUDIT.json").read_text(encoding="utf-8"))
    test_path = audit_root / "TEST_RESULTS.json"
    if test_exit_code is not None:
        test_result = {"exit_code": test_exit_code, "recorded": True, "suite": "V10 pre-acceptance regression suite", "note": "Recorded from the actual pytest process; the artifact-contract test is rerun after finalization."}
        write_json(test_path, test_result)
    else:
        test_result = json.loads(test_path.read_text(encoding="utf-8")) if test_path.exists() else {"exit_code": None, "recorded": False}
    scores = summary.get("scores", {})
    alternate_path = audit_root / "MATH_ALTERNATE_VERIFICATION.json"
    alternate = json.loads(alternate_path.read_text(encoding="utf-8")) if alternate_path.exists() else None
    machine_execution_accepted = bool(audit.get("audit_pass")) and (test_result.get("exit_code") in (None, 0))
    acceptance = {
        "acceptance_type": "MACHINE_EXECUTION_ACCEPTANCE",
        "generated_at_utc": now_utc(),
        "model_id": MODEL_ID,
        "unique_base_language_models": [MODEL_ID],
        "machine_execution_accepted": machine_execution_accepted,
        "scientific_claim_release": "NOT_ASSERTED",
        "hypothesis_supported": False,
        "interpretation": "Acceptance means the frozen machine protocol ran to terminal states and passed independent integrity checks; it does not turn model predictions into proofs.",
        "real_provider_calls": manifest.get("real_provider_calls"),
        "local_usage_cost_usd": manifest.get("local_usage_cost_usd"),
        "planned_units": summary.get("ledger_units"),
        "ledger_status_counts": summary.get("ledger_status_counts"),
        "independent_audit_pass": audit.get("audit_pass"),
        "test_exit_code": test_result.get("exit_code"),
        "historical_denominators_unchanged": manifest.get("historical_denominators_unchanged"),
        "private_truth_injected": manifest.get("private_truth_injected"),
        "g6": scores.get("g6"),
        "q": scores.get("q"),
        "g7": scores.get("g7"),
        "lu": scores.get("lu"),
        "agent": scores.get("agent"),
        "alternate_math_verification": alternate,
        "run_root": str(run_root),
        "audit_root": str(audit_root),
    }
    write_json(audit_root / "MACHINE_ACCEPTANCE.json", acceptance)
    source_files = {}
    for path in [repo / "scripts" / "v10" / "machine_truth.py", repo / "scripts" / "v10" / "run_single_kimi_autonomous.py", repo / "scripts" / "v10" / "independent_audit.py", repo / "scripts" / "v10" / "alternate_math_audit.py", repo / "scripts" / "v10" / "finalize_v10.py"]:
        if path.exists():
            source_files[str(path.relative_to(repo)).replace("\\", "/")] = sha256_file(path)
    write_json(audit_root / "SOURCE_AND_ARTIFACT_SHA256.json", {"generated_at_utc": now_utc(), "source_files": source_files, "audit_artifacts": _hash_files(audit_root, {"SOURCE_AND_ARTIFACT_SHA256.json"})})
    final_text = "\n".join([
        "# V10 Machine Result",
        "",
        f"- Machine execution accepted: `{str(machine_execution_accepted).upper()}`",
        f"- Base model: `{MODEL_ID}` only",
        f"- Real provider calls: `{manifest.get('real_provider_calls')}`",
        f"- Local usage cost (provider ledger): `${float(manifest.get('local_usage_cost_usd') or 0.0):.6f}`",
        f"- Planned units: `{summary.get('ledger_units')}`; statuses: `{json.dumps(summary.get('ledger_status_counts'), ensure_ascii=False, sort_keys=True)}`",
        "",
        "## Scientific outcomes",
        "",
        f"- Alternate exact math diagnostic (primary frozen truth unchanged): `{json.dumps(alternate, ensure_ascii=False, sort_keys=True) if alternate else 'not_run'}`",
        f"- G6: `{json.dumps(scores.get('g6'), ensure_ascii=False, sort_keys=True)}`",
        f"- Q: `{json.dumps(scores.get('q'), ensure_ascii=False, sort_keys=True)}`",
        f"- G7: `{json.dumps(scores.get('g7'), ensure_ascii=False, sort_keys=True)}`",
        f"- LU/U: `{json.dumps(scores.get('lu'), ensure_ascii=False, sort_keys=True)}`",
        f"- Agent comparison: `{json.dumps(scores.get('agent'), ensure_ascii=False, sort_keys=True)}`",
        "",
        "No positive scientific claim is inferred from execution acceptance. Model errors and explicit failures remain in the raw append-only logs.",
        "",
        f"Independent audit: `{audit_root / 'INDEPENDENT_READ_ONLY_AUDIT.json'}`",
        f"Machine acceptance: `{audit_root / 'MACHINE_ACCEPTANCE.json'}`",
        f"Raw traces: `{run_root / 'logs/provider_traces.jsonl'}`",
    ]) + "\n"
    (audit_root / "FINAL_RESULT_ONLY.md").write_text(final_text, encoding="utf-8")
    return acceptance


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--audit-root", type=Path, required=True)
    parser.add_argument("--test-exit-code", type=int, default=None)
    args = parser.parse_args()
    result = finalize(args.repo.resolve(), args.run_root.resolve(), args.audit_root.resolve(), args.test_exit_code)
    print(json.dumps({"machine_execution_accepted": result["machine_execution_accepted"], "real_provider_calls": result["real_provider_calls"]}, ensure_ascii=False, indent=2))
    return 0 if result["machine_execution_accepted"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
