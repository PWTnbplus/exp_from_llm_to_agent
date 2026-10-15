# 科学定律自动驾驶——未解决问题报告

生成时间（UTC）：2026-10-15T05:10:25+00:00

- 开放/阻塞/未验证：**10**
- 已验证修复：**2**
- 已验证完成里程碑：**2**
- 未验证科学门禁：**G0, G1, G2, G3, G4, G5, G6, G7**

## 未解决和阻塞问题

### ISSUE-3d7a9c1e5b20 — P1 — IN_PROGRESS
- 描述：G7 provider execution has terminal failures and low independently valid Q coverage
- 证据：Original canonical G7: 1288 planned fork IDs, 993 completed, 217 checkpoint_missing, 78 provider_error, 153 completed checkpoints, 31 checkpoint provider errors, and 3/1288 independently valid Q rows. Separately frozen non-pooled terminal retries covered 295 rows in retry1 (185 completed, 90 checkpoint_missing, 20 provider_error, Q 2/295), 110 rows in retry2 (79 completed, 20 checkpoint_missing, 3 provider_error, Q 0/110), and 31 rows in retry3 (16 completed, 12 checkpoint_missing, 3 provider_error, Q 0/31). Retry manifests, source mappings, canonical merges, and hashes are recorded under results/g7_failure_localization/formal-20261015T060000Z-terminal-retry, formal-20261015T073000Z-terminal-retry2, and formal-20261015T080000Z-terminal-retry3; terminal failures and low Q remain unresolved.
- 必需修复：Keep all G7 terminal failures and Q invalidity unchanged. Before confirmatory reuse, diagnose provider failures and obtain an independent trace/Q review or run a separately frozen retry plan; do not pool it silently with the present G7 run.
- 尝试次数：1
- 来源：docs/audits/cycle-20261014T163000Z-20/audit.json
- 阻塞原因：未记录

### ISSUE-000000000002 — P1 — RESOLVED_UNVERIFIED
- 描述：Real-provider pilot and retry/cost behavior are unverified
- 证据：The original raw run retains provider-error history and the corrected trace audit passes. Provider model identity metadata is now recorded, but no billing export or immutable weight snapshot is available for independent verification.
- 必需修复：Retain an independently verifiable provider billing export and immutable model snapshot, then repeat the final acceptance review.
- 尝试次数：1
- 来源：legacy:docs/audits/2026-10-08_supervisor_report_autopilot_cycle_01.md
- 阻塞原因：未记录

### ISSUE-000000000003 — P1 — BLOCKED
- 描述：Upstream provenance and GitHub delivery are externally blocked
- 证据：Both git ls-remote commands failed with proxy connection errors; vendored NewtonBench is not a separate Git checkout.
- 必需修复：Restore network/Git credentials, verify the configured upstream commit and license, then push the feature branch and confirm remote state.
- 尝试次数：1
- 来源：legacy:docs/audits/2026-10-08_supervisor_report_autopilot_cycle_01.md
- 阻塞原因：GitHub feature-branch delivery is verified at 106e5b6; NewtonBench upstream provenance and license verification remain externally unverified.

### ISSUE-000000000004 — P1 — RESOLVED_UNVERIFIED
- 描述：Formal statistical validity is not established
- 证据：The 23-family corrected release has 552 matched rows and a deterministic paired-family bootstrap/McNemar analysis. Pooled G4-minus-G3 accuracy difference is -0.01811594202898551 with family-bootstrap 95% CI [-0.07608695652173915, 0.043478260869565216] and exact matched McNemar p=0.6353076420876663. CF3 is a prespecified exploratory stratum with difference -0.2753623188405797 and exact p=0.0005461. The analysis remains pending independent statistical review and does not justify causal or superiority claims.
- 必需修复：Have an independent reviewer inspect the preregistration, oracle provenance, paired-family construction, and statistical code before any confirmatory inference.
- 尝试次数：0
- 来源：legacy:docs/audits/2026-10-08_supervisor_report_autopilot_cycle_01.md
- 阻塞原因：未记录

### ISSUE-ff97c7c89112 — P1 — RESOLVED_UNVERIFIED
- 描述：G6 audit-g5 found 1309 proof_graph.json files and all 1309 had events.jsonl, steps.jsonl, summary.json, and manifest.json siblings, but the audit explicitly rep
- 证据：scripts/verify_g5_g6_inputs.py independently checked the public model/parameters and selected proof graphs without reading answer_key or private_oracle: 23/24 families passed grade-B analytic/numeric checks; TB-L1-010 was explicitly excluded because its recessive mutation-selection formula is inconsistent and its graph contains an unresolved validity node. The 23-family corrected release has 552/552 completed responses, official validation, official score, and trace_audit.pass=true.
- 必需修复：Obtain an independent external mathematical review of the verifier and release only the 23-family corrected subset; never restore TB-L1-010 by synthesis or silently include it in the confirmatory denominator.
- 尝试次数：0
- 来源：docs/audits/cycle-20261012T150331Z-14/audit.json
- 阻塞原因：未记录

### ISSUE-ad61f025976a — P1 — RESOLVED_UNVERIFIED
- 描述：G6 project_preflight returned BLOCKED_REAL_RUN with missing verified model snapshot, missing positive hard limits for model/tool/token/cost, missing private-ora
- 证据：The official project_preflight.py run on configs/g6_project_preflight_verified23.json completed with 0 blockers and status READY_FOR_CONTROLLED_PILOT_NOT_RUN. The provider metadata endpoint returned HTTP 200 for glm-5 and its canonical metadata hash is persisted. The evidence is only model identity/creation metadata: the gateway supplied no immutable weight fingerprint, and no external billing receipt is present.
- 必需修复：Obtain an independently verifiable immutable model snapshot or gateway weight fingerprint and billing evidence; retain the current truthful preflight as a pilot-readiness attestation, not as full RUN_COMPLETE acceptance.
- 尝试次数：0
- 来源：docs/audits/cycle-20261012T150331Z-14/audit.json
- 阻塞原因：未记录

### ISSUE-1f8c2b6a4d90 — P1 — BLOCKED
- 描述：All eligible G6 public proof graphs have no dependency edges for G7 localization
- 证据：The G7 audit remains edge_count_distribution={0:92} with eligible_u_cases=0. G8 therefore executed only the externally reviewed V mechanism and did not fabricate L/U edges or state transitions.
- 必需修复：Obtain independently audited replacement dependency-edge/state-transition data with source hashes before making L/U claims.
- 尝试次数：0
- 来源：docs/audits/cycle-20261014T030000Z-19/audit.json
- 阻塞原因：G7 completed without fabricating edges; replacement independently audited dependency-edge data is still required before edge-level L/U claims.

### ISSUE-f9171bb760b1 — P1 — RESOLVED_UNVERIFIED
- 描述：No frozen, auditable G8 real/sham/off/extra adapter is present
- 证据：The G8 adapter now exposes real, sham, off, and extra-thinking paths with required events and hard per-row budgets; the formal 324-row run passed 324/324 independent structural output audits. External immutable gateway-weight and billing verification remain unavailable.
- 必需修复：Retain the adapter and audit artifacts; obtain independently verifiable immutable model-weight/gateway fingerprint and billing evidence before treating the paid run as fully verified.
- 尝试次数：0
- 来源：docs/audits/cycle-20261015T000000Z-21/audit.json
- 阻塞原因：未记录

### ISSUE-000000000005 — P2 — OPEN
- 描述：Classical baseline is only an extension interface
- 证据：src/scientific_discovery/evaluation/classical.py retains NotImplementedError.
- 必需修复：Implement only if a classical comparison is added to the study; otherwise keep it explicitly out of the claims.
- 尝试次数：0
- 来源：legacy:docs/audits/2026-10-08_supervisor_report_autopilot_cycle_01.md
- 阻塞原因：未记录

### ISSUE-6b3a9e1d4f20 — P2 — RESOLVED_UNVERIFIED
- 描述：Raw G6 traces contain noncanonical retry segments that require a derived audit view
- 证据：The append-only raw trace directory contains 576 files, 378 with nonmonotonic sequence histories and 8 intermediate starts without RUN_END. No raw line was overwritten; repair_g6_trace_views.py selected the last complete successful segment and produced 576 canonical audited traces with failures=[] .
- 必需修复：Keep raw history immutable, use only the hashed canonical trace view for scoring, and fix the runner's resume/sequence protocol before the next formal batch.
- 尝试次数：0
- 来源：docs/audits/cycle-20261014T000000Z-16/audit.json
- 阻塞原因：未记录

## 已验证解决的问题

- **ISSUE-000000000001**（P1）：Formal scientific scoring is incomplete——`python -m pytest -q`；Independent read-only review confirmed that the evaluator binds numeric validation, legal OOD fit, canonical-AST structural recovery, and mechanistic validity; adversarial evaluator tests cover wrong constants, illegal code, finite-region overfit, malformed output, algebraic equivalence, and local constants. The host suite passed 70 tests, including tests/test_evaluator.py::test_algebraically_equivalent_code_passes_structural_and_mechanistic_criteria and tests/test_evaluator.py::test_numeric_fit_alone_cannot_pass_with_ood_or_structural_failure.
- **ISSUE-7e3d4a91c2f0**（P1）：G6 A arm execution semantics do not match the G6/G7 protocol——`E:/resources/python/python.exe -m pytest -q`；Corrected G6 protocol profile executed with exactly 2 workers on the verified 23-family denominator; final audit passes 552/552 plan/response/trace rows with no failures; independent release review structural_pass=true and corrected handoff is used by G7.

## 可复用的已验证完成工作（不要重新构建）

- G1-G5 execution policy and theory contamination controls：Policy boundary tests, provider retry rejection, strict answer isolation, 100-task validation, and 40/30/30 contamination audit are implemented. Full host suite passed 80 tests. | 验证：`python -m pytest -q` | 提交：`未固定`
- Corrected G6 protocol and audited G7 failure-localization execution：G6 corrected 23-family run and G7 16-worker run have canonical merge, independent audits, hashes, and explicit terminal-failure accounting; host suite and package tests pass. Scientific release remains blocked by recorded external/math/provenance/statistical/provider gates. | 验证：`E:/resources/python/python.exe -m pytest -q` | 提交：`未固定`

## 科学性注意事项

绿色单元测试只能验证工程门禁，不能证明 Agent 在科学发现上优于其他方法。
Mock 输出不是科学证据。不得使用正式测试任务进行提示词调优。
