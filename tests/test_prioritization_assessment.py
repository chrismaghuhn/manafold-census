from __future__ import annotations


def test_noise_classification_covers_all_four_classes() -> None:
    from manafold_census.prioritization._common import PlanningNoiseV1
    from manafold_census.prioritization.analyze import classify_planning_noise

    assert classify_planning_noise((None, None)) is PlanningNoiseV1.ALL_NULL
    assert (
        classify_planning_noise(("", "   ", "\t\n"))
        is PlanningNoiseV1.ALL_EMPTY_OR_WHITESPACE
    )
    assert (
        classify_planning_noise((None, "", "  ")) is PlanningNoiseV1.NULL_OR_EMPTY_ONLY
    )
    assert classify_planning_noise(("Draw a card.", None)) is PlanningNoiseV1.NONE
    assert classify_planning_noise(("Draw a card.", "Draw a card.")) is (
        PlanningNoiseV1.NONE
    )
    assert classify_planning_noise(()) is PlanningNoiseV1.NONE


def test_null_and_empty_surfaces_are_preserved_as_distinct() -> None:
    from prioritization_fixtures import noise_records, pipeline

    from manafold_census.prioritization.analyze import build_assessments

    surfaces, groups, opportunities = pipeline(noise_records())
    null_surfaces = [item for item in surfaces if item.raw_text is None]
    empty_surfaces = [item for item in surfaces if item.raw_text == ""]
    assert null_surfaces
    assert empty_surfaces
    surfaces_by_id = {item.surface_id: item for item in surfaces}
    assessments = build_assessments(groups, opportunities, surfaces_by_id)
    assert assessments


def test_all_recurring_opportunities_are_preserved_without_singletons() -> None:
    from prioritization_fixtures import default_pipeline

    from manafold_census.inventory.model import RecurrenceStatusV1
    from manafold_census.prioritization.analyze import build_assessments

    surfaces, groups, opportunities = default_pipeline()
    recurring = [
        item
        for item in groups
        if item.recurrence_status is RecurrenceStatusV1.RECURRING
    ]
    assert len(opportunities) == len(recurring)
    surfaces_by_id = {item.surface_id: item for item in surfaces}
    assessments = build_assessments(groups, opportunities, surfaces_by_id)
    assert len(assessments) == len(opportunities)
    assessed_groups = {item.candidate_group_id for item in assessments}
    assert assessed_groups == {item.group_id for item in recurring}


def test_semantic_fields_remain_unassessed_without_authority() -> None:
    from prioritization_fixtures import assessed_default

    _, assessments, _ = assessed_default()
    assert assessments
    for assessment in assessments:
        assert assessment.authority_scope == "NON_AUTHORITATIVE"
        assert assessment.semantic_impact == "UNASSESSED"
        assert assessment.semantic_uncertainty == "UNASSESSED"
        assert assessment.existing_capability_reuse == "UNASSESSED"
        assert assessment.new_capability_family == "UNASSESSED"
        assert assessment.contract_fit == "UNASSESSED"
        assert assessment.m7_fit == "UNASSESSED"
        assert assessment.semantic_disposition == "UNASSESSED"


def test_no_capability_requirement_or_mapping_objects_are_created() -> None:
    from prioritization_fixtures import assessed_default

    _, assessments, clusters = assessed_default()
    for item in (*assessments, *clusters):
        name = type(item).__name__
        assert not name.endswith("RequirementV1")
        assert not name.endswith("CapabilityDefinitionV1")
        assert "Mapping" not in name
        assert "mapping" not in item.to_wire()


def test_m4_context_remains_read_only_reviewer_context() -> None:
    from prioritization_fixtures import default_loaded_inputs

    loaded = default_loaded_inputs()
    assert loaded.m4_active_family_ids == ()
    wire_keys = set()
    for assessment in __import__(
        "manafold_census.prioritization.analyze", fromlist=["build_assessments"]
    ).build_assessments(
        loaded.groups,
        loaded.opportunities,
        {item.surface_id: item for item in loaded.surfaces},
    ):
        wire_keys |= set(assessment.to_wire())
    assert "capability_family_id" not in wire_keys
    assert "m4_mapping" not in wire_keys


def test_distinct_raw_text_count_treats_null_as_one_value() -> None:
    from manafold_census.prioritization.analyze import distinct_raw_text_count

    assert distinct_raw_text_count((None, None)) == 1
    assert distinct_raw_text_count((None, "")) == 2
    assert distinct_raw_text_count(("a", "a", "b")) == 2


def test_assessment_identity_is_deterministic_and_content_bound() -> None:
    from prioritization_fixtures import make_assessment

    first = make_assessment(1, oracle_ids=("oracle-b", "oracle-a"))
    second = make_assessment(1, oracle_ids=("oracle-a", "oracle-b"))
    assert first.assessment_id == second.assessment_id
    assert first.member_oracle_ids == ("oracle-a", "oracle-b")
    third = make_assessment(2, oracle_ids=("oracle-a", "oracle-b"))
    assert first.assessment_id != third.assessment_id
