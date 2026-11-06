# 监督报告——修复后验证

## 审计摘要

- 审计编号：`2026-10-08-post-fixes`
- 历史基线：[2026-10-08_supervisor_report_initial.md](2026-10-08_supervisor_report_initial.md)
- 工作区 provenance：Git 元数据不可用；目标目录不是 Git 仓库。
- 上游依赖：NewtonBench 已 vendored，固定提交为 `912a4ba5f4356ddd06acc16e44460ca30be4abc2`。
- 真实 API 使用情况：无。所有已执行 provider 响应均为确定性的 Mock 响应。
- 本报告不授权任何正式科学结论。

## 验证命令

| 命令 | 观察结果 |
|---|---|
| `python -m pytest -q` | `14 passed` |
| `python -m scientific_discovery.cli engineering-test --manifest task_manifest.json --limit 12 --output results\engineering_validation` | 12 个任务、24 条 runner 结果，全部完成；有意使用零函数负向控制，因此验证成功数为 0 |
| `python -m scientific_discovery.cli pilot --manifest task_manifest.json --runner both --provider mock --limit 12 --output results\pilot_final` | 生成 24 个稳定的任务/runner 结果文件 |
| 同一命令加 `--resume` | 跳过已有的 24 条结果；没有重复结果文件或重复调用 |
| `python -m scientific_discovery.cli analyze --input results\pilot_final --output figures\pilot_final_analysis` | 24 条结果、12 对配对数据；Agent-minus-LLM 平均差为 0.0；bootstrap 95% CI 为 `[0.0, 0.0]`；已输出资源汇总 |

命令执行前反复出现的 Conda/PowerShell GBK traceback 属于环境启动警告；每个 Python 命令均继续执行并获得上述结果。

## 门禁状态

| 门禁 | 状态 | 证据 / 限制 |
|---|---|---|
| 上游集成 | PASS | 固定版本的 NewtonBench adapter 和审计命令通过。 |
| LLM-only 隔离 | PASS（软件/Mock 证据） | 计划冻结、规划阶段无观测反馈、无工具、轨迹已持久化；真实 provider 尚未测试。 |
| Agent 闭环 | PASS（软件/Mock 证据） | 只暴露 `run_experiment` 工具；12-task 工程/pilot 流程完成。 |
| 评估器对抗测试 | 数值门禁 PASS；结构/机制结论阻塞 | 已测试错误参数、非法代码、有限区域过拟合、格式错误和代数等价案例。结构恢复为 `null`；机制有效性为 `not_implemented`。 |
| 12-task 工程验证 | PASS（仅工程验证） | manifest 中全部 12 个任务均通过两个 runner 执行。零函数是负向协议控制，不是科学结果。 |
| 配对分析 | PASS（流程） | 输出 `n_pairs=12`、置信区间和资源汇总；仍保留 Mock 数据警告。 |
| 24-task 真实 pilot | 未测试 / 阻塞 | 未提供或使用付费 API 授权。 |
| 正式冻结 | 阻塞 | 真实 pilot 和结构/机制评估器支持仍未完成；Git provenance 也缺失。 |

## 发现项处置

| 编号 | 处置结果 |
|---|---|
| SUP-001 | 工程门已关闭：已实现并执行基于 manifest 的 12-task Mock 流程。 |
| SUP-002 | 持久化轨迹覆盖已关闭：请求、响应、工具、模型元数据、用量、延迟和重试/错误记录均被序列化，且不包含 API key。真实 provider 轨迹仍待验证。 |
| SUP-003 | 部分关闭：已加入数值对抗测试及明确的数值/结构/机制字段；结构/机制评分有意暂未实现。 |
| SUP-004 | 分析流程已关闭：已输出任务配对差异、确定性 bootstrap CI、每个 runner 的分母和资源汇总。 |
| SUP-005 | pilot 流程已关闭：已实现并验证稳定文件名、覆盖保护和 `--resume`。 |
| SUP-006 | P2 未解决：目标工作区没有 Git 元数据。 |

## 正式工作前必需事项

1. 确定并记录结构/机制评估协议，或明确将论文结论限定为数值规律恢复。
2. 获得真实 24-task pilot 的明确授权和预算；仅使用 `--provider openai --allow-paid` 执行，并保留全部产物。
3. 在正式结果冻结前增加外部 provenance，最好包括 Git 提交和环境锁定文件。
