# G0–G7 修复与完善交接文档

生成日期：2026-10-16（Asia/Hong_Kong）  
仓库：`E:/master_exp/nature_prj1_cal/from_llm_to_agent`  
分支：`autopilot/scientific-law-discovery`  
Cycle 52 修复基线提交：`ba7e3f8 Finalize cycle 52 handoff`；cycle 51 Q-validity semantic repair is committed as `52aee13`。后续仅为交接/状态元数据提交。
当前宿主回归：`157 passed`

## 0. 交接结论

当前代码测试通过，不等于 G0–G7 科学门禁全部通过。下一个 Agent 必须按 V2 recovery skill 选择最高优先级未解决问题，逐项修复、定向验证、独立只读复核、更新 issue ledger、写审计、提交并在有权限时推送。

当前不能宣称正式科学结果完成，不能宣称 Agent 优越性，不能把历史污染批次或重试批次静默合并进确认性分母。

核心量化状态：

| 项目 | 当前数据 | 结论 |
|---|---:|---|
| G0–G5 正式有效科学结果 | `0/720` formal task-arm-replicate 单元 | 正式 VLDR/accuracy 不可计算 |
| G5 proof graph | `1309/1309` 有 sibling；合格 family `23/24` | 结构有数据，外部数学复核未完成 |
| G5 dependency edge | `0/92` public cases 有 edge | 边级 L 不可计算 |
| G5 eligible U case | `0/92` | U transition 不可计算 |
| G6 corrected | plan/response/handoff `552/552`；2 workers | 结构完整，科学发布仍禁止 |
| G6 CF3 revision | `0/138` valid | 修订结论不可支持 |
| G7 原始批次 | completed `993/1288`；Q valid `3/1288`；路由元数据 `2960/2960` model calls 命中 | 原始批次非确认 |
| G7 corrected retry | state `1288/1288`；completed `1285/1288`；provider error `3/1288`；immutable historical Q audit `20/1288=1.553%`；cycle-51 formal Q validity `NOT_SCORED 1288/1288`；structural diagnostic `316/1288` | 316 只表示 V/L/U/final label consistency + complete Q record，不是外部数学证明；确认性诊断仍被阻断 |
| G7 corrected 分臂 score | `0/14` 可确认分臂 score | 诊断性分组结论不能确认 |
| G6/G7 外部发布门禁 | `0/1 allowed` | 当前禁止科学发布 |

## 1. 新 Agent 必须先做的启动动作

严格按 `.agents/skills/scientific-law-recovery/SKILL.md`：

```powershell
git status --porcelain=v1
git remote -v
git branch --show-current
git log -8 --oneline
E:/resources/python/python.exe scripts/recovery_state.py bootstrap
E:/resources/python/python.exe scripts/recovery_state.py next
```

然后完整阅读：

1. `docs/state/issues.json`：权威问题状态；不能以 Markdown 或聊天记录覆盖它。
2. `docs/state/UNRESOLVED_REPORT.md`：未解决、阻塞、已解决未验证的问题。
3. `docs/state/HANDOFF.md`：V2 自动生成的 canonical handoff。
4. 本文件：G0–G7 的量化修复地图。
5. `.agents/skills/scientific-law-autopilot/references/development_original.md`。
6. `.agents/skills/scientific-law-autopilot/references/supervision_original.md`。
7. `docs/audits/cycle-*/` 中 issue ledger 引用的证据。

`docs/state/gates.json` 已生成并明确记录 G0/G6/G7 BLOCKED、G1–G5 仅 engineering/smoke scope；下一个 Agent 仍不得因本地测试通过而推断科学门禁通过，应以审计证据逐项判定 `PASS / FAIL / NOT TESTED / BLOCKED`。

不要重新下载上游、重建 NewtonBench、重跑已验证的 G1–G5 policy 或重新生成已有 canonical trace，除非有新的回归证据。

## 2. 当前 issue ledger 摘要

截至当前台账：`VERIFIED=2`，`RESOLVED_UNVERIFIED=10`，`BLOCKED=2`，`OPEN=1`，`IN_PROGRESS=1`。

| 优先级 | Issue | 状态 | 当前问题 | 下一步 |
|---|---|---|---|---|
| P1 | `ISSUE-3d7a9c1e5b20` | IN_PROGRESS | G7 有 `3/1288` provider error；Q valid `20/1288`；无确认分臂 score | 诊断 failure；独立审查 trace/Q 或另行冻结 retry；不得静默合并 |
| P1 | `ISSUE-0f2cb195c681` | RESOLVED_UNVERIFIED | 原始 G7 model prompt 有 `2960/2960` 路由元数据命中；修正版 preflight 已为 `0` 命中 | 原始产物永久非确认；未来 paid run preflight 必须 `0` 命中 |
| P1 | `ISSUE-000000000003` | BLOCKED | 上游 provenance 和 GitHub delivery 外部阻断 | 恢复凭据后验证 commit/license/remote；否则保持 BLOCKED |
| P1 | `ISSUE-1f8c2b6a4d90` | BLOCKED | dependency edge `0/92`，eligible U `0/92` | 获取独立审计 replacement edge/state 数据；不得伪造 L/U |
| P1 | `ISSUE-000000000002` | RESOLVED_UNVERIFIED | 无 immutable model snapshot、外部 billing | 获取 gateway weight fingerprint 与 billing export |
| P1 | `ISSUE-000000000004` | RESOLVED_UNVERIFIED | 正式统计有效性未完成独立复核 | 复核 preregistration、oracle provenance、paired-family、统计代码 |
| P1 | `ISSUE-ff97c7c89112` | RESOLVED_UNVERIFIED | G5/G6 verifier 数学合法性未外部复核 | 只审查 23 个合格 family；永久排除 `TB-L1-010` |
| P1 | `ISSUE-ad61f025976a` | RESOLVED_UNVERIFIED | preflight 有数据，但权重/账单不能独立验证 | 保留 truthful preflight；metadata 不等于 immutable weights |
| P1 | `ISSUE-f9171bb760b1` | RESOLVED_UNVERIFIED | G8 adapter 有结构审计，外部快照/账单门禁未完成 | 本交接不重做 G8，保留 artifacts |
| P2 | `ISSUE-000000000005` | OPEN | classical baseline 只有 extension interface | G0–G7 修复期间不扩展研究范围 |
| P2 | `ISSUE-6b3a9e1d4f20` | RESOLVED_UNVERIFIED | G6 raw trace 有 noncanonical retry segments | raw 不可改；只用 canonical hashed view；硬化 resume/sequence |

已验证且不得重做：

- `ISSUE-000000000001`：evaluator numeric/OOD/AST/mechanistic 绑定和 adversarial tests 已验证。
- `ISSUE-7e3d4a91c2f0`：corrected G6 profile 已用 2 workers 执行，`552/552` 结构审计通过；历史产物保持 immutable。

## 3. G0–G7 门禁状态和修复目标

### G0：任务、真实 simulator、licence、评估边界

当前：registry `108` tasks；engineering `24/24`；formal target `720` 单元；formal provider scientific result `0/720`；`official_numeric_evaluator=false`；上游 commit 本地记录为 `912a4ba5f4356ddd06acc16e44460ca30be4abc2`，远程 provenance 未独立确认。

必须完善：

1. 验证上游 commit、许可证、真实 simulator provenance，并记录 URL/commit/hash/时间。
2. 确认官方 evaluator；若仍是 restricted evaluator，标为 `NOT TESTED/BLOCKED`，不能写 PASS。
3. 不因工程、smoke、mock 文件存在而补写 formal VLDR。

验收：simulator、licence、evaluator、provenance 都有独立证据；否则保持 `0/720` formal 结果缺失。

### G1：严格 LLM-only 非自适应

已有：12 tasks、2 runners、`24/24` records；tools `0`；frozen plan `1/1`；mid-run replanning `0`；formal provider requests `0`。

必须完善：完整 immutable plan + SHA-256；执行期间无 tool、观察反馈、重规划、hidden source/evaluator；通过 observation-swap/adversarial test。没有真实 formal result 前，scientific result 仍为 `N/A (0/720)`。

### G2：工具边界和 matched action space

已有：model-call target `2`；calculator 上限 `4` steps；允许工具 `1` 种 `calculate_expression`；formal result `0/720`。

必须完善：从代码和 trace 验证 action space；calculator 只能处理公开表达式；禁止 source/answer/evaluator/private path；逐 task 记录 tool count、result、failure、token/cost/time。越界 call 必须为 `0`。

### G3：固定反思对照

已有：corrected G6 G3 `276/552`；G7 fork plan `644/1288`；G6 structure `552/552`。

必须完善：将 protocol profile、model calls、tools、reflection passes 与 preregistration 对齐；证明 G3/G4 共享 public input、model、budget、seed、family denominator；不能把 CF accuracy 当正式 VLDR。

### G4：单 Agent 自适应反馈

已有：corrected G6 G4 `276/552`；G7 fork plan `644/1288`；实验上限 `6`；允许工具 `run_experiment`、`calculate_expression`。

必须完善：每个 action 只能依赖公开 observation；无 evaluator、hidden law、answer key、unrestricted shell/browser；记录 trajectory、observation、终止原因和资源；不能由一次 CF accuracy 直接声称 Agent superiority。

### G5：真实 simulator、mock pipeline、proof graph

已有：graph `1309/1309` 有 sibling；source-only family `24`；合格 `23/24`；排除 `TB-L1-010` `1/24`；private/answer 命中 `0/1309`；public cases `92`；edge `0/92`；eligible U `0/92`。

必须完善：

1. 对 verifier 和 23 个合格 family 做独立数学 review。
2. 获取带 source hash、family/case lineage 的独立审计 replacement dependency-edge/state-transition 数据。
3. 永久排除 `TB-L1-010`，不得合成、补边或静默换分母。
4. 若拿不到 replacement data，G5 结构结果可报告，但 L/U 必须保持 `NOT COMPUTABLE`。

### G6：完整 reproducibility、results、stats、retry

当前 corrected：23 families、92 cases、CF1–CF4、3 replicates、G3/G4、2 workers；plan/response/handoff `552/552`；model request/response `1826/1826`；tool call/result `1796/1796`；tokens `3,454,449`；trace cost `USD 6.057783`；structural review `1/1`；scientific release `0/1`；CF3 revision valid `0/138`。

必须完善：数学 review `0/1→1/1`；统计 review `0/1→1/1`；immutable model snapshot `0/1→1/1`；independent billing `0/1→1/1`；raw trace immutable、scoring 只用 canonical hash view；修复 resume/sequence 后再考虑 formal batch；CF3 `0/138` 前不能作机制证据。

### G7：冻结 preregistration、V/L/U/Q 失败定位

#### 原始批次：永久非确认

- plan `1288/1288`；completed `993/1288=77.096%`；checkpoint missing `217/1288`；provider error `78/1288`。
- completed checkpoints `153/184`；Q valid `3/1288=0.233%`。
- `cf_type` 和 `theory_family_id` 命中 `2960/2960` model calls。

原始 plan/states/Q/trace 必须 immutable、非确认，不能靠改解释恢复。

#### protocol-corrected retry：仍未达到确认使用条件

- state `1288/1288=100%`；completed `1285/1288=99.767%`；provider error `3/1288=0.233%`。
- checkpoints `184/184=100%`；Q rows `1288/1288`；immutable historical Q audit `20/1288=1.553%`；cycle-51 formal Q validity `NOT_SCORED 1288/1288`；schema-repaired derived label-consistency audit `316/1288`；Q record incomplete `7`。
- corrected route metadata `0/3774`；private-prompt hits `0/3774`；format retry `302/302`。
- corrected confirmatory per-arm score `0/14`。

必须完善：

1. 诊断 3 个 provider error 的精确原因和可复现性；failure rows 不得补成成功。
2. 对 Q invalid 做独立 trace/Q review，区分 schema、provider output、parser、state merge、audit 错误。
3. paid retry 前冻结新 plan/hash、预算、workers、retry policy、format retry 上限、stop rules；确认 key、model identity、billing hard cap。
4. 新 retry 独立存储，不能与原始或旧 retry pooled；只能按预声明规则生成新的 canonical release。
5. 生成独立分臂 score：all-planned accuracy、valid-answer accuracy、W→C、C→W、first error、D0→D1、D1→D2、D2→D3、U_ONLY→D0。
6. L/U replacement graph 未通过审计前，L/U 必须报告 `0/92` 并标 `NOT COMPUTABLE`。

## 4. 严格执行顺序

1. `bootstrap → next`，确认 ledger 与本文件一致。
2. 先处理 P1 `ISSUE-3d7a9c1e5b20`：G7 provider/Q diagnosis；key、snapshot、billing、网络不可用时记录 blocker，不伪造 PASS。
3. 并行做只读的 G7 preflight/prompt 审查和 G5 graph/L/U 审查；不改原始 artifacts。
4. 独立完成数学、统计、模型、billing、provenance 复核；一项 review 不得覆盖其他项。
5. 只有新 retry 的 plan、预算、provider 和 preflight 全部冻结后，才可执行付费批次；不临时放大 workers/预算。
6. 每次修复：定向测试 → adversarial/read-only review → `E:/resources/python/python.exe -m pytest -q` → audit JSON → 更新 `issues.json`/`UNRESOLVED_REPORT.md`/`HANDOFF.md` → commit → 在获授权且网络可用时 push。
7. push 后必须用 `git ls-remote origin refs/heads/autopilot/scientific-law-discovery` 验证；失败就明确记录，不能声称已推送。
8. G0–G7 hard gate 关闭前，不开始新的 G8 scientific claim，也不把量化报告当作实验完成证明。

## 5. 绝对禁止事项

- 不覆盖、删除或修改原始 G6/G7 traces、plans、states、Q audits、retry manifests。
- 不合并原始 G7 `2960/2960` 路由泄漏批次；不静默 pooled retry1/retry2/retry3/corrected retry。
- 不把 historical `Q valid=20/1288` 或 derived `316/1288` 解释成 confirmed scientific cases；derived audit 明确不是外部数学证明。
- 不把 `0/92` edges 或 `0/92` eligible U 补成可用 L/U 数据。
- 不把 mock、engineering、smoke 或 restricted evaluator 当正式 VLDR。
- 不把 provider metadata 当 immutable weights；不把 local trace cost 当外部 billing。
- 不因 `pytest` 通过就将 G0–G7 标为 PASS；失败任务不能删除、补零或移出分母。
- 不提交 credential、private raw result、API key、账单隐私字段；不 force-push、不自动合并 main。

## 6. 主要证据入口

| 用途 | 文件/目录 |
|---|---|
| 权威 issue ledger | `docs/state/issues.json` |
| 未解决报告 | `docs/state/UNRESOLVED_REPORT.md` |
| canonical handoff | `docs/state/HANDOFF.md` |
| G0–G7 量化报告 | `docs/reports/G0_G7_DATA_LEDGER_CN_20261015.md` |
| 最新完整性审计 | `docs/audits/cycle-20261015T083400Z-28/g0_g8_integrity.json` |
| G7 failure taxonomy | `docs/audits/cycle-20261015T081700Z-27/g7_failure_taxonomy.json` |
| G7 corrected artifacts | `results/g7_failure_localization/formal-20261015T060000Z-protocol-corrected-16workers/` |
| G6 corrected artifacts | `results/g6_counterfactual/protocol-g3tools-v2-20261014T030000Z/` |
| experiment policy | `docs/experiment_groups.md`、`configs/experiment_groups.json` |
| V1 scientific requirements | `.agents/skills/scientific-law-autopilot/references/` |

## Cycle 52 state-workflow repair (2026-10-16T07:08Z)

- Repaired `scripts/recovery_state.py`: `start`, `block`, and `claim-fixed` now forward `--evidence` and `--command-run`; explicit evidence updates both the current issue record and its append-only history entry.
- Added `tests/test_recovery_state.py::test_cli_status_transition_persists_evidence`.
- Focused regression: `44 passed`; full host suite: `157 passed`; `git diff --check`: PASS.
- Independent AST and temporary-ledger CLI review: PASS. No provider call, paid run, or retry was made.
- The design requirement remains enforced: without an external independent Q verifier, formal `Q_validity` is `NOT_SCORED` for `1288/1288`; the `316/1288` label-consistency count is structural only. G7 retains `3` provider errors and `368` U-ineligible rows.
- Gate state remains truthful: G0, G6, and G7 are `BLOCKED`; G1-G5 are engineering/smoke scope only; `scientific_release_allowed=false`.
- Cycle audit: `docs/audits/cycle-20261016T070818Z-52/audit.json` and `recovery_state_cli_evidence_review.json`.
- Next priority remains `ISSUE-3d7a9c1e5b20`: independently diagnose provider/Q failures and obtain eligible dependency/state data only through an explicitly authorized, separately frozen run. Do not pool retries, infer L/U from `0/92` edges, or claim scientific completion.
- Delivery: local commits are `d1ad59b` and `8a2c552`; `git push` and `git ls-remote` both failed through the configured proxy, so the remote branch was not verified or claimed updated. This is recorded under `ISSUE-000000000003`.

## Cycle 53 completion audit (2026-10-16T07:14Z)

- Read all three files in `D:/硕士/prj1_ai_cal/writing/实验设计`; the design-to-gate probe found the required G0-G7, `Q_validity`, `verify_Q`, and `independent_verifier` requirements.
- G0/G7/Q focused regression: `36 passed in 2.56s`. The formal contract remains fail-closed: `Q_validity=NOT_SCORED` for `1288/1288` without an external verifier.
- No local-only scientific repair remains for the highest-priority G7 issue. `ISSUE-3d7a9c1e5b20` is now `BLOCKED` with exact external unlock conditions: authorized provider access, independent Q standard/review, and independently audited dependency/state data.
- Existing denominators remain unchanged: `3` provider errors, `0/92` dependency edges, and `0/92` eligible U cases. No provider, paid run, retry, or scientific claim was made.
- Gate conclusion is unchanged: G0/G6/G7 `BLOCKED`; G1-G5 engineering/smoke scope only; `scientific_release_allowed=false`.
- Audit: `docs/audits/cycle-20261016T071456Z-53/audit.json`.

## Cycle 54 paid-provider gate audit (2026-10-16T07:16Z)

- Reviewed `validate_paid_evidence()` and the runner order: missing/invalid snapshot or billing evidence fails before key reading and provider construction.
- `tests/test_g7_protocol.py`: `29 passed in 2.22s`.
- Structurally valid local manifests remain `PRESENT_UNVERIFIED_EXTERNAL`; no explicit paid authorization, positive hard USD ceiling, immutable model evidence, independent billing, or isolation review exists.
- `ISSUE-000000000002` is now `BLOCKED`; its exact unlock conditions are recorded in `docs/state/issues.json`. No provider call, paid run, or retry was made.
- Audit: `docs/audits/cycle-20261016T071631Z-54/audit.json`.
- Cycle 54 delivery was attempted after `e19717d`; both `git push` and `git ls-remote` failed through the configured proxy and are recorded under `ISSUE-000000000003`. The remote branch remains unverified.

## Cycle 55 statistical input-contract repair (2026-10-16T07:21Z)

- Repaired `scripts/analyze_g6_clustered.py`: duplicate plan run IDs, duplicate family/CF/replicate/arm keys, duplicate private case IDs, duplicate response IDs, missing responses, and unexpected responses now fail closed instead of silently changing the statistical denominator.
- Added `tests/test_analyze_g6_clustered.py`; focused tests: `13 passed`; full host suite: `162 passed`.
- Real verified23 read-only probe accepted `552` plan rows, `23` families, and `69` matched runs per CF. Its output remains `ANALYZED_PENDING_INDEPENDENT_STATISTICAL_REVIEW`; this is not a scientific result.
- `ISSUE-000000000004` is now `BLOCKED` pending independent review of preregistration, oracle provenance, paired-family construction, failure denominators, and statistical code.
- No provider call, paid run, retry, confirmatory inference, or scientific superiority claim was made.
- Audit: `docs/audits/cycle-20261016T072158Z-55/audit.json` and `statistical_input_contract_review.json`.
- Cycle 55 delivery: local repair commit `f79bfc5`; push and `git ls-remote` both failed through the configured proxy. Remote branch remains unverified under `ISSUE-000000000003`.

## Cycle 56 G6/G7 collision-guard repair (2026-10-16T07:25Z)

- Repaired `scripts/audit_g6_counterfactual.py` and `scripts/build_g6_g7_handoff.py` so duplicate plan/response/oracle IDs, duplicate arm records, missing oracle rows, and unexpected responses fail closed.
- Added `tests/test_g6_input_collision_guards.py`; focused collision/statistics tests: `16 passed`; full host suite: `165 passed`.
- Real verified23 probes: `552` plan rows, `92` private rows, `552` responses, `552` handoff rows, and `552` unique handoff run IDs; no collision failures.
- `ISSUE-000000000004` remains `BLOCKED` pending independent statistical/mathematical review. Input integrity is not inferential validity and is not a scientific result.
- No provider call, paid run, retry, confirmatory inference, or superiority claim was made.
- Audit: `docs/audits/cycle-20261016T072546Z-56/audit.json` and `g6_g7_collision_review.json`.
- Cycle 56 delivery: local repair commit `b25b76d`; push and `git ls-remote` failed through the configured proxy. Remote branch remains unverified under `ISSUE-000000000003`.

## Cycle 57 G5/G6 public-task input-contract repair (2026-10-16T07:32Z)

- Repaired `scripts/prepare_g6_counterfactual.py` and `scripts/verify_g5_g6_inputs.py`: duplicate or malformed public task rows and duplicate G6 source-index task IDs now fail closed before indexing or report creation; no historical artifacts were modified.
- Reproduction before repair: duplicate `TC-L1-001` public rows silently retained the last row (`k=999` replaced `k=1`). After repair, preparation raises and verifier exits before writing output.
- Added `tests/test_g5_g6_input_contract.py`; focused input/collision/statistics tests: `21 passed`; full host suite: `170 passed`.
- Real verified23 read-only verifier probe remains `24` families: `23 VERIFIED_INDEPENDENT_B`, `TB-L1-010 EXCLUDED_INVALID_SOURCE`; `private_inputs_read=false`, `answer_key_read=false`.
- `ISSUE-ff97c7c89112` remains `RESOLVED_UNVERIFIED`: local input integrity is repaired, but independent external mathematical review of the verifier is still absent. `ISSUE-000000000004` remains `BLOCKED`; no confirmatory inference is allowed.
- No provider call, paid run, retry, confirmatory inference, or superiority/scientific claim was made. G0/G6/G7 remain blocked and `scientific_release_allowed=false`.
- Audit: `docs/audits/cycle-20261016T073248Z-57/audit.json` and `g5_g6_input_contract_review.json`.
- Cycle 57 delivery: local repair commit `e1fdf16`; `git push origin autopilot/scientific-law-discovery` and `git ls-remote origin refs/heads/autopilot/scientific-law-discovery` both failed because the configured proxy could not connect to GitHub port 443. Remote update is not claimed and remains unverified under `ISSUE-000000000003`.

## Cycle 58 G6 frozen statistical-layout repair (2026-10-16T07:39Z)

- Repaired `scripts/analyze_g6_clustered.py`: the formal CLI now requires the frozen verified23 layout of 23 families × CF1–CF4 × replicates 0–2 × G3/G4, exactly 552 plan rows and every expected arm key; unexpected private cases also fail closed.
- Reproduction before repair: a one-family CF1-only input with matched responses was accepted by the validator and could omit CF2–CF4 from a formal analysis. After repair, incomplete layout fails before output creation.
- Added formal-layout adversarial coverage; focused tests: `16 passed`; full host suite: `173 passed`.
- Real verified23 read-only probe remains structurally complete: `552` plan rows, `23` families, CF1–CF4 and `ALL_CF`; output status is `ANALYZED_PENDING_INDEPENDENT_STATISTICAL_REVIEW` and is not a scientific result.
- `ISSUE-000000000004` remains `BLOCKED`: independent statistical/mathematical review is absent. G0/G6/G7 remain blocked and `scientific_release_allowed=false`.
- No provider call, paid run, retry, confirmatory inference, or superiority/scientific claim was made.
- Audit: `docs/audits/cycle-20261016T073921Z-58/audit.json` and `statistical_layout_review.json`.
- Cycle 58 delivery: local repair commit `b60063a`; `git push origin autopilot/scientific-law-discovery` and `git ls-remote origin refs/heads/autopilot/scientific-law-discovery` both failed because the configured proxy could not connect to GitHub port 443. Remote update is not claimed and remains unverified under `ISSUE-000000000003`.

## Cycle 59 G7 corrected-metrics identity/denominator repair (2026-10-16T07:43Z)

- Repaired `scripts/audit_g7_corrected_metrics.py`: duplicate plan/state/Q/oracle identifiers, duplicate checkpoint-arm keys, missing/extra state or Q run IDs, invalid oracle decisions, and oracle/plan case mismatches now fail closed.
- Reproduction before repair: duplicate state/Q rows were silently overwritten; an extra state ID could pass the old length-only guard. After repair, identity collisions and non-bijective inputs fail before report construction.
- Added adversarial coverage; focused G7 tests: `20 passed`; full host suite: `176 passed`.
- Real corrected G7 probe remains truthful: `1288/1288/1288` plan/state/Q rows, `92` oracle rows, `3` terminal failures, `1268` invalid Q rows, `368` ineligible-U rows, and `confirmatory_reuse_allowed=false`.
- `ISSUE-3d7a9c1e5b20` and `ISSUE-000000000004` remain BLOCKED: provider/Q and independent statistical/mathematical evidence are still absent. No V/L/U/Q or scientific superiority claim is allowed.
- No provider call, paid run, retry, confirmatory inference, or superiority/scientific claim was made.
- Audit: `docs/audits/cycle-20261016T074311Z-59/audit.json` and `g7_metrics_input_review.json`.
- Cycle 59 delivery: local repair commit `b65433a`; `git push origin autopilot/scientific-law-discovery` and `git ls-remote origin refs/heads/autopilot/scientific-law-discovery` both failed because the configured proxy could not connect to GitHub port 443. Remote update is not claimed and remains unverified under `ISSUE-000000000003`.

## Cycle 60 G7-to-G8 checkpoint identity repair (2026-10-16T07:45Z)

- Repaired `scripts/review_g7_g8_handoff.py`: duplicate public case IDs, duplicate checkpoint `(case_id, group_id)` pairs, duplicate checkpoint IDs, and malformed identifiers now fail closed before deriving G8 checkpoints.
- Reproduction before repair: duplicate checkpoint rows collapsed in the missing-pair set and could still be emitted while the audit remained `REAL_TRACE_AUDITED`.
- Added `tests/test_g7_g8_handoff_contract.py`; focused tests: `36 passed`; full host suite: `179 passed`.
- Real source-only audit remains incomplete but truthful: `92` public cases, `184` checkpoints, `153` completed, `31` provider_error, `75` completed CF1/CF2 rows, and `17` missing CF1/CF2 pairs; no private oracle or answer key loaded.
- `ISSUE-1f8c2b6a4d90` and `ISSUE-3d7a9c1e5b20` remain BLOCKED. No dependency-edge, Q, L/U, causal, or scientific superiority claim is allowed.
- No provider call, paid run, retry, confirmatory inference, or superiority/scientific claim was made.
- Audit: `docs/audits/cycle-20261016T074534Z-60/audit.json` and `g7_g8_handoff_identity_review.json`.
- Cycle 60 delivery: local repair commit `67f113d`; `git push origin autopilot/scientific-law-discovery` and `git ls-remote origin refs/heads/autopilot/scientific-law-discovery` both failed because the configured proxy could not connect to GitHub port 443. Remote update is not claimed and remains unverified under `ISSUE-000000000003`.

## Cycle 64 ordinary-result privacy independent verification (2026-10-16T08:06Z)

- Independently reviewed `ResultRecorder`, `TraceRecorder`, and `law_recovery.py`; focused privacy/observability/evaluator tests passed `14/14`, and a temporary nested/list mixed-case probe confirmed hidden evaluator values do not enter ordinary result artifacts.
- `ISSUE-ab0746b86bf9` is now `VERIFIED`. This is only a local artifact-privacy verification; it does not change G0/G6/G7 or permit scientific release.
- Local commits: `64c36d2` and delivery-state record `3dc761c`. Push and `git ls-remote` both failed through the configured proxy; remote update remains unverified.

## Cycle 65 initial-observation parity repair and independent verification (2026-10-16T08:11Z)

- Repaired `src/scientific_discovery/runners/llm_only.py` so the frozen-plan arm persists the same normalized public `initial_observations` metadata field already used by the Agent arm; added a regression assertion.
- Focused tests passed `10/10`; full host suite passed `192/192`; an independent paired probe confirmed identical model-visible initial observation content and metadata in both arms.
- `ISSUE-0786397621a0` is now `VERIFIED`. No provider call, paid run, historical artifact edit, or scientific truth decision was made.
- Local commits: `d28b9c6` and delivery-state record `9384a9a`. Push and `git ls-remote` both failed through the configured proxy; remote update remains unverified.
- Current state: `12` open/blocked/unverified issues, `4` verified issues; G0/G6/G7 remain `BLOCKED`, G1–G5 remain engineering/smoke scope, and `scientific_release_allowed=false`.

## Cycle 66 G6 resume/sequence fail-closed repair (2026-10-16T08:18Z)

- Repaired `scripts/run_g6_counterfactual.py::existing_event_seq`: malformed JSONL, non-object rows, invalid sequence types, gaps, duplicates, and non-contiguous prefixes now raise before any append; the raw trace is never rewritten.
- Added `tests/test_g6_resume_sequence.py`; focused G6/G7 tests passed `56/56`, full host suite passed `198/198`, and an independent temporary probe confirmed contiguous input is accepted while gap/malformed inputs fail closed.
- `ISSUE-6b3a9e1d4f20` is now `VERIFIED` for the local resume/sequence remediation. Historical noncanonical raw segments remain immutable and non-confirmatory; canonical derived views remain the audit boundary.
- No provider call, paid run, retry, confirmatory inference, or scientific truth decision was made.
- Local commits: `6a7feb4` and delivery-state record `a5c9f1c`. Push and `git ls-remote` both failed through the configured proxy; remote update remains unverified.
- Current state: `11` open/blocked/unverified issues, `5` verified issues; G0/G6/G7 remain `BLOCKED`, G1–G5 remain engineering/smoke scope, and `scientific_release_allowed=false`.

## Cycle 67 stale workflow blocker independent verification (2026-10-16T08:22Z)

- Independently reviewed the historical malformed/stale nested-agent output in cycle 1 and the subsequent valid cycle-33 audit; the original failure evidence remains immutable, while the later audit exited successfully and current G7 protocol/trace/taxonomy/terminal-retry tests pass `54/54`.
- `ISSUE-28ed827e40a9` is now `VERIFIED` as a transient workflow/test blocker resolved by later valid audit evidence. This does not erase historical provider failures or lift any scientific gate.
- No source, provider artifact, paid run, or scientific result was changed. Local commits: `7589a9e` and delivery-state record `2367fca`. Push and `git ls-remote` both failed through the configured proxy; remote update remains unverified.
- Current state: `10` open/blocked/unverified issues, `6` verified issues; G0/G6/G7 remain `BLOCKED`, G1–G5 remain engineering/smoke scope, and `scientific_release_allowed=false`.

## Cycle 68 G7 forward prompt-isolation repair (2026-10-16T08:34Z)

- Compared the implementation against all three user-specified design documents under `D:/硕士/prj1_ai_cal/writing/实验设计`. The review retained the design requirements that private whole-proof/oracle data cannot reach the model, D0–D3 and ONLY arms are information interventions, U-ineligible rows remain in the denominator, Q requires an independent verifier, and historical contaminated traces cannot be retroactively repaired.
- Repaired `scripts/run_g7_failure_localization.py`: V/L/U labels now have a strict nested public shape; `verifier_ref`, eligibility, and ineligibility-reason metadata are forbidden model-visible keys; `protocol_preflight` now scans the exact constructed diagnostic payload as well as public case prompts; explicit `arm_eligible_for_diagnostic=false` U rows are retained without producing a false ineligible-arm error.
- Added `tests/test_g7_label_contract.py` coverage for nested private-label rejection, extra-field rejection, strict acceptance, private diagnostic-payload scanning, and explicit ineligible-U retention.
- Focused G7 regression: `59 passed`; full host suite: `204 passed`; `git diff --check`: PASS. Fresh read-only preflight of the protocol-corrected input passes with `92` public cases, `92` labels, `1288` plan rows, `184` checkpoints, zero routing/private hits, `provider_calls_made=false`, and no scientific truth decision.
- Independent historical trace review found `3252` MODEL_REQUEST events in the immutable corrected trace, `0` routing hits, but `4222` `verifier_ref` hits. This historical corrected trace remains permanently non-confirmatory; no raw result, plan, label, or trace was modified. The prior original routing-contaminated batch also remains non-confirmatory.
- `ISSUE-0f2cb195c681` is now `VERIFIED` only for the forward local isolation/preflight remediation. This does not verify historical outputs, Q validity, dependency/L/U validity, or scientific release. `ISSUE-000000000002`, `ISSUE-000000000003`, `ISSUE-000000000004`, `ISSUE-1f8c2b6a4d90`, `ISSUE-3d7a9c1e5b20`, `ISSUE-ff97c7c89112`, `ISSUE-ad61f025976a`, and `ISSUE-f9171bb760b1` remain externally or mathematically unresolved; P2 classical baseline remains out of scope.
- Audit files: `docs/audits/cycle-20261016T083448Z-68/audit.json` and `g7_prompt_isolation_review.json`.
- Local repair commit: `1829293`. `git push origin autopilot/scientific-law-discovery` and `git ls-remote origin refs/heads/autopilot/scientific-law-discovery` both failed through the configured proxy with exit `128`; remote delivery is not claimed. This is recorded under `ISSUE-000000000003`.
- Gate conclusion remains truthful: G0/G6/G7 `BLOCKED`; G1–G5 are engineering/smoke scope only; `scientific_release_allowed=false`; no provider, paid experiment, retry, confirmatory inference, or scientific claim was made.

## Cycle 69 G7 strict stage-contract repair (2026-10-16T08:41Z)

- Independently reproduced a fail-open parser defect: before this cycle `normalize_stages()` accepted extra/private fields in V/L/U/Q, object-valued L nodes, non-string edge endpoints, and malformed U changes. A read-only scan of the immutable protocol-corrected states found 7 completed rows with Q missing `reason`, 3 V rows with `verifier_ref`, 2 L rows with `verifier_ref`, 8 U rows with eligibility/provenance fields, and 1 malformed U change. Historical raw states remain unchanged and non-confirmatory.
- Repaired `scripts/run_g7_failure_localization.py` so future model responses require exact V/L/U/Q nested schemas; malformed output receives only the bounded format retry and then remains a failure. Extended `scripts/audit_g7_failure_taxonomy.py` to report `verifier_ref`, `eligible_u`, and `u_ineligibility_reason` request hits.
- Added adversarial tests for all malformed/private stage shapes and forensic detection. Focused G7 regression: `65 passed`; full host suite: `210 passed`; `git diff --check`: PASS. A read-only provider-loop probe produced one format-retry event and rejected a repeated malformed response after two retained model requests.
- Repaired forensic scan of the historical protocol-corrected trace reports `1288` planned, `1285` completed, `3` provider_error, `20` historical Q-valid rows, `2771` `verifier_ref` payload-key hits, zero routing hits, and `302` format-retry model requests. These are execution facts only; no Q/scientific claim is made.
- `ISSUE-4c7e2a91d6f0` is `VERIFIED` for the forward parser/audit remediation only. G0/G6/G7 remain blocked; paid provider authorization, immutable model/billing evidence, upstream provenance, independent Q/statistical/mathematical/dependency review, and historical trace contamination remain unresolved.
- Audit files: `docs/audits/cycle-20261016T084135Z-69/audit.json`, `g7_stage_contract_finding.json`, and `g7_stage_contract_review.json`.
- Local commits: `32af428` (repair) and `7365e22` (audit/state). Push and `ls-remote` both failed through the configured proxy with exit `128`; remote delivery is not claimed. This remains recorded under `ISSUE-000000000003`.
- Gate conclusion remains truthful: G0/G6/G7 `BLOCKED`; G1–G5 engineering/smoke scope only; `scientific_release_allowed=false`; no provider or paid experiment was started.

## Cycle 70 G7 arm-specific top-level output repair (2026-10-16T08:45Z)

- Independently reproduced a second fail-open path in the same G7 output contract: before this cycle `public_tool_loop(..., checkpoint=true)` accepted a checkpoint response containing diagnostic `stages`. The immutable corrected checkpoint artifact has `128/184` rows with stages even though checkpoint messages are specified to contain only decision, affected_claim_ids, revised_claim, and supporting_evidence.
- Repaired `scripts/run_g7_failure_localization.py` with exact checkpoint/diagnostic top-level key contracts and `affected_claim_ids` validation. Checkpoint responses carrying stages now receive the bounded format retry and cannot enter the diagnostic context; diagnostic responses must contain the stages object before strict V/L/U/Q validation.
- Added direct contract and checkpoint retry tests. Focused G7 regression: `67 passed`; full host suite: `212 passed`; `git diff --check`: PASS. Independent post-repair probe confirms one format retry followed by acceptance of a valid four-field checkpoint.
- `ISSUE-4c7e2a91d6f0` remains `VERIFIED` only for the forward parser remediation. The immutable `128/184` historical checkpoint-shape discrepancy remains non-confirmatory; no historical trace or result was modified.
- Audit files: `docs/audits/cycle-20261016T084506Z-70/audit.json`, `g7_top_level_contract_finding.json`, and `g7_top_level_contract_review.json`.
- Local commits: `2f69df9` (repair) and `68b65b4` (audit/state). Push and `ls-remote` both failed through the configured proxy with exit `128`; remote delivery is not claimed. This remains recorded under `ISSUE-000000000003`.
- Gate conclusion remains truthful: G0/G6/G7 `BLOCKED`; G1–G5 engineering/smoke scope only; `scientific_release_allowed=false`; no provider, paid experiment, confirmatory inference, or scientific claim was made.

## Cycle 71 G7 output field-type repair (2026-10-16T08:47Z)

- Compared the implementation with the design-aligned G7 report (`docs/reports/G0_G7_COMPLETE_DATA_CN_20261015.md:670-671`) and found the top-level contract still accepted non-string/empty `supporting_evidence`; the immutable corrected checkpoint artifact contains `22/184` such rows. Historical artifacts remain unchanged and non-confirmatory.
- Repaired `scripts/run_g7_failure_localization.py`: `revised_claim` must be string/null and `supporting_evidence` must be a nonempty string for both checkpoint and diagnostic outputs. Added adversarial type assertions.
- Focused G7 regression: `67 passed`; full host suite: `212 passed`; `git diff --check`: PASS. Independent probes reject a revised-claim object and supporting-evidence list before provider output is accepted.
- `ISSUE-4c7e2a91d6f0` remains `VERIFIED` only for the forward field-type remediation. The historical `22/184` malformed rows remain non-confirmatory; no result, trace, or checkpoint file was modified.
- Audit files: `docs/audits/cycle-20261016T084740Z-71/audit.json`, `g7_field_type_finding.json`, and `g7_field_type_review.json`.
- Local commits: `4542ed3` (repair) and `423724c` (audit/state). Push and `ls-remote` both failed through the configured proxy with exit `128`; remote delivery is not claimed. This remains recorded under `ISSUE-000000000003`.
- Gate conclusion remains truthful: G0/G6/G7 `BLOCKED`; G1–G5 engineering/smoke scope only; `scientific_release_allowed=false`; no provider, paid experiment, confirmatory inference, or scientific claim was made.

## Cycle 72 G6 statistical pair-lineage repair (2026-10-16T08:52Z)

- Compared the G6 statistical input contract with the user design documents under `D:/硕士/prj1_ai_cal/writing/实验设计`, especially the requirement that `paired_set_id` binds variants of one base task, G3/G4 are compared on the same task, and `theory_family_id` is the primary cluster rather than treating variants or replicates as independent laws.
- Independently reproduced a fail-open in `scripts/analyze_g6_clustered.py`: before repair, G3 `case_id=c3, paired_set_id=p3` and G4 `case_id=c4, paired_set_id=p4` under the same family/CF/replicate were accepted because only `(theory_family_id, cf_type, replicate)` was used as the pair key.
- Repaired `validate_statistical_inputs` to require nonempty `case_id` and `paired_set_id` on every plan row and reject any G3/G4 pair with mismatched task lineage before constructing statistical summaries. Historical G6 artifacts were not modified.
- Added adversarial tests for mismatched `case_id` and mismatched `paired_set_id`. Focused G6 input tests: `13 passed`; full host suite: `214 passed`; `git diff --check`: PASS.
- Read-only validation of the immutable corrected G6 inputs passes: `552` plan rows, `552` responses, `92` private rows, `276` complete G3/G4 pairs, replicate values `[0,1,2]`, zero lineage mismatches, and zero missing pair arms.
- `ISSUE-9e31a7c4b2d8` is `VERIFIED` for this local statistical-input guard only. `ISSUE-000000000004` remains `BLOCKED`: independent formal statistical/mathematical review is still absent, so no confirmatory inference or scientific release is allowed.
- Audit files: `docs/audits/cycle-20261016T085230Z-72/audit.json`, `g6_pair_lineage_finding.json`, and `g6_pair_lineage_review.json`.
- Current ledger after this cycle: `9` open/blocked/unverified issues and `9` verified issues. G0/G6/G7 remain `BLOCKED`; G1–G5 remain engineering/smoke scope; `scientific_release_allowed=false`.
- No provider call, paid experiment, retry, historical result edit, confirmatory inference, or scientific claim was made. GitHub delivery remains externally blocked and must not be claimed until push plus `git ls-remote` succeeds.

## Cycle 73 G6 response-status and failure-denominator repair (2026-10-16T08:56Z)

- Compared the response-analysis path with the user design documents under `D:/硕士/prj1_ai_cal/writing/实验设计` and the data report: response statuses must distinguish completed and technical failures, and failures must remain in the all-planned denominator.
- Independently reproduced a fail-open in `scripts/analyze_g6_clustered.py`: a synthetic `provider_error` row carrying the expected decision was accepted by the old decision-only predicate and would be counted as correct; a missing status was also accepted.
- Repaired the validator with the registered G6 statuses (`completed`, `timeout`, `provider_error`, `policy_violation`, `invalid`) and decision set. Completed rows require a known decision; only `status=completed` plus an oracle match is correct. Non-completed rows remain failures in the denominator.
- Added adversarial tests for missing status, unknown completed decision, and provider-error-with-matching-decision. Focused G6 input tests: `16 passed`; full host suite: `217 passed`; `git diff --check`: PASS.
- Read-only validation of the immutable corrected G6 inputs passes: `552` plan rows, `552` responses, all `552` response statuses are `completed`, and the formal input contract remains valid.
- `ISSUE-6a4e8b2c1d90` is `VERIFIED` for this local response-status guard only. `ISSUE-000000000004` remains `BLOCKED`: independent formal statistical/mathematical review is still absent, so no confirmatory inference or scientific release is allowed.
- Audit files: `docs/audits/cycle-20261016T085638Z-73/audit.json`, `g6_response_status_finding.json`, and `g6_response_status_review.json`.
- Current ledger after this cycle: `9` open/blocked/unverified issues and `10` verified issues. G0/G6/G7 remain `BLOCKED`; G1–G5 remain engineering/smoke scope; `scientific_release_allowed=false`.
- No provider call, paid experiment, retry, historical result edit, confirmatory inference, or scientific claim was made. GitHub delivery remains externally blocked and must not be claimed until push plus `git ls-remote` succeeds.

## Cycle 74 G6 typed-schema and oracle-CF alignment repair (2026-10-16T08:59Z)

- Compared the G6 input contract with the user design documents under `D:/硕士/prj1_ai_cal/writing/实验设计` and the data report: frozen plan identity fields are typed, four CF variants and their private oracle rows must remain aligned, and replicates are repeated observations within family clusters.
- Independently reproduced two fail-open cases: the old `int(row["replicate"])` coercion accepted string/boolean replicate values, and a private oracle with `cf_type=CF2` was accepted for a plan case in `CF1`.
- Repaired `validate_statistical_inputs` to require nonempty typed plan identifiers, integer non-boolean replicate values, same-case CF consistency, valid private oracle CF/decision fields, and private-oracle CF equality with the plan.
- Added adversarial tests for string/boolean replicates and private CF mismatch. Focused G6 input tests: `19 passed`; full host suite: `220 passed`; `git diff --check`: PASS.
- Read-only validation of the immutable corrected G6 inputs passes: `552` plan rows, `92` private rows, `552` responses, replicate values `[0,1,2]`, all response statuses `completed`, and no schema/alignment errors.
- `ISSUE-0b7d3f91a2c4` is `VERIFIED` for this local schema/alignment guard only. `ISSUE-000000000004` remains `BLOCKED`: independent formal statistical/mathematical review is still absent, so no confirmatory inference or scientific release is allowed.
- Audit files: `docs/audits/cycle-20261016T085921Z-74/audit.json`, `g6_schema_alignment_finding.json`, and `g6_schema_alignment_review.json`.
- Current ledger after this cycle: `10` open/blocked/unverified issues and `10` verified issues. G0/G6/G7 remain `BLOCKED`; G1–G5 remain engineering/smoke scope; `scientific_release_allowed=false`.
- No provider call, paid experiment, retry, historical result edit, confirmatory inference, or scientific claim was made. GitHub delivery remains externally blocked and must not be claimed until push plus `git ls-remote` succeeds.

## Cycle 75 G6 cross-repeat/cross-CF lineage repair (2026-10-16T09:02Z)

- Compared the G6 pairing contract with the user design documents under `D:/硕士/prj1_ai_cal/writing/实验设计`: one `paired_set_id` binds the four CF variants of one base task, and repeats are repeated observations of the same task within a theory-family cluster.
- Independently reproduced the remaining fail-open: the prior validator checked only each local family×CF×replicate G3/G4 pair, so different `case_id` values could be used across repeats and different `paired_set_id` values across CF variants.
- Repaired `validate_statistical_inputs` to require one `paired_set_id` per `theory_family_id` and one stable `(case_id, paired_set_id)` lineage per family×CF across all arms and repeats. Historical G6 artifacts were not modified.
- Added adversarial cross-repeat and cross-CF tests. Focused G6 input tests: `21 passed`; full host suite: `222 passed`; `git diff --check`: PASS.
- Read-only validation of the immutable corrected G6 inputs passes: `552` plan rows, `92` private rows, `552` responses, `276` complete pairs, zero family-level paired-set violations, and zero family×CF task-lineage violations.
- `ISSUE-8c2f6d1a4b70` is `VERIFIED` for this local lineage guard only. `ISSUE-000000000004` remains `BLOCKED`: independent formal statistical/mathematical review is still absent, so no confirmatory inference or scientific release is allowed.
- Audit files: `docs/audits/cycle-20261016T090232Z-75/audit.json`, `g6_cross_repeat_lineage_finding.json`, and `g6_cross_repeat_lineage_review.json`.
- Current ledger after this cycle: `9` open/blocked/unverified issues and `12` verified issues. G0/G6/G7 remain `BLOCKED`; G1–G5 remain engineering/smoke scope; `scientific_release_allowed=false`.
- No provider call, paid experiment, retry, historical result edit, confirmatory inference, or scientific claim was made. GitHub delivery remains externally blocked and must not be claimed until push plus `git ls-remote` succeeds.

## Cycle 76 G6 frozen-plan identity repair (2026-10-16T09:07Z)

- Compared the statistical analyzer with the design-aligned G6 plan schema: formal rows must carry `experiment_id`, `arm_id`, `group_id`, `replicate`, and `split`; G3/G4 arm identity must remain explicit.
- Independently reproduced a fail-open: before repair, changing `experiment_id`, `arm_id`, or `split` while preserving the family/CF/replicate/group keys did not prevent statistical aggregation.
- Repaired `validate_statistical_inputs` to require `experiment_id=g6_counterfactual`, `G3→G6_A_G3_GIVEN`, `G4→G6_B_G4_GIVEN`, and `split=final_test` on every plan row.
- Added adversarial identity tests. Focused G6 tests: `24 passed`; full host suite: `225 passed`; `git diff --check`: PASS.
- Temporary-output CLI execution on the immutable corrected v2 inputs exits 0 with `552` plan rows and the explicit status `ANALYZED_PENDING_INDEPENDENT_STATISTICAL_REVIEW`; output was removed after verification.
- Read-only plan scan confirms all `552` rows use the required experiment, arm, and split identities. `ISSUE-5f7a1c9d3e20` is `VERIFIED` for this local guard only; `ISSUE-000000000004` remains `BLOCKED` and no confirmatory inference is allowed.
- Audit files: `docs/audits/cycle-20261016T090727Z-76/audit.json`, `g6_plan_identity_finding.json`, and `g6_plan_identity_review.json`.
- Current ledger after this cycle: `10` open/blocked/unverified issues and `12` verified issues. G0/G6/G7 remain `BLOCKED`; G1–G5 remain engineering/smoke scope; `scientific_release_allowed=false`.
- No provider call, paid experiment, retry, historical result edit, confirmatory inference, or scientific claim was made. GitHub delivery remains externally blocked and must not be claimed until push plus `git ls-remote` succeeds.

## Cycle 77 G6 derived-report provenance correction (2026-10-16T09:10Z)

- Compared the G6 report tables against their named artifact roots. The old tables in `G0_G7_COMPLETE_DATA_CN_20261015.md`, `G0_G7_METRICS_CN_REPORT.md`, and `G0_G8_TABULAR_DATA_CN.md` report the older formal-20261013 metrics while the first report names the protocol-v2 root.
- Independently reran the analyzer on both immutable input sets: formal-20261013 reproduces CF1 `37/43`, CF3 `44/25`, ALL `191/186`; protocol-v2 produces CF1 `39/45`, CF3 `32/30`, ALL `181/194`.
- Added `docs/reports/G6_PROTOCOL_V2_REAUDIT_CN_20261016.md` with explicit v2 input paths, release-review hashes, counts, resource totals, current paired metrics, non-confirmatory status, and a clear historical-report boundary. No raw result or old report was overwritten.
- Full host suite remains `225 passed`; `git diff --check`: PASS. `ISSUE-2d7c9a4e1f60` is `VERIFIED` for derived-report provenance only; no confirmatory statistic or scientific claim was made.
- Audit files: `docs/audits/cycle-20261016T091032Z-77/audit.json`, `g6_report_provenance_finding.json`, and `g6_report_provenance_review.json`.
- Current ledger after this cycle: `10` open/blocked/unverified issues and `13` verified issues. G0/G6/G7 remain `BLOCKED`; G1–G5 remain engineering/smoke scope; `scientific_release_allowed=false`.
- No provider call, paid experiment, retry, historical raw-result edit, confirmatory inference, or scientific claim was made. GitHub delivery remains externally blocked and must not be claimed until push plus `git ls-remote` succeeds.

本交接文档不是 PASS 证明。`issues.json`、审计 JSON、冻结 plan/hash、独立复核和回归测试才是后续 Agent 可使用的证据。

