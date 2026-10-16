# G0–G7 修复与完善交接文档

生成日期：2026-10-16（Asia/Hong_Kong）  
仓库：`E:/master_exp/nature_prj1_cal/from_llm_to_agent`  
分支：`autopilot/scientific-law-discovery`  
最新已提交版本：`ba7e3f8 Finalize cycle 52 handoff`；cycle 51 Q-validity semantic repair is committed as `52aee13`
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

本交接文档不是 PASS 证明。`issues.json`、审计 JSON、冻结 plan/hash、独立复核和回归测试才是后续 Agent 可使用的证据。

