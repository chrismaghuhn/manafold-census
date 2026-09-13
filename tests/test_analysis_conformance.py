from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from analysis_fixtures import (
    accepted_producer_candidate,
    candidate_a,
    candidate_b_with_other_evidence,
    canonical_conflict,
    competing_candidate_b,
    complete_candidate,
    explicit_conflict,
    other_candidate,
    partial_candidate_same_id,
)
from test_analysis_build import _build, _source_ref
from test_analysis_validate import (
    SOURCE_LOCK_PATH,
    write_m1_authority,
    write_m3_artifact,
)

from manafold_census.analysis.manifest import (
    merge_partitioned_records,
    partition_records,
)
from manafold_census.analysis.model import AnalysisOutcomeV1, card_source_key
from manafold_census.analysis.reconcile import ReconciliationFailure, reconcile
from manafold_census.analysis.report import build_reports
from manafold_census.analysis.validate import (
    AnalysisClosureError,
    validate_analysis_closure,
)


def test_reference_card_cardinality_and_outcome_matrix(tmp_path: Path) -> None:
    result, structural_records = _build(tmp_path / "base")
    assert len(result.records) == len(structural_records) == 5
    assert {card_source_key(record.source) for record in result.records} == {
        card_source_key(_source_ref(record, result.source_lock_digest))
        for record in structural_records
    }
    no_match = next(
        record
        for record in result.records
        if record.source.oracle_id
        == next(
            item.oracle_id
            for item in structural_records
            if item.name == "Golden No Match"
        )
    )
    assert no_match.outcome is AnalysisOutcomeV1.UNRESOLVED_ANALYSIS
    assert no_match.bundle is None

    authority_result, authority_records = _build(
        tmp_path / "authority",
        with_negative_authority=True,
    )
    authority_source = next(
        item for item in authority_records if item.name == "Golden No Match"
    )
    authority_card = authority_result.record_for(
        card_source_key(
            next(
                record.source
                for record in authority_result.records
                if record.source.oracle_id == authority_source.oracle_id
            )
        )
    )
    assert authority_card.outcome is AnalysisOutcomeV1.NO_REQUIREMENTS_APPLICABLE
    assert authority_card.no_requirements_basis is not None


def test_pattern_requirements_are_proposed_only(tmp_path: Path) -> None:
    result, _ = _build(tmp_path)
    candidates = [
        requirement
        for record in result.records
        if record.bundle is not None
        for requirement in record.bundle.requirements
        if any(
            derivation.method.value == "DETERMINISTIC_RULE"
            for derivation in requirement.provenance.derivations
        )
    ]
    assert candidates
    assert all(
        requirement.review.status.value == "PROPOSED" for requirement in candidates
    )
    assert all(requirement.review.reviewed_by is None for requirement in candidates)


def test_terminal_producer_review_is_execution_failure() -> None:
    with pytest.raises(ReconciliationFailure, match="PROPOSED"):
        reconcile([accepted_producer_candidate()])


def test_reconciliation_identity_and_relationship_matrix() -> None:
    merged = reconcile([candidate_a(), candidate_b_with_other_evidence()])
    assert len(merged.requirements) == 1
    assert len(merged.requirements[0].evidence) == 2
    assert len(merged.requirements[0].provenance.derivations) == 2

    disputed = reconcile([complete_candidate(), partial_candidate_same_id()])
    assert disputed.requirements == ()
    assert disputed.outcome_is_unresolved is True

    distinct = reconcile([candidate_a(), competing_candidate_b()])
    assert {item.requirement_id for item in distinct.requirements} == {
        candidate_a().requirement_id,
        competing_candidate_b().requirement_id,
    }
    assert distinct.relationships == ()

    explicit = reconcile([candidate_a(), other_candidate()], [explicit_conflict()])
    assert explicit.relationships == (canonical_conflict(),)


def test_report_is_downstream_of_finalized_analysis_manifest(tmp_path: Path) -> None:
    result, _ = _build(tmp_path)
    reports = build_reports(result, result.output_dir)
    assert reports.analysis_manifest_sha256 == result.manifest.digest()
    assert (result.output_dir / "report-index.json").is_file()
    assert (result.output_dir / "reports" / "analysis-report.json").is_file()


def test_partition_merge_parity_is_in_process_only(tmp_path: Path) -> None:
    result, _ = _build(tmp_path)
    expected = [card_source_key(record.source) for record in result.records]
    reference = merge_partitioned_records(
        partition_records(result.records, 1), expected
    )
    for count in (2, 8, 16):
        assert (
            merge_partitioned_records(
                partition_records(result.records, count), expected
            )
            == reference
        )
    assert "workers" not in inspect.signature(partition_records).parameters
    assert "workers" not in inspect.signature(merge_partitioned_records).parameters


@pytest.mark.parametrize("count", [1, 2])
def test_closure_rejects_missing_or_extra_source_keys(
    tmp_path: Path, count: int
) -> None:
    m1_root, records, m1_manifest = write_m1_authority(tmp_path / f"m1-{count}", count)
    m3_root, _ = write_m3_artifact(
        tmp_path / f"m3-{count}",
        m1_root,
        m1_manifest,
        records[:1] if count == 2 else records + [records[0]],
    )
    with pytest.raises(AnalysisClosureError, match="identity|duplicate"):
        validate_analysis_closure(m1_root, m3_root, SOURCE_LOCK_PATH)


def test_closure_rejects_duplicate_source_key(tmp_path: Path) -> None:
    m1_root, records, m1_manifest = write_m1_authority(tmp_path)
    m3_root, _ = write_m3_artifact(tmp_path, m1_root, m1_manifest, records)
    path = m3_root / "records" / "a.jsonl"
    raw = path.read_bytes()
    path.write_bytes(raw + raw)
    with pytest.raises(AnalysisClosureError, match="duplicate"):
        validate_analysis_closure(m1_root, m3_root, SOURCE_LOCK_PATH)


def test_conformance_fixture_is_synthetic_and_bounded(tmp_path: Path) -> None:
    result, records = _build(tmp_path)
    assert len(records) == 5
    assert len(result.records) == 5
    assert not any("38740" in str(item) for item in records)
