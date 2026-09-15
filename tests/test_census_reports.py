from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from capability_m3_fixtures import (
    no_requirements_applicable_record,
    record_with_proposed_requirement,
    unresolved_record_with_requirement,
    write_synthetic_m3,
)
from test_census_authority_package import _records, _write_variant
from test_census_bundle import _build_bundle

from manafold_census.analysis.manifest import AnalysisManifestV1
from manafold_census.canonical import canonical_json_bytes
from manafold_census.capability.input import load_m3_requirement_corpus
from manafold_census.capability.manifest import M4_DIMENSION_REGISTRY_VERSION
from manafold_census.digest import sha256_bytes
from manafold_census.models import SourceLock
from manafold_census.reports.build import (
    DerivedCensusBuildError,
    build_census_derived,
    validate_census_derived_output,
)
from manafold_census.reports.model import (
    INDEX_MANIFEST_FILENAME,
    MAPPING_REVIEW_QUEUE_FILENAME,
    REPORT_FILENAME,
    REPORT_INDEX_FILENAME,
    UNRESOLVED_ANALYSIS_FILENAME,
)
from manafold_census.semantic.bundle import RequirementBundleV1
from manafold_census.semantic.kind_payloads import DrawCardsParametersV1
from manafold_census.semantic.kinds import RequirementFamilyV1, RequirementKindV1
from manafold_census.semantic.model import RequirementV1
from manafold_census.semantic.primitives import QuantityModeV1, QuantityV1
from manafold_census.structural.manifest import StructuralCardIndexManifestV1

DERIVED_FILES = {
    REPORT_INDEX_FILENAME,
    REPORT_FILENAME,
    UNRESOLVED_ANALYSIS_FILENAME,
    MAPPING_REVIEW_QUEUE_FILENAME,
    INDEX_MANIFEST_FILENAME,
    "indexes/cards-by-name.jsonl",
    "indexes/cards-by-oracle-id.jsonl",
    "indexes/requirements-by-card.jsonl",
    "indexes/links-by-requirement.jsonl",
    "indexes/cards-by-capability.jsonl",
}


def _file_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def test_derived_build_adds_only_reports_and_indexes_and_preserves_input(
    tmp_path: Path,
) -> None:
    package, bundle_result = _build_bundle(tmp_path / "fixture")
    before = _file_bytes(bundle_result.output_dir)

    result = build_census_derived(
        bundle_result.output_dir,
        tmp_path / "derived",
    )

    after_input = _file_bytes(bundle_result.output_dir)
    output_files = _file_bytes(result.output_dir)
    assert after_input == before
    assert set(output_files) == set(before) | DERIVED_FILES
    assert all(output_files[path] == before[path] for path in before)
    assert result.census_release_id == bundle_result.manifest.census_release_id
    assert result.census_manifest_sha256 == bundle_result.manifest.digest()
    assert package.corpus.requirement_set_digest == result.report.requirement_set_digest


def test_report_has_explicit_population_and_denominator_labelled_metrics(
    tmp_path: Path,
) -> None:
    _package, bundle_result = _build_bundle(tmp_path / "fixture")
    result = build_census_derived(bundle_result.output_dir, tmp_path / "derived")
    report = result.report.to_wire()

    assert report["population"] == {
        "oracle_identity_count": 5,
        "structural_record_count": 5,
        "analysis_record_count": 5,
        "requirement_count": 5,
        "requirements_produced_card_count": 5,
        "no_requirements_applicable_count": 0,
        "unresolved_analysis_count": 0,
    }
    assert report["analysis_outcome_counts"] == {
        "REQUIREMENTS_PRODUCED": 5,
        "NO_REQUIREMENTS_APPLICABLE": 0,
        "UNRESOLVED_ANALYSIS": 0,
    }
    assert report["m4_mapping_disposition_counts"]["MAPPED"] == 5
    assert report["active_capability_mapping_presence"]["denominator_label"] == (
        "TOTAL_ORACLE_IDENTITIES"
    )
    assert report["mapped_subset_capability_frequency"][0]["denominator_label"] == (
        "MAPPED_REQUIREMENTS"
    )
    assert "ratio" not in report


def test_report_and_index_regeneration_is_byte_identical(tmp_path: Path) -> None:
    _package, bundle_result = _build_bundle(tmp_path / "fixture")

    first = build_census_derived(bundle_result.output_dir, tmp_path / "run-a")
    second = build_census_derived(bundle_result.output_dir, tmp_path / "run-b")

    assert _file_bytes(first.output_dir) == _file_bytes(second.output_dir)
    assert first.report_index == second.report_index
    assert first.index_manifest == second.index_manifest


def test_report_keeps_unresolved_bundle_and_explicit_negative_separate(
    tmp_path: Path,
) -> None:
    fourth = record_with_proposed_requirement(4)
    assert fourth.bundle is not None
    first_requirement = fourth.bundle.requirements[0]
    second_requirement = RequirementV1.create(
        source=first_requirement.source,
        family=RequirementFamilyV1.EFFECT,
        kind=RequirementKindV1.DRAW_CARDS,
        parameters=DrawCardsParametersV1(
            first_requirement.parameters.drawer,
            QuantityV1(QuantityModeV1.EXACT, 3),
        ),
        evidence=first_requirement.evidence,
        provenance=first_requirement.provenance,
        review=first_requirement.review,
        resolution=first_requirement.resolution,
    )
    records = (
        record_with_proposed_requirement(0),
        unresolved_record_with_requirement(1),
        no_requirements_applicable_record(2),
        record_with_proposed_requirement(3),
        replace(
            fourth,
            bundle=RequirementBundleV1(
                fourth.bundle.source,
                (first_requirement, second_requirement),
                (),
            ),
        ),
    )
    m3_input = write_synthetic_m3(tmp_path / "m3", records=records)
    corpus = load_m3_requirement_corpus(m3_input)
    source_raw = m3_input.source_lock_path.read_bytes()
    source_lock = SourceLock.from_wire(json.loads(source_raw))
    m1_raw = (
        m3_input.structural_output_directory / "structural-index-manifest.json"
    ).read_bytes()
    m1 = StructuralCardIndexManifestV1.from_wire(json.loads(m1_raw))
    m3_raw = (
        m3_input.analysis_output_directory / "analysis-manifest.json"
    ).read_bytes()
    m3 = AnalysisManifestV1.from_wire(json.loads(m3_raw))
    from manafold_census.release.input_lock import CensusInputLockV1

    lock = CensusInputLockV1(
        source_lock_digest=source_lock.digest(),
        source_lock_file_sha256=sha256_bytes(source_raw),
        m1_structural_manifest_sha256=sha256_bytes(m1_raw),
        m1_structural_aggregate_digest=m1.aggregate_digest,
        m3_analysis_manifest_sha256=sha256_bytes(m3_raw),
        m3_record_identity_set_digest=m3.record_identity_set_digest,
        m3_record_index_digest=m3.record_index_digest,
        m3_trace_index_digest=m3.trace_index_digest,
        expected_m4_requirement_set_digest=corpus.requirement_set_digest,
        m1_structural_schema="census.structural-card.v1",
        m3_analysis_schema="census.card-analysis.v1",
        m2_requirement_schema="census.semantic-requirement.v1",
        m2_bundle_schema="census.semantic-requirement-bundle.v1",
        m4_ontology_schema="census.capability-ontology.v1",
        m4_dimension_registry_version=M4_DIMENSION_REGISTRY_VERSION,
        expected_oracle_identity_count=5,
        expected_structural_record_count=5,
        expected_analysis_record_count=5,
        expected_requirements_produced_card_count=3,
        expected_no_requirements_applicable_count=1,
        expected_unresolved_analysis_count=1,
        expected_requirement_count=5,
    )
    definitions, reviews, admissibility, links, decisions, relations, evolution = (
        _records(corpus)
    )
    authority_root = tmp_path / "authority"
    _write_variant(
        type(
            "Package",
            (),
            {
                "corpus": corpus,
                "definitions": definitions,
                "reviews": reviews,
                "admissibility": admissibility,
                "links": links,
                "mapping_decisions": decisions,
                "relations": relations,
                "evolution": evolution,
            },
        )(),
        authority_root,
    )
    # The fixture helper only needs the fields above; write the lock and M4 input
    # through the same frozen M5-04/M5-05 paths used by the normal fixture.
    from manafold_census.release.bundle import build_census_bundle
    from manafold_census.release.m4_orchestration import build_real_m4_snapshot

    m4_root = tmp_path / "m4"
    build_real_m4_snapshot(
        authority_package_directory=authority_root,
        m3_input=m3_input,
        lock=lock,
        corpus=corpus,
        output_directory=m4_root,
    )
    lock_path = tmp_path / "lock.json"
    lock_path.write_bytes(canonical_json_bytes(lock.to_wire()))
    bundle = build_census_bundle(
        input_lock_path=lock_path,
        source_lock_path=m3_input.source_lock_path,
        structural_output_directory=m3_input.structural_output_directory,
        analysis_output_directory=m3_input.analysis_output_directory,
        authority_package_directory=authority_root,
        m4_output_directory=m4_root,
        output_directory=tmp_path / "bundle",
    )

    result = build_census_derived(bundle.output_dir, tmp_path / "derived")
    report = result.report.to_wire()
    assert report["analysis_outcome_counts"] == {
        "REQUIREMENTS_PRODUCED": 3,
        "NO_REQUIREMENTS_APPLICABLE": 1,
        "UNRESOLVED_ANALYSIS": 1,
    }
    assert report["unresolved_analysis"] == {
        "cards_with_persisted_requirements": 1,
        "cards_without_persisted_requirements": 0,
        "denominator": 1,
        "denominator_label": "UNRESOLVED_ANALYSIS_CARDS",
    }
    assert report["explicit_negative_analysis"]["numerator"] == 1
    unresolved_rows = [
        json.loads(line)
        for line in (result.output_dir / UNRESOLVED_ANALYSIS_FILENAME)
        .read_bytes()
        .splitlines()
    ]
    assert unresolved_rows[0]["persisted_requirement_count"] == 1
    assert (
        report["active_capability_mapping_presence"][
            "cards_with_active_capability_mappings"
        ]
        == 4
    )


def test_derived_output_reread_rejects_corrupt_index_descriptor(tmp_path: Path) -> None:
    _package, bundle_result = _build_bundle(tmp_path / "fixture")
    result = build_census_derived(bundle_result.output_dir, tmp_path / "derived")
    path = result.output_dir / INDEX_MANIFEST_FILENAME
    document = json.loads(path.read_bytes())
    document["index_descriptors"][0]["sha256"] = "f" * 64
    path.write_bytes(canonical_json_bytes(document))

    with pytest.raises(ValueError, match="descriptor|index"):
        validate_census_derived_output(result.output_dir)


def test_derived_output_reread_rejects_missing_derived_file(tmp_path: Path) -> None:
    _package, bundle_result = _build_bundle(tmp_path / "fixture")
    result = build_census_derived(bundle_result.output_dir, tmp_path / "derived")
    (result.output_dir / "indexes/cards-by-name.jsonl").unlink()

    with pytest.raises((FileNotFoundError, ValueError), match="file set|missing"):
        validate_census_derived_output(result.output_dir)


def test_derived_output_reread_rejects_tampered_authoritative_bytes(
    tmp_path: Path,
) -> None:
    _package, bundle_result = _build_bundle(tmp_path / "fixture")
    result = build_census_derived(bundle_result.output_dir, tmp_path / "derived")
    path = result.output_dir / "inputs/source-lock.json"
    path.write_bytes(path.read_bytes() + b" ")

    with pytest.raises(
        ValueError, match="authoritative|descriptor|SourceLock|canonical"
    ):
        validate_census_derived_output(result.output_dir)


def test_derived_output_reread_rejects_tampered_nested_authoritative_bytes(
    tmp_path: Path,
) -> None:
    _package, bundle_result = _build_bundle(tmp_path / "fixture")
    result = build_census_derived(bundle_result.output_dir, tmp_path / "derived")
    relative_paths = (
        "inputs/m1/records/0.jsonl",
        "inputs/m3/records/0.jsonl",
        "inputs/m3/trace/0.jsonl",
        "inputs/m4-authority/links.jsonl",
        "inputs/m4/links/0.jsonl",
    )

    for relative_path in relative_paths:
        path = result.output_dir / relative_path
        original = path.read_bytes()
        path.write_bytes(original + b" ")
        try:
            with pytest.raises(
                ValueError, match="authoritative|descriptor|M[134]|M5-02"
            ):
                validate_census_derived_output(result.output_dir)
        finally:
            path.write_bytes(original)


def test_derived_output_reread_rejects_corrupt_report_descriptor(
    tmp_path: Path,
) -> None:
    _package, bundle_result = _build_bundle(tmp_path / "fixture")
    result = build_census_derived(bundle_result.output_dir, tmp_path / "derived")
    path = result.output_dir / REPORT_INDEX_FILENAME
    document = json.loads(path.read_bytes())
    document["report_descriptors"][0]["byte_length"] += 1
    path.write_bytes(canonical_json_bytes(document))

    with pytest.raises(ValueError, match="descriptor|report"):
        validate_census_derived_output(result.output_dir)


def test_derived_output_reread_rejects_extra_file(tmp_path: Path) -> None:
    _package, bundle_result = _build_bundle(tmp_path / "fixture")
    result = build_census_derived(bundle_result.output_dir, tmp_path / "derived")
    (result.output_dir / "reports/extra.jsonl").write_bytes(b"")

    with pytest.raises(ValueError, match="file set|extra"):
        validate_census_derived_output(result.output_dir)


def test_derived_build_never_overwrites_existing_output(tmp_path: Path) -> None:
    _package, bundle_result = _build_bundle(tmp_path / "fixture")
    output = tmp_path / "existing"
    output.mkdir()
    sentinel = output / "sentinel.txt"
    sentinel.write_bytes(b"keep")

    with pytest.raises(DerivedCensusBuildError, match="already exists"):
        build_census_derived(bundle_result.output_dir, output)

    assert sentinel.read_bytes() == b"keep"


def test_derived_build_rejects_output_inside_input_bundle(tmp_path: Path) -> None:
    _package, bundle_result = _build_bundle(tmp_path / "fixture")

    with pytest.raises(DerivedCensusBuildError, match="outside the input bundle"):
        build_census_derived(
            bundle_result.output_dir,
            bundle_result.output_dir / "derived",
        )


def test_derived_cli_uses_only_explicit_bundle_and_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _package, bundle_result = _build_bundle(tmp_path / "fixture")
    from manafold_census.cli import main

    exit_code = main(
        [
            "m5-derived-build",
            "--bundle",
            str(bundle_result.output_dir),
            "--output",
            str(tmp_path / "cli-derived"),
        ]
    )

    assert exit_code == 0
    captured = capsys.readouterr().out
    assert "report-index=PASS" in captured
    assert "index-manifest=PASS" in captured
    assert "m5-derived-build=PASS" in captured
