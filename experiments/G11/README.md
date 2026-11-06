# G11 — Autonomous scientific experiment selection

G11 tests autonomous selection of scientific actions and closed-loop correction. The independent oracle, action trace and final score must stay separate; the current public package exposes only the contract.

```bash
python experiments/G11/run.py
python experiments/G11/evaluate.py
python experiments/G11/reproduce.py --resume
```

Protected data and historical traces are not copied into the offline smoke output.
