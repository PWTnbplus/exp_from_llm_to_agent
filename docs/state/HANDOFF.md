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

开放/未验证：10。已验证：29。
不要在没有回归证据的情况下重复已验证工作。
不要把审查报告中的沉默视为问题已解决。
下一优先级问题：
- ISSUE-000000000002 P1 BLOCKED 尝试次数=3：Real-provider pilot and retry/cost behavior are unverified；修复=Obtain provider-verifiable billing/usage reconciliation and immutable route or weight identity; keep scientific release closed until independently verified.
- ISSUE-000000000003 P1 RESOLVED_UNVERIFIED 尝试次数=2：Upstream provenance and GitHub delivery are externally blocked；修复=Restore an authorized network path or publish the local commit through an independently verified upstream channel; do not claim remote delivery until git ls-remote confirms it.
- ISSUE-000000000004 P1 BLOCKED 尝试次数=1：Formal statistical validity is not established；修复=Retain the 24/24 public calibration as supplementary evidence and obtain an independent domain-grade blinded review for the frozen 92-case cohort before scientific release.
- ISSUE-ff97c7c89112 P1 RESOLVED_UNVERIFIED 尝试次数=0：G6 audit-g5 found 1309 proof_graph.json files and all 1309 had events.jsonl, steps.jsonl, summary.js；修复=Keep the historical 43 failures and new correction evidence separate; obtain independent mathematical/domain review and a protocol-approved reanalysis before changing G6 scientific status.
- ISSUE-ad61f025976a P1 RESOLVED_UNVERIFIED 尝试次数=0：G6 project_preflight returned BLOCKED_REAL_RUN with missing verified model snapshot, missing positiv；修复=Obtain an independently verifiable immutable model snapshot or gateway weight fingerprint and billing evidence; retain the current truthful preflight as a pilot-readiness attestation, not as full RUN_COMPLETE acceptance.
- ISSUE-1f8c2b6a4d90 P1 BLOCKED 尝试次数=3：All eligible G6 public proof graphs have no dependency edges for G7 localization；修复=Retain the paired calibration and obtain protocol-approved causal validation on the formal LU/U population; do not pool the calibration into the historical G7 denominator.
- ISSUE-3d7a9c1e5b20 P1 BLOCKED 尝试次数=22：G7 provider execution has terminal failures and low independently valid Q coverage；修复=Keep new execution evidence separate from the frozen historical denominator and obtain independent scientific review before changing the formal gate.
- ISSUE-f9171bb760b1 P1 RESOLVED_UNVERIFIED 尝试次数=0：No frozen, auditable G8 real/sham/off/extra adapter is present；修复=Retain the adapter and audit artifacts; obtain independently verifiable immutable model-weight/gateway fingerprint and billing evidence before treating the paid run as fully verified.
- ISSUE-7c2d4e9a10bf P1 RESOLVED_UNVERIFIED 尝试次数=2：G7 revalidation has trace lifecycle inconsistencies after append-only retry recovery；修复=Keep historical lifecycle failures and corrected retry evidence in separate append-only views; require protocol-approved reanalysis for any formal denominator change.
- ISSUE-000000000005 P2 OPEN 尝试次数=0：Classical baseline is only an extension interface；修复=Implement only if a classical comparison is added to the study; otherwise keep it explicitly out of the claims.
已验证的已完成工作（避免重复）：
- G1-G5 execution policy and theory contamination controls：Policy boundary tests, provider retry rejection, strict answer isolation, 100-task validation, and 40/30/30 contamination audit are implemented. Full host suite passed 80 tests.
- Corrected G6 protocol and audited G7 failure-localization execution：G6 corrected 23-family run and G7 16-worker run have canonical merge, independent audits, hashes, and explicit terminal-failure accounting; host suite and package tests pass. Scien

## 权威参考

- `.agents/skills/scientific-law-recovery/SKILL.md`（当前 V2 指令）
- `.agents/skills/scientific-law-autopilot/SKILL.md`（保留的 V1 指令）
- V1 `references/` 下的两份原始完整规范
- `docs/audits/`（周期级证据）

**重要：**状态文件只报告已验证事实；不要假设当前运行的 Codex 能访问之前的聊天记录。
