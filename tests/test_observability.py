import json
from pathlib import Path

from scientific_discovery.benchmark.base import TaskSpec
from scientific_discovery.experiment.runner import run_one
from scientific_discovery.environment.budget import BudgetLimits
from scientific_discovery.models.provider import MockLLMProvider
from scientific_discovery.observability.trace import TraceRecorder, read_trace


ROOT = Path(__file__).parents[1]
NEWTON = ROOT / "third_party" / "NewtonBench"
TASK = TaskSpec(
    "newtonbench:m0_gravity:easy:v0:vanilla_equation",
    "NewtonBench", "m0_gravity", "gravitation", "easy", "vanilla_equation", "v0",
)
ACTION = {"mass1": 1.0, "mass2": 2.0, "distance": 1.0}
LAW = {
    "hypothesis": "direct law", "equation": "F=C*m1*m2/r^1.5",
    "variables": ["mass1", "mass2", "distance"], "parameters": {},
    "evidence": [], "predictions": [], "limitations": [],
    "code": "def discovered_law(mass1, mass2, distance):\n    return 6.674e-5 * mass1 * mass2 / (distance ** 1.5)",
}


def test_trace_is_schema_complete_durable_and_redacts_secret(tmp_path):
    path = tmp_path / "trace.jsonl"
    recorder = TraceRecorder(path, run_id="run-1", task_id="task-1", system_type="agent", model_name="m")
    recorder.emit("MODEL_INPUT", input={"authorization": "Bearer secret", "ground_truth": {"answer": 3}, "messages": [{"content": "visible"}]})
    recorder.emit("RUN_END", status="COMPLETED")
    recorder.close()
    events = read_trace(path)
    assert len(events) == 2
    assert events[0]["input"]["authorization"] == "[REDACTED]"
    assert events[0]["input"]["ground_truth"] == "[REDACTED]"
    assert events[0]["input"]["messages"][0]["content"] == "visible"
    required = {"run_id", "task_id", "system_type", "model_name", "step_id", "parent_step_id", "event_type", "timestamp", "input", "output", "prediction", "tool_name", "tool_arguments", "tool_result", "token_usage", "latency_ms", "cost", "status", "error_message", "metadata"}
    assert required <= set(events[0])


def test_real_runner_events_are_saved_and_repeated_runs_are_distinct(tmp_path):
    llm, _ = run_one(
        TASK, NEWTON, MockLLMProvider([{"experiments": [ACTION]}, LAW]),
        "llm_only", BudgetLimits(max_experiments=1, max_api_calls=4), tmp_path,
    )
    agent, _ = run_one(
        TASK, NEWTON, MockLLMProvider([{"action": ACTION, "hypothesis": "explicit H1"}, {"final_law": LAW}]),
        "single_agent", BudgetLimits(max_experiments=1, max_api_calls=4), tmp_path,
    )
    llm_events = read_trace(tmp_path / llm.trace_path, run_id=llm.run_id)
    events = read_trace(tmp_path / agent.trace_path, run_id=agent.run_id)
    assert {event["system_type"] for event in llm_events + events} == {"llm_only", "single_agent"}
    assert len({event["run_id"] for event in llm_events + events}) == 2
    types = [event["event_type"] for event in events]
    assert types[0] == "RUN_START"
    assert "MODEL_INPUT" in types and "MODEL_OUTPUT" in types
    assert "PROVIDER_ATTEMPT" in types
    assert "TOOL_CALL" in types and "TOOL_RESULT" in types
    assert "HYPOTHESIS_UPDATE" in types and "PREDICTION" in types and "EVALUATION" in types
    model_inputs = [event for event in events if event["event_type"] == "MODEL_INPUT"]
    assert all("ground_truth" not in json.dumps(event["input"], ensure_ascii=False) for event in model_inputs)
    assert (tmp_path / agent.trace_path).exists()


def test_failed_model_run_keeps_incremental_history(tmp_path):
    result, _ = run_one(TASK, NEWTON, MockLLMProvider([]), "llm_only", BudgetLimits(max_experiments=1, max_api_calls=4), tmp_path)
    assert result.status == "failed"
    events = read_trace(tmp_path / result.trace_path, run_id=result.run_id)
    assert [event["event_type"] for event in events][:2] == ["RUN_START", "MODEL_INPUT"]
    assert any(event["event_type"] == "ERROR" and event["metadata"].get("error_type") == "model" for event in events)
    assert events[-1]["event_type"] == "RUN_END"
