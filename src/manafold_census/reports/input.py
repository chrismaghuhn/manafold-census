"""Read and validate the authoritative inputs of a Census bundle."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from ..analysis.manifest import AnalysisManifestV1
from ..analysis.model import CardAnalysisRecordV1
from ..analysis.validate import inspect_record_shards
from ..canonical import canonical_json_bytes
from ..capability.build import _reread_output, _RereadResult
from ..capability.input import M3RequirementCorpusV1
from ..capability.manifest import M4OntologyManifestV1
from ..models import SourceLock
from ..release.bundle import (
    _validate_published_manifest,
    load_census_bundle,
    validate_census_bundle,
)
from ..release.input_lock import (
    CensusInputLockStatusV1,
    CensusInputLockV1,
    CensusInputProvisioningV1,
    validate_census_input_lock,
)
from ..release.manifest import (
    BundleComponentDescriptorV1,
    CensusBundleManifestV1,
)
from ..structural.manifest import StructuralCardIndexManifestV1
from ..structural.model import StructuralCardRecordV1


def _read_canonical_object(path: Path, label: str) -> tuple[dict[str, object], bytes]:
    try:
        raw = path.read_bytes()
        document = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} cannot be read as canonical JSON") from error
    if not isinstance(document, dict) or raw != canonical_json_bytes(document):
        raise ValueError(f"{label} is not canonical JSON")
    return cast(dict[str, object], document), raw


def _manifest_by_role(
    manifest: CensusBundleManifestV1, role: str
) -> BundleComponentDescriptorV1:
    for component in manifest.authoritative_components:
        if component.role == role:
            return component
    raise ValueError(f"bundle is missing component role {role}")


def _reconstruct_input_lock(
    root: Path, manifest: CensusBundleManifestV1
) -> CensusInputLockV1:
    """Reconstruct M5-02 assertions from the self-contained bundle."""

    m1_document, _ = _read_canonical_object(
        root / "inputs/m1/structural-index-manifest.json",
        "M1 structural manifest",
    )
    from ..validation import validate_document

    validate_document(m1_document, "structural-card-index-manifest.v1.schema.json")
    StructuralCardIndexManifestV1.from_wire(m1_document)

    m3_document, _ = _read_canonical_object(
        root / "inputs/m3/analysis-manifest.json",
        "M3 analysis manifest",
    )
    validate_document(m3_document, "analysis-manifest.v1.schema.json")
    m3_manifest = AnalysisManifestV1.from_wire(m3_document)

    m4_document, _ = _read_canonical_object(
        root / "inputs/m4/m4-ontology-manifest.json",
        "M4 ontology manifest",
    )
    validate_document(m4_document, "capability-ontology-manifest.v1.schema.json")
    m4_manifest = M4OntologyManifestV1.from_wire(m4_document)

    source_document, _ = _read_canonical_object(
        root / "inputs/source-lock.json", "SourceLock"
    )
    source_lock = SourceLock.from_wire(source_document)
    if source_lock.digest() != manifest.source_lock_digest:
        raise ValueError("SourceLock digest does not match the Census manifest")

    population = manifest.population
    m1_component = _manifest_by_role(manifest, "m1")
    m3_component = _manifest_by_role(manifest, "m3")
    source_component = _manifest_by_role(manifest, "source_lock")
    return CensusInputLockV1(
        source_lock_digest=manifest.source_lock_digest,
        source_lock_file_sha256=source_component.sha256,
        m1_structural_manifest_sha256=m1_component.sha256,
        m1_structural_aggregate_digest=cast(str, m1_component.aggregate_digest),
        m3_analysis_manifest_sha256=m3_component.sha256,
        m3_record_identity_set_digest=m3_manifest.record_identity_set_digest,
        m3_record_index_digest=m3_manifest.record_index_digest,
        m3_trace_index_digest=m3_manifest.trace_index_digest,
        expected_m4_requirement_set_digest=m4_manifest.requirement_set_digest,
        m1_structural_schema=manifest.schemas.structural_record,
        m3_analysis_schema=manifest.schemas.analysis_record,
        m2_requirement_schema=manifest.schemas.requirement,
        m2_bundle_schema=manifest.schemas.requirement_bundle,
        m4_ontology_schema="census.capability-ontology.v1",
        m4_dimension_registry_version="1",
        expected_oracle_identity_count=population.oracle_identity_count,
        expected_structural_record_count=population.structural_record_count,
        expected_analysis_record_count=population.analysis_record_count,
        expected_requirements_produced_card_count=(
            population.requirements_produced_card_count
        ),
        expected_no_requirements_applicable_count=(
            population.no_requirements_applicable_count
        ),
        expected_unresolved_analysis_count=population.unresolved_analysis_count,
        expected_requirement_count=population.requirement_count,
    )


def validated_bundle_inputs(
    bundle_directory: str | Path,
) -> tuple[
    CensusBundleManifestV1, CensusInputLockV1, M3RequirementCorpusV1, _RereadResult
]:
    """Validate the frozen bundle and return typed records needed by M5-06."""

    contents = load_census_bundle(bundle_directory)
    lock = _reconstruct_input_lock(contents.root, contents.manifest)
    provisioning = CensusInputProvisioningV1(
        source_lock_path=contents.root / "inputs/source-lock.json",
        structural_output_directory=contents.root / "inputs/m1",
        analysis_output_directory=contents.root / "inputs/m3",
    )
    input_result = validate_census_input_lock(lock, provisioning)
    if input_result.status is not CensusInputLockStatusV1.PASS:
        raise ValueError(f"M5-02 bundle validation is {input_result.status.value}")
    if input_result.m3_corpus is None:
        raise ValueError("M5-02 bundle validation returned no corpus")
    validate_census_bundle(contents.root, lock, input_result.m3_corpus)
    published = _reread_output(contents.root / "inputs/m4")
    _validate_published_manifest(published.manifest, lock, input_result.m3_corpus)
    return contents.manifest, lock, input_result.m3_corpus, published


def read_structural_records(root: Path) -> tuple[StructuralCardRecordV1, ...]:
    """Read the already validated M1 records in canonical shard order."""

    records: list[StructuralCardRecordV1] = []
    for shard in tuple("0123456789abcdef"):
        path = root / "inputs/m1/records" / f"{shard}.jsonl"
        try:
            raw = path.read_bytes()
        except OSError as error:
            raise ValueError(f"M1 shard cannot be read: {path}") from error
        previous: str | None = None
        for line in raw.splitlines(keepends=True):
            if not line.endswith(b"\n"):
                raise ValueError(f"M1 shard is missing a final LF: {path}")
            try:
                record = StructuralCardRecordV1.from_wire(json.loads(line))
            except (
                TypeError,
                ValueError,
                UnicodeDecodeError,
                json.JSONDecodeError,
            ) as error:
                raise ValueError(
                    f"M1 shard contains an invalid record: {path}"
                ) from error
            if line != canonical_json_bytes(record.to_wire()) + b"\n":
                raise ValueError(f"M1 shard is not canonical JSONL: {path}")
            if not record.oracle_id.startswith(shard):
                raise ValueError(f"M1 record is in the wrong shard: {path}")
            if previous is not None and record.oracle_id <= previous:
                raise ValueError(f"M1 shard is not ordered: {path}")
            previous = record.oracle_id
            records.append(record)
    return tuple(records)


def read_analysis_records(root: Path) -> tuple[CardAnalysisRecordV1, ...]:
    result = inspect_record_shards(root / "inputs/m3/records")
    return tuple(cast(CardAnalysisRecordV1, item) for item in result.values)


__all__ = [
    "read_analysis_records",
    "read_structural_records",
    "validated_bundle_inputs",
]
