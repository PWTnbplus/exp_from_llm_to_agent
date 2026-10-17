"""Build the auditable G0-G7 handoff for the trace-repair cycle."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any


CYCLE = "cycle-20261018T-g7-trace-repair"
G7_ROOT = Path("runs/ctflow_single_model/20261017T-g7-kimi-k25-v1")
AUDIT_ROOT = G7_ROOT / "g7_audit"
OUT = Path("docs/audits") / CYCLE


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def rel(path: Path) -> str:
    return path.as_posix()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def artifact_hashes(paths: list[Path]) -> dict[str, str | None]:
    return {rel(path): sha256(path) for path in paths}


def main() -> int:
    gates_path = Path("docs/state/gates.json")
    previous_audit_path = Path("docs/audits/cycle-20261018T-kimi-format-revalidation-partial/audit.json")
    merge_path = AUDIT_ROOT / "states_merged_trace_repair_20261018.jsonl"
    checkpoint_merge_path = AUDIT_ROOT / "checkpoints_merged_trace_repair_20261018.jsonl"
    derivation_path = AUDIT_ROOT / "g7_trace_view_20261018/derivation_summary.json"
    trace_path = AUDIT_ROOT / "trace_q_consistency_trace_view_20261018.json"
    q_path = AUDIT_ROOT / "q_audit_trace_repair_20261018.jsonl"
    metrics_path = AUDIT_ROOT / "corrected_metrics_trace_repair_20261018.json"
    review_path = Path("docs/audits/cycle-20261018T-g7-trace-repair/REPAIR_INDEPENDENT_REVIEW.json")
    source_paths = [
        Path("scripts/run_g7_failure_localization.py"),
        Path("scripts/derive_g7_trace_view.py"),
        Path("scripts/audit_g7_trace_q_consistency.py"),
        Path("tests/test_g7_trace_q_consistency.py"),
    ]
    gates = load_json(gates_path)
    previous = load_json(previous_audit_path)
    merge_manifest = load_json(AUDIT_ROOT / "g7_merge_manifest.json")
    derivation = load_json(derivation_path)
    trace = load_json(trace_path)
    metrics = load_json(metrics_path)

    state_summary = merge_manifest["states"]
    checkpoint_summary = merge_manifest["checkpoints"]
    g7_counts = {
        "planned_states": state_summary["expected"],
        "selected_states": state_summary["selected_records"],
        "completed_states": state_summary["selected_completed"],
        "checkpoint_missing_states": sum(
            value == "checkpoint_missing" for value in state_summary["selected_terminal_failures"].values()
        ),
        "provider_error_states": sum(
            value == "provider_error" for value in state_summary["selected_terminal_failures"].values()
        ),
        "planned_checkpoints": checkpoint_summary["expected"],
        "selected_checkpoints": checkpoint_summary["selected_records"],
        "derived_trace_accepted_states": derivation["accepted_states"],
        "derived_trace_accepted_checkpoints": derivation["accepted_checkpoints"],
        "raw_trace_integrity_failures": 28,
        "derived_final_trace_integrity_failures": trace["states"]["trace_integrity_failures"],
        "q_rows": trace["q"]["rows"],
        "q_trace_backed_valid": trace["q"]["trace_backed_valid"],
        "corrected_metrics": metrics["counts"],
    }

    commands = [
        {"command": "E:/resources/python/python.exe -X utf8 -m pytest -q", "exit_code": 0, "result": "267 passed"},
        {"command": "E:/resources/python/python.exe -X utf8 -m py_compile scripts/derive_g7_trace_view.py scripts/run_g7_failure_localization.py tests/test_g7_trace_q_consistency.py", "exit_code": 0},
        {"command": "scripts/merge_g7_states.py ... --states-out states_merged_trace_repair_20261018.jsonl", "exit_code": 0},
        {"command": "scripts/derive_g7_trace_view.py ... --out-root g7_trace_view_20261018", "exit_code": 0},
        {"command": "scripts/audit_g7_q.py ... --out q_audit_trace_repair_20261018.jsonl", "exit_code": 0, "result": "1288 rows, 0 valid"},
        {"command": "scripts/audit_g7_trace_q_consistency.py ... --out trace_q_consistency_trace_view_20261018.json", "exit_code": 0, "result": "13 final trace integrity failures; 0 Q trace-backed valid"},
        {"command": "scripts/audit_g7_corrected_metrics.py ... --out corrected_metrics_trace_repair_20261018.json", "exit_code": 0, "result": "confirmatory_reuse_allowed=false"},
    ]

    evidence_rows = [
        ["G0", "PASS", "scientific_provenance_only", "pinned NewtonBench/licensing evidence in gates.json; official evaluator caveat retained", "scientific release no", "docs/state/gates.json"],
        ["G1", "PASS_ENGINEERING_ONLY", "nonadaptive LLM-only contract", "policy/isolation tests and frozen-plan controls; no formal real-provider result", "scientific release no", "docs/state/gates.json; tests/"],
        ["G2", "PASS_ENGINEERING_ONLY", "feedback-dependent Agent action", "action/tool-boundary engineering tests; no superiority inference", "scientific release no", "docs/state/gates.json; tests/"],
        ["G3", "PASS_ENGINEERING_ONLY", "budget and hidden-answer isolation", "budget ledger and no-leakage controls; provider/model evidence not externally verified", "scientific release no", "docs/state/gates.json; runs/ctflow_single_model/20261017T-g6-kimi-k25-v1"],
        ["G4", "PASS_ENGINEERING_ONLY", "objective evaluator", "adversarial evaluator tests; not upstream scientific validation", "scientific release no", "docs/state/gates.json; tests/"],
        ["G5", "PASS_SMOKE_ONLY", "real simulator/mock pipeline", "smoke and protocol controls; no formal VLDR result", "scientific release no", "docs/state/gates.json; docs/audits/"],
        ["G6", "BLOCKED", "formal scientific release", "552 planned; 550 completed; 2 provider_error; trace 0; revision-valid 0/138; external math/model/billing/statistics blockers", "no", "runs/ctflow_single_model/20261017T-g6-kimi-k25-v1/g6_audit; docs/state/gates.json"],
        ["G7", "BLOCKED", "formal scientific release", f"{g7_counts['planned_states']} planned; {g7_counts['completed_states']} completed; {g7_counts['checkpoint_missing_states']} checkpoint_missing; {g7_counts['provider_error_states']} provider_error; raw trace failures 28, derived final failures {g7_counts['derived_final_trace_integrity_failures']}; Q 0/{g7_counts['q_rows']} independently valid", "no", "runs/ctflow_single_model/20261017T-g7-kimi-k25-v1/g7_audit; docs/state/gates.json"],
    ]

    matrix_path = OUT / "G0_G7_EVIDENCE_MATRIX.csv"
    matrix_path.parent.mkdir(parents=True, exist_ok=True)
    with matrix_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["experiment_group", "status", "scope", "evidence", "scientific_release", "artifact_paths"])
        writer.writerows(evidence_rows)

    artifacts = [
        gates_path, previous_audit_path, merge_path, checkpoint_merge_path,
        derivation_path, trace_path, q_path, metrics_path, *source_paths,
        matrix_path, review_path,
    ]
    final_audit = {
        "audit_version": "g0-g7-single-model-final-audit-v1",
        "cycle": CYCLE,
        "experiment_id": "single_model_g0_g7",
        "model": {"configured_model_id": "kimi-k2.5", "external_immutable_identity_verified": False},
        "status": "BLOCKED_NONCONFIRMATORY",
        "scientific_release_allowed": False,
        "gates": {row[0]: {"status": row[1], "scope": row[2], "evidence": row[3]} for row in evidence_rows},
        "g7_counts": g7_counts,
        "conclusions": [
            "G0 is supported only for pinned simulator provenance and licensing; official evaluator status remains a caveat.",
            "G1-G5 are engineering, policy, evaluator, or smoke evidence, not a formal LLM-versus-Agent scientific result.",
            "G6 has no scientifically valid released law-discovery result: revision-valid is 0/138 and independent math/statistical/model/billing gates remain open.",
            "G7 is diagnostic-only. The derived view separates append-only attempts without pooling; it does not change the frozen denominator, truth, or Q validity. Q is NOT_SCORED with 0 independently valid rows.",
            "No causal L/U conclusion, Agent superiority claim, or confirmatory statistical inference is supported.",
        ],
        "cost_and_provenance": {
            "user_budget_ceiling_usd": 200.0,
            "known_local_observed_g6_g7_usd": 4.757124,
            "this_cycle_incremental_provider_cost_usd": 0.0,
            "external_billing_verified": False,
            "model_snapshot_verified": False,
            "model_id_source": "local runner configuration and persisted summaries only",
        },
        "commands": commands,
        "artifact_sha256": artifact_hashes(artifacts),
        "raw_evidence_policy": "Raw traces are retained; derived trace view is a separate non-confirmatory audit artifact; no frozen truth or raw provider record was modified.",
        "independent_read_only_review": rel(review_path),
    }
    final_path = OUT / "G0_G7_FINAL_AUDIT.json"
    write_json(final_path, final_audit)

    cost = {
        "budget_ceiling_usd": 200.0,
        "known_local_observed_cost_usd": 4.757124,
        "g6_local_observed_cost_usd": 2.039289,
        "g7_local_observed_cost_usd": 2.722796,
        "this_cycle_incremental_provider_cost_usd": 0.0,
        "provider_calls_in_this_cycle": 0,
        "external_billing_verified": False,
        "external_invoice_or_receipt": None,
        "model_id": "kimi-k2.5",
        "base_url": "https://token.ctflow.cn/v1",
        "immutable_model_snapshot_verified": False,
        "billing_interpretation": "Local runner accounting only; do not treat it as provider invoice evidence. The observed local amount is below the authorized USD 200 ceiling, but billing/pricing and immutable gateway identity remain unverified.",
        "source_artifacts": artifact_hashes([
            previous_audit_path,
            Path("runs/ctflow_single_model/20261017T-g6-kimi-k25-v1/g6_audit/trace_audit.json"),
            Path("runs/ctflow_single_model/20261017T-g7-kimi-k25-v1/runner_summary.worker-16-0.json"),
        ]),
    }
    write_json(OUT / "COST_AND_MODEL_PROVENANCE.json", cost)

    summary = f"""# G0–G7 最终审计结果（{CYCLE}）

结论：**不得发布科学结果**。本周期修复了 G7 重试轨迹写入缺陷并完成离线重审，但 G6/G7 仍是非确认性数据；没有证明 Agent 优越性、因果 L/U 机制、Q 有效性或任何确认性统计结论。

| 阶段 | 状态 | 实际证据 |
|---|---|---|
| G0 | PASS（仅溯源/许可） | NewtonBench 固定版本与许可证据；官方 evaluator 仍是 caveat |
| G1–G5 | PASS（工程/策略/烟测） | 测试和协议边界通过；不等于真实科学结果 |
| G6 | BLOCKED | 552 计划，550 完成，2 provider error；revision-valid 0/138；独立数学、统计、模型身份、计费阻塞 |
| G7 | BLOCKED | 1,288 状态，1,150 完成，137 checkpoint_missing，1 provider_error；原始轨迹失败 28，派生最终尝试仍失败 13；Q 独立有效 0/1,288 |

G7 派生视图把每个 `RUN_START` 当作独立尝试边界，确认 1,138 个状态最终尝试的生命周期自洽；这只是审计视图，不改变原始轨迹、冻结真值或 1,288 分母。另有 13 个最终尝试仍不自洽，因此不能把 G7 称为 trace-clean。

实际费用：本周期新增 provider/API 费用 **$0**。现有 G6+G7 本地账本观察值为 **$4.757124**（G6 $2.039289 + G7 $2.722796），低于 $200 上限；外部账单和不可变模型身份未验证，不能把该数字当作供应商发票。

主要文件：

- `G0_G7_EVIDENCE_MATRIX.csv`：阶段矩阵。
- `G0_G7_FINAL_AUDIT.json`：命令、计数和 SHA-256。
- `COST_AND_MODEL_PROVENANCE.json`：预算与模型证据边界。
- `UNRESOLVED_BLOCKERS.md`：尚未解决的发布阻塞。
- `runs/ctflow_single_model/20261017T-g7-kimi-k25-v1/g7_audit/g7_trace_view_20261018/`：不改原始数据的派生轨迹视图。
"""
    (OUT / "G0_G7_RESULT_SUMMARY.md").write_text(summary, encoding="utf-8")
    blockers = """# 未解决阻塞

1. **G6 独立数学/统计验收缺失**：revision-valid 为 0/138；没有独立数学审阅、可发布统计检验或确认性分母验收。
2. **G7 provider/覆盖阻塞**：1,288 状态中 137 个 checkpoint_missing、1 个 provider_error；不能把 1,150/1,288 宣称为科学完成率。
3. **G7 轨迹仍有 13 个真实最终尝试不一致**：旧的 28 个错误中 15 个可由尝试边界解释；其余 13 个保留为失败，未重写、未插值、未伪造。
4. **Q 没有独立 verifier**：Q 为 `NOT_SCORED`，独立有效 0/1,288；模型自报或 V/L/U 标签一致性不等于 Q 数学证明。
5. **模型身份/计费不可外部验证**：`kimi-k2.5`、价格、网关权重指纹和供应商账单均只有本地记录，科学发布继续 fail-closed。
6. **依赖边缺失**：G7 的 L/U 机制诊断不得补造 dependency/state edges；因此不得作因果机制结论。

本周期没有新的付费 worker/API 调用；只有代码修复、离线派生视图和审计重跑。
"""
    (OUT / "UNRESOLVED_BLOCKERS.md").write_text(blockers, encoding="utf-8")
    # Add the generated files after writing them so the final audit hashes the
    # complete deliverable set as well.
    final_audit["artifact_sha256"].update(artifact_hashes([
        OUT / "COST_AND_MODEL_PROVENANCE.json",
        OUT / "G0_G7_RESULT_SUMMARY.md",
        OUT / "UNRESOLVED_BLOCKERS.md",
    ]))
    write_json(final_path, final_audit)
    print(json.dumps({"out": str(OUT), "g7": g7_counts}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
