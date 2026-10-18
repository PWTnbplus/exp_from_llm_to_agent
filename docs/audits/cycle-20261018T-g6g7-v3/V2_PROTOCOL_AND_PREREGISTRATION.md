# G7 prospective Q-v2 / LU-v2 protocol (frozen offline)

Status: `SMOKE_PASS`, `REAL_FORMAL_RUNS=0`, `V2_FINAL_METRICS=NOT_RUN`.

The legacy 1288-state Q and L/U results remain in the LEGACY_FROZEN namespace. This protocol creates a separate `G7_Q_V2` and `G7_LU_V2` namespace; no new rows are added to the legacy denominator.

Q-v2 requires a model-generated typed AST, explicit assumptions/quantifiers/domain, an observed verifier tool trace, input/output hashes, and an independent SymPy verifier. Self-reported `stages.Q.verdict` and `final_decision` are never evidence. Missing candidates are `NOT_SCORED_CANDIDATE_MISSING`; missing tool evidence is `UNOBSERVED_TOOL`.

LU-v2 requires a public acyclic DAG with independently referenced proof artifacts and a real observed non-final claim transition in the same fork. Final-node changes, evaluator-derived edges, private labels, and synthetic arrows are ineligible.

The present artifact is a synthetic contract smoke only (`SYNTHETIC_MOCK_NOT_SCIENTIFIC`). A real DEV/PILOT/FINAL run requires verified provider pricing, atomic budget clearance, a separately frozen task cohort, and a real trace. No paid Q-v2/LU-v2 formal call was made in this cycle; the separate Qwen G7 execution pilot is recorded independently and is not V2 evidence.
