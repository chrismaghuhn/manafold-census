from __future__ import annotations

import json
from pathlib import Path

import pytest
from capability_fixtures import draw_family_key
from jsonschema import Draft202012Validator

from manafold_census.capability.binding import BindingStateV1, ParameterBindingV1
from manafold_census.capability.claim import (
    CapabilityClaimV1,
    CompositionClaimV1,
    CompositionComponentV1,
    ExclusionV1,
)
from manafold_census.capability.dimensions import (
    CapabilityDimensionV1,
    DimensionDomainKindV1,
    DimensionKindV1,
    M2DimensionPathV1,
    UnknownPolicyV1,
    dimension_spec_for,
)
from manafold_census.capability.model import (
    CapabilityFamilyKeyV1,
    CapabilityRefV1,
    NucleusKindV1,
)
from manafold_census.semantic.kinds import RequirementFamilyV1, RequirementKindV1
from manafold_census.semantic.primitives import SemanticShapeV1


def test_draw_quantity_is_a_dimension_not_a_family_identity() -> None:
    quantity = CapabilityDimensionV1(
        path_key=M2DimensionPathV1.DRAW_CARDS_QUANTITY,
        dimension_kind=DimensionKindV1.QUANTITY,
        required=True,
        domain_kind=DimensionDomainKindV1.ANY_TYPED_VALUE,
    )

    assert quantity.path_key is M2DimensionPathV1.DRAW_CARDS_QUANTITY
    assert quantity.dimension_kind is DimensionKindV1.QUANTITY
    assert quantity.required is True
    assert quantity.unknown_policy is UnknownPolicyV1.EXPLICIT_BUT_NOT_ACTIVE


def test_unknown_dimension_path_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown M2 dimension path"):
        M2DimensionPathV1.from_wire("DRAW_CARDS_FREE_FORM")


def test_parameter_binding_preserves_unknown_values() -> None:
    binding = ParameterBindingV1.unknown(
        M2DimensionPathV1.DRAW_CARDS_QUANTITY,
        "UNKNOWN_SEMANTICS",
        "/parameters/quantity",
    )

    assert binding.state is BindingStateV1.UNKNOWN
    assert binding.m2_unknown_path == "/parameters/quantity"
    assert binding.value is None
    assert ParameterBindingV1.from_wire(binding.to_wire()) == binding


def test_registry_binds_path_to_exact_m2_kind_and_parameter_path() -> None:
    spec = dimension_spec_for(M2DimensionPathV1.DRAW_CARDS_QUANTITY)

    assert spec.family is RequirementFamilyV1.EFFECT
    assert spec.kind is RequirementKindV1.DRAW_CARDS
    assert spec.parameter_path == "/parameters/quantity"
    assert spec.dimension_kind is DimensionKindV1.QUANTITY


def test_dimension_kind_must_match_the_code_owned_registry() -> None:
    with pytest.raises(ValueError, match="dimension_kind"):
        CapabilityDimensionV1(
            path_key=M2DimensionPathV1.DRAW_CARDS_QUANTITY,
            dimension_kind=DimensionKindV1.ENTITY_REF,
            required=True,
            domain_kind=DimensionDomainKindV1.ANY_TYPED_VALUE,
        )


def test_enum_subset_rejects_values_outside_the_registered_m2_enum() -> None:
    with pytest.raises(ValueError, match="registered M2 enum"):
        CapabilityDimensionV1(
            path_key=M2DimensionPathV1.MODIFY_CHARACTERISTIC_OPERATION,
            dimension_kind=DimensionKindV1.M2_ENUM,
            required=True,
            domain_kind=DimensionDomainKindV1.M2_ENUM_SUBSET,
            allowed_enum_values=("NOT_AN_M2_OPERATION",),
        )


def test_any_typed_domain_rejects_nonempty_subsets() -> None:
    with pytest.raises(ValueError, match="ANY_TYPED_VALUE"):
        CapabilityDimensionV1(
            path_key=M2DimensionPathV1.DRAW_CARDS_QUANTITY,
            dimension_kind=DimensionKindV1.QUANTITY,
            required=True,
            domain_kind=DimensionDomainKindV1.ANY_TYPED_VALUE,
            allowed_enum_values=("2",),
        )


def test_not_applicable_is_only_allowed_for_optional_m2_paths() -> None:
    optional = ParameterBindingV1.not_applicable(
        M2DimensionPathV1.CREATE_OBJECT_DURATION
    )
    assert optional.state is BindingStateV1.NOT_APPLICABLE

    with pytest.raises(ValueError, match="optional"):
        ParameterBindingV1.not_applicable(M2DimensionPathV1.DRAW_CARDS_QUANTITY)


def test_executable_binding_values_are_rejected() -> None:
    with pytest.raises(TypeError, match="unsupported"):
        ParameterBindingV1.known(
            M2DimensionPathV1.DRAW_CARDS_QUANTITY,
            lambda: None,
        )


def _draw_claim() -> CapabilityClaimV1:
    return CapabilityClaimV1(
        family_key=draw_family_key(),
        capability_version=1,
        m2_requirement_schema="census.semantic-requirement.v1",
        m2_interpretation_version="1",
        m4_dimension_registry_version="1",
        dimensions=(
            CapabilityDimensionV1(
                path_key=M2DimensionPathV1.DRAW_CARDS_DRAWER,
                dimension_kind=DimensionKindV1.ENTITY_REF,
                required=True,
                domain_kind=DimensionDomainKindV1.ANY_TYPED_VALUE,
            ),
            CapabilityDimensionV1(
                path_key=M2DimensionPathV1.DRAW_CARDS_QUANTITY,
                dimension_kind=DimensionKindV1.QUANTITY,
                required=True,
                domain_kind=DimensionDomainKindV1.ANY_TYPED_VALUE,
            ),
        ),
        exclusions=(),
        composition=None,
    )


def test_claim_wire_round_trip_is_canonical() -> None:
    claim = _draw_claim()

    assert CapabilityClaimV1.from_wire(claim.to_wire()) == claim
    assert claim.to_wire()["claim_schema"] == "census.capability-claim.v1"


def test_capability_claim_schema_accepts_the_typed_claim_wire() -> None:
    schema_path = (
        Path(__file__).parents[1] / "schemas" / "capability-claim.v1.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)

    errors = list(Draft202012Validator(schema).iter_errors(_draw_claim().to_wire()))

    assert errors == []


def test_claim_rejects_unknown_wire_fields() -> None:
    wire = _draw_claim().to_wire()
    wire["unexpected"] = True

    with pytest.raises(ValueError, match="unexpected properties"):
        CapabilityClaimV1.from_wire(wire)


def test_claim_rejects_duplicate_dimension_paths() -> None:
    with pytest.raises(ValueError, match="duplicate dimension path"):
        CapabilityClaimV1(
            family_key=draw_family_key(),
            capability_version=1,
            m2_requirement_schema="census.semantic-requirement.v1",
            m2_interpretation_version="1",
            m4_dimension_registry_version="1",
            dimensions=(
                CapabilityDimensionV1(
                    path_key=M2DimensionPathV1.DRAW_CARDS_QUANTITY,
                    dimension_kind=DimensionKindV1.QUANTITY,
                    required=True,
                    domain_kind=DimensionDomainKindV1.ANY_TYPED_VALUE,
                ),
                CapabilityDimensionV1(
                    path_key=M2DimensionPathV1.DRAW_CARDS_QUANTITY,
                    dimension_kind=DimensionKindV1.QUANTITY,
                    required=True,
                    domain_kind=DimensionDomainKindV1.ANY_TYPED_VALUE,
                ),
            ),
            exclusions=(),
            composition=None,
        )


def test_claim_rejects_dimension_outside_family_operation_anchor() -> None:
    with pytest.raises(ValueError, match="operation_anchor"):
        CapabilityClaimV1(
            family_key=draw_family_key(),
            capability_version=1,
            m2_requirement_schema="census.semantic-requirement.v1",
            m2_interpretation_version="1",
            m4_dimension_registry_version="1",
            dimensions=(
                CapabilityDimensionV1(
                    path_key=M2DimensionPathV1.DEAL_DAMAGE_AMOUNT,
                    dimension_kind=DimensionKindV1.QUANTITY,
                    required=True,
                    domain_kind=DimensionDomainKindV1.ANY_TYPED_VALUE,
                ),
            ),
            exclusions=(),
            composition=None,
        )


def test_claim_rejects_exclusion_outside_family_operation_anchor() -> None:
    with pytest.raises(ValueError, match="operation_anchor"):
        CapabilityClaimV1(
            family_key=draw_family_key(),
            capability_version=1,
            m2_requirement_schema="census.semantic-requirement.v1",
            m2_interpretation_version="1",
            m4_dimension_registry_version="1",
            dimensions=(),
            exclusions=(
                ExclusionV1(
                    path_key=M2DimensionPathV1.DEAL_DAMAGE_AMOUNT,
                    domain_kind=DimensionDomainKindV1.ANY_TYPED_VALUE,
                ),
            ),
            composition=None,
        )


def test_composite_claim_accepts_a_declared_anchor_path() -> None:
    claim = CapabilityClaimV1(
        family_key=CapabilityFamilyKeyV1(
            nucleus_contract_version="1",
            nucleus_kind=NucleusKindV1.COMPOSITE,
            operation_anchor=(
                (RequirementFamilyV1.EFFECT, RequirementKindV1.DRAW_CARDS),
                (RequirementFamilyV1.EFFECT, RequirementKindV1.DEAL_DAMAGE),
            ),
        ),
        capability_version=1,
        m2_requirement_schema="census.semantic-requirement.v1",
        m2_interpretation_version="1",
        m4_dimension_registry_version="1",
        dimensions=(
            CapabilityDimensionV1(
                path_key=M2DimensionPathV1.DEAL_DAMAGE_AMOUNT,
                dimension_kind=DimensionKindV1.QUANTITY,
                required=True,
                domain_kind=DimensionDomainKindV1.ANY_TYPED_VALUE,
            ),
        ),
        exclusions=(),
        composition=CompositionClaimV1(
            (
                CompositionComponentV1(
                    "draw",
                    CapabilityRefV1("capfam_" + "a" * 64, 1, "b" * 64),
                    True,
                    0,
                ),
                CompositionComponentV1(
                    "damage",
                    CapabilityRefV1("capfam_" + "c" * 64, 1, "d" * 64),
                    True,
                    1,
                ),
            )
        ),
    )

    assert claim.family_key.nucleus_kind is NucleusKindV1.COMPOSITE


def test_shape_subset_is_typed_and_canonical() -> None:
    dimension = CapabilityDimensionV1(
        path_key=M2DimensionPathV1.MOVE_BETWEEN_ZONES_CAUSE,
        dimension_kind=DimensionKindV1.SEMANTIC_DESCRIPTOR,
        required=False,
        domain_kind=DimensionDomainKindV1.M2_SHAPE_SUBSET,
        allowed_shapes=(
            SemanticShapeV1.EVENT,
            SemanticShapeV1.EFFECT,
        ),
    )

    assert dimension.allowed_shapes == (
        SemanticShapeV1.EFFECT,
        SemanticShapeV1.EVENT,
    )


def test_exclusion_wire_round_trip_is_canonical() -> None:
    exclusion = ExclusionV1(
        path_key=M2DimensionPathV1.MOVE_BETWEEN_ZONES_CAUSE,
        domain_kind=DimensionDomainKindV1.M2_SHAPE_SUBSET,
        excluded_shapes=(SemanticShapeV1.EVENT,),
    )

    assert ExclusionV1.from_wire(exclusion.to_wire()) == exclusion
