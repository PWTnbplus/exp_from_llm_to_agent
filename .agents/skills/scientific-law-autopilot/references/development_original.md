# Codex 科研实验工程任务书

## 项目名称

**From LLMs to Autonomous Agents: Evaluating Scientific Law Discovery Under Controlled Experimental Conditions**

中文：从传统 LLM 到自主 Agent：受控实验条件下的科学规律发现能力研究。

---

# 0. 你的角色与总体任务

你现在是一名具备以下专业能力的高级科研工程师：

- AI for Science
- LLM API Engineering
- Autonomous AI Agents
- Scientific Law Discovery
- Physics Simulation
- Symbolic Regression
- Scientific Benchmark Engineering
- Statistical Experimental Design
- Research Reproducibility
- Python Software Engineering

你的任务不是简单写一个 Benchmark 脚本，而是建立一个**具有论文级可复现性、严格控制变量、可以执行真实 API 实验的科研工程系统**。

本项目未来可能用于 Nature Communications、Nature Machine Intelligence 等期刊的科研工作。

请按照科学研究标准完成系统设计、代码实现、测试、运行和文档。

**不要只生成设计文档。必须真正创建代码、完成可执行环境，并通过测试。**

如果当前环境具备联网和安装依赖的权限，优先寻找、下载并复用成熟开源项目。

不要为了展示编程能力重新实现已有成熟物理模拟器、符号回归算法或评价系统。

如果某项功能无法完成，必须明确说明技术原因，不能使用虚假数据或占位结果冒充完成。

---

# 1. 核心科学问题

本研究只关注一个核心问题：

**Can autonomous AI agents discover unknown scientific laws more reliably than standalone LLMs under controlled experimental conditions?**

中文：

在科学背景知识、基础模型和实验资源受到控制的条件下，自主 AI Agent 是否能够比传统 LLM 更可靠地发现未知科学规律？

我们想研究的是：

1. LLM 是否能够根据有限实验数据推断科学规律？
2. Agent 是否能够通过主动实验和反馈提高规律发现能力？
3. 在相同实验预算下，两者发现正确规律的概率是否存在显著差异？
4. Agent 的发现是否能够通过未见过的科学实验条件得到验证？
5. Agent 的额外能力是否足以抵消其更高的计算和调用成本？

本阶段不研究 Multi-Agent，不研究多 Agent 协作，不开发复杂组织式 Agent 框架。

只比较：

**Traditional LLM-only vs Single Autonomous Agent**

但必须注意科学结论的边界：

这里的 Traditional LLM-only 是严格非自适应的开环 LLM 基线。

如果 Agent 获得优势，我们首先只能得出：

“在当前实验设置下，闭环自主实验策略优于非自适应 LLM 实验策略。”

不能将其自动推广为：

“所有 Agent 都优于所有 LLM。”

所有论文与报告必须遵守这一逻辑边界。

---

# 2. 第一原则：优先复用现成开源项目

正式编码之前，你必须先对以下 GitHub 仓库进行技术调查。

## 2.1 NewtonBench：首选主实验平台

GitHub：

https://github.com/HKUST-KnowComp/NewtonBench

论文：

https://arxiv.org/abs/2510.07172

这是目前优先级最高的资源。

该项目公开介绍包含：

- 324 个 Scientific Law Discovery Tasks
- 12 个物理领域
- 可交互的科学实验系统
- 不同规律复杂度
- 不同系统复杂度
- 物理模拟器
- 规律定义
- 实验评估组件
- LLM API 调用实现

请实际克隆仓库、检查源码与当前提交版本。

重点检查：

- `modules/common/`
- `modules/m0_gravity/` 等物理模块
- `modules/common/physics_base.py`
- `modules/common/evaluation.py`
- `utils/call_llm_api.py`
- `utils/vanilla_agent.py`
- `utils/code_assisted_agent.py`
- `run_master.py`
- `run_experiments.py`

以上路径基于项目公开结构。必须检查当前仓库，不能假定其接口始终不变。

需要回答：

1. 如何枚举全部任务？
2. 如何初始化单个隐藏科学系统？
3. 如何设置物理实验输入？
4. 如何获取模拟器观测结果？
5. 如何控制实验预算？
6. 如何获得或复用官方评价结果？
7. 是否能够独立执行实验查询？
8. 是否能够将物理模拟器与原始 Agent Runner 解耦？
9. 是否能通过 Adapter 实现我们自己的 LLM-only 和 Agent 对照？
10. 是否有隐藏答案通过 Prompt、日志、异常、模块名称或返回字段泄露的风险？

如果已有接口可直接复用，必须使用 Adapter 包装。

不要复制项目中的物理公式再重新写一套模拟器。

特别注意：

NewtonBench 的 `vanilla_agent` 不是本实验的 Traditional LLM-only。

它的命名只是表示不执行代码的 Agent，不能因为名字叫 vanilla 就将它误认为普通 LLM。

## 2.2 SciLaws-Bench：候选外部验证平台

GitHub：

https://github.com/yiyihum/SciLaws-Bench

项目包含 Real 和 Parallel 两种科学规律发现任务。

请调查：

- 任务数据如何加载
- Parallel 环境如何查询
- 隐藏规律如何保护
- 结构恢复如何评分
- 如何隔离评估器
- 哪些任务具有合法的主动实验查询能力

特别关注：

- `harness/`
- `baseline_agent/`
- `dataset/`
- `simulator/`

这里有一个严重风险：

SciLaws-Bench 的隐藏模拟器内部可能包含真实公式与参数。

模型只能通过授权的观测接口查询，不能直接读取模拟器文件、序列化状态或隐藏公式。

此外必须检查每个任务的上游数据许可证。

本阶段优先完成 NewtonBench。SciLaws-Bench 如果需要较大额外开发成本，只实现可扩展接口，不强制加入第一批正式实验。

## 2.3 ODEBench：候选动力学扩展

GitHub：

https://github.com/GPBench/ODEBench

该项目包含 63 个 ODE 系统。

请检查是否能复用其方程、参数、积分器和数据生成逻辑。

注意：

ODEBench 是动力系统辨识资源，不应该未经检查就宣称其提供完整的交互式主动实验环境。

如果需要大量改造才支持可控实验，则仅作为后续扩展，不影响主工程交付。

## 2.4 传统科学算法

调查：

https://github.com/dynamicslab/pysindy

https://github.com/cavalab/srbench

优先复用现有成熟算法。

PySINDy 可作为部分适用任务上的传统系统辨识参考方法。

SRBench 用于寻找合理的符号回归工具及评价方式。

本阶段主要比较 LLM-only 与 Agent，不要求实现完整传统算法排行榜。

但应当建立可扩展的 `ClassicalBaseline` 接口，并在技术文档中说明哪些任务可以直接使用传统算法。

---

# 3. 开源项目调查交付物

在正式改造前，创建：

`docs/open_source_audit.md`

至少包括：

| 项目 | 版本/Commit | 许可证 | 可复用组件 | 限制 | 集成方案 |
|---|---|---|---|---|---|

还需要包含：

- 真实安装步骤
- 实际验证过的 API
- 任务数量和任务结构
- 可交互性检查
- 评分机制
- 隐藏答案泄漏风险
- 是否支持相同预算的公平比较
- 需要编写哪些 Adapter
- 不准备复用的组件及原因

任务源和评估器必须记录确切 Git Commit SHA。

不要只依赖 README 宣传内容。

如果 README 与实际代码不一致，以可复现的代码行为为准，并记录差异。

---

# 4. 工程总体架构

建议创建独立工程：

`scientific_discovery_experiment/`

推荐结构：

```text
scientific_discovery_experiment/
├── README.md
├── pyproject.toml
├── .env.example
├── .gitignore
├── configs/
│   ├── experiment.yaml
│   ├── model.yaml
│   ├── budget.yaml
│   └── task_selection.yaml
├── third_party/
│   └── NewtonBench/
├── src/
│   └── scientific_discovery/
│       ├── benchmark/
│       │   ├── base.py
│       │   ├── newtonbench_adapter.py
│       │   ├── task_registry.py
│       │   └── task_validator.py
│       ├── models/
│       │   ├── provider.py
│       │   ├── api_client.py
│       │   └── mock_provider.py
│       ├── runners/
│       │   ├── llm_only.py
│       │   └── single_agent.py
│       ├── environment/
│       │   ├── experiment_oracle.py
│       │   ├── observation.py
│       │   ├── budget.py
│       │   └── isolation.py
│       ├── evaluation/
│       │   ├── law_recovery.py
│       │   ├── validation.py
│       │   ├── metrics.py
│       │   └── statistics.py
│       ├── experiment/
│       │   ├── runner.py
│       │   ├── scheduler.py
│       │   └── recorder.py
│       └── utils/
├── prompts/
│   ├── llm_plan.md
│   ├── llm_discover.md
│   ├── agent_system.md
│   └── agent_discover.md
├── scripts/
│   ├── audit_upstream.py
│   ├── prepare_tasks.py
│   ├── smoke_test.py
│   ├── run_pilot.py
│   ├── run_experiment.py
│   └── analyze_results.py
├── tests/
│   ├── test_llm_isolation.py
│   ├── test_agent_actions.py
│   ├── test_budget.py
│   ├── test_oracle.py
│   ├── test_no_leakage.py
│   ├── test_evaluator.py
│   └── test_reproducibility.py
├── results/
├── figures/
└── docs/
```

可以根据实际开源仓库接口调整路径。

但必须保证：

- LLM-only Runner 与 Agent Runner 独立。
- 模拟器与模型 API 完全解耦。
- 隐藏答案与模型输入隔离。
- 实验预算由统一组件强制控制。
- 评价器与模型执行器隔离。
- 结果能够复现与审计。

不要为了架构美观引入过度复杂的微服务系统。

优先保证科研正确性。

---

# 5. 核心要求：Traditional LLM 必须是真正的 LLM-only

这是项目最重要的工程约束。

**使用 API 不等于使用 Agent。**

Agent 的关键是具备根据环境反馈选择后续行动的闭环控制能力。

我们的 Traditional LLM-only 不允许具备该能力。

## 5.1 LLM-only 定义

LLM-only 可以：

- 读取科学问题描述
- 读取相同的初始实验观测
- 推理分析
- 提出假设
- 预先制定实验计划
- 在计划全部执行完毕后分析实验数据
- 输出最终科学规律

LLM-only 不可以：

- 在实验执行过程中获取部分新数据并重新规划
- 使用 ReAct 循环
- 在中途自主调用实验工具
- 根据新实验反馈修改剩余实验
- 通过反复 API 调用实现隐式闭环
- 动态请求额外实验
- 使用 LangChain Agent 或类似框架执行任务
- 自主浏览网页或查询隐藏方程
- 通过代码执行访问实验环境

## 5.2 严格执行方式

LLM-only 每个任务分为两个阶段。

### Phase 1：Open-loop Experiment Planning

进行一次逻辑上独立的模型生成调用。

输入：

- Scientific task description
- Variables and units
- Experimental input domain
- Initial observations
- Experimental budget
- Required JSON output schema

输出：

提前确定的完整实验计划。

例如：

```json
{
  "experiments": [
    {"action": {"x": 1.0}},
    {"action": {"x": 2.0}},
    {"action": {"x": 3.0}}
  ]
}
```

这里只是 JSON 结构示例。

真实字段必须匹配对应物理模拟器的合法操作空间。

关键要求：

全部实验在收到任何新增实验结果之前一次性提交。

输出后立刻冻结计划。

计算计划内容的 SHA-256。

保存：

- 完整计划
- 冻结时间
- SHA-256
- 模型版本
- 生成参数
- Token 使用量

冻结后的计划不可修改。

### Phase 2：Batch Execution

实验调度器按冻结计划执行全部实验。

模型不得参与执行过程。

不得向模型返回中途实验观测。

例如：

```text
LLM generates all actions
          |
          v
Plan is frozen
          |
          v
Scheduler executes action 1
Scheduler executes action 2
Scheduler executes action 3
...
          |
          v
All observations collected
```

调度器在执行时不允许根据结果自动优化实验参数。

不能因为使用了 Python 调度器，就让系统获得额外智能能力。

调度器只能忠实执行冻结的实验序列。

若动作无效，按预注册规则处理，不得询问 LLM 如何修正。

### Phase 3：Final Law Inference

当全部观测完成后，再允许一次模型推理调用。

输入：

- 初始观测
- 原先冻结的实验计划
- 所有实验结果
- 统一的科学规律输出 Schema

输出：

- 候选科学规律
- 数学表达式
- 参数估计
- 相关变量
- 证据解释
- 对规律的预测
- 不确定性或局限

此阶段禁止新增实验。

如果模型要求再次实验，应记录为协议违规，不得执行。

## 5.3 API 层面强制隔离

LLM-only API 请求必须：

- 不传入任何实验工具定义
- 禁用或不提供 function calling
- 不启用 browser、code interpreter 或外部 Agent 工具
- 不提供实验模拟器访问权限
- 不提供额外检索接口
- 不包含隐藏规律、评分器和验证数据
- 不提供上一任务的隐藏答案

建议使用结构化输出。

JSON Schema 验证仅用于格式校验。

API 失败时，可以按照统一策略处理网络异常和格式错误，但不能通过格式重试补充新科学反馈，也不能无限追加推理。

对格式错误的重试、费用与额外 API 调用必须记录。

如果 Provider 无法保证所要求的调用限制，必须标记该 Provider 不满足严格基线要求。

## 5.4 必须进行 LLM-only 隔离测试

至少实现以下测试：

1. 模型不能直接调用实验 Oracle。
2. 实验计划冻结后不能修改。
3. 中间观测不能进入模型上下文。
4. Final Inference 后不能追加实验。
5. API 重试不能改变已冻结计划。
6. Runner 不含根据观测选择下一动作的策略。
7. 模型不能访问隐藏公式或评估文件。
8. 单个任务不能通过缓存获取其他任务的隐藏答案。

最关键的测试：

向模拟器返回两组不同的实验结果。

如果冻结计划完全相同，且之后的实验动作不随观测结果变化，则通过非自适应性测试。

需要在 `test_llm_isolation.py` 中提供自动化断言。

**不能仅在 Prompt 中要求模型不要做 Agent。必须由代码架构强制保证。**

---

# 6. Single Autonomous Agent 的实现

Agent 与 LLM-only 使用相同的基础 LLM API。

不要求使用 LangChain、AutoGen、CrewAI 等框架。

如果直接实现一个轻量 Agent Runner 更简单、更可控，可以自行实现。

但不要重新开发成熟的科学模拟器和评分器。

## 6.1 Agent 允许执行的操作

Agent 可以：

- 提出候选科学假设
- 根据目前观测选择下一次实验
- 查询实验结果
- 修改科学假设
- 调整后续实验
- 维护当前任务的实验历史
- 最终输出科学规律

Agent 不允许：

- 读取隐藏科学规律
- 读取评分器内部状态
- 修改物理模拟器
- 无限调用模型
- 无限追加实验
- 访问未授权外部资料
- 任意执行操作系统命令
- 读取其他任务的历史答案

## 6.2 Agent 流程

```text
Scientific Problem
       |
       v
Initial Observations
       |
       v
LLM proposes hypothesis
       |
       v
LLM selects experiment
       |
       v
Oracle returns measurement
       |
       v
LLM updates scientific belief
       |
       v
LLM selects next experiment
       |
       v
Repeat within budget
       |
       v
Final Scientific Law
```

Agent 必须通过受约束的 Experiment Oracle 执行科学实验。

不得将完整物理系统对象或源代码传入模型。

## 6.3 Agent 行为日志

每个决策周期记录：

- 当前预算
- 当前观测摘要
- 当前候选假设
- 被选择的实验动作
- 实验结果
- 假设是否修改
- API 调用次数
- Token 消耗
- 累计成本

这些信息是后续科学分析的基础。

注意：

不要求 API Provider 提供隐藏推理过程。

只记录可获得的模型输出、显式科学假设和工具调用行为。

不得声称已经记录不可访问的模型内部思维。

## 6.4 Agent 安全边界

主实验只允许一个正式动作：

`run_experiment(action)`

其中 `action` 为经过 Schema 验证的合法科学实验参数。

其他工具默认禁止。

如果后续增加代码计算工具，需要重新设计公平对照，不能悄悄只给 Agent 增加能力。

---

# 7. 任务集构建：目标 50–100 个客观任务

我们不从零手工设计 100 条科学定律。

优先从 NewtonBench 官方任务中筛选。

## 7.1 任务数量

建议：

- 第一阶段：12 个任务，测试工程流程
- 第二阶段：24 个任务，进行 Pilot Study
- 第三阶段：72 个任务，作为正式实验的初始配置
- 可扩展至 96 个任务

这里的任务数量是工程配置目标，不是已经论证充分的统计样本量。

正式规模需要根据 Pilot Study 的效应量与方差调整。

特别注意：

72 个任务不能直接写成“72 条独立自然规律”。

必须报告：

- 独立物理领域数
- 基础科学定律族数
- 规律变体数
- 具体科学任务数
- 每项任务的重复次数

## 7.2 任务分层抽样

尽可能覆盖 NewtonBench 的 12 个物理领域。

需要按照：

- Physics domain
- Law complexity
- System complexity
- Law variant / system identity

进行分层抽样。

建议在满足任务实际可用性的前提下，从每个领域选择约 6 个任务，合计 72 个。

不能只选择 Agent 容易成功的任务。

不能使用双方实际表现决定正式任务入选资格。

Pilot 与正式测试任务必须明确分开。

选择任务的随机种子必须固定。

输出：

`task_manifest.json`

至少包含：

```json
{
  "task_id": "example_id",
  "source": "NewtonBench",
  "domain": "example_domain",
  "law_complexity": "medium",
  "system_complexity": "simple",
  "split": "test",
  "seed": 42
}
```

这是 Manifest 格式示例，不是 NewtonBench 原生任务字段定义。

必须建立真实字段映射。

## 7.3 Task Validity Audit

不能因为某个任务出现在官方数据集中，就假定它一定适合我们的比较。

需要检查：

1. 是否可以合法重复查询？
2. 是否具有明确科学目标？
3. 是否能获得客观正确答案？
4. 是否存在训练或公开题目记忆风险？
5. 是否存在隐藏答案泄漏？
6. 是否能在相同预算内执行？
7. 是否能用独立数据验证？
8. 是否存在多个观测上等价的科学规律？
9. 是否属于明显无解或数值不稳定任务？
10. 是否支持非自适应与自适应策略的公平比较？

对于无法辨识的任务，不应简单判定模型失败。

需要识别并报告结构不可辨识或实验权限不足的问题。

特别检查：

某些任务可能无法在给定实验预算内区分竞争规律。

这种任务应事先标记，不能为了提高 Agent 胜率在看过结果后选择性删除。

## 7.4 数据污染控制

必须严格区分：

- 原始科学背景
- 公开基准的规律族
- 隐藏的目标规律
- 隐藏参数
- 观测数据
- 测试数据

模型不得获得隐藏规律或参数。

尽可能优先使用经过修改的科学规律变体。

公开 Benchmark 无法从根本上排除预训练记忆，因此必须保留污染风险说明。

如果上游项目已提供对记忆污染的处理机制，应优先复用，并检查是否适用于我们的实验。

---

# 8. 统一 Scientific Experiment Oracle

需要实现一个最小通用接口。

建议抽象：

`reset(task_id, seed)`

`get_public_task_description()`

`get_initial_observations()`

`get_action_schema()`

`run_experiment(action)`

`get_remaining_budget()`

`finalize()`

这些是我们希望包装出的接口，不代表原始 NewtonBench 一定存在同名函数。

请通过 Adapter 映射真实上游功能。

## 8.1 Oracle 职责

Oracle 必须：

- 验证动作是否合法
- 执行物理模拟
- 返回测量数据
- 统计实验次数
- 记录实验费用
- 保证噪声策略可复现
- 拒绝超预算操作
- 隔离隐藏规律与评估器

## 8.2 实验预算

初始建议：

`max_experiments = 6`

但必须确认这一预算适合任务结构。

部分物理系统可能需要更多实验才能识别规律。

应通过独立的先导试验或理论可辨识性分析确定预算，而不是根据哪组表现更好来调整。

预算至少包含：

- 实验调用次数
- 实验返回的测量点数
- LLM 输入 Token
- LLM 输出 Token
- API 调用次数
- API 费用
- 实际运行时间

主分析优先固定科学实验资源。

同时控制并报告推理资源差异。

如果 Agent 消耗更多 Token，不允许只强调成功率而忽略成本。

需要提供预算敏感性分析。

## 8.3 公平性约束

两个方法必须共享：

- 同一基础模型
- 同一模型版本
- 同一物理任务
- 同一初始数据
- 同一实验输入空间
- 同一实验次数限制
- 同一测量精度
- 同一评估器
- 同一独立验证数据
- 同一规则说明

刻意改变的变量：

**是否允许根据中途实验反馈动态选择后续实验。**

不能让 Agent 获得更多变量、更高精度的测量或额外隐藏信息。

当不同实验动作可能产生不同数量的数据点时，必须把返回信息量计入预算。

不能将一次返回 1000 个观测的动作和一次返回 1 个观测的动作不加区分地计为等价资源。

---

# 9. 真实规律与独立验证必须隔离

建立两个逻辑隔离的环境：

**Discovery Environment**

供 LLM 与 Agent 获取实验观测。

**Validation Environment**

供独立评价器验证最终发现。

Validation Environment 不允许在最终提交前接受模型查询。

验证内容包括：

- 未观察过的参数组合
- 未观察过的实验输入
- 独立随机种子
- 必要时使用不同噪声实现
- 不同实验条件下的科学规律预测

如果某个 NewtonBench 任务不支持这些验证方式，必须在任务能力表中说明。

不要以自制验证器替代官方评分器而不加说明。

优先复用官方评分，并另外添加客观的独立验证指标。

---

# 10. 主要科学指标

不要使用单一的 LLM-as-Judge 作为最终科学发现依据。

优先使用客观数学规律、独立观测和官方评分机制。

## 10.1 Primary Metric

**Validated Law Discovery Rate（VLDR）**

定义：

`VLDR = Validated Successful Tasks / All Evaluated Tasks`

任务成功必须满足预先注册的标准。

至少考虑：

1. 预测未观察实验结果的能力。
2. 正确恢复或等价表达目标科学规律。
3. 满足领域特定科学约束。

不能只通过拟合误差低就判定发现了正确机制。

## 10.2 规律结构恢复

优先使用 NewtonBench 自带的科学规律评价机制。

需要核查官方评分定义。

如果已有结构评分，优先复用。

不能直接将字符串完全一致作为唯一标准。

例如两个表达式：

`2*x + 2*y`

`2*(x+y)`

可能完全等价。

可使用 SymPy 进行表达式规范化及等价性检查。

但必须注意：

- 数值近似可能产生假等价
- 参数可能不可辨识
- 不同表达式可能只在有限区域内等价
- 不同领域可能需要不同的科学约束

因此结构等价与预测验证需要结合。

## 10.3 OOD Scientific Prediction

测试发现的规律能否预测新的实验条件。

可根据物理任务使用：

- RMSE
- Normalized RMSE
- Relative Error
- 官方领域评价指标

必须说明每种指标的定义、单位和归一化方式。

不同物理量之间不能不加归一化就平均 RMSE。

## 10.4 Discovery Efficiency

记录：

- 达到有效发现所需实验次数
- 总实验预算
- 总 Token
- 总 API 调用
- 总成本
- 总运行时间

由于主实验的最终规律可能只在完整预算结束后输出，因此不能假设每一步都已经产生可判定的科学发现。

如需绘制随实验次数变化的发现曲线，必须设计统一的中途评估快照协议。

不能利用只针对 Agent 的额外模型推理来制造成功率曲线。

## 10.5 Scientific Failure Analysis

记录：

- 错误规律结构
- 错误参数
- 科学规律过拟合
- 无法区分竞争假设
- 无效实验选择
- 实验预算耗尽
- API 调用失败
- 无法解析的模型输出
- 物理模拟失败
- 评价器失败

不能把 API 失败混入科学推理错误后直接得出笼统结论。

---

# 11. 最终科学规律输出格式

两组必须使用同一 Schema。

例如：

```json
{
  "task_id": "task_001",
  "hypothesis": "Candidate governing law",
  "equation": "y = a*x + b",
  "variables": ["x", "y"],
  "parameters": {
    "a": 1.0,
    "b": 0.0
  },
  "evidence": [
    "Observation-based justification"
  ],
  "predictions": [],
  "limitations": []
}
```

具体表达方式必须适配不同科学领域。

对于无法写成单个方程的任务，应通过域适配器实现合法输出。

不能为了统一 JSON 而改变原始物理问题的含义。

所有模型输出必须进行 Schema 校验。

评价器不得依赖自然语言印象给出随意分数。

---

# 12. LLM API 设计

必须采用可配置的 API Provider。

不能将 API Key 或具体模型名称硬编码。

`.env.example` 至少包含：

```text
LLM_API_KEY=
LLM_BASE_URL=
LLM_MODEL=
LLM_TIMEOUT=
```

允许兼容 OpenAI 风格 API，但不能假定所有第三方兼容接口都完整支持相同功能。

Provider 应支持：

- 同一基础模型
- 请求参数管理
- JSON 结构化输出
- Token usage
- API latency
- Retry policy
- Rate limit handling
- Error handling
- 请求级日志
- 成本估算

对于推理模型：

不要假定 temperature、seed 等参数总是受支持。

应查询当前 Provider 能力，记录实际使用参数。

如果无法指定随机种子，必须记录这一限制，并通过多次独立运行估计变异性。

禁止输出或提交 API Key。

## 12.1 Mock Provider

必须实现：

`MockLLMProvider`

用于：

- 无付费 API 的端到端测试
- CI 测试
- LLM-only 非自适应测试
- Agent 动作预算测试
- 错误恢复测试

Mock Provider 可以使用人为设定的测试响应。

但 Mock 结果必须标记为 Mock。

**任何 Mock 数据都不得出现在正式科研结果中。**

## 12.2 API 成本控制

默认情况下：

- 禁止直接运行完整 72–96 任务的付费实验。
- 首先执行免费 Mock 测试。
- 然后执行少量真实 API Smoke Test。
- 正式批量运行必须通过显式配置启用。

需要设置全局最大费用和最大 Token 预算。

超出预算时安全停止并记录状态。

---

# 13. Prompt 工程要求

必须分别编写：

`prompts/llm_plan.md`

`prompts/llm_discover.md`

`prompts/agent_system.md`

`prompts/agent_discover.md`

所有 Prompt 需要版本管理。

## LLM Planning Prompt

只允许输出完整实验计划。

不得包含：

- 动态重规划指令
- “观察后决定下一步”之类的行动建议
- 后续自动工具调用
- Agent Workflow
- ReAct 指令

可以要求模型根据当前知识选择信息量高的实验。

但是所有实验必须一次性确定。

## LLM Discovery Prompt

只允许根据已经获得的数据推断规律。

不得允许继续实验。

## Agent Prompt

明确允许：

- 科学假设生成
- 实验选择
- 实验反馈分析
- 假设修正
- 继续实验
- 最终规律提交

但所有行为都必须受到统一预算和工具权限限制。

## Prompt Fairness

双方需要具有：

- 相同科学背景
- 相同任务定义
- 相同目标
- 相同输出要求
- 相同变量及单位
- 相同最终评价标准

不要故意弱化 LLM-only Prompt。

例如，不允许一边要求普通 LLM “简单猜测公式”，另一边要求 Agent “详细科学推理”。

差异只能来自实验反馈和决策权限。

---

# 14. 统计分析设计

本项目必须按照配对实验进行分析。

对同一个科学任务：

- 执行 LLM-only
- 执行 Agent

尽可能匹配：

- 基础模型版本
- 初始条件
- 物理参数
- 观测噪声设置
- 科学任务
- 实验预算

每个任务初步建议进行 5 次独立运行。

正式重复次数和任务总数必须根据 Pilot Study 调整。

## 14.1 主效应

主要分析：

`Delta_VLDR = VLDR_Agent - VLDR_LLM`

报告：

- 两组成功率
- 成功率绝对差
- 95% 置信区间
- 配对分析结果
- 按物理领域划分的效果
- 按复杂度划分的效果

## 14.2 统计依赖

不能把同一物理规律的多个变体当作完全独立的科学发现。

同一任务的不同随机种子也不是新的独立科学任务。

建议采用：

- 分层统计模型
- 配对 Bootstrap
- 按规律族或领域聚类的稳健性分析
- 必要时使用混合效应模型

由于物理领域数量有限，应报告聚类推断的不确定性与敏感性，而不能把某一种统计检验视作绝对可靠。

## 14.3 不得进行的操作

禁止：

- 只报告 Agent 获胜任务
- 删除失败运行后不说明
- 根据测试集结果调整指标阈值
- 用同一任务反复调 Prompt，再把它当盲测
- 先看显著性再决定是否继续实验
- 把 72 个相关任务当作 72 条独立科学定律
- 把离线规律恢复称为发现人类未知自然规律

---

# 15. 实验结果可视化

至少生成三个 Panel。

## Figure 1a：Scientific Discovery Comparison

展示：

- LLM-only VLDR
- Agent VLDR
- 配对差异
- 95% CI

## Figure 1b：Generalization Performance

展示：

- 不同物理领域的规律恢复表现
- OOD Prediction Error
- 不同规律复杂度下的性能

## Figure 1c：Experimental Resource Efficiency

展示：

- Token 使用量
- API Cost
- 实验调用次数
- Validated Discovery per Cost
- 在可比较预算下的性能

同时生成一个代表性的 Case Study。

Case Study 必须如实展示双方的实验计划、观测、最终规律及独立验证结果。

不能仅挑选最好看的案例而不说明选择规则。

图表应当达到科研论文可用质量：

- PDF / SVG 矢量图
- PNG
- 清晰单位
- 误差线
- 样本量
- 明确的统计口径

Mock 图必须显著标注模拟数据，不得与真实实验图混淆。

---

# 16. 必须实现的工程测试

## Test 1：LLM-only 非自适应性

在相同初始输入下：

先生成一次固定实验计划。

然后人为改变中间实验观测。

验证：

后续执行动作完全相同。

Plan Hash 必须保持不变。

这是最重要的验收测试。

## Test 2：Agent 自适应能力

在一个专门构造的测试环境中：

给 Agent 两种不同的科学反馈。

检查 Runner 是否允许模型选择不同后续实验。

这个测试只证明 Agent 架构支持自适应行为，不要求真实模型一定选择不同动作。

可以使用 Mock Provider 确保测试确定性。

## Test 3：实验预算

超过最大实验次数时必须拒绝执行。

禁止隐式额外查询。

## Test 4：隐藏规律泄漏

模型输入中不能包含：

- Ground-truth equation
- Hidden coefficients
- Simulator source code
- Evaluation answer
- Validation targets

检查：

- Prompt
- Tool result
- 日志
- 错误消息
- 可访问文件
- 运行环境权限

如果代码执行工具可访问隐藏规律所在文件，则隔离失败。

建议将模型可访问的执行环境与隐藏模拟器、评分器隔离。

仅依赖 Prompt 保密不够。

## Test 5：重复实验

相同任务、相同随机种子和相同动作序列，在支持确定性复现的模拟环境中，应得到相同结果。

真实 API 输出不保证逐字复现，因此必须保存原始请求与响应元数据。

## Test 6：评价器独立性

模型不得访问独立验证数据。

评分器不能因为答案来自 Agent 或 LLM 而采用不同标准。

## Test 7：端到端测试

用 Mock Provider 完整执行：

任务加载 → 实验计划 → 实验执行 → 科学规律提交 → 评分 → 结果保存 → 统计分析 → Figure 生成。

---

# 17. 运行阶段

请按以下顺序推进。

## Stage 1：Repository Audit

完成：

- 克隆源仓库
- 检查许可证
- 锁定版本
- 识别任务接口
- 验证现有模拟器
- 形成复用计划

交付：

`docs/open_source_audit.md`

## Stage 2：Minimal Working Experiment

选择 1 个可用 NewtonBench 任务。

打通：

- LLM-only
- Agent
- Simulator
- Evaluator
- Results

首先使用 Mock API。

确认两个 Runner 都能得到合法评分。

## Stage 3：Strict Baseline Verification

完成全部非自适应隔离测试。

如果不通过，禁止进入下一阶段。

## Stage 4：12-task Engineering Validation

使用 12 个覆盖不同物理领域的任务。

测试：

- 环境稳定性
- 行动合法性
- 评分准确性
- Token 记录
- 数据泄漏
- 结果保存与恢复

## Stage 5：24-task Pilot

进行小规模真实 API 实验。

估计：

- VLDR
- Task variance
- Run variance
- Domain effects
- API Cost
- Failure rates

根据预实验决定正式实验数量。

不得使用正式盲测任务调 Prompt。

## Stage 6：Formal Evaluation

使用预先冻结的任务 Manifest、Prompt、评分阈值和统计方案。

运行 72 个左右任务，必要时扩展。

该阶段必须支持：

- 断点恢复
- 错误重试
- 任务去重
- 结果持久化
- 实验审计

默认不自动启动大规模付费运行。

---

# 18. 需要生成的文档

至少提供：

`README.md`

完整安装和运行说明。

`docs/open_source_audit.md`

开源项目调查与复用说明。

`docs/scientific_question.md`

科学问题、假设、对照组、指标、结论边界。

`docs/experiment_protocol.md`

实验组定义、控制变量、预算、随机化、执行顺序。

`docs/llm_non_agent_guarantee.md`

重点证明 Traditional LLM 为什么没有转变成 Agent。

必须包含代码实现位置、调用时序和自动化测试证据。

`docs/task_selection.md`

任务筛选过程、任务数量、来源、去重和有效性检查。

`docs/evaluation_protocol.md`

科学规律验证标准、评价器、阈值与统计分析。

`docs/reproducibility.md`

随机种子、环境、依赖、Commit、Prompt 版本、模型版本。

`docs/limitations.md`

明确讨论：

- 公开规律记忆
- 自适应与非自适应实验的区别
- Agent 额外计算开销
- 规律辨识与原创科学发现的区别
- 物理任务泛化限制
- 与经典自适应算法尚未比较的限制

---

# 19. 最终 CLI 要求

提供清晰可用的命令行接口。

至少支持以下操作，具体参数可根据工程实际实现：

- `audit`：检查上游资源
- `prepare`：生成任务 Manifest
- `smoke-test`：运行最小工程测试
- `pilot`：执行小规模实验
- `run`：执行指定实验
- `evaluate`：评价结果
- `analyze`：统计与绘图

支持参数：

- Runner 类型
- Model
- Task split
- Task ID
- Experimental budget
- Random seed
- Output directory
- Resume
- Dry run
- API cost ceiling

所有重要配置必须保存在文件中，不能只通过临时修改源代码改变实验。

---

# 20. 最终验收标准

工程完成时，必须达到：

- [ ] 成功安装并复用至少一个已有科学规律发现环境。
- [ ] 能够自动枚举和选择有效科学任务。
- [ ] LLM-only 使用严格冻结的开环实验计划。
- [ ] LLM-only 无法根据中途反馈修改实验。
- [ ] Agent 能够根据反馈自主选择后续实验。
- [ ] 两者共享相同基础模型、实验权限和预算定义。
- [ ] 隐藏规律与验证数据对模型不可见。
- [ ] 实验次数与 Token、调用和费用可以审计。
- [ ] 双方输出能够被同一评价器评分。
- [ ] 完成 Mock 端到端实验。
- [ ] 全部关键安全、预算和隔离测试通过。
- [ ] 可生成任务级结果和统计图。
- [ ] 支持断点恢复及重复运行。
- [ ] 所有依赖和开源来源可追溯。
- [ ] 生成完整科研方法学文档。

此外必须报告：

1. 实际完成了哪些任务。
2. 实际运行了哪些测试。
3. 哪些测试通过。
4. 哪些测试失败。
5. 哪些功能尚未实现。
6. 是否使用真实付费 API。
7. 哪些结果仅来自 Mock。
8. 怎样启动正式实验。

不能把未执行的测试写成已通过。

---

# 21. 重要的科研原则

你必须始终牢记：

**我们不是为了证明 Agent 一定优于 LLM，而是为了公平检验 Agent 是否拥有额外的科学规律发现能力。**

允许出现：

- LLM 胜过 Agent
- Agent 胜过 LLM
- 两者没有显著差异
- Agent 在简单任务优势不明显
- Agent 消耗更多成本却没有更好结果
- Agent 在复杂任务中产生更大优势

不要人为优化任务或评价器使 Agent 获胜。

对于任何结果，都必须给出客观解释。

不允许修改官方评分使结果更符合研究预期。

本工程必须支持可证伪的科学结论。

---

# 22. 现在开始执行

不要停留在方案描述，也不要仅生成 TODO 文件。

请立即按照以下顺序工作：

**第一步：** 检查当前工作目录和已有代码，不覆盖用户现有研究内容。

**第二步：** 调查并克隆 NewtonBench，验证真实环境接口和评分机制。

**第三步：** 完成开源资源复用审计。

**第四步：** 创建独立科研实验工程，优先实现 NewtonBench Adapter。

**第五步：** 编写严格的 LLM-only Runner 和 Single Agent Runner。

**第六步：** 实现统一实验预算、隐藏答案隔离及评价协议。

**第七步：** 使用 Mock Provider 完成至少一个真实科学模拟任务的端到端实验。

**第八步：** 完成非自适应性、权限、评分、预算和可复现性测试。

**第九步：** 实现任务选择、结果保存、统计和 Figure 绘制。

**第十步：** 输出工程总结、已验证功能、限制和正式运行命令。

如遇到接口、依赖或许可证问题，优先寻找成熟替代方案。

只有当外部访问、权限、密钥或真实资源确实阻断执行时，才说明阻塞原因和已经完成的部分。

未经明确授权，不要启动大规模付费 API 实验。

最终我要获得的是：

**一个真正可以运行、具有严格 LLM/Agent 对照、能够发现和验证科学规律、并且可以用于后续高水平论文实验的科研系统，而不是一个演示性质的 Agent 项目。**