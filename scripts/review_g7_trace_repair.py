"""Independent read-only checks for the G7 trace-repair artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.audit_g7_trace_q_consistency import _trace_path, readl, validate_lifecycle


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    run_root = Path("runs/ctflow_single_model/20261017T-g7-kimi-k25-v1")
    audit_root = run_root / "g7_audit"
    view_root = audit_root / "g7_trace_view_20261018"
    manifest = readl(view_root / "trace_selection_manifest.jsonl")
    source = Path("scripts/run_g7_failure_localization.py").read_text(encoding="utf-8")
    raw_hash_mismatches: list[str] = []
    raw_derived_aliases: list[str] = []
    accepted_recheck_failures: list[str] = []
    for entry in manifest:
        raw_path, path_error = _trace_path(run_root, entry.get("raw_trace_ref"))
        if entry.get("raw_trace_sha256") and raw_path and raw_path.is_file():
            if sha256(raw_path) != entry["raw_trace_sha256"]:
                raw_hash_mismatches.append(str(entry.get("record_id")))
        derived_path, derived_error = _trace_path(view_root, entry.get("derived_trace_ref"))
        if raw_path and derived_path and raw_path.resolve() == derived_path.resolve():
            raw_derived_aliases.append(str(entry.get("record_id")))
        if entry.get("accepted"):
            if derived_error or derived_path is None or not derived_path.is_file():
                accepted_recheck_failures.append(str(entry.get("record_id")))
                continue
            events = [json.loads(line) for line in derived_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            record_id = str(entry.get("record_id"))
            expected = {record_id}
            if entry.get("record_kind") == "checkpoint":
                expected.add(f"checkpoint_{record_id}")
            if validate_lifecycle(events, expected):
                accepted_recheck_failures.append(record_id)

    review: dict[str, Any] = {
        "review_version": "g7-trace-repair-independent-read-only-v1",
        "raw_trace_hash_mismatches": raw_hash_mismatches,
        "raw_derived_path_aliases": raw_derived_aliases,
        "accepted_derived_trace_recheck_failures": accepted_recheck_failures,
        "raw_traces_modified": not raw_hash_mismatches and not raw_derived_aliases,
        "source_fix_contract_present": all(marker in source for marker in (
            "if not path.is_file() or path.stat().st_size == 0",
            "if not retry_path.exists():",
        )),
        "manifest_rows": len(manifest),
        "accepted_rows": sum(bool(row.get("accepted")) for row in manifest),
        "review_scope": "read-only hash/path/lifecycle recheck; no provider call; no scientific truth decision",
    }
    output = Path("docs/audits/cycle-20261018T-g7-trace-repair/REPAIR_INDEPENDENT_REVIEW.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(review, ensure_ascii=False))
    return 0 if all((
        review["raw_traces_modified"],
        review["source_fix_contract_present"],
        not review["accepted_derived_trace_recheck_failures"],
    )) else 1


if __name__ == "__main__":
    raise SystemExit(main())
