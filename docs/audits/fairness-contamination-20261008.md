# G1-G5 fairness and contamination-control audit

Date: 2026-10-08. Scope: execution boundaries and the default 100-task theory
benchmark. This audit does not report model accuracy or a scientific result.

## Implemented

- `PolicyController`/`PolicyProvider` enforce G1-G5 model-call, tool, compute,
  experiment, token, memory, retrieval and transport-retry limits before or at
  the relevant execution boundary.
- G1 passes `tools=None` and preserves the frozen NewtonBench plan boundary;
  G2 exposes only a bounded calculator; G3 is a fixed two-call reflection;
  G4 is the bounded adaptive runner; G5 adds only run-local bounded memory.
- OpenAI-compatible transport retries default to zero. A configured provider
  with retries above the group allowance is rejected before dispatch. Actual
  provider attempts, including failed attempts, are written as Trace events.
- Theory runners load only public tasks before model calls. Evaluation reads
  the answer key only after submission. Ordinary result JSON and Trace do not
  contain Ground Truth values; mismatch diagnostics are redacted and the trace
  redactor covers private answer-field names.
- The default benchmark is the existing answer-separated v1 dataset: 100
  tasks, 50 theoretical chemistry and 50 theoretical biology. The audit layer
  creates deterministic classical/structure-transform/private-dynamic strata
  of 40/30/30. Private dynamic cases require an operator seed and keep their
  answer object separate from the model-visible case.

## Evidence actually run

| Command | Result |
|---|---|
| `python -m pytest -q` | 80 passed |
| `python -m scientific_discovery.cli theory-validate` | PASS; 100 tasks, 100 answer self-checks |
| `python -m scientific_discovery.cli theory-contamination-audit` | 100 public tasks; 40/30/30 strata; private generation not run without seed |
| `python -m scientific_discovery.cli theory-contamination-audit --private-seed test-only-seed` | 30 private cases generated; only count/fingerprint reported |
| `python -m compileall -q src tests scripts` | exit 0 |
| `git diff --check` | no whitespace errors; Git line-ending warnings only |

The independent read-only review inspected the provider, policy, runner,
schema, verification and Trace paths and found no additional unrecorded
fairness or answer-boundary finding. The tests are mock/unit evidence; they do
not validate a real provider or model behavior outside this execution surface.

## Not verified / blocked

- No real provider request was sent. No paid experiment was authorized, so
  provider latency, gateway behavior and real retry accounting remain open.
- Upstream provenance and remote GitHub delivery remain the pre-existing open
  V2 issues; no remote push is claimed.
- Formal repeat counts, law-family clustering and preregistration remain open.
- Private dynamic generation is a risk-mitigation stress mechanism, not a
  detector and not proof of absence of training-data contamination.
