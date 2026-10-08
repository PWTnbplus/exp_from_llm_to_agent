# From LLMs to Autonomous Agents

This is a controlled, reproducible comparison between a strict open-loop LLM-only baseline and a single feedback-controlled scientific agent. It currently integrates the direct-measurement subset of NewtonBench through an adapter and uses a pinned upstream tree.

The important implementation boundary is `src/scientific_discovery/runners/llm_only.py`: the plan is submitted once, hashed, executed without a provider reference, and only then sent to final inference. `single_agent.py` exposes one operation, `run_experiment`, under the same budget ledger.

## Setup

From this directory:

```text
python -m pip install -e .
python -m pytest -q
```

The upstream simulator is vendored under `third_party/NewtonBench/`. Its current pinned commit is recorded in `configs/experiment.json` and `docs/open_source_audit.md`. Copy `.env.example` only when a real API is intentionally configured. No API key is required for tests or the smoke test.

## Commands

```text
python -m scientific_discovery.cli audit
python -m scientific_discovery.cli prepare --limit 12 --output task_manifest.json
python -m scientific_discovery.cli smoke-test --output results/smoke
python -m scientific_discovery.cli engineering-test --manifest task_manifest.json --limit 12 --output results/engineering_validation
python -m scientific_discovery.cli pilot --manifest task_manifest.json --runner both --provider mock --limit 12 --output results/pilot
python -m scientific_discovery.cli pilot --manifest task_manifest.json --runner both --provider mock --limit 12 --resume --output results/pilot
python -m scientific_discovery.cli analyze --input results --output figures
```

The smoke test, engineering validation, and the example pilot use a deterministic Mock Provider and are labelled as mock data in both JSON and figures. The engineering validation intentionally submits a zero-law placeholder so that the full 12-task pipeline and negative evaluator path are exercised; these outputs must not be used as formal scientific results. A real run requires environment variables from `.env.example`, positive input/output token prices, `--provider openai`, and the explicit `--allow-paid` flag. The provider fails closed when pricing is absent. `pilot` refuses to overwrite an existing result unless `--resume` is supplied. Formal paid execution is never auto-started.

## Output and auditability

Each recorded run stores the task ID, runner, observations, frozen plan/hash when applicable, a redacted provider request/response trace, provider metadata, budget usage, and blind validation result. Validation uses new seeded conditions and is not returned to the model before final submission. The frozen `scoring-v1` evaluator reports numeric fit, executable-law structural recovery, legal OOD intervention fit, and mechanistic validity separately; all three criteria are required for `validated_success`. The required research-method documents are in `docs/`; prompt versions are in `prompts/`.

Both NewtonBench runners and the 100-task theory benchmark write append-only
JSONL traces when an output directory is supplied. The trace contains actual
model messages/responses, tool calls/results, explicit hypothesis fields,
predictions and post-submission evaluation events. It does not invent hidden
chain-of-thought or record API credentials. Each run has its own `run_id`, and
the result JSON points to `logs/<run_id>.jsonl`, so repeated runs do not
overwrite history.

For example, after a run:

```text
results/pilot/logs/<run_id>.jsonl
```

Each line is one durable JSON event. `MODEL_INPUT` contains the exact
messages/tools sent to the provider, and the following `MODEL_OUTPUT` contains
the exact returned content, tool calls, token usage and latency. Agent tool
inputs/results and evaluator events use the same file. No hidden chain of
thought is generated, and API credentials are redacted.

## Scope boundary

The current supported registry is 108 direct-measurement combinations (12 domains × 3 law difficulties × 3 variants). NewtonBench's dynamic system types need a separate measurement-information budget and are not silently included. The project does not claim that recovering a public benchmark law is discovering a human-unknown natural law.

## Theory chemistry/biology benchmark

The default isolated `theory-benchmark-v1` contains 100 answer-separated theoretical chemistry and theoretical biology reasoning tasks (50 per domain; 34/33/33 by difficulty). The v2/v3 expansions remain available explicitly, but are not the scope of the controlled 100-task comparison. Contamination controls classify public tasks as classical, structure-transformed, or private-dynamic stress cases; the private seed and answers never enter model prompts or ordinary results. Validate with `python -m scientific_discovery.cli theory-validate`; see `docs/theory_benchmark.md`. This extension does not replace the pinned NewtonBench experiment.
