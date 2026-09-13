"""Deterministic producer registry and authoritative-run admission."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from ..canonical import JSONValue
from ..digest import domain_digest
from ..semantic.model import DerivationMethodV1
from ..semantic.primitives import _require_object
from .producer import ProducerDescriptorV1

PRODUCER_REGISTRY_SCHEMA = "census.producer-registry.v1"
PRODUCER_REGISTRY_DIGEST_DOMAIN = "census.m3-producer-registry.v1"


class ProducerRegistryError(ValueError):
    """Raised when a producer registry is invalid or unsafe to activate."""


def _sort_key(descriptor: ProducerDescriptorV1) -> tuple[str, str]:
    return descriptor.producer_id, descriptor.producer_version


@dataclass(frozen=True, slots=True)
class ProducerRegistryV1:
    producers: tuple[ProducerDescriptorV1, ...]

    SCHEMA: ClassVar[str] = PRODUCER_REGISTRY_SCHEMA
    _WIRE_KEYS: ClassVar[set[str]] = {"schema", "producers"}

    def __post_init__(self) -> None:
        if not isinstance(self.producers, tuple | list):
            raise TypeError("producers must be a tuple or list")
        producers = tuple(self.producers)
        if not producers:
            raise ProducerRegistryError("producer registry must be non-empty")
        if any(not isinstance(item, ProducerDescriptorV1) for item in producers):
            raise TypeError("producers must contain ProducerDescriptorV1 values")
        keys = [_sort_key(item) for item in producers]
        if len(keys) != len(set(keys)):
            raise ProducerRegistryError("producer registry contains duplicate identity")
        if keys != sorted(keys):
            raise ProducerRegistryError("producer registry must be sorted")
        object.__setattr__(self, "producers", producers)

    @classmethod
    def build(
        cls,
        producers: tuple[ProducerDescriptorV1, ...] | list[ProducerDescriptorV1],
    ) -> ProducerRegistryV1:
        ordered = tuple(sorted(producers, key=_sort_key))
        return cls(ordered)

    def for_authoritative_run(self) -> ProducerRegistryV1:
        nondeterministic = [
            item.producer_id for item in self.producers if not item.deterministic
        ]
        if nondeterministic:
            raise ProducerRegistryError(
                "authoritative M3 registry requires deterministic producers: "
                + ", ".join(nondeterministic)
            )
        model_producers = [
            item.producer_id
            for item in self.producers
            if item.derivation_method is DerivationMethodV1.MODEL
        ]
        if model_producers:
            raise ProducerRegistryError(
                "authoritative M3 registry rejects MODEL producers until a "
                "pinned proposal importer contract exists: "
                + ", ".join(model_producers)
            )
        return self

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "schema": self.SCHEMA,
            "producers": [item.to_wire() for item in self.producers],
        }

    @classmethod
    def from_wire(cls, value: object) -> ProducerRegistryV1:
        document = _require_object(value, cls._WIRE_KEYS, "producer registry")
        if document["schema"] != cls.SCHEMA:
            raise ValueError(f"schema must be {cls.SCHEMA}")
        raw_producers = document["producers"]
        if not isinstance(raw_producers, list):
            raise TypeError("producers must be a JSON array")
        try:
            return cls(
                tuple(ProducerDescriptorV1.from_wire(item) for item in raw_producers)
            )
        except (TypeError, ValueError) as error:
            raise ProducerRegistryError(str(error)) from error

    def digest(self) -> str:
        return domain_digest(PRODUCER_REGISTRY_DIGEST_DOMAIN, self.to_wire())


__all__ = [
    "PRODUCER_REGISTRY_DIGEST_DOMAIN",
    "PRODUCER_REGISTRY_SCHEMA",
    "ProducerRegistryError",
    "ProducerRegistryV1",
]
