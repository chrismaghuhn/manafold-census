from capability_fixtures import draw_family_key

from manafold_census.capability.dimensions import (
    CapabilityDimensionV1,
    DimensionDomainKindV1,
    DimensionKindV1,
    M2DimensionPathV1,
)
from manafold_census.capability.identity import (
    capability_claim_digest_for,
    capability_family_id_for,
)
from manafold_census.capability.model import (
    CapabilityClaimV1,
    CapabilityFamilyKeyV1,
    NucleusKindV1,
)
from manafold_census.semantic.kinds import RequirementFamilyV1, RequirementKindV1


def test_family_id_is_derived_only_from_the_stable_nucleus() -> None:
    first = draw_family_key()
    second = draw_family_key()

    assert capability_family_id_for(first) == capability_family_id_for(second)
    assert capability_family_id_for(first).startswith("capfam_")


def test_changed_nucleus_contract_version_changes_family_id() -> None:
    first = draw_family_key()
    second = CapabilityFamilyKeyV1(
        nucleus_contract_version="2",
        nucleus_kind=NucleusKindV1.ATOMIC,
        operation_anchor=first.operation_anchor,
    )

    assert capability_family_id_for(first) != capability_family_id_for(second)


def _draw_claim(
    *,
    path_key: M2DimensionPathV1 = M2DimensionPathV1.DRAW_CARDS_QUANTITY,
    required: bool = True,
    registry_version: str = "1",
) -> CapabilityClaimV1:
    dimension_kind = (
        DimensionKindV1.QUANTITY
        if path_key is M2DimensionPathV1.DRAW_CARDS_QUANTITY
        else DimensionKindV1.ENTITY_REF
    )
    return CapabilityClaimV1(
        family_key=draw_family_key(),
        capability_version=1,
        m2_requirement_schema="census.semantic-requirement.v1",
        m2_interpretation_version="1",
        m4_dimension_registry_version=registry_version,
        dimensions=(
            CapabilityDimensionV1(
                path_key=path_key,
                dimension_kind=dimension_kind,
                required=required,
                domain_kind=DimensionDomainKindV1.ANY_TYPED_VALUE,
            ),
        ),
        exclusions=(),
        composition=None,
    )


def test_claim_digest_changes_for_dimension_path_without_family_change() -> None:
    first = _draw_claim(path_key=M2DimensionPathV1.DRAW_CARDS_QUANTITY)
    second = _draw_claim(path_key=M2DimensionPathV1.DRAW_CARDS_DRAWER)

    assert capability_claim_digest_for(first) != capability_claim_digest_for(second)
    assert capability_family_id_for(first.family_key) == capability_family_id_for(
        second.family_key
    )


def test_claim_digest_changes_for_requiredness_without_family_change() -> None:
    first = _draw_claim(required=True)
    second = _draw_claim(required=False)

    assert capability_claim_digest_for(first) != capability_claim_digest_for(second)
    assert capability_family_id_for(first.family_key) == capability_family_id_for(
        second.family_key
    )


def test_claim_digest_changes_for_registry_version_without_family_change() -> None:
    first = _draw_claim(registry_version="1")
    second = _draw_claim(registry_version="2")

    assert capability_claim_digest_for(first) != capability_claim_digest_for(second)
    assert capability_family_id_for(first.family_key) == capability_family_id_for(
        second.family_key
    )


def test_changed_operation_anchor_changes_family_id() -> None:
    first = draw_family_key()
    second = CapabilityFamilyKeyV1(
        nucleus_contract_version="1",
        nucleus_kind=NucleusKindV1.ATOMIC,
        operation_anchor=((RequirementFamilyV1.EFFECT, RequirementKindV1.DEAL_DAMAGE),),
    )

    assert capability_family_id_for(first) != capability_family_id_for(second)
