"""Exact M4 Requirement-to-Capability links and mapping dispositions."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar, cast

from ..canonical import JSONValue
from ..digest import domain_digest
from ..semantic.primitives import _require_enum, _require_object, _require_text
from .admissibility import SourceRequirementAdmissibilityV1
from .binding import ParameterBindingV1
from .identity import (
    LINK_CLAIM_DOMAIN,
    LINK_ID_DOMAIN,
    LINK_ID_PREFIX,
)
from .model import CapabilityRefV1

_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_REQUIREMENT_ID_PATTERN = re.compile(r"^srq_[0-9a-f]{64}$")
_LINK_ID_PATTERN = re.compile(r"^rcl_[0-9a-f]{64}$")
_REVIEW_ID_PATTERN = re.compile(r"^mrv_[0-9a-f]{64}$")
_SRA_ID_PATTERN = re.compile(r"^sra_[0-9a-f]{64}$")

LINK_SCHEMA = "census.requirement-capability-link.v1"


class LinkRelationV1(StrEnum):
    DIRECT = "DIRECT"
    COMPOSITION_MEMBER = "COMPOSITION_MEMBER"


class LinkAdmissibilityBasisV1(StrEnum):
    M2_TERMINAL_ACCEPTANCE = "M2_TERMINAL_ACCEPTANCE"
    SOURCE_REQUIREMENT_ADMISSIBILITY = "SOURCE_REQUIREMENT_ADMISSIBILITY"


def _digest(field: str, value: object) -> str:
    text = _require_text(field, value)
    if _DIGEST_PATTERN.fullmatch(text) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")
    return text


def _identifier(field: str, value: object, pattern: re.Pattern[str]) -> str:
    text = _require_text(field, value)
    if pattern.fullmatch(text) is None:
        raise ValueError(f"{field} must use its closed digest identity form")
    return text


def _values(value: object, field: str) -> tuple[object, ...]:
    if not isinstance(value, tuple | list):
        raise TypeError(f"{field} must be a tuple or list")
    return tuple(value)


@dataclass(frozen=True, slots=True)
class M4RequirementAdmissibilityV1:
    basis: LinkAdmissibilityBasisV1
    record_id: str | None
    review_digest: str | None

    _WIRE_KEYS: ClassVar[set[str]] = {"basis", "record_id", "review_digest"}

    def __post_init__(self) -> None:
        basis = _require_enum("basis", self.basis, LinkAdmissibilityBasisV1)
        record_id = self.record_id
        review_digest = self.review_digest
        if basis is LinkAdmissibilityBasisV1.M2_TERMINAL_ACCEPTANCE:
            if record_id is not None or review_digest is not None:
                raise ValueError("terminal admissibility cannot contain an SRA record")
        else:
            record_id = _identifier("record_id", record_id, _SRA_ID_PATTERN)
            review_digest = _digest("review_digest", review_digest)
        object.__setattr__(self, "basis", basis)
        object.__setattr__(self, "record_id", record_id)
        object.__setattr__(self, "review_digest", review_digest)

    @classmethod
    def terminal(cls) -> M4RequirementAdmissibilityV1:
        return cls(LinkAdmissibilityBasisV1.M2_TERMINAL_ACCEPTANCE, None, None)

    @classmethod
    def source(
        cls, record: SourceRequirementAdmissibilityV1
    ) -> M4RequirementAdmissibilityV1:
        if not isinstance(record, SourceRequirementAdmissibilityV1):
            raise TypeError("record must be SourceRequirementAdmissibilityV1")
        if record.decision.value != "ACCEPTED_FOR_CAPABILITY_MAPPING":
            raise ValueError("SRA record is not accepted")
        return cls(
            LinkAdmissibilityBasisV1.SOURCE_REQUIREMENT_ADMISSIBILITY,
            record.record_id,
            record.review_digest,
        )

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "basis": self.basis.value,
            "record_id": self.record_id,
            "review_digest": self.review_digest,
        }

    @classmethod
    def from_wire(cls, value: object) -> M4RequirementAdmissibilityV1:
        document = _require_object(value, cls._WIRE_KEYS, "link admissibility")
        return cls(
            _require_enum("basis", document["basis"], LinkAdmissibilityBasisV1),
            cast(str | None, document["record_id"]),
            cast(str | None, document["review_digest"]),
        )


LinkAdmissibilityV1 = M4RequirementAdmissibilityV1


@dataclass(frozen=True, slots=True)
class CompositionContextV1:
    composite: CapabilityRefV1
    component_key: str

    _WIRE_KEYS: ClassVar[set[str]] = {"composite", "component_key"}

    def __post_init__(self) -> None:
        if not isinstance(self.composite, CapabilityRefV1):
            raise TypeError("composite must be CapabilityRefV1")
        object.__setattr__(
            self, "component_key", _require_text("component_key", self.component_key)
        )

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "composite": self.composite.to_wire(),
            "component_key": self.component_key,
        }

    @classmethod
    def from_wire(cls, value: object) -> CompositionContextV1:
        document = _require_object(value, cls._WIRE_KEYS, "composition context")
        return cls(
            CapabilityRefV1.from_wire(document["composite"]),
            cast(str, document["component_key"]),
        )


def _binding_values(value: object) -> tuple[ParameterBindingV1, ...]:
    values = _values(value, "parameter_bindings")
    if any(not isinstance(item, ParameterBindingV1) for item in values):
        raise TypeError("parameter_bindings must contain ParameterBindingV1 values")
    bindings = cast(tuple[ParameterBindingV1, ...], values)
    paths = [item.path_key for item in bindings]
    if len(paths) != len(set(paths)):
        raise ValueError("duplicate parameter binding path")
    return tuple(sorted(bindings, key=lambda item: item.path_key.value))


def _link_claim_payload_values(
    *,
    m3_analysis_manifest_sha256: str,
    requirement_id: str,
    requirement_wire_digest: str,
    requirement_reviewed_claim_digest: str | None,
    capability: CapabilityRefV1,
    relation: LinkRelationV1,
    parameter_bindings: tuple[ParameterBindingV1, ...],
    m4_requirement_admissibility: M4RequirementAdmissibilityV1 | None,
    composition_context: CompositionContextV1 | None,
) -> dict[str, JSONValue]:
    return {
        "link_schema": LINK_SCHEMA,
        "m3_analysis_manifest_sha256": m3_analysis_manifest_sha256,
        "requirement_id": requirement_id,
        "requirement_wire_digest": requirement_wire_digest,
        "requirement_reviewed_claim_digest": requirement_reviewed_claim_digest,
        "capability": capability.to_wire(),
        "relation": relation.value,
        "parameter_bindings": [item.to_wire() for item in parameter_bindings],
        "m4_requirement_admissibility": (
            None
            if m4_requirement_admissibility is None
            else m4_requirement_admissibility.to_wire()
        ),
        "composition_context": (
            None if composition_context is None else composition_context.to_wire()
        ),
    }


@dataclass(frozen=True, slots=True)
class RequirementCapabilityLinkV1:
    link_id: str
    link_claim_digest: str
    m3_analysis_manifest_sha256: str
    requirement_id: str
    requirement_wire_digest: str
    requirement_reviewed_claim_digest: str | None
    capability: CapabilityRefV1
    relation: LinkRelationV1
    parameter_bindings: tuple[ParameterBindingV1, ...]
    m4_requirement_admissibility: M4RequirementAdmissibilityV1 | None
    composition_context: CompositionContextV1 | None
    review_ref: str | None

    _WIRE_KEYS: ClassVar[set[str]] = {
        "link_id",
        "link_claim_digest",
        "link_schema",
        "m3_analysis_manifest_sha256",
        "requirement_id",
        "requirement_wire_digest",
        "requirement_reviewed_claim_digest",
        "capability",
        "relation",
        "parameter_bindings",
        "m4_requirement_admissibility",
        "composition_context",
        "review_ref",
    }

    def __post_init__(self) -> None:
        link_id = _identifier("link_id", self.link_id, _LINK_ID_PATTERN)
        link_claim_digest = _digest("link_claim_digest", self.link_claim_digest)
        manifest = _digest(
            "m3_analysis_manifest_sha256", self.m3_analysis_manifest_sha256
        )
        requirement_id = _identifier(
            "requirement_id", self.requirement_id, _REQUIREMENT_ID_PATTERN
        )
        requirement_wire_digest = _digest(
            "requirement_wire_digest", self.requirement_wire_digest
        )
        reviewed_digest = (
            None
            if self.requirement_reviewed_claim_digest is None
            else _digest(
                "requirement_reviewed_claim_digest",
                self.requirement_reviewed_claim_digest,
            )
        )
        if not isinstance(self.capability, CapabilityRefV1):
            raise TypeError("capability must be CapabilityRefV1")
        relation = _require_enum("relation", self.relation, LinkRelationV1)
        bindings = _binding_values(self.parameter_bindings)
        admissibility = self.m4_requirement_admissibility
        if admissibility is not None and not isinstance(
            admissibility, M4RequirementAdmissibilityV1
        ):
            raise TypeError("m4_requirement_admissibility must be typed or None")
        context = self.composition_context
        if context is not None and not isinstance(context, CompositionContextV1):
            raise TypeError("composition_context must be CompositionContextV1 or None")
        if relation is LinkRelationV1.DIRECT and context is not None:
            raise ValueError("DIRECT link cannot contain composition context")
        if relation is LinkRelationV1.COMPOSITION_MEMBER and context is None:
            raise ValueError("COMPOSITION_MEMBER link requires composition context")
        review_ref = self.review_ref
        if review_ref is not None:
            review_ref = _identifier("review_ref", review_ref, _REVIEW_ID_PATTERN)

        payload = _link_claim_payload_values(
            m3_analysis_manifest_sha256=manifest,
            requirement_id=requirement_id,
            requirement_wire_digest=requirement_wire_digest,
            requirement_reviewed_claim_digest=reviewed_digest,
            capability=self.capability,
            relation=relation,
            parameter_bindings=bindings,
            m4_requirement_admissibility=admissibility,
            composition_context=context,
        )
        expected_claim_digest = domain_digest(LINK_CLAIM_DOMAIN, payload)
        expected_link_id = LINK_ID_PREFIX + domain_digest(LINK_ID_DOMAIN, payload)
        if link_claim_digest != expected_claim_digest:
            raise ValueError("link_claim_digest does not match link claim")
        if link_id != expected_link_id:
            raise ValueError("link_id does not match link claim")

        object.__setattr__(self, "link_id", link_id)
        object.__setattr__(self, "link_claim_digest", link_claim_digest)
        object.__setattr__(self, "m3_analysis_manifest_sha256", manifest)
        object.__setattr__(self, "requirement_id", requirement_id)
        object.__setattr__(self, "requirement_wire_digest", requirement_wire_digest)
        object.__setattr__(self, "requirement_reviewed_claim_digest", reviewed_digest)
        object.__setattr__(self, "relation", relation)
        object.__setattr__(self, "parameter_bindings", bindings)
        object.__setattr__(self, "review_ref", review_ref)

    @classmethod
    def create(
        cls,
        *,
        m3_analysis_manifest_sha256: str,
        requirement_id: str,
        requirement_wire_digest: str,
        requirement_reviewed_claim_digest: str | None,
        capability: CapabilityRefV1,
        relation: LinkRelationV1,
        parameter_bindings: Sequence[ParameterBindingV1],
        m4_requirement_admissibility: M4RequirementAdmissibilityV1 | None,
        composition_context: CompositionContextV1 | None,
        review_ref: str | None = None,
    ) -> RequirementCapabilityLinkV1:
        bindings = _binding_values(parameter_bindings)
        relation_value = _require_enum("relation", relation, LinkRelationV1)
        if not isinstance(capability, CapabilityRefV1):
            raise TypeError("capability must be CapabilityRefV1")
        payload = _link_claim_payload_values(
            m3_analysis_manifest_sha256=m3_analysis_manifest_sha256,
            requirement_id=requirement_id,
            requirement_wire_digest=requirement_wire_digest,
            requirement_reviewed_claim_digest=(
                None
                if requirement_reviewed_claim_digest is None
                else requirement_reviewed_claim_digest
            ),
            capability=capability,
            relation=relation_value,
            parameter_bindings=bindings,
            m4_requirement_admissibility=m4_requirement_admissibility,
            composition_context=composition_context,
        )
        claim_digest = domain_digest(LINK_CLAIM_DOMAIN, payload)
        return cls(
            link_id=LINK_ID_PREFIX + domain_digest(LINK_ID_DOMAIN, payload),
            link_claim_digest=claim_digest,
            m3_analysis_manifest_sha256=m3_analysis_manifest_sha256,
            requirement_id=requirement_id,
            requirement_wire_digest=requirement_wire_digest,
            requirement_reviewed_claim_digest=requirement_reviewed_claim_digest,
            capability=capability,
            relation=relation_value,
            parameter_bindings=bindings,
            m4_requirement_admissibility=m4_requirement_admissibility,
            composition_context=composition_context,
            review_ref=review_ref,
        )

    def to_wire(self) -> dict[str, JSONValue]:
        payload = _link_claim_payload_values(
            m3_analysis_manifest_sha256=self.m3_analysis_manifest_sha256,
            requirement_id=self.requirement_id,
            requirement_wire_digest=self.requirement_wire_digest,
            requirement_reviewed_claim_digest=self.requirement_reviewed_claim_digest,
            capability=self.capability,
            relation=self.relation,
            parameter_bindings=self.parameter_bindings,
            m4_requirement_admissibility=self.m4_requirement_admissibility,
            composition_context=self.composition_context,
        )
        return {
            "link_id": self.link_id,
            "link_claim_digest": self.link_claim_digest,
            **payload,
            "review_ref": self.review_ref,
        }

    @classmethod
    def from_wire(cls, value: object) -> RequirementCapabilityLinkV1:
        document = _require_object(value, cls._WIRE_KEYS, "Requirement Capability link")
        if document["link_schema"] != LINK_SCHEMA:
            raise ValueError(f"link_schema must be {LINK_SCHEMA}")
        raw_bindings = document["parameter_bindings"]
        if not isinstance(raw_bindings, list):
            raise TypeError("parameter_bindings must be a JSON array")
        raw_admissibility = document["m4_requirement_admissibility"]
        raw_context = document["composition_context"]
        result = cls(
            link_id=cast(str, document["link_id"]),
            link_claim_digest=cast(str, document["link_claim_digest"]),
            m3_analysis_manifest_sha256=cast(
                str, document["m3_analysis_manifest_sha256"]
            ),
            requirement_id=cast(str, document["requirement_id"]),
            requirement_wire_digest=cast(str, document["requirement_wire_digest"]),
            requirement_reviewed_claim_digest=cast(
                str | None, document["requirement_reviewed_claim_digest"]
            ),
            capability=CapabilityRefV1.from_wire(document["capability"]),
            relation=_require_enum("relation", document["relation"], LinkRelationV1),
            parameter_bindings=tuple(
                ParameterBindingV1.from_wire(item) for item in raw_bindings
            ),
            m4_requirement_admissibility=(
                None
                if raw_admissibility is None
                else M4RequirementAdmissibilityV1.from_wire(raw_admissibility)
            ),
            composition_context=(
                None
                if raw_context is None
                else CompositionContextV1.from_wire(raw_context)
            ),
            review_ref=cast(str | None, document["review_ref"]),
        )
        if result.to_wire() != document:
            raise ValueError("Requirement Capability link wire is not canonical")
        return result
