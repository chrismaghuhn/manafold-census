"""Census 0.1 reviewed M4 authority-package wire models."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar, cast

from ..canonical import JSONValue
from ..capability.admissibility import SourceRequirementAdmissibilityV1
from ..capability.definition import CapabilityDefinitionV1
from ..capability.evolution import CapabilityEvolutionV1
from ..capability.link import RequirementCapabilityLinkV1
from ..capability.mapping import RequirementMappingDecisionV1
from ..capability.relations import CapabilityRelationV1
from ..capability.review import CapabilityReviewRecordV1
from ..digest import domain_digest

AUTHORITY_PACKAGE_SCHEMA = "census.m5-m4-authority-package.v1"
AUTHORITY_PACKAGE_DIGEST_DOMAIN = "census.m5-m4-authority-package.v1"
CENSUS_0_1_CAMPAIGN_ID = "m5.census-0.1"
SRA_MULTIPLICITY = "EXACTLY_ONE_PER_SELECTED_REQUIREMENT"
MAPPING_MULTIPLICITY = "ONE_PER_SELECTED_REQUIREMENT"
AUTHORITY_PACKAGE_FILES = (
    "capability-definitions.jsonl",
    "review-authority.jsonl",
    "capability-relations.jsonl",
    "requirement-admissibility.jsonl",
    "links.jsonl",
    "mapping-decisions.jsonl",
    "evolution.jsonl",
)
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_REQUIREMENT_ID = re.compile(r"^srq_[0-9a-f]{64}$")
_PACKAGE_FILE_SET = frozenset(AUTHORITY_PACKAGE_FILES)


def _text(field: str, value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty string")
    value.encode("utf-8")
    return value


def _digest(field: str, value: object) -> str:
    value = _text(field, value)
    if _DIGEST.fullmatch(value) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _count(field: str, value: object) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value


def _object(value: object, expected_keys: set[str], label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be an object")
    actual = set(value)
    if actual != expected_keys:
        raise ValueError(
            f"{label} keys differ: missing={sorted(expected_keys - actual)} "
            f"extra={sorted(actual - expected_keys)}"
        )
    return cast(dict[str, object], value)


@dataclass(frozen=True, slots=True)
class AuthorityFileDescriptorV1:
    relative_path: str
    sha256: str
    byte_length: int
    record_count: int

    _WIRE_KEYS: ClassVar[set[str]] = {
        "relative_path",
        "sha256",
        "byte_length",
        "record_count",
    }

    def __post_init__(self) -> None:
        if self.relative_path not in _PACKAGE_FILE_SET:
            raise ValueError("relative_path is not a permitted authority file")
        _digest("sha256", self.sha256)
        _count("byte_length", self.byte_length)
        _count("record_count", self.record_count)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "relative_path": self.relative_path,
            "sha256": self.sha256,
            "byte_length": self.byte_length,
            "record_count": self.record_count,
        }

    @classmethod
    def from_wire(cls, value: object) -> AuthorityFileDescriptorV1:
        document = _object(value, cls._WIRE_KEYS, "authority file descriptor")
        result = cls(
            cast(str, document["relative_path"]),
            cast(str, document["sha256"]),
            cast(int, document["byte_length"]),
            cast(int, document["record_count"]),
        )
        if result.to_wire() != document:
            raise ValueError("authority file descriptor is not canonical")
        return result


@dataclass(frozen=True, slots=True)
class AuthorityReviewPolicyV1:
    sra_authority_id: str
    sra_authority_version: str
    sra_reviewer_id: str
    capability_review_authority_id: str
    capability_review_authority_version: str
    capability_reviewer_id: str
    sra_multiplicity: str = SRA_MULTIPLICITY
    mapping_multiplicity: str = MAPPING_MULTIPLICITY

    _WIRE_KEYS: ClassVar[set[str]] = {
        "sra_authority_id",
        "sra_authority_version",
        "sra_reviewer_id",
        "capability_review_authority_id",
        "capability_review_authority_version",
        "capability_reviewer_id",
        "sra_multiplicity",
        "mapping_multiplicity",
    }

    def __post_init__(self) -> None:
        for field in (
            "sra_authority_id",
            "sra_authority_version",
            "sra_reviewer_id",
            "capability_review_authority_id",
            "capability_review_authority_version",
            "capability_reviewer_id",
        ):
            _text(field, getattr(self, field))
        if self.sra_multiplicity != SRA_MULTIPLICITY:
            raise ValueError("sra_multiplicity is not the frozen M5-03 policy")
        if self.mapping_multiplicity != MAPPING_MULTIPLICITY:
            raise ValueError("mapping_multiplicity is not the frozen M5-03 policy")

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "sra_authority_id": self.sra_authority_id,
            "sra_authority_version": self.sra_authority_version,
            "sra_reviewer_id": self.sra_reviewer_id,
            "capability_review_authority_id": self.capability_review_authority_id,
            "capability_review_authority_version": (
                self.capability_review_authority_version
            ),
            "capability_reviewer_id": self.capability_reviewer_id,
            "sra_multiplicity": self.sra_multiplicity,
            "mapping_multiplicity": self.mapping_multiplicity,
        }

    @classmethod
    def from_wire(cls, value: object) -> AuthorityReviewPolicyV1:
        document = _object(value, cls._WIRE_KEYS, "authority review policy")
        result = cls(**cast(Any, document))
        if result.to_wire() != document:
            raise ValueError("authority review policy is not canonical")
        return result


@dataclass(frozen=True, slots=True)
class AuthorityPackageManifestV1:
    schema: str
    campaign_id: str
    m3_analysis_manifest_sha256: str
    m4_requirement_set_digest: str
    selected_requirement_ids: tuple[str, ...]
    record_file_descriptors: tuple[AuthorityFileDescriptorV1, ...]
    review_policy: AuthorityReviewPolicyV1
    authority_package_digest: str

    SCHEMA: ClassVar[str] = AUTHORITY_PACKAGE_SCHEMA
    _WIRE_KEYS: ClassVar[set[str]] = {
        "schema",
        "campaign_id",
        "m3_analysis_manifest_sha256",
        "m4_requirement_set_digest",
        "selected_requirement_ids",
        "record_file_descriptors",
        "review_policy",
        "authority_package_digest",
    }

    def __post_init__(self) -> None:
        if self.schema != self.SCHEMA:
            raise ValueError(f"schema must be {self.SCHEMA}")
        _text("campaign_id", self.campaign_id)
        _digest("m3_analysis_manifest_sha256", self.m3_analysis_manifest_sha256)
        _digest("m4_requirement_set_digest", self.m4_requirement_set_digest)
        ids = tuple(self.selected_requirement_ids)
        if not ids or any(_REQUIREMENT_ID.fullmatch(item) is None for item in ids):
            raise ValueError("selected_requirement_ids must contain srq identities")
        if ids != tuple(sorted(ids)) or len(ids) != len(set(ids)):
            raise ValueError("selected_requirement_ids must be sorted and unique")
        descriptors = tuple(self.record_file_descriptors)
        if any(not isinstance(item, AuthorityFileDescriptorV1) for item in descriptors):
            raise TypeError("record_file_descriptors contain an invalid value")
        if tuple(item.relative_path for item in descriptors) != tuple(
            sorted(_PACKAGE_FILE_SET)
        ):
            raise ValueError(
                "record_file_descriptors must cover the exact package files"
            )
        if not isinstance(self.review_policy, AuthorityReviewPolicyV1):
            raise TypeError("review_policy must be AuthorityReviewPolicyV1")
        _digest("authority_package_digest", self.authority_package_digest)

    @classmethod
    def create(
        cls,
        *,
        campaign_id: str,
        m3_analysis_manifest_sha256: str,
        m4_requirement_set_digest: str,
        selected_requirement_ids: Sequence[str],
        record_file_descriptors: Sequence[AuthorityFileDescriptorV1],
        review_policy: AuthorityReviewPolicyV1,
    ) -> AuthorityPackageManifestV1:
        provisional = cls(
            cls.SCHEMA,
            campaign_id,
            m3_analysis_manifest_sha256,
            m4_requirement_set_digest,
            tuple(selected_requirement_ids),
            tuple(record_file_descriptors),
            review_policy,
            "0" * 64,
        )
        return cls(
            provisional.schema,
            provisional.campaign_id,
            provisional.m3_analysis_manifest_sha256,
            provisional.m4_requirement_set_digest,
            provisional.selected_requirement_ids,
            provisional.record_file_descriptors,
            provisional.review_policy,
            authority_package_digest_for(provisional),
        )

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "schema": self.schema,
            "campaign_id": self.campaign_id,
            "m3_analysis_manifest_sha256": self.m3_analysis_manifest_sha256,
            "m4_requirement_set_digest": self.m4_requirement_set_digest,
            "selected_requirement_ids": list(self.selected_requirement_ids),
            "record_file_descriptors": [
                item.to_wire() for item in self.record_file_descriptors
            ],
            "review_policy": self.review_policy.to_wire(),
            "authority_package_digest": self.authority_package_digest,
        }

    @classmethod
    def from_wire(cls, value: object) -> AuthorityPackageManifestV1:
        document = _object(value, cls._WIRE_KEYS, "authority package manifest")
        if document["schema"] != cls.SCHEMA:
            raise ValueError(f"schema must be {cls.SCHEMA}")
        raw_ids = document["selected_requirement_ids"]
        raw_descriptors = document["record_file_descriptors"]
        if not isinstance(raw_ids, list) or not isinstance(raw_descriptors, list):
            raise TypeError("manifest arrays have the wrong type")
        result = cls(
            cast(str, document["schema"]),
            cast(str, document["campaign_id"]),
            cast(str, document["m3_analysis_manifest_sha256"]),
            cast(str, document["m4_requirement_set_digest"]),
            tuple(cast(str, item) for item in raw_ids),
            tuple(
                AuthorityFileDescriptorV1.from_wire(item) for item in raw_descriptors
            ),
            AuthorityReviewPolicyV1.from_wire(document["review_policy"]),
            cast(str, document["authority_package_digest"]),
        )
        if result.to_wire() != document:
            raise ValueError("authority package manifest is not canonical")
        if result.authority_package_digest != authority_package_digest_for(result):
            raise ValueError("authority package digest is stale")
        return result


def _manifest_projection(manifest: AuthorityPackageManifestV1) -> dict[str, JSONValue]:
    return {
        "schema": manifest.schema,
        "campaign_id": manifest.campaign_id,
        "m3_analysis_manifest_sha256": manifest.m3_analysis_manifest_sha256,
        "m4_requirement_set_digest": manifest.m4_requirement_set_digest,
        "selected_requirement_ids": list(manifest.selected_requirement_ids),
        "record_file_descriptors": [
            item.to_wire() for item in manifest.record_file_descriptors
        ],
        "review_policy": manifest.review_policy.to_wire(),
    }


def authority_package_digest_for(manifest: AuthorityPackageManifestV1) -> str:
    if not isinstance(manifest, AuthorityPackageManifestV1):
        raise TypeError("manifest must be AuthorityPackageManifestV1")
    return domain_digest(
        AUTHORITY_PACKAGE_DIGEST_DOMAIN, _manifest_projection(manifest)
    )


@dataclass(frozen=True, slots=True)
class AuthorityPackageContentsV1:
    root: Path
    manifest: AuthorityPackageManifestV1
    capability_definitions: tuple[CapabilityDefinitionV1, ...]
    reviews: tuple[CapabilityReviewRecordV1, ...]
    relations: tuple[CapabilityRelationV1, ...]
    admissibility: tuple[SourceRequirementAdmissibilityV1, ...]
    links: tuple[RequirementCapabilityLinkV1, ...]
    mapping_decisions: tuple[RequirementMappingDecisionV1, ...]
    evolution: tuple[CapabilityEvolutionV1, ...]


def write_authority_package(*args: Any, **kwargs: Any) -> AuthorityPackageManifestV1:
    from .authority_package_io import write_authority_package as write

    return write(*args, **kwargs)


def load_authority_package(package_dir: str | Path) -> AuthorityPackageContentsV1:
    from .authority_package_io import load_authority_package as load

    return load(package_dir)


def validate_authority_package(
    package_dir: str | Path,
    lock: Any,
    corpus: Any,
) -> AuthorityPackageContentsV1:
    from .authority_validation import validate_authority_package as validate

    return validate(package_dir, lock, corpus)


__all__ = [
    "AUTHORITY_PACKAGE_DIGEST_DOMAIN",
    "AUTHORITY_PACKAGE_FILES",
    "AUTHORITY_PACKAGE_SCHEMA",
    "CENSUS_0_1_CAMPAIGN_ID",
    "MAPPING_MULTIPLICITY",
    "SRA_MULTIPLICITY",
    "AuthorityFileDescriptorV1",
    "AuthorityPackageContentsV1",
    "AuthorityPackageManifestV1",
    "AuthorityReviewPolicyV1",
    "authority_package_digest_for",
    "load_authority_package",
    "validate_authority_package",
    "write_authority_package",
]
