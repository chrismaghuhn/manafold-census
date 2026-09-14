from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from capability_m3_fixtures import (
    record_with_other_requirement,
    record_with_proposed_requirement,
    unresolved_record_without_bundle,
    write_synthetic_m3,
)

from manafold_census.canonical import canonical_json_bytes
from manafold_census.capability.admissibility import (
    admissibility_claim_payload,
    admissibility_record_id_for,
    admissibility_review_digest_for,
)
from manafold_census.capability.build import build_reference_m4
from manafold_census.capability.candidates import (
    CandidateClusterStatusV1,
    CandidateClusterV1,
    group_requirement_candidates,
)
from manafold_census.capability.evolution import (
    CapabilityEvolutionV1,
    CapabilityRelationKindV1,
    EvolutionOperationV1,
    addition_event,
    merge_event,
    retirement_event,
    split_event,
    supersession_event,
    validate_capability_edges,
)
from manafold_census.capability.identity import (
    capability_claim_digest_for,
    capability_family_id_for,
)
from manafold_census.capability.input import load_m3_requirement_corpus
from manafold_census.capability.link_build import composition_member_link, direct_link
from manafold_census.capability.link_validation import (
    validate_active_link,
    validate_mapping_candidates,
)
from manafold_census.capability.mapping import mapping_decision
from manafold_census.capability.model import CapabilityRefV1
from manafold_census.capability.relations import CapabilityRelationV1
from manafold_census.capability.review import (
    review_claim_payload,
    review_digest_for,
    review_record_id_for,
)
from manafold_census.capability.validate import validate_m4_inputs
from manafold_census.digest import sha256_bytes
from manafold_census.semantic.kinds import RequirementKindV1
from manafold_census.semantic.model import (
    ResolutionReasonV1,
    ResolutionStateV1,
    ResolutionV1,
    ReviewStatusV1,
)

REVIEW_REF = "mrv_" + "0" * 64


def test_capability_identity_and_versioning_are_separate_contracts() -> None:
    from test_capability_definition import _definition, _draw_claim
    from test_capability_evolution import _claim

    base = _draw_claim()
    dimension_changed = replace(base, dimensions=())
    version_changed = replace(base, capability_version=2)
    different_nucleus = _claim(kind=RequirementKindV1.DEAL_DAMAGE)

    assert capability_family_id_for(base.family_key) == capability_family_id_for(
        dimension_changed.family_key
    )
    assert capability_claim_digest_for(base) != capability_claim_digest_for(
        dimension_changed
    )
    assert version_changed.capability_version == 2
    assert capability_family_id_for(base.family_key) == capability_family_id_for(
        version_changed.family_key
    )
    assert capability_claim_digest_for(base) != capability_claim_digest_for(
        version_changed
    )
    assert capability_family_id_for(base.family_key) != capability_family_id_for(
        different_nucleus.family_key
    )

    first = _definition(claim=base, display_name="first name")
    renamed = _definition(claim=base, display_name="second name")
    assert first.capability_ref == renamed.capability_ref
    assert first.claim_digest == renamed.claim_digest


def test_review_and_admissibility_digests_exclude_derived_fields() -> None:
    from test_capability_admissibility import _accepted_record, _requirement
    from test_capability_review import _record

    review = _record()
    assert review.review_digest == review_digest_for(review)
    assert review.record_id == review_record_id_for(review)
    review_payload = review_claim_payload(review)
    assert "record_id" not in review_payload
    assert "review_digest" not in review_payload

    admissibility = _accepted_record(_requirement())
    assert admissibility.review_digest == admissibility_review_digest_for(admissibility)
    assert admissibility.record_id == admissibility_record_id_for(admissibility)
    admissibility_payload = admissibility_claim_payload(admissibility)
    assert "record_id" not in admissibility_payload
    assert "review_digest" not in admissibility_payload

    stale_review = review.to_wire()
    stale_review["record_id"] = "mrv_" + "f" * 64
    with pytest.raises(ValueError, match="record_id"):
        type(review).from_wire(stale_review)

    stale_admissibility = admissibility.to_wire()
    stale_admissibility["review_digest"] = "f" * 64
    with pytest.raises(ValueError, match="review_digest"):
        type(admissibility).from_wire(stale_admissibility)


def _active_link_for(requirement, capability, admissibility):
    from test_capability_link import _link_review, _quantity_binding

    link = direct_link(
        requirement=requirement,
        capability=capability,
        m3_manifest_sha256="a" * 64,
        admissibility=admissibility,
        parameter_bindings=(_quantity_binding(),),
    )
    review = _link_review(link)
    return replace(link, review_ref=review.record_id), review


def test_active_link_routes_preserve_m2_and_m4_authority_boundaries() -> None:
    from test_capability_link import _capability, _requirement, _sra

    proposed = _requirement()
    capability = _capability()
    active, review = _active_link_for(proposed, capability, _sra(proposed))
    validate_active_link(
        active,
        proposed,
        capability,
        reviews=(review,),
        admissibility_record=_sra(proposed),
    )

    accepted = _requirement(status=ReviewStatusV1.ACCEPTED)
    terminal, terminal_review = _active_link_for(accepted, capability, None)
    validate_active_link(
        terminal,
        accepted,
        capability,
        reviews=(terminal_review,),
    )


@pytest.mark.parametrize(
    "requirement",
    [
        pytest.param(
            __import__("test_capability_link")._requirement(
                status=ReviewStatusV1.REJECTED
            ),
            id="rejected",
        ),
        pytest.param(
            __import__("test_capability_link")._requirement(
                resolution=ResolutionV1(
                    ResolutionStateV1.PARTIAL,
                    ResolutionReasonV1.UNKNOWN_SEMANTICS,
                    ("/parameters/quantity",),
                )
            ),
            id="partial",
        ),
        pytest.param(
            __import__("test_capability_link")._requirement(
                resolution=ResolutionV1(
                    ResolutionStateV1.UNRESOLVED,
                    ResolutionReasonV1.CONFLICTING_INTERPRETATIONS,
                    ("/parameters/quantity",),
                )
            ),
            id="unresolved",
        ),
    ],
)
def test_rejected_or_incomplete_requirements_never_enable_active_links(
    requirement,
) -> None:
    from test_capability_link import _capability

    capability = _capability()
    link, review = _active_link_for(requirement, capability, None)

    with pytest.raises(ValueError, match="admissible|rejected|complete"):
        validate_active_link(link, requirement, capability, reviews=(review,))


def _reviewed_mapping_inputs(tmp_path: Path):
    from test_capability_validate import _active_definition_and_links

    m3_input = write_synthetic_m3(
        tmp_path / "m3",
        records=(record_with_proposed_requirement(0), record_with_other_requirement(1)),
    )
    corpus = load_m3_requirement_corpus(m3_input)
    definition, definition_review, links, link_reviews, admissibility = (
        _active_definition_and_links(corpus, 2)
    )
    decisions = tuple(
        mapping_decision(
            requirement,
            "MAPPED",
            None,
            m3_analysis_manifest_sha256=corpus.m3_analysis_manifest_sha256,
            active_link_ids=(link.link_id,),
        )
        for requirement, link in zip(corpus.requirements, links, strict=True)
    )
    return (
        m3_input,
        corpus,
        definition,
        definition_review,
        links,
        link_reviews,
        admissibility,
        decisions,
    )


def test_requirement_coverage_and_explicit_ambiguity_are_closed(tmp_path: Path) -> None:
    (
        m3_input,
        corpus,
        definition,
        definition_review,
        links,
        link_reviews,
        admissibility,
        decisions,
    ) = _reviewed_mapping_inputs(tmp_path)

    validate_m4_inputs(
        corpus,
        None,
        None,
        (definition,),
        (definition_review, *link_reviews),
        (),
        admissibility,
        links,
        decisions,
        (),
    )
    result = build_reference_m4(
        m3_input,
        None,
        None,
        (definition,),
        (definition_review, *link_reviews),
        (),
        admissibility,
        links,
        decisions,
        (),
        tmp_path / "output",
    )
    assert len(result.mapping_decisions) == len(corpus.requirements) == 2
    assert {link.capability for link in result.links} == {definition.capability_ref}

    with pytest.raises(ValueError, match="duplicate mapping decision"):
        validate_m4_inputs(
            corpus,
            None,
            None,
            (definition,),
            (definition_review, *link_reviews),
            (),
            admissibility,
            links,
            decisions + (decisions[0],),
            (),
        )

    from test_capability_link import _capability, _requirement, _sra

    requirement = _requirement()
    first = direct_link(
        requirement=requirement,
        capability=_capability(),
        m3_manifest_sha256="a" * 64,
        admissibility=_sra(requirement),
    )
    second = direct_link(
        requirement=requirement,
        capability=_capability(required=False),
        m3_manifest_sha256="a" * 64,
        admissibility=_sra(requirement),
    )
    assert validate_mapping_candidates((first, second)).is_ambiguous is True


def test_unresolved_without_bundle_is_not_a_requirement_and_member_needs_context(
    tmp_path: Path,
) -> None:
    loaded = load_m3_requirement_corpus(
        write_synthetic_m3(
            tmp_path / "m3",
            records=(unresolved_record_without_bundle(),),
        )
    )
    assert loaded.requirements == ()

    from test_capability_link import _capability, _requirement, _sra

    requirement = _requirement()
    with pytest.raises((TypeError, ValueError), match="context"):
        composition_member_link(
            requirement=requirement,
            capability=_capability(),
            m3_manifest_sha256="a" * 64,
            admissibility=_sra(requirement),
            composition_context=None,  # type: ignore[arg-type]
        )


def _ref(index: int) -> CapabilityRefV1:
    digit = format(index, "x")
    return CapabilityRefV1("capfam_" + digit * 64, 1, digit * 64)


def test_evolution_operation_cardinalities_are_closed() -> None:
    first, second, third = _ref(1), _ref(2), _ref(3)
    valid = (
        addition_event(first, review_ref=REVIEW_REF),
        split_event(first, (second, third), review_ref=REVIEW_REF),
        merge_event((first, second), third, review_ref=REVIEW_REF),
        supersession_event(first, second, review_ref=REVIEW_REF),
        retirement_event(first, review_ref=REVIEW_REF),
    )
    assert {event.operation for event in valid} == set(EvolutionOperationV1)

    invalid = (
        (EvolutionOperationV1.ADDITION, (first,), (second,)),
        (EvolutionOperationV1.SPLIT, (), (second, third)),
        (EvolutionOperationV1.MERGE, (first,), (third,)),
        (EvolutionOperationV1.SUPERSESSION, (first, second), (third,)),
        (EvolutionOperationV1.RETIREMENT, (first,), (second,)),
    )
    for operation, old, new in invalid:
        with pytest.raises(ValueError):
            CapabilityEvolutionV1.create(
                operation=operation,
                from_references=old,
                to_references=new,
                review_ref=REVIEW_REF,
            )


@pytest.mark.parametrize("relation_kind", tuple(CapabilityRelationKindV1))
def test_each_semantic_relation_graph_rejects_cycles(
    relation_kind: CapabilityRelationKindV1,
) -> None:
    first, second = _ref(1), _ref(2)
    fields = (
        {"component_key": "part", "ordinal": 0, "required": True}
        if relation_kind is CapabilityRelationKindV1.COMPOSES
        else {}
    )
    forward = CapabilityRelationV1.create(
        relation_kind=relation_kind,
        from_capability=first,
        to_capability=second,
        **fields,
    )
    backward = CapabilityRelationV1.create(
        relation_kind=relation_kind,
        from_capability=second,
        to_capability=first,
        **fields,
    )
    with pytest.raises(ValueError, match="cycle"):
        validate_capability_edges((forward, backward))


def test_relation_persistence_is_canonical_and_reread(tmp_path: Path) -> None:
    from test_capability_build import empty_m3_input
    from test_capability_definition import _definition, _draw_claim
    from test_capability_evolution import requires_edge

    first = _definition()
    second = _definition(
        claim=replace(_draw_claim(), capability_version=2),
        display_name="Synthetic dependency",
    )
    relation = requires_edge(first, second)
    result = build_reference_m4(
        empty_m3_input(tmp_path / "m3"),
        None,
        None,
        (first, second),
        (),
        (relation,),
        (),
        (),
        (),
        (),
        tmp_path / "m4",
    )
    path = result.output_dir / "capability-relations.jsonl"
    raw = path.read_bytes()
    assert raw == canonical_json_bytes(json.loads(raw)) + b"\n"
    assert CapabilityRelationV1.from_wire(json.loads(raw)) == relation
    assert result.manifest.relation_file.sha256 == sha256_bytes(raw)


def test_candidate_policy_partitions_variations_and_stays_proposal_only() -> None:
    from test_capability_candidates import (
        _choose_mode_requirement,
        _damage_requirement,
        _draw_requirement,
        candidate_grouping_policy,
        corpus_for_requirements,
    )

    same_operation = group_requirement_candidates(
        corpus_for_requirements(
            (_draw_requirement(2), _draw_requirement(3, other_source=True))
        ),
        candidate_grouping_policy(),
    )
    assert len(same_operation.clusters) == 1

    different_operation = group_requirement_candidates(
        corpus_for_requirements((_draw_requirement(), _damage_requirement())),
        candidate_grouping_policy(),
    )
    assert len(different_operation.clusters) == 2

    opaque = group_requirement_candidates(
        corpus_for_requirements(
            (
                _choose_mode_requirement(),
                _choose_mode_requirement("second", other_source=True),
            )
        ),
        candidate_grouping_policy(),
    )
    assert len(opaque.clusters) == 2

    unknown_path = group_requirement_candidates(
        corpus_for_requirements(
            (
                _choose_mode_requirement(unknown_path="/parameters/alternatives"),
                _choose_mode_requirement(
                    unknown_path="/parameters/minimum", other_source=True
                ),
            )
        ),
        candidate_grouping_policy(),
    )
    assert len(unknown_path.clusters) == 2

    cluster = same_operation.clusters[0]
    assert cluster.status is CandidateClusterStatusV1.PROPOSED
    assert cluster.capability_definition is None
    invalid_status = cluster.to_wire()
    invalid_status["status"] = "ACTIVE"
    with pytest.raises(ValueError, match="status"):
        CandidateClusterV1.from_wire(invalid_status)


def test_stale_inputs_duplicates_and_partial_publication_fail_closed(
    tmp_path: Path,
) -> None:
    from test_capability_build import (
        build_synthetic_m4_with_stale_link,
        empty_m3_input,
    )
    from test_capability_definition import _definition, _draw_claim
    from test_capability_link import _capability, _requirement, _sra

    from manafold_census.capability.build import CapabilityBuildError

    m3_input = write_synthetic_m3(
        tmp_path / "m3",
        records=(record_with_proposed_requirement(),),
    )
    with pytest.raises(ValueError, match="M3 manifest"):
        load_m3_requirement_corpus(
            replace(m3_input, expected_analysis_manifest_sha256="f" * 64)
        )

    requirement = _requirement()
    capability = _capability()
    link, review = _active_link_for(requirement, capability, _sra(requirement))
    with pytest.raises(ValueError, match="Requirement wire digest"):
        validate_active_link(
            link,
            _requirement(
                resolution=ResolutionV1(
                    ResolutionStateV1.PARTIAL,
                    ResolutionReasonV1.UNKNOWN_SEMANTICS,
                    ("/parameters/quantity",),
                )
            ),
            capability,
            reviews=(review,),
            admissibility_record=_sra(requirement),
        )
    with pytest.raises(ValueError, match="Capability"):
        validate_active_link(
            link,
            requirement,
            _capability(required=False),
            reviews=(review,),
            admissibility_record=_sra(requirement),
        )

    duplicate = _definition()
    corpus = load_m3_requirement_corpus(empty_m3_input(tmp_path / "empty"))
    with pytest.raises(ValueError, match="duplicate Capability"):
        validate_m4_inputs(
            corpus,
            None,
            None,
            (duplicate, duplicate),
            (),
            (),
            (),
            (),
            (),
            (),
        )
    different_claim = _definition(
        claim=replace(_draw_claim(), m2_interpretation_version="2")
    )
    with pytest.raises(ValueError, match="family.*version"):
        validate_m4_inputs(
            corpus,
            None,
            None,
            (duplicate, different_claim),
            (),
            (),
            (),
            (),
            (),
            (),
        )

    output = tmp_path / "failed"
    with pytest.raises(CapabilityBuildError):
        build_synthetic_m4_with_stale_link(
            output,
            m3_input=write_synthetic_m3(
                tmp_path / "stale-m3",
                records=(record_with_proposed_requirement(),),
            ),
            parent_m4_manifest_sha256=None,
            parent_m4_manifest=None,
        )
    assert not (output / "m4-ontology-manifest.json").exists()


def test_ci_runs_bounded_m4_commands_after_bounded_m3() -> None:
    workflow = (
        Path(__file__).parents[1] / ".github" / "workflows" / "ci.yml"
    ).read_text(encoding="utf-8")
    m3_report = workflow.index("Report bounded synthetic M3")
    for command in (
        "Build bounded synthetic M4",
        "Check bounded synthetic M4",
        "Report bounded synthetic M4",
    ):
        position = workflow.index(command)
        assert position > m3_report
        assert "--synthetic" in workflow[position : position + 180]
