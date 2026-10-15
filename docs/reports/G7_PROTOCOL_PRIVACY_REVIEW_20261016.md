# G7 protocol and result-artifact read-only review — 2026-10-16

This is an engineering review only. It makes no scientific truth or superiority claim and did not call a provider.

## Reviewed controls

- `scripts/run_g7_failure_localization.py` calls the shared `protocol_preflight` before constructing `OpenAICompatibleProvider` or reading the key. A contaminated `model_visible` prompt fails closed and writes a `provider_calls_made: false` report.
- `scripts/g7_protocol_preflight.py` uses the same preflight implementation as the runner. Shared checkpoint IDs remain allowed; duplicate run IDs, missing public/label rows, routing metadata, and private metadata remain errors.
- `NewtonBenchLawEvaluator` no longer returns hidden ground-truth source in its ordinary validation dictionary.
- `ResultRecorder` recursively removes hidden evaluator keys from ordinary result artifacts, including nested validation payloads.

## Verification

- Focused protocol/evaluator/privacy suite: `20 passed`.
- Full host suite: `122 passed`.
- `git diff --check`: clean before commit.

## Remaining hard gates

Historical G7 routing leakage is immutable and non-confirmatory. The corrected retry still retains `3/1288` provider errors and only `20/1288` independently valid Q rows; no confirmatory per-arm score is available. Provider key/billing/immutable model snapshot, upstream provenance, external mathematical/statistical review, dependency-edge replacement data, and machine gate attestation remain unavailable. No paid experiment was launched.
