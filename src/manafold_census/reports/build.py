"""M5-06 derived report/index orchestration and atomic publication."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from ..digest import sha256_bytes
from ..query.indexes import build_index_rows
from .derive import build_report, mapping_queue_rows, unresolved_rows
from .input import (
    read_analysis_records,
    read_structural_records,
    validated_bundle_inputs,
)
from .publish import validate_census_derived_output, write_derived_files
from .report_model import DerivedCensusBuildResultV1


class DerivedCensusBuildError(ValueError):
    """Raised when M5-06 cannot publish a derived Census tree."""


def build_census_derived(
    bundle_directory: str | Path,
    output_directory: str | Path,
) -> DerivedCensusBuildResultV1:
    """Copy a validated Census bundle and atomically add reports and indexes."""

    manifest, _lock, corpus, reread = validated_bundle_inputs(bundle_directory)
    bundle_root = Path(bundle_directory)
    output = Path(output_directory)
    if output.exists():
        raise DerivedCensusBuildError("derived Census output directory already exists")
    try:
        output.resolve().relative_to(bundle_root.resolve())
    except ValueError:
        pass
    except OSError as error:
        raise DerivedCensusBuildError(
            "derived Census output path cannot be resolved"
        ) from error
    else:
        raise DerivedCensusBuildError(
            "derived Census output must be outside the input bundle"
        )

    structural_records = read_structural_records(bundle_root)
    analysis_records = read_analysis_records(bundle_root)
    m4_manifest_path = bundle_root / "inputs/m4/m4-ontology-manifest.json"
    report = build_report(
        manifest_sha256=manifest.digest(),
        release_id=manifest.census_release_id,
        source_lock_digest=manifest.source_lock_digest,
        m3_manifest_sha256=corpus.m3_analysis_manifest_sha256,
        m4_manifest_sha256=sha256_bytes(m4_manifest_path.read_bytes()),
        requirement_set_digest=corpus.requirement_set_digest,
        population=manifest.population.to_wire(),
        requirements=corpus,
        structural_records=structural_records,
        analysis_records=analysis_records,
        reread=reread,
    )
    indexes = build_index_rows(
        structural_records,
        analysis_records,
        corpus.requirements,
        reread,
    )
    reports = unresolved_rows(analysis_records)
    queue = mapping_queue_rows(reread.decisions)

    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(
            prefix=f".{output.name}-", dir=str(output.parent)
        ) as temporary:
            staging = Path(temporary) / "derived"
            shutil.copytree(bundle_root, staging)
            report_index, index_manifest = write_derived_files(
                staging, report, reports, queue, indexes
            )
            validate_census_derived_output(staging)
            os.replace(staging, output)
    except FileNotFoundError:
        raise
    except OSError as error:
        raise DerivedCensusBuildError(f"PUBLICATION_FAILURE: {error}") from error
    except (TypeError, ValueError) as error:
        raise DerivedCensusBuildError(f"PUBLICATION_FAILURE: {error}") from error
    return DerivedCensusBuildResultV1(output, report, report_index, index_manifest)


__all__ = [
    "DerivedCensusBuildError",
    "build_census_derived",
    "validate_census_derived_output",
]
