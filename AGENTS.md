# Repository-wide Codex contract

For all work on LLM-only vs single-Agent scientific law discovery, read and obey `.agents/skills/scientific-law-autopilot/SKILL.md` and both referenced original specifications. Use the self-supervision development/review loop; DO NOT take assertions of completion as test evidence.

Target GitHub repository: `PWTnbplus/exp_from_llm_to_agent`. Commit and push every substantive work cycle to `autopilot/scientific-law-discovery`, not directly to `main`, with `wip:` prefix for unresolved P0/P1. No `git push --force`, no auto-merge, no secrets or paid large-scale runs without authorization. A failed push is a visible BLOCKED state, never a silently ignored error.

Hard scientific invariants: LLM-only's full experiment action plan must be frozen before any added observation; the environment must not trigger LLM decisions mid-execution. Agent is feedback-adaptive with the same scientific experimental budget. No hidden target laws in prompts, tools, accessible local code or evaluation inputs. Prefer actual NewtonBench simulator and evaluator; tests must exercise real components, not merely file existence. Record all failures and scientific limitations.
