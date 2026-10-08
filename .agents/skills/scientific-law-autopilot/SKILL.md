---
name: scientific-law-autopilot
description: End-to-end build, adversarial self-audit, and reproducible LLM-only versus single-Agent scientific law discovery experiments. Reuse NewtonBench before writing simulators; enforce nonadaptive LLM isolation, held-out validation, gated reviews, and commit/push every work cycle to PWTnbplus/exp_from_llm_to_agent.
---

# Scientific Law Discovery Autopilot

## Trigger
Use when asked to build, continue, audit, repair, or run the **LLM-only vs single-Agent scientific-law discovery** project, especially when asked to work autonomously, self-supervise, reuse an existing benchmark, or submit every change to GitHub.

## Mandatory source of truth
Before editing code, read both bundled references in full:
- `references/development_original.md` — the user's complete development specification.
- `references/supervision_original.md` — the user's complete independent review and acceptance specification.

The user-provided documents are preserved, not replaced by this condensed operational skill. Where this skill adds stricter Git, privacy, or statistical safeguards, follow the stricter rule. Where implementation must differ from a source document, justify the difference in `docs/decisions.md` and an audit entry. Do not quietly erase requirements.

## Goal and scientific claims
Investigate whether a **single adaptive LLM-driven Agent** more reliably rediscovers objective scientific laws than an **open-loop non-Agent LLM**, given matched initial data, scientific task, experiment action space, scientific observations and clearly accounted computational budget. Do not assume Agent superiority. Explicitly label this as *scientific law rediscovery*, not a human-unknown discovery. Open-loop versus closed-loop identifies adaptive decision value, not superiority over all conceivable LLM strategies.

## Execution contract: fully automatic *within the authorized Codex run*
1. Inspect repo, remote, git state and access; preserve existing user changes. Default target: `PWTnbplus/exp_from_llm_to_agent`; work on `autopilot/scientific-law-discovery`, never force-push, never silently write to `main`.
2. Audit existing projects: NewtonBench (primary), SciLaws-Bench and ODEBench (optional), PySINDy and SRBench (reference). Inspect real source, licences, API and pinned SHAs. Prefer adapters over rewritten simulators; avoid invented official task counts or unsupported claims.
3. Implement the smallest end-to-end scientific task using the actual upstream simulator and objective evaluator. Build out 12-task engineering checks, then 24-task pilot, then preregistered 72–96 task evaluation only with scientific validity, sufficient budget and permission. Number of tasks does **not** equal independent laws.
4. The **LLM-only runner** gets initial data, generates and SHA-256 freezes *all* experimental actions before any new observation, then a nonintelligent scheduler executes them without additional model decisions; only afterward does the model infer the law. No tool calls, ReAct, code execution, hidden source access or mid-experiment replanning. Enforce by code, not prompt alone.
5. The **single Agent runner** can choose each allowed experiment from actual observed feedback with the *same model* and action domain, strictly metered. No hidden oracle source, unrestricted shell, browser or evaluator access.
6. Keep discovery and validation data separate. Where available, combine official scoring, structure/equivalence checks and blinded OOD intervention prediction. Record output schema, model/version, sampling parameters, task ID, deterministic seeds, token and tool costs, execution trajectory and failure states.
7. Maintain preregistered VLDR as primary outcome, paired delta and clustered uncertainty across law families. Missing tasks and failures remain in denominators. Never improve Agent scores via task filtering or evaluator changes.
8. **Self-supervision loop:** implement a small unit; run deterministic tests; adversarially inspect diffs; run independent read-only reviewer; classify P0/P1/P2/P3; repair and rerun adversarial + regression tests. Read the entire supervisor reference for each audit gate. Assertions must be executed, not just described.
9. **Every work cycle** (including incomplete cycles) writes a dated auditable report and commits the actual code/report changes, then pushes to `origin/autopilot/scientific-law-discovery` if remote write access is available. On unresolved P0/P1 label the commit `wip:` and forbid claiming PASS or merging. Never overwrite remote history; verify remote points to the expected repository. If no write permission, record BLOCKED and provide exact remediation; never claim push success.
10. Commit only safe source and audit artifacts. Never commit API keys, `.env`, provider payload secrets, private datasets, model transcripts containing credentials, huge generated artifacts or raw protected answers. Default **no paid API tasks** until explicitly authorized, with hard ceilings.
11. After all gates, create a PR for human review, rather than auto-merging `main`. Finish with command/test evidence and commit URLs. A prompt is not an always-on service: real unattended recurring operation needs a running trusted Codex host with credentials and scheduling.

## Mandatory gate checks
- `G0` actual upstream repository adapter, pinned SHA/licensing, no unapproved simulator reimplementation.
- `G1` LLM-only frozen-plan nonadaptivity proven by injecting two different intermediate observation sequences; identical subsequent action trace and plan hash.
- `G2` Agent closed-loop action ability proven by observation-conditioned mock intervention; real provider traces separately verified.
- `G3` shared budgets, observation volumes, action domains, task/model configuration, no secret leakage or hidden answer exposure.
- `G4` evaluator adversarial tests: true, algebraic-equivalent, wrong-parameter, in-domain-only overfit, malformed and empty outputs.
- `G5` mock end-to-end and real upstream simulator smoke test (never mislabel mock as science results).
- `G6` run manifests, failures, statistics, reproducibility metadata, figures, cost caps, retry/resume.
- `G7` final preregistration lock before paid formal evaluation.
If a gate is untested, mark NOT TESTED, never PASS. P0/P1 block readiness regardless of green unit tests.

## Autonomous program
The companion runner is `scripts/autopilot.py`. From a writable clone of the target repository after installing this bundle, use:

```bash
python scripts/autopilot.py --cycles 12 --test-cmd 'python -m pytest -q'
```

It launches Codex developer and independent reviewer executions, records reports, runs tests, carries out feedback/repair loops, and attempts `git commit` plus `git push` each cycle. It does not run without a host, working `codex` CLI, network access, repo push permission or any permissions required by upstream dependencies. Read `AUTOPILOT_SETUP.md` first. Check the installed Codex CLI help; prefer `codex exec --sandbox workspace-write` over deprecated flags. Never switch to unrestricted sandbox automatically.

## Final reporting contract
Always state distinct statuses: IMPLEMENTED, VERIFIED, BLOCKED, NOT TESTED. Give task count, upstream SHA, git branch and commit, exact test commands and exit status, actual remote push status, scientific validity caveats, API/spending status, links if remotely confirmed, and next action. Never claim that code passing tests proved the scientific hypothesis.
