# CTFlow Multi-model add-on for Scientific Law Recovery V2

## Important documentation status

The documentation URL provided by the user is `https://token.ctflow.cn/tokendocs`. Its contents could not be retrieved when this bundle was authored. The temporary default `https://token.ctflow.cn/v1` is **not verified**. Before real paid use, a Codex must retrieve provider docs or API-console base URL and validate the actual endpoint with safe probes and test calls. If the actual API hostname/path differs, edit only optional `CTFLOW_BASE_URL` in your local `.env` (or use an environment variable).

## Install as overlay (retain previous work)

Unzip over the repository ROOT that contains the V2 recovery skill. It includes V1 + V2 intact; merges add the V3 CTFlow skill and helper scripts. The package does **not** pre-create `docs/state/issues.json` or overwrite any existing verified handoff ledger. Verify `AGENTS.md` and skill activation.

## For the human user

```bash
cp .env.example .env
# Open local .env and fill CTFLOW_API_KEY only. Do not paste secrets in chat.
python scripts/ctflow_models.py probe
python scripts/ctflow_models.py list
python scripts/ctflow_models.py select --interactive
# Optional, potentially billed one short generation per selected model:
python scripts/ctflow_models.py verify --allow-paid
# Or if the API does not publish a model catalog:
python scripts/ctflow_models.py select --models EXACT_MODEL_ID_1 EXACT_MODEL_ID_2
python scripts/model_matrix.py plan
```

`list` uses the API key to request a model catalog; the first endpoint reachability probe sends **no credentials**. By default the key is only ever read locally. Selected model IDs are written to ignored `configs/selected_models.json` without secrets. You may select 1, 2, or more models. Only the selected models are tested; never silently substitute aliases or default models.

## Developer / Codex gate

V2 is a developer + reviewer harness, not the complete scientific research CLI. Codex must integrate this new model matrix with its ACTUAL built-and-tested experimental entrypoint and put the verified argv list in `configs/model_matrix.json` under `runner_command`, with matching `{model}`, `{mode}`, `{manifest}`, `{output}`, `{max_experiments}` arguments. Do not edit scientific rules to make the Provider fit; use a thin adapter.

The actual scientific runner must enforce costs before API calls, emit audited cost usage, not use hidden targets or tools in LLM-only, and create `result.json` per mode with required quality fields (see `SKILL.md`). When tests prove this, set `runner_supports_budget_enforcement` to true and **explicitly choose** a nonzero USD cap. This safeguard means the Skill will not launch paid evaluations simply because the user entered an API key.

```bash
python -m pytest -q tests/test_ctflow_matrix.py
python scripts/recovery_state.py bootstrap
python scripts/autopilot.py --resume-only --cycles 12 --repairs 2 --test-cmd 'python -m pytest -q'
```

Only after actual integration and explicit authorization:

```bash
python scripts/model_matrix.py run --allow-paid --max-parallel-models 2
```

The model pair order is counterbalanced. Separate output folders prevent collisions; `runs/` is gitignored, and raw API logs are not published. For scientific comparisons, each model must run **both** modes with identical tasks and budget. Run directory contains `summary.json` showing verified/failed pairs and reasons. The current host orchestrator does not independently validate scientific claims; that is the evaluator and reviewer responsibility.

## GitHub handoff and permissions

Target: `https://github.com/PWTnbplus/exp_from_llm_to_agent`. The V2 runner uses a dedicated `autopilot/scientific-law-discovery` branch, pushes on each audited repair cycle and never force-pushes or merges main. Requires actual Git credentials with write access; an AI prompt cannot grant them. If the repo is empty, initialize it first. Commit only public code/tests/redacted reports, never `.env`, keys, hidden test answers or raw model responses. Retry after a blocked push only once permissions are fixed and the remote branch state is inspected.

## Limitations

- No CTFlow live connectivity or live model compatibility was verified during package creation.
- The included `model_matrix.py` is a **real orchestration layer** but intentionally has no science runner wired until Codex completes the real NewtonBench research stack. A `plan` success is not a research result.
- Hard billing protection needs a verified runner implementation; the wrapper alone cannot enforce actual provider charges.
- Automatic concurrent execution requires an actively running host process/CI runner. A skill file does not create unlimited unattended background operation.
