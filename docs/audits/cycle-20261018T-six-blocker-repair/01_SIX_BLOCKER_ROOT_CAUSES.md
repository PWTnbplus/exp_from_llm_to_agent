# Six blocker root causes

- B1/G6: frozen 552 rows; original attempt view 550 completed + 2 provider errors, normalized response view 552/552; all 138 CF3 revision units are classified.
- B2/G7: 1288/1288 state IDs and 184/184 checkpoints join; 137 checkpoint-missing and 1 provider-error state still lack a completed provider response.
- B3/trace: immutable raw evidence gives 28 historical failures = 15 attempt-boundary artifacts + 13 genuine final-attempt inconsistencies.
- B4/Q: independent verifier gives 1150 NOT_SCORED and 138 INELIGIBLE; no Q PASS is claimed.
- B5/provider: local usage is available but billing and immutable route/weight identity are not externally verified.
- B6/L/U: 92 public graphs have 0 declared dependency edges; no independently observed eligible U transition.

Scientific release remains BLOCKED.
