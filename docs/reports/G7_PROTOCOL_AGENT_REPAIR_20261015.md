# G7 协议与 Agent 初始信息修复审查（cycle 32）

本轮只做本地工程修复和只读审计，没有发起 provider 请求、付费实验或修改历史 G6/G7 结果。

## 已修复

- `run_g7_failure_localization.py` 的 fail-closed preflight 现在在 provider 构造和 key-file 读取前执行；递归提示文本检查覆盖 routing metadata、oracle、answer-key、ground-truth、verification 等私有字段，并对字段大小写不敏感。
- preflight 拒绝缺失 `run_id`/`checkpoint_id`/`case_id`、重复 case/run/label ID 和非法 `model_visible`，避免后续 runner 以异常代替协议失败。
- `SingleAgentRunner` 与 LLM-only runner 使用同一份公开初始观测；Agent 将其作为初始 history，并持久化到公开 metadata。

## 审计证据

- focused regression：15 passed；host suite：125 passed。
- corrected G7 preflight：92 public cases、1288 plan rows、184 checkpoints，routing/private hits 均为 0，`provider_calls_made=false`。
- corrected G7 trace/Q audit：1288 rows，1285 completed、3 provider_error；terminal failures 保留，Q trace-backed valid=20/1288，`confirmatory_reuse_allowed=false`。
- 只读契约检查确认 preflight 位于 provider 构造之前，Agent 调用 `get_initial_observations()`；未执行外部 provider。

## 未完成门禁

G7 历史 provider failures/Q 覆盖仍未达到 confirmatory 要求；原始 routing contamination 永久非确认性。billing export、immutable model snapshot、upstream provenance、独立 provider/Q review 和 machine gate attestation 仍缺失。详见 [cycle audit](../audits/cycle-20261015T172856Z-32/audit.json) 与状态账本。
