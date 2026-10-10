#!/usr/bin/env python3
"""Build a local, full input/output Markdown dossier for recovered runs.

The dossier is intentionally written outside the repository.  It expands the
canonical result records and the selected final output, but never copies
provider traces, logs, credentials, or the answer key into the repository.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
LEVELS = {"easy": 1, "mid": 2, "diff": 3}
SENSITIVE_KEY = re.compile(r"(?:api[_-]?key|access[_-]?token|refresh[_-]?token|secret|password|authorization|credential)", re.I)
SECRET_TEXT = re.compile(r"(?i)(?:sk-[a-z0-9_-]{20,}|bearer\s+[a-z0-9._~+/=-]{16,})")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def text(value: Any) -> str:
    return str(value or "")


def redact(value: Any, key: str = "") -> Any:
    """Keep the dossier useful while preventing accidental credential export."""
    if SENSITIVE_KEY.search(key):
        return "<redacted>"
    if isinstance(value, dict):
        return {str(k): redact(v, str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(item, key) for item in value]
    if isinstance(value, str):
        return SECRET_TEXT.sub("<redacted-secret>", value)
    return value


def json_text(value: Any) -> str:
    return json.dumps(redact(value), ensure_ascii=False, indent=2, sort_keys=False)


def relative_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def recovery_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return tuple(
        row.get(key)
        for key in (
            "scope",
            "provider_group",
            "mode",
            "difficulty_level",
            "benchmark_run_id",
            "model_id",
            "task_id",
        )
    )


def canonical_paths(root: Path) -> list[Path]:
    """Enumerate only direct level/run/models/model/result.json files."""
    paths: list[Path] = []
    for top in ("pure_llm", "agent"):
        base = root / top
        if not base.exists():
            continue
        for provider_dir in sorted(path for path in base.iterdir() if path.is_dir()):
            for level_name in LEVELS:
                level_dir = provider_dir / level_name
                if not level_dir.exists():
                    continue
                for run_dir in sorted(path for path in level_dir.glob("run-*") if path.is_dir()):
                    paths.extend(sorted((run_dir / "models").glob("*/*.json")))
    return paths


def result_row_for_unindexed(path: Path, root: Path, result: dict[str, Any]) -> dict[str, Any]:
    top = "agent" if "agent" in path.parts else "pure_llm"
    # The direct layout is <top>/<provider>/<level>/<run>/models/<model>/<file>.
    top_index = path.parts.index(top)
    provider_dir = path.parts[top_index + 1]
    level_name = path.parts[top_index + 2]
    run_dir = path.parents[3]
    return {
        "scope": "unlimited" if provider_dir.endswith("_without_lim") else "limited_or_legacy",
        "provider_group": provider_dir.removesuffix("_without_lim"),
        "mode": "G4" if top == "agent" else "G1",
        "difficulty_level": LEVELS[level_name],
        "difficulty_label": level_name,
        "benchmark_run_id": run_dir.name,
        "run_dir": str(run_dir),
        "model_id": text(result.get("model_id")) or path.parent.name,
        "task_id": text(result.get("task_id")) or path.stem,
        "raw_result_path": str(path),
        "selected_result_path": str(path),
        "selected_source": "raw",
        "raw_classification": "unindexed_raw",
        "selected_classification": "unindexed_raw",
        "raw_status": result.get("status"),
        "selected_status": result.get("status"),
        "raw_validation_status": (result.get("validation") or {}).get("status"),
        "selected_validation_status": (result.get("validation") or {}).get("status"),
        "raw_protocol_valid": result.get("protocol_valid"),
        "selected_protocol_valid": result.get("protocol_valid"),
        "selected_answer_correct": (result.get("validation") or {}).get("answer_correct"),
    }


def load_rows(root: Path) -> tuple[list[dict[str, Any]], dict[tuple[Any, ...], str], int]:
    organized = root / "organized"
    index_path = organized / "results_index.jsonl"
    rows = [json.loads(line) for line in index_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    recovery_paths: dict[tuple[Any, ...], str] = {}
    recovery_index = organized / "format_failures" / "format_recovery_results.jsonl"
    if recovery_index.exists():
        for line in recovery_index.read_text(encoding="utf-8").splitlines():
            if line.strip():
                recovery = json.loads(line)
                recovery_paths[recovery_key(recovery)] = text(recovery.get("format_recovery_result_path"))

    indexed_paths = {Path(row["raw_result_path"]).resolve() for row in rows if row.get("raw_result_path")}
    unindexed_run_dirs: set[Path] = set()
    for path in canonical_paths(root):
        if path.resolve() in indexed_paths:
            continue
        result = load_json(path)
        rows.append(result_row_for_unindexed(path, root, result))
        unindexed_run_dirs.add(path.parents[3].resolve())
    rows.sort(
        key=lambda row: (
            text(row.get("scope")),
            text(row.get("provider_group")),
            text(row.get("mode")),
            text(row.get("difficulty_level")),
            text(row.get("model_id")),
            text(row.get("task_id")),
            text(row.get("raw_result_path")),
        )
    )
    return rows, recovery_paths, len(unindexed_run_dirs)


def field_profiles(values: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    types: dict[str, Counter[str]] = defaultdict(Counter)
    examples: dict[str, Any] = {}
    for value in values:
        for key, item in value.items():
            counts[key] += 1
            types[key][type(item).__name__] += 1
            examples.setdefault(key, item)
    return [
        {
            "field": key,
            "records": counts[key],
            "types": ", ".join(f"{name}:{amount}" for name, amount in sorted(types[key].items())),
            "example": examples[key],
        }
        for key in sorted(counts)
    ]


def nested_field_profiles(values: Iterable[Any], prefix: str = "", depth: int = 0) -> Counter[str]:
    counts: Counter[str] = Counter()
    for value in values:
        if isinstance(value, dict):
            for key, child in value.items():
                path = f"{prefix}.{key}" if prefix else str(key)
                counts[path] += 1
                if depth < 2:
                    counts.update(nested_field_profiles([child], path, depth + 1))
        elif isinstance(value, list) and depth < 2:
            for child in value[:20]:
                counts.update(nested_field_profiles([child], prefix + "[]", depth + 1))
    return counts


def markdown_table(headers: list[str], rows: Iterable[Iterable[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        cells = []
        for value in row:
            cell = str(value).replace("|", "\\|").replace("\n", "<br>")
            cells.append(cell)
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def pct(numerator: int, denominator: int) -> str:
    return f"{100.0 * numerator / denominator:.2f}%" if denominator else "NA"


def group_counts(records: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, ...], Counter[str]] = defaultdict(Counter)
    for record in records:
        group = groups[tuple(record.get(key) for key in keys)]
        group["records"] += 1
        group["output_correct"] += int(record["semantic_correct"] is True)
        group["output_wrong"] += int(record["semantic_correct"] is False)
        group["no_output"] += int(record["semantic_correct"] is None)
        group["strict_correct"] += int(record["strict_correct"])
        group["recovery"] += int(record["final_source"] == "format_recovery")
    result = []
    for key, counts in sorted(groups.items(), key=lambda pair: tuple(text(v) for v in pair[0])):
        item = dict(zip(keys, key))
        item.update(counts)
        item["judged"] = counts["output_correct"] + counts["output_wrong"]
        result.append(item)
    return result


def file_inventory(root: Path) -> list[dict[str, Any]]:
    counts: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        top = path.relative_to(root).parts[0]
        extension = path.suffix.lower() or "<none>"
        counts[(top, extension)][0] += 1
        counts[(top, extension)][1] += path.stat().st_size
    return [
        {"top": key[0], "extension": key[1], "files": value[0], "bytes": value[1]}
        for key, value in sorted(counts.items())
    ]


def build_records(root: Path, rows: list[dict[str, Any]], recovery_paths: dict[tuple[Any, ...], str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    # Imported from the existing audited output-focused scorer.
    sys.path.insert(0, str(REPO_ROOT))
    from scripts.analyze_recovered_final_output import _recover_final_output, _semantic_correct

    answer_key_path = REPO_ROOT / "data" / "theory_benchmark_v2" / "answer_key.json"
    answers = {row["task_id"]: row for row in load_json(answer_key_path)} if answer_key_path.exists() else {}
    task_variants: dict[tuple[str, str], dict[str, Any]] = {}
    records: list[dict[str, Any]] = []
    for ordinal, row in enumerate(rows, 1):
        raw_path = Path(row["raw_result_path"])
        raw = load_json(raw_path) if raw_path.exists() else {}
        key = recovery_key(row)
        recovery_path = Path(recovery_paths[key]) if recovery_paths.get(key) else None
        selected_path = recovery_path if recovery_path and recovery_path.exists() else Path(row.get("selected_result_path") or raw_path)
        selected = load_json(selected_path) if selected_path.exists() else raw
        task = raw.get("task") if isinstance(raw.get("task"), dict) else selected.get("task", {})
        task = redact(task)
        task_id = text(row.get("task_id") or task.get("task_id"))
        task_hash = hashlib.sha256(json.dumps(task, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:12]
        task_variants.setdefault((task_id, task_hash), task)
        actual, extraction = _recover_final_output(selected)
        semantic_correct = None
        if actual is not None and task_id in answers:
            semantic_correct = _semantic_correct(task_id, actual, answers)
        answer = selected.get("answer") if isinstance(selected, dict) else None
        error_summary = ""
        if isinstance(answer, dict) and answer.get("error"):
            error_summary = SECRET_TEXT.sub("<redacted-secret>", text(answer.get("error")))[:500]
        records.append(
            {
                "ordinal": ordinal,
                "scope": row.get("scope"),
                "provider_group": row.get("provider_group"),
                "mode": row.get("mode"),
                "difficulty_level": row.get("difficulty_level"),
                "difficulty_label": row.get("difficulty_label"),
                "benchmark_run_id": row.get("benchmark_run_id"),
                "model_id": row.get("model_id"),
                "task_id": task_id,
                "task_hash": task_hash,
                "raw_result_path": relative_path(raw_path, root),
                "selected_result_path": relative_path(selected_path, root),
                "final_source": "format_recovery" if recovery_path and recovery_path.exists() else "raw",
                "extraction": extraction,
                "selected_status": selected.get("status"),
                "selected_validation_status": (selected.get("validation") or {}).get("status"),
                "selected_protocol_valid": selected.get("protocol_valid"),
                "selected_classification": row.get("selected_classification", "unindexed_raw"),
                "strict_correct": bool((selected.get("validation") or {}).get("answer_correct") is True),
                "semantic_correct": semantic_correct,
                "error_summary": error_summary,
                "output": redact(actual) if actual is not None else None,
            }
        )
    return records, [{"task_id": task_id, "task_hash": task_hash, "task": task} for (task_id, task_hash), task in sorted(task_variants.items())]


def render_report(root: Path, output_path: Path, rows: list[dict[str, Any]], records: list[dict[str, Any]], tasks: list[dict[str, Any]], recovery_paths: dict[tuple[Any, ...], str], unindexed_run_count: int) -> None:
    files = file_inventory(root)
    task_profiles = field_profiles(task["task"] for task in tasks)
    output_values = [record["output"] for record in records if record["output"] is not None]
    output_paths = nested_field_profiles(output_values)
    overall = Counter()
    for record in records:
        overall["records"] += 1
        overall["output_correct"] += int(record["semantic_correct"] is True)
        overall["output_wrong"] += int(record["semantic_correct"] is False)
        overall["no_output"] += int(record["semantic_correct"] is None)
        overall["strict_correct"] += int(record["strict_correct"])
        overall["recovery"] += int(record["final_source"] == "format_recovery")
    judged = overall["output_correct"] + overall["output_wrong"]
    run_ids = {(r.get("scope"), r.get("provider_group"), r.get("mode"), r.get("benchmark_run_id")) for r in rows}

    lines: list[str] = []
    lines += [
        "# Benchmark 全量 Input / Output 数据总档案",
        "",
        f"> 生成时间：{datetime.now(timezone.utc).isoformat()}（UTC）",
        f"> 数据根目录：`{root}`",
        "> 本文档只写在 benchmark 同级目录，不会复制到 Git 仓库；API key、token、provider trace、日志和答案集不展开写入。",
        "",
        "## 1. 阅读范围与口径",
        "",
        "本文档逐条遍历了 `benchmark/agent`、`benchmark/pure_llm` 以及 `benchmark/organized` 的索引和恢复索引。实验样本按直接 `level/run-*/models/*/*.json` 的 canonical result 计数；格式恢复目录中的结果只作为对应原始记录的最终 output 候选，不另算一个样本。",
        "",
        markdown_table(
            ["项目", "数量", "说明"],
            [
                ["canonical result records", f"{overall['records']:,}", "每个直接实验记录一行"],
                ["直接 run 目录", f"{len(run_ids):,}", "scope/provider/mode/run_id 去重"],
                ["唯一 task 定义变体", f"{len(tasks):,}", "按 task_id + task 内容 hash 去重"],
                ["格式恢复选择次数", f"{overall['recovery']:,}", "有恢复结果时优先用恢复后的最终 output"],
                ["未被旧索引覆盖的 run", f"{unindexed_run_count:,}", "直接扫描补入，不改变原始文件"],
            ],
        ),
        "",
        "## 2. 结果总览",
        "",
        markdown_table(
            ["指标", "数量", "比例"],
            [
                ["全部记录", f"{overall['records']:,}", "100%"],
                ["最终 output 语义正确", f"{overall['output_correct']:,}", pct(overall['output_correct'], overall['records'])],
                ["最终 output 语义错误", f"{overall['output_wrong']:,}", pct(overall['output_wrong'], overall['records'])],
                ["无可恢复最终 output", f"{overall['no_output']:,}", pct(overall['no_output'], overall['records'])],
                ["output 正确率（有 output 的记录）", f"{overall['output_correct']:,}/{judged:,}", pct(overall['output_correct'], judged)],
                ["原/恢复结果中的严格 evaluator 正确", f"{overall['strict_correct']:,}", pct(overall['strict_correct'], overall['records'])],
            ],
        ),
        "",
        "> `最终 output 语义正确`使用现有 output-focused 比较器，只比较最终答案中的标量值，忽略字段名和外层 JSON schema；它适合回答“答案本身对不对”，不是正式 protocol 合规率。`无 output`不计入有 output 的分母。",
        "",
        "## 3. 文件层级清单",
        "",
        markdown_table(["顶层目录", "扩展名", "文件数", "字节数"], [[x["top"], x["extension"], f"{x['files']:,}", f"{x['bytes']:,}"] for x in files]),
        "",
        "## 4. Dataset Input：任务输入字段",
        "",
        "模型收到的核心 dataset input 位于每条 result 的 `task` 对象中；同一 task 会被多个 provider、mode、model 重复使用，本文档在任务目录中完整展开一次，在逐条记录中通过 `task_id` 和 `task_hash` 引用。",
        "",
        markdown_table(["Input 字段", "出现记录数", "观测类型", "示例"], [[p["field"], p["records"], p["types"], json.dumps(redact(p["example"]), ensure_ascii=False)[:180]] for p in task_profiles]),
        "",
        "### 4.1 唯一任务输入目录",
        "",
        markdown_table(["task_id", "难度", "领域", "子领域", "理论/主题", "模型", "任务输入摘要"], [
            [t["task"].get("task_id", t["task_id"]), t["task"].get("difficulty_level", ""), t["task"].get("domain", ""), t["task"].get("subdomain", ""), t["task"].get("theory_name", ""), t["task"].get("mathematical_model", ""), text(t["task"].get("problem_statement", "")).replace("\n", " ")[:180]] for t in tasks
        ]),
        "",
        "### 4.2 每个 task 的完整 input JSON",
        "",
    ]
    for task in tasks:
        title = f"{task['task_id']} / variant {task['task_hash']}"
        lines += [f"<details><summary>{title}</summary>", "", "```json", json_text(task["task"]), "```", "", "</details>", ""]

    lines += [
        "## 5. Model Output：输出字段与提取规则",
        "",
        "每条记录的 `output` 是最终可恢复答案：优先使用格式恢复结果中的最终答案；否则使用原始 result 中存储的 `answer.final_answer`，再否则从最后一次 provider response 中解析 JSON 对象。没有任何可恢复内容的记录标为 `NO_OUTPUT`，不把日志或 error message 冒充答案。",
        "",
        markdown_table(["Output 字段路径（最多展开 3 层）", "出现次数"], [[path, count] for path, count in output_paths.most_common()]),
        "",
        "## 6. 按实验组的 output 汇总",
        "",
        markdown_table(["scope", "provider", "mode", "difficulty", "N", "正确", "错误", "无 output", "有 output 正确率", "恢复"], [
            [g.get("scope"), g.get("provider_group"), g.get("mode"), g.get("difficulty_level"), g["records"], g["output_correct"], g["output_wrong"], g["no_output"], pct(g["output_correct"], g["judged"]), g["recovery"]]
            for g in group_counts(records, ("scope", "provider_group", "mode", "difficulty_level"))
        ]),
        "",
        "## 7. 按模型的 output 汇总",
        "",
        markdown_table(["scope", "provider", "model", "N", "正确", "错误", "无 output", "全任务正确率", "有 output 正确率", "严格正确", "恢复"], [
            [g.get("scope"), g.get("provider_group"), g.get("model_id"), g["records"], g["output_correct"], g["output_wrong"], g["no_output"], pct(g["output_correct"], g["records"]), pct(g["output_correct"], g["judged"]), g["strict_correct"], g["recovery"]]
            for g in group_counts(records, ("scope", "provider_group", "model_id"))
        ]),
        "",
        "## 8. 全量逐条 Input / Output 记录",
        "",
        "下面每个条目对应一个 canonical experiment result。Input 通过 `task_id/task_hash` 指向第 4 节，Output 是该条记录最后可恢复的答案；原始结果和所选结果路径保留，便于回到数据目录复核。",
        "",
    ]
    current_group: tuple[Any, ...] | None = None
    for record in records:
        group = (record["scope"], record["provider_group"], record["mode"], record["difficulty_label"])
        if group != current_group:
            current_group = group
            lines += [f"### {group[0]} / {group[1]} / {group[2]} / {group[3]}", ""]
        lines += [
            f"#### {record['ordinal']:05d}. `{record['task_id']}` — `{record['model_id']}`",
            "",
            markdown_table(
                ["字段", "值"],
                [
                    ["输入 task", f"`{record['task_id']}` / variant `{record['task_hash']}`"],
                    ["run", record["benchmark_run_id"]],
                    ["来源", record["final_source"]],
                    ["提取方式", record["extraction"]],
                    ["状态", record["selected_status"]],
                    ["validation", record["selected_validation_status"]],
                    ["protocol_valid", record["selected_protocol_valid"]],
                    ["语义判定", "正确" if record["semantic_correct"] is True else "错误" if record["semantic_correct"] is False else "无 output/不可判定"],
                    ["原始文件", f"`{record['raw_result_path']}`"],
                    ["最终文件", f"`{record['selected_result_path']}`"],
                ],
            ),
            "",
        ]
        if record["output"] is None:
            lines += ["```text", "NO_OUTPUT", record["error_summary"] or "没有可恢复的最终 output。", "```", ""]
        else:
            output_json = json_text(record["output"])
            fence = "````" if "```" in output_json else "```"
            lines += [f"{fence}json", output_json, fence, ""]
        lines += ["---", ""]

    lines += [
        "## 9. 解释与限制",
        "",
        "- 这里的逐条输出是最终答案视图，不含完整 provider trace、token 统计、请求 header 或日志；这些仍留在原始数据目录。",
        "- 同一 task 在不同模型/组别下重复出现是实验设计，不是数据重复错误；重复记录按 run、model、mode 保留。",
        "- `无 output`、provider error、JSON 解析失败和 schema 不匹配不会被强行改成错误答案；它们在本文档中明确标为无 output，并保留结果路径。",
        "- 语义正确率依赖本地答案集只做统计，不在本文档输出答案集内容；字段名不匹配不单独决定答案是否正确。",
        "",
        "---",
        f"报告生成完成：{datetime.now(timezone.utc).isoformat()}（UTC）。",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.benchmark_root.resolve()
    output = (args.output or (root.parent / "FULL_INPUT_OUTPUT_DATA_DOSSIER.md")).resolve()
    rows, recovery_paths, unindexed_run_count = load_rows(root)
    records, tasks = build_records(root, rows, recovery_paths)
    render_report(root, output, rows, records, tasks, recovery_paths, unindexed_run_count)
    print(json.dumps({"output": str(output), "records": len(records), "tasks": len(tasks), "recovery_selected": sum(r["final_source"] == "format_recovery" for r in records), "bytes": output.stat().st_size}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
