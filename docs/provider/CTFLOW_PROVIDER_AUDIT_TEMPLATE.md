# CTFlow 提供方集成审计（未验证模板）

用户提供的提供方文档：https://token.ctflow.cn/tokendocs

## 证据门禁 G8：提供方协议
- 文档获取日期及精确不可变摘录/引用：NOT VERIFIED
- 已验证的 API 基础 URL：NOT VERIFIED
- 鉴权方案：NOT VERIFIED
- 模型列表端点：NOT VERIFIED
- 生成端点：NOT VERIFIED
- 请求/响应 JSON 结构：NOT VERIFIED
- 用户 key 下可用的模型 ID：NOT VERIFIED
- 提供方定价/货币/速率限制：NOT VERIFIED
- 模型别名和上下文窗口：NOT VERIFIED
- 是否支持结构化输出/工具调用：NOT VERIFIED

不要从名称相似但无关的服务复制协议假设。代码中包含的是一个*临时的同源 OpenAI 兼容适配器假设*，不是已验证的服务合同。

## G9：选择/模型兼容性
- `/models` 目录响应已成功解析：NOT TESTED
- 每个精确模型 ID 的 `chat/completions` 响应：NOT TESTED
- 不支持模型的优雅错误处理：仅完成本地 Mock 测试

## G10：配对科学并发
- 同一模型获得匹配的 LLM-only 和 Agent 路径，使用相同科学任务和预算：已规划
- 并行调度下的独立输出隔离：已完成本地测试
- 真实提供方并发行为和 429 限制：NOT TESTED

## G11：科学 runner 与成本
- 已集成真实 NewtonBench Adapter：NOT TESTED
- LLM-only 冻结计划已针对真实 API 验证：NOT TESTED
- Agent 基于观测条件的动作已针对真实 API 验证：NOT TESTED
- 真实 runner 在付费调用前强制执行总成本上限：NOT TESTED
- 实际目标官方评估器验证：NOT TESTED

只有在存在已执行证据时，才能将 G8–G11 标记为 PASS。应记录 HTTP 状态和 schema 结构，但不得记录 token 或 secret。绝不要在此写入 API key。
