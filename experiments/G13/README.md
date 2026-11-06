# G13 — Prediction on unseen tasks

G13 evaluates a pre-specified mechanism prediction on unseen tasks. Holdout truth is private to the independent scorer and prediction quality is not inferred from training or historical recovery records.

```bash
python experiments/G13/run.py
python experiments/G13/evaluate.py
python experiments/G13/reproduce.py --resume
```

The public wrapper is a deterministic offline contract. Controlled holdout access is required for real reproduction.
