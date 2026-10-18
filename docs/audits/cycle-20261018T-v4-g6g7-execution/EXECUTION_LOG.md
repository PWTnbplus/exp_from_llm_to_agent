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
