"""Producer-neutral reconciliation of validated M3 Requirement proposals."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from ..canonical import canonical_json_bytes
from ..semantic.bundle import RequirementBundleV1, RequirementRelationshipV1
from ..semantic.evidence import evidence_to_wire
from ..semantic.model import (
    ProvenanceV1,
    RequirementV1,
    ReviewStatusV1,
    ReviewV1,
)
from .producer import RelationshipProposalV1


class ReconciliationFailure(ValueError):
    """Raised when proposals cannot form a valid producer-neutral result."""


@dataclass(frozen=True, slots=True)
class ReconciliationResultV1:
    requirements: tuple[RequirementV1, ...]
    relationships: tuple[RequirementRelationshipV1, ...]
    outcome_is_unresolved: bool
    trace_dispositions: tuple[str, ...]
    disputed_candidates: tuple[RequirementV1, ...]

    DISPUTED_IDENTITY_DISPOSITION: ClassVar[str] = "DISPUTED_IDENTITY_OMITTED"


def _relationship_sort_key(
    relationship: RequirementRelationshipV1,
) -> tuple[str, str, str, int]:
    return (
        relationship.relationship_type.value,
        relationship.from_requirement_id,
        relationship.to_requirement_id,
        -1 if relationship.ordinal is None else relationship.ordinal,
    )


def _candidate_sort_key(requirement: RequirementV1) -> tuple[str, bytes]:
    return requirement.requirement_id, canonical_json_bytes(requirement.to_wire())


def _merge_compatible_candidates(
    candidates: tuple[RequirementV1, ...],
) -> RequirementV1:
    first = candidates[0]
    evidence_by_wire = {
        canonical_json_bytes(evidence_to_wire(item)): item
        for candidate in candidates
        for item in candidate.evidence
    }
    derivation_by_wire = {
        canonical_json_bytes(item.to_wire()): item
        for candidate in candidates
        for item in candidate.provenance.derivations
    }
    return RequirementV1.create(
        source=first.source,
        family=first.family,
        kind=first.kind,
        parameters=first.parameters,
        evidence=tuple(evidence_by_wire.values()),
        provenance=ProvenanceV1(tuple(derivation_by_wire.values())),
        review=ReviewV1(ReviewStatusV1.PROPOSED, None, None),
        resolution=first.resolution,
    )


def reconcile(
    candidates: list[RequirementV1] | tuple[RequirementV1, ...],
    relationship_proposals: list[RelationshipProposalV1]
    | tuple[RelationshipProposalV1, ...] = (),
) -> ReconciliationResultV1:
    """Reconcile already M2-valid proposals without semantic priority."""

    values = tuple(candidates)
    relationships = tuple(relationship_proposals)
    for candidate in values:
        if not isinstance(candidate, RequirementV1):
            raise ReconciliationFailure("candidate must be RequirementV1")
        if candidate.review.status is not ReviewStatusV1.PROPOSED:
            raise ReconciliationFailure("reconciliation requires PROPOSED candidates")
        if (
            candidate.review.reviewed_by is not None
            or candidate.review.reviewed_claim_digest is not None
        ):
            raise ReconciliationFailure(
                "PROPOSED candidates cannot have review metadata"
            )
    for proposal in relationships:
        if not isinstance(proposal, RelationshipProposalV1):
            raise ReconciliationFailure(
                "relationship proposal must be RelationshipProposalV1"
            )

    if not values:
        if relationships:
            raise ReconciliationFailure("relationship endpoint is missing")
        return ReconciliationResultV1((), (), False, (), ())

    source = values[0].source
    if any(candidate.source != source for candidate in values):
        raise ReconciliationFailure("candidate sources do not match")

    grouped: dict[str, list[RequirementV1]] = {}
    for candidate in values:
        grouped.setdefault(candidate.requirement_id, []).append(candidate)

    retained: list[RequirementV1] = []
    disputed: list[RequirementV1] = []
    dispositions: list[str] = []
    for requirement_id in sorted(grouped):
        group = tuple(grouped[requirement_id])
        resolution_wires = {
            canonical_json_bytes(candidate.resolution.to_wire()) for candidate in group
        }
        if len(resolution_wires) != 1:
            disputed.extend(group)
            dispositions.append(ReconciliationResultV1.DISPUTED_IDENTITY_DISPOSITION)
            continue
        retained.append(_merge_compatible_candidates(group))

    retained.sort(key=lambda requirement: requirement.requirement_id)
    retained_ids = {item.requirement_id for item in retained}
    normalized_relationships: tuple[RequirementRelationshipV1, ...] = ()
    if relationships:
        for proposal in relationships:
            relationship = proposal.relationship
            if (
                relationship.from_requirement_id not in retained_ids
                or relationship.to_requirement_id not in retained_ids
            ):
                raise ReconciliationFailure("relationship endpoint is missing")
        try:
            bundle = RequirementBundleV1(
                source,
                tuple(retained),
                tuple(proposal.relationship for proposal in relationships),
            )
        except (TypeError, ValueError) as error:
            raise ReconciliationFailure(str(error)) from error
        normalized_relationships = tuple(
            sorted(bundle.relationships, key=_relationship_sort_key)
        )

    disputed.sort(key=_candidate_sort_key)
    return ReconciliationResultV1(
        requirements=tuple(retained),
        relationships=normalized_relationships,
        outcome_is_unresolved=bool(disputed),
        trace_dispositions=tuple(dispositions),
        disputed_candidates=tuple(disputed),
    )


__all__ = [
    "ReconciliationFailure",
    "ReconciliationResultV1",
    "reconcile",
]
