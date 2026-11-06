# Evaluation protocol

The discovery process never receives the validation set. `ValidationEnvironment` invokes `NewtonBenchLawEvaluator` after final submission. It obtains the pinned ground-truth function inside the evaluator boundary, compiles the candidate with restricted builtins, and evaluates new seeded conditions.

The primary success criterion is relative RMSE no greater than `1e-5` on 128 validation points for the first direct-measurement implementation. RMSLE is retained as a secondary continuous metric. NewtonBench's numeric evaluation logic is reused conceptually and the upstream numeric function is available for cross-checking; its optional LLM symbolic judge is not used as a primary decision.

Analysis reports task-level denominators, VLDR, paired Agent-minus-LLM differences, bootstrap intervals, and domain/complexity strata. No failed API run is silently deleted or counted as a scientific failure without its operational status.
