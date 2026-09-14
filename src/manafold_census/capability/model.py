"""Stable M4 Capability nucleus and exact Capability references."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, ClassVar, cast

from ..canonical import JSONValue
from ..semantic.kinds import (
    RequirementFamilyV1,
    RequirementKindV1,
    validate_kind_family,
)
from ..semantic.primitives import (
    SemanticShapeV1,
    _require_bool,
    _require_enum,
    _require_int,
    _require_object,
    _require_text,
)

if TYPE_CHECKING:
    from .dimensions import (
        CapabilityDimensionV1,
        DimensionDomainKindV1,
        M2DimensionPathV1,
    )

_FAMILY_ID_PATTERN = re.compile(r"^capfam_[0-9a-f]{64}$")
_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class NucleusKindV1(StrEnum):
    ATOMIC = "ATOMIC"
    COMPOSITE = "COMPOSITE"


def _anchor_values(
    value: object,
) -> tuple[tuple[RequirementFamilyV1, RequirementKindV1], ...]:
    if not isinstance(value, tuple | list):
        raise TypeError("operation_anchor must be a tuple or list")

    anchors: list[tuple[RequirementFamilyV1, RequirementKindV1]] = []
    for index, item in enumerate(value):
        if not isinstance(item, tuple | list) or len(item) != 2:
            raise TypeError(f"operation_anchor[{index}] must contain family and kind")
        family = _require_enum(
            f"operation_anchor[{index}].family",
            item[0],
            RequirementFamilyV1,
        )
        kind = _require_enum(
            f"operation_anchor[{index}].kind",
            item[1],
            RequirementKindV1,
        )
        validate_kind_family(family, kind)
        anchors.append((family, kind))

    return tuple(sorted(anchors, key=lambda item: (item[0].value, item[1].value)))


@dataclass(frozen=True, slots=True)
class CapabilityFamilyKeyV1:
    nucleus_contract_version: str
    nucleus_kind: NucleusKindV1
    operation_anchor: tuple[tuple[RequirementFamilyV1, RequirementKindV1], ...]

    SCHEMA: ClassVar[str] = "census.capability-family-key.v1"
    _WIRE_KEYS: ClassVar[set[str]] = {
        "family_key_schema",
        "nucleus_contract_version",
        "nucleus_kind",
        "operation_anchor",
    }

    def __post_init__(self) -> None:
        version = _require_text(
            "nucleus_contract_version",
            self.nucleus_contract_version,
        )
        nucleus_kind = _require_enum(
            "nucleus_kind",
            self.nucleus_kind,
            NucleusKindV1,
        )
        anchors = _anchor_values(self.operation_anchor)
        if not anchors:
            raise ValueError("operation_anchor must be non-empty")
        if len(anchors) != len(set(anchors)):
            raise ValueError("duplicate operation anchor")
        if nucleus_kind is NucleusKindV1.ATOMIC and len(anchors) != 1:
            raise ValueError("ATOMIC requires exactly one operation anchor")
        if nucleus_kind is NucleusKindV1.COMPOSITE and len(anchors) < 2:
            raise ValueError("COMPOSITE requires at least two operation anchors")

        object.__setattr__(self, "nucleus_contract_version", version)
        object.__setattr__(self, "nucleus_kind", nucleus_kind)
        object.__setattr__(self, "operation_anchor", anchors)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "family_key_schema": self.SCHEMA,
            "nucleus_contract_version": self.nucleus_contract_version,
            "nucleus_kind": self.nucleus_kind.value,
            "operation_anchor": [
                {"family": family.value, "kind": kind.value}
                for family, kind in self.operation_anchor
            ],
        }

    @classmethod
    def from_wire(cls, value: object) -> CapabilityFamilyKeyV1:
        document = _require_object(value, cls._WIRE_KEYS, "capability family key")
        schema = _require_text("family_key_schema", document["family_key_schema"])
        if schema != cls.SCHEMA:
            raise ValueError(f"family_key_schema must be {cls.SCHEMA}")

        raw_anchors = document["operation_anchor"]
        if not isinstance(raw_anchors, list):
            raise TypeError("operation_anchor must be a JSON array")

        anchors: list[tuple[RequirementFamilyV1, RequirementKindV1]] = []
        for index, item in enumerate(raw_anchors):
            anchor = _require_object(
                item,
                {"family", "kind"},
                f"operation_anchor[{index}]",
            )
            family = _require_enum(
                f"operation_anchor[{index}].family",
                anchor["family"],
                RequirementFamilyV1,
            )
            kind = _require_enum(
                f"operation_anchor[{index}].kind",
                anchor["kind"],
                RequirementKindV1,
            )
            validate_kind_family(family, kind)
            anchors.append((family, kind))

        result = cls(
            nucleus_contract_version=cast(
                str,
                document["nucleus_contract_version"],
            ),
            nucleus_kind=_require_enum(
                "nucleus_kind",
                document["nucleus_kind"],
                NucleusKindV1,
            ),
            operation_anchor=tuple(anchors),
        )
        if result.to_wire()["operation_anchor"] != raw_anchors:
            raise ValueError("operation_anchor must be in canonical order")
        return result


@dataclass(frozen=True, slots=True)
class CapabilityRefV1:
    capability_family_id: str
    capability_version: int
    claim_digest: str

    _WIRE_KEYS: ClassVar[set[str]] = {
        "capability_family_id",
        "capability_version",
        "claim_digest",
    }

    def __post_init__(self) -> None:
        family_id = _require_text("capability_family_id", self.capability_family_id)
        if _FAMILY_ID_PATTERN.fullmatch(family_id) is None:
            raise ValueError(
                "capability_family_id must be capfam_ plus a lowercase SHA-256 digest"
            )
        version = _require_int("capability_version", self.capability_version)
        if version < 1:
            raise ValueError("capability_version must be at least one")
        claim_digest = _require_text("claim_digest", self.claim_digest)
        if _DIGEST_PATTERN.fullmatch(claim_digest) is None:
            raise ValueError("claim_digest must be a lowercase SHA-256 digest")

        object.__setattr__(self, "capability_family_id", family_id)
        object.__setattr__(self, "capability_version", version)
        object.__setattr__(self, "claim_digest", claim_digest)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "capability_family_id": self.capability_family_id,
            "capability_version": self.capability_version,
            "claim_digest": self.claim_digest,
        }

    @classmethod
    def from_wire(cls, value: object) -> CapabilityRefV1:
        document = _require_object(value, cls._WIRE_KEYS, "capability reference")
        return cls(
            capability_family_id=cast(str, document["capability_family_id"]),
            capability_version=cast(int, document["capability_version"]),
            claim_digest=cast(str, document["claim_digest"]),
        )


def _values(value: object, field: str) -> tuple[object, ...]:
    if not isinstance(value, tuple | list):
        raise TypeError(f"{field} must be a tuple or list")
    return tuple(value)


def _wire_values(value: object, field: str) -> tuple[object, ...]:
    if not isinstance(value, list):
        raise TypeError(f"{field} must be a JSON array")
    return tuple(value)


@dataclass(frozen=True, slots=True)
class ExclusionV1:
    path_key: M2DimensionPathV1
    domain_kind: DimensionDomainKindV1
    excluded_enum_values: tuple[str, ...] = ()
    excluded_shapes: tuple[SemanticShapeV1, ...] = ()

    _WIRE_KEYS: ClassVar[set[str]] = {"path_key", "domain"}

    def __post_init__(self) -> None:
        from . import dimensions

        path_key = dimensions._path_key(self.path_key)
        domain_kind = _require_enum(
            "domain_kind", self.domain_kind, dimensions.DimensionDomainKindV1
        )
        enum_values = dimensions._strings(
            self.excluded_enum_values, "excluded_enum_values"
        )
        shapes = dimensions._shapes(self.excluded_shapes, "excluded_shapes")
        dimensions._validate_domain(
            path_key, domain_kind, enum_values, shapes, "exclusion domain"
        )
        object.__setattr__(self, "path_key", path_key)
        object.__setattr__(self, "domain_kind", domain_kind)
        object.__setattr__(self, "excluded_enum_values", enum_values)
        object.__setattr__(self, "excluded_shapes", shapes)

    def to_wire(self) -> dict[str, JSONValue]:
        from .dimensions import _domain_wire

        return {
            "path_key": self.path_key.value,
            "domain": _domain_wire(
                "excluded",
                self.domain_kind,
                self.excluded_enum_values,
                self.excluded_shapes,
            ),
        }

    @classmethod
    def from_wire(cls, value: object) -> ExclusionV1:
        document = _require_object(value, cls._WIRE_KEYS, "capability exclusion")
        from .dimensions import _parse_domain

        domain_kind, enum_values, shapes = _parse_domain(document["domain"], "excluded")
        result = cls(
            path_key=cast("M2DimensionPathV1", document["path_key"]),
            domain_kind=domain_kind,
            excluded_enum_values=enum_values,
            excluded_shapes=shapes,
        )
        if result.to_wire() != document:
            raise ValueError("capability exclusion wire is not canonical")
        return result


@dataclass(frozen=True, slots=True)
class CompositionComponentV1:
    component_key: str
    capability: CapabilityRefV1
    required: bool
    ordinal: int

    _WIRE_KEYS: ClassVar[set[str]] = {"component_key", "capability", "required", "ordinal"}  # fmt: skip  # noqa: E501

    def __post_init__(self) -> None:
        component_key = _require_text("component_key", self.component_key)
        if not isinstance(self.capability, CapabilityRefV1):
            raise TypeError("capability must be CapabilityRefV1")
        required = _require_bool("required", self.required)
        ordinal = _require_int("ordinal", self.ordinal, nonnegative=True)
        object.__setattr__(self, "component_key", component_key)
        object.__setattr__(self, "required", required)
        object.__setattr__(self, "ordinal", ordinal)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "component_key": self.component_key,
            "capability": self.capability.to_wire(),
            "required": self.required,
            "ordinal": self.ordinal,
        }

    @classmethod
    def from_wire(cls, value: object) -> CompositionComponentV1:
        document = _require_object(value, cls._WIRE_KEYS, "composition component")
        return cls(
            component_key=cast(str, document["component_key"]),
            capability=CapabilityRefV1.from_wire(document["capability"]),
            required=cast(bool, document["required"]),
            ordinal=cast(int, document["ordinal"]),
        )


@dataclass(frozen=True, slots=True)
class CompositionClaimV1:
    components: tuple[CompositionComponentV1, ...]

    _WIRE_KEYS: ClassVar[set[str]] = {"components"}

    def __post_init__(self) -> None:
        values = _values(self.components, "components")
        if not values:
            raise ValueError("components must be non-empty")
        if any(not isinstance(item, CompositionComponentV1) for item in values):
            raise TypeError("components must contain CompositionComponentV1 values")
        components = cast(tuple[CompositionComponentV1, ...], values)
        if len({item.component_key for item in components}) != len(components):
            raise ValueError("component_key must be unique")
        if len({item.ordinal for item in components}) != len(components):
            raise ValueError("ordinal must be unique")
        ordered = tuple(
            sorted(
                components,
                key=lambda item: (item.ordinal, item.component_key),
            )
        )
        object.__setattr__(self, "components", ordered)

    def to_wire(self) -> dict[str, JSONValue]:
        return {"components": [item.to_wire() for item in self.components]}

    @classmethod
    def from_wire(cls, value: object) -> CompositionClaimV1:
        document = _require_object(value, cls._WIRE_KEYS, "composition claim")
        result = cls(
            tuple(
                CompositionComponentV1.from_wire(item)
                for item in _wire_values(document["components"], "components")
            )
        )
        if result.to_wire() != document:
            raise ValueError("composition claim wire is not canonical")
        return result


CAPABILITY_CLAIM_SCHEMA = "census.capability-claim.v1"
M2_REQUIREMENT_SCHEMA = "census.semantic-requirement.v1"


@dataclass(frozen=True, slots=True)
class CapabilityClaimV1:
    family_key: CapabilityFamilyKeyV1
    capability_version: int
    m2_requirement_schema: str
    m2_interpretation_version: str
    m4_dimension_registry_version: str
    dimensions: tuple[CapabilityDimensionV1, ...]
    exclusions: tuple[ExclusionV1, ...]
    composition: CompositionClaimV1 | None

    SCHEMA: ClassVar[str] = CAPABILITY_CLAIM_SCHEMA
    _WIRE_KEYS: ClassVar[set[str]] = {
        "claim_schema",
        "family_key",
        "capability_version",
        "m2_requirement_schema",
        "m2_interpretation_version",
        "m4_dimension_registry_version",
        "dimensions",
        "exclusions",
        "composition",
    }

    def __post_init__(self) -> None:
        if not isinstance(self.family_key, CapabilityFamilyKeyV1):
            raise TypeError("family_key must be CapabilityFamilyKeyV1")
        capability_version = _require_int("capability_version", self.capability_version)
        if capability_version < 1:
            raise ValueError("capability_version must be at least one")
        m2_schema = _require_text("m2_requirement_schema", self.m2_requirement_schema)
        if m2_schema != M2_REQUIREMENT_SCHEMA:
            raise ValueError(f"m2_requirement_schema must be {M2_REQUIREMENT_SCHEMA}")
        interpretation_version = _require_text(
            "m2_interpretation_version",
            self.m2_interpretation_version,
        )
        registry_version = _require_text(
            "m4_dimension_registry_version",
            self.m4_dimension_registry_version,
        )

        from .dimensions import CapabilityDimensionV1

        dimensions = _values(self.dimensions, "dimensions")
        if any(not isinstance(item, CapabilityDimensionV1) for item in dimensions):
            raise TypeError("dimensions must contain CapabilityDimensionV1 values")
        typed_dimensions = cast(tuple[CapabilityDimensionV1, ...], dimensions)
        dimension_paths = [item.path_key for item in typed_dimensions]
        if len(set(dimension_paths)) != len(dimension_paths):
            raise ValueError("duplicate dimension path")
        ordered_dimensions = tuple(
            sorted(typed_dimensions, key=lambda item: item.path_key.value)
        )

        exclusions = _values(self.exclusions, "exclusions")
        if any(not isinstance(item, ExclusionV1) for item in exclusions):
            raise TypeError("exclusions must contain ExclusionV1 values")
        typed_exclusions = cast(tuple[ExclusionV1, ...], exclusions)
        exclusion_paths = [item.path_key for item in typed_exclusions]
        if len(set(exclusion_paths)) != len(exclusion_paths):
            raise ValueError("duplicate exclusion path")
        if set(dimension_paths) & set(exclusion_paths):
            raise ValueError("dimension and exclusion paths must be disjoint")
        ordered_exclusions = tuple(
            sorted(typed_exclusions, key=lambda item: item.path_key.value)
        )

        composition = self.composition
        if composition is not None and not isinstance(composition, CompositionClaimV1):
            raise TypeError("composition must be CompositionClaimV1 or None")
        object.__setattr__(self, "capability_version", capability_version)
        object.__setattr__(self, "m2_requirement_schema", m2_schema)
        object.__setattr__(
            self,
            "m2_interpretation_version",
            interpretation_version,
        )
        object.__setattr__(
            self,
            "m4_dimension_registry_version",
            registry_version,
        )
        object.__setattr__(self, "dimensions", ordered_dimensions)
        object.__setattr__(self, "exclusions", ordered_exclusions)

    def to_wire(self) -> dict[str, JSONValue]:
        return {
            "claim_schema": self.SCHEMA,
            "family_key": self.family_key.to_wire(),
            "capability_version": self.capability_version,
            "m2_requirement_schema": self.m2_requirement_schema,
            "m2_interpretation_version": self.m2_interpretation_version,
            "m4_dimension_registry_version": self.m4_dimension_registry_version,
            "dimensions": [item.to_wire() for item in self.dimensions],
            "exclusions": [item.to_wire() for item in self.exclusions],
            "composition": (
                None if self.composition is None else self.composition.to_wire()
            ),
        }

    @classmethod
    def from_wire(cls, value: object) -> CapabilityClaimV1:
        document = _require_object(value, cls._WIRE_KEYS, "capability claim")
        schema = _require_text("claim_schema", document["claim_schema"])
        if schema != cls.SCHEMA:
            raise ValueError(f"claim_schema must be {cls.SCHEMA}")
        from .dimensions import CapabilityDimensionV1

        raw_composition = document["composition"]
        composition = (
            None
            if raw_composition is None
            else CompositionClaimV1.from_wire(raw_composition)
        )
        result = cls(
            family_key=CapabilityFamilyKeyV1.from_wire(document["family_key"]),
            capability_version=cast(int, document["capability_version"]),
            m2_requirement_schema=cast(str, document["m2_requirement_schema"]),
            m2_interpretation_version=cast(str, document["m2_interpretation_version"]),
            m4_dimension_registry_version=cast(
                str, document["m4_dimension_registry_version"]
            ),
            dimensions=tuple(
                CapabilityDimensionV1.from_wire(item)
                for item in _wire_values(document["dimensions"], "dimensions")
            ),
            exclusions=tuple(
                ExclusionV1.from_wire(item)
                for item in _wire_values(document["exclusions"], "exclusions")
            ),
            composition=composition,
        )
        if result.to_wire() != document:
            raise ValueError("capability claim wire is not canonical")
        return result
