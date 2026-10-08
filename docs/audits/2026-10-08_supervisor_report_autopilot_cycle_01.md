# 独立监督报告——自动化周期 01

## 审计摘要

- 审计 ID：`20261008-autopilot-cycle-01`
- 基础 Git 提交：`c26a800e2f45c7c5e12bf70b3f375735a6b6db12`
- 工作分支：`autopilot/scientific-law-discovery`
- 阶段：G0–G5 工程验证；G6/G7 尚未达到正式评估条件。
- API/支出状态：未发起付费或真实模型提供商请求。所有已执行实验输出均标记为 Mock；模拟器 smoke test 使用仓库内置的 NewtonBench 实现。
- 当前阻塞项：外部网络阻止了远程仓库/上游验证和推送；结构性/机制性评估尚未实现；真实模型提供商 pilot 尚未测试。

## 验证证据

| 命令 | 结果 | 证据 |
|---|---|---|
| `python -m pytest -q` | 通过 | 本周期修改后 `31 passed`。 |
| `python -m unittest discover -s tests -p 'test_autopilot_harness.py' -v` | 通过 | `12` 个 harness 测试通过，包括 fail-closed 审查和 Git 安全检查。 |
| `python -m scientific_discovery.cli audit` | 通过 | 所需 NewtonBench 路径存在；配置的 SHA 为 `912a4ba5f4356ddd06acc16e44460ca30be4abc2`。 |
| `python -m scientific_discovery.cli prepare --limit 12 --seed 42 ...` | 通过 | 未使用实验结果，生成了确定性的 12 任务清单。 |
| `python -m scientific_discovery.cli smoke-test ...` | 通过（Mock） | 两个 runner 均完成；调用了仓库内置的真实直接测量模拟器；验证仅限数值拟合。 |
| `python -m scientific_discovery.cli engineering-test ... --limit 12 ...` | 通过（仅工程验证） | 12 个任务 × 2 个 runner = 24 条完成记录；零定律负对照产生了 0 个验证成功。 |
| `python -m scientific_discovery.cli analyze ...` | 通过（Mock） | 24 条记录、12 个配对任务 ID；两组 VLDR 均为 0.0；不作科学结论。 |
| `git ls-remote --heads origin autopilot/scientific-law-discovery` | 阻塞 | 经配置的代理连接 GitHub 的 443 端口失败。 |
| `git ls-remote https://github.com/HKUST-KnowComp/NewtonBench.git HEAD` | 阻塞 | 同样的网络/代理故障；无法独立重新检查上游 HEAD。 |

## 本周期完成的修改

- 在适配器 schema 中加入公开的 NewtonBench 仪器参数边界，并在计划验证和 oracle 执行中同时强制执行（`src/scientific_discovery/benchmark/newtonbench_adapter.py`、`src/scientific_discovery/runners/common.py`）。
- 使留出验证动作遵守相同的公开参数域，而不是对每个模块统一采样一个域外分布（`src/scientific_discovery/evaluation/law_recovery.py`）。
- 在 LLM-only 规划和最终推理上下文中保留初始观测，同时确保中间观测不会进入规划阶段。
- 拒绝名称不是唯一授权操作 `run_experiment` 的 Agent 工具调用。
- 当缺少 token 价格时，让真实模型提供商调用 fail-closed，从而避免配置的成本上限被无意中按零成本计账。
- 修正评估元数据和文档：当前实现使用固定版本上游的 ground-truth 函数，并将其置于受限的项目自有数值评估器中；这不是 NewtonBench 的完整官方评估器，当前 `validated_success` 仅表示数值拟合成功。
- 为以上行为增加对抗性测试和回归测试。

## Gate 状态

| Gate | 状态 | 证据/限制 |
|---|---|---|
| G0 上游适配器、SHA、许可证 | 阻塞 | 适配器和 MIT 许可证存在，模拟器也已执行；但由于网络失败，无法重新检查远程 SHA/来源。 |
| G1 LLM-only 冻结计划隔离 | 通过（Mock 架构） | 观测交换、计划哈希、无工具调用、批次中途不调用模型以及最终化测试均通过。未测试真实模型提供商轨迹。 |
| G2 Agent 闭环 | 通过（Mock 架构） | 基于反馈的动作测试和未授权工具测试均通过。这不能证明真实模型具备科学推理能力。 |
| G3 共享预算/动作/隐私边界 | 通过（确定性实现） | 已测试共享账本、参数域检查、工具边界和无秘密信息轨迹；不宣称两组 token 数量相等。 |
| G4 评估器对抗有效性 | 未测试 | 错误参数、过拟合、格式错误和非法代码的数值案例已通过，但结构恢复和机制有效性明确尚未实现。 |
| G5 Mock 端到端 + 真实模拟器 smoke test | 通过（仅 Mock） | 模拟器是真实的；模型提供商调用和正式科学结果尚未验证。 |
| G6 清单/失败/统计/可复现性 | 未测试 | 工程产物已存在，但尚未执行真实 24 任务 pilot 或重复正式运行。 |
| G7 预注册锁定 | 阻塞 | 正式阈值、结构评估器、真实 pilot 估计和外部来源信息尚未完备。 |

## 发现的问题

| ID | 严重性 | 问题 | 证据 | 必需的修复 | 状态 |
|---|---|---|---|---|---|
| SUP-001 | P1 | 正式科学评分尚不完整。 | `src/scientific_discovery/evaluation/law_recovery.py`；`structural_recovery=None`，`mechanistic_validity=not_implemented`。 | 定义并测试确定性的结构/等价性标准和机制/OOD 标准，然后在正式运行前预注册阈值。 | 开放——阻塞 G4/G7 |
| SUP-002 | P1 | 真实模型提供商 pilot 以及重试/成本行为尚未通过实证验证。 | 未发起真实 API 请求；仅对模型提供商失败路径进行了单元测试。 | 在获得明确授权并设置硬性支出上限后，运行最小模型提供商 smoke test，归档脱敏轨迹，并重新执行隔离审计。 | 开放——未测试 |
| SUP-003 | P1 | 上游来源证明和 GitHub 交付受到外部阻塞。 | 两条 `git ls-remote` 命令均因代理连接错误失败；仓库内置的 NewtonBench 不是独立 Git checkout。 | 恢复网络/Git 凭据，验证配置的上游提交和许可证，然后将本分支推送到 `origin/autopilot/scientific-law-discovery`；在确认之前不得声称推送成功。 | 阻塞 |
| SUP-004 | P1 | 正式统计有效性尚未建立。 | 只执行了 12 任务的 Mock 工程运行；分析对任务行使用了未聚类的配对 bootstrap。 | 在任何正式 API 批次前，冻结 pilot/正式测试的任务分层、重复次数和按定律族聚类的统计方案；所有失败都必须保留在分母中。 | 开放——未测试 |
| SUP-005 | P2 | Classical baseline 目前只是扩展接口。 | `src/scientific_discovery/evaluation/classical.py` 仍保留 `NotImplementedError`。 | 只有在研究加入经典方法比较时才实现；否则应明确将其排除在研究结论之外。 | 已记录 |

## 科学有效性

- LLM-only 严格非自适应性：对于确定性架构和 Mock 对抗测试，结果为通过；真实模型提供商请求仍未验证。
- Agent 反馈控制：对于 Mock 架构，结果为通过；这不能证明真实模型具有有用的科学推理能力。
- 资源公平性：实验/动作参数域和账本限制是共享的。在 Mock 12 任务分析中，两组记录的输入 token 不同（`llm_only=3216`、`single_agent=5118`），因此必须报告成本/token 效率，不能将其视为已匹配。
- 隐藏定律隔离：公开描述不包含已知的隐藏源代码 token；评估器在提交后调用；没有暴露代码/文件工具。针对真实模型提供商的完整运行时/文件系统对抗审查仍不完整。
- 客观评估：已实现数值拟合；尚未实现结构和机制有效性。不允许声称发现了人类未知定律。
- 选择偏差：工程清单是确定性的，且不依赖实验结果，但它不是预注册的正式测试集。

## 后续必需行动

1. 恢复网络，验证确切的 NewtonBench SHA/归档来源，并确认推送状态。
2. 完成确定性的结构/机制评估，或将预注册研究主张明确收窄为数值定律函数恢复。
3. 获取明确的真实 API 使用授权和支出上限，配置正数 token 价格，运行一次模型提供商 smoke test，并重新执行隔离审计。
4. 冻结 pilot 清单和聚类统计方案；在保留每个失败记录及运行状态的前提下执行获授权的 pilot。
5. 在 SUP-001–SUP-004 仍处于开放状态时，不得开始 72–96 任务的付费评估，也不得声称 Agent 优于其他方法。

本报告区分了已实现的软件行为、已执行的验证、受阻的外部工作和未经测试的科学主张。测试通过并不等同于研究假设得到证实。
