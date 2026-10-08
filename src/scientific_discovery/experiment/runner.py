"""One-task orchestration for discovery followed by blind validation."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from ..benchmark.base import TaskSpec
from ..benchmark.newtonbench_adapter import NewtonBenchOracle
from ..environment.budget import BudgetLedger, BudgetLimits
from ..evaluation.validation import ValidationEnvironment
from ..models.provider import LLMProvider
from ..runners.llm_only import LLMOnlyRunner
from ..runners.single_agent import SingleAgentRunner
from .recorder import ResultRecorder
from ..observability.trace import NullTraceRecorder, TraceProvider, TraceRecorder
from .policy import PolicyController, PolicyProvider, get_group_policy
import uuid


def run_one(
    task: TaskSpec,
    repo_root: Path,
    provider: LLMProvider,
    runner_name: str,
    limits: BudgetLimits,
    output_dir: Path | None = None,
    replicate_index: int | None = None,
    design: str | None = None,
    manifest_sha256: str | None = None,
) -> tuple[object, dict]:
    run_task = replace(task, seed=task.seed + int(replicate_index)) if replicate_index is not None else task
    policy = get_group_policy(runner_name)
    bounded_limits = BudgetLimits(
        max_experiments=min(limits.max_experiments, policy.max_experiments),
        max_measurements=limits.max_measurements,
        max_api_calls=min(limits.max_api_calls, policy.max_api_calls),
        max_input_tokens=min(limits.max_input_tokens, policy.max_input_tokens),
        max_output_tokens=min(limits.max_output_tokens, policy.max_output_tokens),
        max_cost_usd=limits.max_cost_usd,
        max_runtime_seconds=limits.max_runtime_seconds,
    )
    budget = BudgetLedger(bounded_limits)
    oracle = NewtonBenchOracle(run_task, repo_root, budget)
    run_id = uuid.uuid4().hex
    trace_path: Path | None = None
    if output_dir is not None:
        trace_path = Path(output_dir) / "logs" / f"{run_id}.jsonl"
        trace = TraceRecorder(
            trace_path,
            run_id=run_id,
            task_id=run_task.task_id,
            system_type=runner_name,
            model_name=getattr(provider, "model_name", "unknown"),
            model_version=str(getattr(provider, "model_name", "unknown")),
        )
    else:
        trace = NullTraceRecorder(run_id)
    trace.emit(
        "RUN_START",
        input={"task_id": run_task.task_id, "domain": run_task.domain, "difficulty": run_task.law_complexity},
        status="RUNNING",
        metadata={"runner": runner_name, "group": policy.group, "group_policy": policy.as_dict(), "budget_limits": bounded_limits.__dict__, "replicate_index": replicate_index, "design": design, "manifest_sha256": manifest_sha256},
    )
    controller = PolicyController(policy, trace=trace)
    guarded_provider = PolicyProvider(provider, controller)
    traced_provider = TraceProvider(guarded_provider, trace)
    runner = LLMOnlyRunner(traced_provider, oracle, budget, trace, controller) if policy.group == "G1" else SingleAgentRunner(traced_provider, oracle, budget, trace, controller)
    try:
        result = runner.run(run_task.task_id)
        validation = ValidationEnvironment(repo_root).validate(run_task, result.law)
        trace.emit(
            "EVALUATION",
            input={"prediction": result.law},
            output=validation,
            prediction=result.law,
            status="COMPLETED" if validation.get("validated_success") else "INCORRECT",
            metadata={"ground_truth_phase": True, "ground_truth_exposed_to_model": False, "evaluator": "independent", "error_type": "final_answer" if not validation.get("validated_success") else None},
        )
        result.run_id = run_id
        result.trace_path = str(Path("logs") / f"{run_id}.jsonl") if trace_path else None
        result.metadata["trace_path"] = result.trace_path
        result.metadata["task"] = {"task_id": run_task.task_id, "difficulty": run_task.law_complexity, "domain": run_task.domain, "source": run_task.source, "seed": run_task.seed}
        if replicate_index is not None:
            result.metadata["replicate_index"] = int(replicate_index)
        if design is not None:
            result.metadata["design"] = design
        result.metadata["manifest_sha256"] = manifest_sha256
        result.metadata["policy"] = controller.snapshot()
        trace.emit("RUN_END", output={"status": result.status, "validation": validation}, status=result.status.upper(), metadata={"budget": budget.snapshot()})
    except Exception as exc:
        trace.emit("ERROR", status="FAILED", error_message=str(exc), metadata={"error_type": "orchestrator", "exception": type(exc).__name__})
        trace.emit("RUN_END", status="FAILED", error_message=str(exc), metadata={"error_type": "orchestrator"})
        raise
    finally:
        trace.close()
    if output_dir is not None:
        ResultRecorder(output_dir).write(result, validation, replicate_index=replicate_index)
    return result, validation
