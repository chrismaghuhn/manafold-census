import copy
import json
from pathlib import Path

import pytest
from semantic_fixture_review_report import (
    FIXTURE_PATH,
    PinnedEvidenceBlocked,
    load_fixture_cases,
    load_pinned_records,
)

from manafold_census.semantic.bundle import RelationshipTypeV1, RequirementBundleV1
from manafold_census.semantic.identity import (
    reviewed_claim_digest_for,
    reviewed_claim_payload_for,
)
from manafold_census.semantic.kinds import RequirementKindV1
from manafold_census.semantic.model import RequirementV1, ReviewStatusV1
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

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
REVIEW_REPORT_PATH = (
    REPOSITORY_ROOT / "dist" / "m2-semantic-fixture-review" / "task6a-review.json"
)
REVIEW_DECISIONS_PATH = (
    REPOSITORY_ROOT / "dist" / "m2-semantic-fixture-review" / "task6b-decisions.json"
)


def _loaded_fixture_state():
    try:
        cases = load_fixture_cases()
        records, lock_digest = load_pinned_records(cases)
    except PinnedEvidenceBlocked as error:
        pytest.skip(f"BLOCKED_EXTERNAL_EVIDENCE: {error}")
    return cases, records, lock_digest


def _fixture_requirements():
    requirements = {}
    for case in load_fixture_cases():
        bundle = RequirementBundleV1.from_wire(case["bundle"])
        for requirement in bundle.requirements:
            requirements[requirement.requirement_id] = (case, bundle, requirement)
    return requirements


def _review_artifacts():
    missing = [
        str(path)
        for path in (REVIEW_REPORT_PATH, REVIEW_DECISIONS_PATH)
        if not path.is_file()
    ]
    if missing:
        pytest.skip(
            "BLOCKED_EXTERNAL_EVIDENCE: missing workflow artifact(s): "
            + ", ".join(missing)
        )
    report = json.loads(REVIEW_REPORT_PATH.read_text(encoding="utf-8"))
    decisions_document = json.loads(REVIEW_DECISIONS_PATH.read_text(encoding="utf-8"))
    report_by_id = {
        item["requirement_id"]: (case, item)
        for case in report
        for item in case["requirements"]
    }
    decisions_by_id = {
        item["requirement_id"]: item for item in decisions_document["decisions"]
    }
    return report, decisions_document, report_by_id, decisions_by_id


def _require_external_decision(requirement_id, decisions_by_id):
    decision = decisions_by_id.get(requirement_id)
    if decision is None:
        raise ValueError("external human decision missing")
    return decision


def test_fixture_wrapper_is_small_complete_and_source_free() -> None:
    cases = load_fixture_cases()
    assert len(cases) <= 12
    assert {case["case_id"] for case in cases} == EXPECTED_CASE_IDS
    text = FIXTURE_PATH.read_text(encoding="utf-8")
    assert "card_name_for_reviewer" not in text
    assert "raw_source" not in text
    assert "card_faces" not in text


def test_committed_terminal_fixture_is_hermetic_and_schema_valid() -> None:
    requirements = _fixture_requirements()
    statuses = [item[2].review.status for item in requirements.values()]
    assert len(requirements) == 18
    assert statuses.count(ReviewStatusV1.ACCEPTED) == 17
    assert statuses.count(ReviewStatusV1.REJECTED) == 1
    for _, bundle, requirement in requirements.values():
        validate_document(
            bundle.to_wire(), "semantic-requirement-bundle.v1.schema.json"
        )
        assert requirement.review.status in (
            ReviewStatusV1.ACCEPTED,
            ReviewStatusV1.REJECTED,
        )
        assert requirement.review.reviewed_by == "github:chrismaghuhn"
        assert requirement.review.reviewed_claim_digest == reviewed_claim_digest_for(
            requirement
        )


def test_every_fixture_bundle_is_source_aware_valid() -> None:
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
            in (
                ReviewStatusV1.PROPOSED,
                ReviewStatusV1.IN_REVIEW,
                ReviewStatusV1.ACCEPTED,
                ReviewStatusV1.REJECTED,
            )
            for requirement in bundle.requirements
        )


def test_fixture_matrix_contains_partial_unresolved_and_conflicting_proposals() -> None:
    cases = load_fixture_cases()
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
    cases = load_fixture_cases()
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
    trigger = next(
        item
        for item in hypothesizzle.requirements
        if item.kind is RequirementKindV1.TRIGGER_FROM_EVENT
    )
    conditional = next(
        item
        for item in hypothesizzle.requirements
        if item.kind is RequirementKindV1.CONDITIONAL_EFFECT
    )
    assert trigger.review.status is ReviewStatusV1.ACCEPTED
    assert conditional.review.status is ReviewStatusV1.REJECTED

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
    cases = load_fixture_cases()
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


def test_task6a_report_binds_exact_claim_projection_after_task6b() -> None:
    report = _review_artifacts()[0]
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
            assert requirement.review.status in (
                ReviewStatusV1.ACCEPTED,
                ReviewStatusV1.REJECTED,
            )


def test_task6b_applies_only_exact_external_decisions_and_preserves_claims() -> None:
    report, decisions_document, report_by_id, decisions_by_id = _review_artifacts()
    requirements = _fixture_requirements()
    assert len(report_by_id) == len(decisions_by_id) == len(requirements) == 18
    assert decisions_document["human_review_authority"]["reviewed_by"] == (
        "github:chrismaghuhn"
    )
    for requirement_id, (case, bundle, requirement) in requirements.items():
        report_case, report_item = report_by_id[requirement_id]
        decision = decisions_by_id[requirement_id]
        assert report_case["case_id"] == case["case_id"]
        assert decision["requirement_id"] == report_item["requirement_id"]
        assert decision["review_status"] == decision["decision"]
        assert decision["correction_request"] is None
        assert decision["reviewed_by"] == "github:chrismaghuhn"
        assert requirement.review.status.value == decision["decision"]
        assert requirement.review.reviewed_by == decision["reviewed_by"]
        assert (
            requirement.review.reviewed_claim_digest
            == (decision["reviewed_claim_digest"])
        )
        assert (
            reviewed_claim_digest_for(requirement)
            == (report_item["candidate_reviewed_claim_digest"])
        )
        assert (
            reviewed_claim_digest_for(requirement)
            == (decision["reviewed_claim_digest"])
        )
        assert (
            reviewed_claim_payload_for(requirement)
            == report_item["reviewed_claim_payload"]
        )
        assert requirement.source.to_wire() == case["bundle"]["source"]
        assert requirement.family.value == report_item["proposed_family"]
        assert requirement.kind.value == report_item["proposed_kind"]
        assert requirement.parameters.to_wire() == report_item["proposed_parameters"]
        assert [item.to_wire() for item in requirement.evidence] == report_item[
            "canonical_evidence"
        ]
        assert (
            requirement.provenance.to_wire()
            == report_item["canonical_derivation_provenance"]
        )
        assert requirement.resolution.to_wire() == report_item["proposed_resolution"]
        assert [item.to_wire() for item in bundle.relationships] == report_case[
            "proposed_relationships"
        ]


def test_task6b_decision_set_is_terminal_and_exact() -> None:
    requirements = _fixture_requirements()
    statuses = [
        requirement.review.status for _, _, requirement in requirements.values()
    ]
    assert len(statuses) == 18
    assert statuses.count(ReviewStatusV1.ACCEPTED) == 17
    assert statuses.count(ReviewStatusV1.REJECTED) == 1
    assert ReviewStatusV1.PROPOSED not in statuses
    assert ReviewStatusV1.IN_REVIEW not in statuses


def test_task6b_preserves_accepted_partial_and_unresolved_claims() -> None:
    requirements = [item[2] for item in _fixture_requirements().values()]
    assert any(
        item.review.status is ReviewStatusV1.ACCEPTED
        and item.resolution.state.value == "PARTIAL"
        for item in requirements
    )
    assert any(
        item.review.status is ReviewStatusV1.ACCEPTED
        and item.resolution.state.value == "UNRESOLVED"
        and item.resolution.reason.value == "UNSUPPORTED_SHAPE"
        for item in requirements
    )


def test_task6b_requires_external_decision_for_terminal_review() -> None:
    requirements = _fixture_requirements()
    decisions = {}
    requirement_id = next(iter(requirements))
    with pytest.raises(ValueError, match="external human decision missing"):
        _require_external_decision(requirement_id, decisions)


@pytest.mark.parametrize("changed_dimension", ["evidence", "provenance", "resolution"])
def test_task6b_rejects_stale_terminal_review_binding(changed_dimension: str) -> None:
    requirements = _fixture_requirements()
    requirement = next(iter(requirements.values()))[2]
    decision = {
        "decision": requirement.review.status.value,
        "reviewed_by": requirement.review.reviewed_by,
        "reviewed_claim_digest": requirement.review.reviewed_claim_digest,
    }
    proposal_wire = copy.deepcopy(requirement.to_wire())
    proposal_wire["review"] = {
        "reviewed_by": None,
        "reviewed_claim_digest": None,
        "status": "PROPOSED",
    }
    if changed_dimension == "evidence":
        proposal_wire["evidence"][0]["fragment"] += "!"
    elif changed_dimension == "provenance":
        proposal_wire["provenance"]["derivations"][0]["producer_version"] = "2"
    else:
        proposal_wire["resolution"] = {
            "reason": "INSUFFICIENT_EVIDENCE",
            "state": "PARTIAL",
            "unknown_paths": ["/parameters.quantity"],
        }
    mutated_proposal = RequirementV1.from_wire(proposal_wire)
    assert (
        reviewed_claim_digest_for(mutated_proposal)
        != (decision["reviewed_claim_digest"])
    )
    proposal_wire["review"] = {
        "reviewed_by": decision["reviewed_by"],
        "reviewed_claim_digest": decision["reviewed_claim_digest"],
        "status": decision["decision"],
    }
    with pytest.raises(ValueError, match="reviewed_claim_digest"):
        RequirementV1.from_wire(proposal_wire)
