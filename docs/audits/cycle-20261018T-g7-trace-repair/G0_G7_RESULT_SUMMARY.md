# G0–G7 最终审计结果（cycle-20261018T-g7-trace-repair）

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
