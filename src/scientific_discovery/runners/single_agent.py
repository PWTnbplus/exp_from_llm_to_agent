"""Single adaptive agent with exactly one authorized experiment action."""

from __future__ import annotations

from typing import Any

from ..benchmark.base import ExperimentOracle, RunResult
from ..environment.budget import BudgetLedger, BudgetExceeded
from ..environment.isolation import assert_public_text
from ..evaluation.law_recovery import LawCandidate
from ..models.provider import LLMProvider
from ..utils.json_protocol import ProtocolError
from ..observability.trace import NullTraceRecorder, TraceRecorder
from ..experiment.policy import PolicyController
from .common import ensure_provider_call, observation_dict, record_provider_call, response_payload


AGENT_SYSTEM = """You are a single autonomous scientific agent. You may either submit one JSON action for the authorized run_experiment operation or submit a final_law JSON object. You may use current observations to choose the next action, but you may never access hidden laws, source code, validation data, or the operating system. Stay within the stated budget."""


def _tool_schema(schema: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"type": "function", "function": {"name": "run_experiment", "description": "Run exactly one legal scientific experiment.", "parameters": schema}}]


class SingleAgentRunner:
    name = "single_agent"

    def __init__(self, provider: LLMProvider, oracle: ExperimentOracle, budget: BudgetLedger, trace: TraceRecorder | NullTraceRecorder | None = None, controller: PolicyController | None = None):
        self.provider = provider
        self.oracle = oracle
        self.budget = budget
        self.trace = trace or NullTraceRecorder()
        self.controller = controller

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
                    self.trace.emit("PREDICTION", prediction=law, output=law, status="COMPLETED", metadata={"source": "model_output"})
                    status = "completed"
                    break
                if final_only:
                    raise ProtocolError("agent returned an experiment after the budget was exhausted")
                if payload.get("tool_call") and payload["tool_call"] != "run_experiment":
                    raise ProtocolError(f"unauthorized tool call: {payload['tool_call']}")
                action = payload.get("arguments") if payload.get("tool_call") else payload.get("action")
                if action is None:
                    raise ProtocolError("agent must return an action or final_law")
                call_event = self.trace.emit(
                    "TOOL_CALL",
                    input={"action": action, "remaining_budget": self.oracle.get_remaining_budget()},
                    tool_name="run_experiment",
                    tool_arguments=action,
                    status="RUNNING",
                    metadata={"authorized_tool": True},
                )
                if self.controller is not None:
                    self.controller.before_tool_call("run_experiment")
                if "hypothesis" in payload:
                    self.trace.emit(
                        "HYPOTHESIS_UPDATE",
                        parent_step_id=call_event["step_id"],
                        input={"observations": history},
                        output={"hypothesis": payload["hypothesis"]},
                        status="OBSERVED",
                        metadata={"source": "explicit_model_field", "inferred": False},
                    )
                try:
                    observation = self.oracle.run_experiment(action)
                except Exception as exc:
                    error_type = "budget" if type(exc).__name__ == "BudgetExceeded" else "tool"
                    self.trace.emit(
                        "TOOL_RESULT",
                        parent_step_id=call_event["step_id"],
                        tool_name="run_experiment",
                        tool_arguments=action,
                        status="FAILED",
                        error_message=str(exc),
                        metadata={"error_type": error_type, "exception": type(exc).__name__},
                    )
                    self.trace.emit(
                        "ERROR",
                        parent_step_id=call_event["step_id"],
                        status="FAILED",
                        error_message=str(exc),
                        metadata={"error_type": error_type, "exception": type(exc).__name__},
                    )
                    raise
                self.trace.emit(
                    "TOOL_RESULT",
                    parent_step_id=call_event["step_id"],
                    output={"experiment_index": observation.experiment_index, "result": observation.result},
                    tool_name="run_experiment",
                    tool_arguments=action,
                    tool_result=observation.result,
                    status="COMPLETED",
                    metadata={"measurement_count": observation.measurement_count},
                )
                observations.append(observation)
                assert_public_text(str(observation.result))
                history.append({"action": observation.action, "result": observation.result, "experiment_index": observation.experiment_index})
        except (ProtocolError, ValueError, RuntimeError, BudgetExceeded) as exc:
            metadata["error"] = str(exc)
            error_type = "budget" if type(exc).__name__ == "BudgetExceeded" else "runner"
            self.trace.emit("ERROR", status="FAILED", error_message=str(exc), metadata={"error_type": error_type, "exception": type(exc).__name__})
        finally:
            self.oracle.finalize()
            metadata["budget"] = self.budget.snapshot()
            if self.controller is not None:
                metadata["policy"] = self.controller.snapshot()
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
            run_id=getattr(self.trace, "run_id", None),
            trace_path=str(getattr(self.trace, "path", "") or "") or None,
        )
