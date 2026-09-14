from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from capability_m3_fixtures import (
    record_with_other_requirement,
    record_with_proposed_requirement,
    unresolved_record_without_bundle,
    write_synthetic_m3,
)

from manafold_census.canonical import canonical_json_bytes
from manafold_census.capability.build import M4BuildResultV1, build_reference_m4
from manafold_census.capability.input import (
    M3RequirementCorpusV1,
    load_m3_requirement_corpus,
)
from manafold_census.capability.mapping import (
    MappingDispositionV1,
    MappingReasonV1,
    mapping_decision,
)
from manafold_census.capability.report import (
    CapabilityReportV1,
    build_capability_reports,
)
from manafold_census.validation import validate_document

REPOSITORY_ROOT = Path(__file__).parents[1]


def _build_synthetic_m4(
    root: Path,
    *,
    sparse: bool = False,
) -> tuple[M4BuildResultV1, M3RequirementCorpusV1]:
    records = (
        (record_with_proposed_requirement(), unresolved_record_without_bundle())
        if sparse
        else (unresolved_record_without_bundle(),)
    )
    m3_input = write_synthetic_m3(root / "m3", records=records)
    corpus = load_m3_requirement_corpus(m3_input)
    decisions = tuple(
        mapping_decision(
            requirement,
            MappingDispositionV1.INSUFFICIENT_EVIDENCE,
            MappingReasonV1.M4_ADMISSIBILITY_REVIEW_PENDING,
            m3_analysis_manifest_sha256=corpus.m3_analysis_manifest_sha256,
        )
        for requirement in corpus.requirements
    )
    result = build_reference_m4(
        m3_input,
        None,
        None,
        (),
        (),
        (),
        (),
        (),
        decisions,
        (),
        root / "m4",
    )
    return result, corpus


def _report(result: M4BuildResultV1, corpus: M3RequirementCorpusV1):
    return build_capability_reports(result, m3_context=corpus)


def test_report_is_downstream_of_m4_manifest(tmp_path: Path) -> None:
    result, corpus = _build_synthetic_m4(tmp_path)
    report = _report(result, corpus)

    assert report.m4_manifest_sha256 == result.manifest.digest()
    assert report.report_index.m4_manifest_sha256 == result.manifest.digest()
    assert report.report_index.report_descriptors
    assert (result.output_dir / "reports" / "capability-report.json").is_file()
    assert (result.output_dir / "report-index.json").is_file()


def test_report_keeps_m3_unresolved_context_separate(tmp_path: Path) -> None:
    result, corpus = _build_synthetic_m4(tmp_path, sparse=True)
    report = _report(result, corpus)

    assert report.m3_context.unresolved_analysis_count == 1
    assert report.mapping_counts["INSUFFICIENT_EVIDENCE"] == 1
    assert report.capability_counts["ACTIVE"] == 0
    assert report.m3_context.persisted_requirement_count == 1


def test_report_aggregates_active_reuse_and_dimension_values(tmp_path: Path) -> None:
    from test_capability_validate import _active_definition_and_links

    m3_input = write_synthetic_m3(
        tmp_path / "m3",
        records=(record_with_proposed_requirement(), record_with_other_requirement()),
    )
    corpus = load_m3_requirement_corpus(m3_input)
    definition, definition_review, links, link_reviews, admissibility = (
        _active_definition_and_links(corpus, 2)
    )
    decisions = tuple(
        mapping_decision(
            requirement,
            MappingDispositionV1.MAPPED,
            None,
            m3_analysis_manifest_sha256=corpus.m3_analysis_manifest_sha256,
            active_link_ids=(link.link_id,),
        )
        for requirement, link in zip(corpus.requirements, links, strict=True)
    )
    result = build_reference_m4(
        m3_input,
        None,
        None,
        (definition,),
        (definition_review, *link_reviews),
        (),
        admissibility,
        links,
        decisions,
        (),
        tmp_path / "m4",
    )
    report = build_capability_reports(result, m3_context=corpus)

    assert report.capability_counts["ACTIVE"] == 1
    assert report.mapping_counts["MAPPED"] == 2
    capability_row = report.report.to_wire()["requirements_per_capability"]
    assert isinstance(capability_row, list)
    assert capability_row[0]["requirement_count"] == 2
    dimensions = report.report.to_wire()["parameter_dimension_distributions"]
    assert isinstance(dimensions, list)
    assert dimensions == []


def test_report_wire_and_index_are_schema_valid_and_manifest_is_unchanged(
    tmp_path: Path,
) -> None:
    result, corpus = _build_synthetic_m4(tmp_path)
    manifest_before = (result.output_dir / "m4-ontology-manifest.json").read_bytes()
    report = _report(result, corpus)

    assert CapabilityReportV1.from_wire(report.report.to_wire()) == report.report
    validate_document(report.report.to_wire(), "capability-report.v1.schema.json")
    validate_document(report.report_index.to_wire(), "capability-report.v1.schema.json")
    assert (result.output_dir / "m4-ontology-manifest.json").read_bytes() == (
        manifest_before
    )
    assert "report_index" not in result.manifest.to_wire()
    assert "report_index_digest" not in result.manifest.to_wire()


def test_reports_are_deterministic_for_same_synthetic_inputs(tmp_path: Path) -> None:
    first_result, first_corpus = _build_synthetic_m4(tmp_path / "first")
    second_result, second_corpus = _build_synthetic_m4(tmp_path / "second")
    first = _report(first_result, first_corpus)
    second = _report(second_result, second_corpus)

    assert first.report.to_wire() == second.report.to_wire()
    assert first.report_index.to_wire() == second.report_index.to_wire()
    assert (
        first_result.output_dir / "reports" / "capability-report.json"
    ).read_bytes() == (
        second_result.output_dir / "reports" / "capability-report.json"
    ).read_bytes()


@pytest.mark.parametrize("command", ["m4-build", "m4-check", "m4-report"])
def test_m4_commands_require_explicit_synthetic_mode(command: str) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "manafold_census.cli", command],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert f"{command}=FAIL:" in result.stderr
    assert "--synthetic" in result.stderr


def test_synthetic_m4_commands_are_offline_and_complete(tmp_path: Path) -> None:
    output = tmp_path / "m4"
    build = subprocess.run(
        [
            sys.executable,
            "-m",
            "manafold_census.cli",
            "m4-build",
            "--synthetic",
            "--output",
            str(output),
        ],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert build.returncode == 0, build.stderr
    assert "m4-build=PASS" in build.stdout

    check = subprocess.run(
        [
            sys.executable,
            "-m",
            "manafold_census.cli",
            "m4-check",
            "--synthetic",
            "--output",
            str(output),
        ],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert check.returncode == 0, check.stderr
    assert "m4-check=PASS" in check.stdout

    report = subprocess.run(
        [
            sys.executable,
            "-m",
            "manafold_census.cli",
            "m4-report",
            "--synthetic",
            "--output",
            str(output),
        ],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert report.returncode == 0, report.stderr
    assert "m4-report=PASS" in report.stdout
    assert (output / "reports" / "capability-report.json").is_file()

    check_after_report = subprocess.run(
        [
            sys.executable,
            "-m",
            "manafold_census.cli",
            "m4-check",
            "--synthetic",
            "--output",
            str(output),
        ],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert check_after_report.returncode == 0, check_after_report.stderr


def test_m4_report_wire_is_canonical(tmp_path: Path) -> None:
    result, corpus = _build_synthetic_m4(tmp_path)
    _report(result, corpus)
    report_path = result.output_dir / "reports" / "capability-report.json"

    raw = report_path.read_bytes()
    assert raw == canonical_json_bytes(json.loads(raw))
