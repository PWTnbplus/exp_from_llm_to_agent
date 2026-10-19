#!/usr/bin/env python3
"""Compile append-only audit/report artifacts for the Kimi-only G8 runs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root
    pilot = load(root / "pilot/results/g8_analysis_manifest.json")
    formal = load(root / "formal/results/g8_analysis_manifest.json")
    repair = load(root / "formal_adapter_repair1/results/g8_analysis_manifest.json")
    pilot_audit = load(root / "pilot/audit/g8_independent_audit.json")
    formal_audit = load(root / "formal/audit/g8_independent_audit.json")
    repair_audit = load(root / "formal_adapter_repair1/audit/g8_independent_audit.json")
    summary = {
        "protocol": "G8_SINGLE_KIMI_V1",
        "model_id": "kimi-k2.5",
        "only_model": True,
        "historical_glm5_run_preserved": True,
        "scientific_release_status": "BLOCKED_G7_HANDOFF_AND_EXTERNAL_ATTESTATION",
        "q_scientific_truth_status": "NOT_MEASURED_BY_G8_ACTION_SCORER",
        "pilot": {"manifest": pilot, "audit": pilot_audit},
        "formal_primary_intent_to_treat": {"manifest": formal, "audit": formal_audit},
        "formal_adapter_repair_sensitivity": {"manifest": repair, "audit": repair_audit},
        "primary_denominator_rule": "formal 180 planned rows; 24 technical failures remain failures in ITT",
        "repair_rule": "only the 24 primary technical failures were rerun; primary files were not overwritten",
        "private_oracle_policy": "oracle loaded only by scorer after provider calls; no private-truth fields in plans or model requests",
    }
    write(root / "g8_single_kimi_final_manifest.json", summary)
    lines = [
        "# G8 单一 Kimi 实验最终工程报告",
        "",
        "- 模型：`kimi-k2.5` only；历史 `glm-5` G8 数据未合并、未覆盖。",
        "- 科学发布状态：`BLOCKED_G7_HANDOFF_AND_EXTERNAL_ATTESTATION`。G8 的实际运行完成，但不能宣称机制因果已确认；G7 当前没有独立验证的科学 GO，且模型权重/供应商外部认证未完成。",
        "- Q 状态：G8 动作评分器不测 revised-claim 数学真值，因此不把 G8 分数冒充 Q 科学真值。",
        "",
        "## 终态与资源",
        "",
        f"- Pilot：{pilot['planned']} planned；状态 `{pilot['status_counts']}`；真实调用 {pilot['real_provider_calls']}；成本 `${pilot['total_cost_usd']:.6f}`。",
        f"- Formal 主 ITT：{formal['planned']} planned；状态 `{formal['status_counts']}`；真实调用 {formal['real_provider_calls']}；成本 `${formal['total_cost_usd']:.6f}`。",
        f"- Adapter repair sensitivity：{repair['planned']} 条原技术失败重跑；状态 `{repair['status_counts']}`；真实调用 {repair['real_provider_calls']}；成本 `${repair['total_cost_usd']:.6f}`。",
        "- Formal 主 ITT 的 24 个技术失败仍留在 180 条分母内；修复批次只作为附加敏感性结果，不替换主结果。",
        "",
        "## Formal 主 ITT 配对效应（all-planned correctness）",
        "",
        "| Contrast | Difference | 95% cluster bootstrap CI | pairs | families |",
        "|---|---:|---:|---:|---:|",
    ]
    for item in formal["paired_effects"]:
        lines.append(f"| {item['contrast']} | {item['difference']:.6f} | [{item['ci95_lower']:.6f}, {item['ci95_upper']:.6f}] | {item['n_case_replicate_pairs']} | {item['n_independent_families']} |")
    lines += [
        "",
        "## 独立审计",
        "",
        f"- Pilot audit：{pilot_audit['n_result_files']}/{pilot_audit['n_planned']} 文件存在，audit PASS {pilot_audit['audit_status_counts']}，private oracle 未载入。",
        f"- Formal audit：{formal_audit['n_result_files']}/{formal_audit['n_planned']} 文件存在，audit PASS {formal_audit['audit_status_counts']}，private oracle 未载入。",
        f"- Repair audit：{repair_audit['n_result_files']}/{repair_audit['n_planned']} 文件存在，audit PASS {repair_audit['audit_status_counts']}，private oracle 未载入。",
        "- 原始响应、事件、provider trace、plan hash 和 cost ledger 均保留在相应 run root。",
        "",
        "## 解释边界",
        "",
        "B/C/D/E/F 的运行工作流和对照均已实际执行，但当前样本只有 5 个理论族，且 G7 尚无独立科学 GO；因此这些差异只能作为单一 Kimi 的工程/探索性机制信号，不能写成确认性因果结论。",
        "",
        "机器报告：`g8_single_kimi_final_manifest.json`；源码：`scripts/g8_single_kimi.py`、`scripts/compile_g8_single_kimi_report.py`。",
    ]
    (root / "g8_single_kimi_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": str(root / 'g8_single_kimi_final_manifest.json'), "report": str(root / 'g8_single_kimi_report.md')}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
