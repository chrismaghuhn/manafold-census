from dataclasses import FrozenInstanceError

import pytest

from manafold_census.canonical import MAX_INTEGER, MIN_INTEGER, canonical_json_bytes
from manafold_census.corpus.index import RecordIndexEntry
from manafold_census.digest import sha256_bytes
from manafold_census.structural.model import (
    StructuralCardRecordV1,
    StructuralFaceV1,
    StructuralRelatedPartV1,
)
from manafold_census.validation import SchemaValidationError, validate_document

ORACLE_ID = "00000000-0000-4000-8000-000000000000"
SOURCE_CARD_ID = "00000000-0000-4000-8000-000000000001"
RELATED_CARD_ID = "00000000-0000-4000-8000-000000000002"
SOURCE_RECORD_SHA256 = sha256_bytes(b"source-record\n")


def _related_part(
    *,
    component: str = "related",
    name: str = "Related",
    uri: str = "https://example.invalid/related",
) -> StructuralRelatedPartV1:
    return StructuralRelatedPartV1(
        component=component,
        id=RELATED_CARD_ID,
        name=name,
        object_kind="card",
        type_line="Related Type",
        uri=uri,
    )


def _face(
    face_index: int = 0,
    *,
    colors: list[str] | None = None,
) -> StructuralFaceV1:
    return StructuralFaceV1(
        face_index=face_index,
        name=f"Face {face_index}",
        mana_cost="{1}{G}",
        type_line="Creature",
        oracle_text="raw face text",
        colors=colors if colors is not None else ["G"],
        color_indicator=["G"],
        power="1+*",
        toughness="7-*",
        loyalty=None,
        defense=None,
    )


def _record(
    *,
    colors: list[str] | None = None,
    keywords: list[str] | None = None,
    faces: list[StructuralFaceV1] | None = None,
    all_parts: list[StructuralRelatedPartV1] | None = None,
    attraction_lights: list[int] | None = None,
) -> StructuralCardRecordV1:
    return StructuralCardRecordV1(
        oracle_id=ORACLE_ID,
        source_card_id=SOURCE_CARD_ID,
        source_record_sha256=SOURCE_RECORD_SHA256,
        name="Structural Card",
        layout="normal",
        mana_cost="{2}{U}",
        type_line="Creature",
        oracle_text="Draw two cards.",
        colors=colors if colors is not None else ["U"],
        color_identity=["U"],
        color_indicator=None,
        keywords=keywords if keywords is not None else ["Flying", "Ward"],
        produced_mana=None,
        power="*",
        toughness="1+*",
        loyalty=None,
        defense=None,
        hand_modifier=None,
        life_modifier=None,
        attraction_lights=attraction_lights,
        faces=faces,
        all_parts=all_parts,
    )


def test_structural_card_wire_has_exact_fixed_nested_shapes() -> None:
    record = _record(faces=[_face(0), _face(1)], all_parts=[_related_part()])

    assert set(record.to_wire()) == {
        "schema",
        "oracle_id",
        "source_card_id",
        "source_record_sha256",
        "name",
        "layout",
        "mana_cost",
        "type_line",
        "oracle_text",
        "colors",
        "color_identity",
        "color_indicator",
        "keywords",
        "produced_mana",
        "power",
        "toughness",
        "loyalty",
        "defense",
        "hand_modifier",
        "life_modifier",
        "attraction_lights",
        "faces",
        "all_parts",
    }
    assert record.to_wire()["schema"] == "census.structural-card.v1"
    assert set(record.to_wire()["faces"][0]) == {
        "face_index",
        "name",
        "mana_cost",
        "type_line",
        "oracle_text",
        "colors",
        "color_indicator",
        "power",
        "toughness",
        "loyalty",
        "defense",
    }
    assert set(record.to_wire()["all_parts"][0]) == {
        "component",
        "id",
        "name",
        "object",
        "type_line",
        "uri",
    }


def test_structural_card_round_trips_and_matches_json_schema() -> None:
    record = _record(faces=[_face(0)], all_parts=[_related_part()])
    wire = record.to_wire()

    validate_document(wire, "structural-card.v1.schema.json")

    assert StructuralCardRecordV1.from_wire(wire) == record


def test_nullable_fields_accept_none_as_structural_absence() -> None:
    record = StructuralCardRecordV1(
        oracle_id=ORACLE_ID,
        source_card_id=SOURCE_CARD_ID,
        source_record_sha256=SOURCE_RECORD_SHA256,
        name="Absent Values",
        layout="normal",
        mana_cost=None,
        type_line=None,
        oracle_text=None,
        colors=None,
        color_identity=None,
        color_indicator=None,
        keywords=None,
        produced_mana=None,
        power=None,
        toughness=None,
        loyalty=None,
        defense=None,
        hand_modifier=None,
        life_modifier=None,
        attraction_lights=None,
        faces=None,
        all_parts=None,
    )

    wire = record.to_wire()
    assert wire["oracle_text"] is None
    assert wire["faces"] is None
    validate_document(wire, "structural-card.v1.schema.json")


def test_empty_source_values_remain_empty_and_array_order_is_preserved() -> None:
    record = _record(colors=[], keywords=["Second", "First"])
    wire = record.to_wire()

    assert wire["colors"] == []
    assert wire["keywords"] == ["Second", "First"]


def test_model_rejects_empty_face_array() -> None:
    with pytest.raises(ValueError, match="faces"):
        _record(faces=[])


def test_model_defensively_copies_nested_mutable_inputs() -> None:
    colors = ["U"]
    keywords = ["First"]
    face_colors = ["G"]
    faces = [_face(colors=face_colors)]
    parts = [_related_part()]
    attraction_lights = [1, 5]
    record = _record(
        colors=colors,
        keywords=keywords,
        faces=faces,
        all_parts=parts,
        attraction_lights=attraction_lights,
    )
    before = canonical_json_bytes(record.to_wire())

    colors.append("R")
    keywords.clear()
    face_colors.append("B")
    faces.clear()
    parts.clear()
    attraction_lights.append(6)

    assert canonical_json_bytes(record.to_wire()) == before
    assert record.to_wire()["colors"] == ["U"]
    assert record.to_wire()["keywords"] == ["First"]
    assert record.to_wire()["faces"][0]["colors"] == ["G"]
    assert record.to_wire()["attraction_lights"] == [1, 5]


def test_model_defensively_copies_mutable_wire_output() -> None:
    record = _record(faces=[_face(0)], all_parts=[_related_part()])
    before = canonical_json_bytes(record.to_wire())
    wire = record.to_wire()

    wire["colors"].append("R")
    wire["faces"][0]["colors"].append("B")
    wire["all_parts"].clear()

    assert canonical_json_bytes(record.to_wire()) == before


def test_model_is_frozen() -> None:
    record = _record()

    with pytest.raises(FrozenInstanceError):
        record.name = "changed"  # type: ignore[misc]


def test_task01_identity_projection_uses_existing_record_index_entry() -> None:
    record = _record()

    assert record.task01_identity() == RecordIndexEntry(
        oracle_id=ORACLE_ID,
        source_card_id=SOURCE_CARD_ID,
        name="Structural Card",
        source_record_sha256=SOURCE_RECORD_SHA256,
    )


def test_model_rejects_unknown_wire_properties() -> None:
    wire = _record().to_wire()
    wire["unexpected"] = "rejected"

    with pytest.raises((TypeError, ValueError), match="unexpected"):
        StructuralCardRecordV1.from_wire(wire)

    with pytest.raises(SchemaValidationError, match="additional properties"):
        validate_document(wire, "structural-card.v1.schema.json")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("oracle_text", 7),
        ("colors", ["U", 7]),
        ("attraction_lights", [1, True]),
    ],
)
def test_model_rejects_invalid_parent_field_types(field: str, value: object) -> None:
    wire = _record().to_wire()
    wire[field] = value

    with pytest.raises((TypeError, ValueError), match=field):
        StructuralCardRecordV1.from_wire(wire)


def test_model_rejects_invalid_face_and_related_part_types() -> None:
    face_wire = _face().to_wire()
    face_wire["face_index"] = -1
    with pytest.raises((TypeError, ValueError), match="face_index"):
        StructuralFaceV1.from_wire(face_wire)

    related_wire = _related_part().to_wire()
    related_wire["uri"] = 3
    with pytest.raises((TypeError, ValueError), match="uri"):
        StructuralRelatedPartV1.from_wire(related_wire)


def test_model_rejects_signed_64_bit_overflow_and_accepts_boundaries() -> None:
    maximum_face = _face(face_index=MAX_INTEGER)
    boundary_record = _record(attraction_lights=[MIN_INTEGER, MAX_INTEGER])

    assert maximum_face.face_index == MAX_INTEGER
    assert boundary_record.attraction_lights == (MIN_INTEGER, MAX_INTEGER)

    with pytest.raises(ValueError, match="signed 64-bit"):
        StructuralFaceV1(
            face_index=MAX_INTEGER + 1,
            name="Overflow",
            mana_cost=None,
            type_line=None,
            oracle_text=None,
            colors=None,
            color_indicator=None,
            power=None,
            toughness=None,
            loyalty=None,
            defense=None,
        )

    with pytest.raises(ValueError, match="signed 64-bit"):
        _record(attraction_lights=[MIN_INTEGER - 1])
