"""Pure derived report and report-row construction."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Sequence
from enum import StrEnum
from typing import cast

from ..analysis.model import AnalysisOutcomeV1, CardAnalysisRecordV1, card_source_key
from ..canonical import JSONValue
from ..capability.admissibility import AdmissibilityDecisionV1
from ..capability.build import _RereadResult
from ..capability.definition import CapabilityLifecycleStateV1
from ..capability.input import M3RequirementCorpusV1
from ..capability.mapping import MappingDispositionV1, RequirementMappingDecisionV1
from ..semantic.model import ResolutionStateV1, ReviewStatusV1
from ..structural.model import StructuralCardRecordV1
from .model import CENSUS_REPORT_SCHEMA
from .report_model import CensusReportV1

UNRESOLVED_ROW_SCHEMA = "census.unresolved-analysis.v1"
MAPPING_QUEUE_ROW_SCHEMA = "census.mapping-review-queue.v1"


def _enum_counts(
    enum_type: type[StrEnum], values: Sequence[StrEnum]
) -> dict[str, JSONValue]:
    counts: Counter[str] = Counter(value.value for value in values)
    return {item.value: counts[item.value] for item in enum_type}


def _structural_key(
    record: StructuralCardRecordV1,
) -> tuple[str, str, str, str]:
    return (
        StructuralCardRecordV1.SCHEMA,
        record.oracle_id,
        record.source_card_id,
        record.source_record_sha256,
    )


def build_report(
    *,
    manifest_sha256: str,
    release_id: str,
    source_lock_digest: str,
    m3_manifest_sha256: str,
    m4_manifest_sha256: str,
    requirement_set_digest: str,
    population: dict[str, JSONValue],
    requirements: M3RequirementCorpusV1,
    structural_records: Sequence[StructuralCardRecordV1],
    analysis_records: Sequence[CardAnalysisRecordV1],
    reread: _RereadResult,
) -> CensusReportV1:
    requirement_values = tuple(requirements.requirements)
    requirements_by_id = {item.requirement_id: item for item in requirement_values}
    requirements_by_source: dict[tuple[str, str, str, str], list[str]] = defaultdict(
        list
    )
    for requirement in requirement_values:
        requirements_by_source[card_source_key(requirement.source)].append(
            requirement.requirement_id
        )
    for values in requirements_by_source.values():
        values.sort()

    definitions = {item.capability_ref: item for item in reread.definitions}
    links_by_id = {item.link_id: item for item in reread.links}
    mapped_link_ids: set[str] = set()
    mapped_requirement_ids: set[str] = set()
    active_refs_by_source: dict[tuple[str, str, str, str], set[object]] = defaultdict(
        set
    )
    for decision in reread.decisions:
        if decision.disposition is not MappingDispositionV1.MAPPED:
            continue
        requirement = requirements_by_id[decision.requirement_id]
        mapped_requirement_ids.add(decision.requirement_id)
        for link_id in decision.active_link_ids:
            link = links_by_id[link_id]
            definition = definitions[link.capability]
            if definition.lifecycle is not CapabilityLifecycleStateV1.ACTIVE:
                raise ValueError("MAPPED link does not target an active Capability")
            mapped_link_ids.add(link_id)
            active_refs_by_source[card_source_key(requirement.source)].add(
                link.capability
            )

    total_cards = len(structural_records)
    unresolved = [
        item
        for item in analysis_records
        if item.outcome is AnalysisOutcomeV1.UNRESOLVED_ANALYSIS
    ]
    unresolved_with_bundle = sum(
        item.bundle is not None and bool(item.bundle.requirements)
        for item in unresolved
    )
    analysis_counts = _enum_counts(
        AnalysisOutcomeV1, [item.outcome for item in analysis_records]
    )
    mapped_count = sum(
        item.disposition is MappingDispositionV1.MAPPED for item in reread.decisions
    )
    frequency: list[dict[str, JSONValue]] = []
    for definition in sorted(
        reread.definitions,
        key=lambda item: (
            item.capability_family_id,
            item.capability_version,
            item.claim_digest,
        ),
    ):
        selected = {
            link.requirement_id
            for link in reread.links
            if link.link_id in mapped_link_ids
            and link.capability == definition.capability_ref
        }
        frequency.append(
            {
                "capability": definition.capability_ref.to_wire(),
                "mapped_requirement_count": len(selected),
                "distinct_source_count": len(
                    {
                        card_source_key(requirements_by_id[item].source)
                        for item in selected
                    }
                ),
                "denominator": mapped_count,
                "denominator_label": "MAPPED_REQUIREMENTS",
            }
        )

    queue_counts = {
        "mapping_review_queue_count": sum(
            item.disposition is not MappingDispositionV1.MAPPED
            for item in reread.decisions
        ),
        "unreviewed_capability_definition_count": sum(
            item.review_ref is None for item in reread.definitions
        ),
        "unreviewed_link_count": sum(item.review_ref is None for item in reread.links),
        "unreviewed_evolution_count": sum(
            getattr(item, "review_ref", None) is None for item in reread.evolution
        ),
    }
    queue_counts["total_queue_count"] = sum(queue_counts.values())
    report = CensusReportV1(
        {
            "schema": CENSUS_REPORT_SCHEMA,
            "census_release_id": release_id,
            "census_manifest_sha256": manifest_sha256,
            "source_lock_digest": source_lock_digest,
            "m3_analysis_manifest_sha256": m3_manifest_sha256,
            "m4_manifest_sha256": m4_manifest_sha256,
            "requirement_set_digest": requirement_set_digest,
            "population": population,
            "source_coverage": {
                "numerator": total_cards,
                "denominator": total_cards,
                "denominator_label": "TOTAL_ORACLE_IDENTITIES",
            },
            "structural_coverage": {
                "numerator": len(structural_records),
                "denominator": total_cards,
                "denominator_label": "TOTAL_ORACLE_IDENTITIES",
            },
            "analysis_record_coverage": {
                "numerator": len(analysis_records),
                "denominator": total_cards,
                "denominator_label": "TOTAL_ORACLE_IDENTITIES",
            },
            "analysis_outcome_counts": analysis_counts,
            "requirement_presence": {
                "cards_with_persisted_requirements": len(requirements_by_source),
                "cards_without_persisted_requirements": total_cards
                - len(requirements_by_source),
                "persisted_requirement_count": len(requirement_values),
                "denominator": total_cards,
                "denominator_label": "TOTAL_ORACLE_IDENTITIES",
            },
            "m2_review_status_counts": _enum_counts(
                ReviewStatusV1, [item.review.status for item in requirement_values]
            ),
            "m2_resolution_state_counts": _enum_counts(
                ResolutionStateV1,
                [item.resolution.state for item in requirement_values],
            ),
            "m4_admissibility_status_counts": _enum_counts(
                AdmissibilityDecisionV1,
                [item.decision for item in reread.admissibility],
            ),
            "m4_mapping_disposition_counts": _enum_counts(
                MappingDispositionV1, [item.disposition for item in reread.decisions]
            ),
            "active_capability_mapping_presence": {
                "cards_with_active_capability_mappings": len(active_refs_by_source),
                "cards_without_active_capability_mappings": total_cards
                - len(active_refs_by_source),
                "mapped_requirement_count": len(mapped_requirement_ids),
                "denominator": total_cards,
                "denominator_label": "TOTAL_ORACLE_IDENTITIES",
            },
            "capability_lifecycle_counts": _enum_counts(
                CapabilityLifecycleStateV1,
                [item.lifecycle for item in reread.definitions],
            ),
            "unresolved_analysis": {
                "cards_with_persisted_requirements": unresolved_with_bundle,
                "cards_without_persisted_requirements": len(unresolved)
                - unresolved_with_bundle,
                "denominator": len(unresolved),
                "denominator_label": "UNRESOLVED_ANALYSIS_CARDS",
            },
            "explicit_negative_analysis": {
                "numerator": analysis_counts["NO_REQUIREMENTS_APPLICABLE"],
                "denominator": len(analysis_records),
                "denominator_label": "TOTAL_ANALYSIS_RECORDS",
            },
            "m4_outliers": {
                "numerator": sum(
                    item.disposition is MappingDispositionV1.OUTLIER
                    for item in reread.decisions
                ),
                "denominator": len(requirement_values),
                "denominator_label": "PERSISTED_REQUIREMENTS",
            },
            "ambiguities": {
                "numerator": sum(
                    item.disposition is MappingDispositionV1.AMBIGUOUS
                    for item in reread.decisions
                ),
                "denominator": len(requirement_values),
                "denominator_label": "PERSISTED_REQUIREMENTS",
            },
            "review_queues": cast(JSONValue, queue_counts),
            "mapped_subset_capability_frequency": cast(JSONValue, frequency),
        }
    )
    return report


def unresolved_rows(
    analysis_records: Sequence[CardAnalysisRecordV1],
) -> tuple[dict[str, JSONValue], ...]:
    rows: list[dict[str, JSONValue]] = []
    for record in analysis_records:
        if record.outcome is not AnalysisOutcomeV1.UNRESOLVED_ANALYSIS:
            continue
        ids = (
            ()
            if record.bundle is None
            else tuple(
                sorted(item.requirement_id for item in record.bundle.requirements)
            )
        )
        rows.append(
            {
                "schema": UNRESOLVED_ROW_SCHEMA,
                "source": record.source.to_wire(),
                "outcome": record.outcome.value,
                "persisted_requirement_ids": cast(JSONValue, list(ids)),
                "persisted_requirement_count": len(ids),
            }
        )
    return tuple(
        sorted(
            rows,
            key=lambda item: cast(dict[str, str], item["source"])["oracle_id"],
        )
    )


def mapping_queue_rows(
    decisions: Sequence[RequirementMappingDecisionV1],
) -> tuple[dict[str, JSONValue], ...]:
    return tuple(
        {
            "schema": MAPPING_QUEUE_ROW_SCHEMA,
            "requirement_id": decision.requirement_id,
            "requirement_wire_digest": decision.requirement_wire_digest,
            "decision": decision.to_wire(),
        }
        for decision in sorted(decisions, key=lambda item: item.requirement_id)
        if decision.disposition is not MappingDispositionV1.MAPPED
    )


__all__ = [
    "MAPPING_QUEUE_ROW_SCHEMA",
    "UNRESOLVED_ROW_SCHEMA",
    "build_report",
    "mapping_queue_rows",
    "unresolved_rows",
]
