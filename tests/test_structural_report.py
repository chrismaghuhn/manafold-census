import pytest

from manafold_census.canonical import MAX_INTEGER
from manafold_census.structural.model import StructuralCardRecordV1, StructuralFaceV1
from manafold_census.structural.report import (
    FACE_PRESENCE_FIELDS,
    TOP_LEVEL_PRESENCE_FIELDS,
    collect_structural_statistics,
)
from manafold_census.validation import SchemaValidationError, validate_document

ORACLE_ID = "abcdefab-abcd-4abc-8abc-abcdefabcdef"
SOURCE_CARD_ID = "abcdefab-abcd-4abc-8abc-abcdefabcdea"
SOURCE_RECORD_SHA256 = "a" * 64
SHARD_COUNTS = {shard: 0 for shard in "0123456789abcdef"}


def _shard_counts(record_count: int) -> dict[str, int]:
    counts = dict(SHARD_COUNTS)
    counts["a"] = record_count
    return counts


def _face(
    face_index: int = 0,
    *,
    oracle_text: str | None = "face text",
    colors: tuple[str, ...] | None = ("G",),
) -> StructuralFaceV1:
    return StructuralFaceV1(
        face_index=face_index,
        name=f"Face {face_index}",
        mana_cost="{G}",
        type_line="Creature",
        oracle_text=oracle_text,
        colors=colors,
        color_indicator=(),
        power="1",
        toughness="1",
        loyalty=None,
        defense=None,
    )


def _record(
    *,
    oracle_id: str = ORACLE_ID,
    layout: str = "normal",
    oracle_text: str | None = "parent text",
    colors: tuple[str, ...] | None = ("G",),
    color_identity: tuple[str, ...] | None = ("G",),
    color_indicator: tuple[str, ...] | None = (),
    keywords: tuple[str, ...] | None = ("Flying",),
    produced_mana: tuple[str, ...] | None = None,
    attraction_lights: tuple[int, ...] | None = None,
    faces: tuple[StructuralFaceV1, ...] | None = None,
    all_parts: tuple[object, ...] | None = None,
) -> StructuralCardRecordV1:
    return StructuralCardRecordV1(
        oracle_id=oracle_id,
        source_card_id=SOURCE_CARD_ID,
        source_record_sha256=SOURCE_RECORD_SHA256,
        name="Report Card",
        layout=layout,
        mana_cost="{G}",
        type_line="Creature",
        oracle_text=oracle_text,
        colors=colors,
        color_identity=color_identity,
        color_indicator=color_indicator,
        keywords=keywords,
        produced_mana=produced_mana,
        power="1",
        toughness="1",
        loyalty=None,
        defense=None,
        hand_modifier=None,
        life_modifier=None,
        attraction_lights=attraction_lights,
        faces=faces,
        all_parts=all_parts,  # type: ignore[arg-type]
    )


def _valid_report() -> dict[str, object]:
    top_level = {field: 0 for field in TOP_LEVEL_PRESENCE_FIELDS}
    face_level = {field: 0 for field in FACE_PRESENCE_FIELDS}
    return {
        "schema": "census.structural-card-report.v1",
        "record_provenance": "SOURCE_FACT",
        "source_lock_digest": "a" * 64,
        "source_id": "source-id",
        "source_locator": "https://example.invalid/source",
        "source_artifact_sha256": "b" * 64,
        "source_artifact_byte_length": 0,
        "source_media_type": "application/gzip",
        "task01_record_identity_parity": True,
        "task01_identity_count": 0,
        "structural_record_count": 0,
        "unique_oracle_id_count": 0,
        "duplicate_oracle_id_count": 0,
        "missing_oracle_id_count": 0,
        "extra_oracle_id_count": 0,
        "cards_with_faces": 0,
        "cards_without_faces": 0,
        "total_face_count": 0,
        "max_face_count": 0,
        "face_count_distribution": {},
        "layout_counts": {},
        "top_level_field_presence": top_level,
        "face_field_presence": face_level,
        "shard_count": 16,
        "shard_record_counts": dict(SHARD_COUNTS),
        "structural_index_aggregate_digest": "c" * 64,
        "structural_index_manifest_sha256": "d" * 64,
        "structural_index_manifest_byte_length": 0,
        "dataset_manifest_digest": "e" * 64,
        "study_digest": "f" * 64,
        "artifact_manifest_digest": "0" * 64,
    }


def test_report_schema_has_exact_fixed_identity_and_maps() -> None:
    document = _valid_report()

    validate_document(document, "structural-card-report.v1.schema.json")

    assert set(document["top_level_field_presence"]) == set(TOP_LEVEL_PRESENCE_FIELDS)
    assert set(document["face_field_presence"]) == set(FACE_PRESENCE_FIELDS)
    assert set(document["shard_record_counts"]) == set(SHARD_COUNTS)


def test_presence_counts_source_membership_not_truthiness() -> None:
    record = _record(
        oracle_text="",
        colors=(),
        color_indicator=(),
        keywords=(),
        produced_mana=(),
        attraction_lights=(),
        faces=(_face(oracle_text="", colors=()),),
        all_parts=(),
    )

    statistics = collect_structural_statistics(
        [record], _shard_counts(1), task01_identity_parity=True, task01_identity_count=1
    )

    assert statistics.top_level_field_presence["oracle_text"] == 1
    assert statistics.top_level_field_presence["colors"] == 1
    assert statistics.top_level_field_presence["produced_mana"] == 1
    assert statistics.top_level_field_presence["all_parts"] == 1
    assert statistics.face_field_presence["oracle_text"] == 1
    assert statistics.face_field_presence["colors"] == 1
    assert statistics.cards_with_faces == 1
    assert statistics.cards_without_faces == 0
    assert statistics.total_face_count == 1
    assert statistics.max_face_count == 1
    assert statistics.face_count_distribution == {"1": 1}
    assert "0" not in statistics.face_count_distribution


def test_missing_faces_create_no_zero_bucket_and_maximum_is_zero() -> None:
    statistics = collect_structural_statistics(
        [_record(oracle_text=None, colors=None)],
        _shard_counts(1),
        task01_identity_parity=True,
        task01_identity_count=1,
    )

    assert statistics.cards_with_faces == 0
    assert statistics.cards_without_faces == 1
    assert statistics.total_face_count == 0
    assert statistics.max_face_count == 0
    assert statistics.face_count_distribution == {}


def test_face_count_distribution_counts_only_present_face_arrays() -> None:
    records = [
        _record(oracle_id=ORACLE_ID, faces=(_face(0), _face(1))),
        _record(
            oracle_id="abcdefab-abcd-4abc-8abc-abcdefabcdec",
            faces=(_face(0), _face(1), _face(2)),
        ),
        _record(
            oracle_id="abcdefab-abcd-4abc-8abc-abcdefabcded",
            faces=None,
        ),
    ]

    statistics = collect_structural_statistics(
        records, _shard_counts(3), task01_identity_parity=True, task01_identity_count=3
    )

    assert statistics.face_count_distribution == {"2": 1, "3": 1}
    assert statistics.total_face_count == 5
    assert statistics.max_face_count == 3


def test_statistics_count_duplicate_records_and_layouts() -> None:
    records = [_record(layout="normal"), _record(layout="normal")]

    statistics = collect_structural_statistics(
        records, _shard_counts(2), task01_identity_parity=False, task01_identity_count=2
    )

    assert statistics.record_count == 2
    assert statistics.unique_oracle_id_count == 1
    assert statistics.duplicate_oracle_id_count == 1
    assert statistics.layout_counts == {"normal": 2}


def test_statistics_reject_invalid_fixed_map_or_parity_values() -> None:
    with pytest.raises((TypeError, ValueError), match="task01_record_identity_parity"):
        collect_structural_statistics(
            [],
            SHARD_COUNTS,
            task01_identity_parity=1,
            task01_identity_count=0,  # type: ignore[arg-type]
        )

    invalid_shards = dict(SHARD_COUNTS)
    invalid_shards.pop("f")
    with pytest.raises(ValueError, match="shard_record_counts"):
        collect_structural_statistics(
            [], invalid_shards, task01_identity_parity=True, task01_identity_count=0
        )


def test_report_schema_rejects_unknown_fixed_keys_and_zero_face_bucket() -> None:
    unknown = _valid_report()
    unknown["unexpected"] = True
    with pytest.raises(SchemaValidationError, match="additional properties"):
        validate_document(unknown, "structural-card-report.v1.schema.json")

    zero_bucket = _valid_report()
    zero_bucket["face_count_distribution"] = {"0": 1}
    with pytest.raises(SchemaValidationError):
        validate_document(zero_bucket, "structural-card-report.v1.schema.json")


@pytest.mark.parametrize(
    "mutation",
    [
        lambda document: document.pop("face_field_presence"),
        lambda document: document["face_field_presence"].update({"extra": 1}),
        lambda document: document["shard_record_counts"].update({"g": 1}),
        lambda document: document.update({"task01_record_identity_parity": "true"}),
        lambda document: document.update({"structural_record_count": -1}),
        lambda document: document.update({"structural_record_count": MAX_INTEGER + 1}),
    ],
)
def test_report_schema_rejects_contract_mutations(mutation) -> None:
    document = _valid_report()
    mutation(document)

    with pytest.raises(SchemaValidationError):
        validate_document(document, "structural-card-report.v1.schema.json")
