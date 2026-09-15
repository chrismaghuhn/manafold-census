"""Census 0.1 input-lock model and explicit frozen-artifact validation."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, ClassVar, cast

from ..analysis.manifest import AnalysisManifestV1
from ..canonical import MAX_INTEGER, JSONValue, canonical_json_bytes
from ..capability.identity import requirement_set_digest_for
from ..capability.input import (
    FrozenM3InputV1,
    M3RequirementCorpusV1,
    load_m3_requirement_corpus,
)
from ..capability.manifest import M4_DIMENSION_REGISTRY_VERSION
from ..digest import sha256_bytes
from ..models import SourceLock
from ..structural.manifest import StructuralCardIndexManifestV1
from ..validation import validate_document

INPUT_LOCK_SCHEMA = "census.census-input-lock.v1"
INPUT_LOCK_VERSION = 1
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")

_TEXT_FIELDS = {
    "m1_structural_schema": "census.structural-card.v1",
    "m3_analysis_schema": "census.card-analysis.v1",
    "m2_requirement_schema": "census.semantic-requirement.v1",
    "m2_bundle_schema": "census.semantic-requirement-bundle.v1",
    "m4_ontology_schema": "census.capability-ontology.v1",
    "m4_dimension_registry_version": M4_DIMENSION_REGISTRY_VERSION,
}
_DIGEST_FIELDS = (
    "source_lock_digest",
    "source_lock_file_sha256",
    "m1_structural_manifest_sha256",
    "m1_structural_aggregate_digest",
    "m3_analysis_manifest_sha256",
    "m3_record_identity_set_digest",
    "m3_record_index_digest",
    "m3_trace_index_digest",
    "expected_m4_requirement_set_digest",
)
_COUNT_FIELDS = (
    "expected_oracle_identity_count",
    "expected_structural_record_count",
    "expected_analysis_record_count",
    "expected_requirements_produced_card_count",
    "expected_no_requirements_applicable_count",
    "expected_unresolved_analysis_count",
    "expected_requirement_count",
)


def _require_object(
    value: object, expected_keys: set[str], label: str
) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be an object")
    actual_keys = set(value)
    missing = expected_keys - actual_keys
    unexpected = actual_keys - expected_keys
    if missing or unexpected:
        details: list[str] = []
        if missing:
            details.append(f"missing properties: {sorted(missing)}")
        if unexpected:
            details.append(f"unexpected properties: {sorted(unexpected)}")
        raise ValueError(f"{label} has {'; '.join(details)}")
    return cast(dict[str, object], value)


def _require_digest(field: str, value: object) -> str:
    if not isinstance(value, str) or _DIGEST_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _require_count(field: str, value: object) -> int:
    if type(value) is not int or value < 0 or value > MAX_INTEGER:
        raise ValueError(f"{field} must be a non-negative signed 64-bit integer")
    return value


class CensusInputLockStatusV1(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
    NOT_RUN = "NOT_RUN"


@dataclass(frozen=True, slots=True)
class CensusInputLockV1:
    """Immutable identity and population assertions for one M5 input set."""

    source_lock_digest: str
    source_lock_file_sha256: str
    m1_structural_manifest_sha256: str
    m1_structural_aggregate_digest: str
    m3_analysis_manifest_sha256: str
    m3_record_identity_set_digest: str
    m3_record_index_digest: str
    m3_trace_index_digest: str
    expected_m4_requirement_set_digest: str
    m1_structural_schema: str
    m3_analysis_schema: str
    m2_requirement_schema: str
    m2_bundle_schema: str
    m4_ontology_schema: str
    m4_dimension_registry_version: str
    expected_oracle_identity_count: int
    expected_structural_record_count: int
    expected_analysis_record_count: int
    expected_requirements_produced_card_count: int
    expected_no_requirements_applicable_count: int
    expected_unresolved_analysis_count: int
    expected_requirement_count: int

    SCHEMA: ClassVar[str] = INPUT_LOCK_SCHEMA
    LOCK_VERSION: ClassVar[int] = INPUT_LOCK_VERSION
    _WIRE_KEYS: ClassVar[set[str]] = {
        "schema",
        "lock_version",
        *_DIGEST_FIELDS,
        *_TEXT_FIELDS,
        *_COUNT_FIELDS,
    }

    def __post_init__(self) -> None:
        for field in _DIGEST_FIELDS:
            _require_digest(field, getattr(self, field))
        for field, expected in _TEXT_FIELDS.items():
            value = getattr(self, field)
            if not isinstance(value, str) or value != expected:
                raise ValueError(f"{field} must be {expected}")
        for field in _COUNT_FIELDS:
            _require_count(field, getattr(self, field))
        if self.expected_oracle_identity_count != self.expected_structural_record_count:
            raise ValueError(
                "expected Oracle identity and structural record counts must match"
            )
        if self.expected_structural_record_count != self.expected_analysis_record_count:
            raise ValueError(
                "expected structural and analysis record counts must match"
            )
        outcome_total = (
            self.expected_requirements_produced_card_count
            + self.expected_no_requirements_applicable_count
            + self.expected_unresolved_analysis_count
        )
        if outcome_total != self.expected_analysis_record_count:
            raise ValueError("expected M3 outcome counts must sum to analysis count")

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "schema": self.SCHEMA,
            "lock_version": self.LOCK_VERSION,
            **{
                field: cast(JSONValue, getattr(self, field))
                for field in (*_DIGEST_FIELDS, *_TEXT_FIELDS, *_COUNT_FIELDS)
            },
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_wire())

    def digest(self) -> str:
        """Return the raw SHA-256 of the exact canonical lock bytes."""

        return sha256_bytes(self.canonical_bytes())

    @classmethod
    def from_wire(cls, value: object) -> CensusInputLockV1:
        document = _require_object(value, cls._WIRE_KEYS, "Census input lock")
        if document["schema"] != cls.SCHEMA:
            raise ValueError(f"schema must be {cls.SCHEMA}")
        if (
            type(document["lock_version"]) is not int
            or document["lock_version"] != cls.LOCK_VERSION
        ):
            raise ValueError(f"lock_version must be {cls.LOCK_VERSION}")
        wire_values = {
            field: document[field]
            for field in (*_DIGEST_FIELDS, *_TEXT_FIELDS, *_COUNT_FIELDS)
        }
        return cls(**cast(Any, wire_values))


@dataclass(frozen=True, slots=True)
class CensusInputProvisioningV1:
    """Explicit local paths for one already-selected frozen input set."""

    source_lock_path: Path
    structural_output_directory: Path
    analysis_output_directory: Path

    def __post_init__(self) -> None:
        for field in (
            "source_lock_path",
            "structural_output_directory",
            "analysis_output_directory",
        ):
            if not isinstance(getattr(self, field), Path):
                raise TypeError(f"{field} must be a pathlib.Path")


@dataclass(frozen=True, slots=True)
class CensusInputCheckV1:
    name: str
    status: CensusInputLockStatusV1
    detail: str


@dataclass(frozen=True, slots=True)
class CensusInputValidationResultV1:
    status: CensusInputLockStatusV1
    checks: tuple[CensusInputCheckV1, ...]
    m3_corpus: M3RequirementCorpusV1 | None

    def __post_init__(self) -> None:
        status = CensusInputLockStatusV1(self.status)
        checks = tuple(self.checks)
        if any(not isinstance(check, CensusInputCheckV1) for check in checks):
            raise TypeError("checks must contain CensusInputCheckV1 values")
        if not checks:
            raise ValueError("checks must not be empty")
        if status is CensusInputLockStatusV1.PASS and self.m3_corpus is None:
            raise ValueError("PASS requires a validated M3 corpus")
        if status is not CensusInputLockStatusV1.PASS and self.m3_corpus is not None:
            raise ValueError("non-PASS result cannot expose an M3 corpus")
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "checks", checks)


def load_census_input_lock(path: str | Path) -> CensusInputLockV1:
    """Read and validate one canonical CensusInputLockV1 document."""

    lock_path = Path(path)
    raw = lock_path.read_bytes()
    try:
        document = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("Census input lock cannot be read as JSON") from error
    if raw != canonical_json_bytes(document):
        raise ValueError("Census input lock is not canonical JSON")
    validate_document(document, "census-input-lock.v1.schema.json")
    return CensusInputLockV1.from_wire(document)


def _result(
    status: CensusInputLockStatusV1,
    name: str,
    detail: str,
    corpus: M3RequirementCorpusV1 | None = None,
) -> CensusInputValidationResultV1:
    return CensusInputValidationResultV1(
        status=status,
        checks=(CensusInputCheckV1(name, status, detail),),
        m3_corpus=corpus,
    )


def _read_canonical_document(
    path: Path, schema: str, label: str
) -> tuple[dict[str, object], bytes]:
    raw = path.read_bytes()
    try:
        document = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} cannot be read as JSON") from error
    if not isinstance(document, dict):
        raise ValueError(f"{label} must be an object")
    if raw != canonical_json_bytes(document):
        raise ValueError(f"{label} is not canonical JSON")
    validate_document(document, schema)
    return cast(dict[str, object], document), raw


def validate_census_input_lock(
    lock: CensusInputLockV1,
    provisioning: CensusInputProvisioningV1,
) -> CensusInputValidationResultV1:
    """Validate one lock against exactly the explicitly supplied artifacts."""

    if not isinstance(lock, CensusInputLockV1):
        raise TypeError("lock must be CensusInputLockV1")
    if not isinstance(provisioning, CensusInputProvisioningV1):
        raise TypeError("provisioning must be CensusInputProvisioningV1")

    expected_paths = (
        ("source_lock_path", provisioning.source_lock_path, True),
        (
            "structural_output_directory",
            provisioning.structural_output_directory,
            False,
        ),
        ("analysis_output_directory", provisioning.analysis_output_directory, False),
    )
    for field, path, is_file in expected_paths:
        available = path.is_file() if is_file else path.is_dir()
        if not available:
            return _result(
                CensusInputLockStatusV1.BLOCKED,
                field,
                f"{field} is missing or has the wrong type: {path}",
            )

    try:
        source_document, source_raw = _read_canonical_document(
            provisioning.source_lock_path,
            "source-lock.v1.schema.json",
            "source lock",
        )
        source_lock = SourceLock.from_wire(source_document)
        if sha256_bytes(source_raw) != lock.source_lock_file_sha256:
            return _result(
                CensusInputLockStatusV1.FAIL,
                "source-lock-file",
                "source lock file SHA-256 mismatch",
            )
        if source_lock.digest() != lock.source_lock_digest:
            return _result(
                CensusInputLockStatusV1.FAIL,
                "source-lock-digest",
                "source lock semantic digest mismatch",
            )

        m1_path = (
            provisioning.structural_output_directory / "structural-index-manifest.json"
        )
        m1_document, m1_raw = _read_canonical_document(
            m1_path,
            "structural-card-index-manifest.v1.schema.json",
            "M1 structural manifest",
        )
        m1_manifest = StructuralCardIndexManifestV1.from_wire(m1_document)
        if sha256_bytes(m1_raw) != lock.m1_structural_manifest_sha256:
            return _result(
                CensusInputLockStatusV1.FAIL,
                "m1-manifest",
                "M1 structural manifest SHA-256 mismatch",
            )
        if m1_manifest.aggregate_digest != lock.m1_structural_aggregate_digest:
            return _result(
                CensusInputLockStatusV1.FAIL,
                "m1-aggregate",
                "M1 structural aggregate digest mismatch",
            )
        m1_record_count = sum(shard.record_count for shard in m1_manifest.shards)
        if m1_record_count != lock.expected_structural_record_count:
            return _result(
                CensusInputLockStatusV1.FAIL,
                "m1-count",
                "M1 structural record count mismatch",
            )

        m3_path = provisioning.analysis_output_directory / "analysis-manifest.json"
        m3_document, m3_raw = _read_canonical_document(
            m3_path,
            "analysis-manifest.v1.schema.json",
            "M3 analysis manifest",
        )
        m3_manifest = AnalysisManifestV1.from_wire(m3_document)
        m3_manifest_sha256 = sha256_bytes(m3_raw)
        if m3_manifest_sha256 != lock.m3_analysis_manifest_sha256:
            return _result(
                CensusInputLockStatusV1.FAIL,
                "m3-manifest",
                "M3 analysis manifest SHA-256 mismatch",
            )
        if m3_manifest.record_identity_set_digest != lock.m3_record_identity_set_digest:
            return _result(
                CensusInputLockStatusV1.FAIL,
                "m3-identity",
                "M3 identity set digest mismatch",
            )
        if m3_manifest.record_index_digest != lock.m3_record_index_digest:
            return _result(
                CensusInputLockStatusV1.FAIL,
                "m3-record-index",
                "M3 record index digest mismatch",
            )
        if m3_manifest.trace_index_digest != lock.m3_trace_index_digest:
            return _result(
                CensusInputLockStatusV1.FAIL,
                "m3-trace-index",
                "M3 trace index digest mismatch",
            )

        m3_input = FrozenM3InputV1(
            structural_output_directory=provisioning.structural_output_directory,
            analysis_output_directory=provisioning.analysis_output_directory,
            source_lock_path=provisioning.source_lock_path,
            expected_analysis_manifest_sha256=m3_manifest_sha256,
        )
        corpus = load_m3_requirement_corpus(m3_input)
        if corpus.m3_analysis_manifest_sha256 != lock.m3_analysis_manifest_sha256:
            return _result(
                CensusInputLockStatusV1.FAIL,
                "m3-corpus",
                "M3 corpus manifest identity mismatch",
            )
        if corpus.requirement_set_digest != lock.expected_m4_requirement_set_digest:
            return _result(
                CensusInputLockStatusV1.FAIL,
                "m4-requirement-set",
                "M4 Requirement-set digest mismatch",
            )
        if (
            requirement_set_digest_for(
                lock.m3_analysis_manifest_sha256, corpus.requirements
            )
            != lock.expected_m4_requirement_set_digest
        ):
            return _result(
                CensusInputLockStatusV1.FAIL,
                "m4-requirement-set",
                "M4 Requirement-set recomputation mismatch",
            )
        actual_counts = {
            "expected_oracle_identity_count": m1_record_count,
            "expected_structural_record_count": m1_record_count,
            "expected_analysis_record_count": corpus.m3_record_count,
            "expected_requirements_produced_card_count": (
                corpus.requirements_produced_card_count
            ),
            "expected_no_requirements_applicable_count": (
                corpus.no_requirements_applicable_count
            ),
            "expected_unresolved_analysis_count": corpus.unresolved_analysis_count,
            "expected_requirement_count": len(corpus.requirements),
        }
        for field, actual in actual_counts.items():
            if getattr(lock, field) != actual:
                return _result(
                    CensusInputLockStatusV1.FAIL,
                    "population",
                    f"{field} mismatch",
                )
    except FileNotFoundError as error:
        return _result(
            CensusInputLockStatusV1.BLOCKED, "artifact-availability", str(error)
        )
    except OSError as error:
        return _result(
            CensusInputLockStatusV1.BLOCKED, "artifact-availability", str(error)
        )
    except (TypeError, ValueError) as error:
        return _result(CensusInputLockStatusV1.FAIL, "cross-check", str(error))

    checks = tuple(
        CensusInputCheckV1(name, CensusInputLockStatusV1.PASS, "verified")
        for name in (
            "source-lock-file",
            "source-lock-digest",
            "m1-manifest",
            "m1-aggregate",
            "m1-count",
            "m3-manifest",
            "m3-identity",
            "m3-record-index",
            "m3-trace-index",
            "m3-closure",
            "m4-requirement-set",
            "population",
        )
    )
    return CensusInputValidationResultV1(
        status=CensusInputLockStatusV1.PASS,
        checks=checks,
        m3_corpus=corpus,
    )


__all__ = [
    "CensusInputCheckV1",
    "CensusInputLockStatusV1",
    "CensusInputLockV1",
    "CensusInputProvisioningV1",
    "CensusInputValidationResultV1",
    "INPUT_LOCK_SCHEMA",
    "INPUT_LOCK_VERSION",
    "load_census_input_lock",
    "validate_census_input_lock",
]
