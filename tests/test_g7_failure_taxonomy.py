from __future__ import annotations

from scripts.audit_g7_failure_taxonomy import count_model_key_hits


def test_failure_taxonomy_detects_routing_metadata_in_model_requests() -> None:
    events = [
        {
            "event_type": "MODEL_REQUEST",
            "payload": {"messages": [{"role": "user", "content": "cf_type=CF1"}]},
        },
        {
            "event_type": "MODEL_REQUEST",
            "payload": {"messages": [{"role": "user", "content": "public only"}]},
        },
    ]
    assert count_model_key_hits(events, ("cf_type", "theory_family_id")) == {"cf_type": 1}
