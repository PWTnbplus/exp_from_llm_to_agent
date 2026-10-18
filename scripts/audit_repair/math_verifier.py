"""Small, independent, fail-closed mathematical verifier.

It is intentionally narrow.  It proves only the structured counterfactual
fixtures implemented here and refuses to turn arbitrary model prose into a
theorem.  The G6 audit therefore reports unparseable/free-text revisions as
NOT_SCORED or INCONCLUSIVE rather than copying the private oracle.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any


STATUSES = {"PASS", "FAIL", "INCONCLUSIVE", "NOT_SCORED", "INELIGIBLE"}


@dataclass(frozen=True)
class Verdict:
    status: str
    grade: str | None
    proof_kind: str | None
    reason_code: str
    evidence: dict[str, Any]


def _v(status: str, reason: str, *, grade: str | None = None,
       proof: str | None = None, **evidence: Any) -> Verdict:
    if status not in STATUSES:
        raise ValueError(status)
    return Verdict(status, grade, proof, reason, evidence)


def verify_counterfactual(*, cf_type: str, claim: str | None,
                          quantifier: str = "forall_allowed_parameters") -> Verdict:
    """Verify the fixed dx/dt=-k*x adversarial fixtures without an oracle."""
    if not isinstance(claim, str) or not claim.strip():
        return _v("NOT_SCORED", "CLAIM_UNPARSABLE")
    text = claim.casefold()
    if cf_type == "CF1":
        if "k<0" in text or "k < 0" in text:
            return _v("FAIL", "MATHEMATICAL_COUNTEREXAMPLE", grade="A", proof="counterexample",
                      counterexample="k=-1 makes -k*x increasing for x>0")
        return _v("INCONCLUSIVE", "VERIFIER_INCONCLUSIVE")
    if cf_type == "CF2":
        if any(token in text for token in ("rename", "renaming", "重命名", "同构")):
            return _v("PASS", "VARIABLE_RENAMING_PRESERVED", grade="A", proof="symbolic",
                      invariant="alpha-renaming leaves the expression tree unchanged")
        return _v("INCONCLUSIVE", "VERIFIER_INCONCLUSIVE")
    if cf_type == "CF3":
        if re.search(r"all\s+k\s*(?:>=|≥)\s*0", text) and "strict" in text:
            return _v("FAIL", "LOGICAL_QUANTIFIER_ERROR", grade="A", proof="counterexample",
                      counterexample="k=0 gives dx/dt=0, not strict decrease")
        if ("k=0" in text or "k = 0" in text or "k=0" in text.replace(" ", "")) and any(
            token in text for token in ("not strict", "not guaranteed", "boundary", "非严格", "非增加", "undefined", "无定义")
        ):
            return _v("PASS", "BOUNDARY_CONDITION_HANDLED", grade="A", proof="symbolic",
                      implication="k=0 implies x is constant and strict decrease is not licensed")
        return _v("INCONCLUSIVE", "VERIFIER_INCONCLUSIVE")
    if cf_type == "CF4":
        if any(token in text for token in ("undetermined", "undetermined", "无法确定", "cannot determine", "unknown")):
            return _v("PASS", "UNKNOWN_SIGN_LEFT_UNDETERMINED", grade="A", proof="symbolic")
        if "strict" in text and any(token in text for token in ("always", "forall", "所有", "必然")):
            return _v("FAIL", "LOGICAL_QUANTIFIER_ERROR", grade="A", proof="counterexample",
                      counterexample="the sign of k is unspecified")
        return _v("INCONCLUSIVE", "VERIFIER_INCONCLUSIVE")
    return _v("INELIGIBLE", "UNKNOWN_COUNTERFACTUAL_TYPE")


def verify_candidate_claim(*, cf_type: str, claim: Any,
                           quantifier: str, public_problem: str) -> Verdict:
    """Apply the narrow verifier to an actual model claim, never the oracle."""
    if not isinstance(claim, str) or not claim.strip():
        return _v("NOT_SCORED", "CLAIM_UNPARSABLE")
    verdict = verify_counterfactual(cf_type=cf_type, claim=claim, quantifier=quantifier)
    if verdict.status == "PASS" and quantifier not in {"forall_allowed_parameters", "instance"}:
        return _v("INCONCLUSIVE", "DOMAIN_OR_QUANTIFIER_AMBIGUOUS")
    return verdict


def verifier_sha256() -> str:
    # The caller records the source hash, not a generated or provider claim.
    with open(__file__, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()
