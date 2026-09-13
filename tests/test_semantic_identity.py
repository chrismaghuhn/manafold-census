import pytest

from manafold_census.semantic.evidence import (
    SourceRecordRefV1,
    StructuralFieldEvidenceV1,
    StructuralRecordEvidenceV1,
    evidence_sort_key,
)
from manafold_census.semantic.identity import (
    evidence_digest_for,
    requirement_id_for,
    requirement_identity_payload,
    reviewed_claim_digest_for,
    wire_digest_for,
)
from manafold_census.semantic.kind_payloads import (
    DrawCardsParametersV1,
    PayCostParametersV1,
    UnresolvedParametersV1,
)
from manafold_census.semantic.kinds import RequirementFamilyV1, RequirementKindV1
from manafold_census.semantic.model import (
    DerivationMethodV1,
    DerivationV1,
    ProvenanceV1,
    RequirementV1,
    ResolutionReasonV1,
    ResolutionStateV1,
    ResolutionV1,
    ReviewStatusV1,
    ReviewV1,
)
from manafold_census.semantic.primitives import (
    EntityRefV1,
    EntityRoleV1,
    MultiplicityV1,
    QuantityModeV1,
    QuantityV1,
    SemanticDescriptorV1,
    SemanticShapeV1,
    UnknownReasonV1,
    UnknownValueV1,
)

ORACLE_ID = "abcdefab-abcd-4abc-8abc-abcdefabcdef"
SOURCE_CARD_ID = "abcdefab-abcd-4abc-8abc-abcdefabcdea"
SOURCE_LOCK_DIGEST = "a" * 64
SOURCE_RECORD_SHA256 = "b" * 64


def _source(
    *,
    source_lock_digest: str = SOURCE_LOCK_DIGEST,
    source_record_sha256: str = SOURCE_RECORD_SHA256,
) -> SourceRecordRefV1:
    return SourceRecordRefV1(
        record_schema="census.structural-card.v1",
        source_lock_digest=source_lock_digest,
        oracle_id=ORACLE_ID,
        source_card_id=SOURCE_CARD_ID,
        source_record_sha256=source_record_sha256,
    )


def _entity() -> EntityRefV1:
    return EntityRefV1(EntityRoleV1.SOURCE, MultiplicityV1.ONE, None)


def _derivation(producer_id: str = "parser") -> DerivationV1:
    return DerivationV1(DerivationMethodV1.PARSER, producer_id, "1")


def _provenance(producer_id: str = "parser") -> ProvenanceV1:
    return ProvenanceV1((_derivation(producer_id),))


def _complete() -> ResolutionV1:
    return ResolutionV1(ResolutionStateV1.COMPLETE, ResolutionReasonV1.NONE, ())


def _proposal(
    *,
    source: SourceRecordRefV1 | None = None,
    evidence: tuple[object, ...] | None = None,
    provenance: ProvenanceV1 | None = None,
    parameters: object | None = None,
    kind: RequirementKindV1 = RequirementKindV1.DRAW_CARDS,
    family: RequirementFamilyV1 = RequirementFamilyV1.EFFECT,
    resolution: ResolutionV1 | None = None,
) -> RequirementV1:
    actual_source = source or _source()
    actual_evidence = evidence or (
        StructuralFieldEvidenceV1(actual_source, "oracle_text", None, "Draw"),
    )
    actual_parameters = parameters or DrawCardsParametersV1(
        _entity(), QuantityV1(QuantityModeV1.EXACT, 2)
    )
    return RequirementV1.create(
        source=actual_source,
        family=family,
        kind=kind,
        parameters=actual_parameters,
        evidence=actual_evidence,
        provenance=provenance or _provenance(),
        review=ReviewV1(ReviewStatusV1.PROPOSED, None, None),
        resolution=resolution or _complete(),
    )


def _accepted(requirement: RequirementV1) -> RequirementV1:
    return RequirementV1.create(
        source=requirement.source,
        family=requirement.family,
        kind=requirement.kind,
        parameters=requirement.parameters,
        evidence=requirement.evidence,
        provenance=requirement.provenance,
        review=ReviewV1(
            ReviewStatusV1.ACCEPTED,
            "independent-reviewer",
            reviewed_claim_digest_for(requirement),
        ),
        resolution=requirement.resolution,
    )


def test_identity_payload_and_digests_are_exact_and_deterministic() -> None:
    requirement = _proposal()

    assert requirement_id_for(requirement) == requirement.requirement_id
    assert requirement.requirement_id.startswith("srq_")
    payload = requirement_identity_payload(requirement)
    assert payload == {
        "identity_schema": "census.semantic-requirement-id.v1",
        "source_identity": {
            "record_schema": "census.structural-card.v1",
            "oracle_id": ORACLE_ID,
            "source_card_id": SOURCE_CARD_ID,
            "source_record_sha256": SOURCE_RECORD_SHA256,
        },
        "family": "effect",
        "kind": "draw_cards",
        "parameters": requirement.parameters.to_wire(),
    }
    assert "source_lock_digest" not in payload["source_identity"]
    assert evidence_digest_for(requirement.evidence[0]) == evidence_sort_key(
        requirement.evidence[0]
    )
    assert wire_digest_for(requirement) == wire_digest_for(requirement)
    assert reviewed_claim_digest_for(requirement) == reviewed_claim_digest_for(
        requirement
    )


def test_identity_is_producer_neutral_and_source_lock_stable() -> None:
    first = _proposal()
    second = _proposal(
        evidence=(StructuralRecordEvidenceV1(_source()),),
        provenance=_provenance("human-entry"),
    )
    changed_lock = _proposal(
        source=_source(source_lock_digest="c" * 64),
        evidence=(
            StructuralFieldEvidenceV1(
                _source(source_lock_digest="c" * 64), "oracle_text", None, "Draw"
            ),
        ),
    )

    assert first.requirement_id == second.requirement_id == changed_lock.requirement_id
    assert first.requirement_id == requirement_id_for(changed_lock)
    assert (
        first.requirement_id
        != _proposal(
            source=_source(source_record_sha256="d" * 64),
            evidence=(
                StructuralFieldEvidenceV1(
                    _source(source_record_sha256="d" * 64), "oracle_text", None, "Draw"
                ),
            ),
        ).requirement_id
    )
    assert reviewed_claim_digest_for(first) == reviewed_claim_digest_for(changed_lock)
    assert wire_digest_for(first) != wire_digest_for(changed_lock)


def test_identity_changes_for_kind_and_parameter_changes() -> None:
    draw = _proposal()
    changed_quantity = _proposal(
        parameters=DrawCardsParametersV1(_entity(), QuantityV1(QuantityModeV1.EXACT, 3))
    )

    assert draw.requirement_id != changed_quantity.requirement_id


def test_requirement_wire_round_trip_and_root_keys_are_exact() -> None:
    requirement = _proposal()

    assert set(requirement.to_wire()) == {
        "schema",
        "requirement_id",
        "source",
        "family",
        "kind",
        "parameters",
        "evidence",
        "provenance",
        "review",
        "resolution",
    }
    assert RequirementV1.from_wire(requirement.to_wire()) == requirement

    wire = requirement.to_wire()
    wire["extra"] = True
    with pytest.raises((TypeError, ValueError), match="extra|unexpected"):
        RequirementV1.from_wire(wire)


def test_wire_digest_changes_for_review_and_evidence_but_id_does_not() -> None:
    proposal = _proposal()
    accepted = _accepted(proposal)
    added_evidence = _proposal(
        evidence=(
            StructuralFieldEvidenceV1(proposal.source, "oracle_text", None, "Draw"),
            StructuralRecordEvidenceV1(proposal.source),
        )
    )

    assert accepted.requirement_id == proposal.requirement_id
    assert added_evidence.requirement_id == proposal.requirement_id
    assert wire_digest_for(accepted) != wire_digest_for(proposal)
    assert wire_digest_for(added_evidence) != wire_digest_for(proposal)


def test_review_binding_rejects_stale_terminal_content_and_allows_reopen() -> None:
    proposal = _proposal()
    accepted = _accepted(proposal)
    changed_provenance = _provenance("different-producer")

    with pytest.raises(ValueError, match="reviewed_claim_digest"):
        RequirementV1.create(
            source=proposal.source,
            family=proposal.family,
            kind=proposal.kind,
            parameters=proposal.parameters,
            evidence=proposal.evidence,
            provenance=changed_provenance,
            review=accepted.review,
            resolution=proposal.resolution,
        )

    reopened = RequirementV1.create(
        source=proposal.source,
        family=proposal.family,
        kind=proposal.kind,
        parameters=proposal.parameters,
        evidence=proposal.evidence,
        provenance=changed_provenance,
        review=ReviewV1(ReviewStatusV1.IN_REVIEW, None, None),
        resolution=proposal.resolution,
    )
    assert reopened.requirement_id == proposal.requirement_id


def test_review_status_separation_and_accepted_partial_claim() -> None:
    partial_resolution = ResolutionV1(
        ResolutionStateV1.PARTIAL,
        ResolutionReasonV1.INSUFFICIENT_EVIDENCE,
        ("/parameters.quantity.value",),
    )
    partial = _proposal(
        parameters=DrawCardsParametersV1(
            _entity(),
            QuantityV1(
                QuantityModeV1.UNKNOWN,
                UnknownValueV1(UnknownReasonV1.INSUFFICIENT_EVIDENCE, "quantity"),
            ),
        ),
        resolution=partial_resolution,
    )
    accepted = _accepted(partial)

    assert accepted.review.status is ReviewStatusV1.ACCEPTED
    assert accepted.resolution.state is ResolutionStateV1.PARTIAL
    assert accepted.review.reviewed_claim_digest == reviewed_claim_digest_for(partial)

    with pytest.raises((TypeError, ValueError)):
        ReviewV1(ReviewStatusV1.PROPOSED, "reviewer", None)
    with pytest.raises((TypeError, ValueError)):
        ReviewV1(ReviewStatusV1.ACCEPTED, None, "a" * 64)


def test_unresolved_requirement_round_trips_and_is_valid() -> None:
    unresolved = _proposal(
        family=RequirementFamilyV1.UNKNOWN,
        kind=RequirementKindV1.UNRESOLVED,
        parameters=UnresolvedParametersV1(
            "oracle_text",
            SemanticShapeV1.UNKNOWN,
            "What does this text require?",
            (),
            None,
        ),
        resolution=ResolutionV1(
            ResolutionStateV1.UNRESOLVED,
            ResolutionReasonV1.UNSUPPORTED_SHAPE,
            ("/parameters",),
        ),
    )

    assert RequirementV1.from_wire(unresolved.to_wire()) == unresolved


def test_complete_rejects_unknown_and_free_text_only_descriptor_meaning() -> None:
    with pytest.raises(ValueError, match="COMPLETE|unknown"):
        _proposal(
            parameters=DrawCardsParametersV1(
                _entity(),
                QuantityV1(
                    QuantityModeV1.UNKNOWN,
                    UnknownValueV1(UnknownReasonV1.UNKNOWN_SEMANTICS, None),
                ),
            )
        )

    label_only = SemanticDescriptorV1(
        SemanticShapeV1.EFFECT, "only prose", None, None, None, ()
    )
    with pytest.raises(ValueError, match="descriptor|COMPLETE"):
        _proposal(
            family=RequirementFamilyV1.COST,
            kind=RequirementKindV1.PAY_COST,
            parameters=PayCostParametersV1(_entity(), label_only),
        )


def test_model_rejects_invalid_terminal_digest() -> None:
    proposal = _proposal()

    with pytest.raises(ValueError, match="reviewed_claim_digest"):
        RequirementV1.create(
            source=proposal.source,
            family=proposal.family,
            kind=proposal.kind,
            parameters=proposal.parameters,
            evidence=proposal.evidence,
            provenance=proposal.provenance,
            review=ReviewV1(ReviewStatusV1.ACCEPTED, "reviewer", "0" * 64),
            resolution=proposal.resolution,
        )
