from dataclasses import replace

import pytest

from manafold_census.semantic.bundle import RequirementBundleV1
from manafold_census.semantic.evidence import (
    SourceRecordRefV1,
    StructuralFaceEvidenceV1,
    StructuralFieldEvidenceV1,
    StructuralKeywordEvidenceV1,
    StructuralRecordEvidenceV1,
)
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
from manafold_census.semantic.validate import (
    validate_bundle_against_structural_record,
    validate_requirement_against_structural_record,
)
from manafold_census.structural.model import (
    StructuralCardRecordV1,
    StructuralFaceV1,
)

SOURCE_LOCK = "a" * 64
ORACLE_ID = "abcdefab-abcd-4abc-8abc-abcdefabcdef"
SOURCE_CARD_ID = "abcdefab-abcd-4abc-8abc-abcdefabcdea"
RECORD_SHA = "b" * 64


def _record(
    *, faces: tuple[StructuralFaceV1, ...] | None = None
) -> StructuralCardRecordV1:
    return StructuralCardRecordV1(
        oracle_id=ORACLE_ID,
        source_card_id=SOURCE_CARD_ID,
        source_record_sha256=RECORD_SHA,
        name="Fixture Card",
        layout="normal",
        mana_cost="{1}{U}",
        type_line="Creature",
        oracle_text="Draw two cards.",
        colors=("U",),
        color_identity=("U",),
        color_indicator=None,
        keywords=("Flying", "Ward"),
        produced_mana=None,
        power="2",
        toughness="2",
        loyalty=None,
        defense=None,
        hand_modifier=None,
        life_modifier=None,
        attraction_lights=None,
        faces=faces,
        all_parts=None,
    )


def _face() -> StructuralFaceV1:
    return StructuralFaceV1(
        face_index=0,
        name="Fixture Face",
        mana_cost="{U}",
        type_line="Creature",
        oracle_text="Face text.",
        colors=("U",),
        color_indicator=None,
        power="1",
        toughness="1",
        loyalty=None,
        defense=None,
    )


def _source(record: StructuralCardRecordV1) -> SourceRecordRefV1:
    return SourceRecordRefV1(
        record_schema="census.structural-card.v1",
        source_lock_digest=SOURCE_LOCK,
        oracle_id=record.oracle_id,
        source_card_id=record.source_card_id,
        source_record_sha256=record.source_record_sha256,
    )


def _requirement(
    record: StructuralCardRecordV1,
    evidence: tuple[object, ...],
    *,
    source: SourceRecordRefV1 | None = None,
) -> RequirementV1:
    source = source or _source(record)
    return RequirementV1.create(
        source=source,
        family=RequirementFamilyV1.EFFECT,
        kind=RequirementKindV1.DRAW_CARDS,
        parameters=DrawCardsParametersV1(
            EntityRefV1(EntityRoleV1.SOURCE, MultiplicityV1.ONE, None),
            QuantityV1(QuantityModeV1.EXACT, 2),
        ),
        evidence=evidence,  # type: ignore[arg-type]
        provenance=ProvenanceV1(
            (DerivationV1(DerivationMethodV1.PARSER, "fixture-parser", "1"),)
        ),
        review=ReviewV1(ReviewStatusV1.PROPOSED, None, None),
        resolution=ResolutionV1(
            ResolutionStateV1.COMPLETE, ResolutionReasonV1.NONE, ()
        ),
    )


def test_validates_record_face_field_keyword_and_fragment_evidence() -> None:
    record = _record(faces=(_face(),))
    source = _source(record)
    requirement = _requirement(
        record,
        (
            StructuralRecordEvidenceV1(source),
            StructuralFaceEvidenceV1(source, 0),
            StructuralFieldEvidenceV1(source, "oracle_text", None, "Draw"),
            StructuralFieldEvidenceV1(source, "oracle_text", 0, "Face"),
            StructuralKeywordEvidenceV1(source, 0, "Flying"),
        ),
    )

    validate_requirement_against_structural_record(requirement, record, SOURCE_LOCK)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_lock_digest", "c" * 64),
        ("oracle_id", "abcdefab-abcd-4abc-8abc-abcdefabcdec"),
        ("source_card_id", "abcdefab-abcd-4abc-8abc-abcdefabcdeb"),
        ("source_record_sha256", "d" * 64),
    ],
)
def test_rejects_wrong_source_lock_or_record_identity(field: str, value: str) -> None:
    record = _record()
    source = replace(_source(record), **{field: value})
    requirement = _requirement(
        record, (StructuralRecordEvidenceV1(source),), source=source
    )

    with pytest.raises(ValueError, match="source|identity|digest"):
        validate_requirement_against_structural_record(requirement, record, SOURCE_LOCK)


def test_rejects_expected_lock_mismatch() -> None:
    record = _record()
    requirement = _requirement(record, (StructuralRecordEvidenceV1(_source(record)),))

    with pytest.raises(ValueError, match="source lock"):
        validate_requirement_against_structural_record(requirement, record, "c" * 64)


@pytest.mark.parametrize(
    "evidence",
    [
        lambda source: StructuralFaceEvidenceV1(source, 1),
        lambda source: StructuralFieldEvidenceV1(
            source, "oracle_text", None, "missing"
        ),
        lambda source: StructuralKeywordEvidenceV1(source, 1, "Wrong"),
    ],
)
def test_rejects_invalid_face_field_keyword_and_fragment_references(evidence) -> None:
    record = _record(faces=(_face(),))
    source = _source(record)
    requirement = _requirement(record, (evidence(source),))

    with pytest.raises(ValueError, match="face|field|keyword|fragment"):
        validate_requirement_against_structural_record(requirement, record, SOURCE_LOCK)


def test_rejects_missing_face_and_bundle_cross_source_closure() -> None:
    no_faces = _record()
    source = _source(no_faces)
    face_requirement = _requirement(no_faces, (StructuralFaceEvidenceV1(source, 0),))
    with pytest.raises(ValueError, match="face"):
        validate_requirement_against_structural_record(
            face_requirement, no_faces, SOURCE_LOCK
        )

    first = _record()
    second = replace(_record(), source_card_id="abcdefab-abcd-4abc-8abc-abcdefabcdeb")
    first_requirement = _requirement(
        first, (StructuralRecordEvidenceV1(_source(first)),)
    )
    bundle = RequirementBundleV1(_source(first), (first_requirement,), ())
    with pytest.raises(ValueError, match="source"):
        validate_bundle_against_structural_record(bundle, second, SOURCE_LOCK)
