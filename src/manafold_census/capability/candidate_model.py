"""Closed wire values and identities for M4 candidate proposals."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar, cast

from ..canonical import JSONValue, canonical_json_bytes
from ..digest import domain_digest
from ..semantic.kinds import (
    RequirementFamilyV1,
    RequirementKindV1,
    family_for_kind,
    validate_kind_family,
)
from ..semantic.primitives import (
    _require_enum,
    _require_int,
    _require_object,
    _require_text,
)
from .binding import _typed_known_value
from .dimensions import M2DimensionPathV1, dimension_spec_for, registered_paths_for

CANDIDATE_SCHEMA = "census.capability-candidate-cluster.v1"
POLICY_SCHEMA = "census.candidate-grouping-policy.v1"
POLICY_DIGEST_DOMAIN = "census.m4-candidate-grouping-policy.v1"
CANDIDATE_ID_DOMAIN = "census.capability-candidate-cluster.v1"
CANDIDATE_ID_PREFIX = "ccg_"
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_REQ_ID = re.compile(r"^srq_[0-9a-f]{64}$")
_CANDIDATE_ID = re.compile(r"^ccg_[0-9a-f]{64}$")
_SUPPORTED_KINDS = tuple(
    kind for kind in RequirementKindV1 if kind is not RequirementKindV1.UNRESOLVED
)


def _digest(field: str, value: object) -> str:
    text = _require_text(field, value)
    if _DIGEST.fullmatch(text) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")
    return text


def _paths(value: object, field: str) -> tuple[M2DimensionPathV1, ...]:
    if not isinstance(value, tuple | list):
        raise TypeError(f"{field} must be a tuple or list")
    return tuple(
        sorted(
            (M2DimensionPathV1.from_wire(item) for item in value),
            key=lambda item: item.value,
        )
    )


@dataclass(frozen=True, slots=True)
class CandidateGroupingRuleV1:
    family: RequirementFamilyV1
    kind: RequirementKindV1
    dimension_paths: tuple[M2DimensionPathV1, ...]
    partition_paths: tuple[M2DimensionPathV1, ...]

    _WIRE_KEYS: ClassVar[set[str]] = {
        "family",
        "kind",
        "dimension_paths",
        "partition_paths",
    }

    def __post_init__(self) -> None:
        family = _require_enum("family", self.family, RequirementFamilyV1)
        kind = _require_enum("kind", self.kind, RequirementKindV1)
        validate_kind_family(family, kind)
        object.__setattr__(self, "family", family)
        object.__setattr__(self, "kind", kind)
        object.__setattr__(
            self, "dimension_paths", _paths(self.dimension_paths, "dimension_paths")
        )
        object.__setattr__(
            self, "partition_paths", _paths(self.partition_paths, "partition_paths")
        )

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "family": self.family.value,
            "kind": self.kind.value,
            "dimension_paths": [path.value for path in self.dimension_paths],
            "partition_paths": [path.value for path in self.partition_paths],
        }

    @classmethod
    def from_wire(cls, value: object) -> CandidateGroupingRuleV1:
        document = _require_object(value, cls._WIRE_KEYS, "candidate grouping rule")
        result = cls(
            _require_enum("family", document["family"], RequirementFamilyV1),
            _require_enum("kind", document["kind"], RequirementKindV1),
            _paths(document["dimension_paths"], "dimension_paths"),
            _paths(document["partition_paths"], "partition_paths"),
        )
        if result.to_wire() != document:
            raise ValueError("candidate grouping rule is not canonical")
        return result


@dataclass(frozen=True, slots=True)
class CandidateGroupingPolicyV1:
    policy_version: str
    rules: tuple[CandidateGroupingRuleV1, ...]

    SCHEMA: ClassVar[str] = POLICY_SCHEMA
    _WIRE_KEYS: ClassVar[set[str]] = {"schema", "policy_version", "rules"}

    def __post_init__(self) -> None:
        version = _require_text("policy_version", self.policy_version)
        if not isinstance(self.rules, tuple | list):
            raise TypeError("rules must be a tuple or list")
        rules = tuple(self.rules)
        if any(not isinstance(rule, CandidateGroupingRuleV1) for rule in rules):
            raise TypeError("rules must contain CandidateGroupingRuleV1 values")
        object.__setattr__(self, "policy_version", version)
        object.__setattr__(
            self,
            "rules",
            tuple(sorted(rules, key=lambda rule: (rule.family.value, rule.kind.value))),
        )

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "schema": self.SCHEMA,
            "policy_version": self.policy_version,
            "rules": [rule.to_wire() for rule in self.rules],
        }

    @classmethod
    def from_wire(cls, value: object) -> CandidateGroupingPolicyV1:
        document = _require_object(value, cls._WIRE_KEYS, "candidate grouping policy")
        if document["schema"] != cls.SCHEMA:
            raise ValueError(f"schema must be {cls.SCHEMA}")
        raw_rules = document["rules"]
        if not isinstance(raw_rules, list):
            raise TypeError("rules must be a JSON array")
        result = cls(
            cast(str, document["policy_version"]),
            tuple(CandidateGroupingRuleV1.from_wire(item) for item in raw_rules),
        )
        if result.to_wire() != document:
            raise ValueError("candidate grouping policy is not canonical")
        return result


def validate_candidate_grouping_policy(policy: CandidateGroupingPolicyV1) -> None:
    if not isinstance(policy, CandidateGroupingPolicyV1):
        raise TypeError("candidate grouping policy must be CandidateGroupingPolicyV1")
    expected = {(family_for_kind(kind), kind) for kind in _SUPPORTED_KINDS}
    seen: set[tuple[RequirementFamilyV1, RequirementKindV1]] = set()
    for rule in policy.rules:
        pair = rule.family, rule.kind
        if pair in seen or pair not in expected:
            raise ValueError("candidate grouping policy has an invalid rule set")
        seen.add(pair)
        paths = rule.dimension_paths + rule.partition_paths
        if len(paths) != len(set(paths)):
            raise ValueError("candidate grouping policy paths overlap or duplicate")
        if set(paths) != set(registered_paths_for(*pair)):
            raise ValueError("candidate grouping policy paths are incomplete")
        if any(
            (dimension_spec_for(path).family, dimension_spec_for(path).kind) != pair
            for path in paths
        ):
            raise ValueError("candidate grouping policy path has the wrong kind")
    if seen != expected:
        raise ValueError("candidate grouping policy is missing a supported rule")


def candidate_grouping_policy_digest_for(policy: CandidateGroupingPolicyV1) -> str:
    if not isinstance(policy, CandidateGroupingPolicyV1):
        raise TypeError("policy must be CandidateGroupingPolicyV1")
    return domain_digest(POLICY_DIGEST_DOMAIN, policy.to_wire())


def candidate_id_for(
    *,
    m3_analysis_manifest_sha256: str,
    requirement_set_digest: str,
    policy_version: str,
    policy_digest: str,
    generator_id: str,
    generator_version: str,
    group_signature_digest: str,
    requirement_ids: Sequence[str],
) -> str:
    ids = tuple(sorted(requirement_ids))
    if any(
        not isinstance(item, str) or _REQ_ID.fullmatch(item) is None for item in ids
    ):
        raise ValueError("requirement_ids must contain valid Requirement IDs")
    if len(ids) != len(set(ids)):
        raise ValueError("requirement_ids must be unique")
    payload: dict[str, JSONValue] = {
        "m3_analysis_manifest_sha256": _digest(
            "m3_analysis_manifest_sha256", m3_analysis_manifest_sha256
        ),
        "requirement_set_digest": _digest(
            "requirement_set_digest", requirement_set_digest
        ),
        "policy_version": _require_text("policy_version", policy_version),
        "policy_digest": _digest("policy_digest", policy_digest),
        "generator_id": _require_text("generator_id", generator_id),
        "generator_version": _require_text("generator_version", generator_version),
        "group_signature_digest": _digest(
            "group_signature_digest", group_signature_digest
        ),
        "requirement_ids": list(ids),
    }
    return CANDIDATE_ID_PREFIX + domain_digest(CANDIDATE_ID_DOMAIN, payload)


def _validate_proposed_claim(value: dict[str, JSONValue]) -> tuple[str, ...]:
    expected = {"family", "kind", "dimension_paths", "partition_paths"}
    if set(value) != expected:
        raise ValueError("proposed_claim has an invalid closed shape")
    family = _require_enum(
        "proposed_claim.family", value["family"], RequirementFamilyV1
    )
    kind = _require_enum("proposed_claim.kind", value["kind"], RequirementKindV1)
    validate_kind_family(family, kind)
    dimensions = _paths(value["dimension_paths"], "proposed_claim.dimension_paths")
    partitions = _paths(value["partition_paths"], "proposed_claim.partition_paths")
    paths = dimensions + partitions
    if len(paths) != len(set(paths)):
        raise ValueError("proposed_claim paths overlap or duplicate")
    if set(paths) != set(registered_paths_for(family, kind)):
        raise ValueError("proposed_claim paths are incomplete")
    if any(
        (dimension_spec_for(path).family, dimension_spec_for(path).kind)
        != (family, kind)
        for path in paths
    ):
        raise ValueError("proposed_claim path has the wrong kind")
    return tuple(path.value for path in dimensions)


def _validate_variations(
    value: dict[str, JSONValue], dimension_paths: tuple[str, ...]
) -> None:
    expected = {
        "dimensions",
        "unknown_requirement_count",
        "unresolved_requirement_count",
    }
    if set(value) != expected or not isinstance(value["dimensions"], dict):
        raise ValueError("parameter_variations has an invalid closed shape")
    dimensions = cast(dict[str, JSONValue], value["dimensions"])
    if set(dimensions) != set(dimension_paths):
        raise ValueError("parameter_variations dimensions do not match proposed_claim")
    for path, raw in dimensions.items():
        path_key = M2DimensionPathV1.from_wire(path)
        if not isinstance(raw, dict) or set(raw) != {"distinct_count", "values"}:
            raise ValueError(f"parameter variation for {path} is invalid")
        distinct_count = _require_int(
            "distinct_count", raw["distinct_count"], nonnegative=True
        )
        if not isinstance(raw["values"], list):
            raise TypeError(f"parameter variation values for {path} must be an array")
        values = raw["values"]
        encoded_values = [canonical_json_bytes(item) for item in values]
        if distinct_count != len(values) or len(encoded_values) != len(
            set(encoded_values)
        ):
            raise ValueError(f"parameter variation for {path} has a stale count")
        if encoded_values != sorted(encoded_values):
            raise ValueError(f"parameter variation for {path} is not canonical")
        spec = dimension_spec_for(path_key)
        for item in values:
            if item is None:
                if not spec.optional:
                    raise ValueError(f"null variation is not valid for {path}")
            elif isinstance(item, dict) and set(item) == {"unknown_path"}:
                if item["unknown_path"] != spec.parameter_path:
                    raise ValueError(f"unknown variation path is not valid for {path}")
            else:
                _typed_known_value(path_key, item)
    _require_int(
        "unknown_requirement_count",
        value["unknown_requirement_count"],
        nonnegative=True,
    )
    _require_int(
        "unresolved_requirement_count",
        value["unresolved_requirement_count"],
        nonnegative=True,
    )


class CandidateClusterStatusV1(StrEnum):
    PROPOSED = "PROPOSED"


@dataclass(frozen=True, slots=True)
class CandidateClusterV1:
    m3_analysis_manifest_sha256: str
    requirement_set_digest: str
    policy_version: str
    policy_digest: str
    generator_id: str
    generator_version: str
    candidate_id: str
    group_signature_digest: str
    requirement_ids: tuple[str, ...]
    requirement_count: int
    distinct_source_count: int
    parameter_variations: dict[str, JSONValue]
    proposed_claim: dict[str, JSONValue]
    status: CandidateClusterStatusV1

    SCHEMA: ClassVar[str] = CANDIDATE_SCHEMA
    _WIRE_KEYS: ClassVar[set[str]] = {
        "schema",
        "m3_analysis_manifest_sha256",
        "requirement_set_digest",
        "policy_version",
        "policy_digest",
        "generator_id",
        "generator_version",
        "candidate_id",
        "group_signature_digest",
        "requirement_ids",
        "requirement_count",
        "distinct_source_count",
        "parameter_variations",
        "proposed_claim",
        "status",
    }

    def __post_init__(self) -> None:
        for field, value in (
            ("m3_analysis_manifest_sha256", self.m3_analysis_manifest_sha256),
            ("requirement_set_digest", self.requirement_set_digest),
            ("policy_digest", self.policy_digest),
            ("group_signature_digest", self.group_signature_digest),
        ):
            _digest(field, value)
        _require_text("policy_version", self.policy_version)
        _require_text("generator_id", self.generator_id)
        _require_text("generator_version", self.generator_version)
        if _CANDIDATE_ID.fullmatch(self.candidate_id) is None:
            raise ValueError("candidate_id must use the ccg_ digest form")
        ids = tuple(self.requirement_ids)
        if any(_REQ_ID.fullmatch(item) is None for item in ids):
            raise ValueError("requirement_ids must use the srq_ digest form")
        if ids != tuple(sorted(ids)) or len(ids) != len(set(ids)):
            raise ValueError("requirement_ids must be sorted and unique")
        if self.requirement_count != len(ids):
            raise ValueError("requirement_count does not match requirement_ids")
        _require_int("requirement_count", self.requirement_count, nonnegative=True)
        _require_int(
            "distinct_source_count", self.distinct_source_count, nonnegative=True
        )
        if not 0 < self.distinct_source_count <= self.requirement_count:
            raise ValueError("distinct_source_count is outside the cluster cardinality")
        if not isinstance(self.parameter_variations, dict) or not isinstance(
            self.proposed_claim, dict
        ):
            raise TypeError("candidate summaries must be objects")
        dimension_paths = _validate_proposed_claim(self.proposed_claim)
        _validate_variations(self.parameter_variations, dimension_paths)
        status = _require_enum("status", self.status, CandidateClusterStatusV1)
        if status is not CandidateClusterStatusV1.PROPOSED:
            raise ValueError("candidate clusters are proposal-only")
        if self.candidate_id != candidate_id_for(
            m3_analysis_manifest_sha256=self.m3_analysis_manifest_sha256,
            requirement_set_digest=self.requirement_set_digest,
            policy_version=self.policy_version,
            policy_digest=self.policy_digest,
            generator_id=self.generator_id,
            generator_version=self.generator_version,
            group_signature_digest=self.group_signature_digest,
            requirement_ids=ids,
        ):
            raise ValueError("candidate_id does not match the candidate claim")
        object.__setattr__(self, "requirement_ids", ids)
        object.__setattr__(self, "status", status)

    @property
    def capability_definition(self) -> None:
        return None

    @property
    def representative_requirement_ids(self) -> tuple[str, ...]:
        return self.requirement_ids[:3]

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "schema": self.SCHEMA,
            "m3_analysis_manifest_sha256": self.m3_analysis_manifest_sha256,
            "requirement_set_digest": self.requirement_set_digest,
            "policy_version": self.policy_version,
            "policy_digest": self.policy_digest,
            "generator_id": self.generator_id,
            "generator_version": self.generator_version,
            "candidate_id": self.candidate_id,
            "group_signature_digest": self.group_signature_digest,
            "requirement_ids": list(self.requirement_ids),
            "requirement_count": self.requirement_count,
            "distinct_source_count": self.distinct_source_count,
            "parameter_variations": self.parameter_variations,
            "proposed_claim": self.proposed_claim,
            "status": self.status.value,
        }

    @classmethod
    def from_wire(cls, value: object) -> CandidateClusterV1:
        document = _require_object(value, cls._WIRE_KEYS, "candidate cluster")
        raw_ids = document["requirement_ids"]
        if not isinstance(raw_ids, list):
            raise TypeError("requirement_ids must be a JSON array")
        result = cls(
            cast(str, document["m3_analysis_manifest_sha256"]),
            cast(str, document["requirement_set_digest"]),
            cast(str, document["policy_version"]),
            cast(str, document["policy_digest"]),
            cast(str, document["generator_id"]),
            cast(str, document["generator_version"]),
            cast(str, document["candidate_id"]),
            cast(str, document["group_signature_digest"]),
            tuple(cast(str, item) for item in raw_ids),
            cast(int, document["requirement_count"]),
            cast(int, document["distinct_source_count"]),
            cast(dict[str, JSONValue], document["parameter_variations"]),
            cast(dict[str, JSONValue], document["proposed_claim"]),
            _require_enum("status", document["status"], CandidateClusterStatusV1),
        )
        if result.to_wire() != document:
            raise ValueError("candidate cluster wire is not canonical")
        return result


@dataclass(frozen=True, slots=True)
class CandidateGroupingResultV1:
    clusters: tuple[CandidateClusterV1, ...]

    def __post_init__(self) -> None:
        values = tuple(self.clusters)
        if any(not isinstance(item, CandidateClusterV1) for item in values):
            raise TypeError("clusters must contain CandidateClusterV1 values")
        object.__setattr__(
            self, "clusters", tuple(sorted(values, key=lambda item: item.candidate_id))
        )

    @property
    def worklist(self) -> tuple[CandidateClusterV1, ...]:
        return tuple(
            sorted(
                self.clusters,
                key=lambda item: (
                    -item.distinct_source_count,
                    -item.requirement_count,
                    item.group_signature_digest,
                    item.candidate_id,
                ),
            )
        )


__all__ = [
    "CANDIDATE_ID_DOMAIN",
    "CANDIDATE_ID_PREFIX",
    "CANDIDATE_SCHEMA",
    "CandidateClusterStatusV1",
    "CandidateClusterV1",
    "CandidateGroupingPolicyV1",
    "CandidateGroupingResultV1",
    "CandidateGroupingRuleV1",
    "POLICY_DIGEST_DOMAIN",
    "POLICY_SCHEMA",
    "candidate_grouping_policy_digest_for",
    "candidate_id_for",
    "validate_candidate_grouping_policy",
]
