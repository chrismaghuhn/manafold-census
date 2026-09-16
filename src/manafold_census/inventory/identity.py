"""Domain-separated identities for non-authoritative M6-02 artifacts."""

from __future__ import annotations

from collections.abc import Iterable
from typing import cast

from ..canonical import JSONValue
from ..digest import domain_digest


def source_surface_id(
    *,
    oracle_id: str,
    source_card_id: str,
    source_record_sha256: str,
    scope: str,
    face_index: int | None,
    line_index: int | None,
    raw_text: str | None,
) -> str:
    """Return a stable identity for one source-preserving surface occurrence."""

    payload: dict[str, JSONValue] = {
        "oracle_id": oracle_id,
        "source_card_id": source_card_id,
        "source_record_sha256": source_record_sha256,
        "scope": scope,
        "face_index": face_index,
        "line_index": line_index,
        "raw_text": raw_text,
    }
    return "m6surf_" + domain_digest(
        "census.m6-02-source-surface.v1",
        payload,
    )


def group_key_digest(
    *,
    lens: str,
    policy_id: str,
    policy_version: str,
    group_key: str | None,
) -> str:
    """Digest one lens/policy-bound exact or shape grouping key."""

    payload: dict[str, JSONValue] = {
        "grouping_lens": lens,
        "grouping_policy_id": policy_id,
        "grouping_policy_version": policy_version,
        "group_key": group_key,
    }
    return domain_digest("census.m6-02-group-key.v1", payload)


def candidate_group_id(
    *,
    lens: str,
    policy_id: str,
    policy_version: str,
    group_key: str | None,
) -> str:
    """Return a stable identity for one lens/policy/key group."""

    payload: dict[str, JSONValue] = {
        "grouping_lens": lens,
        "grouping_policy_id": policy_id,
        "grouping_policy_version": policy_version,
        "group_key": group_key,
    }
    return "m6grp_" + domain_digest(
        "census.m6-02-candidate-group.v1",
        payload,
    )


def capability_opportunity_id(
    *,
    candidate_group_ids: Iterable[str],
    policy_id: str,
    policy_version: str,
) -> str:
    """Return a stable non-authoritative Opportunity identity."""

    group_ids = sorted(set(candidate_group_ids))
    payload: dict[str, JSONValue] = {
        "candidate_group_ids": cast(JSONValue, group_ids),
        "grouping_policy_id": policy_id,
        "grouping_policy_version": policy_version,
    }
    return "m6opp_" + domain_digest(
        "census.m6-02-capability-opportunity.v1",
        payload,
    )


def selected_identity_set_digest(oracle_ids: Iterable[str]) -> str:
    """Digest the sorted distinct Oracle IDs selected for this inventory."""

    payload: dict[str, JSONValue] = {
        "oracle_ids": cast(JSONValue, sorted(set(oracle_ids)))
    }
    return domain_digest(
        "census.m6-02-selected-identity-set.v1",
        payload,
    )
