#!/usr/bin/env python3
"""Compile the append-only G8.5 engineering-pilot report and handoff."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root
    pre = load(root / "G85_PREFLIGHT.json")
    plan_manifest = load(root / "plans/g85_engineering_pilot_plan.jsonl.manifest.json")
    execution = load(root / "run/execution_summary.json")
    scores = load(root / "results/g85_results_manifest.json")
    audit = load(root / "results/g85_private_truth_audit.json")
    repair_manifest = load(root / "plans/g85_engineering_adapter_repair1_plan.jsonl.manifest.json")
    repair_execution = load(root / "run_adapter_repair1/execution_summary.json")
    repair_scores = load(root / "results_adapter_repair1/g85_results_manifest.json")
    hypotheses = {
        "freeze_time": "before provider calls; engineering pilot only",
        "H_S": {"name": "state sufficient", "prediction": "A/B/C/D should agree when canonical state and evidence are identical"},
        "H_H": {"name": "visible history effect", "prediction": "A_CLEAN_FULL may differ from B_RECOVERED_FULL while C/D remain equal"},
        "H_V": {"name": "validation adoption", "prediction": "full-history arms may use validation evidence more often than state-only arms"},
        "H_N": {"name": "non-mechanistic confounds", "prediction": "differences may be explained by formatting, parsing, or technical failure"},
        "status": "NOT_ELIGIBLE_FOR_CONFIRMATION",
    }
    anomalies = [
        {"id": "G85-UPSTREAM-001", "status": "OPEN", "finding": "G8 scientific release is blocked; G7 handoff has no independent scientific GO."},
        {"id": "G85-HISTORY-001", "status": "OPEN", "finding": "No same-state/same-evidence real H_CLEAN/H_RECOVERED pair found in 233 JSONL files and 3232 rows."},
        {"id": "G85-ADAPTER-001", "status": "REPAIRED_SENSITIVITY", "finding": "One pilot response used decision=confirmed; the original failure is retained and an explicit-enum retry passed."},
    ]
    report = {
        "protocol": "G8_5_SINGLE_KIMI_V1",
        "model_id": "kimi-k2.5",
        "only_model": True,
        "science_status": "SCIENCE_BLOCKED_UPSTREAM",
        "engineering_status": "REAL_KIMI_ENGINEERING_PILOT_COMPLETE",
        "preflight": pre,
        "frozen_hypotheses": hypotheses,
        "anomaly_registry": anomalies,
        "pilot": {"plan": plan_manifest, "execution": execution, "scores": scores, "audit": audit},
        "adapter_repair": {"plan": repair_manifest, "execution": repair_execution, "scores": repair_scores},
        "real_provider_calls_total": execution["real_provider_calls"] + repair_execution["real_provider_calls"],
        "cost_usd_total": execution["total_cost_usd"] + repair_execution["total_cost_usd"],
        "private_truth_policy": "machine truth is separate and loaded only by scorer; model_requests_private_truth_scan_hits=0",
        "confirmatory_claims": [],
        "next_valid_step": "obtain real provenance-linked clean/recovered history pairs and an independently verified G8 scientific GO before any G8.5 confirmation plan",
    }
    write(root / "G85_HYPOTHESES_PREREGISTER.json", hypotheses)
    write(root / "G85_ANOMALY_REGISTRY.json", {"protocol": "G8_5_SINGLE_KIMI_V1", "anomalies": anomalies})
    write(root / "G85_FINAL_MANIFEST.json", report)
    write(root / "G85_HANDOFF.json", {"protocol": "G8_5_SINGLE_KIMI_V1", "science_status": "SCIENCE_BLOCKED_UPSTREAM", "engineering_status": "REAL_KIMI_ENGINEERING_PILOT_COMPLETE", "candidate_g9_edges": [], "supported_hypotheses": [], "real_provider_calls": report["real_provider_calls_total"], "cost_usd": report["cost_usd_total"], "upstream_preflight": str(root / "G85_PREFLIGHT.json"), "confirmatory_data_available": False})
    md = [
        "# G8.5 单一 Kimi 工程验收报告",
        "",
        "## 结论",
        "",
        "- 科学状态：`SCIENCE_BLOCKED_UPSTREAM`。不是等待人工，而是当前证据不满足 G8.5 的真实上游资格：G8 没有独立科学 GO，G7 轨迹没有成对的真实 H_CLEAN/H_RECOVERED。",
        "- 工程状态：`REAL_KIMI_ENGINEERING_PILOT_COMPLETE`。真实调用均为 `kimi-k2.5`，pilot 16 条，修复敏感性 1 条。",
        "- 不支持任何确认性机制、历史效应或 G9 candidate edge 结论。",
        "",
        "## 真实资源与结果",
        "",
        f"- Pilot：16/16 结果文件；PASS {execution['new_result_status_counts'].get('PASS', 0)}，TECHNICAL_FAILURE {execution['new_result_status_counts'].get('TECHNICAL_FAILURE', 0)}；调用 {execution['real_provider_calls']}；成本 `${execution['total_cost_usd']:.6f}`。",
        f"- 修复敏感性：1/1 PASS；调用 {repair_execution['real_provider_calls']}；成本 `${repair_execution['total_cost_usd']:.6f}`。",
        f"- 合计真实 Kimi 调用：{report['real_provider_calls_total']}；成本 `${report['cost_usd_total']:.6f}`。",
        "- Pilot all-planned accuracy：A=1.000、B=1.000、C=1.000、D=0.750；D 的 1 条技术失败留在 pilot 分母，修复批次不替换它。上述数字仅为合成工程输入上的链路指标，不是科学结果。",
        "- 私有真值请求扫描：0 命中；私有真值只在 scorer 读取。",
        "",
        "## 已冻结假设",
        "",
        "- H_S：state sufficient；H_H：visible history effect；H_V：validation adoption；H_N：non-mechanistic confounds。冻结文件为 `G85_HYPOTHESES_PREREGISTER.json`。",
        "- C/D 的可见请求在 plan 构建时做了 byte-equivalence 断言；A/B 才携带不同的工程合成 history。",
        "",
        "## 阻塞原因与审计",
        "",
        "- preflight 扫描 233 个 G7 JSONL、3232 条记录，真实 clean/recovered pair markers=0；`canonical_state_id/evidence_id/history_provenance/visible_history` 均未在上游出现。",
        "- 16 条 pilot 中出现 1 个 schema 技术失败（模型返回 `confirmed`）；原始响应、事件和 trace 保留，修复计划明确要求枚举值并单独重跑通过。",
        "- 合成 history 的科学用途固定为 `FORBIDDEN`；没有用它们支持机制或历史因果结论。",
        "",
        "机器文件：`G85_PREFLIGHT.json`、`G85_HYPOTHESES_PREREGISTER.json`、`G85_ANOMALY_REGISTRY.json`、`G85_FINAL_MANIFEST.json`、`G85_HANDOFF.json`。源码：`scripts/g8_5_mechanism_identification.py`、`scripts/compile_g85_report.py`。",
    ]
    (root / "G85_FINAL_REPORT.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": str(root / "G85_FINAL_MANIFEST.json"), "report": str(root / "G85_FINAL_REPORT.md"), "handoff": str(root / "G85_HANDOFF.json")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
