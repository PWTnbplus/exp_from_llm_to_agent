# 科学定律自动驾驶——未解决问题报告

生成时间（UTC）：2026-10-16T09:51:54+00:00

- 开放/阻塞/未验证：**9**
- 已验证修复：**20**
- 已验证完成里程碑：**2**
- 未验证科学门禁：**G0, G6, G7**

## 未解决和阻塞问题

### ISSUE-000000000002 — P1 — BLOCKED
- 描述：Real-provider pilot and retry/cost behavior are unverified
- 证据：Cycle 54: tests/test_g7_protocol.py 29 passed; fail-closed paid-evidence gate rejects missing or malformed snapshot/billing before key/provider setup, and structurally valid local manifests remain PRESENT_UNVERIFIED_EXTERNAL. No explicit paid authorization, positive hard USD ceiling, immutable model evidence, independent billing, or external isolation review is available; no provider call was made.
- 必需修复：Keep the paid gate closed. Obtain explicit authorization, a positive hard USD ceiling, independently verifiable model/billing evidence, and an independent isolation review before any real-provider pilot.
- 尝试次数：2
- 来源：legacy:docs/audits/2026-10-08_supervisor_report_autopilot_cycle_01.md
- 阻塞原因：Cycle 54 paid-evidence review confirms external authorization and verification blocker

### ISSUE-000000000003 — P1 — BLOCKED
- 描述：Upstream provenance and GitHub delivery are externally blocked
- 证据：After local commits b84f005 and 45267ed, git push origin autopilot/scientific-law-discovery exited 1 and git ls-remote origin refs/heads/autopilot/scientific-law-discovery exited 1; both failed to connect to github.com:443 via 127.0.0.1. The remote update is not verified or claimed.
- 必需修复：Restore network/Git credentials, independently verify the configured NewtonBench commit and license against the upstream remote, then re-run G0 and verify the feature-branch remote state.
- 尝试次数：1
- 来源：legacy:docs/audits/2026-10-08_supervisor_report_autopilot_cycle_01.md
- 阻塞原因：Cycle 82 remote delivery remains blocked by the configured proxy

### ISSUE-000000000004 — P1 — BLOCKED
- 描述：Formal statistical validity is not established
- 证据：Cycle 59: G7 corrected metrics now fail closed on identity collisions and non-bijective inputs; focused G7 tests 20 passed, host suite 176 passed, and corrected probe retained all 1288 rows with confirmatory_reuse_allowed=false. No confirmatory inference or scientific release is allowed.
- 必需修复：Retain the fail-closed G6/G7 input guards and obtain independent statistical and mathematical review before any confirmatory inference or scientific release.
- 尝试次数：0
- 来源：legacy:docs/audits/2026-10-08_supervisor_report_autopilot_cycle_01.md
- 阻塞原因：Cycle 59 repaired G7 diagnostic input identity; independent statistical and mathematical review remains unavailable.

### ISSUE-ff97c7c89112 — P1 — RESOLVED_UNVERIFIED
- 描述：G6 audit-g5 found 1309 proof_graph.json files and all 1309 had events.jsonl, steps.jsonl, summary.json, and manifest.json siblings, but the audit explicitly rep
- 证据：Cycle 57: duplicate public task and source-index identifiers now fail closed; focused tests 21 passed, host suite 170 passed, and verified23 remains 23 VERIFIED_INDEPENDENT_B plus TB-L1-010 permanently excluded. No external mathematical review is present.
- 必需修复：Retain the fail-closed input guards and obtain an independent external mathematical review of the verifier; release only the 23-family corrected subset and never synthesize or restore TB-L1-010.
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
- 证据：Cycle 63 keeps the reduced denominator non-confirmatory. No dependency-edge or independent Q/math/provenance evidence is available, so no G8 causal, L/U, or scientific release claim is made.
- 必需修复：Keep the reduced denominator structural and non-confirmatory. Obtain an independently audited complete dependency/state dataset and Q/math review before any G8 causal, L/U, or scientific release claim.
- 尝试次数：2
- 来源：docs/audits/cycle-20261014T030000Z-19/audit.json
- 阻塞原因：The reduced source-only denominator is structural only; independent dependency/state/Q/mathematical evidence remains externally unavailable.

### ISSUE-3d7a9c1e5b20 — P1 — BLOCKED
- 描述：G7 provider execution has terminal failures and low independently valid Q coverage
- 证据：Cycle 61: future G7 trace identity/collision guards pass 53 focused tests and 185 host tests. Re-auditing the immutable corrected run found 1288/1288 state traces and 184/184 checkpoint traces without event/step identities, invalidated all 20 previously Q-valid rows by trace review, retained 3 provider_error states, and confirmed confirmatory_reuse_allowed=false. No V/L/U/Q or scientific claim is made.
- 必需修复：Keep historical G7 artifacts non-confirmatory. Restore authorized provider access only with explicit paid authorization and a hard ceiling, run a separately frozen non-pooled batch using the repaired trace contract, and obtain independent Q and dependency/state review while retaining every failure in the denominator.
- 尝试次数：21
- 来源：docs/audits/cycle-20261015T081700Z-27/g7_failure_taxonomy.json
- 阻塞原因：Historical raw traces cannot be retroactively repaired; authorized provider access and independent Q/dependency review remain external blockers.

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

## 已验证解决的问题

- **ISSUE-000000000001**（P1）：Formal scientific scoring is incomplete——`python -m pytest -q`；Independent read-only review confirmed that the evaluator binds numeric validation, legal OOD fit, canonical-AST structural recovery, and mechanistic validity; adversarial evaluator tests cover wrong constants, illegal code, finite-region overfit, malformed output, algebraic equivalence, and local constants. The host suite passed 70 tests, including tests/test_evaluator.py::test_algebraically_equivalent_code_passes_structural_and_mechanistic_criteria and tests/test_evaluator.py::test_numeric_fit_alone_cannot_pass_with_ood_or_structural_failure.
- **ISSUE-6b3a9e1d4f20**（P2）：Raw G6 traces contain noncanonical retry segments that require a derived audit view——`E:/resources/python/python.exe -X utf8 -m pytest -q tests/test_g6_resume_sequence.py tests/test_g7_trace_q_consistency.py tests/test_g7_protocol.py`；existing_event_seq accepts only contiguous integer sequence prefixes and fails closed on malformed JSONL, non-object rows, gaps, duplicates, and invalid sequence types. Focused tests 56/56, full host suite 198/198, and an independent temporary probe pass. Raw historical traces remain immutable and canonical derived traces remain the scoring boundary.
- **ISSUE-7e3d4a91c2f0**（P1）：G6 A arm execution semantics do not match the G6/G7 protocol——`E:/resources/python/python.exe -m pytest -q`；Corrected G6 protocol profile executed with exactly 2 workers on the verified 23-family denominator; final audit passes 552/552 plan/response/trace rows with no failures; independent release review structural_pass=true and corrected handoff is used by G7.
- **ISSUE-0f2cb195c681**（P1）：Original G7 model-facing prompt leaked routing metadata——`E:/resources/python/python.exe -X utf8 -m pytest -q tests/test_g7_label_contract.py tests/test_g7_protocol.py tests/test_g7_protocol_preflight.py tests/test_g7_failure_taxonomy.py tests/test_g7_trace_q_consistency.py`；The forward G7 contract now validates strict V/L/U label shapes, strips verifier_ref/eligibility/provenance from model-visible diagnostic payloads, and the executable preflight scans both public case prompts and constructed diagnostic payloads for routing/private metadata. Focused tests pass 59/59 and the full host suite passes 204/204. A fresh read-only preflight of the 92-case, 1288-row, 184-checkpoint protocol-corrected plan passes with zero routing/private hits and provider_calls_made=false. The immutable historical corrected trace is not retroactively reclassified: its model requests contain 4222 verifier_ref hits and remain non-confirmatory.
- **ISSUE-28ed827e40a9**（P1）：Last cycle blocked: RuntimeError: Codex exit 4294967295: c94fd2a435478adde6a18079beb:G6F-TB-L1-009-CF2"}, "applied_stages": ["V", "L", "U"], "source": "independ——`E:/resources/python/python.exe -X utf8 -m pytest -q tests/test_g7_protocol.py tests/test_g7_protocol_preflight.py tests/test_g7_trace_q_consistency.py tests/test_g7_failure_taxonomy.py tests/test_g7_terminal_retry.py`；Historical malformed output is retained; subsequent valid audit exit_code=0 and independent review pass; current G7 protocol/trace/taxonomy/terminal-retry focused tests pass 54/54.
- **ISSUE-ab0746b86bf9**（P1）：The prior evaluator returned hidden ground-truth source in validation results and ResultRecorder persisted validation verbatim. Cycle 31 removes the source fiel——`E:/resources/python/python.exe -X utf8 -m pytest -q tests/test_result_recorder_privacy.py tests/test_observability.py tests/test_evaluator.py`；Focused tests 14/14 pass. A separate temporary probe writes mixed-case nested/list hidden fields through ResultRecorder and hidden values/private keys do not occur in the ordinary result file; TraceRecorder recursively redacts hidden values. Source inspection confirms law_recovery.py does not return a ground_truth source field.
- **ISSUE-0786397621a0**（P1）：Before this cycle SingleAgentRunner initialized an empty history and did not call get_initial_observations(), while LLMOnlyRunner supplied the same public obser——`E:/resources/python/python.exe -X utf8 -m pytest -q tests/test_agent_actions.py tests/test_llm_isolation.py tests/test_no_leakage.py`；Both arms expose the same public initial observation to their model-facing prompt and persist the same normalized initial_observations metadata field. Focused tests 10/10 and full host suite 192/192 pass; the paired temporary probe passes.
- **ISSUE-4c7e2a91d6f0**（P1）：G7 model-output stage parser accepted malformed nested V/L/U fields——`E:/resources/python/python.exe -X utf8 -m pytest -q tests/test_g7_protocol.py tests/test_g7_label_contract.py tests/test_g7_protocol_preflight.py tests/test_g7_failure_taxonomy.py tests/test_g7_trace_q_consistency.py`；The arm-specific output contract now rejects non-string/nonempty supporting_evidence and non-string/non-null revised_claim. New adversarial assertions pass together with the existing checkpoint and nested-stage tests: 67 focused tests and 212 full host tests. The immutable 22/184 historical malformed checkpoint rows remain unchanged and non-confirmatory.
- **ISSUE-9e31a7c4b2d8**（P1）：G6 statistical pairing did not enforce same task lineage across G3 and G4——`E:/resources/python/python.exe -X utf8 -m pytest -q tests/test_analyze_g6_clustered.py tests/test_g6_input_collision_guards.py`；The repaired validator rejects both synthetic mismatched case_id and mismatched paired_set_id probes. The immutable corrected G6 plan passes the formal 23-family × CF1–CF4 × replicate 0–2 × G3/G4 layout check with 552 plan rows, 552 responses, 92 private rows, 276 complete pairs, and zero case_id/paired_set_id lineage mismatches. Focused G6 input tests pass 13/13 and the full host suite passes 214/214.
- **ISSUE-6a4e8b2c1d90**（P1）：G6 clustered analysis could count a failed response with a matching decision as correct——`E:/resources/python/python.exe -X utf8 -m pytest -q tests/test_analyze_g6_clustered.py tests/test_g6_input_collision_guards.py`；The repaired validator rejects missing response status and unknown completed decisions. The independent response_matches_oracle probe returns false for provider_error with a matching decision and true only for completed with a matching decision. The immutable corrected G6 inputs pass with 552/552 responses status=completed and the full formal input validation. Focused G6 tests pass 16/16 and the full host suite passes 217/217.
- **ISSUE-0b7d3f91a2c4**（P1）：G6 statistical input validation coerced malformed replicate and oracle alignment fields——`E:/resources/python/python.exe -X utf8 -m pytest -q tests/test_analyze_g6_clustered.py tests/test_g6_input_collision_guards.py`；The repaired validator rejects string/boolean replicate probes and rejects a private CF mismatch against the plan. It also enforces nonempty typed plan identifiers, valid private CF/decision fields, and same-case CF consistency. The immutable corrected inputs pass formal validation with 552 plan rows, 92 private rows, 552 responses, replicate values [0,1,2], and all registered statuses/decisions. Focused G6 tests pass 19/19 and the full host suite passes 220/220.
- **ISSUE-8c2f6d1a4b70**（P1）：G6 validation did not enforce one task lineage across repeats and counterfactual variants——`E:/resources/python/python.exe -X utf8 -m pytest -q tests/test_analyze_g6_clustered.py tests/test_g6_input_collision_guards.py`；The repaired validator rejects a case_id change across replicates and a paired_set_id change across CF variants. The immutable corrected 552-row plan has zero family-level paired_set_id violations and zero family×CF task-lineage violations; formal validation passes with 276 complete G3/G4 pairs. Focused G6 tests pass 21/21 and the full host suite passes 222/222.
- **ISSUE-5f7a1c9d3e20**（P1）：G6 statistical analysis did not validate formal experiment, arm, and split identity fields——`E:/resources/python/python.exe -X utf8 -m pytest -q tests/test_analyze_g6_clustered.py tests/test_g6_input_collision_guards.py`；The repaired validator rejects wrong experiment_id, wrong arm_id/group_id mapping, and non-final split probes. The immutable corrected v2 plan has 552 rows with experiment_id=g6_counterfactual, G3→G6_A_G3_GIVEN, G4→G6_B_G4_GIVEN, and split=final_test throughout. The temporary real-data CLI run exits 0 and produces the explicitly non-confirmatory ANALYZED_PENDING_INDEPENDENT_STATISTICAL_REVIEW status. Focused G6 tests pass 24/24 and the full host suite passes 225/225.
- **ISSUE-2d7c9a4e1f60**（P1）：G6 report table mixed formal-run metrics with the protocol-v2 artifact root——`E:/resources/python/python.exe -X utf8 -m pytest -q`；Independent CLI reruns reproduce the old table from formal-20261013 verified23 inputs and reproduce the current v2 metrics from protocol-g3tools-v2 inputs. A new source-explicit report docs/reports/G6_PROTOCOL_V2_REAUDIT_CN_20261016.md records the v2 paths, release-review hashes, 552/552/92/552 counts, 1,826 model requests, 1,796 tool calls, 3,454,449 tokens, USD 6.057783 trace cost, current CF metrics, and ANALYZED_PENDING_INDEPENDENT_STATISTICAL_REVIEW status. Existing historical reports and raw artifacts were not overwritten. Full host tests pass 225/225.
- **ISSUE-4a8f6c2e1d90**（P1）：Independent G7-to-G8 handoff review could miss case-variant private or routing metadata keys——`python -m pytest -q`；find_forbidden now recursively casefolds dictionary keys against the complete private/routing metadata boundary. The new adversarial tests detect nested Verifier_Ref, Eligible_U, CF_TYPE, and Theory_Family_Id; public prose mentioning reserved words remains accepted. Focused G7 tests pass 77/77, py_compile passes, and git diff --check passes.
- **ISSUE-7b3e9a1c5d20**（P2）：Issue status transitions did not refresh top-level last_seen——`python -m pytest -q`；update_status now stores one transition_time in last_seen and the append-only history event. The new stale-timestamp test passes, recovery_state.py tests pass 13/13, the full host suite passes 228/228, and py_compile/diff-check pass.
- **ISSUE-dad1d3f0293e**（P1）：G7 formal preflight could accept a plan that silently dropped an entire public case——`E:/resources/python/python.exe -X utf8 -m pytest -q`；The repaired preflight computes case/group coverage independently of the aggregate checkpoint view, requires exactly one checkpoint and the complete D0/D1/D2/D3/L_ONLY/U_ONLY/V_ONLY arm set for every public case in both G3 and G4, rejects duplicate case/group checkpoints and cross-case checkpoint reuse, and still allows the same source checkpoint to be shared by one case's G3/G4 forks. Adversarial protocol tests pass 41/41; the full repository suite passes 231/231; the immutable 92-case/1288-row plan preflight reports no missing, duplicate, or colliding coverage.
- **ISSUE-42e2f49eb73e**（P1）：G7 complete preflight accepted a source G6 arm inconsistent with the diagnostic group——`E:/resources/python/python.exe -X utf8 -m pytest -q`；The complete-plan gate now requires G3 rows to use G6_A_G3_GIVEN and G4 rows to use G6_B_G4_GIVEN. The adversarial wrong-mapping test passes; the focused G7 suite passes 42/42; the full repository suite passes 232/232; the immutable 1288-row formal plan has zero source-arm mismatches in an independent PowerShell reconstruction and the runner preflight reports formal_run_allowed_by_protocol=true with errors=[].
- **ISSUE-6f5db82e86c0**（P1）：G7 complete preflight accepted a missing or wrong formal experiment identity——`E:/resources/python/python.exe -X utf8 -m pytest -q`；The complete-plan contract now requires experiment_id=g7_failure_localization. The adversarial missing/wrong identity test passes; the focused G7 suite passes 43/43; the full repository suite passes 233/233; the immutable 1288-row formal plan preflight reports no invalid plan metadata, and an independent PowerShell reconstruction reports zero missing or wrong experiment identities, zero source-arm mismatches, and the expected plan hash.
- **ISSUE-57a074f246f3**（P1）：G7 complete preflight accepted a pooled retry protocol——`E:/resources/python/python.exe -X utf8 -m pytest -q`；The complete-plan contract now requires separate_frozen_retry_not_pooled. The adversarial pooled-protocol test passes; the focused G7 suite passes 44/44; the full repository suite passes 234/234; the immutable 1288-row formal plan preflight reports no invalid plan metadata, and an independent PowerShell scan reports zero wrong retry protocols, zero identity failures, and zero source-arm mismatches.

## 可复用的已验证完成工作（不要重新构建）

- G1-G5 execution policy and theory contamination controls：Policy boundary tests, provider retry rejection, strict answer isolation, 100-task validation, and 40/30/30 contamination audit are implemented. Full host suite passed 80 tests. | 验证：`python -m pytest -q` | 提交：`未固定`
- Corrected G6 protocol and audited G7 failure-localization execution：G6 corrected 23-family run and G7 16-worker run have canonical merge, independent audits, hashes, and explicit terminal-failure accounting; host suite and package tests pass. Scientific release remains blocked by recorded external/math/provenance/statistical/provider gates. | 验证：`E:/resources/python/python.exe -m pytest -q` | 提交：`未固定`

## 科学性注意事项

绿色单元测试只能验证工程门禁，不能证明 Agent 在科学发现上优于其他方法。
Mock 输出不是科学证据。不得使用正式测试任务进行提示词调优。
