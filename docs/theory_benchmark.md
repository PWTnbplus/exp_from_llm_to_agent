# Theory chemistry/biology benchmark

The default controlled comparison uses `theory-benchmark-v1`: 100 answer-separated synthetic mathematical tasks, with 50 Theoretical Chemistry and 50 Theoretical Biology tasks and difficulty counts 34/33/33. The expanded v2 and v3 datasets remain available only when selected explicitly.

Model-visible tasks, answer keys and manifests are separate:

- public tasks: `data/theory_benchmark_v1/public_tasks.json`
- evaluator-only answer key: `data/theory_benchmark_v1/answer_key.json`
- manifest: `data/theory_benchmark_v1/manifest.json`

The runner loads only public tasks before model dispatch. The answer key is opened by `verify_candidate` after the candidate is submitted. Ordinary result JSON and Trace events do not contain answer values; mismatch diagnostics are redacted.

## Validation and commands

```text
python -m scientific_discovery.cli theory-validate
python -m pytest -q tests/test_theory_benchmark.py
python -m scientific_discovery.cli theory-contamination-audit
python -m scientific_discovery.cli theory-contamination-audit --private-seed <operator-secret>
python -m scientific_discovery.cli theory-run --task-id TC-L1-001 --mode G1 --provider mock
python -m scientific_discovery.cli theory-batch --level 1 --mode G4 --provider mock
```

The private seed must not be committed or written to ordinary results. The audit reports a seed fingerprint and count, never private answers.

## G1-G5 fairness contract

The executable policy is in `src/scientific_discovery/experiment/policy.py`, with the registered configuration in `configs/experiment_groups.json`:

- G1: LLM-only; no tools, memory, retrieval or transport retries.
- G2: fixed calculator assistance; only `calculate_expression`, with four compute steps.
- G3: exactly two fixed reflection calls; no tools, memory, retrieval or retries.
- G4: bounded adaptive Agent; only authorized experiment/calculator tools, with shared call and experiment budgets.
- G5: G4 plus bounded run-local memory; no cross-run memory or external retrieval.

Every model, tool, compute, memory and retrieval operation passes a controller. Policy checks, budget snapshots, denials and actual provider attempts are durable Trace events. An OpenAI-compatible provider defaults to zero transport retries; a provider configured above the group retry budget is rejected before dispatch.

## Interpretation boundary

The checker validates structured numeric, expression and categorical fields. It is not a mathematical proof. Classical public tasks are contamination-risk exposed; structure-transform cases reduce verbatim memorization risk; private dynamic cases are a stress test, not a detector and not evidence that a model has not seen the underlying theory. Mock runs validate engineering only and must not be reported as scientific performance.
