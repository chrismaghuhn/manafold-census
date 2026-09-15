from __future__ import annotations

from pathlib import Path

import pytest
from analysis_fixtures import structural_record
from capability_m3_fixtures import (
    no_requirements_applicable_record,
    record_with_proposed_requirement,
    unresolved_record_with_requirement,
)
from test_census_bundle import _build_bundle

from manafold_census.analysis.model import AnalysisOutcomeV1
from manafold_census.capability.mapping import (
    MappingDispositionV1,
    MappingReasonV1,
    mapping_decision,
)
from manafold_census.query.api import open_bundle
from manafold_census.query.cards import (
    QueryNotFoundV1,
    SemanticStateV1,
    build_card_semantic_view,
    semantic_state_for,
)
from manafold_census.reports.build import build_census_derived

ORACLE_ID = "abcdefab-abcd-4abc-8abc-abcdefabcdef"
UNKNOWN_ORACLE_ID = "00000000-0000-4000-8000-000000000000"


def _derived_bundle(tmp_path: Path) -> Path:
    _package, bundle = _build_bundle(tmp_path / "fixture")
    return build_census_derived(bundle.output_dir, tmp_path / "derived").output_dir


def test_open_bundle_exposes_validated_metadata_and_established_view(
    tmp_path: Path,
) -> None:
    root = _derived_bundle(tmp_path)
    reader = open_bundle(root)

    metadata = reader.metadata()
    assert metadata.census_release_version == "0.1.0"
    assert metadata.census_release_id.startswith("censusrel_")
    assert len(metadata.census_manifest_sha256) == 64
    assert metadata.query_contract == "census.query.v1"
    assert metadata.semantic_coverage_limitation

    structural = reader.get_structural_record(ORACLE_ID)
    analysis = reader.get_analysis_record(ORACLE_ID)
    view = reader.get_card_semantic_view(ORACLE_ID)
    assert structural.oracle_id == ORACLE_ID
    assert analysis.source.oracle_id == ORACLE_ID
    assert view.oracle_id == ORACLE_ID
    assert view.analysis_outcome is AnalysisOutcomeV1.REQUIREMENTS_PRODUCED
    assert view.semantic_state is SemanticStateV1.ESTABLISHED
    assert len(view.requirements) == 1
    assert len(view.active_capability_mappings) == 1


def test_semantic_state_uses_m3_first_precedence() -> None:
    assert (
        semantic_state_for(AnalysisOutcomeV1.UNRESOLVED_ANALYSIS, 1, 1)
        is SemanticStateV1.UNRESOLVED_ANALYSIS
    )
    assert (
        semantic_state_for(AnalysisOutcomeV1.NO_REQUIREMENTS_APPLICABLE, 0, 0)
        is SemanticStateV1.NO_REQUIREMENTS_APPLICABLE
    )
    assert (
        semantic_state_for(AnalysisOutcomeV1.REQUIREMENTS_PRODUCED, 2, 2)
        is SemanticStateV1.ESTABLISHED
    )
    assert (
        semantic_state_for(AnalysisOutcomeV1.REQUIREMENTS_PRODUCED, 2, 1)
        is SemanticStateV1.PARTIALLY_ESTABLISHED
    )


def test_card_view_keeps_unresolved_bundle_and_explicit_negative_distinct(
    tmp_path: Path,
) -> None:
    package, _bundle = _build_bundle(tmp_path / "fixture")
    unresolved = unresolved_record_with_requirement(1)
    assert unresolved.bundle is not None
    requirement = unresolved.bundle.requirements[0]
    structural = structural_record(
        oracle_id=unresolved.source.oracle_id,
        source_card_id=unresolved.source.source_card_id,
        source_record_sha256=unresolved.source.source_record_sha256,
    )
    definitions = {item.capability_ref: item for item in package.definitions}
    admissibility = {item.requirement_id: item for item in package.admissibility}
    decisions = {item.requirement_id: item for item in package.mapping_decisions}
    links = {item.link_id: item for item in package.links}
    unresolved_view = build_card_semantic_view(
        structural_record=structural,
        analysis_record=unresolved,
        requirements=(requirement,),
        admissibility_by_requirement=admissibility,
        decisions_by_requirement=decisions,
        links_by_id=links,
        definitions_by_ref=definitions,
        census_release_id="censusrel_" + "0" * 64,
        census_manifest_sha256="a" * 64,
        m3_analysis_manifest_sha256=package.corpus.m3_analysis_manifest_sha256,
    )
    assert unresolved_view.semantic_state is SemanticStateV1.UNRESOLVED_ANALYSIS
    assert unresolved_view.requirements
    assert unresolved_view.active_capability_mappings

    partial = record_with_proposed_requirement(0)
    assert partial.bundle is not None
    partial_requirement = partial.bundle.requirements[0]
    partial_decisions = dict(decisions)
    partial_decisions[partial_requirement.requirement_id] = mapping_decision(
        partial_requirement,
        MappingDispositionV1.UNMAPPED,
        MappingReasonV1.NO_REVIEWED_CAPABILITY,
        m3_analysis_manifest_sha256=package.corpus.m3_analysis_manifest_sha256,
    )
    partial_view = build_card_semantic_view(
        structural_record=structural_record(
            oracle_id=partial.source.oracle_id,
            source_card_id=partial.source.source_card_id,
            source_record_sha256=partial.source.source_record_sha256,
        ),
        analysis_record=partial,
        requirements=(partial_requirement,),
        admissibility_by_requirement=admissibility,
        decisions_by_requirement=partial_decisions,
        links_by_id=links,
        definitions_by_ref=definitions,
        census_release_id="censusrel_" + "0" * 64,
        census_manifest_sha256="a" * 64,
        m3_analysis_manifest_sha256=package.corpus.m3_analysis_manifest_sha256,
    )
    assert partial_view.semantic_state is SemanticStateV1.PARTIALLY_ESTABLISHED
    assert not partial_view.active_capability_mappings

    negative = no_requirements_applicable_record(2)
    negative_view = build_card_semantic_view(
        structural_record=structural_record(
            oracle_id=negative.source.oracle_id,
            source_card_id=negative.source.source_card_id,
            source_record_sha256=negative.source.source_record_sha256,
        ),
        analysis_record=negative,
        requirements=(),
        admissibility_by_requirement={},
        decisions_by_requirement={},
        links_by_id={},
        definitions_by_ref={},
        census_release_id="censusrel_" + "0" * 64,
        census_manifest_sha256="a" * 64,
        m3_analysis_manifest_sha256=package.corpus.m3_analysis_manifest_sha256,
    )
    assert negative_view.semantic_state is SemanticStateV1.NO_REQUIREMENTS_APPLICABLE
    assert not negative_view.requirements
    assert not negative_view.active_capability_mappings


def test_unknown_ids_return_explicit_not_found_values(tmp_path: Path) -> None:
    reader = open_bundle(_derived_bundle(tmp_path))

    for result in (
        reader.get_structural_record(UNKNOWN_ORACLE_ID),
        reader.get_analysis_record(UNKNOWN_ORACLE_ID),
        reader.get_card_semantic_view(UNKNOWN_ORACLE_ID),
        reader.trace_requirement("srq_" + "0" * 64),
        reader.trace_mapping("rcl_" + "0" * 64),
    ):
        assert isinstance(result, QueryNotFoundV1)
        assert result.identifier


def test_requirement_and_mapping_traces_are_complete_and_deterministic(
    tmp_path: Path,
) -> None:
    reader = open_bundle(_derived_bundle(tmp_path))
    view = reader.get_card_semantic_view(ORACLE_ID)
    requirement_id = view.requirements[0].requirement_id
    link_id = view.active_capability_mappings[0].link_id

    requirement_trace_a = reader.trace_requirement(requirement_id)
    requirement_trace_b = reader.trace_requirement(requirement_id)
    mapping_trace = reader.trace_mapping(link_id)

    assert requirement_trace_a == requirement_trace_b
    assert requirement_trace_a.requirement.requirement_id == requirement_id
    assert requirement_trace_a.analysis_record.source.oracle_id == ORACLE_ID
    assert requirement_trace_a.admissibility.requirement_id == requirement_id
    assert requirement_trace_a.mapping_decision.requirement_id == requirement_id
    assert requirement_trace_a.links[0].link_id == link_id
    assert requirement_trace_a.capability_definitions
    assert mapping_trace.link.link_id == link_id
    assert mapping_trace.requirement.requirement_id == requirement_id
    assert mapping_trace.mapping_decision.requirement_id == requirement_id


def test_open_bundle_rejects_nested_authoritative_corruption(tmp_path: Path) -> None:
    root = _derived_bundle(tmp_path)
    path = root / "inputs/m3/records/0.jsonl"
    path.write_bytes(path.read_bytes() + b" ")

    with pytest.raises(ValueError):
        open_bundle(root)


def test_open_bundle_rejects_corrupt_derived_index(tmp_path: Path) -> None:
    root = _derived_bundle(tmp_path)
    path = root / "indexes/cards-by-oracle-id.jsonl"
    path.write_bytes(path.read_bytes() + b" ")

    with pytest.raises(ValueError):
        open_bundle(root)


def test_open_bundle_does_not_write_to_the_bundle(tmp_path: Path) -> None:
    root = _derived_bundle(tmp_path)
    before = {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }

    open_bundle(root)

    after = {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }
    assert after == before
