# G6 protocol-v2 重审报告（非确认性）

## 目的与来源

本报告专门对应当前 canonical corrected v2 artifact：

`results/g6_counterfactual/protocol-g3tools-v2-20261014T030000Z`

输入文件为：

- `run_plan.jsonl`（552 行）
- `private_oracle.jsonl`（92 行）
- `responses_audited.jsonl`（552 行）

使用的分析命令为：

```text
E:/resources/python/python.exe -X utf8 scripts/analyze_g6_clustered.py --plan <v2>/run_plan.jsonl --private <v2>/private_oracle.jsonl --responses <v2>/responses_audited.jsonl --out <temporary-output>
```

分析输出状态为 `ANALYZED_PENDING_INDEPENDENT_STATISTICAL_REVIEW`。这不是确认性统计结果，也不允许据此发布 Agent 优势或科学机制结论。

## v2 输入与资源审计

| 项目 | 数值 |
|---|---:|
| corrected family | 23 |
| CF | CF1–CF4 |
| replicate | 3（0/1/2） |
| arm | G3/G4 |
| plan / response / private / handoff | 552 / 552 / 92 / 552 |
| G3 / G4 plan rows | 276 / 276 |
| 每个 arm×CF | 69 |
| model requests / responses | 1,826 / 1,826 |
| tool calls / results | 1,796 / 1,796 |
| tokens | 3,454,449 |
| trace cost | USD 6.057783 |
| revision valid | 0 / 138 |
| structural release review | pass |
| scientific release allowed | false |

v2 release-review 中的输入哈希为：

- `run_plan.jsonl`: `c60b14205f061fa2178b9d0a42074d9957a460bea2cf4e06b841acbe4b0bbde0`
- `public_cases.jsonl`: `1bffc3769523e437cc7e4ea5cff22f4eb2d42cd3500299f914cb03ec36b6063f`
- `private_oracle.jsonl`: `e966efbadffea604d4de735a0323dbb5ffb2593e510bb8a456cb84422258d6c0`
- `responses_audited.jsonl`: `97022fa9ac84dad61c24c98fbc1fee2ba2b357ee853eccd9614cc348da8312fa`

## v2 paired-family diagnostic metrics

| CF | G3 正确/69 | G3 准确率 | G4 正确/69 | G4 准确率 | G4−G3 | family bootstrap 95% CI | McNemar p |
|---|---:|---:|---:|---:|---:|---|---:|
| CF1 | 39 | 56.522% | 45 | 65.217% | +8.696 pp | [-2.899, 18.841] pp | 0.263176 |
| CF2 | 69 | 100.000% | 69 | 100.000% | 0.000 pp | [0.000, 0.000] pp | 不适用 |
| CF3 | 32 | 46.377% | 30 | 43.478% | -2.899 pp | [-15.942, 10.145] pp | 0.838820 |
| CF4 | 41 | 59.420% | 50 | 72.464% | +13.043 pp | [0.000, 27.536] pp | 0.162756 |
| **ALL** | **181/276** | **65.580%** | **194/276** | **70.290%** | **+4.710 pp** | **[-0.725, 9.783] pp** | **0.171061** |

`CF3` 的 revision validity 仍须与 decision accuracy 分开解释；本 v2 batch 的 revision valid 为 `0/138`。

## 与旧报告的来源边界

`docs/reports/G0_G7_COMPLETE_DATA_CN_20261015.md`、`G0_G7_METRICS_CN_REPORT.md` 和 `G0_G8_TABULAR_DATA_CN.md` 中的旧 G6 表（例如 CF1=37/43、CF3=44/25、ALL=191/186）可由旧输入 `results/g6_counterfactual/formal-20261013T000000Z/run_plan_verified23.jsonl`、`private_oracle_verified23.jsonl`、`responses_verified23.jsonl` 重现；它们不是当前 v2 三文件输入的指标。旧文件保留不改，避免篡改历史快照；本报告是 v2 指标的明确来源修正。

## 科学门禁

G0/G6/G7 仍为 `BLOCKED`。上游 provenance、独立数学/统计复核、immutable model weight fingerprint、独立 billing evidence、G7 独立 Q/dependency 复核仍缺失。没有 provider 调用、付费实验、确认性推断或科学真值结论。
