"""Stable M4 Capability nucleus and exact Capability references."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar, cast

from ..canonical import JSONValue
from ..semantic.kinds import (
    RequirementFamilyV1,
    RequirementKindV1,
    validate_kind_family,
)
from ..semantic.primitives import (
    _require_enum,
    _require_int,
    _require_object,
    _require_text,
)

_FAMILY_ID_PATTERN = re.compile(r"^capfam_[0-9a-f]{64}$")
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class NucleusKindV1(StrEnum):
    ATOMIC = "ATOMIC"
    COMPOSITE = "COMPOSITE"


def _anchor_values(
    value: object,
) -> tuple[tuple[RequirementFamilyV1, RequirementKindV1], ...]:
    if not isinstance(value, tuple | list):
        raise TypeError("operation_anchor must be a tuple or list")

    anchors: list[tuple[RequirementFamilyV1, RequirementKindV1]] = []
    for index, item in enumerate(value):
        if not isinstance(item, tuple | list) or len(item) != 2:
            raise TypeError(f"operation_anchor[{index}] must contain family and kind")
        family = _require_enum(
            f"operation_anchor[{index}].family",
            item[0],
            RequirementFamilyV1,
        )
        kind = _require_enum(
            f"operation_anchor[{index}].kind",
            item[1],
            RequirementKindV1,
        )
        validate_kind_family(family, kind)
        anchors.append((family, kind))

    return tuple(sorted(anchors, key=lambda item: (item[0].value, item[1].value)))


@dataclass(frozen=True, slots=True)
class CapabilityFamilyKeyV1:
    nucleus_contract_version: str
    nucleus_kind: NucleusKindV1
    operation_anchor: tuple[tuple[RequirementFamilyV1, RequirementKindV1], ...]

    SCHEMA: ClassVar[str] = "census.capability-family-key.v1"
    _WIRE_KEYS: ClassVar[set[str]] = {
        "family_key_schema",
        "nucleus_contract_version",
        "nucleus_kind",
        "operation_anchor",
    }

    def __post_init__(self) -> None:
        version = _require_text(
            "nucleus_contract_version",
            self.nucleus_contract_version,
        )
        nucleus_kind = _require_enum(
            "nucleus_kind",
            self.nucleus_kind,
            NucleusKindV1,
        )
        anchors = _anchor_values(self.operation_anchor)
        if not anchors:
            raise ValueError("operation_anchor must be non-empty")
        if len(anchors) != len(set(anchors)):
            raise ValueError("duplicate operation anchor")
        if nucleus_kind is NucleusKindV1.ATOMIC and len(anchors) != 1:
            raise ValueError("ATOMIC requires exactly one operation anchor")
        if nucleus_kind is NucleusKindV1.COMPOSITE and len(anchors) < 2:
            raise ValueError("COMPOSITE requires at least two operation anchors")

        object.__setattr__(self, "nucleus_contract_version", version)
        object.__setattr__(self, "nucleus_kind", nucleus_kind)
        object.__setattr__(self, "operation_anchor", anchors)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "family_key_schema": self.SCHEMA,
            "nucleus_contract_version": self.nucleus_contract_version,
            "nucleus_kind": self.nucleus_kind.value,
            "operation_anchor": [
                {"family": family.value, "kind": kind.value}
                for family, kind in self.operation_anchor
            ],
        }

    @classmethod
    def from_wire(cls, value: object) -> CapabilityFamilyKeyV1:
        document = _require_object(value, cls._WIRE_KEYS, "capability family key")
        schema = _require_text("family_key_schema", document["family_key_schema"])
        if schema != cls.SCHEMA:
            raise ValueError(f"family_key_schema must be {cls.SCHEMA}")

        raw_anchors = document["operation_anchor"]
        if not isinstance(raw_anchors, list):
            raise TypeError("operation_anchor must be a JSON array")

        anchors: list[tuple[RequirementFamilyV1, RequirementKindV1]] = []
        for index, item in enumerate(raw_anchors):
            anchor = _require_object(
                item,
                {"family", "kind"},
                f"operation_anchor[{index}]",
            )
            family = _require_enum(
                f"operation_anchor[{index}].family",
                anchor["family"],
                RequirementFamilyV1,
            )
            kind = _require_enum(
                f"operation_anchor[{index}].kind",
                anchor["kind"],
                RequirementKindV1,
            )
            validate_kind_family(family, kind)
            anchors.append((family, kind))

        result = cls(
            nucleus_contract_version=cast(
                str,
                document["nucleus_contract_version"],
            ),
            nucleus_kind=_require_enum(
                "nucleus_kind",
                document["nucleus_kind"],
                NucleusKindV1,
            ),
            operation_anchor=tuple(anchors),
        )
        if result.to_wire()["operation_anchor"] != raw_anchors:
            raise ValueError("operation_anchor must be in canonical order")
        return result


@dataclass(frozen=True, slots=True)
class CapabilityRefV1:
    capability_family_id: str
    capability_version: int
    claim_digest: str

    _WIRE_KEYS: ClassVar[set[str]] = {
        "capability_family_id",
        "capability_version",
        "claim_digest",
    }

    def __post_init__(self) -> None:
        family_id = _require_text("capability_family_id", self.capability_family_id)
        if _FAMILY_ID_PATTERN.fullmatch(family_id) is None:
            raise ValueError(
                "capability_family_id must be capfam_ plus a lowercase SHA-256 digest"
            )
        version = _require_int("capability_version", self.capability_version)
        if version < 1:
            raise ValueError("capability_version must be at least one")
        claim_digest = _require_text("claim_digest", self.claim_digest)
        if _DIGEST_PATTERN.fullmatch(claim_digest) is None:
            raise ValueError("claim_digest must be a lowercase SHA-256 digest")

        object.__setattr__(self, "capability_family_id", family_id)
        object.__setattr__(self, "capability_version", version)
        object.__setattr__(self, "claim_digest", claim_digest)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "capability_family_id": self.capability_family_id,
            "capability_version": self.capability_version,
            "claim_digest": self.claim_digest,
        }

    @classmethod
    def from_wire(cls, value: object) -> CapabilityRefV1:
        document = _require_object(value, cls._WIRE_KEYS, "capability reference")
        return cls(
            capability_family_id=cast(str, document["capability_family_id"]),
            capability_version=cast(int, document["capability_version"]),
            claim_digest=cast(str, document["claim_digest"]),
        )


__all__ = [
    "CapabilityFamilyKeyV1",
    "CapabilityRefV1",
    "NucleusKindV1",
]
