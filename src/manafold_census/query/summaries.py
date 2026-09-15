"""Immutable M2 and M4 summary values used by CardSemanticViewV1."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import cast

from ..canonical import JSONValue
from ..capability.admissibility import AdmissibilityDecisionV1
from ..capability.mapping import MappingDispositionV1
from ..semantic.model import ResolutionStateV1, ReviewStatusV1
from ..semantic.primitives import _require_int, _require_object


def _count_map(field: str, value: object, keys: tuple[str, ...]) -> Mapping[str, int]:
    document = _require_object(value, set(keys), field)
    return MappingProxyType(
        {
            key: _require_int(f"{field}.{key}", document[key], nonnegative=True)
            for key in keys
        }
    )


@dataclass(frozen=True, slots=True)
class M2ReviewSummaryV1:
    review_status_counts: Mapping[str, int]
    resolution_state_counts: Mapping[str, int]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "review_status_counts",
            _count_map(
                "review_status_counts",
                self.review_status_counts,
                tuple(item.value for item in ReviewStatusV1),
            ),
        )
        object.__setattr__(
            self,
            "resolution_state_counts",
            _count_map(
                "resolution_state_counts",
                self.resolution_state_counts,
                tuple(item.value for item in ResolutionStateV1),
            ),
        )

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "review_status_counts": cast(JSONValue, dict(self.review_status_counts)),
            "resolution_state_counts": cast(
                JSONValue, dict(self.resolution_state_counts)
            ),
        }


@dataclass(frozen=True, slots=True)
class M4MappingSummaryV1:
    admissibility_decision_counts: Mapping[str, int]
    mapping_disposition_counts: Mapping[str, int]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "admissibility_decision_counts",
            _count_map(
                "admissibility_decision_counts",
                self.admissibility_decision_counts,
                tuple(item.value for item in AdmissibilityDecisionV1),
            ),
        )
        object.__setattr__(
            self,
            "mapping_disposition_counts",
            _count_map(
                "mapping_disposition_counts",
                self.mapping_disposition_counts,
                tuple(item.value for item in MappingDispositionV1),
            ),
        )

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "admissibility_decision_counts": cast(
                JSONValue, dict(self.admissibility_decision_counts)
            ),
            "mapping_disposition_counts": cast(
                JSONValue, dict(self.mapping_disposition_counts)
            ),
        }


__all__ = ["M2ReviewSummaryV1", "M4MappingSummaryV1"]
