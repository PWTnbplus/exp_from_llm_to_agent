from scripts.v5.build_v5_pack import (
    all_planned_with_missing,
    square_nonnegative_monotonicity,
    truth_flip_requires_semantic_change,
    validate_checkpoint_fork_messages,
    validate_nonfinal_u_observation,
)


def test_u_targets_intermediate_b_not_final_c() -> None:
    graph = {
        "nodes": [
            {"claim_id": "A", "kind": "assumption"},
            {"claim_id": "B", "kind": "intermediate"},
            {"claim_id": "C", "kind": "conclusion"},
        ],
        "edges": [{"source_claim_id": "A", "target_claim_id": "B"},
                  {"source_claim_id": "B", "target_claim_id": "C"}],
    }
    assert validate_nonfinal_u_observation(graph, "B", "supported", "refuted") == (
        True, "eligible_nonfinal_transition"
    )
    assert validate_nonfinal_u_observation(graph, "C", "supported", "refuted")[0] is False


def test_u_does_not_call_irrelevant_no_update_a_successful_flip() -> None:
    graph = {"nodes": [{"claim_id": "B", "kind": "intermediate"}], "edges": []}
    assert validate_nonfinal_u_observation(graph, "B", "supported", "supported")[0] is False


def test_truth_flip_requires_public_semantic_change() -> None:
    assert truth_flip_requires_semantic_change("f(x)=x", "f(x)=x") is False
    assert truth_flip_requires_semantic_change("f(x)=x", "f(x)=-x") is True


def test_luct008_square_closed_endpoint_semantics() -> None:
    result = square_nonnegative_monotonicity()
    assert result["weakly_increasing"] is True
    assert result["strictly_increasing"] is True
    assert result["strictly_decreasing"] is False
    assert result["endpoint_zero_derivative"] is True


def test_checkpoint_forks_require_identical_initial_messages() -> None:
    good = [
        {"checkpoint_id": "cp-1", "initial_messages_sha256": "same", "arm": "control"},
        {"checkpoint_id": "cp-1", "initial_messages_sha256": "same", "arm": "intervention"},
    ]
    bad = [*good, {"checkpoint_id": "cp-1", "initial_messages_sha256": "different", "arm": "sham"}]
    assert validate_checkpoint_fork_messages(good)[0] is True
    assert validate_checkpoint_fork_messages(bad) == (False, "same_checkpoint_has_different_initial_messages")


def test_missing_model_response_stays_in_all_planned_denominator() -> None:
    assert all_planned_with_missing(["a", "b", "c"], ["a", "c"]) == {
        "planned": 3, "observed": 2, "missing": 1
    }
