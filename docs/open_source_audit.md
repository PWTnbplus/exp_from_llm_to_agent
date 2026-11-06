# 开源依赖审计

审计日期：2026-10-08。工作副本位于 `third_party/NewtonBench/`。

| 项目 | 版本 / 提交 | 许可证 | 可复用组件 | 限制 | 集成方式 |
|---|---|---|---|---|---|
| NewtonBench | `912a4ba5f4356ddd06acc16e44460ca30be4abc2`（`main`，从仓库归档下载） | MIT（`third_party/NewtonBench/LICENSE`） | 12 个物理模块、规律变体、直接测量模拟器、Verlet 动力学、数值 RMSLE 评估器 | 上游 runner 是交互式 LLM 循环；评估器还包含可选且不可复现的 LLM 符号评判器；源规律函数与模拟器处于同一 Python 进程 | `NewtonBenchOracle` 只调用选定模块的模拟器。验证在仅评估器进程中使用固定版本的规律实现。 |
| SciLaws-Bench | 未固定；本阶段未集成 | 使用前必须逐任务/逐数据集检查 | 候选外部验证基准 | 隐藏模拟器/数据许可和查询隔离需要单独审计 | 仅作为扩展点 |
| ODEBench | 未固定；本阶段未集成 | 使用前必须逐任务/逐数据集检查 | 候选 ODE 方程/积分数据 | 该仓库是系统辨识资源，不能假定它提供活动 oracle | 仅作为扩展点 |
| PySINDy | 未固定；本阶段未集成 | 正式使用前必须记录候选库许可证 | 经典系统辨识基线 | 不能替代受控的 LLM/Agent 比较 | 计划中的 `ClassicalBaseline` 扩展 |
| SRBench | 未固定；本阶段未集成 | 正式使用前必须记录候选基准/工具许可证 | 符号回归参考和指标 | 需要逐任务兼容性和泄漏审计 | 计划中的参考项 |

## 可复现的上游检查

归档文件来自 `https://github.com/HKUST-KnowComp/NewtonBench/archive/refs/heads/main.zip`；由于当前环境无法使用 Git transport，在写入 `configs/experiment.json` 前通过 GitHub API 独立固定了提交号。下载后的目录包含任务说明中列出的路径：

- `modules/common/physics_base.py`：共享的 1D/2D Verlet 辅助函数。
- `modules/common/evaluation.py`：可执行规律的数值评估，以及可选的 LLM 符号评判器。
- `modules/m0_gravity/core.py`：`run_experiment_for_module(...)` 和模块评估器。
- `utils/vanilla_agent.py`：调用模型、执行实验并反馈结果的交互循环。
- `utils/code_assisted_agent.py`：带额外 Python 工具的交互循环；为保证公平比较而排除。
- `run_experiments.py`：导入模块、运行上游 agent，并评估提交的代码。

根目录 README 描述了 324 种组合（12 个领域 × 3 种规律难度 × 3 种系统类型 × 3 个变体）。当前实现的 registry 明确冻结为 108 个直接测量组合（12 × 3 × 3）；动态系统被明确标记为后续工作，不会被静默当作已支持任务。

## 接口发现

1. 模块通过 `__init__.py` 从 `m*_*` 目录发现，并暴露 `run_experiment_for_module`、`evaluate_law`、`PARAM_DESCRIPTION` 和 `FUNCTION_SIGNATURE`。
2. 直接实验是带关键字参数的调用，adapter 会额外加入 `noise_level`、`difficulty`、`system` 和 `law_version`。
3. 直接系统返回一个标量测量值。上游动力学系统返回截断时间序列，需要单独设计 measurement budget。
4. 规律变体通过 `get_ground_truth_law(difficulty, law_version)` 显式选择；adapter 不使用上游随机选择。
5. 上游数值评估器可以通过 `symbolic_check=False` 复用；可选符号评判器会引入另一个模型、另一套 API 预算和非客观决策，因此被排除在主要指标之外。

## 泄漏与公平性发现

上游 `laws.py` 文件在模拟器进程中包含隐藏常数和公式。模型 runner 从不导入这些内容，只有评估器可以访问。公开任务描述由安全的参数元数据重建，不会转发可能包含公式提示的上游 prompt 示例。LLM-only 调用没有工具定义；Agent 调用只暴露单一的 `run_experiment` 函数 schema。

实际源代码采用 MIT 许可证。下载的归档被保留以便审计；没有修改任何上游文件。
