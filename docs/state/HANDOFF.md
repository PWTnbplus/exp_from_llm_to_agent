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

开放/未验证：9。已验证：16。
不要在没有回归证据的情况下重复已验证工作。
不要把审查报告中的沉默视为问题已解决。
下一优先级问题：
- ISSUE-000000000002 P1 BLOCKED 尝试次数=2：Real-provider pilot and retry/cost behavior are unverified；修复=Keep the paid gate closed. Obtain explicit authorization, a positive hard USD ceiling, independently verifiable model/billing evidence, and an independent isolation review before any real-provider pilot.
- ISSUE-000000000003 P1 BLOCKED 尝试次数=1：Upstream provenance and GitHub delivery are externally blocked；修复=Restore network/Git credentials, independently verify the configured NewtonBench commit and license against the upstream remote, then re-run G0 and verify the feature-branch remote state.
- ISSUE-000000000004 P1 BLOCKED 尝试次数=0：Formal statistical validity is not established；修复=Retain the fail-closed G6/G7 input guards and obtain independent statistical and mathematical review before any confirmatory inference or scientific release.
- ISSUE-ff97c7c89112 P1 RESOLVED_UNVERIFIED 尝试次数=0：G6 audit-g5 found 1309 proof_graph.json files and all 1309 had events.jsonl, steps.jsonl, summary.js；修复=Retain the fail-closed input guards and obtain an independent external mathematical review of the verifier; release only the 23-family corrected subset and never synthesize or restore TB-L1-010.
- ISSUE-ad61f025976a P1 RESOLVED_UNVERIFIED 尝试次数=0：G6 project_preflight returned BLOCKED_REAL_RUN with missing verified model snapshot, missing positiv；修复=Obtain an independently verifiable immutable model snapshot or gateway weight fingerprint and billing evidence; retain the current truthful preflight as a pilot-readiness attestation, not as full RUN_COMPLETE acceptance.
- ISSUE-1f8c2b6a4d90 P1 BLOCKED 尝试次数=2：All eligible G6 public proof graphs have no dependency edges for G7 localization；修复=Keep the reduced denominator structural and non-confirmatory. Obtain an independently audited complete dependency/state dataset and Q/math review before any G8 causal, L/U, or scientific release claim.
- ISSUE-3d7a9c1e5b20 P1 BLOCKED 尝试次数=21：G7 provider execution has terminal failures and low independently valid Q coverage；修复=Keep historical G7 artifacts non-confirmatory. Restore authorized provider access only with explicit paid authorization and a hard ceiling, run a separately frozen non-pooled batch using the repaired trace contract, and 
- ISSUE-f9171bb760b1 P1 RESOLVED_UNVERIFIED 尝试次数=0：No frozen, auditable G8 real/sham/off/extra adapter is present；修复=Retain the adapter and audit artifacts; obtain independently verifiable immutable model-weight/gateway fingerprint and billing evidence before treating the paid run as fully verified.
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
