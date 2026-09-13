from __future__ import annotations

import pytest
from analysis_fixtures import (
    accepted_producer_candidate,
    candidate_a,
    candidate_b_with_other_evidence,
    canonical_conflict,
    competing_candidate_b,
    complete_candidate,
    explicit_conflict,
    other_candidate,
    partial_candidate_same_id,
)

from manafold_census.analysis.producer import RelationshipProposalV1
from manafold_census.analysis.reconcile import (
    ReconciliationFailure,
    reconcile,
)


def test_same_id_same_resolution_unions_evidence_and_provenance() -> None:
    result = reconcile([candidate_a(), candidate_b_with_other_evidence()])
    assert [item.requirement_id for item in result.requirements] == [
        candidate_a().requirement_id
    ]
    assert {item.fragment for item in result.requirements[0].evidence} == {
        "Draw",
        "two",
    }
    assert len(result.requirements[0].provenance.derivations) == 2
    assert result.outcome_is_unresolved is False


def test_same_id_different_resolution_is_omitted_not_synthesized() -> None:
    result = reconcile([complete_candidate(), partial_candidate_same_id()])
    assert result.requirements == ()
    assert result.outcome_is_unresolved is True
    assert result.trace_dispositions == ("DISPUTED_IDENTITY_OMITTED",)
    assert {
        (item.requirement_id, item.resolution.state)
        for item in result.disputed_candidates
    } == {
        (complete_candidate().requirement_id, complete_candidate().resolution.state),
        (
            partial_candidate_same_id().requirement_id,
            partial_candidate_same_id().resolution.state,
        ),
    }


def test_other_undisputed_requirements_survive_a_disputed_identity() -> None:
    result = reconcile(
        [complete_candidate(), partial_candidate_same_id(), other_candidate()]
    )
    assert [item.requirement_id for item in result.requirements] == [
        other_candidate().requirement_id
    ]


def test_different_ids_are_not_deduplicated_or_priority_selected() -> None:
    result = reconcile([candidate_a(), competing_candidate_b()])
    assert {item.requirement_id for item in result.requirements} == {
        candidate_a().requirement_id,
        competing_candidate_b().requirement_id,
    }
    assert result.relationships == ()


def test_conflicts_with_requires_explicit_producer_proposal() -> None:
    without_relation = reconcile([candidate_a(), other_candidate()])
    assert without_relation.relationships == ()
    with_relation = reconcile(
        [candidate_a(), other_candidate()],
        [explicit_conflict()],
    )
    assert with_relation.relationships == (canonical_conflict(),)


def test_invalid_relationship_endpoint_is_execution_failure() -> None:
    invalid = explicit_conflict().relationship
    missing_endpoint = type(invalid)(
        invalid.relationship_type,
        invalid.from_requirement_id,
        "srq_" + "f" * 64,
        invalid.ordinal,
    )
    with pytest.raises(ReconciliationFailure, match="endpoint"):
        reconcile(
            [candidate_a(), other_candidate()],
            [RelationshipProposalV1(missing_endpoint)],
        )


def test_terminal_producer_review_is_execution_failure() -> None:
    with pytest.raises(ReconciliationFailure, match="PROPOSED"):
        reconcile([accepted_producer_candidate()])
