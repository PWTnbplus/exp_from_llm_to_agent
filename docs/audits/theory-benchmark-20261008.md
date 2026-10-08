# 理论化学/理论生物学 Benchmark 重构审计

日期：2026-10-08（Asia/Hong_Kong）

## 交付范围

- 新增独立版本 `theory-benchmark-v1`，不覆盖原 NewtonBench 任务和评测接口。
- 生成 100 条公开题面与分离的答案键；所有人为构造实例均标记为 `Synthetic Mathematical Model`。
- 新增确定性数值/表达式 checker、答案泄漏检查、四种 runner 模式、批处理、统计汇总和四张图表接口。
- 将 SymPy 加入项目依赖，并为真实 provider 增加发送前硬成本上限检查。

## 验收证据

| 检查 | 结果 |
|---|---|
| `python -m scientific_discovery.cli theory-validate` | 通过；100 条答案键自检通过 |
| 任务总数 | 100 |
| Level 1 / 2 / 3 | 34 / 33 / 33 |
| 理论化学 / 理论生物学 | 50 / 50 |
| 只读独立检查 | 通过；计数、题目唯一性、来源标签、答案自检均通过 |
| `python -m pytest -q` | 68 passed |
| Mock 批处理 2 条 Level 1 任务 | 2 条工程运行完成；故意使用空答案，正确数为 0，不作为科学结果 |
| `git diff --check` | 通过；仅有 Git 的换行风格提示 |

## 关键科学边界

当前 100 条任务是可复现的合成理论实例，答案键具有确定性 checker；这证明数据和验证工程可运行，不证明任何真实化学/生物经验规律，也不证明 Agent 优于 LLM。Level 3 中的线性化、数值求根和稳定性结论都保留了适用范围。

正式比较仍需冻结模型、任务版本、重复次数、预算匹配和统计方案，并分别保留模型失败、验证器失败和基础设施失败。未进行付费科学批次，也未生成真实模型性能结果。

## 尚未完成事项

- CTFlow model matrix 的 `runner_command` 仍为空；它不能把本 Benchmark 的接口自动宣称为已验证的 NewtonBench 科学 runner。
- 外部 V2 issue ledger 中的真实 provider pilot、上游 provenance、正式聚类统计和远程交付问题仍按原状态保持未解决。
- 本轮没有提交或推送 Git；工作树中还存在此前用户/代理的未提交修改。
