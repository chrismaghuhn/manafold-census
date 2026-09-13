from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path

import pytest
from analysis_fixtures import (
    OTHER_ORACLE_ID,
    exact_pattern_rule,
    source_lock_digest,
    structural_record,
)

from manafold_census.analysis.patterns import (
    PATTERN_REGISTRY_DIGEST_DOMAIN,
    EffectivePatternRegistryV1,
    EvidencePolicyV1,
    MatcherKindV1,
    PatternEligibilityStateV1,
    PatternEligibilityV1,
    PatternSourceFieldV1,
    PatternSourceScopeV1,
    pattern_rule_digest_for,
)
from manafold_census.analysis.producer import (
    ImmutableRegistrySnapshotV1,
    ProducerContractError,
    ProducerExecutionError,
    ProducerResultStatusV1,
    execute_producer,
)
from manafold_census.semantic.evidence import (
    StructuralFieldEvidenceV1,
    StructuralKeywordEvidenceV1,
)
from manafold_census.semantic.model import DerivationMethodV1, ReviewStatusV1
from manafold_census.structural.model import StructuralFaceV1

PRODUCER_ID = "m3.registry-exact-pattern"
PRODUCER_VERSION = "1"


def _registry(
    *rules,
    states: tuple[PatternEligibilityStateV1, ...] | None = None,
) -> EffectivePatternRegistryV1:
    selected_states = states or (PatternEligibilityStateV1.REVIEWED_FOR_REUSE,) * len(
        rules
    )
    eligibilities = tuple(
        PatternEligibilityV1(
            pattern_id=rule.pattern_id,
            pattern_version=rule.pattern_version,
            eligibility=state,
            review_record_id=f"review-{rule.pattern_id}",
            review_record_sha256="d" * 64,
        )
        for rule, state in zip(rules, selected_states, strict=True)
    )
    return EffectivePatternRegistryV1.build(tuple(rules), eligibilities)


def _producer_context(registry: EffectivePatternRegistryV1):
    snapshot = ImmutableRegistrySnapshotV1.from_wire(
        "pattern",
        "census.pattern-registry.v1",
        PATTERN_REGISTRY_DIGEST_DOMAIN,
        registry.to_wire(),
    )
    return _context_for_snapshot(snapshot)


def _context_for_snapshot(snapshot: ImmutableRegistrySnapshotV1):
    producer_snapshot = ImmutableRegistrySnapshotV1.from_wire(
        "producer",
        "census.producer-registry.v1",
        "census.test-registry.v1",
        {"schema": "census.producer-registry.v1", "producers": []},
    )
    from manafold_census.analysis.producer import ProducerContextV1

    return ProducerContextV1(
        source_lock_digest=source_lock_digest(),
        m2_requirement_schema="census.semantic-requirement.v1",
        m2_bundle_schema="census.semantic-requirement-bundle.v1",
        producer_registry=producer_snapshot,
        pattern_registry=snapshot,
    )


def _producer(registry: EffectivePatternRegistryV1):
    from manafold_census.analysis.pattern_producer import (
        RegistryDrivenExactPatternProducerV1,
    )

    return RegistryDrivenExactPatternProducerV1(
        pattern_registry_digest=registry.digest()
    )


def _fixture_rule():
    rule, _ = exact_pattern_rule()
    return replace(
        rule,
        producer_id=PRODUCER_ID,
        producer_version=PRODUCER_VERSION,
    )


def test_exact_fragment_emits_typed_proposed_candidate_and_finding() -> None:
    rule = _fixture_rule()
    registry = _registry(rule)
    producer = _producer(registry)
    result = execute_producer(
        producer, structural_record(), _producer_context(registry)
    )

    assert producer.descriptor.producer_id == PRODUCER_ID
    assert producer.descriptor.producer_version == PRODUCER_VERSION
    assert producer.descriptor.deterministic is True
    assert producer.descriptor.supports_relationships is False
    assert producer.descriptor.input_fields == ("faces", "keywords", "oracle_text")
    assert result.status is ProducerResultStatusV1.EMITTED
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.family is rule.output_template.family
    assert candidate.kind is rule.output_template.kind
    assert candidate.parameters.to_wire() == rule.output_template.parameters.to_wire()
    assert candidate.review.status is ReviewStatusV1.PROPOSED
    assert candidate.review.reviewed_by is None
    assert candidate.review.reviewed_claim_digest is None
    assert (
        candidate.provenance.derivations[0].method
        is DerivationMethodV1.DETERMINISTIC_RULE
    )
    assert candidate.provenance.derivations[0].producer_id == PRODUCER_ID
    assert candidate.provenance.derivations[0].producer_version == PRODUCER_VERSION
    assert isinstance(candidate.evidence[0], StructuralFieldEvidenceV1)
    assert candidate.evidence[0].field == "oracle_text"
    assert candidate.evidence[0].fragment == rule.match_text
    assert result.relationship_proposals == ()
    assert result.negative_authority is None
    assert result.findings[0].candidate_index == 0
    assert result.findings[0].pattern_id == rule.pattern_id
    assert result.findings[0].pattern_version == rule.pattern_version
    assert result.findings[0].pattern_digest == pattern_rule_digest_for(rule)
    assert result.findings[0].source_field is PatternSourceFieldV1.ORACLE_TEXT
    assert result.findings[0].face_index is None
    assert result.findings[0].exact_fragment == rule.match_text


def test_matching_does_not_depend_on_card_name_or_source_identity() -> None:
    rule = _fixture_rule()
    registry = _registry(rule)
    producer = _producer(registry)
    other_record = replace(
        structural_record(oracle_id=OTHER_ORACLE_ID),
        name="Different card name",
    )

    result = execute_producer(producer, other_record, _producer_context(registry))

    assert result.status is ProducerResultStatusV1.EMITTED
    assert result.candidates[0].source.oracle_id == OTHER_ORACLE_ID


def test_exact_field_text_requires_exact_parent_field_equality() -> None:
    rule = replace(
        _fixture_rule(),
        pattern_id="m3.exact-field.draw",
        matcher_kind=MatcherKindV1.EXACT_FIELD_TEXT,
        evidence_policy=EvidencePolicyV1.EXACT_FIELD,
    )
    registry = _registry(rule)
    result = execute_producer(
        _producer(registry), structural_record(), _producer_context(registry)
    )

    assert result.status is ProducerResultStatusV1.EMITTED
    assert result.findings[0].exact_fragment is None
    assert result.candidates[0].evidence[0].fragment is None

    nonmatching_record = replace(structural_record(), oracle_text="Draw two cards now.")
    no_match = execute_producer(
        _producer(registry), nonmatching_record, _producer_context(registry)
    )
    assert no_match.status is ProducerResultStatusV1.NO_MATCH


def test_exact_field_text_emits_keyword_evidence() -> None:
    rule = replace(
        _fixture_rule(),
        pattern_id="m3.exact-field.keyword",
        matcher_kind=MatcherKindV1.EXACT_FIELD_TEXT,
        source_scope=PatternSourceScopeV1(PatternSourceFieldV1.KEYWORDS, None),
        match_text="Flying",
        evidence_policy=EvidencePolicyV1.EXACT_FIELD,
    )
    registry = _registry(rule)
    result = execute_producer(
        _producer(registry), structural_record(), _producer_context(registry)
    )

    assert result.status is ProducerResultStatusV1.EMITTED
    evidence = result.candidates[0].evidence[0]
    assert isinstance(evidence, StructuralKeywordEvidenceV1)
    assert evidence.keyword_index == 0
    assert evidence.keyword_value == "Flying"
    assert result.findings[0].source_field is PatternSourceFieldV1.KEYWORDS
    assert result.findings[0].exact_fragment is None


def test_exact_face_field_text_uses_only_requested_face() -> None:
    rule = replace(
        _fixture_rule(),
        pattern_id="m3.exact-face.draw",
        matcher_kind=MatcherKindV1.EXACT_FACE_FIELD_TEXT,
        source_scope=PatternSourceScopeV1(PatternSourceFieldV1.ORACLE_TEXT, 1),
        evidence_policy=EvidencePolicyV1.EXACT_FIELD,
    )
    face_zero = StructuralFaceV1(
        face_index=0,
        name="Front",
        mana_cost=None,
        type_line="Creature",
        oracle_text="Other text.",
        colors=None,
        color_indicator=None,
        power=None,
        toughness=None,
        loyalty=None,
        defense=None,
    )
    face_one = replace(
        face_zero, face_index=1, name="Back", oracle_text=rule.match_text
    )
    record = replace(structural_record(), oracle_text=None, faces=(face_zero, face_one))
    registry = _registry(rule)
    result = execute_producer(_producer(registry), record, _producer_context(registry))

    assert result.status is ProducerResultStatusV1.EMITTED
    evidence = result.candidates[0].evidence[0]
    assert isinstance(evidence, StructuralFieldEvidenceV1)
    assert evidence.field == "oracle_text"
    assert evidence.face_index == 1
    assert result.findings[0].face_index == 1


def test_ineligible_rule_is_not_activated_and_returns_no_match() -> None:
    rule = _fixture_rule()
    registry = _registry(rule, states=(PatternEligibilityStateV1.NOT_ELIGIBLE,))
    result = execute_producer(
        _producer(registry), structural_record(), _producer_context(registry)
    )

    assert result.status is ProducerResultStatusV1.NO_MATCH
    assert result.candidates == ()
    assert result.findings == ()


def test_multiple_matches_follow_canonical_registry_order() -> None:
    first = replace(_fixture_rule(), pattern_id="m3.pattern.a", match_text="Draw")
    second = replace(
        _fixture_rule(), pattern_id="m3.pattern.b", match_text="two cards."
    )
    registry = _registry(first, second)
    result = execute_producer(
        _producer(registry), structural_record(), _producer_context(registry)
    )

    assert [item.pattern_id for item in result.findings] == [
        "m3.pattern.a",
        "m3.pattern.b",
    ]
    assert [item.candidate_index for item in result.findings] == [0, 1]
    assert [item.exact_fragment for item in result.findings] == [
        "Draw",
        "two cards.",
    ]


def test_registry_digest_mismatch_is_rejected_before_producer_execution() -> None:
    declared = _registry(_fixture_rule())
    actual_rule = replace(_fixture_rule(), pattern_id="m3.other-rule")
    actual = _registry(actual_rule)
    producer = _producer(declared)

    with pytest.raises(ProducerContractError, match="pattern_registry_digest"):
        execute_producer(producer, structural_record(), _producer_context(actual))


@pytest.mark.parametrize(
    "mutation",
    [
        lambda rule: replace(rule, producer_id="m3.other-producer"),
        lambda rule: replace(rule, producer_version="2"),
    ],
)
def test_rule_producer_binding_mismatch_fails_closed(mutation) -> None:
    registry = _registry(mutation(_fixture_rule()))
    with pytest.raises(ProducerExecutionError, match="producer"):
        execute_producer(
            _producer(registry), structural_record(), _producer_context(registry)
        )


def test_malformed_pattern_snapshot_fails_closed_as_unsupported_shape() -> None:
    registry = _registry(_fixture_rule())
    wire = registry.to_wire()
    wire["rules"][0]["matcher_kind"] = "EXACT_FACE_FIELD_TEXT"
    snapshot = ImmutableRegistrySnapshotV1.from_wire(
        "pattern",
        "census.pattern-registry.v1",
        PATTERN_REGISTRY_DIGEST_DOMAIN,
        wire,
    )
    context = _context_for_snapshot(snapshot)
    from manafold_census.analysis.pattern_producer import (
        RegistryDrivenExactPatternProducerV1,
    )

    with pytest.raises(ProducerExecutionError, match="producer failed"):
        execute_producer(
            RegistryDrivenExactPatternProducerV1(
                pattern_registry_digest=snapshot.digest
            ),
            structural_record(),
            context,
        )


def test_producer_module_has_no_dynamic_or_external_execution_imports() -> None:
    source_path = (
        Path(__file__).parents[1]
        / "src"
        / "manafold_census"
        / "analysis"
        / "pattern_producer.py"
    )
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imported_roots = set()
    forbidden_calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".", 1)[0])
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                forbidden_calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                forbidden_calls.add(node.func.attr)
    assert not imported_roots.intersection(
        {
            "pickle",
            "subprocess",
            "importlib",
            "random",
            "datetime",
            "time",
            "requests",
            "urllib",
            "socket",
            "openai",
        }
    )
    assert not forbidden_calls.intersection({"eval", "exec", "compile", "__import__"})
