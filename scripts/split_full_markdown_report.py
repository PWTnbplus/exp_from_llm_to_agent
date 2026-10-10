#!/usr/bin/env python3
"""Split the full local benchmark dossier into small, linked Markdown files."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


RECORD_RE = re.compile(r"(?ms)^#### \d{5}\. .*?(?=^#### \d{5}\. |\Z)")
DETAIL_RE = re.compile(r"(?s)<details><summary>.*?</details>")


def write(path: Path, content: str) -> None:
    path.write_text(content.rstrip() + "\n", encoding="utf-8", newline="\n")


def split_fixed(items: list[str], size: int) -> list[list[str]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def split_report(report: Path, output_dir: Path) -> dict[str, int | str]:
    if not report.is_file():
        raise FileNotFoundError(report)
    if output_dir.exists() and not output_dir.is_dir():
        raise NotADirectoryError(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    text = report.read_text(encoding="utf-8")
    section4 = text.index("## 4. Dataset Input")
    section5 = text.index("## 5. Model Output")
    section8 = text.index("## 8. 全量逐条 Input / Output 记录")
    section9 = text.index("## 9. 解释与限制")

    overview_name = "01_OVERVIEW.md"
    input_schema_name = "02_INPUT_SCHEMA_AND_SUMMARY.md"
    output_summary_name = "04_OUTPUT_SUMMARY.md"
    write(output_dir / overview_name, text[:section4])
    write(
        output_dir / input_schema_name,
        "# Dataset Input 字段与任务汇总\n\n" + text[section4: text.index("### 4.2 每个 task 的完整 input JSON")],
    )
    write(
        output_dir / output_summary_name,
        "# Output 汇总、统计与限制\n\n" + text[section5:section8] + "\n" + text[section9:],
    )

    input_section = text[section4:section5]
    input_details = DETAIL_RE.findall(input_section)
    input_parts: list[str] = []
    for part_number, group in enumerate(split_fixed(input_details, 25), 1):
        name = f"03_INPUT_TASKS_{part_number:03d}.md"
        write(
            output_dir / name,
            "# Dataset Input 任务详情\n\n"
            f"> 本文件包含第 {part_number} 组 task input，共 {len(group)} 个。\n\n"
            + "\n\n".join(group),
        )
        input_parts.append(name)

    records_section = text[section8:section9]
    record_matches = list(RECORD_RE.finditer(records_section))
    record_blocks = [match.group(0).strip() for match in record_matches]
    output_parts: list[str] = []
    for part_number, group in enumerate(split_fixed(record_blocks, 100), 1):
        body: list[str] = [
            "# 全量 Output 记录",
            "",
            f"> 本文件包含第 {part_number} 组 output 记录，共 {len(group)} 条。",
            "",
        ]
        for block in group:
            body.extend([block, "", "---", ""])
        name = f"05_OUTPUT_RECORDS_{part_number:03d}.md"
        write(output_dir / name, "\n".join(body))
        output_parts.append(name)

    index_lines = [
        "# Benchmark 全量 Input / Output 拆分索引",
        "",
        f"> 原始总报告：`{report}`",
        "> 本目录中的文件均为原报告的结构化拆分版本；先打开本索引，再按需要查看对应部分。",
        "",
        "## 文件说明",
        "",
        f"- [总览与数据范围]({overview_name})",
        f"- [Input 字段与任务汇总]({input_schema_name})",
        f"- [Output 汇总、统计与限制]({output_summary_name})",
        f"- Input 任务详情：{len(input_parts)} 个文件，每个约 25 个 task",
    ]
    index_lines.extend(f"  - [{name}]({name})" for name in input_parts)
    index_lines.extend([
        f"- Output 逐条记录：{len(output_parts)} 个文件，每个约 100 条记录",
    ])
    index_lines.extend(f"  - [{name}]({name})" for name in output_parts)
    index_lines.extend([
        "",
        "## 拆分校验",
        "",
        f"- Input task blocks：{len(input_details)}",
        f"- Output record blocks：{len(record_blocks)}",
        f"- Output 文件数：{len(output_parts)}",
        "- 每个 output 文件均在记录边界切分，没有按字节截断 JSON 或 Markdown。",
    ])
    write(output_dir / "00_INDEX.md", "\n".join(index_lines))
    return {
        "output_dir": str(output_dir),
        "input_tasks": len(input_details),
        "input_parts": len(input_parts),
        "output_records": len(record_blocks),
        "output_parts": len(output_parts),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = split_report(args.report.resolve(), args.output_dir.resolve())
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
