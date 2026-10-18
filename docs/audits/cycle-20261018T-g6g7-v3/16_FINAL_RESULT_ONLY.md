# Final result only

模型：kimi-k2.5；网关/路由外部核验：未获得；账单外部核验：未获得。

历史本地 proxy 费用：G6 6.057783 USD；G7 8.915826 USD；本轮新增 API 费用 0 USD。供应商已核实费用不可得，不能把本地估计当账单，也不能给出安全剩余额度。

G6：原始尝试视图 {'planned': 552, 'completed': 550, 'provider_error': 2, 'source': 'runs/ctflow_single_model/20261017T-g6-kimi-k25-v1/g6_audit/release_review.json'}；规范化响应视图 552/552；revision 分母 138/138 有唯一主原因。主因计数：{'BAD_DECISION': 109, 'VERIFIER_INCONCLUSIVE': 29}；二级原因计数：{'BAD_DECISION': 109, 'REVISED_CLAIM_NULL': 61}。独立数学状态：{'INCONCLUSIVE': 59, 'NOT_SCORED': 61, 'PASS': 18}；handoff 源记录 552 行，但科学释放不可用。

G7：checkpoint 184/184；实际 provider completed 1150/1288；canonical trace-valid 1123/1288；trace-qualified sensitivity 1138/1288；需要真实 provider 调用 138。

Trace 旧 28：边界解释 15，真实最终不一致 13；新尝试恢复 0。

Q：PASS 0、FAIL 0、INCONCLUSIVE 0、NOT_SCORED 1150、INELIGIBLE 138。L/U：L 可评分 0；U 可评分 0；U 不适用 756。

科学统计：仅 DESCRIPTIVE_ONLY，G4-G3 家族配对效应 -0.07246376811594203，95% CI [-0.14492753623188406, -0.007246376811594208]；确认性资格 false。

科学发布：BLOCKED。六项阻塞均已实际审计/修复到其证据边界，但 provider 外部证据、G6 数学/统计、G7 缺失响应、13 条历史 trace、Q、L/U 仍不能宣称解决。

代码与审计：`scripts/audit_repair/`；`docs/audits/cycle-20261018T-g6g7-v3/`；敏感逐行审计：`runs/ctflow_single_model/20261017T-g7-kimi-k25-v1/g7_audit/cycle-20261018T-g6g7-v3/`。
