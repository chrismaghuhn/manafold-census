from __future__ import annotations


def test_exact_surface_id_sets_share_one_mechanical_cluster() -> None:
    from prioritization_fixtures import make_assessment, make_surface_id

    from manafold_census.inventory.model import GroupingLensV1
    from manafold_census.prioritization.analyze import cluster_mechanical_overlaps

    shared = (make_surface_id(901), make_surface_id(902))
    exact = make_assessment(
        41,
        lens=GroupingLensV1.ABILITY_LINE_EXACT,
        oracle_ids=("a", "b"),
        raw_texts=("t1", "t2"),
        surface_ids=shared,
    )
    shape = make_assessment(
        42,
        lens=GroupingLensV1.ABILITY_LINE_SHAPE,
        oracle_ids=("a", "b"),
        raw_texts=("t1", "t2"),
        surface_ids=shared,
    )
    (cluster,) = cluster_mechanical_overlaps((exact, shape))
    assert cluster.member_surface_ids == tuple(sorted(shared))
    assert set(cluster.member_opportunity_ids) == {
        exact.opportunity_id,
        shape.opportunity_id,
    }
    assert cluster.representative_opportunity_id == exact.opportunity_id


def test_different_surface_sets_are_never_mechanically_merged() -> None:
    from prioritization_fixtures import make_assessment

    from manafold_census.prioritization.analyze import cluster_mechanical_overlaps

    first = make_assessment(51, oracle_ids=("a", "b"))
    second = make_assessment(52, oracle_ids=("a", "b"))
    assert first.member_surface_ids != second.member_surface_ids
    clusters = cluster_mechanical_overlaps((first, second))
    assert len(clusters) == 2


def test_shape_representative_wins_only_without_exact_competitor() -> None:
    from prioritization_fixtures import make_assessment, make_surface_id

    from manafold_census.inventory.model import GroupingLensV1
    from manafold_census.prioritization.analyze import cluster_mechanical_overlaps

    shared = (make_surface_id(911), make_surface_id(912))
    first_shape = make_assessment(
        61,
        lens=GroupingLensV1.ABILITY_LINE_SHAPE,
        oracle_ids=("a", "b"),
        raw_texts=("t1", "t2"),
        surface_ids=shared,
    )
    second_shape = make_assessment(
        62,
        lens=GroupingLensV1.ABILITY_LINE_SHAPE,
        oracle_ids=("a", "b"),
        raw_texts=("t1", "t2"),
        surface_ids=shared,
    )
    (cluster,) = cluster_mechanical_overlaps((second_shape, first_shape))
    assert cluster.representative_opportunity_id == min(
        first_shape.opportunity_id, second_shape.opportunity_id
    )


def test_every_opportunity_stays_traceable_in_exactly_one_cluster() -> None:
    from prioritization_fixtures import assessed_default

    _, assessments, clusters = assessed_default()
    seen: dict[str, int] = {}
    for cluster in clusters:
        for opportunity_id in cluster.member_opportunity_ids:
            seen[opportunity_id] = seen.get(opportunity_id, 0) + 1
    assert set(seen) == {item.opportunity_id for item in assessments}
    assert set(seen.values()) == {1}


def test_tampered_overlap_cluster_is_rejected(tmp_path) -> None:
    import json

    from prioritization_fixtures import default_loaded_inputs

    from manafold_census.canonical import canonical_json_bytes
    from manafold_census.prioritization.build import (
        build_prioritization_from_loaded_inputs,
    )
    from manafold_census.prioritization.validate import (
        PrioritizationValidationError,
        validate_prioritization,
    )

    output = build_prioritization_from_loaded_inputs(
        default_loaded_inputs(), tmp_path / "output"
    ).output_directory
    path = output / "mechanical-overlap-clusters.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    first = json.loads(lines[0])
    members = list(first["member_opportunity_ids"])
    members.append(members[0])
    first["member_opportunity_ids"] = sorted(set(members))
    first["member_count"] = len(first["member_opportunity_ids"])
    lines[0] = canonical_json_bytes(first).decode("utf-8")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        validate_prioritization(output)
    except PrioritizationValidationError:
        return
    raise AssertionError("tampered overlap cluster was accepted")
