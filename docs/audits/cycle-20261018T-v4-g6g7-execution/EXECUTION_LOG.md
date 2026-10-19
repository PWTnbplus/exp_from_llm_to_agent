# V4 execution log

This log records real commands and artifacts for the current repair cycle. It
does not change the frozen protocol, private labels, oracle, or historical raw
traces.

| UTC time | command/action | exit | evidence |
|---|---|---:|---|
| 2026-10-18 | `python scripts/recovery_state.py bootstrap` | 0 | Imported 0 unseen audit reports; authoritative ledger loaded |
| 2026-10-18 | `python scripts/recovery_state.py next` | 0 | Selected `ISSUE-7c2d4e9a10bf` |
| 2026-10-18 | targeted G7 protocol/trace tests before patch | 0 | 86 passed |
| 2026-10-18 | runner writer/claim patch and Q/LU identity inspection | — | source changes recorded in working tree; no raw run overwritten |
| 2026-10-18 | `python -m pytest -q tests/test_g7_*.py tests/test_v3_observability.py` (PowerShell-expanded file list) | 0 | 112 passed in 6.45s |
| 2026-10-18 | `python -m scripts.review_g7_trace_repair` | 0 | 1,472 manifest rows; 1,322 accepted; raw hashes unchanged; no accepted derived lifecycle failures |
| 2026-10-18 | `python scripts/audit_g7_trace_q_consistency.py ...` | 0 | 1,288 states; terminal failures retained; 0 trace-backed valid Q; confirmatory reuse false |
| 2026-10-18 | `python -m py_compile scripts/v3/...` and `pytest -q tests/test_v4_q_lu.py` | 0 | 3 passed; Q-v2/LU-v2 code compiles and adversarial checks pass |
| 2026-10-18 | `scripts/v3/build_public_lu_graphs.py` on public TC-L1-001/002 | 0 | 2 graphs, 4/4 independently verified L edges; U candidates 0; no answer key/private labels read |
| 2026-10-18 | `scripts/v3/run_q_v2_cohort.py --preflight-only` on 4 public G7 cases | 0 | isolated Kimi K2.5 cohort plan; 0 provider calls; no private labels/answer key; pooling false |
| 2026-10-18 | regression group 1: G5/G6/G7/gates/V3/V4 tests | 0 | 136 passed in 7.13s |
| 2026-10-18 | regression group 2: provider/policy/evaluator/isolation tests | 0 | 94 passed in 17.70s |
| 2026-10-18 | regression group 3: matrix/observability/recorder/statistics/theory/recovery tests | 0 | 53 passed in 22.75s |
| 2026-10-18 | G7 runner resume preflight with the 150-row target file, one-row limit, Kimi K2.5 | 2 | frozen contract passed; provider calls false; stopped at missing Kimi pricing evidence before any provider request |
| 2026-10-18 | `scripts/ctflow_models.py probe` | 0 | unauthenticated catalog probe returned HTTP 401; no credential transmitted |
| 2026-10-18 | independent read-only recheck of V4 outputs | 0 | 2/2 DAGs valid; all proof refs exist; resume counts 138 terminal + 13 trace with 1 overlap = 150; Q calls 0 and private-label read false |
| 2026-10-18 | `python scripts/recovery_state.py bootstrap` then `next` | 0 | authoritative ledger imported 0 unseen reports; next remains G7 trace issue IN_PROGRESS; no false resolution claimed |
| 2026-10-18 | `git push origin autopilot/scientific-law-discovery` and `git ls-remote` verification | 128 / 128 | GitHub connection failed through configured proxy; remote push not claimed successful |
| 2026-10-18 | Q-v2 real cohort runs v1-v4 with `kimi-k2.5` only | 0 | 13 provider calls total across four preserved run directories; final v4 has 4 successful responses, independent counts `FAIL=1`, `INCONCLUSIVE=3`, `NOT_SCORED=0`; no private labels or answer key read |
| 2026-10-18 | G7 first real resume segment using the 150-row target set | interrupted | 72 checkpoints and 103 states completed before interruption; one incomplete historical request and its reservation/claim were preserved for reconciliation; no prior traces overwritten |
| 2026-10-18 | Windows stale-claim repair in `scripts/run_g7_failure_localization.py` plus targeted tests | 0 | `OSError`/`SystemError` stale PID cases (including WinError 87) are reclaimable; active/permission-denied owners remain protected; 86 targeted tests passed |
| 2026-10-18 | G7 recovery rerun from `G7_REMAINING_AFTER_INTERRUPT.jsonl` | 0 | 47 remaining target rows processed; final persisted states `150/150`, checkpoints `72/72`, single base model `kimi-k2.5`; local run cap remained $60 |
| 2026-10-18 | independent event/trace count over `20261018T-v4-g7-kimi-resume` | 0 | `MODEL_REQUEST=614`, `MODEL_RESPONSE=613`, `TOOL_CALL=512`, `TOOL_RESULT=512`, `RUN_START=223`, `RUN_END=222`; one interrupted request retained; latest trace audit: 150/150 state traces and 72/72 checkpoint traces pass |
| 2026-10-18 | `G7_REAL_RUN_RETRY_AUDIT.json` | 0 | 13 retry-target states completed and `bad_latest_traces=[]`; terminal-state and retry target overlap is retained rather than double-counted |
| 2026-10-18 | cost-ledger reconciliation for the interrupted G7 reservation | 0 | stale reservation `0.005666` settled conservatively at full reserved amount after runner exit and empty claims; final local ledger `settled_new_usd=1.131542`, `inflight_reserved_usd=0` |
| 2026-10-18 | `LU_V2_PUBLIC_GRAPHS_MANIFEST.json` and proof files | 0 | 2 public-derived graphs, 4/4 independently verified edges, 0 U-transition candidates; artifact explicitly marked derivation-only, not a model-behavior result |
| 2026-10-18 | G7 trace/Q consistency audit on the new run | 0 | 150 completed states and 72 completed checkpoints pass lifecycle checks; Q rows intentionally absent from this G7 run because Q-v2 is a separate public cohort; confirmatory reuse remains false |
| 2026-10-18 | `scripts/build_g6_g7_handoff.py` rebuilt the missing run-local G6 handoff | 0 | Reconstructed 552 handoff rows from the frozen plan and actual audited responses; no private source was changed |
| 2026-10-18 | `scripts/review_g6_release.py` on the repaired single-model G6 run | 0 | Structural review PASS: plan 552, responses 552, public 92, private 92, handoff 552, terminal failures 0; scientific release remains false |
| 2026-10-18 | authenticated `GET /v1/models` catalog capture | 0 | HTTP 200; exact service IDs `kimi-k2.5` and `kimi/kimi-k2.5` present; no immutable weight fingerprint or billing export returned, so provider gate remains blocked |
| 2026-10-18 | full Q-v2 public cohort with Kimi K2.5 | 0 | 92/92 provider responses completed in one isolated cohort; independent rereview reproduces PASS 9, FAIL 3, INCONCLUSIVE 26, NOT_SCORED 54; no private labels/answer key read |
| 2026-10-18 | extended public-only LU-v2 derivation | 0 | 11 public graphs, 22/22 independently verified SymPy edges; 0 U transitions because no observed model-state transition was supplied; derivation-only status retained |
| 2026-10-18 | G6 CF3 revision retry, two disjoint workers | 0 | 138/138 new real responses completed with Kimi K2.5; 390 model responses and 488 tool calls; latest append-safe traces 138/138; raw failures preserved |
| 2026-10-18 | `scripts/audit_g6_counterfactual.py` on the CF3 retry view | 0 | 138/138 traces and all lifecycle/manifest/model/isolation checks pass; controlled private-oracle exact revision validity is 0/138 and is not claimed as scientific success |
| 2026-10-18 | `scripts/audit_g6_cf3_retry_independent.py` public-only rereview | 0 | Independent verifier: PASS 23, INCONCLUSIVE 62, NOT_SCORED 53; private oracle not loaded; scientific release remains false |
| 2026-10-18 | `E:/resources/python/python.exe -X utf8 -m pytest -q tests/test_v4_q_lu.py tests/test_g7_protocol.py tests/test_g7_trace_q_consistency.py` | 0 | 87 passed in 2.36s |
| 2026-10-18 | `E:/resources/python/python.exe -X utf8 scripts/recovery_state.py bootstrap` | 0 | Imported this cycle's audit; state remains truthful: engineering execution advanced, provider/statistics/LU/U and historical-trace scientific blockers remain unresolved |
| 2026-10-18 | Q-v2 format-retry cohort with `kimi-k2.5`, 92 public cases, `--max-output-tokens 512`, one fixed format retry | 0 | 103 recorded provider calls, 92/92 responses, 11 retry cases; independent counts PASS 18, FAIL 8, INCONCLUSIVE 55, NOT_SCORED 11; no private labels/answer key; non-confirmatory |
| 2026-10-18 | `scripts/audit_q_v2_cohort.py` after proof-reference path repair | 0 | 92 records, 103 traces, 92 unique cases, stored/recomputed counts match, proof hashes valid, single model `kimi-k2.5`, engineering audit PASS |
| 2026-10-18 | `scripts/analyze_q_v2_confirmatory.py` | 0 | Prespecified primary PASS fraction 18/92 = 0.1957 (exact 95% CI 0.1203-0.2915); scoreable fraction 18/26 = 0.6923 (0.4821-0.8567); confirmatory scientific status BLOCKED because no independent blinded truth |
| 2026-10-18 | Public-only LU-v2 U transition cohort and `scripts/audit_lu_u_v2.py` | 0 | 11/11 real responses, 3 observed validated transitions, 8 no observed state changes; independent audit PASS; no private labels/answer key/pooling; scientific release remains false |
| 2026-10-18 | Read-only provider evidence probe (`scripts/audit_provider_evidence.py`) | 0 | Authenticated `/models` HTTP 200 with 241 records and no fingerprint-like fields; `/usage`, `/billing`, `/account/usage` HTTP 404; no generation request sent; billing/fingerprint remain unverified |
| 2026-10-18 | `python scripts/recovery_state.py bootstrap` for `cycle-20261018T-v5-scientific-gates/audit.json` | 0 | Imported 1 new audit; Q statistics, LU U, provider evidence, G6 math, G7 historical failures, and GitHub delivery remain separately tracked; scientific release remains false |
| 2026-10-18 | `git -c http.proxy= -c https.proxy= push origin autopilot/scientific-law-discovery` | 0 | Direct upload succeeded; remote branch advanced to `fae8d76c64e7a78a213185125faf43ee40f82a48` |
| 2026-10-18 | `git -c http.proxy= -c https.proxy= ls-remote origin refs/heads/autopilot/scientific-law-discovery` | 0 | Remote SHA exactly matches local HEAD; GitHub delivery verified without changing global proxy configuration |
| 2026-10-18 | `scripts/audit_g6_cf3_public_boundary_review.py` on the 138-row public CF3 retry | 0 | 138/138 public rows covered across 23 families; 95 public-witness-aligned model actions and 43 inconsistent actions; private oracle and labels not loaded; scientific release remains false |
| 2026-10-18 | Targeted Q-v2 recovery for the 11 original NOT_SCORED cases | 0 | 17 new `kimi-k2.5` calls, 3 format retries; independent counts PASS 1, FAIL 0, INCONCLUSIVE 7, NOT_SCORED 3; original 92-case denominator unchanged |
| 2026-10-18 | LU/U public replicate batches 1-3 | 0 | 33 new `kimi-k2.5` calls; independently audited transitions 1/11, 6/11, 3/11; aggregate with initial batch is 44 calls, 13 transitions, 31 no-change observations |
| 2026-10-18 | `python scripts/recovery_state.py bootstrap` for `cycle-20261018T-v7-scientific-review/audit.json` | 0 | Imported 1 audit; new evidence strengthens coverage but does not unlock G6/G7 scientific release; historical failures and no-change rows retained |
| 2026-10-18 | v8 G6 public mismatch correction cohort with `kimi-k2.5` | 0 | Exactly 43 prior public mismatches selected; 54 real provider calls including 11 visible format retries; 43/43 records audited; 35 valid candidates; 19 public-witness alignments and 16 remaining mismatches; historical rows unchanged |
| 2026-10-18 | v8 Q blind-truth calibration build and run with `kimi-k2.5` | 0 | 24 real provider calls and 24 structured responses; truth key created before calls, never read by runner or sent to model; independent audit `TRUTH_MATCH=24/24`; not pooled with frozen Q-v2 |
| 2026-10-18 | v8 LU/U paired causal calibration with `kimi-k2.5` | 0 | 24 primary calls plus 6 visible format retries (30 traces); independent public truth audit validates 5 paired causal contrasts; mismatches/NOT_SCORED retained; not pooled with formal G7 |
| 2026-10-18 | v8 independent audits and regression | 0 | G6 chain-of-custody audit PASS; Q blind-truth audit PASS; LU/U causal audit PASS; focused regression 87 passed; scientific release remains BLOCKED |
| 2026-10-19 | v9 G6 targeted recovery rounds 1-3 with `kimi-k2.5` | 0 | 19+13+8 selected rows, 21+16+9 real provider attempts; latest r3 independently audits 7 remaining public mismatches and 1 unscored candidate; historical 43 remain unchanged |
| 2026-10-19 | independent frozen Q-92 public reviewer | 0 | Separate AST/SymPy implementation reproduces PASS 18, FAIL 8, INCONCLUSIVE 55, NOT_SCORED 11; no truth key/private labels read; domain-grade review remains incomplete |
| 2026-10-19 | repaired LU/U builder and fixed-cohort r4/r5 recovery | 0 | Intervention propositions are explicit; r4 has 12/12 valid records and 2 validated causal contrasts; r5 adds 2 calls for the remaining square task; formal G7 causal estimate not claimed |
| 2026-10-19 | v9 audit and regression preparation | 0 | Append-only artifacts recorded; G6/Q/LU scientific release remains BLOCKED; G7 150/150 states, 72/72 checkpoints, and 13 historical lifecycle failures retained |
