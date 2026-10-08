---
name: scientific-law-recovery
description: V2 stateful successor to scientific-law-autopilot. Resume the scientific-law LLM-vs-Agent project from committed issue ledger, repair verified outstanding defects only, adversarially test fixes, publish resolved/unresolved reports and Git commits on every cycle without rebuilding completed work.
---

# Scientific Law Recovery & Handoff — V2

## Use this skill when
- A new Codex agent inherits an incomplete LLM-only vs Agent scientific discovery repository.
- The previous Codex stopped midway, reached its cycle ceiling, encountered errors, or left unresolved audit findings.
- The user asks to automatically repair remaining defects and report both solved and unsolved issues.

**This skill is a strict superset of V1**, not an independent greenfield specification. V1 remains in `.agents/skills/scientific-law-autopilot/` along with complete unchanged user-provided `development_original.md` and `supervision_original.md`. Use V1 implementation and scientific audit requirements, but **V2's persisted state, selective-repair and handoff rules take precedence** where they concern execution order and continuity. Never overwrite the original specifications.

## The no-repeat startup protocol (MANDATORY)

1. Run `git status --porcelain=v1`, `git remote -v`, `git branch --show-current`, `git log -8 --oneline`. Protect existing work and do not assume anything about a previous chat.
2. Run `python scripts/recovery_state.py bootstrap`. This imports unprocessed `docs/audits/cycle-*/audit.json` records without repeating previously ingested reports. It writes:
   - `docs/state/issues.json` — structured authoritative issue lifecycle ledger;
   - `docs/state/UNRESOLVED_REPORT.md` — open/blocked/resolved-unverified and verified outcomes;
   - `docs/state/HANDOFF.md` — self-contained next-agent instructions and next target.
3. Read **all three** files, plus `docs/state/gates.json` if present. Inspect only affected source/test files and evidence in the referenced audits. Do not rerun repository discovery, cloned benchmark downloads, adapters or completed milestones without fresh evidence of breakage.
4. If legacy free-form reports exist (for example `docs/audits/supervisor_report.md`), inspect them once and create traceable issue entries through documented reviewer findings; do not silently treat Markdown as a verified machine-readable ledger.
5. Select the highest-priority unresolved issue (P0 before P1, then P2, P3); if none exists, inspect the remaining NOT TESTED/FAIL/BLOCKED G0–G7 gate(s) and implement the smallest missing deliverable. If all gates already have evidence, stop; do not perform invented busywork.

## Persistent issues, not conversation memory

Canonical states: `OPEN`, `IN_PROGRESS`, `BLOCKED`, `RESOLVED_UNVERIFIED`, `VERIFIED`.

- An issue **remains unresolved until evidence-backed explicit verification**. Review omission, a developer saying "fixed," a passing unrelated test, a commit message or changed filename cannot close it.
- Use stable `ISSUE-<12 hex>` IDs, reuse IDs in subsequent reviews. Do not create a new issue for the same underlying defect each cycle.
- Record the exact failure evidence, remediation, severity, attempt count, blocker reason and verification command. Failed verification reopens the defect; regressions reopen previously verified defects.
- Blocked external permissions or infrastructure are still listed under unresolved, with an exact unlocking action. Never mask permission failures with fabricated PASS states.
- `completed_work[]` records validated code paths, pinned upstream commits and commands. Treat it as a cache of **verified milestones**, not a project-complete claim. Never redo verified work just to consume a cycle.
- A new agent only needs the ledger, source tree, targeted source documents and test evidence. It does not need the previous conversational context or previous agent model state.

## Execute the targeted repair loop

Use:

```bash
python scripts/recovery_state.py bootstrap
python scripts/recovery_state.py next
python scripts/autopilot.py --resume-only --cycles 12 --repairs 2 --test-cmd "python -m pytest -q"
```

The V2 runner preserves the original trusted cycle: developer -> host tests -> independent read-only reviewer -> repair -> rerun -> report -> commit/push. In resume mode it injects the persisted issue list and verified completed work into both developer and reviewer prompts. Do not use `--no-push` for the user's deliverable, except for local tests.

On each cycle:
1. **Choose** the top unresolved issue or explicitly missing gate.
2. **Reproduce** its failure before altering the implementation, when feasible.
3. **Fix** the smallest relevant implementation section; reuse all available open-source scientific tooling.
4. **Verify** with issue-specific tests, adversarial injection and global regression as appropriate. Do not run expensive unrelated tests every tiny edit; mandatory gates and pre-PR validation still require comprehensive tests.
5. **Review independently**; return findings with stable IDs and explicit resolution verdicts. If a repair is plausible but not proven, classify `RESOLVED_UNVERIFIED`.
6. **Update** `issues.json`, `UNRESOLVED_REPORT.md` and `HANDOFF.md`; write a timestamped audit.
7. **Commit and push** actual reviewed source, tests and reports to `origin/autopilot/scientific-law-discovery` after each cycle. Use WIP status for unresolved P0/P1; no force push or automatic main merge. If push fails, make the failure explicit and stop claiming remote completion.
8. **Continue** while the trusted host process is running, within its configured cycle/time/cost limits. A skill file by itself cannot guarantee permanent background operation.

## Scientific safety / original constraints (inherited intact)

- Scientific claim: compare **open-loop nonadaptive LLM-only** and **closed-loop single Agent** for verified scientific law *rediscovery*, not human-unknown discoveries.
- LLM-only: one initial prompt generates a complete immutable SHA-256 experimental plan; batch execution receives no model feedback; final law inference sees all results only after the full plan executes. No tool calling or mid-experiment replanning. Test by observation-swap perturbations.
- Agent: identical base LLM and scientific experiment action space; bounded observation-conditioned experimentation; no evaluator, hidden law source or unrestricted code access.
- Reuse real pinned NewtonBench simulator and official evaluator where applicable. SciLaws-Bench/ODEBench/PySINDy/SRBench only after inspecting actual interfaces/licences. No fake scientific tasks or scores.
- Never silently ignore failed tasks or violations, tune on formal held-out evaluation or treat many variants as independent natural laws.
- Primary outcome: preregistered VLDR with independent validation and paired/cluster-aware inference; record token/cost/time, task lineage and failures.
- No paid evaluation batches without a separate explicit user authorization and hard cost ceiling. Credential files and private raw results never enter commits.

## Gates and stop rules

- G0: pinned true simulator and licensing
- G1: strict LLM-only nonadaptivity
- G2: feedback-dependent Agent action capability
- G3: shared budget and hidden-answer isolation
- G4: objective evaluator adversarial cases
- G5: real simulator + mock pipeline smoke test
- G6: complete reproducibility / results / stats / retry gates
- G7: frozen preregistration before costly formal testing

If any hard gate lacks executed evidence, mark NOT TESTED or FAIL, not PASS. Never mark the whole project complete only because `pytest` passes. If the target repository is empty, both V1 and V2 will necessarily identify missing gates; the "no repeat" rule starts as verified work accumulates.

## Reporting contract for each handoff

In `docs/state/UNRESOLVED_REPORT.md`, always include: verified resolved issues with evidence, unresolved issues with severity and attempts, external blockers and specific resolution conditions, verified milestone inventory (what the successor should not rebuild), the exact next priority, test/commit/push statuses, and scientific caveats. At the end of a run state whether the Git remote was actually updated. Never invent SHA, tests, publications or results.

For setup, tools and Git credentials, read the retained `AUTOPILOT_SETUP.md` and `RECOVERY_SETUP.md`.
