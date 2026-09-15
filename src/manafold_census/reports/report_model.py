"""Closed Census report wire model and derived build result."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, cast

from ..canonical import JSONValue
from ..semantic.primitives import _require_int
from .model import CENSUS_REPORT_SCHEMA, IndexManifestV1, ReportIndexV1
from .report_contract import (
    _ADMISSIBILITY_KEYS,
    _ANALYSIS_OUTCOME_KEYS,
    _LIFECYCLE_KEYS,
    _MAPPING_KEYS,
    _POPULATION_KEYS,
    _RESOLUTION_STATE_KEYS,
    _REVIEW_STATUS_KEYS,
    _active_mapping_presence,
    _capability_frequency,
    _counts,
    _digest,
    _metric,
    _object,
    _release_id,
    _requirement_presence,
    _unresolved_summary,
)


@dataclass(frozen=True, slots=True)
class CensusReportV1:
    """Global derived statistics bound to one immutable Census manifest."""

    wire: dict[str, JSONValue]

    SCHEMA: ClassVar[str] = CENSUS_REPORT_SCHEMA
    _WIRE_KEYS: ClassVar[set[str]] = {
        "schema",
        "census_release_id",
        "census_manifest_sha256",
        "source_lock_digest",
        "m3_analysis_manifest_sha256",
        "m4_manifest_sha256",
        "requirement_set_digest",
        "population",
        "source_coverage",
        "structural_coverage",
        "analysis_record_coverage",
        "analysis_outcome_counts",
        "requirement_presence",
        "m2_review_status_counts",
        "m2_resolution_state_counts",
        "m4_admissibility_status_counts",
        "m4_mapping_disposition_counts",
        "active_capability_mapping_presence",
        "capability_lifecycle_counts",
        "unresolved_analysis",
        "explicit_negative_analysis",
        "m4_outliers",
        "ambiguities",
        "review_queues",
        "mapped_subset_capability_frequency",
    }

    def __post_init__(self) -> None:
        if not isinstance(self.wire, dict):
            raise TypeError("report wire must be an object")
        document = _object(self.wire, self._WIRE_KEYS, "Census report")
        if document["schema"] != self.SCHEMA:
            raise ValueError(f"schema must be {self.SCHEMA}")
        _release_id("census_release_id", document["census_release_id"])
        for field in (
            "census_manifest_sha256",
            "source_lock_digest",
            "m3_analysis_manifest_sha256",
            "m4_manifest_sha256",
            "requirement_set_digest",
        ):
            _digest(field, document[field])

        population = _counts("population", document["population"], _POPULATION_KEYS)
        source_numerator, source_denominator = _metric(
            "source_coverage", document["source_coverage"], "TOTAL_ORACLE_IDENTITIES"
        )
        structural_numerator, structural_denominator = _metric(
            "structural_coverage",
            document["structural_coverage"],
            "TOTAL_ORACLE_IDENTITIES",
        )
        analysis_numerator, analysis_denominator = _metric(
            "analysis_record_coverage",
            document["analysis_record_coverage"],
            "TOTAL_ORACLE_IDENTITIES",
        )
        analysis_counts = _counts(
            "analysis_outcome_counts",
            document["analysis_outcome_counts"],
            _ANALYSIS_OUTCOME_KEYS,
        )
        if (
            source_numerator != population["oracle_identity_count"]
            or source_denominator != population["oracle_identity_count"]
        ):
            raise ValueError("source coverage does not match population")
        if (
            structural_numerator != population["structural_record_count"]
            or structural_denominator != population["oracle_identity_count"]
        ):
            raise ValueError("structural coverage does not match population")
        if (
            analysis_numerator != population["analysis_record_count"]
            or analysis_denominator != population["oracle_identity_count"]
        ):
            raise ValueError("analysis coverage does not match population")
        if sum(analysis_counts.values()) != population["analysis_record_count"]:
            raise ValueError("analysis outcome counts do not match population")
        if (
            analysis_counts["REQUIREMENTS_PRODUCED"]
            != population["requirements_produced_card_count"]
            or analysis_counts["NO_REQUIREMENTS_APPLICABLE"]
            != population["no_requirements_applicable_count"]
            or analysis_counts["UNRESOLVED_ANALYSIS"]
            != population["unresolved_analysis_count"]
        ):
            raise ValueError("analysis outcome population assertions are stale")

        _requirement_presence(document["requirement_presence"])
        presence = _object(
            document["requirement_presence"],
            {
                "cards_with_persisted_requirements",
                "cards_without_persisted_requirements",
                "persisted_requirement_count",
                "denominator",
                "denominator_label",
            },
            "requirement_presence",
        )
        if (
            _require_int(
                "requirement_presence.persisted_requirement_count",
                presence["persisted_requirement_count"],
                nonnegative=True,
            )
            != population["requirement_count"]
        ):
            raise ValueError("Requirement presence count does not match population")
        if (
            _require_int(
                "requirement_presence.denominator",
                presence["denominator"],
                nonnegative=True,
            )
            != population["oracle_identity_count"]
        ):
            raise ValueError("Requirement presence denominator is stale")

        review_counts = _counts(
            "m2_review_status_counts",
            document["m2_review_status_counts"],
            _REVIEW_STATUS_KEYS,
        )
        resolution_counts = _counts(
            "m2_resolution_state_counts",
            document["m2_resolution_state_counts"],
            _RESOLUTION_STATE_KEYS,
        )
        admissibility_counts = _counts(
            "m4_admissibility_status_counts",
            document["m4_admissibility_status_counts"],
            _ADMISSIBILITY_KEYS,
        )
        mapping_counts = _counts(
            "m4_mapping_disposition_counts",
            document["m4_mapping_disposition_counts"],
            _MAPPING_KEYS,
        )
        for label, counts in (
            ("M2 review", review_counts),
            ("M2 resolution", resolution_counts),
            ("M4 admissibility", admissibility_counts),
            ("M4 mapping", mapping_counts),
        ):
            if sum(counts.values()) != population["requirement_count"]:
                raise ValueError(f"{label} counts do not match Requirements")

        _active_mapping_presence(document["active_capability_mapping_presence"])
        active_mapping = _object(
            document["active_capability_mapping_presence"],
            {
                "cards_with_active_capability_mappings",
                "cards_without_active_capability_mappings",
                "mapped_requirement_count",
                "denominator",
                "denominator_label",
            },
            "active_capability_mapping_presence",
        )
        if (
            _require_int(
                "active_capability_mapping_presence.denominator",
                active_mapping["denominator"],
                nonnegative=True,
            )
            != population["oracle_identity_count"]
        ):
            raise ValueError("active mapping denominator is stale")
        if (
            _require_int(
                "active_capability_mapping_presence.mapped_requirement_count",
                active_mapping["mapped_requirement_count"],
                nonnegative=True,
            )
            != mapping_counts["MAPPED"]
        ):
            raise ValueError("active mapping count is stale")

        _counts(
            "capability_lifecycle_counts",
            document["capability_lifecycle_counts"],
            _LIFECYCLE_KEYS,
        )
        _unresolved_summary(document["unresolved_analysis"])
        unresolved = _object(
            document["unresolved_analysis"],
            {
                "cards_with_persisted_requirements",
                "cards_without_persisted_requirements",
                "denominator",
                "denominator_label",
            },
            "unresolved_analysis",
        )
        if (
            _require_int(
                "unresolved_analysis.denominator",
                unresolved["denominator"],
                nonnegative=True,
            )
            != analysis_counts["UNRESOLVED_ANALYSIS"]
        ):
            raise ValueError("unresolved analysis denominator is stale")

        negative_numerator, negative_denominator = _metric(
            "explicit_negative_analysis",
            document["explicit_negative_analysis"],
            "TOTAL_ANALYSIS_RECORDS",
        )
        if negative_numerator != analysis_counts["NO_REQUIREMENTS_APPLICABLE"]:
            raise ValueError("explicit negative analysis count is stale")
        if negative_denominator != population["analysis_record_count"]:
            raise ValueError("explicit negative analysis denominator is stale")
        outlier_numerator, outlier_denominator = _metric(
            "m4_outliers", document["m4_outliers"], "PERSISTED_REQUIREMENTS"
        )
        ambiguity_numerator, ambiguity_denominator = _metric(
            "ambiguities", document["ambiguities"], "PERSISTED_REQUIREMENTS"
        )
        if (
            outlier_numerator != mapping_counts["OUTLIER"]
            or outlier_denominator != population["requirement_count"]
        ):
            raise ValueError("M4 outlier metric is stale")
        if (
            ambiguity_numerator != mapping_counts["AMBIGUOUS"]
            or ambiguity_denominator != population["requirement_count"]
        ):
            raise ValueError("M4 ambiguity metric is stale")

        queue = _object(
            document["review_queues"],
            {
                "mapping_review_queue_count",
                "unreviewed_capability_definition_count",
                "unreviewed_link_count",
                "unreviewed_evolution_count",
                "total_queue_count",
            },
            "review_queues",
        )
        queue_values = {
            field: _require_int(
                f"review_queues.{field}", queue[field], nonnegative=True
            )
            for field in queue
        }
        if queue_values["total_queue_count"] != sum(
            queue_values[field]
            for field in (
                "mapping_review_queue_count",
                "unreviewed_capability_definition_count",
                "unreviewed_link_count",
                "unreviewed_evolution_count",
            )
        ):
            raise ValueError("review queue counts do not reconcile")
        frequency = document["mapped_subset_capability_frequency"]
        _capability_frequency(frequency)
        if not isinstance(frequency, list):
            raise TypeError("mapped_subset_capability_frequency must be an array")
        for item in frequency:
            row = _object(
                item,
                {
                    "capability",
                    "mapped_requirement_count",
                    "distinct_source_count",
                    "denominator",
                    "denominator_label",
                },
                "mapped_subset_capability_frequency row",
            )
            if (
                _require_int(
                    "mapped_subset_capability_frequency.denominator",
                    row["denominator"],
                    nonnegative=True,
                )
                != mapping_counts["MAPPED"]
            ):
                raise ValueError("mapped capability denominator is stale")

    @property
    def census_manifest_sha256(self) -> str:
        return cast(str, self.wire["census_manifest_sha256"])

    @property
    def census_release_id(self) -> str:
        return cast(str, self.wire["census_release_id"])

    @property
    def source_lock_digest(self) -> str:
        return cast(str, self.wire["source_lock_digest"])

    @property
    def m3_analysis_manifest_sha256(self) -> str:
        return cast(str, self.wire["m3_analysis_manifest_sha256"])

    @property
    def m4_manifest_sha256(self) -> str:
        return cast(str, self.wire["m4_manifest_sha256"])

    @property
    def requirement_set_digest(self) -> str:
        return cast(str, self.wire["requirement_set_digest"])

    def to_wire(self) -> dict[str, JSONValue]:
        return self.wire

    @classmethod
    def from_wire(cls, value: object) -> CensusReportV1:
        document = _object(value, cls._WIRE_KEYS, "Census report")
        result = cls(cast(dict[str, JSONValue], document))
        if result.to_wire() != document:
            raise ValueError("Census report is not canonical")
        return result


@dataclass(frozen=True, slots=True)
class DerivedCensusBuildResultV1:
    output_dir: Path
    report: CensusReportV1
    report_index: ReportIndexV1
    index_manifest: IndexManifestV1

    @property
    def census_manifest_sha256(self) -> str:
        return self.report.census_manifest_sha256

    @property
    def census_release_id(self) -> str:
        return self.report.census_release_id


__all__ = ["CensusReportV1", "DerivedCensusBuildResultV1"]
