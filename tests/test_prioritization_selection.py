from __future__ import annotations


def _ranked(assessments):
    from manafold_census.prioritization.analyze import (
        cluster_mechanical_overlaps,
        rank_worklist,
    )

    clusters = cluster_mechanical_overlaps(assessments)
    return rank_worklist(assessments, clusters), clusters


def test_greedy_selection_maximizes_marginal_oracle_coverage() -> None:
    from prioritization_fixtures import make_assessment

    from manafold_census.prioritization.analyze import select_greedy_review_packet

    broad = make_assessment(71, oracle_ids=("a", "b", "c", "d"))
    narrow = make_assessment(72, oracle_ids=("a", "b"))
    disjoint = make_assessment(73, oracle_ids=("e", "f"))
    ranked, _ = _ranked((narrow, disjoint, broad))
    by_id = {item.opportunity_id: item for item in (broad, narrow, disjoint)}
    selected, reason, marginals = select_greedy_review_packet(ranked, by_id)
    assert selected[0] == broad.opportunity_id
    assert marginals[0] == 4
    assert reason.value in (
        "REVIEW_BUDGET_REACHED",
        "NO_ADDITIONAL_ORACLE_COVERAGE",
    )
    covered: set[str] = set()
    for opportunity_id, marginal in zip(selected, marginals, strict=True):
        fresh = len(set(by_id[opportunity_id].member_oracle_ids) - covered)
        assert marginal == fresh
        covered |= set(by_id[opportunity_id].member_oracle_ids)


def test_review_budget_caps_selection_at_twenty_five() -> None:
    from prioritization_fixtures import make_assessment

    from manafold_census.prioritization._common import REVIEW_PACKET_LIMIT
    from manafold_census.prioritization.analyze import select_greedy_review_packet

    assessments = tuple(
        make_assessment(100 + index, oracle_ids=(f"oracle-{index:03d}-a", f"o-{index}"))
        for index in range(40)
    )
    ranked, _ = _ranked(assessments)
    by_id = {item.opportunity_id: item for item in assessments}
    selected, reason, marginals = select_greedy_review_packet(ranked, by_id)
    assert REVIEW_PACKET_LIMIT == 25
    assert len(selected) == 25
    assert reason.value == "REVIEW_BUDGET_REACHED"
    assert len(marginals) == 25


def test_empty_marginal_coverage_stops_before_the_budget() -> None:
    from prioritization_fixtures import make_assessment

    from manafold_census.prioritization.analyze import select_greedy_review_packet

    first = make_assessment(81, oracle_ids=("a", "b"))
    second = make_assessment(82, oracle_ids=("a", "b"))
    ranked, _ = _ranked((first, second))
    by_id = {item.opportunity_id: item for item in (first, second)}
    selected, reason, _ = select_greedy_review_packet(ranked, by_id)
    assert len(selected) == 1
    assert reason.value == "NO_ADDITIONAL_ORACLE_COVERAGE"


def test_planning_noise_never_enters_the_bounded_packet() -> None:
    from prioritization_fixtures import noise_records, pipeline

    from manafold_census.prioritization._common import PlanningNoiseV1
    from manafold_census.prioritization.analyze import (
        build_assessments,
        cluster_mechanical_overlaps,
        rank_worklist,
        select_greedy_review_packet,
    )

    surfaces, groups, opportunities = pipeline(noise_records())
    surfaces_by_id = {item.surface_id: item for item in surfaces}
    assessments = build_assessments(groups, opportunities, surfaces_by_id)
    noise = [
        item for item in assessments if item.planning_noise is not PlanningNoiseV1.NONE
    ]
    assert noise
    clusters = cluster_mechanical_overlaps(assessments)
    ranked = rank_worklist(assessments, clusters)
    by_id = {item.opportunity_id: item for item in assessments}
    selected, _, _ = select_greedy_review_packet(ranked, by_id)
    assert selected
    assert not (set(selected) & {item.opportunity_id for item in noise})


def test_non_representative_overlap_members_are_excluded() -> None:
    from prioritization_fixtures import make_assessment, make_surface_id

    from manafold_census.inventory.model import GroupingLensV1
    from manafold_census.prioritization.analyze import (
        cluster_mechanical_overlaps,
        rank_worklist,
        select_greedy_review_packet,
    )

    shared = (make_surface_id(931), make_surface_id(932))
    exact = make_assessment(
        91,
        lens=GroupingLensV1.ABILITY_LINE_EXACT,
        oracle_ids=("a", "b"),
        raw_texts=("t1", "t2"),
        surface_ids=shared,
    )
    shape = make_assessment(
        92,
        lens=GroupingLensV1.ABILITY_LINE_SHAPE,
        oracle_ids=("a", "b"),
        raw_texts=("t1", "t2"),
        surface_ids=shared,
    )
    clusters = cluster_mechanical_overlaps((exact, shape))
    ranked = rank_worklist((exact, shape), clusters)
    by_id = {item.opportunity_id: item for item in (exact, shape)}
    selected, _, _ = select_greedy_review_packet(ranked, by_id)
    assert selected == (exact.opportunity_id,)


def test_packet_examples_are_deterministic_and_sourced() -> None:
    from prioritization_fixtures import assessed_default

    loaded, assessments, clusters = assessed_default()
    from manafold_census.prioritization.analyze import rank_worklist

    ranked = rank_worklist(assessments, clusters)
    surfaces_by_id = {item.surface_id: item for item in loaded.surfaces}
    for assessment in assessments:
        for surface_id in assessment.representative_surface_ids:
            assert surface_id in surfaces_by_id
    assert ranked
