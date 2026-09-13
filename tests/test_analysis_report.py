from __future__ import annotations

import json
from pathlib import Path

from test_analysis_build import _build

from manafold_census.analysis.report import build_reports


def test_report_index_binds_analysis_manifest_and_report_bytes(tmp_path: Path) -> None:
    validated_run, _ = _build(tmp_path / "fixture")
    result = build_reports(validated_run, tmp_path / "reports")

    assert result.analysis_manifest_sha256 == validated_run.manifest.digest()
    assert result.report_descriptors
    assert (tmp_path / "reports" / "analysis-report.json").is_file()
    assert (tmp_path / "reports" / "report-index.json").is_file()


def test_analysis_manifest_does_not_change_when_report_bytes_change(
    tmp_path: Path,
) -> None:
    validated_run, _ = _build(tmp_path / "fixture")
    manifest_path = validated_run.output_dir / "analysis-manifest.json"
    before = manifest_path.read_bytes()
    build_reports(validated_run, tmp_path / "reports")
    report_path = tmp_path / "reports" / "analysis-report.json"
    report_document = json.loads(report_path.read_bytes())
    report_document["cards_with_zero_retained_requirements"] += 1
    report_path.write_text(json.dumps(report_document), encoding="utf-8")

    assert manifest_path.read_bytes() == before


def test_report_index_is_not_an_analysis_manifest_input(tmp_path: Path) -> None:
    validated_run, _ = _build(tmp_path / "fixture")
    build_reports(validated_run, tmp_path / "reports")
    wire = validated_run.manifest.to_wire()

    assert "report-index" not in json.dumps(wire)
    assert "report_index" not in wire
    assert "report_index_digest" not in wire


def test_report_order_and_reuse_counts_are_integer_and_deterministic(
    tmp_path: Path,
) -> None:
    first_run, _ = _build(tmp_path / "first-fixture")
    second_run, _ = _build(tmp_path / "second-fixture")
    first = build_reports(first_run, tmp_path / "first-reports")
    second = build_reports(second_run, tmp_path / "second-reports")

    assert first.to_wire() == second.to_wire()
    assert first.reuse_summary.reused_match_count >= 0
    assert isinstance(first.reuse_summary.reused_match_count, int)
    assert list(first.report.pattern_counts) == sorted(
        first.report.pattern_counts,
        key=lambda item: (item["pattern_id"], item["pattern_version"]),
    )
