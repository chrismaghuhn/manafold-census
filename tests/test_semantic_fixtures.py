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

from manafold_census.semantic.bundle import RequirementBundleV1
from manafold_census.semantic.identity import (
    reviewed_claim_digest_for,
    reviewed_claim_payload_for,
)
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
