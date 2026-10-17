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

## Cycle 80 G7 complete-plan case/group coverage repair (2026-10-16T09:35Z)

- Compared the executable G7 preflight with `D:/硕士/prj1_ai_cal/writing/实验设计/全流程实验.md` G7.3–G7.7: a complete formal plan must retain every public case in both G3 and G4 and all seven diagnostic arms D0/D1/D2/D3/V_ONLY/L_ONLY/U_ONLY; checkpoint sharing is allowed only for the two forks of the same case.
- Independently reproduced a local fail-open before repair: a valid two-case public/label input with all seven arms for case-1 but no plan rows for case-2 returned `formal_run_allowed_by_protocol=true` under `require_complete_plan=True`.
- Repaired `scripts/run_g7_failure_localization.py::protocol_preflight` to check per-case/per-group coverage independently of aggregate checkpoint IDs, require exactly one checkpoint and the complete seven-arm set for each case/G3 and case/G4, reject duplicate case/group checkpoints and cross-case checkpoint reuse, and preserve same-case G3/G4 shared-checkpoint compatibility.
- Added adversarial tests for dropped public cases, duplicate case/group checkpoints, cross-case checkpoint collisions, and updated the shared-checkpoint control. Focused protocol tests pass `41/41`; the full repository suite passes `231/231`; py_compile and `git diff --check` pass.
- Re-ran the immutable protocol-corrected G7 plan preflight: `92` public cases, `1288` plan rows, `184` case/group keys, all complete; `incomplete_case_group_coverage=[]`, `duplicate_case_group_checkpoints=[]`, and `checkpoint_identity_collisions=[]`.
- `ISSUE-dad1d3f0293e` is `VERIFIED` for this local formal-plan coverage guard only. `ISSUE-000000000002`, `ISSUE-000000000003`, `ISSUE-000000000004`, `ISSUE-1f8c2b6a4d90`, and `ISSUE-3d7a9c1e5b20` remain externally or scientifically blocked; G0/G6/G7 remain `BLOCKED` and `scientific_release_allowed=false`.
- Audit files: `docs/audits/cycle-20261016T093500Z-80/audit.json`, `g7_plan_coverage_finding.json`, and `g7_plan_coverage_review.json`.
- Local commits: `776285b` (`Enforce complete G7 case-group coverage`), `83c35e4` (`Record G7 complete-plan coverage audit`), and `6623a63` (`Record cycle 80 remote delivery blocker`). Final `git push` and `git ls-remote` both exited `1` with a proxy connection failure to `github.com:443`; remote delivery is not claimed or verified.
- No provider call, paid experiment, retry, historical result edit, confirmatory inference, or scientific claim was made. The user-owned untracked `research_data_summary_G0_G7/` remains preserved and unstaged.

## Cycle 79 V2 ledger chronology repair (2026-10-16T09:27Z)

- During the post-cycle-78 state review, `ISSUE-000000000003` had a newer append-only BLOCKED history event but a stale top-level `last_seen`, weakening handoff chronology.
- Reproduced the defect with `tests/test_recovery_state.py::RecoveryTests::test_status_transition_updates_last_seen_with_history_timestamp`: the adversarial stale-timestamp probe failed before repair.
- Repaired `scripts/recovery_state.py::update_status` to write one `transition_time` to both `issue.last_seen` and the new history event. Added a regression test that rejects stale `last_seen` values.
- Recovery-state tests pass `13/13`; full host suite passes `228/228`; `py_compile` and `git diff --check` pass. The actual delivery-blocker issue was transitioned once after the repair so its top-level timestamp is current.
- `ISSUE-7b3e9a1c5d20` is `VERIFIED` for this local state-ledger consistency only. G0/G6/G7 remain `BLOCKED`; scientific release remains false; paid/provider and external provenance/statistical/math blockers are unchanged.
- Audit files: `docs/audits/cycle-20261016T092700Z-79/audit.json`, `ledger_timestamp_finding.json`, and `ledger_timestamp_review.json`.
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

## Cycle 78 G7 independent handoff boundary repair (2026-10-16T09:45Z)

- Compared the G7-to-G8 source-only handoff boundary with the design requirements under `D:/硕士/prj1_ai_cal/writing/实验设计` and the executable G7 preflight. The independent reviewer must fail closed on routing, private-oracle, verifier, and eligibility metadata in model-visible messages.
- Independently identified a local fail-open in `scripts/review_g7_g8_handoff.py::find_forbidden`: it used an incomplete, case-sensitive key set, so nested `Verifier_Ref`, `Eligible_U`, `CF_TYPE`, and `Theory_Family_Id` variants could be missed even though the runner rejects them.
- Repaired the independent reviewer to recursively casefold dictionary keys against the complete runner-aligned private/routing boundary. Ordinary public prose mentioning reserved words remains allowed because values are not scanned as key names.
- Added adversarial handoff tests. Focused G7 suite: `77 passed`; full host suite: `227 passed`; `py_compile` and `git diff --check` pass.
- `ISSUE-4a8f6c2e1d90` is `VERIFIED` for this local independent-audit boundary only. `ISSUE-000000000002`, `ISSUE-000000000003`, `ISSUE-000000000004`, `ISSUE-1f8c2b6a4d90`, and `ISSUE-3d7a9c1e5b20` remain externally or scientifically blocked; G0/G6/G7 remain `BLOCKED` and `scientific_release_allowed=false`.
- Audit files: `docs/audits/cycle-20261016T094500Z-78/audit.json`, `g7_handoff_boundary_finding.json`, and `g7_handoff_boundary_review.json`.
- No provider call, paid experiment, retry, historical result edit, confirmatory inference, or scientific claim was made. GitHub delivery remains externally blocked and must not be claimed until push plus `git ls-remote` succeeds.

## Cycle 81 G7 source G6 arm/group identity repair (2026-10-16T09:44Z)

- Re-read the three user-design documents under `D:/硕士/prj1_ai_cal/writing/实验设计` (`全流程实验.md`, `整体思路简化版.md`, and `科学问题到科学假设全思路.md`) and the V2 state/gate requirements before selecting the next local P1.
- Independently reproduced a structural fail-open in `scripts/run_g7_failure_localization.py::protocol_preflight`: after changing every G3 plan row's `source_g6_arm_id` from `G6_A_G3_GIVEN` to `G6_B_G4_GIVEN`, the old complete-plan preflight still returned `formal_run_allowed_by_protocol=true` and `errors=[]`.
- Repaired the complete-plan gate with explicit `G7_SOURCE_G6_ARM_BY_GROUP`: G3 must bind to `G6_A_G3_GIVEN` and G4 to `G6_B_G4_GIVEN`; mismatches now emit `g7_plan_group_arm_mismatch` and are listed in counts. Corrected the preflight fixture so it no longer masks the G3 mapping defect.
- Added an adversarial regression test. Focused G7 tests pass `42/42`; full repository suite passes `232/232`; py_compile and `git diff --check` pass.
- Re-ran the immutable formal plan preflight with `92` public cases, `92` labels, and `1288` plan rows: `formal_run_allowed_by_protocol=true`, `errors=[]`, `g7_plan_group_arm_mismatches=[]`, `incomplete_case_group_coverage=[]`, `duplicate_case_group_checkpoints=[]`, `checkpoint_identity_collisions=[]`, and `184` unique checkpoints.
- Independent read-only PowerShell reconstruction confirms `1288` rows, `184` case/group keys, `644` G3 rows, `644` G4 rows, zero source-arm mismatches, zero duplicate run-id groups, and plan SHA256 `be6c5550dfc453110b3f526f9ed6cf865bb0c1df5c3891b87dc0a23d6cf4c2e5`.
- `ISSUE-42e2f49eb73e` is `VERIFIED` for this local source-arm/group identity guard only. G0/G6/G7 remain `BLOCKED`; `scientific_release_allowed=false`; paid provider authorization, upstream provenance/Git delivery, independent statistical/mathematical review, dependency-edge truth, and scientific validity remain unresolved.
- Audit files: `docs/audits/cycle-20261016T094408Z-81/audit.json`, `g7_source_arm_mapping_finding.json`, and `g7_source_arm_mapping_review.json`.
- Local repair commit: `e5bc327`; audit/state commit: `01c5f52`; delivery-blocker state commit: `0e9e3c7`. Both `git push` and `git ls-remote` exited `1` because the configured proxy could not connect to GitHub port 443; remote delivery is not claimed. Do not stage the user-owned untracked `research_data_summary_G0_G7/` directory.
- No provider call, paid experiment, retry, historical result edit, confirmatory inference, or scientific claim was made. A remote push must be attempted and verified with `git ls-remote`; do not claim success if the proxy remains unavailable.

## Cycle 82 G7 formal experiment identity repair (2026-10-16T09:48Z)

- Re-read `D:/硕士/prj1_ai_cal/writing/实验设计/全流程实验.md`, `整体思路简化版.md`, and `科学问题到科学假设全思路.md`; the executable G7 plan namespace is `g7_failure_localization`, and the G7 design requires a frozen, auditable experiment/run contract before provider creation.
- Independently reproduced a local fail-open: before repair, a complete valid G7 fixture with `experiment_id` omitted from every plan row returned `formal_run_allowed_by_protocol=true` and `errors=[]` under `require_complete_plan=True`.
- Repaired `scripts/run_g7_failure_localization.py` so `_formal_plan_contract_valid` requires exact `experiment_id=g7_failure_localization`; added an adversarial missing/wrong identity test and corrected complete-plan fixtures.
- Focused G7 tests pass `43/43`; full repository suite passes `233/233`; py_compile and `git diff --check` pass.
- Re-ran the immutable formal preflight: `92` public cases, `92` labels, `1288` plan rows, `formal_run_allowed_by_protocol=true`, `errors=[]`, `invalid_g7_plan_metadata=[]`, `g7_plan_group_arm_mismatches=[]`, `incomplete_case_group_coverage=[]`, `duplicate_case_group_checkpoints=[]`, `checkpoint_identity_collisions=[]`, `184` unique checkpoints.
- Independent read-only scan confirms `1288` rows, `missing_experiment_id=0`, `wrong_experiment_id=0`, `source_arm_mismatches=0`, and plan SHA256 `be6c5550dfc453110b3f526f9ed6cf865bb0c1df5c3891b87dc0a23d6cf4c2e5`.
- `ISSUE-6f5db82e86c0` is `VERIFIED` for this local formal experiment-identity guard only. G0/G6/G7 remain `BLOCKED`; `scientific_release_allowed=false`; paid provider authorization, upstream provenance/Git delivery, independent statistical/mathematical review, dependency-edge truth, Q validity, and scientific claims remain unresolved.
- Audit files: `docs/audits/cycle-20261016T094833Z-82/audit.json`, `g7_experiment_identity_finding.json`, and `g7_experiment_identity_review.json`.
- Local repair commit: `b84f005`; audit/state commit: `45267ed`; delivery-blocker state commit: `bf9b8d9`. Both `git push` and `git ls-remote` exited `1` because the configured proxy could not connect to GitHub port 443; remote delivery is not claimed. Preserve and do not stage `research_data_summary_G0_G7/`.
- No provider call, paid experiment, retry, historical artifact edit, confirmatory inference, or scientific claim was made. Remote push plus `git ls-remote` must be attempted and verified before claiming delivery.

## Cycle 83 G7 non-pooled retry protocol repair (2026-10-16T09:51Z)

- Re-read the design and state controls. G7 terminal retries must remain separately frozen/non-pooled so failures and denominators cannot be hidden by combining batches.
- Independently reproduced a local fail-open: changing every valid complete-plan row's `retry_protocol` to `pooled` still returned `formal_run_allowed_by_protocol=true` and `errors=[]` under `require_complete_plan=True`.
- Repaired `scripts/run_g7_failure_localization.py` with `G7_RETRY_PROTOCOL=separate_frozen_retry_not_pooled`; complete-plan rows with any other value now fail `invalid_g7_plan_metadata`. Added an adversarial pooled-retry regression test.
- Focused G7 tests pass `44/44`; full repository suite passes `234/234`; py_compile and `git diff --check` pass.
- Re-ran the immutable formal preflight: `1288` plan rows, `formal_run_allowed_by_protocol=true`, `errors=[]`, `invalid_g7_plan_metadata=[]`, source-arm mismatches empty, complete case/group/checkpoint coverage intact, and `184` unique checkpoints.
- Independent read-only scan confirms `wrong_retry_protocol=0`, `missing_experiment_id=0`, `wrong_experiment_id=0`, `source_arm_mismatches=0`, and plan SHA256 `be6c5550dfc453110b3f526f9ed6cf865bb0c1df5c3891b87dc0a23d6cf4c2e5`.
- `ISSUE-57a074f246f3` is `VERIFIED` for this local retry-boundary guard only. G0/G6/G7 remain `BLOCKED`; `scientific_release_allowed=false`; external provider authorization, upstream provenance/Git delivery, Q/math/statistical review, dependency edges, and scientific release remain unresolved.
- Audit files: `docs/audits/cycle-20261016T095127Z-83/audit.json`, `g7_retry_protocol_finding.json`, and `g7_retry_protocol_review.json`.
- Local repair commit: `09432ff`; audit/state commit: `b66936d`; delivery-blocker state commit: `94adb84`. Both `git push` and `git ls-remote` exited `1` because the configured proxy could not connect to GitHub port 443; remote delivery is not claimed. Preserve and do not stage `research_data_summary_G0_G7/`.
- No provider call, paid experiment, retry, historical artifact edit, confirmatory inference, or scientific claim was made. Remote delivery requires both successful push and verified `git ls-remote`.

## Cycle 84 G7 source checkpoint lineage repair (2026-10-16T09:55Z)

- During an independent plan-lineage review, reproduced another local fail-open: changing one nonempty `source_checkpoint_id` within a complete G3 fork still returned `formal_run_allowed_by_protocol=true` and `errors=[]`.
- The intended invariant is one shared source checkpoint per `case_id/group_id`; `source_run_id` is intentionally distinct per diagnostic arm in the actual plan and was not constrained.
- Repaired `scripts/run_g7_failure_localization.py` to group source checkpoint IDs by case/group and reject mixed values with `g7_plan_source_checkpoint_mismatch`; added an adversarial regression test.
- Focused G7 tests pass `45/45`; full repository suite passes `235/235`; py_compile and `git diff --check` pass.
- Immutable preflight passes: `1288` plan rows, `formal_run_allowed_by_protocol=true`, `errors=[]`, source-checkpoint mismatches empty, source-arm mismatches empty, fixed non-pooled retry and experiment identities valid, and `184` unique checkpoints.
- Independent read-only scan confirms `184` case/group keys, `mixed_source_checkpoint_groups=0`, `wrong_retry_protocol=0`, missing/wrong experiment identity `0`, source-arm mismatches `0`, and plan SHA256 `be6c5550dfc453110b3f526f9ed6cf865bb0c1df5c3891b87dc0a23d6cf4c2e5`.
- `ISSUE-508d66813a87` is `VERIFIED` for this local source-checkpoint lineage guard only. G0/G6/G7 remain `BLOCKED`; `scientific_release_allowed=false`; provider, provenance, Q/math/statistics, dependency-edge, and scientific-release blockers remain.
- Audit files: `docs/audits/cycle-20261016T095537Z-84/audit.json`, `g7_source_checkpoint_finding.json`, and `g7_source_checkpoint_review.json`.
- Local repair commit: `d9e6b7f`; audit/state commit: `8a7468d`; delivery-blocker state commit: `b41043c`. Both `git push` and `git ls-remote` exited `1` because the configured proxy could not connect to GitHub port 443; remote delivery is not claimed. Preserve and do not stage `research_data_summary_G0_G7/`.
- No provider call, paid experiment, retry, historical artifact edit, confirmatory inference, or scientific claim was made. Remote delivery requires successful push plus verified `git ls-remote`.

## Cycle 93 final G0-G7 integrity audit (2026-10-17T00:20 HKT / 2026-10-16T16:20Z)

- Re-read the V2 recovery skill, the V1 scientific requirements, all three files under `D:/硕士/prj1_ai_cal/writing/实验设计`, `docs/state/issues.json`, `docs/state/UNRESOLVED_REPORT.md`, and `docs/state/gates.json`. The design files explicitly distinguish frozen historical G0-G6 artifacts from proposed G7-G13 protocol extensions; they do not authorize treating mock or historical non-confirmatory runs as new scientific evidence.
- Full host suite passes `247/247`; the explicit G7/gate/statistics suite passes `113/113`. A failed PowerShell wildcard invocation ran zero tests and is not counted as evidence.
- Re-ran the strict preflight with the correct separately frozen protocol-corrected plan: public `results/g7_failure_localization/formal-20261014T030000Z/g7_public_cases.jsonl`, labels `results/g7_failure_localization/formal-20261014T030000Z/g7_vlu_private.jsonl`, and plan `results/g7_failure_localization/formal-20261015T060000Z-protocol-corrected-16workers/g7_full_retry_plan.jsonl`. It reports `formal_run_allowed_by_protocol=true`, `errors=[]`, `92` public cases, `92` labels, `1288` plan rows, `184` checkpoints, zero duplicate runs/cases/labels, and canonical hashes matching the frozen constants. The older `formal-20261014T030000Z/g7_run_plan*.jsonl` is an intermediate historical plan and correctly fails the strict retry-scope/hash gate; it is not the formal input.
- Independent read-only `audit_g0_g8_integrity.py` and `review_g6_release.py` complete successfully for structural scope. Independent `audit_g7_failure_taxonomy.py` confirms failures remain in the denominator and retries are not pooled: original G7 has `78` provider errors, `217` checkpoint-missing rows, and `3/1288` Q-valid rows; protocol-corrected retry has `3` provider errors and `20/1288` Q-valid rows. Historical routing/verifier contamination remains non-confirmatory; no scientific truth decision is made.
- No local P0/P1 repair remains. `G0=BLOCKED`, `G1-G5=PASS` only in engineering/smoke scope, `G6=BLOCKED`, `G7=BLOCKED`, and `scientific_release_allowed=false` remain unchanged. The remaining P1 blockers require external upstream verification, authorized paid provider access with a positive hard USD ceiling and immutable billing/model evidence, and independent mathematical/statistical/dependency review. P2 classical baseline remains out of scope unless the study adds that comparison.
- Audit files: `docs/audits/cycle-20261017T000000Z-93/audit.json`, `g0_g7_completion_finding.json`, and `g0_g7_completion_review.json`.
- No provider call, paid experiment, raw-result edit, retry pooling, confirmatory inference, or scientific claim was made. Remote push and `git ls-remote` must still be attempted and reported truthfully; preserve and do not stage `research_data_summary_G0_G7/`.

## Cycle 89 G7 source-run lineage repair (2026-10-16T15:52Z)

- Re-read the three design documents under `D:/硕士/prj1_ai_cal/writing/实验设计` and the V2 state. The formal G7 plan must retain auditable source-run lineage for every diagnostic row; this is a protocol/input condition, not a scientific result. The source checkpoint may remain shared per case/group as repaired in cycle 84, while source run IDs must remain distinct per plan row.
- Independently reproduced a local fail-open before repair: setting every complete formal plan row's `source_run_id` to the same valid identifier still returned `formal_run_allowed_by_protocol=true`, `errors=[]`, and `duplicate_run_ids=0` under the strict formal-input preflight.
- Repaired `scripts/run_g7_failure_localization.py` to reject duplicate `source_run_id` values in the strict formal contract with `g7_formal_source_run_id_collision`; updated complete-plan fixtures to use unique source-run IDs per diagnostic arm and added an adversarial collision regression test.
- Focused G7 tests pass `54/54`; full repository suite passes `244/244`; py_compile and `git diff --check` pass.
- Immutable strict formal preflight passes: `92` public cases, `92` labels, `1288` plan rows, `23` families, exact CF1-CF4/final-test family coverage, exact public/label sets, fixed retry scope, no source-run collisions, no mixed source checkpoints, and `184` unique case/group checkpoints. Independent read-only scan confirms `1288` unique source-run IDs.
- `ISSUE-95600eba9ce3` is `VERIFIED` for this local source-run lineage guard only. G0/G6/G7 remain `BLOCKED`; `scientific_release_allowed=false`; paid provider authorization/billing, upstream provenance/Git delivery, independent statistical/mathematical review, dependency-edge truth, Q validity, and scientific claims remain unresolved.
- Audit files: `docs/audits/cycle-20261016T155220Z-89/audit.json`, `g7_source_run_lineage_finding.json`, and `g7_source_run_lineage_review.json`.
- Local repair commit: `37acedd`; audit/state commit: `64e7f3a`; delivery-blocker state commit: `9a6ad07`. Both `git push` and `git ls-remote` exited `1` because the configured proxy could not connect to GitHub port 443; remote delivery is not claimed. Preserve and do not stage the user-owned untracked `research_data_summary_G0_G7/` directory. No provider call, paid experiment, retry, historical artifact edit, confirmatory inference, or scientific claim was made.

## Cycle 90 G7 corrected family-denominator identity repair (2026-10-16T15:57Z)

- Re-read the three design documents under `D:/硕士/prj1_ai_cal/writing/实验设计` and the V2 state. The formal G7 input is the frozen corrected 23-family source-only denominator; `TB-L1-010` remains permanently excluded and must not be replaced by a new family.
- Independently reproduced a local fail-open before repair: replacing all four CF rows of one audited family with a new family, while synchronizing `paired_set_id`, label public hashes, and plan metadata, still passed strict preflight with `23` families and complete CF1-CF4/pair coverage.
- Repaired `scripts/run_g7_failure_localization.py` with the exact audited 23-family set and missing/extra family-set reporting under `require_formal_input_contract`; added an adversarial replacement-family regression test in `tests/test_g7_protocol.py`.
- Focused G7 tests pass `55/55`; full repository suite passes `245/245`; py_compile and `git diff --check` pass.
- Immutable strict preflight passes: `92` public cases, `92` labels, `1288` plan rows, exact `23`-family set with no missing/extra IDs, every family exactly CF1-CF4, exact public/label sets, no family/pair or source-run collisions, `1288` unique source runs, and `184` unique checkpoints. Independent read-only reconstruction reports the same zero-defect counts.
- `ISSUE-e83dea5cdd11` is `VERIFIED` for this local corrected-family denominator guard only. G0/G6/G7 remain `BLOCKED`; `scientific_release_allowed=false`; paid provider authorization/billing, upstream provenance/Git delivery, independent statistical/mathematical review, dependency-edge truth, Q validity, and scientific claims remain unresolved.
- Audit files: `docs/audits/cycle-20261016T155738Z-90/audit.json`, `g7_formal_family_denominator_finding.json`, and `g7_formal_family_denominator_review.json`.
- Local repair commit: `1f3cda2`; audit/state commit: `04b8958`; delivery-blocker state commit: `7e2693a`. Both `git push` and `git ls-remote` exited `1` because the configured proxy could not connect to GitHub port 443; remote delivery is not claimed. Preserve and do not stage the user-owned untracked `research_data_summary_G0_G7/` directory. No provider call, paid experiment, retry, historical artifact edit, confirmatory inference, or scientific claim was made.

## Cycle 91 G7 frozen case-denominator identity repair (2026-10-16T16:01Z)

- Re-read the three design documents under `D:/硕士/prj1_ai_cal/writing/实验设计` and the V2 state. The formal G7 public/private input set is frozen; preserving only row count, family layout, and synchronized label/plan mappings is insufficient if a case is silently replaced.
- Independently reproduced a local fail-open before repair: replacing one formal `case_id` with a new ID, updating its public `source_task_id`, label public hash, and every plan mapping, still returned `formal_run_allowed_by_protocol=true` and `errors=[]` with `92` public rows and complete family/checkpoint coverage.
- Repaired `scripts/run_g7_failure_localization.py` with the exact corrected `92`-case set generated from the audited `23` families × `CF1`-`CF4`; strict preflight now reports missing/extra case IDs and rejects the mutation. Added an adversarial replacement-case test in `tests/test_g7_protocol.py`.
- Focused G7 tests pass `56/56`; full repository suite passes `246/246`; py_compile and `git diff --check` pass.
- Immutable strict preflight passes: `92` public cases, `92` labels, `1288` plan rows, exact case/family sets with no missing or extra IDs, every family exactly CF1-CF4, public/label equality, `1288` unique source runs, and `184` unique checkpoints. Independent read-only reconstruction reports the same zero-defect counts.
- `ISSUE-5984ec2cef1c` is `VERIFIED` for this local frozen case-set guard only. G0/G6/G7 remain `BLOCKED`; `scientific_release_allowed=false`; paid provider authorization/billing, upstream provenance/Git delivery, independent statistical/mathematical review, dependency-edge truth, Q validity, and scientific claims remain unresolved.
- Audit files: `docs/audits/cycle-20261016T160121Z-91/audit.json`, `g7_formal_case_denominator_finding.json`, and `g7_formal_case_denominator_review.json`.
- Local repair commit: `95a5a70`; audit/state commit: `7cc33fb`; delivery-blocker state commit: `bd89c50`. Both `git push` and `git ls-remote` exited `1` because the configured proxy could not connect to GitHub port 443; remote delivery is not claimed. Preserve and do not stage the user-owned untracked `research_data_summary_G0_G7/` directory. No provider call, paid experiment, retry, historical artifact edit, confirmatory inference, or scientific claim was made.

## Cycle 92 G7 canonical frozen-input identity repair (2026-10-16T16:04Z)

- Re-read the three design documents under `D:/硕士/prj1_ai_cal/writing/实验设计` and the V2 state. The G7 public cases, private labels, and corrected retry plan are frozen inputs; field-level structural checks alone must not allow synchronized source-task or content mutations.
- Independently reproduced a local fail-open before repair: changing one public `source_task_id` and recomputing the affected label public hash still returned `formal_run_allowed_by_protocol=true` and `errors=[]`.
- Repaired `scripts/run_g7_failure_localization.py` with canonical compact sorted-key JSONL SHA-256 checks for the exact public, private-label, and retry-plan row sequences; added an adversarial source-task mutation test. The strict report now exposes canonical hashes and mismatch names.
- Focused G7 tests pass `57/57`; full repository suite passes `247/247`; py_compile and `git diff --check` pass.
- Immutable strict preflight passes: `92` public cases, `92` labels, `1288` plan rows, exact case/family sets, canonical hash mismatches `[]`, public hash `b0ff3d3c9178cc068b0399f073981f990e313677536b6791cc170ecd2c6db597`, labels hash `bd34b7087e04810208baeb1cbfa4b9d0b207b3d7066dec2817debe9112d44f70`, plan hash `a99e44f5e4edbc959284993714a0a460e8c83b30b07a261c938b14b0d916aec3`, `1288` unique source runs, and `184` unique checkpoints. Independent read-only reconstruction matches.
- `ISSUE-a9c2ef769cad` is `VERIFIED` for this local frozen-input hash guard only. G0/G6/G7 remain `BLOCKED`; `scientific_release_allowed=false`; paid provider authorization/billing, upstream provenance/Git delivery, independent statistical/mathematical review, dependency-edge truth, Q validity, and scientific claims remain unresolved.
- Audit files: `docs/audits/cycle-20261016T160431Z-92/audit.json`, `g7_formal_input_hash_finding.json`, and `g7_formal_input_hash_review.json`.
- Local repair commit: `aeb5375`; audit/state commit: `749bfb0`; final delivery-blocker state commit: `d2a505f` (hash-evidence correction commit: `d57cba8`). Both `git push` and `git ls-remote` exited `1` because the configured proxy could not connect to GitHub port 443; remote delivery is not claimed. Preserve and do not stage the user-owned untracked `research_data_summary_G0_G7/` directory. No provider call, paid experiment, retry, historical artifact edit, confirmatory inference, or scientific claim was made.

## Cycle 87 G7 formal public CF/split contract repair (2026-10-16T15:40Z)

- Re-read the three design documents under `D:/硕士/prj1_ai_cal/writing/实验设计` (`全流程实验.md`, `整体思路简化版.md`, and `科学问题到科学假设全思路.md`) together with `docs/state/gates.json`. The formal G7 input contract is the CF1-CF4 `final_test` public benchmark set; this is a precondition for any frozen provider plan, not a scientific result.
- Independently reproduced another local fail-open before repair: changing a valid complete fixture's public and plan `cf_type` to `CF5`, or its `split` to `dev` while recalculating the label public-case hash, still returned `formal_run_allowed_by_protocol=true` and `errors=[]` under `require_complete_plan=True`.
- Repaired `scripts/run_g7_failure_localization.py` with exact `G7_CF_TYPES={CF1,CF2,CF3,CF4}` and `G7_FORMAL_SPLIT=final_test` checks in `_formal_public_contract_valid`; added an adversarial test covering both mutations in `tests/test_g7_protocol.py`.
- Focused G7 tests pass `48/48`; full repository suite passes `238/238`; py_compile and `git diff --check` pass.
- Immutable formal preflight passes with `92` public cases, `92` labels, `1288` plan rows, `formal_run_allowed_by_protocol=true`, `errors=[]`, empty invalid public/plan metadata, empty source-checkpoint and group-arm mismatches, complete coverage, no collisions, and `184` unique checkpoints. Public SHA256 is `1bffc3769523e437cc7e4ea5cff22f4eb2d42cd3500299f914cb03ec36b6063f`; plan SHA256 remains `be6c5550dfc453110b3f526f9ed6cf865bb0c1df5c3891b87dc0a23d6cf4c2e5`.
- Independent read-only Python reconstruction confirms `92` public rows across `23` families, each with exactly `CF1`-`CF4` and `final_test`; duplicate public case IDs `0`; `1288` plan rows; duplicate run IDs `0`; wrong protocol/profile/retry/experiment/split/CF metadata `0`; and mixed source-checkpoint groups `0`.
- `ISSUE-53e9722cb252` is `VERIFIED` for this local formal public-input guard only. G0/G6/G7 remain `BLOCKED`; `scientific_release_allowed=false`; provider authorization/billing, upstream provenance/Git delivery, independent statistical/mathematical review, dependency-edge truth, and scientific validity remain unresolved.
- Audit files: `docs/audits/cycle-20261016T154007Z-87/audit.json`, `g7_public_contract_finding.json`, and `g7_public_contract_review.json`.
- Local repair commit: `7bc22e2`; audit/state commit: `479a67e`; delivery-blocker state commit: `81ab8ce`. Both push and `git ls-remote` exited `1` because the configured proxy could not connect to GitHub port 443; remote delivery is not claimed. Do not stage the user-owned untracked `research_data_summary_G0_G7/` directory.
- No provider call, paid experiment, retry, historical artifact edit, confirmatory inference, or scientific claim was made. Both remote push and `git ls-remote` must be attempted and independently verified; never claim GitHub delivery from a failed or unverified command.

## Cycle 88 G7 formal input completeness repair (2026-10-16T15:47Z)

- Re-read `D:/硕士/prj1_ai_cal/writing/实验设计/全流程实验.md`, `整体思路简化版.md`, and `科学问题到科学假设全思路.md`, plus `docs/state/gates.json`. The formal G7 contract must preserve the public/private case set, CF1-CF4 family structure, paired lineage, and the separately frozen full retry scope before any provider call.
- Independently reproduced three local fail-open mutations before repair: an orphan but structurally valid label case was accepted; every `retry_scope` was changed to another nonempty value and accepted; and one family's CF4 public case, label, and plan rows were removed, leaving a complete remaining case/group grid that was accepted.
- Repaired `scripts/run_g7_failure_localization.py` with `require_formal_input_contract`: production/formal preflight now requires exact public/label case-set equality, `retry_scope=all_original_rows_protocol_corrected`, every theory family covering CF1-CF4, and bijective family/paired-set lineage. Enabled the strict flag in both the real runner and `scripts/g7_protocol_preflight.py`; added report counts and adversarial tests.
- Focused G7 tests pass `52/52`; full repository suite passes `242/242`; py_compile and `git diff --check` pass.
- Strict immutable formal preflight passes: `92` public cases, `92` labels, `1288` plan rows, `23` families each with exactly CF1-CF4, exact public/label case sets, retry-scope mismatches `[]`, paired-lineage mismatches `[]`, source-checkpoint/group-arm mismatches `[]`, and `184` unique checkpoints. Public SHA256 remains `1bffc3769523e437cc7e4ea5cff22f4eb2d42cd3500299f914cb03ec36b6063f`; plan SHA256 remains `be6c5550dfc453110b3f526f9ed6cf865bb0c1df5c3891b87dc0a23d6cf4c2e5`.
- Independent read-only Python reconstruction confirms `public_rows=92`, `label_rows=92`, `plan_rows=1288`, `families=23`, family sizes all `4`, every family CF set exactly `CF1-CF4`, public/label sets equal, duplicate IDs `0`, wrong retry scope/protocol/version `0`, and mixed source checkpoints `0`.
- `ISSUE-136c15318a59` is `VERIFIED` for this local formal-input completeness guard only. G0/G6/G7 remain `BLOCKED`; `scientific_release_allowed=false`; paid provider authorization/billing, upstream provenance/Git delivery, independent statistical/mathematical review, dependency-edge truth, Q validity, and scientific claims remain unresolved.
- Audit files: `docs/audits/cycle-20261016T154759Z-88/audit.json`, `g7_formal_input_contract_finding.json`, and `g7_formal_input_contract_review.json`.
- Local repair commit: `de7581f`; audit/state commit: `7ab3a40`; delivery-blocker state commit: `02145e0`. Both push and `git ls-remote` exited `1` because the configured proxy could not connect to GitHub port 443; remote delivery is not claimed. Preserve and do not stage the user-owned untracked `research_data_summary_G0_G7/` directory.
- No provider call, paid experiment, retry, historical artifact edit, confirmatory inference, or scientific claim was made. Both remote push and `git ls-remote` must be attempted and independently verified; never claim GitHub delivery from a failed or unverified command.

## Cycle 86 G7 strict protocol-version identity repair (2026-10-16T10:01Z)

- Compared the formal plan with the current strict G7 response/retry contract and the three design documents. The executable corrected plan uses `g7-public-case-format-retry-v1`, but the old preflight accepted any nonempty version.
- Independently reproduced the fail-open by changing every valid fixture row to `protocol_version=legacy`; old preflight returned `formal_run_allowed_by_protocol=true` and `errors=[]`.
- Repaired `scripts/run_g7_failure_localization.py` with `G7_PROTOCOL_VERSION=g7-public-case-format-retry-v1`; wrong versions now fail `invalid_g7_plan_metadata`. Added an adversarial wrong-version test and updated complete-plan fixtures.
- Focused G7 tests pass `47/47`; full repository suite passes `237/237`; py_compile and `git diff --check` pass.
- Immutable formal preflight passes: `1288` plan rows, `formal_run_allowed_by_protocol=true`, `errors=[]`, invalid metadata empty, source checkpoint/arm mismatches empty, fixed profile/experiment/retry identities valid, and `184` unique checkpoints.
- Independent read-only scan confirms `wrong_protocol_version=0`, `wrong_profile=0`, `wrong_retry_protocol=0`, missing/wrong experiment identity `0`, source-arm mismatches `0`, source-checkpoint mismatch groups `0`, and plan SHA256 `be6c5550dfc453110b3f526f9ed6cf865bb0c1df5c3891b87dc0a23d6cf4c2e5`.
- `ISSUE-5788b5a4ed09` is `VERIFIED` for this local protocol-version identity guard only. G0/G6/G7 remain `BLOCKED`; `scientific_release_allowed=false`; provider, provenance, Q/math/statistics, dependency-edge, and scientific-release blockers remain.
- Audit files: `docs/audits/cycle-20261016T100123Z-86/audit.json`, `g7_protocol_version_finding.json`, and `g7_protocol_version_review.json`.
- Local repair commit: `077c649`; audit/state commit: `0067010`; delivery-blocker state commit: `32535f9`. Both `git push` and `git ls-remote` exited `1` because the configured proxy could not connect to GitHub port 443; remote delivery is not claimed. Preserve and do not stage `research_data_summary_G0_G7/`.
- No provider call, paid experiment, retry, historical artifact edit, confirmatory inference, or scientific claim was made. Remote delivery requires successful push plus verified `git ls-remote`.

## Cycle 85 G7 executable profile identity repair (2026-10-16T09:58Z)

- Compared the plan contract with the actual runner prompt and the three design documents. The runner explicitly executes `profile=theory_benchmark`, but the complete-plan gate previously accepted any nonempty profile.
- Independently reproduced the fail-open by changing every valid fixture row to `profile=law_discovery`; old preflight returned `formal_run_allowed_by_protocol=true` and `errors=[]`.
- Repaired `scripts/run_g7_failure_localization.py` with `G7_PROFILE=theory_benchmark`; complete-plan rows with another profile now fail `invalid_g7_plan_metadata`. Added an adversarial wrong-profile test.
- Focused G7 tests pass `46/46`; full repository suite passes `236/236`; py_compile and `git diff --check` pass.
- Immutable formal preflight passes: `1288` plan rows, `formal_run_allowed_by_protocol=true`, `errors=[]`, invalid plan metadata empty, source checkpoint/arm mismatches empty, fixed retry/experiment identities valid, and `184` unique checkpoints.
- Independent read-only scan confirms `wrong_profile=0`, `wrong_retry_protocol=0`, missing/wrong experiment identity `0`, source-arm mismatches `0`, source-checkpoint mismatch groups `0`, and plan SHA256 `be6c5550dfc453110b3f526f9ed6cf865bb0c1df5c3891b87dc0a23d6cf4c2e5`.
- `ISSUE-6bd0c43fb941` is `VERIFIED` for this local executable-profile identity guard only. G0/G6/G7 remain `BLOCKED`; `scientific_release_allowed=false`; provider, provenance, Q/math/statistics, dependency-edge, and scientific-release blockers remain.
- Audit files: `docs/audits/cycle-20261016T095836Z-85/audit.json`, `g7_profile_finding.json`, and `g7_profile_review.json`.
- Local repair commit: `4474e95`; audit/state commit: `102994c`; delivery-blocker state commit: `c004e9d`. Both `git push` and `git ls-remote` exited `1` because the configured proxy could not connect to GitHub port 443; remote delivery is not claimed. Preserve and do not stage `research_data_summary_G0_G7/`.
- No provider call, paid experiment, retry, historical artifact edit, confirmatory inference, or scientific claim was made. Remote delivery requires successful push plus verified `git ls-remote`.

## Cycle 94 — CTFlow live preflight and paid-boundary audit (2026-10-17 00:40 HKT / 2026-10-16 16:40Z)

- Applied `scientific-law-recovery`, `scientific-law-autopilot`, and `scientific-law-ctflow-matrix`. Rechecked the external experiment design: G0–G6 are frozen historical handoff material and G7 requires real logs, independent labels, D0–D3 intervention evidence, fair G3/G4 pairing, and retained failures.
- The user authorization is now explicit: paid calls allowed with an aggregate hard ceiling of USD 200. This is recorded in `configs/model_matrix.json`; it does not override provider, runner, or scientific gates.
- Fetched `https://token.ctflow.cn/tokendocs` over HTTPS. The page documents `https://token.ctflow.cn/v1`, `/models`, `/chat/completions`, and Bearer authentication, but no independently verifiable pricing/usage/billing contract.
- Same-origin unauthenticated catalog probe returned HTTP 401. Authenticated discovery returned 243 exact model IDs. Minimal live preflight: `qwen3.5-plus=PASS`, `glm-5.2=PASS`, `deepseek-v3.2=FAILED`. The failed model remains excluded from any formal selection.
- Fixed the matrix manifest path from nonexistent `configs/task_manifest.json` to the existing root `task_manifest.json`; recorded the USD 200 ceiling while retaining `runner_command=[]` and `runner_supports_budget_enforcement=false`.
- New evidence: `docs/provider/CTFLOW_LIVE_PREFLIGHT_20261016.md`, `docs/audits/cycle-20261016T163912Z-94/audit.json`, `provider_preflight_finding.json`, and `provider_preflight_review.json`.
- Verification: live CTFlow preflight completed; `tests/test_ctflow_matrix.py` passed `14/14`; full host suite passed `247/247`; matrix plan resolved the manifest and remained `runner_integrated=false`; strict G7 preflight passed `92` public cases, `92` labels, `1288` rows, `184` checkpoints, zero errors, and `provider_calls_made=false`; independent G0–G8/G7 taxonomy/G6 reviews retained `scientific_release_allowed=false`.
- Formal paid G0–G7 experiment was not started. No formal scientific result or claim was created. The remaining P1 blocker is now provider-verifiable pricing/billing, immutable model identity, tested runner-level hard cap, and independent isolation/statistical review—not missing user authorization.
- Preserve user-owned untracked `research_data_summary_G0_G7/`; do not stage it. Do not commit `.env`, key files, `runs/`, raw protected outputs, or hidden labels. Cycle-94 `git push` and independent `git ls-remote` both exited `1` because the configured proxy could not connect to GitHub port 443; remote update is not claimed.
- Next priority: only after provider pricing/billing and runner-level cap evidence are available, implement/test the thin existing-runner adapter and run a separately frozen authorized pilot. Otherwise remain blocked; never synthesize a billing export, immutable weight fingerprint, G7 result, or scientific release.

## Cycle 95 real CTFlow matrix execution and fail-closed audit (2026-10-17 HKT / 2026-10-16 UTC)

- Continued from the V2 handoff and rechecked the user design reference under `D:/硕士/prj1_ai_cal/writing/实验设计`. The executed scope remains the frozen NewtonBench G0-G7 LLM-only versus single-Agent matrix; historical G8/G9 artifacts were not relabeled as new evidence.
- Implemented and tested the integrated `scripts/run_matrix_scientific.py` adapter around the existing authoritative `run_one` orchestration. It preserves frozen-plan LLM-only isolation, adaptive single-Agent tool use, held-out evaluator results, task-level failures, exact model IDs, manifest hashes, traces, and conservative pre-request reservations.
- Real paid CTFlow matrix completed at `runs/ctflow_matrix/20261016T173343Z-98f74b99`: models `qwen3.5-plus` and `glm-5.2`, both `llm_only` and `agent` arms, `4` arms × `12` tasks = `48` task rows. The host returned `RC=3` and `all_paired_verified=false`; this is the intended fail-closed outcome because the arms contain task/protocol failures.
- Persisted arm outcomes: qwen Agent `12` tasks/`2` failures/`3` held-out validated successes; qwen LLM-only `12`/`4`/`4`; glm Agent `12`/`12`/`0`; glm LLM-only `12`/`10`/`0`. These are execution/evaluator outcomes only and do not support superiority, causal, or release claims.
- Local proxy accounting totals are actual `$0.828254` and conservative reserved `$8.175212` against the user-authorized aggregate ceiling `$200`. These are not provider billing figures; `provider_billing_verified=false`, immutable model-weight identity is unverified, and the provider rate contract remains unverified.
- Added `scripts/audit_ctflow_matrix.py` and independent report `docs/audits/cycle-20261017T000000Z-95/ctflow_matrix_audit.json`: exact four-arm set, 48 task rows, 48 traces, manifest hash, redaction markers, failure counts, and aggregate/per-arm caps all pass structurally; `scientific_release_allowed=false` and paired verification remains false.
- Repaired the matrix host to report existing failed `result.json` contracts instead of mislabeling `RC=3` as a missing evaluator sidecar. Repaired the runner budget gate to require both reserved and observed local cost under the cap. Added adversarial regression coverage.
- Independent audits: `g0_g8_integrity.json`, `g7_failure_taxonomy.json`, and `g6_release_review.json` under the cycle-95 directory all exit `0`; they retain external/math/statistical/G7 caveats and make no scientific truth decision. Final host suite passes `253/253`; matrix-focused suite passes `19/19`; py_compile and `git diff --check` pass.
- State ledger: `ISSUE-000000000002` remains `BLOCKED` with cycle-95 evidence. `ISSUE-000000000003` remains blocked until a push and `git ls-remote` are both independently successful. `ISSUE-000000000004`, dependency-edge/Q/math/statistical issues, and G0/G6/G7 scientific release remain blocked. Do not close issues because one audit is silent.
- Delivery: local commits `ddac6d8`, `d0f50fb`, and `06e081d` were created. The latest `git push origin autopilot/scientific-law-discovery` and `git ls-remote origin refs/heads/autopilot/scientific-law-discovery` both exited `1` with the configured proxy unable to connect to GitHub port 443; remote delivery is not claimed.
- Preserve and do not stage the user-owned untracked `research_data_summary_G0_G7/` directory. Do not commit API keys, `.env`, or raw protected outputs. A new agent must inspect the cycle-95 audit, run `recovery_state.py bootstrap`, and continue only from the ledger.

## Cycle 96 qwen single-model pilot and resumable runner repair (2026-10-17 HKT)

- Followed `scientific-law-recovery` and rechecked the frozen NewtonBench G0-G7 scope plus the three design documents under `D:/硕士/prj1_ai_cal/writing/实验设计`. The new paid scope was one exact model only: `qwen3.5-plus`, matched `llm_only` and `agent`, the existing 12-task frozen manifest, five repeats per task per arm.
- Qualification was run first on one frozen hard task. LLM-only failed with a provider read timeout; Agent retained two real observations but failed before final submission on a later provider timeout. The operator interruption of the first long attempt is retained in `runs/ctflow_single_model/20261017T-single-qwen/agent/interrupted_attempt.json`; neither qualification arm is counted as a success.
- Repaired the runner budget boundary so the request timeout is tightened through the local policy/trace wrappers to the remaining runtime budget. Added `scripts/run_single_model_pilot.py` with exact model/base selection, per-task conservative reservations, independent task directories, durable checkpointing, bounded concurrency, `--resume`, and artifact reconciliation that registers trace-only interruptions as failures. Added tests for timeout clamping, pilot checkpointing, failure retention, and no-duplicate reconciliation.
- Paid pilot completed at `runs/ctflow_single_model/20261017T-pilot-qwen/result.json`: `120/120` registered task-runs (`12 tasks × 5 repeats × 2 arms`), `81` task failures, `11` held-out `validated_success` rows, actual local proxy cost `$1.398455`, conservative reserved local proxy cost `$61.674731`, pilot cap `$140`. Provider billing is not verified; these are not invoice values.
- Independent audit `docs/audits/cycle-20261017T-pilot-qwen/single_model_pilot_audit.json` passes with exact row keys, 120 trace directories, manifest SHA256 `5f7da3480ad5f40c747ceaeaf09b028f6bef823fe3ea230e88665ed2a5c6c3cf`, failure/success/cost sums, and zero Bearer/unredacted truth markers. Descriptive summary is `docs/audits/cycle-20261017T-pilot-qwen/single_model_pilot_summary.json`: LLM-only `5/60` validated successes, Agent `6/60`, paired mean `0.0166667`, law-family bootstrap 95% CI `[-0.0666667, 0.1]`; formal inference is prohibited.
- Full host suite passes `257/257`; focused pilot/budget tests pass `6/6`; py_compile and `git diff --check` pass. Audit package: `docs/audits/cycle-20261017T-pilot-qwen/audit.json`.
- State ledger keeps `ISSUE-000000000002` blocked: local runner and failure retention are verified, but provider billing/pricing and immutable model identity remain unverified. G0, G6, G7, dependency-edge/Q/statistical/math issues, and scientific release remain blocked. This pilot is not a G7 failure-localization result and does not repair historical G7 artifacts.
- Local commits for this cycle include `53fba30`, `b7746dc`, `a84267`, `b7c9acc`, and final evidence commit `37e21eb`. `git push origin autopilot/scientific-law-discovery` and independent `git ls-remote origin refs/heads/autopilot/scientific-law-discovery` both exited `1` because the configured proxy could not connect to GitHub port 443; remote delivery is not claimed. Preserve and do not stage the user-owned untracked `research_data_summary_G0_G7/` directory; do not commit API keys, `.env`, or raw protected outputs.

## Cycle 97 G0 provenance repair and qwen single-model G7 preflight (2026-10-17 HKT)

- The stale local proxy was bypassed only for the network commands. Direct `git ls-remote` verified the configured NewtonBench commit `912a4ba5f4356ddd06acc16e44460ca30be4abc2` at upstream `HEAD`, and the upstream raw `LICENSE` at that exact commit returned HTTP 200 with SHA-256 `47158d3a1eb6cbebe82fab657c11d4959c453f4d803b103a132b4627b63719f0`, matching the vendored license. `G0` is now `PASS` for simulator provenance/licensing only; `official_numeric_evaluator=false` remains a caveat and scientific release remains false.
- The feature branch was pushed successfully with proxy bypass: `git push` exit `0`; independent `git ls-remote origin refs/heads/autopilot/scientific-law-discovery` exit `0` returned `a592f832fbb1e787a9edb21f67b46d44fbefa910`. `ISSUE-000000000003` is verified. Do not confuse this with a scientific release.
- qwen3.5-plus G7 formal-input preflight was run without provider calls. It passes the exact frozen corrected input contract: 92 public cases, 92 labels, 1288 plan rows, 184 checkpoints, all seven arms per checkpoint, zero duplicate/lineage/metadata/privacy errors. Audit: `docs/audits/cycle-20261017T-g7-single-qwen-preflight/audit.json`.
- The qwen G7 paid run was not started because the formal runner still correctly requires provider-verifiable billing evidence and an immutable model snapshot/gateway weight fingerprint. The existing qwen single-model NewtonBench pilot remains complete non-confirmatory evidence; it is not relabelled as G7. Do not fabricate either missing artifact or bypass the gate.
- Verification: `E:/resources/python/python.exe -X utf8 -m pytest -q tests/test_gate_attestation.py` passed `3/3`; run the full host suite before the next commit. Preserve and do not stage `research_data_summary_G0_G7/`, API keys, `.env`, or raw protected outputs.

## Cycle 98 post-commit remote verification (2026-10-17 HKT)

- Full host regression after the G0 update passed `257/257`; py_compile and `git diff --check` passed.
- Commit `ebca2e12e18ef68888691f27f25e99d76f8ec54c` was pushed with proxy bypass and independently verified by `git ls-remote` as `origin/autopilot/scientific-law-discovery`. The user-owned untracked `research_data_summary_G0_G7/` directory remains untouched and unstaged.

## Cycle 99 qwen single-model G7 API execution and trace-repair recovery (2026-10-17 HKT)

- The user explicitly authorized paid calls with a total ceiling of USD 200. The new G7 execution used only `qwen3.5-plus` through CTFlow, with a 16-worker aggregate cap of USD 60; the local trace-summed cost is USD 6.696837. Provider billing, pricing, and immutable gateway/model-weight evidence remain unverified, so this is an authorized non-confirmatory pilot.
- The frozen corrected G7 input was unchanged: 92 public cases, 92 labels, 1288 plan rows, 184 checkpoints, seven diagnostic arms per checkpoint, and the input hashes recorded in `runs/ctflow_single_model/20261017T-g7-qwen-v1/g7_protocol_preflight.json`.
- Canonical qwen results are complete for accounting: 1288/1288 states (`438 completed`, `17 provider_error`, `833 checkpoint_missing`) and 184/184 checkpoints (`65 completed`, `119 provider_error`). All provider failures remain in the denominator. The provider returned recorded invalid-token/HTTP-401 failures during recovery; they were not relabeled as successes.
- Independent qwen audits: Q audit `1288/1288` is `NOT_SCORED` without an external Q verifier; trace/Q consistency reports zero state and checkpoint trace-integrity failures, 438 completed state traces, 17 terminal-failure traces, 833 not-executed checkpoint-dependent states, 65 completed checkpoint traces, and 119 terminal-failure traces. Confirmatory reuse is false and no scientific truth decision was made.
- Repaired and tested three runner defects exposed by the real run: terminal-error sequence recovery after an inner provider exception, append-safe `.retry-N` paths for malformed historical traces, and concurrent worker writes to the shared preflight artifact. Targeted G7/trace/Q tests pass `82/82`; commits are `419f94f`, `4e6b3c1`, `5f5cf23`, and `e2052eb`.
- `ISSUE-3d7a9c1e5b20` remains `BLOCKED`: the qwen run is real and structurally auditable, but provider 401 failures, independently valid Q evidence, dependency/L/U data, external model identity, billing, and statistical/math review are unresolved. Do not claim G7 formal completion or Agent superiority.
- G6 qwen single-model API execution is still running in `runs/ctflow_single_model/20261017T-g6-qwen-v2` with two workers. Do not merge or score it until both worker summaries exist; then run the parameterized G6 audit with `--expected-model-id qwen3.5-plus --expected-base-url https://token.ctflow.cn/v1`, an independent release review, full tests, a cycle audit, bootstrap, commit, push, and remote `ls-remote` verification.
- Audit: `docs/audits/cycle-20261017T-g7-qwen-api-repair/audit.json`. Preserve API keys, billing/private raw results, `runs/`, and the untracked user-owned `research_data_summary_G0_G7/`; never stage them.

## Cycle 100 qwen single-model G6 API completion and failure-retention audit (2026-10-17 HKT)

- The qwen3.5-plus G6 single-model API run completed for the frozen corrected G6 plan. The canonical merge covers all `552/552` unique rows: `231 completed` and `321 provider_error`; no row was dropped or converted into a success.
- G6 trace audit covers `552/552` traces with `0` integrity failures, `1171` model requests, `532` model responses, `371` tool calls/results, `1,064,548` tokens, and observed local trace cost `USD 1.932244`. Failure-only retries recorded upstream `HTTP 401 Invalid token`; this is retained as terminal provider failure evidence.
- The independent coverage review passes structurally with `scientific_release_allowed=false`, explicitly allowing retained terminal failures only for non-confirmatory execution coverage. No G6-to-G7 handoff was generated from incomplete responses; CF3 revision validity is `0/138`.
- G6 repair changes: append-safe `.retry-N` trace paths, persisted-sequence recovery before terminal error events, failure-preserving canonical merge, qwen model/base-url parameterization, and aggregate-manifest exclusion from the two-worker audit. Focused G6 tests pass `8/8`; full host suite passes `262/262`.
- Audit: `docs/audits/cycle-20261017T-g6-qwen-api/audit.json`. G6 remains non-confirmatory because provider failures, external billing/model snapshot, independent math/statistics, and scientific gates remain unresolved. The prior Cycle 99 “G6 still running” note is superseded by this completion entry.
- Preserve API keys, billing/private raw results, `runs/`, and the untracked user-owned `research_data_summary_G0_G7/`; never stage them. G0/G6/G7 remain `BLOCKED` and `scientific_release_allowed=false`.

## Cycle 101 CTFlow credential blocker recheck (2026-10-17 HKT)

- Re-ran the mandatory V2 bootstrap and read the current ledger, unresolved report, and gates. No completed G0–G7 milestone was rebuilt.
- A read-only same-origin catalog check against `https://token.ctflow.cn/v1/models` returned HTTP `401` both without credentials and with the local qwen credential source. No generation request or paid retry was made in this cycle.
- This reproduces the `HTTP 401 Invalid token` evidence retained in the qwen G6/G7 terminal failures. The provider key/model identity/billing blocker remains external; a new paid retry is not justified until a valid authorized credential and provider-verifiable billing/model snapshot evidence are supplied.
- Audit: `docs/audits/cycle-20261017T-provider-key-audit/audit.json`. Provider-focused regression tests pass `19/19`; the prior full host result remains `262/262`.
- State remains truthful: `ISSUE-000000000002` is `BLOCKED`; G6/G7 are non-confirmatory and `scientific_release_allowed=false`. Preserve API keys, `runs/`, and `research_data_summary_G0_G7/`; do not stage them.
- Delivery note: the local provider-blocker audit was committed as `4e13ec4`, but two proxy-bypassed push attempts and an independent `git ls-remote` failed because GitHub TCP/443 was unreachable. Do not claim this cycle is remotely delivered until `git ls-remote` returns the exact local SHA.

## Cycle 102 Kimi K2.5 single-model G6/G7 execution and audit (2026-10-17 HKT)

- Followed `scientific-law-recovery` and the frozen experiment design. The user explicitly authorized paid calls with a total ceiling of USD 200. Only `kimi-k2.5` was used through `https://token.ctflow.cn/v1`; keys and raw runs remain local and untracked.
- Kimi G6 completed with two workers and append-only failure-only resume. The canonical frozen plan covers `552/552` unique rows: `550 completed`, `2 provider_error`; `22` earlier provider failures recovered on retry. G6 trace integrity failures are `0/552`; revision audit is `0/138` valid; independent structural review passes but `scientific_release_allowed=false`.
- Kimi G6 observed local trace cost is USD `2.034328`. This is local proxy accounting, not independently verified provider billing.
- Kimi G7 strict preflight passed without provider calls: `92` public cases, `92` labels, `1288` plan rows, `184` checkpoints, seven arms/checkpoint, zero protocol/hash/lineage errors.
- Kimi G7 completed with 16 workers and append-only failure-only resume. Latest canonical merge covers `1288/1288` rows and `184/184` checkpoints: states `35 completed` and `1253 checkpoint_missing`; checkpoints `5 completed` and `179 provider_error`. All failures remain in the denominator.
- G7 Q audit retains `1288/1288` invalid/not-scored rows because no independent Q verifier exists. Corrected metrics reports `terminal_failures=1253` and `confirmatory_reuse_allowed=false`; all numbers are diagnostic-only.
- Correctly parameterized G7 trace/Q consistency rerun with the run root reports `0` state trace-integrity failures and `0` checkpoint trace-integrity failures; completed and terminal-failure evidence are retained. The first narrower-root run was discarded as a parameterization artifact, not used as evidence.
- Kimi G7 observed local worker-summary cost is USD `2.722796`; cumulative observed local G6+G7 cost is approximately USD `4.757124`, below the user ceiling. External billing, pricing, and immutable model snapshot/weight evidence remain unavailable.
- Full host suite passes `262/262`. Audit: `docs/audits/cycle-20261017T-kimi-k25-single-model-g0-g7/audit.json`. G0-G5 engineering gates remain as previously verified; formal G6/G7 and scientific release remain blocked.
- No scientific truth, superiority, causal, L/U, Q-validity, or formal statistical claim is made. Do not stage `runs/`, keys, `.env`, private labels/oracles, or `research_data_summary_G0_G7/`.
- This cycle's local audit/state commit must be pushed only with independent `git ls-remote` verification. If GitHub TCP/443 remains unreachable, report the exact local commit and failed push; never claim remote delivery.

