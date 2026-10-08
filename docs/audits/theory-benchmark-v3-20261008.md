# 纯理论化学 Benchmark v3 审计记录（2026-10-08）

## 范围

本轮在保留 v1（100 条）和 v2（化学/生物混合 300 条）的基础上，新增纯化学 v3。v3 共 300 条，全部标注为 Theoretical Chemistry。

## 目标分层

- 总数：300
- Level 1（简单）：100
- Level 2（中等）：100
- Level 3（困难）：100
- 理论化学：300
- 理论生物学：0
- 每个化学领域×难度单元格：100

## 数据与隔离

- 公共题面与答案键分离保存。
- 公共题面不包含 ground_truth、verification_code 和验证状态等答案泄漏字段。
- 任务覆盖反应动力学、热力学、相平衡、酸碱与溶液、无机与配位、光谱、电化学、量子化学、表面与催化、输运、聚合物和胶体等纯化学子领域。
- 所有新任务都是 Synthetic Mathematical Model，不冒充真实实验结果或已发表定理。

## 可复现命令

~~~
python scripts/build_theory_benchmark.py
python -m scientific_discovery.cli theory-validate
python -m pytest -q tests/test_theory_benchmark.py
python -m pytest -q
~~~

本轮未进行付费 API 科学运行；Mock 运行只能验证流程。

实际验证结果：默认 v3 的 theory-validate 报告 300 个任务、300 个答案自检通过；显式 v2 复核仍报告 300 个任务、300 个答案自检通过；全量测试为 73 passed；独立只读复核通过。
