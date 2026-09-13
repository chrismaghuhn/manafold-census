from __future__ import annotations

import copy

import pytest

from manafold_census.analysis.producer import ProducerDescriptorV1
from manafold_census.analysis.registry import (
    ProducerRegistryError,
    ProducerRegistryV1,
)
from manafold_census.semantic.model import DerivationMethodV1
from manafold_census.validation import validate_document


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


def test_producer_descriptor_round_trips_and_registry_is_sorted() -> None:
    registry = ProducerRegistryV1.build(
        [descriptor("m3.parser"), descriptor("m3.exact-rule")]
    )
    assert [item.producer_id for item in registry.producers] == [
        "m3.exact-rule",
        "m3.parser",
    ]
    assert ProducerRegistryV1.from_wire(registry.to_wire()) == registry


def test_authoritative_registry_rejects_nondeterministic_active_producer() -> None:
    with pytest.raises(ProducerRegistryError, match="deterministic"):
        ProducerRegistryV1.build(
            [descriptor("m3.model", deterministic=False)]
        ).for_authoritative_run()


def test_registry_rejects_duplicate_descriptor_identity() -> None:
    with pytest.raises(ProducerRegistryError, match="duplicate"):
        ProducerRegistryV1.build([descriptor("m3.same"), descriptor("m3.same")])


def test_registry_wire_rejects_unsorted_producers_and_unknown_fields() -> None:
    registry = ProducerRegistryV1.build(
        [descriptor("m3.exact-rule"), descriptor("m3.parser")]
    )
    unsorted = copy.deepcopy(registry.to_wire())
    unsorted["producers"] = list(reversed(unsorted["producers"]))
    with pytest.raises(ValueError, match="sorted"):
        ProducerRegistryV1.from_wire(unsorted)

    unknown = copy.deepcopy(registry.to_wire())
    unknown["unexpected"] = True
    with pytest.raises((TypeError, ValueError), match="unexpected"):
        ProducerRegistryV1.from_wire(unknown)


def test_registry_schema_accepts_a_valid_registry() -> None:
    registry = ProducerRegistryV1.build([descriptor("m3.exact-rule")])
    validate_document(registry.to_wire(), "producer-registry.v1.schema.json")
