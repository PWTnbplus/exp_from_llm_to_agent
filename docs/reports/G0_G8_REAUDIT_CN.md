# G0–G8 全量复核与修复附录

本附录记录 2026-10-15 recovery cycle 的只读全量审计、G7 独立终止重试和协议修复。它不把工程审计通过改写成科学结论。

## 核心结果

| 模块 | 复核/运行对象 | 计划/输入 | 完成或审计结果 | 当前解释 |
|---|---:|---:|---:|---|
| G0–G5 | 已持久化 pilot、engineering、smoke、theory 工件 | 55 个 JSON 工件 | mock 标记只出现在 theory/theory_agent_smoke 教学工件各 1 个 | 未把 smoke/mock 当正式科学结果 |
| G6 | corrected 23-family release | 552 plan / 552 response / 552 handoff；2 workers | release structural review PASS；scientific_release_allowed=false | 保留数学、provider、snapshot、billing 外部门禁 |
| G7 原始 | formal-20261014T030000Z-16workers | 1288 fork；184 checkpoint | 993 completed；217 checkpoint_missing；78 provider_error；Q valid 3/1288；edge_count=0/92；eligible_U=0；MODEL_REQUEST 中 routing metadata 各命中 2960 次 | 原始结果不可变；prompt 隔离门禁失败，不得作确认性结论 |
| G7 retry1 | formal-20261015T060000Z-terminal-retry | 仅原始 295 个 terminal fork；81 source checkpoint；16 workers | 185 completed；90 checkpoint_missing；20 provider_error；Q valid 2/295 | 单独冻结、不可与原始 G7 合并 |
| G7 retry2 | formal-20261015T073000Z-terminal-retry2 | retry1 中 110 个 terminal fork；32 source checkpoint；2 workers | 规范状态 102/110：79 completed；20 checkpoint_missing；3 provider_error；另有 8 missing state；Q valid 0/110 | 未完成项已单独进入 retry3；retry2 不与前轮 pooling |
| G7 retry3 | formal-20261015T080000Z-terminal-retry3 | retry2 中 31 个 terminal/missing-state fork；14 source checkpoint；4 workers | 16 completed；12 checkpoint_missing；3 provider_error；Q valid 0/31 | 已规范合并；仍有终端失败，不与前轮 pooling |
| G8 | formal-20261015T030000Z-16workers | 324 plan / 324 result | execution PASS 284、TECHNICAL_FAILURE 40；独立结构审计 324/324 PASS；private_oracle_loaded=false | 只支持结构完整性，不能自动形成因果结论 |

## G7 retry 资源

| 指标 | 数值 |
|---|---:|
| retry1 model calls / tool calls | 646 / 535 |
| retry1 total tokens / observed cost | 1,385,282 / USD 2.266946 |
| retry2 model calls / tool calls | 276 / 196 |
| retry2 total tokens / observed cost | 601,606 / USD 1.006640 |
| retry3 model calls / tool calls | 68 / 61 |
| retry3 total tokens / observed cost | 156,629 / USD 0.271911 |
| retry plan SHA256 | `1e35cc087d72ed857e4b60eaab9c75e5f47adc1ac4f1500c56c9ee5fecef3c0e` |
| source plan SHA256 | `549c39a9508fae3c7611564f0cca6022ade5dda67f52d8cc6c1fbd51b9633eb3` |
| source states SHA256 | `714e53654e070a74bc026c11c7396fc243b8e4b72a45e3ed4e9025d8fe66efef` |

## 本轮修复

| 修复项 | 证据 | 状态 |
|---|---|---|
| G7 model-facing prompt 删除 `cf_type`、`theory_family_id` | `scripts/run_g7_failure_localization.py::case_prompt`；`tests/test_g7_protocol.py` | 已修复并回归通过 |
| 原始 G7 prompt 泄漏诊断 | `scripts/audit_g7_failure_taxonomy.py`；`docs/reports/G7_FAILURE_DIAGNOSIS_CN.md`；cycle-20261015T051500Z-25 | 已确认；原始数据不可逆修复，保留为 P1 未解决门禁 |
| G7 terminal retry 独立冻结与 source 映射 | `scripts/build_g7_terminal_retry.py`、`retry_manifest.json`、`g7_merge_manifest.json` | 已完成；禁止静默 pooling |
| G0–G8 lineage / 私有 oracle / 计划完整性审计 | `scripts/audit_g0_g8_integrity.py`、`docs/audits/cycle-20261015T080000Z-24/audit.json` | 已完成；包含 retry1–retry3 链路 |

## 尚未解除的门禁

| 问题 | 保留原因 |
|---|---|
| G7 provider/Q | retry1–retry3 仍有 terminal failures（90/295、23/110、15/31）；Q valid 分别为 2/295、0/110、0/31；不能宣称已修复 |
| G7 原始 prompt 隔离 | 原始 MODEL_REQUEST 含 `cf_type`、`theory_family_id` 各 2960 次；只能排除原始 run，不能从历史 trace 删除 |
| G7 L/U | 92/92 proof graph 无 dependency edge，U eligible=0；没有独立替代边数据 |
| G6/G8 provider 真实性 | 无 immutable gateway weight fingerprint 与外部 billing receipt |
| G5 数学审查、统计审查、upstream provenance | 仍需外部/独立审查或网络凭据，不能由本地 pytest 代替 |

## 协议修正版 G7 全量结果

| 指标 | 结果 |
|---|---:|
| plan / checkpoint | 1288 / 184 |
| canonical states | 1288/1288（1285 completed，3 provider_error） |
| canonical checkpoints | 184/184 completed |
| 独立 Q 有效 | 20/1288 |
| 格式重试事件 / 请求 | 302 / 302 |
| routing metadata / private-key prompt 命中 | 0 / 0 |

该运行是独立的 frozen retry，未与原始 G7 pooling；原始 G7 的 2960 次 `cf_type` 和 2960 次 `theory_family_id` 命中保持不可变并继续作为 P1 隔离问题。3 条 provider_error、低 Q 有效覆盖、G7 L/U 图结构限制，以及 G6/G8 外部凭据限制均保留。

新增审计：`docs/audits/cycle-20261015T081700Z-27/g0_g8_integrity.json`、`docs/audits/cycle-20261015T081700Z-27/g7_failure_taxonomy.json`。
