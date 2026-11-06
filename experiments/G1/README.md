# G1 — LLM-only open-loop baseline

G1 measures the single-LLM baseline without tools or adaptive feedback. It is the reference condition for the tool, iteration and Agent workflow experiments.

```bash
python experiments/G1/run.py
python experiments/G1/evaluate.py
python experiments/G1/reproduce.py --resume
```

The public wrapper executes only an offline smoke artifact. Historical provider traces and private scoring remain local and are never silently replaced by the smoke result.
