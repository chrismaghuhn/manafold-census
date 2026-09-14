"""Deterministic, proposal-only grouping of validated M3 Requirements."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import cast

from ..canonical import JSONValue, canonical_json_bytes
from ..digest import domain_digest, sha256_bytes
from ..semantic.kind_payloads import payload_to_wire
from ..semantic.kinds import RequirementFamilyV1, RequirementKindV1
from ..semantic.model import RequirementV1, _semantic_flags
from .candidate_model import (
    CANDIDATE_ID_DOMAIN,
    CANDIDATE_ID_PREFIX,
    CANDIDATE_SCHEMA,
    POLICY_DIGEST_DOMAIN,
    POLICY_SCHEMA,
    CandidateClusterStatusV1,
    CandidateClusterV1,
    CandidateGroupingPolicyV1,
    CandidateGroupingResultV1,
    CandidateGroupingRuleV1,
    candidate_grouping_policy_digest_for,
    candidate_id_for,
    validate_candidate_grouping_policy,
)
from .dimensions import M2DimensionPathV1, dimension_spec_for
from .input import M3RequirementCorpusV1

GROUP_SIGNATURE_DOMAIN = "census.m4-candidate-group-signature.v1"
GENERATOR_ID = "m4.deterministic-shape-grouping"
GENERATOR_VERSION = "1"


def _masked(value: JSONValue) -> JSONValue:
    if isinstance(value, dict):
        return {
            key: item if key in {"mode", "shape", "type", "kind"} else {"masked": True}
            for key, item in value.items()
        }
    if isinstance(value, list):
        return cast(JSONValue, [{"masked": True}])
    return {"masked": True}


def _path_feature(
    requirement: RequirementV1,
    path: M2DimensionPathV1,
    is_dimension: bool,
) -> tuple[dict[str, JSONValue], bool]:
    spec = dimension_spec_for(path)
    payload = payload_to_wire(
        requirement.family, requirement.kind, requirement.parameters
    )
    field = spec.parameter_path.rsplit("/", 1)[-1]
    if field not in payload:
        return (
            {
                "path_key": path.value,
                "mode": "UNKNOWN_PATH",
                "state": "UNKNOWN",
                "value": {"unknown_path": spec.parameter_path},
            },
            True,
        )
    typed, wire = getattr(requirement.parameters, field), payload[field]
    if _semantic_flags(typed)[0]:
        return (
            {
                "path_key": path.value,
                "mode": "DIMENSION" if is_dimension else "PARTITION",
                "state": "UNKNOWN",
                "value": {"unknown_path": spec.parameter_path},
            },
            True,
        )
    return (
        {
            "path_key": path.value,
            "mode": "DIMENSION" if is_dimension else "PARTITION",
            "state": "ABSENT" if wire is None else "KNOWN",
            "value": None if wire is None else _masked(wire) if is_dimension else wire,
        },
        False,
    )


def _signature(
    requirement: RequirementV1,
    rules: Mapping[
        tuple[RequirementFamilyV1, RequirementKindV1], CandidateGroupingRuleV1
    ],
    policy_version: str,
    policy_digest: str,
) -> tuple[dict[str, JSONValue], bool]:
    rule = rules.get((requirement.family, requirement.kind))
    if rule is None:
        return (
            {
                "family": requirement.family.value,
                "kind": requirement.kind.value,
                "resolution_state": requirement.resolution.state.value,
                "policy_version": policy_version,
                "policy_digest": policy_digest,
                "unclassified_paths": [{"unknown_path": "/kind"}],
            },
            True,
        )
    dimensions = set(rule.dimension_paths)
    entries: list[dict[str, JSONValue]] = []
    unknown = False
    for path in sorted(
        rule.dimension_paths + rule.partition_paths, key=lambda item: item.value
    ):
        entry, found = _path_feature(requirement, path, path in dimensions)
        entries.append(entry)
        unknown |= found
    return (
        {
            "family": requirement.family.value,
            "kind": requirement.kind.value,
            "resolution_state": requirement.resolution.state.value,
            "policy_version": policy_version,
            "policy_digest": policy_digest,
            "paths": cast(JSONValue, entries),
        },
        unknown,
    )


def _variation_summary(
    requirements: Sequence[RequirementV1],
    rule: CandidateGroupingRuleV1 | None,
    policy_version: str,
    policy_digest: str,
) -> dict[str, JSONValue]:
    dimensions: dict[str, list[JSONValue]] = (
        {} if rule is None else {path.value: [] for path in rule.dimension_paths}
    )
    unknown = unresolved = 0
    rules = {} if rule is None else {(rule.family, rule.kind): rule}
    for requirement in requirements:
        signature, has_unknown = _signature(
            requirement, rules, policy_version, policy_digest
        )
        unknown += int(has_unknown)
        unresolved += int(requirement.resolution.state.value != "COMPLETE")
        for entry in cast(list[dict[str, JSONValue]], signature.get("paths", [])):
            path = cast(str, entry["path_key"])
            if path in dimensions:
                path_key = M2DimensionPathV1(path)
                spec = dimension_spec_for(path_key)
                payload = payload_to_wire(
                    requirement.family,
                    requirement.kind,
                    requirement.parameters,
                )
                field = spec.parameter_path.rsplit("/", 1)[-1]
                typed = getattr(requirement.parameters, field, None)
                dimensions[path].append(
                    {"unknown_path": spec.parameter_path}
                    if field not in payload or _semantic_flags(typed)[0]
                    else payload[field]
                )
    result: dict[str, JSONValue] = {
        "dimensions": {},
        "unknown_requirement_count": unknown,
        "unresolved_requirement_count": unresolved,
    }
    output = cast(dict[str, JSONValue], result["dimensions"])
    for path, values in dimensions.items():
        unique = {canonical_json_bytes(value).decode(): value for value in values}
        output[path] = {
            "distinct_count": len(unique),
            "values": sorted(unique.values(), key=canonical_json_bytes),
        }
    return result


def _group_validated_requirements(
    corpus: M3RequirementCorpusV1,
    policy: CandidateGroupingPolicyV1,
) -> CandidateGroupingResultV1:
    rules = {(rule.family, rule.kind): rule for rule in policy.rules}
    policy_digest = candidate_grouping_policy_digest_for(policy)
    groups: dict[bytes, list[RequirementV1]] = {}
    signatures: dict[bytes, dict[str, JSONValue]] = {}
    for requirement in sorted(
        corpus.requirements, key=lambda item: item.requirement_id
    ):
        signature, _ = _signature(
            requirement, rules, policy.policy_version, policy_digest
        )
        key = canonical_json_bytes(signature)
        groups.setdefault(key, []).append(requirement)
        signatures[key] = signature
    clusters: list[CandidateClusterV1] = []
    for key, values in groups.items():
        ordered = tuple(sorted(values, key=lambda item: item.requirement_id))
        rule = rules.get((ordered[0].family, ordered[0].kind))
        ids = tuple(item.requirement_id for item in ordered)
        sources = {
            (
                item.source.record_schema,
                item.source.oracle_id,
                item.source.source_card_id,
                item.source.source_record_sha256,
            )
            for item in ordered
        }
        signature_digest = domain_digest(GROUP_SIGNATURE_DOMAIN, signatures[key])
        claim: dict[str, JSONValue] = {
            "family": ordered[0].family.value,
            "kind": ordered[0].kind.value,
            "dimension_paths": (
                [] if rule is None else [path.value for path in rule.dimension_paths]
            ),
            "partition_paths": (
                [] if rule is None else [path.value for path in rule.partition_paths]
            ),
        }
        clusters.append(
            CandidateClusterV1(
                corpus.m3_analysis_manifest_sha256,
                corpus.requirement_set_digest,
                policy.policy_version,
                policy_digest,
                GENERATOR_ID,
                GENERATOR_VERSION,
                candidate_id_for(
                    m3_analysis_manifest_sha256=corpus.m3_analysis_manifest_sha256,
                    requirement_set_digest=corpus.requirement_set_digest,
                    policy_version=policy.policy_version,
                    policy_digest=policy_digest,
                    generator_id=GENERATOR_ID,
                    generator_version=GENERATOR_VERSION,
                    group_signature_digest=signature_digest,
                    requirement_ids=ids,
                ),
                signature_digest,
                ids,
                len(ids),
                len(sources),
                _variation_summary(ordered, rule, policy.policy_version, policy_digest),
                claim,
                CandidateClusterStatusV1.PROPOSED,
            )
        )
    return CandidateGroupingResultV1(tuple(clusters))


def group_requirement_candidates(
    corpus: M3RequirementCorpusV1,
    policy: CandidateGroupingPolicyV1,
) -> CandidateGroupingResultV1:
    if not isinstance(corpus, M3RequirementCorpusV1):
        raise TypeError("grouping requires M3RequirementCorpusV1")
    if not isinstance(policy, CandidateGroupingPolicyV1):
        raise TypeError("grouping requires CandidateGroupingPolicyV1")
    validate_candidate_grouping_policy(policy)
    return _group_validated_requirements(corpus, policy)


def import_pinned_candidate_proposals(
    raw: bytes,
    *,
    expected_sha256: str,
    expected_m3_analysis_manifest_sha256: str,
    expected_requirement_set_digest: str,
    enabled: bool = False,
) -> tuple[CandidateClusterV1, ...]:
    """Validate a pinned proposal artifact; no live model execution exists."""
    if not enabled:
        raise ValueError("pinned candidate proposal importer is disabled")
    if type(raw) is not bytes or sha256_bytes(raw) != expected_sha256:
        raise ValueError("pinned candidate proposal digest does not match")
    try:
        document = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("pinned candidate proposal is not valid JSON") from error
    keys = {
        "schema",
        "generator_id",
        "generator_version",
        "input_m3_analysis_manifest_sha256",
        "input_requirement_set_digest",
        "status",
        "candidates",
    }
    if not isinstance(document, dict) or set(document) != keys:
        raise ValueError("pinned candidate proposal has an invalid wire")
    if (
        document["schema"] != "census.capability-candidate-proposals.v1"
        or document["status"] != "PROPOSED"
        or raw != canonical_json_bytes(document)
    ):
        raise ValueError("pinned candidate proposal has an invalid wire")
    if (
        document["input_m3_analysis_manifest_sha256"]
        != expected_m3_analysis_manifest_sha256
        or document["input_requirement_set_digest"] != expected_requirement_set_digest
    ):
        raise ValueError("pinned candidate proposal input identity is stale")
    raw_candidates = document["candidates"]
    if not isinstance(raw_candidates, list):
        raise TypeError("pinned candidate candidates must be an array")
    result = tuple(CandidateClusterV1.from_wire(item) for item in raw_candidates)
    if any(
        item.m3_analysis_manifest_sha256 != expected_m3_analysis_manifest_sha256
        or item.requirement_set_digest != expected_requirement_set_digest
        for item in result
    ):
        raise ValueError("pinned candidate proposal input identity is stale")
    generator = (
        cast(str, document["generator_id"]),
        cast(str, document["generator_version"]),
    )
    if tuple(item.candidate_id for item in result) != tuple(
        sorted(item.candidate_id for item in result)
    ):
        raise ValueError("pinned candidate proposal candidates are not canonical")
    if len({item.candidate_id for item in result}) != len(result) or any(
        (item.generator_id, item.generator_version) != generator for item in result
    ):
        raise ValueError("pinned candidate proposal contains an invalid candidate")
    return tuple(sorted(result, key=lambda item: item.candidate_id))


__all__ = [
    "CANDIDATE_ID_DOMAIN",
    "CANDIDATE_ID_PREFIX",
    "CANDIDATE_SCHEMA",
    "CandidateClusterStatusV1",
    "CandidateClusterV1",
    "CandidateGroupingPolicyV1",
    "CandidateGroupingResultV1",
    "CandidateGroupingRuleV1",
    "GENERATOR_ID",
    "GENERATOR_VERSION",
    "GROUP_SIGNATURE_DOMAIN",
    "POLICY_DIGEST_DOMAIN",
    "POLICY_SCHEMA",
    "candidate_grouping_policy_digest_for",
    "candidate_id_for",
    "group_requirement_candidates",
    "import_pinned_candidate_proposals",
    "validate_candidate_grouping_policy",
]
