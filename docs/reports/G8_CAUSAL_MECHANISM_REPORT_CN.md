# G8 因果机制实验报告（中文）

> 状态：**正式实验已完成；统计结果已生成；结论保留为“需外部科学复核”，不自动宣称因果机制成立。**
>
> 实验时间：2026-10-15（Asia/Hong_Kong）
> 机制：V（公开数学/领域后果的再评估机制）
> G8 skill ZIP SHA-256：`4086360f393b8b3232ec700105a87738246438a16e4e97daad1de8a5e3a09bb2`

## 1. 实验目标与边界

G8 检验的是：在相同公开任务、相同模型快照、相同预算约束下，给 G3/G4 工作流加入一个经过 G7 审核的机制 V，是否改变最终决策的正确率，并且这种改变能否区别于 sham、额外思考、格式变化和更多计算量。

本轮只冻结并执行机制 V。G7 中 L/U 没有被擅自升级为可执行机制：原始 G7 证明图边数为 0，U eligible 为 0，因此它们不具备本轮 G8 的可审计中间状态证据。

模型只看公开 case、公开 proof graph、公开机制输出和白名单工具。私有 oracle 只在实验结束后的独立评分步骤读取，未传入 adapter 或模型可见 trace。

## 2. G7 到 G8 的输入审核

G8 使用的 G7 经过 source-only trace review 后的派生 handoff，而不是直接使用原始未审核 handoff。审核结果如下：

| 指标 | 数值 |
|---|---:|
| G7 public cases | 92 |
| G7 theory families | 23 |
| G7 checkpoint rows | 184 |
| G7 完成 checkpoint | 153 |
| G7 provider error checkpoint | 31 |
| G8 选用 theory families | 9 |
| G8 选用 public cases | 18（9 个 CF1、9 个 CF2） |
| G8 选用 public checkpoints | 54 个 case-replicate 基础 checkpoint |
| G8 输入审计状态 | `AUDITED_INPUT_STRUCTURE_ONLY` |
| demo/mock 输入 | 0 |
| 私有 oracle 是否进入模型输入 | 否 |

G8 的 9 个 family 是从 rep0 中真实完成的 public checkpoint 派生而来；rep1/rep2 的相同公开 checkpoint 由真实 provider 补跑并合并。补跑与合并均只保留实际完成的 checkpoint，不对 provider error 做结果插补。

## 3. 冻结设计

正式计划文件：`results/g8_causal_mechanism/formal-20261015T030000Z-16workers/g8_run_plan.jsonl`

| 设计项 | 冻结值 |
|---|---|
| workflow/profile | theory_benchmark；G3/G4 derived pair |
| mechanism | V |
| arms | A/B/C/D/E/F 六臂 |
| replicate | 3 |
| theory families | 9 |
| case 数 | 18 |
| 总计划行 | 324 = 18 × 6 × 3 |
| workers | 16 |
| provider RPS | 4 |
| 每行最大 model calls | 8 |
| 每行最大 tool calls | 64 |
| 每行最大 tokens | 32,000 |
| 每行最大 cost | 0.25 USD |
| provider internal retries | 0 |
| 外层失败重试 | 2 |
| plan SHA-256 | `e784dfdb108e0d7534557a3c20e83959f3054ee0daa3cccef5ae9f44986296dd` |

六臂含义：

| arm | 含义 |
|---|---|
| `A_G3_BASE` | G3，不执行机制 V |
| `B_G3_REAL_M` | G3，执行真实机制 V |
| `C_G3_SHAM_M` | G3，执行 schema-matched 但语义中性的 sham 机制 |
| `D_G3_EXTRA_THINK` | G3，加入预定的额外思考/一致性 pass 作为计算量对照 |
| `E_G4_PLUS_M` | G4 derived workflow，执行真实机制 V |
| `F_G4_MINUS_M` | G4 derived workflow，关闭机制 V |

## 4. 实际执行完整性

执行摘要文件：`results/g8_causal_mechanism/formal-20261015T030000Z-16workers/raw/execution_summary.json`

| 执行状态 | 数量 | 占计划 |
|---|---:|---:|
| `PASS` | 284 | 87.654% |
| `TECHNICAL_FAILURE` | 40 | 12.346% |
| `MISSING` | 0 | 0% |
| 总计 | 324 | 100% |

40 个技术失败没有被删除、重标或当作错误答案；它们在 G8 评分中按 ITT 规范留在 all-planned 分母中。16 workers 是并发度，不是独立样本数；统计独立单位是 9 个 theory families。

独立输出审计文件：`results/g8_causal_mechanism/formal-20261015T030000Z-16workers/audit/g8_independent_audit.json`。

审计结果：324/324 result files 存在；324/324 通过结果结构审计；无意外 run id；无 mock；模型可见 trace 未发现 G8 禁止的私有字段；`public_only`、`budget_enforced`、冻结 model snapshot 和各臂的必需机制事件均通过结构核验。技术失败仍按失败保留，独立审计没有把它们升级为成功。

## 5. 资源使用

资源明细：`results/g8_causal_mechanism/formal-20261015T030000Z-16workers/score/g8_resource_usage.csv`

| 资源指标 | 总量 |
|---|---:|
| result rows | 324 |
| total tokens | 1,448,684 |
| model calls | 818 |
| tool calls | 977 |
| provider cost | 2.557378 USD |
| 单行最大实际 cost | 0.022333 USD |
| 单行预算上限 | 0.25 USD |

所有统计均以实际 usage 为准；未把 worker 数量当作样本量，也未把失败调用从成本和失败率中抹除。

## 6. 六臂结果指标

评分文件：`results/g8_causal_mechanism/formal-20261015T030000Z-16workers/score/g8_arm_scores.csv`。

| arm | planned | valid completed | all-planned 正确 | all-planned accuracy | valid-only accuracy | coverage | W→C rate | C→W rate | technical failures |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A_G3_BASE | 54 | 42 | 33 | 0.6111 | 0.7857 | 0.7778 | 0.2500 | 0.1190 | 12 |
| B_G3_REAL_M | 54 | 49 | 40 | 0.7407 | 0.8163 | 0.9074 | 0.6667 | 0.1667 | 5 |
| C_G3_SHAM_M | 54 | 47 | 39 | 0.7222 | 0.8298 | 0.8704 | 0.3333 | 0.0476 | 7 |
| D_G3_EXTRA_THINK | 54 | 39 | 37 | 0.6852 | 0.9487 | 0.7222 | 0.5000 | 0.0238 | 15 |
| E_G4_PLUS_M | 54 | 54 | 43 | 0.7963 | 0.7963 | 1.0000 | 0.4615 | 0.0976 | 0 |
| F_G4_MINUS_M | 54 | 53 | 47 | 0.8704 | 0.8868 | 0.9815 | 0.7692 | 0.0732 | 1 |

说明：`all-planned accuracy` 是预注册主结果口径；技术失败、未完成和无有效决策均不会被当成正确。`valid-only accuracy` 只用于诊断，不能替代 ITT 主结果。W→C 是初始错误到最终正确，C→W 是初始正确到最终错误。

## 7. 预设配对效应

文件：`g8_paired_effects.csv`。置信区间为按 theory family 聚类的 bootstrap 95% 区间。

| 对比 | case-replicate pairs | 独立 families | all-planned 差值 | 95% CI |
|---|---:|---:|---:|---:|
| B−A：真实机制−G3 基线 | 54 | 9 | +0.1296 | [0.0370, 0.2407] |
| B−C：真实机制−sham | 54 | 9 | +0.0185 | [−0.0926, 0.1481] |
| B−D：真实机制−额外思考 | 54 | 9 | +0.0556 | [−0.1481, 0.2407] |
| E−F：G4 真实机制−G4 关闭机制 | 54 | 9 | −0.0741 | [−0.2037, 0.0556] |

这里 E−F 是本轮 derived pair，不是历史 G4 ablation 的回填。B−A 的区间不跨 0，但 B−C、B−D 和 E−F 均跨 0；因此结果不能单凭 B−A 证明机制 V 的独立因果贡献。

## 8. 机制目标失败过程指标

文件：`g8_targeted_failure_effects.csv`。该指标由独立程序根据 assigned mechanism event contract 和 execution status 审核，是“机制交付/流程失败”指标，不是私有答案真值，也不是科学正确性标签。

| 对比 | 失败率差值 | 95% CI |
|---|---:|---:|
| B−A | −0.1296 | [−0.2407, −0.0370] |
| B−C | −0.0370 | [−0.1111, 0.0370] |
| B−D | −0.1852 | [−0.3148, −0.0556] |
| E−F | −0.0185 | [−0.0556, 0.0000] |

该表不能被解释为“科学错误率降低了同样的数值”。它只说明分配的机制事件和正式执行是否按合同出现。

## 9. Q 审计、私有 oracle 与信息隔离

Q 审计文件：`audit/g8_q_audit.jsonl`；过程审计文件：`audit/g8_process_audit.jsonl`。

本轮共生成 30 条需要 Q 审计的 REVISE 行；每条 Q 记录包含独立审计 verifier hash、evidence reference 和 revised claim hash。Q 审计只检查公开 trace 的结构与证据存在性，不读取 expected decision，也不把模型自报的“正确”当作独立证明。

准确率评分使用 `results/g6_counterfactual/formal-20261013T000000Z/private_oracle_verified23.jsonl`，但只在外部 scorer 中读取。adapter、模型输入、`model_visible_trace` 和 G8 public verifier 均没有加载该文件。G8 public verifier 只计算可由公开 problem 参数得到的公开数值，quality 标记为 `PUBLIC_COMPUTATION_ONLY`，不输出 decision label。

## 10. G9 交接与最终解释

G9 交接文件：`results/g8_causal_mechanism/formal-20261015T030000Z-16workers/g9_handoff.json`。

其状态是 `PENDING_INDEPENDENT_SCIENTIFIC_REVIEW`，而不是自动 `GO`。当前最稳妥的科学结论是：

1. G8 的 324 行正式 provider 实验已经完整执行并完成统计；
2. 真实机制相对 G3 baseline 的主指标提高，但相对 sham、额外思考和 G4 关闭机制的对比没有得到跨过 0 的区间证据；
3. 因此本轮观察到的是“与机制效应相容的结果”，不是已经排除更多计算、提示变化、采样差异和 workflow 差异后的因果机制确证；
4. 不能把 G8 结果写成 V 机制已被证明，也不能把 G9 的中间状态路径当作已发现；后续若执行 G9，必须继续使用独立中间状态干预和审计。

## 11. 可复核文件索引

- 冻结计划：[g8_run_plan.jsonl](../../results/g8_causal_mechanism/formal-20261015T030000Z-16workers/g8_run_plan.jsonl)
- 执行摘要：[execution_summary.json](../../results/g8_causal_mechanism/formal-20261015T030000Z-16workers/raw/execution_summary.json)
- 独立输出审计：[g8_independent_audit.json](../../results/g8_causal_mechanism/formal-20261015T030000Z-16workers/audit/g8_independent_audit.json)
- 六臂统计：[g8_arm_scores.csv](../../results/g8_causal_mechanism/formal-20261015T030000Z-16workers/score/g8_arm_scores.csv)
- 配对效应：[g8_paired_effects.csv](../../results/g8_causal_mechanism/formal-20261015T030000Z-16workers/score/g8_paired_effects.csv)
- 资源明细：[g8_resource_usage.csv](../../results/g8_causal_mechanism/formal-20261015T030000Z-16workers/score/g8_resource_usage.csv)
- G9 交接：[g9_handoff.json](../../results/g8_causal_mechanism/formal-20261015T030000Z-16workers/g9_handoff.json)
