import pytest

from manafold_census.capability.model import (
    CapabilityFamilyKeyV1,
    CapabilityRefV1,
    NucleusKindV1,
)
from manafold_census.semantic.kinds import (
    RequirementFamilyV1,
    RequirementKindV1,
)
from tests.capability_fixtures import draw_family_key


def test_family_id_input_is_stable_for_equal_nuclei() -> None:
    first = draw_family_key()
    second = draw_family_key()

    assert first.to_wire() == second.to_wire()


def test_operation_anchor_order_is_canonical() -> None:
    first = CapabilityFamilyKeyV1(
        nucleus_contract_version="1",
        nucleus_kind=NucleusKindV1.COMPOSITE,
        operation_anchor=(
            (RequirementFamilyV1.EFFECT, RequirementKindV1.DRAW_CARDS),
            (RequirementFamilyV1.EFFECT, RequirementKindV1.DEAL_DAMAGE),
        ),
    )
    second = CapabilityFamilyKeyV1(
        nucleus_contract_version="1",
        nucleus_kind=NucleusKindV1.COMPOSITE,
        operation_anchor=(
            (RequirementFamilyV1.EFFECT, RequirementKindV1.DEAL_DAMAGE),
            (RequirementFamilyV1.EFFECT, RequirementKindV1.DRAW_CARDS),
        ),
    )

    assert first.to_wire() == second.to_wire()


def test_atomic_requires_exactly_one_operation_anchor() -> None:
    with pytest.raises(ValueError, match="exactly one operation anchor"):
        CapabilityFamilyKeyV1(
            nucleus_contract_version="1",
            nucleus_kind=NucleusKindV1.ATOMIC,
            operation_anchor=(
                (RequirementFamilyV1.EFFECT, RequirementKindV1.DRAW_CARDS),
                (RequirementFamilyV1.EFFECT, RequirementKindV1.DEAL_DAMAGE),
            ),
        )


def test_composite_requires_multiple_operation_anchors() -> None:
    with pytest.raises(ValueError, match="at least two operation anchors"):
        CapabilityFamilyKeyV1(
            nucleus_contract_version="1",
            nucleus_kind=NucleusKindV1.COMPOSITE,
            operation_anchor=(
                (RequirementFamilyV1.EFFECT, RequirementKindV1.DRAW_CARDS),
            ),
        )


def test_duplicate_operation_anchor_is_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate operation anchor"):
        CapabilityFamilyKeyV1(
            nucleus_contract_version="1",
            nucleus_kind=NucleusKindV1.COMPOSITE,
            operation_anchor=(
                (RequirementFamilyV1.EFFECT, RequirementKindV1.DRAW_CARDS),
                (RequirementFamilyV1.EFFECT, RequirementKindV1.DRAW_CARDS),
            ),
        )


def test_empty_operation_anchor_is_rejected() -> None:
    with pytest.raises(ValueError, match="operation_anchor must be non-empty"):
        CapabilityFamilyKeyV1(
            nucleus_contract_version="1",
            nucleus_kind=NucleusKindV1.ATOMIC,
            operation_anchor=(),
        )


def test_family_kind_mismatch_is_rejected() -> None:
    with pytest.raises(ValueError, match="does not belong to family"):
        CapabilityFamilyKeyV1(
            nucleus_contract_version="1",
            nucleus_kind=NucleusKindV1.ATOMIC,
            operation_anchor=(
                (RequirementFamilyV1.COST, RequirementKindV1.DRAW_CARDS),
            ),
        )


def test_unsorted_family_key_wire_is_rejected() -> None:
    wire = CapabilityFamilyKeyV1(
        nucleus_contract_version="1",
        nucleus_kind=NucleusKindV1.COMPOSITE,
        operation_anchor=(
            (RequirementFamilyV1.EFFECT, RequirementKindV1.DRAW_CARDS),
            (RequirementFamilyV1.EFFECT, RequirementKindV1.DEAL_DAMAGE),
        ),
    ).to_wire()
    wire["operation_anchor"] = list(reversed(wire["operation_anchor"]))

    with pytest.raises(ValueError, match="canonical order"):
        CapabilityFamilyKeyV1.from_wire(wire)


@pytest.mark.parametrize("extra_field", ["unexpected", "dimension_paths"])
def test_family_key_wire_rejects_unknown_or_dimension_fields(
    extra_field: str,
) -> None:
    wire = draw_family_key().to_wire()
    wire[extra_field] = []  # type: ignore[literal-required]

    with pytest.raises(ValueError, match="unexpected properties"):
        CapabilityFamilyKeyV1.from_wire(wire)


def test_family_key_wire_rejects_noncanonical_anchor_shape() -> None:
    wire = draw_family_key().to_wire()
    wire["operation_anchor"] = [["effect", "draw_cards"]]

    with pytest.raises(TypeError, match="must be an object"):
        CapabilityFamilyKeyV1.from_wire(wire)


def test_capability_ref_wire_is_exact() -> None:
    reference = CapabilityRefV1("capfam_" + "a" * 64, 1, "b" * 64)

    assert reference.to_wire() == {
        "capability_family_id": "capfam_" + "a" * 64,
        "capability_version": 1,
        "claim_digest": "b" * 64,
    }


def test_capability_ref_rejects_invalid_family_id_prefix() -> None:
    with pytest.raises(ValueError, match="capability_family_id"):
        CapabilityRefV1("capability_" + "a" * 64, 1, "b" * 64)


@pytest.mark.parametrize("version", [0, -1])
def test_capability_ref_rejects_nonpositive_version(version: int) -> None:
    with pytest.raises(ValueError, match="capability_version"):
        CapabilityRefV1("capfam_" + "a" * 64, version, "b" * 64)


def test_capability_ref_rejects_nonhex_claim_digest() -> None:
    with pytest.raises(ValueError, match="claim_digest"):
        CapabilityRefV1("capfam_" + "a" * 64, 1, "g" * 64)
