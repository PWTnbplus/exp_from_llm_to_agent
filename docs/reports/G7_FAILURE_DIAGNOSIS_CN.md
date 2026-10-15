# G7 终端失败与 Q 无效性诊断报告

本报告是只读取证，不修复或重解释历史结果，不把重试结果与原始 G7 pooling，也不做科学真值判断。

## 运行级指标

| 运行 | MODEL_REQUEST | 记录的 ERROR | Q 有效 | routing metadata 命中 | 结论边界 |
|---|---:|---:|---:|---:|---|
| 原始 G7 | 2960 | 119 | 3/1288 | `cf_type` 2960；`theory_family_id` 2960 | 原始 formal run 违反 prompt 隔离门禁，不作确认性结论 |
| retry1 | 646 | 36 | 2/295 | 0 | 仍有 provider 契约失败，未与原始合并 |
| retry2 | 276 | 20 | 0/110 | 0 | canonical 状态 102/110，8 个缺失状态已另列入 retry3 |
| retry3 | 68 | 7 | 0/31 | 0 | 31/31 状态已合并，但 15 条仍为终端失败 |

## 终端错误分类

| 运行 | 主要错误证据 |
|---|---|
| 原始 G7 | `no valid JSON response` 44；`missing stage Q` 39；`missing stages object` 12；`missing stage V` 9；`missing stage U` 7；非 JSON object 7；invalid V 1 |
| retry1 | `no valid JSON response` 28；`missing stage Q` 4；非 JSON object 2；missing U/V 各 1 |
| retry2 | `no valid JSON response` 18；非 JSON object 1；missing Q 1 |
| retry3 | `no valid JSON response` 6；missing Q 1 |

这些是 provider 返回契约失败的原始事件字符串；不能进一步推断服务端的未记录原因。runner 按规范将 malformed output 保留为 `provider_error`，没有静默修复。

## 修复与剩余门禁

- 已修复 runner 的 model-facing prompt：`cf_type` 和 `theory_family_id` 不再发送给模型；retry1–retry3 的 990 个模型请求均为 0 命中。
- 原始 G7 的 5920 次 routing metadata 命中不可从历史 trace 中删除，因此该原始 formal run 保持不可确认状态。
- provider 终端失败与独立 Q 无效性仍未解除；任何后续 formal run 必须先通过 prompt preflight，并继续保留失败项。

证据文件：[cycle-20261015T051500Z-25/audit.json](../audits/cycle-20261015T051500Z-25/audit.json)。
