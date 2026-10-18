# V3 executive report

模型/路由：CTFlow catalog probe exposed service IDs only; immutable model identity remains UNVERIFIED. 账单/价格：Qwen `qwen3.5-plus` public pricing is provider-verifiable for the pilot; account-level billing and historic provider-charge reconciliation remain UNVERIFIED.

G6 legacy: 552 normalized rows; revision denominator 138; root causes and independent verifier counts are in `G6_138_MATH_CLASSIFICATION.csv` and `G6_INDEPENDENT_VERIFIER_RESULT.jsonl`. G6 remains partial/not scored for scientific release.

G7 legacy: 1288 unique states, 184 checkpoints, 1150 provider-completed, 137 checkpoint-missing, 1 provider-error; canonical trace-valid and sensitivity views remain separate. Historical trace defects remain 15 boundary + 13 genuine final inconsistencies. A separate one-case Qwen execution pilot completed, but it is not pooled into the historical denominator and is not scientific evidence.

Legacy Q remains NOT_SCORED/INELIGIBLE. Legacy L/U remains unverified with no public dependency edges and no eligible observed non-final transition.

Q-v2/LU-v2: strict schemas, independent verifier hooks, leakage tests and synthetic smoke passed; real formal V2 metrics are `NOT_RUN` and no synthetic result is scientific evidence.

Cost: after explicit authorization, this V3 cycle sent 4 minimal compatibility requests (`qwen3.5-plus`, `glm-5.2`), all PASS. Two follow-up responses exposed token usage (qwen 180 total tokens; GLM 23), but neither exposed a cost field or invoice. A separate one-case Qwen G7 pilot used 9 provider requests across an initial hard-budget failure and a completed retry; local pricing estimates were USD 0.0166128 and USD 0.0145112, respectively, for USD 0.031124 total. The completed retry settled USD 0.0145112 in its local ledger using the provider-public Qwen pricing record; this is not an account-level billing receipt. Compatibility-call billing remains `UNKNOWN_UNVERIFIED_PROVIDER_BILLING`, and no safe remaining budget is claimed. The frozen G6 audited trace view is USD 6.057783 and raw G6 attempts are USD 6.610445; raw G7 trace directories are USD 8.915826. These historical values are local proxy estimates, not provider billing.

Scientific release: BLOCKED. Offline engineering, source hashing, math classification, trace regression and V2 contract validation are complete to their evidence boundary; external billing/pricing/model identity and real V2/G7 missing responses remain unresolved.
