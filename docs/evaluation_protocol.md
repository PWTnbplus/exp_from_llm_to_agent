# Evaluation protocol

The discovery process never receives the validation set. `ValidationEnvironment` invokes `NewtonBenchLawEvaluator` after final submission. It obtains the pinned ground-truth function inside the evaluator boundary, compiles the candidate with restricted builtins, and evaluates new seeded conditions.

The primary success criterion is relative RMSE no greater than `1e-5` on 128 validation points for the first direct-measurement implementation. RMSLE is retained as a secondary continuous metric. The evaluator uses the pinned NewtonBench ground-truth function inside the evaluator boundary, but it is a project-owned restricted numeric evaluator, not NewtonBench's full official evaluator; this is recorded as `official_numeric_evaluator: false`. NewtonBench's optional LLM symbolic judge is not used as a primary decision. Structural recovery and mechanistic validity therefore remain `not_implemented`, and `validated_success` currently means numeric fit only.

Validation actions are sampled from the public apparatus domain encoded in the adapter schema. For example, Snell-law indices and incidence angles use the documented ranges, and positive controls remain strictly positive. This prevents an apparently held-out score from depending on out-of-domain inputs.

Analysis reports task-level denominators, VLDR, paired Agent-minus-LLM differences, bootstrap intervals, and domain/complexity strata. No failed API run is silently deleted or counted as a scientific failure without its operational status.
