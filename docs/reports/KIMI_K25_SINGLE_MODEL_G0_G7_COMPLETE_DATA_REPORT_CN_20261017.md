# Kimi K2.5 单模型 G0–G7 完整数据报告

**报告周期**：2026-10-17  
**实验对象**：Kimi K2.5，单模型、真实 API 执行  
**实验入口**：`single_model_g0_g7`  
**报告边界**：本报告只汇总已落盘、可复核的公开数据、聚合审计和失败记录；不包含私有 oracle 原值、API 凭据或原始敏感模型响应。

## 1. 执行结论

本轮已经完成 Kimi K2.5 的 G6 和 G7 单模型 API 执行，并完成 canonical merge、trace 审计、Q 审计、纠正指标审计、独立 release review、全量测试和状态交接。

但是，本轮**不是可发布的确认性科学结果**：

- G0 仅在固定模拟器 provenance/licensing 层面通过；官方数值 evaluator 未被宣称已接入。
- G1–G5 是协议、隔离、评估器和真实 simulator smoke/engineering evidence，不是正式 provider VLDR 结果。
- G6 保留了 552 个计划行，但有 2 个终端 provider error，revision-valid 为 0；私有 oracle 为受控干预等级 C，不是独立领域级真值。
- G7 保留全部 1,288 个计划行，但只有 35 个 state 完成，1,253 个 state 为 `checkpoint_missing`；Q 有效行是 `0/1288`，因此不能做 V/L/U/Q、机制、因果或 superiority 结论。
- 当前总状态为 `scientific_release_allowed=false`。

## 2. 与实验设计的对应关系

实验设计文档把 G0–G5 定义为历史基础/工程和 smoke 阶段，把 G6 定义为四类前提干预，把 G7 定义为 V/L/U/Q 过程定位。设计中 G7 的正式规划是约 24 个独立理论族、3 次重复、主实验 1,152 行加补充 288 行，合计约 1,440 行；该数字是规划值，不是强制事实。

本次实际冻结数据为：

| 项目 | 实际值 |
|---|---:|
| 合格理论族 | 23 |
| 排除理论族 | `TB-L1-010`，未合成、未恢复 |
| G6 public cases | 92 = 23 族 × CF1–CF4 |
| G6 组别 | G3 / G4 |
| G6 每 case 重复 | 3 |
| G6 计划行 | 552 = 92 × 2 组 × 3 重复 |
| G7 checkpoints | 184 = 92 cases × G3/G4 |
| G7 每 checkpoint arms | D0、D1、D2、D3、L_ONLY、U_ONLY、V_ONLY，共 7 |
| G7 计划行 | 1,288 = 184 × 7 |

因此，本轮 G7 是**当前修正协议下的 1,288 行诊断执行**，不是设计建议中约 1,440 行、3 重复的完整正式规模；不能把它写成已满足设计样本量的确认性实验。

## 3. 模型、接口与预算

| 项目 | 值 |
|---|---|
| model id | `kimi-k2.5` |
| base URL | `https://token.ctflow.cn/v1` |
| G6 workers | 2 |
| G6 单 worker 本地硬成本上限 | `$20` |
| G7 workers | 16 |
| G7 aggregate cap | `$60` |
| G7 有效单 worker cap | `$3.75` |
| 用户总预算授权 | `$200` |
| 外部 invoice/billing | 未独立验证 |
| immutable model snapshot/weight fingerprint | 未验证 |
| 本地观测成本范围 | G6 `$2.034328`；G7 `$2.722796`；合计 `$4.757124` |

这里的成本是本地 trace/worker summary 的观测值，不是 provider invoice。不能把 `$4.757124` 写成已经核验的账单金额。

## 4. G0–G5 状态与数据边界

| Gate | 状态 | 已有证据 | 结论边界 |
|---|---|---|---|
| G0 | PASS（限定范围） | NewtonBench pinned commit `912a4ba5f4356ddd06acc16e44460ca30be4abc2`；vendored archive 与 LICENSE hash 已核验 | 只证明 simulator provenance/licensing；`official_numeric_evaluator=false`，不证明正式科学结果 |
| G1 | PASS（engineering） | frozen plan、无工具、无中途反馈、observation swap、plan hash 控制通过测试 | 不证明真实 provider 的 LLM-only 科学结果；历史 formal coverage 为 `0/720` |
| G2 | PASS（engineering） | Agent 公共观察分支、工具白名单、非法工具失败路径通过测试 | 不证明 Agent superiority |
| G3 | PASS（engineering） | 预算 ledger、private-oracle isolation、retry policy、公共初始信息控制通过测试 | G3/G4 matched scientific inference 未发布 |
| G4 | PASS（evaluator） | numeric、structural、OOD、malformed、overfit、illegal candidate 测试通过 | 不证明上游 provenance 或真实模型结果 |
| G5 | PASS（smoke/engineering） | 真实 simulator smoke 与 mock pipeline 持久化；保留 23/24 source-only family subset、零 dependency edges | 不是 formal VLDR evidence；没有制造 L/U 边 |

G0–G5 的 PASS 是分层 PASS，不等同于整项实验 PASS。

## 5. G6 完整数据

### 5.1 输入、覆盖与完整性

- 计划行：`552/552`
- public cases：`92/92`
- private oracle rows：`92/92`
- canonical responses：`552/552`
- canonical traces：`552/552`
- final status：`550 completed`、`2 provider_error`
- terminal failures：2，全部保留
- revision audit rows：138
- revision-valid：`0/138`
- trace-integrity failures：0
- handoff rows：0；因此没有把 G6 结果误标为可供 G7 的成功机制交接

G6 的 canonical hash：

| 数据 | SHA-256 |
|---|---|
| `run_plan.jsonl` | `c60b14205f061fa2178b9d0a42074d9957a460bea2cf4e06b841acbe4b0bbde0` |
| `public_cases.jsonl` | `1bffc3769523e437cc7e4ea5cff22f4eb2d42cd3500299f914cb03ec36b6063f` |
| private oracle | `e966efbadffea604d4de735a0323dbb5ffb2593e510bb8a456cb84422258d6c0` |
| canonical responses | `f907f7ad778461ca3ebae6dcd019540f1ec05d84de7fb088df03074eb974a139` |

### 5.2 G6 按反事实类型的描述性结果

以下是模型 `decision` 与受控 private oracle 的 `expected_decision` 的**原始描述性匹配**。由于 oracle 为等级 C、revision-valid 为 0，这些数字不能作为确认性准确率或模型科学能力结论。

| CF | 计划 | 完成 | provider error | completed 中匹配 oracle | completed 模型决策分布 |
|---|---:|---:|---:|---:|---|
| CF1 critical_flip | 138 | 138 | 0 | 124 | REJECT 124，MAINTAIN 8，REVISE 6 |
| CF2 irrelevant_equivalent | 138 | 137 | 1 | 137 | MAINTAIN 137 |
| CF3 boundary_weakening | 138 | 137 | 1 | 29 | REJECT 55，MAINTAIN 51，REVISE 29，UNDETERMINED 2 |
| CF4 insufficient_information | 138 | 138 | 0 | 109 | UNDETERMINED 109，REJECT 18，REVISE 18，MAINTAIN 4 |
| **合计** | **552** | **550** | **2** | **399** | **MAINTAIN 200，REJECT 197，UNDETERMINED 111，REVISE 42** |

按组汇总：

| 组别 | 计划 | 完成 | provider error | completed 中匹配 oracle |
|---|---:|---:|---:|---:|
| G3 | 276 | 274 | 2 | 209 |
| G4 | 276 | 276 | 0 | 190 |

### 5.3 G6 资源与 trace

- model requests：1,482
- model responses：1,480
- tool calls：1,644
- tool results：1,644
- response tokens：1,611,628
- canonical response cost：`$2.034328`
- append-only 历史 segment-end 中曾出现 `26 provider_error`；canonical final 状态只保留最终 `2 provider_error`，并没有删除失败历史
- 独立 G6 structural review：coverage accounting 通过；`g6_audit_pass=false`，`scientific_release_allowed=false`

## 6. G7 完整数据

### 6.1 严格 preflight

G7 preflight 在 provider calls 之前执行，结果如下：

- provider calls made by preflight：`false`
- formal run allowed by protocol：`true`
- public cases：92
- private labels：92
- plan rows：1,288
- checkpoints：184
- 每个 checkpoint 的 arms：D0、D1、D2、D3、L_ONLY、U_ONLY、V_ONLY
- protocol/lineage/privacy/mapping/hash errors：0
- missing cases/labels：0
- duplicate run IDs：0
- incomplete checkpoints：0

G7 输入 hash：

| 数据 | SHA-256 |
|---|---|
| public | `1bffc3769523e437cc7e4ea5cff22f4eb2d42cd3500299f914cb03ec36b6063f` |
| labels | `29782338db2a76a7c854cacb8c68479cb6a47241caddadc26ba18393cc0e7490` |
| plan | `be6c5550dfc453110b3f526f9ed6cf865bb0c1df5c3891b87dc0a23d6cf4c2e5` |

### 6.2 canonical 状态与失败

| 对象 | 总数 | 完成 | 失败/缺失 |
|---|---:|---:|---:|
| state rows | 1,288 | 35 | 1,253 `checkpoint_missing` |
| checkpoint rows | 184 | 5 | 179 `provider_error` |
| Q rows | 1,288 | 0 valid | 1,288 `NOT_SCORED`/invalid |

canonical trace/Q consistency audit：

- state trace integrity failures：0
- checkpoint trace integrity failures：0
- state trace status：1,253 `not_executed`，35 `pass`
- checkpoint trace status：179 `terminal_failure_evidence`，5 `pass`
- unique state run IDs：1,288
- unique checkpoint IDs：184
- missing state/Q rows：0
- valid rows invalidated by trace review：0；因为最初没有独立有效 Q 行
- terminal failures retained：true
- retries pooled：false
- confirmatory reuse allowed：false
- scientific truth decision made：false

### 6.3 G7 按 arm 的诊断数据

所有 arm 都计划 92 行。`all_planned_correct` 把缺失/失败保留在分母；`valid_only_accuracy` 只描述已完成的少量行，不能解释为正式效果。

| Arm | 完成/计划 | all-planned correct | valid-only accuracy | W→C | C→W | 首次可观察错误/缺失 |
|---|---:|---:|---:|---:|---:|---|
| G3 D0 | 0/92 | 0 | — | 0 | 0 | missing 92 |
| G3 D1 | 0/92 | 0 | — | 0 | 0 | missing 92 |
| G3 D2 | 0/92 | 0 | — | 0 | 0 | missing 92 |
| G3 D3 | 0/92 | 0 | — | 0 | 0 | missing 92 |
| G3 L_ONLY | 0/92 | 0 | — | 0 | 0 | missing 92 |
| G3 U_ONLY | 0/92 | 0 | — | 0 | 0 | missing 92 |
| G3 V_ONLY | 0/92 | 0 | — | 0 | 0 | missing 92 |
| G4 D0 | 5/92 | 4 | 0.8 | 0 | 0 | L 3，V 2，missing 87 |
| G4 D1 | 5/92 | 4 | 0.8 | 1 | 1 | L 3，none 2，missing 87 |
| G4 D2 | 5/92 | 5 | 1.0 | 1 | 0 | none 3，U 2，missing 87 |
| G4 D3 | 5/92 | 5 | 1.0 | 1 | 0 | none 4，U 1，missing 87 |
| G4 L_ONLY | 5/92 | 4 | 0.8 | 0 | 0 | L 1，V 1，U 1，none 2，missing 87 |
| G4 U_ONLY | 5/92 | 5 | 1.0 | 1 | 0 | L 4，V 1，missing 87 |
| G4 V_ONLY | 5/92 | 5 | 1.0 | 1 | 0 | L 3，none 2，missing 87 |

由于 G3 的 7 个 arm 全部为 0/92，G4 每个 arm 只有 5/92 完成，以上 arm 差异完全不能支持机制、恢复率、V/L/U/Q 或因果解释。

### 6.4 G7 资源

16 个 worker summary 合计记录：

- model calls：1,452
- tool calls：1,134
- response tokens：1,998,276
- worker-summary local cost：`$2.722796`
- 16 workers 全部正常退出；canonical merge 后没有遗漏的计划 ID

## 7. 跨阶段成本与数据完整性

| 阶段 | canonical/summary 本地观测成本 | 解释 |
|---|---:|---|
| G6 | `$2.034328` | canonical response trace audit 汇总 |
| G7 | `$2.722796` | 16 个 worker summaries 汇总 |
| G6+G7 | `$4.757124` | 本地观测值，不是外部账单 |

数据完整性控制结果：

- 所有计划行都保留在 canonical denominator。
- provider failure、checkpoint missing、invalid Q 没有被静默删除。
- G7 retries 没有与原运行池化。
- 没有把 `g7_vlu_private.jsonl` 错当作 G6 oracle；最终 corrected metrics 使用的是正确的 G6 private oracle。
- 错误的 trace-root 参数化审计没有作为最终证据；最终审计使用了正确 artifact root。
- 本报告和提交中不包含 `runs/` 原始运行目录、私有 oracle 原文、API key 或 Bearer token。

## 8. 可报告与不可报告的结论

### 可以报告

1. Kimi K2.5 在冻结的 G6/G7 协议上确实发起了真实 API 执行。
2. G6 的 552 行和 G7 的 1,288 行均完成了计划级 canonical accounting。
3. 失败、缺失、重试和 trace 状态均被持久化并保留在分母中。
4. G7 的当前执行瓶颈是 provider execution failure / checkpoint missing，而不是由审计脚本删除数据造成。
5. 当前工程与审计协议能发现并阻止不完整数据被升级成确认性科学结果。

### 不能报告

1. 不能报告 Kimi K2.5 的正式 VLDR、科学发现率或 Agent superiority。
2. 不能报告 G3 与 G4 的显著差异。
3. 不能报告 V、L、U、Q 中任何一个是自然错误瓶颈。
4. 不能报告 D1/D2/D3、L_ONLY/U_ONLY/V_ONLY 带来了机制恢复效果。
5. 不能把 G6 的 399/550 descriptive oracle matches 当成独立科学准确率。
6. 不能把 G7 的 G4 5/92 完成行上的 0.8/1.0 当成正式 arm accuracy。
7. 不能把本地 `$4.757124` 当成 provider invoice，也不能声称模型 immutable weights 已验证。

## 9. 审计产物与复现入口

主审计：[Kimi K2.5 G0–G7 audit.json](../audits/cycle-20261017T-kimi-k25-single-model-g0-g7/audit.json)

状态与 gate：[gates.json](../state/gates.json)、[issues.json](../state/issues.json)、[UNRESOLVED_REPORT.md](../state/UNRESOLVED_REPORT.md)

主要原始/派生数据位置（不进入公开提交）：

- G6：`runs/ctflow_single_model/20261017T-g6-kimi-k25-v1/`
- G7：`runs/ctflow_single_model/20261017T-g7-kimi-k25-v1/`
- G6 public/plan/oracle：`results/g6_counterfactual/protocol-g3tools-v2-20261014T030000Z/`
- G7 public/labels/plan：`results/g7_failure_localization/formal-20261015T060000Z-protocol-corrected-16workers/`

关键复核命令：

```text
E:/resources/python/python.exe -X utf8 -m pytest -q
E:/resources/python/python.exe scripts/review_g6_release.py ... --allow-terminal-failures
E:/resources/python/python.exe scripts/g7_protocol_preflight.py ...
E:/resources/python/python.exe scripts/merge_g7_states.py ...
E:/resources/python/python.exe scripts/audit_g7_q.py ...
E:/resources/python/python.exe scripts/audit_g7_trace_q_consistency.py ...
E:/resources/python/python.exe scripts/audit_g7_corrected_metrics.py ...
```

最终测试结果：`262 passed`。本报告对应的 GitHub 分支为 `autopilot/scientific-law-discovery`，远端已验证到提交 `211d215a7d53d56530c5f54c5d984cfae1a12463`。

