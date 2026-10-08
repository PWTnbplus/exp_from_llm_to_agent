# Experiment protocol

Both arms use the same pinned NewtonBench task, model provider, public task description, action schema, noise level, measurement precision, validation evaluator, and `BudgetLimits`.

LLM-only has three phases: (1) one planning call, (2) frozen-plan batch execution with no provider reference, and (3) one final inference call after all observations are collected. The canonical plan is SHA-256 hashed before execution.

The single agent repeatedly receives the current public history and may issue exactly one `run_experiment` action per provider call. It can stop with the shared final-law schema. No code execution, browsing, file access, hidden state, or other tools are exposed.

The default experiment budget is six experiments and 120 measurements. API, token, cost, and runtime ceilings are tracked by the same `BudgetLedger`. Formal paid runs are disabled by default and require `--allow-paid`. Validation is numeric-fit-only in this implementation; it must not be reported as structural or mechanistic law recovery.
