from __future__ import annotations

from scripts.audit_g7_q import assess_q_record, q_record_is_complete


def test_q_audit_accepts_any_nonempty_design_compliant_strings() -> None:
    assert q_record_is_complete({"verdict": "REJECT", "reason": "counterexample checked"})
    assert q_record_is_complete({"verdict": "boundary review", "reason": "the text is retained"})


def test_q_audit_rejects_missing_or_blank_q_fields() -> None:
    assert not q_record_is_complete({"verdict": "SUPPORTED"})
    assert not q_record_is_complete({"verdict": "", "reason": "present"})
    assert not q_record_is_complete({"verdict": "SUPPORTED", "reason": "   "})
    assert not q_record_is_complete(None)


def test_q_self_report_is_not_an_external_q_pass() -> None:
    # The formal Q metric remains NOT_SCORED until a separate verifier artifact
    # is supplied; a complete model record alone cannot set is_valid=True.
    assert assess_q_record({"verdict": "SUPPORTED", "reason": "checked"}) == {
        "record_complete": True,
        "q_validity": "NOT_SCORED",
        "external_q_verifier_present": False,
    }
