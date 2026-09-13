from __future__ import annotations

import pytest
from analysis_fixtures import (
    accepted_requirement,
    bundle,
    source_lock_digest,
    structural_record,
)

from manafold_census.analysis.producer import (
    ProducerContextV1,
    ProducerContractError,
    ProducerDescriptorV1,
    ProducerExecutionError,
    ProducerResultStatusV1,
    ProducerResultV1,
    execute_producer,
    validate_producer_candidate,
)
from manafold_census.digest import domain_digest
from manafold_census.semantic.model import DerivationMethodV1


def descriptor(
    producer_id: str,
    *,
    deterministic: bool = True,
) -> ProducerDescriptorV1:
    return ProducerDescriptorV1(
        producer_id=producer_id,
        producer_version="1",
        derivation_method=DerivationMethodV1.DETERMINISTIC_RULE,
        input_schema="census.structural-card.v1",
        input_fields=("oracle_text",),
        pattern_registry_digest=None,
        deterministic=deterministic,
        supports_relationships=False,
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
                producer_registry_digest=domain_digest(
                    "census.test-registry.v1",
                    {"producer": "m3.raising"},
                ),
                pattern_registry_digest=None,
            ),
        )
