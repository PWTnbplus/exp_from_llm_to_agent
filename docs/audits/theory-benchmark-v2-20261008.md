# 理论 Benchmark v2 审计记录（2026-10-08）

## 范围

本轮将原 `theory-benchmark-v1` 的 100 个任务扩展为独立的 `theory-benchmark-v2`。v1 数据、清单和原有评测结果保留，不被覆盖。

## 目标分层

- 总数：300
- Level 1（简单）：100
- Level 2（中等）：100
- Level 3（困难）：100
- 理论化学：150
- 理论生物学：150
- 六个“领域×难度”单元格：每格 50

## 数据与隔离

- 公共题面与答案键分离保存。
- 公共题面不包含 `ground_truth`、`verification_code` 和验证状态等答案泄漏字段。
- v2 使用 `Synthetic Mathematical Model` 标注；不冒充真实实验结果或已发表定理。
- 生成器检查任务 ID、题面、数学模型唯一性及分层计数。

## 可复现命令

```bash
python scripts/build_theory_benchmark.py
python -m scientific_discovery.cli theory-validate
python -m pytest -q tests/test_theory_benchmark.py
python -m pytest -q
```

本轮实际结果：`theory-validate` 报告 300 个任务、300 个答案自检通过；旧版显式校验报告 100 个任务、100 个答案自检通过；全量测试为 `72 passed`；独立只读复核中的计数、唯一性、来源标签、答案隔离和 v1 保留检查全部通过。

## 解释边界

本轮验证的是数据结构、答案隔离和 checker 自洽性，不是 LLM 或 Agent 的科学能力结果。正式 API 评测仍须在明确授权、冻结版本、固定预算和有成本审计的条件下运行；本轮没有据此声称付费科学实验结果。
