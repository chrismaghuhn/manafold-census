"""Validation for the complete typed M4 semantic relation set."""

from __future__ import annotations

from collections.abc import Sequence

from .claim import CompositionClaimV1
from .definition import CapabilityDefinitionV1, CapabilityLifecycleStateV1
from .model import CapabilityRefV1, NucleusKindV1
from .relations import CapabilityRelationKindV1, CapabilityRelationV1


def _capability_index(
    capabilities: Sequence[CapabilityDefinitionV1],
) -> dict[CapabilityRefV1, CapabilityDefinitionV1]:
    values = tuple(capabilities)
    if any(not isinstance(item, CapabilityDefinitionV1) for item in values):
        raise TypeError("capabilities must contain CapabilityDefinitionV1 values")
    result: dict[CapabilityRefV1, CapabilityDefinitionV1] = {}
    for capability in values:
        reference = capability.capability_ref
        if reference in result:
            raise ValueError("duplicate Capability reference")
        result[reference] = capability
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


def _composition(
    capability: CapabilityDefinitionV1,
    definitions: dict[CapabilityRefV1, CapabilityDefinitionV1],
) -> CompositionClaimV1:
    if capability.claim.family_key.nucleus_kind is not NucleusKindV1.COMPOSITE:
        raise ValueError("COMPOSES source must be a composite Capability")
    composition = capability.claim.composition
    if not isinstance(composition, CompositionClaimV1):
        raise ValueError("COMPOSITE Capability must declare a composition claim")
    component_anchors: set[object] = set()
    for component in composition.components:
        target = definitions.get(component.capability)
        if target is None:
            raise ValueError(
                "composition component Capability does not exist with exact "
                "claim digest"
            )
        component_anchors.update(target.claim.family_key.operation_anchor)
    if component_anchors != set(capability.claim.family_key.operation_anchor):
        raise ValueError("composite operation anchor does not match component nuclei")
    return composition


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
    compositions: dict[CapabilityRefV1, CompositionClaimV1] = {}
    if definitions:
        for capability in definitions.values():
            if capability.claim.family_key.nucleus_kind is NucleusKindV1.COMPOSITE:
                compositions[capability.capability_ref] = _composition(
                    capability, definitions
                )
        for relation in values:
            source = definitions.get(relation.from_capability)
            target = definitions.get(relation.to_capability)
            if source is None or target is None:
                raise ValueError("Capability relation endpoint does not exist exactly")
            if relation.relation_kind is not CapabilityRelationKindV1.COMPOSES:
                continue
            composition = compositions.get(relation.from_capability)
            if composition is None:
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
    for composite_ref, composition in compositions.items():
        expected = {
            (
                composite_ref,
                item.component_key,
                item.capability,
                item.ordinal,
                item.required,
            )
            for item in composition.components
        }
        actual: set[tuple[CapabilityRefV1, str, CapabilityRefV1, int, bool]] = set()
        for relation in values:
            if (
                relation.relation_kind is CapabilityRelationKindV1.COMPOSES
                and relation.from_capability == composite_ref
            ):
                assert relation.component_key is not None
                assert relation.ordinal is not None
                assert relation.required is not None
                actual.add(
                    (
                        relation.from_capability,
                        relation.component_key,
                        relation.to_capability,
                        relation.ordinal,
                        relation.required,
                    )
                )
        if actual != expected:
            if expected - actual:
                raise ValueError("declared component relations are missing")
            raise ValueError(
                "COMPOSES relation set does not exactly match component claim"
            )
