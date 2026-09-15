"""Strict row validation for M5-06 canonical indexes."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import cast

from ..capability.link import RequirementCapabilityLinkV1
from ..capability.mapping import MappingDispositionV1, RequirementMappingDecisionV1
from ..capability.model import CapabilityRefV1
from ..semantic.evidence import SourceRecordRefV1
from ..semantic.primitives import _require_int
from .index_contract import (
    CARD_NAME_INDEX_SCHEMA,
    CARD_ORACLE_INDEX_SCHEMA,
    CARDS_BY_CAPABILITY_SCHEMA,
    LINKS_BY_REQUIREMENT_SCHEMA,
    REQUIREMENTS_BY_CARD_SCHEMA,
)

_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
_REQUIREMENT_ID_PATTERN = re.compile(r"^srq_[0-9a-f]{64}$")
_LINK_ID_PATTERN = re.compile(r"^rcl_[0-9a-f]{64}$")
_ANALYSIS_OUTCOMES = frozenset(
    {"REQUIREMENTS_PRODUCED", "NO_REQUIREMENTS_APPLICABLE", "UNRESOLVED_ANALYSIS"}
)
_MAPPING_DISPOSITIONS = frozenset(item.value for item in MappingDispositionV1)


def _object(value: object, keys: set[str], label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be an object")
    if set(value) != keys:
        raise ValueError(f"{label} has unexpected or missing properties")
    return cast(dict[str, object], value)


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or value == "":
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _card_identity(document: Mapping[str, object]) -> None:
    if not _text(document["name"], "name"):
        raise ValueError("name must be non-empty")
    oracle_id = _text(document["oracle_id"], "oracle_id")
    source_card_id = _text(document["source_card_id"], "source_card_id")
    source_digest = _text(document["source_record_sha256"], "source_record_sha256")
    if _IDENTIFIER_PATTERN.fullmatch(oracle_id) is None:
        raise ValueError("oracle_id is not a lowercase UUID")
    if _IDENTIFIER_PATTERN.fullmatch(source_card_id) is None:
        raise ValueError("source_card_id is not a lowercase UUID")
    if _DIGEST_PATTERN.fullmatch(source_digest) is None:
        raise ValueError("source_record_sha256 is not a lowercase SHA-256 digest")


def _requirement_ids(value: object, field: str) -> list[str]:
    if not isinstance(value, list):
        raise TypeError(f"{field} must be an array")
    values = [_text(item, f"{field}[{index}]") for index, item in enumerate(value)]
    if any(_REQUIREMENT_ID_PATTERN.fullmatch(item) is None for item in values):
        raise ValueError(f"{field} contains an invalid Requirement ID")
    if values != sorted(values) or len(values) != len(set(values)):
        raise ValueError(f"{field} must be unique and sorted")
    return values


def _validate_card_row(
    value: object, schema: str, extra: set[str]
) -> dict[str, object]:
    document = _object(
        value,
        {
            "schema",
            "name",
            "oracle_id",
            "source_card_id",
            "source_record_sha256",
            *extra,
        },
        "card index row",
    )
    if document["schema"] != schema:
        raise ValueError("card index row schema is invalid")
    _card_identity(document)
    return document


def validate_index_row(relative_path: str, value: object) -> None:
    """Validate one row, including all embedded frozen M4 records."""

    if relative_path == "indexes/cards-by-name.jsonl":
        _validate_card_row(value, CARD_NAME_INDEX_SCHEMA, set())
        return
    if relative_path == "indexes/cards-by-oracle-id.jsonl":
        document = _validate_card_row(
            value,
            CARD_ORACLE_INDEX_SCHEMA,
            {
                "analysis_outcome",
                "requirement_ids",
                "mapping_dispositions",
                "active_capability_refs",
            },
        )
        requirement_ids = _requirement_ids(
            document["requirement_ids"], "requirement_ids"
        )
        if document["analysis_outcome"] not in _ANALYSIS_OUTCOMES:
            raise ValueError("card Oracle analysis outcome is invalid")
        dispositions = document["mapping_dispositions"]
        refs = document["active_capability_refs"]
        if not isinstance(dispositions, list) or not isinstance(refs, list):
            raise TypeError("mapping dispositions and capability refs must be arrays")
        if len(dispositions) != len(requirement_ids):
            raise ValueError("card Oracle mapping count does not match Requirements")
        if any(
            _text(item, "mapping disposition") not in _MAPPING_DISPOSITIONS
            for item in dispositions
        ):
            raise ValueError("card Oracle mapping disposition is invalid")
        for ref in refs:
            CapabilityRefV1.from_wire(ref)
        return
    if relative_path == "indexes/requirements-by-card.jsonl":
        document = _validate_card_row(
            value,
            REQUIREMENTS_BY_CARD_SCHEMA,
            {"analysis_outcome", "requirement_ids"},
        )
        if document["analysis_outcome"] not in _ANALYSIS_OUTCOMES:
            raise ValueError("Requirement card analysis outcome is invalid")
        _requirement_ids(document["requirement_ids"], "requirement_ids")
        return
    if relative_path == "indexes/links-by-requirement.jsonl":
        document = _object(
            value,
            {
                "schema",
                "requirement_id",
                "requirement_wire_digest",
                "source",
                "links",
                "mapping_decision",
            },
            "Requirement link index row",
        )
        if document["schema"] != LINKS_BY_REQUIREMENT_SCHEMA:
            raise ValueError("Requirement link row schema is invalid")
        requirement_id = _text(document["requirement_id"], "requirement_id")
        if _REQUIREMENT_ID_PATTERN.fullmatch(requirement_id) is None:
            raise ValueError("Requirement link row ID is invalid")
        digest = _text(document["requirement_wire_digest"], "requirement_wire_digest")
        if _DIGEST_PATTERN.fullmatch(digest) is None:
            raise ValueError("Requirement link row digest is invalid")
        SourceRecordRefV1.from_wire(document["source"])
        links = document["links"]
        if not isinstance(links, list):
            raise TypeError("links must be an array")
        link_ids: list[str] = []
        for value_item in links:
            link = RequirementCapabilityLinkV1.from_wire(value_item)
            if link.requirement_id != requirement_id:
                raise ValueError("Requirement link does not match index row")
            link_ids.append(link.link_id)
        if link_ids != sorted(link_ids) or len(link_ids) != len(set(link_ids)):
            raise ValueError("Requirement link IDs must be unique and sorted")
        decision = RequirementMappingDecisionV1.from_wire(document["mapping_decision"])
        if decision.requirement_id != requirement_id:
            raise ValueError("mapping decision does not match index row")
        if decision.requirement_wire_digest != digest:
            raise ValueError("mapping decision digest does not match index row")
        return
    if relative_path == "indexes/cards-by-capability.jsonl":
        document = _object(
            value,
            {
                "schema",
                "capability",
                "display_name",
                "lifecycle",
                "card_refs",
                "requirement_ids",
                "link_ids",
                "mapped_requirement_count",
                "denominator",
                "denominator_label",
            },
            "Capability card index row",
        )
        if document["schema"] != CARDS_BY_CAPABILITY_SCHEMA:
            raise ValueError("Capability card row schema is invalid")
        CapabilityRefV1.from_wire(document["capability"])
        cards = document["card_refs"]
        if not isinstance(cards, list):
            raise TypeError("card_refs must be an array")
        card_keys: list[str] = []
        for card in cards:
            card_document = _object(
                card,
                {"name", "oracle_id", "source_card_id", "source_record_sha256"},
                "Capability card reference",
            )
            _card_identity(card_document)
            card_keys.append(cast(str, card_document["oracle_id"]))
        if card_keys != sorted(card_keys) or len(card_keys) != len(set(card_keys)):
            raise ValueError("Capability card references must be unique and sorted")
        requirement_ids = _requirement_ids(
            document["requirement_ids"], "requirement_ids"
        )
        raw_link_ids = document["link_ids"]
        if not isinstance(raw_link_ids, list):
            raise TypeError("link_ids must be an array")
        link_ids = [_text(item, "link ID") for item in raw_link_ids]
        if any(_LINK_ID_PATTERN.fullmatch(item) is None for item in link_ids):
            raise ValueError("Capability card link ID is invalid")
        if link_ids != sorted(link_ids) or len(link_ids) != len(set(link_ids)):
            raise ValueError("Capability card link IDs must be unique and sorted")
        mapped_count = _require_int(
            "mapped_requirement_count",
            document["mapped_requirement_count"],
            nonnegative=True,
        )
        denominator = _require_int(
            "denominator", document["denominator"], nonnegative=True
        )
        if mapped_count != len(requirement_ids) or mapped_count > denominator:
            raise ValueError("Capability card mapping counts do not reconcile")
        if document["denominator_label"] != "MAPPED_REQUIREMENTS":
            raise ValueError("Capability card denominator label is invalid")
        _text(document["display_name"], "display_name")
        if document["lifecycle"] not in {"PROPOSED", "ACTIVE", "SUPERSEDED", "RETIRED"}:
            raise ValueError("Capability lifecycle is invalid")
        return
    raise ValueError(f"unknown derived index path: {relative_path}")


__all__ = ["validate_index_row"]
