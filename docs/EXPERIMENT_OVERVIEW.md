# Experiment overview and status audit

This document is an engineering inventory, not a scientific release claim. `IMPLEMENTED`, `TESTED`, `REAL_EXECUTED` and `REPRODUCIBLE` are independent fields. A real archive does not imply public reproducibility; an offline test does not imply a real result.

| ID | Research task | IMPLEMENTED | TESTED | REAL_EXECUTED | REPRODUCIBLE | Main evidence / limitation |
|---|---|---|---|---|---|---|
| G0 | Protocol gate | IMPLEMENTED | TESTED | REAL_EXECUTED | PARTIAL | Gate evidence exists; no model arm |
| G1 | LLM-only baseline | IMPLEMENTED | TESTED | REAL_EXECUTED | PARTIAL | Archived Kimi traces; protected scoring |
| G2 | Tool contribution | IMPLEMENTED | TESTED | REAL_EXECUTED | PARTIAL | Fixed tool contract; protected scoring |
| G3 | Iteration contribution | IMPLEMENTED | TESTED | REAL_EXECUTED | PARTIAL | Fixed reflection workflow |
| G4 | Agentic workflow | IMPLEMENTED | TESTED | REAL_EXECUTED | PARTIAL | Main/append provenance must stay separate |
| G5 | Reverse derivation | IMPLEMENTED | TESTED | REAL_EXECUTED | PARTIAL | Private answer isolation required |
| G6 | Counterfactual sensitivity | IMPLEMENTED | TESTED | REAL_EXECUTED | PARTIAL | `science_pass=false`; independent review remains open |
| G7 | Failure localization | IMPLEMENTED | TESTED | REAL_EXECUTED | PARTIAL | Q coverage and trace-validity limits remain |
| G8 | Causal intervention | IMPLEMENTED | TESTED | REAL_EXECUTED | PARTIAL | External provider identity/billing gate remains |
| G8.5 | Competing mechanism identification | IMPLEMENTED | TESTED | REAL_EXECUTED | PARTIAL | Historical pair audit is not prospective confirmation |
| G9 | Pathway intervention | PARTIAL | PARTIAL | REAL_EXECUTED | BLOCKED | Public replay inputs are protected; single-block limits |
| G10 | Combination and synergy | PARTIAL | PARTIAL | REAL_EXECUTED | BLOCKED | More independent blocks needed |
| G11 | Autonomous experiment choice | PARTIAL | PARTIAL | REAL_EXECUTED | BLOCKED | Private oracle and traces are not public |
| G12 | Failure boundary | PARTIAL | PARTIAL | REAL_EXECUTED | BLOCKED | Descriptive result; robust inference not established |
| G13 | Unseen-task prediction | PARTIAL | PARTIAL | REAL_EXECUTED | BLOCKED | Holdout truth requires controlled access |

## Dependency order

`G0 → {G1,G2,G3} → G4 → G5 → G6 → G7 → G8 → G8.5 → G9 → G10 → G11 → G12 → G13`

The dependency graph is used by `python scripts/reproduce.py --all`; a missing or protected predecessor cannot be bypassed by copying a hand-written result file.

## Scientific caveats

- G6 and G7 remain scientifically blocked in the current audit ledger.
- G8.5 is retained as an independent experiment with its own mechanism-identification contract.
- Historical raw records are immutable and are not replaced by the public offline smoke artifacts.
- “REAL_EXECUTED” means a locally auditable execution record exists; it is not a claim that every external scientific release gate passed.
