# Why the LLM-only arm is non-agentic

The guarantee is implemented in `src/scientific_discovery/runners/llm_only.py`:

1. The planning provider call is made with `tools=None`.
2. Its JSON plan is validated, canonicalized, and hashed by `freeze_plan`.
3. The batch loop calls only `oracle.run_experiment(action)` over the frozen list. It has no provider reference, no observation-dependent branch, and no re-planning path.
4. The final provider call happens only after the batch loop and receives the initial observations plus all batch observations at once.

The adapter's public action schema also carries the upstream apparatus bounds. The plan validator and oracle enforce those bounds before execution; the scheduler still only executes the already-frozen sequence.

Every provider request and response is copied into the result's `metadata.provider_trace` (with no API key). The trace is an audit record, not an additional information channel: the LLM-only runner still passes `tools=None` for both calls. `tests/test_llm_isolation.py` asserts this property.

In the G1-G5 control layer, G1 additionally passes through `PolicyProvider`.
Its executable policy denies every tool, retrieval, memory operation and
transport retry before dispatch. `TraceProvider` records the policy check and
each actual provider attempt. The default OpenAI-compatible provider retry
count is zero; a provider configured with a higher retry count is rejected at
construction time for a controlled run.

`tests/test_llm_isolation.py` checks that intermediate observations do not enter planning messages, changing simulated outputs cannot alter a frozen plan, and no tools are passed to either LLM-only call. The Agent test in `tests/test_agent_actions.py` separately checks that an adaptive runner can use feedback.
