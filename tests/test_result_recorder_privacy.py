from pathlib import Path

from src.scientific_discovery.benchmark.base import RunResult
from src.scientific_discovery.experiment.recorder import ResultRecorder


def test_result_recorder_removes_hidden_evaluator_payloads(tmp_path: Path) -> None:
    result = RunResult(runner="llm_only", task_id="task", status="COMPLETED", law={})
    path = ResultRecorder(tmp_path).write(
        result,
        {"validated_success": True, "ground_truth": {"source": "secret"}, "nested": {"answer_key": "secret"}},
    )
    text = path.read_text(encoding="utf-8")
    assert "ground_truth" not in text
    assert "answer_key" not in text
    assert "secret" not in text
