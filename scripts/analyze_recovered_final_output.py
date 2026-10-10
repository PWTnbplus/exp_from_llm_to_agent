#!/usr/bin/env python3
"""Aggregate recovered benchmark attempts by the semantic content of final output.

This deliberately keeps raw benchmark records and answer keys outside the
repository.  It reads the local answer key only for scoring and prints
aggregate counts; it never prints model output, traces, or private paths.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import re
import sys
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _balanced_objects(text: str | None) -> list[str]:
    if not isinstance(text, str) or not text.strip():
        return []
    objects: list[str] = []
    for start, char in enumerate(text):
        if char != "{":
            continue
        depth = 0
        in_string = False
        escaped = False
        for index in range(start, len(text)):
            current = text[index]
            if in_string:
                if escaped:
                    escaped = False
                elif current == "\\":
                    escaped = True
                elif current == '"':
                    in_string = False
                continue
            if current == '"':
                in_string = True
            elif current == "{":
                depth += 1
            elif current == "}":
                depth -= 1
                if depth == 0:
                    objects.append(text[start : index + 1])
                    break
                if depth < 0:
                    break
    return objects


def _parse_output(text: str | None) -> list[dict[str, Any]]:
    if not isinstance(text, str) or not text.strip():
        return []
    candidates: list[dict[str, Any]] = []
    for raw in [text.strip(), *_balanced_objects(text)]:
        variants = [raw, re.sub(r",\s*([}\]])", r"\1", raw)]
        for value in variants:
            try:
                parsed = json.loads(value)
            except (TypeError, json.JSONDecodeError):
                continue
            if isinstance(parsed, dict):
                candidates.append(parsed)
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in candidates:
        marker = json.dumps(candidate, ensure_ascii=False, sort_keys=True)
        if marker not in seen:
            seen.add(marker)
            unique.append(candidate)
    return sorted(unique, key=lambda item: len(json.dumps(item, ensure_ascii=False)), reverse=True)


def _recover_final_output(result: dict[str, Any] | None) -> tuple[Any, str]:
    if not isinstance(result, dict):
        return None, "none"
    answer = result.get("answer")
    if isinstance(answer, dict) and "final_answer" in answer:
        return answer["final_answer"], "stored"
    traces = (result.get("metadata") or {}).get("provider_trace") or []
    for trace in reversed(traces):
        response = trace.get("response") or {}
        content = response.get("content") if isinstance(response, dict) else None
        candidates = _parse_output(content)
        if candidates:
            candidate = candidates[0]
            return candidate.get("final_answer", candidate), "trace"
    return None, "none"


def _flatten(value: Any, key: str | None = None) -> list[tuple[Any, str | None]]:
    if isinstance(value, dict):
        output: list[tuple[Any, str | None]] = []
        for child_key, child_value in value.items():
            output.extend(_flatten(child_value, str(child_key)))
        return output
    if isinstance(value, list):
        output = []
        for child in value:
            output.extend(_flatten(child, key))
        return output
    return [(value, key)]


def _expression_equal(actual: str, expected: str) -> bool:
    try:
        import sympy as sp

        def parse(text: str) -> Any:
            names = set(re.findall(r"\b[A-Za-z_]\w*\b", text))
            known = {"exp": sp.exp, "log": sp.log, "sqrt": sp.sqrt, "sin": sp.sin, "cos": sp.cos, "tan": sp.tan, "pi": sp.pi, "E": sp.E}
            return sp.sympify(text, locals={name: known.get(name, sp.Symbol(name)) for name in names})

        def relation(text: str) -> Any:
            if text.count("=") == 1:
                left, right = text.split("=", 1)
                return parse(left) - parse(right)
            return parse(text)

        return bool(sp.simplify(relation(actual) - relation(expected)) == 0)
    except (TypeError, ValueError, SyntaxError, ImportError):
        return False


def _scalar_equal(expected: Any, actual: Any, key: str | None, checker: dict[str, Any]) -> bool:
    if isinstance(expected, bool):
        return isinstance(actual, bool) and expected == actual
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        if not isinstance(actual, (int, float)) or isinstance(actual, bool):
            return False
        if not math.isfinite(float(actual)):
            return False
        tolerance = float(checker.get("tolerance", 1e-6))
        return abs(float(expected) - float(actual)) <= tolerance * max(1.0, abs(float(expected)))
    if isinstance(expected, str):
        if key in set(checker.get("expression_fields", [])) and isinstance(actual, str):
            return _expression_equal(actual, expected)
        return isinstance(actual, str) and expected == actual
    return expected == actual


def _semantic_correct(task_id: str, actual: Any, answers: dict[str, dict[str, Any]]) -> bool:
    answer = answers.get(task_id)
    if not answer:
        return False
    expected = answer["ground_truth"]["answer"]
    checker = answer["checker"]
    actual_values = _flatten(actual)
    used: set[int] = set()
    for expected_value, key in _flatten(expected):
        match = next(
            (
                index
                for index, (actual_value, _) in enumerate(actual_values)
                if index not in used and _scalar_equal(expected_value, actual_value, key, checker)
            ),
            None,
        )
        if match is None:
            return False
        used.add(match)
    return True


def _recovery_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return tuple(row.get(key) for key in ("scope", "provider_group", "mode", "difficulty_level", "benchmark_run_id", "model_id", "task_id"))


def _aggregate(rows: Iterable[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], Counter[str]] = defaultdict(Counter)
    for row in rows:
        key = tuple(row.get(name) for name in keys)
        counts = grouped[key]
        counts["records"] += 1
        counts["strict_correct"] += int(row["strict_correct"])
        counts["output_correct"] += int(row["semantic_correct"] is True)
        counts["output_wrong"] += int(row["semantic_correct"] is False)
        counts["no_output"] += int(row["semantic_correct"] is None)
        counts["recovery_selected"] += int(row["final_source"] == "format_recovery")
        counts["cost_usd_proxy"] += float(row.get("selected_cost_usd", 0.0) or 0.0)
    result: list[dict[str, Any]] = []
    for key, counts in sorted(grouped.items(), key=lambda item: tuple(str(value) for value in item[0])):
        item = {name: value for name, value in zip(keys, key)}
        item.update(dict(counts))
        judged = counts["output_correct"] + counts["output_wrong"]
        item["output_correct_all_pct"] = round(100.0 * counts["output_correct"] / counts["records"], 4) if counts["records"] else None
        item["output_correct_judged_pct"] = round(100.0 * counts["output_correct"] / judged, 4) if judged else None
        result.append(item)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark-root", type=Path, required=True)
    parser.add_argument("--answer-key", type=Path, default=ROOT / "data" / "theory_benchmark_v2" / "answer_key.json")
    args = parser.parse_args()
    benchmark_root = args.benchmark_root.resolve()
    organized = benchmark_root / "organized"
    answers = {row["task_id"]: row for row in _load(args.answer_key.resolve())}

    recovery_paths: dict[tuple[Any, ...], str] = {}
    recovery_file = organized / "format_failures" / "format_recovery_results.jsonl"
    if recovery_file.exists():
        for line in recovery_file.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                recovery_paths[_recovery_key(row)] = str(row.get("format_recovery_result_path") or "")

    rows: list[dict[str, Any]] = []
    indexed_run_dirs: set[Path] = set()
    index_file = organized / "results_index.jsonl"
    for line in index_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        indexed_run_dirs.add(Path(row["run_dir"]).resolve())
        key = _recovery_key(row)
        recovery_path = recovery_paths.get(key, "")
        final_path = Path(recovery_path) if recovery_path else Path(row["selected_result_path"])
        result = _load(final_path) if final_path.exists() else None
        actual, _ = _recover_final_output(result)
        rows.append(
            {
                **row,
                "final_source": "format_recovery" if recovery_path else row.get("selected_source", "raw"),
                "strict_correct": bool(isinstance(result, dict) and (result.get("validation") or {}).get("answer_correct") is True),
                "semantic_correct": None if actual is None else _semantic_correct(str(row["task_id"]), actual, answers),
            }
        )

    # A legacy complete run may predate run_manifest.json and therefore be
    # absent from results_index.jsonl.  Include only direct level/run folders
    # containing result JSON files; recovery subdirectories are not scanned.
    unindexed_runs = 0
    level_numbers = {"easy": 1, "mid": 2, "diff": 3}
    for arm_dir_name, mode in (("pure_llm", "G1"), ("agent", "G4")):
        arm_dir = benchmark_root / arm_dir_name
        if not arm_dir.exists():
            continue
        for provider_dir in sorted(path for path in arm_dir.iterdir() if path.is_dir()):
            provider_group = provider_dir.name.removesuffix("_without_lim")
            scope = "unlimited" if provider_dir.name.endswith("_without_lim") else "limited_or_legacy"
            for level_name, level_number in level_numbers.items():
                level_dir = provider_dir / level_name
                if not level_dir.exists():
                    continue
                for run_dir in sorted(path for path in level_dir.glob("run-*") if path.is_dir()):
                    resolved_run = run_dir.resolve()
                    if resolved_run in indexed_run_dirs:
                        continue
                    result_paths = sorted(run_dir.glob("models/*/*.json"))
                    if not result_paths:
                        continue
                    unindexed_runs += 1
                    for result_path in result_paths:
                        result = _load(result_path)
                        actual, _ = _recover_final_output(result)
                        rows.append(
                            {
                                "scope": scope,
                                "provider_group": provider_group,
                                "mode": mode,
                                "difficulty_level": level_number,
                                "difficulty_label": level_name,
                                "benchmark_run_id": run_dir.name,
                                "run_dir": str(run_dir),
                                "model_id": result_path.parent.name,
                                "task_id": (result or {}).get("task_id", result_path.stem),
                                "selected_cost_usd": ((result or {}).get("metadata") or {}).get("budget", {}).get("used", {}).get("cost_usd", 0.0),
                                "final_source": "raw",
                                "strict_correct": bool(isinstance(result, dict) and (result.get("validation") or {}).get("answer_correct") is True),
                                "semantic_correct": None if actual is None else _semantic_correct(str((result or {}).get("task_id", "")), actual, answers),
                            }
                        )

    output = {
        "records": len(rows),
        "format_recovery_selected": sum(row["final_source"] == "format_recovery" for row in rows),
        "unindexed_run_count": unindexed_runs,
        "overall": _aggregate(rows, ()),
        "by_scope_provider": _aggregate(rows, ("scope", "provider_group")),
        "by_scope_provider_mode": _aggregate(rows, ("scope", "provider_group", "mode")),
        "by_scope_provider_mode_level": _aggregate(rows, ("scope", "provider_group", "mode", "difficulty_level")),
        "by_scope_provider_model": _aggregate(rows, ("scope", "provider_group", "model_id")),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
