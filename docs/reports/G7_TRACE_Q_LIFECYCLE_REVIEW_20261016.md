# G7 trace/Q lifecycle review — cycle 20261016T120000Z-30

This cycle repaired the read-only G7 trace audit contract. It did not modify raw provider traces, state rows, Q labels, retry plans, or any scientific result.

The selected append-only segment is now split only when a new `RUN_START` follows a completed segment. A malformed segment is rejected when it contains duplicate lifecycle events, missing or non-monotonic `seq`, duplicate event IDs, run-ID mismatches, orphan model/tool results, or unclosed calls in a completed trace. A provider exception may retain an unanswered model request only when the segment has explicit terminal provider-error evidence.

Persisted G7 evidence remains non-confirmatory:

| Run | Trace-backed Q-valid | Terminal failure status |
|---|---:|---|
| Original | 3/1288 | retained |
| Retry 1 | 2/295 | retained |
| Retry 2 | 0/110 | retained; 8 Q rows lack canonical state review |
| Retry 3 | 0/31 | retained |
| Protocol-corrected | 20/1288 | 3 `provider_error` states retained |

Verification:

- `E:/resources/python/python.exe -X utf8 -m pytest -q tests/test_g7_trace_q_consistency.py` — 11 passed in 0.18s.
- G7 regression command in the cycle audit — 21 passed in 2.44s.
- `E:/resources/python/python.exe -X utf8 -m pytest -q` — 119 passed in 26.56s.
- Fresh read-only lifecycle/JSON probe — passed; `git diff --check` was clean.

The P1 issue `ISSUE-3d7a9c1e5b20` remains `IN_PROGRESS`. This cycle made the trace/Q evidence gate stricter, but it did not diagnose the external provider root cause, obtain new provider evidence, or authorize a paid retry. Confirmatory reuse remains disallowed.
