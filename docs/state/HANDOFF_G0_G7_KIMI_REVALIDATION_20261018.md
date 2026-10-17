# G0-G7 Kimi K2.5 revalidation handoff — 2026-10-18 HKT

This is the detailed continuation document for the next agent. It supplements the generated docs/state/HANDOFF.md and supersedes the older, stale docs/state/HANDOFF_G0_G7_REPAIR_NEXT_AGENT.md for the current Kimi revalidation attempt.

## 1. Executive status

The source repair in local commit c1178b9 fixed the main observed provider-format mismatch:

- G6 now has a bounded format-retry path requiring the exact response contract.
- G7 now sends a checkpoint-specific retry instruction requiring exactly four top-level fields and explicitly forbidding the diagnostic stages field.
- Focused tests passed 58; the full host suite passed 264 after the source repair.

The repair improved execution, but the single-model experiment is not scientifically complete:

| Area | Current evidence | Status |
|---|---:|---|
| Kimi model | kimi-k2.5 via https://token.ctflow.cn/v1 | Local real-provider pilot only |
| User authorization | Paid calls authorized, hard ceiling USD 200 | Present |
| Provider billing/pricing | No independent invoice or usage export | BLOCKED |
| Immutable model identity | No immutable weights/gateway fingerprint | BLOCKED |
| G6 canonical rows | 552/552: 550 completed, 2 provider_error | Structural accounting only |
| G6 revision validity | 0/138 | No G6 scientific release |
| G6 handoff | No G6-to-G7 handoff file; independent review failure missing_handoff | Not releasable |
| G7 preflight | 92 public, 92 labels, 1288 plan rows, 184 checkpoints, 7 arms/checkpoint, no preflight errors | Protocol PASS only |
| G7 current checkpoints | 184/184 completed, 0 provider_error in the latest canonical checkpoint merge | Checkpoint layer recovered |
| G7 current states | 1150 completed, 137 checkpoint_missing, 1 provider_error | Partial; not complete |
| G7 current Q audit | 0/1288 independently valid; external Q verifier absent | NOT_SCORED |
| G7 current trace audit | 28 integrity failures: 27 completed traces and 1 failure trace | BLOCKED |
| Scientific release | false | Must remain closed |

The most important distinction is: all checkpoints are now complete, but 138 diagnostic state rows are still terminal/incomplete, and 28 of the traces selected for the latest revalidation are not lifecycle-clean. Do not report 1150/1288 as a valid scientific completion rate.

## 2. Mandatory startup for the next agent

Use the repository Python, not the system Python:

~~~powershell
git status --porcelain=v1
git remote -v
git branch --show-current
git log -8 --oneline
E:/resources/python/python.exe scripts/recovery_state.py bootstrap
E:/resources/python/python.exe scripts/recovery_state.py next
~~~

Read all of these before changing anything:

1. .agents/skills/scientific-law-recovery/SKILL.md
2. docs/state/issues.json — authoritative issue lifecycle ledger
3. docs/state/UNRESOLVED_REPORT.md
4. docs/state/HANDOFF.md
5. This file
6. docs/state/gates.json
7. docs/audits/cycle-20261018T-kimi-format-revalidation-partial/audit.json
8. docs/audits/cycle-20261017T-kimi-k25-single-model-g0-g7/audit.json
9. The three design files under D:/硕士/prj1_ai_cal/writing/实验设计

Do not rebuild NewtonBench, regenerate the frozen G6/G7 denominator, or rerun verified G0-G5 engineering work without fresh regression evidence.

## 3. Exact current artifacts

### G6

Run directory:

~~~text
runs/ctflow_single_model/20261017T-g6-kimi-k25-v1
~~~

Important derived artifacts:

- responses_audited.jsonl: canonical G6 response view.
- g6_audit/trace_audit.json: trace accounting.
- g6_audit/revision_audit.json: 0/138 revision-valid rows.
- g6_audit/release_review.revalidated.json: independent structural review; structural_review_pass=false only because missing_handoff remains.

The G6 audit itself has coverage accounting 552/552, zero trace-integrity failures, and no terminal failures in the latest canonical response view, but historical provider failures remain recorded and the release review cannot establish scientific validity. Do not invent a G6-to-G7 handoff; none exists.

### G7

Run directory:

~~~text
runs/ctflow_single_model/20261017T-g7-kimi-k25-v1
~~~

Frozen inputs:

~~~text
results/g7_failure_localization/formal-20261014T030000Z/g7_public_cases.jsonl
results/g7_failure_localization/formal-20261014T030000Z/g7_vlu_private.jsonl
results/g7_failure_localization/formal-20261015T060000Z-protocol-corrected-16workers/g7_full_retry_plan.jsonl
~~~

Current revalidated derived views:

~~~text
runs/ctflow_single_model/20261017T-g7-kimi-k25-v1/g7_audit/states_revalidated_20261018.jsonl
runs/ctflow_single_model/20261017T-g7-kimi-k25-v1/g7_audit/checkpoints_revalidated_20261018.jsonl
runs/ctflow_single_model/20261017T-g7-kimi-k25-v1/g7_audit/q_audit_revalidated_20261018.json
runs/ctflow_single_model/20261017T-g7-kimi-k25-v1/g7_audit/trace_q_consistency_revalidated_20261018.json
runs/ctflow_single_model/20261017T-g7-kimi-k25-v1/g7_audit/corrected_metrics_revalidated_20261018.json
~~~

The merge selection rule is failure-preserving: latest completed row wins; otherwise the latest terminal row is retained. It selected all 1288 expected state IDs and all 184 checkpoint IDs with no missing IDs. The state terminal set is 137 checkpoint_missing plus 1 provider_error; the checkpoint terminal set is empty because all 184 checkpoints eventually completed.

The 137 missing rows are concentrated in worker files that stopped before their diagnostic loops finished:

| Worker | Unique rows | Completed | Missing | Provider error |
|---:|---:|---:|---:|---:|
| 2 | 91 | 87 | 4 | 0 |
| 6 | 105 | 93 | 12 | 0 |
| 8 | 133 | 87 | 46 | 0 |
| 11 | 98 | 90 | 8 | 0 |
| 13 | 119 | 73 | 45 | 1 |
| 14 | 77 | 55 | 22 | 0 |
| Total | 623 | 485 | 137 | 1 |

Workers 0, 1, 3, 4, 5, 7, 9, 10, 12, and 15 currently have all their assigned state IDs completed. Worker 14 was accidentally stopped while removing a duplicate process; its append-only data remains intact and it must be resumed once.

## 4. Immediate next execution — only six workers

First confirm no G7 process is active. Never run the same worker index concurrently:

~~~powershell
$p=Get-CimInstance Win32_Process | Where-Object {
  $_.Name -eq 'python.exe' -and $_.CommandLine -like '*run_g7_failure_localization.py*'
}
$p | Select-Object ProcessId,CommandLine
~~~

If the output is empty, resume only workers 2, 6, 8, 11, 13, 14. Use the exact existing command and the same output directory; do not delete or reset any files:

~~~powershell
$base = @(
  'scripts/run_g7_failure_localization.py',
  '--public','results/g7_failure_localization/formal-20261014T030000Z/g7_public_cases.jsonl',
  '--labels','results/g7_failure_localization/formal-20261014T030000Z/g7_vlu_private.jsonl',
  '--plan','results/g7_failure_localization/formal-20261015T060000Z-protocol-corrected-16workers/g7_full_retry_plan.jsonl',
  '--out','runs/ctflow_single_model/20261017T-g7-kimi-k25-v1',
  '--model-id','kimi-k2.5',
  '--key-file','api_key/kimi/kimi-k2.5.txt',
  '--base-url','https://token.ctflow.cn/v1',
  '--allow-paid','--allow-unverified-paid-evidence',
  '--worker-count','16','--aggregate-max-cost-usd','60','--max-cost-usd','5',
  '--max-model-calls','4608','--max-tool-calls','3456','--max-total-tokens','4608000',
  '--provider-retries','0','--provider-timeout','60'
)
foreach ($i in @(2,6,8,11,13,14)) {
  & E:/resources/python/python.exe @base '--worker-index' $i
}
~~~

The loop above is sequential. For speed, launch one independent process per worker, but keep one process per worker index and keep stdout/stderr logs. Do not start a second batch merely because a PTY appears silent: verify the actual Python process list first. Previous monitoring showed that PTY sessions can disappear while child Python processes remain alive.

During this resume:

- Completed state rows are skipped by the runner.
- Checkpoints are already completed and should be skipped.
- The 137 checkpoint-missing rows should be attempted.
- The one provider-error row may be retried; retain failure if it fails again.
- Do not increase the declared aggregate cap above USD 60 for G7 or the user’s USD 200 total ceiling.

## 5. Required post-run merge and audits

After all six workers have actually exited and every corresponding new summary is written, create a fresh derived view. Use a new filename so the prior handoff remains reproducible:

~~~powershell
$root='runs/ctflow_single_model/20261017T-g7-kimi-k25-v1'
$plan='results/g7_failure_localization/formal-20261015T060000Z-protocol-corrected-16workers/g7_full_retry_plan.jsonl'
$public='results/g7_failure_localization/formal-20261014T030000Z/g7_public_cases.jsonl'
$labels='results/g7_failure_localization/formal-20261014T030000Z/g7_vlu_private.jsonl'
$oracle='results/g6_counterfactual/protocol-g3tools-v2-20261014T030000Z/private_oracle.jsonl'
$audit=Join-Path $root 'g7_audit'
E:/resources/python/python.exe scripts/merge_g7_states.py --plan $plan --states-dir $root --states-out (Join-Path $audit 'states_final_20261018.jsonl') --checkpoints-out (Join-Path $audit 'checkpoints_final_20261018.jsonl')
E:/resources/python/python.exe scripts/audit_g7_q.py --states (Join-Path $audit 'states_final_20261018.jsonl') --plan $plan --labels $labels --g6-oracle $oracle --out (Join-Path $audit 'q_audit_final_20261018.json')
E:/resources/python/python.exe scripts/audit_g7_trace_q_consistency.py --states (Join-Path $audit 'states_final_20261018.jsonl') --q (Join-Path $audit 'q_audit_final_20261018.json') --trace-root $root --checkpoints (Join-Path $audit 'checkpoints_final_20261018.jsonl') --out (Join-Path $audit 'trace_q_consistency_final_20261018.json')
E:/resources/python/python.exe scripts/audit_g7_corrected_metrics.py --plan $plan --states (Join-Path $audit 'states_final_20261018.jsonl') --q (Join-Path $audit 'q_audit_final_20261018.json') --oracle $oracle --preflight (Join-Path $root 'g7_protocol_preflight.json') --out (Join-Path $audit 'corrected_metrics_final_20261018.json')
~~~

Acceptance conditions for execution accounting are not scientific release conditions:

1. selected_records=1288 and missing_ids=[].
2. Every final state is either completed or an explicit retained failure.
3. Every checkpoint is either completed or an explicit retained failure.
4. Q audit remains NOT_SCORED unless an independent verifier is genuinely added.
5. Trace audit must be read in full. The current 28 failures are a blocker even if all state rows become completed.
6. Corrected metrics must retain all planned denominators and must say confirmatory_reuse_allowed=false.

## 6. Trace lifecycle defect that must not be ignored

The latest trace audit is materially worse than the old Cycle-102 summary because the current append-only revalidation exposed lifecycle problems in selected retry segments:

- 28 state trace integrity failures.
- 27 are attached to rows marked completed.
- 1 is attached to the provider-error row.
- Typical reasons: run_start_count:2, model_response_parent_mismatch, unmatched_model_request, duplicate sequence/event/step IDs, run_end_not_last, and missing RUN_END on a failure trace.
- Checkpoint traces themselves currently pass 184/184.

The next agent must inspect scripts/run_g7_failure_localization.py, especially trace_path_for_retry, existing_trace_sequence, emit, and the retry-segment contract. Determine whether the audit is selecting the wrong append-only segment or whether concurrent/retry writes genuinely create invalid lifecycle records. Add an adversarial regression test before changing the runner. Never delete malformed historical traces; use a derived canonical audit view and retain the old evidence.

## 7. Issue ledger: what remains unresolved

The following issues remain active and must not be closed by passing tests alone:

### ISSUE-000000000002 — P1 — provider verification and billing

User authorization and USD 200 ceiling are now explicit. That removes the old authorization blocker, but not provider-verifiable billing/pricing or immutable model identity. Local proxy cost (G6 2.039289 USD; prior G7 worker summaries plus retries are local accounting only) is not an invoice. Required unlock: independent provider usage/billing evidence and immutable model/gateway fingerprint.

### ISSUE-000000000004 — P1 — statistics/math/Q validity

G6 revision-valid is 0/138; G7 Q independent valid is 0/1288; no external Q verifier is present. No paired superiority, causal, VLDR, L/U, or confirmatory statistical inference is allowed. Required unlock: independent math/Q verifier and preregistered statistical review.

### ISSUE-1f8c2b6a4d90 — P1 — dependency/state edge data

No independently audited dependency edges/state transitions are available for causal G7 localization. Do not synthesize L/U evidence from model text or private labels. Required unlock: audited dependency/state data and independent review.

### ISSUE-3d7a9c1e5b20 — P1 — incomplete/failed G7 execution

Current revalidated state view is 1150 completed + 137 checkpoint_missing + 1 provider_error. The six worker resumes are the next execution action. Even after that, trace/Q defects remain.

### ISSUE-7c2d4e9a10bf — P1 — trace lifecycle integrity

Newly recorded in the 2026-10-18 partial audit. The current trace audit has 28 integrity failures. This issue is not resolved by the format retry repair.

### ISSUE-ff97c7c89112 and ISSUE-ad61f025976a — P1 — resolved only as local engineering repairs

These remain RESOLVED_UNVERIFIED: external math/model/billing evidence is missing. Keep them in the unresolved report.

### ISSUE-000000000005 — P2 — classical baseline

Only an extension interface exists. Do not expand scope during this repair unless the design explicitly adds a classical baseline.

## 8. Gate interpretation

- G0: PASS only for pinned simulator provenance/licensing; official_numeric_evaluator=false remains a caveat.
- G1-G5: engineering/policy/smoke PASS, not formal scientific result evidence.
- G6: BLOCKED. Structural coverage exists, but terminal provider history, revision-valid zero, no handoff, provider identity/billing, and independent math/statistics remain.
- G7: BLOCKED. Preflight is valid; current checkpoint layer is recovered; diagnostic state execution and trace lifecycle are incomplete; Q is NOT_SCORED.
- Overall scientific_release_allowed=false.

## 9. Git and hygiene

Current local HEAD at handoff creation: c1178b95d59f053730e09e46e229df9c49503fc7.

The latest direct git ls-remote attempt failed to connect to GitHub port 443 through the configured 127.0.0.1:7890 proxy. Therefore remote delivery of this handoff is not verified. The next agent must:

~~~powershell
git diff --check
git status --porcelain=v1
git add docs/audits/cycle-20261018T-kimi-format-revalidation-partial/audit.json docs/state docs/reports
git commit -m "Record Kimi G7 format revalidation handoff"
$env:HTTP_PROXY=$null; $env:HTTPS_PROXY=$null; $env:ALL_PROXY=$null
git -c http.proxy= -c https.proxy= push origin autopilot/scientific-law-discovery
git -c http.proxy= -c https.proxy= ls-remote origin refs/heads/autopilot/scientific-law-discovery
~~~

Only claim push success if ls-remote returns the exact new commit. Never stage:

- runs/
- api_key/
- .env or bearer tokens
- private labels/oracles
- research_data_summary_G0_G7/ (user-owned untracked directory)

## 10. Final scientific boundary

This work has demonstrated a real Kimi provider path and repaired a concrete response-contract defect. It has not demonstrated a scientific law, Agent superiority, causal localization, valid Q, or confirmatory statistical effect. The next agent’s success criterion is a truthful, independently auditable, failure-retaining experiment record—not a forced PASS label.
