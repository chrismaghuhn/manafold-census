"""Semantic validation for the M4 reference build."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, cast

from ..canonical import canonical_json_bytes
from ..semantic.identity import reviewed_claim_digest_for, wire_digest_for
from ..semantic.model import RequirementV1, ResolutionStateV1, ReviewStatusV1
from .admissibility import SourceRequirementAdmissibilityV1, active_admissibility_for
from .definition import (
    CapabilityDefinitionReviewSubjectV1,
    CapabilityDefinitionV1,
    CapabilityLifecycleStateV1,
    validate_active_definition,
)
from .evolution import (
    CapabilityEvolutionV1,
    evolution_claim_digest_for,
    validate_evolution_history,
)
from .input import M3RequirementCorpusV1
from .link import (
    LinkAdmissibilityBasisV1,
    LinkRelationV1,
    RequirementCapabilityLinkV1,
)
from .link_validation import validate_active_link, validate_active_links
from .manifest import M4_DIMENSION_REGISTRY_VERSION, M4OntologyManifestV1
from .mapping import (
    RequirementMappingDecisionV1,
    mapping_decision_claim_digest_for,
    mapping_decision_id_for,
    validate_mapping_decision,
)
from .model import CapabilityRefV1, NucleusKindV1
from .relations import CapabilityRelationV1, sort_capability_relations
from .review import (
    CapabilityLinkReviewSubjectV1,
    CapabilityReviewRecordV1,
    EvolutionReviewSubjectV1,
    MappingDecisionReviewSubjectV1,
    ReviewDecisionV1,
)


def _typed(values: Sequence[Any], expected: type[Any], label: str) -> tuple[Any, ...]:
    result = tuple(values)
    if any(not isinstance(value, expected) for value in result):
        raise TypeError(f"{label} must contain {expected.__name__} values")
    return result


def _capability_index(
    definitions: Sequence[CapabilityDefinitionV1],
) -> dict[CapabilityRefV1, CapabilityDefinitionV1]:
    result: dict[CapabilityRefV1, CapabilityDefinitionV1] = {}
    family_versions: set[tuple[str, int]] = set()
    for definition in _typed(
        definitions, CapabilityDefinitionV1, "capability_definitions"
    ):
        if CapabilityDefinitionV1.from_wire(definition.to_wire()) != definition:
            raise ValueError("Capability definition wire is not canonical")
        reference = definition.capability_ref
        if reference in result:
            raise ValueError("duplicate Capability reference")
        family_version = definition.capability_family_id, definition.capability_version
        if family_version in family_versions:
            raise ValueError("duplicate Capability family and version")
        family_versions.add(family_version)
        result[reference] = definition
    return result


def _validate_reviews(
    reviews: Sequence[CapabilityReviewRecordV1],
) -> tuple[CapabilityReviewRecordV1, ...]:
    result = cast(
        tuple[CapabilityReviewRecordV1, ...],
        _typed(reviews, CapabilityReviewRecordV1, "reviews"),
    )
    if len({record.record_id for record in result}) != len(result):
        raise ValueError("duplicate review record")
    decisions: dict[str, set[ReviewDecisionV1]] = {}
    for record in result:
        if CapabilityReviewRecordV1.from_wire(record.to_wire()) != record:
            raise ValueError("review record wire is not canonical")
        subject_key = canonical_json_bytes(record.subject.to_wire()).decode()
        decisions.setdefault(subject_key, set()).add(record.decision)
    if any(
        ReviewDecisionV1.ACCEPTED in values and ReviewDecisionV1.REJECTED in values
        for values in decisions.values()
    ):
        raise ValueError("conflicting accepted and rejected reviews")
    return result


def _requirements(corpus: M3RequirementCorpusV1) -> dict[str, RequirementV1]:
    return {item.requirement_id: item for item in corpus.requirements}


def _validate_admissibility(
    records: Sequence[SourceRequirementAdmissibilityV1],
    corpus: M3RequirementCorpusV1,
    requirements: Mapping[str, RequirementV1],
) -> dict[str, SourceRequirementAdmissibilityV1]:
    result: dict[str, SourceRequirementAdmissibilityV1] = {}
    for record in cast(
        tuple[SourceRequirementAdmissibilityV1, ...],
        _typed(records, SourceRequirementAdmissibilityV1, "admissibility_records"),
    ):
        if SourceRequirementAdmissibilityV1.from_wire(record.to_wire()) != record:
            raise ValueError("admissibility record wire is not canonical")
        if record.record_id in result:
            raise ValueError("duplicate admissibility record")
        requirement = requirements.get(record.requirement_id)
        if requirement is None:
            raise ValueError("admissibility Requirement does not exist")
        record.validate_m3_manifest(corpus.m3_analysis_manifest_sha256)
        record.validate_against_requirement(requirement)
        result[record.record_id] = record
    for requirement in requirements.values():
        active_admissibility_for(requirement, tuple(result.values()))
    return result


def _validate_link_shape(
    link: RequirementCapabilityLinkV1,
    requirement: RequirementV1,
    definitions: Mapping[CapabilityRefV1, CapabilityDefinitionV1],
    admissibility: Mapping[str, SourceRequirementAdmissibilityV1],
    corpus: M3RequirementCorpusV1,
) -> SourceRequirementAdmissibilityV1 | None:
    if link.m3_analysis_manifest_sha256 != corpus.m3_analysis_manifest_sha256:
        raise ValueError("link M3 manifest does not match the selected corpus")
    if link.requirement_wire_digest != wire_digest_for(requirement):
        raise ValueError("link Requirement wire is stale")
    expected_review = reviewed_claim_digest_for(requirement)
    if link.requirement_reviewed_claim_digest not in (None, expected_review):
        raise ValueError("link Requirement reviewed claim is stale")
    capability = definitions.get(link.capability)
    if capability is None:
        raise ValueError("link Capability reference does not exist exactly")
    if link.relation is LinkRelationV1.DIRECT:
        if capability.claim.family_key.nucleus_kind is not NucleusKindV1.ATOMIC:
            raise ValueError("DIRECT link requires an atomic Capability")
        if capability.claim.family_key.operation_anchor != (
            (requirement.family, requirement.kind),
        ):
            raise ValueError("DIRECT link operation anchor does not match Requirement")
    route = link.m4_requirement_admissibility
    sra: SourceRequirementAdmissibilityV1 | None = None
    if route is not None:
        if route.basis is LinkAdmissibilityBasisV1.M2_TERMINAL_ACCEPTANCE:
            if requirement.review.status is not ReviewStatusV1.ACCEPTED or (
                requirement.resolution.state is not ResolutionStateV1.COMPLETE
            ):
                raise ValueError(
                    "terminal admissibility requires M2 ACCEPTED and COMPLETE"
                )
        else:
            if route.record_id is None or route.review_digest is None:
                raise ValueError("source admissibility route is incomplete")
            sra = admissibility.get(route.record_id)
            if sra is None or sra.review_digest != route.review_digest:
                raise ValueError("link SRA reference does not match an exact record")
            sra.validate_m3_manifest(corpus.m3_analysis_manifest_sha256)
            sra.validate_against_requirement(requirement)
    elif requirement.review.status is ReviewStatusV1.ACCEPTED:
        raise ValueError("M2 ACCEPTED link requires terminal admissibility")
    if link.relation is LinkRelationV1.COMPOSITION_MEMBER:
        context = link.composition_context
        if context is None:
            raise ValueError("COMPOSITION_MEMBER link requires composition context")
        composite = definitions.get(context.composite)
        if composite is None or composite.claim.composition is None:
            raise ValueError("composition composite Capability is not declared")
        matches = tuple(
            item
            for item in composite.claim.composition.components
            if item.component_key == context.component_key
        )
        if len(matches) != 1 or matches[0].capability != capability.capability_ref:
            raise ValueError("composition component does not match its declared key")
    return sra


def _validate_links(
    links: Sequence[RequirementCapabilityLinkV1],
    corpus: M3RequirementCorpusV1,
    definitions: Mapping[CapabilityRefV1, CapabilityDefinitionV1],
    reviews: Sequence[CapabilityReviewRecordV1],
    admissibility: Mapping[str, SourceRequirementAdmissibilityV1],
) -> dict[str, RequirementCapabilityLinkV1]:
    values = cast(
        tuple[RequirementCapabilityLinkV1, ...],
        _typed(links, RequirementCapabilityLinkV1, "links"),
    )
    requirements = _requirements(corpus)
    result: dict[str, RequirementCapabilityLinkV1] = {}
    for link in values:
        if RequirementCapabilityLinkV1.from_wire(link.to_wire()) != link:
            raise ValueError("link wire is not canonical")
        if link.link_id in result:
            raise ValueError("duplicate link record")
        requirement = requirements.get(link.requirement_id)
        if requirement is None:
            raise ValueError("link Requirement does not exist exactly")
        sra = _validate_link_shape(
            link, requirement, definitions, admissibility, corpus
        )
        if link.review_ref is not None:
            composite = (
                definitions[link.composition_context.composite]
                if link.composition_context is not None
                else None
            )
            validate_active_link(
                link,
                requirement,
                definitions[link.capability],
                reviews=reviews,
                admissibility_record=sra,
                composite_capability=composite,
            )
        result[link.link_id] = link
    validate_active_links(
        values,
        capabilities=tuple(definitions.values()),
        requirements=requirements,
    )
    return result


def _validate_decisions(
    decisions: Sequence[RequirementMappingDecisionV1],
    corpus: M3RequirementCorpusV1,
    reviews: Sequence[CapabilityReviewRecordV1],
    links: Mapping[str, RequirementCapabilityLinkV1],
) -> tuple[RequirementMappingDecisionV1, ...]:
    values = cast(
        tuple[RequirementMappingDecisionV1, ...],
        _typed(decisions, RequirementMappingDecisionV1, "mapping_decisions"),
    )
    requirements = _requirements(corpus)
    by_requirement: dict[str, RequirementMappingDecisionV1] = {}
    mapped_links: set[str] = set()
    for decision in values:
        if RequirementMappingDecisionV1.from_wire(decision.to_wire()) != decision:
            raise ValueError("mapping decision wire is not canonical")
        if decision.requirement_id in by_requirement:
            raise ValueError("duplicate mapping decision")
        requirement = requirements.get(decision.requirement_id)
        if requirement is None:
            raise ValueError("mapping decision Requirement does not exist")
        if decision.m3_analysis_manifest_sha256 != corpus.m3_analysis_manifest_sha256:
            raise ValueError("mapping decision M3 manifest does not match corpus")
        decision.validate_against_requirement(requirement)
        validate_mapping_decision(decision, reviews)
        for link_id in decision.active_link_ids:
            link = links.get(link_id)
            if link is None or link.requirement_id != decision.requirement_id:
                raise ValueError("mapping decision references an unknown active link")
            if link.review_ref is None:
                raise ValueError("mapping decision references an inactive link")
            mapped_links.add(link_id)
        candidate_claims = {
            link.link_claim_digest
            for link in links.values()
            if link.requirement_id == decision.requirement_id
        }
        if not set(decision.candidate_link_claims).issubset(candidate_claims):
            raise ValueError("mapping decision references an unknown candidate link")
        by_requirement[decision.requirement_id] = decision
    expected = set(requirements)
    actual = set(by_requirement)
    if expected != actual:
        raise ValueError(
            "mapping decision coverage mismatch: "
            f"missing={len(expected - actual)} extra={len(actual - expected)}"
        )
    active = {link_id for link_id, link in links.items() if link.review_ref is not None}
    if active - mapped_links:
        raise ValueError("active link is not represented by a MAPPED decision")
    return values


def _validate_parent(
    parent_sha256: str | None,
    parent_manifest: M4OntologyManifestV1 | None,
) -> None:
    if parent_sha256 is None and parent_manifest is None:
        return
    if parent_sha256 is None or parent_manifest is None:
        raise ValueError("parent M4 manifest must be supplied as a matching pair")
    if not isinstance(parent_manifest, M4OntologyManifestV1):
        raise TypeError("parent_m4_manifest must be M4OntologyManifestV1")
    reread = M4OntologyManifestV1.from_wire(parent_manifest.to_wire())
    if reread != parent_manifest or reread.digest() != parent_sha256:
        raise ValueError("parent M4 manifest digest does not match supplied manifest")


def validate_m4_inputs(
    corpus: M3RequirementCorpusV1,
    parent_m4_manifest_sha256: str | None,
    parent_m4_manifest: M4OntologyManifestV1 | None,
    capability_definitions: Sequence[CapabilityDefinitionV1],
    reviews: Sequence[CapabilityReviewRecordV1],
    semantic_relations: Sequence[CapabilityRelationV1],
    admissibility_records: Sequence[SourceRequirementAdmissibilityV1],
    links: Sequence[RequirementCapabilityLinkV1],
    mapping_decisions: Sequence[RequirementMappingDecisionV1],
    evolution_records: Sequence[CapabilityEvolutionV1],
) -> None:
    if not isinstance(corpus, M3RequirementCorpusV1):
        raise TypeError("corpus must be M3RequirementCorpusV1")
    _validate_parent(parent_m4_manifest_sha256, parent_m4_manifest)
    definitions = _capability_index(capability_definitions)
    review_values = _validate_reviews(reviews)
    review_by_id = {record.record_id: record for record in review_values}
    definition_subjects = set()
    for definition in definitions.values():
        if definition.claim.m4_dimension_registry_version != (
            M4_DIMENSION_REGISTRY_VERSION
        ):
            raise ValueError("Capability claim dimension registry does not match M4")
        if definition.claim.m2_requirement_schema != corpus.m2_requirement_schema:
            raise ValueError("Capability claim M2 schema does not match M3 corpus")
        subject = CapabilityDefinitionReviewSubjectV1(
            definition.capability_family_id,
            definition.capability_version,
            definition.claim_digest,
        )
        definition_subjects.add(subject)
        if definition.review_ref is not None:
            review = review_by_id.get(definition.review_ref)
            if review is None or review.subject != subject:
                raise ValueError("Capability definition review reference is invalid")
        if (
            definition.lifecycle is CapabilityLifecycleStateV1.ACTIVE
            and definition.review_ref is None
        ):
            raise ValueError("active definition requires accepted review")
    relations = sort_capability_relations(semantic_relations)
    for relation in relations:
        if CapabilityRelationV1.from_wire(relation.to_wire()) != relation:
            raise ValueError("semantic relation wire is not canonical")
    from .relation_validation import validate_capability_edges

    validate_capability_edges(relations, tuple(definitions.values()))
    requirements = _requirements(corpus)
    admissibility = _validate_admissibility(admissibility_records, corpus, requirements)
    link_index = _validate_links(
        links, corpus, definitions, review_values, admissibility
    )
    for definition in definitions.values():
        if definition.lifecycle is not CapabilityLifecycleStateV1.ACTIVE:
            continue
        assert definition.review_ref is not None
        review = review_by_id[definition.review_ref]
        supporting = tuple(
            link
            for link in link_index.values()
            if link.review_ref is not None
            and (
                link.capability == definition.capability_ref
                if definition.claim.family_key.nucleus_kind is NucleusKindV1.ATOMIC
                else (
                    link.relation is LinkRelationV1.COMPOSITION_MEMBER
                    and link.composition_context is not None
                    and link.composition_context.composite == definition.capability_ref
                )
            )
        )
        validate_activation_eligibility(definition, review, corpus, supporting)
    decisions = _validate_decisions(
        mapping_decisions, corpus, review_values, link_index
    )
    events = cast(
        tuple[CapabilityEvolutionV1, ...],
        _typed(evolution_records, CapabilityEvolutionV1, "evolution_records"),
    )
    for event in events:
        if CapabilityEvolutionV1.from_wire(event.to_wire()) != event:
            raise ValueError("evolution wire is not canonical")
    validate_evolution_history(
        events,
        capabilities=tuple(definitions.values()),
        reviews=review_values,
        active_links=tuple(link_index.values()),
    )
    known_subjects = (
        definition_subjects
        | {
            CapabilityLinkReviewSubjectV1(link.link_id, link.link_claim_digest)
            for link in link_index.values()
        }
        | {
            MappingDecisionReviewSubjectV1(
                mapping_decision_id_for(decision),
                mapping_decision_claim_digest_for(decision),
            )
            for decision in decisions
        }
        | {
            EvolutionReviewSubjectV1(event.event_id, evolution_claim_digest_for(event))
            for event in events
        }
    )
    if any(record.subject not in known_subjects for record in review_values):
        raise ValueError("review subject does not exist in the M4 input set")


def validate_activation_eligibility(
    definition: CapabilityDefinitionV1,
    definition_review: CapabilityReviewRecordV1,
    corpus: M3RequirementCorpusV1,
    supporting_links: Sequence[RequirementCapabilityLinkV1],
) -> None:
    """Validate the multi-source or explicitly reviewed singleton gate."""

    validate_active_definition(
        definition,
        (definition_review,),
        selected_m3_manifest_sha256=corpus.m3_analysis_manifest_sha256,
        selected_requirements=corpus.requirements,
    )
    requirements = _requirements(corpus)
    admitted: list[RequirementV1] = []
    seen: set[str] = set()
    for link in supporting_links:
        if not isinstance(link, RequirementCapabilityLinkV1):
            raise TypeError(
                "supporting_links must contain RequirementCapabilityLinkV1 values"
            )
        if definition.claim.family_key.nucleus_kind is NucleusKindV1.ATOMIC:
            if link.capability != definition.capability_ref or link.review_ref is None:
                raise ValueError("supporting link does not bind the active definition")
        else:
            context = link.composition_context
            if (
                link.relation is not LinkRelationV1.COMPOSITION_MEMBER
                or context is None
                or context.composite != definition.capability_ref
                or link.review_ref is None
            ):
                raise ValueError("supporting link does not bind the active definition")
        requirement = requirements.get(link.requirement_id)
        if (
            requirement is None
            or wire_digest_for(requirement) != link.requirement_wire_digest
        ):
            raise ValueError("supporting link Requirement is stale or unknown")
        if requirement.requirement_id in seen:
            raise ValueError("supporting links contain a duplicate Requirement")
        if requirement.resolution.state is not ResolutionStateV1.COMPLETE:
            raise ValueError("supporting Requirement is not complete")
        route = link.m4_requirement_admissibility
        if requirement.review.status is ReviewStatusV1.ACCEPTED:
            if (
                route is None
                or route.basis is not LinkAdmissibilityBasisV1.M2_TERMINAL_ACCEPTANCE
            ):
                raise ValueError("supporting link lacks terminal M2 acceptance")
        elif requirement.review.status in (
            ReviewStatusV1.PROPOSED,
            ReviewStatusV1.IN_REVIEW,
        ):
            if (
                route is None
                or route.basis
                is not LinkAdmissibilityBasisV1.SOURCE_REQUIREMENT_ADMISSIBILITY
            ):
                raise ValueError("supporting link lacks source admissibility")
        else:
            raise ValueError("supporting Requirement is rejected")
        seen.add(requirement.requirement_id)
        admitted.append(requirement)
    basis = definition_review.generalization_basis
    if basis is None:
        raise ValueError("active definition requires generalization_basis")
    if basis.value == "MULTI_SOURCE_REUSE":
        sources = {
            (
                item.source.record_schema,
                item.source.oracle_id,
                item.source.source_card_id,
                item.source.source_record_sha256,
            )
            for item in admitted
        }
        if len(sources) < 2:
            raise ValueError("multi-source reuse requires two M1 sources")
    elif len(admitted) != 1:
        raise ValueError("singleton generalization requires one Requirement")


__all__ = ["validate_activation_eligibility", "validate_m4_inputs"]
