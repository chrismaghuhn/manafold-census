from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from analysis_fixtures import effective_pattern_registry, exact_pattern_rule
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from manafold_census.analysis.patterns import (
    EffectivePatternRegistryV1,
    EvidencePolicyV1,
    MatcherKindV1,
    NormalizationProfileV1,
    PatternRuleV1,
    PatternSourceFieldV1,
    PatternSourceScopeV1,
)


def validate_pattern_schema(document: dict[str, object]) -> None:
    root = Path(__file__).parents[1]
    schema = json.loads(
        (root / "schemas" / "pattern-registry.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    requirement = json.loads(
        (root / "schemas" / "semantic-requirement.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    requirement_id = requirement["$id"]
    registry = Registry().with_resource(
        requirement_id,
        Resource.from_contents(requirement, default_specification=DRAFT202012),
    )
    Draft202012Validator(schema, registry=registry).validate(document)


def test_effective_pattern_registry_digest_changes_when_eligibility_changes() -> None:
    eligible = effective_pattern_registry(reviewed_for_reuse=True)
    ineligible = effective_pattern_registry(reviewed_for_reuse=False)
    assert eligible.digest() != ineligible.digest()


def test_pattern_identity_contains_behavior_but_not_card_name() -> None:
    rule, _ = exact_pattern_rule()
    assert not hasattr(rule, "card_name")
    assert rule.pattern_id == "m3.exact-clause.draw"


def test_v1_rejects_arbitrary_output_templates_and_non_none_normalization() -> None:
    rule, _ = exact_pattern_rule()
    wire = rule.to_wire()

    arbitrary = copy.deepcopy(wire)
    arbitrary["output_template"]["parameters"] = {"arbitrary": True}
    with pytest.raises(
        (TypeError, ValueError),
        match="parameters|payload|missing|unexpected",
    ):
        PatternRuleV1.from_wire(arbitrary)

    non_none = copy.deepcopy(wire)
    non_none["normalization_profile"] = "LOWERCASE"
    with pytest.raises((TypeError, ValueError), match="normalization"):
        PatternRuleV1.from_wire(non_none)


def test_exact_matcher_modes_have_closed_source_scope_rules() -> None:
    rule, _ = exact_pattern_rule()
    assert rule.matcher_kind is MatcherKindV1.EXACT_FRAGMENT
    assert rule.normalization_profile is NormalizationProfileV1.NONE
    assert rule.source_scope.field is PatternSourceFieldV1.ORACLE_TEXT
    assert rule.evidence_policy is EvidencePolicyV1.EXACT_FRAGMENT

    with pytest.raises(ValueError, match="face_index"):
        PatternSourceScopeV1(PatternSourceFieldV1.KEYWORDS, 0)


def test_pattern_registry_wire_round_trips_and_schema_validates() -> None:
    registry = effective_pattern_registry()
    assert EffectivePatternRegistryV1.from_wire(registry.to_wire()) == registry
    validate_pattern_schema(registry.to_wire())


def test_checked_in_pattern_registry_fixture_is_valid() -> None:
    root = Path(__file__).parents[1]
    document = json.loads(
        (root / "fixtures" / "analysis" / "pattern-registry.v1.json").read_text(
            encoding="utf-8"
        )
    )
    registry = EffectivePatternRegistryV1.from_wire(document)
    validate_pattern_schema(registry.to_wire())


def test_pattern_registry_rejects_missing_or_mismatched_eligibility() -> None:
    rule, eligibility = exact_pattern_rule()
    with pytest.raises(ValueError, match="eligibility"):
        EffectivePatternRegistryV1.build((rule,), ())
    with pytest.raises(ValueError, match="unknown|match"):
        EffectivePatternRegistryV1.build(
            (rule,),
            (
                type(eligibility)(
                    pattern_id="m3.other",
                    pattern_version="1",
                    eligibility=eligibility.eligibility,
                    review_record_id=eligibility.review_record_id,
                    review_record_sha256=eligibility.review_record_sha256,
                ),
            ),
        )
