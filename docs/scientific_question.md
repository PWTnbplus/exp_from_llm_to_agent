# Scientific question

Primary question: under the same model, task, initial information, measurement precision, and experiment budget, does allowing feedback-controlled experiment selection improve validated law discovery over a frozen open-loop plan?

The comparison is deliberately narrower than “agents are better than LLMs”. The LLM-only arm is a non-adaptive baseline; the Agent arm differs only by receiving oracle feedback before selecting later actions. Any conclusion is therefore conditional on this environment and protocol.

Primary endpoint: **Validated Law Discovery Rate (VLDR)**, the fraction of evaluated task runs whose submitted law passes the pre-registered independent prediction threshold. Structural equivalence is supplementary; numerical prediction on held-out conditions is required.
