# Codex repository instructions — State-aware V2 scientific discovery research

Read `.agents/skills/scientific-law-recovery/SKILL.md` FIRST. It supersedes V1 on issue management, task prioritization and handoff. V1 `.agents/skills/scientific-law-autopilot/SKILL.md` and the two original full specifications are preserved and remain authoritative for scientific requirements.

A new agent must run `python scripts/recovery_state.py bootstrap` then read `docs/state/HANDOFF.md` and `docs/state/issues.json`. Fix outstanding P0/P1 issues before implementing new features; do not redo work in `completed_work` unless a regression is evidenced. Each cycle must include tests, independent read-only review, auditable reports, and git commit/push to `PWTnbplus/exp_from_llm_to_agent` on `autopilot/scientific-law-discovery` if authorized. Never claim a remote push succeeded without verifying it. Never force push or merge to main automatically.

Important experiment controls: strict frozen-plan LLM-only versus adaptive single Agent, same base model/action/experiment budget, hidden law isolation, real upstream simulator and objective held-out evaluation, no invented results, no unauthorized paid experiments. `docs/state/issues.json` is authoritative for issue status; `docs/state/UNRESOLVED_REPORT.md` is generated from it. A missing finding in one audit never means fixed.
