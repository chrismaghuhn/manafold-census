"""Immutable same-source Requirement bundles and minimal relationships."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar, cast

from ..canonical import JSONValue, canonical_json_bytes
from ..digest import domain_digest
from .evidence import SourceRecordRefV1
from .model import RequirementV1
from .primitives import (
    _require_enum,
    _require_int,
    _require_object,
    _validate_json_wire,
)

BUNDLE_SCHEMA = "census.semantic-requirement-bundle.v1"
BUNDLE_DIGEST_DOMAIN = "census.semantic-requirement-bundle.v1"
_REQUIREMENT_ID_PATTERN = re.compile(r"^srq_[0-9a-f]{64}$")
_SYMMETRIC_TYPES = frozenset(
    {
        "ALTERNATIVE_OF",
        "CONFLICTS_WITH",
    }
)


class RelationshipTypeV1(StrEnum):
    PARENT_OF = "PARENT_OF"
    ALTERNATIVE_OF = "ALTERNATIVE_OF"
    CONDITION_OF = "CONDITION_OF"
    COST_OF = "COST_OF"
    SEQUENCE_BEFORE = "SEQUENCE_BEFORE"
    CONFLICTS_WITH = "CONFLICTS_WITH"
    SUPERSEDES = "SUPERSEDES"


def _require_requirement_id(field: str, value: object) -> str:
    if not isinstance(value, str) or _REQUIREMENT_ID_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field} must be a valid Requirement ID")
    return value


def _wire_list(value: object, field: str) -> list[object]:
    _validate_json_wire(value, field)
    if not isinstance(value, list):
        raise TypeError(f"{field} must be a JSON array")
    return value


def _is_symmetric(value: RelationshipTypeV1) -> bool:
    return value.value in _SYMMETRIC_TYPES


@dataclass(frozen=True, slots=True)
class RequirementRelationshipV1:
    relationship_type: RelationshipTypeV1
    from_requirement_id: str
    to_requirement_id: str
    ordinal: int | None

    _WIRE_KEYS: ClassVar[set[str]] = {"type", "from", "to", "ordinal"}

    def __post_init__(self) -> None:
        relationship_type = _require_enum(
            "type", self.relationship_type, RelationshipTypeV1
        )
        from_id = _require_requirement_id("from", self.from_requirement_id)
        to_id = _require_requirement_id("to", self.to_requirement_id)
        ordinal = self.ordinal
        if relationship_type is RelationshipTypeV1.SEQUENCE_BEFORE:
            if ordinal is None:
                raise ValueError("SEQUENCE_BEFORE requires an ordinal")
            ordinal = _require_int("ordinal", ordinal, nonnegative=True)
        elif relationship_type is RelationshipTypeV1.PARENT_OF:
            if ordinal is not None:
                ordinal = _require_int("ordinal", ordinal, nonnegative=True)
        elif ordinal is not None:
            raise ValueError("ordinal is not allowed for this relationship type")
        if _is_symmetric(relationship_type) and from_id > to_id:
            from_id, to_id = to_id, from_id
        object.__setattr__(self, "relationship_type", relationship_type)
        object.__setattr__(self, "from_requirement_id", from_id)
        object.__setattr__(self, "to_requirement_id", to_id)
        object.__setattr__(self, "ordinal", ordinal)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "type": self.relationship_type.value,
            "from": self.from_requirement_id,
            "to": self.to_requirement_id,
            "ordinal": self.ordinal,
        }

    @classmethod
    def from_wire(cls, value: object) -> RequirementRelationshipV1:
        document = _require_object(value, cls._WIRE_KEYS, "relationship")
        relationship_type = _require_enum("type", document["type"], RelationshipTypeV1)
        from_id = cast(str, document["from"])
        to_id = cast(str, document["to"])
        relationship = cls(
            relationship_type,
            from_id,
            to_id,
            None
            if document["ordinal"] is None
            else _require_int("ordinal", document["ordinal"], nonnegative=True),
        )
        if (
            _is_symmetric(relationship_type)
            and from_id != relationship.from_requirement_id
        ):
            raise ValueError("symmetric relationship endpoints are not canonical")
        return relationship


def _relationship_sort_key(
    relationship: RequirementRelationshipV1,
) -> tuple[str, str, str, int]:
    return (
        relationship.relationship_type.value,
        relationship.from_requirement_id,
        relationship.to_requirement_id,
        -1 if relationship.ordinal is None else relationship.ordinal,
    )


def _reject_cycle(
    relationships: tuple[RequirementRelationshipV1, ...],
    relationship_type: RelationshipTypeV1,
) -> None:
    adjacency: dict[str, list[str]] = {}
    for relationship in relationships:
        if relationship.relationship_type is relationship_type:
            adjacency.setdefault(relationship.from_requirement_id, []).append(
                relationship.to_requirement_id
            )
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            raise ValueError(f"{relationship_type.value} relationship cycle")
        if node in visited:
            return
        visiting.add(node)
        for child in adjacency.get(node, ()):
            visit(child)
        visiting.remove(node)
        visited.add(node)

    for node in adjacency:
        visit(node)


@dataclass(frozen=True, slots=True)
class RequirementBundleV1:
    source: SourceRecordRefV1
    requirements: tuple[RequirementV1, ...]
    relationships: tuple[RequirementRelationshipV1, ...]

    SCHEMA: ClassVar[str] = BUNDLE_SCHEMA
    _WIRE_KEYS: ClassVar[set[str]] = {
        "schema",
        "source",
        "requirements",
        "relationships",
    }

    def __post_init__(self) -> None:
        if not isinstance(self.source, SourceRecordRefV1):
            raise TypeError("source must be SourceRecordRefV1")
        if not isinstance(self.requirements, tuple | list):
            raise TypeError("requirements must be a tuple or list")
        requirements = tuple(self.requirements)
        if not requirements:
            raise ValueError("requirements must be non-empty")
        if any(not isinstance(item, RequirementV1) for item in requirements):
            raise TypeError("requirements must contain RequirementV1 values")
        if any(item.source != self.source for item in requirements):
            raise ValueError("all requirements must use the bundle source")
        requirement_ids = [item.requirement_id for item in requirements]
        if len(requirement_ids) != len(set(requirement_ids)):
            raise ValueError("bundle contains duplicate requirement IDs")
        if requirement_ids != sorted(requirement_ids):
            raise ValueError("requirements must be strictly sorted by requirement ID")

        if not isinstance(self.relationships, tuple | list):
            raise TypeError("relationships must be a tuple or list")
        relationships = tuple(self.relationships)
        if any(
            not isinstance(item, RequirementRelationshipV1) for item in relationships
        ):
            raise TypeError(
                "relationships must contain RequirementRelationshipV1 values"
            )
        requirement_id_set = set(requirement_ids)
        for relationship in relationships:
            if relationship.from_requirement_id == relationship.to_requirement_id:
                raise ValueError("relationship self-edge is not allowed")
            if (
                relationship.from_requirement_id not in requirement_id_set
                or relationship.to_requirement_id not in requirement_id_set
            ):
                raise ValueError("relationship endpoint is missing")
        ordered_relationships = tuple(sorted(relationships, key=_relationship_sort_key))
        relationship_wires = [
            canonical_json_bytes(item.to_wire()) for item in ordered_relationships
        ]
        if len(relationship_wires) != len(set(relationship_wires)):
            raise ValueError("bundle contains duplicate relationships")
        _reject_cycle(ordered_relationships, RelationshipTypeV1.PARENT_OF)
        _reject_cycle(ordered_relationships, RelationshipTypeV1.SUPERSEDES)
        object.__setattr__(self, "requirements", requirements)
        object.__setattr__(self, "relationships", ordered_relationships)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "schema": BUNDLE_SCHEMA,
            "source": self.source.to_wire(),
            "requirements": [item.to_wire() for item in self.requirements],
            "relationships": [item.to_wire() for item in self.relationships],
        }

    @classmethod
    def from_wire(cls, value: object) -> RequirementBundleV1:
        document = _require_object(value, cls._WIRE_KEYS, "RequirementBundleV1")
        if document["schema"] != BUNDLE_SCHEMA:
            raise ValueError("schema must be census.semantic-requirement-bundle.v1")
        source = SourceRecordRefV1.from_wire(document["source"])
        requirements = tuple(
            RequirementV1.from_wire(item)
            for item in _wire_list(document["requirements"], "requirements")
        )
        relationships = tuple(
            RequirementRelationshipV1.from_wire(item)
            for item in _wire_list(document["relationships"], "relationships")
        )
        return cls(source, requirements, relationships)


def bundle_digest_for(bundle: RequirementBundleV1) -> str:
    """Return the deterministic digest of the complete bundle wire."""

    return domain_digest(BUNDLE_DIGEST_DOMAIN, bundle.to_wire())


__all__ = [
    "BUNDLE_DIGEST_DOMAIN",
    "BUNDLE_SCHEMA",
    "RelationshipTypeV1",
    "RequirementBundleV1",
    "RequirementRelationshipV1",
    "bundle_digest_for",
]
