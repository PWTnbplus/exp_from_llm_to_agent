# DeepSeek 四组实验结果汇总

生成时间：2026-10-09（Asia/Hong_Kong）
统计范围：外部实验目录中的四个 DeepSeek 组别；本文件只保存汇总统计，不包含原始结果、日志、trace、答案键或密钥。

## 1. 统计口径

- 每个难度级别包含 6 个模型、每模型 100 个任务；三档难度共 600 条/批次、1800 条/组别。
- `正确率 = validation.answer_correct == true 的条数 / 结果文件条数`。失败任务不计为正确，但单独报告完成率和失败数。
- 本次四组主批次中 `unscored = 0`，即没有因为缺少 `answer_correct` 而被静默排除的记录。
- “放宽组”不是无限预算：它使用每模型 200 USD 的硬上限；限制组使用每模型 2 USD。纯 LLM 每题最多 1 次模型调用，Agent 每题最多 8 次调用，传输重试均为 0。
- 纯 LLM 限制组 easy 的早期 `run-20261009T024916Z` 只有 119 条结果（正确 2 条），不进入下面 1800 条主分母，单独列在“遗留部分批次”中。
- `cost_usd_proxy` 是本地 input/output token 价格估算，不是 CTFlow 实际账单。

## 2. 主结论

| 组别 | 结果数 | 正确 | 正确率 | 完成 | 完成率 | 正确/已完成 | 审计状态 |
|---|---:|---:|---:|---:|---:|---:|---|
| 纯 LLM·限制（G1，2 USD/模型） | 1800 | 69 | 3.83% | 1275 | 70.83% | 5.41% | 三批次结构审计通过 |
| 纯 LLM·放宽（G1，200 USD/模型） | 1800 | 35 | 1.94% | 807 | 44.83% | 4.34% | 三批次结构审计通过 |
| Agent·限制（G4，2 USD/模型） | 1800 | 2 | 0.11% | 21 | 1.17% | 9.52% | 三批次结构审计通过 |
| Agent·放宽（G4，200 USD/模型） | 1800 | 8 | 0.44% | 27 | 1.50% | 29.63% | mid 批次结构审计不通过 |

四个主组别合计 7200 条结果、114 条正确。由于 Agent 两组的失败率约 98.5%–98.8%，其“已完成条件正确率”不应被解释为稳定能力指标。

## 3. 逐批次统计

| 组别 | 难度 | run | 结果数 | 正确 | 正确率 | 完成 | 失败 | 协议不合格 | 成本估算 USD | 结构审计 |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 纯 LLM·限制 | easy | `run-20261009T025635Z` | 600 | 32 | 5.33% | 462 | 138 | 138 | 1.6995 | 通过 |
| 纯 LLM·限制 | mid | `run-20261009T035500Z` | 600 | 22 | 3.67% | 402 | 198 | 198 | 2.0104 | 通过 |
| 纯 LLM·限制 | diff | `run-20261009T045500Z` | 600 | 15 | 2.50% | 411 | 189 | 189 | 2.0811 | 通过 |
| 纯 LLM·放宽 | easy | `run-20261009T074500Z` | 600 | 31 | 5.17% | 442 | 158 | 158 | 1.7687 | 通过 |
| 纯 LLM·放宽 | mid | `run-20261009T084500Z` | 600 | 3 | 0.50% | 170 | 430 | 430 | 7.3465 | 通过 |
| 纯 LLM·放宽 | diff | `run-20261009T111500Z` | 600 | 1 | 0.17% | 195 | 405 | 405 | 7.1454 | 通过 |
| Agent·限制 | easy | `run-20261009T070500Z` | 600 | 2 | 0.33% | 7 | 593 | 593 | 0.3324 | 通过 |
| Agent·限制 | mid | `run-20261009T071000Z` | 600 | 0 | 0.00% | 7 | 593 | 593 | 0.3473 | 通过 |
| Agent·限制 | diff | `run-20261009T073000Z` | 600 | 0 | 0.00% | 7 | 593 | 593 | 0.4997 | 通过 |
| Agent·放宽 | easy | `run-20261009T074000Z` | 600 | 3 | 0.50% | 5 | 595 | 595 | 0.3400 | 通过 |
| Agent·放宽 | mid | `run-20261009T080000Z` | 600 | 3 | 0.50% | 12 | 588 | 588 | 0.4487 | **不通过** |
| Agent·放宽 | diff | `run-20261009T083000Z` | 600 | 2 | 0.33% | 10 | 590 | 590 | 0.5157 | 通过 |

Agent·放宽 mid 的 600 个文件数量齐全，但独立审计为 false：`deepseek-v3.2` 的 100 个任务全部为 `PolicyViolation`，并且审计发现凭据模式命中。因此该批次的 3 条正确记录只能作为观测结果，不能作为协议合格的正式比较证据。

## 4. 限制组与放宽组对比

下表为“放宽 − 限制”的百分点变化；负值表示放宽后下降。

| 范式 | 难度 | 限制正确率 | 放宽正确率 | 正确率变化 | 限制完成率 | 放宽完成率 |
|---|---|---:|---:|---:|---:|---:|
| 纯 LLM | easy | 5.33% | 5.17% | -0.17 pp | 77.00% | 73.67% |
| 纯 LLM | mid | 3.67% | 0.50% | -3.17 pp | 67.00% | 28.33% |
| 纯 LLM | diff | 2.50% | 0.17% | -2.33 pp | 68.50% | 32.50% |
| Agent | easy | 0.33% | 0.50% | +0.17 pp | 1.17% | 0.83% |
| Agent | mid | 0.00% | 0.50% | +0.50 pp | 1.17% | 2.00% |
| Agent | diff | 0.00% | 0.33% | +0.33 pp | 1.17% | 1.67% |

观察：放宽预算没有带来纯 LLM 正确率提升，mid/diff 反而伴随完成率大幅下降；Agent 放宽组正确条数增加，但绝对正确率仍低于 0.5%，且 mid 批次存在审计失败，不能据此得出 Agent 优于纯 LLM 的结论。

## 5. 每个模型、每个难度的完整统计

缩写：PL=纯 LLM 限制，PU=纯 LLM 放宽，AL=Agent 限制，AU=Agent 放宽。每行理论任务数为 100；`协议不合格` 是 `protocol_valid == false` 的条数；`验证状态` 是结果文件中的 validator 状态计数。

|组别|难度|模型|N|正确|正确率|完成|失败|协议不合格|验证状态|
|---|---|---|---:|---:|---:|---:|---:|---:|---|
|PL|easy|deepseek-r1-distill-qwen-1.5b|100|1|1.00%|79|21|21|MODEL_ERROR:99, PASS:1|
|PL|easy|deepseek-v3.2|100|4|4.00%|94|6|6|MODEL_ERROR:96, PASS:4|
|PL|easy|deepseek-v4.1-flash|100|26|26.00%|87|13|13|MODEL_ERROR:74, PASS:26|
|PL|easy|deepseek-r1-distill-qwen-14b|100|1|1.00%|33|67|67|MODEL_ERROR:99, PASS:1|
|PL|easy|deepseek-r1-distill-qwen-32b|100|0|0.00%|81|19|19|MODEL_ERROR:100|
|PL|easy|deepseek-r1-distill-qwen-7b|100|0|0.00%|88|12|12|MODEL_ERROR:100|
|PL|mid|deepseek-r1-distill-qwen-1.5b|100|0|0.00%|61|39|39|MODEL_ERROR:100|
|PL|mid|deepseek-v3.2|100|0|0.00%|89|11|11|MODEL_ERROR:100|
|PL|mid|deepseek-v4.1-flash|100|20|20.00%|69|31|31|MODEL_ERROR:80, PASS:20|
|PL|mid|deepseek-r1-distill-qwen-14b|100|1|1.00%|30|70|70|MODEL_ERROR:99, PASS:1|
|PL|mid|deepseek-r1-distill-qwen-32b|100|0|0.00%|73|27|27|MODEL_ERROR:100|
|PL|mid|deepseek-r1-distill-qwen-7b|100|1|1.00%|80|20|20|MODEL_ERROR:99, PASS:1|
|PL|diff|deepseek-r1-distill-qwen-1.5b|100|0|0.00%|74|26|26|MODEL_ERROR:100|
|PL|diff|deepseek-v3.2|100|1|1.00%|88|12|12|MODEL_ERROR:99, PASS:1|
|PL|diff|deepseek-v4.1-flash|100|13|13.00%|61|39|39|MODEL_ERROR:87, PASS:13|
|PL|diff|deepseek-r1-distill-qwen-14b|100|0|0.00%|37|63|63|MODEL_ERROR:100|
|PL|diff|deepseek-r1-distill-qwen-32b|100|1|1.00%|75|25|25|MODEL_ERROR:99, PASS:1|
|PL|diff|deepseek-r1-distill-qwen-7b|100|0|0.00%|76|24|24|MODEL_ERROR:100|
|PU|easy|deepseek-r1-distill-qwen-1.5b|100|0|0.00%|75|25|25|MODEL_ERROR:100|
|PU|easy|deepseek-v3.2|100|2|2.00%|86|14|14|MODEL_ERROR:98, PASS:2|
|PU|easy|deepseek-v4.1-flash|100|27|27.00%|85|15|15|MODEL_ERROR:73, PASS:27|
|PU|easy|deepseek-r1-distill-qwen-14b|100|1|1.00%|33|67|67|MODEL_ERROR:99, PASS:1|
|PU|easy|deepseek-r1-distill-qwen-32b|100|0|0.00%|73|27|27|MODEL_ERROR:100|
|PU|easy|deepseek-r1-distill-qwen-7b|100|1|1.00%|90|10|10|MODEL_ERROR:99, PASS:1|
|PU|mid|deepseek-r1-distill-qwen-1.5b|100|0|0.00%|64|36|36|MODEL_ERROR:100|
|PU|mid|deepseek-v3.2|100|1|1.00%|56|44|44|MODEL_ERROR:99, PASS:1|
|PU|mid|deepseek-v4.1-flash|100|2|2.00%|4|96|96|MODEL_ERROR:98, PASS:2|
|PU|mid|deepseek-r1-distill-qwen-14b|100|0|0.00%|36|64|64|MODEL_ERROR:100|
|PU|mid|deepseek-r1-distill-qwen-32b|100|0|0.00%|1|99|99|MODEL_ERROR:100|
|PU|mid|deepseek-r1-distill-qwen-7b|100|0|0.00%|9|91|91|MODEL_ERROR:100|
|PU|diff|deepseek-r1-distill-qwen-1.5b|100|0|0.00%|72|28|28|MODEL_ERROR:100|
|PU|diff|deepseek-v3.2|100|0|0.00%|55|45|45|MODEL_ERROR:100|
|PU|diff|deepseek-v4.1-flash|100|1|1.00%|1|99|99|MODEL_ERROR:99, PASS:1|
|PU|diff|deepseek-r1-distill-qwen-14b|100|0|0.00%|40|60|60|MODEL_ERROR:100|
|PU|diff|deepseek-r1-distill-qwen-32b|100|0|0.00%|4|96|96|MODEL_ERROR:100|
|PU|diff|deepseek-r1-distill-qwen-7b|100|0|0.00%|23|77|77|MODEL_ERROR:100|
|AL|easy|deepseek-r1-distill-qwen-1.5b|100|0|0.00%|0|100|100|MODEL_ERROR:100|
|AL|easy|deepseek-v3.2|100|0|0.00%|0|100|100|MODEL_ERROR:100|
|AL|easy|deepseek-v4.1-flash|100|2|2.00%|7|93|93|MODEL_ERROR:98, PASS:2|
|AL|easy|deepseek-r1-distill-qwen-14b|100|0|0.00%|0|100|100|MODEL_ERROR:100|
|AL|easy|deepseek-r1-distill-qwen-32b|100|0|0.00%|0|100|100|MODEL_ERROR:100|
|AL|easy|deepseek-r1-distill-qwen-7b|100|0|0.00%|0|100|100|MODEL_ERROR:100|
|AL|mid|deepseek-r1-distill-qwen-1.5b|100|0|0.00%|0|100|100|MODEL_ERROR:100|
|AL|mid|deepseek-v3.2|100|0|0.00%|0|100|100|MODEL_ERROR:100|
|AL|mid|deepseek-v4.1-flash|100|0|0.00%|7|93|93|MODEL_ERROR:100|
|AL|mid|deepseek-r1-distill-qwen-14b|100|0|0.00%|0|100|100|MODEL_ERROR:100|
|AL|mid|deepseek-r1-distill-qwen-32b|100|0|0.00%|0|100|100|MODEL_ERROR:100|
|AL|mid|deepseek-r1-distill-qwen-7b|100|0|0.00%|0|100|100|MODEL_ERROR:100|
|AL|diff|deepseek-r1-distill-qwen-1.5b|100|0|0.00%|0|100|100|MODEL_ERROR:100|
|AL|diff|deepseek-v3.2|100|0|0.00%|0|100|100|MODEL_ERROR:100|
|AL|diff|deepseek-v4.1-flash|100|0|0.00%|7|93|93|MODEL_ERROR:100|
|AL|diff|deepseek-r1-distill-qwen-14b|100|0|0.00%|0|100|100|MODEL_ERROR:100|
|AL|diff|deepseek-r1-distill-qwen-32b|100|0|0.00%|0|100|100|MODEL_ERROR:100|
|AL|diff|deepseek-r1-distill-qwen-7b|100|0|0.00%|0|100|100|MODEL_ERROR:100|
|AU|easy|deepseek-r1-distill-qwen-1.5b|100|0|0.00%|0|100|100|MODEL_ERROR:100|
|AU|easy|deepseek-v3.2|100|0|0.00%|0|100|100|MODEL_ERROR:100|
|AU|easy|deepseek-v4.1-flash|100|3|3.00%|5|95|95|MODEL_ERROR:97, PASS:3|
|AU|easy|deepseek-r1-distill-qwen-14b|100|0|0.00%|0|100|100|MODEL_ERROR:100|
|AU|easy|deepseek-r1-distill-qwen-32b|100|0|0.00%|0|100|100|MODEL_ERROR:100|
|AU|easy|deepseek-r1-distill-qwen-7b|100|0|0.00%|0|100|100|MODEL_ERROR:100|
|AU|mid|deepseek-r1-distill-qwen-1.5b|100|0|0.00%|0|100|100|MODEL_ERROR:100|
|AU|mid|deepseek-v3.2|100|0|0.00%|0|100|100|MODEL_ERROR:100|
|AU|mid|deepseek-v4.1-flash|100|3|3.00%|12|88|88|MODEL_ERROR:97, PASS:3|
|AU|mid|deepseek-r1-distill-qwen-14b|100|0|0.00%|0|100|100|MODEL_ERROR:100|
|AU|mid|deepseek-r1-distill-qwen-32b|100|0|0.00%|0|100|100|MODEL_ERROR:100|
|AU|mid|deepseek-r1-distill-qwen-7b|100|0|0.00%|0|100|100|MODEL_ERROR:100|
|AU|diff|deepseek-r1-distill-qwen-1.5b|100|0|0.00%|0|100|100|MODEL_ERROR:100|
|AU|diff|deepseek-v3.2|100|0|0.00%|0|100|100|MODEL_ERROR:100|
|AU|diff|deepseek-v4.1-flash|100|2|2.00%|10|90|90|MODEL_ERROR:98, PASS:2|
|AU|diff|deepseek-r1-distill-qwen-14b|100|0|0.00%|0|100|100|MODEL_ERROR:100|
|AU|diff|deepseek-r1-distill-qwen-32b|100|0|0.00%|0|100|100|MODEL_ERROR:100|
|AU|diff|deepseek-r1-distill-qwen-7b|100|0|0.00%|0|100|100|MODEL_ERROR:100|

## 6. 模型层面的结论

跨三档难度汇总：

| 组别 | 模型 | 正确/300 | 正确率 | 完成 | 失败 |
|---|---|---:|---:|---:|---:|
| 纯 LLM·限制 | deepseek-r1-distill-qwen-1.5b | 1/300 | 0.33% | 214 | 86 |
| 纯 LLM·限制 | deepseek-v3.2 | 5/300 | 1.67% | 271 | 29 |
| 纯 LLM·限制 | deepseek-v4.1-flash | 59/300 | 19.67% | 217 | 83 |
| 纯 LLM·限制 | deepseek-r1-distill-qwen-14b | 2/300 | 0.67% | 100 | 200 |
| 纯 LLM·限制 | deepseek-r1-distill-qwen-32b | 1/300 | 0.33% | 229 | 71 |
| 纯 LLM·限制 | deepseek-r1-distill-qwen-7b | 1/300 | 0.33% | 244 | 56 |
| 纯 LLM·放宽 | deepseek-r1-distill-qwen-1.5b | 0/300 | 0.00% | 211 | 89 |
| 纯 LLM·放宽 | deepseek-v3.2 | 3/300 | 1.00% | 197 | 103 |
| 纯 LLM·放宽 | deepseek-v4.1-flash | 30/300 | 10.00% | 90 | 210 |
| 纯 LLM·放宽 | deepseek-r1-distill-qwen-14b | 1/300 | 0.33% | 109 | 191 |
| 纯 LLM·放宽 | deepseek-r1-distill-qwen-32b | 0/300 | 0.00% | 78 | 222 |
| 纯 LLM·放宽 | deepseek-r1-distill-qwen-7b | 1/300 | 0.33% | 122 | 178 |
| Agent·限制 | deepseek-r1-distill-qwen-1.5b | 0/300 | 0.00% | 0 | 300 |
| Agent·限制 | deepseek-v3.2 | 0/300 | 0.00% | 0 | 300 |
| Agent·限制 | deepseek-v4.1-flash | 2/300 | 0.67% | 21 | 279 |
| Agent·限制 | deepseek-r1-distill-qwen-14b | 0/300 | 0.00% | 0 | 300 |
| Agent·限制 | deepseek-r1-distill-qwen-32b | 0/300 | 0.00% | 0 | 300 |
| Agent·限制 | deepseek-r1-distill-qwen-7b | 0/300 | 0.00% | 0 | 300 |
| Agent·放宽 | deepseek-r1-distill-qwen-1.5b | 0/300 | 0.00% | 0 | 300 |
| Agent·放宽 | deepseek-v3.2 | 0/300 | 0.00% | 0 | 300 |
| Agent·放宽 | deepseek-v4.1-flash | 8/300 | 2.67% | 27 | 273 |
| Agent·放宽 | deepseek-r1-distill-qwen-14b | 0/300 | 0.00% | 0 | 300 |
| Agent·放宽 | deepseek-r1-distill-qwen-32b | 0/300 | 0.00% | 0 | 300 |
| Agent·放宽 | deepseek-r1-distill-qwen-7b | 0/300 | 0.00% | 0 | 300 |

`deepseek-v4.1-flash` 是唯一在四个组别都出现正确答案的模型，也是绝大多数正确数的来源；但它在 Agent 组的完成量仍只有 21/300（限制）和 27/300（放宽）。

## 7. 失败与审计概览

按单个 validation error 计数（一个结果可能包含多个错误，因此这些计数不一定加总到 1800）：

| 组别 | 主要错误 1 | 主要错误 2 | 主要错误 3 |
|---|---|---|---|
| 纯 LLM·限制 | validation mismatch（1841） | JSONDecodeError（487） | RuntimeError/timeout（38） |
| 纯 LLM·放宽 | validation mismatch（1118） | JSONDecodeError（959） | RuntimeError/timeout（34） |
| Agent·限制 | RuntimeError/timeout（1230） | PolicyViolation（528） | validation mismatch（27） |
| Agent·放宽 | RuntimeError/timeout（1200） | PolicyViolation（548） | validation mismatch（30） |

这里的 `MODEL_ERROR` 反映的是任务没有通过模型输出/协议/验证流程，并不等同于“模型知道答案但答错”。因此本报告同时给出总体正确率和完成条件正确率，避免把大量接口失败误读成纯粹的知识错误。

## 8. 遗留部分批次

纯 LLM 限制 easy 的早期运行 `run-20261009T024916Z` 只有 119 条结果：正确 2 条、完成 27 条、失败 92 条。它与之后的 600 条完整批次不是同一完整分母，故不合并到主表。

## 9. 不应据此作出的结论

这批结果可以说明当前四组运行的观测正确率、完成率和协议失败分布；不能单独证明“Agent 一定优于/劣于纯 LLM”，也不能把放宽组 200 USD 上限称为真正无限预算。正式科学结论仍需解决项目状态中的统计有效性、真实 provider 复核和 Agent 放宽 mid 审计失败问题。
