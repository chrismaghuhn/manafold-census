"""Safe Rich renderers for the offline Census Explorer."""

from __future__ import annotations

import json
from collections.abc import Sequence

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..capability.model import CapabilityRefV1
from ..query.api import QueryMetadataV1
from ..query.cards import CardSemanticViewV1, QueryNotFoundV1
from ..query.deck import DeckAnalysisV1, DeckSectionAnalysisV1
from ..query.details import (
    CapabilityDetailViewV1,
    CardDetailViewV1,
    CardNameResolutionV1,
)
from ..query.provenance import MappingTraceV1, RequirementTraceV1


def _cell(value: object) -> Text:
    return Text(str(value))


def _fields(title: str, values: Sequence[tuple[str, object]]) -> Table:
    table = Table(title=title, show_header=False)
    table.add_column("field", style="cyan", no_wrap=True)
    table.add_column("value", overflow="fold")
    for label, value in values:
        table.add_row(_cell(label), _cell(value))
    return table


def render_view_context(metadata: QueryMetadataV1) -> RenderableType:
    return _fields(
        "Census Explorer context",
        (
            ("Explorer version", "0.1.0"),
            ("Census release version", metadata.census_release_version),
            ("Census release", metadata.census_release_id),
            ("Census manifest SHA", metadata.census_manifest_sha256),
            ("Source-lock digest", metadata.source_lock_digest),
            ("M3 analysis manifest SHA", metadata.m3_analysis_manifest_sha256),
            ("M4 manifest SHA", metadata.m4_manifest_sha256),
            ("Query contract", metadata.query_contract),
            ("Semantic coverage limitation", metadata.semantic_coverage_limitation),
        ),
    )


def render_info(metadata: QueryMetadataV1) -> RenderableType:
    return render_view_context(metadata)


def render_not_found(value: QueryNotFoundV1) -> RenderableType:
    return Panel(
        _fields(
            "Query not found",
            (("resource", value.resource), ("identifier", value.identifier)),
        ),
        title="NOT_FOUND",
    )


def render_card_search(resolution: CardNameResolutionV1) -> RenderableType:
    matches = Table(title=f"matches={len(resolution.matches)}")
    matches.add_column("name", overflow="fold")
    matches.add_column("oracle_id", overflow="fold")
    matches.add_column("source_card_id", overflow="fold")
    for identity in resolution.matches:
        matches.add_row(
            _cell(identity.name),
            _cell(identity.oracle_id),
            _cell(identity.source_card_id),
        )
    summary = _fields(
        "Card name resolution",
        (
            ("status", resolution.status.value),
            ("query", resolution.query),
            ("lookup_key", resolution.lookup_key),
        ),
    )
    return Group(summary, matches)


def render_card_detail(detail: CardDetailViewV1) -> RenderableType:
    semantic = detail.semantic_view
    summary = _fields(
        "Card detail",
        (
            ("name", detail.structural_record.name),
            ("oracle_id", detail.structural_record.oracle_id),
            ("source_card_id", detail.structural_record.source_card_id),
            ("analysis_outcome", semantic.analysis_outcome.value),
            ("semantic_state", semantic.semantic_state.value),
            ("requirements", len(semantic.requirements)),
            ("active_capability_mappings", len(semantic.active_capability_mappings)),
            ("census_release_id", semantic.provenance.census_release_id),
            ("census_manifest_sha256", semantic.provenance.census_manifest_sha256),
            ("trace_event_count", semantic.provenance.trace_event_count),
        ),
    )
    requirements = Table(title=f"requirements={len(detail.requirement_details)}")
    requirements.add_column("requirement_id", overflow="fold")
    requirements.add_column("review")
    requirements.add_column("resolution")
    requirements.add_column("mapping")
    for requirement_detail in detail.requirement_details:
        requirements.add_row(
            _cell(requirement_detail.requirement_id),
            _cell(requirement_detail.summary.review_status.value),
            _cell(requirement_detail.summary.resolution_state.value),
            _cell(requirement_detail.mapping_decision.disposition.value),
        )
    capabilities = Table(title=f"capabilities={len(detail.capability_details)}")
    capabilities.add_column("display_name", overflow="fold")
    capabilities.add_column("capability_ref", overflow="fold")
    capabilities.add_column("lifecycle")
    capabilities.add_column("links")
    for capability_detail in detail.capability_details:
        capabilities.add_row(
            _cell(capability_detail.definition.display_name),
            _cell(_capability_ref_text(capability_detail.definition.capability_ref)),
            _cell(capability_detail.definition.lifecycle.value),
            _cell(len(capability_detail.links)),
        )
    return Group(summary, requirements, capabilities)


def _capability_ref_text(ref: CapabilityRefV1) -> str:
    return f"{ref.capability_family_id}/{ref.capability_version}/{ref.claim_digest}"


def render_capability_list(
    details: Sequence[CapabilityDetailViewV1],
) -> RenderableType:
    table = Table(title=f"capabilities={len(details)}")
    table.add_column("display_name", overflow="fold")
    table.add_column("capability_ref", overflow="fold")
    table.add_column("lifecycle")
    table.add_column("mapped_cards")
    table.add_column("mapped_subset")
    for detail in details:
        table.add_row(
            _cell(detail.definition.display_name),
            _cell(_capability_ref_text(detail.definition.capability_ref)),
            _cell(detail.definition.lifecycle.value),
            _cell(len(detail.mapped_cards)),
            _cell(
                f"{detail.mapped_requirement_count}/"
                f"{detail.mapped_subset_denominator} "
                f"{detail.mapped_subset_denominator_label}"
            ),
        )
    return table


def render_capability_detail(detail: CapabilityDetailViewV1) -> RenderableType:
    summary = _fields(
        "Capability detail",
        (
            ("display_name", detail.definition.display_name),
            ("capability_ref", _capability_ref_text(detail.definition.capability_ref)),
            ("lifecycle", detail.definition.lifecycle.value),
            ("definition_review", detail.definition.review_ref or "NONE"),
            ("linked_requirements", len(detail.linked_requirements)),
            ("supporting_links", len(detail.links)),
            ("mapped_cards", len(detail.mapped_cards)),
            ("mapped_requirement_count", detail.mapped_requirement_count),
            ("mapped_subset_denominator", detail.mapped_subset_denominator),
            ("mapped_subset_denominator_label", detail.mapped_subset_denominator_label),
            ("census_release_id", detail.census_release_id),
            ("census_manifest_sha256", detail.census_manifest_sha256),
        ),
    )
    links = Table(title=f"supporting_links={len(detail.links)}")
    links.add_column("link_id", overflow="fold")
    links.add_column("requirement_id", overflow="fold")
    links.add_column("relation")
    links.add_column("claim_digest")
    for link in detail.links:
        links.add_row(
            _cell(link.link_id),
            _cell(link.requirement_id),
            _cell(link.relation.value),
            _cell(link.link_claim_digest),
        )
    return Group(summary, links)


def _trace_text(
    title: str,
    value: RequirementTraceV1 | MappingTraceV1,
) -> RenderableType:
    document = value.to_wire()
    return Panel(
        Text(json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2)),
        title=title,
    )


def render_requirement_trace(trace: RequirementTraceV1) -> RenderableType:
    return _trace_text("Requirement trace", trace)


def render_mapping_trace(trace: MappingTraceV1) -> RenderableType:
    return _trace_text("Mapping trace", trace)


def render_unresolved(
    views: Sequence[CardSemanticViewV1],
) -> RenderableType:
    table = Table(title=f"unresolved_cards={len(views)}")
    table.add_column("oracle_id", overflow="fold")
    table.add_column("analysis_outcome")
    table.add_column("semantic_state")
    table.add_column("requirements")
    for view in views:
        table.add_row(
            _cell(view.oracle_id),
            _cell(view.analysis_outcome.value),
            _cell(view.semantic_state.value),
            _cell(len(view.requirements)),
        )
    states = tuple(
        Text(f"semantic_state={view.semantic_state.value}") for view in views
    )
    return Group(Text(f"unresolved_cards={len(views)}"), *states, table)


def _render_deck_section(section: DeckSectionAnalysisV1) -> Table:
    values = (
        ("section", section.section.value),
        ("declared_card_count", section.declared_card_count),
        ("resolved_card_count", section.resolved_card_count),
        (
            "unique_resolved_oracle_identity_count",
            section.unique_resolved_oracle_identity_count,
        ),
        ("unknown_names", len(section.unknown_names)),
        ("ambiguous_names", len(section.ambiguous_names)),
        ("invalid_line_count", section.invalid_line_count),
        (
            "analysis_outcome_denominator",
            f"{section.analysis_outcome_denominator} "
            f"{section.analysis_outcome_denominator_label}",
        ),
        (
            "m2_review_status_denominator",
            f"{section.m2_review_status_denominator} "
            f"{section.m2_review_status_denominator_label}",
        ),
        (
            "m4_mapping_disposition_denominator",
            f"{section.m4_mapping_disposition_denominator} "
            f"{section.m4_mapping_disposition_denominator_label}",
        ),
        ("established_cards", len(section.established_cards)),
        (
            "partially_established_cards",
            len(section.partially_established_cards),
        ),
        ("unresolved_cards", len(section.unresolved_cards)),
        ("explicit_negative_cards", len(section.explicit_negative_cards)),
    )
    return _fields(f"Deck {section.section.value}", values)


def _render_deck_name_resolutions(section: DeckSectionAnalysisV1) -> Table:
    table = Table(title=f"{section.section.value} name resolutions")
    table.add_column("status")
    table.add_column("name", overflow="fold")
    table.add_column("quantity")
    for unknown_name in section.unknown_names:
        table.add_row(
            _cell("UNKNOWN"), _cell(unknown_name.name), _cell(unknown_name.quantity)
        )
    for ambiguous_name in section.ambiguous_names:
        table.add_row(
            _cell("AMBIGUOUS"),
            _cell(ambiguous_name.name),
            _cell(ambiguous_name.quantity),
        )
    return table


def render_deck_analysis(analysis: DeckAnalysisV1) -> RenderableType:
    header = _fields(
        "Deck analysis",
        (
            ("schema", analysis.SCHEMA),
            ("deck_input_sha256", analysis.deck_input_sha256),
            ("census_release_id", analysis.census_release_id),
            ("census_manifest_sha256", analysis.census_manifest_sha256),
            ("source_lock_digest", analysis.source_lock_digest),
            ("m3_analysis_manifest_sha256", analysis.m3_analysis_manifest_sha256),
            ("m4_manifest_sha256", analysis.m4_manifest_sha256),
            ("invalid_lines", len(analysis.invalid_lines)),
        ),
    )
    return Group(
        header,
        _render_deck_section(analysis.main),
        _render_deck_name_resolutions(analysis.main),
        _render_deck_section(analysis.sideboard),
        _render_deck_name_resolutions(analysis.sideboard),
    )


__all__ = [
    "render_card_detail",
    "render_card_search",
    "render_capability_detail",
    "render_capability_list",
    "render_deck_analysis",
    "render_info",
    "render_mapping_trace",
    "render_not_found",
    "render_requirement_trace",
    "render_unresolved",
    "render_view_context",
]
