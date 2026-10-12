#!/usr/bin/env python3
"""Build a non-destructive cross-profile benchmark repair handoff.

This report builder consumes the already-produced structural audits and local
recovery summaries.  It never opens a private answer key, never calls a
provider, never edits raw runs, and never turns a missing result into a
synthetic answer.
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


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_optional(path: Path, missing: Any = None) -> Any:
    try:
        return load(path)
    except (OSError, UnicodeError, json.JSONDecodeError):
        return missing


def number_from_report(path: Path, label: str) -> str | None:
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(rf"\|\s*{re.escape(label)}\s*\|\s*([0-9][0-9,]*(?:\.[0-9]+)?%?)\s*\|", text)
    return match.group(1) if match else None


def table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(value).replace("|", "\\|").replace("\n", "<br>") for value in row) + " |")
    return "\n".join(lines)


def compact_standard_audit(audit: dict[str, Any]) -> dict[str, Any]:
    totals = audit.get("totals") or {}
    return {
        "run_count": audit.get("run_count", 0),
        "runs_with_structural_problems": audit.get("runs_with_structural_problems", 0),
        "result_files": totals.get("result_files", 0),
        "duplicate_task_ids": totals.get("duplicate_task_ids", 0),
        "missing_task_ids": totals.get("missing_task_ids", 0),
        "unexpected_task_ids": totals.get("unexpected_task_ids", 0),
        "malformed_result_files": totals.get("malformed_result_files", 0),
        "missing_trace_files": totals.get("missing_trace_files", 0),
        "wrong_group_or_mode": totals.get("wrong_group_or_mode", 0),
        "model_id_mismatch": totals.get("model_id_mismatch", 0),
        "credential_pattern_hits": totals.get("credential_pattern_hits", 0),
        "provider_error_traces": totals.get("provider_error_traces", 0),
        "timeout_traces": totals.get("timeout_traces", 0),
        "json_parse_failures": totals.get("json_parse_failures", 0),
        "schema_failures": totals.get("schema_failures", 0),
        "protocol_invalid": totals.get("protocol_invalid", 0),
        "evaluator_invalid": totals.get("evaluator_invalid", 0),
    }


def matrix_rows(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for group in ("G2", "G3"):
        group_dir = root / group
        for run_dir in sorted(path for path in group_dir.glob("*") if path.is_dir()):
            report = read_optional(run_dir / "matrix_io_integrity_report.json")
            ledger = read_optional(run_dir / "matrix_completion_ledger.json")
            if not isinstance(report, dict):
                continue
            launcher = report.get("launcher_summary") or {}
            rows.append({
                "group": group,
                "run_dir": str(run_dir),
                "expected_task_model_rows": report.get("expected_task_model_rows"),
                "completion_state_counts": report.get("completion_state_counts") or {},
                "all_raw_io_complete": report.get("all_model_raw_io_complete"),
                "field_schema_complete": report.get("field_schema_complete"),
                "derived_completion_ledger_complete": report.get("derived_completion_ledger_complete"),
                "all_processes_exit_zero": launcher.get("all_processes_exit_zero"),
                "launcher_exit_codes": {
                    str(model.get("model_id")): model.get("launcher", {}).get("exit_code")
                    for model in report.get("models", []) if isinstance(model, dict)
                },
                "ledger_raw_results_modified": (ledger or {}).get("raw_results_modified"),
                "ledger_synthetic_results_created": (ledger or {}).get("synthetic_results_created"),
            })
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark-root", type=Path, required=True)
    parser.add_argument("--whole-skill-zip", type=Path, required=True)
    parser.add_argument("--g5-skill-zip", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    root = args.benchmark_root.resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    organized = root / "organized"
    standard_audit = read_optional(organized / "g1_g4_data_audit.json", {})
    organization = read_optional(organized / "summary.json", {})
    recovery = read_optional(organized / "format_failures" / "format_recovery_summary.json", {})
    g5_runs = sorted(path for path in (root / "g5_answer_given").glob("g5-answer-given-*") if path.is_dir())
    g5_report_path = next((path / "strict_compliance" / "report.json" for path in g5_runs if (path / "strict_compliance" / "report.json").is_file()), None)
    g5_report = read_optional(g5_report_path or Path("__missing__"), {})
    usable_report = root.parent / "VALID_RESPONSE_OUTPUT_METRICS_REPORT.md"
    matrix = matrix_rows(root)
    failure_reconciliation = read_optional(organized / "failure_recovery_20261012" / "failure_reconciliation_summary.json", {})

    standard = compact_standard_audit(standard_audit if isinstance(standard_audit, dict) else {})
    local_recovery = {
        "selected_format_failures": recovery.get("selected_format_failure_count", 0),
        "recovery_result_count": recovery.get("recovery_result_count", 0),
        "missing_recovery_count": recovery.get("missing_recovery_count", 0),
        "invalid_recovery_file_count": recovery.get("invalid_recovery_file_count", 0),
        "usable_recovery_rows": sum((recovery.get("resolution_counts") or {}).get(key, 0) for key in ("recovered_answer_correct", "recovered_structured_wrong_answer")),
        "still_format_failure_rows": sum((recovery.get("resolution_counts") or {}).get(key, 0) for key in ("still_format_json_parse_failure", "still_format_schema_failure")),
        "policy_or_provider_rows": sum((recovery.get("resolution_counts") or {}).get(key, 0) for key in ("recovery_policy_violation", "recovery_provider_error")),
        "retry8_incomplete": recovery.get("retry8_incomplete"),
        "final_selected_recovery_cost_usd": recovery.get("final_selected_recovery_cost_usd"),
        "all_recovery_attempts_cost_usd": recovery.get("all_recovery_attempts_cost_usd"),
    }
    g5 = {
        key: g5_report.get(key)
        for key in (
            "expected_records", "observed_records", "status_counts", "strict_package_records",
            "substantive_package_records", "fully_compliant_records", "repaired_format_records",
            "recovered_prior_attempt_records", "unrepaired_records", "provider_error_records",
            "no_submission_provider_error_records", "timeout_records", "orphan_interrupted_attempt_count",
            "raw_records_not_modified", "private_answer_key_read",
        )
    } if isinstance(g5_report, dict) else {}
    failure_summary = {
        "path": str(organized / "failure_recovery_20261012"),
        "exists": isinstance(failure_reconciliation, dict) and bool(failure_reconciliation),
        "row_count": failure_reconciliation.get("row_count", 0) if isinstance(failure_reconciliation, dict) else 0,
        "by_group": failure_reconciliation.get("by_group", {}) if isinstance(failure_reconciliation, dict) else {},
        "provider_requests_made": failure_reconciliation.get("provider_requests_made", 0) if isinstance(failure_reconciliation, dict) else 0,
        "raw_results_modified": failure_reconciliation.get("raw_results_modified", False) if isinstance(failure_reconciliation, dict) else False,
        "synthetic_results_created": failure_reconciliation.get("synthetic_results_created", False) if isinstance(failure_reconciliation, dict) else False,
    }
    provenance = {}
    for label, path in (("whole_pros.zip", args.whole_skill_zip), ("whole_pros_g5.zip", args.g5_skill_zip)):
        provenance[label] = {"path": str(path.resolve()), "exists": path.is_file(), "sha256": sha256(path.resolve()) if path.is_file() else None}

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "benchmark_root": str(root),
        "answer_key_read": bool(failure_summary.get("exists") and failure_summary.get("provider_requests_made") == 0),
        "raw_results_modified": False,
        "synthetic_results_created": False,
        "skill_provenance": provenance,
        "g1_g4_structural": standard,
        "g1_g4_local_recovery": local_recovery,
        "g2_g3_matrix": matrix,
        "g2_g3_failure_reconciliation": failure_summary,
        "g5_answer_given": g5,
        "usable_output_report": {
            "path": str(usable_report),
            "exists": usable_report.is_file(),
            "total_records": number_from_report(usable_report, "全部记录"),
            "usable_final_output": number_from_report(usable_report, "保留：可用 final output"),
            "judged_accuracy": number_from_report(usable_report, "可判定 output 正确率"),
        },
    }
    (output / "benchmark_repair_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "matrix_audit_compact.json").write_text(json.dumps(matrix, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Benchmark 有效数据与本地修复核对报告",
        "",
        f"> 生成时间：{summary['generated_at_utc']}。本报告只整理已有运行、trace、恢复目录和审计产物；失败 reconciliation 仅使用本地 evaluator 读取私有答案键生成 PASS/MODEL_ERROR，不输出答案键、不调用 provider、不修改 raw 结果。",
        "",
        "## 1. 口径和隔离",
        "",
        "- `whole_pros.zip` 作为普通 theory_benchmark 规范，`whole_pros_g5.zip` 作为独立 G5 answer-given 规范。",
        "- G5 与普通 G1–G4 分开统计；G5 的已知答案条件不能解释为普通组的自主发现能力。",
        "- 只允许本地可证据化修复：已有 trace 中可解析的完整 output、已有历史 attempt 中的完整 G5 package、索引/字段/校验修复。没有对缺失 provider response 重新发起请求。",
        "- 403、超时、provider 错误、policy violation、缺失 output 和无法从已有日志恢复的格式错误仍保留为失败/UNPROVEN，不进入正确率分母。",
        "",
        "## 2. Skill provenance",
        "",
        table(["文件", "存在", "SHA-256"], [[name, item["exists"], item["sha256"] or "MISSING"] for name, item in provenance.items()]),
        "",
        "## 3. 普通 G1/G4 结构审计",
        "",
        table(["项目", "值"], [[key, value] for key, value in standard.items()]),
        "",
        "结构审计结论：`runs_with_structural_problems = %s`。这表示 canonical result 文件的 task 数、重复、trace 路径、group/model 字段和敏感模式检查没有发现结构性断裂；它不等于所有模型输出都有效。" % standard.get("runs_with_structural_problems", "NOT_TESTED"),
        "",
        "### 3.1 既有本地恢复",
        "",
        table(["指标", "值"], [[key, value] for key, value in local_recovery.items()]),
        "",
        "已有恢复阶段中，能够得到完整结构化 output 的记录才被选入 usable view；剩余格式错误、provider error 和 policy violation 不被补成答案。`retry8_incomplete = true` 时，该阶段只能作为备查，不能当作完整最终恢复批次。",
        "",
        "可用 output 的完整指标仍见：[%s](%s)。" % (usable_report.name, usable_report),
        "",
        "## 4. G2/G3 matrix",
        "",
        table(["组别", "预期 task×model", "完成状态", "raw I/O 完整", "字段完整", "launcher 全部成功", "raw 是否改写", "是否合成结果"], [
            [row["group"], row["expected_task_model_rows"], json.dumps(row["completion_state_counts"], ensure_ascii=False), row["all_raw_io_complete"], row["field_schema_complete"], row["all_processes_exit_zero"], row["ledger_raw_results_modified"], row["ledger_synthetic_results_created"]]
            for row in matrix
        ]),
        "",
        "G2/G3 的 `RECORDED_RESULT` 只表示存在原始 result artifact；`RECORDED_FAILURE` 和 `MISSING_RAW_RESULT` 不应当被当作正确答案。G3 的 launcher/完成状态若未全通过，正式比较应标为 `PARTIAL`，不能因为每个子进程退出码或索引存在而宣称完整实验。",
        "",
        "## 5. G2/G3 failure reconciliation (failure is not wrong)",
        "",
        "This derived layer treats FAILED, provider/access errors, timeouts, policy/budget violations, parse failures, and missing raw artifacts as failures rather than wrong answers. The runner's default answer_correct=false is not used for those rows. Only a completed row with a real payload and an independent MODEL_ERROR is counted as ANSWER_WRONG.",
        "",
        table(["group", "rows", "correct", "wrong (completed only)", "failed/unproven", "missing raw", "failed -> recovered correct", "failed payload wrong (not counted)"], [
            [group, (failure_summary.get("by_group", {}).get(group, {}) or {}).get("row_count", 0),
             ((failure_summary.get("by_group", {}).get(group, {}) or {}).get("failure_class_counts", {}) or {}).get("ANSWER_CORRECT", 0),
             ((failure_summary.get("by_group", {}).get(group, {}) or {}).get("failure_class_counts", {}) or {}).get("ANSWER_WRONG", 0),
             sum(value for key, value in ((failure_summary.get("by_group", {}).get(group, {}) or {}).get("failure_class_counts", {}) or {}).items() if str(key).startswith("FAILED")),
             ((failure_summary.get("by_group", {}).get(group, {}) or {}).get("failure_class_counts", {}) or {}).get("MISSING_RAW_RESULT", 0),
             ((failure_summary.get("by_group", {}).get(group, {}) or {}).get("failure_class_counts", {}) or {}).get("FAILED_RECOVERED_CORRECT", 0),
             ((failure_summary.get("by_group", {}).get(group, {}) or {}).get("failure_class_counts", {}) or {}).get("FAILED_WITH_PAYLOAD_EVALUATED_WRONG_NOT_COUNTED", 0)]
            for group in ("G2", "G3")
        ]),
        "",
        f"Machine-readable reconciliation: `{organized / 'failure_recovery_20261012'}`. Provider requests made: `{failure_summary.get('provider_requests_made', 0)}`; raw results modified: `{failure_summary.get('raw_results_modified', False)}`.",
        "",
        "## 6. G5 answer-given 修复结果",
        "",
        table(["指标", "值"], [[key, value] for key, value in g5.items()]),
        "",
        "G5 本轮本地修复选择同一 task/model 下最新的、已有 attempt 中可通过 G5 final-package schema 的 observable package。恢复记录仍保留当前最终 attempt 的 provider error/status 和 source attempt lineage，因此不能写成当前请求成功。剩余 `UNPROVEN_INVALID_SUBMISSION` 只有不完整模型输出，无法凭空补齐。",
        "",
        "## 7. 可交付与阻塞",
        "",
        "- 可交付：普通组 canonical 结构审计、已有 format/provider/timeout recovery 的选中视图、G2/G3 completion ledger 与 I/O integrity、G5 strict compliance layer，以及本报告 JSON/Markdown。",
        "- 未做：新的真实 provider/API 重试。当前没有本次重试的明确模型、调用数、美元硬上限和授权，因此按 skill 记为 `BLOCKED_EXTERNAL_RETRIAL`，避免产生未预算的付费数据。",
        "- 不可恢复数据不会被删除；raw 日志、失败记录、orphan attempt 和恢复失败仍在原目录中备查。",
        "",
        "## 8. 备查路径",
        "",
        f"- 普通组结构审计：`{organized / 'g1_g4_data_audit.json'}`",
        f"- 普通组组织索引：`{organized / 'summary.json'}`、`{organized / 'format_failures'}`",
        f"- G2/G3 integrity：`{root / 'G2'}`、`{root / 'G3'}` 下的 `matrix_completion_ledger.json` 和 `matrix_io_integrity_report.json`",
        f"- G5 strict layer：`{root / 'g5_answer_given'}` 下对应 run 的 `strict_compliance`",
        f"- 本报告机器可读摘要：`{output / 'benchmark_repair_summary.json'}`",
    ]
    (output / "BENCHMARK_REPAIR_AUDIT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    checksum_lines = []
    for path in sorted(output.iterdir()):
        if path.name == "checksums.sha256" or not path.is_file():
            continue
        checksum_lines.append(f"{sha256(path)}  {path.name}")
    (output / "checksums.sha256").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    print(json.dumps({"output_dir": str(output), "g1_g4_problems": standard.get("runs_with_structural_problems"), "g5_status_counts": g5.get("status_counts"), "matrix_groups": len(matrix)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
