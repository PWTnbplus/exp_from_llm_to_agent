"""Independent audit for the public-only LU-v2 U transition cohort."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.v3.lu_v2 import FORBIDDEN, validate_nonfinal_transition


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contains_forbidden(value: Any) -> bool:
    if isinstance(value, dict):
        return any(contains_forbidden(key) or contains_forbidden(child) for key, child in value.items())
    if isinstance(value, list):
        return any(contains_forbidden(child) for child in value)
    if isinstance(value, str):
        folded = value.casefold()
        return any(term in folded for term in FORBIDDEN)
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--graphs", type=Path, required=True)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--traces", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--expected-model-id", default="kimi-k2.5")
    args = parser.parse_args()

    graphs = {row["graph_id"]: row for row in read_jsonl(args.graphs)}
    records = read_jsonl(args.records)
    traces = read_jsonl(args.traces)
    failures: list[str] = []
    if len(records) != len(graphs) or len({row.get("graph_id") for row in records}) != len(records):
        failures.append("record_graph_denominator_or_uniqueness")
    if len(traces) != len(records):
        failures.append("trace_record_bijection")
    transition_count = 0
    error_counts: Counter[str] = Counter()
    for index, record in enumerate(records):
        graph_id = record.get("graph_id")
        graph = graphs.get(graph_id)
        if graph is None:
            failures.append(f"unknown_graph:{graph_id}")
            continue
        if record.get("private_labels_read") is not False or contains_forbidden(record.get("candidate")):
            failures.append(f"private_or_forbidden_candidate:{graph_id}")
        if not record.get("provider_usage"):
            failures.append(f"missing_provider_usage:{graph_id}")
        transition = record.get("transition")
        if transition is not None:
            try:
                validate_nonfinal_transition(graph, transition)
                transition_count += 1
            except ValueError as exc:
                failures.append(f"invalid_transition:{graph_id}:{exc}")
        error_counts[str(record.get("validation_error") or "none")] += 1
        trace = traces[index] if index < len(traces) else {}
        if trace.get("model") != args.expected_model_id:
            failures.append(f"trace_model:{graph_id}")
        if contains_forbidden(trace.get("request")):
            failures.append(f"private_or_forbidden_request:{graph_id}")
    summary = {
        "audit_version": "lu-v2-public-u-independent-v1",
        "graph_count": len(graphs),
        "record_count": len(records),
        "trace_count": len(traces),
        "observed_transition_count": transition_count,
        "validation_error_counts": dict(sorted(error_counts.items())),
        "model_ids": sorted({str(trace.get("model")) for trace in traces}),
        "graphs_sha256": sha256(args.graphs),
        "records_sha256": sha256(args.records),
        "traces_sha256": sha256(args.traces),
        "private_labels_read": False,
        "answer_key_read": False,
        "pooling_with_frozen_g7": False,
        "scientific_release_allowed": False,
        "failures": failures,
        "engineering_audit_pass": not failures and transition_count == sum(record.get("transition") is not None for record in records),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if summary["engineering_audit_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
