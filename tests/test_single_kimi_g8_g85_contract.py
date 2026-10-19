import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
G8 = ROOT / "runs/ctflow_single_model/20261020T-kimi-g8-v1"
G85 = ROOT / "runs/ctflow_single_model/20261020T-kimi-g8-5-v1"


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_g8_formal_plan_is_single_kimi_and_public_only():
    rows = read_jsonl(G8 / "plans/g8_formal_plan.jsonl")
    assert len(rows) == 180
    assert {row["model_id"] for row in rows} == {"kimi-k2.5"}
    assert all("expected_decision" not in json.dumps(row["public_messages"], ensure_ascii=False) for row in rows)
    assert all(row["is_mock"] is False for row in rows)


def test_g8_repair_is_append_only():
    rows = read_jsonl(G8 / "plans/g8_formal_adapter_repair1_plan.jsonl")
    assert len(rows) == 24
    assert all(row["repair_of_run_id"] in row["run_id"] for row in rows)
    assert all(row["model_id"] == "kimi-k2.5" for row in rows)
    primary = G8 / "formal/raw" / rows[0]["repair_of_run_id"] / "result.json"
    assert primary.exists()
    assert json.loads(primary.read_text(encoding="utf-8"))["execution_status"] == "TECHNICAL_FAILURE"


def test_g85_preflight_blocks_science_without_real_histories():
    preflight = json.loads((G85 / "G85_PREFLIGHT.json").read_text(encoding="utf-8"))
    assert preflight["status"] == "BLOCKED_MISSING_REAL_UPSTREAM"
    assert preflight["qualifying_real_history_pairs"] == 0
    assert preflight["g7_clean_recovered_pair_markers"] == 0
    assert preflight["only_model"] is True


def test_g85_state_only_controls_are_byte_equivalent_and_truth_is_separate():
    rows = read_jsonl(G85 / "plans/g85_engineering_pilot_plan.jsonl")
    assert len(rows) == 16
    assert {row["model_id"] for row in rows} == {"kimi-k2.5"}
    for family in {row["family_id"] for row in rows}:
        for evidence in {row["evidence_id"] for row in rows if row["family_id"] == family}:
            c = next(row for row in rows if row["family_id"] == family and row["evidence_id"] == evidence and row["arm_id"] == "C_CLEAN_STATE_ONLY")
            d = next(row for row in rows if row["family_id"] == family and row["evidence_id"] == evidence and row["arm_id"] == "D_RECOVERED_STATE_ONLY")
            assert c["public_messages"] == d["public_messages"]
    assert all(row["history_provenance"] == "synthetic_engineering_only" for row in rows)
    assert all("expected_decision" not in row for row in rows)
    truth = read_jsonl(G85 / "private_truth.jsonl")
    assert {row["run_id"] for row in truth} == {row["run_id"] for row in rows}
    assert json.loads((G85 / "results/g85_private_truth_audit.json").read_text(encoding="utf-8"))["model_requests_private_truth_scan_hits"] == 0


def test_g85_repair_does_not_replace_primary_failure():
    primary_rows = read_jsonl(G85 / "plans/g85_engineering_pilot_plan.jsonl")
    repair_rows = read_jsonl(G85 / "plans/g85_engineering_adapter_repair1_plan.jsonl")
    assert len(repair_rows) == 1
    source = next(row for row in primary_rows if row["run_id"] == repair_rows[0]["repair_of_run_id"])
    primary = json.loads((G85 / "run/raw" / source["run_id"] / "result.json").read_text(encoding="utf-8"))
    repaired = json.loads((G85 / "run_adapter_repair1/raw" / repair_rows[0]["run_id"] / "result.json").read_text(encoding="utf-8"))
    assert primary["execution_status"] == "TECHNICAL_FAILURE"
    assert repaired["execution_status"] == "PASS"
    assert source["run_id"] != repair_rows[0]["run_id"]
