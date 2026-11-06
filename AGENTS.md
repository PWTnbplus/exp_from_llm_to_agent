# AI Scientific Reasoning repository guidance

## Scientific safety

- Keep the 15 experiment definitions and their original protocols unchanged.
- Keep historical raw runs, private truth, model traces and audit lineage append-only.
- Never use an offline smoke artifact as scientific evidence.
- Separate implementation, test, real execution and reproducibility status.
- Do not start paid provider calls from CI or from the default reproduction commands.
- Keep G8.5 as an independent mechanism-identification experiment, not a G8 ablation.

## Public release boundary

Only source code, protocol definitions, schemas, synthetic examples and reproducibility instructions belong in a public release. Use the public-release allowlist; never add `api_key/`, `runs/`, private truth, raw provider traces, checkpoints or local archives.

## Verification

```bash
python scripts/check_environment.py
python scripts/reproduce.py --all --resume
python scripts/verify_results.py --all
python -m pytest -q
```
