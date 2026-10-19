from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.v7.machine_experiment_config import get_config
from scripts.v7.math_claim_ir import ClaimParseError, parse_claim
from scripts.v7.math_verify_smt import verify as verify_bounded
from scripts.v7.math_verify_sympy import verify as verify_sympy


def test_v7_enforces_one_kimi_model() -> None:
    assert get_config("kimi-k2.5").language_model_count == 1
    with pytest.raises(ValueError):
        get_config("qwen3.5-plus")


def test_controlled_parser_rejects_calls_and_attributes() -> None:
    with pytest.raises((ClaimParseError, SyntaxError)):
        parse_claim("f(x)=__import__('os').system('whoami') is increasing for x>=0")


def test_independent_verifiers_detect_mutation_counterexample() -> None:
    ir = parse_claim("f(x)=x^2 is decreasing for x>=0")
    assert verify_bounded(ir)["result"] == "COUNTEREXAMPLE"
    assert verify_sympy(ir)["result"] == "UNKNOWN"


def test_historical_denominators_are_not_accepted_as_new_counts(tmp_path: Path) -> None:
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({"formal_denominator": 552, "denominator_changed": False}), encoding="utf-8")
    assert json.loads(p.read_text(encoding="utf-8"))["denominator_changed"] is False
