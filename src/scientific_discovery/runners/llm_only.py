"""Strict three-phase non-adaptive baseline.

The important invariant is architectural: after the planning provider call,
the plan is frozen and batch execution has no reference to the provider.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from ..benchmark.base import ExperimentOracle, RunResult
from ..environment.budget import BudgetLedger
from ..environment.isolation import assert_public_text
from ..evaluation.law_recovery import LawCandidate
from ..models.provider import LLMProvider
from ..utils.json_protocol import ProtocolError
from ..experiment.scheduler import execute_frozen_plan
from ..observability.trace import NullTraceRecorder, TraceRecorder
from ..experiment.policy import PolicyController
from .common import ensure_provider_call, freeze_plan, observation_dict, record_provider_call, response_payload, validate_plan_shape


PLAN_SYSTEM = """You are the non-adaptive planning phase of a scientific law discovery study. Return JSON only with one key, experiments. Choose the complete list of legal experiments before any new result is observed. Do not call tools, re-plan, or include a hidden law."""
FINAL_SYSTEM = """You are the final inference phase of a scientific law discovery study. Return JSON only as a final law object with hypothesis, equation, variables, parameters, evidence, predictions, limitations, and code. Use only the supplied observations. Do not request another experiment."""


class LLMOnlyRunner:
    name = "llm_only"

    def __init__(self, provider: LLMProvider, oracle: ExperimentOracle, budget: BudgetLedger, trace: TraceRecorder | NullTraceRecorder | None = None, controller: PolicyController | None = None):
        self.provider = provider
        self.oracle = oracle
        self.budget = budget
        self.trace = trace or NullTraceRecorder()
        self.controller = controller

    def _planning_messages(self, initial_observations: list[dict[str, Any]]) -> list[dict[str, str]]:
        public = self.oracle.get_public_task_description()
        assert_public_text(public)
        schema = self.oracle.get_action_schema()
        assert_public_text(str(schema))
        assert_public_text(str(initial_observations))
        return [
            {"role": "system", "content": PLAN_SYSTEM},
            {"role": "user", "content": (
                f"Scientific task:\n{public}\n\n"
                f"Action schema:\n{schema}\n\n"
                f"Initial observations:\n{initial_observations}\n\n"
                f"Available experiment budget:\n{self.oracle.get_remaining_budget()}\n"
                "Return the complete frozen plan now."
            )},
        ]

    def run(self, task_id: str) -> RunResult:
        plan: list[dict[str, Any]] = []
        plan_hash: str | None = None
        observations = []
        initial_observations: list[dict[str, Any]] = []
        metadata: dict[str, Any] = {"protocol": "three_phase_open_loop", "intermediate_observations_sent_to_model": False}
        try:
            initial_observations = [observation_dict(v) for v in self.oracle.get_initial_observations()]
            ensure_provider_call(self.budget)
            planning = self.provider.complete(self._planning_messages(initial_observations), tools=None)
            record_provider_call(self.provider, planning, self.budget)
            payload = response_payload(planning)
            plan = validate_plan_shape(payload.get("experiments"), self.oracle.get_action_schema(), self.budget.limits.max_experiments)
            plan, plan_hash = freeze_plan(plan)
            metadata["plan_hash"] = plan_hash

            # This scheduler intentionally contains no provider call and no
            # observation-dependent branch.
            observations = execute_frozen_plan(self.oracle, plan)

            final_messages = [
                {"role": "system", "content": FINAL_SYSTEM},
                {"role": "user", "content": (
                    f"Initial observations: {initial_observations}\n"
                    f"Frozen plan: {plan}\n"
                    f"All batch observations: {[observation_dict(v) for v in observations]}\n"
                    "Submit the final law JSON now."
                )},
            ]
            assert_public_text(str(initial_observations))
            assert_public_text(str([observation_dict(v) for v in observations]))
            ensure_provider_call(self.budget)
            final = self.provider.complete(final_messages, tools=None)
            record_provider_call(self.provider, final, self.budget)
            law = LawCandidate.from_payload(final.content, task_id).to_dict()
            self.trace.emit("PREDICTION", prediction=law, output=law, status="COMPLETED", metadata={"source": "model_output"})
            status = "completed"
        except (ProtocolError, ValueError, RuntimeError) as exc:
            law = {"error": str(exc)}
            status = "failed"
            metadata["error"] = str(exc)
            self.trace.emit("ERROR", status="FAILED", error_message=str(exc), metadata={"error_type": "runner", "exception": type(exc).__name__})
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
            plan=plan,
            plan_hash=plan_hash,
            metadata=metadata,
            run_id=getattr(self.trace, "run_id", None),
            trace_path=str(getattr(self.trace, "path", "") or "") or None,
        )
