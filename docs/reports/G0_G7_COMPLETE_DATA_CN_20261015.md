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
