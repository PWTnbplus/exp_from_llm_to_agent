# G1-G5 experiment-group execution contract

The groups isolate model capability, fixed computation, reflection compute and
adaptive Agent workflow. Prompt text describes a group but never grants its
permissions; `policy.py` enforces them at the provider and tool boundaries.

| Group | Model calls | Tools | Planning/feedback | Memory | Retrieval | Transport retries |
|---|---:|---|---|---|---|---:|
| G1 | 2 for NewtonBench frozen-plan/final inference; 1 for theory | none | frozen / one-shot | no | no | 0 |
| G2 | 2 | `calculate_expression`, four compute steps | fixed calculator assistance | no | no | 0 |
| G3 | 2 | none | fixed two-pass reflection | no | no | 0 |
| G4 | 8 | authorized experiment/calculator tools | observation-conditioned adaptive | no | no | 0 |
| G5 | 10 | same tools, ten tool calls and 32 memory items | adaptive | run-local only | no | 0 |

For NewtonBench, G1 may execute its complete pre-frozen simulator action list;
those simulator actions are not model tool calls. The plan hash and action
sequence are recorded. Only G4/G5 can choose a new experiment after observing
the previous result.

An unauthorized tool, retrieval request, memory access, computation, model
call, experiment, or retry emits `POLICY_CHECK` and `ERROR` Trace events and
fails the run. Budget snapshots are emitted regardless of success. Provider
attempt events distinguish logical model calls from actual transport attempts.

Ground Truth is opened only after model submission by the evaluator. It is not
part of model messages, ordinary run results, or Trace; evaluator mismatch
diagnostics omit expected values.
