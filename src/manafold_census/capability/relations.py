"""Typed M4 semantic relations and graph validation."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar, cast

from ..canonical import JSONValue, canonical_json_bytes
from ..digest import domain_digest
from ..semantic.primitives import (
    _require_bool,
    _require_enum,
    _require_int,
    _require_object,
    _require_text,
)
from .claim import CompositionClaimV1
from .definition import CapabilityDefinitionV1, CapabilityLifecycleStateV1
from .model import CapabilityRefV1, NucleusKindV1

RELATION_SCHEMA = "census.capability-relations.v1"
RELATION_ID_DOMAIN = "census.capability-relation-id.v1"
RELATION_ID_PREFIX = "crl_"
_RELATION_ID = re.compile(r"^crl_[0-9a-f]{64}$")


class CapabilityRelationKindV1(StrEnum):
    COMPOSES = "COMPOSES"
    REQUIRES = "REQUIRES"
    SPECIALIZES = "SPECIALIZES"


def _identifier(field: str, value: object, pattern: re.Pattern[str]) -> str:
    text = _require_text(field, value)
    if pattern.fullmatch(text) is None:
        raise ValueError(f"{field} must use its closed digest identity form")
    return text


def _ref(value: object, field: str) -> CapabilityRefV1:
    if isinstance(value, CapabilityDefinitionV1):
        return value.capability_ref
    if isinstance(value, CapabilityRefV1):
        return value
    raise TypeError(f"{field} must be a CapabilityDefinitionV1 or CapabilityRefV1")


def _refs(value: object, field: str) -> tuple[CapabilityRefV1, ...]:
    if not isinstance(value, tuple | list):
        raise TypeError(f"{field} must be a tuple or list")
    values = tuple(value)
    if any(not isinstance(item, CapabilityRefV1) for item in values):
        raise TypeError(f"{field} must contain CapabilityRefV1 values")
    typed = cast(tuple[CapabilityRefV1, ...], values)
    if len(typed) != len(set(typed)):
        raise ValueError(f"duplicate {field} reference")
    return tuple(
        sorted(
            typed,
            key=lambda item: (
                item.capability_family_id,
                item.capability_version,
                item.claim_digest,
            ),
        )
    )


def _relation_payload(
    kind: CapabilityRelationKindV1,
    source: CapabilityRefV1,
    target: CapabilityRefV1,
    component_key: str | None,
    ordinal: int | None,
    required: bool | None,
) -> dict[str, JSONValue]:
    return {
        "schema": RELATION_SCHEMA,
        "relation_kind": kind.value,
        "from_capability": source.to_wire(),
        "to_capability": target.to_wire(),
        "component_key": component_key,
        "ordinal": ordinal,
        "required": required,
    }


def _relation_id(
    kind: CapabilityRelationKindV1,
    source: CapabilityRefV1,
    target: CapabilityRefV1,
    component_key: str | None,
    ordinal: int | None,
    required: bool | None,
) -> str:
    return RELATION_ID_PREFIX + domain_digest(
        RELATION_ID_DOMAIN,
        _relation_payload(kind, source, target, component_key, ordinal, required),
    )


@dataclass(frozen=True, slots=True)
class CapabilityRelationV1:
    relation_id: str
    relation_kind: CapabilityRelationKindV1
    from_capability: CapabilityRefV1
    to_capability: CapabilityRefV1
    component_key: str | None
    ordinal: int | None
    required: bool | None

    SCHEMA: ClassVar[str] = RELATION_SCHEMA
    _WIRE_KEYS: ClassVar[set[str]] = {
        "schema",
        "relation_id",
        "relation_kind",
        "from_capability",
        "to_capability",
        "component_key",
        "ordinal",
        "required",
    }

    def __post_init__(self) -> None:
        kind = _require_enum(
            "relation_kind", self.relation_kind, CapabilityRelationKindV1
        )
        if not isinstance(self.from_capability, CapabilityRefV1):
            raise TypeError("from_capability must be CapabilityRefV1")
        if not isinstance(self.to_capability, CapabilityRefV1):
            raise TypeError("to_capability must be CapabilityRefV1")
        key, ordinal, required = self.component_key, self.ordinal, self.required
        if kind is CapabilityRelationKindV1.COMPOSES:
            key = _require_text("component_key", key)
            ordinal = _require_int("ordinal", ordinal, nonnegative=True)
            required = _require_bool("required", required)
        elif key is not None or ordinal is not None or required is not None:
            raise ValueError("non-COMPOSES relations require null component fields")
        relation_id = _identifier("relation_id", self.relation_id, _RELATION_ID)
        if relation_id != _relation_id(
            kind, self.from_capability, self.to_capability, key, ordinal, required
        ):
            raise ValueError("relation_id does not match the relation claim")
        object.__setattr__(self, "relation_id", relation_id)
        object.__setattr__(self, "relation_kind", kind)
        object.__setattr__(self, "component_key", key)
        object.__setattr__(self, "ordinal", ordinal)
        object.__setattr__(self, "required", required)

    @classmethod
    def create(
        cls,
        *,
        relation_kind: CapabilityRelationKindV1,
        from_capability: CapabilityRefV1,
        to_capability: CapabilityRefV1,
        component_key: str | None = None,
        ordinal: int | None = None,
        required: bool | None = None,
    ) -> CapabilityRelationV1:
        kind = _require_enum("relation_kind", relation_kind, CapabilityRelationKindV1)
        if not isinstance(from_capability, CapabilityRefV1):
            raise TypeError("from_capability must be CapabilityRefV1")
        if not isinstance(to_capability, CapabilityRefV1):
            raise TypeError("to_capability must be CapabilityRefV1")
        return cls(
            _relation_id(
                kind, from_capability, to_capability, component_key, ordinal, required
            ),
            kind,
            from_capability,
            to_capability,
            component_key,
            ordinal,
            required,
        )

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "schema": self.SCHEMA,
            "relation_id": self.relation_id,
            "relation_kind": self.relation_kind.value,
            "from_capability": self.from_capability.to_wire(),
            "to_capability": self.to_capability.to_wire(),
            "component_key": self.component_key,
            "ordinal": self.ordinal,
            "required": self.required,
        }

    @classmethod
    def from_wire(cls, value: object) -> CapabilityRelationV1:
        document = _require_object(value, cls._WIRE_KEYS, "Capability relation")
        if _require_text("schema", document["schema"]) != cls.SCHEMA:
            raise ValueError(f"schema must be {cls.SCHEMA}")
        result = cls(
            cast(str, document["relation_id"]),
            _require_enum(
                "relation_kind", document["relation_kind"], CapabilityRelationKindV1
            ),
            CapabilityRefV1.from_wire(document["from_capability"]),
            CapabilityRefV1.from_wire(document["to_capability"]),
            cast(str | None, document["component_key"]),
            cast(int | None, document["ordinal"]),
            cast(bool | None, document["required"]),
        )
        if result.to_wire() != document:
            raise ValueError("Capability relation wire is not canonical")
        return result


def relation_claim_digest_for(relation: CapabilityRelationV1) -> str:
    if not isinstance(relation, CapabilityRelationV1):
        raise TypeError("relation must be CapabilityRelationV1")
    return domain_digest(
        RELATION_ID_DOMAIN,
        _relation_payload(
            relation.relation_kind,
            relation.from_capability,
            relation.to_capability,
            relation.component_key,
            relation.ordinal,
            relation.required,
        ),
    )


def relation_sort_key(relation: CapabilityRelationV1) -> tuple[str, bytes, bytes, str]:
    if not isinstance(relation, CapabilityRelationV1):
        raise TypeError("relation must be CapabilityRelationV1")
    return (
        relation.relation_kind.value,
        canonical_json_bytes(relation.from_capability.to_wire()),
        canonical_json_bytes(relation.to_capability.to_wire()),
        relation.relation_id,
    )


def sort_capability_relations(
    relations: Sequence[CapabilityRelationV1],
) -> tuple[CapabilityRelationV1, ...]:
    values = tuple(relations)
    if any(not isinstance(item, CapabilityRelationV1) for item in values):
        raise TypeError("relations must contain CapabilityRelationV1 values")
    return tuple(sorted(values, key=relation_sort_key))


def _edge(
    kind: CapabilityRelationKindV1,
    source: object,
    target: object,
    **fields: object,
) -> CapabilityRelationV1:
    return CapabilityRelationV1.create(
        relation_kind=kind,
        from_capability=_ref(source, "from_capability"),
        to_capability=_ref(target, "to_capability"),
        component_key=cast(str | None, fields.get("component_key")),
        ordinal=cast(int | None, fields.get("ordinal")),
        required=cast(bool | None, fields.get("required")),
    )


def composes_edge(
    composite: CapabilityDefinitionV1,
    component: CapabilityDefinitionV1 | CapabilityRefV1,
    *,
    component_key: str | None = None,
) -> CapabilityRelationV1:
    if not isinstance(composite, CapabilityDefinitionV1):
        raise TypeError("composes_edge requires a composite Capability definition")
    if composite.claim.family_key.nucleus_kind is not NucleusKindV1.COMPOSITE:
        raise ValueError("COMPOSES source must be a composite Capability")
    composition = composite.claim.composition
    if not isinstance(composition, CompositionClaimV1):
        raise ValueError("COMPOSES source must declare a composition claim")
    target = _ref(component, "component")
    matches = tuple(
        item for item in composition.components if item.capability == target
    )
    if component_key is not None:
        matches = tuple(item for item in matches if item.component_key == component_key)
    if len(matches) != 1:
        raise ValueError("component Capability is not declared exactly once")
    item = matches[0]
    return _edge(
        CapabilityRelationKindV1.COMPOSES,
        composite,
        target,
        component_key=item.component_key,
        ordinal=item.ordinal,
        required=item.required,
    )


def requires_edge(
    source: CapabilityDefinitionV1 | CapabilityRefV1,
    target: CapabilityDefinitionV1 | CapabilityRefV1,
) -> CapabilityRelationV1:
    return _edge(CapabilityRelationKindV1.REQUIRES, source, target)


def specializes_edge(
    source: CapabilityDefinitionV1 | CapabilityRefV1,
    target: CapabilityDefinitionV1 | CapabilityRefV1,
) -> CapabilityRelationV1:
    return _edge(CapabilityRelationKindV1.SPECIALIZES, source, target)


def _capability_index(
    capabilities: Sequence[CapabilityDefinitionV1],
) -> dict[CapabilityRefV1, CapabilityDefinitionV1]:
    values = tuple(capabilities)
    if any(not isinstance(item, CapabilityDefinitionV1) for item in values):
        raise TypeError("capabilities must contain CapabilityDefinitionV1 values")
    result: dict[CapabilityRefV1, CapabilityDefinitionV1] = {}
    for capability in values:
        if capability.capability_ref in result:
            raise ValueError("duplicate Capability reference")
        result[capability.capability_ref] = capability
    return result


def _assert_acyclic(
    graph: dict[CapabilityRefV1, set[CapabilityRefV1]],
    kind: CapabilityRelationKindV1,
) -> None:
    visiting: set[CapabilityRefV1] = set()
    visited: set[CapabilityRefV1] = set()

    def visit(node: CapabilityRefV1) -> None:
        if node in visiting:
            raise ValueError(f"{kind.value} relation cycle detected")
        if node in visited:
            return
        visiting.add(node)
        for successor in graph.get(node, ()):
            visit(successor)
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node)


def _validate_cycles(relations: Sequence[CapabilityRelationV1]) -> None:
    for kind in CapabilityRelationKindV1:
        graph: dict[CapabilityRefV1, set[CapabilityRefV1]] = {}
        for relation in relations:
            if relation.relation_kind is kind:
                graph.setdefault(relation.from_capability, set()).add(
                    relation.to_capability
                )
        _assert_acyclic(graph, kind)


def validate_capability_edges(
    relations: Sequence[CapabilityRelationV1],
    capabilities: Sequence[CapabilityDefinitionV1] = (),
) -> None:
    values = tuple(relations)
    if any(not isinstance(item, CapabilityRelationV1) for item in values):
        raise TypeError("relations must contain CapabilityRelationV1 values")
    if len({item.relation_id for item in values}) != len(values):
        raise ValueError("duplicate Capability relation")
    if any(item.from_capability == item.to_capability for item in values):
        raise ValueError("self-edge is not allowed")
    definitions = _capability_index(capabilities)
    if definitions:
        for relation in values:
            source = definitions.get(relation.from_capability)
            target = definitions.get(relation.to_capability)
            if source is None or target is None:
                raise ValueError("Capability relation endpoint does not exist exactly")
            if relation.relation_kind is not CapabilityRelationKindV1.COMPOSES:
                continue
            if source.claim.family_key.nucleus_kind is not NucleusKindV1.COMPOSITE:
                raise ValueError("COMPOSES source must be a composite Capability")
            composition = source.claim.composition
            if not isinstance(composition, CompositionClaimV1):
                raise ValueError("COMPOSES source must declare a composition claim")
            matches = tuple(
                item
                for item in composition.components
                if item.component_key == relation.component_key
            )
            if len(matches) != 1:
                raise ValueError("COMPOSES component key is not declared exactly once")
            component = matches[0]
            if component.capability != relation.to_capability:
                raise ValueError(
                    "COMPOSES target does not match the declared component"
                )
            if (
                component.ordinal != relation.ordinal
                or component.required != relation.required
            ):
                raise ValueError(
                    "COMPOSES relation fields do not match the component claim"
                )
            if (
                source.lifecycle is CapabilityLifecycleStateV1.ACTIVE
                and target.lifecycle is not CapabilityLifecycleStateV1.ACTIVE
            ):
                raise ValueError(
                    "active composite may reference only active non-retired components"
                )
    _validate_cycles(values)
    if not definitions:
        return
    grouped: dict[CapabilityRefV1, list[CapabilityRelationV1]] = {}
    for relation in values:
        if relation.relation_kind is CapabilityRelationKindV1.COMPOSES:
            grouped.setdefault(relation.from_capability, []).append(relation)
    for composite_ref, component_relations in grouped.items():
        composition = definitions[composite_ref].claim.composition
        assert composition is not None
        keys = [item.component_key for item in component_relations]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate composition component key")
        required = {
            item.component_key for item in composition.components if item.required
        }
        if not required.issubset(set(keys)):
            raise ValueError("required component keys are not covered exactly once")
    for composite_ref, composite in definitions.items():
        if (
            composite.lifecycle is CapabilityLifecycleStateV1.ACTIVE
            and composite.claim.family_key.nucleus_kind is NucleusKindV1.COMPOSITE
        ):
            composition = composite.claim.composition
            if not isinstance(composition, CompositionClaimV1):
                raise ValueError("active composite must declare a composition claim")
            required_edge_keys = {
                item.component_key for item in grouped.get(composite_ref, ())
            }
            required = {
                item.component_key for item in composition.components if item.required
            }
            if not required.issubset(required_edge_keys):
                raise ValueError("required component keys are not covered exactly once")
