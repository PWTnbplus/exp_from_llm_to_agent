# G0–G7 科学定律恢复实验指标报告

## 0. 报告范围与阅读方式

本报告基于当前工作区中已经生成并审计的 G0–G7 产物，重点罗列指标、分母、完成率、准确率、成本、哈希和门禁状态，不逐条展开案例。

需要特别区分三类状态：

1. **工程执行通过**：代码、schema、隔离、trace、merge 或统计流程按规则运行。
2. **数据审计通过**：输入、数量、哈希、缺失记录和失败记录可追溯。
3. **科学发布允许**：还需要独立数学复核、模型快照/计费证明、上游 provenance、统计复核和足够的有效 provider 输出。

本项目目前已经达到前两类的较大范围，但没有达到第三类。因此，下面的准确率和差异均是协议内的诊断性指标，不是 Agent 优越性或因果机制结论。

主要数据截点：2026-10-14 UTC。报告依据的实验审计 commit：`4fd1fb7`；本报告作为后续独立文档提交。

---

## 1. 总体结论

| 阶段 | 核心对象 | 主要指标 | 当前结论 |
|---|---|---:|---|
| G0 | 科学问题、任务注册、评估协议 | 108 个直接测量任务；正式目标 72 任务 × 5 replicate × 2 arm | 协议冻结；上游远程 provenance 仍受外部网络阻断 |
| G1 | 冻结计划 LLM-only | NewtonBench 2 次模型调用；无工具、无反馈、无重试 | 架构/Mock 门禁通过；无真实科学结论 |
| G2 | 固定计算辅助 | 2 次模型调用；4 个 calculator compute steps | 权限边界通过；没有独立的付费正式批次 |
| G3 | 固定两遍反思 | 2 次模型调用；原始定义无工具 | G6 使用了单独冻结的 Tools+Iteration 修正版 |
| G4 | 自适应单 Agent | 最多 8 次模型调用；可用授权工具并根据反馈行动 | G6 中 276 行，G7 中作为 G4 组运行 |
| G5 | Agent + run-local memory | 10 次模型调用；10 次工具调用；32 个 memory slots | 源图审计通过 23/24；图依赖边缺失 |
| G6 | 反事实验证 | 552/552 response、trace 完成；2 workers；成本约 $6.057783 | 结构审计通过；科学发布仍阻断 |
| G7 | 失败定位 | 1288 个 fork；993 完成；Q valid 3/1288 | 执行、merge、审计、score、handoff 完成；provider 失败率过高 |

---

## 2. G0：问题定义、任务注册与评估协议

### 2.1 科学问题

研究问题是：在相同模型、任务、初始信息、测量精度和实验预算下，反馈控制的实验选择是否提高科学定律恢复率。

主指标是 **VLDR（Validated Law Discovery Rate）**，即提交的定律同时通过预注册的数值拟合、结构恢复和留出 OOD 拟合的任务运行比例。该问题不是泛化的“Agent 是否优于 LLM”，而是限定在当前模拟器、任务族和预算协议内的比较。

### 2.2 任务与样本规划

| 指标 | 数值/规则 |
|---|---:|
| 第一阶段 registry | 108 个直接测量任务 |
| 工程验证集 | 12 个任务，2 个 runner，共 24 条结果 |
| Pilot 统计规划 | 12 个 domain × 5 个 matched replicate |
| 正式目标规划 | 72 个任务 × 5 个 replicate × 2 个 arm |
| 统计独立单位 | NewtonBench law-family/module，而非任务变体或 replicate |
| 默认实验预算 | 6 experiments、120 measurements |
| 数值验证点 | 128 个 deterministic seeded validation interventions |
| OOD 验证点 | 64 个 deterministic legal OOD interventions |
| numeric/OOD 阈值 | relative RMSE ≤ 1e-5 |
| OOD 有效点最低要求 | 至少 16 个有限点 |
| 选择方式 | outcome-blind、注册 seed=42、分层 round-robin |
| 失败分母规则 | provider、parse、budget、missing-arm 失败都保留在分母 |

### 2.3 G0 门禁状态

- **已通过的工程部分**：任务注册、manifest/frozen-plan 设计、公共输入与隐藏评估器边界、预算账本和失败分母规则均有代码及测试。
- **仍未完全通过的外部部分**：配置的 NewtonBench commit 为 `912a4ba5f4356ddd06acc16e44460ca30be4abc2`，但远程上游和 GitHub delivery 受代理网络阻断，不能把本地 vendored provenance 当成远程独立确认。
- **评估限制**：当前 evaluator 是项目自有的受限数值 evaluator，`official_numeric_evaluator=false`；不能把当前结果表述为完整官方 NewtonBench 评估。

---

## 3. G1–G5：能力隔离与工程基线

### 3.1 冻结能力矩阵

| 组别 | 模型调用上限/约定 | 工具 | 反馈/规划 | memory | retrieval | transport retry |
|---|---:|---|---|---|---|---:|
| G1 | NewtonBench 2；theory 1 | 无 | frozen plan / one-shot | 无 | 无 | 0 |
| G2 | 2 | `calculate_expression`；4 compute steps | 固定计算辅助 | 无 | 无 | 0 |
| G3 | 2 | 无 | fixed two-pass reflection | 无 | 无 | 0 |
| G4 | 8 | `calculate_expression`、`run_experiment` | observation-conditioned adaptive | 无 | 无 | 0 |
| G5 | 10 | 同 G4 | adaptive | run-local，32 items | 无 | 0 |

任何越权工具、检索、memory、额外模型调用、额外实验或重试都应产生 `POLICY_CHECK`/`ERROR`，并令该运行失败。Ground truth 只在模型提交之后由 evaluator 打开，不进入模型消息、普通结果或 trace。

### 3.2 G1–G5 工程基线指标

历史工程验证使用 12 个任务、2 个 runner，共 24 条记录：

| 指标 | 数值 |
|---|---:|
| 任务数 | 12 |
| runner 数 | 2（LLM-only / Agent） |
| 结果记录 | 24/24 完成 |
| 配对数 | 12 |
| Mock Agent−LLM 平均差 | 0.0 |
| Mock bootstrap 95% CI | [0.0, 0.0] |
| 负控制 | zero-function；验证成功数为 0 |
| 真实 provider 请求 | 历史 G1–G5 工程阶段为 0 |

上述结果只说明工程流程可运行，不能作为模型科学能力或 Agent 优势的证据。当前全仓 host suite 为 **99 passed**；早期报告中的 14/31/80 tests 是不同历史周期的局部测试计数，不与当前 99 混用。

### 3.3 G5 源图与独立验证

| 指标 | 数值 |
|---|---:|
| G5 `proof_graph.json` 文件 | 1309 |
| 具有预期 sibling 文件的 graph | 1309/1309 |
| source-only 独立核验 family | 24 |
| `VERIFIED_INDEPENDENT_B` | 23/24 |
| `EXCLUDED_INVALID_SOURCE` | 1/24（TB-L1-010） |
| private input 是否读取 | 否 |
| answer key 是否读取 | 否 |
| 进入 corrected G6 的 family | 23 |
| G6/G7 public case 数 | 92（23 family × 4 CF） |

TB-L1-010 没有被填充、重标或恢复。其公开公式与标准隐性突变选择平衡不一致，且 graph 中 validity 节点未解决，因此被永久排除在 corrected denominator 之外。

G5/G7 的关键限制是：92 个 eligible public cases 的依赖边审计结果为 **edge_count=0（92/92）**。因此 L 只能报告受影响 claim 的有限信息，不能报告可信的边级传播；U 在 92/92 个案例中均不具备资格。

---

## 4. G6：修正后的反事实验证

### 4.1 数据规模与协议

| 指标 | 数值 |
|---|---:|
| corrected family | 23 |
| counterfactual 类型 | CF1、CF2、CF3、CF4，共 4 类 |
| replicate | 3 |
| arm | G3 / G4 |
| 总计划行 | 23 × 4 × 3 × 2 = 552 |
| G3 行 | 276 |
| G4 行 | 276 |
| 每个 arm×CF | 69（23 family × 3 replicate） |
| workers | 2（严格保持用户指定的 G6 配置） |
| plan/response/trace | 552/552/552 |
| model requests/responses | 1826/1826 |
| tool calls/results | 1796/1796 |
| total tokens | 3,454,449 |
| trace-audit cost | $6.057783 |
| revision audit | 138 条；valid=0 |
| raw nonmonotonic trace | 0（derived trace view） |

G6 A 臂的协议缺陷已修复为显式 `g6_protocol_g3_tools_iteration`：G3 使用有界公开工具并固定执行第二遍 synthesis/reflection；G4 保持 adaptive 工具流程。G6 审计 `pass=true`，release review 的 `structural_review_pass=true`；但 `scientific_release_allowed=false`。

### 4.2 G6 按 counterfactual 的准确率

这里的 accuracy 是对 G6 decision/original-claim 状态的协议指标，不是最终科学定律 VLDR。

| CF | G3 正确/69 | G3 准确率 | G4 正确/69 | G4 准确率 | G4−G3 | family bootstrap 95% CI | McNemar p |
|---|---:|---:|---:|---:|---:|---|---:|
| CF1 | 37 | 53.623% | 43 | 62.319% | +8.696 pp | [-1.449, 20.290] pp | 0.263176 |
| CF2 | 69 | 100.000% | 69 | 100.000% | 0.000 pp | [0.000, 0.000] pp | 不适用 |
| CF3 | 44 | 63.768% | 25 | 36.232% | -27.536 pp | [-42.029, -11.594] pp | 0.000546 |
| CF4 | 41 | 59.420% | 49 | 71.014% | +11.594 pp | [-1.449, 24.638] pp | 0.133801 |
| **ALL** | **191/276** | **69.203%** | **186/276** | **67.391%** | **-1.812 pp** | **[-7.609, 4.348] pp** | **0.635308** |

CF3 的独立 revision audit 为 138 条、valid=0；CF3 中“正确识别原命题无效”和“给出正确修订命题”是两个不同指标，不能用 decision accuracy 替代 revision validity。

### 4.3 G6 发布门禁

当前仍未满足的科学门禁：

- Grade-B source-only 数学核验尚缺独立外部数学/domain review。
- provider 只提供模型身份/creation metadata，没有 immutable weight fingerprint。
- 没有独立 billing export。
- 统计分析虽按 23 个 family 聚类，但尚未完成独立统计复核。
- 上游 NewtonBench provenance 和远程交付仍受网络阻断。

---

## 5. G7：Failure Localization

### 5.1 输入与冻结计划

| 指标 | 数值 |
|---|---:|
| G7 public cases | 92 |
| theory families | 23 |
| 每 family 的 CF | 4（CF1–CF4） |
| groups | G3、G4 |
| diagnostic arms | D0、D1、D2、D3、L_ONLY、U_ONLY、V_ONLY，共 7 |
| replicate | 1 |
| fork 总计划 | 92 × 2 × 7 × 1 = 1288 |
| checkpoint 计划 | 92 × 2 = 184 |
| G3 fork 计划 | 644 |
| G4 fork 计划 | 644 |
| workers | 16（只用于 G7；G6 仍为 2） |
| model | glm-5 |
| G7 evidence status | `IMPORTED_REQUIRE_CHECKPOINT_PROVIDER_ORACLE_TRACE_AUDIT` |

每个 checkpoint 是新的 provider call，不从 G6 最终输出回填；G7 provider prompt 只读取 public case 和独立 G7 local labels，不读取 G6 private oracle、G6 model response 或 answer key。

### 5.2 G7 覆盖率与失败保留

| 对象 | 计划 | canonical selected | completed | terminal failure | 完成率 |
|---|---:|---:|---:|---:|---:|
| fork/state | 1288 | 1288 | 993 | 295 | 77.096% |
| checkpoint | 184 | 184 | 153 | 31 | 83.152% |

fork 终止状态为 `checkpoint_missing=217`、`provider_error=78`；checkpoint 终止状态为 `provider_error=31`。所有计划 ID 都存在，`missing_ids=[]`，但失败记录没有被当成成功记录。

### 5.3 G7 各诊断臂指标

“全计划准确率”把未完成/无效行保留在计划分母中；“有效回答准确率”只在已完成且可解析的回答中计算。因此两列不能互换。

| 组别 | 条件 | 完成/计划 | 完成率 | 全计划最终决策准确率 | 有效回答准确率 | 缺失/无效 |
|---|---|---:|---:|---:|---:|---:|
| G3 | D0 | 56/92 | 60.870% | 41.304% | 67.857% | 36 |
| G3 | D1 | 61/92 | 66.304% | 50.000% | 75.410% | 31 |
| G3 | D2 | 59/92 | 64.130% | 47.826% | 74.576% | 33 |
| G3 | D3 | 59/92 | 64.130% | 51.087% | 79.661% | 33 |
| G3 | L_ONLY | 59/92 | 64.130% | 43.478% | 67.797% | 33 |
| G3 | U_ONLY | 59/92 | 64.130% | 41.304% | 64.407% | 33 |
| G3 | V_ONLY | 59/92 | 64.130% | 48.913% | 76.271% | 33 |
| G4 | D0 | 87/92 | 94.565% | 55.435% | 58.621% | 5 |
| G4 | D1 | 85/92 | 92.391% | 60.870% | 65.882% | 7 |
| G4 | D2 | 80/92 | 86.957% | 63.043% | 72.500% | 12 |
| G4 | D3 | 77/92 | 83.696% | 57.609% | 68.831% | 15 |
| G4 | L_ONLY | 85/92 | 92.391% | 57.609% | 62.353% | 7 |
| G4 | U_ONLY | 85/92 | 92.391% | 58.696% | 63.529% | 7 |
| G4 | V_ONLY | 82/92 | 89.130% | 61.957% | 69.512% | 10 |

### 5.4 G7 配对诊断效应

这些是局部信息干预的诊断效果，不是内生因果机制。`both_completed` 是配对比较中两臂都完成的行数。

| 比较 | 两者均完成 | G3 均值差 | G4 均值差 | 可估计性 |
|---|---:|---:|---:|---|
| D1 − D0 | 138 | +0.086957 | +0.054348 | 可估计 |
| D2 − D1 | 136 | -0.021739 | +0.021739 | 可估计 |
| D3 − D2 | 0 | — | — | 不可估计 |
| L_ONLY − D0 | 136 | +0.021739 | +0.021739 | 可估计 |
| U_ONLY − D0 | 0 | — | — | 不可估计 |
| V_ONLY − D0 | 133 | +0.076087 | +0.065217 | 可估计 |

### 5.5 G7 V/L/U/Q 标签与独立审计

| 指标 | 结果 |
|---|---:|
| V local label：CF1/CF3 | CONTRADICTED |
| V local label：CF2 | SUPPORTED |
| V local label：CF4 | INDETERMINATE |
| L edges | 0/92 cases 有可用 dependency edge |
| U eligible cases | 0/92 |
| U 注入 | 未伪造；全部保持空/不资格 |
| Q audit rows | 1288 |
| Q independently valid | 3 |
| Q invalid | 1285 |
| G8 auto-selected mechanism | 0 |

Q invalid 的主要原因是 terminal/missing state 和严格 verdict 审计失败。Q 结论不能通过后处理把模型输出改成 PASS。

### 5.6 G7 资源与并发

每个 worker 的硬上限为：100,000 model calls、100,000 tool calls、100,000,000 tokens、$1,000。16 个 worker 的 summary 汇总记录约 5,540 model calls、3,619 tool calls、12,183,598 tokens、$19.263478；该汇总包含 worker-12 的 resume accounting，只用于运行资源审计，不能替代去重后的科学指标。

---

## 6. 完整性、隔离与复现证据

### 6.1 关键完整性检查

- G6 corrected audit：`pass=true`，552/552/552，`worker_counts=[2]`。
- G6 release review：`structural_review_pass=true`，但 `scientific_release_allowed=false`。
- G7 input audit：92 cases、23 families、552 G6 handoff rows、无 mock/demo。
- G7 merge：fork/checkpoint 均无 missing ID。
- G7 completed state 的 trace_ref 和 checkpoint_trace_ref 全部存在。
- G7 provider trace 未发现 `private_oracle`、`g6_import`、`answer_key` 字符串泄漏。
- raw append-only retry trace 未被覆盖；G6 只使用 derived canonical trace view。

### 6.2 关键 SHA-256

| 产物 | SHA-256（前缀可用于人工核对） |
|---|---|
| G6 run plan | `c60b14205f061fa2178b9d0a42074d9957a460bea2cf4e06b841acbe4b0bbde0` |
| G6 canonical responses | `97022fa9ac84dad61c24c98fbc1fee2ba2b357ee853eccd9614cc348da8312fa` |
| G6→G7 handoff | `ec51c3114b84da9f818d0f6407794e42454cbe87565aa0baaf60081c61602c02` |
| G7 run plan | `549c39a9508fae3c7611564f0cca6022ade5dda67f52d8cc6c1fbd51b9633eb3` |
| G7 states | `714e53654e070a74bc026c11c7396fc243b8e4b72a45e3ed4e9025d8fe66efef` |
| G7 checkpoints | `28cbfead349cc35682141df3ac99841d3ebbecdde08280d2849738645b201932` |
| G7 Q audit | `7090520110215c742259dc5598d0c37dc14a155dfd93dc165d011a3e460d27ff` |
| G7 score report | `060e5a59fc52caaed6bdc773c0fe4252cc732f5d66e8b837f5740c14095da43e` |

### 6.3 测试计数

| 测试/检查 | 结果 |
|---|---:|
| G6 skill package tests | 13 passed |
| G7 skill package tests | 8 passed |
| host `pytest -q` | 99 passed |
| relevant scripts `py_compile` | PASS |
| G7 offline doctor | PASS |
| G7 strict-real input audit | PASS |
| G7 independent Q audit | 1288 rows retained；3 valid |

---

## 7. 当前限制与不应作出的结论

1. 不能根据 G6 的 -1.812 pp pooled difference 声称 G4 Agent 劣于或优于 G3；该结果仍等待独立统计复核，且 oracle 是 controlled-intervention grade-C evidence。
2. 不能根据 G7 D1/V_ONLY 的局部恢复差异声称发现了内生失败机制；G7 local labels 是诊断性信息干预。
3. 不能把 G7 77.096% fork completion 当作有效回答准确率；295 个 terminal failures 必须留在分母或单独作为失败分析。
4. 不能把 Q valid=3/1288 隐去，也不能后处理修正 Q verdict。
5. 不能把 23 个 grade-B family 当成已完成外部 domain-grade 数学证明。
6. G7 每臂只有 1 个 replicate；D3−D2 和 U_ONLY−D0 在当前完成数据下不可估计。
7. G8 没有自动选择 mechanism；G8 需要新的外部 trace、数学和因果审查。

---

## 8. 结论与复现入口

**执行层面**：G0–G6 的可修复内部协议/数据问题已经复核，G6 corrected run 已完成；G7 已完成冻结计划、真实 checkpoint/fork 执行、16-way 并行、canonical merge、独立 Q 审计、score 和 G8 handoff。

**科学层面**：当前最终状态是 `BLOCKED_PENDING_EXTERNAL_REVIEW_AND_PROVIDER_FAILURES`。该状态不是实验未运行，而是实验运行结果中仍有真实失败，并且外部科学发布门禁未关闭。

关键文件：

- `docs/state/G6_HANDOFF_NEXT_AGENT.md`
- `results/g6_counterfactual/protocol-g3tools-v2-20261014T030000Z/g6_audit/audit_final.json`
- `results/g6_counterfactual/protocol-g3tools-v2-20261014T030000Z/g6_release_review_final.json`
- `results/g7_failure_localization/formal-20261014T030000Z-16workers/g7_input_audit_final.json`
- `results/g7_failure_localization/formal-20261014T030000Z-16workers/g7_score_report.json`
- `results/g7_failure_localization/formal-20261014T030000Z-16workers/g7_q_audit.jsonl`
- `results/g7_failure_localization/formal-20261014T030000Z-16workers/g8_handoff.json`
- `docs/audits/cycle-20261014T163000Z-20/audit.json`

