# G2 — LLM plus bounded tools

G2 isolates the contribution of a fixed, non-adaptive tool contract while retaining the G1 task cohort and scoring boundary. It is not a different base model.

```bash
python experiments/G2/run.py
python experiments/G2/evaluate.py
python experiments/G2/reproduce.py --resume
```

The public wrapper is an offline engineering smoke only; protected real traces and independent scoring are not bundled.
