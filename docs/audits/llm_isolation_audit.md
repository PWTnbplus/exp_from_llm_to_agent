# LLM-only 隔离审计

审计日期：2026-10-08  
范围：NewtonBench 直接测量子集、`llm_only` runner  
状态：已实现协议 PASS；真实 provider 执行尚未测试

## 检查的协议

LLM-only 实验臂必须在观察任何结果前选择完整实验计划；随后在没有 provider 引用的情况下执行冻结计划；批处理完成后只能进行一次最终 provider 调用；不得暴露工具。

## 证据

- `tests/test_llm_isolation.py`：模拟观测值变化时，plan hash 和 action 序列保持不变；规划请求中没有中间观测；两个 provider 调用的 `tools` 均为 `None`；API 调用预算耗尽时会在 provider 调用前阻止请求。
- `tests/test_provider_trace.py`：离线模拟三次重试，确认每次重试都被记录，并且不会写入传入的 API key。
- `python -m pytest -q`：2026-10-08 执行结果为 `14 passed`。
- `results/pilot_final/llm_only_newtonbench__m0_gravity__easy__v1__vanilla_equation.json` 包含 `metadata.protocol=three_phase_open_loop`、`intermediate_observations_sent_to_model=false`、两个 `metadata.provider_trace` 条目，并且两个请求的 `tools=null`。
- 对应的 Agent 结果也包含脱敏 provider trace，但使用显式的 `run_experiment` 工具 schema，因此 API 层面的差异可被检查。

## 边界

provider trace 在 provider 边界进行脱敏，绝不包含 API key。当前结果文件包含确定性的 Mock trace；没有执行付费 API。因此，本审计证明的是软件协议及其 Mock 回归证据，不是关于真实模型科学行为的结论。

## 后续工作

正式使用前，应在记录的真实 provider dry/pilot 结果上重复本审计，并确认重试/错误条目、模型名称、token 用量、延迟和成本均被保留，同时不包含任何 secret。
