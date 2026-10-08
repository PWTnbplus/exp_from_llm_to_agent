# Setup: install and run the self-supervising Codex skill

This bundle is designed to be **copied into the root** of a writable clone of `https://github.com/PWTnbplus/exp_from_llm_to_agent`. Preserve its relative `.agents/skills/...` layout, `AGENTS.md`, `scripts/`, `tests/` and `.github/workflows/` files. Keep the two original reference specifications intact.

## Prerequisites

1. Install Python >=3.10, Git and an installed, authenticated `codex` CLI. Verify `codex exec --help` supports `--sandbox workspace-write` and `-o/--output-last-message` (the current script uses both). If installed CLI differs, adapt using its real help output; do not silently bypass sandboxing.
2. Configure Git identity and an **authenticated GitHub account/token with WRITE permission** to `PWTnbplus/exp_from_llm_to_agent`, e.g. Git Credential Manager or SSH. `git remote -v` must point to that exact repository. The credential is stored in the Git credential helper, not inside this project.
3. A fresh repository may be empty/unborn. Local branch creation and first push initialize it. Keep `main` protected; work on feature branch `autopilot/scientific-law-discovery`. The repository admin should enable branch protection/required CI when available.
4. Ensure upstream NewtonBench can be accessed (network and dependencies). Codex workspace-write sandboxes commonly restrict network; preclone/pin upstream sources using a trusted operator if network is unavailable. Do not grant unrestricted shell/network access to the Agent being evaluated.
5. Run this offline harness test before any automated model call:

```bash
python -m unittest discover -s tests -p 'test_autopilot_harness.py' -v
```

## Execution

```bash
# inspect intended git host first
git remote get-url origin
codex exec --help

# launch bounded unattended local cycles; each cycle attempts a commit and push
python scripts/autopilot.py --cycles 12 --test-cmd 'python -m pytest -q'
```

Optional `--dry-run` checks commands and repository prerequisites without calling Codex. Optional `--no-push` is for LOCAL SELF-TESTS ONLY and cannot satisfy the user's GitHub delivery requirement.

The runner performs independent Codex development and read-only adversarial review, executes deterministic test commands, writes versioned audit artifacts and attempts a Git push after every cycle. An audit is **not** independent proof simply because another LLM produced it: deterministic tests and repo checks are authoritative where available, and the reviewer must cite exact evidence.

If a cycle is incomplete or blocked, its audit and code changes still get a `wip:` commit and push when safe. A P0/P1 failure keeps the project unapproved and must be repaired in later cycles. If the push fails, the run stops rather than pretending synchronization succeeded. A completion PR is generated through `gh pr create` only if GitHub CLI is present and authenticated; otherwise create it manually from the pushed feature branch. No automatic merge.

**Safety:** by default the skill does not run large-scale paid LLM experiments. Change this only after a separate explicit user authorization and spend ceiling. Do not put API keys or any secrets in CLI args, reports or git commits.

**Unattended means for the duration of this local launched process**, not a hosted persistent agent. For recurring execution, configure a trusted external scheduler/runner with bounded runtime and least-privilege GitHub credentials. The GitHub Action in this bundle is a CI verifier, not an AI developer with credentials.

## V2 stateful handoff

The newer skill is `.agents/skills/scientific-law-recovery/SKILL.md`. It contains the complete V1 bundle rather than replacing the original references. Read `RECOVERY_SETUP.md`, run `python scripts/recovery_state.py bootstrap`, and use `python scripts/autopilot.py --resume-only ...` to repair only unresolved issues/missing gates. Issue/verification state is persisted in `docs/state/` for a new agent to inherit without repeating verified work.
