"""Typed composition-group assignments and context identity."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar, cast

from ..canonical import JSONValue, canonical_json_bytes
from ..digest import domain_digest
from ..semantic.primitives import _require_object, _require_text
from .model import CapabilityRefV1

COMPOSITION_GROUP_SCHEMA = "census.capability-composition-group.v1"
COMPOSITION_GROUP_ID_DOMAIN = "census.capability-composition-group-id.v1"
COMPOSITION_GROUP_ID_PREFIX = "rcg_"
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_REQUIREMENT_ID_PATTERN = re.compile(r"^srq_[0-9a-f]{64}$")
_GROUP_ID_PATTERN = re.compile(r"^rcg_[0-9a-f]{64}$")


def _digest(field: str, value: object) -> str:
    text = _require_text(field, value)
    if _DIGEST_PATTERN.fullmatch(text) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")
    return text


def _identifier(field: str, value: object, pattern: re.Pattern[str]) -> str:
    text = _require_text(field, value)
    if pattern.fullmatch(text) is None:
        raise ValueError(f"{field} must use its closed digest identity form")
    return text


@dataclass(frozen=True, slots=True)
class CompositionAssignmentV1:
    requirement_id: str
    requirement_wire_digest: str
    component: CapabilityRefV1
    component_key: str

    _WIRE_KEYS: ClassVar[set[str]] = {
        "requirement_id",
        "requirement_wire_digest",
        "component",
        "component_key",
    }

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "requirement_id",
            _identifier("requirement_id", self.requirement_id, _REQUIREMENT_ID_PATTERN),
        )
        object.__setattr__(
            self,
            "requirement_wire_digest",
            _digest("requirement_wire_digest", self.requirement_wire_digest),
        )
        if not isinstance(self.component, CapabilityRefV1):
            raise TypeError("component must be CapabilityRefV1")
        object.__setattr__(
            self,
            "component_key",
            _require_text("component_key", self.component_key),
        )

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "requirement_id": self.requirement_id,
            "requirement_wire_digest": self.requirement_wire_digest,
            "component": self.component.to_wire(),
            "component_key": self.component_key,
        }

    @classmethod
    def from_wire(cls, value: object) -> CompositionAssignmentV1:
        document = _require_object(value, cls._WIRE_KEYS, "composition assignment")
        result = cls(
            cast(str, document["requirement_id"]),
            cast(str, document["requirement_wire_digest"]),
            CapabilityRefV1.from_wire(document["component"]),
            cast(str, document["component_key"]),
        )
        if result.to_wire() != document:
            raise ValueError("composition assignment wire is not canonical")
        return result


@dataclass(frozen=True, slots=True)
class CompositionContextV1:
    composition_group_id: str
    composite: CapabilityRefV1
    component_key: str

    _WIRE_KEYS: ClassVar[set[str]] = {
        "composition_group_id",
        "composite",
        "component_key",
    }

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "composition_group_id",
            _identifier(
                "composition_group_id",
                self.composition_group_id,
                _GROUP_ID_PATTERN,
            ),
        )
        if not isinstance(self.composite, CapabilityRefV1):
            raise TypeError("composite must be CapabilityRefV1")
        object.__setattr__(
            self,
            "component_key",
            _require_text("component_key", self.component_key),
        )

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "composition_group_id": self.composition_group_id,
            "composite": self.composite.to_wire(),
            "component_key": self.component_key,
        }

    @classmethod
    def from_wire(cls, value: object) -> CompositionContextV1:
        document = _require_object(value, cls._WIRE_KEYS, "composition context")
        return cls(
            cast(str, document["composition_group_id"]),
            CapabilityRefV1.from_wire(document["composite"]),
            cast(str, document["component_key"]),
        )


def composition_group_id_for(
    *,
    m3_analysis_manifest_sha256: str,
    composite: CapabilityRefV1,
    assignments: Sequence[CompositionAssignmentV1],
) -> str:
    manifest = _digest("m3_analysis_manifest_sha256", m3_analysis_manifest_sha256)
    if not isinstance(composite, CapabilityRefV1):
        raise TypeError("composite must be CapabilityRefV1")
    values = tuple(assignments)
    if not values:
        raise ValueError("composition group requires at least one assignment")
    if any(not isinstance(item, CompositionAssignmentV1) for item in values):
        raise TypeError("assignments must contain CompositionAssignmentV1 values")
    keys = [(item.requirement_id, item.component_key) for item in values]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate composition group assignment")
    component_keys = [item.component_key for item in values]
    if len(component_keys) != len(set(component_keys)):
        raise ValueError("duplicate composition group component key")
    ordered = tuple(
        sorted(values, key=lambda item: canonical_json_bytes(item.to_wire()))
    )
    payload: dict[str, JSONValue] = {
        "schema": COMPOSITION_GROUP_SCHEMA,
        "m3_analysis_manifest_sha256": manifest,
        "composite": composite.to_wire(),
        "assignments": [item.to_wire() for item in ordered],
    }
    return COMPOSITION_GROUP_ID_PREFIX + domain_digest(
        COMPOSITION_GROUP_ID_DOMAIN, payload
    )


__all__ = [
    "COMPOSITION_GROUP_ID_DOMAIN",
    "COMPOSITION_GROUP_ID_PREFIX",
    "COMPOSITION_GROUP_SCHEMA",
    "CompositionAssignmentV1",
    "CompositionContextV1",
    "composition_group_id_for",
]
