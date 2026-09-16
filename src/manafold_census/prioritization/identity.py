"""Domain-separated identities for non-authoritative M6-03 planning."""

from __future__ import annotations

from collections.abc import Iterable
from typing import cast

from ..canonical import JSONValue
from ..digest import domain_digest


def surface_set_digest(surface_ids: Iterable[str]) -> str:
    """Digest the exact sorted set of underlying source surface IDs."""

    payload: dict[str, JSONValue] = {
        "surface_ids": cast(JSONValue, sorted(set(surface_ids))),
    }
    return domain_digest("census.m6-03-surface-set.v1", payload)


def overlap_cluster_id(surface_ids: Iterable[str]) -> str:
    """Return a stable identity for one exact surface-ID set."""

    payload: dict[str, JSONValue] = {
        "surface_ids": cast(JSONValue, sorted(set(surface_ids))),
    }
    return "m6ovl_" + domain_digest(
        "census.m6-03-mechanical-overlap-cluster.v1",
        payload,
    )


def opportunity_assessment_id(
    *,
    opportunity_id: str,
    assessment_policy_id: str,
    assessment_policy_version: str,
    grouping_lens: str,
    member_surface_set_digest: str,
    distinct_oracle_count: int,
    distinct_raw_text_count: int,
    occurrence_count: int,
    planning_noise: str,
) -> str:
    """Return a stable identity for one planning assessment."""

    payload: dict[str, JSONValue] = {
        "opportunity_id": opportunity_id,
        "assessment_policy_id": assessment_policy_id,
        "assessment_policy_version": assessment_policy_version,
        "grouping_lens": grouping_lens,
        "member_surface_set_digest": member_surface_set_digest,
        "distinct_oracle_count": distinct_oracle_count,
        "distinct_raw_text_count": distinct_raw_text_count,
        "occurrence_count": occurrence_count,
        "planning_noise": planning_noise,
    }
    return "m6ass_" + domain_digest(
        "census.m6-03-opportunity-assessment.v1",
        payload,
    )


__all__ = [
    "opportunity_assessment_id",
    "overlap_cluster_id",
    "surface_set_digest",
]
