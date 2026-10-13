# G6 handoff for the next agent

Date: 2026-10-14 (Asia/Hong_Kong)
Repository: `E:\\master_exp\\nature_prj1_cal\\from_llm_to_agent`
Branch: `autopilot/scientific-law-discovery`
Latest local commit: `252c6d7 complete g6 corrected subset audit`

## Read first

1. Read `AGENTS.md`.
2. Read `.agents/skills/scientific-law-recovery/SKILL.md` completely. It is the active V2 state protocol.
3. Run `python scripts/recovery_state.py bootstrap`, then read `docs/state/issues.json` and `docs/state/UNRESOLVED_REPORT.md`.
4. Read this file before changing any G6 artifact.

## What is complete

The G6 execution and audit chain is complete at the engineering/data-integrity level. No raw provider trace was overwritten and no synthetic scientific result was created.

Original persisted run:

- 576/576 canonical responses; 288 G3 and 288 G4.
- Official G6 validation: 96 cases, 24 paired families, PASS.
- `trace_audit.json`: `pass=true`, 576 canonical traces, failures empty.
- Full `g6_to_g7_handoff.jsonl`: 576 rows. This file must remain the original full handoff.
- Full plan SHA-256: `757bbe375ca2af474a0dcf3a009a889265d6ce2ba62ff488d37427cedb426c30`.
- Full canonical response SHA-256: `bddb0981ae795b6e1faf9b8b8151852afa03dcc820299963ca4c1126a3c81c0b`.

Corrected scientifically eligible subset:

- Source-only independent verifier accepted 23/24 families and excluded `TB-L1-010`.
- The exclusion is intentional: its public recessive mutation-selection formula is inconsistent (`q*=mu/s` versus the standard `q ~ sqrt(mu/s)`), and its G5 graph has unresolved validity.
- 552/552 persisted responses; 276 G3 and 276 G4; no API rerun and no response-outcome-based selection.
- Official G6 validation: 92 cases, 23 paired families, PASS.
- `trace_audit_verified23.json`: `pass=true`, 552 traces, failures empty.
- Corrected handoff: `g6_to_g7_handoff_verified23.jsonl`, 552 rows.
- Corrected plan SHA-256: `c60b14205f061fa2178b9d0a42074d9957a460bea2cf4e06b841acbe4b0bbde0`.
- Corrected response SHA-256: `4951c8a8d2bf6c88b91429582dd1c48323b49ccc675e2682002a4e08451dc34b`.
- Release report: `results/g6_counterfactual/formal-20261013T000000Z/reports/G6_VERIFIED23_REPORT.md`.
- Release manifest: `results/g6_counterfactual/formal-20261013T000000Z/verified23_manifest.json`.

## Main numerical result currently allowed

The corrected paired-family analysis is exploratory and pending independent review:

- Pooled G4 minus G3 accuracy: `-0.01811594202898551`.
- Family-bootstrap 95% CI: `[-0.07608695652173915, 0.043478260869565216]`.
- Exact matched McNemar two-sided p: `0.6353076420876663`.
- CF3 exploratory difference: `-0.2753623188405797`, exact p `0.0005461126565933228`.

Do not convert these into causal, superiority, or confirmatory claims.

## Current issue ledger status

- `ISSUE-000000000002` P1 `RESOLVED_UNVERIFIED`: real-provider accounting is locally auditable, but independent billing and immutable model snapshot evidence are absent.
- `ISSUE-000000000003` P1 `BLOCKED`: upstream provenance/GitHub delivery was blocked by external network/credential state.
- `ISSUE-000000000004` P1 `RESOLVED_UNVERIFIED`: paired-family analysis exists; independent statistical review is still required.
- `ISSUE-ff97c7c89112` P1 `RESOLVED_UNVERIFIED`: source-only G5 verifier exists; independent external mathematical/domain review is still required.
- `ISSUE-ad61f025976a` P1 `RESOLVED_UNVERIFIED`: official corrected-subset preflight has zero blockers, but it is only a manifest/path attestation. The provider supplied no immutable weight fingerprint.
- `ISSUE-000000000005` P2 `OPEN`: classical baseline is intentionally out of scope unless the study claims a classical comparison.
- `ISSUE-6b3a9e1d4f20` P2 `RESOLVED_UNVERIFIED`: raw traces contain retry segments; canonical derived views are used and raw history remains immutable. Runner resume protocol should be hardened before a new formal batch.

## Remaining gates / next actions

1. Obtain an independent mathematical/domain review of `scripts/verify_g5_g6_inputs.py` and the exclusion of `TB-L1-010`. Do not restore that family by padding, relabeling, or synthesis.
2. Obtain an independent review of the preregistered paired-family construction, oracle provenance, bootstrap, and McNemar implementation.
3. Obtain provider-verifiable immutable model identity/weights and billing evidence. `provider_model_metadata.json` only proves HTTP 200 model identity for `glm-5`; it is not an immutable weight snapshot.
4. If external network and credentials are restored and push is authorized, verify upstream provenance, commit, push the feature branch, and verify the remote SHA. Never force-push and never claim success without verification.
5. Keep `scientific_release_allowed=false` until the required independent gates pass.

## Commands already verified

From the repository root:

```powershell
python -m pytest -q                         # 99 passed
python -m unittest discover -s <G6_SKILL>\\tests -p test_g6.py  # 13 passed
python scripts/verify_g5_g6_inputs.py --g6-out results/g6_counterfactual/formal-20261013T000000Z --out results/g6_counterfactual/formal-20261013T000000Z/g5_independent_verification.json
python scripts/review_g6_release.py --out results/g6_counterfactual/formal-20261013T000000Z --report results/g6_counterfactual/formal-20261013T000000Z/independent_release_review.json
python scripts/recovery_state.py status
```

The official skill scripts are in the extracted G6 skill directory under the local temp directory; locate the directory rather than assuming a new copy. `g6_offline.py doctor` and `selfcheck` are demo/self-checks and must not be cited as the real scientific result.

## Important operational warnings

- The official score command writes the fixed filename `g6_to_g7_handoff.jsonl`. If scoring the 23-family subset, use the verified subset inputs and then restore the original full score/handoff before handing off.
- Do not rerun the paid provider experiment merely to reproduce a completed artifact.
- Do not use the private oracle or `answer_key` in the source-only mathematical eligibility verifier.
- Do not modify raw G5/G6 results. Derived audit views and reports may be regenerated only with matching hashes and explicit audit evidence.
- `results/` is git-ignored; the local result directory is part of the workspace handoff even though the source/audit code and ledger are committed.
