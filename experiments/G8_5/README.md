# G8.5 — Independent mechanism identification

G8.5 is an independent experiment, not an ordinary G8 ablation. It distinguishes competing mechanisms with matched state-history pairs, information-equivalent controls and independent confirmation. Historical paired audits are not silently relabelled as prospective confirmation.

```bash
python experiments/G8_5/run.py
python experiments/G8_5/evaluate.py
python experiments/G8_5/reproduce.py --resume
```

The public wrapper produces only offline engineering output; protected histories and private validation remain local.
