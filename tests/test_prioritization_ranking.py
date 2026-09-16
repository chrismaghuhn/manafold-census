from __future__ import annotations


def test_non_noise_orders_before_planning_noise() -> None:
    from prioritization_fixtures import make_assessment

    from manafold_census.prioritization.analyze import (
        cluster_mechanical_overlaps,
        rank_worklist,
    )

    noise = make_assessment(
        11,
        oracle_ids=("n-a", "n-b"),
        raw_texts=(None, None),
    )
    assert noise.planning_noise.value != "NONE"
    normal = make_assessment(12, oracle_ids=("x-a", "x-b"), raw_texts=("alpha", "beta"))
    assert normal.planning_noise.value == "NONE"
    clusters = cluster_mechanical_overlaps((noise, normal))
    ranked = rank_worklist((noise, normal), clusters)
    assert ranked[0].opportunity_id == normal.opportunity_id
    assert ranked[-1].opportunity_id == noise.opportunity_id


def test_full_worklist_ordering_uses_frozen_lexicographic_keys() -> None:
    from prioritization_fixtures import make_assessment

    from manafold_census.inventory.model import GroupingLensV1
    from manafold_census.prioritization.analyze import (
        assessment_sort_key,
        cluster_mechanical_overlaps,
        rank_worklist,
    )

    many = make_assessment(21, oracle_ids=("a", "b", "c"), raw_texts=("t1", "t2", "t3"))
    few = make_assessment(22, oracle_ids=("a", "b"), raw_texts=("t1", "t2"))
    assert assessment_sort_key(many) < assessment_sort_key(few)
    narrow = make_assessment(23, oracle_ids=("a", "b"), raw_texts=("same", "same"))
    wide = make_assessment(24, oracle_ids=("a", "b"), raw_texts=("same", "different"))
    assert assessment_sort_key(narrow) < assessment_sort_key(wide)
    exact = make_assessment(
        25,
        lens=GroupingLensV1.ABILITY_LINE_EXACT,
        oracle_ids=("a", "b"),
        raw_texts=("t1", "t2"),
    )
    shape = make_assessment(
        26,
        lens=GroupingLensV1.ABILITY_LINE_SHAPE,
        oracle_ids=("a", "b"),
        raw_texts=("t1", "t2"),
    )
    assert assessment_sort_key(exact) < assessment_sort_key(shape)
    clusters = cluster_mechanical_overlaps((many, few, narrow, wide, exact, shape))
    ranked = rank_worklist((shape, wide, few, exact, narrow, many), clusters)
    by_id = {item.opportunity_id: item for item in (many, few, narrow, wide)}
    expected_order = sorted((many, few, narrow, wide), key=assessment_sort_key)
    assert [item.opportunity_id for item in ranked if item.opportunity_id in by_id] == [
        item.opportunity_id for item in expected_order
    ]
    assert ranked[0].rank == 1
    assert [item.rank for item in ranked] == list(range(1, len(ranked) + 1))


def test_canonical_opportunity_id_breaks_all_remaining_ties() -> None:
    from prioritization_fixtures import make_assessment

    from manafold_census.prioritization.analyze import (
        assessment_sort_key,
        cluster_mechanical_overlaps,
        rank_worklist,
    )

    first = make_assessment(31, oracle_ids=("a", "b"), raw_texts=("t1", "t2"))
    second = make_assessment(32, oracle_ids=("a", "b"), raw_texts=("t1", "t2"))
    assert assessment_sort_key(first) != assessment_sort_key(second)
    earlier = min(first.opportunity_id, second.opportunity_id)
    clusters = cluster_mechanical_overlaps((first, second))
    ranked = rank_worklist((second, first), clusters)
    assert ranked[0].opportunity_id == earlier


def test_representative_examples_use_canonical_surface_identity() -> None:
    from prioritization_fixtures import assessed_default

    loaded, assessments, _ = assessed_default()
    surfaces_by_id = {item.surface_id: item for item in loaded.surfaces}
    for assessment in assessments:
        assert (
            assessment.representative_surface_ids
            == tuple(sorted(assessment.member_surface_ids))[:3]
        )
        for surface_id in assessment.representative_surface_ids:
            assert surface_id in surfaces_by_id


def test_shuffled_inputs_keep_assessment_and_worklist_bytes() -> None:
    import random

    from prioritization_fixtures import default_pipeline

    from manafold_census.prioritization.analyze import (
        build_assessments,
        cluster_mechanical_overlaps,
        rank_worklist,
    )

    surfaces, groups, opportunities = default_pipeline()
    surfaces_by_id = {item.surface_id: item for item in surfaces}
    first_assessments = build_assessments(groups, opportunities, surfaces_by_id)
    first_clusters = cluster_mechanical_overlaps(first_assessments)
    first_worklist = rank_worklist(first_assessments, first_clusters)
    shuffled_groups = list(groups)
    shuffled_opportunities = list(opportunities)
    random.Random(7).shuffle(shuffled_groups)
    random.Random(11).shuffle(shuffled_opportunities)
    second_assessments = build_assessments(
        shuffled_groups, shuffled_opportunities, surfaces_by_id
    )
    second_clusters = cluster_mechanical_overlaps(second_assessments)
    second_worklist = rank_worklist(second_assessments, second_clusters)
    assert [item.to_wire() for item in second_assessments] == [
        item.to_wire() for item in first_assessments
    ]
    assert [item.to_wire() for item in second_clusters] == [
        item.to_wire() for item in first_clusters
    ]
    assert [item.to_wire() for item in second_worklist] == [
        item.to_wire() for item in first_worklist
    ]
