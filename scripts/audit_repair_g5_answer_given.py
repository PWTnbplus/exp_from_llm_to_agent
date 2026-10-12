#!/usr/bin/env python3
"""Strict, non-destructive G5 compliance audit and format recovery.

The raw G5 run is never edited.  This script writes a separate
``strict_compliance`` layer containing only normalized final packages and
auditable references back to the raw attempt.  A repair is allowed only when
the observable raw response already contains the required information (for
example, extracting a fenced JSON object or adding the known task id).  It
never reads the private answer key and never invents a claim, result, or
evidence item.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any


EVENT_TYPES = {
    "RUN_START", "MODEL_REQUEST", "MODEL_RESPONSE", "MODEL_ERROR", "MODEL_RETRY",
    "TOOL_CALL", "TOOL_RESULT", "TOOL_ERROR", "STEP_START", "STEP_END",
    "CLAIM_UPDATE", "PREDICTION", "EVALUATION", "CHECKPOINT", "ERROR",
    "POLICY_VIOLATION", "RUN_END",
}
ALLOWED_TOOLS = {"safe_sympy", "safe_scipy", "sandbox_python"}
REQUIRED_ATTEMPT_FILES = {"manifest.json", "checkpoint.json", "proof_graph.json", "stderr.log", "events.jsonl", "steps.jsonl"}
SECRET_RE = re.compile(r"(?i)\b(?:sk-[A-Za-z0-9_-]{12,}|Bearer\s+[A-Za-z0-9._~+/=-]{12,})")
PRIVATE_KEY_RE = re.compile(r'(?i)"(?:ground_truth|answer_key|verification_code|verification_status)"\s*:')


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def extract_json_object(text: str) -> dict[str, Any] | None:
    """Recover the first balanced JSON object without executing model text."""
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?\s*", "", candidate, flags=re.I)
        candidate = re.sub(r"\s*```$", "", candidate)
    try:
        value = json.loads(candidate)
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        pass
    start = candidate.find("{")
    while start >= 0:
        depth = 0
        in_string = False
        escaped = False
        for index in range(start, len(candidate)):
            char = candidate[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    try:
                        value = json.loads(candidate[start:index + 1])
                    except json.JSONDecodeError:
                        value = None
                    if isinstance(value, dict):
                        return value
                    break
        start = candidate.find("{", start + 1)
    return None


def validate_final_package(task_id: str, payload: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["final package is not an object"]
    if payload.get("task_id") != task_id:
        errors.append("task_id must be present and equal to the public task id")
    if payload.get("final_assessment") not in {"SUPPORTED", "REFUTED", "UNPROVEN"}:
        errors.append("final_assessment must be SUPPORTED, REFUTED, or UNPROVEN")
    claims = payload.get("claims")
    if not isinstance(claims, list):
        errors.append("claims must be a list")
    else:
        for index, claim in enumerate(claims):
            if not isinstance(claim, dict):
                errors.append(f"claim {index} is not an object")
                continue
            for field in ("claim_id", "statement", "status", "evidence_refs"):
                if field not in claim:
                    errors.append(f"claim {index} missing {field}")
            if not isinstance(claim.get("claim_id"), str) or not claim.get("claim_id", "").strip():
                errors.append(f"claim {index} claim_id must be a non-empty string")
            if not isinstance(claim.get("statement"), str) or not claim.get("statement", "").strip():
                errors.append(f"claim {index} statement must be a non-empty string")
            if claim.get("status") not in {"proposed", "supported", "refuted", "unresolved"}:
                errors.append(f"claim {index} has invalid status")
            refs = claim.get("evidence_refs")
            if not isinstance(refs, list) or any(not isinstance(ref, str) or not ref.strip() for ref in (refs or [])):
                errors.append(f"claim {index} evidence_refs must be a list of non-empty strings")
    for field in ("backward_derivation", "forward_check", "answer_dependency_assessment"):
        if not isinstance(payload.get(field), str) or not payload[field].strip():
            errors.append(f"missing {field}")
    if not isinstance(payload.get("unresolved_steps"), list) or any(not isinstance(x, str) for x in payload.get("unresolved_steps", [])):
        errors.append("unresolved_steps must be a list of strings")
    return errors


def normalized_package(task_id: str, candidate: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    """Keep only the published G5 fields; return errors rather than guessing."""
    package = {
        "task_id": candidate.get("task_id"),
        "final_assessment": candidate.get("final_assessment"),
        "claims": candidate.get("claims"),
        "backward_derivation": candidate.get("backward_derivation"),
        "forward_check": candidate.get("forward_check"),
        "answer_dependency_assessment": candidate.get("answer_dependency_assessment"),
        "unresolved_steps": candidate.get("unresolved_steps"),
    }
    errors = validate_final_package(task_id, package)
    if errors:
        return None, errors
    return package, []


def load_events(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    errors: list[str] = []
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return [], ["missing events.jsonl"]
    for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        try:
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError("event is not an object")
            rows.append(value)
        except (ValueError, json.JSONDecodeError) as exc:
            errors.append(f"event line {number}: invalid JSON: {exc}")
    seqs = [row.get("seq") for row in rows]
    if seqs != list(range(1, len(rows) + 1)):
        errors.append("event sequence is not contiguous from 1")
    if rows and rows[0].get("event_type") != "RUN_START":
        errors.append("first event is not RUN_START")
    if rows and rows[-1].get("event_type") != "RUN_END":
        errors.append("last event is not RUN_END")
    model_requests: Counter[str] = Counter()
    model_closures: Counter[str] = Counter()
    tool_requests: Counter[str] = Counter()
    tool_closures: Counter[str] = Counter()
    for row in rows:
        event_type = row.get("event_type")
        if event_type not in EVENT_TYPES:
            errors.append(f"unknown event type: {event_type}")
        serialized = json_text(row)
        if SECRET_RE.search(serialized):
            errors.append(f"possible credential at event seq {row.get('seq')}")
        if PRIVATE_KEY_RE.search(serialized):
            errors.append(f"private answer-key field at event seq {row.get('seq')}")
        payload = row.get("payload") or {}
        if event_type == "MODEL_REQUEST":
            model_requests[str(row.get("span_id"))] += 1
            if not isinstance(payload.get("messages"), list):
                errors.append(f"MODEL_REQUEST seq {row.get('seq')} has no messages list")
        elif event_type in {"MODEL_RESPONSE", "MODEL_ERROR"}:
            parent = row.get("parent_span_id") or str(row.get("span_id", "")).rsplit(":", 1)[0]
            model_closures[str(parent)] += 1
        elif event_type == "TOOL_CALL":
            tool_requests[str(row.get("span_id"))] += 1
            tool_name = str(payload.get("tool_name", ""))
            if tool_name not in ALLOWED_TOOLS:
                errors.append(f"unauthorized tool {tool_name!r} at event seq {row.get('seq')}")
        elif event_type in {"TOOL_RESULT", "TOOL_ERROR"}:
            parent = row.get("parent_span_id") or str(row.get("span_id", "")).rsplit(":", 1)[0]
            tool_closures[str(parent)] += 1
    for span, count in model_requests.items():
        if count != 1 or model_closures[span] != 1:
            errors.append(f"model span {span}: request={count}, closure={model_closures[span]}")
    for span, count in tool_requests.items():
        if count != 1 or tool_closures[span] != 1:
            errors.append(f"tool span {span}: request={count}, closure={tool_closures[span]}")
    return rows, errors


def check_steps(path: Path) -> list[str]:
    if not path.is_file():
        return ["missing steps.jsonl"]
    errors: list[str] = []
    previous = 0
    for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"steps line {number}: invalid JSON: {exc}")
            continue
        if not isinstance(row, dict) or row.get("event_type") not in {"STEP_START", "STEP_END"}:
            errors.append(f"steps line {number}: invalid step event")
            continue
        seq = int(row.get("seq", 0) or 0)
        if seq <= previous:
            errors.append(f"steps line {number}: sequence is not increasing")
        previous = seq
    return errors


def candidate_sources(summary: dict[str, Any], events: list[dict[str, Any]]) -> list[tuple[str, int | None, Any]]:
    sources: list[tuple[str, int | None, Any]] = []
    if isinstance(summary.get("final_package"), dict):
        sources.append(("canonical_summary.final_package", None, summary["final_package"]))
    for event in reversed(events):
        payload = event.get("payload") or {}
        if event.get("event_type") == "PREDICTION" and isinstance(payload.get("final_package"), dict):
            sources.append(("PREDICTION.final_package", event.get("seq"), payload["final_package"]))
        if event.get("event_type") == "MODEL_RESPONSE":
            response = payload.get("response") or {}
            content = response.get("content") if isinstance(response, dict) else None
            if isinstance(content, str):
                parsed = extract_json_object(content)
                if parsed is not None:
                    sources.append(("MODEL_RESPONSE.extracted_json", event.get("seq"), parsed))
    return sources


def audit_attempt(attempt_dir: Path, task_id: str, summary: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    for filename in sorted(REQUIRED_ATTEMPT_FILES):
        if not (attempt_dir / filename).is_file():
            errors.append(f"missing {filename}")
    events, event_errors = load_events(attempt_dir / "events.jsonl")
    errors.extend(event_errors)
    errors.extend(check_steps(attempt_dir / "steps.jsonl"))
    attempt_manifest = {}
    try:
        attempt_manifest = load_json(attempt_dir / "manifest.json")
    except (OSError, UnicodeError, json.JSONDecodeError):
        errors.append("invalid attempt manifest")
    if isinstance(attempt_manifest, dict):
        if attempt_manifest.get("no_private_answer_access") is not True:
            errors.append("attempt no_private_answer_access is not true")
        if attempt_manifest.get("answer_exposure") != "given_to_g5_only":
            errors.append("attempt answer exposure mismatch")
        if attempt_manifest.get("web_access") is not False or attempt_manifest.get("cross_task_memory") is not False:
            errors.append("web access or cross-task memory is not disabled")
    model_calls = sum(row.get("event_type") == "MODEL_REQUEST" for row in events)
    tool_calls = sum(row.get("event_type") == "TOOL_CALL" for row in events)
    if model_calls > 8:
        errors.append(f"model call budget exceeded: {model_calls}")
    if tool_calls > 6:
        errors.append(f"tool call budget exceeded: {tool_calls}")
    if int(summary.get("total_tokens", 0) or 0) > 8000:
        errors.append("total token budget exceeded")
    if float(summary.get("elapsed_seconds", 0.0) or 0.0) > 300:
        errors.append("wall-time budget exceeded")
    return {"errors": errors, "events": events, "model_calls": model_calls, "tool_calls": tool_calls}


def normalize_candidate(task_id: str, candidate: Any) -> tuple[dict[str, Any] | None, list[str], list[str]]:
    """Apply only observable, schema-level repairs to one candidate package."""
    if not isinstance(candidate, dict):
        return None, ["candidate is not an object"], []
    candidate_copy = dict(candidate)
    actions: list[str] = []
    if candidate_copy.get("task_id") is None:
        candidate_copy["task_id"] = task_id
        actions.append("added_missing_task_id_from_task_directory")
    # These aliases preserve the meaning of an explicitly non-conclusive
    # submission; they do not add claims or change statements/evidence.
    final_aliases = {
        "PARTIALLY_SUPPORTED": "UNPROVEN",
        "PARTIALLY_REFUTED": "UNPROVEN",
    }
    if candidate_copy.get("final_assessment") in final_aliases:
        candidate_copy["final_assessment"] = final_aliases[candidate_copy["final_assessment"]]
        actions.append("normalized_final_assessment_enum")
    claim_aliases = {
        "supported_answer": "supported",
        "refuted_answer": "refuted",
        "proposed_answer": "proposed",
        "partially_supported": "unresolved",
        "partially_refuted": "unresolved",
    }
    claims = candidate_copy.get("claims")
    if isinstance(claims, list):
        normalized_claims = []
        for claim in claims:
            if isinstance(claim, dict) and claim.get("status") in claim_aliases:
                claim = dict(claim)
                claim["status"] = claim_aliases[claim["status"]]
                actions.append("normalized_claim_status_enum")
            normalized_claims.append(claim)
        candidate_copy["claims"] = normalized_claims
    normalized, errors = normalized_package(task_id, candidate_copy)
    return normalized, errors, actions


def attempt_number(path: Path) -> int:
    match = re.fullmatch(r"attempt-(\d+)", path.name)
    return int(match.group(1)) if match else -1


def find_package_across_attempts(task_dir: Path, task_id: str) -> dict[str, Any]:
    """Audit every persisted attempt and select the newest valid package.

    A resumed run can finish with a provider error after an earlier attempt
    already produced a valid final package.  Reusing that package is a local
    recovery, not a new model call.  The current attempt remains the raw
    status, and every inspected attempt is retained as lineage evidence.
    """
    attempts_root = task_dir / "attempts"
    attempt_dirs = sorted(
        (path for path in attempts_root.glob("attempt-*") if path.is_dir()),
        key=attempt_number,
        reverse=True,
    )
    lineage: list[dict[str, Any]] = []
    for attempt_dir in attempt_dirs:
        summary_path = attempt_dir / "summary.json"
        if not summary_path.is_file():
            lineage.append({
                "attempt": attempt_number(attempt_dir),
                "status": "MISSING_SUMMARY",
                "valid_candidates": 0,
                "errors": ["missing summary.json"],
            })
            continue
        try:
            summary = load_json(summary_path)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            lineage.append({
                "attempt": attempt_number(attempt_dir),
                "status": "INVALID_SUMMARY",
                "valid_candidates": 0,
                "errors": [str(exc)],
            })
            continue
        audit = audit_attempt(attempt_dir, task_id, summary)
        sources = candidate_sources(summary, audit["events"])
        package_errors: list[str] = []
        valid_candidates = 0
        for name, seq, candidate in sources:
            package, errors, actions = normalize_candidate(task_id, candidate)
            if package is not None:
                valid_candidates += 1
                lineage.append({
                    "attempt": attempt_number(attempt_dir),
                    "status": str(summary.get("status")),
                    "event_count": len(audit["events"]),
                    "event_errors": audit["errors"],
                    "valid_candidates": valid_candidates,
                    "selected": True,
                    "source_package": name,
                    "source_event_seq": seq,
                    "model_calls": audit["model_calls"],
                    "tool_calls": audit["tool_calls"],
                })
                return {
                    "package": package,
                    "source_name": name,
                    "source_seq": seq,
                    "repair_actions": actions,
                    "source_attempt": attempt_dir,
                    "source_summary": summary,
                    "source_audit": audit,
                    "lineage": lineage,
                }
            package_errors = errors
        lineage.append({
            "attempt": attempt_number(attempt_dir),
            "status": str(summary.get("status")),
            "event_count": len(audit["events"]),
            "event_errors": audit["errors"],
            "package_errors": package_errors,
            "valid_candidates": valid_candidates,
            "selected": False,
            "model_calls": audit["model_calls"],
            "tool_calls": audit["tool_calls"],
        })
    return {"package": None, "lineage": lineage}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, default=Path("data/theory_benchmark_v2"))
    parser.add_argument("--skill-zip", type=Path, required=True)
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    data_dir = args.data_dir.resolve()
    compliance_dir = run_dir / "strict_compliance"
    tasks_dir = compliance_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    manifest = load_json(run_dir / "manifest.json")
    public = load_json(data_dir / "public_tasks.json")
    expected_task_ids = [str(row["task_id"]) for row in public[: int(manifest.get("tasks", len(public)))] if isinstance(row, dict)]
    model_rows = manifest.get("models") or []
    model_ids = [str(row.get("model_id")) if isinstance(row, dict) else str(row) for row in model_rows]
    counts: Counter[str] = Counter()
    records: list[dict[str, Any]] = []
    orphan_interrupted_attempts: list[str] = []
    for model_id in model_ids:
        for task_id in expected_task_ids:
            task_dir = run_dir / "models" / model_id / "tasks" / task_id
            summary_path = task_dir / "summary.json"
            record: dict[str, Any] = {"model_id": model_id, "task_id": task_id, "source_task_dir": str(task_dir), "raw_sha256": None}
            if not summary_path.is_file():
                record.update({"compliance_status": "MISSING_SUMMARY", "errors": ["canonical summary is missing"]})
                counts[record["compliance_status"]] += 1
                records.append(record)
                write_json(tasks_dir / model_id / f"{task_id}.json", record)
                continue
            record["raw_sha256"] = sha256_file(summary_path)
            try:
                summary = load_json(summary_path)
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                record.update({"compliance_status": "INVALID_SUMMARY", "errors": [str(exc)]})
                counts[record["compliance_status"]] += 1
                records.append(record)
                write_json(tasks_dir / model_id / f"{task_id}.json", record)
                continue
            attempt = int(summary.get("attempt", 0) or 0)
            attempt_dir = task_dir / "attempts" / f"attempt-{attempt:03d}"
            for orphan_dir in sorted((task_dir / "attempts").glob("attempt-*")):
                if orphan_dir != attempt_dir and not (orphan_dir / "summary.json").is_file():
                    orphan_interrupted_attempts.append(str(orphan_dir))
            selection = find_package_across_attempts(task_dir, task_id)
            package = selection.get("package")
            source_name = selection.get("source_name")
            source_seq = selection.get("source_seq")
            package_errors: list[str] = []
            source_attempt = selection.get("source_attempt")
            source_audit = selection.get("source_audit")
            repair_actions = list(selection.get("repair_actions") or [])
            lineage = selection.get("lineage") or []
            # The current attempt is the authoritative raw status.  Reuse of
            # a prior valid attempt is explicitly marked as recovery and never
            # relabelled as a successful current provider call.
            audit = audit_attempt(attempt_dir, task_id, summary)
            raw_status = str(summary.get("status"))
            record.update({
                "raw_status": raw_status,
                "attempt": attempt,
                "source_attempt": str(attempt_dir),
                "selected_attempt": str(source_attempt) if source_attempt else None,
                "attempt_lineage": lineage,
                "event_count": len(audit["events"]),
                "event_errors": audit["errors"],
                "package_errors": package_errors,
                "model_calls": audit["model_calls"],
                "tool_calls": audit["tool_calls"],
            })
            if package is not None:
                recovered_prior = source_attempt is not None and source_attempt != attempt_dir
                repaired = recovered_prior or source_name != "canonical_summary.final_package" or summary.get("final_package", {}).get("task_id") is None
                if recovered_prior:
                    repair_actions.append("reused_valid_final_package_from_prior_attempt")
                record.update({
                    "compliance_status": "RECOVERED_PRIOR_ATTEMPT" if recovered_prior else ("REPAIRED_FORMAT" if repaired else ("COMPLIANT" if not audit["errors"] else "PACKAGE_VALID_TRACE_NONCOMPLIANT")),
                    "source_package": source_name,
                    "source_event_seq": source_seq,
                    "source_attempt_audit_errors": (source_audit or {}).get("errors", []),
                    "final_package": package,
                    "repair_actions": repair_actions + (["extracted_json_from_observable_model_response"] if source_name and "extracted_json" in source_name else []),
                })
            elif raw_status == "PROVIDER_ERROR":
                record.update({"compliance_status": "NO_SUBMISSION_PROVIDER_ERROR", "errors": ["provider error has no recoverable final package"]})
            elif raw_status == "TIMEOUT":
                record.update({"compliance_status": "NO_SUBMISSION_TIMEOUT", "errors": ["timeout has no recoverable final package"]})
            else:
                record.update({"compliance_status": "NONCOMPLIANT_UNREPAIRED", "errors": package_errors or ["no valid observable final package"]})
            if package is None:
                # Keep the analysis table schema complete without fabricating
                # a scientific answer.  This explicit UNPROVEN package is a
                # derived audit placeholder; raw status, events, and errors
                # remain unchanged and are retained in the same record.
                fallback = {
                    "task_id": task_id,
                    "final_assessment": "UNPROVEN",
                    "claims": [],
                    "backward_derivation": "No complete G5 final package was submitted; see the preserved raw trace.",
                    "forward_check": "No scientific conclusion was scored because the observable submission was incomplete or unavailable.",
                    "answer_dependency_assessment": "Unassessed: no valid final package was available for independent evaluation.",
                    "unresolved_steps": ["No valid observable final package was submitted."],
                }
                if raw_status == "PROVIDER_ERROR":
                    fallback_status = "UNPROVEN_NO_SUBMISSION_PROVIDER_ERROR"
                elif raw_status == "TIMEOUT":
                    fallback_status = "UNPROVEN_NO_SUBMISSION_TIMEOUT"
                else:
                    fallback_status = "UNPROVEN_INVALID_SUBMISSION"
                record.update({
                    "compliance_status": fallback_status,
                    "source_package": "strict_audit_unproven_fallback",
                    "source_event_seq": None,
                    "final_package": fallback,
                    "repair_actions": ["created_non_conclusive_unproven_fallback"],
                })
            counts[record["compliance_status"]] += 1
            records.append(record)
            write_json(tasks_dir / model_id / f"{task_id}.json", record)
    skill_record = {
        "path": str(args.skill_zip.resolve()),
        "sha256": sha256_file(args.skill_zip.resolve()),
        "exists": args.skill_zip.is_file(),
    }
    schema_valid_statuses = (
        "COMPLIANT", "REPAIRED_FORMAT", "RECOVERED_PRIOR_ATTEMPT", "PACKAGE_VALID_TRACE_NONCOMPLIANT",
        "UNPROVEN_NO_SUBMISSION_PROVIDER_ERROR", "UNPROVEN_NO_SUBMISSION_TIMEOUT",
        "UNPROVEN_INVALID_SUBMISSION",
    )
    substantive_statuses = (
        "COMPLIANT", "REPAIRED_FORMAT", "RECOVERED_PRIOR_ATTEMPT", "PACKAGE_VALID_TRACE_NONCOMPLIANT",
    )
    raw_provider_errors = sum(1 for row in records if row.get("raw_status") == "PROVIDER_ERROR")
    raw_timeouts = sum(1 for row in records if row.get("raw_status") == "TIMEOUT")
    report = {
        "generated_at_utc": utc_now(),
        "run_dir": str(run_dir),
        "mode": manifest.get("mode"),
        "group": manifest.get("group"),
        "private_answer_key_read": False,
        "source_raw_unchanged": True,
        "skill_provenance": skill_record,
        "expected_records": len(model_ids) * len(expected_task_ids),
        "observed_records": len(records),
        "status_counts": dict(counts),
        "strict_package_records": sum(counts[k] for k in schema_valid_statuses),
        "substantive_package_records": sum(counts[k] for k in substantive_statuses),
        "fully_compliant_records": counts["COMPLIANT"],
        "repaired_format_records": counts["REPAIRED_FORMAT"],
        "recovered_prior_attempt_records": counts["RECOVERED_PRIOR_ATTEMPT"],
        "unrepaired_records": sum(counts[k] for k in ("NONCOMPLIANT_UNREPAIRED", "MISSING_SUMMARY", "INVALID_SUMMARY")),
        "provider_error_records": raw_provider_errors,
        "no_submission_provider_error_records": counts["NO_SUBMISSION_PROVIDER_ERROR"] + counts["UNPROVEN_NO_SUBMISSION_PROVIDER_ERROR"],
        "timeout_records": raw_timeouts,
        "no_submission_timeout_records": counts["NO_SUBMISSION_TIMEOUT"] + counts["UNPROVEN_NO_SUBMISSION_TIMEOUT"],
        "unproven_fallback_records": sum(counts[k] for k in schema_valid_statuses if k.startswith("UNPROVEN_")),
        "trace_noncompliant_records": counts["PACKAGE_VALID_TRACE_NONCOMPLIANT"],
        "orphan_interrupted_attempt_count": len(orphan_interrupted_attempts),
        "orphan_interrupted_attempts": orphan_interrupted_attempts[:200],
        "raw_records_not_modified": True,
    }
    write_json(compliance_dir / "manifest.json", {"type": "g5_strict_compliance_layer", "run_dir": str(run_dir), "created_at_utc": utc_now(), "private_answer_key_read": False, "skill_provenance": skill_record})
    write_json(compliance_dir / "report.json", report)
    repair_statuses = {"REPAIRED_FORMAT", "RECOVERED_PRIOR_ATTEMPT"}
    (compliance_dir / "repairs.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records if row.get("compliance_status") in repair_statuses), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["expected_records"] == report["observed_records"] and report["unrepaired_records"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
