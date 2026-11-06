# G7 — Failure localization and local recovery

G7 diagnoses where a scientific reasoning trajectory fails using bounded V/L/U/Q conditions and shared checkpoint lineage. Independent Q verification is a separate measure from final answer correctness.

```bash
python experiments/G7/run.py
python experiments/G7/evaluate.py
python experiments/G7/reproduce.py --resume
```

The public wrapper emits only labelled offline engineering output; historical Q and checkpoint artifacts are not copied into the public smoke run.
