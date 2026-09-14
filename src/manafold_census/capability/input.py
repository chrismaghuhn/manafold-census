"""Validated M3 input and Requirement-set values for the M4 boundary."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from ..analysis.manifest import AnalysisManifestV1
from ..analysis.model import AnalysisOutcomeV1, CardAnalysisRecordV1
from ..analysis.validate import validate_analysis_closure
from ..canonical import canonical_json_bytes
from ..digest import sha256_bytes
from ..semantic.identity import wire_digest_for
from ..semantic.model import RequirementV1
from ..validation import validate_document
from .identity import requirement_set_digest_for

_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _require_digest(field: str, value: object) -> str:
    if not isinstance(value, str) or _DIGEST_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _require_count(field: str, value: object) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value


@dataclass(frozen=True, slots=True)
class FrozenM3InputV1:
    """The complete, explicit input descriptor for one frozen M3 snapshot."""

    structural_output_directory: Path
    analysis_output_directory: Path
    source_lock_path: Path
    expected_analysis_manifest_sha256: str

    def __post_init__(self) -> None:
        for field in (
            "structural_output_directory",
            "analysis_output_directory",
            "source_lock_path",
        ):
            value = getattr(self, field)
            if not isinstance(value, Path):
                raise TypeError(f"{field} must be a pathlib.Path")
        _require_digest(
            "expected_analysis_manifest_sha256",
            self.expected_analysis_manifest_sha256,
        )


@dataclass(frozen=True, slots=True)
class M3RequirementCorpusV1:
    """Actual Requirements extracted from one independently validated M3 run."""

    m3_analysis_manifest_sha256: str
    m3_analysis_schema: str
    m2_requirement_schema: str
    m2_bundle_schema: str
    requirements: tuple[RequirementV1, ...]
    requirement_set_digest: str
    m3_record_count: int
    requirements_produced_card_count: int
    no_requirements_applicable_count: int
    unresolved_analysis_count: int

    def __post_init__(self) -> None:
        _require_digest("m3_analysis_manifest_sha256", self.m3_analysis_manifest_sha256)
        if self.m3_analysis_schema != "census.card-analysis.v1":
            raise ValueError("m3_analysis_schema must be census.card-analysis.v1")
        if self.m2_requirement_schema != "census.semantic-requirement.v1":
            raise ValueError(
                "m2_requirement_schema must be census.semantic-requirement.v1"
            )
        if self.m2_bundle_schema != "census.semantic-requirement-bundle.v1":
            raise ValueError(
                "m2_bundle_schema must be census.semantic-requirement-bundle.v1"
            )
        requirements = tuple(self.requirements)
        if any(not isinstance(item, RequirementV1) for item in requirements):
            raise TypeError("requirements must contain RequirementV1 values")
        requirement_ids = [item.requirement_id for item in requirements]
        if requirement_ids != sorted(requirement_ids):
            raise ValueError("requirements must be sorted by Requirement ID")
        if len(requirement_ids) != len(set(requirement_ids)):
            raise ValueError("requirements must contain unique Requirement IDs")
        object.__setattr__(self, "requirements", requirements)
        _require_digest("requirement_set_digest", self.requirement_set_digest)
        expected_digest = requirement_set_digest_for(
            self.m3_analysis_manifest_sha256,
            requirements,
        )
        if self.requirement_set_digest != expected_digest:
            raise ValueError("requirement_set_digest is stale or incorrect")

        counts = (
            _require_count("m3_record_count", self.m3_record_count),
            _require_count(
                "requirements_produced_card_count",
                self.requirements_produced_card_count,
            ),
            _require_count(
                "no_requirements_applicable_count",
                self.no_requirements_applicable_count,
            ),
            _require_count(
                "unresolved_analysis_count",
                self.unresolved_analysis_count,
            ),
        )
        if sum(counts[1:]) != counts[0]:
            raise ValueError("M3 outcome counts do not sum to m3_record_count")


def _read_analysis_manifest(
    input_descriptor: FrozenM3InputV1,
) -> tuple[AnalysisManifestV1, str]:
    path = input_descriptor.analysis_output_directory / "analysis-manifest.json"
    try:
        raw = path.read_bytes()
        document = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("M3 analysis manifest cannot be read as JSON") from error
    if not isinstance(document, dict):
        raise ValueError("M3 analysis manifest must contain an object")
    try:
        canonical = canonical_json_bytes(document)
    except (TypeError, ValueError) as error:
        raise ValueError("M3 analysis manifest is not canonical JSON") from error
    if raw != canonical:
        raise ValueError("M3 analysis manifest is not canonical JSON")
    manifest_sha256 = sha256_bytes(raw)
    if manifest_sha256 != input_descriptor.expected_analysis_manifest_sha256:
        raise ValueError("M3 manifest SHA does not match the selected input")
    try:
        validate_document(document, "analysis-manifest.v1.schema.json")
        manifest = AnalysisManifestV1.from_wire(document)
    except (TypeError, ValueError, OSError) as error:
        raise ValueError(f"M3 analysis manifest is invalid: {error}") from error
    return manifest, manifest_sha256


def _collect_requirements(
    records: tuple[object, ...],
) -> tuple[RequirementV1, ...]:
    by_id: dict[str, tuple[RequirementV1, str]] = {}
    for value in records:
        if not isinstance(value, CardAnalysisRecordV1):
            raise ValueError("M3 record result contains an unsupported value")
        if value.bundle is None:
            continue
        for requirement in value.bundle.requirements:
            if requirement.source != value.source:
                raise ValueError("Requirement source is not validated by M3")
            digest = wire_digest_for(requirement)
            existing = by_id.get(requirement.requirement_id)
            if existing is not None:
                if existing[1] != digest:
                    raise ValueError(
                        "duplicate Requirement ID has a different wire digest"
                    )
                continue
            by_id[requirement.requirement_id] = (requirement, digest)
    return tuple(by_id[requirement_id][0] for requirement_id in sorted(by_id))


def load_m3_requirement_corpus(
    input_descriptor: FrozenM3InputV1,
) -> M3RequirementCorpusV1:
    """Validate one frozen M3 artifact and return only persisted Requirements."""

    if not isinstance(input_descriptor, FrozenM3InputV1):
        raise TypeError("input_descriptor must be FrozenM3InputV1")
    manifest, manifest_sha256 = _read_analysis_manifest(input_descriptor)
    record_result, _trace_result = validate_analysis_closure(
        input_descriptor.structural_output_directory,
        input_descriptor.analysis_output_directory,
        input_descriptor.source_lock_path,
    )
    requirements = _collect_requirements(record_result.values)
    counts = {
        AnalysisOutcomeV1.REQUIREMENTS_PRODUCED: 0,
        AnalysisOutcomeV1.NO_REQUIREMENTS_APPLICABLE: 0,
        AnalysisOutcomeV1.UNRESOLVED_ANALYSIS: 0,
    }
    for value in record_result.values:
        if not isinstance(value, CardAnalysisRecordV1):
            raise ValueError("M3 record result contains an unsupported value")
        counts[value.outcome] += 1
    return M3RequirementCorpusV1(
        m3_analysis_manifest_sha256=manifest_sha256,
        m3_analysis_schema=manifest.analysis_schema,
        m2_requirement_schema=manifest.m2_requirement_schema,
        m2_bundle_schema=manifest.m2_bundle_schema,
        requirements=requirements,
        requirement_set_digest=requirement_set_digest_for(
            manifest_sha256,
            requirements,
        ),
        m3_record_count=len(record_result.values),
        requirements_produced_card_count=counts[
            AnalysisOutcomeV1.REQUIREMENTS_PRODUCED
        ],
        no_requirements_applicable_count=counts[
            AnalysisOutcomeV1.NO_REQUIREMENTS_APPLICABLE
        ],
        unresolved_analysis_count=counts[AnalysisOutcomeV1.UNRESOLVED_ANALYSIS],
    )


__all__ = [
    "FrozenM3InputV1",
    "M3RequirementCorpusV1",
    "load_m3_requirement_corpus",
]
