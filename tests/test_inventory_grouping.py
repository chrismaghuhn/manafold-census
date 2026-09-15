from __future__ import annotations

from tests.inventory_fixtures import records


def test_grouping_keeps_exact_shape_and_singleton_lenses_separate() -> None:
    from manafold_census.inventory.grouping import group_surfaces
    from manafold_census.inventory.model import GroupingLensV1
    from manafold_census.inventory.projection import project_surfaces

    groups = group_surfaces(project_surfaces(records()))

    exact_card = [
        item
        for item in groups
        if item.grouping_lens is GroupingLensV1.CARD_TEXT_EXACT
        and item.group_key == "Shared line.\nValue 1 {G}"
    ]
    shape_card = [
        item
        for item in groups
        if item.grouping_lens is GroupingLensV1.CARD_TEXT_SHAPE
        and item.group_key == "Shared line. Value {NUMBER} {MANA_SYMBOL}"
    ]

    assert len(exact_card) == 1
    assert exact_card[0].recurrence_status.value == "SINGLETON"
    assert len(shape_card) == 1
    assert shape_card[0].recurrence_status.value == "RECURRING"
    assert shape_card[0].distinct_oracle_identity_count == 2
    assert any(item.distinct_oracle_identity_count == 1 for item in groups)


def test_grouping_overlaps_lenses_and_emits_only_non_authoritative_opportunities() -> (
    None
):
    from manafold_census.inventory.grouping import (
        build_capability_opportunities,
        group_surfaces,
    )
    from manafold_census.inventory.projection import project_surfaces

    groups = group_surfaces(project_surfaces(records()))
    opportunities = build_capability_opportunities(groups)

    assert opportunities
    assert all(item.authority_scope == "NON_AUTHORITATIVE" for item in opportunities)
    assert all(item.planning_status == "UNASSESSED" for item in opportunities)
    assert all(item.distinct_oracle_identity_count >= 2 for item in opportunities)
    assert len({item.candidate_group_ids[0] for item in opportunities}) == len(
        opportunities
    )


def test_shape_policy_replaces_only_source_name_tokens() -> None:
    from manafold_census.inventory.grouping import shape_text

    assert shape_text("Alpha and Alphabet", "Alpha") == "{SOURCE_NAME} and Alphabet"
