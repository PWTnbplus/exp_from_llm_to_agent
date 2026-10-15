# G0–G7 实验完整数据报告（当前审计版）

## 0. 报告范围、数据截点与解释规则

本报告汇总 G0–G7 的指标、样本量、完成/失败状态、资源用量、统计量、哈希和科学门禁状态。按用户要求只展开指标，不逐条罗列每个案例。

| 项目 | 值 |
|---|---|
| 数据截点 | 2026-10-15（Asia/Hong_Kong；最新审计 cycle `20261015T083400Z-28`） |
| 审计范围 | G0–G7；本报告不纳入 G8 |
| 最新代码状态 | 分支 `autopilot/scientific-law-discovery`；报告生成前 HEAD `b4f5fc3` |
| 当前 host 测试 | `108 passed` |
| 最新完整性审计 | `COMPLETED_WITH_EXTERNAL_REVIEW_CAVEATS` |
| 科学发布状态 | 未允许（`scientific_release_allowed=false`） |

本报告严格区分三种状态：

1. **工程通过**：代码、schema、权限边界、trace、merge 或统计程序按规则运行。
2. **数据审计通过**：计划行、缺失行、失败行、哈希和派生 canonical 数据可追溯。
3. **科学发布允许**：还需要独立数学/领域复核、外部统计复核、不可变模型快照和计费证据、上游 provenance，以及足够的有效 provider 输出。

失败记录始终保留；重试批次是独立批次，不能与原批次做 pooled scientific estimate。原始 G7 因模型提示中出现了路由元数据，作为**不可确认批次**保留；修正后的 G7 另行报告。

## 1. G0–G7 总览

| 阶段 | 目标 | 主要数据规模 | 当前数据状态 | 科学发布状态 |
|---|---|---:|---|---|
| G0 | 问题定义、任务注册、冻结评估协议 | 108 个直接测量任务；正式规划 72×5×2 | 协议与门禁已落盘；上游远程 provenance 仍受阻 | 未发布 |
| G1 | 冻结计划 LLM-only | 2 次模型调用；无工具/反馈/重试 | 能力隔离与工程门禁通过 | 不作科学结论 |
| G2 | 固定计算辅助 | 2 次模型调用；4 个 calculator steps | 权限边界通过 | 不作科学结论 |
| G3 | 固定两遍反思/Tools+Iteration 诊断基线 | G6 中 276 行；G7 中 644 个 fork 计划行 | 结构可审计 | 不作科学结论 |
| G4 | 自适应单 Agent | G6 中 276 行；G7 中 644 个 fork 计划行 | 结构可审计 | 不作科学结论 |
| G5 | Agent + run-local memory 与 proof graph | 1309 个 graph；23/24 family 独立通过 | 依赖边审计为 0；U 不具备资格 | 未发布 |
| G6 | 23 family 的 4 类反事实验证 | 552 计划/552 response/552 handoff；2 workers | 结构审计通过；revision valid=0 | 未发布 |
| G7 | 失败定位与 V/L/U/Q 诊断 | 92 public cases；1288 fork；184 checkpoint | 修正版 canonical 完整，仍有 3 个 provider failure、Q valid 20/1288 | 未发布 |

## 2. G0：问题定义、任务注册与评估协议

### 2.1 研究对象与主要判定

G0 将问题限定为：在相同模型、任务、初始信息、测量精度和实验预算下，反馈控制的实验选择是否提高科学定律恢复率。主评估对象是 VLDR（Validated Law Discovery Rate）：提交的定律同时通过预注册数值拟合、结构恢复和留出 OOD 拟合的任务比例。

这不是脱离协议的“Agent 是否优于 LLM”命题，而是当前模拟器、任务族、预算和验证器下的受限比较。

### 2.2 任务、样本与阈值

| 指标 | 数值/规则 |
|---|---:|
| 第一阶段 registry 直接测量任务 | 108 |
| 工程验证任务 | 12 |
| 工程验证 runner | 2（LLM-only / Agent） |
| 工程验证结果记录 | 24 |
| Pilot 规划 | 12 domains × 5 matched replicates |
| 正式规划 | 72 tasks × 5 replicates × 2 arms |
| 统计独立单位 | `NewtonBench law-family/module`，不是任务变体或 replicate |
| 默认实验预算 | 6 experiments；计划记录为 120 measurements |
| deterministic seeded validation interventions | 128 |
| deterministic legal OOD interventions | 64 |
| numeric/OOD relative RMSE 阈值 | ≤ `1e-5` |
| OOD 有限点最低要求 | ≥ 16 |
| 注册随机种子 | 42 |
| 选择策略 | outcome-blind、分层 round-robin |
| 失败分母 | provider、parse、budget、missing-arm 全部保留 |

### 2.3 G0 持久化产物盘点

| 产物类别 | JSON 文件数 | mock 标记文件数 | 解释 |
|---|---:|---:|---|
| pilot | 25 | 0 | 持久化 pilot 结果 |
| engineering validation | 25 | 0 | 持久化工程验证结果 |
| final smoke | 3 | 0 | 最终 smoke 产物 |
| theory | 1 | 1 | theory 级工程/示例产物，明确标记 mock |
| theory_agent_smoke | 1 | 1 | theory Agent smoke，明确标记 mock |

### 2.4 G0 门禁

| 门禁 | 结果 |
|---|---|
| 任务注册、manifest、frozen-plan 设计 | 通过并有代码/测试 |
| 公共输入与隐藏评估器边界 | 已实现；ground truth 不进入模型消息、普通结果或 trace |
| 预算账本与失败分母规则 | 已实现 |
| NewtonBench 远程 commit | 配置为 `912a4ba5f4356ddd06acc16e44460ca30be4abc2` |
| 上游远程 provenance / GitHub delivery | 外部网络阻断，未能独立确认 |
| evaluator 状态 | `official_numeric_evaluator=false`；当前为项目自有受限 numeric evaluator |

## 3. G1–G5：能力隔离与工程基线

### 3.1 冻结能力矩阵

| 组别 | 模型调用约束 | 工具 | 反馈/规划 | memory | retrieval | transport retry |
|---|---:|---|---|---|---|---:|
| G1 | NewtonBench 2；theory 1 | 无 | frozen plan / one-shot | 无 | 无 | 0 |
| G2 | 2 | `calculate_expression`；4 compute steps | 固定计算辅助 | 无 | 无 | 0 |
| G3 | 2 | 原始定义无工具 | fixed two-pass reflection | 无 | 无 | 0 |
| G4 | 8 | `calculate_expression`、`run_experiment` | observation-conditioned adaptive | 无 | 无 | 0 |
| G5 | 10 | 同 G4 | adaptive | run-local，32 items | 无 | 0 |

任何越权工具、检索、memory、额外模型调用、额外实验或 transport retry 均应触发 `POLICY_CHECK`/`ERROR` 并使该运行失败。G6 采用单独冻结的 `g6_protocol_g3_tools_iteration` 修正版；不能把 G6 修正版反写成 G3 原始能力定义。

### 3.2 G1–G5 工程验证数据

| 指标 | 数值 |
|---|---:|
| 任务数 | 12 |
| runner 数 | 2 |
| 结果记录 | 24/24 完成 |
| 配对数 | 12 |
| Mock Agent−LLM 平均差 | 0.0 |
| Mock bootstrap 95% CI | [0.0, 0.0] |
| zero-function 负控制 | 验证成功数 0 |
| 历史 G1–G5 工程阶段真实 provider 请求 | 0 |
| 当前全仓 host suite | 108 passed |

这些数值只证明工程流程、配对、隔离和负控制可运行，不能作为模型科学能力或 Agent 优势的证据。

### 3.3 G5 proof graph 与独立 family

| 指标 | 数值 |
|---|---:|
| `proof_graph.json` 文件 | 1309 |
| 具有预期 sibling 的 graph | 1309/1309 |
| source-only 独立 family | 24 |
| `VERIFIED_INDEPENDENT_B` | 23/24 |
| `EXCLUDED_INVALID_SOURCE` | 1/24（TB-L1-010） |
| private input 是否读取 | 否 |
| answer key 是否读取 | 否 |
| corrected G6/G7 family 分母 | 23 |
| public cases | 92（23 family × 4 CF） |
| 92 public cases 的 dependency edge | 0/92 有边；`edge_count=0` |
| eligible U cases | 0/92 |

TB-L1-010 未填充、未重标、未恢复。由于公开公式与标准隐性突变选择平衡不一致且 validity 节点未解决，该 family 从 corrected denominator 永久排除。由于 92 个案例均没有可审计的 dependency edge，L 不能报告可信的边级传播，U 不能被人为注入或据此判定。

## 4. G6：修正后的反事实验证

### 4.1 设计、完成度与资源

| 指标 | 数值 |
|---|---:|
| artifact root | `results/g6_counterfactual/protocol-g3tools-v2-20261014T030000Z` |
| protocol profile | `g6_protocol_g3_tools_iteration` |
| corrected family | 23 |
| counterfactual | CF1、CF2、CF3、CF4 |
| replicate | 3 |
| arm | G3 / G4 |
| 计划行 | 552 = 23 × 4 × 3 × 2 |
| G3 行 | 276 |
| G4 行 | 276 |
| 每个 arm×CF | 69 |
| workers | 2 |
| plan / response / handoff | 552 / 552 / 552 |
| model requests / responses | 1826 / 1826 |
| tool calls / results | 1796 / 1796 |
| total tokens | 3,454,449 |
| trace-audit observed cost | USD 6.057783 |
| revision audit | 138 行；valid=0 |
| raw nonmonotonic trace | 0（derived canonical trace view） |
| structural review | pass |
| scientific release allowed | false |

### 4.2 G6 decision 指标

这里的 accuracy 是 G6 decision/original-claim 的协议指标，不是最终 VLDR，也不是因果效应。

| CF | G3 正确/69 | G3 准确率 | G4 正确/69 | G4 准确率 | G4−G3 | family bootstrap 95% CI | McNemar p |
|---|---:|---:|---:|---:|---:|---|---:|
| CF1 | 37 | 53.623% | 43 | 62.319% | +8.696 pp | [-1.449, 20.290] pp | 0.263176 |
| CF2 | 69 | 100.000% | 69 | 100.000% | 0.000 pp | [0.000, 0.000] pp | 不适用 |
| CF3 | 44 | 63.768% | 25 | 36.232% | -27.536 pp | [-42.029, -11.594] pp | 0.000546 |
| CF4 | 41 | 59.420% | 49 | 71.014% | +11.594 pp | [-1.449, 24.638] pp | 0.133801 |
| **ALL** | **191/276** | **69.203%** | **186/276** | **67.391%** | **-1.812 pp** | **[-7.609, 4.348] pp** | **0.635308** |

CF3 的 revision audit 为 138 行且 `valid=0`。因此“识别原命题无效”和“给出有效修订命题”不能合并为一个 accuracy。

### 4.3 G6 发布门禁

| 门禁 | 状态 |
|---|---|
| corrected plan/response/handoff 结构完整 | 通过 |
| 失败和缺失记录审计 | 通过；本次结构上无失败行 |
| 独立 Grade-B 数学/领域复核 | 尚未完成 |
| immutable model weight fingerprint | 缺失 |
| 独立 billing export | 缺失 |
| 独立统计复核 | 尚未完成 |
| 上游 NewtonBench provenance | 远程确认受阻 |
| G6 科学发布 | 不允许 |

## 5. G7：Failure Localization

### 5.1 冻结输入与计划

| 指标 | 数值 |
|---|---:|
| public cases | 92 |
| theory families | 23 |
| counterfactual | 4（CF1–CF4） |
| groups | G3、G4 |
| diagnostic arms | D0、D1、D2、D3、L_ONLY、U_ONLY、V_ONLY（7） |
| replicate | 1 |
| fork 总计划 | 1288 = 92 × 2 × 7 × 1 |
| checkpoint 计划 | 184 = 92 × 2 |
| G3 / G4 fork | 644 / 644 |
| protocol-corrected workers | 16 |
| checkpoint 是否从 G6 回填 | 否；均为新的 provider call |
| provider 是否读取 G6 private oracle/model response | 否 |

### 5.2 原始 G7（不可确认、非 pooled）

原始 G7 的 prompt 向模型暴露了 `cf_type` 和 `theory_family_id` 等路由元数据。该批次保留用于故障审计，但不作为 confirmatory scientific result；所有 retry 都与它分开，不与它 pooled。

| 指标 | 原始 G7 值 |
|---|---:|
| root | `formal-20261014T030000Z-16workers` |
| plan rows | 1288 |
| canonical state rows | 1288 |
| completed | 993（77.096%） |
| `checkpoint_missing` | 217 |
| `provider_error` | 78 |
| checkpoint completed / provider_error | 153 / 31 |
| Q rows / Q valid | 1288 / 3（0.233%） |
| trace files | 1255 |
| model calls | 2960 |
| tool calls | 1925 |
| total tokens | 6,494,545 |
| observed cost | USD 10.260655 |
| route metadata hits（审计字段） | `cf_type=2960`；`theory_family_id=2960` |
| forbidden private prompt hits | `{}` |
| confirmatory status | 不允许 |

原始 G7 的已生成诊断指标也只能作为历史描述。由于 prompt contamination，不能将下表解读为无偏的失败机制或 G3/G4 优势证据。

| 组别/arm | 完成/92 | 完成率 | 全计划 decision accuracy | 有效回答 accuracy | 缺失/无效 |
|---|---:|---:|---:|---:|---:|
| G3/D0 | 56 | 60.870% | 41.304% | 67.857% | 36 |
| G3/D1 | 61 | 66.304% | 50.000% | 75.410% | 31 |
| G3/D2 | 59 | 64.130% | 47.826% | 74.576% | 33 |
| G3/D3 | 59 | 64.130% | 51.087% | 79.661% | 33 |
| G3/L_ONLY | 59 | 64.130% | 43.478% | 67.797% | 33 |
| G3/U_ONLY | 59 | 64.130% | 41.304% | 64.407% | 33 |
| G3/V_ONLY | 59 | 64.130% | 48.913% | 76.271% | 33 |
| G4/D0 | 87 | 94.565% | 55.435% | 58.621% | 5 |
| G4/D1 | 85 | 92.391% | 60.870% | 65.882% | 7 |
| G4/D2 | 80 | 86.957% | 63.043% | 72.500% | 12 |
| G4/D3 | 77 | 83.696% | 57.609% | 68.831% | 15 |
| G4/L_ONLY | 85 | 92.391% | 57.609% | 62.353% | 7 |
| G4/U_ONLY | 85 | 92.391% | 58.696% | 63.529% | 7 |
| G4/V_ONLY | 82 | 89.130% | 61.957% | 69.512% | 10 |

原始 G7 配对诊断的 `both_completed` 与均值差如下；“不可估计”不是零效应：

| 比较 | 两者均完成 | G3 均值差 | G4 均值差 | 可估计性 |
|---|---:|---:|---:|---|
| D1 − D0 | 138 | +0.086957 | +0.054348 | 可估计 |
| D2 − D1 | 136 | -0.021739 | +0.021739 | 可估计 |
| D3 − D2 | 0 | — | — | 不可估计 |
| L_ONLY − D0 | 136 | +0.021739 | +0.021739 | 可估计 |
| U_ONLY − D0 | 0 | — | — | 不可估计 |
| V_ONLY − D0 | 133 | +0.076087 | +0.065217 | 可估计 |

### 5.3 G7 terminal retries 1–3（分别 canonical，不合并）

| 批次 | 计划行 | completed | checkpoint_missing | provider_error | Q valid | model calls | tool calls | tokens | observed cost |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| retry1 | 295 | 185 | 90 | 20 | 2 | 646 | 535 | 1,385,282 | $2.266946 |
| retry2 | 110 | 79 | 20 | 3 | 0 | 276 | 196 | 601,606 | $1.006640 |
| retry3 | 31 | 16 | 12 | 3 | 0 | 68 | 61 | 156,629 | $0.271911 |

retry2 的 canonical state 为 102/110，缺失 8 个 ID；这 8 个 ID 进入 retry3。retry3 的 canonical state 为 31/31。三批均为 `FROZEN_SEPARATE_RETRY`，失败行没有被转成成功行。

### 5.4 protocol-corrected G7 full retry（当前主要 G7 数据）

该批次采用修复后的 prompt contract，明确禁止向模型暴露 `cf_type` 和 `theory_family_id` 等路由提示，并单独冻结了 format retry：每个 workflow 最多一次、且不增加新的科学观察。

| 指标 | protocol-corrected retry |
|---|---:|
| root | `formal-20261015T060000Z-protocol-corrected-16workers` |
| plan rows | 1288 |
| unique checkpoints | 184 |
| canonical state rows | 1288/1288 |
| completed | 1285（99.767%） |
| provider_error | 3（0.233%） |
| checkpoint completed | 184/184（100%） |
| Q rows / Q valid | 1288 / 20（1.553%） |
| model calls | 3774 |
| tool calls | 2356 |
| total tokens | 8,147,109 |
| observed cost | USD 13.009913 |
| format retry scheduled / model requests | 302 / 302 |
| format retry 上限 | 每 workflow 最多 1 次 |
| new scientific observation | 否 |
| route metadata hits | 0 |
| forbidden private prompt hits | 0 |
| missing state IDs | 0 |
| duplicate completed IDs | 0 |
| confirmatory status | 仍不允许 |

protocol-corrected retry 的完成率显著高于原始 G7，但 Q valid 仍只有 20/1288；因此不能把“canonical 完整”误写成“科学结果有效”。

### 5.5 G7 V/L/U/Q 数据与限制

| 指标 | 结果 |
|---|---:|
| V local label：CF1/CF3 | `CONTRADICTED` |
| V local label：CF2 | `SUPPORTED` |
| V local label：CF4 | `INDETERMINATE` |
| L dependency edges | 0/92 cases |
| U eligible cases | 0/92 |
| U 是否注入缺失边 | 否 |
| 原始 G7 Q valid | 3/1288 |
| 修正版 G7 Q valid | 20/1288 |
| 修正版 G7 provider failure | 3/1288 |
| G7 replicate | 1 |

由于所有 public case 的 edge count 都为 0，U 在协议上不具备资格；该空状态不能被后处理成 U transition。L 也不能被写成可信的边级传播。Q 是独立 verifier audit 的标签，不能通过后处理把 invalid 改成 PASS。

## 6. G0–G7 复现与哈希证据

### 6.1 当前审计/测试

| 检查 | 结果 |
|---|---:|
| host `pytest -q` | 108 passed |
| `git diff --check` | PASS |
| G6 structural review | PASS |
| G6 release review | structural pass；scientific release false |
| G7 corrected canonical merge | 1288/1288 state；184/184 checkpoint |
| G7 corrected private prompt hit audit | 0 |
| G7 corrected route metadata hit audit | 0 |
| G7 Q audit | 1288 行保留；20 valid |
| G7 terminal retry rows | 失败记录均保留，未 pooled |

### 6.2 G6 关键哈希

| 产物 | SHA-256 |
|---|---|
| G6 `run_plan.jsonl` | `c60b14205f061fa2178b9d0a42074d9957a460bea2cf4e06b841acbe4b0bbde0` |
| G6 `responses.jsonl` | `97022fa9ac84dad61c24c98fbc1fee2ba2b357ee853eccd9614cc348da8312fa` |
| G6 `g6_to_g7_handoff.jsonl` | `ec51c3114b84da9f818d0f6407794e42454cbe87565aa0baaf60081c61602c02` |
| G6 `public_cases.jsonl` | `1bffc3769523e437cc7e4ea5cff22f4eb2d42cd3500299f914cb03ec36b6063f` |
| G6 `private_oracle.jsonl` | `e966efbadffea604d4de735a0323dbb5ffb2593e510bb8a456cb84422258d6c0` |

### 6.3 G7 关键哈希

| 产物 | SHA-256 |
|---|---|
| 原始 G7 `g7_run_plan.jsonl` | `549c39a9508fae3c7611564f0cca6022ade5dda67f52d8cc6c1fbd51b9633eb3` |
| 原始 G7 `g7_states.jsonl` | `714e53654e070a74bc026c11c7396fc243b8e4b72a45e3ed4e9025d8fe66efef` |
| 原始 G7 `g7_checkpoints.jsonl` | `28cbfead349cc35682141df3ac99841d3ebbecdde08280d2849738645b201932` |
| 原始 G7 `g7_q_audit.jsonl` | `7090520110215c742259dc5598d0c37dc14a155dfd93dc165d011a3e460d27ff` |
| protocol-corrected retry plan | `be6c5550dfc453110b3f526f9ed6cf865bb0c1df5c3891b87dc0a23d6cf4c2e5` |
| protocol-corrected retry states | `45fa85c25fada1fe6653d582e7167b1f54bf7551f80c2b847ca5badddec93bc2` |
| protocol-corrected retry Q audit | `95349ef7fa28b9e3a63290c5bda4e67be007027b2f12cce29aa656bc252543` |

## 7. 当前问题台账与最终解释

| 类型 | 当前状态 | 对 G0–G7 报告的影响 |
|---|---|---|
| G7 原始 prompt 路由元数据泄漏 | 已识别；原始批次不可确认；修正版命中 0 | 原始 G7 只作历史/故障数据，不能作 confirmatory 结论 |
| G7 provider/terminal failure | 原始批次 295/1288 terminal；修正版 3/1288 provider error | 失败必须保留，不能隐去或改成有效回答 |
| G7 Q 有效率 | 原始 3/1288；修正版 20/1288 | Q 结论证据不足，不能后处理修正 |
| G5 dependency edges | 0/92；eligible U=0 | L/U 机制指标受协议资格限制 |
| G6 CF3 revision valid | 0/138 | decision accuracy 不能替代 revision validity |
| 独立数学/领域复核 | 未完成 | 不能宣称 23 family 已完成外部证明 |
| 独立统计复核 | 未完成 | G6 CI/p 值只是当前分析输出，尚未外部确认 |
| immutable model snapshot / weight fingerprint | 缺失 | 不能独立确认模型身份/权重不可变 |
| billing export | 缺失 | 运行成本为 trace-audit observed cost，不是外部账单证明 |
| 上游 provenance / GitHub delivery | 外部网络阻断 | 不能宣称远程交付或上游独立验证成功 |

### 最终结论

截至本报告截点，G0–G7 的工程执行、产物留痕和内部数据审计已整理完成；G6 corrected run 结构完整，G7 protocol-corrected retry 的 state/checkpoint canonical 覆盖完整，且已修复原始 G7 的路由提示泄漏。

但这不等于科学结论已经发布。当前可审计的结论是：**G0–G7 数据和失败状态已被保留并可复现核对，但整体仍处于 `BLOCKED_PENDING_EXTERNAL_REVIEW_AND_PROVIDER_FAILURES`，不允许据此宣称 Agent 优越性、内生失败机制或因果结论。**

## 8. 复现入口

- 最新完整性审计：`docs/audits/cycle-20261015T083400Z-28/g0_g8_integrity.json`
- G7 失败分类审计：`docs/audits/cycle-20261015T083400Z-28/g7_failure_taxonomy.json`
- 状态台账：`docs/state/issues.json`
- 未解决报告：`docs/state/UNRESOLVED_REPORT.md`
- G6 handoff：`docs/state/G6_HANDOFF_NEXT_AGENT.md`
- G6 corrected root：`results/g6_counterfactual/protocol-g3tools-v2-20261014T030000Z`
- G7 original root：`results/g7_failure_localization/formal-20261014T030000Z-16workers`
- G7 corrected root：`results/g7_failure_localization/formal-20261015T060000Z-protocol-corrected-16workers`

---

# 附录 A：逐个 Skill 的内部指标、字段与门禁

本附录回答“每个 skill 内部到底检查什么、记录什么、怎么算”的问题。所有数值都标注为以下三类之一：

- **规范/计划值**：来自 skill、schema 或配置的要求，不能当成已执行数据。
- **实际落盘值**：来自本仓库真实结果、trace、merge 或审计文件。
- **审计结论**：对结构、隔离、缺失和失败的判定，不等于科学真值。

## A.1 编号和 namespace 对齐

| 来源 | G 编号含义 | 本报告如何使用 |
|---|---|---|
| `g0-g4.zip` 统一总控 skill 的 `theory_benchmark` | G0=Single LLM；G1=LLM+Tools；G2=LLM+Iteration；G3=Tools+Iteration；G4=Agentic Workflow | 作为理论 benchmark 能力组规范 |
| 本仓库 `law_discovery` 的 `experiment_groups.json` | G1=冻结 LLM-only；G2=固定 calculator；G3=固定 reflection；G4=adaptive Agent；G5=bounded memory Agent | 作为 NewtonBench/定律恢复实际组规范 |
| G6 专项 skill | G6 counterfactual，比较派生 G3/G4 | 独立于旧 G0–G5，不改写旧数据 |
| G7 专项 skill | G7 failure localization，V/L/U/Q | 独立消费 G6 public/checkpoint，不能读取私有 oracle |

因此，统一总控 skill 的“theory_benchmark G0–G4”和本项目定律恢复的“G1–G5”不能按同名直接合并。下面的实际数据均以本项目执行编号为准。

## A.2 统一总控 Skill 的内部总指标（规范值）

| 内部项 | skill 规定 |
|---|---:|
| theory benchmark base tasks | 100 |
| theoretical chemistry | 50 |
| theoretical biology | 50 |
| L1/L2/L3 合计 | 34 / 33 / 33 |
| L1 chemistry/biology | 17 / 17 |
| L2 chemistry/biology | 17 / 16 |
| L3 chemistry/biology | 16 / 17 |
| 理论 benchmark 能力组 | 5 组（G0–G4） |
| real provider trace 记录 | 每次 provider、LLM role、tool、retry、异常和 evaluator 边界事件均追加写入 JSONL |
| mock/demo 规则 | mock 必须显式标记；不得进入正式科学统计 |
| transport retry 默认 | 0；配置更高时 controlled run 应在构造阶段拒绝 |
| ground truth 进入模型消息 | 禁止；只在 evaluator 边界打开 |

### A.2.1 统一 trace 的内部字段

每个可观察事件至少围绕以下字段审计：

| 字段类别 | 字段 |
|---|---|
| 身份与拓扑 | `run_id`、`task_id`、`system_type`、`model_name`、`step_id`、`parent_step_id` |
| 时间与事件 | `event_type`、`timestamp`、`status`、`latency_ms` |
| 输入输出 | `input`、`output`、`prediction` |
| 工具 | `tool_name`、`tool_arguments`、`tool_result` |
| 资源 | `token_usage`、`cost` |
| 失败 | `error_message`、policy/budget/provider/parse 状态 |
| 元数据 | `metadata`、模型信息、重试/attempt、哈希和隔离审计字段 |

关键原则是：失败 attempt 也记录；原始 trace append-only；API key、hidden chain-of-thought、private oracle 和 answer key 不得进入普通结果或模型输入。

## A.3 G0 Skill 内部指标：注册、冻结、预算和 evaluator

### A.3.1 输入、输出和控制字段

| 类别 | 内部字段/产物 | 本项目实际情况 |
|---|---|---|
| 上游 | pinned NewtonBench registry/commit | commit 配置为 `912a4ba5f4356ddd06acc16e44460ca30be4abc2` |
| 注册 | stable task ID、domain、difficulty、variant、law-family | 当前首阶段 108 个 direct-measurement tasks |
| 选择 | registered seed、stratified round-robin、outcome-blind manifest | seed=42；manifest hash 写入每条正式结果 |
| 公开输入 | public task description、action schema、noise、precision | 模型可见；不含 ground truth |
| 隐藏输入 | target law、validation/OOD interventions | 仅 evaluator 可见 |
| 运行记录 | runner、task/arm/replicate、plan hash、observations、provider metadata、budget ledger | 已实现并进入结果/trace |
| 交付 | frozen manifest、manifest SHA-256、task-run result、validation output | 工程验证和正式结果均有审计路径 |

### A.3.2 G0 的数值判定字段

| 指标 | 固定规则 |
|---|---|
| `numeric_fit` | 128 个 deterministic seeded validation interventions；relative RMSE ≤ `1e-5` |
| `structural_recovery` | canonical executable-law AST fingerprint；只匹配字符串不算通过 |
| `ood_fit` | 64 个 deterministic legal OOD interventions；relative RMSE ≤ `1e-5`；至少 16 个 finite points |
| `mechanistic_validity` | structural recovery 和 OOD fit 同时为真 |
| `validated_success` | numeric fit、structural recovery、OOD fit 三者全部通过 |
| 次要诊断 | RMSLE 保留，但不能替代主判定 |
| evaluator 归属 | 项目自有 restricted numeric evaluator；`official_numeric_evaluator=false` |
| 失败分母 | provider、parse、budget、missing-arm 全部保留 |

### A.3.3 G0 计划值与落盘值对照

| 指标 | Skill/协议计划 | 实际盘点 |
|---|---:|---:|
| 直接测量任务 | 由 registry 生成 | 108 |
| 工程验证 | 12 tasks × 2 runners | 24 records |
| pilot | 12 domains × 5 matched replicates | 作为 pilot 规划记录 |
| formal target | 72 tasks × 5 replicates × 2 arms | 作为 frozen statistical target |
| 默认单次实验 | 6 experiments；120 measurements | runner/protocol 配置 |
| mock 标记 JSON | 应显式标记 | pilot/engineering/final smoke 为 0；theory/theory-agent-smoke 各 1 |

## A.4 G1–G5 Skill 内部能力与策略指标

### A.4.1 共享硬约束

| 约束 | 值 |
|---|---:|
| shared max input tokens | 100,000 |
| shared max output tokens | 30,000 |
| transport retries | 0 |
| ground truth | 只在最终提交后由 evaluator 打开 |
| policy violation | 写入 `POLICY_CHECK` 和 `ERROR`，该运行失败 |
| budget snapshots | 无论成功/失败均记录 |
| provider attempt | 区分 logical model call 与实际 transport attempt |
| LLM-only 反馈通道 | 关闭；中间 observations 不得进入 planning message |

### A.4.2 各组内部指标

| 组 | Skill 内部名称 | model calls | tools/steps | feedback/planning | memory/retrieval | 实际审计要点 |
|---|---|---:|---|---|---|---|
| G1 | `llm_only` / frozen plan | NewtonBench 2；theory 1 | 无 | one-shot；plan→batch→final | 无/无 | `tools=None`；plan canonicalize+hash；batch 无 provider reference |
| G2 | `llm_with_fixed_tools` | 2 | `calculate_expression`；4 compute steps | fixed tool assist | 无/无 | 只允许 calculator；越权工具/计算失败 |
| G3 | `llm_with_reflection` | 2 | 无 | fixed two-pass reflection | 无/无 | 第二次是固定 synthesis，不是 observation-conditioned replanning |
| G4 | `single_agent` | 8 | `run_experiment`、`calculate_expression`；6 experiments | adaptive；后续行动可依赖公开 observation | 无/无 | 每次 provider call 最多一个 `run_experiment`；工具白名单硬校验 |
| G5 | `single_agent_with_bounded_memory` | 10 | 同 G4；最多 10 tool calls | adaptive memory | run-local 32 items/无 retrieval | memory 只属于当前 run；跨任务记忆、检索、越权均失败 |

### A.4.3 G1–G5 的内部阶段和失败字段

| 组/阶段 | 关键内部数据 | 不能做的事情 |
|---|---|---|
| G1 plan | provider request、JSON plan、canonical plan、SHA-256 | 得到 observation 后重规划；让后续结果影响已冻结计划 |
| G1 batch | action sequence、每次 observation、budget snapshot | provider reference、tools、文件/网络/隐藏状态 |
| G1 final | initial+batch observations 一次性提交、law schema | 在 batch 中插入最终判断 |
| G2 compute | calculator arguments/result、step index、4 steps | 使用实验、memory、retrieval 或额外模型调用 |
| G3 reflection | first response、fixed second synthesis、两次 usage | 根据反馈改变实验路径；追加第三次调用 |
| G4 adaptive | observation history、selected action、tool result、stop/final schema | 使用未授权 tool、代码、浏览、文件、隐藏 state |
| G5 memory | memory slot id/content、write/read event、32-item cap | 跨 task memory、answer key、retrieval |
| 任意组 | `provider_error`、`parse_error`、`budget_exceeded`、`policy_violation`、`missing_arm` | 删除失败行、将缺失当成 wrong 或成功 |

### A.4.4 实际 G1–G5 工程数据

| 指标 | 实际值 |
|---|---:|
| engineering tasks | 12 |
| runner | 2 |
| completed records | 24/24 |
| matched pairs | 12 |
| Mock Agent−LLM mean difference | 0.0 |
| Mock bootstrap CI | [0.0, 0.0] |
| zero-function negative control success | 0 |
| historical real provider requests | 0 |
| 当前 host suite | 108 passed |

这些内部数据验证的是 policy/runner/trace/negative-control 工程，不是 G1–G5 的科学 superiority 结果。

## A.5 G5 Skill 内部指标：proof graph、family 和可用分母

| 内部项 | 规范含义 | 实际值 |
|---|---|---:|
| G5 产物 | `events.jsonl`、`steps.jsonl`、`proof_graph.json`、`summary.json`、`manifest.json` | 均有对应审计路径 |
| graph 文件 | 每个 proof graph 与 expected sibling 绑定 | 1309/1309 |
| source-only family | 不读取 private input/answer key 的独立核验单位 | 24 |
| independent grade-B family | 进入 corrected denominator 的 family | 23/24 |
| excluded family | `EXCLUDED_INVALID_SOURCE`，TB-L1-010 | 1/24 |
| graph source hash | 由 graph/manifest 追溯 | 保留 |
| private input | G5 graph 审计不得读取 | 否 |
| answer key | G5 graph 审计不得读取 | 否 |
| public cases | 23 family × 4 CF | 92 |
| dependency edges | 每个 case 的 `from→to` 依赖传播边 | `edge_count=0`，92/92 |
| eligible U | 需要真实非终值中间节点 | 0/92 |

G5 的“graph 文件存在”与“graph 能支持边级机制推断”是两件事。当前 edge_count=0 导致 G7 的 L/U 受协议性不资格限制；不能通过补标签、padding 或推测恢复。

## A.6 G6 Skill 内部指标、schema 和计划/实际差异

### A.6.1 G6 假设与固定 arm

| 项目 | 内部定义 |
|---|---|
| H6 | 关键前提翻转应拒绝原结论；无关/等价改变应保持；边界弱化应合法修订；信息不足应 `UNDETERMINED` |
| G6-A | `G6_A_G3_GIVEN`，派生 G3 Tools+Iteration，主对照 |
| G6-B | `G6_B_G4_GIVEN`，派生 G4 Agentic Workflow，主实验 |
| G6-C | `G6_C_G4_HIDDEN`，可选 hidden anchor；不得与 A/B 主试验混算；当前 corrected run 未使用 |
| 四类 CF | CF1 critical flip；CF2 irrelevant equivalent；CF3 boundary weakening；CF4 insufficient information |
| 统计独立单位 | `theory_family_id`；不是 case、variant 或 replicate |
| 主分析 | A/B 同族配对；family-cluster bootstrap；保留 all planned 分母 |

### A.6.2 G6 schema 内部字段

| 数据对象 | 必需/关键字段 |
|---|---|
| public case | `case_id`、`paired_set_id`、`source_task_id`、`theory_family_id`、`domain`、`cf_type`、`split`、`quantifier`、`model_visible`、`source_g5_graph_sha256`、`verification_grade` |
| `model_visible` | `original_problem`、`original_claim`、`public_proof_graph`、`intervention_statement`、`quantifier` |
| private oracle | `case_id`、`cf_type`、`expected_decision`、`affected_claim_ids`、`oracle_reason`、`verification_grade`、`verifier_status`；可选 `correct_revised_claim`、`counterexample` |
| frozen plan | `run_id`、`experiment_id=g6_counterfactual`、`case_id`、`paired_set_id`、`theory_family_id`、`cf_type`、`arm_id`、`group_id`、`replicate`、`split` |
| model response | `run_id`、`decision`、`affected_claim_ids`、`revised_claim`、`supporting_evidence`、`status`、`trace_ref`；可选 revision verification fields |
| response status | `completed`、`timeout`、`provider_error`、`policy_violation`、`invalid` |

模型只能看 public case；private oracle 的 expected decision、reason、counterexample、correct revised claim 和 verifier status 不得进入 prompt。

### A.6.3 G6 计划值、历史完整运行和 corrected 实际运行

| 层级 | families | public cases | CF | arms | replicate | plan/response |
|---|---:|---:|---:|---:|---:|---:|
| 离线 DEMO 规范 | 2（不同族） | 8 | 4 | 2 | 1 | 仅工具自测，不是科学数据 |
| 正式先导规范 | 4 | 16 | 4 | 2 | 1 | 32 条轨迹 |
| 正式规模规范 | 24 | 96 | 4 | 2 | 3 | 576 条轨迹 |
| 历史 full G6 | 24 | 96 | 4 | 2 | 3 | 576/576 |
| corrected eligible G6 | 23 | 92 | 4 | 2 | 3 | 552/552 |

corrected 版本不是重新随机抽取，也不是根据 response outcome 选样；它固定排除 TB-L1-010，使用 23 个 source-only accepted family，保留原始独立轨迹。

### A.6.4 G6 runner 硬限制与实际使用

| 资源 | corrected 配置上限 | 实际使用 |
|---|---:|---:|
| model calls | 4608 | 1826 |
| tool calls | 3456 | 1796 |
| total tokens | 4,608,000 | 3,454,449 |
| cost ceiling | USD 200.0 | trace-audit USD 6.057783 |
| provider transport retries | 0 | 按 controlled run 规则 |
| workers | 用户指定 2 | `[2]` |
| revision audit rows | — | 138 |
| valid revision rows | — | 0 |

### A.6.5 G6 分数内部定义

| 指标 | 分母/定义 |
|---|---|
| completion rate | completed response ÷ all frozen plan rows |
| end-to-end / all-planned decision accuracy | 正确 decision ÷ 全计划行；缺失/失败不删除 |
| conditional/valid-only accuracy | 正确 decision ÷ completed 且可解析行；不能替代 all-planned |
| CF1 accuracy | 正确 `REJECT` |
| CF2 accuracy | 正确 `MAINTAIN` |
| CF3 accuracy | 正确识别边界并给合法 `REVISE`；revision validity 需另审 |
| CF4 accuracy | 正确 `UNDETERMINED` |
| paired effect | 同一 theory family 的 G4−G3 |
| uncertainty | family-level bootstrap 95% CI |
| paired test | matched McNemar；不把 replicates 当独立自然定律 |

## A.7 G7 Skill 内部指标、字段和诊断定义

### A.7.1 G7 强制观测顺序

`checkpoint → initial_Y → V → L → U → Q → final_Y`

| 阶段 | 必须记录的内部内容 | 允许为空的情况 |
|---|---|---|
| checkpoint | 新 provider call、public messages、工具输出、initial decision、usage、trace hash | 不能从 G6 final response 回填 |
| `initial_Y` | 同一 checkpoint 的初始 decision/status | provider/checkpoint failure 时可缺失，但必须记失败 |
| V | `verdict`：`SUPPORTED`/`CONTRADICTED`/`INDETERMINATE` | 不接受模型声称已核验替代独立标签 |
| L | `nodes`、`edges`，edge 为 `from→to` | 空 graph 合法；本项目 92/92 无 edge |
| U | `node_changes`，每项 `claim_id` + `to_status`（supported/rejected/uncertain） | 没有非终值中间命题时为 ineligible，不得注入最终答案 |
| Q | 顶层 `stages.Q={verdict,reason}` | 必须由运行结束后的独立 `q_audit` 审计 |
| final_Y | `decision`、`affected_claim_ids`、`revised_claim`、`supporting_evidence` | 不能用 final answer 字符串反推 V/L/U |

### A.7.2 G7 7 个 diagnostic arm 的信息注入

| arm | 注入内容 | 内部用途 | 重要限制 |
|---|---|---|---|
| D0 | 中性占位；无 oracle 信息 | 自然过程/格式基线 | 不是“完全无提示”以外的因果证明 |
| D1 | V | V 阶梯入口 | 若与 V_ONLY 同内容，不算两个独立机制证据 |
| D2 | V + L | 逐级诊断上界 | D2−D1 不能称内生 L 因果效应 |
| D3 | V + L + 非终值 U | 诊断上界 | 禁止 final claim/answer injection |
| V_ONLY | 仅 V | 单因素/一致性检查 | 与 D1 重复时不应 double count |
| L_ONLY | 仅 L | L 单因素诊断 | 需 matched injection position/context |
| U_ONLY | 仅非终值 U | U 单因素诊断 | 无非平凡中间命题时 `INELIGIBLE` |

### A.7.3 G7 规范计划、实际计划和 runner 限制

| 指标 | G7 skill 提案 | 本次实际值 |
|---|---:|---:|
| pilot families | 4 | 未单独作为本次 confirmatory batch |
| confirmatory families | 24 | corrected 可用 23 |
| only-substudy families | 8 | 未另建 only-substudy 分母 |
| proposed repeats | 3 | 本次正式 retry 为 1 replicate |
| proposed main+only forks | 1440（建议值） | 1288 = 23×4×2×7×1 |
| checkpoint count | 每 case×group 一份 | 184 |
| workers | skill 不固定 | 原始 16；corrected 16；G6 为 2 |
| max model calls/worker | skill example 为 null | runner default 4608 |
| max tool calls/worker | skill example 为 null | runner default 3456 |
| max tokens/worker | skill example 为 null | runner default 4,608,000 |
| max cost/worker | skill example 为 null | runner default USD 200 |
| provider retries | — | 0 |
| provider timeout | — | 60 seconds |
| max output tokens | — | 1024 |
| input/output price proxy | — | USD 0.001 / 0.003 per 1k |

### A.7.4 G7 内部响应格式和硬校验

| 层级 | 必须字段/规则 |
|---|---|
| decision | `MAINTAIN`、`REJECT`、`REVISE`、`UNDETERMINED` |
| claim fields | `affected_claim_ids` 为 list；`revised_claim` 可为 string/null；`supporting_evidence` 为 string |
| stages | 顶层 `stages` 必须含 V、L、U、Q 四个 object |
| V | `verdict` 只能是 SUPPORTED/CONTRADICTED/INDETERMINATE |
| L | `nodes` 和 `edges` 必须是 list；禁止用 arrow string 代替 edge object |
| U | `node_changes` 必须是 list；不能用 object/map 代替 |
| Q | `verdict` 和 `reason` 必须是 string |
| format retry | 每个 workflow 最多 1 次；不增加新的 scientific observation |
| malformed response | 记 invalid/provider failure；不得静默修复为成功 |

### A.7.5 G7 内部分数、失败和配对指标

| 指标 | 定义 |
|---|---|
| `completion_rate` | completed state ÷ 全部计划 fork rows |
| `all_planned_final_decision_accuracy` | 正确 final decision ÷ 全部计划行；terminal/missing 保留 |
| `valid_only_accuracy` | 正确 final decision ÷ completed 且结构有效回答 |
| `original_claim_status_accuracy` | 对原 claim 状态的独立判定正确率 |
| `corrected_wrong_W_to_C` | 初始错误后恢复正确的比例 |
| `damaged_correct_C_to_W` | 初始正确后被辅助损坏的比例，安全性指标 |
| `C_TO_C/W_TO_C/C_TO_W/W_TO_W` | checkpoint 初始状态到 final 状态的转移计数 |
| `first_observable_error` | V/L/U/Q/MISSING/NOT_OBSERVED 等首次可观察错误位置 |
| V metric | 独立局部 verdict accuracy/F1 |
| L metric | affected nodes、dependency edges 的 precision/recall/F1；当前 edge 不可用 |
| U metric | 非终值 node transition accuracy；当前 92/92 U ineligible |
| Q metric | 独立 q_audit valid/invalid；不能信模型自报 Q |
| paired effect | 同一 checkpoint、同一 family 的 arm/diagnostic paired difference |
| CI | theory-family cluster bootstrap；不把 tasks/repeats 当自然定律 |

### A.7.6 G7 交付文件与当前状态

| 规范交付物 | 当前对应数据 |
|---|---|
| G6 import audit | `g7_input_audit`/integrity audit 路径 |
| public cases | 92 cases；source public SHA 保留 |
| private V/L/U labels | `g7_vlu_private`；模型不可见 |
| frozen plan | 原始 plan 与 corrected retry plan 分开 |
| checkpoint traces | corrected 184/184 completed |
| raw events | append-only；format/provider/terminal events 保留 |
| state merge | corrected 1288/1288 canonical；原始/terminal retry 不 pooled |
| error taxonomy | `g7_failure_taxonomy.json`；按批次和 workflow 分层 |
| Q audit | 原始 3/1288 valid；corrected 20/1288 valid |
| selected mechanisms | 当前不能从 G7 直接宣称机制；G8/外部复核门禁未关闭 |

## A.8 各 Skill 的“计划、执行、发布”三层状态总表

| Skill | 计划/接口层 | 实际执行层 | 发布层 |
|---|---|---|---|
| G0 | registry、manifest、seed、预算、evaluator 已定义 | 108 registry；工程/测试数据可追溯 | 上游 provenance/evaluator 官方性未完全确认 |
| G1 | 2-call frozen LLM-only，0 tool/retry | 24/24 engineering records；历史 real provider=0 | 仅工程证据 |
| G2 | 2-call calculator，4 steps | 权限边界可审计 | 仅工程证据 |
| G3 | fixed reflection；G6 使用显式 Tools+Iteration profile | G6 276 rows；G7 644 planned forks | 无 superiority/causal 发布 |
| G4 | adaptive observation-conditioned agent | G6 276 rows；G7 644 planned forks | 无 superiority/causal 发布 |
| G5 | memory 32、10 calls、10 tools、proof graph | 1309 graph；23/24 accepted family；edge 0/92 | U/L 机制发布受阻 |
| G6 | 24×4×2×3 proposed；CF1–CF4；A/B paired | full 576 历史；corrected 552/552；revision valid 0 | external math/stats/model/billing gates open |
| G7 | checkpoint + V/L/U/Q；7 arms；独立 Q | corrected 1288 state、184 checkpoint；Q valid 20 | provider failure、low Q、edge 0；不允许 confirmatory claim |

## A.9 本附录使用的 Skill 源文件

| Skill/规范 | 源文件 |
|---|---|
| 统一 G0–G5 总控 | `D:/硕士/prj1_ai_cal/exp/exp1_from_llm_to_agent/prompt/g0-g4.zip`、`whole_pros_g5.zip` |
| G6 | `D:/硕士/prj1_ai_cal/exp/exp1_from_llm_to_agent/prompt/G6_Counterfactual_Reasoning_Skill.zip` |
| G7 | `D:/硕士/prj1_ai_cal/exp/exp1_from_llm_to_agent/prompt/G7_Failure_Localization_Skill.zip` |
| 实际 G1–G5 配置 | `configs/experiment_groups.json`、`docs/experiment_groups.md` |
| G0 evaluator | `docs/evaluation_protocol.md`、`docs/experiment_protocol.md` |
| G6/G7 最新审计 | `docs/audits/cycle-20261015T083400Z-28/g0_g8_integrity.json`、`g7_failure_taxonomy.json` |

附录中的 proposed/demo 数字只用于解释 skill 的内部设计；实际科研数据仍以正文的 canonical artifacts、失败分母、哈希和 issue ledger 为准。
