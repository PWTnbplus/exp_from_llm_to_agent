# CTFlow 提供方集成审计

审计日期：2026-10-08（Asia/Hong_Kong）
审计范围：模型目录鉴权、精确模型兼容性预检和科学矩阵安全门禁。
密钥处理：仅从本地文件读取到当前进程环境；未写入报告、配置、日志或 Git。

## 已验证的运行时证据

| 检查项 | 结果 |
|---|---|
| 未携带凭据的 `GET https://token.ctflow.cn/v1/models` | HTTP 401；同源目录路径可达，但协议仍需验证 |
| 携带本地凭据的 `GET https://token.ctflow.cn/v1/models` | HTTP 200；响应成功解析为 182 个唯一模型 ID |
| 选定模型 | `deepseek-v3.2`、`qwen3.5-plus`、`glm-5.2` |
| `deepseek-v3.2` 最小生成预检 | PASS |
| `qwen3.5-plus` 最小生成预检 | PASS |
| `glm-5.2` 最小生成预检 | PASS |
| 重定向处理 | 代码拒绝重定向，不向重定向目标转发凭据 |

最小生成预检使用精确模型 ID、`stream=false`、`max_tokens=8` 和短消息；只验证响应为 JSON 且包含非空 `choices`，不构成科学实验结果或官方兼容性认证。

## 尚未验证的提供方属性

官方文档、正式 API 基础 URL 的权威来源、定价/货币、速率限制、上下文窗口、结构化输出/工具调用支持、完整错误结构和重试语义仍未完成独立文档核验。当前成功证据只支持本次运行中探测到的同源路径和请求形状。

## 科学矩阵门禁

本地计划为 3 组模型配对，每组包含 `llm_only` 和 `agent`，共 6 个匹配运行槽位；计划输出明确记录 `runner_integrated=false`。

执行 `python scripts/model_matrix.py run --allow-paid` 时，在发起矩阵 API 调用前即被拒绝，原因是：

- `configs/model_matrix.json` 的 `runner_command` 为空；
- `runner_supports_budget_enforcement=false`；
- `max_total_cost_usd=0.0`；
- 尚无符合要求的真实 NewtonBench 科学 runner 和逐运行成本硬上限。

因此，本次只完成了提供方目录和最小兼容性预检，没有进行科学 pilot、正式矩阵运行或科学结论推断。原有 `ISSUE-000000000002`（真实提供方 pilot 与重试/成本行为未验证）继续保持开放。
