---
name: scientific-law-ctflow-matrix
description: V3 add-on for scientific-law-recovery: configure CTFlow API with a local key, discover/select gateway model IDs, run simultaneous per-model LLM-only vs Agent matched scientific evaluations with hard safety gates and auditable model-specific reports. Resume V2 state instead of rebuilding completed work.
---

# Scientific Law CTFlow Model Matrix — V3 Supplemental Skill

## Mandatory precedence and inheritance

This is an **add-on**, not a replacement for V2 or V1. Read `.agents/skills/scientific-law-recovery/SKILL.md` first, then this file; consult `.agents/skills/scientific-law-autopilot/SKILL.md` and original development/supervision briefs only for requirements actually affected. V2 `issues.json`, `HANDOFF.md`, G0–G7 gates and auditor loop remain authoritative. Do NOT rebuild the entire scientific experiment environment. Work only on unsolved provider/matrix issues; retain verified NewtonBench adapter, evaluator and runners.

## Documentation provenance / warning

User-provided documentation: `https://token.ctflow.cn/tokendocs`. At creation time the exact docs were not reachable from the authoring runtime (web fetch failed, and DNS was unavailable). **Therefore no claim is made that this service implements OpenAI-compatible routes, has any particular model name, or supports `/v1/models`.** The candidate `https://token.ctflow.cn/v1` in `scripts/ctflow_models.py` is an *unverified same-origin guess*, NOT an endorsed/verified endpoint. All provider properties require independent verification by Codex when networking works. Do not confuse other similarly named TokenFlow/token services with this exact provider.

1. Read the actual CTFlow docs if accessible from the user's Codex network. Record verified auth mechanism, **exact API base URL**, chat/generation endpoint, models listing endpoint, streaming quirks, model ID spelling, context/pricing availability, token usage, rate limits, response types, tools support, error structure and references in `docs/provider/CTFLOW_PROVIDER_AUDIT.md` with retrieval date.
2. If the docs are unavailable, probe `GET /models` at the **same host** *without credentials* first. Treat only 200/401/403 as evidence of a plausible catalog path; then authenticate with a local key over HTTPS **without following redirects**. A 200 with a parseable model list is evidence of model discovery, not proof that completions work. Never silently switch to an unrelated gateway domain or leak keys on redirects.
3. If the guessed base URL is invalid, use CTFlow's verified base URL from documentation or user console via optional `CTFLOW_BASE_URL=` in `.env`; tell the user the URL must be supplied. Do not invent endpoints or model names to satisfy a one-field UX promise.
4. If the catalog is absent/unavailable, allow exact model IDs entered interactively, and mark them `manual_unverified` until an authorized minimal live preflight succeeds.

## What the user actually configures

- Copy `.env.example` to `.env`; fill **only `CTFLOW_API_KEY`** when the provider's actual endpoint matches the tested default. If not, also set `CTFLOW_BASE_URL`. This is a provider constraint, not a missing prompt.
- No hardcoded API key, no key in CLI flags, YAML, JSON, Git, logs, reports, exception messages or Codex prompts. Process env overrides local `.env`; secrets stay local.
- `python scripts/ctflow_models.py probe` — non-secret reachability probe.
- `python scripts/ctflow_models.py list` — live model catalog when supported; does not generate tokens but may be billable by provider; network call.
- `python scripts/ctflow_models.py select --interactive` — user selects indices; or `select --models ACTUAL_ID_1 ACTUAL_ID_2` manually. Never hardcode invented models.
- `python scripts/ctflow_models.py verify --allow-paid` — short live generation preflight for each selected model; may incur charges and requires explicit authorization. Record compatibility per exact model ID and base URL.
- `python scripts/model_matrix.py plan` — dry-run plan, no API key needed, never paid.
- `python scripts/model_matrix.py run --allow-paid --max-parallel-models 2` — only after validated project runner, task manifest, model preflight and explicit nonzero cost cap; NEVER start based solely on skill installation.

## Automatic integration / no-repeat Codex repair task

The V2 archive bundles a **supervisory harness only**, not yet a complete NewtonBench scientific runner. `configs/model_matrix.json` therefore has `runner_command: []` and `runner_supports_budget_enforcement: false` intentionally. Neither scripts nor reviewer may claim real model testing is ready at this point.

An inheriting Codex must:

1. `python scripts/recovery_state.py bootstrap`; read open issues and verified milestones. If unfinished G0–G7 research engine gates exist, solve them before real API batch tests.
2. Inspect *existing* actual experiment CLI and Provider abstraction, avoiding duplicate physics engine/agent implementations. Wire CTFlow via a **thin protocol adapter** and a verified array-form `runner_command` into existing code. Use official SDKs only if verified compatible; avoid fabricating tool API calls. Use tool-free LLM-only and bounded experiment-tool Agent, **same base model per pair**.
3. Implement official provider model ID discovery, minimum working chat request / response validation with supported parameters only, credentials masking, retry for retryable 429/5xx with bounded backoff, model-specific rate and concurrency controls. No free-text tools, shell, browsing or evaluator access in the scientific Agent.
4. Implement/project-test the sub-run contract: a real execution writes `{output}/result.json` with `status:COMPLETED`, `model_id`, `runner` (`llm_only` or `agent`), `protocol_valid:true`, `evaluator_valid:true`, `mock:false`, actual `cost_usd` and `budget_enforced:true`. Exit 0 alone NEVER suffices. The evaluator must be objective with official upstream task records, independent test split and prerecorded conditions.
5. The host matrix will apportion `max_total_cost_usd / (2 × models)` per mode job. A validated runner MUST refuse API calls that could violate its **hard** local cap and record cost using provider-verified billing or conservative worst-case bound. If uncertain, do not claim hard cap; leave `runner_supports_budget_enforcement:false` and BLOCK live execution. Matrix-level cap without runner enforcement is NOT a safe spending limit.
6. Each model's Agent and LLM-only pair uses exactly the same model ID, manifest, initial observations, experimental call budget, oracle access, evaluator and hold-out scientific tasks. Different model pairs can run simultaneously. Parallelism alone must not change fairness within a pair; use independent output directories, no cross-run caches, stable seed manifests and per-provider rate limits.
7. Model matrix is experimental *infrastructure*, not a second scientific discovery benchmark. Report per-model paired `ΔVLDR`, OOD error, experiment tokens/calls/cost/failure rates, hierarchical CI and correct unit of analysis. Do not pool task variants as independent laws or treat different models as replicates of the same model. If some model cannot serve required structured output, report incompatibility rather than quietly drop it.
8. Extend V2 issue ledger (`docs/state/issues.json`) with provider/model-run failures, write `docs/state/HANDOFF.md` and an updated unresolved report. On each Codex repair cycle, audit, targeted tests, regression, commit and push only reviewed files to `autopilot/scientific-law-discovery` when credentials have write access. Never include `.env`, `runs/`, model raw prompts, hidden equations or credentials. No force-push and no auto merge.

## Required adversarial tests

- API key is never stored in `.env.example`, model manifests, logs or git diff; no redirect key forwarding; TLS only.
- Catalog failure cannot cause silent selection of fictitious or unrelated provider models.
- Discovery and manual selection preserve exact provider IDs and report provenance.
- Selecting 3 models produces **six runs** grouped in three matched LLM-only/Agent pairs, not a misleading 3-vs-3 unpaired sample.
- `max_parallel_models=1` serializes; `=2` runs two model pairs concurrently; a pair never shares in-memory task state with another pair.
- Identical hidden task manifest/hash, action schema and budget in each paired execution.
- LLM-only plan remains frozen and does NOT receive interim feedback; tool definitions absent.
- Agent receives bounded observations and can condition its actions on them, no access to hidden target law.
- 401/403/429/500, malformed JSON, unsupported models, missing token usage, cost cap, interruption, resume, timeout, partial pair and crash cases produce auditable failures, NOT fabricated scores.
- `python scripts/model_matrix.py plan` works without API key and without paid calls. `run` is rejected unless explicit `--allow-paid`, real CLI, locked tasks and tested hard cap exist.
- All statuses persisted to V2 issues ledger; a handoff successor continues only unresolved work.

## Completion criteria

`G8 provider gateway verified`, `G9 model discovery/selection`, `G10 model-paired concurrency/isolation`, `G11 real provider budget & science audit` are add-on gates. Mark NOT TESTED/FAIL/BLOCKED until actual test evidence exists, including docs/API reachability. A Mock Provider test is NOT evidence of true CTFlow compatibility. Never claim a successful scientific comparison without actual paid scientific evaluations, objective validation and trustworthy statistical evidence.

## Handoff

Every new agent: run V2 bootstrap, read issue ledger, current selected model IDs (never secrets), inspect existing provider integration and G8–G11 evidence, repair only highest unresolved gate, rerun tests and report solved/unsolved. No repeated repository cloning or recreation of validated runners.
