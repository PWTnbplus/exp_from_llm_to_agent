# G8 受控机制因果实验报告（中文）

> 报告状态：`BLOCKED_G7_HANDOFF`
>
> 数据截点：2026-10-15（Asia/Hong_Kong）。本报告严格区分“门禁审计完成”和“真实 G8 实验已执行”。当前只完成 G8 工具包审阅、输入审计和阻断证据固化，未把 demo 或 G7 诊断结果冒充 G8 因果实验。

## 1. G8 的科学问题与实验设计

G8 要检验的是：在相同模型、公开任务、工具权限和硬预算下，执行一个由 G7 冻结并审核的工作流机制 `M`，是否对最终可信改判产生独立因果贡献，并能否解释部分 G4 相对 G3 的优势。

正式六臂设计应为：

| 实验臂 | 含义 |
|---|---|
| `A_G3_BASE` | G3，不启用机制 M |
| `B_G3_REAL_M` | G3，真实执行 M |
| `C_G3_SHAM_M` | G3，执行格式匹配但语义无关的 sham M |
| `D_G3_EXTRA_THINK` | G3，使用预定额外计算作为计算量对照 |
| `E_G4_BASE` | 原 G4 完整 workflow；若历史 G4 不含 M，则必须改名为 `E_G4_PLUS_M` |
| `F_G4_NO_M` | 在执行层真正关闭 M；若历史 G4 不含 M，则必须改名为 `F_G4_MINUS_M` |

预注册主比较是 `B−A`、`B−C`、`B−D` 和合法的 `E−F`。统计独立单位是 `theory_family_id`，而不是 worker 数、任务行数或 API 调用数。

## 2. G7→G8 输入门禁结果

实际使用的 G7 根目录为：

`results/g7_failure_localization/formal-20261014T030000Z-16workers`

| 门禁指标 | 实际值 | G8 要求 | 结论 |
|---|---:|---|---|
| G7 public cases | 92 | 必须来自真实公共任务 | 结构上满足 |
| theory families | 23 | 独立理论族 | 已记录 |
| G6/G7 handoff rows | 552 | 必须有真实 checkpoint/trace | 有，但证据仍需外部复核 |
| demo/mock 输入 | `false` | 必须为 false | 通过结构检查 |
| G7 handoff selection | `REQUIRES_EXTERNAL_TRACE_AND_SCIENTIFIC_REVIEW` | 必须为 `GO` | **不通过** |
| G7 候选机制数 | 0 | 首次 G8 必须冻结 1 个 | **不通过** |
| G7 evidence status | `IMPORTED_REQUIRE_CHECKPOINT_PROVIDER_ORACLE_TRACE_AUDIT` | 需要真实 trace/科学复核状态 | **不通过** |
| dependency edge 分布 | `{0: 92}` | L/U 需要可审计图/状态边 | L/U 当前不具备资格 |
| U eligible cases | 0 | U 必须有中间状态转移 | 当前不可执行 |

关键文件：

- `g8_handoff.json`：`mechanisms=[]`，没有自动选择机制。
- `g7_input_audit_final.json`：92 cases、23 families、552 handoff rows、无 mock/demo，但明确要求外部数学和 trace review。
- `g7_vlu_oracle_audit.json`：`edge_count_distribution={"0":92}`、`eligible_u_cases=0`。
- `g7_score_report.json`：G7 诊断结果只可作为候选线索，不能直接当作 G8 的可执行机制证明。

## 3. G7 数据质量对 G8 的影响

G7 canonical 运行包含 1288 个 fork 计划行和 184 个 checkpoint 计划行：

| 指标 | 数量 | 比例 |
|---|---:|---:|
| fork planned/provided | 1288/1288 | 100% |
| fork completed | 993 | 77.096% |
| fork terminal failures | 295 | 22.904% |
| checkpoint planned/provided | 184/184 | 100% |
| checkpoint completed | 153 | 83.152% |
| independent Q rows | 1288 | 100% 保留 |
| Q valid | 3 | 0.233% |
| Q invalid | 1285 | 99.767% |

这些失败和无效 Q 记录不能删除、插补或重标记。G8 skill 明确要求：在 G7 provider failure、Q 审计和外部数学/trace 复核未完成前，不得把 G7 候选升级为 G8 的确认性机制。

G7 的诊断指标也不能直接证明 G8 机制：

- `V_ONLY`、`L_ONLY`、`U_ONLY` 是局部信息干预或诊断条件，不等于真实执行层的 `M_real`。
- 当前无独立依赖边，不能凭空实现可信的 L 或 U。
- `G7` 的 `D1–D3` 是给模型额外局部信息的诊断上界，不是 G8 的机制开关实验。

## 4. G8 工具包审计

使用的 skill ZIP：

`D:\硕士\prj1_ai_cal\exp\exp1_from_llm_to_agent\prompt\G8_Causal_Mechanism_Skill.zip`

SHA-256：

`4086360f393b8b3232ec700105a87738246438a16e4e97daad1de8a5e3a09bb2`

已完整读取：

- `SKILL.md`
- `references/01_实验科学问题与6臂矩阵.md`
- `references/02_G7输入审计与变量冻结.md`
- `references/03_机制开关实现与真实性核验.md`
- `references/04_16workers并行调度与预算控制.md`
- `references/05_指标统计与论文证据.md`
- `references/06_G9交接与门禁.md`

工具检查结果：

| 检查 | 结果 |
|---|---|
| G8 doctor | PASS |
| G8 package tests | 8/8 PASS |
| 私有字段检查 | PASS |
| budget violation 检查 | PASS |
| 六臂结构检查 | PASS |
| family cluster bootstrap 检查 | PASS |
| demo pipeline | 仅用于接口回归，不计入科学数据 |
| 真实 G7 输入 audit | 正确阻断：`G7 handoff not GO` |

测试期间发现 skill 工具在 Windows 下用 POSIX `shlex.split` 解析带反斜杠的 Python adapter 路径，会导致 demo 回归测试误报失败。该问题已在临时 skill 审阅副本中修复为 Windows 原生解析并复测 8/8；原始 ZIP 未被修改，也未将 demo 结果用于科学结论。

## 5. 为什么没有启动真实 G8

当前不能合法生成 G8 run plan，更不能启动 16 workers 或付费 provider，原因是三个硬门禁同时未通过：

1. G7 没有人工科学复核后的 `selection=GO`，且 `mechanisms=[]`；G8 不允许自动选择 L。
2. G7 依赖边全部为零，L/U 的执行合同缺少可审计输入；V 也仍需要真实外部校验 trace，不能从模型自报或最终答案推断。
3. 项目中没有已冻结并审计的 G8 `M_real/M_sham/M_off/generic_extra_thinking` adapter。G8 配置仍包含 placeholder model snapshot，不能作为真实实验配置。

因此本轮 G8 的真实实验计数为：

| 指标 | 值 |
|---|---:|
| G8 planned rows | 0 |
| G8 completed rows | 0 |
| G8 six-arm runs | 0 |
| G8 paid provider calls | 0 |
| G8 causal score | 不存在 |
| G8 GO/REVISE/STOP causal verdict | 不适用；当前为 pre-run BLOCKED |

这里的 0 是“尚未获准进入真实 G8”的门禁结果，不是零效应、负效应或实验失败率。

## 6. 进入 G8 所需的下一步

必须先完成并留存以下证据，才能重新执行 G8：

1. 对 G7 真实 provider trace、初稿 checkpoint、局部 oracle、Q audit 和数学 provenance 做独立人工科学复核，并将 `g8_handoff.json` 升级为 `selection=GO`。
2. 选择一个且仅一个首个机制，写清 `mechanism_id`、failure mode、支持案例、反例、操作定义、falsification、source hashes 和 verifier hashes。
3. 若选择 L/U，提供独立审计的依赖边或 versioned intermediate-state transition；不能从当前 `{0:92}` 推造边。
4. 实现并审计真实 G8 adapter：四种实际路径 `M_real/M_sham/M_off/generic_extra_thinking`，包括 `MECHANISM_INVOKED`、`SHAM_MECHANISM_INVOKED`、`MECHANISM_DISABLED`、`EXTRA_THINK_APPLIED` 事件，以及每次 provider/tool call 前的硬预算检查。
5. 冻结真实 model snapshot、G3/G4 workflow、tool whitelist、public checkpoint、私有 oracle 隔离、seed、RPS/TPM、重试规则和费用上限。
6. 先运行 4 theory families × 2 CF × 6 arms × 1 replicate = 48 行 pilot；只有 pilot、adapter trace 和独立审计通过后，才能重新评估正式设计。

## 7. 审计产物

- `docs/audits/cycle-20261015T000000Z-21/audit.json`
- `results/g7_failure_localization/formal-20261014T030000Z-16workers/g8_handoff.json`
- `results/g7_failure_localization/formal-20261014T030000Z-16workers/g7_input_audit_final.json`
- `results/g7_failure_localization/formal-20261014T030000Z-16workers/g7_score_report.json`
- `results/g7_failure_localization/formal-20261014T030000Z-16workers/g7_vlu_oracle_audit.json`

最终判定：**G8 真实因果机制实验未执行，且按 skill 门禁必须保持 BLOCKED；继续启动会违反 G8 的 G7 选择、科学审计和真实 adapter 规范。**
