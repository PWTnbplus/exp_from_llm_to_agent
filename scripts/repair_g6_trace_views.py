"""Derive auditable final-success trace views without modifying raw traces."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def split_attempts(events: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    attempts: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for event in events:
        if event.get("event_type") == "RUN_START" and current:
            attempts.append(current)
            current = []
        current.append(event)
    if current:
        attempts.append(current)
    return attempts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--responses", type=Path, required=True)
    parser.add_argument("--trace-root", type=Path, required=True)
    parser.add_argument("--responses-out", type=Path, required=True)
    parser.add_argument("--manifest-out", type=Path, required=True)
    args = parser.parse_args()

    responses = read_jsonl(args.responses)
    audited_root = args.out / "traces_audited"
    selected: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    failures: list[str] = []
    raw_nonmonotonic = 0
    for response in responses:
        run_id = response["run_id"]
        raw_path = args.trace_root / response["trace_ref"]
        events = read_jsonl(raw_path)
        raw_seqs = [event.get("seq") for event in events]
        raw_ok = raw_seqs == list(range(1, len(events) + 1))
        if not raw_ok:
            raw_nonmonotonic += 1
        attempts = split_attempts(events)
        successful = [attempt for attempt in attempts if attempt and attempt[-1].get("event_type") == "RUN_END" and (attempt[-1].get("payload") or {}).get("status") == "completed"]
        if not successful:
            failures.append(run_id)
            continue
        final_attempt = successful[-1]
        audited_events: list[dict[str, Any]] = []
        for seq, event in enumerate(final_attempt, 1):
            audited_event = dict(event)
            audited_event["seq"] = seq
            audited_events.append(audited_event)
        audited_path = audited_root / run_id / "events.jsonl"
        write_jsonl(audited_path, audited_events)
        audited_response = dict(response)
        audited_response["trace_ref"] = str(audited_path.relative_to(args.out))
        selected.append(audited_response)
        records.append({"run_id": run_id, "raw_trace_ref": response["trace_ref"], "audited_trace_ref": audited_response["trace_ref"], "raw_seq_monotonic": raw_ok, "raw_event_count": len(events), "audited_event_count": len(audited_events), "successful_attempt_count": len(successful)})

    write_jsonl(args.responses_out, selected)
    manifest = {"experiment_id": "g6_counterfactual", "source_responses_sha256": sha256(args.responses), "audited_response_count": len(selected), "raw_nonmonotonic_trace_count": raw_nonmonotonic, "failed_to_extract_successful_attempt": failures, "selection_rule": "last RUN_START-to-RUN_END segment with COMPLETED status; raw traces remain unchanged", "records": records}
    args.manifest_out.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in manifest.items() if k != "records"}, ensure_ascii=False))
    return 0 if not failures and len(selected) == len(responses) else 2


if __name__ == "__main__":
    raise SystemExit(main())
