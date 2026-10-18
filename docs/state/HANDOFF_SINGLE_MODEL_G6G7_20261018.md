# 单模型 G6/G7 继续执行交接文档

**生成时间：** 2026-10-18（Asia/Hong_Kong）

**仓库：** `E:/master_exp/nature_prj1_cal/from_llm_to_agent`

**分支：** `autopilot/scientific-law-discovery`

**当前本地 HEAD：** `bcecb8d31098be8bcfb7189c4c3da0e60f5fd81f`
**文档性质：** 当前状态的单模型 G6/G7 执行交接；不覆盖原始数据、冻结协议或历史失败记录。

> 本文是给下一次执行者的可操作交接，不是科学结果发布。`docs/state/issues.json` 仍是问题状态的权威来源，`docs/state/gates.json` 仍是门禁状态的权威来源。

## 1. 先看结论

当前不是“代码完全坏了”，而是单模型正式 G6/G7 同时被以下硬门禁阻断：

1. G7 有 137 个 `checkpoint_missing` 和 1 个 `provider_error` 状态。
2. G7 原始轨迹仍有 13 个 genuine final-attempt lifecycle inconsistencies；历史 28 个缺陷已解释为 15 个边界伪影加 13 个真实终态缺陷。
3. 生产 Q 没有可独立重放、可评分的结构化 claim；Q 必须保持 `NOT_SCORED`，不能用模型文本补分。
4. 92 个 G7 图案例没有独立可审计 dependency edge，L/U 不能计算。
5. provider 价格、账户账单/usage export、不可变模型身份或 gateway weight fingerprint 未独立验证。
6. G6 revision 的 138 行只有 18 PASS、59 INCONCLUSIVE、61 NOT_SCORED，不能形成确认性统计。

因此当前总状态必须保持：

```text
scientific_release_allowed = false
G6 = BLOCKED
G7 = BLOCKED
Q = NOT_SCORED
L/U = UNVERIFIED
```

单模型的正确含义是：**选择一个不可变模型 ID，同时完成该模型的 LLM-only 和 Agent 两个匹配臂**。只跑一个臂只能叫 pilot，不能叫完整 G6/G7 科学实验；Kimi 和 Qwen 的历史运行也不能混合成一个单模型结果。

## 2. 必须遵守的 Skill 规则

先完整阅读：

```text
.agents/skills/scientific-law-recovery/SKILL.md
.agents/skills/scientific-law-autopilot/SKILL.md
docs/state/issues.json
docs/state/UNRESOLVED_REPORT.md
docs/state/HANDOFF.md
docs/state/gates.json
```

核心规则：

- G0–G5 的 PASS 目前只表示 provenance、协议、隔离、评估器和 smoke 的工程证据，不表示正式科学结果。
- LLM-only 必须是冻结计划、无工具、无中途反馈、无中途重规划。
- Agent 必须使用同一个基础模型、相同任务集、相同动作空间和相同预算，唯一差别是允许基于观察自适应行动。
- hidden law、private labels、private oracle 不得进入模型过程或 Q 独立审计器。
- 所有失败、provider error、checkpoint missing、重试片段和格式错误都保留在原始证据中，不得删除、覆盖或静默排除。
- mock、smoke、兼容性预检和单案例 pilot 都不是科学结果。
- 没有独立 evaluator proof、独立验证和合格分母时，不得计算或声称 VLDR。
- 外部阻塞必须在 issue ledger 中保持 `BLOCKED` 或 `RESOLVED_UNVERIFIED`，不能因本地测试通过而关闭。
- 付费正式批次必须先通过 provider、身份、账单、预算和 trace writer 门禁；不能使用“无限预算”绕过门禁。

## 3. 当前已完成且不得重做的内容

### 3.1 工程门禁

| 阶段 | 当前状态 | 可声称范围 |
|---|---|---|
| G0 | PASS | 本地 pinned simulator/license；GitHub 远端交付仍未验证 |
| G1 | PASS | LLM-only 工程隔离和非自适应约束 |
| G2 | PASS | Agent 观察驱动动作能力 |
| G3 | PASS | 预算、隔离、重试和 private-oracle 边界 |
| G4 | PASS | evaluator adversarial 工程覆盖 |
| G5 | PASS | 真实入口和 smoke；不是科学证据 |
| G6 | BLOCKED | 结构审计有结果，正式统计和科学发布未通过 |
| G7 | BLOCKED | 预检和部分恢复有结果，正式 Q/L/U/科学发布未通过 |

### 3.2 G6 当前真实数据

- 规范化计划/响应：552/552。
- 原始尝试视图：550 completed，2 provider error；失败必须保留。
- revision 分母：138（G3 69，G4 69）。
- 根因分类：`BAD_DECISION=109`，`VERIFIER_INCONCLUSIVE=29`。
- secondary `REVISED_CLAIM_NULL=61`。
- 独立数学审计：PASS 18，INCONCLUSIVE 59，NOT_SCORED 61。
- 有效 revision claim：0/138。
- 当前统计只能做描述性审计，不能做 VLDR、优越性或确认性推断。

### 3.3 G7 当前真实数据

- 冻结 state IDs：1288/1288。
- checkpoints：184/184。
- 状态：1150 completed，137 `checkpoint_missing`，1 `provider_error`。
- canonical trace-valid：1123；trace-qualified sensitivity：1138。
- 仍需真实 provider response 的状态：138。
- 历史 trace 缺陷：28 = 15 attempt-boundary + 13 genuine final-attempt。
- Legacy Q：eligible 0，verified pass/fail/inconclusive 0，1150 NOT_SCORED，138 INELIGIBLE。
- Legacy L/U：92 个 graph cases，0 个 declared dependency edges，L scored 0，U scored 0。
- Q-v2：`NOT_RUN`。
- LU-v2：仅 smoke，不能作为科学结果。

### 3.4 单模型历史运行边界

- Kimi K2.5：有 G6/G7 单模型真实调用和较完整的结构审计，但仍受 provider、trace、Q、L/U、统计门禁阻断。
- Qwen：有 G6/G7 历史运行；G7 terminal failures 为 850，不能作为正式结果。
- Qwen 单案例 retry：1 个冻结案例，4 次成功 retry 模型调用、1 次工具调用、7314 tokens；这是非确认性 pilot，不得并入 1288 分母。
- CTFlow 矩阵：Qwen/GLM × LLM-only/Agent 共 4 个 job 均因缺少 `result.json` evaluator proof sidecar 未验证，不是科学结果。

## 4. 问题台账与解除条件

以下 ID 必须复用，不能为同一个根因新建重复 issue：

| Issue | 状态 | 根因 | 解除条件 |
|---|---|---|---|
| `ISSUE-7c2d4e9a10bf` | P1 IN_PROGRESS | G7 仍有 13 个真实终态 trace lifecycle 缺陷 | 修复 writer 并重新生成独立审计，或在 corrected writer 下重跑这些状态；原始缺陷永久保留 |
| `ISSUE-000000000002` | P1 BLOCKED | provider billing、usage、不可变模型身份缺失 | provider 可核验账单/usage export + immutable model/gateway fingerprint |
| `ISSUE-000000000003` | P1 BLOCKED | 上游 provenance/GitHub remote 外部不可达 | 恢复网络/凭据，验证 upstream commit/license 和 remote SHA |
| `ISSUE-000000000004` | P1 BLOCKED | 正式统计有效性未建立 | 独立复核 Q/math、paired denominator、bootstrap/McNemar 和 preregistration |
| `ISSUE-1f8c2b6a4d90` | P1 BLOCKED | 0/92 dependency edges，L/U 无可评分转移 | 获得独立审计的 edge/state 数据；禁止从模型文本或 private labels 合成 |
| `ISSUE-3d7a9c1e5b20` | P1 BLOCKED | G7 不完整状态和终态失败 | 对 138 状态做 append-safe 精准恢复，失败仍保留 |
| `ISSUE-ff97c7c89112` | P1 RESOLVED_UNVERIFIED | G5/G6 数学 verifier 还缺外部域审查 | 独立审查 23-family corrected subset；不得恢复 TB-L1-010 |
| `ISSUE-ad61f025976a` | P1 RESOLVED_UNVERIFIED | preflight 不是 immutable weights/billing 证明 | 获取外部可验证的模型身份和计费证据 |
| `ISSUE-000000000005` | P2 OPEN | classical baseline 只有接口 | 当前 G6/G7 不扩展 classical comparison |

## 5. 单模型正式执行的定义

执行者只能在一个新建的、明确命名的 cohort 中使用一个模型：

```text
MODEL_ID = provider 返回的精确模型 ID
MODEL_ROUTE = 固定 base URL / gateway route
COHORT_ID = 新的单模型 G6/G7 cohort
ARMS = {LLM_ONLY, AGENT}
```

必须同时冻结并记录：

1. provider、base URL、精确 model ID、模型目录响应和模型身份证据。
2. 输入任务、public cases、private labels 的 SHA-256。
3. LLM-only plan hash、Agent action policy、tool/action schema。
4. 每臂最大 model calls、tool calls、tokens、时间和美元上限。
5. retry policy、terminal-failure policy、trace schema 和 evaluator proof sidecar schema。
6. G6/G7 预注册 cohort、分母、排除规则和统计方法。

禁止：

- 把 Kimi 和 Qwen 合并成一个结果。
- 把 pilot、smoke、mock、旧批次或失败恢复结果静默合并到新 cohort。
- 用 Qwen pilot 证明 Qwen 正式能力。
- 用已有模型文本重写 Q、补充 L/U edge 或覆盖冻结真值。
- 为得到显著结果而更换分母、挑选完成行、删除失败行或增加未预注册 arm。

## 6. 推荐执行顺序：先离线，后付费

### Step A：启动和状态确认

在仓库根目录运行：

```powershell
git status --porcelain=v1
git remote -v
git branch --show-current
git log -8 --oneline
E:/resources/python/python.exe -X utf8 scripts/recovery_state.py bootstrap
E:/resources/python/python.exe -X utf8 scripts/recovery_state.py next
```

重新阅读 `issues.json`、`UNRESOLVED_REPORT.md`、`HANDOFF.md`、`gates.json`。若状态与本文不同，以最新 machine-readable 文件为准，并在本文件或新审计中记录差异。

### Step B：离线回归和独立审计

```powershell
E:/resources/python/python.exe -X utf8 -m pytest -q
E:/resources/python/python.exe -X utf8 -m py_compile scripts/run_g7_failure_localization.py scripts/v3/q_v2.py scripts/v3/lu_v2.py scripts/v3/observability_smoke.py
E:/resources/python/python.exe -X utf8 scripts/v3/observability_smoke.py --out docs/audits/single-model-smoke-<UTC>
E:/resources/python/python.exe -X utf8 scripts/audit_repair/review_v3_audit.py --docs docs/audits/cycle-20261018T-g6g7-v3
```

离线验收必须确认：

- raw runs、冻结输入和 protected hashes 未改变。
- trace writer 的 adversarial tests 通过。
- 所有 retry 是 append-safe，不能删除历史事件。
- G7 state/checkpoint join 的 expected IDs、duplicate IDs、terminal states 全部可解释。
- `Q_v2` 和 `LU_v2` 若没有真实正式输入，只能标记 `NOT_RUN` 或 `SMOKE_ONLY_NOT_SCIENTIFIC`。

### Step C：修复 G7 trace lifecycle

先针对 `ISSUE-7c2d4e9a10bf` 重现，不要先付费重跑：

1. 检查 `scripts/run_g7_failure_localization.py` 的 `trace_path_for_retry`、`existing_trace_sequence`、`emit` 和 retry segment contract。
2. 加入或运行 adversarial tests：重复 RUN_START、重复 sequence/event/step ID、parent mismatch、RUN_END 非末事件、失败 trace 缺 RUN_END、并发 append。
3. 生成新的 derived trace view，不能覆盖 `G7_TRACE_15_EXPLAINED_13_INVALID.jsonl`。
4. 只有 13 个 genuine final-attempt 缺陷清零并由独立只读审计复核后，才可解除 trace issue。

### Step D：精确恢复 138 个 G7 状态

仅在 trace writer 修复且 provider 门禁通过后恢复：

- 只恢复 138 个 `checkpoint_missing/provider_error` state IDs。
- 不重跑已完成状态，不并发运行同一 worker/state。
- 原始 output 目录只 append，不删除、不 reset。
- 每次请求写入 model request、response、tool event、cost ledger、RUN_END 和 result sidecar。
- provider 失败仍写入明确 terminal failure，不伪造 completed。

恢复后的结构性验收：

```text
selected_records = 1288
missing_ids = []
每个最终状态 = completed 或显式 terminal failure
每个 checkpoint = completed 或显式 terminal failure
raw traces 未覆盖
Q 仍 NOT_SCORED（除非真正新增并独立审查 verifier）
confirmatory_reuse_allowed = false，直到正式门禁全部通过
```

### Step E：provider 和付费门禁

正式付费前必须保存下列证据：

1. provider catalog/docs/base URL。
2. 精确 model ID 与 provider 返回值。
3. provider 可验证价格和账户 billing/usage export。
4. immutable model/gateway weight fingerprint；HTTP 返回的 `model` 字段不够。
5. hard cap 和 atomic ledger；余额、单请求、总 cohort 均 fail closed。
6. 成功和失败请求均有 trace/result sidecar。
7. 先完成最小 compatibility preflight，再决定是否允许正式 cohort。

如果账单或模型身份不能独立验证，状态仍是 `BLOCKED`；不能用本地 proxy estimate 代替供应商账单。

### Step F：G6/G7 正式验收

只有以下条件全部满足，才可生成正式科学报告：

- 单一 immutable model ID 同时完成 LLM-only 和 Agent 臂。
- 两臂使用相同任务集、动作空间、预算和 held-out evaluator。
- G6 response/revision 分母完整，失败保留，数学 verifier 独立通过。
- G7 轨迹无未解释的 final-attempt lifecycle failure。
- Q 有独立、可重放、与 private oracle 隔离的结构化验证。
- L/U 有真实、独立审计的 dependency edges 和 eligible non-final transitions。
- 每个正式 task 有 `status=COMPLETED`、`verified=true`、`mock=false`、evaluator proof sidecar。
- 统计方案预注册，并由独立只读 review 复核。
- cost ledger、provider billing、model identity 和 raw trace 哈希一致。

## 7. Skill 指标及其计算边界

主指标只能使用：

```text
VLDR = Validated Successful Tasks / All Evaluated Tasks
Delta_VLDR = VLDR_Agent - VLDR_LLM-only
```

必须同时报告：

- `VLDR_LLM-only`、`VLDR_Agent`、`Delta_VLDR`。
- paired/cluster-aware 95% CI。
- OOD error。
- task、失败、provider error、retry、model calls、tool calls、tokens、time、cost。
- Q 的 pass/fail/inconclusive/not-scored/ineligible 分解。
- L/U 的 edge 数、eligible transition 数和独立验证状态。

当前这些科学指标均为 `NOT_AVAILABLE`，不是 0：

```text
VLDR_LLM-only = NOT_COMPUTABLE
VLDR_Agent = NOT_COMPUTABLE
Delta_VLDR = NOT_COMPUTABLE
OOD error = NOT_SCORED
95% CI = NOT_ESTABLISHED
Q = NOT_SCORED
L/U = UNVERIFIED
```

失败率、完成率和调用/成本只能作为 execution diagnostics，不能替代 VLDR。

## 8. 需要生成的审计文件

每次修复周期至少生成：

```text
docs/audits/cycle-<timestamp>/
  SOURCE_MANIFEST.json
  G0_G7_GATE_MATRIX.json
  G6_*_MATH_*.json/jsonl/csv
  G7_STATE_ATTEMPT_MATRIX.csv
  G7_TRACE_*.jsonl
  G7_Q_*.json
  G7_LU_*.json
  PROVIDER_MODEL_PROVENANCE.json
  PROVIDER_BILLING_RECONCILIATION.json
  COST_AND_PROVIDER_EVIDENCE.json
  TEST_RUNS_AND_SHA256.json
  INDEPENDENT_READ_ONLY_REVIEW.json
  FINAL_GATES.json
  FINAL_RESULT_ONLY.md
```

报告中必须明确：

- 哪些数据来自旧批次，哪些来自新 cohort。
- 哪些行是 completed、provider error、checkpoint missing、not scored。
- 哪些指标是正式科学指标，哪些只是 diagnostic。
- 实际 provider billing 是否可核验；不可核验就写 `UNKNOWN`。
- Git remote 是否真的更新；没有 `ls-remote` 精确 SHA 就写未更新。

## 9. Git、隐私和恢复安全

不要提交：

- `runs/`
- `api_key/`
- `.env`、bearer token、私钥
- private labels/oracle
- 用户未提交的 `research_data_summary_G0_G7/`

每个修复周期执行：

```powershell
git diff --check
git status --porcelain=v1
git add <only-reviewed-source-tests-audits-state-files>
git commit -m "<truthful repair or audit summary>"
git push origin autopilot/scientific-law-discovery
git ls-remote origin refs/heads/autopilot/scientific-law-discovery
```

只有 `ls-remote` 返回与本地新 commit 完全相同的 SHA，才能写“remote 已更新”。当前 GitHub 443 连接仍失败，不能声称远端交付成功。

## 10. 最终验收模板

下一次执行结束时，最终报告必须按以下格式给出：

```text
单模型：<provider>/<exact model ID>
cohort：<new cohort id>
G0：PASS / BLOCKED / FAIL
G1：PASS / BLOCKED / FAIL
G2：PASS / BLOCKED / FAIL
G3：PASS / BLOCKED / FAIL
G4：PASS / BLOCKED / FAIL
G5：PASS / BLOCKED / FAIL
G6：PASS / BLOCKED / FAIL
G7：PASS / BLOCKED / FAIL

VLDR_LLM-only：数值或 NOT_COMPUTABLE
VLDR_Agent：数值或 NOT_COMPUTABLE
Delta_VLDR：数值或 NOT_COMPUTABLE
OOD error：数值或 NOT_SCORED
95% CI：数值或 NOT_ESTABLISHED
Q：PASS/FAIL/INCONCLUSIVE/NOT_SCORED 分解
L/U：edge、eligible transition、scored 分解
实际 provider billing：可核验数值或 UNKNOWN
本地 cost ledger：数值及哈希
剩余 external blockers：Issue ID + 解锁条件
代码/审计文件：绝对路径
remote SHA：已核验或未核验
```

## 11. 当前最短可行路径

如果目标是尽快得到一个真实、可审计的单模型 G6/G7，而不是继续反复被同一个 blocked 状态打断，顺序只能是：

```text
离线修复 13 个 trace final-attempt 缺陷
  -> 独立只读审计通过
  -> provider billing + immutable model identity 通过
  -> 精准恢复 138 个 G7 状态
  -> 重新生成 G6/G7 derived views
  -> 独立 Q/math/statistics/LU 审计
  -> 只有全部门禁通过才计算 VLDR / Delta_VLDR / CI
```

其中任何一环失败，都应保留失败证据并停止进入下一科学阶段；这不是执行器卡死，而是 Skill 要求的 fail-closed 科学门禁。

## 12. 证据索引

- 状态台账：[issues.json](issues.json)
- 自动交接：[HANDOFF.md](HANDOFF.md)
- 未解决报告：[UNRESOLVED_REPORT.md](UNRESOLVED_REPORT.md)
- 门禁：[gates.json](gates.json)
- V3 总报告：[../audits/cycle-20261018T-g6g7-v3/FINAL_EXECUTIVE_REPORT.md](../audits/cycle-20261018T-g6g7-v3/FINAL_EXECUTIVE_REPORT.md)
- 最终门禁：[../audits/cycle-20261018T-g6g7-v3/14_FINAL_GATES.json](../audits/cycle-20261018T-g6g7-v3/14_FINAL_GATES.json)
- 门禁矩阵：[../audits/cycle-20261018T-g6g7-v3/G0_G7_GATE_MATRIX.json](../audits/cycle-20261018T-g6g7-v3/G0_G7_GATE_MATRIX.json)
- G7 状态矩阵：[../audits/cycle-20261018T-g6g7-v3/G7_STATE_ATTEMPT_MATRIX.csv](../audits/cycle-20261018T-g6g7-v3/G7_STATE_ATTEMPT_MATRIX.csv)
- G7 trace 缺陷：[../audits/cycle-20261018T-g6g7-v3/G7_TRACE_15_EXPLAINED_13_INVALID.jsonl](../audits/cycle-20261018T-g6g7-v3/G7_TRACE_15_EXPLAINED_13_INVALID.jsonl)
- G6 数学分类：[../audits/cycle-20261018T-g6g7-v3/G6_138_MATH_CLASSIFICATION.csv](../audits/cycle-20261018T-g6g7-v3/G6_138_MATH_CLASSIFICATION.csv)
- 独立复核：[../audits/cycle-20261018T-g6g7-v3/18_INDEPENDENT_READ_ONLY_REVIEW_V3.json](../audits/cycle-20261018T-g6g7-v3/18_INDEPENDENT_READ_ONLY_REVIEW_V3.json)

**交接终点：** 在上述外部证据和 trace/Q/LU 门禁解除前，任何“G6/G7 已完成”“单模型已证明 Agent 优越”“VLDR 已得到”的说法都不成立。
