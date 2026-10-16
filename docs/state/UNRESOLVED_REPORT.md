# 科学定律自动驾驶——未解决问题报告

生成时间（UTC）：2026-10-16T08:20:01+00:00

- 开放/阻塞/未验证：**11**
- 已验证修复：**5**
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
- 证据：Cycle 66 local commit 6a7feb4 exists on autopilot/scientific-law-discovery, but git push and git ls-remote both failed with proxy connection errors to github.com:443.
- 必需修复：Restore network/Git credentials, independently verify the configured NewtonBench commit and license against the upstream remote, then re-run G0 and verify the feature-branch remote state.
- 尝试次数：1
- 来源：legacy:docs/audits/2026-10-08_supervisor_report_autopilot_cycle_01.md
- 阻塞原因：Cycle 66 GitHub delivery remains externally blocked after the G6 resume fail-closed repair commit.

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

### ISSUE-0f2cb195c681 — P1 — RESOLVED_UNVERIFIED
- 描述：Original G7 model-facing prompt leaked routing metadata
- 证据：The executable G7 preflight now runs before provider construction and key-file reading, case_prompt rejects malformed model_visible objects, and the preflight recursively scans routing plus private fields case-insensitively. The corrected public input passes with 92 cases, 1288 plan rows, 184 checkpoints, and zero routing/private hits; immutable original contamination remains non-confirmatory.
- 必需修复：Keep the original batch permanently non-confirmatory and require the executable preflight to pass with zero routing/private hits before any future paid run.
- 尝试次数：3
- 来源：docs/audits/cycle-20261015T081700Z-27/g7_failure_taxonomy.json
- 阻塞原因：未记录

### ISSUE-28ed827e40a9 — P1 — RESOLVED_UNVERIFIED
- 描述：Last cycle blocked: RuntimeError: Codex exit 4294967295: c94fd2a435478adde6a18079beb:G6F-TB-L1-009-CF2"}, "applied_stages": ["V", "L", "U"], "source": "independ
- 证据：Last cycle blocked: RuntimeError: Codex exit 4294967295: c94fd2a435478adde6a18079beb:G6F-TB-L1-009-CF2"}, "applied_stages": ["V", "L", "U"], "source": "independently_verified_g7_local_labels"}, "run_id": "g7full_73f3c3a5bd3823bdb85c", "status": "provider_error", "trace_ref": "traces\\g7full_73f3c3a5bd3823bdb85c\\events.jsonl"}
events [('MODEL_RESPONSE', 'COMPLETED', None, None), ('MODEL_REQUEST', 'RUNNING', None, None), ('MODEL_RESPONSE', 'COMPLETED', None, None), ('ERROR', 'FAILED', 'ValueError', 'missing stages object'), ('RUN_END', 'FAILED', None, None)]

2026-10-15T17:06:43.791296Z  WARN codex_core::responses_retry: stream disconnected - retrying sampling request (1/5 in 216ms)... turn_id=01a1407e-9393-7fb2-a2f2-b19efae12fb4 retries=1 max_retries=5 sampling_error=stream disconnected before completion: idle timeout waiting for SSE
ERROR: Reconnecting... 1/5
exec
"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe" -Command "@'
import json
from pathlib import Path
base=Path('results/g7_failure_localization/formal-20261015T060000Z-protocol-corrected-16workers')
states=[json.loads(x) for x in (base/'g7_full_retry_states.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
for s in states:
 if s.get('status')"'!='"'completed':
  p=base/s['trace_ref'].replace('\\\\\\\\','/')
  ev=[json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]
  print(s['run_id'], [(e.get('event_type'), (e.get('payload') or {}).get('call_index'), (e.get('payload') or {}).get('error')) for e in ev])
'@ | E:/resources/python/python.exe -" in E:\master_exp\nature_prj1_cal\from_llm_to_agent
 succeeded in 612ms:
g7full_dff0dae5a314dd9fb081 [('RUN_START', None, None), ('INJECTION_APPLIED', None, None), ('MODEL_REQUEST', 1, None), ('MODEL_RESPONSE', 1, None), ('TOOL_CALL', None, None), ('TOOL_RESULT', None, None), ('MODEL_REQUEST', 2, None), ('MODEL_RESPONSE', 2, None), ('TOOL_CALL', None, None), ('TOOL_RESULT', None, None), ('MODEL_REQUEST', 3, None), ('MODEL_RESPONSE', 3, None), ('TOOL
- 必需修复：Resolve environment/format/test blocker; rerun audit
- 尝试次数：0
- 来源：cycle-20261015T161447Z-01
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
- **ISSUE-ab0746b86bf9**（P1）：The prior evaluator returned hidden ground-truth source in validation results and ResultRecorder persisted validation verbatim. Cycle 31 removes the source fiel——`E:/resources/python/python.exe -X utf8 -m pytest -q tests/test_result_recorder_privacy.py tests/test_observability.py tests/test_evaluator.py`；Focused tests 14/14 pass. A separate temporary probe writes mixed-case nested/list hidden fields through ResultRecorder and hidden values/private keys do not occur in the ordinary result file; TraceRecorder recursively redacts hidden values. Source inspection confirms law_recovery.py does not return a ground_truth source field.
- **ISSUE-0786397621a0**（P1）：Before this cycle SingleAgentRunner initialized an empty history and did not call get_initial_observations(), while LLMOnlyRunner supplied the same public obser——`E:/resources/python/python.exe -X utf8 -m pytest -q tests/test_agent_actions.py tests/test_llm_isolation.py tests/test_no_leakage.py`；Both arms expose the same public initial observation to their model-facing prompt and persist the same normalized initial_observations metadata field. Focused tests 10/10 and full host suite 192/192 pass; the paired temporary probe passes.

## 可复用的已验证完成工作（不要重新构建）

- G1-G5 execution policy and theory contamination controls：Policy boundary tests, provider retry rejection, strict answer isolation, 100-task validation, and 40/30/30 contamination audit are implemented. Full host suite passed 80 tests. | 验证：`python -m pytest -q` | 提交：`未固定`
- Corrected G6 protocol and audited G7 failure-localization execution：G6 corrected 23-family run and G7 16-worker run have canonical merge, independent audits, hashes, and explicit terminal-failure accounting; host suite and package tests pass. Scientific release remains blocked by recorded external/math/provenance/statistical/provider gates. | 验证：`E:/resources/python/python.exe -m pytest -q` | 提交：`未固定`

## 科学性注意事项

绿色单元测试只能验证工程门禁，不能证明 Agent 在科学发现上优于其他方法。
Mock 输出不是科学证据。不得使用正式测试任务进行提示词调优。
