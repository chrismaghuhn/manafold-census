from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

from test_analysis_build import _build

from manafold_census.analysis.model import AnalysisOutcomeV1, card_source_key
from manafold_census.analysis.report import build_reports
from manafold_census.analysis.trace import TraceDispositionV1


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
    assert document["cards_by_outcome"] == {
        "REQUIREMENTS_PRODUCED": 3,
        "NO_REQUIREMENTS_APPLICABLE": 0,
        "UNRESOLVED_ANALYSIS": 2,
    }
    assert document["requirements_by_review_status"] == {
        "PROPOSED": 5,
        "IN_REVIEW": 0,
        "ACCEPTED": 0,
        "REJECTED": 0,
    }
    assert document["requirements_by_resolution_state"] == {
        "COMPLETE": 5,
        "PARTIAL": 0,
        "UNRESOLVED": 0,
    }
    assert document["requirements_by_resolution_reason"] == {
        "NONE": 5,
        "INSUFFICIENT_EVIDENCE": 0,
        "AMBIGUOUS_SOURCE": 0,
        "UNSUPPORTED_SHAPE": 0,
        "CONFLICTING_INTERPRETATIONS": 0,
        "UNKNOWN_SEMANTICS": 0,
    }
    assert document["requirements_by_derivation"] == {
        "HUMAN_AUTHORED": 0,
        "DETERMINISTIC_RULE": 6,
        "PARSER": 0,
        "HEURISTIC": 0,
        "MODEL": 0,
        "IMPORTED_ANNOTATION": 0,
    }
    assert document["requirements_by_family"] == {
        "effect": 5,
        "event": 0,
        "choice": 0,
        "cost": 0,
        "control": 0,
        "reference": 0,
        "unknown": 0,
    }
    assert document["requirements_by_kind"] == {
        "move_between_zones": 0,
        "create_object": 0,
        "select": 0,
        "modify_characteristic": 0,
        "apply_continuous_effect": 0,
        "search_zone": 0,
        "draw_cards": 5,
        "deal_damage": 0,
        "create_delayed_effect": 0,
        "trigger_from_event": 0,
        "replace_event": 0,
        "pay_cost": 0,
        "modify_cost": 0,
        "choose_mode": 0,
        "conditional_effect": 0,
        "keyword_reference": 0,
        "unresolved": 0,
    }
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


def test_negative_authority_conflict_is_attributed_without_no_match_blame(
    tmp_path: Path,
) -> None:
    validated_run, _ = _build(
        tmp_path / "fixture",
        variant="conflict",
        with_negative_authority=True,
    )
    result = build_reports(validated_run, validated_run.output_dir)
    document = result.report.to_wire()
    contributions = {
        (item["producer_id"], item["producer_version"]): item
        for item in document["producer_contributions"]
    }

    assert document["largest_unresolved_groups"] == [
        {"group_key": "NEGATIVE_AUTHORITY_CONFLICT", "card_count": 1},
        {"group_key": "PRODUCER_UNSUPPORTED_SHAPE", "card_count": 1},
    ]
    conflict = contributions[("m3.fixture-conflict", "1")]
    assert conflict["candidate_emitted_count"] == 1
    assert conflict["candidate_retained_count"] == 1
    assert conflict["conflict_count"] == 1
    assert conflict["unresolved_card_count"] == 1
    unsupported = contributions[("m3.fixture-unsupported", "1")]
    assert unsupported["unsupported_shape_count"] == 1
    assert unsupported["unresolved_card_count"] == 1
    exact = contributions[("m3.exact-rule", "1")]
    assert exact["unresolved_card_count"] == 0
    assert exact["no_match_count"] == 3


def test_mixed_negative_authority_and_unsupported_attribution_is_multi_cause_safe(
    tmp_path: Path,
) -> None:
    validated_run, _ = _build(
        tmp_path / "fixture",
        variant="mixed",
        with_negative_authority=True,
    )
    result = build_reports(validated_run, validated_run.output_dir)
    contributions = {
        (item["producer_id"], item["producer_version"]): item
        for item in result.report.to_wire()["producer_contributions"]
    }

    candidate = contributions[("m3.fixture-conflict", "1")]
    assert candidate["candidate_emitted_count"] == 1
    assert candidate["candidate_retained_count"] == 1
    assert candidate["conflict_count"] == 1
    assert candidate["unresolved_card_count"] == 1

    unsupported = contributions[("m3.fixture-mixed-unsupported", "1")]
    assert unsupported["unsupported_shape_count"] == 1
    assert unsupported["unresolved_card_count"] == 1

    assert contributions[("m3.exact-rule", "1")]["unresolved_card_count"] == 0
    assert contributions[("m3.fixture-double", "1")]["unresolved_card_count"] == 0


def test_negative_authority_and_dispute_keep_independent_contributions(
    tmp_path: Path,
) -> None:
    validated_run, _ = _build(
        tmp_path / "fixture",
        variant="disputed",
        with_negative_authority=True,
    )
    result = build_reports(validated_run, validated_run.output_dir)
    document = result.report.to_wire()
    contributions = {
        (item["producer_id"], item["producer_version"]): item
        for item in document["producer_contributions"]
    }

    assert document["largest_unresolved_groups"] == [
        {"group_key": "DISPUTED_IDENTITY_OMITTED", "card_count": 1},
        {"group_key": "PRODUCER_UNSUPPORTED_SHAPE", "card_count": 1},
    ]
    for producer_id in ("m3.fixture-conflict", "m3.fixture-disputed"):
        contribution = contributions[(producer_id, "1")]
        assert contribution["candidate_emitted_count"] == 1
        assert contribution["candidate_retained_count"] == 0
        assert contribution["conflict_count"] == 1
        assert contribution["unresolved_card_count"] == 1
    assert contributions[("m3.exact-rule", "1")]["unresolved_card_count"] == 0


def test_report_does_not_infer_authority_conflict_from_bundle_presence(
    tmp_path: Path,
) -> None:
    validated_run, structural_records = _build(tmp_path / "fixture")
    target = next(
        record
        for record in validated_run.records
        if record.source.oracle_id == structural_records[0].oracle_id
    )
    unresolved_target = replace(
        target,
        outcome=AnalysisOutcomeV1.UNRESOLVED_ANALYSIS,
    )
    records = tuple(
        unresolved_target
        if record.source.oracle_id == target.source.oracle_id
        else record
        for record in validated_run.records
    )
    synthetic_run = validated_run._replace(records=records)
    result = build_reports(synthetic_run, validated_run.output_dir)

    assert all(
        item["group_key"] != "NEGATIVE_AUTHORITY_CONFLICT"
        for item in result.report.to_wire()["largest_unresolved_groups"]
    )


def test_single_card_and_outlier_patterns_are_reported_deterministically(
    tmp_path: Path,
) -> None:
    validated_run, _ = _build(tmp_path / "fixture")
    source_event = next(
        event for event in validated_run.traces if event.pattern_id is not None
    )
    singleton_event = replace(
        source_event,
        pattern_id="synthetic.singleton",
        pattern_version="1",
        pattern_digest="a" * 64,
    )
    synthetic_run = validated_run._replace(
        traces=validated_run.traces + (singleton_event,)
    )
    result = build_reports(synthetic_run, validated_run.output_dir)

    assert result.report.to_wire()["single_card_patterns"] == [
        "synthetic.singleton@1",
    ]
    assert result.report.to_wire()["outlier_patterns"] == [
        "synthetic.singleton@1",
    ]


def test_disputed_candidate_is_the_only_unresolved_producer_contributor(
    tmp_path: Path,
) -> None:
    validated_run, structural_records = _build(tmp_path / "fixture")
    disputed_source = next(
        record for record in structural_records if record.name == "Golden Exact"
    )
    disputed_key = card_source_key(
        next(
            record.source
            for record in validated_run.records
            if record.source.oracle_id == disputed_source.oracle_id
        )
    )
    disputed_record = next(
        record
        for record in validated_run.records
        if record.source.oracle_id == disputed_source.oracle_id
    )
    disputed_record = replace(
        disputed_record,
        outcome=AnalysisOutcomeV1.UNRESOLVED_ANALYSIS,
        bundle=None,
        no_requirements_basis=None,
    )
    records = tuple(
        disputed_record
        if record.source.oracle_id == disputed_source.oracle_id
        else record
        for record in validated_run.records
    )
    target_event = next(
        event
        for event in validated_run.traces
        if event.card_source_key == disputed_key
        and event.producer_id == "m3.exact-rule"
        and event.candidate_requirement_id is not None
    )
    traces = tuple(
        replace(
            event,
            disposition=TraceDispositionV1.DISPUTED_IDENTITY_OMITTED,
        )
        if event is target_event
        else event
        for event in validated_run.traces
    )
    disputed_run = validated_run._replace(records=records, traces=traces)
    result = build_reports(disputed_run, validated_run.output_dir)
    document = result.report.to_wire()
    contributions = {
        (item["producer_id"], item["producer_version"]): item
        for item in document["producer_contributions"]
    }

    exact = contributions[("m3.exact-rule", "1")]
    assert exact["candidate_emitted_count"] == 2
    assert exact["candidate_retained_count"] == 1
    assert exact["conflict_count"] == 1
    assert exact["unresolved_card_count"] == 1
    assert contributions[("m3.fixture-double", "1")]["unresolved_card_count"] == 0
    assert any(
        item == {"group_key": "DISPUTED_IDENTITY_OMITTED", "card_count": 1}
        for item in document["largest_unresolved_groups"]
    )


def test_disputed_and_unsupported_producers_are_both_unresolved_contributors(
    tmp_path: Path,
) -> None:
    validated_run, structural_records = _build(
        tmp_path / "fixture",
        variant="mixed",
        with_negative_authority=True,
    )
    target_source = next(
        record for record in structural_records if record.name == "Golden No Match"
    )
    target_key = card_source_key(
        next(
            record.source
            for record in validated_run.records
            if record.source.oracle_id == target_source.oracle_id
        )
    )
    target_record = next(
        record
        for record in validated_run.records
        if record.source.oracle_id == target_source.oracle_id
    )
    records = tuple(
        replace(
            target_record,
            outcome=AnalysisOutcomeV1.UNRESOLVED_ANALYSIS,
            bundle=None,
            no_requirements_basis=None,
        )
        if record.source.oracle_id == target_record.source.oracle_id
        else record
        for record in validated_run.records
    )
    target_event = next(
        event
        for event in validated_run.traces
        if event.card_source_key == target_key
        and getattr(event, "producer_id", None) == "m3.fixture-conflict"
        and getattr(event, "candidate_requirement_id", None) is not None
    )
    traces = tuple(
        replace(
            event,
            disposition=TraceDispositionV1.DISPUTED_IDENTITY_OMITTED,
        )
        if event is target_event
        else event
        for event in validated_run.traces
    )
    result = build_reports(
        validated_run._replace(records=records, traces=traces),
        validated_run.output_dir,
    )
    contributions = {
        (item["producer_id"], item["producer_version"]): item
        for item in result.report.to_wire()["producer_contributions"]
    }

    assert contributions[("m3.fixture-conflict", "1")]["unresolved_card_count"] == 1
    assert (
        contributions[("m3.fixture-mixed-unsupported", "1")]["unresolved_card_count"]
        == 1
    )
    assert contributions[("m3.exact-rule", "1")]["unresolved_card_count"] == 0
    assert contributions[("m3.fixture-double", "1")]["unresolved_card_count"] == 0
