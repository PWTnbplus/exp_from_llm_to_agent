import pytest

from scripts.v9.claim_ir import ClaimIR, ClaimParseError, parse_claim


def test_v9_claim_parser_is_conservative():
    ir = parse_claim("f(x)=x**2 is increasing for x>=0")
    assert isinstance(ir, ClaimIR)
    assert ir.expression == "x**2"
    with pytest.raises(ClaimParseError):
        parse_claim("missing proposition")
