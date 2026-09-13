"""Independent M1 and SourceLock authority loading for the M3 build."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from ..canonical import canonical_json_bytes
from ..models import ArtifactManifest, DatasetManifest, SourceLock, StudySpec
from ..semantic.evidence import SourceRecordRefV1
from ..structural.build import (
    SHARD_COUNT,
    STRUCTURAL_ARTIFACT_ID,
    STRUCTURAL_ARTIFACT_KIND,
    STRUCTURAL_DATASET_ID,
    STRUCTURAL_DATASET_VERSION,
    STRUCTURAL_NORMALIZATION_PROFILE,
    STRUCTURAL_OPERATION,
    STRUCTURAL_STUDY_ID,
)
from ..structural.model import StructuralCardRecordV1
from ..validation import validate_document
from .manifest import SHARD_NAMES
from .validate import _read_m1_authority


@dataclass(frozen=True, slots=True)
class ReferenceBuildInputV1:
    root: Path
    source_lock_path: Path
    source_lock_digest: str
    records: tuple[StructuralCardRecordV1, ...]
    structural_index_aggregate_digest: str
    manifest_sha256: str


def _read_canonical_object(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    document = json.loads(raw)
    if not isinstance(document, dict):
        raise ValueError(f"{path} must contain an object")
    if raw != canonical_json_bytes(document):
        raise ValueError(f"{path} is not canonical JSON")
    return cast(dict[str, object], document)


def _read_lifecycle(
    root: Path, source_lock: SourceLock, record_count: int, manifest_sha256: str
) -> None:
    dataset_document = _read_canonical_object(root / "dataset-manifest.json")
    study_document = _read_canonical_object(root / "study-spec.json")
    artifact_document = _read_canonical_object(root / "artifact-manifest.json")
    validate_document(dataset_document, "dataset-manifest.v1.schema.json")
    validate_document(study_document, "study-spec.v1.schema.json")
    validate_document(artifact_document, "artifact-manifest.v1.schema.json")
    dataset = DatasetManifest.from_wire(dataset_document)
    study = StudySpec.from_wire(study_document)
    artifact = ArtifactManifest.from_wire(artifact_document)
    lock_digest = source_lock.digest()
    if (
        dataset.dataset_id != STRUCTURAL_DATASET_ID
        or dataset.dataset_version != STRUCTURAL_DATASET_VERSION
        or dataset.normalization_profile != STRUCTURAL_NORMALIZATION_PROFILE
        or dataset.source_lock_digest != lock_digest
        or dataset.record_count != record_count
    ):
        raise ValueError("M1 dataset lifecycle binding mismatch")
    if (
        study.study_id != STRUCTURAL_STUDY_ID
        or study.dataset_refs != (STRUCTURAL_DATASET_ID,)
        or study.operation != STRUCTURAL_OPERATION
        or study.to_wire()["parameters"]
        != {"shard_count": SHARD_COUNT, "source_lock_digest": lock_digest}
    ):
        raise ValueError("M1 study lifecycle binding mismatch")
    manifest_path = root / "structural-index-manifest.json"
    manifest_bytes = manifest_path.read_bytes()
    if (
        artifact.artifact_id != STRUCTURAL_ARTIFACT_ID
        or artifact.artifact_kind != STRUCTURAL_ARTIFACT_KIND
        or artifact.study_digest != study.digest()
        or artifact.content_sha256 != manifest_sha256
        or artifact.byte_length != len(manifest_bytes)
    ):
        raise ValueError("M1 artifact lifecycle binding mismatch")


def source_ref_for_record(
    record: StructuralCardRecordV1,
    source_lock_digest: str,
) -> SourceRecordRefV1:
    return SourceRecordRefV1(
        record_schema=StructuralCardRecordV1.SCHEMA,
        source_lock_digest=source_lock_digest,
        oracle_id=record.oracle_id,
        source_card_id=record.source_card_id,
        source_record_sha256=record.source_record_sha256,
    )


def load_reference_build_input(
    structural_index: str | Path,
    source_lock_path: str | Path | None,
) -> ReferenceBuildInputV1:
    root = Path(structural_index)
    manifest, _, manifest_sha256 = _read_m1_authority(root)
    lock_path = (
        Path(source_lock_path)
        if source_lock_path is not None
        else root / "source-lock.json"
    )
    lock_document = _read_canonical_object(lock_path)
    validate_document(lock_document, "source-lock.v1.schema.json")
    source_lock = SourceLock.from_wire(lock_document)
    records = tuple(
        sorted(
            (
                StructuralCardRecordV1.from_wire(json.loads(line))
                for shard in SHARD_NAMES
                for line in (root / "records" / f"{shard}.jsonl")
                .read_bytes()
                .splitlines()
            ),
            key=lambda item: item.oracle_id,
        )
    )
    _read_lifecycle(root, source_lock, len(records), manifest_sha256)
    return ReferenceBuildInputV1(
        root=root,
        source_lock_path=lock_path,
        source_lock_digest=source_lock.digest(),
        records=records,
        structural_index_aggregate_digest=manifest.aggregate_digest,
        manifest_sha256=manifest_sha256,
    )


__all__ = [
    "ReferenceBuildInputV1",
    "load_reference_build_input",
    "source_ref_for_record",
]
