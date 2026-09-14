"""Bounded synthetic-only M4 maintainer commands."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from ..analysis.build_input import source_ref_for_record
from ..analysis.manifest import (
    SHARD_NAMES as ANALYSIS_SHARD_NAMES,
)
from ..analysis.manifest import (
    AnalysisManifestV1,
    AnalysisShardDescriptorV1,
    analysis_shard_for,
    record_identity_set_digest,
)
from ..analysis.model import AnalysisOutcomeV1, CardAnalysisRecordV1, card_source_key
from ..canonical import canonical_json_bytes
from ..digest import measure_file, sha256_bytes
from ..models import SourceLock
from ..resources import project_data_root
from ..semantic.bundle import RequirementBundleV1
from ..semantic.model import RequirementV1
from ..structural.build import build_structural_corpus
from ..structural.model import StructuralCardRecordV1
from ..structural.synthetic import _write_synthetic_input
from .build import M4BuildResultV1, _reread_output, _RereadResult, build_reference_m4
from .input import FrozenM3InputV1, M3RequirementCorpusV1, load_m3_requirement_corpus
from .report import CapabilityReportBuildResultV1, build_capability_reports
from .report_model import REPORT_INDEX_FILENAME
from .validate import validate_m4_inputs


def _descriptor(
    path: Path, relative_path: str, record_count: int
) -> AnalysisShardDescriptorV1:
    measurement = measure_file(path)
    return AnalysisShardDescriptorV1(
        relative_path=relative_path,
        sha256=measurement.sha256,
        byte_length=measurement.byte_length,
        record_count=record_count,
    )


def _validate_synthetic_fixture() -> None:
    path = (
        project_data_root() / "fixtures" / "capability" / "synthetic-m4-fixture.v1.json"
    )
    try:
        document = json.loads(path.read_bytes())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("synthetic M4 fixture cannot be read") from error
    expected = {
        "fixture_schema",
        "fixture_id",
        "purpose",
        "m3_record_mode",
        "capability_definition_count",
        "real_corpus",
        "real_requirement_mapping",
        "real_capability_activation",
    }
    if (
        not isinstance(document, dict)
        or set(document) != expected
        or document["fixture_schema"] != "census.m4-synthetic-fixture.v1"
        or document["m3_record_mode"] != "UNRESOLVED_ANALYSIS_WITHOUT_BUNDLE"
        or document["capability_definition_count"] != 0
        or document["real_corpus"] is not False
        or document["real_requirement_mapping"] is not False
        or document["real_capability_activation"] is not False
    ):
        raise ValueError("synthetic M4 fixture is not a permitted fixture")


def _write_synthetic_m3(root: Path) -> FrozenM3InputV1:
    _validate_synthetic_fixture()
    source_root = root / "source"
    source_root.mkdir(parents=True)
    source_path, source_lock_path = _write_synthetic_input(source_root)
    structural_root = root / "m1"
    structural = build_structural_corpus(source_path, source_lock_path, structural_root)
    source_lock = SourceLock.from_wire(json.loads(source_lock_path.read_bytes()))
    sources = tuple(
        StructuralCardRecordV1.from_wire(json.loads(line))
        for shard in ANALYSIS_SHARD_NAMES
        for line in (structural_root / "records" / f"{shard}.jsonl")
        .read_bytes()
        .splitlines()
    )
    records = tuple(
        CardAnalysisRecordV1(
            source=source_ref_for_record(item, source_lock.digest()),
            outcome=AnalysisOutcomeV1.UNRESOLVED_ANALYSIS,
            bundle=None,
            no_requirements_basis=None,
        )
        for item in sources
    )
    analysis_root = root / "m3"
    records_root = analysis_root / "records"
    trace_root = analysis_root / "trace"
    records_root.mkdir(parents=True)
    trace_root.mkdir()
    record_shards: list[AnalysisShardDescriptorV1] = []
    trace_shards: list[AnalysisShardDescriptorV1] = []
    for shard in ANALYSIS_SHARD_NAMES:
        shard_records = tuple(
            item
            for item in records
            if analysis_shard_for(item.source.oracle_id) == shard
        )
        record_path = records_root / f"{shard}.jsonl"
        record_path.write_bytes(
            b"".join(
                canonical_json_bytes(item.to_wire()) + b"\n" for item in shard_records
            )
        )
        trace_path = trace_root / f"{shard}.jsonl"
        trace_path.write_bytes(b"")
        record_shards.append(
            _descriptor(record_path, f"records/{shard}.jsonl", len(shard_records))
        )
        trace_shards.append(_descriptor(trace_path, f"trace/{shard}.jsonl", 0))
    manifest = AnalysisManifestV1(
        analysis_schema=CardAnalysisRecordV1.SCHEMA,
        source_lock_digest=source_lock.digest(),
        structural_record_schema=StructuralCardRecordV1.SCHEMA,
        structural_index_manifest_sha256=sha256_bytes(
            (structural_root / "structural-index-manifest.json").read_bytes()
        ),
        structural_index_aggregate_digest=structural.index_manifest.aggregate_digest,
        m2_requirement_schema=RequirementV1.SCHEMA,
        m2_bundle_schema=RequirementBundleV1.SCHEMA,
        producer_registry_digest="0" * 64,
        pattern_registry_digest="1" * 64,
        build_profile="census.m4-cli-synthetic.v1",
        record_count=len(records),
        record_identity_set_digest=record_identity_set_digest(
            tuple(card_source_key(item.source) for item in records)
        ),
        record_shards=tuple(record_shards),
        trace_shards=tuple(trace_shards),
    )
    manifest_path = analysis_root / "analysis-manifest.json"
    manifest_path.write_bytes(canonical_json_bytes(manifest.to_wire()))
    return FrozenM3InputV1(
        structural_output_directory=structural_root,
        analysis_output_directory=analysis_root,
        source_lock_path=source_lock_path,
        expected_analysis_manifest_sha256=sha256_bytes(manifest_path.read_bytes()),
    )


def _synthetic_m3_context(root: Path) -> tuple[FrozenM3InputV1, M3RequirementCorpusV1]:
    descriptor = _write_synthetic_m3(root)
    return descriptor, load_m3_requirement_corpus(descriptor)


def build_synthetic_m4_command(output_dir: str | Path) -> M4BuildResultV1:
    output_path = Path(output_dir)
    with tempfile.TemporaryDirectory(prefix="census-m4-cli-build-") as temp:
        m3_input, _ = _synthetic_m3_context(Path(temp))
        return build_reference_m4(
            m3_input,
            None,
            None,
            (),
            (),
            (),
            (),
            (),
            (),
            (),
            output_path,
        )


def _loaded_synthetic_result(
    output_dir: str | Path,
    corpus: M3RequirementCorpusV1,
) -> M4BuildResultV1:
    output_path = Path(output_dir)
    reread: _RereadResult
    if (output_path / REPORT_INDEX_FILENAME).exists():
        with tempfile.TemporaryDirectory(prefix="census-m4-core-reread-") as temp:
            core_root = Path(temp)
            for path in output_path.rglob("*"):
                relative = path.relative_to(output_path)
                if relative.as_posix() == REPORT_INDEX_FILENAME or (
                    relative.parts and relative.parts[0] == "reports"
                ):
                    continue
                target = core_root / relative
                if path.is_file():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(path, target)
            reread = _reread_output(core_root)
    else:
        reread = _reread_output(output_path)
    validate_m4_inputs(
        corpus,
        None,
        None,
        reread.definitions,
        reread.reviews,
        reread.relations,
        reread.admissibility,
        reread.links,
        reread.decisions,
        reread.evolution,
    )
    if (
        reread.manifest.m3_analysis_manifest_sha256
        != corpus.m3_analysis_manifest_sha256
    ):
        raise ValueError("synthetic M4 output is bound to a different M3 input")
    return M4BuildResultV1(
        output_path,
        reread.manifest,
        corpus.requirements,
        reread.definitions,
        reread.relations,
        reread.links,
        reread.decisions,
    )


def check_synthetic_m4_command(output_dir: str | Path) -> M4BuildResultV1:
    with tempfile.TemporaryDirectory(prefix="census-m4-cli-check-") as temp:
        _, corpus = _synthetic_m3_context(Path(temp))
        return _loaded_synthetic_result(output_dir, corpus)


def report_synthetic_m4_command(
    output_dir: str | Path,
) -> CapabilityReportBuildResultV1:
    with tempfile.TemporaryDirectory(prefix="census-m4-cli-report-") as temp:
        _, corpus = _synthetic_m3_context(Path(temp))
        result = _loaded_synthetic_result(output_dir, corpus)
        return build_capability_reports(result, m3_context=corpus)


__all__ = [
    "build_synthetic_m4_command",
    "check_synthetic_m4_command",
    "report_synthetic_m4_command",
]
