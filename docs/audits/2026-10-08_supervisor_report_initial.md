# 监督报告——初始审计

## 审计摘要

- 审计编号：`2026-10-08-initial`
- 当前 Git 提交：不可用；执行 `git status --short --branch` 返回“不是 Git 仓库”。
- 当前阶段：NewtonBench 直接测量子集的工程原型。
- 真实 API 使用情况：无；所有已执行的模型输出均来自 Mock Provider（模拟提供方）。
- 已执行命令：
  - `python -m pytest -q` → `9 passed in 1.73s`。
  - `python -m scientific_discovery.cli audit` → 必需的上游路径存在；已记录固定提交 `912a4ba5f4356ddd06acc16e44460ca30be4abc2`。
  - `python -m scientific_discovery.cli smoke-test --output results\final_smoke` → 两个 runner 均完成；均通过 128 个点的独立数值验证；provider 调用次数分别为 2 和 3。
  - `python -m scientific_discovery.cli analyze --input results\final_smoke --output figures\final` → 已生成摘要及 PNG/PDF/SVG，且标记为 Mock 数据。
- 测试失败：现有 9 个测试全部通过。
- 尚未验证：12-task 工程门、真实 API 冒烟测试、24-task pilot、正式统计分析、断点续跑/去重、持久化 provider 请求/响应审计轨迹、结构等价性评分。
- 当前阻塞：在以下 P1 问题解决前，不得进行正式付费实验或提出科学结论。

## 门禁状态

| 门禁 | 状态 | 证据 / 原因 |
|---|---|---|
| 门禁 1：上游集成 | PASS | Adapter 调用 `modules.m0_gravity.run_experiment_for_module`；可复现性测试比较了两次模拟器调用。 |
| 门禁 2：LLM-only 隔离 | 对当前直接测量子集 PASS | 现有对抗反馈测试保持 action 和 plan hash 不变；两次调用均使用 `tools=None`；scheduler 没有 provider 引用。完整的持久化 API 轨迹仍缺失。 |
| 门禁 3：Agent 闭环 | 架构 PASS | Mock handler 接收反馈并选择第二个不同 action；只暴露 `run_experiment` 工具 schema。 |
| 门禁 4：评估器 | FAIL / 不完整 | 客观数值验证可用，但所需的错误参数、非法代码、过拟合、预测与机制区分测试尚未实现。 |
| 门禁 5：12-task 工程验证 | 未测试 | smoke 命令只执行一个 `m0_gravity` 任务。虽然存在 12-task manifest，但尚未端到端执行。 |
| 门禁 6：24-task pilot | 未测试 | 尚未执行真实 API，也没有 pilot 命令。 |
| 门禁 7：正式冻结 | 阻塞 | 在上述 P1 项目完成前，不允许正式运行。 |

## 发现项

| 编号 | 严重性 | 发现 | 证据 | 必需修复 | 状态 |
|---|---|---|---|---|---|
| SUP-001 | P1 | `smoke-test` 只运行一个任务；12-task manifest 不是可执行的工程验证流程。 | `src/scientific_discovery/cli.py` 中的 `smoke_test`；`results/final_smoke/` 只包含一个任务的两个 runner 文件。 | 增加确定性的 12-task Mock 验证命令，并保留每个任务的结果，包括失败结果。 | 未解决 |
| SUP-002 | P1 | provider 请求、响应内容/工具调用、重试元数据和模型元数据没有持久化到结果文件。 | 结果文件只有预算计数，没有 provider 调用轨迹。 | 持久化脱敏后的请求/响应元数据，并写入两个 runner 的结果；不得保存 API key。 | 未解决 |
| SUP-003 | P1 | 评估器只有一个正确精确律的正向测试；缺少错误参数、非法代码、有限区域过拟合、预测与机制、格式错误测试。 | `tests/test_evaluator.py` 只有一个测试。 | 增加评估器对抗测试，并明确数值拟合、结构支持、机制支持的结果字段。 | 未解决 |
| SUP-004 | P1 | `analyze` 报告 VLDR，但没有执行已注册的配对分析或置信区间。 | `evaluation/statistics.py` 存在，但未接入 CLI 输出。 | 增加按任务/运行方式的配对聚合、bootstrap 95% CI、资源汇总，并在结果不成对时给出警告。 | 未解决 |
| SUP-005 | P1 | 尚未实现断点续跑、去重、pilot 和正式批处理；重复运行可能重复调用和写入结果。 | CLI 只有 `audit`、`prepare`、`smoke-test`、`run`、`evaluate`、`analyze`。 | 增加基于 manifest 的批处理 runner、`--resume`、稳定运行 ID 和重复结果保护；付费执行必须保持显式授权。 | 未解决 |
| SUP-006 | P2 | 目标工作区没有 Git 元数据，因此无法记录当前实现的 provenance。 | `git status --short --branch` 返回不是 Git 仓库。 | 初始化项目仓库，或在正式工作前明确保留外部 provenance 记录。 | 未解决 |

## 科学有效性

- LLM-only 不适应性：当前架构和 Mock 对抗测试支持该结论，但 API 调用轨迹仍需持久化才能完整审计。
- Agent 反馈：受控 Mock handler 已演示该架构；这属于架构测试，不是真实模型科学推理能力的证据。
- 公平性：两个实验臂使用同一 adapter、任务、action schema、评估器和实验预算。Agent 有意使用更多 API 调用；差异必须报告，不能假设推理成本相同。
- 隐藏规律隔离：公开描述不包含已知隐藏 token 检查；模型 runner 不接收 evaluator 对象或源代码。未来若加入代码工具，文件系统级隔离尚未证明。
- 客观评估：已具备 OOD 数值验证；结构性/机制性恢复尚不支持作为主要结论。
- 选择偏差：未发现基于结果的任务选择；实际上只执行了一个任务，因此 12-task 门禁仍未验证。

## 下一步必需行动

1. 持久化完整的脱敏 provider 调用轨迹，并增加 LLM-only 隔离审计产物。
2. 增加评估器对抗测试及明确的数值/结构/机制结果字段。
3. 实现并执行 12-task Mock 工程验证。
4. 将配对统计和置信区间接入 `analyze`。
5. 增加可恢复的 manifest 执行和重复保护。
6. 重新运行完整回归测试，并生成新的报告；不得覆盖本历史报告。

在 SUP-001 至 SUP-005 关闭前，不得开始正式实验或付费实验。
