# DeepSeek 最终 Output 语义统计报告

生成时间：2026-10-09（Asia/Hong_Kong）

本报告回答的问题是：**不把 JSON 格式、外层包装、字段名不匹配等协议问题当作答错，只看模型最后输出中是否包含正确答案内容，结果如何？**

原始结果、trace、日志和答案键均未写入本文件，也未提交到 GitHub。

## 1. 新统计口径

对每条结果执行以下处理：

1. 优先读取结果文件中已经保存的 `answer.final_answer`；如果该字段无法读取，则从最后一次 provider response 中尝试恢复 JSON 对象，去除 Markdown code fence，并容忍外层 JSON 的尾逗号或不完整包装。
2. 只取最终 `final_answer` 的内容，不把题目、推导过程、输入参数或日志内容当作答案。
3. 忽略答案字段名和外层字段结构，对最终答案中的标量值做语义比对：数值使用 benchmark checker 的容差，表达式使用 checker 的符号等价规则；期望答案中的所有标量都必须在最终输出中找到匹配值。
4. 完全没有可恢复最终 output 的任务不判为“语义错误”，单列为“无可恢复 output”。因此报告同时给出两种比例：
   - `OutputCorrect/All`：语义正确数 / 全部 1800 条任务；
   - `OutputCorrect/Judged`：语义正确数 /（语义正确数 + 语义错误数），只在确实有最终 output 的任务中计算。

这是一种“最终 output 语义近似统计”，不是项目原有的严格 schema evaluator 分数。它适合回答“答案内容是否出现”，不适合替代正式协议合规性或科学统计检验。

## 2. 四组总览

| 组别 | 全部任务 | 原严格正确 | Output 语义正确 | Output 语义错误 | 无可恢复 output | OutputCorrect/All | OutputCorrect/Judged |
|---|---:|---:|---:|---:|---:|---:|---:|
| 纯 LLM·限制（PL） | 1800 | 69 | 612 | 1003 | 185 | 34.00% | 37.89% |
| 纯 LLM·放宽（PU） | 1800 | 35 | 446 | 755 | 599 | 24.78% | 37.14% |
| Agent·限制（AL） | 1800 | 2 | 16 | 13 | 1771 | 0.89% | 55.17% |
| Agent·放宽（AU） | 1800 | 8 | 24 | 13 | 1763 | 1.33% | 64.86% |

### 直接结论

- 从“有最终 output 的任务”看，纯 LLM 限制和放宽分别为 37.89% 和 37.14%，基本接近。
- 从全部任务看，纯 LLM 放宽组降到 24.78%，主要原因是放宽组 mid/diff 出现了大量不可恢复 output。
- Agent 放宽组的条件正确率看起来最高（64.86%），但只有 37/1800 条存在可恢复最终 output；这不是稳定能力结论。
- Agent 限制组只有 29/1800 条可判定，Agent 放宽组只有 37/1800 条可判定，不能和纯 LLM 的千级可判定样本直接比较。

## 3. 按难度统计

| 组别 | 难度 | 全部 | 原严格正确 | Output 正确 | Output 错误 | 无可恢复 output | OutputCorrect/All | OutputCorrect/Judged |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| PL | easy | 600 | 32 | 246 | 308 | 46 | 41.00% | 44.40% |
| PL | mid | 600 | 22 | 212 | 327 | 61 | 35.33% | 39.33% |
| PL | diff | 600 | 15 | 154 | 368 | 78 | 25.67% | 29.50% |
| PU | easy | 600 | 31 | 244 | 303 | 53 | 40.67% | 44.61% |
| PU | mid | 600 | 3 | 119 | 207 | 274 | 19.83% | 36.50% |
| PU | diff | 600 | 1 | 83 | 245 | 272 | 13.83% | 25.30% |
| AL | easy | 600 | 2 | 7 | 2 | 591 | 1.17% | 77.78% |
| AL | mid | 600 | 0 | 5 | 5 | 590 | 0.83% | 50.00% |
| AL | diff | 600 | 0 | 4 | 6 | 590 | 0.67% | 40.00% |
| AU | easy | 600 | 3 | 4 | 3 | 593 | 0.67% | 57.14% |
| AU | mid | 600 | 3 | 11 | 4 | 585 | 1.83% | 73.33% |
| AU | diff | 600 | 2 | 9 | 6 | 585 | 1.50% | 60.00% |

## 4. 限制组与放宽组的 Output 对比

这里的变化是“放宽 − 限制”，使用 `OutputCorrect/All`。

| 范式 | 难度 | 限制 | 放宽 | 变化 |
|---|---|---:|---:|---:|
| 纯 LLM | easy | 41.00% | 40.67% | -0.33 pp |
| 纯 LLM | mid | 35.33% | 19.83% | -15.50 pp |
| 纯 LLM | diff | 25.67% | 13.83% | -11.83 pp |
| Agent | easy | 1.17% | 0.67% | -0.50 pp |
| Agent | mid | 0.83% | 1.83% | +1.00 pp |
| Agent | diff | 0.67% | 1.50% | +0.83 pp |

纯 LLM 的最终答案内容准确率并没有因为预算放宽而上升；mid 和 diff 反而明显下降，主要与不可恢复 output 增多同时发生。Agent 的放宽组虽然绝对正确数增加，但可判定样本极少。

## 5. 每个模型、每个难度的完整统计

缩写：PL=纯 LLM 限制，PU=纯 LLM 放宽，AL=Agent 限制，AU=Agent 放宽。每行理论任务数为 100。

|组别|难度|模型|N|原严格正确|Output 正确|Output 错误|无可恢复 output|正确/全部|正确/可判定|
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
|PL|easy|deepseek-r1-distill-qwen-1.5b|100|1|7|82|11|7.00%|7.87%|
|PL|easy|deepseek-v3.2|100|4|50|45|5|50.00%|52.63%|
|PL|easy|deepseek-v4.1-flash|100|26|74|15|11|74.00%|83.15%|
|PL|easy|deepseek-r1-distill-qwen-14b|100|1|40|54|6|40.00%|42.55%|
|PL|easy|deepseek-r1-distill-qwen-32b|100|0|41|53|6|41.00%|43.62%|
|PL|easy|deepseek-r1-distill-qwen-7b|100|0|34|59|7|34.00%|36.56%|
|PL|mid|deepseek-r1-distill-qwen-1.5b|100|0|10|80|10|10.00%|11.11%|
|PL|mid|deepseek-v3.2|100|0|37|56|7|37.00%|39.78%|
|PL|mid|deepseek-v4.1-flash|100|20|60|18|22|60.00%|76.92%|
|PL|mid|deepseek-r1-distill-qwen-14b|100|1|40|57|3|40.00%|41.24%|
|PL|mid|deepseek-r1-distill-qwen-32b|100|0|38|54|8|38.00%|41.30%|
|PL|mid|deepseek-r1-distill-qwen-7b|100|1|27|62|11|27.00%|30.34%|
|PL|diff|deepseek-r1-distill-qwen-1.5b|100|0|6|85|9|6.00%|6.59%|
|PL|diff|deepseek-v3.2|100|1|25|70|5|25.00%|26.32%|
|PL|diff|deepseek-v4.1-flash|100|13|46|20|34|46.00%|69.70%|
|PL|diff|deepseek-r1-distill-qwen-14b|100|0|30|67|3|30.00%|30.93%|
|PL|diff|deepseek-r1-distill-qwen-32b|100|1|25|64|11|25.00%|28.09%|
|PL|diff|deepseek-r1-distill-qwen-7b|100|0|22|62|16|22.00%|26.19%|
|PU|easy|deepseek-r1-distill-qwen-1.5b|100|0|6|79|15|6.00%|7.06%|
|PU|easy|deepseek-v3.2|100|2|41|48|11|41.00%|46.07%|
|PU|easy|deepseek-v4.1-flash|100|27|75|13|12|75.00%|85.23%|
|PU|easy|deepseek-r1-distill-qwen-14b|100|1|42|55|3|42.00%|43.30%|
|PU|easy|deepseek-r1-distill-qwen-32b|100|0|44|52|4|44.00%|45.83%|
|PU|easy|deepseek-r1-distill-qwen-7b|100|1|36|56|8|36.00%|39.13%|
|PU|mid|deepseek-r1-distill-qwen-1.5b|100|0|6|78|16|6.00%|7.14%|
|PU|mid|deepseek-v3.2|100|1|30|55|15|30.00%|35.29%|
|PU|mid|deepseek-v4.1-flash|100|2|30|4|66|30.00%|88.24%|
|PU|mid|deepseek-r1-distill-qwen-14b|100|0|40|57|3|40.00%|41.24%|
|PU|mid|deepseek-r1-distill-qwen-32b|100|0|1|0|99|1.00%|100.00%|
|PU|mid|deepseek-r1-distill-qwen-7b|100|0|12|13|75|12.00%|48.00%|
|PU|diff|deepseek-r1-distill-qwen-1.5b|100|0|2|91|7|2.00%|2.15%|
|PU|diff|deepseek-v3.2|100|0|23|62|15|23.00%|27.06%|
|PU|diff|deepseek-v4.1-flash|100|1|18|8|74|18.00%|69.23%|
|PU|diff|deepseek-r1-distill-qwen-14b|100|0|26|63|11|26.00%|29.21%|
|PU|diff|deepseek-r1-distill-qwen-32b|100|0|2|5|93|2.00%|28.57%|
|PU|diff|deepseek-r1-distill-qwen-7b|100|0|12|16|72|12.00%|42.86%|
|AL|easy|deepseek-r1-distill-qwen-1.5b|100|0|0|0|100|0.00%|NA|
|AL|easy|deepseek-v3.2|100|0|0|2|98|0.00%|0.00%|
|AL|easy|deepseek-v4.1-flash|100|2|7|0|93|7.00%|100.00%|
|AL|easy|deepseek-r1-distill-qwen-14b|100|0|0|0|100|0.00%|NA|
|AL|easy|deepseek-r1-distill-qwen-32b|100|0|0|0|100|0.00%|NA|
|AL|easy|deepseek-r1-distill-qwen-7b|100|0|0|0|100|0.00%|NA|
|AL|mid|deepseek-r1-distill-qwen-1.5b|100|0|0|0|100|0.00%|NA|
|AL|mid|deepseek-v3.2|100|0|0|1|99|0.00%|0.00%|
|AL|mid|deepseek-v4.1-flash|100|0|5|4|91|5.00%|55.56%|
|AL|mid|deepseek-r1-distill-qwen-14b|100|0|0|0|100|0.00%|NA|
|AL|mid|deepseek-r1-distill-qwen-32b|100|0|0|0|100|0.00%|NA|
|AL|mid|deepseek-r1-distill-qwen-7b|100|0|0|0|100|0.00%|NA|
|AL|diff|deepseek-r1-distill-qwen-1.5b|100|0|0|0|100|0.00%|NA|
|AL|diff|deepseek-v3.2|100|0|0|2|98|0.00%|0.00%|
|AL|diff|deepseek-v4.1-flash|100|0|4|4|92|4.00%|50.00%|
|AL|diff|deepseek-r1-distill-qwen-14b|100|0|0|0|100|0.00%|NA|
|AL|diff|deepseek-r1-distill-qwen-32b|100|0|0|0|100|0.00%|NA|
|AL|diff|deepseek-r1-distill-qwen-7b|100|0|0|0|100|0.00%|NA|
|AU|easy|deepseek-r1-distill-qwen-1.5b|100|0|0|0|100|0.00%|NA|
|AU|easy|deepseek-v3.2|100|0|0|1|99|0.00%|0.00%|
|AU|easy|deepseek-v4.1-flash|100|3|4|2|94|4.00%|66.67%|
|AU|easy|deepseek-r1-distill-qwen-14b|100|0|0|0|100|0.00%|NA|
|AU|easy|deepseek-r1-distill-qwen-32b|100|0|0|0|100|0.00%|NA|
|AU|easy|deepseek-r1-distill-qwen-7b|100|0|0|0|100|0.00%|NA|
|AU|mid|deepseek-r1-distill-qwen-1.5b|100|0|0|0|100|0.00%|NA|
|AU|mid|deepseek-v3.2|100|0|1|0|99|1.00%|100.00%|
|AU|mid|deepseek-v4.1-flash|100|3|10|4|86|10.00%|71.43%|
|AU|mid|deepseek-r1-distill-qwen-14b|100|0|0|0|100|0.00%|NA|
|AU|mid|deepseek-r1-distill-qwen-32b|100|0|0|0|100|0.00%|NA|
|AU|mid|deepseek-r1-distill-qwen-7b|100|0|0|0|100|0.00%|NA|
|AU|diff|deepseek-r1-distill-qwen-1.5b|100|0|0|0|100|0.00%|NA|
|AU|diff|deepseek-v3.2|100|0|0|4|96|0.00%|0.00%|
|AU|diff|deepseek-v4.1-flash|100|2|9|2|89|9.00%|81.82%|
|AU|diff|deepseek-r1-distill-qwen-14b|100|0|0|0|100|0.00%|NA|
|AU|diff|deepseek-r1-distill-qwen-32b|100|0|0|0|100|0.00%|NA|
|AU|diff|deepseek-r1-distill-qwen-7b|100|0|0|0|100|0.00%|NA|

## 6. 跨难度模型汇总

|组别|模型|N|原严格正确|Output 正确|Output 错误|无可恢复 output|正确/全部|正确/可判定|
|---|---|---:|---:|---:|---:|---:|---:|---:|
|PL|deepseek-r1-distill-qwen-1.5b|300|1|23|247|30|7.67%|8.52%|
|PL|deepseek-v3.2|300|5|112|171|17|37.33%|39.58%|
|PL|deepseek-v4.1-flash|300|59|180|53|67|60.00%|77.25%|
|PL|deepseek-r1-distill-qwen-14b|300|2|110|178|12|36.67%|38.19%|
|PL|deepseek-r1-distill-qwen-32b|300|1|104|171|25|34.67%|37.82%|
|PL|deepseek-r1-distill-qwen-7b|300|1|83|183|34|27.67%|31.20%|
|PU|deepseek-r1-distill-qwen-1.5b|300|0|14|248|38|4.67%|5.34%|
|PU|deepseek-v3.2|300|3|94|165|41|31.33%|36.29%|
|PU|deepseek-v4.1-flash|300|30|123|25|152|41.00%|83.11%|
|PU|deepseek-r1-distill-qwen-14b|300|1|108|175|17|36.00%|38.16%|
|PU|deepseek-r1-distill-qwen-32b|300|0|47|57|196|15.67%|45.19%|
|PU|deepseek-r1-distill-qwen-7b|300|1|60|85|155|20.00%|41.38%|
|AL|deepseek-r1-distill-qwen-1.5b|300|0|0|0|300|0.00%|NA|
|AL|deepseek-v3.2|300|0|0|5|295|0.00%|0.00%|
|AL|deepseek-v4.1-flash|300|2|16|8|276|5.33%|66.67%|
|AL|deepseek-r1-distill-qwen-14b|300|0|0|0|300|0.00%|NA|
|AL|deepseek-r1-distill-qwen-32b|300|0|0|0|300|0.00%|NA|
|AL|deepseek-r1-distill-qwen-7b|300|0|0|0|300|0.00%|NA|
|AU|deepseek-r1-distill-qwen-1.5b|300|0|0|0|300|0.00%|NA|
|AU|deepseek-v3.2|300|0|1|5|294|0.33%|16.67%|
|AU|deepseek-v4.1-flash|300|8|23|8|269|7.67%|74.19%|
|AU|deepseek-r1-distill-qwen-14b|300|0|0|0|300|0.00%|NA|
|AU|deepseek-r1-distill-qwen-32b|300|0|0|0|300|0.00%|NA|
|AU|deepseek-r1-distill-qwen-7b|300|0|0|0|300|0.00%|NA|

## 7. 这份报告与原严格报告的关系

原报告把 `answer_correct == false` 全部作为不正确；因此它反映“协议加语义的严格通过率”。本报告只看 final output 的内容，所以把下列情况从“语义错误”中救回：

- `final_answer` 是单个标量，但标准答案只有一个同值字段，例如输出 `10.0`，标准字段为 `protein_mean: 10.0`；
- 外层 JSON 不完整或带格式问题，但其中的 `final_answer` 对象仍可恢复；
- 最终答案值正确，但字段名与标准字段名不同。

例如，`TB-L1-031` 的输出内容是 `10.0`，严格 evaluator 报告 `final_answer.protein_mean: missing`；按本报告口径，它属于 Output 正确。相反，如果 provider 在超时或预算中断前没有最终答案，即使推理过程看起来接近，也不会被强行判成正确。

## 8. 遗留部分批次

纯 LLM 限制 easy 的早期 `run-20261009T024916Z` 只有 119 条结果，未并入四组主分母。按同一 output 口径，它是：14 条 Output 正确、51 条 Output 错误、54 条无可恢复 output；OutputCorrect/All=11.76%，OutputCorrect/Judged=21.54%。

## 9. 最终解释

如果你的研究问题是“模型是否在最后输出中给出了正确数值/公式”，应优先看本报告的 `OutputCorrect/Judged`，同时报告可判定覆盖率：

- 纯 LLM 限制：37.89%，覆盖 1615/1800；
- 纯 LLM 放宽：37.14%，覆盖 1201/1800；
- Agent 限制：55.17%，但只覆盖 29/1800；
- Agent 放宽：64.86%，但只覆盖 37/1800。

因此，当前数据支持的谨慎结论是：纯 LLM 的最终答案语义准确率约在 37%–38% 的可判定样本中保持稳定；Agent 的条件准确率不能独立解释，因为绝大多数任务没有最终 output。Agent 放宽组 mid 仍存在独立审计不通过问题，这一点与“忽略格式错误”是两个不同层面，不能省略。
