# 恢复数据的最终 Output 全量分析报告

生成时间：2026-10-10（Asia/Hong_Kong）

本报告纳入恢复后的所有 provider 结果，并按最终 output 内容重新统计。原始结果、日志、trace、答案键和密钥没有写入仓库。

## 1. 数据范围

- 实际纳入：**16,919 条结果**，覆盖 37 个直接运行目录。
- `organized/results_index.jsonl` 原先只索引了 16,319 条；另外补入了纯 LLM 限制 easy 的完整 600 条旧批次，因为该批次缺少 `run_manifest.json`，但结果文件完整。
- 格式恢复后的最终尝试：**5,024 条**；恢复结果替换对应的失败尝试参与最终 output 分析。
- Minimax 和 Qwen 每个模式/难度为 200 条（每组 2 个模型）；其他主要组别通常为 600 条（每组 6 个模型）。
- `limited_or_legacy` 中的 DeepSeek 包含限制组和 119 条早期 legacy 部分批次；legacy 部分批次单独列出。

## 2. 最终 Output 口径

仍采用上一份报告的 output-focused 口径：

1. 优先读取结果中的 `answer.final_answer`；无法读取时，从最后一次 provider response 尝试恢复 JSON 对象，容忍 code fence、外层尾逗号和不完整包装。
2. 只比较最后 `final_answer` 的值，不把题目、推导、输入参数或日志内容当成答案。
3. 忽略字段名和外层 JSON 结构，对最终答案中的标量值做匹配；数值使用 checker 容差，表达式使用符号等价规则。
4. 没有任何可恢复最终 output 的任务单列为 `no_output`。因此同时报告：
   - `正确/全部`：Output 正确 / 全部任务；
   - `正确/可判定`：Output 正确 /（Output 正确 + Output 错误）。

这是最终答案内容的语义近似统计，不替代严格 schema/protocol evaluator。

## 3. 全量总览

| 指标 | 数量 |
|---|---:|
| 全部结果 | 16,919 |
| 原严格 evaluator 正确 | 314 |
| Output 语义正确 | 3,198 |
| Output 语义错误 | 3,711 |
| 无可恢复 output | 10,010 |
| Output 正确率 / 全部 | 18.90% |
| Output 正确率 / 可判定 | 46.29% |
| 格式恢复最终尝试 | 5,024 |

## 4. Provider 汇总

| scope | provider | 结果数 | Output 正确 | Output 错误 | 无 output | 正确/全部 | 正确/可判定 | 恢复选中数 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| limited/legacy | DeepSeek | 3,719 | 652 | 1,132 | 1,935 | 17.53% | 36.55% | 480 |
| unlimited | DeepSeek | 3,600 | 638 | 1,100 | 1,862 | 17.72% | 36.71% | 996 |
| unlimited | GLM | 3,600 | 840 | 785 | 1,975 | 23.33% | 51.69% | 1,515 |
| unlimited | Kimi | 3,600 | 491 | 157 | 2,952 | 13.64% | 75.77% | 1,196 |
| unlimited | MiniMax | 1,200 | 404 | 273 | 523 | 33.67% | 59.68% | 334 |
| unlimited | Qwen | 1,200 | 173 | 264 | 763 | 14.42% | 39.59% | 503 |

## 5. Provider × 模式汇总

| scope | provider | 模式 | 结果数 | Output 正确 | Output 错误 | 无 output | 正确/全部 | 正确/可判定 | 恢复选中数 |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| limited/legacy | DeepSeek | G1 | 1,800 | 622 | 1,065 | 113 | 34.56% | 36.87% | 368 |
| limited/legacy | DeepSeek | G4 | 1,800 | 16 | 9 | 1,775 | 0.89% | 64.00% | 21 |
| limited/legacy | DeepSeek | legacy llm_only | 119 | 14 | 58 | 47 | 11.76% | 19.44% | 91 |
| unlimited | DeepSeek | G1 | 1,800 | 614 | 1,088 | 98 | 34.11% | 36.08% | 971 |
| unlimited | DeepSeek | G4 | 1,800 | 24 | 12 | 1,764 | 1.33% | 66.67% | 25 |
| unlimited | GLM | G1 | 1,800 | 785 | 711 | 304 | 43.61% | 52.47% | 1,184 |
| unlimited | GLM | G4 | 1,800 | 55 | 74 | 1,671 | 3.06% | 42.64% | 331 |
| unlimited | Kimi | G1 | 1,800 | 256 | 85 | 1,459 | 14.22% | 75.07% | 752 |
| unlimited | Kimi | G4 | 1,800 | 235 | 72 | 1,493 | 13.06% | 76.55% | 444 |
| unlimited | MiniMax | G1 | 600 | 240 | 171 | 189 | 40.00% | 58.39% | 186 |
| unlimited | MiniMax | G4 | 600 | 164 | 102 | 334 | 27.33% | 61.65% | 148 |
| unlimited | Qwen | G1 | 600 | 92 | 129 | 379 | 15.33% | 41.63% | 259 |
| unlimited | Qwen | G4 | 600 | 81 | 135 | 384 | 13.50% | 37.50% | 244 |

## 6. Provider × 模式 × 难度

| scope | provider | 模式 | 难度 | N | Output 正确 | Output 错误 | 无 output | 正确/全部 | 正确/可判定 |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| limited/legacy | DeepSeek | G1 | easy | 600 | 246 | 308 | 46 | 41.00% | 44.40% |
| limited/legacy | DeepSeek | G1 | mid | 600 | 217 | 357 | 26 | 36.17% | 37.80% |
| limited/legacy | DeepSeek | G1 | diff | 600 | 159 | 400 | 41 | 26.50% | 28.44% |
| limited/legacy | DeepSeek | G4 | easy | 600 | 7 | 1 | 592 | 1.17% | 87.50% |
| limited/legacy | DeepSeek | G4 | mid | 600 | 5 | 4 | 591 | 0.83% | 55.56% |
| limited/legacy | DeepSeek | G4 | diff | 600 | 4 | 4 | 592 | 0.67% | 50.00% |
| limited/legacy | DeepSeek | legacy llm_only | easy | 119 | 14 | 58 | 47 | 11.76% | 19.44% |
| unlimited | DeepSeek | G1 | easy | 600 | 257 | 324 | 19 | 42.83% | 44.23% |
| unlimited | DeepSeek | G1 | mid | 600 | 210 | 355 | 35 | 35.00% | 37.17% |
| unlimited | DeepSeek | G1 | diff | 600 | 147 | 409 | 44 | 24.50% | 26.44% |
| unlimited | DeepSeek | G4 | easy | 600 | 4 | 2 | 594 | 0.67% | 66.67% |
| unlimited | DeepSeek | G4 | mid | 600 | 12 | 3 | 585 | 2.00% | 80.00% |
| unlimited | DeepSeek | G4 | diff | 600 | 8 | 7 | 585 | 1.33% | 53.33% |
| unlimited | GLM | G1 | easy | 600 | 357 | 192 | 51 | 59.50% | 65.03% |
| unlimited | GLM | G1 | mid | 600 | 270 | 244 | 86 | 45.00% | 52.53% |
| unlimited | GLM | G1 | diff | 600 | 158 | 275 | 167 | 26.33% | 36.49% |
| unlimited | GLM | G4 | easy | 600 | 15 | 17 | 568 | 2.50% | 46.88% |
| unlimited | GLM | G4 | mid | 600 | 24 | 20 | 556 | 4.00% | 54.55% |
| unlimited | GLM | G4 | diff | 600 | 16 | 37 | 547 | 2.67% | 30.19% |
| unlimited | Kimi | G1 | easy | 600 | 154 | 30 | 416 | 25.67% | 83.70% |
| unlimited | Kimi | G1 | mid | 600 | 40 | 20 | 540 | 6.67% | 66.67% |
| unlimited | Kimi | G1 | diff | 600 | 62 | 35 | 503 | 10.33% | 63.92% |
| unlimited | Kimi | G4 | easy | 600 | 117 | 21 | 462 | 19.50% | 84.78% |
| unlimited | Kimi | G4 | mid | 600 | 50 | 20 | 530 | 8.33% | 71.43% |
| unlimited | Kimi | G4 | diff | 600 | 68 | 31 | 501 | 11.33% | 68.69% |
| unlimited | MiniMax | G1 | easy | 200 | 106 | 51 | 43 | 53.00% | 67.52% |
| unlimited | MiniMax | G1 | mid | 200 | 75 | 50 | 75 | 37.50% | 60.00% |
| unlimited | MiniMax | G1 | diff | 200 | 59 | 70 | 71 | 29.50% | 45.74% |
| unlimited | MiniMax | G4 | easy | 200 | 72 | 24 | 104 | 36.00% | 75.00% |
| unlimited | MiniMax | G4 | mid | 200 | 48 | 36 | 116 | 24.00% | 57.14% |
| unlimited | MiniMax | G4 | diff | 200 | 44 | 42 | 114 | 22.00% | 51.16% |
| unlimited | Qwen | G1 | easy | 200 | 33 | 49 | 118 | 16.50% | 40.24% |
| unlimited | Qwen | G1 | mid | 200 | 28 | 41 | 131 | 14.00% | 40.58% |
| unlimited | Qwen | G1 | diff | 200 | 31 | 39 | 130 | 15.50% | 44.29% |
| unlimited | Qwen | G4 | easy | 200 | 31 | 44 | 125 | 15.50% | 41.33% |
| unlimited | Qwen | G4 | mid | 200 | 27 | 43 | 130 | 13.50% | 38.57% |
| unlimited | Qwen | G4 | diff | 200 | 23 | 48 | 129 | 11.50% | 32.39% |

## 7. 每模型汇总

| scope | provider | 模型 | N | Output 正确 | Output 错误 | 无 output | 正确/全部 | 正确/可判定 |
|---|---|---|---:|---:|---:|---:|---:|---:|
| limited/legacy | DeepSeek | deepseek-r1-distill-qwen-1.5b | 619 | 18 | 282 | 319 | 2.91% | 6.00% |
| limited/legacy | DeepSeek | deepseek-v3.2 | 621 | 120 | 195 | 306 | 19.32% | 38.10% |
| limited/legacy | DeepSeek | deepseek-v4.1-flash | 631 | 203 | 70 | 358 | 32.17% | 74.36% |
| limited/legacy | DeepSeek | deepseek-r1-distill-qwen-14b | 610 | 113 | 188 | 309 | 18.52% | 37.54% |
| limited/legacy | DeepSeek | deepseek-r1-distill-qwen-32b | 610 | 109 | 180 | 321 | 17.87% | 37.72% |
| limited/legacy | DeepSeek | deepseek-r1-distill-qwen-7b | 628 | 89 | 217 | 322 | 14.17% | 29.09% |
| unlimited | DeepSeek | deepseek-r1-distill-qwen-1.5b | 600 | 17 | 276 | 307 | 2.83% | 5.80% |
| unlimited | DeepSeek | deepseek-v3.2 | 600 | 100 | 199 | 301 | 16.67% | 33.44% |
| unlimited | DeepSeek | deepseek-v4.1-flash | 600 | 205 | 71 | 324 | 34.17% | 74.28% |
| unlimited | DeepSeek | deepseek-r1-distill-qwen-14b | 600 | 110 | 183 | 307 | 18.33% | 37.54% |
| unlimited | DeepSeek | deepseek-r1-distill-qwen-32b | 600 | 116 | 173 | 311 | 19.33% | 40.14% |
| unlimited | DeepSeek | deepseek-r1-distill-qwen-7b | 600 | 90 | 198 | 312 | 15.00% | 31.25% |
| unlimited | GLM | glm-4.7 | 600 | 171 | 226 | 203 | 28.50% | 43.07% |
| unlimited | GLM | glm-5 | 600 | 108 | 186 | 306 | 18.00% | 36.73% |
| unlimited | GLM | glm-5.1 | 600 | 122 | 178 | 300 | 20.33% | 40.67% |
| unlimited | GLM | glm-5.2 | 600 | 117 | 44 | 439 | 19.50% | 72.67% |
| unlimited | GLM | glm-5.2-fast-preview | 600 | 150 | 94 | 356 | 25.00% | 61.48% |
| unlimited | GLM | glm-5.3 | 600 | 172 | 57 | 371 | 28.67% | 75.11% |
| unlimited | Kimi | kimi-k2-thinking | 600 | 138 | 80 | 382 | 23.00% | 63.30% |
| unlimited | Kimi | kimi-k2.5 | 600 | 96 | 45 | 459 | 16.00% | 68.09% |
| unlimited | Kimi | kimi-k2.6 | 600 | 65 | 7 | 528 | 10.83% | 90.28% |
| unlimited | Kimi | kimi-k2.7-code | 600 | 102 | 15 | 483 | 17.00% | 87.18% |
| unlimited | Kimi | kimi-k2.7-code-highspeed | 600 | 82 | 10 | 508 | 13.67% | 89.13% |
| unlimited | Kimi | kimi-k3 | 600 | 8 | 0 | 592 | 1.33% | 100.00% |
| unlimited | MiniMax | MiniMax-M2.1 | 600 | 168 | 103 | 329 | 28.00% | 61.99% |
| unlimited | MiniMax | MiniMax-M2.5 | 600 | 236 | 170 | 194 | 39.33% | 58.13% |
| unlimited | Qwen | qwen-coder-plus | 600 | 173 | 264 | 163 | 28.83% | 39.59% |
| unlimited | Qwen | qwen-deep-research-2025-12-15 | 600 | 0 | 0 | 600 | 0.00% | NA |

## 8. 恢复结果说明

5,024 条格式失败任务都已有对应恢复尝试。恢复后的严格分类为：95 条严格正确、1,789 条结构化答案错误、678 条仍然 JSON 解析失败、3 条 schema 失败、176 条 policy violation、2,281 条 provider error、2 条传输超时。这里的严格分类只用于解释恢复质量；上面的 Output 统计仍会从可恢复的最终内容中重新判断。

当前全量数据的主要瓶颈已经不只是 JSON 格式：大量恢复尝试最终没有可用 provider output，尤其是 Agent、Kimi、Qwen-deep-research 等模型。因此 `正确/可判定` 必须和覆盖率一起看，不能单独当作模型总体准确率。

## 9. 结论

- 全量恢复数据中，最终 output 语义正确率为 46.29%（仅在 6,909 条有可判定 output 的任务上），按全部 16,919 条任务计算为 18.90%。
- 在 provider 层面，Kimi 的可判定正确率最高，但覆盖率只有 648/3,600；MiniMax 的全任务正确率最高，为 33.67%，覆盖率为 677/1,200。
- GLM 的全任务正确率为 23.33%，且 G1 的覆盖率明显高于 G4；DeepSeek 无限组 G1 为 34.11%，G4 仅 1.33%，后者主要受无 output 影响。
- 不能把 Agent 的高 `正确/可判定` 直接解释为能力更强，因为 Agent 各组的可判定 output 数量非常低。
- 这是恢复后最终 output 的内容分析，不是严格协议合规率，也不是正式统计显著性结论。
