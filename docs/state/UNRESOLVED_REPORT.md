# 科学定律自动驾驶——未解决问题报告

生成时间（UTC）：2026-10-08T11:17:55+00:00

- 开放/阻塞/未验证：**4**
- 已验证修复：**1**
- 已验证完成里程碑：**1**
- 未验证科学门禁：**G0, G1, G2, G3, G4, G5, G6, G7**

## 未解决和阻塞问题

### ISSUE-000000000002 — P1 — BLOCKED
- 描述：Real-provider pilot and retry/cost behavior are unverified
- 证据：No real API request was launched; only provider failure paths are unit-tested.
- 必需修复：With explicit authorization and a hard spend ceiling, run a minimal provider smoke test, archive redacted traces, and rerun the isolation audit.
- 尝试次数：1
- 来源：legacy:docs/audits/2026-10-08_supervisor_report_autopilot_cycle_01.md
- 阻塞原因：A real-provider pilot requires explicit authorization and a positive hard cost ceiling; no such pilot parameters were supplied.

### ISSUE-000000000003 — P1 — BLOCKED
- 描述：Upstream provenance and GitHub delivery are externally blocked
- 证据：Both git ls-remote commands failed with proxy connection errors; vendored NewtonBench is not a separate Git checkout.
- 必需修复：Restore network/Git credentials, verify the configured upstream commit and license, then push the feature branch and confirm remote state.
- 尝试次数：1
- 来源：legacy:docs/audits/2026-10-08_supervisor_report_autopilot_cycle_01.md
- 阻塞原因：Remote provenance and delivery require a successful network/credential check and verified push.

### ISSUE-000000000004 — P1 — RESOLVED_UNVERIFIED
- 描述：Formal statistical validity is not established
- 证据：configs/statistical_plan.json declares frozen 12/72 task strata and five repeats per arm, but src/scientific_discovery/cli.py only provides a one-run pilot path, accepts arbitrary manifests and limits, has no formal command, and does not execute repeat loops or assign replicate indices. Analysis also operates only on result files and does not join the registered manifest to synthesize missing task-runs; repeated rows lack persisted replicate identity.
- 必需修复：Implement plan-driven pilot/formal execution with exact task counts, frozen manifest SHA-256, five registered replicates per arm, explicit persisted replicate_index, rejection of deviations, and analysis against the frozen manifest multiplied by repeats and arms. Add adversarial tests for unequal/incomplete clusters, failures, repeats, missing files, domain strata and complexity strata.
- 尝试次数：0
- 来源：legacy:docs/audits/2026-10-08_supervisor_report_autopilot_cycle_01.md
- 阻塞原因：未记录

### ISSUE-000000000005 — P2 — OPEN
- 描述：Classical baseline is only an extension interface
- 证据：src/scientific_discovery/evaluation/classical.py retains NotImplementedError.
- 必需修复：Implement only if a classical comparison is added to the study; otherwise keep it explicitly out of the claims.
- 尝试次数：0
- 来源：legacy:docs/audits/2026-10-08_supervisor_report_autopilot_cycle_01.md
- 阻塞原因：未记录

## 已验证解决的问题

- **ISSUE-000000000001**（P1）：Formal scientific scoring is incomplete——`python -m pytest -q`；Independent read-only review confirmed that the evaluator binds numeric validation, legal OOD fit, canonical-AST structural recovery, and mechanistic validity; adversarial evaluator tests cover wrong constants, illegal code, finite-region overfit, malformed output, algebraic equivalence, and local constants. The host suite passed 70 tests, including tests/test_evaluator.py::test_algebraically_equivalent_code_passes_structural_and_mechanistic_criteria and tests/test_evaluator.py::test_numeric_fit_alone_cannot_pass_with_ood_or_structural_failure.

## 可复用的已验证完成工作（不要重新构建）

- G1-G5 execution policy and theory contamination controls：Policy boundary tests, provider retry rejection, strict answer isolation, 100-task validation, and 40/30/30 contamination audit are implemented. Full host suite passed 80 tests. | 验证：`python -m pytest -q` | 提交：`未固定`

## 科学性注意事项

绿色单元测试只能验证工程门禁，不能证明 Agent 在科学发现上优于其他方法。
Mock 输出不是科学证据。不得使用正式测试任务进行提示词调优。
