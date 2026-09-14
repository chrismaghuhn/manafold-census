from __future__ import annotations

from dataclasses import replace

import pytest
from analysis_fixtures import source_ref

from manafold_census.canonical import canonical_json_bytes
from manafold_census.capability.candidates import (
    CandidateClusterStatusV1,
    CandidateClusterV1,
    CandidateGroupingPolicyV1,
    CandidateGroupingRuleV1,
    candidate_id_for,
    group_requirement_candidates,
    import_pinned_candidate_proposals,
    validate_candidate_grouping_policy,
)
from manafold_census.capability.dimensions import (
    M2DimensionPathV1,
    registered_paths_for,
)
from manafold_census.capability.identity import requirement_set_digest_for
from manafold_census.capability.input import M3RequirementCorpusV1
from manafold_census.digest import sha256_bytes
from manafold_census.semantic.evidence import StructuralFieldEvidenceV1
from manafold_census.semantic.kind_payloads import (
    DealDamageParametersV1,
    DrawCardsParametersV1,
)
from manafold_census.semantic.kinds import (
    RequirementFamilyV1,
    RequirementKindV1,
    family_for_kind,
)
from manafold_census.semantic.model import (
    DerivationMethodV1,
    DerivationV1,
    ProvenanceV1,
    RequirementV1,
    ResolutionReasonV1,
    ResolutionStateV1,
    ResolutionV1,
    ReviewStatusV1,
    ReviewV1,
)
from manafold_census.semantic.primitives import (
    EntityRefV1,
    EntityRoleV1,
    MultiplicityV1,
    QuantityModeV1,
    QuantityV1,
    UnknownReasonV1,
    UnknownValueV1,
)
from manafold_census.validation import SchemaValidationError, validate_document

M3_SHA256 = "a" * 64


def _draw_requirement(
    quantity: int = 2,
    *,
    drawer: EntityRoleV1 = EntityRoleV1.CONTROLLER,
    other_source: bool = False,
    unknown_quantity: bool = False,
) -> RequirementV1:
    source = source_ref(
        oracle_id=(
            "abcdefab-abcd-4abc-8abc-abcdefabcdea"
            if other_source
            else "abcdefab-abcd-4abc-8abc-abcdefabcdef"
        )
    )
    quantity_value = (
        QuantityV1(
            QuantityModeV1.UNKNOWN,
            UnknownValueV1(UnknownReasonV1.UNKNOWN_SEMANTICS, "fixture"),
        )
        if unknown_quantity
        else QuantityV1(QuantityModeV1.EXACT, quantity)
    )
    return RequirementV1.create(
        source=source,
        family=RequirementFamilyV1.EFFECT,
        kind=RequirementKindV1.DRAW_CARDS,
        parameters=DrawCardsParametersV1(
            EntityRefV1(drawer, MultiplicityV1.ONE, None),
            quantity_value,
        ),
        evidence=(StructuralFieldEvidenceV1(source, "oracle_text", None, "Draw"),),
        provenance=ProvenanceV1(
            (DerivationV1(DerivationMethodV1.PARSER, "candidate-test", "1"),)
        ),
        review=ReviewV1(ReviewStatusV1.PROPOSED, None, None),
        resolution=ResolutionV1(
            ResolutionStateV1.PARTIAL
            if unknown_quantity
            else ResolutionStateV1.COMPLETE,
            ResolutionReasonV1.UNKNOWN_SEMANTICS
            if unknown_quantity
            else ResolutionReasonV1.NONE,
            ("/parameters/quantity",) if unknown_quantity else (),
        ),
    )


def _damage_requirement() -> RequirementV1:
    source = source_ref(
        oracle_id="abcdefab-abcd-4abc-8abc-abcdefabcdea",
        source_card_id="abcdefab-abcd-4abc-8abc-abcdefabcdec",
        source_record_sha256="c" * 64,
    )
    return RequirementV1.create(
        source=source,
        family=RequirementFamilyV1.EFFECT,
        kind=RequirementKindV1.DEAL_DAMAGE,
        parameters=DealDamageParametersV1(
            EntityRefV1(EntityRoleV1.SOURCE, MultiplicityV1.ONE, None),
            EntityRefV1(EntityRoleV1.TARGET, MultiplicityV1.ONE, None),
            QuantityV1(QuantityModeV1.EXACT, 2),
        ),
        evidence=(StructuralFieldEvidenceV1(source, "oracle_text", None, "Damage"),),
        provenance=ProvenanceV1(
            (DerivationV1(DerivationMethodV1.PARSER, "candidate-test", "1"),)
        ),
        review=ReviewV1(ReviewStatusV1.PROPOSED, None, None),
        resolution=ResolutionV1(
            ResolutionStateV1.COMPLETE,
            ResolutionReasonV1.NONE,
            (),
        ),
    )


def corpus_for_requirements(
    requirements: tuple[RequirementV1, ...],
) -> M3RequirementCorpusV1:
    ordered = tuple(sorted(requirements, key=lambda item: item.requirement_id))
    return M3RequirementCorpusV1(
        m3_analysis_manifest_sha256=M3_SHA256,
        m3_analysis_schema="census.card-analysis.v1",
        m2_requirement_schema="census.semantic-requirement.v1",
        m2_bundle_schema="census.semantic-requirement-bundle.v1",
        requirements=ordered,
        requirement_set_digest=requirement_set_digest_for(M3_SHA256, ordered),
        m3_record_count=len(ordered),
        requirements_produced_card_count=len(ordered),
        no_requirements_applicable_count=0,
        unresolved_analysis_count=0,
    )


def candidate_grouping_policy() -> CandidateGroupingPolicyV1:
    rules = []
    for kind in RequirementKindV1:
        if kind is RequirementKindV1.UNRESOLVED:
            continue
        family = family_for_kind(kind)
        paths = registered_paths_for(family, kind)
        dimensions = (
            (M2DimensionPathV1.DRAW_CARDS_QUANTITY,)
            if kind is RequirementKindV1.DRAW_CARDS
            else ()
        )
        rules.append(
            CandidateGroupingRuleV1(
                family,
                kind,
                dimensions,
                tuple(path for path in paths if path not in dimensions),
            )
        )
    return CandidateGroupingPolicyV1("1", tuple(rules))


def policy_with_duplicate_or_overlapping_paths() -> CandidateGroupingPolicyV1:
    policy = candidate_grouping_policy()
    draw = next(
        rule for rule in policy.rules if rule.kind is RequirementKindV1.DRAW_CARDS
    )
    duplicate = replace(
        draw,
        dimension_paths=(M2DimensionPathV1.DRAW_CARDS_QUANTITY,) * 2,
    )
    return replace(
        policy,
        rules=tuple(duplicate if rule is draw else rule for rule in policy.rules),
    )


def policy_with_changed_partition_rule() -> CandidateGroupingPolicyV1:
    policy = candidate_grouping_policy()
    draw = next(
        rule for rule in policy.rules if rule.kind is RequirementKindV1.DRAW_CARDS
    )
    changed = replace(
        draw,
        dimension_paths=(
            M2DimensionPathV1.DRAW_CARDS_DRAWER,
            M2DimensionPathV1.DRAW_CARDS_QUANTITY,
        ),
        partition_paths=(),
    )
    return CandidateGroupingPolicyV1(
        "2",
        tuple(changed if rule is draw else rule for rule in policy.rules),
    )


def test_quantity_variants_share_one_candidate_signature() -> None:
    first = _draw_requirement(quantity=2)
    second = _draw_requirement(quantity=3, other_source=True)
    result = group_requirement_candidates(
        corpus_for_requirements((first, second)), candidate_grouping_policy()
    )

    assert len(result.clusters) == 1
    assert result.clusters[0].distinct_source_count == 2
    assert result.clusters[0].requirement_count == 2


def test_different_operation_kinds_do_not_share_signature() -> None:
    result = group_requirement_candidates(
        corpus_for_requirements((_draw_requirement(), _damage_requirement())),
        candidate_grouping_policy(),
    )

    assert len(result.clusters) == 2


def test_cluster_is_not_a_capability_definition() -> None:
    cluster = group_requirement_candidates(
        corpus_for_requirements((_draw_requirement(),)), candidate_grouping_policy()
    ).clusters[0]

    assert cluster.status is CandidateClusterStatusV1.PROPOSED
    assert cluster.capability_definition is None


def test_candidate_identity_requires_the_frozen_m3_corpus() -> None:
    with pytest.raises(TypeError, match="M3RequirementCorpusV1"):
        group_requirement_candidates(
            (_draw_requirement(),),  # type: ignore[arg-type]
            candidate_grouping_policy(),
        )


def test_policy_partition_paths_prevent_semantic_overgrouping() -> None:
    first = _draw_requirement(quantity=2, drawer=EntityRoleV1.CONTROLLER)
    second = _draw_requirement(
        quantity=3,
        drawer=EntityRoleV1.OWNER,
        other_source=True,
    )

    result = group_requirement_candidates(
        corpus_for_requirements((first, second)), candidate_grouping_policy()
    )

    assert len(result.clusters) == 2


def test_unknown_observed_path_is_always_a_partition() -> None:
    result = group_requirement_candidates(
        corpus_for_requirements(
            (
                _draw_requirement(),
                _draw_requirement(unknown_quantity=True, other_source=True),
            )
        ),
        candidate_grouping_policy(),
    )

    assert len(result.clusters) == 2


def test_policy_rejects_duplicate_or_overlapping_paths() -> None:
    with pytest.raises(ValueError, match="candidate grouping policy"):
        group_requirement_candidates(
            corpus_for_requirements((_draw_requirement(),)),
            policy_with_duplicate_or_overlapping_paths(),
        )


def test_policy_digest_is_part_of_candidate_identity() -> None:
    corpus = corpus_for_requirements((_draw_requirement(),))
    first = group_requirement_candidates(corpus, candidate_grouping_policy())
    second = group_requirement_candidates(corpus, policy_with_changed_partition_rule())

    assert first.clusters[0].candidate_id != second.clusters[0].candidate_id


def test_policy_identity_is_part_of_group_signature() -> None:
    corpus = corpus_for_requirements((_draw_requirement(),))
    first = group_requirement_candidates(corpus, candidate_grouping_policy())
    second = group_requirement_candidates(
        corpus,
        CandidateGroupingPolicyV1("2", candidate_grouping_policy().rules),
    )

    assert (
        first.clusters[0].group_signature_digest
        != second.clusters[0].group_signature_digest
    )


def test_parameter_variations_preserve_typed_values_and_count() -> None:
    first = _draw_requirement(quantity=2)
    second = _draw_requirement(quantity=3, other_source=True)

    cluster = group_requirement_candidates(
        corpus_for_requirements((first, second)), candidate_grouping_policy()
    ).clusters[0]

    assert cluster.parameter_variations["dimensions"] == {
        "DRAW_CARDS_QUANTITY": {
            "distinct_count": 2,
            "values": [
                {"mode": "exact", "value": 2},
                {"mode": "exact", "value": 3},
            ],
        }
    }


def test_worklist_prefers_more_reusable_candidate_groups() -> None:
    result = group_requirement_candidates(
        corpus_for_requirements(
            (
                _draw_requirement(quantity=2),
                _draw_requirement(quantity=3, other_source=True),
                _damage_requirement(),
            )
        ),
        candidate_grouping_policy(),
    )

    assert result.worklist[0].requirement_count == 2
    assert result.worklist[0].distinct_source_count == 2


def test_pinned_proposal_rejects_cluster_with_stale_input_identity() -> None:
    corpus = corpus_for_requirements((_draw_requirement(),))
    cluster = group_requirement_candidates(
        corpus, candidate_grouping_policy()
    ).clusters[0]
    stale_cluster = replace(
        cluster,
        m3_analysis_manifest_sha256="b" * 64,
        candidate_id=candidate_id_for(
            m3_analysis_manifest_sha256="b" * 64,
            requirement_set_digest=cluster.requirement_set_digest,
            policy_version=cluster.policy_version,
            policy_digest=cluster.policy_digest,
            generator_id=cluster.generator_id,
            generator_version=cluster.generator_version,
            group_signature_digest=cluster.group_signature_digest,
            requirement_ids=cluster.requirement_ids,
        ),
    )
    raw = canonical_json_bytes(
        {
            "schema": "census.capability-candidate-proposals.v1",
            "generator_id": cluster.generator_id,
            "generator_version": cluster.generator_version,
            "input_m3_analysis_manifest_sha256": M3_SHA256,
            "input_requirement_set_digest": cluster.requirement_set_digest,
            "status": "PROPOSED",
            "candidates": [stale_cluster.to_wire()],
        }
    )

    with pytest.raises(ValueError, match="input identity"):
        import_pinned_candidate_proposals(
            raw,
            expected_sha256=sha256_bytes(raw),
            expected_m3_analysis_manifest_sha256=M3_SHA256,
            expected_requirement_set_digest=cluster.requirement_set_digest,
            enabled=True,
        )


def test_pinned_proposal_accepts_exact_canonical_cluster() -> None:
    corpus = corpus_for_requirements((_draw_requirement(),))
    cluster = group_requirement_candidates(
        corpus, candidate_grouping_policy()
    ).clusters[0]
    raw = canonical_json_bytes(
        {
            "schema": "census.capability-candidate-proposals.v1",
            "generator_id": cluster.generator_id,
            "generator_version": cluster.generator_version,
            "input_m3_analysis_manifest_sha256": M3_SHA256,
            "input_requirement_set_digest": cluster.requirement_set_digest,
            "status": "PROPOSED",
            "candidates": [cluster.to_wire()],
        }
    )

    assert import_pinned_candidate_proposals(
        raw,
        expected_sha256=sha256_bytes(raw),
        expected_m3_analysis_manifest_sha256=M3_SHA256,
        expected_requirement_set_digest=cluster.requirement_set_digest,
        enabled=True,
    ) == (cluster,)


def test_candidate_policy_round_trip_is_canonical() -> None:
    policy = candidate_grouping_policy()

    assert CandidateGroupingPolicyV1.from_wire(policy.to_wire()) == policy
    validate_candidate_grouping_policy(policy)
    validate_document(policy.to_wire(), "candidate-grouping-policy.v1.schema.json")


def test_candidate_cluster_wire_round_trip_is_proposal_only() -> None:
    cluster = group_requirement_candidates(
        corpus_for_requirements((_draw_requirement(),)), candidate_grouping_policy()
    ).clusters[0]

    assert CandidateClusterV1.from_wire(cluster.to_wire()) == cluster
    validate_document(cluster.to_wire(), "capability-candidate-cluster.v1.schema.json")
    assert cluster.capability_definition is None


def test_candidate_variation_wire_rejects_stale_count() -> None:
    cluster = group_requirement_candidates(
        corpus_for_requirements((_draw_requirement(),)), candidate_grouping_policy()
    ).clusters[0]
    wire = cluster.to_wire()
    variations = wire["parameter_variations"]
    assert isinstance(variations, dict)
    dimensions = variations["dimensions"]
    assert isinstance(dimensions, dict)
    quantity = dimensions["DRAW_CARDS_QUANTITY"]
    assert isinstance(quantity, dict)
    quantity["distinct_count"] = 2

    with pytest.raises(ValueError, match="stale count"):
        CandidateClusterV1.from_wire(wire)


def test_policy_schema_rejects_duplicate_rule_entries() -> None:
    policy = candidate_grouping_policy().to_wire()
    rules = policy["rules"]
    assert isinstance(rules, list)
    rules[-1] = rules[0]

    with pytest.raises(SchemaValidationError):
        validate_document(policy, "candidate-grouping-policy.v1.schema.json")


def test_pinned_proposal_import_is_disabled_by_default() -> None:
    from manafold_census.capability.candidates import import_pinned_candidate_proposals

    with pytest.raises(ValueError, match="disabled"):
        import_pinned_candidate_proposals(
            b"{}",
            expected_sha256="a" * 64,
            expected_m3_analysis_manifest_sha256=M3_SHA256,
            expected_requirement_set_digest="b" * 64,
        )
