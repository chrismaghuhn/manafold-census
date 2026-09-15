"""Deterministic M3-to-M4 provenance traces for the query layer."""

from __future__ import annotations

from dataclasses import dataclass

from ..analysis.model import CardAnalysisRecordV1, card_source_key
from ..analysis.trace import TraceEventV1
from ..canonical import JSONValue
from ..capability.admissibility import SourceRequirementAdmissibilityV1
from ..capability.definition import CapabilityDefinitionV1
from ..capability.link import RequirementCapabilityLinkV1
from ..capability.mapping import RequirementMappingDecisionV1
from ..capability.review import CapabilityReviewRecordV1
from ..semantic.model import RequirementV1
from .bundle import ValidatedQueryBundleV1


def _definition_key(value: CapabilityDefinitionV1) -> tuple[str, int, str]:
    return (
        value.capability_family_id,
        value.capability_version,
        value.claim_digest,
    )


def _review_key(value: CapabilityReviewRecordV1) -> tuple[str, str]:
    return (value.record_id, value.review_digest)


def _related(
    bundle: ValidatedQueryBundleV1,
    links: tuple[RequirementCapabilityLinkV1, ...],
    decision: RequirementMappingDecisionV1,
) -> tuple[tuple[CapabilityDefinitionV1, ...], tuple[CapabilityReviewRecordV1, ...]]:
    definitions_by_ref: dict[object, CapabilityDefinitionV1] = {}
    for link in links:
        definition = bundle.definitions_by_ref.get(link.capability)
        if definition is None:
            raise ValueError("trace link references an unknown Capability")
        definitions_by_ref[link.capability] = definition
    definitions = tuple(sorted(definitions_by_ref.values(), key=_definition_key))
    review_ids = {item.review_ref for item in links if item.review_ref is not None}
    review_ids.update(
        item.review_ref for item in definitions if item.review_ref is not None
    )
    if decision.review_ref is not None:
        review_ids.add(decision.review_ref)
    reviews: list[CapabilityReviewRecordV1] = []
    for review_id in sorted(review_ids):
        review = bundle.reviews_by_id.get(review_id)
        if review is None:
            raise ValueError("trace references an unknown review record")
        reviews.append(review)
    return definitions, tuple(reviews)


@dataclass(frozen=True, slots=True)
class RequirementTraceV1:
    census_release_id: str
    census_manifest_sha256: str
    requirement: RequirementV1
    analysis_record: CardAnalysisRecordV1
    analysis_trace: tuple[TraceEventV1, ...]
    admissibility: SourceRequirementAdmissibilityV1
    links: tuple[RequirementCapabilityLinkV1, ...]
    mapping_decision: RequirementMappingDecisionV1
    capability_definitions: tuple[CapabilityDefinitionV1, ...]
    reviews: tuple[CapabilityReviewRecordV1, ...]

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "census_release_id": self.census_release_id,
            "census_manifest_sha256": self.census_manifest_sha256,
            "requirement": self.requirement.to_wire(),
            "analysis_record": self.analysis_record.to_wire(),
            "analysis_trace": [item.to_wire() for item in self.analysis_trace],
            "admissibility": self.admissibility.to_wire(),
            "links": [item.to_wire() for item in self.links],
            "mapping_decision": self.mapping_decision.to_wire(),
            "capability_definitions": [
                item.to_wire() for item in self.capability_definitions
            ],
            "reviews": [item.to_wire() for item in self.reviews],
        }


@dataclass(frozen=True, slots=True)
class MappingTraceV1:
    census_release_id: str
    census_manifest_sha256: str
    link: RequirementCapabilityLinkV1
    requirement: RequirementV1
    analysis_record: CardAnalysisRecordV1
    analysis_trace: tuple[TraceEventV1, ...]
    admissibility: SourceRequirementAdmissibilityV1
    mapping_decision: RequirementMappingDecisionV1
    capability_definition: CapabilityDefinitionV1
    reviews: tuple[CapabilityReviewRecordV1, ...]

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "census_release_id": self.census_release_id,
            "census_manifest_sha256": self.census_manifest_sha256,
            "link": self.link.to_wire(),
            "requirement": self.requirement.to_wire(),
            "analysis_record": self.analysis_record.to_wire(),
            "analysis_trace": [item.to_wire() for item in self.analysis_trace],
            "admissibility": self.admissibility.to_wire(),
            "mapping_decision": self.mapping_decision.to_wire(),
            "capability_definition": self.capability_definition.to_wire(),
            "reviews": [item.to_wire() for item in self.reviews],
        }


def _requirement_parts(
    bundle: ValidatedQueryBundleV1,
    requirement_id: str,
) -> tuple[
    RequirementV1,
    CardAnalysisRecordV1,
    tuple[TraceEventV1, ...],
    SourceRequirementAdmissibilityV1,
    tuple[RequirementCapabilityLinkV1, ...],
    RequirementMappingDecisionV1,
]:
    requirement = bundle.requirements_by_id[requirement_id]
    analysis_record = bundle.analysis_by_oracle[requirement.source.oracle_id]
    source_key = card_source_key(requirement.source)
    analysis_trace = bundle.traces_by_source.get(source_key, ())
    admissibility = bundle.admissibility_by_requirement[requirement_id]
    links = bundle.links_by_requirement.get(requirement_id, ())
    decision = bundle.decisions_by_requirement[requirement_id]
    return requirement, analysis_record, analysis_trace, admissibility, links, decision


def build_requirement_trace(
    bundle: ValidatedQueryBundleV1,
    requirement_id: str,
) -> RequirementTraceV1:
    """Assemble a complete trace for one exact persisted Requirement."""

    parts = _requirement_parts(bundle, requirement_id)
    requirement, analysis_record, analysis_trace, admissibility, links, decision = parts
    definitions, reviews = _related(bundle, links, decision)
    return RequirementTraceV1(
        bundle.manifest.census_release_id,
        bundle.report.census_manifest_sha256,
        requirement,
        analysis_record,
        analysis_trace,
        admissibility,
        links,
        decision,
        definitions,
        reviews,
    )


def build_mapping_trace(
    bundle: ValidatedQueryBundleV1,
    link_id: str,
) -> MappingTraceV1:
    """Assemble a complete trace for one exact published M4 link."""

    link = bundle.links_by_id[link_id]
    parts = _requirement_parts(bundle, link.requirement_id)
    requirement, analysis_record, analysis_trace, admissibility, _links, decision = (
        parts
    )
    definition = bundle.definitions_by_ref[link.capability]
    _definitions, reviews = _related(bundle, (link,), decision)
    return MappingTraceV1(
        bundle.manifest.census_release_id,
        bundle.report.census_manifest_sha256,
        link,
        requirement,
        analysis_record,
        analysis_trace,
        admissibility,
        decision,
        definition,
        reviews,
    )


__all__ = [
    "MappingTraceV1",
    "RequirementTraceV1",
    "build_mapping_trace",
    "build_requirement_trace",
]
