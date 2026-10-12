#!/usr/bin/env python3
"""Exhaustively audit deterministic recovery of already-persisted outputs.

This is a read-only repair pass.  It scans failed recovery/matrix artifacts,
extracts only JSON objects that are already present in a provider trace (with
the existing balanced-object and trailing-comma parser), and checks them with
the local evaluator.  It never calls a provider, edits a raw result, or emits
the candidate/answer/key in its derived output.

The important distinction is intentional: a failed run whose persisted
response can be verified is reported as ``FAILED_RECOVERED_CORRECT`` or
``FAILED_WITH_PERSISTED_PAYLOAD_EVALUATED_WRONG_NOT_COUNTED``.  Neither case
silently changes the ordinary completed-answer denominator.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.analyze_recovered_final_output import _parse_output
from scripts.audit_recover_failed_matrix_records import error_only
from src.scientific_discovery.theory_benchmark.verification import verify_candidate


RECOVERY_STAGES = (
    "timeout_recovery",
    "format_recovery",
    "format_recovery_retry2",
    "format_recovery_retry3",
    "format_recovery_retry4",
    "provider_recovery_retry1",
    "provider_recovery_retry2",
    "format_recovery_retry5",
    "provider_recovery_retry3",
    "format_recovery_retry6",
    "provider_recovery_retry4",
    "format_recovery_retry7",
    "provider_recovery_retry5",
)
EXCLUDED_STAGES = {"format_recovery_retry8"}
GROUP_MATRIX_STAGES = {"G2", "G3"}
FAILED_STATUS = "FAILED"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_json(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_benchmark_root(path: Path) -> Path:
    """Resolve an ASCII drive-root sentinel for Windows Unicode paths."""
    if (path / "agent").is_dir() and (path / "organized").is_dir():
        # Keep an ASCII junction path un-resolved.  Resolving it would expose
        # the Unicode target to the subprocess code page on affected hosts.
        return path.absolute()
    if path.name == "benchmark" and path.is_dir():
        return path.absolute()
    candidates: list[Path] = []
    if path.is_dir():
        try:
            entries = list(os.scandir(path))
        except OSError:
            entries = []
        for entry in entries:
            if not entry.is_dir(follow_symlinks=False):
                continue
            candidate = Path(entry.path) / "prj1_ai_cal" / "exp" / "exp1_from_llm_to_agent" / "benchmark"
            try:
                if candidate.is_dir():
                    candidates.append(candidate)
            except OSError:
                continue
    if len(candidates) == 1 and candidates[0].is_dir():
        return candidates[0].absolute()
    raise FileNotFoundError(f"could not resolve benchmark root from {path}")


def artifact_stage(path: Path) -> str | None:
    parts = set(path.parts)
    for stage in RECOVERY_STAGES + tuple(EXCLUDED_STAGES):
        if stage in parts:
            return stage
    for group in GROUP_MATRIX_STAGES:
        if group in parts:
            # Only matrix result files are considered; this prevents unrelated
            # G2/G3 audit files from being interpreted as model results.
            try:
                models_index = path.parts.index("models")
            except ValueError:
                continue
            if models_index + 3 == len(path.parts):
                return group
    return None


def iter_artifacts(benchmark_root: Path) -> Iterable[tuple[Path, str, str]]:
    """Yield (artifact, stage, source_kind) without traversing organized data."""
    seen: set[Path] = set()
    for base in (benchmark_root / "agent", benchmark_root / "pure_llm", benchmark_root / "G2", benchmark_root / "G3"):
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.json")):
            if path in seen or not path.is_file():
                continue
            stage = artifact_stage(path)
            if stage is None:
                continue
            # All model result artifacts have models/<model>/<file>.json.
            try:
                models_index = path.parts.index("models")
            except ValueError:
                continue
            if models_index + 3 != len(path.parts):
                continue
            seen.add(path)
            source_kind = "matrix" if stage in GROUP_MATRIX_STAGES else "recovery"
            yield path, stage, source_kind


def run_dir_for(path: Path, source_kind: str) -> Path:
    # Recovery: .../<run>/stage/models/<model>/<result>.json
    # Matrix:   .../<group>/<run>/models/<model>/<result>.json
    return path.parents[3] if source_kind == "recovery" else path.parents[2]


def model_id_for(path: Path, result: dict[str, Any]) -> str:
    value = result.get("model_id")
    return str(value) if value else path.parents[0].name


def task_id_for(path: Path, result: dict[str, Any]) -> str:
    value = result.get("task_id")
    if value:
        return str(value)
    return path.name.split("__", 2)[1] if "__" in path.name else path.stem


def response_candidates(result: dict[str, Any]) -> list[tuple[str, int | None, dict[str, Any]]]:
    candidates: list[tuple[str, int | None, dict[str, Any]]] = []
    answer = result.get("answer")
    if isinstance(answer, dict) and not error_only(answer):
        candidates.append(("stored_answer", None, answer))
    trace = (result.get("metadata") or {}).get("provider_trace")
    if isinstance(trace, list):
        for item_index, item in enumerate(trace):
            if not isinstance(item, dict):
                continue
            response = item.get("response")
            content = response.get("content") if isinstance(response, dict) else None
            for candidate in _parse_output(content):
                candidates.append(("provider_trace", item.get("call_index", item_index), candidate))
    unique: list[tuple[str, int | None, dict[str, Any]]] = []
    seen: set[str] = set()
    for source, call_index, candidate in candidates:
        marker = json.dumps(candidate, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if marker not in seen:
            seen.add(marker)
            unique.append((source, call_index, candidate))
    return unique


def classify_evaluations(evaluations: Iterable[str]) -> str:
    statuses = list(evaluations)
    if "PASS" in statuses:
        return "FAILED_RECOVERED_CORRECT"
    if "MODEL_ERROR" in statuses:
        return "FAILED_WITH_PERSISTED_PAYLOAD_EVALUATED_WRONG_NOT_COUNTED"
    if statuses:
        return "FAILED_PAYLOAD_UNJUDGED"
    return "FAILED_NO_PARSEABLE_PERSISTED_PAYLOAD"


def audit_artifact(path: Path, stage: str, source_kind: str, data_dir: Path) -> dict[str, Any]:
    run_dir = run_dir_for(path, source_kind)
    base: dict[str, Any] = {
        "group": None,
        "run_dir": str(run_dir),
        "model_id": path.parents[0].name,
        "task_id": path.name.split("__", 2)[1] if "__" in path.name else path.stem,
        "stage": stage,
        "source_kind": source_kind,
        "source_path": str(path),
        "source_sha256": sha256_file(path),
        "raw_status": None,
        "candidate_count": 0,
        "candidate_source": None,
        "candidate_call_index": None,
        "candidate_index": None,
        "candidate_sha256": None,
        "independent_evaluations": [],
        "independent_evaluation": None,
        "classification": None,
        "counted_as_wrong": False,
    }
    try:
        value = load_json(path)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        base["classification"] = "FAILED_ARTIFACT_UNREADABLE"
        base["independent_evaluation"] = type(exc).__name__
        return base
    if not isinstance(value, dict):
        base["classification"] = "FAILED_ARTIFACT_NOT_OBJECT"
        return base
    base["group"] = str(value.get("group") or value.get("runner") or ("G2" if stage == "G2" else "G3" if stage == "G3" else "UNKNOWN"))
    base["model_id"] = model_id_for(path, value)
    base["task_id"] = task_id_for(path, value)
    base["raw_status"] = value.get("status")
    if value.get("status") != FAILED_STATUS:
        base["classification"] = "NOT_FAILED_ARTIFACT"
        return base
    candidates = response_candidates(value)
    base["candidate_count"] = len(candidates)
    evaluations: list[str] = []
    for index, (source, call_index, candidate) in enumerate(candidates):
        checked = verify_candidate(base["task_id"], candidate, data_dir=data_dir, redact_errors=True)
        status = str(checked.get("status"))
        evaluations.append(status)
        if status == "PASS":
            base["candidate_source"] = source
            base["candidate_call_index"] = call_index
            base["candidate_index"] = index
            base["candidate_sha256"] = sha256_json(candidate)
            break
    base["independent_evaluations"] = evaluations
    base["independent_evaluation"] = "PASS" if "PASS" in evaluations else ("MODEL_ERROR" if "MODEL_ERROR" in evaluations else (evaluations[0] if evaluations else None))
    base["classification"] = classify_evaluations(evaluations)
    return base


def recovery_key(record: dict[str, Any]) -> tuple[str, str, str, str]:
    return (str(record.get("group")), str(record.get("run_dir")), str(record.get("model_id")), str(record.get("task_id")))


def coverage_key(record: dict[str, Any]) -> tuple[str, str, str]:
    # Run IDs and model/task IDs are ASCII and remain comparable even when a
    # legacy JSON index was generated with a different Windows code page.
    return (Path(str(record.get("run_dir"))).name, str(record.get("model_id")), str(record.get("task_id")))


def canonical_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rank = {
        "FAILED_RECOVERED_CORRECT": 0,
        "FAILED_WITH_PERSISTED_PAYLOAD_EVALUATED_WRONG_NOT_COUNTED": 1,
        "FAILED_PAYLOAD_UNJUDGED": 2,
        "FAILED_NO_PARSEABLE_PERSISTED_PAYLOAD": 3,
        "FAILED_ARTIFACT_UNREADABLE": 4,
        "FAILED_ARTIFACT_NOT_OBJECT": 5,
        "NOT_FAILED_ARTIFACT": 6,
    }
    grouped: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        if record.get("classification") == "NOT_FAILED_ARTIFACT":
            continue
        grouped[recovery_key(record)].append(record)
    selected: list[dict[str, Any]] = []
    for key, values in grouped.items():
        chosen = min(values, key=lambda item: (rank.get(str(item.get("classification")), 99), RECOVERY_STAGES.index(item["stage"]) if item["stage"] in RECOVERY_STAGES else 99, item["source_path"]))
        item = dict(chosen)
        item["duplicate_artifact_count"] = len(values)
        item["duplicate_classifications"] = dict(sorted(Counter(str(value.get("classification")) for value in values).items()))
        selected.append(item)
    return sorted(selected, key=lambda item: recovery_key(item))


def existing_selected_keys(benchmark_root: Path) -> set[tuple[str, str, str]]:
    """Read only derived indexes to identify rows already in the organized view."""
    keys: set[tuple[str, str, str]] = set()
    organized = benchmark_root / "organized"
    for path in sorted((organized / "format_failures").glob("*.jsonl")) if (organized / "format_failures").is_dir() else []:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            if all(row.get(field) is not None for field in ("run_dir", "model_id", "task_id")):
                group = str(row.get("group") or row.get("runner") or "")
                if not group:
                    # Standard recovery rows encode G1/G4 as mode; group is
                    # recoverable from the selected path/result filename only
                    # when present, so leave it empty rather than guessing.
                    group = str(row.get("mode") or "")
                keys.add((Path(str(row["run_dir"])).name, str(row["model_id"]), str(row["task_id"])))
    failure_path = organized / "failure_recovery_20261012" / "failure_reconciliation_records.json"
    if failure_path.is_file():
        try:
            rows = load_json(failure_path)
        except (OSError, UnicodeError, json.JSONDecodeError):
            rows = []
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, dict) and all(row.get(field) is not None for field in ("group", "run_dir", "model_id", "task_id")):
                    keys.add((Path(str(row["run_dir"])).name, str(row["model_id"]), str(row["task_id"])))
    return keys


def markdown(summary: dict[str, Any], records: list[dict[str, Any]], generated_at: str) -> str:
    counts = summary["canonical_classification_counts"]
    lines = [
        "# Exhaustive local recovery audit",
        "",
        f"> Generated at {generated_at}. Read-only derived audit; provider requests made: **0**; raw benchmark artifacts modified: **false**.",
        "",
        "## Conclusion",
        "",
        f"The scan inspected **{summary['failed_artifacts_scanned']}** failed artifacts and found **{summary['canonical_recovered_correct']}** unique failed rows whose already-persisted response can be parsed and independently verified as correct. These are recovery diagnostics, not completed-run replacements. The remaining parseable payloads were independently evaluated as mismatches but remain failures and are not counted as wrong answers.",
        "",
        "`format_recovery_retry8` is excluded from final candidates because the existing audit marks that batch incomplete. It was still inspected read-only; any PASS would be listed as not promoted. No provider retry was attempted.",
        "",
        "## Canonical classification",
        "",
        "| Classification | Rows | Meaning |",
        "|---|---:|---|",
        f"| `FAILED_RECOVERED_CORRECT` | {counts.get('FAILED_RECOVERED_CORRECT', 0)} | Persisted output is parseable and passes the local evaluator; recoverable evidence only. |",
        f"| `FAILED_WITH_PERSISTED_PAYLOAD_EVALUATED_WRONG_NOT_COUNTED` | {counts.get('FAILED_WITH_PERSISTED_PAYLOAD_EVALUATED_WRONG_NOT_COUNTED', 0)} | Persisted output is parseable but mismatches; retained as failure, excluded from wrong denominator. |",
        f"| `FAILED_PAYLOAD_UNJUDGED` | {counts.get('FAILED_PAYLOAD_UNJUDGED', 0)} | Candidate exists but local evaluator did not produce PASS/MODEL_ERROR. |",
        f"| `FAILED_NO_PARSEABLE_PERSISTED_PAYLOAD` | {counts.get('FAILED_NO_PARSEABLE_PERSISTED_PAYLOAD', 0)} | No deterministic candidate could be extracted from the saved response. |",
        "",
        "## Coverage against existing derived view",
        "",
        "| Metric | Count |",
        "|---|---:|",
        f"| Canonical failed keys | {summary['canonical_key_count']} |",
        f"| Canonical keys with parseable payload | {summary['canonical_parseable_key_count']} |",
        f"| retry8 excluded artifacts locally inspected | {summary['retry8_excluded_artifact_count']} |",
        f"| retry8 parseable keys | {summary['retry8_parseable_key_count']} |",
        f"| retry8 independently verified PASS (not promoted) | {summary['retry8_recovered_correct_count']} |",
        f"| retry8 PASS already covered by an existing selected key | {summary['retry8_recovered_correct_already_covered']} |",
        f"| retry8 PASS not covered elsewhere | {summary['retry8_recovered_correct_not_covered']} |",
        f"| Recovered correct keys already represented by existing organized indexes | {summary['recovered_correct_already_covered']} |",
        f"| Recovered correct keys not represented by existing organized indexes | {summary['recovered_correct_not_covered']} |",
        "",
        "## Audit boundary",
        "",
        "- The report stores source paths, hashes, statuses, and counts only; it does not store prompts, model outputs, private answer keys, or ground-truth values.",
        "- A failed row is never converted into an ordinary correct/wrong row by this audit. Any future publication must explicitly decide whether to report recovered failures as a separate sensitivity analysis.",
        "- The raw source remains authoritative. This output can be regenerated with the committed script and the same benchmark directory.",
        "",
        "## Per-group summary",
        "",
        "| Group | Scanned failed artifacts | Canonical keys | Recovered correct | Payload evaluated wrong (not counted) |",
        "|---|---:|---:|---:|---:|",
    ]
    for group, item in sorted(summary["by_group"].items()):
        lines.append(f"| {group} | {item['failed_artifacts_scanned']} | {item['canonical_keys']} | {item['recovered_correct']} | {item['payload_wrong_not_counted']} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark-root", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    benchmark_root = resolve_benchmark_root(args.benchmark_root.absolute())
    data_dir = args.data_dir.resolve()
    output_dir = args.output_dir.absolute()
    if output_dir == Path(output_dir.anchor):
        output_dir = benchmark_root / "organized" / "exhaustive_local_recovery_20261012"
    output_dir.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    retry8_records: list[dict[str, Any]] = []
    excluded_retry8 = 0
    total_artifacts = 0
    for path, stage, source_kind in iter_artifacts(benchmark_root):
        total_artifacts += 1
        if stage in EXCLUDED_STAGES:
            record = audit_artifact(path, stage, source_kind, data_dir)
            if record.get("raw_status") == FAILED_STATUS or record.get("classification", "").startswith("FAILED_"):
                retry8_records.append(record)
            excluded_retry8 += 1
            continue
        record = audit_artifact(path, stage, source_kind, data_dir)
        if record.get("raw_status") == FAILED_STATUS or record.get("classification", "").startswith("FAILED_"):
            records.append(record)

    selected = canonical_records(records)
    retry8_selected = canonical_records(retry8_records)
    covered_keys = existing_selected_keys(benchmark_root)
    for record in selected:
        record["already_in_existing_organized_view"] = coverage_key(record) in covered_keys
    for record in retry8_selected:
        record["already_in_existing_organized_view"] = coverage_key(record) in covered_keys

    canonical_counts = Counter(str(record.get("classification")) for record in selected)
    parseable = [record for record in selected if int(record.get("candidate_count", 0) or 0) > 0]
    by_group: dict[str, dict[str, int]] = {}
    for group in sorted({str(record.get("group")) for record in selected}):
        subset = [record for record in selected if str(record.get("group")) == group]
        by_group[group] = {
            "failed_artifacts_scanned": sum(1 for record in records if str(record.get("group")) == group),
            "canonical_keys": len(subset),
            "recovered_correct": sum(record.get("classification") == "FAILED_RECOVERED_CORRECT" for record in subset),
            "payload_wrong_not_counted": sum(record.get("classification") == "FAILED_WITH_PERSISTED_PAYLOAD_EVALUATED_WRONG_NOT_COUNTED" for record in subset),
        }
    generated_at = datetime.now(timezone.utc).isoformat()
    summary: dict[str, Any] = {
        "schema_version": 1,
        "generated_at_utc": generated_at,
        "benchmark_root": str(benchmark_root),
        "data_dir": str(data_dir),
        "failed_artifacts_scanned": len(records),
        "all_candidate_artifacts_seen_including_retry8": total_artifacts,
        "retry8_excluded_artifact_count": excluded_retry8,
        "retry8_parseable_key_count": sum(int(record.get("candidate_count", 0) or 0) > 0 for record in retry8_selected),
        "retry8_recovered_correct_count": sum(record.get("classification") == "FAILED_RECOVERED_CORRECT" for record in retry8_selected),
        "retry8_recovered_correct_already_covered": sum(record.get("classification") == "FAILED_RECOVERED_CORRECT" and record.get("already_in_existing_organized_view") for record in retry8_selected),
        "retry8_recovered_correct_not_covered": sum(record.get("classification") == "FAILED_RECOVERED_CORRECT" and not record.get("already_in_existing_organized_view") for record in retry8_selected),
        "retry8_classification_counts": dict(sorted(Counter(str(record.get("classification")) for record in retry8_selected).items())),
        "canonical_key_count": len(selected),
        "canonical_parseable_key_count": len(parseable),
        "canonical_classification_counts": dict(sorted(canonical_counts.items())),
        "canonical_recovered_correct": canonical_counts.get("FAILED_RECOVERED_CORRECT", 0),
        "recovered_correct_already_covered": sum(record.get("classification") == "FAILED_RECOVERED_CORRECT" and record.get("already_in_existing_organized_view") for record in selected),
        "recovered_correct_not_covered": sum(record.get("classification") == "FAILED_RECOVERED_CORRECT" and not record.get("already_in_existing_organized_view") for record in selected),
        "by_group": by_group,
        "provider_requests_made": 0,
        "raw_results_modified": False,
        "synthetic_results_created": False,
        "answer_key_read_for_local_evaluation": True,
        "excluded_stages": sorted(EXCLUDED_STAGES),
    }
    (output_dir / "exhaustive_local_recovery_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output_dir / "exhaustive_local_recovery_records.json").write_text(json.dumps(selected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output_dir / "exhaustive_local_recovery_retry8_records.json").write_text(json.dumps(retry8_selected, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output_dir / "EXHAUSTIVE_LOCAL_RECOVERY.md").write_text(markdown(summary, selected, generated_at), encoding="utf-8")
    print(json.dumps({"output_dir": str(output_dir), "summary": summary}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
