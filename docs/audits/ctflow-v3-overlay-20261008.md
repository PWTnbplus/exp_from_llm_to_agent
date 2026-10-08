# CTFlow V3 覆盖层执行审计

日期：2026-10-08（Asia/Hong_Kong）

## 范围

- 以非破坏性覆盖层方式应用 CTFlow V3 补充 skill。
- 保留现有 V2 问题台账和此前未提交的项目修改。
- 未提供 API key，未发起付费提供方请求，也未生成科学结果。

## 证据

| 检查项 | 结果 |
|---|---|
| `python scripts/recovery_state.py bootstrap` | 导入 0 份未见过的审计；仍有 5 个活跃/未验证问题 |
| CTFlow 可达性探测 | `GET https://token.ctflow.cn/v1/models` 返回 HTTP 401；端点仍未验证 |
| CTFlow 文档获取 | 当前网络工具无法访问 `https://token.ctflow.cn/tokendocs` |
| `python -m pytest -q tests/test_evaluator.py tests/test_ctflow_matrix.py` | 24 项通过 |
| `python -m pytest -q` | 62 项通过 |
| 使用 3 个手工 ID 执行 `python scripts/model_matrix.py plan` | 计划了 3 组匹配模型；`runner_integrated=false` |
| 付费矩阵运行 | 未开始；没有已选且已验证的模型、真实 runner 或正数硬性成本上限 |

## 问题处置

`ISSUE-000000000001` 的状态为 `RESOLVED_UNVERIFIED`：确定性的 canonical-AST
结构评分、合法的确定性 OOD 评分、机制有效性以及锁定的 `scoring-v1` 阈值均已实现并通过宿主测试。独立只读审查已检查受影响代码，但在返回所需结构化处置结果前超时，因此该问题有意保持为非 `VERIFIED`。

## CTFlow 门禁状态

G8 提供方协议、G9 模型兼容性、G10 真实提供方并发，以及 G11 真实 runner/成本/科学审计仍为 `NOT TESTED`。临时的同源 OpenAI 兼容适配器不得被视为已验证的 CTFlow 合同。

## 交付

本次执行未进行提交或远程推送。工作树中已有未提交修改；远程交付需要单独审查的 WIP 周期和已验证的 Git 写入权限。
