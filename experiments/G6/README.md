# G6 — Counterfactual premise sensitivity

G6 changes a frozen premise and measures whether the conclusion changes appropriately. Model answers, tool traces, mathematical certificates and independent verification are separate outputs; the historical gate remains scientifically blocked.

```bash
python experiments/G6/run.py
python experiments/G6/evaluate.py
python experiments/G6/reproduce.py --resume
```

The public wrapper is an offline smoke contract. Real reproduction requires protected truth inputs, provider authorization and the existing legacy runner.
