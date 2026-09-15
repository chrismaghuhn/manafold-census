"""Shared validation helpers for the closed Census report model."""

from __future__ import annotations

import re
from typing import cast

from ..capability.admissibility import AdmissibilityDecisionV1
from ..capability.definition import CapabilityLifecycleStateV1
from ..capability.mapping import MappingDispositionV1
from ..capability.model import CapabilityRefV1
from ..semantic.model import ResolutionStateV1, ReviewStatusV1
from ..semantic.primitives import _require_int

_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_RELEASE_ID = re.compile(r"^censusrel_[0-9a-f]{64}$")

_POPULATION_KEYS = (
    "oracle_identity_count",
    "structural_record_count",
    "analysis_record_count",
    "requirement_count",
    "requirements_produced_card_count",
    "no_requirements_applicable_count",
    "unresolved_analysis_count",
)
_ANALYSIS_OUTCOME_KEYS = (
    "REQUIREMENTS_PRODUCED",
    "NO_REQUIREMENTS_APPLICABLE",
    "UNRESOLVED_ANALYSIS",
)
_REVIEW_STATUS_KEYS = tuple(item.value for item in ReviewStatusV1)
_RESOLUTION_STATE_KEYS = tuple(item.value for item in ResolutionStateV1)
_ADMISSIBILITY_KEYS = tuple(item.value for item in AdmissibilityDecisionV1)
_MAPPING_KEYS = tuple(item.value for item in MappingDispositionV1)
_LIFECYCLE_KEYS = tuple(item.value for item in CapabilityLifecycleStateV1)


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


def _text(field: str, value: object) -> str:
    if not isinstance(value, str) or value == "":
        raise ValueError(f"{field} must be a non-empty string")
    value.encode("utf-8")
    return value


def _digest(field: str, value: object) -> str:
    value = _text(field, value)
    if _DIGEST.fullmatch(value) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _release_id(field: str, value: object) -> str:
    value = _text(field, value)
    if _RELEASE_ID.fullmatch(value) is None:
        raise ValueError(f"{field} must be a Census release identity")
    return value


def _counts(field: str, value: object, keys: tuple[str, ...]) -> dict[str, int]:
    document = _object(value, set(keys), field)
    return {
        key: _require_int(f"{field}.{key}", document[key], nonnegative=True)
        for key in keys
    }


def _metric(
    field: str, value: object, denominator_label: str | None = None
) -> tuple[int, int]:
    document = _object(value, {"numerator", "denominator", "denominator_label"}, field)
    numerator = _require_int(
        f"{field}.numerator", document["numerator"], nonnegative=True
    )
    denominator = _require_int(
        f"{field}.denominator", document["denominator"], nonnegative=True
    )
    if numerator > denominator:
        raise ValueError(f"{field}.numerator cannot exceed denominator")
    label = _text(f"{field}.denominator_label", document["denominator_label"])
    if denominator_label is not None and label != denominator_label:
        raise ValueError(f"{field}.denominator_label must be {denominator_label}")
    return numerator, denominator


def _requirement_presence(value: object) -> None:
    document = _object(
        value,
        {
            "cards_with_persisted_requirements",
            "cards_without_persisted_requirements",
            "persisted_requirement_count",
            "denominator",
            "denominator_label",
        },
        "requirement_presence",
    )
    with_requirements = _require_int(
        "requirement_presence.cards_with_persisted_requirements",
        document["cards_with_persisted_requirements"],
        nonnegative=True,
    )
    without_requirements = _require_int(
        "requirement_presence.cards_without_persisted_requirements",
        document["cards_without_persisted_requirements"],
        nonnegative=True,
    )
    denominator = _require_int(
        "requirement_presence.denominator", document["denominator"], nonnegative=True
    )
    _require_int(
        "requirement_presence.persisted_requirement_count",
        document["persisted_requirement_count"],
        nonnegative=True,
    )
    if with_requirements + without_requirements != denominator:
        raise ValueError("requirement_presence card counts do not reconcile")
    if document["denominator_label"] != "TOTAL_ORACLE_IDENTITIES":
        raise ValueError("requirement_presence denominator label is invalid")


def _active_mapping_presence(value: object) -> None:
    document = _object(
        value,
        {
            "cards_with_active_capability_mappings",
            "cards_without_active_capability_mappings",
            "mapped_requirement_count",
            "denominator",
            "denominator_label",
        },
        "active_capability_mapping_presence",
    )
    with_mappings = _require_int(
        "active_capability_mapping_presence.cards_with_active_capability_mappings",
        document["cards_with_active_capability_mappings"],
        nonnegative=True,
    )
    without_mappings = _require_int(
        "active_capability_mapping_presence.cards_without_active_capability_mappings",
        document["cards_without_active_capability_mappings"],
        nonnegative=True,
    )
    denominator = _require_int(
        "active_capability_mapping_presence.denominator",
        document["denominator"],
        nonnegative=True,
    )
    _require_int(
        "active_capability_mapping_presence.mapped_requirement_count",
        document["mapped_requirement_count"],
        nonnegative=True,
    )
    if with_mappings + without_mappings != denominator:
        raise ValueError("active mapping card counts do not reconcile")
    if document["denominator_label"] != "TOTAL_ORACLE_IDENTITIES":
        raise ValueError("active mapping denominator label is invalid")


def _unresolved_summary(value: object) -> None:
    document = _object(
        value,
        {
            "cards_with_persisted_requirements",
            "cards_without_persisted_requirements",
            "denominator",
            "denominator_label",
        },
        "unresolved_analysis",
    )
    with_requirements = _require_int(
        "unresolved_analysis.cards_with_persisted_requirements",
        document["cards_with_persisted_requirements"],
        nonnegative=True,
    )
    without_requirements = _require_int(
        "unresolved_analysis.cards_without_persisted_requirements",
        document["cards_without_persisted_requirements"],
        nonnegative=True,
    )
    denominator = _require_int(
        "unresolved_analysis.denominator", document["denominator"], nonnegative=True
    )
    if with_requirements + without_requirements != denominator:
        raise ValueError("unresolved analysis counts do not reconcile")
    if document["denominator_label"] != "UNRESOLVED_ANALYSIS_CARDS":
        raise ValueError("unresolved analysis denominator label is invalid")


def _capability_frequency(value: object) -> None:
    if not isinstance(value, list):
        raise TypeError("mapped_subset_capability_frequency must be an array")
    for index, raw in enumerate(value):
        document = _object(
            raw,
            {
                "capability",
                "mapped_requirement_count",
                "distinct_source_count",
                "denominator",
                "denominator_label",
            },
            f"mapped_subset_capability_frequency[{index}]",
        )
        CapabilityRefV1.from_wire(document["capability"])
        mapped_count = _require_int(
            f"mapped_subset_capability_frequency[{index}].mapped_requirement_count",
            document["mapped_requirement_count"],
            nonnegative=True,
        )
        _require_int(
            f"mapped_subset_capability_frequency[{index}].distinct_source_count",
            document["distinct_source_count"],
            nonnegative=True,
        )
        denominator = _require_int(
            f"mapped_subset_capability_frequency[{index}].denominator",
            document["denominator"],
            nonnegative=True,
        )
        if mapped_count > denominator:
            raise ValueError("mapped capability count exceeds its denominator")
        if document["denominator_label"] != "MAPPED_REQUIREMENTS":
            raise ValueError("mapped capability denominator label is invalid")


__all__ = [
    "_ADMISSIBILITY_KEYS",
    "_ANALYSIS_OUTCOME_KEYS",
    "_LIFECYCLE_KEYS",
    "_MAPPING_KEYS",
    "_POPULATION_KEYS",
    "_RESOLUTION_STATE_KEYS",
    "_REVIEW_STATUS_KEYS",
    "_active_mapping_presence",
    "_capability_frequency",
    "_counts",
    "_digest",
    "_metric",
    "_object",
    "_release_id",
    "_requirement_presence",
    "_text",
    "_unresolved_summary",
]
