from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from manafold_census.capability.model import CapabilityRefV1
from manafold_census.capability.review import (
    CapabilityDefinitionReviewSubjectV1,
    CapabilityLinkReviewSubjectV1,
    CapabilityReviewRecordV1,
    EvolutionReviewSubjectV1,
    GeneralizationBasisV1,
    MappingDecisionReviewSubjectV1,
    ReviewDecisionV1,
    ReviewSubjectKindV1,
    ReviewSubjectV1,
    review_digest_for,
    review_record_id_for,
)

CAPABILITY_FAMILY_ID = "capfam_" + "a" * 64
CLAIM_DIGEST = "b" * 64


def _definition_subject() -> CapabilityDefinitionReviewSubjectV1:
    return CapabilityDefinitionReviewSubjectV1(
        capability_family_id=CAPABILITY_FAMILY_ID,
        capability_version=1,
        claim_digest=CLAIM_DIGEST,
    )


def _record(
    *,
    subject: ReviewSubjectV1 | None = None,
    decision: ReviewDecisionV1 = ReviewDecisionV1.ACCEPTED,
    basis: GeneralizationBasisV1 | None = GeneralizationBasisV1.MULTI_SOURCE_REUSE,
) -> CapabilityReviewRecordV1:
    actual_subject = _definition_subject() if subject is None else subject
    return CapabilityReviewRecordV1.create(
        authority_id="m4.capability-review",
        authority_version="1",
        subject=actual_subject,
        decision=decision,
        reviewer_id="maintainer:test",
        generalization_basis=basis,
    )


def _validate_schema(document: dict[str, object]) -> None:
    schema_path = (
        Path(__file__).parents[1] / "schemas" / "capability-review.v1.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(document)


def test_definition_review_requires_a_closed_generalization_basis() -> None:
    review = _record(
        basis=GeneralizationBasisV1.MULTI_SOURCE_REUSE,
    )

    assert review.generalization_basis is GeneralizationBasisV1.MULTI_SOURCE_REUSE
    with pytest.raises(ValueError, match="generalization_basis"):
        _record(basis="CARD_SPECIFIC_EXCEPTION")  # type: ignore[arg-type]


def test_accepted_definition_review_requires_a_basis() -> None:
    with pytest.raises(ValueError, match="generalization_basis"):
        _record(basis=None)


def test_non_definition_review_subjects_require_null_generalization_basis() -> None:
    subjects = (
        CapabilityLinkReviewSubjectV1("rcl_" + "c" * 64, "d" * 64),
        MappingDecisionReviewSubjectV1("rmd_" + "e" * 64, "f" * 64),
        EvolutionReviewSubjectV1("cev_" + "1" * 64, "2" * 64),
    )

    for subject in subjects:
        record = _record(subject=subject, basis=None)
        assert record.generalization_basis is None

        with pytest.raises(ValueError, match="generalization_basis"):
            _record(subject=subject)


def test_review_wire_round_trip_is_canonical_and_schema_valid() -> None:
    record = _record()

    assert CapabilityReviewRecordV1.from_wire(record.to_wire()) == record
    _validate_schema(record.to_wire())
    assert record.subject.KIND is ReviewSubjectKindV1.CAPABILITY_DEFINITION


def test_review_digest_projection_excludes_derived_fields() -> None:
    record = _record()

    assert record.review_digest == review_digest_for(record)
    assert record.record_id == review_record_id_for(record)

    wire = record.to_wire()
    wire["record_id"] = "mrv_" + "f" * 64
    wire["review_digest"] = "e" * 64
    with pytest.raises(ValueError, match="record_id"):
        CapabilityReviewRecordV1.from_wire(wire)


def test_review_subjects_are_closed_typed_wires() -> None:
    definition_wire = _definition_subject().to_wire()
    assert definition_wire == {
        "type": "CAPABILITY_DEFINITION",
        "capability_family_id": CAPABILITY_FAMILY_ID,
        "capability_version": 1,
        "claim_digest": CLAIM_DIGEST,
    }
    assert (
        CapabilityDefinitionReviewSubjectV1.from_wire(definition_wire)
        == _definition_subject()
    )

    with pytest.raises(TypeError, match="typed review subject"):
        CapabilityReviewRecordV1.create(
            authority_id="m4.capability-review",
            authority_version="1",
            subject={"type": "CAPABILITY_DEFINITION"},  # type: ignore[arg-type]
            decision=ReviewDecisionV1.ACCEPTED,
            reviewer_id="maintainer:test",
            generalization_basis=GeneralizationBasisV1.MULTI_SOURCE_REUSE,
        )

    unknown = dict(definition_wire)
    unknown["type"] = "UNSUPPORTED"
    with pytest.raises(ValueError, match="subject type"):
        CapabilityDefinitionReviewSubjectV1.from_wire(unknown)


def test_review_rejects_stale_digest_and_unknown_wire_fields() -> None:
    record = _record()
    stale = record.to_wire()
    stale["review_digest"] = "f" * 64
    with pytest.raises(ValueError, match="review_digest"):
        CapabilityReviewRecordV1.from_wire(stale)

    extra = record.to_wire()
    extra["timestamp"] = "never"
    with pytest.raises(ValueError, match="unexpected properties"):
        CapabilityReviewRecordV1.from_wire(extra)


@pytest.mark.parametrize(
    "subject",
    [
        CapabilityLinkReviewSubjectV1("rcl_" + "c" * 64, "d" * 64),
        MappingDecisionReviewSubjectV1("rmd_" + "e" * 64, "f" * 64),
        EvolutionReviewSubjectV1("cev_" + "1" * 64, "2" * 64),
    ],
)
def test_review_schema_rejects_generalization_basis_for_non_definition_subject(
    subject: ReviewSubjectV1,
) -> None:
    wire = _record(subject=subject, basis=None).to_wire()
    wire["generalization_basis"] = "MULTI_SOURCE_REUSE"

    with pytest.raises(ValidationError):
        _validate_schema(wire)


def test_review_schema_requires_generalization_basis_for_accepted_definition() -> None:
    wire = _record().to_wire()
    wire["generalization_basis"] = None

    with pytest.raises(ValidationError):
        _validate_schema(wire)


def test_review_subject_rejects_wrong_capability_ref_shape() -> None:
    with pytest.raises(ValueError, match="capability_family_id"):
        CapabilityDefinitionReviewSubjectV1("capability_" + "a" * 64, 1, CLAIM_DIGEST)

    assert _definition_subject().capability_ref == CapabilityRefV1(
        CAPABILITY_FAMILY_ID,
        1,
        CLAIM_DIGEST,
    )
