import json

import pytest
from semantic_fixture_review_report import (
    FIXTURE_PATH,
    PinnedEvidenceBlocked,
    build_review_report,
    load_fixture_cases,
    load_pinned_records,
    write_review_report,
)

from manafold_census.semantic.bundle import RelationshipTypeV1, RequirementBundleV1
from manafold_census.semantic.identity import (
    reviewed_claim_digest_for,
    reviewed_claim_payload_for,
)
from manafold_census.semantic.kinds import RequirementKindV1
from manafold_census.semantic.model import ReviewStatusV1
from manafold_census.semantic.validate import (
    validate_bundle_against_structural_record,
)
from manafold_census.validation import validate_document

EXPECTED_CASE_IDS = {
    "simple",
    "multiple_requirements",
    "modal_relationships",
    "multi_face",
    "keyword_unresolved",
    "trigger_condition",
    "replacement",
    "continuous_characteristic",
    "cost_and_cost_modification",
    "zone_and_object_creation",
    "selection_and_delayed",
    "outlier_partial_or_unresolved",
}


def _loaded_fixture_state():
    try:
        cases = load_fixture_cases()
        records, lock_digest = load_pinned_records(cases)
    except PinnedEvidenceBlocked as error:
        pytest.fail(str(error))
    return cases, records, lock_digest


def test_fixture_wrapper_is_small_complete_and_source_free() -> None:
    cases, _, _ = _loaded_fixture_state()
    assert len(cases) <= 12
    assert {case["case_id"] for case in cases} == EXPECTED_CASE_IDS
    text = FIXTURE_PATH.read_text(encoding="utf-8")
    assert "card_name_for_reviewer" not in text
    assert "raw_source" not in text
    assert "card_faces" not in text


def test_every_proposed_bundle_is_schema_and_source_aware_valid() -> None:
    cases, records, lock_digest = _loaded_fixture_state()
    for case in cases:
        bundle = RequirementBundleV1.from_wire(case["bundle"])
        validate_document(
            bundle.to_wire(), "semantic-requirement-bundle.v1.schema.json"
        )
        validate_bundle_against_structural_record(
            bundle, records[bundle.source.oracle_id], lock_digest
        )
        assert all(
            requirement.review.status
            in (ReviewStatusV1.PROPOSED, ReviewStatusV1.IN_REVIEW)
            for requirement in bundle.requirements
        )


def test_fixture_matrix_contains_partial_unresolved_and_conflicting_proposals() -> None:
    cases, _, _ = _loaded_fixture_state()
    bundles = [RequirementBundleV1.from_wire(case["bundle"]) for case in cases]
    assert any(
        requirement.resolution.state.value == "PARTIAL"
        for bundle in bundles
        for requirement in bundle.requirements
    )
    assert any(
        requirement.resolution.state.value == "UNRESOLVED"
        for bundle in bundles
        for requirement in bundle.requirements
    )
    assert any(
        relationship.relationship_type.value == "CONFLICTS_WITH"
        for bundle in bundles
        for relationship in bundle.relationships
    )


def test_hypothesizzle_is_the_authorized_conflict_case_and_shahrazad_is_not() -> None:
    cases, _, _ = _loaded_fixture_state()
    by_case = {
        case["case_id"]: RequirementBundleV1.from_wire(case["bundle"]) for case in cases
    }
    hypothesizzle = by_case["trigger_condition"]
    assert hypothesizzle.source.oracle_id == "e4e6cb61-f673-4f36-b95c-c84a68459503"
    assert {item.kind for item in hypothesizzle.requirements} == {
        RequirementKindV1.TRIGGER_FROM_EVENT,
        RequirementKindV1.CONDITIONAL_EFFECT,
    }
    assert len({item.requirement_id for item in hypothesizzle.requirements}) == 2
    assert [item.relationship_type for item in hypothesizzle.relationships] == [
        RelationshipTypeV1.CONFLICTS_WITH
    ]
    assert all(
        item.review.status is ReviewStatusV1.PROPOSED
        for item in hypothesizzle.requirements
    )

    shahrazad = by_case["outlier_partial_or_unresolved"]
    assert all(
        item.resolution.reason.value != "CONFLICTING_INTERPRETATIONS"
        for item in shahrazad.requirements
    )
    assert all(
        item.relationship_type is not RelationshipTypeV1.CONFLICTS_WITH
        for item in shahrazad.relationships
    )


def test_revision01_repairs_remain_pinned_for_living_cryptic_platinum_and_eerie() -> (
    None
):
    cases, _, _ = _loaded_fixture_state()
    by_case = {
        case["case_id"]: RequirementBundleV1.from_wire(case["bundle"]) for case in cases
    }

    living = by_case["multiple_requirements"]
    living_moves = [
        item
        for item in living.requirements
        if item.kind is RequirementKindV1.MOVE_BETWEEN_ZONES
    ]
    assert {
        (item.parameters.from_zone.zone.value, item.parameters.to_zone.zone.value)
        for item in living_moves
    } == {
        ("graveyard", "exile"),
        ("battlefield", "graveyard"),
        ("exile", "battlefield"),
    }
    assert all(
        relationship.relationship_type is RelationshipTypeV1.SEQUENCE_BEFORE
        for relationship in living.relationships
    )

    cryptic = by_case["modal_relationships"]
    choose = next(
        item
        for item in cryptic.requirements
        if item.kind is RequirementKindV1.CHOOSE_MODE
    )
    select = next(
        item for item in cryptic.requirements if item.kind is RequirementKindV1.SELECT
    )
    assert len(choose.parameters.alternatives) == 4
    assert choose.parameters.minimum.value == 2
    assert choose.parameters.maximum.value == 2
    assert select.parameters.targeting is True
    assert select.resolution.state.value == "PARTIAL"
    assert all(
        relationship.relationship_type is RelationshipTypeV1.PARENT_OF
        for relationship in cryptic.relationships
    )

    platinum = by_case["replacement"].requirements[0]
    assert platinum.kind is RequirementKindV1.UNRESOLVED
    assert platinum.resolution.reason.value == "UNSUPPORTED_SHAPE"

    eerie = by_case["selection_and_delayed"]
    selection = next(
        item for item in eerie.requirements if item.kind is RequirementKindV1.SELECT
    )
    delayed = next(
        item
        for item in eerie.requirements
        if item.kind is RequirementKindV1.CREATE_DELAYED_EFFECT
    )
    assert selection.parameters.quantity.mode.value == "symbolic"
    assert selection.parameters.quantity.value == "any number"
    assert selection.parameters.targeting is True
    assert set(selection.resolution.unknown_paths) == {
        "/parameters.quantity",
        "/parameters.restriction",
    }
    assert any(
        relationship.relationship_type is RelationshipTypeV1.SEQUENCE_BEFORE
        and relationship.from_requirement_id == selection.requirement_id
        and relationship.to_requirement_id == delayed.requirement_id
        for relationship in eerie.relationships
    )


def test_review_report_binds_exact_claim_projection_without_terminal_review() -> None:
    report = build_review_report()
    assert {case["case_id"] for case in report} == EXPECTED_CASE_IDS
    for case in report:
        assert case["review_status"] == "PROPOSED"
        for item in case["requirements"]:
            bundle_case = next(
                source_case
                for source_case in load_fixture_cases()
                if source_case["case_id"] == case["case_id"]
            )
            bundle = RequirementBundleV1.from_wire(bundle_case["bundle"])
            requirement = next(
                value
                for value in bundle.requirements
                if value.requirement_id == item["requirement_id"]
            )
            assert item["candidate_reviewed_claim_digest"] == reviewed_claim_digest_for(
                requirement
            )
            assert item["reviewed_claim_payload"] == reviewed_claim_payload_for(
                requirement
            )
            assert item["review_status"] == "PROPOSED"


def test_review_report_can_write_to_an_ignored_output_path(tmp_path) -> None:
    path = write_review_report(tmp_path / "task6a-review.json")
    assert path.is_file()
    assert json.loads(path.read_text(encoding="utf-8")) == build_review_report()
