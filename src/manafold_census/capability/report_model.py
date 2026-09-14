"""Closed wire models for downstream M4 reports."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import ClassVar, cast

from ..canonical import JSONValue
from ..semantic.primitives import (
    _require_bool,
    _require_int,
    _require_object,
    _require_text,
)
from .input import M3RequirementCorpusV1

REPORT_SCHEMA = "census.capability-report.v1"
REPORT_INDEX_SCHEMA = "census.capability-report-index.v1"
REPORT_FILENAME = "capability-report.json"
REPORT_INDEX_FILENAME = "report-index.json"
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_REPORT_PATH = re.compile(r"^reports/[^/]+\.json$")


def _digest(field: str, value: object) -> str:
    text = _require_text(field, value)
    if _DIGEST.fullmatch(text) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")
    return text


def _count(field: str, value: object) -> int:
    return _require_int(field, value, nonnegative=True)


@dataclass(frozen=True, slots=True)
class CapabilityReportDescriptorV1:
    relative_path: str
    sha256: str
    byte_length: int

    _WIRE_KEYS: ClassVar[set[str]] = {"relative_path", "sha256", "byte_length"}

    def __post_init__(self) -> None:
        path = _require_text("relative_path", self.relative_path)
        if _REPORT_PATH.fullmatch(path) is None:
            raise ValueError("relative_path must identify a report JSON file")
        _digest("sha256", self.sha256)
        _count("byte_length", self.byte_length)
        object.__setattr__(self, "relative_path", path)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "relative_path": self.relative_path,
            "sha256": self.sha256,
            "byte_length": self.byte_length,
        }

    @classmethod
    def from_wire(cls, value: object) -> CapabilityReportDescriptorV1:
        document = _require_object(
            value, cls._WIRE_KEYS, "Capability report descriptor"
        )
        result = cls(
            cast(str, document["relative_path"]),
            cast(str, document["sha256"]),
            cast(int, document["byte_length"]),
        )
        if result.to_wire() != document:
            raise ValueError("Capability report descriptor is not canonical")
        return result


@dataclass(frozen=True, slots=True)
class CapabilityReportIndexV1:
    m4_manifest_sha256: str
    report_descriptors: tuple[CapabilityReportDescriptorV1, ...]

    SCHEMA: ClassVar[str] = REPORT_INDEX_SCHEMA
    _WIRE_KEYS: ClassVar[set[str]] = {
        "report_index_schema",
        "m4_manifest_sha256",
        "report_descriptors",
    }

    def __post_init__(self) -> None:
        _digest("m4_manifest_sha256", self.m4_manifest_sha256)
        descriptors = tuple(self.report_descriptors)
        if not descriptors or any(
            not isinstance(item, CapabilityReportDescriptorV1) for item in descriptors
        ):
            raise ValueError("report_descriptors must be non-empty typed values")
        paths = tuple(item.relative_path for item in descriptors)
        if paths != tuple(sorted(paths)) or len(paths) != len(set(paths)):
            raise ValueError("report_descriptors must be unique and sorted")
        object.__setattr__(self, "report_descriptors", descriptors)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "report_index_schema": self.SCHEMA,
            "m4_manifest_sha256": self.m4_manifest_sha256,
            "report_descriptors": [item.to_wire() for item in self.report_descriptors],
        }

    @classmethod
    def from_wire(cls, value: object) -> CapabilityReportIndexV1:
        document = _require_object(value, cls._WIRE_KEYS, "Capability report index")
        if document["report_index_schema"] != cls.SCHEMA:
            raise ValueError(f"report_index_schema must be {cls.SCHEMA}")
        raw = document["report_descriptors"]
        if not isinstance(raw, list):
            raise TypeError("report_descriptors must be an array")
        result = cls(
            cast(str, document["m4_manifest_sha256"]),
            tuple(CapabilityReportDescriptorV1.from_wire(item) for item in raw),
        )
        if result.to_wire() != document:
            raise ValueError("Capability report index is not canonical")
        return result


@dataclass(frozen=True, slots=True)
class M3ReportContextV1:
    m3_analysis_manifest_sha256: str
    requirement_set_digest: str
    m3_record_count: int | None
    requirements_produced_card_count: int | None
    no_requirements_applicable_count: int | None
    unresolved_analysis_count: int | None
    persisted_requirement_count: int
    complete: bool

    _WIRE_KEYS: ClassVar[set[str]] = {
        "m3_analysis_manifest_sha256",
        "requirement_set_digest",
        "m3_record_count",
        "requirements_produced_card_count",
        "no_requirements_applicable_count",
        "unresolved_analysis_count",
        "persisted_requirement_count",
        "complete",
    }

    def __post_init__(self) -> None:
        _digest("m3_analysis_manifest_sha256", self.m3_analysis_manifest_sha256)
        _digest("requirement_set_digest", self.requirement_set_digest)
        _count("persisted_requirement_count", self.persisted_requirement_count)
        _require_bool("complete", self.complete)
        values = (
            self.m3_record_count,
            self.requirements_produced_card_count,
            self.no_requirements_applicable_count,
            self.unresolved_analysis_count,
        )
        if self.complete and any(value is None for value in values):
            raise ValueError("complete M3 context requires all outcome counts")
        if not self.complete and any(value is not None for value in values):
            raise ValueError("incomplete M3 context cannot claim outcome counts")
        if all(value is not None for value in values):
            counts = tuple(_count("M3 outcome count", value) for value in values)
            if sum(counts[1:]) != counts[0]:
                raise ValueError("M3 outcome counts do not sum to m3_record_count")

    @classmethod
    def from_corpus(cls, corpus: M3RequirementCorpusV1) -> M3ReportContextV1:
        if not isinstance(corpus, M3RequirementCorpusV1):
            raise TypeError("corpus must be M3RequirementCorpusV1")
        return cls(
            corpus.m3_analysis_manifest_sha256,
            corpus.requirement_set_digest,
            corpus.m3_record_count,
            corpus.requirements_produced_card_count,
            corpus.no_requirements_applicable_count,
            corpus.unresolved_analysis_count,
            len(corpus.requirements),
            True,
        )

    @classmethod
    def incomplete(
        cls, manifest_sha256: str, requirement_set_digest: str, requirement_count: int
    ) -> M3ReportContextV1:
        return cls(
            manifest_sha256,
            requirement_set_digest,
            None,
            None,
            None,
            None,
            requirement_count,
            False,
        )

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "m3_analysis_manifest_sha256": self.m3_analysis_manifest_sha256,
            "requirement_set_digest": self.requirement_set_digest,
            "m3_record_count": self.m3_record_count,
            "requirements_produced_card_count": self.requirements_produced_card_count,
            "no_requirements_applicable_count": self.no_requirements_applicable_count,
            "unresolved_analysis_count": self.unresolved_analysis_count,
            "persisted_requirement_count": self.persisted_requirement_count,
            "complete": self.complete,
        }

    @classmethod
    def from_wire(cls, value: object) -> M3ReportContextV1:
        document = _require_object(value, cls._WIRE_KEYS, "M3 report context")
        result = cls(
            cast(str, document["m3_analysis_manifest_sha256"]),
            cast(str, document["requirement_set_digest"]),
            cast(int | None, document["m3_record_count"]),
            cast(int | None, document["requirements_produced_card_count"]),
            cast(int | None, document["no_requirements_applicable_count"]),
            cast(int | None, document["unresolved_analysis_count"]),
            cast(int, document["persisted_requirement_count"]),
            cast(bool, document["complete"]),
        )
        if result.to_wire() != document:
            raise ValueError("M3 report context is not canonical")
        return result


@dataclass(frozen=True, slots=True)
class CapabilityReportV1:
    wire: dict[str, JSONValue]
    m3_context: M3ReportContextV1

    _WIRE_KEYS: ClassVar[set[str]] = {
        "schema",
        "m4_manifest_sha256",
        "m3_context",
        "capability_counts",
        "mapping_counts",
        "requirements_per_capability",
        "capabilities_by_requirement_kind",
        "parameter_dimension_distributions",
        "evolution_counts",
        "review_queue_sizes",
        "candidate_worklist",
    }

    def __post_init__(self) -> None:
        if not isinstance(self.wire, dict):
            raise TypeError("report wire must be an object")
        if not isinstance(self.m3_context, M3ReportContextV1):
            raise TypeError("m3_context must be M3ReportContextV1")

    @property
    def m4_manifest_sha256(self) -> str:
        return cast(str, self.wire["m4_manifest_sha256"])

    @property
    def capability_counts(self) -> dict[str, JSONValue]:
        return cast(dict[str, JSONValue], self.wire["capability_counts"])

    @property
    def mapping_counts(self) -> dict[str, JSONValue]:
        return cast(dict[str, JSONValue], self.wire["mapping_counts"])

    @classmethod
    def from_wire(cls, value: object) -> CapabilityReportV1:
        document = _require_object(value, cls._WIRE_KEYS, "Capability report")
        if document["schema"] != REPORT_SCHEMA:
            raise ValueError(f"schema must be {REPORT_SCHEMA}")
        context = M3ReportContextV1.from_wire(document["m3_context"])
        result = cls(cast(dict[str, JSONValue], document), context)
        if result.to_wire() != document:
            raise ValueError("Capability report is not canonical")
        return result

    def to_wire(self) -> dict[str, JSONValue]:
        return self.wire


@dataclass(frozen=True, slots=True)
class CapabilityReportBuildResultV1:
    report: CapabilityReportV1
    report_index: CapabilityReportIndexV1

    @property
    def m4_manifest_sha256(self) -> str:
        return self.report.m4_manifest_sha256

    @property
    def m3_context(self) -> M3ReportContextV1:
        return self.report.m3_context

    @property
    def capability_counts(self) -> dict[str, JSONValue]:
        return self.report.capability_counts

    @property
    def mapping_counts(self) -> dict[str, JSONValue]:
        return self.report.mapping_counts

    def to_wire(self) -> dict[str, JSONValue]:
        return self.report.to_wire()


__all__ = [
    "CapabilityReportBuildResultV1",
    "CapabilityReportDescriptorV1",
    "CapabilityReportIndexV1",
    "CapabilityReportV1",
    "M3ReportContextV1",
    "REPORT_INDEX_FILENAME",
    "REPORT_INDEX_SCHEMA",
    "REPORT_FILENAME",
    "REPORT_SCHEMA",
]
