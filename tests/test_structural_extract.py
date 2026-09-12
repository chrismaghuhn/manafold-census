import gzip
import json
from pathlib import Path

import pytest

from manafold_census.corpus.index import parse_source_record
from manafold_census.digest import sha256_bytes
from manafold_census.structural.extract import (
    StructuralExtractionError,
    iter_structural_records,
    parse_structural_source_record,
)

ORACLE_ID = "abcdefab-abcd-4abc-8abc-abcdefabcdef"
SOURCE_CARD_ID = "abcdefab-abcd-4abc-8abc-abcdefabcdea"
RELATED_CARD_ID = "abcdefab-abcd-4abc-8abc-abcdefabcdeb"


def _source_record() -> dict[str, object]:
    return {
        "object": "card",
        "oracle_id": ORACLE_ID,
        "id": SOURCE_CARD_ID,
        "name": "Source Card",
        "layout": "normal",
    }


def _raw_line(record: dict[str, object]) -> bytes:
    return (
        json.dumps(record, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        + b"\n"
    )


def _face(name: str, **overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "name": name,
        "mana_cost": "{1}{G}",
        "type_line": "Creature",
        "oracle_text": f"{name} face text",
        "colors": ["G"],
        "color_indicator": ["G"],
        "power": "1+*",
        "toughness": "7-*",
    }
    value.update(overrides)
    return value


def _related(name: str, component: str) -> dict[str, object]:
    return {
        "component": component,
        "id": RELATED_CARD_ID,
        "name": name,
        "object": "card",
        "type_line": "Related Type",
        "uri": f"https://example.invalid/{component}",
    }


def test_absent_fields_become_none_and_identity_hash_matches_task01() -> None:
    raw_line = _raw_line(_source_record())

    structural = parse_structural_source_record(raw_line, 1)
    task01 = parse_source_record(raw_line, 1)

    assert structural.task01_identity() == task01
    assert structural.source_record_sha256 == sha256_bytes(raw_line)
    assert structural.mana_cost is None
    assert structural.oracle_text is None
    assert structural.colors is None
    assert structural.faces is None
    assert structural.all_parts is None


def test_parent_raw_values_and_array_order_are_preserved() -> None:
    source = _source_record()
    source.update(
        {
            "mana_cost": "{2}{U}",
            "type_line": "Creature",
            "oracle_text": "line one\nline two",
            "colors": ["U", "G"],
            "color_identity": ["G", "U"],
            "color_indicator": [],
            "keywords": ["Second", "First"],
            "produced_mana": [],
            "power": "1+*",
            "toughness": "7-*",
            "loyalty": "3",
            "defense": "*",
            "hand_modifier": "-1",
            "life_modifier": "+2",
            "attraction_lights": [5, 1],
            "ignored_printing_field": {"artist": "not retained"},
        }
    )

    structural = parse_structural_source_record(_raw_line(source), 1)

    assert structural.mana_cost == "{2}{U}"
    assert structural.oracle_text == "line one\nline two"
    assert structural.colors == ("U", "G")
    assert structural.color_identity == ("G", "U")
    assert structural.color_indicator == ()
    assert structural.keywords == ("Second", "First")
    assert structural.produced_mana == ()
    assert structural.attraction_lights == (5, 1)


def test_faces_preserve_order_and_do_not_inherit_parent_fields() -> None:
    source = _source_record()
    source.update(
        {
            "oracle_text": "parent-only text",
            "colors": ["U"],
            "card_faces": [
                _face(
                    "Front",
                    oracle_text=None,
                    colors=[],
                    color_indicator=[],
                ),
                _face("Back", oracle_text="back-only text", colors=["G"]),
            ],
        }
    )
    source["card_faces"][0].pop("oracle_text")  # type: ignore[union-attr]

    structural = parse_structural_source_record(_raw_line(source), 1)

    assert structural.faces is not None
    assert [face.face_index for face in structural.faces] == [0, 1]
    assert [face.name for face in structural.faces] == ["Front", "Back"]
    assert structural.faces[0].oracle_text is None
    assert structural.faces[0].colors == ()
    assert structural.faces[1].oracle_text == "back-only text"
    assert structural.faces[1].colors == ("G",)
    assert structural.oracle_text == "parent-only text"
    assert structural.colors == ("U",)


def test_related_parts_preserve_order_and_opaque_uris() -> None:
    source = _source_record()
    source["all_parts"] = [
        _related("First Related", "first"),
        _related("Second Related", "second"),
    ]

    structural = parse_structural_source_record(_raw_line(source), 1)

    assert structural.all_parts is not None
    assert [part.component for part in structural.all_parts] == ["first", "second"]
    assert [part.name for part in structural.all_parts] == [
        "First Related",
        "Second Related",
    ]
    assert [part.uri for part in structural.all_parts] == [
        "https://example.invalid/first",
        "https://example.invalid/second",
    ]


@pytest.mark.parametrize(
    "field",
    [
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
        "card_faces",
        "all_parts",
    ],
)
def test_explicit_parent_source_null_fails(field: str) -> None:
    source = _source_record()
    source[field] = None

    with pytest.raises(StructuralExtractionError, match="explicit source null"):
        parse_structural_source_record(_raw_line(source), 1)


def test_explicit_face_source_null_fails() -> None:
    source = _source_record()
    source["card_faces"] = [_face("Front", oracle_text=None)]

    with pytest.raises(StructuralExtractionError, match="explicit source null"):
        parse_structural_source_record(_raw_line(source), 1)


def test_explicit_related_part_source_null_fails() -> None:
    source = _source_record()
    related = _related("Related", "related")
    related["uri"] = None
    source["all_parts"] = [related]

    with pytest.raises(StructuralExtractionError, match="explicit source null"):
        parse_structural_source_record(_raw_line(source), 1)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("layout", ""),
        ("layout", 4),
        ("colors", ["U", 4]),
        ("keywords", "Flying"),
        ("attraction_lights", [1, True]),
        ("card_faces", "not-an-array"),
        ("all_parts", "not-an-array"),
    ],
)
def test_invalid_parent_shapes_fail_closed(field: str, value: object) -> None:
    source = _source_record()
    source[field] = value

    with pytest.raises(StructuralExtractionError):
        parse_structural_source_record(_raw_line(source), 1)


@pytest.mark.parametrize(
    "faces",
    [
        [],
        ["not-an-object"],
        [{"type_line": "Missing name"}],
        [_face("", oracle_text="text")],
        [_face("Front", colors="not-an-array")],
    ],
)
def test_invalid_face_shapes_fail_closed(faces: list[object]) -> None:
    source = _source_record()
    source["card_faces"] = faces

    with pytest.raises(StructuralExtractionError):
        parse_structural_source_record(_raw_line(source), 1)


@pytest.mark.parametrize(
    "parts",
    [
        [{}],
        [{"component": "only-component"}],
        [{**_related("Related", "related"), "uri": 4}],
    ],
)
def test_invalid_related_part_shapes_fail_closed(parts: list[object]) -> None:
    source = _source_record()
    source["all_parts"] = parts

    with pytest.raises(StructuralExtractionError):
        parse_structural_source_record(_raw_line(source), 1)


def test_iter_structural_records_streams_gzip_jsonl(tmp_path: Path) -> None:
    source_path = tmp_path / "source.jsonl.gz"
    first = _source_record()
    second = {**_source_record(), "oracle_id": "abcdefab-abcd-4abc-8abc-abcdefabcdec"}
    with gzip.open(source_path, "wb") as stream:
        stream.write(_raw_line(first))
        stream.write(_raw_line(second))

    records = list(iter_structural_records(source_path))

    assert len(records) == 2
    assert records[0].oracle_id == ORACLE_ID
    assert records[1].oracle_id == second["oracle_id"]
