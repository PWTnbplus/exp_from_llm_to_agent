# G0–G7 实验数据总账（指标用途版）

## 1. 阅读规则

这份报告只回答三件事：

1. 这个指标用来观察什么；
2. 当前实际数据是多少；
3. 数据是否完整、是否缺失、是否可以解释。

不在这里展开指标的计算公式或执行教程。

### 量化口径

- `x/y` 表示已观测数量/应观测数量；后面同时给出百分比时，百分比只描述覆盖率或有效率，不把缺失结果当作失败成功。
- `N/A（0/y 已完成）` 表示没有可用于计算的正式结果，不等价于“0 个成功”。
- `0 hits/y requests` 表示在已审计请求中未发现该事件；`0/1 review` 表示该项独立复核尚未完成。
- 配置类指标同时列出“目标/上限”和“实际请求/记录数”；两者不混作科学结果。

| 标记 | 含义 |
|---|---|
| **有数据** | 已找到对应真实产物或审计产物，可以直接报告数值 |
| **部分数据** | 有部分批次/部分阶段数据，但不能代表完整阶段 |
| **缺失** | 没有对应结果文件，不能填写数值 |
| **不可计算** | 有输入，但缺少必要条件、有效回答或可资格样本，不能得到该指标 |
| **未验证** | 有本地数值，但外部数学、统计、模型快照、账单或 provenance 门禁未通过 |
| **非确认** | 有数值，但运行存在协议污染或其他原因，只能作故障/历史数据 |
| **不适用** | 该阶段按设计不产生该指标 |

数据截点：`2026-10-15`；主要审计来源：`docs/audits/cycle-20261015T083400Z-28/`。本报告范围到 G7，不包含 G8。

## 2. G0–G7 阶段总览

| 阶段 | 这一阶段主要看什么 | 关键实际数据 | 完整性 |
|---|---|---|---|
| G0 | 研究问题、任务注册、冻结协议和评估边界 | registry `108`；工程验证 `24/24`；正式目标 `720` 个任务-重复-臂单元（72 tasks、5 replicates、2 arms）；有效正式结果 `0/720` | **部分数据；完整正式科学结果覆盖 0/720** |
| G1 | 冻结计划 LLM-only 的工程隔离 | 工程 `24/24`；真实 formal provider 请求 `0`；正式科学结果 `0/720` | **工程数据完整；科学结果覆盖 0/720** |
| G2 | 固定 calculator 工具的权限和执行 | 配置 model calls `2`、calculator steps `4`；真实 formal provider 请求 `0`；正式科学结果 `0/720` | **规范有数；科学结果覆盖 0/720** |
| G3 | 固定反思/Tools+Iteration 对照流程 | G6 corrected `276/552`；G7 fork plan `644/1288`；G1–G5 formal provider 请求 `0` | **运行数据有数；外部发布复核 `0/1`** |
| G4 | 自适应 Agent 流程 | G6 corrected `276/552`；G7 fork plan `644/1288`；G1–G5 formal provider 请求 `0` | **运行数据有数；外部发布复核 `0/1`** |
| G5 | bounded memory、proof graph 和独立 family | graph `1309/1309`；合格 family `23/24`；dependency edge `0/92` | **数据有数；L/U 可计算 cases `0/92`** |
| G6 | CF1–CF4 前提反事实响应 | corrected plan/response/handoff 均 `552/552`；family `23`；workers `2` | **结构覆盖 100%；科学发布门禁 `0/1`** |
| G7 | V/L/U/Q 失败定位 | corrected state `1288/1288`；checkpoint `184/184`；completed `1285/1288=99.767%`；Q valid `20/1288=1.553%` | **执行覆盖高；诊断有效率 1.553%，发布门禁 `0/1`** |

## 3. G0 数据

### 3.1 G0 任务与样本数据

| 指标 | 用途 | 数据 | 状态/说明 |
|---|---|---:|---|
| 首阶段 registry 任务 | 确认可供实验选择的任务范围 | 108 | **有数据** |
| 工程验证任务 | 检验 runner、权限、trace 和结果格式 | 12 | **有数据** |
| 工程验证 runner | 确认两条对照路径都被执行 | 2（LLM-only / Agent） | **有数据** |
| 工程验证结果 | 确认工程记录是否成对落盘 | 24/24 完成 | **有数据** |
| pilot 规划 | 评估先导阶段任务覆盖 | 12 domains、5 matched replicates | **规划值；不是完整正式结果** |
| formal 规划 | 规定正式科学样本范围 | `720` 个目标单元：72 tasks、5 replicates、2 arms | **规划值；完整正式结果缺失** |
| 统计独立单位 | 防止 task variant/replicate 被误当成独立定律 | `1` 类独立单位：law-family/module | **有配置** |
| 默认实验预算 | 记录每个任务的可用实验资源 | `6` experiments、`120` measurements/任务配置 | **有配置** |
| 随机种子 | 保证任务选择可复现 | 42 | **有配置** |
| 上游 NewtonBench commit | 固定上游来源 | `912a4ba5f4356ddd06acc16e44460ca30be4abc2` | **本地记录有；远程独立确认缺失** |

### 3.2 G0 评估指标

| 指标 | 用途 | 规则/目标值 | 实际状态 |
|---|---|---|---|
| Numeric fit | 看提交的规律能否拟合验证观测 | relative RMSE ≤ `1e-5` | **N/A（有效正式评估 `0/720`）** |
| Structural recovery | 看提交规律的可执行结构是否与目标结构一致 | canonical AST fingerprint | **N/A（有效正式评估 `0/720`）** |
| OOD fit | 看规律能否在未见边界/外推条件下预测 | relative RMSE ≤ `1e-5` | **N/A（有效正式评估 `0/720`）** |
| Mechanistic validity | 看结构恢复与 OOD 是否同时成立 | 需两项同时有效 | **N/A（联合有效结果 `0/720`）** |
| Validated success | 作为一次定律恢复成功的总判定 | 需 numeric、structural、OOD 全部有效 | **N/A（完成正式评估 `0/720`，不能记为 0 个成功）** |
| VLDR | 观察经过验证的定律恢复比例 | 研究主终点 | **N/A（可用正式分母 `0/720`）** |
| OOD finite-point 最低要求 | 防止无有效点时错误判定 | 至少 `16` 个 finite points/任务 | **N/A（满足性记录 `0/720`）** |
| Official evaluator 状态 | 确认是否使用官方 NewtonBench 评估器 | official evaluator 目标 `1/1` | **实际官方 evaluator `0/1`；项目自有 restricted evaluator `1/1`** |

### 3.3 G0 文件盘点

| 目录类别 | JSON 文件 | mock 标记 | 用途 | 状态 |
|---|---:|---:|---|---|
| pilot | 25 | `0/25=0%` | 保存 pilot 结果 | **有数据** |
| engineering validation | 25 | `0/25=0%` | 保存工程验证结果 | **有数据** |
| final smoke | 3 | `0/3=0%` | 保存最终 smoke 结果 | **有数据** |
| theory | 1 | `1/1=100%` | theory 示例/工程产物 | **有数据；明确 mock** |
| theory_agent_smoke | 1 | `1/1=100%` | theory Agent smoke 产物 | **有数据；明确 mock** |

### 3.4 G0 缺失或不能报告的项目

| 指标 | 用途 | 当前状态 | 原因 |
|---|---|---|---|
| G0–G5 完整正式 VLDR | 判断正式定律恢复成功率 | **N/A（正式有效结果 `0/720`）** | 现有 G1–G5 工程阶段真实 provider 请求为 `0`；不能把工程/mock 记录当正式科学结果 |
| 官方 NewtonBench 数值判定 | 确认结果是否通过官方评估 | **不可用（官方 evaluator `0/1`）** | 当前 evaluator 标记为项目自有 restricted evaluator |
| 上游远程 provenance | 独立确认上游代码来源 | **未验证（独立确认 `0/1`）** | 外部网络/远程交付受阻 |

## 4. G1–G5 数据

### 4.1 能力和资源指标

| 组 | 指标 | 用途 | 配置值 | 实际数据状态 |
|---|---|---|---:|---|
| G1 | model calls | 限制冻结 LLM 的模型交互次数 | 目标 NewtonBench `2`、theory `1`；实际 formal provider `0` | **正式结果覆盖 `0/720`** |
| G1 | tools | 确认 LLM-only 不使用工具 | 允许工具 `0`；工程记录 `24/24` | **工程隔离有审计** |
| G1 | planning | 确认计划是否提前冻结 | 冻结计划 `1/1`；中途重规划 `0` | **工程隔离有审计** |
| G1 | memory/retrieval | 确认无隐藏记忆和检索 | memory `0`；retrieval `0` | **工程隔离有审计** |
| G1 | transport retry | 防止失败重试改变实验预算 | 配置重试 `0`；额外 transport retry `0` | **有配置** |
| G2 | model calls | 限制固定计算辅助的交互规模 | 目标 `2`；实际 formal provider `0` | **正式结果覆盖 `0/720`** |
| G2 | calculator steps | 限制固定计算操作数量 | 上限 `4` steps；formal records `0` | **工程边界有审计** |
| G2 | tool | 确认只能做公开表达式计算 | 允许工具 `1` 种：`calculate_expression`；其他允许数 `0` | **工程边界有审计** |
| G3 | model calls | 限制固定两遍反思 | 目标 `2`；正式 G1–G5 provider `0` | **正式结果覆盖 `0/720`** |
| G3 | tools | 确认原始 G3 不使用工具 | 允许工具 `0`；工程记录 `24/24` | **工程边界有审计** |
| G3 | planning | 区分固定反思和自适应 Agent | fixed passes `2`；adaptive replans `0` | **G6 使用 `1` 个单独修正版 profile** |
| G4 | model calls | 限制 Agent 交互规模 | 目标 `8`；正式 G1–G5 provider `0` | **正式结果覆盖 `0/720`** |
| G4 | experiments | 限制 Agent 可选择的实验数 | 上限 `6`；formal records `0` | **有配置** |
| G4 | tools | 确认可用工具边界 | 允许工具 `2` 种：`run_experiment`、`calculate_expression` | **工程边界有审计** |
| G4 | feedback | 确认行动可依赖公开观测 | adaptive profile `1/1`；固定 profile `0/1` | **有规范** |
| G5 | model calls | 限制带 memory 的 Agent 交互规模 | 目标 `10`；正式 G1–G5 provider `0` | **正式结果覆盖 `0/720`** |
| G5 | tool calls | 限制工具操作次数 | 上限 `10`；formal records `0` | **有规范** |
| G5 | memory items | 限制 run-local memory 大小 | 上限 `32` items；formal records `0` | **有规范** |
| G5 | retrieval | 防止外部检索引入额外信息 | retrieval calls `0`；工程记录 `24/24` | **工程边界有审计** |

### 4.2 G1–G5 实际工程数据

| 指标 | 用途 | 数据 | 状态/说明 |
|---|---|---:|---|
| 工程验证任务 | 检验两条 runner 是否都能执行 | 12 | **有数据** |
| 工程验证 runner | 确认比较两侧均被执行 | 2 | **有数据** |
| 工程结果记录 | 检查是否有缺失结果 | 24/24 | **有数据** |
| 配对记录 | 检查同一任务两侧能否匹配 | 12 | **有数据** |
| Mock Agent−LLM 平均差 | 检查 mock 对照是否引入额外差异 | 0.0 | **有数据；仅工程证据** |
| Mock bootstrap CI | 检查 mock 差异是否稳定为零 | `[0.0, 0.0]` | **有数据；仅工程证据** |
| zero-function 负控制 | 检查错误规律是否被错误判为成功 | 成功数 0 | **有数据** |
| G1–G5 历史真实 provider 请求 | 确认是否存在正式真实模型结果 | 0 | **有数据；因此正式科学指标缺失** |
| G1–G5 正式 VLDR | 判断各组定律恢复率 | **N/A（有效正式评估 `0/720`）** | **不能用 mock/工程结果替代** |
| G1–G5 正式 accuracy | 比较组间任务正确率 | **N/A（有效正式回答 `0/720`）** | **真实 provider 正式批次缺失** |
| G1–G5 正式 cost/token | 统计正式模型资源代价 | formal provider `0`；正式 cost/token **N/A** | **没有对应正式 provider 批次** |

### 4.3 G5 proof graph 数据

| 指标 | 用途 | 数据 | 状态 |
|---|---|---:|---|
| proof graph 文件 | 检查 G5 是否产生推导图 | 1309 | **有数据** |
| graph sibling 完整性 | 检查每个 graph 是否有配套产物 | 1309/1309 | **有数据** |
| source-only family | 统计不读取私有输入的独立理论族 | 24 | **有数据** |
| 独立通过 family | 作为 corrected G6/G7 合法分母 | 23/24 | **有数据** |
| 排除 family | 记录不能进入科学分母的来源 | 1/24，TB-L1-010 | **有数据；永久排除** |
| private input 读取 | 检查 graph 审计是否泄漏私有输入 | `0/1309` graph 命中 | **审计通过** |
| answer key 读取 | 检查 graph 审计是否泄漏答案 | `0/1309` graph 命中 | **审计通过** |
| corrected public cases | 作为 G6/G7 公开题数量 | 92 | **有数据** |
| dependency edge | 支持 L 的边级传播分析 | 0/92 cases 有边 | **不可计算边级 L** |
| eligible U cases | 支持 U 的非终值节点分析 | 0/92 | **不可计算 U 转移** |

## 5. G6 数据

### 5.1 G6 运行完整性

| 指标 | 用途 | 数据 | 状态 |
|---|---|---:|---|
| corrected families | 确认可用独立理论族数量 | 23 | **有数据** |
| public cases | 确认公开反事实题数量 | 92 | **有数据** |
| counterfactual types | 检查四类前提干预是否覆盖 | `4/4`：CF1、CF2、CF3、CF4 | **有数据** |
| arms | 比较 G3 与 G4 | `2/2`：G3、G4 | **有数据** |
| replicates | 检查重复运行覆盖 | 3 | **有数据** |
| workers | 检查并行配置 | 2 | **有数据；符合指定配置** |
| plan rows | 检查冻结任务是否完整 | 552 | **有数据** |
| response rows | 检查模型响应是否完整 | 552 | **有数据** |
| handoff rows | 检查是否能交接给 G7 | 552 | **有数据** |
| structural review | 检查文件结构、数量和哈希 | `1/1 PASS` | **有数据** |
| scientific release | 检查是否可作科学发布 | `0/1 allowed`（false） | **未验证/禁止发布** |

### 5.2 G6 反事实决策结果

| 指标 | 用途 | G3 | G4 | 组间差异 | family CI（pp） | p | 状态 |
|---|---|---:|---:|---:|---:|---:|---|
| CF1 decision accuracy | 看能否识别关键前提翻转 | 37/69（53.623%） | 43/69（62.319%） | +8.696 pp | `[-1.449, 20.290]` | `0.263176` | **有数据；未外部统计复核** |
| CF2 decision accuracy | 看能否保持无关/等价改变后的原结论 | 69/69（100%） | 69/69（100%） | 0 pp | `[0, 0]` | N/A | **有数据；未外部统计复核** |
| CF3 decision accuracy | 看能否识别边界弱化并作出合法响应 | 44/69（63.768%） | 25/69（36.232%） | −27.536 pp | `[-42.029, -11.594]` | `0.000546` | **有数据；revision 另有缺失** |
| CF4 decision accuracy | 看信息不足时是否保持不确定 | 41/69（59.420%） | 49/69（71.014%） | +11.594 pp | `[-1.449, 24.638]` | `0.133801` | **有数据；未外部统计复核** |
| ALL decision accuracy | 看全部四类干预的总体决策表现 | 191/276（69.203%） | 186/276（67.391%） | −1.812 pp | `[-7.609, 4.348]` | `0.635308` | **有数据；不可作为 superiority 结论** |
| CF3 revision validity | 检查 CF3 的修订命题是否真的合法 | — | — | `0/138` valid | N/A | N/A | **不可支持 CF3 修订结论** |

### 5.3 G6 资源数据

| 指标 | 用途 | 数据 | 状态 |
|---|---|---:|---|
| model requests/responses | 记录真实模型调用规模 | `1826/1826`；model-call cap 使用 `1826/4608=39.627%` | **有数据** |
| tool calls/results | 记录真实工具调用规模 | `1796/1796`；tool-call cap 使用 `1796/3456=51.968%` | **有数据** |
| total tokens | 记录模型资源消耗 | `3,454,449/4,608,000=74.966%` | **有数据** |
| trace-audit observed cost | 记录本地 trace 估算成本 | `USD 6.057783/200=3.029%` | **有数据；不是外部 billing proof** |
| model-call hard cap | 防止调用无限增长 | 4608 | **配置有；独立账单/快照缺失** |
| tool-call hard cap | 防止工具调用无限增长 | 3456 | **配置有** |
| token hard cap | 防止 token 超额 | 4,608,000 | **配置有** |
| cost hard cap | 防止付费超预算 | USD 200 | **配置有** |

### 5.4 G6 缺失/不可计算/未验证

| 指标 | 用途 | 状态 | 原因 |
|---|---|---|---|
| 外部数学/领域复核 | 确认 23 个 family 的数学合法性 | **0/1 review 完成** | 尚无独立外部 review |
| 外部统计复核 | 确认 CI、p 值和 family clustering | **0/1 review 完成** | 尚无独立统计 review |
| immutable model snapshot | 确认模型权重不可变 | **0/1 snapshot 完成** | provider metadata 不是 weight fingerprint |
| 独立 billing export | 确认真实费用 | **0/1 export 完成** | 只有本地 trace cost |
| G6-C hidden arm | 检查无答案锚定的额外对照 | **0/1 executed；按设计不适用** | corrected run 只执行 G3/G4 主臂 |
| G6 因果机制结论 | 判断 Agent 是否因机制而优越 | **N/A（机制干预单元 `0`）** | G6 只提供反事实响应数据，不是机制干预验证 |

## 6. G7 数据

### 6.1 G7 计划和输入数据

| 指标 | 用途 | 数据 | 状态 |
|---|---|---:|---|
| public cases | 作为 G7 失败定位题 | 92 | **有数据** |
| theory families | 作为独立统计/分层单位 | 23 | **有数据** |
| groups | 比较 G3 与 G4 | `2/2`：G3、G4 | **有数据** |
| diagnostic arms | 比较不同局部信息辅助 | `7/7`：D0、D1、D2、D3、L_ONLY、U_ONLY、V_ONLY | **有数据** |
| replicate | 检查独立重复覆盖 | 1 | **有数据；只有单重复** |
| fork plan rows | 检查所有诊断路径是否计划 | 1288 | **有数据** |
| checkpoints | 为同题各诊断臂提供共同起点 | 184 | **有数据** |
| workers | 检查并行执行规模 | 16 | **有数据** |
| private oracle read by model | 检查 G6 私有答案是否泄漏 | 原始 `0/2960` hits；修正版 `0/3774` hits | **审计通过** |
| route metadata read by model | 检查 `cf_type`、`theory_family_id` 是否泄漏 | 原始 `2960/2960` calls 命中；修正版 `0/3774` | **原始非确认；修正版通过** |

### 6.2 原始 G7 数据（非确认批次）

原始批次因模型请求包含 `cf_type`、`theory_family_id` 路由元数据，以下数值只能用于描述失败和历史执行，不能作为确认性科学结论。

| 指标 | 用途 | 数据 | 状态 |
|---|---|---:|---|
| planned fork rows | 判断计划规模 | `1288/1288` | **有数据；非确认** |
| completed states | 判断执行覆盖 | `993/1288=77.096%` | **有数据；非确认** |
| checkpoint missing | 记录 checkpoint 缺失规模 | `217/1288=16.848%` | **有数据；必须保留** |
| provider error | 记录 provider/runtime 失败规模 | `78/1288=6.056%` | **有数据；必须保留** |
| completed checkpoints | 判断共同起点覆盖 | `153/184=83.152%` | **有数据；非确认** |
| checkpoint provider error | 记录 checkpoint provider 失败 | `31/184=16.848%` | **有数据；必须保留** |
| Q audit rows | 检查所有计划行是否接受 Q 审计 | `1288/1288` | **有数据** |
| Q valid | 判断独立 Q 是否有效 | `3/1288=0.233%` | **有数据；有效率过低** |
| trace files | 判断原始轨迹是否落盘 | `1255/1288=97.438%` | **有数据；与计划不等同** |
| model calls | 记录资源消耗 | 2960 | **有数据** |
| tool calls | 记录工具消耗 | 1925 | **有数据** |
| total tokens | 记录 token 消耗 | 6,494,545 | **有数据** |
| observed cost | 记录本地 trace 成本 | USD 10.260655 | **有数据；不是外部账单** |
| private prompt hits | 检查私有答案是否泄漏 | `0/2960` requests | **审计通过** |
| route metadata hits | 检查路由信息是否泄漏 | `cf_type=2960/2960`；`theory_family_id=2960/2960` | **协议污染；非确认** |

### 6.3 原始 G7 每臂结果（仅历史/故障数据）

| 组/臂 | completed | completion rate | all-planned decision accuracy（正确/92） | valid-answer accuracy（正确/completed） | missing/invalid |
|---|---:|---:|---:|---:|---:|
| G3/D0 | 56/92 | 60.870% | 38/92=41.304% | 38/56=67.857% | 36/92 |
| G3/D1 | 61/92 | 66.304% | 46/92=50.000% | 46/61=75.410% | 31/92 |
| G3/D2 | 59/92 | 64.130% | 44/92=47.826% | 44/59=74.576% | 33/92 |
| G3/D3 | 59/92 | 64.130% | 47/92=51.087% | 47/59=79.661% | 33/92 |
| G3/L_ONLY | 59/92 | 64.130% | 40/92=43.478% | 40/59=67.797% | 33/92 |
| G3/U_ONLY | 59/92 | 64.130% | 38/92=41.304% | 38/59=64.407% | 33/92 |
| G3/V_ONLY | 59/92 | 64.130% | 45/92=48.913% | 45/59=76.271% | 33/92 |
| G4/D0 | 87/92 | 94.565% | 51/92=55.435% | 51/87=58.621% | 5/92 |
| G4/D1 | 85/92 | 92.391% | 56/92=60.870% | 56/85=65.882% | 7/92 |
| G4/D2 | 80/92 | 86.957% | 58/92=63.043% | 58/80=72.500% | 12/92 |
| G4/D3 | 77/92 | 83.696% | 53/92=57.609% | 53/77=68.831% | 15/92 |
| G4/L_ONLY | 85/92 | 92.391% | 53/92=57.609% | 53/85=62.353% | 7/92 |
| G4/U_ONLY | 85/92 | 92.391% | 54/92=58.696% | 54/85=63.529% | 7/92 |
| G4/V_ONLY | 82/92 | 89.130% | 57/92=61.957% | 57/82=69.512% | 10/92 |

表中 `正确/92` 与 `正确/completed` 的整数计数沿用现有审计数值整理；它们仍属于原始污染批次，不能替代确认性 score 文件。

这些指标的用途是观察每个 diagnostic arm 的完成情况、最终决策表现和有效回答表现；但由于原始 prompt 污染，**均标记为非确认数据**。

### 6.4 G7 terminal retry 数据

| 批次 | 用途 | plan rows | completed | completion rate | checkpoint missing | provider error | 分类合计 | Q valid | tokens | cost | 状态 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| retry1 | 回收原始 terminal failures | 295 | 185 | 62.712% | 90 | 20 | 295/295 | 2 | 1,385,282 | USD 2.266946 | **独立批次；不合并** |
| retry2 | 回收 retry1 terminal failures | 110 | 79 | 71.818% | 20 | 3 | 102/110（另有 8 行未在三类单列） | 0 | 601,606 | USD 1.006640 | **独立批次；不合并** |
| retry3 | 回收 retry2 缺失 ID | 31 | 16 | 51.613% | 12 | 3 | 31/31 | 0 | 156,629 | USD 0.271911 | **独立批次；不合并** |

这些 retry 的用途是恢复执行记录，不是重新定义原始实验的成功结果。失败行仍然保留。

### 6.5 protocol-corrected G7 full retry（当前修正版主数据）

| 指标 | 用途 | 数据 | 状态 |
|---|---|---:|---|
| plan rows | 检查修正版是否覆盖原计划 | 1288 | **有数据** |
| canonical states | 检查每个计划 ID 是否有最终选定状态 | `1288/1288=100%` | **有数据** |
| completed | 检查 provider 执行成功数 | `1285/1288=99.767%` | **有数据** |
| provider error | 记录剩余真实 provider failure | `3/1288=0.233%` | **有数据；必须保留** |
| missing state IDs | 检查 canonical merge 是否丢 ID | `0/1288=0%` | **审计通过** |
| duplicate completed IDs | 检查是否重复计入完成记录 | `0/1285=0%` | **审计通过** |
| checkpoints planned | 检查共同起点规模 | 184 | **有数据** |
| checkpoints completed | 检查共同起点是否完整 | 184/184 | **有数据** |
| Q rows | 检查 Q 是否逐行进入独立审计 | `1288/1288=100%` | **有数据** |
| Q valid | 检查独立 Q 是否真正有效 | `20/1288=1.553%` | **有数据；有效比例仍低** |
| model calls | 记录修正版资源规模 | 3774 | **有数据** |
| tool calls | 记录修正版工具规模 | 2356 | **有数据** |
| total tokens | 记录修正版 token 消耗 | 8,147,109 | **有数据** |
| observed cost | 记录修正版本地 trace 成本 | USD 13.009913 | **有数据；不是外部账单** |
| format retry | 记录格式修复调用 | `302/302` scheduled/requests；占计划 `23.447%` | **有数据；最多一次/流程** |
| new scientific observation | 检查格式 retry 是否增加新实验信息 | `0/302` retries 产生新观测 | **审计通过** |
| route metadata hits | 检查原始污染是否修复 | `0/3774` model calls | **审计通过** |
| forbidden private prompt hits | 检查私有信息泄漏 | `0/3774` model calls | **审计通过** |

### 6.6 G7 V/L/U/Q 数据

| 指标 | 用途 | 数据 | 状态 |
|---|---|---:|---|
| V label：CF1/CF3 | 观察局部验证对关键/边界干预的判断 | `2/4` CF 类型为 `CONTRADICTED` | **有局部标签；科学解释未验证** |
| V label：CF2 | 观察等价前提的局部判断 | `1/4` CF 类型为 `SUPPORTED` | **有局部标签；科学解释未验证** |
| V label：CF4 | 观察信息不足时的局部判断 | `1/4` CF 类型为 `INDETERMINATE` | **有局部标签；科学解释未验证** |
| L dependency edges | 观察受影响 claim 的边级定位 | 0/92 cases | **不可计算边级 L** |
| U eligible cases | 观察非终值状态更新 | 0/92 | **不可计算 U transition** |
| U 是否注入最终答案 | 检查是否发生答案泄漏 | `0` injection events | **审计通过** |
| original Q valid | 观察原始批次独立复核有效性 | `3/1288=0.233%` | **有数据；非确认** |
| corrected Q valid | 观察修正版独立复核有效性 | `20/1288=1.553%` | **有数据；不足以支撑强结论** |
| Q invalid | 观察无法通过独立复核的行 | 原始 `1285/1288=99.767%`；修正版 `1268/1288=98.447%` | **有数据；必须保留** |
| G7 replicate | 判断是否可估计重复稳定性 | 1 | **不足；重复稳定性不可计算** |

### 6.7 G7 指标结果状态

| 指标 | 用途 | 原始 G7 | 修正版 full retry | 状态 |
|---|---|---:|---:|---|
| all-planned final decision accuracy | 看全计划范围的最终决策表现 | 原始历史 `14/14` arm rows；修正版确认 score `0/14` | **未生成可确认 score** | 原始非确认；修正版不可确认 |
| valid-answer accuracy | 看有效解析回答的决策表现 | 原始历史 `14/14` arm rows；修正版确认 score `0/14` | **未生成可确认 score** | 修正版缺失 |
| W→C recovery | 看错误初始判断是否被恢复 | 原始非确认值存在 `1` 批；修正版可确认分组结果 `0/1` | **未生成可确认分组结果** | 修正版不可计算 |
| C→W damage | 看辅助是否损坏原本正确判断 | 原始非确认值存在 `1` 批；修正版可确认分组结果 `0/1` | **未生成可确认分组结果** | 修正版不可计算 |
| first observable error V/L/U/Q | 定位第一次可观察失败位置 | 可确认分组统计 `0/1`；现有基础字段：L `0/92`、U `0/92`、Q valid `20/1288` | **未生成可确认分组统计** | 修正版不可计算 |
| paired D0→D1 | 看加入 V 后诊断性变化 | 原始非确认值 `1` 批；修正版可确认结果 `0/1` | **未生成可确认结果** | 原始非确认；修正版缺失 |
| paired D1→D2 | 看增加 L 后诊断性变化 | 原始非确认值 `1` 批；修正版可确认结果 `0/1` | **未生成可确认结果** | 原始非确认；修正版缺失 |
| paired D2→D3 | 看增加 U 后诊断性变化 | 可资格配对 `0`；修正版可确认结果 `0/1` | **未生成可确认结果** | 不可计算 |
| paired U_ONLY→D0 | 看 U 单因素诊断性变化 | 可资格配对 `0`；修正版可确认结果 `0/1` | **未生成可确认结果** | 不可计算 |
| Q-independent pass rate | 看外部复核是否有效 | 3/1288 | 20/1288 | **有数据；有效率过低** |

## 7. G0–G7 缺失、失败和未验证项目汇总

| 项目 | 影响阶段 | 当前状态 | 具体数据/原因 |
|---|---|---|---|
| 完整正式 G0–G5 provider 结果 | G0–G5 | **缺失 `0/720`** | 历史 G1–G5 工程阶段真实 provider 请求为 `0` |
| 完整 G0–G5 VLDR | G0–G5 | **不可计算 `0/720` 已完成** | 缺少完整正式科学运行结果 |
| G5 edge-based L | G5/G7 | **不可计算 `0/92`** | 92/92 public cases 的 dependency edge 为 0 |
| G5 U transition | G5/G7 | **不可计算 `0/92`** | eligible U cases 为 0/92 |
| G6 CF3 valid revision | G6 | **不可支持 `0/138`** | revision audit valid=0/138 |
| G6 数学/领域外部复核 | G6 | **缺失 `0/1`** | 尚未取得独立 review |
| G6 独立统计复核 | G6 | **缺失 `0/1`** | 尚未取得独立 review |
| G6 immutable model snapshot | G6 | **缺失 `0/1`** | 只有 provider model metadata |
| G6 external billing | G6 | **缺失 `0/1`** | 只有 trace-audit observed cost |
| G7 原始批次无偏结果 | G7 | **非确认 `2960/2960` 命中路由元数据** | 模型请求含 `cf_type` 和 `theory_family_id` |
| G7 corrected Q 有效率 | G7 | **部分数据/不足 `20/1288=1.553%`** | 有效 Q 数量不足 |
| G7 corrected 分臂 score | G7 | **缺失/不可确认 `0/14`** | 当前审计有 state/Q/资源，但没有可作为确认结果的独立分臂 score |
| G7 重复稳定性 | G7 | **不可计算 `1` replicate** | 正式 corrected retry 只有 1 replicate |
| G7 L/U 机制恢复 | G7 | **不可计算 `0/92`** | graph edge=0、eligible U=0 |
| 上游远程 provenance | 全部 | **未验证 `0/1`** | 外部网络/远程交付阻断 |
| 科学发布 | G6/G7 | **禁止 `0/1 allowed`** | `scientific_release_allowed=false`；外部门禁未关闭 |

## 8. 关键哈希与数据入口

| 数据 | SHA-256/入口 |
|---|---|
| G6 plan | `c60b14205f061fa2178b9d0a42074d9957a460bea2cf4e06b841acbe4b0bbde0` |
| G6 responses | `97022fa9ac84dad61c24c98fbc1fee2ba2b357ee853eccd9614cc348da8312fa` |
| G6 handoff | `ec51c3114b84da9f818d0f6407794e42454cbe87565aa0baaf60081c61602c02` |
| 原始 G7 plan | `549c39a9508fae3c7611564f0cca6022ade5dda67f52d8cc6c1fbd51b9633eb3` |
| 原始 G7 states | `714e53654e070a74bc026c11c7396fc243b8e4b72a45e3ed4e9025d8fe66efef` |
| 原始 G7 Q audit | `7090520110215c742259dc5598d0c37dc14a155dfd93dc165d011a3e460d27ff` |
| corrected G7 plan | `be6c5550dfc453110b3f526f9ed6cf865bb0c1df5c3891b87dc0a23d6cf4c2e5` |
| corrected G7 states | `45fa85c25fada1fe6653d582e7167b1f54bf7551f80c2b847ca5badddec93bc2` |
| corrected G7 Q audit | `95349ef7fa28b9e3a63290c5bda4e67be007027b2f12cce29aa656bc252543` |
| 最新完整性审计 | `docs/audits/cycle-20261015T083400Z-28/g0_g8_integrity.json` |
| G7 失败审计 | `docs/audits/cycle-20261015T083400Z-28/g7_failure_taxonomy.json` |
| issue ledger | `docs/state/issues.json` |

## 9. 最终数据结论

| 总体门槛 | 量化结果 | 含义 |
|---|---:|---|
| G0–G5 正式科学结果 | `0/720` 有效 formal task-arm-replicate 单元 | 不能计算正式 VLDR/accuracy |
| G6 corrected 结构记录 | plan/response/handoff `552/552`；structural review `1/1` | 文件结构覆盖完整 |
| G6 corrected CF 决策 | G3 `191/276=69.203%`；G4 `186/276=67.391%` | 有数值，但外部复核 `0/1` |
| G6 CF3 revision | `0/138` valid | 该修订结论不可支持 |
| G7 corrected 执行状态 | state `1288/1288`；completed `1285/1288=99.767%` | 执行覆盖高，仍有 3 个 provider error |
| G7 corrected Q 审计 | valid `20/1288=1.553%`；invalid `1268/1288=98.447%` | 确认性诊断有效率不足 |
| G7 corrected L/U | edge `0/92`；eligible U `0/92` | L/U 机制指标不可计算 |
| G6/G7 外部发布 | `0/1 allowed` | 当前禁止科学发布 |

1. G0–G5 中，任务注册、工程验证、能力隔离和 G5 graph 审计有数据；完整正式 G0–G5 provider 科学结果缺失，不能报告正式 VLDR 或组间科学优越性。
2. G6 corrected 结构数据完整，CF1–CF4 的 decision 指标已有数值；但 CF3 revision valid 为 0/138，外部数学/统计/模型/账单门禁未完成。
3. G7 原始批次有大量执行数据，但因路由元数据进入模型请求，只能作为非确认故障数据。
4. G7 corrected full retry 的 state、checkpoint、资源和 Q 审计数据完整，但 Q valid 只有 20/1288；同时 L/U 因 edge 和 eligible U 为 0 不可计算，修正版确认性分臂 score 缺失。
5. 因此当前最准确的总状态是：**数据已整理，部分指标可报告；若标记为“缺失/不可计算/未验证”的项目不能用推测、补零或历史批次替代。**
