# Evaluation protocol

This scoring protocol is preregistered in `configs/evaluation.json` as
`scoring-v1`. Its values are frozen before any formal paid evaluation and are
implemented in `evaluation/scoring.py`; no formal result may override them.

`ValidationEnvironment` invokes `NewtonBenchLawEvaluator` only after final
submission. The target law and all validation/OOD interventions remain inside
that evaluator boundary. The candidate is compiled with restricted builtins;
the model never receives evaluator data.

## Deterministic criteria

1. Numeric fit (`numeric_fit`) is relative RMSE `<= 1e-5` on 128 deterministic,
   seeded validation interventions. Invalid upstream outputs are excluded
   from the finite-point denominator; a run with no finite points fails.
2. Structural recovery (`structural_recovery`) compares the submitted
   executable law with the pinned target function using a canonical AST
   fingerprint. It resolves upstream numeric constants inside the evaluator,
   normalizes parentheses, commutative addition/multiplication, division as
   inverse multiplication, `pow`/`sqrt`, and harmless zero/one identities.
   A matching equation string alone cannot earn structural recovery.
3. OOD fit (`ood_fit`) is relative RMSE `<= 1e-5` on 64 deterministic legal
   interventions shifted toward public-domain boundaries and extrapolative
   positive scales. At least 16 finite OOD points are required. These points
   are distinct from the validation sampling sequence.
4. Mechanistic validity (`mechanistic_validity`) is true only when both
   structural recovery and OOD fit are true. This is a conservative
   operational criterion for law rediscovery, not evidence of a human-unknown
   discovery.

`validated_success` is true only when numeric fit, structural recovery, and OOD
fit all pass. RMSLE is retained as a secondary diagnostic. The evaluator uses
the pinned NewtonBench ground-truth function inside the evaluator boundary,
but it is a project-owned restricted numeric evaluator, not NewtonBench's full
official evaluator (`official_numeric_evaluator: false`). The optional
NewtonBench LLM symbolic judge is not used.

Analysis follows the frozen `configs/statistical_plan.json`. It retains every
registered task-run failure in the denominator, pairs the two arms by task and
replicate index, and treats a missing arm as a failed task-run rather than
silently dropping it. The primary point estimate is the mean paired
Agent-minus-LLM difference. Its uncertainty interval is a deterministic
10,000-repeat bootstrap over NewtonBench module (law-family) means; variants
and repeated seeds are therefore not treated as independent natural laws.
Reports must include the scoring/statistical protocol versions, task-level
VLDR, missing-arm count, cluster count, and domain/complexity strata. Mock
results remain engineering evidence only.
