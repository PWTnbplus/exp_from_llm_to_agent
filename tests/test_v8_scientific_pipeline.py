from __future__ import annotations

import json
import random

from scripts.v8.build_v8_cohorts import build_g6, build_g7, build_lu, build_q
from scripts.v8.claim_ir import ClaimIR, parse_claim_text
from scripts.v8.prove_exact import prove_claim, replay_certificate


def test_exact_math_certificate_and_mutation() -> None:
    ir, reason = parse_claim_text("f(x)=2*x+1 is increasing for x>=0")
    assert reason == "RECOVERED"
    assert ir is not None
    certificate = prove_claim(ir)
    assert certificate["status"] == "PROVEN_TRUE"
    assert replay_certificate(certificate)["status_matches"]
    mutated = ClaimIR(**{**ir.to_dict(), "expression": "-2*x-1", "relation": "increasing"})
    assert prove_claim(mutated)["status"] == "PROVEN_FALSE"


def test_truth_is_not_in_public_cohorts(tmp_path) -> None:
    build_g6(tmp_path)
    build_q(tmp_path)
    build_lu(tmp_path)
    build_g7(tmp_path)
    for path in tmp_path.glob("prospective_*/public_cases.jsonl"):
        text = path.read_text(encoding="utf-8")
        assert "expected_action" not in text
        assert "truth_key" not in text
        assert "independent_proof" not in text


def test_lu_randomization_is_reproducible_and_complete(tmp_path) -> None:
    plan = build_lu(tmp_path)
    assert plan["arms"] == ["CONTROL", "REAL", "SHAM"]
    first, second = random.Random(20261019), random.Random(20261019)
    a, b = ["CONTROL", "REAL", "SHAM"], ["CONTROL", "REAL", "SHAM"]
    first.shuffle(a)
    second.shuffle(b)
    assert a == b
    rows = [json.loads(line) for line in (tmp_path / "prospective_lu/public_cases.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 4
    assert all({"checkpoint_nodes", "real_intervention", "sham_intervention"} <= set(row) for row in rows)


def test_g7_has_forward_stages_and_new_graphs(tmp_path) -> None:
    plan = build_g7(tmp_path)
    assert plan["not_retroactive"] is True
    assert plan["diagnostic_stages"] == ["D0", "D1_V", "D2_VL", "D3_VLU"]
    rows = [json.loads(line) for line in (tmp_path / "prospective_g7/public_cases.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 4
    assert all(row["graph_id"].endswith("NEW-GRAPH") for row in rows)

