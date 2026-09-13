from __future__ import annotations

import hashlib
import json
from pathlib import Path

from analysis_fixtures import source_lock_digest, structural_record
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from manafold_census.analysis.patterns import (
    PATTERN_REGISTRY_DIGEST_DOMAIN,
    EffectivePatternRegistryV1,
)
from manafold_census.analysis.producer import (
    ImmutableRegistrySnapshotV1,
    ProducerContextV1,
    ProducerResultStatusV1,
    execute_producer,
)
from manafold_census.canonical import canonical_json_bytes
from manafold_census.resources import project_data_root

PROPOSAL_RECORD_ID = "m3.corpus.pattern-proposal.draw-two-cards.v1"
DECISION_RECORD_ID = "m3.corpus.pattern-decision.draw-two-cards.v1"
EXPECTED_PROPOSAL_SHA256 = (
    "f963d6ae37a6895458da2ed40b606d3d5f52f2f9daea97d6033c417fbbf478cb"
)
EXPECTED_RULE_DIGEST = (
    "d4ef898620fb9d2e794390a545d08b9c9cb90a238af83fc7fd6e76900d0023a9"
)
EXPECTED_REGISTRY_DIGEST = (
    "1f7f2189aaa9e2fa12b9e76f9da57ff7c57a4cd53a553b3de60287a31cd8cbaa"
)
EXPECTED_DECISION_SHA256 = (
    "89b73bb76d2a54bd847a322519a12a43b0e9736361f307771598b2225e67fd07"
)
EXPECTED_POST_DECISION_REGISTRY_DIGEST = (
    "097973ee6ae59b06d868eaac8e1947dc66e519fca78432b3f79a650e2d4e21c1"
)


def _analysis_config_root() -> Path:
    return project_data_root() / "config" / "analysis"


def _proposal_path() -> Path:
    return _analysis_config_root() / "m3-corpus-pattern-proposal.v1.json"


def _registry_path() -> Path:
    return _analysis_config_root() / "m3-corpus-pattern-registry.v1.json"


def _decision_path() -> Path:
    return _analysis_config_root() / "m3-corpus-pattern-decision.v1.json"


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_bytes())


def _validate_pattern_registry_schema(document: dict[str, object]) -> None:
    root = project_data_root()
    schema = _read_json(root / "schemas" / "pattern-registry.v1.schema.json")
    requirement = _read_json(root / "schemas" / "semantic-requirement.v1.schema.json")
    schema_id = requirement["$id"]
    assert isinstance(schema_id, str)
    registry = Registry().with_resource(
        schema_id,
        Resource.from_contents(requirement, default_specification=DRAFT202012),
    )
    Draft202012Validator(schema, registry=registry).validate(document)


def _context_for_registry(registry: EffectivePatternRegistryV1) -> ProducerContextV1:
    pattern_snapshot = ImmutableRegistrySnapshotV1.from_wire(
        "pattern",
        "census.pattern-registry.v1",
        PATTERN_REGISTRY_DIGEST_DOMAIN,
        registry.to_wire(),
    )
    producer_snapshot = ImmutableRegistrySnapshotV1.from_wire(
        "producer",
        "census.producer-registry.v1",
        "census.test-registry.v1",
        {"schema": "census.producer-registry.v1", "producers": []},
    )
    return ProducerContextV1(
        source_lock_digest=source_lock_digest(),
        m2_requirement_schema="census.semantic-requirement.v1",
        m2_bundle_schema="census.semantic-requirement-bundle.v1",
        producer_registry=producer_snapshot,
        pattern_registry=pattern_snapshot,
    )


def test_proposal_record_is_closed_and_canonical() -> None:
    path = _proposal_path()
    document = _read_json(path)

    assert set(document) == {
        "known_false_negative_scope",
        "known_false_positive_risk",
        "match_text",
        "matcher_kind",
        "m2_contract_version",
        "normalization_profile",
        "output_template",
        "pattern_id",
        "pattern_version",
        "producer_id",
        "producer_version",
        "record_id",
        "record_version",
        "source_scope",
        "status",
        "evidence_policy",
    }
    assert path.read_bytes() == canonical_json_bytes(document)
    assert document["record_id"] == PROPOSAL_RECORD_ID
    assert document["record_version"] == 1
    assert document["status"] == "PROPOSAL_ONLY"
    assert "registry_digest" not in document
    assert all(
        forbidden not in json.dumps(document)
        for forbidden in ("APPROVED", "ACCEPTED", "REVIEWED_FOR_REUSE")
    )


def test_decision_record_is_closed_canonical_and_rejects_reuse() -> None:
    path = _decision_path()
    document = _read_json(path)

    assert set(document) == {
        "decision",
        "decision_reason",
        "pattern_id",
        "pattern_version",
        "proposal_record_id",
        "proposal_record_sha256",
        "record_id",
        "record_version",
        "reviewer_role",
    }
    assert path.read_bytes() == canonical_json_bytes(document)
    assert document["record_id"] == DECISION_RECORD_ID
    assert document["record_version"] == 1
    assert document["decision"] == "REJECT_FOR_REUSE"
    assert document["reviewer_role"] == "MAINTAINER"
    assert document["proposal_record_id"] == PROPOSAL_RECORD_ID
    assert document["proposal_record_sha256"] == EXPECTED_PROPOSAL_SHA256
    assert document["pattern_id"] == "m3.corpus.exact-clause.draw-two-cards"
    assert document["pattern_version"] == "1"
    assert "effective_registry_digest" not in document
    assert "EXACT_FRAGMENT" in str(document["decision_reason"])
    assert "context" in str(document["decision_reason"])


def test_corpus_registry_is_canonical_schema_valid_and_not_fixture_authority() -> None:
    root = project_data_root()
    registry_path = _registry_path()
    document = _read_json(registry_path)
    registry = EffectivePatternRegistryV1.from_wire(document)

    assert registry_path.parent == root / "config" / "analysis"
    assert "fixtures" not in registry_path.parts
    assert registry_path.read_bytes() == canonical_json_bytes(document)
    _validate_pattern_registry_schema(document)
    assert len(registry.rules) == 1
    assert len(registry.eligibility) == 1
    assert all(
        item.review_record_id != "fixture-pattern-review"
        for item in registry.eligibility
    )
    assert registry.rules[0].pattern_id != "m3.exact-clause.draw"
    assert registry.eligibility[0].review_record_sha256 != "d" * 64


def test_corpus_rule_and_typed_draw_output_are_exact() -> None:
    registry = EffectivePatternRegistryV1.from_wire(_read_json(_registry_path()))
    rule = registry.rules[0]
    parameters = rule.output_template.parameters.to_wire()

    assert rule.pattern_id == "m3.corpus.exact-clause.draw-two-cards"
    assert rule.pattern_version == "1"
    assert rule.matcher_kind.value == "EXACT_FRAGMENT"
    assert rule.normalization_profile.value == "NONE"
    assert rule.source_scope.field.value == "oracle_text"
    assert rule.source_scope.face_index is None
    assert rule.match_text == "Draw two cards."
    assert rule.evidence_policy.value == "EXACT_FRAGMENT"
    assert rule.output_template.family.value == "effect"
    assert rule.output_template.kind.value == "draw_cards"
    assert parameters == {
        "drawer": {"role": "source", "multiplicity": "one", "ordinal": None},
        "quantity": {"mode": "exact", "value": 2},
    }
    assert rule.producer_id == "m3.registry-exact-pattern"
    assert rule.producer_version == "1"
    assert rule.m2_contract_version == "census.semantic-requirement.v1"


def test_decision_sha_is_the_registry_binding_and_rule_digest_is_unchanged() -> None:
    proposal_bytes = _proposal_path().read_bytes()
    proposal_sha = hashlib.sha256(proposal_bytes).hexdigest()
    decision_bytes = _decision_path().read_bytes()
    decision_sha = hashlib.sha256(decision_bytes).hexdigest()
    registry = EffectivePatternRegistryV1.from_wire(_read_json(_registry_path()))
    eligibility = registry.eligibility[0]

    assert proposal_sha == EXPECTED_PROPOSAL_SHA256
    assert decision_sha == EXPECTED_DECISION_SHA256
    assert registry.rules[0].pattern_id == eligibility.pattern_id
    assert eligibility.eligibility.value == "NOT_ELIGIBLE"
    assert eligibility.review_record_id == DECISION_RECORD_ID
    assert eligibility.review_record_sha256 == decision_sha
    assert registry.rules[0].pattern_id == "m3.corpus.exact-clause.draw-two-cards"
    from manafold_census.analysis.patterns import pattern_rule_digest_for

    assert pattern_rule_digest_for(registry.rules[0]) == EXPECTED_RULE_DIGEST
    assert registry.digest() == EXPECTED_POST_DECISION_REGISTRY_DIGEST


def test_proposed_corpus_rule_is_not_activated_by_registry_configuration() -> None:
    registry = EffectivePatternRegistryV1.from_wire(_read_json(_registry_path()))
    from manafold_census.analysis.pattern_producer import (
        RegistryDrivenExactPatternProducerV1,
    )

    producer = RegistryDrivenExactPatternProducerV1(
        pattern_registry_digest=registry.digest()
    )
    result = execute_producer(
        producer,
        structural_record(),
        _context_for_registry(registry),
    )

    assert result.status is ProducerResultStatusV1.NO_MATCH
    assert result.candidates == ()
    assert result.findings == ()


def test_review_packet_records_pending_authority_and_exact_fragment_risk() -> None:
    packet = (
        project_data_root()
        / "docs"
        / "reports"
        / "2026-09-13-m3-corpus-pattern-review.md"
    ).read_text(encoding="utf-8")

    assert "MAINTAINER_DECISION = PENDING" in packet
    assert "ELIGIBILITY         = NOT_ELIGIBLE" in packet
    assert "CORPUS_AUTHORITY    = NOT_ESTABLISHED" in packet
    assert 'EXACT_FRAGMENT("Draw two cards.")' in packet
    assert "conditional" in packet
    assert "triggered" in packet
    assert "modal" in packet
    assert "replacement" in packet


def test_decision_report_records_rejection_without_establishing_authority() -> None:
    report = (
        project_data_root()
        / "docs"
        / "reports"
        / "2026-09-14-m3-corpus-pattern-decision.md"
    ).read_text(encoding="utf-8")

    assert "DECISION   = REJECT_FOR_REUSE" in report
    assert "ELIGIBILITY = NOT_ELIGIBLE" in report
    assert "CORPUS_AUTHORITY_ESTABLISHED = NO" in report
    assert "TASK_11_RETRY_ALLOWED        = NO" in report
    assert "proposal validity = PASS" in report
    assert "reuse approval     = REJECTED" in report
