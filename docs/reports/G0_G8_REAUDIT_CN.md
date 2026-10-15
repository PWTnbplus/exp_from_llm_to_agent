# G0–G8 全量复核与修复附录

本附录记录 2026-10-15 recovery cycle 的只读全量审计、G7 独立终止重试和协议修复。它不把工程审计通过改写成科学结论。

## 核心结果

| 模块 | 复核/运行对象 | 计划/输入 | 完成或审计结果 | 当前解释 |
|---|---:|---:|---:|---|
| G0–G5 | 已持久化 pilot、engineering、smoke、theory 工件 | 55 个 JSON 工件 | mock 标记只出现在 theory/theory_agent_smoke 教学工件各 1 个 | 未把 smoke/mock 当正式科学结果 |
| G6 | corrected 23-family release | 552 plan / 552 response / 552 handoff；2 workers | release structural review PASS；scientific_release_allowed=false | 保留数学、provider、snapshot、billing 外部门禁 |
| G7 原始 | formal-20261014T030000Z-16workers | 1288 fork；184 checkpoint | 993 completed；217 checkpoint_missing；78 provider_error；Q valid 3/1288；edge_count=0/92；eligible_U=0 | 原始结果不可变；不得作 L/U 机制确认 |
| G7 retry | formal-20261015T060000Z-terminal-retry | 仅原始 295 个 terminal fork；81 source checkpoint；16 workers | 185 completed；90 checkpoint_missing；20 provider_error；Q valid 2/295 | 单独冻结、不可与原始 G7 合并；未解决 Q/执行门禁 |
| G8 | formal-20261015T030000Z-16workers | 324 plan / 324 result | execution PASS 284、TECHNICAL_FAILURE 40；独立结构审计 324/324 PASS；private_oracle_loaded=false | 只支持结构完整性，不能自动形成因果结论 |

## G7 retry 资源

| 指标 | 数值 |
|---|---:|
| model calls | 646 |
| tool calls | 535 |
| total tokens | 1,385,282 |
| observed provider cost | USD 2.266946 |
| retry plan SHA256 | `1e35cc087d72ed857e4b60eaab9c75e5f47adc1ac4f1500c56c9ee5fecef3c0e` |
| source plan SHA256 | `549c39a9508fae3c7611564f0cca6022ade5dda67f52d8cc6c1fbd51b9633eb3` |
| source states SHA256 | `714e53654e070a74bc026c11c7396fc243b8e4b72a45e3ed4e9025d8fe66efef` |

## 本轮修复

| 修复项 | 证据 | 状态 |
|---|---|---|
| G7 model-facing prompt 删除 `cf_type`、`theory_family_id` | `scripts/run_g7_failure_localization.py::case_prompt`；`tests/test_g7_protocol.py` | 已修复并回归通过 |
| G7 terminal retry 独立冻结与 source 映射 | `scripts/build_g7_terminal_retry.py`、`retry_manifest.json`、`g7_merge_manifest.json` | 已完成；禁止静默 pooling |
| G0–G8 lineage / 私有 oracle / 计划完整性审计 | `scripts/audit_g0_g8_integrity.py`、`docs/audits/cycle-20261015T060000Z-23/audit.json` | 已完成 |

## 尚未解除的门禁

| 问题 | 保留原因 |
|---|---|
| G7 provider/Q | retry 后仍有 terminal failures，且 Q valid 仅 2/295；不能宣称已修复 |
| G7 L/U | 92/92 proof graph 无 dependency edge，U eligible=0；没有独立替代边数据 |
| G6/G8 provider 真实性 | 无 immutable gateway weight fingerprint 与外部 billing receipt |
| G5 数学审查、统计审查、upstream provenance | 仍需外部/独立审查或网络凭据，不能由本地 pytest 代替 |
