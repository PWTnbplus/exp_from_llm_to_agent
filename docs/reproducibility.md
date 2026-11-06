# Reproducibility

- Upstream NewtonBench commit: `912a4ba5f4356ddd06acc16e44460ca30be4abc2`.
- Python requirement: 3.10 or newer; package metadata is in `pyproject.toml`.
- Task-selection seed: 42 by default; manifests store the seed.
- Prompts are versioned under `prompts/`.
- Every run stores the runner, task ID, frozen plan/hash (when applicable), observations, provider metadata, budget ledger, and validation output.
- `metadata.provider_trace` stores redacted request/response records, tool payloads, model metadata, latency, token usage, and retry/error attempts. API keys are never serialized.
- Real providers record model, latency, token usage, retry count, and estimated cost. API keys are read from environment variables and are never serialized.
- Mock runs are explicitly marked and must not be used as formal scientific results.
- `engineering-test` executes the selected manifest for both runners with deterministic negative controls; `pilot --resume` skips existing stable task/runner result paths and refuses accidental overwrites otherwise.
