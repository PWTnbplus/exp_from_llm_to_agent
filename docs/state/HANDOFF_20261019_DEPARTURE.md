# 单模型科学发现项目离任交接（2026-10-19）

> 本文是给下一位维护者和审计者的完整交接材料。它以仓库中实际存在的代码、日志、审计 JSON、运行目录和 Git 证据为准；聊天消息中没有落盘、没有可复算日志支持的数字，不得当作实验结果。

## 0. 一页结论

### 当前项目状态

- 仓库：`E:\master_exp\nature_prj1_cal\from_llm_to_agent`
- 分支：`autopilot/scientific-law-discovery`
- 单模型约束：当前正式/恢复队列统一使用 `kimi-k2.5`；没有把不同基础模型或不同 G 组体系的结果合并进本轮单模型证据。
- 最新本地提交：`cb73b3fa871a8133f7eef1039fbede189593d437`，提交消息为 `add v9 targeted scientific recovery evidence`。
- 最新远端分支：已通过关闭本机代理的方式推送并以 `git ls-remote` 验证到同一 SHA。旧问题台账中的 GitHub BLOCKED 记录没有被静默改写，见第 7 节。
- `recovery_state.py bootstrap` 当前摘要：开放/未验证 10 项，已验证 29 项。
- 科学发布结论：`scientific_release_allowed=false`，状态为 `ENGINEERING_ADVANCED_SCIENTIFIC_RELEASE_BLOCKED`。

### 最重要的判断

工程执行已经明显推进，但科学发布条件没有诚实满足。下一位维护者不能因为新增调用、格式重试、公共数学 witness 对齐或局部因果对照成功，就把整个 G6/G7、Q 或 LU/U 宣布为科学通过。

仍然必须保持 BLOCKED 的核心原因是：

1. G6 的历史公开数学不一致没有被改写；v9 仍有不一致和未评分候选，且不能用私有受控 oracle 的结果冒充独立科学验证。
2. Q 的冻结 92 条队列已有独立重算，但缺少 domain-grade 的外部盲真值审阅；24/24 的补充校准不能替代冻结确认性分析。
3. LU/U 已经修复了一个真实的因果构造缺陷，并获得少量完整成对对照，但还没有形成可支持总体因果结论的独立验证集合。
4. G7 的 13 条历史生命周期错误必须永久保留；新重试有效不等于历史失败从分母中消失，也不等于形式门禁已经满足。
5. 供应商未提供可验证账单/用量导出，也未提供 immutable weight/route fingerprint。这是可追溯性问题，不得通过猜测路由或价格解决。

## 1. 离任时必须先读的文件

按顺序阅读：

1. `.agents/skills/scientific-law-recovery/SKILL.md`：V2 状态恢复、问题台账、证据和提交规则。
2. `AGENTS.md`：仓库级科学约束与启动顺序。
3. `docs/state/HANDOFF.md`：状态脚本维护的短交接摘要；本文件是更完整的离任补充。
4. `docs/state/issues.json`：问题状态的权威台账。
5. `docs/state/UNRESOLVED_REPORT.md`：由问题台账生成的未解决问题报告。
6. `docs/state/gates.json`：G0–G7 的门禁快照；注意它包含冻结/正式门禁指标，不能和附录恢复队列直接混为一个分母。
7. `docs/audits/cycle-20261019T-v9-targeted-recovery/audit.json`：本轮 v9 汇总审计。
8. `docs/audits/cycle-20261019T-v9-targeted-recovery/` 下的 G6、Q、LU/U 审计文件。
9. `docs/audits/cycle-20261018T-v4-g6g7-execution/EXECUTION_LOG.md`：V4 到后续恢复的追加执行日志。

不要先删改 `runs/`、`docs/audits/` 或 `research_data_summary_G0_G7/`。先完成只读盘点并建立新的审计目录；历史失败是科学分母和可追责链的一部分。

## 2. 按困难分级的未完成工作

这里的“困难”按解除科学发布门禁所需的独立性、外部依赖和修改风险排序，而不是按代码量排序。

### A 级：最困难、当前不能靠继续重跑同一模型解决

#### A1. G6：公开数学不一致与正式科学评分仍未闭合

当前事实：

- G6 正式历史队列包含 552 条规范化记录；CF3 相关历史重试/审阅队列为 138 条。
- 针对 43 条公开数学不一致，v8 已新增真实 `kimi-k2.5` 调用 54 次（含 11 次格式重试）；35 条结构有效，其中 19 条与公开数学 witness 对齐，16 条仍不一致，3 条候选存在格式/质量缺陷。历史 43 条没有改写。
- v9 又对 v8 选出的困难子集做了定向恢复：
  - r1：19 行、21 次尝试，5 条对齐、13 条不一致、1 条无候选/未评分；
  - r2：13 行、16 次尝试，3 条对齐、8 条不一致、2 条无候选/未评分；
  - r3：8 行、9 次尝试，0 条对齐、7 条不一致、1 条无候选/未评分。
- v9 的定向恢复没有删除或覆盖 v8 的历史结果，也没有把模型重新回答直接写成真值。
- 受控 oracle 的有效修订仍不能被解释为独立科学通过；公开数学 witness 只能作为独立可检查参照的一部分。

关键证据：

- `docs/audits/cycle-20261018T-v8-scientific-resolution/G6_PUBLIC_MISMATCH_AUDIT.json`
- `docs/audits/cycle-20261019T-v9-targeted-recovery/G6_TARGETED_RECOVERY_AUDIT.json`
- `docs/audits/cycle-20261019T-v9-targeted-recovery/G6_TARGETED_RECOVERY_R2_AUDIT.json`
- `docs/audits/cycle-20261019T-v9-targeted-recovery/G6_TARGETED_RECOVERY_R3_AUDIT.json`
- `runs/ctflow_single_model/20261019T-v9-targeted-recovery/g6/`
- `runs/ctflow_single_model/20261019T-v9-targeted-recovery/g6-r2/`
- `runs/ctflow_single_model/20261019T-v9-targeted-recovery/g6-r3/`

尚未完成：

1. 对剩余不一致逐条进行独立数学审阅：先固定公开命题、定义、witness、允许的等价变换和判定规则，再判定是模型错误、题目/格式缺陷、公开 witness 错误，还是证据不足。
2. 对无法独立判定的条目保持 `INCONCLUSIVE` 或 `NOT_SCORED`，不得强行二值化。
3. 明确 v8/v9 追加队列与冻结正式分母的关系；不能把恢复队列悄悄 pooled 进原确认性统计。
4. 在正式统计和独立审阅完成前，不得解除 G6 科学门禁。

停止条件：如果新的调用只是在同一提示下得到更多同样不一致的回答，应停止盲目重试，改做题目语义、公开证明和独立审阅；“调用次数增加”本身不是科学证据。

#### A2. Q：冻结 92 条确认性分析仍缺盲真值和领域审阅

当前事实：

- 冻结 Q-v2 队列为 92/92 样本完成。
- 原始运行记录位于：`runs/ctflow_single_model/20261018T-v5-qv2-kimi-format-retry/q_records.jsonl`。
- 运行统计为 103 次供应商调用，其中 11 次为可见格式重试；重试没有扩大冻结样本分母。
- 独立审计重算得到：`PASS=18`、`FAIL=8`、`INCONCLUSIVE=55`、`NOT_SCORED=11`，主比例 `18/92=19.57%`。
- 独立审阅脚本为 `scripts/audit_q_v2_frozen_public_reviewer.py`，使用独立 AST/SymPy 解析路径，不导入生产 Q verifier，也不读取私有 truth key。
- 审计结果：92 行、计数与上面一致；`domain_grade_review_complete=false`；`external_blinded_truth_available=false`。
- 后续补充校准队列曾新增 24 次真实 `kimi-k2.5` 调用并得到 24/24 `TRUTH_MATCH`，但这是补充盲真值校准，不得替换冻结 92 条，也不得把二者合并后宣称确认性通过。

关键证据：

- `docs/audits/cycle-20261019T-v9-targeted-recovery/Q_FROZEN_PUBLIC_REVIEW.json`
- `scripts/audit_q_v2_frozen_public_reviewer.py`
- `runs/ctflow_single_model/20261018T-v5-qv2-kimi-format-retry/`
- `docs/audits/cycle-20261019T-v9-targeted-recovery/audit.json`

尚未完成：

1. 为冻结 92 条建立预注册、外部或至少独立于生产解析器的 domain-grade 盲真值复核。
2. 固定真值生成时间、访问权限、哈希和审阅者身份，保证审阅者未通过提示或日志看到模型答案后再生成标签。
3. 完成确认性统计：明确估计量、区间、缺失/不可评分规则、多重比较和停止规则。
4. 将 24/24 校准作为补充证据单独报告，不能替换 92 条冻结队列。

#### A3. LU/U：已修复执行器根因，但总体因果证据仍不足

已发现并修复的真实根因：

- 旧 builder 把 intervention 写成裸公式（例如 `f(x)=x`），而 truth key 把它当成原命题的同一单调性判断，导致部分任务的干预语义与真值定义不一致，科学上不适合作为因果对照。
- `scripts/v3/build_lu_u_causal_cohort.py` 已改为保留同一显式命题并替换表达式，避免 intervention 只剩孤立公式。
- `scripts/v3/run_lu_u_causal_cohort.py` 已固定 `state_before=supported`，明确 weak nondecreasing/nonincreasing 语义，并记录 pairwise strict monotonicity 的端点限制；同时缩短 evidence，降低 JSON 截断风险。

当前 v9 固定队列事实：

- r4 队列：`runs/ctflow_single_model/20261019T-v9-targeted-recovery/lu-u-cohort-r4`
- r4 运行：`runs/ctflow_single_model/20261019T-v9-targeted-recovery/lu-u-run-r4`
- 12 次主供应商调用、12 条有效记录、12 条 trace。
- 审计：`docs/audits/cycle-20261019T-v9-targeted-recovery/LU_U_FIXED_COHORT_AUDIT.json`
- control：5 条 `TRUTH_MATCH`、1 条 `TRUTH_MISMATCH`。
- intervention：6 条 `TRUTH_MATCH`。
- 完整 `validated_causal_contrast=2`：`LUCT-004 identity_neg_to_pos` 与 `LUCT-005 zero_nondec_to_neg`。
- `LUCT-008 square_neg_to_pos` 仍因模型把严格导数语义解释错误而未通过。
- r5 只针对 LUCT-008 做了 2 次新增真实调用；control 仍 `TRUTH_MISMATCH`、intervention `TRUTH_MATCH`，没有新增完整因果对照。

更早失败/恢复记录必须保留：

- `LU_U_TARGETED_RECOVERY_AUDIT.json`
- `LU_U_TARGETED_RECOVERY_R2_AUDIT.json`
- `LU_U_TARGETED_RECOVERY_R3_AUDIT.json`

尚未完成：

1. 由独立真值和预注册因果判定规则完成足够数量的成对 control/intervention 对照。
2. 证明 state transition 是由 intervention 造成，而不是 prompt wording、解析偏差或本来就存在的状态差异造成。
3. 对 r4/r5 作为校准/修复证据与正式 LU/U 统计分开报告，不把 2 条有效对照外推为总体因果结论。
4. 对 `L` 的公开推导证据和 `U` 的真实模型状态转移证据分开：推导证明不等于模型执行造成的状态转移。

### B 级：工程上可继续推进，但必须保留失败历史

#### B1. G7 生命周期恢复和正式分母的分离

当前恢复证据：

- 新恢复/重试路径已达到 `150/150` 状态、`72/72` checkpoint、`13/13` 新重试有效。
- 13 条历史生命周期错误完整保留；新重试有效不允许 retroactively 清除历史失败。
- 旧正式门禁快照仍记录较大的冻结/历史队列：`gates.json` 中的形式指标包含 1288 计划、184 checkpoint、7 arms，以及历史状态缺口、trace defect、Q 不可评分和 L/U 边缺失等。该快照与附加恢复队列不是同一个分母。

当前主要问题：

- `ISSUE-7c2d4e9a10bf`：`IN_PROGRESS`，G7 revalidation 在 append-only retry recovery 后仍有 trace lifecycle inconsistencies。
- 必须保持两个视图：原始/历史生命周期视图显示 13 条错误及其他历史失败；新重试有效性视图显示新尝试达到的恢复情况。
- 任何改变正式分母、将补救尝试纳入确认性估计的动作都必须有 protocol-approved reanalysis，不能靠编辑 JSON 或重写 report 完成。

尚未完成：

1. 逐条核对 attempt、trace、checkpoint、state transition、terminal status 和 retry lineage。
2. 建立不可覆盖的 parent/child retry 关系和唯一 trace ID。
3. 用只读审计证明历史错误仍存在，且新状态只作为追加记录存在。
4. 重新判断形式 G7 门禁，不能用 `150/150` 的恢复子集替换正式门禁中的历史分母。

#### B2. 供应商账单、用量、权重/路由身份

已检查事实：

- `/models` 返回 HTTP 200，但没有 immutable fingerprint。
- `/usage`、`/billing`、`/account/usage` 均返回 404。
- 当前没有供应商可验证的账单/用量导出，也没有 immutable weight/route fingerprint。

尚未完成：

- 如果供应商或账户侧以后提供正式导出，应保存原始响应、获取时间、请求范围、哈希以及与本地调用记录的对账表。
- 不能靠本地的 `model` 字符串、请求 ID 或经验猜测证明权重/路由身份。
- 不能因为用户说“不用管价格”就伪造供应商账单；预算限制放宽不等于可验证性条件消失。
- 该问题主要影响可追溯性/发布门禁，不应阻塞已经可以在本地完成的数学审阅、Q 盲审和 LU/U 代码验证。

#### B3. GitHub/上游交付状态的台账滞后

本轮实际证据：

- 使用命令：`git -c http.proxy= -c https.proxy= push origin autopilot/scientific-law-discovery`
- 推送成功。
- 使用命令：`git -c http.proxy= -c https.proxy= ls-remote origin refs/heads/autopilot/scientific-law-discovery`
- 返回：`cb73b3fa871a8133f7eef1039fbede189593d437 refs/heads/autopilot/scientific-law-discovery`。
- 本地 HEAD 与远端 SHA 一致。

但 `issues.json` 仍有 `ISSUE-000000000003` 为 P1/BLOCKED，描述“Upstream provenance and GitHub delivery are externally blocked”。这属于台账与新证据暂未同步，不应静默删除或手工把问题标成 resolved。下一位维护者应：

1. 在新审计记录中附上 push 命令、远端 ref 和 SHA；
2. 复核该 issue 是否还涵盖 provenance 的其他未解决部分；
3. 只有在审阅者确认后更新问题状态；
4. 不要把“GitHub 分支可见”扩大解释成“科学来源、模型身份、真值和上游可验证性全部解决”。

### C 级：低难度但不能遗忘的剩余工程项

#### C1. 测试命令退出码异常

已运行：

```powershell
E:\resources\python\python.exe -X utf8 -m pytest -q tests/test_v4_q_lu.py tests/test_g7_protocol.py tests/test_g7_trace_q_consistency.py
```

输出内容显示 `87 passed`，嵌入式 `pytest.main` 返回值为 0，但外层执行工具报告 `exit_code:1`。这不是科学失败结论，但属于可复现性问题。下一位维护者应在干净 PowerShell、无 conda 自动激活干扰的环境中复核真实退出码、编码/初始化脚本、pytest plugin 或 shell wrapper 是否在测试后改变退出码。

在复核前只能准确写“87 passed；内部 pytest 返回 0；外层退出码异常”，不能写成“宿主测试完全 PASS”。

#### C2. 旧问题台账和新证据的同步

`recovery_state.py bootstrap` 当前报告 10 项开放/未验证、29 项已验证。任何状态更改都必须引用具体审计文件和审阅者结论。特别注意：

- `UNRESOLVED_REPORT.md` 是由台账生成的，不是独立真值源；
- 不能只改 `issues.json`、`gates.json` 或 `HANDOFF.md` 来制造完成状态；
- 新增实验必须先落盘 raw records、manifest、audit，再更新台账。

## 3. 当前问题台账逐项交接

以下是启动时看到的主要开放/未验证问题。状态以 `docs/state/issues.json` 为准；若后来有新的提交，应先重新运行 bootstrap 再核对。

| Issue | 优先级/状态 | 当前含义 | 解除所需证据 |
|---|---|---|---|
| `ISSUE-7c2d4e9a10bf` | P1 / `IN_PROGRESS` | G7 append-only retry 后 trace lifecycle 仍需重新核验 | parent/child retry lineage、历史 13 条保留、新旧分母分离、protocol-approved reanalysis |
| `ISSUE-000000000002` | P1 / `BLOCKED` | 供应商账单/用量和 immutable route/weight identity 未验证 | 供应商可验证导出和不可变身份；不能本地猜测 |
| `ISSUE-000000000003` | P1 / `BLOCKED` | 台账认为上游/GitHub 交付受阻，但最新 push/ls-remote 已成功 | 新审计确认远端 SHA，并拆分剩余 provenance 问题后再改状态 |
| `ISSUE-000000000004` | P1 / `BLOCKED` | 正式统计有效性未建立 | 冻结 92 条的独立 domain-grade blind review、预注册统计和缺失规则 |
| `ISSUE-ff97c7c89112` | P1 / `RESOLVED_UNVERIFIED` | G6 公开数学不一致相关审计证据尚需独立验证 | 逐条公开 witness 审阅，保留历史不一致；不能只看公共 verifier PASS |
| `ISSUE-ad61f025976a` | P1 / `RESOLVED_UNVERIFIED` | 模型 snapshot / positive pricing 等可验证供应商信息不足 | 供应商原始证据、immutable identity、用量/计费对账 |
| `ISSUE-1f8c2b6a4d90` | P1 / `BLOCKED` | LU/U 正式因果验证未建立 | 独立真值、预注册成对 intervention、真实状态转移和可审计因果判定 |
| `ISSUE-3d7a9c1e5b20` | P1 / `BLOCKED` | G7 provider execution terminal failures / Q 覆盖仍影响正式门禁 | 先保持历史失败，完成正式协议允许的恢复和重新分析 |
| `ISSUE-f9171bb760b1` | P1 / `RESOLVED_UNVERIFIED` | G8 real/sham/off/extra adapter 仍不是当前单模型科学发布主证据 | 若项目仍要求 G8，必须另行按协议建立真实/伪/关闭/额外 adapter 证据；不能把 G6/G7 结果代替 G8 |
| `ISSUE-000000000005` | P2 / `OPEN` | classical baseline extension 尚未完成 | 按协议实现并独立测试；不应阻塞先解决的 P1 科学门禁 |

## 4. G0–G7 门禁现状及解释

`docs/state/gates.json` 是门禁快照。以下解释尤其重要：通过通常只是工程或 evaluator 级别通过，不等于科学发布通过。

| 门禁 | 快照状态 | 可以说明什么 | 不能说明什么 |
|---|---|---|---|
| G0 | PASS | 具备科学 provenance/运行框架的部分工程条件 | 官方 numeric evaluator、模型身份、独立真值和发布资格已完成 |
| G1 | PASS | 协议/任务结构的工程检查通过 | 历史正式覆盖与科学结论已通过 |
| G2 | PASS | 对照结构或执行框架存在 | 不足以支持 superiority claim |
| G3 | PASS | 部分 G6 trace 修复/运行可执行 | provider、统计和独立数学接受条件全部满足 |
| G4 | PASS | evaluator 层检查通过 | 领域科学复核通过 |
| G5 | PASS | smoke/engineering checks 以及部分依赖检查可运行 | 0 dependency edges、正式 U 因果结论或完整科学发布 |
| G6 | BLOCKED | 有历史记录和追加恢复证据可审计 | 公开数学不一致、正式统计和供应商可验证性仍未闭合 |
| G7 | BLOCKED | 追加恢复已验证一部分状态/checkpoint/retry | 不能用 150/150 子集覆盖历史正式分母，也不能忽略 13 条生命周期错误 |

`gates.json` 中的冻结正式 G7 数字（例如 1288 计划、184 checkpoint、7 arms、历史状态缺口和 trace defects）必须和后来的 150/150 恢复子集分开呈现。它们是不同的视图，不能直接相加或互相替换。

## 5. 已完成或已核验的工作：不要无证据重做

以下工作已有代码、日志、审计或提交支撑，除非出现回归，不要重新从头构建：

1. 单模型当前实验约束和 `kimi-k2.5` 调用路径已建立。
2. G6/G7 协议、runner、审计和基础测试已经存在。
3. G7 追加恢复已完成 150/150 state、72/72 checkpoint、13/13 新重试有效；13 条历史生命周期错误已保留。
4. Q-v2 92 条冻结队列已经执行，格式重试和独立重算已落盘。
5. Q 独立 reviewer 已实现，且不读取私有 truth key、不复用生产 verifier。
6. Q 的 24/24 补充盲真值校准已作为 supplementary evidence 保留，未替换冻结 92。
7. LU/U builder 和 runner 的真实语义缺陷已修复；r4/r5 及更早失败审计均已保留。
8. G6 v8 的 43 条公开不一致恢复和 v9 r1/r2/r3 定向恢复已执行，历史结果未覆盖。
9. v9 汇总审计和执行日志已提交。
10. 最新提交已推送并通过 `ls-remote` 验证；不能继续声称“本机代理导致 GitHub 一律不可用”，但仍要区分远端可见性和科学 provenance。

## 6. 关键代码、数据和审计索引

### 代码

- `scripts/recovery_state.py`：状态 bootstrap、问题台账和下一问题选择。
- `scripts/audit_q_v2_frozen_public_reviewer.py`：Q-v2 独立公开 reviewer。
- `scripts/v3/build_lu_u_causal_cohort.py`：LU/U 因果队列构建，已修复 intervention 语义。
- `scripts/v3/run_lu_u_causal_cohort.py`：LU/U 运行器，已固定 state/单调性语义和紧凑 evidence。
- `scripts/v3/run_g6_public_mismatch_review.py`：G6 公开不一致定向恢复 runner。
- `scripts/audit_g6_public_mismatch_review.py`：G6 定向恢复审计。
- `scripts/audit_lu_u_causal_cohort.py`：LU/U 队列独立审计。

### v9 审计

- `docs/audits/cycle-20261019T-v9-targeted-recovery/audit.json`
- `docs/audits/cycle-20261019T-v9-targeted-recovery/G6_TARGETED_RECOVERY_AUDIT.json`
- `docs/audits/cycle-20261019T-v9-targeted-recovery/G6_TARGETED_RECOVERY_R2_AUDIT.json`
- `docs/audits/cycle-20261019T-v9-targeted-recovery/G6_TARGETED_RECOVERY_R3_AUDIT.json`
- `docs/audits/cycle-20261019T-v9-targeted-recovery/Q_FROZEN_PUBLIC_REVIEW.json`
- `docs/audits/cycle-20261019T-v9-targeted-recovery/LU_U_FIXED_COHORT_AUDIT.json`
- `docs/audits/cycle-20261019T-v9-targeted-recovery/LU_U_FIXED_COHORT_R5_AUDIT.json`

### v8、V4 和执行日志

- `docs/audits/cycle-20261018T-v8-scientific-resolution/G6_PUBLIC_MISMATCH_AUDIT.json`
- `docs/audits/cycle-20261018T-v4-g6g7-execution/EXECUTION_LOG.md`
- `docs/state/issues.json`
- `docs/state/UNRESOLVED_REPORT.md`
- `docs/state/gates.json`

### 运行目录

运行目录通常被 Git 忽略，必须在本机保留并在审计中引用，不能仅依赖提交后的代码：

- `runs/ctflow_single_model/20261018T-v5-qv2-kimi-format-retry/`
- `runs/ctflow_single_model/20261019T-v9-targeted-recovery/g6/`
- `runs/ctflow_single_model/20261019T-v9-targeted-recovery/g6-r2/`
- `runs/ctflow_single_model/20261019T-v9-targeted-recovery/g6-r3/`
- `runs/ctflow_single_model/20261019T-v9-targeted-recovery/lu-u-cohort-r4/`
- `runs/ctflow_single_model/20261019T-v9-targeted-recovery/lu-u-run-r4/`
- 对应的 v8 Q/LU/G6 运行目录。

交接时发现的未跟踪用户工件必须保留，不能清理：

- `docs/audits/cycle-20261018T-v4-g6g7-execution/LU_V2_PROOFS_ALL/`
- `docs/audits/cycle-20261018T-v4-g6g7-execution/LU_V2_PUBLIC_GRAPHS_ALL.jsonl`
- `docs/audits/cycle-20261018T-v4-g6g7-execution/LU_V2_PUBLIC_GRAPHS_ALL_MANIFEST.json`
- `research_data_summary_G0_G7/`

## 7. 推荐的下一轮执行顺序

### 第一步：启动和只读基线

```powershell
Set-Location E:\master_exp\nature_prj1_cal\from_llm_to_agent
git status --porcelain=v1
git remote -v
git branch --show-current
git log -8 --oneline
E:\resources\python\python.exe -X utf8 scripts/recovery_state.py bootstrap
```

然后重新读取 `docs/state/HANDOFF.md`、本文件、`issues.json`、`UNRESOLVED_REPORT.md` 和 `gates.json`。先确认运行目录和未跟踪工件仍在。

### 第二步：优先完成独立性，而不是继续无信息重试

建议顺序：

1. G6 剩余不一致：建立逐行数学审阅表，明确公开 witness 和可复核推导；只有审阅规则固定后才决定是否追加调用。
2. Q：为冻结 92 条获取独立盲真值/domain-grade review，并预注册统计；24/24 校准单独报告。
3. LU/U：用修复后的 builder/runner 构造正式成对设计，增加独立可验证的状态转移，不把 r4 的 2 条当总体证据。
4. G7：逐条做生命周期 lineage review，保持历史 13 条；如要改变正式分母，先得到协议批准的重新分析。
5. 供应商证据：在供应商真实提供原始导出后再对账；没有导出就保持未验证。
6. 最后再处理低风险的台账同步、测试退出码和 P2 baseline。

### 第三步：每个实验循环的最低落盘要求

每次新增调用都必须同时留下：

- frozen cohort/manifest 和输入哈希；
- 原始 provider response、请求 ID、时间和模型字段；
- 格式重试与主调用的 parent/child 关系；
- 独立审计脚本和审计输出；
- 失败、未评分和不一致的逐条原因；
- 运行命令、Python 解释器、代码 commit SHA；
- 是否改变正式分母的明确声明；
- reviewer 的只读复核结果。

## 8. 可复现验证命令

### 状态和文件检查

```powershell
E:\resources\python\python.exe -X utf8 scripts/recovery_state.py bootstrap
E:\resources\python\python.exe -X utf8 scripts/recovery_state.py next
git diff --check
git status --short
```

### 独立 Q reviewer

先阅读脚本的参数说明，然后按脚本当前接口运行，不要手写或修改真值文件。预期应能复现 92 行及 `18/8/55/11` 的独立计数，并保持 `domain_grade_review_complete=false`。

```powershell
E:\resources\python\python.exe -X utf8 scripts/audit_q_v2_frozen_public_reviewer.py --help
```

### LU/U 审计

```powershell
E:\resources\python\python.exe -X utf8 scripts/audit_lu_u_causal_cohort.py --help
```

按 r4/r5 目录的 manifest 和脚本接口复核；不要把审计输出直接写回 frozen truth。

### G6 审计

```powershell
E:\resources\python\python.exe -X utf8 scripts/audit_g6_public_mismatch_review.py --help
```

按 r1/r2/r3 的 manifest 逐个复核，检查历史 43 行是否仍在、定向恢复是否仅追加。

### 当前重点测试

```powershell
E:\resources\python\python.exe -X utf8 -m pytest -q tests/test_v4_q_lu.py tests/test_g7_protocol.py tests/test_g7_trace_q_consistency.py
```

当前已有结果是 `87 passed`，但外层工具曾报告异常 `exit_code:1`；下一位必须重新确认真实 shell 退出码后再把它写成完整 PASS。

### 提交和远端验证

```powershell
git diff --check
git status --short
git add <仅限本轮代码、审计和交接文件>
git commit -m "<描述本轮真实证据>"
git -c http.proxy= -c https.proxy= push origin autopilot/scientific-law-discovery
git -c http.proxy= -c https.proxy= ls-remote origin refs/heads/autopilot/scientific-law-discovery
```

不要 `git add .`，因为上述未跟踪用户工件不应被无意纳入提交；也不要 force push、merge main 或把本地 SHA 当作远端 SHA。

## 9. 明确禁止的做法

1. 只修改 `issues.json`、`gates.json`、`HANDOFF.md` 或生成报告，然后宣称任务完成。
2. 删除、覆盖、重命名历史 13 条 G7 生命周期错误，或把新重试直接替换原始记录。
3. 把公共 verifier PASS、模型自我修订、公开 witness 对齐或 24/24 补充校准称为完整科学验证。
4. 把冻结 Q 92 条与后续校准/恢复队列 pooled 后改变确认性分母。
5. 把 L 的公开推导证据伪装成 U 的真实模型状态转移，或把少量 LU/U 成功对照外推成因果总体结论。
6. 混用不同基础模型、不同路由的结果，或在没有 immutable route/weight fingerprint 时猜测模型身份。
7. 伪造供应商账单、用量、价格、权重或路由证据；用户放宽额度不等于供应商提供了验证材料。
8. 为了解除门禁泄漏私有 truth key、hidden law、评测答案或未公开真值。
9. 因本地工程门禁通过而宣称科学发布；工程状态与科学状态必须分开。
10. 因一次审计没有再次提到某问题就把问题当作已修复；问题台账和历史审计是 append-only 的证据链。

## 10. 科学发布最终验收清单

下一位维护者只有在以下各项都有可审计证据时，才可以重新评估发布门禁；目前全部条件尚未满足：

- [ ] G6 每条历史不一致都有独立数学判定、公开 witness/推导和可复查分类。
- [ ] G6 追加恢复与冻结正式分母关系已获协议批准并记录。
- [ ] Q 冻结 92 条获得独立盲真值/domain-grade review。
- [ ] Q 统计分析预注册、缺失处理、区间和多重比较规则已完成。
- [ ] LU/U 的 control/intervention 成对设计由独立真值支持，并有足够真实状态转移。
- [ ] L 的推导证据与 U 的因果证据分开归档。
- [ ] G7 13 条历史生命周期错误仍在原始视图中，且 retry lineage 可审计。
- [ ] G7 正式分母的任何变化都有协议批准的重新分析。
- [ ] 所有正式调用都能关联到单一基础模型、代码 SHA、请求记录和原始响应。
- [ ] 供应商用量/账单和 immutable route/weight identity 已获得可验证原始证据，或明确将其作为不可解除的发布条件。
- [ ] 所有历史失败、格式失败、未评分和 inconclusive 记录均保留。
- [ ] 独立 reviewer、工程测试和 Git 远端交付均可复现。
- [ ] `scientific_release_allowed` 只有在上述条件都满足后才可改变。

## 11. 离任交接签收建议

接手者应在第一轮工作结束时回填以下信息，而不是直接覆盖本文件：

```text
接手日期：
接手人/审阅者：
起始 commit SHA：
起始远端 SHA：
bootstrap 摘要：
未跟踪用户工件是否仍完整：
首先处理的 issue：
新增实验/调用数量：
新增失败或未评分数量：
是否改变任何正式分母：
独立审计输出路径：
测试命令与真实退出码：
提交 SHA 与远端验证结果：
科学发布状态：
```

本交接的最终结论仍是：**工程执行已推进到可继续恢复和审阅，但科学发布门禁必须保持 BLOCKED；下一步的价值在独立验证、因果设计和历史可追溯性，而不是把状态文件改成绿色。**
