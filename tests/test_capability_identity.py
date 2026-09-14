from manafold_census.capability.identity import capability_family_id_for
from manafold_census.capability.model import CapabilityFamilyKeyV1, NucleusKindV1
from tests.capability_fixtures import draw_family_key


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
