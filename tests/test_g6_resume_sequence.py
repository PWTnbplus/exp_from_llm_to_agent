from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.run_g6_counterfactual import event_path_for_retry, existing_event_seq


def _write(path: Path, rows: list[object]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_existing_g6_trace_sequence_accepts_only_contiguous_prefix(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    _write(path, [{"seq": 1}, {"seq": 2}, {"seq": 3}])
    assert existing_event_seq(path) == 3


@pytest.mark.parametrize(
    "rows, match",
    [
        ([{"seq": 1}, {"seq": 3}], "strictly contiguous"),
        ([{"seq": 1}, {"seq": 1}], "strictly contiguous"),
        ([{"seq": 1}, {"seq": "2"}], "invalid sequence"),
        ([{"seq": 1}, ["not", "an", "event"]], "not an object"),
    ],
)
def test_existing_g6_trace_sequence_fails_closed_on_invalid_prefix(
    tmp_path: Path, rows: list[object], match: str
) -> None:
    path = tmp_path / "events.jsonl"
    _write(path, rows)
    with pytest.raises(RuntimeError, match=match):
        existing_event_seq(path)


def test_existing_g6_trace_sequence_fails_closed_on_malformed_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    path.write_text('{"seq": 1}\n{"seq":\n', encoding="utf-8")
    with pytest.raises(RuntimeError, match="not valid JSONL"):
        existing_event_seq(path)


def test_g6_retry_trace_path_preserves_malformed_history(tmp_path: Path) -> None:
    path = tmp_path / "traces" / "run-1" / "events.jsonl"
    path.parent.mkdir(parents=True)
    _write(path, [{"seq": 1}, {"seq": 1}])

    retry_path, seq = event_path_for_retry(path)

    assert retry_path != path
    assert retry_path.parent.name == "run-1.retry-1"
    assert seq == 0
    assert path.read_text(encoding="utf-8").count('"seq": 1') == 2
