"""Immutable M4 Capability evolution events and history validation."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar, cast

from ..canonical import JSONValue
from ..digest import domain_digest
from ..semantic.primitives import _require_enum, _require_object, _require_text
from .definition import CapabilityDefinitionV1, CapabilityLifecycleStateV1
from .model import CapabilityRefV1
from .relations import (
    RELATION_ID_DOMAIN,
    RELATION_ID_PREFIX,
    RELATION_SCHEMA,
    CapabilityRelationKindV1,
    CapabilityRelationV1,
    composes_edge,
    relation_claim_digest_for,
    relation_sort_key,
    requires_edge,
    sort_capability_relations,
    specializes_edge,
    validate_capability_edges,
)
from .review import CapabilityReviewRecordV1, EvolutionReviewSubjectV1, ReviewDecisionV1

EVOLUTION_SCHEMA = "census.capability-evolution.v1"
EVOLUTION_ID_DOMAIN = EVOLUTION_SCHEMA
EVOLUTION_ID_PREFIX = "cev_"
_EVOLUTION_ID = re.compile(r"^cev_[0-9a-f]{64}$")
_REVIEW_ID = re.compile(r"^mrv_[0-9a-f]{64}$")


class EvolutionOperationV1(StrEnum):
    ADDITION = "ADDITION"
    SPLIT = "SPLIT"
    MERGE = "MERGE"
    SUPERSESSION = "SUPERSESSION"
    RETIREMENT = "RETIREMENT"


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


def _evolution_payload(
    operation: EvolutionOperationV1,
    old: tuple[CapabilityRefV1, ...],
    new: tuple[CapabilityRefV1, ...],
) -> dict[str, JSONValue]:
    return {
        "schema": EVOLUTION_SCHEMA,
        "operation": operation.value,
        "from": [item.to_wire() for item in old],
        "to": [item.to_wire() for item in new],
    }


def _evolution_id(
    operation: EvolutionOperationV1,
    old: tuple[CapabilityRefV1, ...],
    new: tuple[CapabilityRefV1, ...],
) -> str:
    return EVOLUTION_ID_PREFIX + domain_digest(
        EVOLUTION_ID_DOMAIN, _evolution_payload(operation, old, new)
    )


def _evolution_values(
    operation: EvolutionOperationV1,
    old: object,
    new: object,
) -> tuple[
    EvolutionOperationV1, tuple[CapabilityRefV1, ...], tuple[CapabilityRefV1, ...]
]:
    kind = _require_enum("operation", operation, EvolutionOperationV1)
    old_refs, new_refs = _refs(old, "from"), _refs(new, "to")
    limits = {
        EvolutionOperationV1.ADDITION: (0, 0, 1, 1),
        EvolutionOperationV1.SPLIT: (1, 1, 2, None),
        EvolutionOperationV1.MERGE: (2, None, 1, 1),
        EvolutionOperationV1.SUPERSESSION: (1, 1, 1, 1),
        EvolutionOperationV1.RETIREMENT: (1, 1, 0, 0),
    }
    old_min, old_max, new_min, new_max = limits[kind]
    if len(old_refs) < old_min or (old_max is not None and len(old_refs) > old_max):
        expected = (
            "no"
            if old_max == 0
            else (
                "exactly one"
                if old_min == old_max
                else f"at least {'two' if old_min == 2 else old_min}"
            )
        )
        raise ValueError(f"{kind.value} requires {expected} from reference(s)")
    if len(new_refs) < new_min or (new_max is not None and len(new_refs) > new_max):
        expected = (
            "no"
            if new_max == 0
            else (
                "exactly one"
                if new_min == new_max
                else f"at least {'two' if new_min == 2 else new_min}"
            )
        )
        raise ValueError(f"{kind.value} requires {expected} to reference(s)")
    if kind is EvolutionOperationV1.SUPERSESSION:
        first, successor = old_refs[0], new_refs[0]
        if first == successor or (
            first.capability_family_id == successor.capability_family_id
            and first.capability_version == successor.capability_version
        ):
            raise ValueError("SUPERSESSION cannot target the same version")
    if set(old_refs) & set(new_refs):
        raise ValueError("evolution endpoints must be distinct")
    return kind, old_refs, new_refs


@dataclass(frozen=True, slots=True)
class CapabilityEvolutionV1:
    event_id: str
    operation: EvolutionOperationV1
    from_references: tuple[CapabilityRefV1, ...]
    to_references: tuple[CapabilityRefV1, ...]
    review_ref: str

    SCHEMA: ClassVar[str] = EVOLUTION_SCHEMA
    _WIRE_KEYS: ClassVar[set[str]] = {
        "schema",
        "event_id",
        "operation",
        "from",
        "to",
        "review_ref",
    }

    def __post_init__(self) -> None:
        operation, old, new = _evolution_values(
            self.operation, self.from_references, self.to_references
        )
        event_id = _identifier("event_id", self.event_id, _EVOLUTION_ID)
        if event_id != _evolution_id(operation, old, new):
            raise ValueError("event_id does not match the evolution claim")
        review_ref = _identifier("review_ref", self.review_ref, _REVIEW_ID)
        object.__setattr__(self, "event_id", event_id)
        object.__setattr__(self, "operation", operation)
        object.__setattr__(self, "from_references", old)
        object.__setattr__(self, "to_references", new)
        object.__setattr__(self, "review_ref", review_ref)

    @classmethod
    def create(
        cls,
        *,
        operation: EvolutionOperationV1,
        from_references: Sequence[CapabilityRefV1],
        to_references: Sequence[CapabilityRefV1],
        review_ref: str,
    ) -> CapabilityEvolutionV1:
        kind, old, new = _evolution_values(
            operation, tuple(from_references), tuple(to_references)
        )
        return cls(_evolution_id(kind, old, new), kind, old, new, review_ref)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "schema": self.SCHEMA,
            "event_id": self.event_id,
            "operation": self.operation.value,
            "from": [item.to_wire() for item in self.from_references],
            "to": [item.to_wire() for item in self.to_references],
            "review_ref": self.review_ref,
        }

    @classmethod
    def from_wire(cls, value: object) -> CapabilityEvolutionV1:
        document = _require_object(value, cls._WIRE_KEYS, "Capability evolution")
        if _require_text("schema", document["schema"]) != cls.SCHEMA:
            raise ValueError(f"schema must be {cls.SCHEMA}")
        old, new = document["from"], document["to"]
        if not isinstance(old, list) or not isinstance(new, list):
            raise TypeError("evolution from and to must be JSON arrays")
        result = cls(
            cast(str, document["event_id"]),
            _require_enum("operation", document["operation"], EvolutionOperationV1),
            tuple(CapabilityRefV1.from_wire(item) for item in old),
            tuple(CapabilityRefV1.from_wire(item) for item in new),
            cast(str, document["review_ref"]),
        )
        if result.to_wire() != document:
            raise ValueError("Capability evolution wire is not canonical")
        return result


def evolution_claim_digest_for(event: CapabilityEvolutionV1) -> str:
    if not isinstance(event, CapabilityEvolutionV1):
        raise TypeError("event must be CapabilityEvolutionV1")
    return domain_digest(
        EVOLUTION_ID_DOMAIN,
        _evolution_payload(event.operation, event.from_references, event.to_references),
    )


def evolution_event_id_for(event: CapabilityEvolutionV1) -> str:
    return EVOLUTION_ID_PREFIX + evolution_claim_digest_for(event)


def addition_event(
    capability: CapabilityDefinitionV1 | CapabilityRefV1,
    *,
    review_ref: str,
) -> CapabilityEvolutionV1:
    return CapabilityEvolutionV1.create(
        operation=EvolutionOperationV1.ADDITION,
        from_references=(),
        to_references=(_ref(capability, "capability"),),
        review_ref=review_ref,
    )


def split_event(
    old: CapabilityDefinitionV1 | CapabilityRefV1,
    new: Sequence[CapabilityDefinitionV1 | CapabilityRefV1],
    *,
    review_ref: str,
) -> CapabilityEvolutionV1:
    return CapabilityEvolutionV1.create(
        operation=EvolutionOperationV1.SPLIT,
        from_references=(_ref(old, "old_capability"),),
        to_references=tuple(_ref(item, "new_capability") for item in new),
        review_ref=review_ref,
    )


def merge_event(
    old: Sequence[CapabilityDefinitionV1 | CapabilityRefV1],
    new: CapabilityDefinitionV1 | CapabilityRefV1,
    *,
    review_ref: str,
) -> CapabilityEvolutionV1:
    return CapabilityEvolutionV1.create(
        operation=EvolutionOperationV1.MERGE,
        from_references=tuple(_ref(item, "old_capability") for item in old),
        to_references=(_ref(new, "new_capability"),),
        review_ref=review_ref,
    )


def supersession_event(
    old: CapabilityDefinitionV1 | CapabilityRefV1,
    successor: CapabilityDefinitionV1 | CapabilityRefV1,
    *,
    review_ref: str,
) -> CapabilityEvolutionV1:
    return CapabilityEvolutionV1.create(
        operation=EvolutionOperationV1.SUPERSESSION,
        from_references=(_ref(old, "old_capability"),),
        to_references=(_ref(successor, "successor"),),
        review_ref=review_ref,
    )


def retirement_event(
    capability: CapabilityDefinitionV1 | CapabilityRefV1,
    *,
    review_ref: str,
) -> CapabilityEvolutionV1:
    return CapabilityEvolutionV1.create(
        operation=EvolutionOperationV1.RETIREMENT,
        from_references=(_ref(capability, "capability"),),
        to_references=(),
        review_ref=review_ref,
    )


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


def _validate_review(
    event: CapabilityEvolutionV1,
    reviews: Sequence[CapabilityReviewRecordV1],
) -> None:
    records = tuple(reviews)
    if any(not isinstance(item, CapabilityReviewRecordV1) for item in records):
        raise TypeError("reviews must contain CapabilityReviewRecordV1 values")
    subject = EvolutionReviewSubjectV1(
        event.event_id, evolution_claim_digest_for(event)
    )
    matching = tuple(item for item in records if item.subject == subject)
    if any(item.decision is ReviewDecisionV1.ACCEPTED for item in matching) and any(
        item.decision is ReviewDecisionV1.REJECTED for item in matching
    ):
        raise ValueError("conflicting accepted and rejected evolution reviews")
    referenced = tuple(item for item in matching if item.record_id == event.review_ref)
    if len(referenced) != 1 or referenced[0].decision is not ReviewDecisionV1.ACCEPTED:
        raise ValueError("evolution requires an exact accepted review")


def _validate_states(
    event: CapabilityEvolutionV1,
    definitions: dict[CapabilityRefV1, CapabilityDefinitionV1],
) -> None:
    old = [definitions[item] for item in event.from_references]
    new = [definitions[item] for item in event.to_references]
    if event.operation is EvolutionOperationV1.ADDITION:
        if new[0].lifecycle is not CapabilityLifecycleStateV1.ACTIVE:
            raise ValueError("ADDITION target must be ACTIVE")
    elif event.operation in (EvolutionOperationV1.SPLIT, EvolutionOperationV1.MERGE):
        if any(
            item.lifecycle is not CapabilityLifecycleStateV1.SUPERSEDED for item in old
        ):
            raise ValueError("split or merge sources must be SUPERSEDED")
        if any(item.lifecycle is not CapabilityLifecycleStateV1.ACTIVE for item in new):
            raise ValueError("split or merge targets must be ACTIVE")
    elif event.operation is EvolutionOperationV1.SUPERSESSION:
        if old[0].lifecycle is not CapabilityLifecycleStateV1.SUPERSEDED:
            raise ValueError("SUPERSESSION source must be SUPERSEDED")
        if new[0].lifecycle is not CapabilityLifecycleStateV1.ACTIVE:
            raise ValueError("SUPERSESSION successor must be ACTIVE")
    elif old[0].lifecycle is not CapabilityLifecycleStateV1.RETIRED:
        raise ValueError("RETIREMENT source must be RETIRED")


def _validate_supersession_cycles(events: Sequence[CapabilityEvolutionV1]) -> None:
    graph: dict[CapabilityRefV1, set[CapabilityRefV1]] = {}
    for event in events:
        if event.operation is EvolutionOperationV1.SUPERSESSION:
            source, target = event.from_references[0], event.to_references[0]
            successors = graph.setdefault(source, set())
            if successors and target not in successors:
                raise ValueError("multiple SUPERSESSION successors are ambiguous")
            successors.add(target)
    visiting: set[CapabilityRefV1] = set()
    visited: set[CapabilityRefV1] = set()

    def visit(node: CapabilityRefV1) -> None:
        if node in visiting:
            raise ValueError("SUPERSESSION evolution cycle detected")
        if node in visited:
            return
        visiting.add(node)
        for successor in graph.get(node, ()):
            visit(successor)
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node)


def validate_evolution_history(
    events: Sequence[CapabilityEvolutionV1],
    *,
    capabilities: Sequence[CapabilityDefinitionV1],
    reviews: Sequence[CapabilityReviewRecordV1],
    active_links: Sequence[object] = (),
) -> None:
    values = tuple(events)
    if any(not isinstance(item, CapabilityEvolutionV1) for item in values):
        raise TypeError("events must contain CapabilityEvolutionV1 values")
    if len({item.event_id for item in values}) != len(values):
        raise ValueError("duplicate evolution event")
    definitions = _capability_index(capabilities)
    consumed: set[CapabilityRefV1] = set()
    produced: set[CapabilityRefV1] = set()
    for event in values:
        if any(item not in definitions for item in event.from_references):
            raise ValueError("evolution source does not exist with exact claim digest")
        if any(item not in definitions for item in event.to_references):
            raise ValueError("evolution target does not exist with exact claim digest")
        if set(event.from_references) & consumed:
            raise ValueError("duplicate evolution source")
        if set(event.to_references) & produced:
            raise ValueError("duplicate evolution target")
        consumed.update(event.from_references)
        produced.update(event.to_references)
        _validate_review(event, reviews)
    _validate_supersession_cycles(values)
    for event in values:
        _validate_states(event, definitions)
    if active_links:
        from .link import RequirementCapabilityLinkV1

        for link in active_links:
            if not isinstance(link, RequirementCapabilityLinkV1):
                raise TypeError(
                    "active_links must contain RequirementCapabilityLinkV1 values"
                )
            if link.review_ref is None:
                continue
            target = definitions.get(link.capability)
            if target is None:
                raise ValueError("active link Capability reference does not exist")
            if target.lifecycle is not CapabilityLifecycleStateV1.ACTIVE:
                raise ValueError(
                    "new active link cannot target a superseded or retired Capability"
                )


__all__ = [
    "CapabilityEvolutionV1",
    "CapabilityRelationKindV1",
    "CapabilityRelationV1",
    "EVOLUTION_ID_DOMAIN",
    "EVOLUTION_ID_PREFIX",
    "EVOLUTION_SCHEMA",
    "EvolutionOperationV1",
    "RELATION_ID_DOMAIN",
    "RELATION_ID_PREFIX",
    "RELATION_SCHEMA",
    "addition_event",
    "composes_edge",
    "evolution_claim_digest_for",
    "evolution_event_id_for",
    "merge_event",
    "relation_claim_digest_for",
    "relation_sort_key",
    "requires_edge",
    "retirement_event",
    "sort_capability_relations",
    "specializes_edge",
    "split_event",
    "supersession_event",
    "validate_capability_edges",
    "validate_evolution_history",
]
