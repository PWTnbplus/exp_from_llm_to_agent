"""Single adaptive agent with exactly one authorized experiment action."""

from __future__ import annotations

from typing import Any

from ..benchmark.base import ExperimentOracle, RunResult
from ..environment.budget import BudgetLedger, BudgetExceeded
from ..environment.isolation import assert_public_text
from ..evaluation.law_recovery import LawCandidate
from ..models.provider import LLMProvider
from ..utils.json_protocol import ProtocolError
from .common import ensure_provider_call, observation_dict, record_provider_call, response_payload


AGENT_SYSTEM = """You are a single autonomous scientific agent. You may either submit one JSON action for the authorized run_experiment operation or submit a final_law JSON object. You may use current observations to choose the next action, but you may never access hidden laws, source code, validation data, or the operating system. Stay within the stated budget."""


def _tool_schema(schema: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"type": "function", "function": {"name": "run_experiment", "description": "Run exactly one legal scientific experiment.", "parameters": schema}}]


class SingleAgentRunner:
    name = "single_agent"

    def __init__(self, provider: LLMProvider, oracle: ExperimentOracle, budget: BudgetLedger):
        self.provider = provider
        self.oracle = oracle
        self.budget = budget

    def run(self, task_id: str) -> RunResult:
        public = self.oracle.get_public_task_description()
        assert_public_text(public)
        schema = self.oracle.get_action_schema()
        history: list[dict[str, Any]] = []
        observations = []
        metadata: dict[str, Any] = {"protocol": "closed_loop_single_agent", "authorized_tool": "run_experiment"}
        law: dict[str, Any] = {"error": "agent did not submit a final law"}
        status = "failed"
        try:
            while True:
                experiments_remaining = self.oracle.get_remaining_budget()["experiments"]
                final_only = experiments_remaining <= 0
                messages = [
                    {"role": "system", "content": AGENT_SYSTEM},
                    {"role": "user", "content": (
                        f"Scientific task:\n{public}\n\nAction schema:\n{schema}\n\n"
                        f"Current observations:\n{history}\n\n"
                        f"Remaining budget:\n{self.oracle.get_remaining_budget()}\n"
                        + ("The experiment budget is exhausted. Return final_law only."
                           if final_only else
                           "Return one JSON object: {action: {...}, hypothesis: ...} or {final_law: {...}}.")
                    )},
                ]
                assert_public_text(str(history))
                ensure_provider_call(self.budget)
                response = self.provider.complete(messages, tools=None if final_only else _tool_schema(schema))
                record_provider_call(self.provider, response, self.budget)
                payload = response_payload(response)
                if "final_law" in payload:
                    law = LawCandidate.from_payload(payload, task_id).to_dict()
                    status = "completed"
                    break
                if final_only:
                    raise ProtocolError("agent returned an experiment after the budget was exhausted")
                if payload.get("tool_call") and payload["tool_call"] != "run_experiment":
                    raise ProtocolError(f"unauthorized tool call: {payload['tool_call']}")
                action = payload.get("arguments") if payload.get("tool_call") else payload.get("action")
                if action is None:
                    raise ProtocolError("agent must return an action or final_law")
                observation = self.oracle.run_experiment(action)
                observations.append(observation)
                assert_public_text(str(observation.result))
                history.append({"action": observation.action, "result": observation.result, "experiment_index": observation.experiment_index})
        except (ProtocolError, ValueError, RuntimeError, BudgetExceeded) as exc:
            metadata["error"] = str(exc)
        finally:
            self.oracle.finalize()
            metadata["budget"] = self.budget.snapshot()
            metadata["provider_trace"] = self.provider.audit_trace()
        return RunResult(
            runner=self.name,
            task_id=task_id,
            status=status,
            law=law,
            observations=observations,
            plan=[observation.action for observation in observations],
            plan_hash=None,
            metadata=metadata,
        )
