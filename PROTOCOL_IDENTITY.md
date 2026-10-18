# Protocol identity — V4 single-model recovery

- Profile: `theory_benchmark`.
- Exact route: CTFlow `https://token.ctflow.cn/v1`, model `kimi-k2.5`.
- Cohort: append-only recovery of the frozen Kimi G6/G7 line; no Qwen/GLM pooling.
- G6: CF1–CF4 counterfactual reasoning with G3/G4 matched arms.
- G7: V/L/U/Q failure localization from frozen public checkpoints.
- G7 input: 92 public cases, 23 families, 184 checkpoints, 1,288 diagnostic rows.
- G7 recovery: terminal-state rows and 13 historical trace-invalid rows are separate retry targets.
- Runner: `scripts/run_g7_failure_localization.py`.
- Frozen public/label/plan hashes are enforced by protocol preflight.
- Scientific release remains independent from execution progress and remains closed.
