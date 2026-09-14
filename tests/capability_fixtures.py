from manafold_census.capability.model import (
    CapabilityFamilyKeyV1,
    NucleusKindV1,
)
from manafold_census.semantic.kinds import (
    RequirementFamilyV1,
    RequirementKindV1,
)


def draw_family_key() -> CapabilityFamilyKeyV1:
    return CapabilityFamilyKeyV1(
        nucleus_contract_version="1",
        nucleus_kind=NucleusKindV1.ATOMIC,
        operation_anchor=(
            (
                RequirementFamilyV1.EFFECT,
                RequirementKindV1.DRAW_CARDS,
            ),
        ),
    )
