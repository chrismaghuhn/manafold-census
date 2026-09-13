from __future__ import annotations

import pytest
from analysis_fixtures import (
    accepted_requirement,
    bundle,
    source_lock_digest,
    structural_record,
)

from manafold_census.analysis.patterns import PatternSourceFieldV1
from manafold_census.analysis.producer import (
    ImmutableRegistrySnapshotV1,
    ProducerContextV1,
    ProducerContractError,
    ProducerDescriptorV1,
    ProducerExecutionError,
    ProducerFindingV1,
    ProducerResultStatusV1,
    ProducerResultV1,
    RelationshipProposalV1,
    execute_producer,
    validate_producer_candidate,
)
from manafold_census.digest import domain_digest
from manafold_census.semantic.bundle import (
    RelationshipTypeV1,
    RequirementRelationshipV1,
)
from manafold_census.semantic.model import DerivationMethodV1


def descriptor(
    producer_id: str,
    *,
    deterministic: bool = True,
    derivation_method: DerivationMethodV1 = DerivationMethodV1.DETERMINISTIC_RULE,
    supports_relationships: bool = False,
    pattern_registry_digest: str | None = None,
) -> ProducerDescriptorV1:
    return ProducerDescriptorV1(
        producer_id=producer_id,
        producer_version="1",
        derivation_method=derivation_method,
        input_schema="census.structural-card.v1",
        input_fields=("oracle_text",),
        pattern_registry_digest=pattern_registry_digest,
        deterministic=deterministic,
        supports_relationships=supports_relationships,
    )


def producer_context(
    *,
    pattern_registry: ImmutableRegistrySnapshotV1 | None = None,
) -> ProducerContextV1:
    return ProducerContextV1(
        source_lock_digest=source_lock_digest(),
        m2_requirement_schema="census.semantic-requirement.v1",
        m2_bundle_schema="census.semantic-requirement-bundle.v1",
        producer_registry=ImmutableRegistrySnapshotV1.from_wire(
            "producer",
            "census.producer-registry.v1",
            "census.test-registry.v1",
            {"schema": "census.producer-registry.v1", "producers": []},
        ),
        pattern_registry=pattern_registry,
    )


def test_producer_candidate_with_terminal_review_is_invalid() -> None:
    with pytest.raises(ProducerContractError, match="PROPOSED"):
        validate_producer_candidate(
            accepted_requirement(),
            structural_record(),
            source_lock_digest(),
        )


def test_no_match_is_not_a_negative_card_result() -> None:
    result = ProducerResultV1.no_match()
    assert result.status is ProducerResultStatusV1.NO_MATCH
    assert result.candidates == ()
    assert result.negative_authority is None


def test_unsupported_shape_is_explicit_and_has_no_candidates() -> None:
    result = ProducerResultV1.unsupported_shape("nested choice")
    assert result.status is ProducerResultStatusV1.UNSUPPORTED_SHAPE
    assert result.candidates == ()
    assert result.unresolved_reason == "nested choice"


def test_emitted_result_requires_a_proposed_requirement() -> None:
    proposal = bundle().requirements[0]
    result = ProducerResultV1.emitted((proposal,))
    assert result.status is ProducerResultStatusV1.EMITTED
    assert result.candidates == (proposal,)


def test_emitted_result_carries_typed_pattern_finding() -> None:
    proposal = bundle().requirements[0]
    finding = ProducerFindingV1(
        candidate_index=0,
        pattern_id="fixture.pattern",
        pattern_version="1",
        pattern_digest="d" * 64,
        source_field=PatternSourceFieldV1.ORACLE_TEXT,
        face_index=None,
        exact_fragment="Draw two cards.",
        clause_ordinal=0,
        parser_span=None,
    )
    result = ProducerResultV1.emitted((proposal,), findings=(finding,))
    assert result.findings == (finding,)


def test_producer_exception_is_not_a_no_match_result() -> None:
    class RaisingProducer:
        descriptor = descriptor("m3.raising")

        def produce(self, record, context):
            raise RuntimeError("boom")

    with pytest.raises(ProducerExecutionError, match="producer failed"):
        execute_producer(
            RaisingProducer(),
            structural_record(),
            ProducerContextV1(
                source_lock_digest=source_lock_digest(),
                m2_requirement_schema="census.semantic-requirement.v1",
                m2_bundle_schema="census.semantic-requirement-bundle.v1",
                producer_registry=ImmutableRegistrySnapshotV1.from_wire(
                    "producer",
                    "census.producer-registry.v1",
                    "census.test-registry.v1",
                    {"schema": "census.producer-registry.v1", "producers": []},
                ),
                pattern_registry=None,
            ),
        )


def test_context_carries_immutable_registry_snapshots() -> None:
    producer_snapshot = ImmutableRegistrySnapshotV1.from_wire(
        "producer",
        "census.producer-registry.v1",
        "census.test-registry.v1",
        {"schema": "census.producer-registry.v1", "producers": []},
    )
    pattern_snapshot = ImmutableRegistrySnapshotV1.from_wire(
        "pattern",
        "census.pattern-registry.v1",
        "census.test-pattern-registry.v1",
        {"schema": "census.pattern-registry.v1", "rules": []},
    )
    context = ProducerContextV1(
        source_lock_digest=source_lock_digest(),
        m2_requirement_schema="census.semantic-requirement.v1",
        m2_bundle_schema="census.semantic-requirement-bundle.v1",
        producer_registry=producer_snapshot,
        pattern_registry=pattern_snapshot,
    )
    assert context.producer_registry is producer_snapshot
    assert context.pattern_registry is pattern_snapshot
    assert context.producer_registry_digest == producer_snapshot.digest
    with pytest.raises(TypeError):
        producer_snapshot.wire["mutated"] = True  # type: ignore[index]


def test_direct_snapshot_construction_defensively_freezes_mutable_wire() -> None:
    wire = {"schema": "census.producer-registry.v1", "producers": []}
    digest_domain_name = "census.test-registry.v1"
    snapshot = ImmutableRegistrySnapshotV1(
        registry_kind="producer",
        registry_schema="census.producer-registry.v1",
        digest_domain=digest_domain_name,
        digest=domain_digest(digest_domain_name, wire),
        wire=wire,
    )
    wire["producers"].append({"mutated": True})
    assert snapshot.to_wire() == {
        "schema": "census.producer-registry.v1",
        "producers": [],
    }


def test_relationship_proposals_require_descriptor_support() -> None:
    proposal = bundle().requirements[0]
    relationship = RelationshipProposalV1(
        RequirementRelationshipV1(
            RelationshipTypeV1.PARENT_OF,
            proposal.requirement_id,
            proposal.requirement_id,
            None,
        )
    )

    class RelationshipProducer:
        descriptor = descriptor("m3.relationship", supports_relationships=False)

        def produce(self, record, context):
            return ProducerResultV1.emitted((proposal,), (relationship,))

    with pytest.raises(ProducerContractError, match="supports_relationships"):
        execute_producer(
            RelationshipProducer(),
            structural_record(),
            producer_context(),
        )


def test_pattern_descriptor_requires_context_snapshot() -> None:
    pattern = ImmutableRegistrySnapshotV1.from_wire(
        "pattern",
        "census.pattern-registry.v1",
        "census.test-pattern-registry.v1",
        {"schema": "census.pattern-registry.v1", "rules": []},
    )

    class ProbeProducer:
        descriptor = descriptor(
            "m3.pattern-dependent",
            pattern_registry_digest=pattern.digest,
        )
        called = False

        def produce(self, record, context):
            self.called = True
            return ProducerResultV1.no_match()

    producer = ProbeProducer()
    with pytest.raises(ProducerContractError, match="pattern_registry"):
        execute_producer(
            producer,
            structural_record(),
            producer_context(pattern_registry=None),
        )
    assert producer.called is False


def test_pattern_descriptor_rejects_context_digest_mismatch() -> None:
    declared = ImmutableRegistrySnapshotV1.from_wire(
        "pattern",
        "census.pattern-registry.v1",
        "census.test-pattern-registry.v1",
        {"schema": "census.pattern-registry.v1", "rules": []},
    )
    actual = ImmutableRegistrySnapshotV1.from_wire(
        "pattern",
        "census.pattern-registry.v1",
        "census.test-pattern-registry.v1",
        {"schema": "census.pattern-registry.v1", "rules": [{"id": "other"}]},
    )

    class ProbeProducer:
        descriptor = descriptor(
            "m3.pattern-dependent",
            pattern_registry_digest=declared.digest,
        )
        called = False

        def produce(self, record, context):
            self.called = True
            return ProducerResultV1.no_match()

    producer = ProbeProducer()
    with pytest.raises(ProducerContractError, match="digest"):
        execute_producer(
            producer,
            structural_record(),
            producer_context(pattern_registry=actual),
        )
    assert producer.called is False


def test_pattern_descriptor_matching_context_is_allowed() -> None:
    pattern = ImmutableRegistrySnapshotV1.from_wire(
        "pattern",
        "census.pattern-registry.v1",
        "census.test-pattern-registry.v1",
        {"schema": "census.pattern-registry.v1", "rules": []},
    )

    class ProbeProducer:
        descriptor = descriptor(
            "m3.pattern-dependent",
            pattern_registry_digest=pattern.digest,
        )
        called = False

        def produce(self, record, context):
            self.called = True
            return ProducerResultV1.no_match()

    producer = ProbeProducer()
    assert (
        execute_producer(
            producer,
            structural_record(),
            producer_context(pattern_registry=pattern),
        ).status
        is ProducerResultStatusV1.NO_MATCH
    )
    assert producer.called is True


def test_invalid_descriptor_is_rejected_before_producer_call() -> None:
    class InvalidProducer:
        called = False

        def produce(self, record, context):
            self.called = True
            return ProducerResultV1.no_match()

    producer = InvalidProducer()
    with pytest.raises(ProducerContractError, match="Descriptor"):
        execute_producer(producer, structural_record(), producer_context())
    assert producer.called is False
