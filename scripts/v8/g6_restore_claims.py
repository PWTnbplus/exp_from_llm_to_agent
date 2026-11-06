"""Recover historical G6 public propositions without changing old results.

The V7 adjudication deliberately produced UNKNOWN when its public claim text
was missing.  This script searches immutable historical request traces and
emits an append-only recovery table.  A row remains UNKNOWN when no source
text is found; no text is synthesized from an oracle or from a model answer.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.v8.claim_ir import parse_claim_text


def _sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _message_text(message: Any) -> str:
    if isinstance(message, dict):
        content = message.get("content", "")
        if isinstance(content, str):
            return content
        return json.dumps(content, ensure_ascii=False)
    return str(message)


def _collect_trace_cases(runs_root: Path) -> dict[str, list[dict[str, Any]]]:
    found: dict[str, list[dict[str, Any]]] = {}
    for path in sorted(runs_root.glob("*/**/events.jsonl")):
        if "g6" not in path.as_posix().lower():
            continue
        case_id = None
        arm_id = None
        request_text = None
        response_text = None
        response_event = None
        request_event = None
        try:
            events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        except (OSError, json.JSONDecodeError):
            continue
        for event in events:
            payload = event.get("payload") or {}
            if event.get("event_type") == "RUN_START":
                case_id = payload.get("case_id")
                arm_id = payload.get("arm_id")
            elif event.get("event_type") == "MODEL_REQUEST":
                messages = payload.get("messages") or []
                for message in messages:
                    text = _message_text(message)
                    if '"g6_case"' in text or '"case_id"' in text:
                        request_text = text
                        request_event = event
                        break
            elif event.get("event_type") == "MODEL_RESPONSE":
                content = payload.get("content")
                if content:
                    response_text = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
                    response_event = event
        if not case_id or not request_text:
            continue
        try:
            decoded = json.loads(request_text)
            public_case = decoded.get("g6_case") if isinstance(decoded, dict) else None
        except json.JSONDecodeError:
            public_case = None
        if not isinstance(public_case, dict):
            continue
        cid = public_case.get("case_id") or case_id
        candidate = {
            "trace_path": str(path),
            "trace_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "case_id": cid,
            "run_start_case_id": case_id,
            "arm_id": arm_id,
            "public_case": public_case,
            "original_response_excerpt": (response_text or "")[:4000],
            "request_event_seq": request_event.get("seq") if request_event else None,
            "response_event_seq": response_event.get("seq") if response_event else None,
        }
        found.setdefault(cid, []).append(candidate)
    return found


def recover(v7_units: Path, runs_root: Path, output: Path, summary: Path) -> None:
    units = [json.loads(line) for line in v7_units.read_text(encoding="utf-8").splitlines() if line.strip()]
    cases = _collect_trace_cases(runs_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        for unit in units:
            case_id = unit.get("case_id")
            candidates = cases.get(case_id, [])
            selected = candidates[0] if candidates else None
            public_case = selected.get("public_case") if selected else None
            original_problem = public_case.get("original_problem") if public_case else None
            original_claim = public_case.get("original_claim") if public_case else None
            intervention = public_case.get("intervention_statement") if public_case else None
            claim_ir, parse_reason = parse_claim_text(original_claim)
            if selected is None:
                recovery_status = "UNKNOWN"
                reason = "MISSING_HISTORICAL_PUBLIC_TRACE"
            elif not original_claim:
                recovery_status = "UNKNOWN"
                reason = "TRACE_FOUND_BUT_PUBLIC_CLAIM_MISSING"
            elif claim_ir is None:
                recovery_status = "SOURCE_RECOVERED_UNPARSEABLE"
                reason = parse_reason
            else:
                recovery_status = "RECOVERED_CLAIM_IR"
                reason = "RECOVERED"
            row = {
                "unit_index": unit.get("unit_index"),
                "attempt_id": unit.get("attempt_id"),
                "case_id": case_id,
                "cf_type": unit.get("cf_type"),
                "historical_source_row_sha256": unit.get("source_row_sha256"),
                "join_key": {"case_id": case_id, "attempt_id": unit.get("attempt_id")},
                "join_status": "CASE_ID_ONLY_NO_ATTEMPT_IN_TRACE" if selected else "NO_MATCH",
                "trace_provenance": {
                    "trace_path": selected.get("trace_path") if selected else None,
                    "trace_sha256": selected.get("trace_sha256") if selected else None,
                    "run_start_case_id": selected.get("run_start_case_id") if selected else None,
                    "arm_id": selected.get("arm_id") if selected else None,
                    "request_event_seq": selected.get("request_event_seq") if selected else None,
                    "response_event_seq": selected.get("response_event_seq") if selected else None,
                },
                "original_problem": original_problem,
                "original_claim": original_claim,
                "intervention_statement": intervention,
                "recovered_claim_ir": claim_ir.to_dict() if claim_ir else None,
                "recovery_status": recovery_status,
                "recovery_reason": reason,
                "original_response_excerpt": selected.get("original_response_excerpt") if selected else None,
                "truth_key_read": False,
                "source_synthesized": False,
            }
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            counts[recovery_status] = counts.get(recovery_status, 0) + 1
    report = {
        "protocol": "V8_LEGACY_G6_CLAIM_RECOVERY",
        "input_units": str(v7_units),
        "historical_units": len(units),
        "trace_case_count": len(cases),
        "counts": counts,
        "historical_data_modified": False,
        "source_synthesized": False,
        "output_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
    }
    summary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v7-units", type=Path, required=True)
    parser.add_argument("--runs-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()
    recover(args.v7_units, args.runs_root, args.output, args.summary)


if __name__ == "__main__":
    main()

