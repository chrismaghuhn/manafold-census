"""Small read-only Census query interface."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..analysis.model import CardAnalysisRecordV1, card_source_key
from ..capability.model import CapabilityRefV1
from ..structural.model import StructuralCardRecordV1
from .bundle import ValidatedQueryBundleV1, load_validated_query_bundle
from .cards import (
    CardSemanticViewV1,
    QueryNotFoundV1,
    RequirementSummaryV1,
    build_card_semantic_view,
)
from .details import (
    CapabilityDetailViewV1,
    CardDetailViewV1,
    CardIdentityV1,
    CardNameResolutionStatusV1,
    CardNameResolutionV1,
)
from .lookup import (
    build_capability_detail,
    build_card_detail,
    resolve_card_name_from_index,
)
from .provenance import (
    MappingTraceV1,
    RequirementTraceV1,
    build_mapping_trace,
    build_requirement_trace,
)


@dataclass(frozen=True, slots=True)
class QueryMetadataV1:
    census_release_version: str
    census_release_id: str
    census_manifest_sha256: str
    source_lock_digest: str
    m3_analysis_manifest_sha256: str
    m4_manifest_sha256: str
    query_contract: str
    semantic_coverage_limitation: str


@dataclass(frozen=True, slots=True)
class CensusReader:
    """Read-only adapter over one validated Census tree."""

    _bundle: ValidatedQueryBundleV1

    def metadata(self) -> QueryMetadataV1:
        manifest = self._bundle.manifest
        return QueryMetadataV1(
            manifest.census_release_version,
            manifest.census_release_id,
            self._bundle.report.census_manifest_sha256,
            manifest.source_lock_digest,
            self._bundle.report.m3_analysis_manifest_sha256,
            self._bundle.report.m4_manifest_sha256,
            manifest.compatibility.query_contract,
            "Census 0.1 records complete pinned-source accounting; unresolved "
            "analysis is not a claim of absent semantics.",
        )

    def get_structural_record(
        self, oracle_id: str
    ) -> StructuralCardRecordV1 | QueryNotFoundV1:
        result = self._bundle.structural_by_oracle.get(oracle_id)
        return (
            result
            if result is not None
            else QueryNotFoundV1("structural_record", oracle_id)
        )

    def get_analysis_record(
        self, oracle_id: str
    ) -> CardAnalysisRecordV1 | QueryNotFoundV1:
        result = self._bundle.analysis_by_oracle.get(oracle_id)
        return (
            result
            if result is not None
            else QueryNotFoundV1("analysis_record", oracle_id)
        )

    def get_card_semantic_view(
        self, oracle_id: str
    ) -> CardSemanticViewV1 | QueryNotFoundV1:
        structural = self._bundle.structural_by_oracle.get(oracle_id)
        analysis = self._bundle.analysis_by_oracle.get(oracle_id)
        if structural is None or analysis is None:
            return QueryNotFoundV1("card_semantic_view", oracle_id)
        source_key = card_source_key(analysis.source)
        requirements = tuple(
            item
            for item in self._bundle.requirements
            if card_source_key(item.source) == source_key
        )
        return build_card_semantic_view(
            structural_record=structural,
            analysis_record=analysis,
            requirements=requirements,
            admissibility_by_requirement=self._bundle.admissibility_by_requirement,
            decisions_by_requirement=self._bundle.decisions_by_requirement,
            links_by_id=self._bundle.links_by_id,
            definitions_by_ref=self._bundle.definitions_by_ref,
            census_release_id=self._bundle.manifest.census_release_id,
            census_manifest_sha256=self._bundle.report.census_manifest_sha256,
            m3_analysis_manifest_sha256=self._bundle.report.m3_analysis_manifest_sha256,
            trace_event_count=len(self._bundle.traces_by_source.get(source_key, ())),
        )

    def resolve_card_name(self, name: str) -> CardNameResolutionV1:
        return resolve_card_name_from_index(name, self._bundle.name_index)

    def search_cards(self, query: str) -> CardNameResolutionV1:
        """Resolve a card name using the exact M5-08 lookup contract."""

        return self.resolve_card_name(query)

    def list_card_semantic_views(self) -> tuple[CardSemanticViewV1, ...]:
        """Return all CardSemanticView values in canonical Oracle order."""

        views: list[CardSemanticViewV1] = []
        for record in self._bundle.structural_records:
            view = self.get_card_semantic_view(record.oracle_id)
            if isinstance(view, QueryNotFoundV1):
                raise ValueError("validated card is missing a semantic view")
            views.append(view)
        return tuple(views)

    def get_card(self, oracle_id: str) -> CardDetailViewV1 | QueryNotFoundV1:
        if oracle_id not in self._bundle.structural_by_oracle:
            return QueryNotFoundV1("card_detail", oracle_id)
        return build_card_detail(self._bundle, oracle_id)

    def get_card_by_name(self, name: str) -> CardDetailViewV1 | CardNameResolutionV1:
        resolution = self.resolve_card_name(name)
        if resolution.status is not CardNameResolutionStatusV1.RESOLVED:
            return resolution
        return build_card_detail(self._bundle, resolution.matches[0].oracle_id)

    def get_capability(
        self, capability_ref: CapabilityRefV1
    ) -> CapabilityDetailViewV1 | QueryNotFoundV1:
        if capability_ref not in self._bundle.definitions_by_ref:
            return QueryNotFoundV1("capability_detail", str(capability_ref))
        return build_capability_detail(self._bundle, capability_ref)

    def list_capabilities(self) -> tuple[CapabilityDetailViewV1, ...]:
        """Return all Capability details in canonical Capability order."""

        refs = sorted(
            self._bundle.definitions_by_ref,
            key=lambda ref: (
                ref.capability_family_id,
                ref.capability_version,
                ref.claim_digest,
            ),
        )
        return tuple(build_capability_detail(self._bundle, ref) for ref in refs)

    def get_requirements_for_capability(
        self, capability_ref: CapabilityRefV1
    ) -> tuple[RequirementSummaryV1, ...] | QueryNotFoundV1:
        """Return the exact Requirements linked to one Capability."""

        detail = self.get_capability(capability_ref)
        if isinstance(detail, QueryNotFoundV1):
            return detail
        return detail.linked_requirements

    def get_capabilities_for_card(
        self, oracle_id: str
    ) -> tuple[CapabilityDetailViewV1, ...] | QueryNotFoundV1:
        detail = self.get_card(oracle_id)
        if isinstance(detail, QueryNotFoundV1):
            return detail
        return detail.capability_details

    def get_cards_for_capability(
        self, capability_ref: CapabilityRefV1
    ) -> tuple[CardIdentityV1, ...] | QueryNotFoundV1:
        detail = self.get_capability(capability_ref)
        if isinstance(detail, QueryNotFoundV1):
            return detail
        return detail.mapped_cards

    def trace_requirement(
        self, requirement_id: str
    ) -> RequirementTraceV1 | QueryNotFoundV1:
        if requirement_id not in self._bundle.requirements_by_id:
            return QueryNotFoundV1("requirement_trace", requirement_id)
        return build_requirement_trace(self._bundle, requirement_id)

    def trace_mapping(self, link_id: str) -> MappingTraceV1 | QueryNotFoundV1:
        if link_id not in self._bundle.links_by_id:
            return QueryNotFoundV1("mapping_trace", link_id)
        return build_mapping_trace(self._bundle, link_id)


def open_bundle(bundle_directory: str | Path) -> CensusReader:
    """Validate and open one explicit M5-06 Census tree read-only."""

    return CensusReader(load_validated_query_bundle(bundle_directory))


__all__ = ["CensusReader", "QueryMetadataV1", "open_bundle"]
