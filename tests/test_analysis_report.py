from __future__ import annotations

import hashlib
import json
from pathlib import Path

from test_analysis_build import _build

from manafold_census.analysis.report import build_reports


def test_report_index_binds_analysis_manifest_and_report_bytes(tmp_path: Path) -> None:
    validated_run, _ = _build(tmp_path / "fixture")
    result = build_reports(validated_run, validated_run.output_dir)

    assert result.analysis_manifest_sha256 == validated_run.manifest.digest()
    assert result.report_descriptors
    assert (validated_run.output_dir / "reports" / "analysis-report.json").is_file()
    assert (validated_run.output_dir / "report-index.json").is_file()
    assert result.to_wire()["report_index_schema"] == "census.analysis-report-index.v1"
    descriptor = result.report_descriptors[0]
    report_bytes = (validated_run.output_dir / descriptor.relative_path).read_bytes()
    assert descriptor.sha256 == hashlib.sha256(report_bytes).hexdigest()
    assert descriptor.byte_length == len(report_bytes)


def test_analysis_manifest_does_not_change_when_report_bytes_change(
    tmp_path: Path,
) -> None:
    validated_run, _ = _build(tmp_path / "fixture")
    manifest_path = validated_run.output_dir / "analysis-manifest.json"
    before = manifest_path.read_bytes()
    build_reports(validated_run, validated_run.output_dir)
    report_path = validated_run.output_dir / "reports" / "analysis-report.json"
    report_document = json.loads(report_path.read_bytes())
    report_document["cards_with_zero_retained_requirements"] += 1
    report_path.write_text(json.dumps(report_document), encoding="utf-8")

    assert manifest_path.read_bytes() == before


def test_report_index_is_not_an_analysis_manifest_input(tmp_path: Path) -> None:
    validated_run, _ = _build(tmp_path / "fixture")
    build_reports(validated_run, validated_run.output_dir)
    wire = validated_run.manifest.to_wire()

    assert "report-index" not in json.dumps(wire)
    assert "report_index" not in wire
    assert "report_index_digest" not in wire


def test_report_order_and_reuse_counts_are_integer_and_deterministic(
    tmp_path: Path,
) -> None:
    first_run, _ = _build(tmp_path / "first-fixture")
    second_run, _ = _build(tmp_path / "second-fixture")
    first = build_reports(first_run, first_run.output_dir)
    second = build_reports(second_run, second_run.output_dir)

    assert first.to_wire() == second.to_wire()
    assert first.reuse_summary.reused_match_count >= 0
    assert isinstance(first.reuse_summary.reused_match_count, int)
    assert list(first.report.pattern_counts) == sorted(
        first.report.pattern_counts,
        key=lambda item: (item["pattern_id"], item["pattern_version"]),
    )


def test_report_semantic_dimensions_are_derived_from_validated_records_and_trace(
    tmp_path: Path,
) -> None:
    validated_run, _ = _build(tmp_path / "fixture")
    result = build_reports(validated_run, validated_run.output_dir)
    document = result.report.to_wire()

    assert document["cards_with_zero_retained_requirements"] == 2
    assert document["matched_card_count"] == 2
    assert document["matched_requirement_count"] == 2
    assert document["distinct_pattern_count"] == 1
    assert document["reuse_summary"]["reused_match_count"] == 1
    assert document["face_source_counts"] == {"FACE": 2, "PARENT": 3}
    assert document["multi_face_card_count"] == 1
    assert document["largest_unresolved_groups"] == [
        {"group_key": "PRODUCER_NO_MATCH", "card_count": 1},
        {"group_key": "PRODUCER_UNSUPPORTED_SHAPE", "card_count": 1},
    ]
    exact = next(
        item
        for item in document["producer_contributions"]
        if item["producer_id"] == "m3.exact-rule"
    )
    assert exact["candidate_emitted_count"] == 2
    assert exact["candidate_retained_count"] == 2
