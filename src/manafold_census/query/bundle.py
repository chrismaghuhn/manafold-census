"""Validated, immutable-in-use data for the read-only query layer."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import cast

from ..analysis.model import CardAnalysisRecordV1
from ..analysis.trace import TraceEventV1, trace_sort_key
from ..analysis.validate import inspect_trace_shards
from ..canonical import canonical_json_bytes
from ..capability.admissibility import SourceRequirementAdmissibilityV1
from ..capability.build import _reread_output, _RereadResult
from ..capability.definition import CapabilityDefinitionV1
from ..capability.link import RequirementCapabilityLinkV1
from ..capability.mapping import RequirementMappingDecisionV1
from ..capability.model import CapabilityRefV1
from ..capability.review import CapabilityReviewRecordV1
from ..digest import sha256_bytes
from ..release.manifest import CensusBundleManifestV1
from ..release.publish import read_bundle_manifest
from ..reports.build import validate_census_derived_output
from ..reports.input import read_analysis_records, read_structural_records
from ..reports.report_model import CensusReportV1
from ..semantic.identity import wire_digest_for
from ..semantic.model import RequirementV1
from ..structural.model import StructuralCardRecordV1
from .cards import card_name_lookup_key
from .details import _requirement_link_sort_key
from .indexes import validate_index_row


def _collect_requirements(
    analysis_records: tuple[CardAnalysisRecordV1, ...],
) -> tuple[RequirementV1, ...]:
    values: dict[str, tuple[RequirementV1, str]] = {}
    for record in analysis_records:
        if record.bundle is None:
            continue
        for requirement in record.bundle.requirements:
            if requirement.source != record.source:
                raise ValueError(
                    "Requirement source does not match its analysis record"
                )
            digest = wire_digest_for(requirement)
            existing = values.get(requirement.requirement_id)
            if existing is not None and existing[1] != digest:
                raise ValueError("duplicate Requirement ID has different wire bytes")
            values.setdefault(requirement.requirement_id, (requirement, digest))
    return tuple(values[key][0] for key in sorted(values))


def _read_name_index(
    root: Path,
    structural_by_oracle: Mapping[str, StructuralCardRecordV1],
) -> Mapping[str, tuple[StructuralCardRecordV1, ...]]:
    path = root / "indexes/cards-by-name.jsonl"
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise FileNotFoundError("cards-by-name index cannot be read") from error
    values: dict[str, list[StructuralCardRecordV1]] = defaultdict(list)
    order_keys: list[tuple[str, str, str]] = []
    for line in raw.splitlines(keepends=True):
        if not line.endswith(b"\n"):
            raise ValueError("cards-by-name index is missing a final LF")
        try:
            document = json.loads(line)
            if line != canonical_json_bytes(document) + b"\n":
                raise ValueError("cards-by-name index is not canonical JSONL")
            validate_index_row("indexes/cards-by-name.jsonl", document)
        except (
            TypeError,
            ValueError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as error:
            raise ValueError("cards-by-name index contains an invalid row") from error
        row = cast(dict[str, object], document)
        oracle_id = cast(str, row["oracle_id"])
        record = structural_by_oracle.get(oracle_id)
        if record is None:
            raise ValueError("cards-by-name index references an unknown card")
        for field in ("name", "source_card_id", "source_record_sha256"):
            if row[field] != getattr(record, field):
                raise ValueError("cards-by-name index disagrees with source record")
        key = card_name_lookup_key(record.name)
        values[key].append(record)
        order_keys.append((cast(str, row["name"]), oracle_id, record.source_card_id))
    if order_keys != sorted(order_keys) or len({item[1] for item in order_keys}) != len(
        order_keys
    ):
        raise ValueError("cards-by-name index is not canonically ordered")
    if len(order_keys) != len(structural_by_oracle):
        raise ValueError("cards-by-name index does not cover every card")
    return MappingProxyType(
        {
            key: tuple(sorted(records, key=lambda item: (item.name, item.oracle_id)))
            for key, records in values.items()
        }
    )


@dataclass(frozen=True, slots=True)
class ValidatedQueryBundleV1:
    root: Path
    manifest: CensusBundleManifestV1
    report: CensusReportV1
    structural_records: tuple[StructuralCardRecordV1, ...]
    analysis_records: tuple[CardAnalysisRecordV1, ...]
    trace_events: tuple[TraceEventV1, ...]
    requirements: tuple[RequirementV1, ...]
    m4: _RereadResult
    structural_by_oracle: Mapping[str, StructuralCardRecordV1]
    analysis_by_oracle: Mapping[str, CardAnalysisRecordV1]
    name_index: Mapping[str, tuple[StructuralCardRecordV1, ...]]
    requirements_by_id: Mapping[str, RequirementV1]
    admissibility_by_requirement: Mapping[str, SourceRequirementAdmissibilityV1]
    decisions_by_requirement: Mapping[str, RequirementMappingDecisionV1]
    links_by_id: Mapping[str, RequirementCapabilityLinkV1]
    links_by_requirement: Mapping[str, tuple[RequirementCapabilityLinkV1, ...]]
    definitions_by_ref: Mapping[CapabilityRefV1, CapabilityDefinitionV1]
    reviews_by_id: Mapping[str, CapabilityReviewRecordV1]
    traces_by_source: Mapping[tuple[str, str, str, str], tuple[TraceEventV1, ...]]


def load_validated_query_bundle(
    bundle_directory: str | Path,
) -> ValidatedQueryBundleV1:
    """Validate the complete M5-06 tree before loading any query data."""

    root = Path(bundle_directory)
    derived = validate_census_derived_output(root)
    manifest = read_bundle_manifest(root)
    structural_records = read_structural_records(root)
    analysis_records = read_analysis_records(root)
    trace_result = inspect_trace_shards(root / "inputs/m3/trace")
    trace_events = tuple(cast(TraceEventV1, item) for item in trace_result.values)
    requirements = _collect_requirements(analysis_records)
    m4 = _reread_output(root / "inputs/m4")

    structural_by_oracle = MappingProxyType(
        {item.oracle_id: item for item in structural_records}
    )
    analysis_by_oracle = MappingProxyType(
        {item.source.oracle_id: item for item in analysis_records}
    )
    name_index = _read_name_index(root, structural_by_oracle)
    requirements_by_id = MappingProxyType(
        {item.requirement_id: item for item in requirements}
    )
    admissibility_by_requirement = MappingProxyType(
        {item.requirement_id: item for item in m4.admissibility}
    )
    decisions_by_requirement = MappingProxyType(
        {item.requirement_id: item for item in m4.decisions}
    )
    links_by_id = MappingProxyType({item.link_id: item for item in m4.links})
    links_by_requirement_values: dict[str, list[RequirementCapabilityLinkV1]] = (
        defaultdict(list)
    )
    for link in m4.links:
        links_by_requirement_values[link.requirement_id].append(link)
    links_by_requirement = MappingProxyType(
        {
            key: tuple(
                sorted(
                    values,
                    key=_requirement_link_sort_key,
                )
            )
            for key, values in links_by_requirement_values.items()
        }
    )
    definitions_by_ref = MappingProxyType(
        {item.capability_ref: item for item in m4.definitions}
    )
    reviews_by_id = MappingProxyType({item.record_id: item for item in m4.reviews})
    traces_by_source_values: dict[tuple[str, str, str, str], list[TraceEventV1]] = (
        defaultdict(list)
    )
    for event in trace_events:
        traces_by_source_values[event.card_source_key].append(event)
    traces_by_source = MappingProxyType(
        {
            key: tuple(sorted(values, key=trace_sort_key))
            for key, values in traces_by_source_values.items()
        }
    )

    if (
        sha256_bytes((root / "census-manifest.json").read_bytes())
        != derived.report.census_manifest_sha256
    ):
        raise ValueError("query bundle Census manifest identity is stale")
    return ValidatedQueryBundleV1(
        root,
        manifest,
        derived.report,
        structural_records,
        analysis_records,
        trace_events,
        requirements,
        m4,
        structural_by_oracle,
        analysis_by_oracle,
        name_index,
        requirements_by_id,
        admissibility_by_requirement,
        decisions_by_requirement,
        links_by_id,
        links_by_requirement,
        definitions_by_ref,
        reviews_by_id,
        traces_by_source,
    )


__all__ = ["ValidatedQueryBundleV1", "load_validated_query_bundle"]
