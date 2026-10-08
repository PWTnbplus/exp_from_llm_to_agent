# Experiment protocol

Both arms use the same pinned NewtonBench task, model provider, public task description, action schema, noise level, measurement precision, validation evaluator, and `BudgetLimits`.

LLM-only has three phases: (1) one planning call, (2) frozen-plan batch execution with no provider reference, and (3) one final inference call after all observations are collected. The canonical plan is SHA-256 hashed before execution.

The single agent repeatedly receives the current public history and may issue exactly one `run_experiment` action per provider call. It can stop with the shared final-law schema. No code execution, browsing, file access, hidden state, or other tools are exposed.

The default experiment budget is six experiments and 120 measurements. API, token, cost, and runtime ceilings are tracked by the same `BudgetLedger`. Formal paid runs are disabled by default and require `--allow-paid`. Validation follows the frozen `scoring-v1` protocol in `docs/evaluation_protocol.md`: numeric fit, canonical executable-law structural recovery, and deterministic legal OOD intervention fit are reported separately, and all three are required for `validated_success`.

The pilot/formal command requires an existing frozen manifest. It validates the
manifest against the pinned NewtonBench registry and outcome-blind seed-42
selection, records the manifest SHA-256 in every task-run result, and refuses
formal execution unless both arms use the real provider with an explicit
positive hard cost cap. Analysis must receive the same manifest and rejects
duplicate, out-of-grid, stale, or malformed task-run records.
