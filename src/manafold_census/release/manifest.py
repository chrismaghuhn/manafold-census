"""Closed Census 0.1 bundle manifest and release identity."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, ClassVar, cast

from ..canonical import JSONValue, canonical_json_bytes
from ..digest import domain_digest, sha256_bytes

BUNDLE_SCHEMA = "census.census-bundle-manifest.v1"
BUNDLE_MANIFEST_FILENAME = "census-manifest.json"
BUNDLE_VERSION = "0.1.0"
CENSUS_RELEASE_ID_DOMAIN = "census.census-release-id.v1"
AUTHORITATIVE_COMPONENT_ROLES = (
    "source_lock",
    "m1",
    "m3",
    "m4_authority",
    "m4",
)
COMPONENT_MANIFEST_PATHS = {
    "source_lock": "inputs/source-lock.json",
    "m1": "inputs/m1/structural-index-manifest.json",
    "m3": "inputs/m3/analysis-manifest.json",
    "m4_authority": "inputs/m4-authority/authority-manifest.json",
    "m4": "inputs/m4/m4-ontology-manifest.json",
}
COMPONENT_SCHEMAS = {
    "source_lock": "census.source-lock.v1",
    "m1": "census.structural-card-index-manifest.v1",
    "m3": "census.analysis-manifest.v1",
    "m4_authority": "census.m5-m4-authority-package.v1",
    "m4": "census.m4-ontology-manifest.v1",
}
QUERY_CONTRACT = "census.query.v1"
MINIMUM_EXPLORER_VERSION = "0.1.0"
BUNDLE_FORMAT_MAJOR = 1
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_RELEASE_ID = re.compile(r"^censusrel_[0-9a-f]{64}$")


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
class BundleComponentDescriptorV1:
    role: str
    manifest_path: str
    sha256: str
    byte_length: int
    schema: str
    aggregate_digest: str | None = None

    _BASE_KEYS: ClassVar[set[str]] = {
        "role",
        "manifest_path",
        "sha256",
        "byte_length",
        "schema",
    }

    def __post_init__(self) -> None:
        if self.role not in AUTHORITATIVE_COMPONENT_ROLES:
            raise ValueError("component role is not authoritative")
        if self.manifest_path != COMPONENT_MANIFEST_PATHS[self.role]:
            raise ValueError("component manifest path does not match its role")
        if self.schema != COMPONENT_SCHEMAS[self.role]:
            raise ValueError("component schema does not match its role")
        _digest("sha256", self.sha256)
        _count("byte_length", self.byte_length)
        if self.role == "m1":
            if self.aggregate_digest is None:
                raise ValueError("M1 component requires aggregate_digest")
            _digest("aggregate_digest", self.aggregate_digest)
        elif self.aggregate_digest is not None:
            raise ValueError("only the M1 component may contain aggregate_digest")

    def to_wire(self) -> dict[str, JSONValue]:
        result: dict[str, JSONValue] = {
            "role": self.role,
            "manifest_path": self.manifest_path,
            "sha256": self.sha256,
            "byte_length": self.byte_length,
            "schema": self.schema,
        }
        if self.aggregate_digest is not None:
            result["aggregate_digest"] = self.aggregate_digest
        return result

    @classmethod
    def from_wire(cls, value: object) -> BundleComponentDescriptorV1:
        if not isinstance(value, dict):
            raise TypeError("bundle component must be an object")
        role = value.get("role")
        if not isinstance(role, str):
            raise ValueError("bundle component role is required")
        keys = cls._BASE_KEYS | ({"aggregate_digest"} if role == "m1" else set())
        document = _object(value, keys, "bundle component")
        result = cls(
            cast(str, document["role"]),
            cast(str, document["manifest_path"]),
            cast(str, document["sha256"]),
            cast(int, document["byte_length"]),
            cast(str, document["schema"]),
            cast(str | None, document.get("aggregate_digest")),
        )
        if result.to_wire() != document:
            raise ValueError("bundle component is not canonical")
        return result


@dataclass(frozen=True, slots=True)
class BundlePopulationV1:
    oracle_identity_count: int
    structural_record_count: int
    analysis_record_count: int
    requirement_count: int
    requirements_produced_card_count: int
    no_requirements_applicable_count: int
    unresolved_analysis_count: int

    _WIRE_KEYS: ClassVar[set[str]] = {
        "oracle_identity_count",
        "structural_record_count",
        "analysis_record_count",
        "requirement_count",
        "requirements_produced_card_count",
        "no_requirements_applicable_count",
        "unresolved_analysis_count",
    }

    def __post_init__(self) -> None:
        for field in self._WIRE_KEYS:
            _count(field, getattr(self, field))

    def to_wire(self) -> dict[str, JSONValue]:
        return {field: getattr(self, field) for field in self._WIRE_KEYS}

    @classmethod
    def from_wire(cls, value: object) -> BundlePopulationV1:
        document = _object(value, cls._WIRE_KEYS, "bundle population")
        return cls(**cast(Any, document))


@dataclass(frozen=True, slots=True)
class BundleSchemaCompatibilityV1:
    structural_record: str
    analysis_record: str
    requirement: str
    requirement_bundle: str
    m4_manifest: str

    _WIRE_KEYS: ClassVar[set[str]] = {
        "structural_record",
        "analysis_record",
        "requirement",
        "requirement_bundle",
        "m4_manifest",
    }
    _EXPECTED: ClassVar[dict[str, str]] = {
        "structural_record": "census.structural-card.v1",
        "analysis_record": "census.card-analysis.v1",
        "requirement": "census.semantic-requirement.v1",
        "requirement_bundle": "census.semantic-requirement-bundle.v1",
        "m4_manifest": "census.m4-ontology-manifest.v1",
    }

    def __post_init__(self) -> None:
        for field, expected in self._EXPECTED.items():
            if getattr(self, field) != expected:
                raise ValueError(f"{field} must be {expected}")

    def to_wire(self) -> dict[str, JSONValue]:
        return {field: getattr(self, field) for field in self._WIRE_KEYS}

    @classmethod
    def from_wire(cls, value: object) -> BundleSchemaCompatibilityV1:
        document = _object(value, cls._WIRE_KEYS, "bundle schema compatibility")
        return cls(**cast(Any, document))


@dataclass(frozen=True, slots=True)
class BundleCompatibilityV1:
    bundle_format_major: int
    query_contract: str
    minimum_explorer_version: str

    _WIRE_KEYS: ClassVar[set[str]] = {
        "bundle_format_major",
        "query_contract",
        "minimum_explorer_version",
    }

    def __post_init__(self) -> None:
        if self.bundle_format_major != BUNDLE_FORMAT_MAJOR:
            raise ValueError("bundle_format_major must be 1")
        if self.query_contract != QUERY_CONTRACT:
            raise ValueError(f"query_contract must be {QUERY_CONTRACT}")
        if self.minimum_explorer_version != MINIMUM_EXPLORER_VERSION:
            raise ValueError(
                f"minimum_explorer_version must be {MINIMUM_EXPLORER_VERSION}"
            )

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "bundle_format_major": self.bundle_format_major,
            "query_contract": self.query_contract,
            "minimum_explorer_version": self.minimum_explorer_version,
        }

    @classmethod
    def from_wire(cls, value: object) -> BundleCompatibilityV1:
        document = _object(value, cls._WIRE_KEYS, "bundle compatibility")
        return cls(**cast(Any, document))


@dataclass(frozen=True, slots=True)
class CensusBundleManifestV1:
    schema: str
    census_release_version: str
    census_release_id: str
    source_lock_digest: str
    authoritative_components: tuple[BundleComponentDescriptorV1, ...]
    population: BundlePopulationV1
    schemas: BundleSchemaCompatibilityV1
    compatibility: BundleCompatibilityV1
    parent_census_release_id: str | None

    _WIRE_KEYS: ClassVar[set[str]] = {
        "schema",
        "census_release_version",
        "census_release_id",
        "source_lock_digest",
        "authoritative_components",
        "population",
        "schemas",
        "compatibility",
        "parent_census_release_id",
    }

    def __post_init__(self) -> None:
        if self.schema != BUNDLE_SCHEMA:
            raise ValueError(f"schema must be {BUNDLE_SCHEMA}")
        if self.census_release_version != BUNDLE_VERSION:
            raise ValueError(f"census_release_version must be {BUNDLE_VERSION}")
        if _RELEASE_ID.fullmatch(self.census_release_id) is None:
            raise ValueError("census_release_id is invalid")
        _digest("source_lock_digest", self.source_lock_digest)
        components = tuple(self.authoritative_components)
        if any(
            not isinstance(item, BundleComponentDescriptorV1) for item in components
        ):
            raise TypeError("authoritative_components contain an invalid value")
        if tuple(item.role for item in components) != AUTHORITATIVE_COMPONENT_ROLES:
            raise ValueError("authoritative_components must use the frozen role order")
        if not isinstance(self.population, BundlePopulationV1):
            raise TypeError("population must be BundlePopulationV1")
        if not isinstance(self.schemas, BundleSchemaCompatibilityV1):
            raise TypeError("schemas must be BundleSchemaCompatibilityV1")
        if not isinstance(self.compatibility, BundleCompatibilityV1):
            raise TypeError("compatibility must be BundleCompatibilityV1")
        parent = self.parent_census_release_id
        if parent is not None and _RELEASE_ID.fullmatch(parent) is None:
            raise ValueError("parent_census_release_id is invalid")

    @classmethod
    def create(
        cls,
        *,
        census_release_version: str,
        source_lock_digest: str,
        authoritative_components: Sequence[BundleComponentDescriptorV1],
        population: BundlePopulationV1,
        schemas: BundleSchemaCompatibilityV1,
        compatibility: BundleCompatibilityV1,
        parent_census_release_id: str | None,
    ) -> CensusBundleManifestV1:
        provisional = cls(
            BUNDLE_SCHEMA,
            census_release_version,
            "censusrel_" + "0" * 64,
            source_lock_digest,
            tuple(authoritative_components),
            population,
            schemas,
            compatibility,
            parent_census_release_id,
        )
        return cls(
            provisional.schema,
            provisional.census_release_version,
            census_release_id_for(provisional),
            provisional.source_lock_digest,
            provisional.authoritative_components,
            provisional.population,
            provisional.schemas,
            provisional.compatibility,
            provisional.parent_census_release_id,
        )

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "schema": self.schema,
            "census_release_version": self.census_release_version,
            "census_release_id": self.census_release_id,
            "source_lock_digest": self.source_lock_digest,
            "authoritative_components": [
                item.to_wire() for item in self.authoritative_components
            ],
            "population": self.population.to_wire(),
            "schemas": self.schemas.to_wire(),
            "compatibility": self.compatibility.to_wire(),
            "parent_census_release_id": self.parent_census_release_id,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_wire())

    def digest(self) -> str:
        return sha256_bytes(self.canonical_bytes())

    @classmethod
    def from_wire(cls, value: object) -> CensusBundleManifestV1:
        document = _object(value, cls._WIRE_KEYS, "Census bundle manifest")
        raw_components = document["authoritative_components"]
        if not isinstance(raw_components, list):
            raise TypeError("authoritative_components must be a JSON array")
        result = cls(
            cast(str, document["schema"]),
            cast(str, document["census_release_version"]),
            cast(str, document["census_release_id"]),
            cast(str, document["source_lock_digest"]),
            tuple(
                BundleComponentDescriptorV1.from_wire(item) for item in raw_components
            ),
            BundlePopulationV1.from_wire(document["population"]),
            BundleSchemaCompatibilityV1.from_wire(document["schemas"]),
            BundleCompatibilityV1.from_wire(document["compatibility"]),
            cast(str | None, document["parent_census_release_id"]),
        )
        if result.to_wire() != document:
            raise ValueError("Census bundle manifest is not canonical")
        if result.census_release_id != census_release_id_for(result):
            raise ValueError("census_release_id is stale")
        return result


def _release_identity_projection(
    manifest: CensusBundleManifestV1,
) -> dict[str, JSONValue]:
    return {
        "schema": manifest.schema,
        "census_release_version": manifest.census_release_version,
        "source_lock_digest": manifest.source_lock_digest,
        "authoritative_components": [
            item.to_wire() for item in manifest.authoritative_components
        ],
        "population": manifest.population.to_wire(),
        "schemas": manifest.schemas.to_wire(),
        "compatibility": manifest.compatibility.to_wire(),
        "parent_census_release_id": manifest.parent_census_release_id,
    }


def census_release_id_for(manifest: CensusBundleManifestV1) -> str:
    if not isinstance(manifest, CensusBundleManifestV1):
        raise TypeError("manifest must be CensusBundleManifestV1")
    return "censusrel_" + domain_digest(
        CENSUS_RELEASE_ID_DOMAIN,
        _release_identity_projection(manifest),
    )


__all__ = [
    "AUTHORITATIVE_COMPONENT_ROLES",
    "BUNDLE_FORMAT_MAJOR",
    "BUNDLE_MANIFEST_FILENAME",
    "BUNDLE_SCHEMA",
    "BUNDLE_VERSION",
    "COMPONENT_MANIFEST_PATHS",
    "COMPONENT_SCHEMAS",
    "BundleCompatibilityV1",
    "BundleComponentDescriptorV1",
    "BundlePopulationV1",
    "BundleSchemaCompatibilityV1",
    "CensusBundleManifestV1",
    "census_release_id_for",
]
