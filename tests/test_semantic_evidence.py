from dataclasses import FrozenInstanceError

import pytest

from manafold_census.semantic.evidence import (
    EvidenceKindV1,
    ExternalReviewEvidenceV1,
    RulesCitationEvidenceV1,
    SourceRecordRefV1,
    StructuralFaceEvidenceV1,
    StructuralFieldEvidenceV1,
    StructuralKeywordEvidenceV1,
    StructuralRecordEvidenceV1,
    evidence_from_wire,
    evidence_sort_key,
    evidence_to_wire,
)

ORACLE_ID = "abcdefab-abcd-4abc-8abc-abcdefabcdef"
SOURCE_CARD_ID = "abcdefab-abcd-4abc-8abc-abcdefabcdea"
SOURCE_LOCK_DIGEST = "a" * 64
SOURCE_RECORD_SHA256 = "b" * 64


def _source() -> SourceRecordRefV1:
    return SourceRecordRefV1(
        record_schema="census.structural-card.v1",
        source_lock_digest=SOURCE_LOCK_DIGEST,
        oracle_id=ORACLE_ID,
        source_card_id=SOURCE_CARD_ID,
        source_record_sha256=SOURCE_RECORD_SHA256,
    )


def test_source_record_reference_has_exact_wire_shape_and_round_trips() -> None:
    source = _source()

    assert source.to_wire() == {
        "record_schema": "census.structural-card.v1",
        "source_lock_digest": SOURCE_LOCK_DIGEST,
        "oracle_id": ORACLE_ID,
        "source_card_id": SOURCE_CARD_ID,
        "source_record_sha256": SOURCE_RECORD_SHA256,
    }
    assert SourceRecordRefV1.from_wire(source.to_wire()) == source
    with pytest.raises(FrozenInstanceError):
        source.oracle_id = SOURCE_CARD_ID  # type: ignore[misc]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("record_schema", "wrong.schema.v1"),
        ("source_lock_digest", "A" * 64),
        ("oracle_id", ORACLE_ID.upper()),
        ("source_card_id", "not-a-uuid"),
        ("source_record_sha256", "not-a-digest"),
    ],
)
def test_source_reference_rejects_invalid_identity(field: str, value: str) -> None:
    wire = _source().to_wire()
    wire[field] = value

    with pytest.raises((TypeError, ValueError), match=field.split("_")[0]):
        SourceRecordRefV1.from_wire(wire)


def test_structural_record_and_face_evidence_round_trip() -> None:
    values = (
        StructuralRecordEvidenceV1(_source()),
        StructuralFaceEvidenceV1(_source(), 1),
    )

    for evidence in values:
        assert evidence_from_wire(evidence_to_wire(evidence)) == evidence

    assert values[0].to_wire() == {
        "kind": "STRUCTURAL_RECORD",
        "source": _source().to_wire(),
    }
    assert values[1].to_wire()["face_index"] == 1


def test_structural_field_evidence_enforces_parent_and_face_field_vocabulary() -> None:
    parent = StructuralFieldEvidenceV1(
        source=_source(),
        field="oracle_text",
        face_index=None,
        fragment="Draw two cards.",
    )
    face = StructuralFieldEvidenceV1(
        source=_source(),
        field="oracle_text",
        face_index=0,
        fragment="Face text.",
    )

    assert evidence_from_wire(parent.to_wire()) == parent
    assert evidence_from_wire(face.to_wire()) == face

    with pytest.raises(ValueError, match="face"):
        StructuralFieldEvidenceV1(_source(), "keywords", 0, "Flying")
    with pytest.raises(ValueError, match="field"):
        StructuralFieldEvidenceV1(_source(), "not_m1_field", None, None)
    with pytest.raises(ValueError, match="field"):
        StructuralFieldEvidenceV1(_source(), "record", None, None)
    with pytest.raises(ValueError, match="non-negative"):
        StructuralFieldEvidenceV1(_source(), "oracle_text", -1, None)
    with pytest.raises(ValueError, match="4096"):
        StructuralFieldEvidenceV1(_source(), "oracle_text", None, "x" * 4097)

    for field in ("colors", "keywords", "faces", "all_parts"):
        with pytest.raises(ValueError, match="textual"):
            StructuralFieldEvidenceV1(_source(), field, None, "fragment")


def test_keyword_evidence_is_parent_level_and_preserves_exact_value() -> None:
    evidence = StructuralKeywordEvidenceV1(
        source=_source(),
        keyword_index=2,
        keyword_value="Flying",
    )

    assert evidence_from_wire(evidence.to_wire()) == evidence
    empty = StructuralKeywordEvidenceV1(_source(), 0, "")
    assert evidence_from_wire(empty.to_wire()) == empty
    with pytest.raises(ValueError, match="non-negative"):
        StructuralKeywordEvidenceV1(_source(), -1, "Flying")


def test_rules_and_external_review_evidence_remain_distinct() -> None:
    rules = RulesCitationEvidenceV1(
        ruleset_id="magic-comprehensive-rules",
        ruleset_version="2026-09-12",
        rule_id="701.5",
        rules_artifact_sha256=None,
    )
    external = ExternalReviewEvidenceV1(
        authority_id="review-authority",
        authority_version="v1",
        record_id="review-1",
        record_sha256="c" * 64,
    )

    assert evidence_from_wire(rules.to_wire()) == rules
    assert evidence_from_wire(external.to_wire()) == external
    assert rules.to_wire()["kind"] == "RULES_CITATION"
    assert external.to_wire()["kind"] == "EXTERNAL_REVIEW"

    long_ruleset = RulesCitationEvidenceV1("r" * 4097, "v1", "rule", None)
    assert long_ruleset.ruleset_id == "r" * 4097


def test_evidence_kind_vocabulary_is_exact() -> None:
    assert {kind.value for kind in EvidenceKindV1} == {
        "STRUCTURAL_RECORD",
        "STRUCTURAL_FACE",
        "STRUCTURAL_FIELD",
        "STRUCTURAL_KEYWORD",
        "RULES_CITATION",
        "EXTERNAL_REVIEW",
    }


@pytest.mark.parametrize(
    ("evidence", "expected_kind"),
    [
        (StructuralRecordEvidenceV1(_source()), EvidenceKindV1.STRUCTURAL_RECORD),
        (StructuralFaceEvidenceV1(_source(), 0), EvidenceKindV1.STRUCTURAL_FACE),
        (
            StructuralFieldEvidenceV1(_source(), "oracle_text", None, None),
            EvidenceKindV1.STRUCTURAL_FIELD,
        ),
        (
            StructuralKeywordEvidenceV1(_source(), 0, "Flying"),
            EvidenceKindV1.STRUCTURAL_KEYWORD,
        ),
        (
            RulesCitationEvidenceV1("rules", "v1", "701.5", None),
            EvidenceKindV1.RULES_CITATION,
        ),
        (
            ExternalReviewEvidenceV1("authority", "v1", "record", "c" * 64),
            EvidenceKindV1.EXTERNAL_REVIEW,
        ),
    ],
)
def test_each_evidence_variant_exposes_its_public_kind(
    evidence: object, expected_kind: EvidenceKindV1
) -> None:
    assert evidence.kind == expected_kind  # type: ignore[attr-defined]
    assert evidence.to_wire()["kind"] == expected_kind.value  # type: ignore[attr-defined]


def test_evidence_digest_ordering_is_deterministic_and_fresh() -> None:
    first = StructuralFieldEvidenceV1(_source(), "oracle_text", None, "text")
    second = StructuralFieldEvidenceV1(_source(), "type_line", None, None)

    assert evidence_sort_key(first) == evidence_sort_key(first)
    assert evidence_sort_key(first) != evidence_sort_key(second)
    assert first.source == second.source
    wire = evidence_to_wire(first)
    wire["source"]["oracle_id"] = SOURCE_CARD_ID  # type: ignore[index]
    assert evidence_to_wire(first)["source"]["oracle_id"] == ORACLE_ID  # type: ignore[index]


def test_evidence_wire_rejects_unknown_kind_and_properties() -> None:
    wire = StructuralRecordEvidenceV1(_source()).to_wire()
    wire["kind"] = "NOT_A_KIND"
    with pytest.raises(ValueError, match="kind"):
        evidence_from_wire(wire)

    wire = StructuralRecordEvidenceV1(_source()).to_wire()
    wire["extra"] = True
    with pytest.raises((TypeError, ValueError), match="extra|unexpected"):
        evidence_from_wire(wire)


def test_evidence_from_wire_rejects_internal_model_and_tuple_values() -> None:
    wire = StructuralRecordEvidenceV1(_source()).to_wire()
    wire["source"] = _source()  # type: ignore[assignment]
    with pytest.raises(TypeError, match="JSON|unsupported"):
        evidence_from_wire(wire)

    wire = StructuralFieldEvidenceV1(_source(), "oracle_text", None, None).to_wire()
    wire["source"] = (SOURCE_LOCK_DIGEST,)  # type: ignore[assignment]
    with pytest.raises(TypeError, match="JSON|tuple|unsupported"):
        evidence_from_wire(wire)
