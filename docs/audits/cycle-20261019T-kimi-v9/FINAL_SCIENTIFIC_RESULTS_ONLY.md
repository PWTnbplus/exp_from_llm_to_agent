# V9 Final Scientific Results Only

- Base model: `kimi-k2.5` only; no Qwen/GLM calls in this V9 run.
- Real provider calls: 104; local usage estimate: USD 0.076148; mock: false.
- Historical denominators are unchanged and all failed/negative observations remain retained.

## Results

- Historical G6 276: public problem valid 276/276; original model text present 276/276; model decision match 96/276; revised claim valid 84/276.
- New G6 V9: 25/32 strict action decisions correct; independent SymPy/rational and separate stdlib numeric replay agree on 32/32 truth certificates.
- New Q V9: 8/8 schema-valid and 8/8 mathematically correct by the blind independent reviewer; second numeric replay agrees on 8/8.
- New LU/U V9: REAL semantic update 4/4; CONTROL 0/4; SHAM 0/4. This is a small prospective causal calibration, not a powered formal G7 estimate.
- G7 V9 initial cohort: D3 input V/L/U was present in 4/4 and structured in 4/4, but strict and semantic final accuracy were 0/4 because the public graph did not contain a public equation; this negative design result is retained.
- G7 V9 repair cohort: public equation/domain added before calls, D3 structured 4/4, semantic final accuracy 3/4 (strict status-token metric 0/4); private Y was never injected.
- Same-Kimi Agent comparison: 0.812 allowed-action validity overall; LLM-only and Agent used 8 records each, and 8 adaptive feedback records were observed.

## Interpretation

These are real internal machine-verifiable results, not an overall superiority claim. The current evidence does not establish that the adaptive Agent is more reliable than the frozen LLM-only workflow; the Agent comparison is small and action-validity-only. External provider billing/weight attestation remains separate and unverified.

## Audit locations

- `docs/audits/cycle-20261019T-kimi-v9`
- `runs/ctflow_single_model/20261019T-kimi-v9-prospective`
