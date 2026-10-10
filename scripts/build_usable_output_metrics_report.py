#!/usr/bin/env python3
"""Build a metrics-focused report containing only usable final outputs."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_403 = re.compile(r"(?i)(?:\b403\b|forbidden)")
TIMEOUT_WORDS = ("timeout", "timed out", "time out", "deadline exceeded", "deadline reached")


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def text(value: Any) -> str:
    return str(value or "")


def flatten(value: Any) -> list[Any]:
    if isinstance(value, dict):
        result: list[Any] = []
        for child in value.values():
            result.extend(flatten(child))
        return result
    if isinstance(value, list):
        result = []
        for child in value:
            result.extend(flatten(child))
        return result
    return [value]


def field_paths(value: Any, prefix: str = "") -> Counter[str]:
    result: Counter[str] = Counter()
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            result[path] += 1
            result.update(field_paths(child, path))
    elif isinstance(value, list):
        for child in value[:20]:
            result.update(field_paths(child, prefix + "[]"))
    return result


def contains_text(value: Any, pattern: re.Pattern[str]) -> bool:
    try:
        return bool(pattern.search(json.dumps(value, ensure_ascii=False)))
    except (TypeError, ValueError):
        return False


def has_timeout(value: Any) -> bool:
    try:
        haystack = json.dumps(value, ensure_ascii=False).lower()
    except (TypeError, ValueError):
        return False
    return any(word in haystack for word in TIMEOUT_WORDS)


def pct(numerator: int, denominator: int) -> str:
    return f"{100.0 * numerator / denominator:.2f}%" if denominator else "NA"


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        cells = [str(value).replace("|", "\\|").replace("\n", "<br>") for value in row]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def classify_exclusion(raw: dict[str, Any], selected: dict[str, Any], raw_class: str, selected_class: str, actual: Any) -> str:
    # Transport/provider failures are excluded even if a later retry happened
    # to leave partial content in the result envelope.
    if contains_text(raw, FORBIDDEN_403) or contains_text(selected, FORBIDDEN_403):
        return "403_or_forbidden"
    if raw_class == "transport_timeout" or selected_class == "transport_timeout" or has_timeout(raw) or has_timeout(selected):
        return "timeout"
    if raw_class == "provider_error" or selected_class == "provider_error":
        return "provider_error"
    if raw_class == "policy_violation" or selected_class == "policy_violation":
        return "policy_violation"
    if actual is not None:
        return "usable_output"
    if raw_class.startswith("format_") or selected_class.startswith("format_"):
        return "unusable_format_or_schema"
    return "no_output_or_other_error"


def group_stat(records: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], Counter[str]] = defaultdict(Counter)
    for record in records:
        counter = groups[tuple(record.get(key) for key in keys)]
        counter["all"] += 1
        counter["usable"] += int(record["usable"])
        counter["clean"] += int(record["usable"] and not record["raw_format_failure"])
        counter["recovered"] += int(record["usable"] and record["raw_format_failure"])
        counter["correct"] += int(record["semantic_correct"] is True)
        counter["wrong"] += int(record["semantic_correct"] is False)
        counter["strict_correct"] += int(record["strict_correct"] and record["usable"])
    output = []
    for key, counter in sorted(groups.items(), key=lambda item: tuple(text(value) for value in item[0])):
        row = dict(zip(keys, key))
        row.update(counter)
        row["judged"] = counter["correct"] + counter["wrong"]
        output.append(row)
    return output


def build_records(root: Path) -> tuple[list[dict[str, Any]], int, int]:
    sys.path.insert(0, str(REPO_ROOT))
    from scripts.analyze_recovered_final_output import _recover_final_output, _semantic_correct
    from scripts.build_full_input_output_report import load_rows, recovery_key
    from scripts.organize_benchmark_results import classify

    answer_key_path = REPO_ROOT / "data" / "theory_benchmark_v2" / "answer_key.json"
    answers = {row["task_id"]: row for row in load(answer_key_path)} if answer_key_path.exists() else {}
    rows, recovery_paths, unindexed_runs = load_rows(root)
    records: list[dict[str, Any]] = []
    for row in rows:
        raw_path = Path(row["raw_result_path"])
        raw = load(raw_path) if raw_path.exists() else {}
        recovery_path = Path(recovery_paths[recovery_key(row)]) if recovery_paths.get(recovery_key(row)) else None
        selected_path = recovery_path if recovery_path and recovery_path.exists() else Path(row.get("selected_result_path") or raw_path)
        selected = load(selected_path) if selected_path.exists() else raw
        actual, extraction = _recover_final_output(selected)
        raw_class = classify(raw)
        selected_class = classify(selected)
        exclusion = classify_exclusion(raw, selected, raw_class, selected_class, actual)
        usable = exclusion == "usable_output"
        task_id = text(row.get("task_id") or (raw.get("task") or {}).get("task_id"))
        semantic_correct = None
        if usable and task_id in answers:
            semantic_correct = _semantic_correct(task_id, actual, answers)
        records.append(
            {
                "scope": row.get("scope"),
                "provider_group": row.get("provider_group"),
                "mode": row.get("mode"),
                "difficulty_level": row.get("difficulty_level"),
                "difficulty_label": row.get("difficulty_label"),
                "benchmark_run_id": row.get("benchmark_run_id"),
                "model_id": row.get("model_id"),
                "task_id": task_id,
                "raw_result_path": str(raw_path),
                "selected_result_path": str(selected_path),
                "final_source": "format_recovery" if recovery_path and recovery_path.exists() else "raw",
                "extraction": extraction,
                "raw_class": raw_class,
                "selected_class": selected_class,
                "raw_format_failure": raw_class.startswith("format_"),
                "exclusion": exclusion,
                "usable": usable,
                "strict_correct": bool((selected.get("validation") or {}).get("answer_correct") is True),
                "semantic_correct": semantic_correct,
                "output": actual if usable else None,
            }
        )
    return records, len(rows), unindexed_runs


def render(root: Path, output: Path, records: list[dict[str, Any]], total: int, unindexed_runs: int) -> None:
    exclusion_counts = Counter(record["exclusion"] for record in records)
    usable = [record for record in records if record["usable"]]
    correct = sum(record["semantic_correct"] is True for record in usable)
    wrong = sum(record["semantic_correct"] is False for record in usable)
    judged = correct + wrong
    strict_correct = sum(record["strict_correct"] for record in usable)
    clean = sum(not record["raw_format_failure"] for record in usable)
    recovered = len(usable) - clean
    lengths = [len(json.dumps(record["output"], ensure_ascii=False, separators=(",", ":"))) for record in usable]
    leaf_counts = [len(flatten(record["output"])) for record in usable]
    lengths.sort()
    leaf_counts.sort()
    output_types = Counter(type(record["output"]).__name__ for record in usable)
    top_keys = Counter()
    output_paths: Counter[str] = Counter()
    for record in usable:
        value = record["output"]
        if isinstance(value, dict):
            top_keys.update(value.keys())
        output_paths.update(field_paths(value))

    lines = [
        "# 可用 Final Output 指标报告",
        "",
        f"> 生成时间：{datetime.now(timezone.utc).isoformat()}（UTC）",
        f"> 数据根目录：`{root}`",
        "> 本报告只统计最终 output 可恢复且可用于答案分析的记录，不展开原始日志、trace、答案集或 provider 请求细节。",
        "",
        "## 1. 可用数据筛选口径",
        "",
        "保留条件：最终 output 能被解析为有内容的 JSON/对象，并且不是超时、403/Forbidden、provider/API 错误或 policy violation。原始结果发生过格式错误、但格式恢复后拿到完整 output 的记录保留，并单独计为“格式恢复后可用”。",
        "",
        md_table(["筛选类别", "记录数", "占全部"], [
            ["全部记录", total, "100%"],
            ["保留：可用 final output", len(usable), pct(len(usable), total)],
            ["其中：原始格式干净", clean, pct(clean, len(usable))],
            ["其中：格式恢复后可用", recovered, pct(recovered, len(usable))],
            ["排除：403/Forbidden", exclusion_counts["403_or_forbidden"], pct(exclusion_counts["403_or_forbidden"], total)],
            ["排除：超时", exclusion_counts["timeout"], pct(exclusion_counts["timeout"], total)],
            ["排除：provider/API 错误", exclusion_counts["provider_error"], pct(exclusion_counts["provider_error"], total)],
            ["排除：policy violation", exclusion_counts["policy_violation"], pct(exclusion_counts["policy_violation"], total)],
            ["排除：格式/schema 错误且无可用 output", exclusion_counts["unusable_format_or_schema"], pct(exclusion_counts["unusable_format_or_schema"], total)],
            ["排除：无 output 或其他错误", exclusion_counts["no_output_or_other_error"], pct(exclusion_counts["no_output_or_other_error"], total)],
        ]),
        "",
        f"补入旧索引的直接 run：{unindexed_runs} 个；总记录数保持为 {total:,}。",
        "",
        "## 2. 最终 Output 核心指标",
        "",
        md_table(["指标", "数值", "说明"], [
            ["可用 final output", f"{len(usable):,}", "通过筛选的数据"],
            ["语义正确", f"{correct:,}", "按答案值/表达式比较"],
            ["语义错误", f"{wrong:,}", "有 output 但答案值不匹配"],
            ["可判定 output 正确率", pct(correct, judged), f"{correct:,}/{judged:,}"],
            ["全量任务覆盖率", pct(len(usable), total), f"{len(usable):,}/{total:,}"],
            ["严格 evaluator 正确", f"{strict_correct:,}", "selected validation.answer_correct=True"],
            ["格式恢复后可用占比", pct(recovered, len(usable)), f"{recovered:,}/{len(usable):,}"],
            ["output JSON 长度中位数", lengths[len(lengths) // 2] if lengths else 0, "字符数"],
            ["output JSON 长度 P95", lengths[int(len(lengths) * 0.95)] if lengths else 0, "字符数"],
            ["output JSON 最大长度", max(lengths) if lengths else 0, "字符数"],
            ["output 标量叶节点中位数", leaf_counts[len(leaf_counts) // 2] if leaf_counts else 0, "递归展开后的标量数量"],
        ]),
        "",
        "## 3. 可用 Output 按 provider / mode / 难度",
        "",
        md_table(["scope", "provider", "mode", "难度", "全部 N", "可用 N", "覆盖率", "正确", "错误", "可判定正确率", "格式恢复"], [
            [g.get("scope"), g.get("provider_group"), g.get("mode"), g.get("difficulty_level"), g["all"], g["usable"], pct(g["usable"], g["all"]), g["correct"], g["wrong"], pct(g["correct"], g["judged"]), g["recovered"]]
            for g in group_stat(records, ("scope", "provider_group", "mode", "difficulty_level"))
        ]),
        "",
        "## 4. 可用 Output 按模型",
        "",
        md_table(["scope", "provider", "model", "全部 N", "可用 N", "覆盖率", "正确", "错误", "可判定正确率", "严格正确", "格式恢复"], [
            [g.get("scope"), g.get("provider_group"), g.get("model_id"), g["all"], g["usable"], pct(g["usable"], g["all"]), g["correct"], g["wrong"], pct(g["correct"], g["judged"]), g["strict_correct"], g["recovered"]]
            for g in group_stat(records, ("scope", "provider_group", "model_id"))
        ]),
        "",
        "## 5. 可用 Output 的结构指标",
        "",
        md_table(["output 顶层类型", "数量", "占可用 output"], [[kind, count, pct(count, len(usable))] for kind, count in output_types.most_common()]),
        "",
        "最常见顶层字段：",
        "",
        md_table(["字段", "出现次数", "占可用 output"], [[key, count, pct(count, len(usable))] for key, count in top_keys.most_common(30)]),
        "",
        "最常见递归字段路径（最多三十项）：",
        "",
        md_table(["字段路径", "出现次数"], [[key, count] for key, count in output_paths.most_common(30)]),
        "",
        "## 6. 结论",
        "",
        f"本报告将 {total:,} 条原始记录过滤为 {len(usable):,} 条可用于最终 output 分析的数据；超时、403/Forbidden、provider/API 错误、policy violation 以及没有可恢复 output 的格式错误均未进入正确率分母。可用数据的最终 output 语义正确率为 {pct(correct, judged)}，覆盖率为 {pct(len(usable), total)}。",
        "",
        "格式恢复后仍能拿到完整 output 的记录被保留，但在表格中单列为“格式恢复”，建议在正式统计时同时报告原始干净子集与恢复后扩展子集。",
        "",
        "## 7. 可用记录索引",
        "",
        "下面只列出保留记录的定位信息，不复制完整 output；完整 output 仍位于原总档案的对应记录文件中。",
        "",
        md_table(["provider", "mode", "难度", "model", "task", "run", "来源", "正确性", "结果文件"], [
            [record["provider_group"], record["mode"], record["difficulty_label"], record["model_id"], record["task_id"], record["benchmark_run_id"], record["final_source"], "正确" if record["semantic_correct"] is True else "错误" if record["semantic_correct"] is False else "未判定", record["selected_result_path"]]
            for record in usable
        ]),
        "",
        "---",
        f"报告生成完成：{datetime.now(timezone.utc).isoformat()}（UTC）。",
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.benchmark_root.resolve()
    records, total, unindexed_runs = build_records(root)
    render(root, args.output.resolve(), records, total, unindexed_runs)
    usable = sum(record["usable"] for record in records)
    correct = sum(record["semantic_correct"] is True for record in records if record["usable"])
    wrong = sum(record["semantic_correct"] is False for record in records if record["usable"])
    print(json.dumps({"output": str(args.output.resolve()), "total": total, "usable": usable, "correct": correct, "wrong": wrong, "judged_accuracy_pct": round(100 * correct / (correct + wrong), 4) if correct + wrong else None}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
