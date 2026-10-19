from scripts.v9.claim_ir import ClaimIR
from scripts.v9.math_verifier import verify_claim


def test_v9_exact_and_counterexample_certificates():
    assert verify_claim(ClaimIR("monotonicity", "x**2", "increasing", "x", "x>=0", ""))["status"] == "PROVEN_TRUE"
    assert verify_claim(ClaimIR("monotonicity", "x**2", "decreasing", "x", "x>=0", ""))["status"] == "PROVEN_FALSE"
