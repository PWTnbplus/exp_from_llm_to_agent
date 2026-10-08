# 下一位 Codex Agent 的交接说明

## 从这里开始——不要重复最初的实现过程

1. 检查 `git status`、分支、远程仓库和最近提交；保留用户未提交的工作。
2. 阅读 `docs/state/issues.json` 和 `docs/state/UNRESOLVED_REPORT.md`。
3. 阅读本交接说明和已验证完成工作。除非有证据要求，否则不要重复已固定的上游审计、适配器和测试。
4. 修复**一个最高优先级的未解决问题**；运行定向检查、对抗测试，然后运行宿主回归测试。
5. 审查者必须明确验证问题 ID。沉默不是修复。更新状态台账和问题报告。
6. 将已审查更新提交并推送到获授权的特性分支；报告推送失败。
7. 仅当没有遗留问题时，才继续下一个未验证的原始项目门禁。

**下一问题（Next issue:）：** ISSUE-000000000002 / P1 / Real-provider pilot and retry/cost behavior are unverified

## 当前状态摘要

开放/未验证：4。已验证：1。
不要在没有回归证据的情况下重复已验证工作。
不要把审查报告中的沉默视为问题已解决。
下一优先级问题：
- ISSUE-000000000002 P1 BLOCKED 尝试次数=1：Real-provider pilot and retry/cost behavior are unverified；修复=With explicit authorization and a hard spend ceiling, run a minimal provider smoke test, archive redacted traces, and rerun the isolation audit.
- ISSUE-000000000003 P1 BLOCKED 尝试次数=1：Upstream provenance and GitHub delivery are externally blocked；修复=Restore network/Git credentials, verify the configured upstream commit and license, then push the feature branch and confirm remote state.
- ISSUE-000000000004 P1 RESOLVED_UNVERIFIED 尝试次数=0：Formal statistical validity is not established；修复=Implement plan-driven pilot/formal execution with exact task counts, frozen manifest SHA-256, five registered replicates per arm, explicit persisted replicate_index, rejection of deviations, and analysis against the froz
- ISSUE-000000000005 P2 OPEN 尝试次数=0：Classical baseline is only an extension interface；修复=Implement only if a classical comparison is added to the study; otherwise keep it explicitly out of the claims.
已验证的已完成工作（避免重复）：
- G1-G5 execution policy and theory contamination controls：Policy boundary tests, provider retry rejection, strict answer isolation, 100-task validation, and 40/30/30 contamination audit are implemented. Full host suite passed 80 tests.

## 权威参考

- `.agents/skills/scientific-law-recovery/SKILL.md`（当前 V2 指令）
- `.agents/skills/scientific-law-autopilot/SKILL.md`（保留的 V1 指令）
- V1 `references/` 下的两份原始完整规范
- `docs/audits/`（周期级证据）

**重要：**状态文件只报告已验证事实；不要假设当前运行的 Codex 能访问之前的聊天记录。
