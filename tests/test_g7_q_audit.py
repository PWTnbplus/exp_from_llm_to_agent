from __future__ import annotations

from scripts.audit_g7_q import q_record_is_complete


def test_q_audit_accepts_any_nonempty_design_compliant_strings() -> None:
    assert q_record_is_complete({"verdict": "REJECT", "reason": "counterexample checked"})
    assert q_record_is_complete({"verdict": "boundary review", "reason": "the text is retained"})


def test_q_audit_rejects_missing_or_blank_q_fields() -> None:
    assert not q_record_is_complete({"verdict": "SUPPORTED"})
    assert not q_record_is_complete({"verdict": "", "reason": "present"})
    assert not q_record_is_complete({"verdict": "SUPPORTED", "reason": "   "})
    assert not q_record_is_complete(None)
