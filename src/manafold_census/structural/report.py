"""Pure structural statistics for the M1 report contract."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from re import fullmatch
from types import MappingProxyType

from ..canonical import MAX_INTEGER
from .index import SHARD_NAMES
from .model import StructuralCardRecordV1

REPORT_SCHEMA = "census.structural-card-report.v1"
REPORT_SCHEMA_PATH = "schemas/structural-card-report.v1.schema.json"
REPORT_PROVENANCE = "SOURCE_FACT"

TOP_LEVEL_PRESENCE_FIELDS = (
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
)
FACE_PRESENCE_FIELDS = (
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
)


def _require_count(field: str, value: object) -> int:
    if type(value) is not int:
        raise TypeError(f"{field} must be an integer")
    if value < 0 or value > MAX_INTEGER:
        raise ValueError(f"{field} is outside the signed 64-bit range")
    return value


def _freeze_fixed_counts(
    field: str, values: Mapping[str, int], expected_keys: tuple[str, ...]
) -> Mapping[str, int]:
    if set(values) != set(expected_keys):
        raise ValueError(f"{field} must contain exactly the frozen keys")
    frozen = {
        key: _require_count(f"{field}.{key}", values[key]) for key in expected_keys
    }
    return MappingProxyType(frozen)


def _freeze_face_counts(values: Mapping[str, int]) -> Mapping[str, int]:
    frozen: dict[str, int] = {}
    for key, value in values.items():
        if fullmatch(r"[1-9][0-9]*", key) is None:
            raise ValueError("face_count_distribution keys must be positive decimals")
        frozen[key] = _require_count(f"face_count_distribution.{key}", value)
    return MappingProxyType(frozen)


def _freeze_layout_counts(values: Mapping[str, int]) -> Mapping[str, int]:
    frozen: dict[str, int] = {}
    for key, value in values.items():
        if not isinstance(key, str) or key == "":
            raise ValueError("layout_counts keys must be non-empty strings")
        frozen[key] = _require_count(f"layout_counts.{key}", value)
    return MappingProxyType(frozen)


@dataclass(frozen=True, slots=True)
class StructuralStatistics:
    """Deterministic source-presence statistics for structural records."""

    record_count: int
    unique_oracle_id_count: int
    duplicate_oracle_id_count: int
    cards_with_faces: int
    cards_without_faces: int
    total_face_count: int
    max_face_count: int
    face_count_distribution: Mapping[str, int]
    layout_counts: Mapping[str, int]
    top_level_field_presence: Mapping[str, int]
    face_field_presence: Mapping[str, int]
    shard_record_counts: Mapping[str, int]
    task01_record_identity_parity: bool
    task01_identity_count: int

    def __post_init__(self) -> None:
        for field in (
            "record_count",
            "unique_oracle_id_count",
            "duplicate_oracle_id_count",
            "cards_with_faces",
            "cards_without_faces",
            "total_face_count",
            "max_face_count",
            "task01_identity_count",
        ):
            object.__setattr__(self, field, _require_count(field, getattr(self, field)))
        if type(self.task01_record_identity_parity) is not bool:
            raise TypeError("task01_record_identity_parity must be a boolean")
        object.__setattr__(
            self,
            "face_count_distribution",
            _freeze_face_counts(self.face_count_distribution),
        )
        object.__setattr__(
            self, "layout_counts", _freeze_layout_counts(self.layout_counts)
        )
        object.__setattr__(
            self,
            "top_level_field_presence",
            _freeze_fixed_counts(
                "top_level_field_presence",
                self.top_level_field_presence,
                TOP_LEVEL_PRESENCE_FIELDS,
            ),
        )
        object.__setattr__(
            self,
            "face_field_presence",
            _freeze_fixed_counts(
                "face_field_presence",
                self.face_field_presence,
                FACE_PRESENCE_FIELDS,
            ),
        )
        object.__setattr__(
            self,
            "shard_record_counts",
            _freeze_fixed_counts(
                "shard_record_counts", self.shard_record_counts, SHARD_NAMES
            ),
        )
        if self.record_count != (
            self.unique_oracle_id_count + self.duplicate_oracle_id_count
        ):
            raise ValueError("record and identity counts do not reconcile")
        if self.record_count != self.cards_with_faces + self.cards_without_faces:
            raise ValueError("face presence counts do not reconcile")
        if sum(self.layout_counts.values()) != self.record_count:
            raise ValueError("layout counts do not reconcile")
        if sum(self.shard_record_counts.values()) != self.record_count:
            raise ValueError("shard counts do not reconcile")
        expected_total_faces = sum(
            int(key) * count for key, count in self.face_count_distribution.items()
        )
        if self.total_face_count != expected_total_faces:
            raise ValueError("total_face_count does not reconcile")
        expected_max_faces = max(
            (int(key) for key in self.face_count_distribution), default=0
        )
        if self.max_face_count != expected_max_faces:
            raise ValueError("max_face_count does not reconcile")


def collect_structural_statistics(
    records: Iterable[StructuralCardRecordV1],
    shard_record_counts: Mapping[str, int],
    task01_identity_parity: bool,
    task01_identity_count: int,
) -> StructuralStatistics:
    """Collect source-membership facts without interpreting card semantics."""

    record_count = 0
    unique_ids: set[str] = set()
    duplicate_count = 0
    cards_with_faces = 0
    cards_without_faces = 0
    total_face_count = 0
    max_face_count = 0
    face_count_distribution: Counter[str] = Counter()
    layout_counts: Counter[str] = Counter()
    top_level_presence: Counter[str] = Counter(
        {field: 0 for field in TOP_LEVEL_PRESENCE_FIELDS}
    )
    face_presence: Counter[str] = Counter({field: 0 for field in FACE_PRESENCE_FIELDS})

    for record in records:
        record_count += 1
        if record.oracle_id in unique_ids:
            duplicate_count += 1
        else:
            unique_ids.add(record.oracle_id)
        layout_counts[record.layout] += 1
        for field in TOP_LEVEL_PRESENCE_FIELDS:
            value = record.faces if field == "card_faces" else getattr(record, field)
            if field == "all_parts":
                value = record.all_parts
            if value is not None:
                top_level_presence[field] += 1
        if record.faces is None:
            cards_without_faces += 1
        else:
            cards_with_faces += 1
            face_count = len(record.faces)
            face_count_distribution[str(face_count)] += 1
            total_face_count += face_count
            max_face_count = max(max_face_count, face_count)
            for face in record.faces:
                for field in FACE_PRESENCE_FIELDS:
                    if getattr(face, field) is not None:
                        face_presence[field] += 1

    return StructuralStatistics(
        record_count=record_count,
        unique_oracle_id_count=len(unique_ids),
        duplicate_oracle_id_count=duplicate_count,
        cards_with_faces=cards_with_faces,
        cards_without_faces=cards_without_faces,
        total_face_count=total_face_count,
        max_face_count=max_face_count,
        face_count_distribution=face_count_distribution,
        layout_counts=layout_counts,
        top_level_field_presence=top_level_presence,
        face_field_presence=face_presence,
        shard_record_counts=shard_record_counts,
        task01_record_identity_parity=task01_identity_parity,
        task01_identity_count=task01_identity_count,
    )
