# G7 trace/Q consistency review — cycle 20261015T162335Z-29

This cycle repaired the audit path for `ISSUE-3d7a9c1e5b20`; it did not repair or reinterpret historical provider output. The new read-only audit checks the latest append-only `RUN_START`–`RUN_END` segment referenced by each state, retains terminal failures, and only treats an independently valid Q row as trace-backed when that segment completed without an error event.

| Persisted run | State rows | Q rows | Original Q-valid | Trace-backed Q-valid | Terminal failures retained |
|---|---:|---:|---:|---:|---|
| Original G7 | 1,288 | 1,288 | 3 | 3 | Yes |
| Retry 1 | 295 | 295 | 2 | 2 | Yes |
| Retry 2 | 102 canonical / 110 Q | 110 | 0 | 0 | Yes; 8 Q rows lack canonical state review |
| Retry 3 | 31 | 31 | 0 | 0 | Yes |
| Protocol-corrected retry | 1,288 | 1,288 | 20 | 20 | Yes; 3 `provider_error` states |

The audit is derived only from persisted files and made no provider calls. It does not pool retries, convert failures into successes, establish scientific truth, or permit confirmatory reuse. Historical raw traces remain immutable; append-only prior segments are retained while the latest canonical segment is checked.

Changed implementation and tests:

- `scripts/audit_g7_trace_q_consistency.py`
- `tests/test_g7_trace_q_consistency.py`
- `docs/audits/cycle-20261015T162335Z-29/g7_trace_q_*.json`

Verification:

- `E:/resources/python/python.exe -X utf8 -m pytest -q tests/test_g7_trace_q_consistency.py tests/test_g7_protocol.py tests/test_g7_terminal_retry.py tests/test_g7_failure_taxonomy.py tests/test_provider_trace.py` — 15 passed.
- `E:/resources/python/python.exe -X utf8 -m pytest -q` — 113 passed.

The P1 issue remains `IN_PROGRESS`: terminal failures and low Q coverage remain, and no real-provider retry was authorized or started. `docs/state/gates.json` is absent, so no G0–G7 gate is promoted to PASS by this cycle.
