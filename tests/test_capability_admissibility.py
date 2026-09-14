from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from manafold_census.capability.admissibility import (
    ADMISSIBILITY_DOMAIN,
    ADMISSIBILITY_PREFIX,
    AdmissibilityDecisionV1,
    SourceRequirementAdmissibilityV1,
    active_admissibility_for,
    admissibility_claim_payload,
    admissibility_record_id_for,
    admissibility_review_digest_for,
)
from manafold_census.semantic.evidence import (
    SourceRecordRefV1,
    StructuralFieldEvidenceV1,
)
from manafold_census.semantic.identity import reviewed_claim_digest_for
from manafold_census.semantic.kind_payloads import DrawCardsParametersV1
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
)

M3_MANIFEST_SHA256 = "a" * 64
ORACLE_ID = "abcdefab-abcd-4abc-8abc-abcdefabcdef"
SOURCE_CARD_ID = "abcdefab-abcd-4abc-8abc-abcdefabcdea"


def _complete_resolution() -> ResolutionV1:
    return ResolutionV1(ResolutionStateV1.COMPLETE, ResolutionReasonV1.NONE, ())


def _requirement(
    *,
    status: ReviewStatusV1 = ReviewStatusV1.PROPOSED,
    resolution: ResolutionV1 | None = None,
) -> RequirementV1:
    source = SourceRecordRefV1(
        "census.structural-card.v1",
        "1" * 64,
        ORACLE_ID,
        SOURCE_CARD_ID,
        "2" * 64,
    )
    actual_resolution = resolution or _complete_resolution()
    parameters = DrawCardsParametersV1(
        EntityRefV1(EntityRoleV1.CONTROLLER, MultiplicityV1.ONE, None),
        QuantityV1(QuantityModeV1.EXACT, 2),
    )
    proposal = RequirementV1.create(
        source=source,
        family=RequirementFamilyV1.EFFECT,
        kind=RequirementKindV1.DRAW_CARDS,
        parameters=parameters,
        evidence=(StructuralFieldEvidenceV1(source, "oracle_text", None, "Draw"),),
        provenance=ProvenanceV1(
            (DerivationV1(DerivationMethodV1.PARSER, "task4-test", "1"),)
        ),
        review=ReviewV1(ReviewStatusV1.PROPOSED, None, None),
        resolution=actual_resolution,
    )
    if status is ReviewStatusV1.PROPOSED:
        return proposal
    review = ReviewV1(
        status,
        "maintainer:test"
        if status in (ReviewStatusV1.ACCEPTED, ReviewStatusV1.REJECTED)
        else None,
        reviewed_claim_digest_for(proposal)
        if status in (ReviewStatusV1.ACCEPTED, ReviewStatusV1.REJECTED)
        else None,
    )
    return RequirementV1.create(
        source=source,
        family=RequirementFamilyV1.EFFECT,
        kind=RequirementKindV1.DRAW_CARDS,
        parameters=parameters,
        evidence=proposal.evidence,
        provenance=proposal.provenance,
        review=review,
        resolution=actual_resolution,
    )


def _accepted_record(
    requirement: RequirementV1,
    *,
    m3_manifest_sha256: str = M3_MANIFEST_SHA256,
) -> SourceRequirementAdmissibilityV1:
    return SourceRequirementAdmissibilityV1.for_requirement(
        requirement,
        m3_analysis_manifest_sha256=m3_manifest_sha256,
        authority_id="m4.source-requirement-admissibility",
        authority_version="1",
        reviewer_id="maintainer:test",
    )


def _validate_schema(document: dict[str, object]) -> None:
    root = Path(__file__).parents[1]
    schema_path = root / "schemas" / "source-requirement-admissibility.v1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(document)


def test_proposed_complete_requirement_requires_m4_admissibility() -> None:
    requirement = _requirement()

    assert requirement.review.status is ReviewStatusV1.PROPOSED
    assert requirement.resolution.state is ResolutionStateV1.COMPLETE
    assert active_admissibility_for(requirement, records=()) is False


def test_accepted_admissibility_binds_exact_m3_m2_digests() -> None:
    requirement = _requirement()
    before = requirement.review.to_wire()
    record = _accepted_record(requirement)

    assert record.decision is AdmissibilityDecisionV1.ACCEPTED_FOR_CAPABILITY_MAPPING
    assert record.requirement_id == requirement.requirement_id
    assert active_admissibility_for(requirement, records=(record,)) is True
    assert requirement.review.to_wire() == before
    assert record.m2_reviewed_claim_digest == reviewed_claim_digest_for(requirement)


@pytest.mark.parametrize(
    ("status", "resolution"),
    [
        (ReviewStatusV1.REJECTED, _complete_resolution()),
        (
            ReviewStatusV1.PROPOSED,
            ResolutionV1(
                ResolutionStateV1.PARTIAL,
                ResolutionReasonV1.UNKNOWN_SEMANTICS,
                ("/parameters/quantity",),
            ),
        ),
        (
            ReviewStatusV1.PROPOSED,
            ResolutionV1(
                ResolutionStateV1.UNRESOLVED,
                ResolutionReasonV1.CONFLICTING_INTERPRETATIONS,
                ("/parameters/quantity",),
            ),
        ),
    ],
)
def test_rejected_or_incomplete_requirement_is_never_admissible(
    status: ReviewStatusV1,
    resolution: ResolutionV1,
) -> None:
    requirement = _requirement(status=status, resolution=resolution)

    with pytest.raises(ValueError, match="not admissible"):
        _accepted_record(requirement)
    assert active_admissibility_for(requirement, records=()) is False


def test_admissibility_digest_is_non_cyclic_and_schema_valid() -> None:
    record = _accepted_record(_requirement())

    assert ADMISSIBILITY_DOMAIN == "census.source-requirement-admissibility.v1"
    assert ADMISSIBILITY_PREFIX == "sra_"
    assert record.review_digest == admissibility_review_digest_for(record)
    assert record.record_id == admissibility_record_id_for(record)
    assert admissibility_claim_payload(record)["schema"] == record.SCHEMA
    assert SourceRequirementAdmissibilityV1.from_wire(record.to_wire()) == record
    _validate_schema(record.to_wire())


def test_rejected_admissibility_is_retained_but_not_active() -> None:
    requirement = _requirement()
    record = SourceRequirementAdmissibilityV1.for_requirement(
        requirement,
        m3_analysis_manifest_sha256=M3_MANIFEST_SHA256,
        authority_id="m4.source-requirement-admissibility",
        authority_version="1",
        reviewer_id="maintainer:test",
        decision=AdmissibilityDecisionV1.REJECTED_FOR_CAPABILITY_MAPPING,
    )

    assert record.decision is AdmissibilityDecisionV1.REJECTED_FOR_CAPABILITY_MAPPING
    assert active_admissibility_for(requirement, records=(record,)) is False


def test_admissibility_rejects_stale_requirement_claims_and_manifest() -> None:
    requirement = _requirement()
    record = _accepted_record(requirement)

    with pytest.raises(ValueError, match="Requirement wire digest"):
        record.validate_against_requirement(
            _requirement(
                resolution=ResolutionV1(
                    ResolutionStateV1.PARTIAL,
                    ResolutionReasonV1.UNKNOWN_SEMANTICS,
                    ("/parameters/quantity",),
                )
            )
        )

    wrong_manifest = SourceRequirementAdmissibilityV1.for_requirement(
        requirement,
        m3_analysis_manifest_sha256="f" * 64,
        authority_id="m4.source-requirement-admissibility",
        authority_version="1",
        reviewer_id="maintainer:test",
    )
    with pytest.raises(ValueError, match="M3 manifest"):
        wrong_manifest.validate_m3_manifest(M3_MANIFEST_SHA256)


def test_admissibility_rejects_conflicting_records() -> None:
    requirement = _requirement()
    accepted = _accepted_record(requirement)
    rejected = SourceRequirementAdmissibilityV1.for_requirement(
        requirement,
        m3_analysis_manifest_sha256=M3_MANIFEST_SHA256,
        authority_id="m4.source-requirement-admissibility",
        authority_version="2",
        reviewer_id="maintainer:test",
        decision=AdmissibilityDecisionV1.REJECTED_FOR_CAPABILITY_MAPPING,
    )

    with pytest.raises(ValueError, match="conflicting"):
        active_admissibility_for(requirement, records=(accepted, rejected))


def test_admissibility_wire_rejects_stale_derived_fields_and_unknown_fields() -> None:
    record = _accepted_record(_requirement())
    stale = record.to_wire()
    stale["record_id"] = "sra_" + "f" * 64
    with pytest.raises(ValueError, match="record_id"):
        SourceRequirementAdmissibilityV1.from_wire(stale)

    extra = record.to_wire()
    extra["timestamp"] = "never"
    with pytest.raises(ValueError, match="unexpected properties"):
        SourceRequirementAdmissibilityV1.from_wire(extra)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("m2_review_status_observed", "REJECTED"),
        ("m2_resolution_state_observed", "PARTIAL"),
    ],
)
def test_admissibility_schema_rejects_ineligible_accepted_observations(
    field: str,
    value: str,
) -> None:
    wire = _accepted_record(_requirement()).to_wire()
    wire[field] = value

    with pytest.raises(ValidationError):
        _validate_schema(wire)
