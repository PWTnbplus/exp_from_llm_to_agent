# V9 内部机器证据闸门

- 生成时间：`2026-10-20T03:50:20.721058+00:00`
- 基础模型：`kimi-k2.5`（only_model=true）
- 内部机器状态：`UNLOCKED`
- 正式历史科学发布：`RETAINED_BLOCKED`

## 内部闸门

- `V9_G6_Q_LU_G7`: `True`
- `G7_PROSPECTIVE_HISTORY_PAIR`: `True`
- `G8_SINGLE_KIMI`: `True`
- `G8_5_PROSPECTIVE`: `True`
- `ENGINEERING_LEDGER_LOCK`: `True`

## 实际结果

- V9：104 次真实 Kimi 调用；G6 独立数值证书 32/32；Q 8/8；LU/U REAL=4/4、CONTROL=0/4、SHAM=0/4；G7 repair D3 语义 3/4、严格 token 指标 0/4。
- G7 前瞻性 history pair：2 对、4 条记录，same-state/same-evidence 结构审计通过；资格为 `NO_PROSPECTIVE_NOT_HISTORICAL`。
- G8：真实 Kimi 工程队列已完成；正式 ITT 的 24 个技术失败保留，未从分母删除。
- G8.5：前瞻 pilot 8/8 完成，四臂各 2/2；private truth 扫描 0；不作为历史确认。

## 锁定边界

工程执行锁已通过只读 SQLite integrity_check；正式科学发布锁仍保留，因为历史证据与外部供应商证明不能由内部重跑伪造替代。

## 复算

- 机器 JSON：`docs/audits/cycle-20261020T-kimi-internal-machine-gate/INTERNAL_MACHINE_GATE.json`
- 源码：`scripts/v9/internal_machine_gate.py`
