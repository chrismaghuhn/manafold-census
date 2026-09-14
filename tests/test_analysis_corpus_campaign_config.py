from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

from analysis_fixtures import structural_record

from manafold_census.analysis.pattern_producer import (
    RegistryDrivenExactPatternProducerV1,
)
from manafold_census.analysis.patterns import (
    EffectivePatternRegistryV1,
    PatternEligibilityStateV1,
    pattern_rule_digest_for,
)
from manafold_census.analysis.producer import (
    ProducerResultStatusV1,
    execute_producer,
)
from manafold_census.analysis.registry import ProducerRegistryV1
from manafold_census.resources import project_data_root
from manafold_census.semantic.evidence import StructuralFieldEvidenceV1
from manafold_census.semantic.kinds import RequirementKindV1
from manafold_census.semantic.model import ReviewStatusV1
from manafold_census.validation import validate_document

APPROVAL_RECORD_ID = "m3.corpus.pattern-decision.draw-two-cards-exact-field.v1"
PROPOSAL_RECORD_ID = "m3.corpus.pattern-proposal.draw-two-cards-exact-field.v1"
EXPECTED_PROPOSAL_SHA256 = (
    "04d659d2e21e3b2333efc4d5bd974f46119fe128e20ec5cebcb3aa894b00897f"
)
EXPECTED_MATCH_CENSUS_SHA256 = (
    "6795a7bbd1e9340589a0b182d129c8ad67dd8fdf376dd5a6935b6a2b9c274d89"
)
EXPECTED_PATTERN_RULE_DIGEST = (
    "b97740ed2d63e8b23e1a2e6fec5ed340d9b223078ca6d728e9feb279e2a7a32c"
)
EXPECTED_PATTERN_REGISTRY_DIGEST = (
    "a27effa3d7f5497fca0d9d2e3e3abb562037278b17cf7b17b0f54523d58e5eb1"
)
EXPECTED_APPROVAL_SHA256 = (
    "a393c3c4bf91bf03469075ce5ad372edb79249cdb30e43d3b59f7d90053485fe"
)
EXPECTED_PRODUCER_REGISTRY_DIGEST = (
    "fca4a0d9318669a372ee1dcded22c55e1fd1fdff7dd470ecd0bbfa9c07be498f"
)


def _root() -> Path:
    return project_data_root()


def _config() -> Path:
    return _root() / "config" / "analysis"


def _read(path: Path) -> dict[str, object]:
    return json.loads(path.read_bytes())


def _pattern_registry() -> EffectivePatternRegistryV1:
    return EffectivePatternRegistryV1.from_wire(
        _read(_config() / "m3-corpus-pattern-registry.v1.json")
    )


def test_approval_decision_is_canonical_and_binds_match_census() -> None:
    path = _config() / "m3-corpus-pattern-decision-draw-two-exact-field.v1.json"
    document = _read(path)

    from manafold_census.canonical import canonical_json_bytes

    assert path.read_bytes() == canonical_json_bytes(document)
    assert document["record_id"] == APPROVAL_RECORD_ID
    assert document["record_version"] == 1
    assert document["decision"] == "APPROVE_FOR_REUSE"
    assert document["reviewer_role"] == "MAINTAINER"
    assert document["proposal_record_id"] == PROPOSAL_RECORD_ID
    assert document["proposal_record_sha256"] == EXPECTED_PROPOSAL_SHA256
    assert document["pattern_id"] == "m3.corpus.exact-field.draw-two-cards"
    assert document["pattern_version"] == "1"
    assert document["match_census_sha256"] == EXPECTED_MATCH_CENSUS_SHA256
    assert document["match_count"] == 5
    assert "pattern_registry_digest" not in document
    assert "producer_registry_digest" not in document
    assert hashlib.sha256(path.read_bytes()).hexdigest() == EXPECTED_APPROVAL_SHA256


def test_approved_pattern_registry_is_pinned_and_old_fragment_remains_rejected() -> (
    None
):
    registry = _pattern_registry()
    from test_analysis_corpus_pattern_registry import _validate_pattern_registry_schema

    _validate_pattern_registry_schema(registry.to_wire())

    old_rule = next(
        rule
        for rule in registry.rules
        if rule.pattern_id == "m3.corpus.exact-clause.draw-two-cards"
    )
    new_rule = next(
        rule
        for rule in registry.rules
        if rule.pattern_id == "m3.corpus.exact-field.draw-two-cards"
    )
    old_eligibility = next(
        item for item in registry.eligibility if item.pattern_id == old_rule.pattern_id
    )
    new_eligibility = next(
        item for item in registry.eligibility if item.pattern_id == new_rule.pattern_id
    )

    assert old_eligibility.eligibility is PatternEligibilityStateV1.NOT_ELIGIBLE
    assert old_eligibility.review_record_id == (
        "m3.corpus.pattern-decision.draw-two-cards.v1"
    )
    assert old_eligibility.review_record_sha256 == (
        "89b73bb76d2a54bd847a322519a12a43b0e9736361f307771598b2225e67fd07"
    )
    assert pattern_rule_digest_for(old_rule) == (
        "d4ef898620fb9d2e794390a545d08b9c9cb90a238af83fc7fd6e76900d0023a9"
    )
    assert new_eligibility.eligibility is PatternEligibilityStateV1.REVIEWED_FOR_REUSE
    assert new_eligibility.review_record_id == APPROVAL_RECORD_ID
    assert new_eligibility.review_record_sha256 == EXPECTED_APPROVAL_SHA256
    assert pattern_rule_digest_for(new_rule) == EXPECTED_PATTERN_RULE_DIGEST
    assert registry.digest() == EXPECTED_PATTERN_REGISTRY_DIGEST


def test_producer_registry_is_authoritative_and_matches_implementation() -> None:
    path = _config() / "m3-corpus-producer-registry.v1.json"
    document = _read(path)
    validate_document(document, "producer-registry.v1.schema.json")
    registry = ProducerRegistryV1.from_wire(document)
    authoritative = registry.for_authoritative_run()
    producer = RegistryDrivenExactPatternProducerV1(
        pattern_registry_digest=EXPECTED_PATTERN_REGISTRY_DIGEST
    )

    assert authoritative == registry
    assert len(registry.producers) == 1
    assert registry.producers[0] == producer.descriptor
    assert registry.digest() == EXPECTED_PRODUCER_REGISTRY_DIGEST


def test_approved_producer_emits_one_proposed_draw_candidate() -> None:
    registry = _pattern_registry()
    producer = RegistryDrivenExactPatternProducerV1(
        pattern_registry_digest=registry.digest()
    )
    from test_analysis_corpus_pattern_registry import _context_for_registry

    result = execute_producer(
        producer,
        structural_record(),
        _context_for_registry(registry),
    )

    assert result.status is ProducerResultStatusV1.EMITTED
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.review.status is ReviewStatusV1.PROPOSED
    assert candidate.kind is RequirementKindV1.DRAW_CARDS
    assert candidate.parameters.to_wire() == {
        "drawer": {"multiplicity": "one", "ordinal": None, "role": "source"},
        "quantity": {"mode": "exact", "value": 2},
    }
    assert isinstance(candidate.evidence[0], StructuralFieldEvidenceV1)
    assert candidate.evidence[0].field == "oracle_text"
    assert candidate.evidence[0].face_index is None
    assert candidate.evidence[0].fragment is None
    assert result.findings[0].pattern_id == "m3.corpus.exact-field.draw-two-cards"
    assert result.relationship_proposals == ()
    assert result.negative_authority is None

    nonmatch = execute_producer(
        producer,
        replace(structural_record(), oracle_text="Other text."),
        _context_for_registry(registry),
    )
    assert nonmatch.status is ProducerResultStatusV1.NO_MATCH
    assert nonmatch.candidates == ()
    assert nonmatch.findings == ()


def test_campaign_report_records_frozen_inputs_without_claiming_certification() -> None:
    report = (
        _root() / "docs" / "reports" / "2026-09-14-m3-corpus-campaign-config.md"
    ).read_text(encoding="utf-8")

    assert "ACTIVE_REVIEWED_PATTERN_COUNT = 1" in report
    assert "m3.corpus.exact-field.draw-two-cards@1" in report
    assert "EXPECTED_EXACT_FIELD_M1_MATCH_COUNT = 5" in report
    assert "NONMATCH_WITHOUT_NEGATIVE_AUTHORITY" in report
    assert "UNRESOLVED_ANALYSIS" in report
    assert "5 cards certified" not in report
    assert "global semantic coverage" not in report
