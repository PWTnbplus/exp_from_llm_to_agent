# AI Scientific Reasoning

Engineering framework for controlled scientific-reasoning experiments that compare an open-loop LLM with bounded, feedback-controlled Agent workflows. The project studies law rediscovery and mechanism evidence; it does not claim human-unknown scientific discovery or a causal mechanism solely because an engineering test passes.

## Scientific framework

The project follows:

**Observation → Failure Identification → Causal Intervention → Mechanism Identification → Pathway Verification → Interaction → Closed-loop Research → Boundary → Prediction**

G0–G13 and G8.5 are distinct experiments. G8.5 is an independent competing-mechanism identification experiment using matched state-history pairs and information-equivalent controls, not a routine G8 ablation.

## Experiments

| Experiment | Scientific question | Description | Status | Reproduction |
|---|---|---|---|---|
| G0 | Can the protocol and isolation boundary be verified? | Protocol gate; not a model arm | IMPLEMENTED / TESTED / REAL_EXECUTED / PARTIAL | `python experiments/G0/reproduce.py` |
| G1 | What is the open-loop baseline? | LLM-only, no tools | IMPLEMENTED / TESTED / REAL_EXECUTED / PARTIAL | `python experiments/G1/reproduce.py` |
| G2 | What is the tool contribution? | Bounded fixed tool | IMPLEMENTED / TESTED / REAL_EXECUTED / PARTIAL | `python experiments/G2/reproduce.py` |
| G3 | What is the fixed-iteration contribution? | Non-adaptive reflection baseline | IMPLEMENTED / TESTED / REAL_EXECUTED / PARTIAL | `python experiments/G3/reproduce.py` |
| G4 | Does adaptive workflow add value? | Bounded Agentic Workflow | IMPLEMENTED / TESTED / REAL_EXECUTED / PARTIAL | `python experiments/G4/reproduce.py` |
| G5 | Can known answers be reverse-derived? | Reverse derivation and verification | IMPLEMENTED / TESTED / REAL_EXECUTED / PARTIAL | `python experiments/G5/reproduce.py` |
| G6 | Are conclusions premise-sensitive? | Counterfactual premise intervention | IMPLEMENTED / TESTED / REAL_EXECUTED / PARTIAL | `python experiments/G6/reproduce.py` |
| G7 | Where does reasoning fail? | Failure localization and local recovery | IMPLEMENTED / TESTED / REAL_EXECUTED / PARTIAL | `python experiments/G7/reproduce.py` |
| G8 | Does a correction mechanism cause change? | Multi-arm causal intervention | IMPLEMENTED / TESTED / REAL_EXECUTED / PARTIAL | `python experiments/G8/reproduce.py` |
| G8.5 | Which competing mechanism explains recovery? | Matched state-history mechanism identification | IMPLEMENTED / TESTED / REAL_EXECUTED / PARTIAL | `python experiments/G8_5/reproduce.py` |
| G9 | Which pathway mediates the mechanism? | Intermediate-state intervention | PARTIAL / PARTIAL / REAL_EXECUTED / BLOCKED | `python experiments/G9/reproduce.py` |
| G10 | Are components redundant or synergistic? | Combination and interaction | PARTIAL / PARTIAL / REAL_EXECUTED / BLOCKED | `python experiments/G10/reproduce.py` |
| G11 | Can the system choose experiments autonomously? | Closed-loop experiment selection | PARTIAL / PARTIAL / REAL_EXECUTED / BLOCKED | `python experiments/G11/reproduce.py` |
| G12 | Where does the mechanism fail? | Applicability boundary | PARTIAL / PARTIAL / REAL_EXECUTED / BLOCKED | `python experiments/G12/reproduce.py` |
| G13 | Does it predict unseen tasks? | Pre-registered holdout prediction | PARTIAL / PARTIAL / REAL_EXECUTED / BLOCKED | `python experiments/G13/reproduce.py` |

The authoritative machine-readable status is [`configs/experiment_registry.yaml`](configs/experiment_registry.yaml); the narrative audit is [`docs/EXPERIMENT_OVERVIEW.md`](docs/EXPERIMENT_OVERVIEW.md). Status fields are intentionally separate and are not inferred from README prose.

## Repository structure

```text
experiments/        Independent G0–G13/G8.5 entrypoints and contracts
src/                Shared runners, budgets, isolation, scoring and registry
configs/            Frozen project and experiment configuration examples
docs/               Architecture, reproducibility and data-access boundaries
scripts/            Environment, reproduction, verification and figure CLIs
tests/              Existing scientific regression tests and public-boundary tests
third_party/        Pinned upstream code and its licence/audit metadata
```

## Installation

```bash
python -m pip install -e ".[dev]"
```

The lockfile records the tested development environment in [`requirements.lock`](requirements.lock). No API key is required for the offline smoke pipeline.

## Quick start

```bash
python scripts/check_environment.py
python scripts/reproduce.py --experiment G6
python scripts/verify_results.py --all
python -m pytest -q
```

The default reproduction mode is deterministic and offline. It writes explicitly labelled `ENGINEERING_SMOKE_ONLY` artifacts and sets `scientific_result=false`. It never calls a paid provider.

## Full offline pipeline

```bash
python scripts/reproduce.py --all --resume
python scripts/verify_results.py --all
python scripts/generate_figures.py --all
```

Real reproduction is intentionally fail-closed in the public entrypoint. It requires protected data, authorized credentials, an explicit budget and a controlled local environment. Historical real executions are evidence records, not a license to expose raw traces or private truth.

## Evaluation and verification

The independent evaluator separates numerical fit, structural recovery, out-of-distribution validation, mechanistic validity, execution status and provider failures. Existing regression tests cover isolation, evaluator adversarial cases, budget behavior, trace persistence, recovery, privacy and G6/G7/G8 contracts. Scientific gates remain blocked where external provider identity, billing, independent domain review or sufficient replication is unavailable.

## Data access and limitations

Raw real runs, private truth, hidden holdouts, provider payloads, API credentials and local archives are excluded from the public release. See [`docs/DATA_ACCESS.md`](docs/DATA_ACCESS.md) for the controlled-data workflow. The repository retains historical evidence locally without rewriting denominators or reclassifying failures.

## Citation and licence

See [`CITATION.cff`](CITATION.cff) and [`LICENSE`](LICENSE). The upstream NewtonBench material remains subject to its own licence and attribution requirements.
