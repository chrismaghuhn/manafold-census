"""Deterministic M4 Capability family identity helpers."""

from __future__ import annotations

from ..digest import domain_digest
from .model import CapabilityFamilyKeyV1

FAMILY_ID_DOMAIN = "census.capability-family-id.v1"
FAMILY_ID_PREFIX = "capfam_"


def capability_family_id_for(key: CapabilityFamilyKeyV1) -> str:
    """Return the stable identity of one validated Capability nucleus."""

    if not isinstance(key, CapabilityFamilyKeyV1):
        raise TypeError("key must be CapabilityFamilyKeyV1")
    return FAMILY_ID_PREFIX + domain_digest(FAMILY_ID_DOMAIN, key.to_wire())


__all__ = [
    "FAMILY_ID_DOMAIN",
    "FAMILY_ID_PREFIX",
    "capability_family_id_for",
]
