from __future__ import annotations

import hashlib
from pathlib import Path

from test_analysis_build import _build

from manafold_census import analysis
from manafold_census.analysis.report import build_reports


def _tree_files(root: Path) -> tuple[Path, ...]:
    return tuple(
        sorted(path.relative_to(root) for path in root.rglob("*") if path.is_file())
    )


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for relative_path in _tree_files(root):
        digest.update(relative_path.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update((root / relative_path).read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def test_two_clean_synthetic_m3_builds_are_byte_and_digest_identical(
    tmp_path: Path,
) -> None:
    first, _ = _build(tmp_path / "first")
    second, _ = _build(tmp_path / "second")
    build_reports(first, first.output_dir)
    build_reports(second, second.output_dir)

    first_files = _tree_files(first.output_dir)
    second_files = _tree_files(second.output_dir)
    assert first_files == second_files
    assert first_files
    for relative_path in first_files:
        assert (first.output_dir / relative_path).read_bytes() == (
            second.output_dir / relative_path
        ).read_bytes()
    assert _tree_digest(first.output_dir) == _tree_digest(second.output_dir)


def test_m3_public_export_boundary_is_explicit() -> None:
    expected = {
        "AnalysisBuildError",
        "AnalysisManifestV1",
        "AnalysisOutcomeV1",
        "CardAnalysisRecordV1",
        "EffectivePatternRegistryV1",
        "NegativeAuthorityDecisionV1",
        "NegativeAuthorityInputV1",
        "NegativeAuthorityTraceEventV1",
        "NegativeAuthorityScopeV1",
        "NegativeRequirementAuthorityRecordV1",
        "NegativeReviewAuthorityRefV1",
        "ProducerRegistryV1",
        "ReferenceBuildResultV1",
        "RequirementTraceEventV1",
        "ReportBuildResultV1",
        "TraceEventV1",
        "build_reference_m3",
        "build_reports",
        "validate_analysis_closure",
        "load_negative_requirement_authority",
        "negative_authority_record_sha256",
        "negative_authority_scope_digest",
        "validate_negative_requirement_authority",
        "card_source_key",
    }
    assert set(analysis.__all__) == expected
    assert all(hasattr(analysis, name) for name in expected)
    assert "_matches_exact_text" not in analysis.__all__
