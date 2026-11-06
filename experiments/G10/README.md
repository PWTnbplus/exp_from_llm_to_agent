# G10 — Mechanism combination, redundancy and synergy

G10 tests interactions among mechanism components. It must preserve the original combination matrix and distinguish interaction estimates from execution success.

```bash
python experiments/G10/run.py
python experiments/G10/evaluate.py
python experiments/G10/reproduce.py --resume
```

Real replay is marked blocked in the registry because the protected archived inputs are not part of the public package.
