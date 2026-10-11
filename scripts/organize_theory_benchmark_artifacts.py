#!/usr/bin/env python3
"""Build a skill-compliant, read-only organization layer for theory benchmark data.

The benchmark tree already contains the raw result JSON and per-task JSONL
traces.  This script does not move, delete, retry, or rewrite those files.  It
creates a separate artifact directory with:

* public task/input records;
* raw and selected model outputs;
* per-record usage, latency, cost, status, and lineage metrics;
* a complete trace-file index with hashes, event counts, token totals, and
  request/response/error reconciliation fields;
* run-manifest and result-artifact indexes;
* failure and integrity ledgers; and
* a human-readable summary.

The private answer key is never read.  Sensitive-looking fields and common API
credential patterns are redacted before normalized copies are written.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable


REQUIRED_TRACE_KEYS = {
    "event_id",
    "run_id",
    "task_id",
    "system_type",
    "model_name",
    "step_id",
    "parent_step_id",
    "event_type",
    "timestamp",
    "input",
    "output",
    "prediction",
    "tool_name",
    "tool_arguments",
    "tool_result",
    "token_usage",
    "latency_ms",
    "cost",
    "status",
    "error_message",
    "metadata",
}

PRIVATE_KEYS = {
    "answer_key",
    "ground_truth",
    "checker",
    "hidden_answer",
    "hidden_data",
    "private_test",
    "private_tests",
    "evaluator_answer",
}
SECRET_KEY_PARTS = ("api_key", "apikey", "authorization", "access_token", "secret", "password", "cookie")
SECRET_PATTERNS = (
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}"),
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
            count += 1
    return count


def text(value: Any) -> str:
    return str(value or "")


def redact(value: Any, key: str | None = None) -> Any:
    """Redact credentials/private fields while preserving observable payloads."""
    lowered = (key or "").lower().replace("-", "_")
    if any(part in lowered for part in SECRET_KEY_PARTS):
        return "[REDACTED_SECRET]"
    if lowered in PRIVATE_KEYS:
        return "[REDACTED_PRIVATE_FIELD]"
    if isinstance(value, dict):
        return {str(k): redact(v, str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        output = value
        for pattern in SECRET_PATTERNS:
            output = pattern.sub("[REDACTED_SECRET]", output)
        return output
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relpath(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def numeric(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def int_value(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def result_file_info(path: Path, root: Path, parsed: dict[str, Any] | None = None) -> dict[str, Any]:
    row: dict[str, Any] = {
        "path": str(path.resolve()),
        "relative_path": relpath(path, root),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "json_valid": parsed is not None,
    }
    if parsed is not None:
        row.update(
            {
                "task_id": parsed.get("task_id"),
                "model_id": parsed.get("model_id"),
                "run_id": parsed.get("run_id"),
                "status": parsed.get("status"),
                "validation_status": (parsed.get("validation") or {}).get("status"),
                "trace_path": parsed.get("trace_path"),
            }
        )
    return row


def trace_path_for(result: dict[str, Any] | None, result_path: Path | None) -> Path | None:
    if not result or not result_path:
        return None
    value = result.get("trace_path")
    if not isinstance(value, str) or not value:
        return None
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = result_path.parent / candidate
    return candidate.resolve()


def provider_calls(result: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not result:
        return []
    traces = (result.get("metadata") or {}).get("provider_trace") or []
    return [item for item in traces if isinstance(item, dict)]


def call_usage(call: dict[str, Any]) -> dict[str, Any]:
    response = call.get("response") or {}
    usage = response.get("usage") or {}
    return {
        "input_tokens": int_value(usage.get("input_tokens")),
        "output_tokens": int_value(usage.get("output_tokens")),
        "cost_usd": numeric(usage.get("cost_usd")),
    }


def call_output(call: dict[str, Any]) -> dict[str, Any]:
    response = call.get("response") or {}
    metadata = response.get("metadata") or {}
    usage = call_usage(call)
    return {
        "call_index": call.get("call_index"),
        "content": redact(response.get("content")),
        "tool_calls": redact(response.get("tool_calls")),
        "usage": usage,
        "provider": metadata.get("provider"),
        "model": metadata.get("model"),
        "provider_request_id": metadata.get("raw_id"),
        "attempt": metadata.get("attempt"),
        "latency_seconds": metadata.get("latency_seconds"),
        "error": redact(call.get("error")),
        "has_response": bool(response),
    }


def call_input(call: dict[str, Any]) -> dict[str, Any]:
    request = call.get("request") or {}
    return {
        "call_index": call.get("call_index"),
        "messages": redact(request.get("messages")),
        "tools": redact(request.get("tools")),
        "request_metadata": redact(call.get("metadata")),
    }


def usage_totals(result: dict[str, Any] | None) -> dict[str, Any]:
    calls = provider_calls(result)
    usages = [call_usage(call) for call in calls]
    return {
        "provider_calls": len(calls),
        "responses_with_content": sum(bool(((call.get("response") or {}).get("content"))) for call in calls),
        "calls_with_error": sum(bool(call.get("error")) for call in calls),
        "input_tokens": sum(item["input_tokens"] for item in usages),
        "output_tokens": sum(item["output_tokens"] for item in usages),
        "cost_usd_proxy": round(sum(item["cost_usd"] for item in usages), 8),
        "usage_available_calls": sum(bool((call.get("response") or {}).get("usage")) for call in calls),
        "tool_calls": sum(len((call.get("response") or {}).get("tool_calls") or []) for call in calls),
        "latency_seconds_total": round(
            sum(numeric(((call.get("response") or {}).get("metadata") or {}).get("latency_seconds")) for call in calls),
            6,
        ),
        "latency_seconds_max": round(
            max(
                [numeric(((call.get("response") or {}).get("metadata") or {}).get("latency_seconds")) for call in calls]
                or [0.0]
            ),
            6,
        ),
    }


def trace_summary(path: Path, root: Path) -> dict[str, Any]:
    event_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()
    required_missing = 0
    invalid_json = 0
    sequence_values: list[int] = []
    token_totals = Counter()
    cost_total = 0.0
    latency_values: list[float] = []
    provider_attempts = 0
    provider_responses = 0
    provider_errors = 0
    unresolved_attempts = 0
    first_timestamp: str | None = None
    last_timestamp: str | None = None
    lines = 0
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for raw_line in handle:
            lines += 1
            try:
                event = json.loads(raw_line)
            except json.JSONDecodeError:
                invalid_json += 1
                continue
            if not isinstance(event, dict):
                invalid_json += 1
                continue
            missing = REQUIRED_TRACE_KEYS.difference(event)
            required_missing += int(bool(missing))
            event_type = text(event.get("event_type")) or "<missing>"
            event_counts[event_type] += 1
            status = text(event.get("status")) or "<missing>"
            status_counts[status] += 1
            sequence = event.get("sequence")
            if isinstance(sequence, int):
                sequence_values.append(sequence)
            timestamp = event.get("timestamp")
            if isinstance(timestamp, str):
                first_timestamp = first_timestamp or timestamp
                last_timestamp = timestamp
            usage = event.get("token_usage") or {}
            token_totals["input_tokens"] += int_value(usage.get("input_tokens"))
            token_totals["output_tokens"] += int_value(usage.get("output_tokens"))
            cost_total += numeric(event.get("cost"))
            if event.get("latency_ms") is not None:
                latency_values.append(numeric(event.get("latency_ms")))
            if event_type == "PROVIDER_ATTEMPT":
                provider_attempts += 1
                output = event.get("output") or {}
                if output.get("has_response") is True:
                    provider_responses += 1
                if output.get("error") or event.get("error_message"):
                    provider_errors += 1
    if sequence_values:
        expected = list(range(min(sequence_values), max(sequence_values) + 1))
        sequence_gap_count = len(set(expected).difference(sequence_values))
        sequence_duplicate_count = len(sequence_values) - len(set(sequence_values))
    else:
        sequence_gap_count = 0
        sequence_duplicate_count = 0
    unresolved_attempts = max(0, provider_attempts - provider_responses - provider_errors)
    return {
        "path": str(path.resolve()),
        "relative_path": relpath(path, root),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "line_count": lines,
        "invalid_json_line_count": invalid_json,
        "required_field_missing_line_count": required_missing,
        "event_counts": dict(sorted(event_counts.items())),
        "status_counts": dict(sorted(status_counts.items())),
        "provider_attempt_count": provider_attempts,
        "provider_attempt_response_count": provider_responses,
        "provider_attempt_error_count": provider_errors,
        "provider_attempt_unresolved_count": unresolved_attempts,
        "model_input_count": event_counts.get("MODEL_INPUT", 0),
        "model_output_count": event_counts.get("MODEL_OUTPUT", 0),
        "model_error_count": event_counts.get("MODEL_ERROR", 0),
        "tool_call_count": event_counts.get("TOOL_CALL", 0),
        "tool_result_count": event_counts.get("TOOL_RESULT", 0),
        "tool_error_count": event_counts.get("TOOL_ERROR", 0),
        "retry_event_count": sum(count for key, count in event_counts.items() if "RETRY" in key.upper()),
        "input_tokens": token_totals["input_tokens"],
        "output_tokens": token_totals["output_tokens"],
        "cost_usd_proxy": round(cost_total, 8),
        "latency_ms_total": round(sum(latency_values), 3),
        "latency_ms_max": round(max(latency_values or [0.0]), 3),
        "sequence_gap_count": sequence_gap_count,
        "sequence_duplicate_count": sequence_duplicate_count,
        "first_timestamp": first_timestamp,
        "last_timestamp": last_timestamp,
        "request_response_reconciliation": {
            "provider_attempts_equal_response_plus_error": unresolved_attempts == 0,
            "model_inputs": event_counts.get("MODEL_INPUT", 0),
            "model_outputs": event_counts.get("MODEL_OUTPUT", 0),
            "model_errors": event_counts.get("MODEL_ERROR", 0),
            "tool_calls": event_counts.get("TOOL_CALL", 0),
            "tool_results": event_counts.get("TOOL_RESULT", 0),
            "tool_errors": event_counts.get("TOOL_ERROR", 0),
        },
    }


def result_lineage(row: dict[str, Any], raw: dict[str, Any] | None, selected: dict[str, Any] | None, root: Path) -> dict[str, Any]:
    raw_path = Path(row["raw_result_path"]) if row.get("raw_result_path") else None
    selected_path = Path(row["selected_result_path"]) if row.get("selected_result_path") else None
    raw_info = result_file_info(raw_path, root, raw) if raw_path and raw_path.exists() else {"path": str(raw_path), "exists": False}
    selected_info = (
        result_file_info(selected_path, root, selected)
        if selected_path and selected_path.exists()
        else {"path": str(selected_path), "exists": False}
    )
    raw_trace = trace_path_for(raw, raw_path)
    selected_trace = trace_path_for(selected, selected_path)
    return {
        "record_key": hashlib.sha256(
            "|".join(
                text(row.get(key))
                for key in ("scope", "provider_group", "mode", "difficulty_level", "benchmark_run_id", "model_id", "task_id", "raw_result_path")
            ).encode("utf-8")
        ).hexdigest()[:24],
        "scope": row.get("scope"),
        "provider_group": row.get("provider_group"),
        "mode": row.get("mode"),
        "difficulty_level": row.get("difficulty_level"),
        "difficulty_label": row.get("difficulty_label"),
        "benchmark_run_id": row.get("benchmark_run_id"),
        "run_dir": row.get("run_dir"),
        "model_id": row.get("model_id"),
        "task_id": row.get("task_id"),
        "raw_result": raw_info,
        "selected_result": selected_info,
        "selected_source": row.get("selected_source"),
        "raw_classification": row.get("raw_classification"),
        "selected_classification": row.get("selected_classification"),
        "raw_status": row.get("raw_status"),
        "selected_status": row.get("selected_status"),
        "raw_validation_status": row.get("raw_validation_status"),
        "selected_validation_status": row.get("selected_validation_status"),
        "selected_protocol_valid": row.get("selected_protocol_valid"),
        "selected_answer_available": row.get("selected_answer_available"),
        "selected_answer_correct": row.get("selected_answer_correct"),
        "raw_trace_path": str(raw_trace) if raw_trace else None,
        "selected_trace_path": str(selected_trace) if selected_trace else None,
        "raw_trace_relative_path": relpath(raw_trace, root) if raw_trace else None,
        "selected_trace_relative_path": relpath(selected_trace, root) if selected_trace else None,
        "input_record": "inputs.jsonl",
        "output_record": "outputs.jsonl",
        "metrics_record": "record_metrics.jsonl",
    }


def task_from_result(result: dict[str, Any] | None) -> Any:
    if not result:
        return None
    return redact(result.get("task"))


def make_input_record(lineage: dict[str, Any], raw: dict[str, Any] | None, selected: dict[str, Any] | None) -> dict[str, Any]:
    def inputs(result: dict[str, Any] | None) -> dict[str, Any]:
        return {
            "public_task": task_from_result(result),
            "provider_requests": [call_input(call) for call in provider_calls(result)],
        }

    return {
        "record_key": lineage["record_key"],
        "task_id": lineage["task_id"],
        "model_id": lineage["model_id"],
        "mode": lineage["mode"],
        "benchmark_run_id": lineage["benchmark_run_id"],
        "raw_input": inputs(raw),
        "selected_input": inputs(selected),
        "answer_key_included": False,
        "credential_values_included": False,
    }


def make_output_record(lineage: dict[str, Any], raw: dict[str, Any] | None, selected: dict[str, Any] | None) -> dict[str, Any]:
    def outputs(result: dict[str, Any] | None) -> dict[str, Any]:
        return {
            "answer": redact((result or {}).get("answer")),
            "provider_responses": [call_output(call) for call in provider_calls(result)],
            "validation": redact((result or {}).get("validation")),
            "status": (result or {}).get("status"),
            "protocol_valid": (result or {}).get("protocol_valid"),
        }

    return {
        "record_key": lineage["record_key"],
        "task_id": lineage["task_id"],
        "model_id": lineage["model_id"],
        "mode": lineage["mode"],
        "benchmark_run_id": lineage["benchmark_run_id"],
        "raw_output": outputs(raw),
        "selected_output": outputs(selected),
        "answer_key_included": False,
        "credential_values_included": False,
    }


def make_metrics_record(lineage: dict[str, Any], raw: dict[str, Any] | None, selected: dict[str, Any] | None) -> dict[str, Any]:
    selected_usage = usage_totals(selected)
    raw_usage = usage_totals(raw)
    return {
        "record_key": lineage["record_key"],
        "scope": lineage["scope"],
        "provider_group": lineage["provider_group"],
        "mode": lineage["mode"],
        "difficulty_level": lineage["difficulty_level"],
        "difficulty_label": lineage["difficulty_label"],
        "benchmark_run_id": lineage["benchmark_run_id"],
        "model_id": lineage["model_id"],
        "task_id": lineage["task_id"],
        "selected_source": lineage["selected_source"],
        "raw_classification": lineage["raw_classification"],
        "selected_classification": lineage["selected_classification"],
        "selected_answer_available": lineage["selected_answer_available"],
        "selected_answer_correct": lineage["selected_answer_correct"],
        "raw_usage": raw_usage,
        "selected_usage": selected_usage,
        "selected_trace_exists": bool(lineage["selected_trace_path"] and Path(lineage["selected_trace_path"]).exists()),
        "raw_trace_exists": bool(lineage["raw_trace_path"] and Path(lineage["raw_trace_path"]).exists()),
    }


def aggregate(metrics: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in metrics:
        grouped[tuple(row.get(key) for key in keys)].append(row)
    result: list[dict[str, Any]] = []
    for group_key, rows in sorted(grouped.items(), key=lambda item: tuple(text(value) for value in item[0])):
        usage = [row["selected_usage"] for row in rows]
        result.append(
            {
                **dict(zip(keys, group_key)),
                "records": len(rows),
                "answer_available": sum(bool(row["selected_answer_available"]) for row in rows),
                "answer_correct": sum(bool(row["selected_answer_correct"]) for row in rows),
                "input_tokens": sum(item["input_tokens"] for item in usage),
                "output_tokens": sum(item["output_tokens"] for item in usage),
                "cost_usd_proxy": round(sum(item["cost_usd_proxy"] for item in usage), 8),
                "provider_calls": sum(item["provider_calls"] for item in usage),
                "responses_with_content": sum(item["responses_with_content"] for item in usage),
                "trace_missing": sum(not row["selected_trace_exists"] for row in rows),
                "selected_classification_counts": dict(sorted(Counter(row["selected_classification"] for row in rows).items())),
            }
        )
    return result


def markdown_table(headers: list[str], rows: Iterable[Iterable[Any]]) -> str:
    output = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        output.append("| " + " | ".join(str(value).replace("|", "\\|").replace("\n", "<br>") for value in row) + " |")
    return "\n".join(output)


def build_summary_markdown(summary: dict[str, Any], groups: list[dict[str, Any]], models: list[dict[str, Any]], output: Path) -> str:
    counts = summary["counts"]
    usage = summary["selected_usage_totals"]
    group_rows = []
    for row in groups:
        judged = row["answer_available"]
        accuracy = f"{100 * row['answer_correct'] / judged:.2f}%" if judged else "NA"
        group_rows.append(
            [
                row.get("scope"),
                row.get("provider_group"),
                row.get("mode"),
                row.get("difficulty_level"),
                row["records"],
                row["answer_available"],
                row["answer_correct"],
                accuracy,
                row["input_tokens"],
                row["output_tokens"],
                f"{row['cost_usd_proxy']:.6f}",
            ]
        )
    model_rows = []
    for row in models:
        judged = row["answer_available"]
        accuracy = f"{100 * row['answer_correct'] / judged:.2f}%" if judged else "NA"
        model_rows.append(
            [
                row.get("scope"),
                row.get("provider_group"),
                row.get("mode"),
                row.get("model_id"),
                row["records"],
                row["answer_available"],
                row["answer_correct"],
                accuracy,
                row["input_tokens"],
                row["output_tokens"],
                f"{row['cost_usd_proxy']:.6f}",
            ]
        )
    return f"""# Theory Benchmark Skill Artifacts

> 生成时间：{summary['generated_at_utc']}（UTC）  
> profile：`theory_benchmark`  
> 原始数据根目录：`{summary['source_benchmark_root']}`  
> 本目录是整理层；原始 result JSON、per-task trace JSONL、恢复结果和审计日志均保留在原位置，不被移动或覆盖。

## 1. 交付范围

本整理层按 `whole_pros.zip` 中的 Unified Skill 组织，覆盖公开题面输入、provider 可见 request、模型 response、结构化 answer、usage/token、cost proxy、latency、工具调用、错误/重试、run lineage、trace 完整性和文件 SHA-256。答案键、隐藏真值、API key 和 Authorization 值未复制。

核心文件：

- `organization_manifest.json`：profile、源目录、产物清单和安全边界。
- `task_catalog.jsonl`：去重后的公开题面任务输入。
- `inputs.jsonl`：逐条记录的公开任务与 provider request/messages/tools。
- `outputs.jsonl`：逐条记录的 raw/selected provider response、answer、validation 和错误。
- `record_metrics.jsonl`：逐条 token、调用、耗时、cost proxy、状态、分类和 lineage 指标。
- `records_index.jsonl`：raw/selected result、trace、输入/输出/指标之间的关联索引。
- `trace_index.jsonl`：每个 JSONL 日志文件的 hash、事件计数、token、错误和 request/response 对账。
- `result_artifact_index.jsonl`：所有 `models/*/*.json` 结果/恢复文件的文件级索引。
- `run_manifests.jsonl`：36 个 run manifest 的脱敏整理版。
- `failures.jsonl`：失败、超时、provider、格式、策略和无答案记录索引。
- `SUMMARY.md`：本摘要；`summary.json`：机器可读汇总。

## 2. 总量与安全边界

{markdown_table(['指标', '数量/值'], [
    ['run manifest', counts['run_manifests']],
    ['canonical result records', counts['canonical_records']],
    ['result artifacts（含恢复阶段）', counts['result_artifacts']],
    ['unique task IDs', counts['unique_task_ids']],
    ['task input variants', counts['task_input_variants']],
    ['trace JSONL files', counts['trace_files']],
    ['invalid JSON trace lines', counts['invalid_trace_lines']],
    ['trace lines missing required keys', counts['trace_lines_missing_required_keys']],
    ['provider attempts unresolved', counts['provider_attempts_unresolved']],
    ['records missing selected trace', counts['records_missing_selected_trace']],
    ['answer key copied', 'NO'],
    ['credential values copied', 'NO'],
])}

## 3. Selected provider usage totals

以下是 canonical record 的 selected 结果口径；如果 selected 是格式/超时恢复结果，恢复结果的 usage 会进入 selected 合计，raw usage 仍保存在 `record_metrics.jsonl` 中。`cost_usd_proxy` 是结果中记录的本地输入/输出价格代理，不等同于 provider 最终账单。

{markdown_table(['指标', '值'], [
    ['input tokens', usage['input_tokens']],
    ['output tokens', usage['output_tokens']],
    ['provider calls', usage['provider_calls']],
    ['responses with content', usage['responses_with_content']],
    ['calls with error', usage['calls_with_error']],
    ['calls with usage', usage['usage_available_calls']],
    ['tool calls', usage['tool_calls']],
    ['latency seconds total', usage['latency_seconds_total']],
    ['latency seconds max per record', usage['latency_seconds_max']],
    ['cost USD proxy', f"{usage['cost_usd_proxy']:.8f}"],
])}

## 4. 按 scope/provider/mode/难度

{markdown_table(['scope', 'provider', 'mode', 'level', 'records', 'answer available', 'correct', 'accuracy', 'input tok', 'output tok', 'cost proxy'], group_rows)}

## 5. 按模型

{markdown_table(['scope', 'provider', 'mode', 'model', 'records', 'answer available', 'correct', 'accuracy', 'input tok', 'output tok', 'cost proxy'], model_rows)}

## 6. 分类与错误

selected classification：

{markdown_table(['分类', '数量'], sorted(summary['selected_classification_counts'].items()))}

trace event type：

{markdown_table(['event_type', '数量'], sorted(summary['trace_event_type_counts'].items()))}

## 7. 对账与解释

- `inputs.jsonl` 和 `outputs.jsonl` 都同时保留 raw 与 selected 两个视角；格式恢复不会覆盖原始结果。
- 每条记录的 provider response usage、latency、cost 和 request/response 内容可通过 `record_key` 与 `record_metrics.jsonl`、`records_index.jsonl` 关联。
- 每个 trace 的事件级证据、文件大小、SHA-256、schema 必要字段缺失行、序号缺口、provider attempt 响应/错误/未决数量见 `trace_index.jsonl`。
- 失败样本不被删除；超时、403/provider 错误、格式错误、策略违反和没有答案的记录进入 `failures.jsonl`，并保留原始路径。
- 本整理层不是新的科学结论，也不把 provider 的本地 cost proxy 当作真实账单；正式准确率仍必须按项目 evaluator 和预注册统计口径解释。

## 8. 恢复命令

```text
python scripts/organize_theory_benchmark_artifacts.py --benchmark-root {summary['source_benchmark_root']} --output-dir {output}
```

生成完成时间：{summary['generated_at_utc']}（UTC）。
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    root = args.benchmark_root.resolve()
    output = (args.output_dir or root / "organized" / "skill_artifacts").resolve()
    output.mkdir(parents=True, exist_ok=True)

    source_index = root / "organized" / "results_index.jsonl"
    if not source_index.is_file():
        raise SystemExit(f"missing canonical index: {source_index}")
    index_rows = [json.loads(line) for line in source_index.read_text(encoding="utf-8").splitlines() if line.strip()]

    records: list[dict[str, Any]] = []
    input_records: list[dict[str, Any]] = []
    output_records: list[dict[str, Any]] = []
    metrics_records: list[dict[str, Any]] = []
    task_variants: dict[str, dict[str, Any]] = {}
    failure_records: list[dict[str, Any]] = []
    missing_result_count = 0
    private_field_hits = 0

    for row in index_rows:
        raw_path = Path(row.get("raw_result_path", ""))
        selected_path = Path(row.get("selected_result_path", ""))
        raw = None
        selected = None
        try:
            raw = load_json(raw_path) if raw_path.is_file() else None
        except (OSError, json.JSONDecodeError):
            raw = None
        try:
            selected = load_json(selected_path) if selected_path.is_file() else None
        except (OSError, json.JSONDecodeError):
            selected = None
        if raw is None or selected is None:
            missing_result_count += 1
        lineage = result_lineage(row, raw, selected, root)
        records.append(lineage)
        input_record = make_input_record(lineage, raw, selected)
        output_record = make_output_record(lineage, raw, selected)
        metrics_record = make_metrics_record(lineage, raw, selected)
        input_records.append(input_record)
        output_records.append(output_record)
        metrics_records.append(metrics_record)

        task = task_from_result(selected) or task_from_result(raw)
        task_id = text(row.get("task_id"))
        if task_id:
            variant_hash = hashlib.sha256(json.dumps(task, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]
            variant_key = f"{task_id}:{variant_hash}"
            entry = task_variants.setdefault(
                variant_key,
                {
                    "task_id": task_id,
                    "task_variant_hash": variant_hash,
                    "public_task": task,
                    "record_count": 0,
                    "record_keys": [],
                },
            )
            entry["record_count"] += 1
            entry["record_keys"].append(lineage["record_key"])

        if row.get("selected_classification") not in {"answer_correct", "answer_incorrect_structured"}:
            failure_records.append(
                {
                    **{key: lineage.get(key) for key in ("record_key", "scope", "provider_group", "mode", "difficulty_level", "benchmark_run_id", "model_id", "task_id")},
                    "raw_classification": lineage.get("raw_classification"),
                    "selected_classification": lineage.get("selected_classification"),
                    "selected_status": lineage.get("selected_status"),
                    "selected_validation_status": lineage.get("selected_validation_status"),
                    "raw_result_path": lineage["raw_result"].get("path"),
                    "selected_result_path": lineage["selected_result"].get("path"),
                    "selected_trace_path": lineage.get("selected_trace_path"),
                }
            )

    task_catalog = sorted(task_variants.values(), key=lambda item: (item["task_id"], item["task_variant_hash"]))

    trace_paths = sorted({path for path in root.rglob("logs/*.jsonl") if path.is_file()})
    trace_records = [trace_summary(path, root) for path in trace_paths]
    trace_event_counts: Counter[str] = Counter()
    for trace in trace_records:
        trace_event_counts.update(trace["event_counts"])

    manifest_records: list[dict[str, Any]] = []
    for manifest_path in sorted(root.rglob("run_manifest.json")):
        try:
            manifest = load_json(manifest_path)
        except (OSError, json.JSONDecodeError):
            manifest = {"_read_error": True}
        manifest_records.append(
            {
                "manifest_path": str(manifest_path.resolve()),
                "manifest_relative_path": relpath(manifest_path, root),
                "manifest_sha256": sha256(manifest_path),
                "manifest": redact(manifest),
            }
        )

    result_artifact_records: list[dict[str, Any]] = []
    for result_path in sorted(path for path in root.rglob("models/*/*.json") if path.is_file()):
        try:
            parsed = load_json(result_path)
        except (OSError, json.JSONDecodeError):
            parsed = None
        result_artifact_records.append(result_file_info(result_path, root, parsed if isinstance(parsed, dict) else None))

    selected_usage = usage_totals({"metadata": {"provider_trace": []}})
    selected_usage = {
        "input_tokens": sum(row["selected_usage"]["input_tokens"] for row in metrics_records),
        "output_tokens": sum(row["selected_usage"]["output_tokens"] for row in metrics_records),
        "cost_usd_proxy": round(sum(row["selected_usage"]["cost_usd_proxy"] for row in metrics_records), 8),
        "provider_calls": sum(row["selected_usage"]["provider_calls"] for row in metrics_records),
        "responses_with_content": sum(row["selected_usage"]["responses_with_content"] for row in metrics_records),
        "calls_with_error": sum(row["selected_usage"]["calls_with_error"] for row in metrics_records),
        "usage_available_calls": sum(row["selected_usage"]["usage_available_calls"] for row in metrics_records),
        "tool_calls": sum(row["selected_usage"]["tool_calls"] for row in metrics_records),
        "latency_seconds_total": round(sum(row["selected_usage"]["latency_seconds_total"] for row in metrics_records), 6),
        "latency_seconds_max": round(max((row["selected_usage"]["latency_seconds_max"] for row in metrics_records), default=0.0), 6),
    }

    groups = aggregate(metrics_records, ("scope", "provider_group", "mode", "difficulty_level"))
    models = aggregate(metrics_records, ("scope", "provider_group", "mode", "model_id"))
    selected_classes = Counter(text(row.get("selected_classification")) for row in metrics_records)
    counts = {
        "run_manifests": len(manifest_records),
        "canonical_records": len(records),
        "result_artifacts": len(result_artifact_records),
        "unique_task_ids": len({row["task_id"] for row in task_catalog}),
        "task_input_variants": len(task_catalog),
        "trace_files": len(trace_records),
        "invalid_trace_lines": sum(row["invalid_json_line_count"] for row in trace_records),
        "trace_lines_missing_required_keys": sum(row["required_field_missing_line_count"] for row in trace_records),
        "provider_attempts_unresolved": sum(row["provider_attempt_unresolved_count"] for row in trace_records),
        "records_missing_selected_trace": sum(not row["selected_trace_exists"] for row in metrics_records),
        "missing_canonical_result_files": missing_result_count,
    }
    summary = {
        "generated_at_utc": now_utc(),
        "organization_version": 1,
        "profile": "theory_benchmark",
        "source_benchmark_root": str(root),
        "source_canonical_index": str(source_index),
        "answer_key_read": False,
        "credential_values_copied": False,
        "counts": counts,
        "selected_usage_totals": selected_usage,
        "raw_classification_counts": dict(sorted(Counter(text(row.get("raw_classification")) for row in records).items())),
        "selected_classification_counts": dict(sorted(selected_classes.items())),
        "trace_event_type_counts": dict(sorted(trace_event_counts.items())),
        "trace_status_counts": dict(
            sorted(
                (
                    status,
                    sum(row["status_counts"].get(status, 0) for row in trace_records),
                )
                for status in {status for row in trace_records for status in row["status_counts"]}
            )
        ),
        "aggregates": {"by_scope_provider_mode_level": groups, "by_model": models},
        "source_artifacts": {
            "run_manifest_count": len(manifest_records),
            "result_artifact_count": len(result_artifact_records),
            "trace_file_count": len(trace_records),
        },
    }

    generated = {
        "task_catalog.jsonl": lambda: write_jsonl(output / "task_catalog.jsonl", task_catalog),
        "inputs.jsonl": lambda: write_jsonl(output / "inputs.jsonl", input_records),
        "outputs.jsonl": lambda: write_jsonl(output / "outputs.jsonl", output_records),
        "record_metrics.jsonl": lambda: write_jsonl(output / "record_metrics.jsonl", metrics_records),
        "records_index.jsonl": lambda: write_jsonl(output / "records_index.jsonl", records),
        "trace_index.jsonl": lambda: write_jsonl(output / "trace_index.jsonl", trace_records),
        "result_artifact_index.jsonl": lambda: write_jsonl(output / "result_artifact_index.jsonl", result_artifact_records),
        "run_manifests.jsonl": lambda: write_jsonl(output / "run_manifests.jsonl", manifest_records),
        "failures.jsonl": lambda: write_jsonl(output / "failures.jsonl", failure_records),
    }
    artifact_counts = {name: writer() for name, writer in generated.items()}
    write_json(output / "summary.json", summary)
    write_json(output / "organization_manifest.json", {
        "generated_at_utc": summary["generated_at_utc"],
        "profile": "theory_benchmark",
        "source_benchmark_root": str(root),
        "source_skill_archive": "D:\\硕士\\prj1_ai_cal\\exp\\exp1_from_llm_to_agent\\prompt\\whole_pros.zip",
        "source_skill_archive_sha256": sha256(Path("D:\\硕士\\prj1_ai_cal\\exp\\exp1_from_llm_to_agent\\prompt\\whole_pros.zip")) if Path("D:\\硕士\\prj1_ai_cal\\exp\\exp1_from_llm_to_agent\\prompt\\whole_pros.zip").is_file() else None,
        "answer_key_read": False,
        "credential_values_copied": False,
        "raw_data_mutated": False,
        "raw_logs_copied": False,
        "raw_logs_indexed": True,
        "artifact_files": artifact_counts | {"summary.json": 1, "organization_manifest.json": 1, "SUMMARY.md": 1},
        "file_roles": {
            "inputs.jsonl": "public task and provider-visible request payloads",
            "outputs.jsonl": "raw/selected provider-visible responses and evaluator status",
            "record_metrics.jsonl": "per-record usage, latency, cost proxy, classifications and trace existence",
            "trace_index.jsonl": "all run logs with hash, schema presence and event reconciliation",
            "records_index.jsonl": "record lineage and source paths",
        },
    })
    summary_md = build_summary_markdown(summary, groups, models, output)
    (output / "SUMMARY.md").write_text(summary_md, encoding="utf-8")

    checksum_rows = []
    for path in sorted(output.iterdir()):
        if path.name == "checksums.sha256" or not path.is_file():
            continue
        checksum_rows.append(f"{sha256(path)}  {path.name}")
    (output / "checksums.sha256").write_text("\n".join(checksum_rows) + "\n", encoding="utf-8")

    print(json.dumps({
        "output_dir": str(output),
        "canonical_records": len(records),
        "result_artifacts": len(result_artifact_records),
        "trace_files": len(trace_records),
        "task_variants": len(task_catalog),
        "input_tokens": selected_usage["input_tokens"],
        "output_tokens": selected_usage["output_tokens"],
        "cost_usd_proxy": selected_usage["cost_usd_proxy"],
        "failures": len(failure_records),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
