# G8 — Causal intervention on a candidate correction mechanism

G8 compares frozen workflow arms including real mechanism, sham, off and extra-thinking conditions. Execution success, answer correctness, feedback response and causal contrasts are separate metrics.

```bash
python experiments/G8/run.py
python experiments/G8/evaluate.py
python experiments/G8/reproduce.py --resume
```

The public wrapper is an offline smoke contract. It never calls a paid provider by default.
