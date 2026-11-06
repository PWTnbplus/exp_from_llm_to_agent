# G0 — Protocol and scientific-reasoning baseline gate

G0 verifies the protocol, public/private boundary, budget ledger, pinned simulator and evaluator contract. It is a gate, not a model arm and not a model accuracy result.

The historical implementation and audits are referenced in `configs/experiment_registry.yaml`. The public entrypoint runs only the deterministic offline smoke contract; real execution requires the protected local data and an explicitly authorized provider environment.

```bash
python experiments/G0/run.py
python experiments/G0/evaluate.py
python experiments/G0/reproduce.py --resume
```

Outputs are JSON artifacts under `results/engineering_smoke/G0/` and are labelled synthetic. They must not enter scientific statistics.
