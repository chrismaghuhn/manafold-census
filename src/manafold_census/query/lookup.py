"""Pure M5-08 name-resolution and Card/Capability detail builders."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from ..analysis.model import card_source_key
from ..capability.definition import CapabilityDefinitionV1
from ..capability.link import LinkRelationV1, RequirementCapabilityLinkV1
from ..capability.mapping import MappingDispositionV1
from ..capability.model import CapabilityRefV1, NucleusKindV1
from ..semantic.model import RequirementV1
from ..structural.model import StructuralCardRecordV1
from .bundle import ValidatedQueryBundleV1
from .cards import (
    RequirementSummaryV1,
    build_card_semantic_view,
    card_name_lookup_key,
)
from .details import (
    CapabilityDetailViewV1,
    CardDetailViewV1,
    CardIdentityV1,
    CardNameResolutionStatusV1,
    CardNameResolutionV1,
    MappedSubsetFrequencyV1,
    RequirementDetailViewV1,
    _supporting_link_sort_key,
)


def resolve_card_name_from_index(
    name: str,
    name_index: Mapping[str, Sequence[StructuralCardRecordV1]],
) -> CardNameResolutionV1:
    """Resolve one name key without fuzzy matching or silent selection."""

    key = card_name_lookup_key(name)
    records = tuple(name_index.get(key, ()))
    identities = tuple(
        CardIdentityV1.from_record(record)
        for record in sorted(records, key=lambda item: (item.name, item.oracle_id))
    )
    status = (
        CardNameResolutionStatusV1.UNKNOWN
        if not identities
        else CardNameResolutionStatusV1.RESOLVED
        if len(identities) == 1
        else CardNameResolutionStatusV1.AMBIGUOUS
    )
    return CardNameResolutionV1(name, key, status, identities)


def _supports_definition(
    definition: CapabilityDefinitionV1,
    link: RequirementCapabilityLinkV1,
) -> bool:
    if definition.claim.family_key.nucleus_kind is NucleusKindV1.ATOMIC:
        return link.capability == definition.capability_ref
    return (
        link.relation is LinkRelationV1.COMPOSITION_MEMBER
        and link.composition_context is not None
        and link.composition_context.composite == definition.capability_ref
    )


def build_capability_detail(
    bundle: ValidatedQueryBundleV1,
    capability_ref: CapabilityRefV1,
) -> CapabilityDetailViewV1:
    """Build one detail view from the already validated M4 publication."""

    definition = bundle.definitions_by_ref[capability_ref]
    definition_review = (
        None
        if definition.review_ref is None
        else bundle.reviews_by_id.get(definition.review_ref)
    )
    supporting_links = tuple(
        sorted(
            (
                link
                for link in bundle.m4.links
                if _supports_definition(definition, link)
            ),
            key=_supporting_link_sort_key,
        )
    )
    linked_requirements_by_id: dict[str, RequirementV1] = {}
    for link in supporting_links:
        requirement = bundle.requirements_by_id.get(link.requirement_id)
        if requirement is None:
            raise ValueError("Capability link references an unknown Requirement")
        linked_requirements_by_id[requirement.requirement_id] = requirement

    mapped_requirement_ids: set[str] = set()
    for decision in bundle.m4.decisions:
        if decision.disposition is not MappingDispositionV1.MAPPED:
            continue
        if any(
            _supports_definition(definition, bundle.links_by_id[link_id])
            for link_id in decision.active_link_ids
        ):
            mapped_requirement_ids.add(decision.requirement_id)

    mapped_cards_by_oracle: dict[str, CardIdentityV1] = {}
    for requirement_id in mapped_requirement_ids:
        requirement = bundle.requirements_by_id[requirement_id]
        card = bundle.structural_by_oracle.get(requirement.source.oracle_id)
        if card is None:
            raise ValueError("mapped Requirement references an unknown card")
        mapped_cards_by_oracle[card.oracle_id] = CardIdentityV1.from_record(card)

    denominator = sum(
        decision.disposition is MappingDispositionV1.MAPPED
        for decision in bundle.m4.decisions
    )
    return CapabilityDetailViewV1(
        census_release_id=bundle.manifest.census_release_id,
        census_manifest_sha256=bundle.report.census_manifest_sha256,
        definition=definition,
        definition_review=definition_review,
        links=supporting_links,
        linked_requirements=tuple(
            RequirementSummaryV1.from_requirement(item)
            for item in sorted(
                linked_requirements_by_id.values(),
                key=lambda value: value.requirement_id,
            )
        ),
        mapped_cards=tuple(
            sorted(mapped_cards_by_oracle.values(), key=lambda item: item.oracle_id)
        ),
        mapped_subset_frequency=MappedSubsetFrequencyV1(
            len(mapped_requirement_ids), denominator, "MAPPED_REQUIREMENTS"
        ),
    )


def build_card_detail(
    bundle: ValidatedQueryBundleV1,
    oracle_id: str,
) -> CardDetailViewV1:
    """Build one Card detail with active Capability detail views."""

    structural = bundle.structural_by_oracle[oracle_id]
    analysis = bundle.analysis_by_oracle[oracle_id]
    source_key = card_source_key(analysis.source)
    requirements = tuple(
        item
        for item in bundle.requirements
        if (
            item.source.record_schema,
            item.source.oracle_id,
            item.source.source_card_id,
            item.source.source_record_sha256,
        )
        == source_key
    )
    semantic_view = build_card_semantic_view(
        structural_record=structural,
        analysis_record=analysis,
        requirements=requirements,
        admissibility_by_requirement=bundle.admissibility_by_requirement,
        decisions_by_requirement=bundle.decisions_by_requirement,
        links_by_id=bundle.links_by_id,
        definitions_by_ref=bundle.definitions_by_ref,
        census_release_id=bundle.manifest.census_release_id,
        census_manifest_sha256=bundle.report.census_manifest_sha256,
        m3_analysis_manifest_sha256=bundle.report.m3_analysis_manifest_sha256,
        trace_event_count=len(bundle.traces_by_source.get(source_key, ())),
    )
    refs = {mapping.capability for mapping in semantic_view.active_capability_mappings}
    details = tuple(
        sorted(
            (build_capability_detail(bundle, ref) for ref in refs),
            key=lambda item: (
                item.definition.capability_family_id,
                item.definition.capability_version,
                item.definition.claim_digest,
            ),
        )
    )
    requirement_details = tuple(
        RequirementDetailViewV1(
            RequirementSummaryV1.from_requirement(requirement),
            bundle.admissibility_by_requirement[requirement.requirement_id],
            bundle.decisions_by_requirement[requirement.requirement_id],
            bundle.links_by_requirement.get(requirement.requirement_id, ()),
        )
        for requirement in requirements
    )
    return CardDetailViewV1(
        structural,
        semantic_view,
        requirement_details,
        details,
    )


__all__ = [
    "build_card_detail",
    "build_capability_detail",
    "resolve_card_name_from_index",
]
