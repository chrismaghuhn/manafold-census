"""Independent M1 and SourceLock authority loading for the M3 build."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, cast

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
from .patterns import (
    EffectivePatternRegistryV1,
    MatcherKindV1,
    PatternEligibilityStateV1,
    PatternSourceFieldV1,
    pattern_rule_digest_for,
)
from .validate import _read_m1_authority

if TYPE_CHECKING:
    from .producer import (
        ProducerContextV1,
        ProducerDescriptorV1,
        ProducerFindingV1,
        ProducerResultV1,
    )


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


def _validate_finding_shape(finding: ProducerFindingV1) -> None:
    if finding.candidate_index is not None and (
        type(finding.candidate_index) is not int or finding.candidate_index < 0
    ):
        raise ValueError("finding candidate_index is invalid")
    fields = (finding.pattern_id, finding.pattern_version, finding.pattern_digest)
    if any(item is not None for item in fields) and not all(
        item is not None for item in fields
    ):
        raise ValueError("finding pattern identity must be complete")
    if finding.pattern_id is None:
        raise ValueError("pattern finding requires pattern identity")
    if not isinstance(finding.pattern_id, str) or not isinstance(
        finding.pattern_version, str
    ):
        raise ValueError("pattern finding identity is not text")
    if not isinstance(finding.pattern_digest, str):
        raise ValueError("pattern finding digest is not text")
    if not isinstance(finding.source_field, PatternSourceFieldV1):
        raise ValueError("pattern finding requires a source field")
    if finding.face_index is not None and (
        type(finding.face_index) is not int or finding.face_index < 0
    ):
        raise ValueError("finding face_index is invalid")
    if finding.exact_fragment is not None and not isinstance(
        finding.exact_fragment, str
    ):
        raise ValueError("finding exact_fragment is not text")
    if finding.clause_ordinal is not None and (
        type(finding.clause_ordinal) is not int or finding.clause_ordinal < 0
    ):
        raise ValueError("finding clause_ordinal is invalid")
    if finding.parser_span is not None:
        if (
            not isinstance(finding.parser_span, tuple | list)
            or len(finding.parser_span) != 2
        ):
            raise ValueError("finding parser_span is invalid")
        start, end = finding.parser_span
        if type(start) is not int or type(end) is not int or start < 0 or end < start:
            raise ValueError("finding parser_span is invalid")


def _validate_finding_match(
    finding: ProducerFindingV1,
    descriptor: ProducerDescriptorV1,
    record: StructuralCardRecordV1,
    registry: EffectivePatternRegistryV1,
) -> None:
    _validate_finding_shape(finding)
    key = (cast(str, finding.pattern_id), cast(str, finding.pattern_version))
    rules = {(item.pattern_id, item.pattern_version): item for item in registry.rules}
    eligibilities = {
        (item.pattern_id, item.pattern_version): item for item in registry.eligibility
    }
    rule = rules.get(key)
    eligibility = eligibilities.get(key)
    if rule is None or eligibility is None:
        raise ValueError("pattern finding references an unknown rule")
    if eligibility.eligibility is not PatternEligibilityStateV1.REVIEWED_FOR_REUSE:
        raise ValueError("pattern finding references an ineligible rule")
    if finding.pattern_digest != pattern_rule_digest_for(rule):
        raise ValueError("pattern finding digest does not match rule")
    if (rule.producer_id, rule.producer_version) != (
        descriptor.producer_id,
        descriptor.producer_version,
    ):
        raise ValueError("pattern finding producer does not match descriptor")
    if finding.source_field is not rule.source_scope.field:
        raise ValueError("pattern finding source field does not match rule")
    if finding.face_index != rule.source_scope.face_index:
        raise ValueError("pattern finding face index does not match rule")
    expected_fragment = (
        rule.match_text if rule.evidence_policy.value == "EXACT_FRAGMENT" else None
    )
    if finding.exact_fragment != expected_fragment:
        raise ValueError("pattern finding fragment does not match rule policy")
    if rule.source_scope.field is PatternSourceFieldV1.KEYWORDS:
        actual_match = (
            record.keywords is not None and rule.match_text in record.keywords
        )
    else:
        text = record.oracle_text
        if finding.face_index is not None:
            if record.faces is None or finding.face_index >= len(record.faces):
                raise ValueError("pattern finding face is missing")
            text = record.faces[finding.face_index].oracle_text
        actual_match = isinstance(text, str) and (
            rule.match_text in text
            if rule.matcher_kind is MatcherKindV1.EXACT_FRAGMENT
            else rule.match_text == text
        )
    if not actual_match:
        raise ValueError("pattern finding does not match the M1 source")


def validate_producer_findings(
    result: ProducerResultV1,
    descriptor: ProducerDescriptorV1,
    record: StructuralCardRecordV1,
    context: ProducerContextV1,
) -> None:
    from .producer import ProducerContractError, ProducerResultStatusV1

    if descriptor.pattern_registry_digest is None:
        if result.findings:
            raise ProducerContractError(
                "producer findings require a pattern registry dependency"
            )
        return
    if context.pattern_registry is None:
        raise ProducerContractError("pattern finding requires a registry snapshot")
    if not result.findings:
        if result.status is ProducerResultStatusV1.EMITTED:
            raise ProducerContractError(
                "pattern-dependent producer requires one finding per candidate"
            )
        return
    try:
        registry = EffectivePatternRegistryV1.from_wire(
            context.pattern_registry.to_wire()
        )
        if result.status is ProducerResultStatusV1.EMITTED and {
            item.candidate_index for item in result.findings
        } != set(range(len(result.candidates))):
            raise ValueError(
                "pattern-dependent producer requires one finding per candidate"
            )
        for finding in result.findings:
            _validate_finding_match(finding, descriptor, record, registry)
    except (TypeError, ValueError) as error:
        raise ProducerContractError(str(error)) from error


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
    "validate_producer_findings",
]
