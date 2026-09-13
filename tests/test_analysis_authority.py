from __future__ import annotations

import copy
from dataclasses import replace

import pytest
from analysis_fixtures import source_ref

from manafold_census.analysis.authority import (
    NegativeAuthorityScopeV1,
    NegativeRequirementAuthorityRecordV1,
    negative_authority_record_sha256,
    negative_authority_scope_digest,
    validate_negative_requirement_authority,
)
from manafold_census.analysis.model import NegativeReviewAuthorityRefV1
from manafold_census.validation import validate_document


def scope() -> NegativeAuthorityScopeV1:
    return NegativeAuthorityScopeV1(
        source_fields=("face.oracle_text", "keywords", "oracle_text")
    )


def negative_authority_record() -> NegativeRequirementAuthorityRecordV1:
    return NegativeRequirementAuthorityRecordV1.create(
        authority_id="fixture-negative-authority",
        authority_version="1",
        source=source_ref(),
        scope=scope(),
    )


def authority_reference(
    record: NegativeRequirementAuthorityRecordV1,
) -> NegativeReviewAuthorityRefV1:
    return NegativeReviewAuthorityRefV1(
        authority_id=record.authority_id,
        authority_version=record.authority_version,
        record_id=record.record_id,
        record_sha256=record.record_sha256,
        scope_digest=record.scope_digest,
    )


def test_negative_authority_record_id_is_deterministic() -> None:
    first = negative_authority_record()
    second = negative_authority_record()
    assert first.record_id == second.record_id
    assert first.record_sha256 == second.record_sha256


def test_negative_authority_record_rejects_other_decision() -> None:
    wire = negative_authority_record().to_wire()
    wire["decision"] = "UNRESOLVED_ANALYSIS"
    with pytest.raises(ValueError, match="decision"):
        NegativeRequirementAuthorityRecordV1.from_wire(wire)


def test_negative_authority_scope_digest_is_the_digest_of_the_closed_scope_wire() -> (
    None
):
    record = negative_authority_record()
    assert record.scope_digest == negative_authority_scope_digest(record.scope)


def test_negative_authority_record_digest_excludes_only_record_sha256() -> None:
    record = negative_authority_record()
    assert record.record_sha256 == negative_authority_record_sha256(record)


def test_negative_authority_record_rejects_arbitrary_scope_fields() -> None:
    wire = negative_authority_record().to_wire()
    wire["scope"]["source_fields"].append("arbitrary_expression")
    with pytest.raises(ValueError, match="source_fields"):
        NegativeRequirementAuthorityRecordV1.from_wire(wire)


@pytest.mark.parametrize(
    "field",
    [
        "authority_id",
        "authority_version",
        "record_id",
        "record_sha256",
        "scope_digest",
    ],
)
def test_card_reference_requires_exact_authority_record_binding(field: str) -> None:
    record = negative_authority_record()
    reference = authority_reference(record)
    replacement = {
        "authority_id": "other-authority",
        "authority_version": "2",
        "record_id": "nra_" + "f" * 64,
        "record_sha256": "f" * 64,
        "scope_digest": "f" * 64,
    }[field]
    with pytest.raises(ValueError, match=field):
        validate_negative_requirement_authority(
            record,
            replace(reference, **{field: replacement}),
            source_ref(),
        )


def test_card_reference_requires_exact_authority_source() -> None:
    record = negative_authority_record()
    with pytest.raises(ValueError, match="source"):
        validate_negative_requirement_authority(
            record,
            authority_reference(record),
            source_ref(oracle_id="abcdefab-abcd-4abc-8abc-abcdefabcdea"),
        )


def test_authority_wire_round_trips_without_digest_drift() -> None:
    record = negative_authority_record()
    round_tripped = NegativeRequirementAuthorityRecordV1.from_wire(
        copy.deepcopy(record.to_wire())
    )
    assert round_tripped == record


def test_negative_authority_schema_accepts_a_valid_record() -> None:
    validate_document(
        negative_authority_record().to_wire(),
        "negative-requirement-authority.v1.schema.json",
    )
