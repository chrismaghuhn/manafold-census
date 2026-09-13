"""Closed, exact-only M3 pattern definitions and effective registry."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar, cast

from ..canonical import JSONValue
from ..digest import domain_digest
from ..semantic.kind_payloads import (
    KindPayloadV1,
    payload_from_wire,
    payload_to_wire,
)
from ..semantic.kinds import RequirementFamilyV1, RequirementKindV1
from ..semantic.primitives import (
    _require_enum,
    _require_object,
)

PATTERN_RULE_SCHEMA = "census.pattern-rule.v1"
PATTERN_REGISTRY_SCHEMA = "census.pattern-registry.v1"
PATTERN_RULE_DIGEST_DOMAIN = "census.m3-pattern-rule.v1"
PATTERN_REGISTRY_DIGEST_DOMAIN = "census.m3-pattern-registry.v1"
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class MatcherKindV1(StrEnum):
    EXACT_FIELD_TEXT = "EXACT_FIELD_TEXT"
    EXACT_FACE_FIELD_TEXT = "EXACT_FACE_FIELD_TEXT"
    EXACT_FRAGMENT = "EXACT_FRAGMENT"


class NormalizationProfileV1(StrEnum):
    NONE = "NONE"


class PatternSourceFieldV1(StrEnum):
    ORACLE_TEXT = "oracle_text"
    KEYWORDS = "keywords"


class EvidencePolicyV1(StrEnum):
    EXACT_FIELD = "EXACT_FIELD"
    EXACT_FRAGMENT = "EXACT_FRAGMENT"


class PatternEligibilityStateV1(StrEnum):
    REVIEWED_FOR_REUSE = "REVIEWED_FOR_REUSE"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"


def _require_text(field: str, value: object) -> str:
    if not isinstance(value, str) or value == "":
        raise ValueError(f"{field} must be a non-empty string")
    value.encode("utf-8")
    return value


def _require_digest(field: str, value: object) -> str:
    if not isinstance(value, str) or _DIGEST_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _require_nonnegative_int(field: str, value: object) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value


@dataclass(frozen=True, slots=True)
class PatternSourceScopeV1:
    field: PatternSourceFieldV1
    face_index: int | None

    _WIRE_KEYS: ClassVar[set[str]] = {"field", "face_index"}

    def __post_init__(self) -> None:
        field = _require_enum("field", self.field, PatternSourceFieldV1)
        object.__setattr__(self, "field", field)
        if self.face_index is not None:
            object.__setattr__(
                self,
                "face_index",
                _require_nonnegative_int("face_index", self.face_index),
            )
        if field is PatternSourceFieldV1.KEYWORDS and self.face_index is not None:
            raise ValueError("keywords scope cannot have a face_index")

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "field": self.field.value,
            "face_index": self.face_index,
        }

    @classmethod
    def from_wire(cls, value: object) -> PatternSourceScopeV1:
        document = _require_object(value, cls._WIRE_KEYS, "pattern source scope")
        return cls(
            field=_require_enum("field", document["field"], PatternSourceFieldV1),
            face_index=(
                None
                if document["face_index"] is None
                else _require_nonnegative_int("face_index", document["face_index"])
            ),
        )


@dataclass(frozen=True, slots=True)
class PatternOutputTemplateV1:
    family: RequirementFamilyV1
    kind: RequirementKindV1
    parameters: KindPayloadV1

    _WIRE_KEYS: ClassVar[set[str]] = {"family", "kind", "parameters"}

    def __post_init__(self) -> None:
        family = _require_enum("family", self.family, RequirementFamilyV1)
        kind = _require_enum("kind", self.kind, RequirementKindV1)
        from ..semantic.kinds import validate_kind_family

        validate_kind_family(family, kind)
        payload_to_wire(family, kind, self.parameters)
        object.__setattr__(self, "family", family)
        object.__setattr__(self, "kind", kind)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "family": self.family.value,
            "kind": self.kind.value,
            "parameters": payload_to_wire(self.family, self.kind, self.parameters),
        }

    @classmethod
    def from_wire(cls, value: object) -> PatternOutputTemplateV1:
        document = _require_object(value, cls._WIRE_KEYS, "pattern output template")
        family = _require_enum("family", document["family"], RequirementFamilyV1)
        kind = _require_enum("kind", document["kind"], RequirementKindV1)
        return cls(
            family=family,
            kind=kind,
            parameters=payload_from_wire(family, kind, document["parameters"]),
        )


@dataclass(frozen=True, slots=True)
class PatternRuleV1:
    pattern_id: str
    pattern_version: str
    matcher_kind: MatcherKindV1
    source_scope: PatternSourceScopeV1
    normalization_profile: NormalizationProfileV1
    match_text: str
    output_template: PatternOutputTemplateV1
    evidence_policy: EvidencePolicyV1
    producer_id: str
    producer_version: str
    m2_contract_version: str

    SCHEMA: ClassVar[str] = PATTERN_RULE_SCHEMA
    _WIRE_KEYS: ClassVar[set[str]] = {
        "schema",
        "pattern_id",
        "pattern_version",
        "matcher_kind",
        "source_scope",
        "normalization_profile",
        "match_text",
        "output_template",
        "evidence_policy",
        "producer_id",
        "producer_version",
        "m2_contract_version",
    }

    def __post_init__(self) -> None:
        for field in (
            "pattern_id",
            "pattern_version",
            "match_text",
            "producer_id",
            "producer_version",
            "m2_contract_version",
        ):
            object.__setattr__(self, field, _require_text(field, getattr(self, field)))
        matcher_kind = _require_enum("matcher_kind", self.matcher_kind, MatcherKindV1)
        normalization = _require_enum(
            "normalization_profile",
            self.normalization_profile,
            NormalizationProfileV1,
        )
        evidence_policy = _require_enum(
            "evidence_policy",
            self.evidence_policy,
            EvidencePolicyV1,
        )
        if not isinstance(self.source_scope, PatternSourceScopeV1):
            raise TypeError("source_scope must be PatternSourceScopeV1")
        if not isinstance(self.output_template, PatternOutputTemplateV1):
            raise TypeError("output_template must be PatternOutputTemplateV1")
        if normalization is not NormalizationProfileV1.NONE:
            raise ValueError("M3 V1 supports only NONE normalization")
        if self.m2_contract_version != "census.semantic-requirement.v1":
            raise ValueError(
                "m2_contract_version must be census.semantic-requirement.v1"
            )
        if matcher_kind is MatcherKindV1.EXACT_FIELD_TEXT:
            if self.source_scope.face_index is not None:
                raise ValueError("EXACT_FIELD_TEXT cannot have a face_index")
            if evidence_policy is not EvidencePolicyV1.EXACT_FIELD:
                raise ValueError("EXACT_FIELD_TEXT requires EXACT_FIELD evidence")
        elif matcher_kind is MatcherKindV1.EXACT_FACE_FIELD_TEXT:
            if self.source_scope.field is not PatternSourceFieldV1.ORACLE_TEXT:
                raise ValueError("EXACT_FACE_FIELD_TEXT requires oracle_text")
            if self.source_scope.face_index is None:
                raise ValueError("EXACT_FACE_FIELD_TEXT requires a face_index")
            if evidence_policy is not EvidencePolicyV1.EXACT_FIELD:
                raise ValueError("EXACT_FACE_FIELD_TEXT requires EXACT_FIELD evidence")
        elif matcher_kind is MatcherKindV1.EXACT_FRAGMENT:
            if self.source_scope.field is not PatternSourceFieldV1.ORACLE_TEXT:
                raise ValueError("EXACT_FRAGMENT requires oracle_text")
            if evidence_policy is not EvidencePolicyV1.EXACT_FRAGMENT:
                raise ValueError("EXACT_FRAGMENT requires EXACT_FRAGMENT evidence")
        object.__setattr__(self, "matcher_kind", matcher_kind)
        object.__setattr__(self, "normalization_profile", normalization)
        object.__setattr__(self, "evidence_policy", evidence_policy)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "schema": self.SCHEMA,
            "pattern_id": self.pattern_id,
            "pattern_version": self.pattern_version,
            "matcher_kind": self.matcher_kind.value,
            "source_scope": self.source_scope.to_wire(),
            "normalization_profile": self.normalization_profile.value,
            "match_text": self.match_text,
            "output_template": self.output_template.to_wire(),
            "evidence_policy": self.evidence_policy.value,
            "producer_id": self.producer_id,
            "producer_version": self.producer_version,
            "m2_contract_version": self.m2_contract_version,
        }

    @classmethod
    def from_wire(cls, value: object) -> PatternRuleV1:
        document = _require_object(value, cls._WIRE_KEYS, "PatternRuleV1")
        if document["schema"] != cls.SCHEMA:
            raise ValueError(f"schema must be {cls.SCHEMA}")
        return cls(
            pattern_id=cast(str, document["pattern_id"]),
            pattern_version=cast(str, document["pattern_version"]),
            matcher_kind=_require_enum(
                "matcher_kind", document["matcher_kind"], MatcherKindV1
            ),
            source_scope=PatternSourceScopeV1.from_wire(document["source_scope"]),
            normalization_profile=_require_enum(
                "normalization_profile",
                document["normalization_profile"],
                NormalizationProfileV1,
            ),
            match_text=cast(str, document["match_text"]),
            output_template=PatternOutputTemplateV1.from_wire(
                document["output_template"]
            ),
            evidence_policy=_require_enum(
                "evidence_policy",
                document["evidence_policy"],
                EvidencePolicyV1,
            ),
            producer_id=cast(str, document["producer_id"]),
            producer_version=cast(str, document["producer_version"]),
            m2_contract_version=cast(str, document["m2_contract_version"]),
        )


@dataclass(frozen=True, slots=True)
class PatternEligibilityV1:
    pattern_id: str
    pattern_version: str
    eligibility: PatternEligibilityStateV1
    review_record_id: str
    review_record_sha256: str

    _WIRE_KEYS: ClassVar[set[str]] = {
        "pattern_id",
        "pattern_version",
        "eligibility",
        "review_record_id",
        "review_record_sha256",
    }

    def __post_init__(self) -> None:
        for field in ("pattern_id", "pattern_version", "review_record_id"):
            object.__setattr__(self, field, _require_text(field, getattr(self, field)))
        object.__setattr__(
            self,
            "eligibility",
            _require_enum("eligibility", self.eligibility, PatternEligibilityStateV1),
        )
        object.__setattr__(
            self,
            "review_record_sha256",
            _require_digest("review_record_sha256", self.review_record_sha256),
        )

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "pattern_id": self.pattern_id,
            "pattern_version": self.pattern_version,
            "eligibility": self.eligibility.value,
            "review_record_id": self.review_record_id,
            "review_record_sha256": self.review_record_sha256,
        }

    @classmethod
    def from_wire(cls, value: object) -> PatternEligibilityV1:
        document = _require_object(value, cls._WIRE_KEYS, "pattern eligibility")
        return cls(
            pattern_id=cast(str, document["pattern_id"]),
            pattern_version=cast(str, document["pattern_version"]),
            eligibility=_require_enum(
                "eligibility",
                document["eligibility"],
                PatternEligibilityStateV1,
            ),
            review_record_id=cast(str, document["review_record_id"]),
            review_record_sha256=cast(str, document["review_record_sha256"]),
        )


def pattern_rule_digest_for(rule: PatternRuleV1) -> str:
    if not isinstance(rule, PatternRuleV1):
        raise TypeError("rule must be PatternRuleV1")
    return domain_digest(PATTERN_RULE_DIGEST_DOMAIN, rule.to_wire())


@dataclass(frozen=True, slots=True)
class EffectivePatternRegistryV1:
    rules: tuple[PatternRuleV1, ...]
    eligibility: tuple[PatternEligibilityV1, ...]

    SCHEMA: ClassVar[str] = PATTERN_REGISTRY_SCHEMA
    _WIRE_KEYS: ClassVar[set[str]] = {"schema", "rules", "eligibility"}

    def __post_init__(self) -> None:
        rules = tuple(self.rules)
        eligibility = tuple(self.eligibility)
        if any(not isinstance(item, PatternRuleV1) for item in rules):
            raise TypeError("rules must contain PatternRuleV1 values")
        if any(not isinstance(item, PatternEligibilityV1) for item in eligibility):
            raise TypeError("eligibility must contain PatternEligibilityV1 values")
        rule_keys = [(item.pattern_id, item.pattern_version) for item in rules]
        eligibility_keys = [
            (item.pattern_id, item.pattern_version) for item in eligibility
        ]
        if rule_keys != sorted(rule_keys) or len(rule_keys) != len(set(rule_keys)):
            raise ValueError("rules must be sorted and unique")
        if eligibility_keys != sorted(eligibility_keys) or len(eligibility_keys) != len(
            set(eligibility_keys)
        ):
            raise ValueError("eligibility must be sorted and unique")
        if set(rule_keys) != set(eligibility_keys):
            raise ValueError("every pattern rule requires matching eligibility")
        object.__setattr__(self, "rules", rules)
        object.__setattr__(self, "eligibility", eligibility)

    @classmethod
    def build(
        cls,
        rules: tuple[PatternRuleV1, ...] | list[PatternRuleV1],
        eligibility: tuple[PatternEligibilityV1, ...] | list[PatternEligibilityV1],
    ) -> EffectivePatternRegistryV1:
        return cls(
            tuple(
                sorted(rules, key=lambda item: (item.pattern_id, item.pattern_version))
            ),
            tuple(
                sorted(
                    eligibility,
                    key=lambda item: (item.pattern_id, item.pattern_version),
                )
            ),
        )

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "schema": self.SCHEMA,
            "rules": [item.to_wire() for item in self.rules],
            "eligibility": [item.to_wire() for item in self.eligibility],
        }

    @classmethod
    def from_wire(cls, value: object) -> EffectivePatternRegistryV1:
        document = _require_object(value, cls._WIRE_KEYS, "pattern registry")
        if document["schema"] != cls.SCHEMA:
            raise ValueError(f"schema must be {cls.SCHEMA}")
        raw_rules = document["rules"]
        raw_eligibility = document["eligibility"]
        if not isinstance(raw_rules, list) or not isinstance(raw_eligibility, list):
            raise TypeError("rules and eligibility must be JSON arrays")
        return cls(
            tuple(PatternRuleV1.from_wire(item) for item in raw_rules),
            tuple(PatternEligibilityV1.from_wire(item) for item in raw_eligibility),
        )

    def digest(self) -> str:
        return domain_digest(PATTERN_REGISTRY_DIGEST_DOMAIN, self.to_wire())

    def matches_exact_text(
        self,
        pattern_id: str,
        pattern_version: str,
        text: str,
        *,
        face_index: int | None,
    ) -> bool:
        """Match only a rule explicitly eligible for deterministic reuse."""

        key = (pattern_id, pattern_version)
        rules = {(item.pattern_id, item.pattern_version): item for item in self.rules}
        eligibilities = {
            (item.pattern_id, item.pattern_version): item for item in self.eligibility
        }
        rule = rules.get(key)
        eligibility = eligibilities.get(key)
        if rule is None or eligibility is None:
            raise ValueError("pattern rule is not present in effective registry")
        if eligibility.eligibility is not PatternEligibilityStateV1.REVIEWED_FOR_REUSE:
            return False
        return matches_exact_text(rule, text, face_index=face_index)


def matches_exact_text(
    rule: PatternRuleV1,
    text: str,
    *,
    face_index: int | None,
) -> bool:
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if rule.source_scope.face_index != face_index:
        return False
    if rule.matcher_kind is MatcherKindV1.EXACT_FRAGMENT:
        return rule.match_text in text
    return rule.match_text == text


__all__ = [
    "EffectivePatternRegistryV1",
    "EvidencePolicyV1",
    "MatcherKindV1",
    "NormalizationProfileV1",
    "PATTERN_REGISTRY_DIGEST_DOMAIN",
    "PATTERN_REGISTRY_SCHEMA",
    "PATTERN_RULE_DIGEST_DOMAIN",
    "PATTERN_RULE_SCHEMA",
    "PatternEligibilityStateV1",
    "PatternEligibilityV1",
    "PatternOutputTemplateV1",
    "PatternRuleV1",
    "PatternSourceFieldV1",
    "PatternSourceScopeV1",
    "matches_exact_text",
    "pattern_rule_digest_for",
]
