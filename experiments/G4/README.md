# G4 — Adaptive Agent workflow

G4 tests whether bounded adaptive tool and feedback selection adds value beyond fixed tools and iteration. Main, append and repair queues are provenance-separated.

```bash
python experiments/G4/run.py
python experiments/G4/evaluate.py
python experiments/G4/reproduce.py --resume
```

This public entrypoint is an offline smoke contract. Historical and private run evidence is not overwritten or bundled into the smoke result.
