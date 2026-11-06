# G5 — Known-answer reverse derivation

G5 evaluates reverse derivation and proof/verification behavior when the target answer is known to the independent scorer. Private answers remain outside model-visible prompts.

```bash
python experiments/G5/run.py
python experiments/G5/evaluate.py
python experiments/G5/reproduce.py --resume
```

Only deterministic offline smoke output is public. The historical provider-backed audit remains a separate evidence source.
