# Independent supervisor report — autopilot cycle 01

## Audit Summary

- Audit ID: `20261008-autopilot-cycle-01`
- Base Git commit: `c26a800e2f45c7c5e12bf70b3f375735a6b6db12`
- Working branch: `autopilot/scientific-law-discovery`
- Stage: G0–G5 engineering validation; G6/G7 are not ready for formal evaluation.
- API/spending status: no paid or real-provider request was launched. All executed experiment outputs are Mock-labelled, while the simulator smoke path uses the vendored NewtonBench implementation.
- Current blocking items: external network prevented remote/upstream verification and push; structural/mechanistic evaluation is not implemented; real-provider pilot is not tested.

## Verification Evidence

| Command | Result | Evidence |
|---|---|---|
| `python -m pytest -q` | PASS | `31 passed` after the cycle changes. |
| `python -m unittest discover -s tests -p 'test_autopilot_harness.py' -v` | PASS | `12` harness tests passed, including fail-closed review and Git safety checks. |
| `python -m scientific_discovery.cli audit` | PASS | Required NewtonBench paths exist; configured SHA is `912a4ba5f4356ddd06acc16e44460ca30be4abc2`. |
| `python -m scientific_discovery.cli prepare --limit 12 --seed 42 ...` | PASS | Deterministic 12-task manifest generated without using outcomes. |
| `python -m scientific_discovery.cli smoke-test ...` | PASS (Mock) | Both runners completed; the real vendored direct-measurement simulator was called; validation is numeric-fit-only. |
| `python -m scientific_discovery.cli engineering-test ... --limit 12 ...` | PASS (engineering only) | 12 tasks × 2 runners = 24 completed rows; zero-law negative controls produced zero validated successes. |
| `python -m scientific_discovery.cli analyze ...` | PASS (Mock) | 24 rows, 12 paired task IDs, VLDR 0.0 for both arms; no scientific claim is made. |
| `git ls-remote --heads origin autopilot/scientific-law-discovery` | BLOCKED | GitHub connection failed through the configured proxy on port 443. |
| `git ls-remote https://github.com/HKUST-KnowComp/NewtonBench.git HEAD` | BLOCKED | Same network/proxy failure; upstream HEAD could not be independently rechecked. |

## Changes made in this cycle

- Added public NewtonBench apparatus bounds to the adapter schema and enforced them in both plan validation and oracle execution (`src/scientific_discovery/benchmark/newtonbench_adapter.py`, `src/scientific_discovery/runners/common.py`).
- Made held-out validation actions obey those same public domains rather than sampling one out-of-domain distribution for every module (`src/scientific_discovery/evaluation/law_recovery.py`).
- Preserved initial observations in both LLM-only planning and final-inference contexts, while keeping intermediate observations out of planning.
- Rejected Agent tool calls whose name is not the sole authorized `run_experiment` operation.
- Made real-provider calls fail closed when token prices are absent, so the configured cost ceiling cannot silently become zero-cost accounting.
- Corrected evaluation metadata and documentation: this implementation uses the pinned upstream ground-truth function inside a restricted project-owned numeric evaluator; it is not NewtonBench's full official evaluator, and `validated_success` currently means numeric fit only.
- Added adversarial and regression tests for all of the above.

## Gate status

| Gate | Status | Evidence / limitation |
|---|---|---|
| G0 upstream adapter, SHA, license | BLOCKED | Adapter and MIT license are present and the simulator is executed, but remote SHA/provenance could not be rechecked because network access failed. |
| G1 LLM-only frozen-plan isolation | PASS (Mock architecture) | Observation-swap, plan-hash, no-tools, no-mid-batch-call and finalization tests pass. A real provider trace is not tested. |
| G2 Agent closed loop | PASS (Mock architecture) | Feedback-conditioned action test and unauthorized-tool test pass. This does not establish real-model scientific reasoning. |
| G3 shared budget/action/privacy boundary | PASS (deterministic implementation) | Shared ledger, domain checks, tool boundary and secret-free traces are tested; token equality between arms is not claimed. |
| G4 evaluator adversarial validity | NOT TESTED | Numeric wrong-parameter, overfit, malformed and illegal-code cases pass, but structural recovery and mechanistic validity are explicitly unimplemented. |
| G5 Mock end-to-end + real simulator smoke | PASS (Mock only) | The simulator is real; provider and formal science result are not. |
| G6 manifests/failures/statistics/reproducibility | NOT TESTED | Engineering artifacts exist, but no real 24-task pilot or repeated formal runs have been performed. |
| G7 preregistration lock | BLOCKED | Formal thresholds, structural evaluator, real pilot estimates and external provenance are not complete. |

## Findings

| ID | Severity | Problem | Evidence | Required remediation | Status |
|---|---|---|---|---|---|
| SUP-001 | P1 | Formal scientific scoring is incomplete. | `src/scientific_discovery/evaluation/law_recovery.py`; `structural_recovery=None`, `mechanistic_validity=not_implemented`. | Define and test deterministic structural/equivalence and mechanistic/OOD criteria, then preregister thresholds before formal runs. | OPEN — blocks G4/G7 |
| SUP-002 | P1 | Real-provider pilot and retry/cost behavior are not empirically verified. | No real API request was launched; only provider failure paths are unit-tested. | With explicit authorization and a hard spend ceiling, run a minimal provider smoke test, archive redacted traces, and rerun the isolation audit. | OPEN — not tested |
| SUP-003 | P1 | Upstream provenance and GitHub delivery are externally blocked. | Both `git ls-remote` commands failed with proxy connection errors; vendored NewtonBench is not a separate Git checkout. | Restore network/Git credentials, verify the configured upstream commit and license, then push this branch to `origin/autopilot/scientific-law-discovery`; do not claim push success before confirmation. | BLOCKED |
| SUP-004 | P1 | Formal statistical validity is not established. | Only a 12-task Mock engineering run was executed; the analysis reports unclustered paired bootstrap over task rows. | Freeze pilot/formal task strata, repeat counts and law-family clustering plan before any formal API batch; retain all failures in denominators. | OPEN — not tested |
| SUP-005 | P2 | Classical baseline is only an extension interface. | `src/scientific_discovery/evaluation/classical.py` retains `NotImplementedError`. | Implement only if a classical comparison is added to the study; otherwise keep it explicitly out of the claims. | DOCUMENTED |

## Scientific validity

- LLM-only strict non-adaptivity: PASS for the deterministic architecture and Mock adversarial tests; real provider requests remain unverified.
- Agent feedback control: PASS for the Mock architecture; this does not prove useful scientific reasoning by a real model.
- Resource fairness: experiment/action domains and ledger limits are shared. In the Mock 12-task analysis, recorded input tokens differ (`llm_only=3216`, `single_agent=5118`), so cost/token efficiency must be reported rather than treated as matched.
- Hidden-law isolation: public descriptions omit known hidden-source tokens, the evaluator is called after submission, and no code/file tool is exposed. Full runtime/file-system adversarial review remains incomplete for a real provider.
- Objective evaluation: numeric fit is implemented; structural and mechanistic validity are not. No claim of discovering a human-unknown law is permitted.
- Selection bias: the engineering manifest is deterministic and outcome-independent, but it is not a preregistered formal test set.

## Next Required Actions

1. Restore network and verify the exact NewtonBench SHA/archive provenance and push status.
2. Complete deterministic structural/mechanistic evaluation or explicitly narrow the preregistered claim to numeric law-function recovery.
3. Obtain explicit real-API authorization and a spend ceiling, configure positive token prices, run one provider smoke test, and rerun the isolation audit.
4. Freeze a pilot manifest and clustered statistical plan; run the authorized pilot while preserving every failure and operational status.
5. Do not start a 72–96 task paid evaluation or claim Agent superiority while SUP-001–SUP-004 remain open.

This report distinguishes implemented software behavior, executed verification, blocked external work, and untested scientific claims. Passing the tests does not establish the research hypothesis.
