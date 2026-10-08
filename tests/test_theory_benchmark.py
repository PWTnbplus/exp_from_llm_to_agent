import json
import json
from collections import Counter
from pathlib import Path

from scientific_discovery.models.provider import MockLLMProvider
from scientific_discovery.theory_benchmark.analysis import analyze
from scientific_discovery.theory_benchmark.runner import run_task
from scientific_discovery.theory_benchmark.schema import LEGACY_DATA_DIR, MIXED_DATA_DIR, load_benchmark
from scientific_discovery.theory_benchmark.verification import verify_candidate
from scientific_discovery.theory_benchmark.contamination import contamination_manifest, generate_private_dynamic_cases
from scientific_discovery.observability.trace import read_trace


def test_theory_dataset_counts_and_answer_separation():
    public, answers, manifest = load_benchmark()
    assert len(public) == 100
    assert len(answers) == 100
    assert manifest["version"] == "theory-benchmark-v1"
    assert manifest["counts"]["by_level"] == {"1": 34, "2": 33, "3": 33}
    assert manifest["counts"]["by_domain"] == {"Theoretical Chemistry": 50, "Theoretical Biology": 50}
    assert Counter((row["domain"], row["difficulty_level"]) for row in public) == {
        (domain, level): sum(row["domain"] == domain and row["difficulty_level"] == level for row in public)
        for domain in ("Theoretical Chemistry", "Theoretical Biology")
        for level in (1, 2, 3)
    }
    public_text = json.dumps(public, ensure_ascii=False).lower()
    assert "ground_truth" not in public_text
    assert "verification_code" not in public_text


def test_legacy_v1_dataset_remains_loadable():
    public, answers, manifest = load_benchmark(LEGACY_DATA_DIR)
    assert len(public) == 100
    assert len(answers) == 100
    assert manifest["version"] == "theory-benchmark-v1"


def test_mixed_v2_dataset_remains_loadable():
    public, answers, manifest = load_benchmark(MIXED_DATA_DIR)
    assert len(public) == 300
    assert len(answers) == 300
    assert manifest["version"] == "theory-benchmark-v2"


def test_all_answer_keys_self_verify():
    _, answers, _ = load_benchmark()
    for task_id, answer in answers.items():
        result = verify_candidate(task_id, {"final_answer": answer["ground_truth"]["answer"]})
        assert result["status"] == "PASS", (task_id, result)


def test_expression_equivalence_and_model_error():
    result = verify_candidate("TC-L1-001", {"final_answer": {"formula": "A0*exp(-k*t)", "half_life": 0.6931471805599453/.4, "depends_on_A0": False}})
    assert result["status"] == "PASS"
    bad = verify_candidate("TC-L1-001", {"final_answer": {"formula": "A0*exp(k*t)", "half_life": 0.0, "depends_on_A0": True}})
    assert bad["status"] == "MODEL_ERROR"


def test_llm_only_and_agent_protocol_surface(tmp_path: Path):
    _, answers, _ = load_benchmark()
    expected = {"task_id": "TC-L1-001", "final_answer": answers["TC-L1-001"]["ground_truth"]["answer"], "derivation": "test"}
    llm_provider = MockLLMProvider([expected])
    llm_result = run_task("TC-L1-001", llm_provider, "llm_only", output_dir=tmp_path)
    assert llm_result["status"] == "COMPLETED"
    assert llm_result["validation"]["status"] == "PASS"
    assert llm_provider.calls[0]["tools"] is None
    trace_events = read_trace(tmp_path / llm_result["trace_path"], run_id=llm_result["run_id"])
    assert [event["event_type"] for event in trace_events][0] == "RUN_START"
    assert "MODEL_INPUT" in [event["event_type"] for event in trace_events]
    assert "PREDICTION" in [event["event_type"] for event in trace_events]
    assert "EVALUATION" in [event["event_type"] for event in trace_events]
    agent_provider = MockLLMProvider([expected])
    agent_result = run_task("TC-L1-001", agent_provider, "agent", output_dir=tmp_path)
    assert agent_result["status"] == "COMPLETED"
    assert agent_provider.calls[0]["tools"]


def test_analysis_keeps_failures_in_denominator(tmp_path: Path):
    _, answers, _ = load_benchmark()
    good = {"task_id": "TC-L1-001", "runner": "llm_only", "validation": {"status": "PASS", "answer_correct": True}, "metadata": {"provider_calls": 1}}
    bad = {"task_id": "TC-L1-002", "runner": "agent", "validation": {"status": "MODEL_ERROR", "answer_correct": False}, "metadata": {"provider_calls": 1}}
    (tmp_path / "good.json").write_text(json.dumps(good), encoding="utf-8")
    (tmp_path / "bad.json").write_text(json.dumps(bad), encoding="utf-8")
    summary = analyze(tmp_path, tmp_path / "figures")
    assert summary["n_results"] == 2
    assert summary["by_mode"]["agent"]["n"] == 1
    assert summary["by_mode"]["agent"]["accuracy"] == 0.0
    assert summary["failure_frequency"]["MODEL_ERROR"] == 1


def test_contamination_controls_are_audit_only_and_private_answers_stay_separate():
    public, _, manifest = load_benchmark()
    report = contamination_manifest(public, version=manifest["version"])
    assert report["task_count"] == 100
    assert report["strata_counts"] == {"classical": 40, "structure_transform": 30, "private_dynamic": 30}
    cases = generate_private_dynamic_cases(public, seed="unit-test-private-seed")
    assert len(cases) == 30
    assert all("ground_truth" not in json.dumps(case.public, ensure_ascii=False) for case in cases)
    assert all(case.answer["ground_truth"]["answer"]["y"] == case.public["given_parameters"]["a"] * case.public["given_parameters"]["x"] + case.public["given_parameters"]["b"] for case in cases)


def test_all_five_groups_are_distinct_and_do_not_serialize_ground_truth(tmp_path: Path):
    _, answers, _ = load_benchmark()
    expected = {"task_id": "TC-L1-001", "final_answer": answers["TC-L1-001"]["ground_truth"]["answer"]}
    for group in ("G1", "G2", "G3", "G4", "G5"):
        responses = [expected, expected] if group == "G3" else [expected]
        result = run_task("TC-L1-001", MockLLMProvider(responses), group, output_dir=tmp_path)
        assert result["status"] == "COMPLETED"
        assert result["group"] == group
        assert "ground_truth" not in json.dumps(result, ensure_ascii=False)
        events = read_trace(tmp_path / result["trace_path"], run_id=result["run_id"])
        model_inputs = [event for event in events if event["event_type"] == "MODEL_INPUT"]
        assert all("ground_truth" not in json.dumps(event["input"], ensure_ascii=False) for event in model_inputs)
        assert any(event["event_type"] == "POLICY_CHECK" for event in events)
