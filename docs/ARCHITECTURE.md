# Architecture

## Layers

1. `experiments/` contains one stable entrypoint per scientific experiment. Each wrapper exposes `run.py`, `evaluate.py`, `reproduce.py`, a config, a result schema, tests and a figures placeholder.
2. `src/scientific_discovery/` contains shared policy, isolation, budget, provider, trace, runner, evaluator and statistics code. `project/registry.py` is the single dependency/status registry.
3. `scripts/` contains safe orchestration CLIs. Offline reproduction is the default and is deterministic from the registry; real provider execution fails closed in the public layer.
4. `configs/` stores frozen protocol examples and environment-independent experiment metadata. Real secrets and private data are addressed by environment variables, never committed.
5. Historical `runs/`, private truth and audit archives remain local evidence. They are not part of the public release allowlist.

## Input and output contracts

Every run records an experiment ID, run ID, mode, model identity, code commit, config hash, timestamps, events and explicit scientific/non-scientific status. Independent scoring is a separate step and is not delegated to model self-evaluation.

## Failure and resume policy

The offline runner refuses to overwrite an existing result unless `--resume` is passed. Real failures, timeouts, unknown truth and schema errors must remain visible in protected ledgers; they are never converted into successful synthetic outputs.
