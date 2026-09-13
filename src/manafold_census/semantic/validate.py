"""Source-aware validation against one already-loaded M1 structural record."""

from __future__ import annotations

from typing import Final

from ..structural.model import StructuralCardRecordV1, StructuralFaceV1
from .bundle import RequirementBundleV1
from .evidence import (
    M1_FACE_FIELDS,
    M1_TEXT_FACE_FIELDS,
    M1_TEXT_PARENT_FIELDS,
    M1_TOP_LEVEL_FIELDS,
    EvidenceV1,
    SourceRecordRefV1,
    StructuralFaceEvidenceV1,
    StructuralFieldEvidenceV1,
    StructuralKeywordEvidenceV1,
    StructuralRecordEvidenceV1,
)
from .model import RequirementV1

_PARENT_ONLY_FIELDS: Final[frozenset[str]] = M1_TOP_LEVEL_FIELDS - {"record"}


def _validate_source_reference(
    source: SourceRecordRefV1,
    record: StructuralCardRecordV1,
    expected_source_lock_digest: str,
) -> None:
    if source.record_schema != StructuralCardRecordV1.SCHEMA:
        raise ValueError("source record schema mismatch")
    if source.source_lock_digest != expected_source_lock_digest:
        raise ValueError("source lock digest mismatch")
    checks = (
        ("oracle_id", source.oracle_id, record.oracle_id),
        ("source_card_id", source.source_card_id, record.source_card_id),
        (
            "source_record_sha256",
            source.source_record_sha256,
            record.source_record_sha256,
        ),
    )
    for field, actual, expected in checks:
        if actual != expected:
            raise ValueError(f"source {field} mismatch")


def _face_at(record: StructuralCardRecordV1, face_index: int) -> StructuralFaceV1:
    if record.faces is None or face_index >= len(record.faces):
        raise ValueError("face index is missing from the structural record")
    face = record.faces[face_index]
    if face.face_index != face_index:
        raise ValueError("face index does not match the M1 face position")
    return face


def _field_value(
    evidence: StructuralFieldEvidenceV1, record: StructuralCardRecordV1
) -> object:
    if evidence.face_index is None:
        if evidence.field not in _PARENT_ONLY_FIELDS:
            raise ValueError("structural field is not a parent M1 field")
        return getattr(record, evidence.field)
    if evidence.field not in M1_FACE_FIELDS:
        raise ValueError("structural field is not a face M1 field")
    return getattr(_face_at(record, evidence.face_index), evidence.field)


def _validate_evidence(
    evidence: EvidenceV1,
    record: StructuralCardRecordV1,
    expected_source_lock_digest: str,
) -> None:
    if isinstance(
        evidence,
        StructuralRecordEvidenceV1
        | StructuralFaceEvidenceV1
        | StructuralFieldEvidenceV1
        | StructuralKeywordEvidenceV1,
    ):
        _validate_source_reference(evidence.source, record, expected_source_lock_digest)
    if isinstance(evidence, StructuralRecordEvidenceV1):
        return
    if isinstance(evidence, StructuralFaceEvidenceV1):
        _face_at(record, evidence.face_index)
        return
    if isinstance(evidence, StructuralFieldEvidenceV1):
        value = _field_value(evidence, record)
        if evidence.fragment is not None:
            text_fields = (
                M1_TEXT_FACE_FIELDS
                if evidence.face_index is not None
                else M1_TEXT_PARENT_FIELDS
            )
            if evidence.field not in text_fields or not isinstance(value, str):
                raise ValueError("fragment requires a textual M1 field")
            if evidence.fragment not in value:
                raise ValueError("fragment is not an exact M1 substring")
        return
    if isinstance(evidence, StructuralKeywordEvidenceV1):
        if record.keywords is None:
            raise ValueError("keyword evidence requires an M1 keywords array")
        if evidence.keyword_index >= len(record.keywords):
            raise ValueError("keyword index is missing from the M1 keywords array")
        if record.keywords[evidence.keyword_index] != evidence.keyword_value:
            raise ValueError("keyword value does not match M1 source")


def validate_requirement_against_structural_record(
    requirement: RequirementV1,
    record: StructuralCardRecordV1,
    expected_source_lock_digest: str,
) -> None:
    """Validate one Requirement's source references against one M1 record."""

    if not isinstance(requirement, RequirementV1):
        raise TypeError("requirement must be RequirementV1")
    if not isinstance(record, StructuralCardRecordV1):
        raise TypeError("record must be StructuralCardRecordV1")
    _validate_source_reference(requirement.source, record, expected_source_lock_digest)
    for evidence in requirement.evidence:
        _validate_evidence(evidence, record, expected_source_lock_digest)


def validate_bundle_against_structural_record(
    bundle: RequirementBundleV1,
    record: StructuralCardRecordV1,
    expected_source_lock_digest: str,
) -> None:
    """Validate every Requirement in one bundle against one M1 record."""

    if not isinstance(bundle, RequirementBundleV1):
        raise TypeError("bundle must be RequirementBundleV1")
    if not isinstance(record, StructuralCardRecordV1):
        raise TypeError("record must be StructuralCardRecordV1")
    _validate_source_reference(bundle.source, record, expected_source_lock_digest)
    for requirement in bundle.requirements:
        validate_requirement_against_structural_record(
            requirement, record, expected_source_lock_digest
        )


__all__ = [
    "validate_bundle_against_structural_record",
    "validate_requirement_against_structural_record",
]
