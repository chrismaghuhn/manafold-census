"""Deterministic, non-authoritative reports downstream of M4 publication."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from typing import Any, cast

from ..canonical import JSONValue, canonical_json_bytes
from ..digest import measure_file, sha256_bytes
from ..semantic.model import RequirementV1
from ..validation import validate_document
from .binding import BindingStateV1
from .build import M4BuildResultV1, _reread_output
from .definition import CapabilityDefinitionV1, CapabilityLifecycleStateV1
from .evolution import CapabilityEvolutionV1, EvolutionOperationV1
from .input import M3RequirementCorpusV1
from .link import LinkRelationV1, RequirementCapabilityLinkV1
from .manifest import M4_MANIFEST_FILENAME, M4OntologyManifestV1
from .mapping import MappingDispositionV1, RequirementMappingDecisionV1
from .model import CapabilityRefV1, NucleusKindV1
from .report_model import (
    REPORT_FILENAME,
    REPORT_INDEX_FILENAME,
    REPORT_INDEX_SCHEMA,
    REPORT_SCHEMA,
    CapabilityReportBuildResultV1,
    CapabilityReportDescriptorV1,
    CapabilityReportIndexV1,
    CapabilityReportV1,
    M3ReportContextV1,
)
from .review import CapabilityReviewRecordV1


def _sorted_unique_wires(values: Sequence[JSONValue]) -> list[JSONValue]:
    unique = {canonical_json_bytes(value): value for value in values}
    return [unique[key] for key in sorted(unique)]


def _enum_counts(enum_type: type[Any], values: Sequence[Any]) -> dict[str, JSONValue]:
    counts = Counter(item.value for item in values)
    return {member.value: counts[member.value] for member in enum_type}


def _capability_ref_wire(ref: CapabilityRefV1) -> dict[str, JSONValue]:
    return ref.to_wire()


def _supporting_links(
    definition: CapabilityDefinitionV1,
    links: Sequence[RequirementCapabilityLinkV1],
) -> tuple[RequirementCapabilityLinkV1, ...]:
    result: list[RequirementCapabilityLinkV1] = []
    for link in links:
        if link.review_ref is None:
            continue
        if definition.claim.family_key.nucleus_kind is NucleusKindV1.ATOMIC:
            if link.capability == definition.capability_ref:
                result.append(link)
        elif (
            link.relation is LinkRelationV1.COMPOSITION_MEMBER
            and link.composition_context is not None
            and link.composition_context.composite == definition.capability_ref
        ):
            result.append(link)
    return tuple(result)


def _requirements_per_capability(
    definitions: Sequence[CapabilityDefinitionV1],
    links: Sequence[RequirementCapabilityLinkV1],
    requirements: Mapping[str, RequirementV1],
) -> list[dict[str, JSONValue]]:
    rows: list[dict[str, JSONValue]] = []
    for definition in sorted(
        definitions,
        key=lambda item: (
            item.capability_family_id,
            item.capability_version,
            item.claim_digest,
        ),
    ):
        selected = _supporting_links(definition, links)
        ids = sorted({link.requirement_id for link in selected})
        sources = {
            (
                requirements[item].source.record_schema,
                requirements[item].source.oracle_id,
                requirements[item].source.source_card_id,
                requirements[item].source.source_record_sha256,
            )
            for item in ids
            if item in requirements
        }
        rows.append(
            {
                "capability": _capability_ref_wire(definition.capability_ref),
                "lifecycle": definition.lifecycle.value,
                "requirement_ids": cast(JSONValue, ids),
                "requirement_count": len(ids),
                "distinct_source_count": len(sources),
            }
        )
    return rows


def _capabilities_by_requirement_kind(
    definitions: Sequence[CapabilityDefinitionV1],
    links: Sequence[RequirementCapabilityLinkV1],
    requirements: Mapping[str, RequirementV1],
) -> list[dict[str, JSONValue]]:
    capability_by_ref = {item.capability_ref: item for item in definitions}
    counts: Counter[tuple[str, int, str, bool, str, str]] = Counter()
    for link in links:
        if link.review_ref is None:
            continue
        definition = capability_by_ref.get(link.capability)
        if definition is None or link.requirement_id not in requirements:
            continue
        requirement = requirements[link.requirement_id]
        counts[
            (
                definition.capability_family_id,
                definition.capability_version,
                definition.claim_digest,
                definition.lifecycle is CapabilityLifecycleStateV1.ACTIVE,
                requirement.family.value,
                requirement.kind.value,
            )
        ] += 1
    rows: list[dict[str, JSONValue]] = []
    for (family_id, version, claim_digest, active, family, kind), count in sorted(
        counts.items()
    ):
        rows.append(
            {
                "capability": {
                    "capability_family_id": family_id,
                    "capability_version": version,
                    "claim_digest": claim_digest,
                },
                "family": family,
                "kind": kind,
                "active": active,
                "link_count": count,
            }
        )
    return rows


def _dimension_distributions(
    definitions: Sequence[CapabilityDefinitionV1],
    links: Sequence[RequirementCapabilityLinkV1],
) -> list[dict[str, JSONValue]]:
    rows: list[dict[str, JSONValue]] = []
    for definition in sorted(
        definitions,
        key=lambda item: (
            item.capability_family_id,
            item.capability_version,
            item.claim_digest,
        ),
    ):
        bindings_by_path: dict[str, list[Any]] = defaultdict(list)
        for link in _supporting_links(definition, links):
            for binding in link.parameter_bindings:
                bindings_by_path[binding.path_key.value].append(binding)
        for dimension in definition.claim.dimensions:
            bindings = bindings_by_path[dimension.path_key.value]
            values = [
                cast(JSONValue, binding.value)
                for binding in bindings
                if binding.state is BindingStateV1.KNOWN
            ]
            rows.append(
                {
                    "capability": _capability_ref_wire(definition.capability_ref),
                    "path_key": dimension.path_key.value,
                    "known_count": sum(
                        binding.state is BindingStateV1.KNOWN for binding in bindings
                    ),
                    "unknown_count": sum(
                        binding.state is BindingStateV1.UNKNOWN for binding in bindings
                    ),
                    "not_applicable_count": sum(
                        binding.state is BindingStateV1.NOT_APPLICABLE
                        for binding in bindings
                    ),
                    "distinct_value_count": len(
                        {canonical_json_bytes(value) for value in values}
                    ),
                    "values": _sorted_unique_wires(values),
                }
            )
    return rows


def _report_wire(
    result: M4BuildResultV1,
    definitions: Sequence[CapabilityDefinitionV1],
    reviews: Sequence[CapabilityReviewRecordV1],
    evolution: Sequence[CapabilityEvolutionV1],
    links: Sequence[RequirementCapabilityLinkV1],
    decisions: Sequence[RequirementMappingDecisionV1],
    m3_context: M3ReportContextV1,
) -> dict[str, JSONValue]:
    requirements = {item.requirement_id: item for item in result.requirements}
    review_ids = {item.record_id for item in reviews}
    review_queue = {
        "capability_definitions": sum(item.review_ref is None for item in definitions),
        "links": sum(item.review_ref is None for item in links),
        "mapping_decisions": sum(item.review_ref is None for item in decisions),
        "evolution_records": sum(
            item.review_ref not in review_ids for item in evolution
        ),
        "candidate_clusters": 0,
    }
    return {
        "schema": REPORT_SCHEMA,
        "m4_manifest_sha256": result.manifest.digest(),
        "m3_context": m3_context.to_wire(),
        "capability_counts": _enum_counts(
            CapabilityLifecycleStateV1, [item.lifecycle for item in definitions]
        ),
        "mapping_counts": _enum_counts(
            MappingDispositionV1, [item.disposition for item in decisions]
        ),
        "requirements_per_capability": cast(
            JSONValue, _requirements_per_capability(definitions, links, requirements)
        ),
        "capabilities_by_requirement_kind": cast(
            JSONValue,
            _capabilities_by_requirement_kind(definitions, links, requirements),
        ),
        "parameter_dimension_distributions": cast(
            JSONValue, _dimension_distributions(definitions, links)
        ),
        "evolution_counts": _enum_counts(
            EvolutionOperationV1, [item.operation for item in evolution]
        ),
        "review_queue_sizes": cast(JSONValue, review_queue),
        "candidate_worklist": [],
    }


def _load_final_manifest(result: M4BuildResultV1) -> None:
    path = result.output_dir / M4_MANIFEST_FILENAME
    try:
        raw = path.read_bytes()
        document = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("finalized M4 manifest cannot be read") from error
    if raw != canonical_json_bytes(document):
        raise ValueError("finalized M4 manifest is not canonical")
    if sha256_bytes(raw) != result.manifest.digest():
        raise ValueError("finalized M4 manifest does not match the build result")
    validate_document(document, "capability-ontology-manifest.v1.schema.json")
    if M4OntologyManifestV1.from_wire(document) != result.manifest:
        raise ValueError("finalized M4 manifest does not match the build result")


def build_capability_reports(
    result: M4BuildResultV1,
    *,
    m3_context: M3RequirementCorpusV1 | None = None,
) -> CapabilityReportBuildResultV1:
    """Build and publish reports from one finalized M4 build result."""

    if not isinstance(result, M4BuildResultV1):
        raise TypeError("result must be M4BuildResultV1")
    _load_final_manifest(result)
    output_path = result.output_dir
    report_index_path = output_path / REPORT_INDEX_FILENAME
    reports_path = output_path / "reports"
    if report_index_path.exists():
        raise ValueError("report-index.json already exists")
    if reports_path.exists() and any(reports_path.iterdir()):
        raise ValueError("reports directory must be empty")

    reread = _reread_output(output_path)
    if reread.manifest != result.manifest:
        raise ValueError("reread M4 manifest changed")
    if m3_context is None:
        context = M3ReportContextV1.incomplete(
            result.manifest.m3_analysis_manifest_sha256,
            result.manifest.requirement_set_digest,
            len(result.requirements),
        )
    else:
        context = M3ReportContextV1.from_corpus(m3_context)
        if (
            context.m3_analysis_manifest_sha256
            != result.manifest.m3_analysis_manifest_sha256
            or context.requirement_set_digest != result.manifest.requirement_set_digest
            or m3_context.requirements != result.requirements
        ):
            raise ValueError("M3 report context does not match finalized M4 input")

    wire = _report_wire(
        result,
        reread.definitions,
        reread.reviews,
        reread.evolution,
        reread.links,
        reread.decisions,
        context,
    )
    validate_document(wire, "capability-report.v1.schema.json")
    report = CapabilityReportV1(wire, context)
    report_bytes = canonical_json_bytes(report.to_wire())
    reports_path.mkdir(parents=True, exist_ok=True)
    report_path = reports_path / REPORT_FILENAME
    report_path.write_bytes(report_bytes)
    measurement = measure_file(report_path)
    descriptor = CapabilityReportDescriptorV1(
        f"reports/{REPORT_FILENAME}", measurement.sha256, measurement.byte_length
    )
    report_index = CapabilityReportIndexV1(result.manifest.digest(), (descriptor,))
    validate_document(report_index.to_wire(), "capability-report.v1.schema.json")
    report_index_path.write_bytes(canonical_json_bytes(report_index.to_wire()))

    reread_report_bytes = report_path.read_bytes()
    if reread_report_bytes != report_bytes:
        raise ValueError("published Capability report changed during reread")
    reread_measurement = measure_file(report_path)
    if (
        reread_measurement.sha256 != descriptor.sha256
        or reread_measurement.byte_length != descriptor.byte_length
    ):
        raise ValueError("published Capability report descriptor changed during reread")
    if CapabilityReportV1.from_wire(json.loads(reread_report_bytes)) != report:
        raise ValueError("published Capability report wire changed during reread")
    reread_index_bytes = report_index_path.read_bytes()
    reread_index_document = json.loads(reread_index_bytes)
    if reread_index_bytes != canonical_json_bytes(reread_index_document):
        raise ValueError("published Capability report index is not canonical")
    reread_index = CapabilityReportIndexV1.from_wire(reread_index_document)
    if reread_index != report_index:
        raise ValueError("published Capability report index changed during reread")
    return CapabilityReportBuildResultV1(report, report_index)


__all__ = [
    "CapabilityReportBuildResultV1",
    "CapabilityReportDescriptorV1",
    "CapabilityReportIndexV1",
    "CapabilityReportV1",
    "M3ReportContextV1",
    "REPORT_INDEX_SCHEMA",
    "REPORT_SCHEMA",
    "build_capability_reports",
]
