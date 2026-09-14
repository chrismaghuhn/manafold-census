from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from capability_m3_fixtures import (
    record_with_proposed_requirement,
    source_for,
    unresolved_record_without_bundle,
    write_synthetic_m3,
)

from manafold_census.capability.admissibility import SourceRequirementAdmissibilityV1
from manafold_census.capability.build import build_reference_m4
from manafold_census.capability.definition import (
    CapabilityDefinitionV1,
    CapabilityLifecycleStateV1,
    CapabilityProvenanceV1,
    CapabilityRequirementProvenanceV1,
)
from manafold_census.capability.identity import (
    capability_claim_digest_for,
    capability_family_id_for,
)
from manafold_census.capability.input import load_m3_requirement_corpus
from manafold_census.capability.link_build import composition_member_link, direct_link
from manafold_census.capability.mapping import (
    MappingDispositionV1,
    MappingReasonV1,
    mapping_decision,
)
from manafold_census.capability.review import (
    CapabilityDefinitionReviewSubjectV1,
    CapabilityLinkReviewSubjectV1,
    CapabilityReviewRecordV1,
    GeneralizationBasisV1,
    ReviewDecisionV1,
)
from manafold_census.capability.validate import (
    validate_activation_eligibility,
    validate_m4_inputs,
)


def _active_definition_and_links(corpus, requirement_count: int):
    from test_capability_evolution import _claim

    requirements = corpus.requirements[:requirement_count]
    claim = _claim(kind=requirements[0].kind)
    definition = CapabilityDefinitionV1(
        capability_family_id=capability_family_id_for(claim.family_key),
        capability_version=claim.capability_version,
        claim_digest=capability_claim_digest_for(claim),
        claim=claim,
        display_name="Synthetic active Capability",
        lifecycle=CapabilityLifecycleStateV1.ACTIVE,
        provenance=CapabilityProvenanceV1(
            corpus.m3_analysis_manifest_sha256,
            (),
            tuple(
                CapabilityRequirementProvenanceV1.from_requirement(item)
                for item in requirements
            ),
        ),
        review_ref="mrv_" + "0" * 64,
    )
    definition_review = CapabilityReviewRecordV1.create(
        authority_id="m4.capability-review",
        authority_version="1",
        subject=CapabilityDefinitionReviewSubjectV1(
            definition.capability_family_id,
            definition.capability_version,
            definition.claim_digest,
        ),
        decision=ReviewDecisionV1.ACCEPTED,
        reviewer_id="maintainer:test",
        generalization_basis=(
            GeneralizationBasisV1.MULTI_SOURCE_REUSE
            if requirement_count > 1
            else GeneralizationBasisV1.SINGLE_OBSERVATION_GENERALIZATION
        ),
    )
    definition = replace(definition, review_ref=definition_review.record_id)
    links = []
    link_reviews = []
    admissibility = []
    for requirement in requirements:
        sra = SourceRequirementAdmissibilityV1.for_requirement(
            requirement,
            m3_analysis_manifest_sha256=corpus.m3_analysis_manifest_sha256,
            authority_id="m4.source-requirement-admissibility",
            authority_version="1",
            reviewer_id="maintainer:test",
        )
        proposal = direct_link(
            requirement=requirement,
            capability=definition,
            m3_manifest_sha256=corpus.m3_analysis_manifest_sha256,
            admissibility=sra,
        )
        link_review = CapabilityReviewRecordV1.create(
            authority_id="m4.capability-review",
            authority_version="1",
            subject=CapabilityLinkReviewSubjectV1(
                proposal.link_id,
                proposal.link_claim_digest,
            ),
            decision=ReviewDecisionV1.ACCEPTED,
            reviewer_id="maintainer:test",
            generalization_basis=None,
        )
        links.append(replace(proposal, review_ref=link_review.record_id))
        link_reviews.append(link_review)
        admissibility.append(sra)
    return (
        definition,
        definition_review,
        tuple(links),
        tuple(link_reviews),
        tuple(admissibility),
    )


def test_missing_mapping_decision_is_rejected(tmp_path: Path) -> None:
    m3_input = write_synthetic_m3(
        tmp_path / "m3",
        records=(record_with_proposed_requirement(),),
    )
    corpus = load_m3_requirement_corpus(m3_input)

    with pytest.raises(ValueError, match="mapping decision"):
        validate_m4_inputs(
            corpus,
            None,
            None,
            (),
            (),
            (),
            (),
            (),
            (),
            (),
        )


def test_mapping_decision_is_bound_to_the_selected_m3_snapshot(
    tmp_path: Path,
) -> None:
    m3_input = write_synthetic_m3(
        tmp_path / "m3",
        records=(record_with_proposed_requirement(),),
    )
    corpus = load_m3_requirement_corpus(m3_input)
    requirement = corpus.requirements[0]
    decision = mapping_decision(
        requirement,
        MappingDispositionV1.INSUFFICIENT_EVIDENCE,
        MappingReasonV1.M4_ADMISSIBILITY_REVIEW_PENDING,
        m3_analysis_manifest_sha256="f" * 64,
    )

    with pytest.raises(ValueError, match="M3 manifest"):
        validate_m4_inputs(
            corpus,
            None,
            None,
            (),
            (),
            (),
            (),
            (),
            (decision,),
            (),
        )


def test_m4_build_rejects_unknown_requirement_mapping(tmp_path: Path) -> None:
    m3_input = write_synthetic_m3(
        tmp_path / "m3",
        records=(record_with_proposed_requirement(),),
    )
    corpus = load_m3_requirement_corpus(m3_input)
    decision = mapping_decision(
        corpus.requirements[0],
        MappingDispositionV1.INSUFFICIENT_EVIDENCE,
        MappingReasonV1.M4_ADMISSIBILITY_REVIEW_PENDING,
        m3_analysis_manifest_sha256=corpus.m3_analysis_manifest_sha256,
    )
    with pytest.raises(ValueError, match="mapping"):
        validate_m4_inputs(
            corpus,
            None,
            None,
            (),
            (),
            (),
            (),
            (),
            (decision, decision),
            (),
        )


def test_capability_claim_registry_must_match_m4_manifest(tmp_path: Path) -> None:
    from dataclasses import replace

    from test_capability_definition import _definition, _draw_claim

    corpus = load_m3_requirement_corpus(
        write_synthetic_m3(
            tmp_path / "m3",
            records=(unresolved_record_without_bundle(),),
        )
    )
    definition = _definition(claim=replace(_draw_claim(registry_version="2")))

    with pytest.raises(ValueError, match="dimension registry"):
        validate_m4_inputs(
            corpus,
            None,
            None,
            (definition,),
            (),
            (),
            (),
            (),
            (),
            (),
        )


def test_definition_family_and_version_must_be_unique(tmp_path: Path) -> None:
    from dataclasses import replace

    from test_capability_definition import _definition, _draw_claim

    corpus = load_m3_requirement_corpus(
        write_synthetic_m3(
            tmp_path / "m3",
            records=(unresolved_record_without_bundle(),),
        )
    )
    first = _definition()
    second = _definition(
        claim=replace(_draw_claim(), m2_interpretation_version="2"),
        display_name="Same family and version, different claim",
    )

    with pytest.raises(ValueError, match="family.*version"):
        validate_m4_inputs(
            corpus,
            None,
            None,
            (first, second),
            (),
            (),
            (),
            (),
            (),
            (),
        )


def test_build_reference_m4_has_explicit_output_contract(tmp_path: Path) -> None:
    m3_input = write_synthetic_m3(
        tmp_path / "m3",
        records=(unresolved_record_without_bundle(),),
    )
    result = build_reference_m4(
        m3_input,
        None,
        None,
        (),
        (),
        (),
        (),
        (),
        (),
        (),
        tmp_path / "output",
    )

    assert result.requirements == ()
    assert result.mapping_decisions == ()


def test_activation_accepts_reviewed_multi_source_reuse(tmp_path: Path) -> None:
    m3_input = write_synthetic_m3(
        tmp_path / "m3",
        records=(
            record_with_proposed_requirement(0),
            record_with_proposed_requirement(1),
        ),
    )
    corpus = load_m3_requirement_corpus(m3_input)
    definition, definition_review, links, _, _ = _active_definition_and_links(corpus, 2)

    validate_activation_eligibility(
        definition,
        definition_review,
        corpus,
        links,
    )


def test_activation_rejects_multi_source_basis_without_two_sources(
    tmp_path: Path,
) -> None:
    m3_input = write_synthetic_m3(
        tmp_path / "m3",
        records=(record_with_proposed_requirement(),),
    )
    corpus = load_m3_requirement_corpus(m3_input)
    definition, definition_review, links, _, _ = _active_definition_and_links(corpus, 1)
    definition_review = CapabilityReviewRecordV1.create(
        authority_id=definition_review.authority_id,
        authority_version=definition_review.authority_version,
        subject=definition_review.subject,
        decision=ReviewDecisionV1.ACCEPTED,
        reviewer_id=definition_review.reviewer_id,
        generalization_basis=GeneralizationBasisV1.MULTI_SOURCE_REUSE,
    )
    definition = replace(definition, review_ref=definition_review.record_id)

    with pytest.raises(ValueError, match="two M1 sources"):
        validate_activation_eligibility(
            definition,
            definition_review,
            corpus,
            links,
        )


def test_validate_m4_inputs_runs_active_definition_eligibility(
    tmp_path: Path,
) -> None:
    m3_input = write_synthetic_m3(
        tmp_path / "m3",
        records=(
            record_with_proposed_requirement(0),
            record_with_proposed_requirement(1),
        ),
    )
    corpus = load_m3_requirement_corpus(m3_input)
    definition, definition_review, links, link_reviews, admissibility = (
        _active_definition_and_links(corpus, 2)
    )
    decisions = tuple(
        mapping_decision(
            requirement,
            MappingDispositionV1.MAPPED,
            None,
            m3_analysis_manifest_sha256=corpus.m3_analysis_manifest_sha256,
            active_link_ids=(link.link_id,),
        )
        for requirement, link in zip(corpus.requirements, links, strict=True)
    )

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
    assert result.definitions == (definition,)
    assert len(result.links) == 2


def test_composite_activation_uses_member_links_as_supporting_evidence(
    tmp_path: Path,
) -> None:
    from dataclasses import replace

    from test_capability_definition import _definition
    from test_capability_evolution import _claim

    from manafold_census.capability.claim import (
        CompositionClaimV1,
        CompositionComponentV1,
    )
    from manafold_census.capability.composition import CompositionContextV1
    from manafold_census.capability.definition import CapabilityDefinitionV1
    from manafold_census.capability.identity import (
        capability_claim_digest_for,
        capability_family_id_for,
    )
    from manafold_census.capability.model import CapabilityFamilyKeyV1, NucleusKindV1
    from manafold_census.semantic.kinds import RequirementFamilyV1, RequirementKindV1

    m3_input = write_synthetic_m3(
        tmp_path / "m3",
        records=(record_with_proposed_requirement(),),
    )
    corpus = load_m3_requirement_corpus(m3_input)
    requirement = corpus.requirements[0]
    draw = _definition(claim=_claim(kind=RequirementKindV1.DRAW_CARDS))
    damage = _definition(claim=_claim(kind=RequirementKindV1.DEAL_DAMAGE))
    family_key = CapabilityFamilyKeyV1(
        "1",
        NucleusKindV1.COMPOSITE,
        (
            (RequirementFamilyV1.EFFECT, RequirementKindV1.DRAW_CARDS),
            (RequirementFamilyV1.EFFECT, RequirementKindV1.DEAL_DAMAGE),
        ),
    )
    claim = _claim(
        kind=RequirementKindV1.DRAW_CARDS,
        family_key=family_key,
        composition=CompositionClaimV1(
            (
                CompositionComponentV1("draw", draw.capability_ref, True, 0),
                CompositionComponentV1("damage", damage.capability_ref, True, 1),
            )
        ),
    )
    composite = CapabilityDefinitionV1(
        capability_family_id=capability_family_id_for(claim.family_key),
        capability_version=claim.capability_version,
        claim_digest=capability_claim_digest_for(claim),
        claim=claim,
        display_name="Synthetic composite Capability",
        lifecycle=CapabilityLifecycleStateV1.ACTIVE,
        provenance=CapabilityProvenanceV1(
            corpus.m3_analysis_manifest_sha256,
            (),
            (CapabilityRequirementProvenanceV1.from_requirement(requirement),),
        ),
        review_ref="mrv_" + "0" * 64,
    )
    composite_review = CapabilityReviewRecordV1.create(
        authority_id="m4.capability-review",
        authority_version="1",
        subject=CapabilityDefinitionReviewSubjectV1(
            composite.capability_family_id,
            composite.capability_version,
            composite.claim_digest,
        ),
        decision=ReviewDecisionV1.ACCEPTED,
        reviewer_id="maintainer:test",
        generalization_basis=GeneralizationBasisV1.SINGLE_OBSERVATION_GENERALIZATION,
    )
    composite = replace(composite, review_ref=composite_review.record_id)
    admissibility = SourceRequirementAdmissibilityV1.for_requirement(
        requirement,
        m3_analysis_manifest_sha256=corpus.m3_analysis_manifest_sha256,
        authority_id="m4.source-requirement-admissibility",
        authority_version="1",
        reviewer_id="maintainer:test",
    )
    member = composition_member_link(
        requirement=requirement,
        capability=draw,
        m3_manifest_sha256=corpus.m3_analysis_manifest_sha256,
        admissibility=admissibility,
        composition_context=CompositionContextV1(
            "rcg_" + "a" * 64,
            composite.capability_ref,
            "draw",
        ),
    )
    member = replace(member, review_ref="mrv_" + "f" * 64)

    validate_activation_eligibility(
        composite,
        composite_review,
        corpus,
        (member,),
    )


def test_composite_activation_deduplicates_requirement_evidence_across_components(
    tmp_path: Path,
) -> None:
    from dataclasses import replace

    from test_capability_definition import _definition
    from test_capability_evolution import _claim

    from manafold_census.analysis.model import (
        AnalysisOutcomeV1,
        CardAnalysisRecordV1,
    )
    from manafold_census.capability.claim import (
        CompositionClaimV1,
        CompositionComponentV1,
    )
    from manafold_census.capability.composition import CompositionContextV1
    from manafold_census.capability.identity import (
        capability_claim_digest_for,
        capability_family_id_for,
    )
    from manafold_census.capability.model import CapabilityFamilyKeyV1, NucleusKindV1
    from manafold_census.semantic.bundle import RequirementBundleV1
    from manafold_census.semantic.evidence import StructuralFieldEvidenceV1
    from manafold_census.semantic.kind_payloads import DealDamageParametersV1
    from manafold_census.semantic.kinds import RequirementFamilyV1, RequirementKindV1
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
    )

    damage_source = source_for(1)
    damage_requirement = RequirementV1.create(
        source=damage_source,
        family=RequirementFamilyV1.EFFECT,
        kind=RequirementKindV1.DEAL_DAMAGE,
        parameters=DealDamageParametersV1(
            EntityRefV1(EntityRoleV1.SOURCE, MultiplicityV1.ONE, None),
            EntityRefV1(EntityRoleV1.TARGET, MultiplicityV1.ONE, None),
            QuantityV1(QuantityModeV1.EXACT, 2),
        ),
        evidence=(
            StructuralFieldEvidenceV1(damage_source, "oracle_text", None, "Damage"),
        ),
        provenance=ProvenanceV1(
            (DerivationV1(DerivationMethodV1.PARSER, "task8-test", "1"),)
        ),
        review=ReviewV1(ReviewStatusV1.PROPOSED, None, None),
        resolution=ResolutionV1(
            ResolutionStateV1.COMPLETE,
            ResolutionReasonV1.NONE,
            (),
        ),
    )
    damage_record = CardAnalysisRecordV1(
        source=damage_source,
        outcome=AnalysisOutcomeV1.REQUIREMENTS_PRODUCED,
        bundle=RequirementBundleV1(
            damage_source,
            (damage_requirement,),
            (),
        ),
        no_requirements_basis=None,
    )
    m3_input = write_synthetic_m3(
        tmp_path / "m3",
        records=(record_with_proposed_requirement(), damage_record),
    )
    corpus = load_m3_requirement_corpus(m3_input)
    draw_requirement = next(
        item
        for item in corpus.requirements
        if item.kind is RequirementKindV1.DRAW_CARDS
    )
    loaded_damage = next(
        item
        for item in corpus.requirements
        if item.kind is RequirementKindV1.DEAL_DAMAGE
    )
    draw_a = _definition(claim=_claim(kind=RequirementKindV1.DRAW_CARDS))
    draw_b = _definition(
        claim=_claim(kind=RequirementKindV1.DRAW_CARDS, version=2),
        display_name="Synthetic second draw component",
    )
    damage = _definition(claim=_claim(kind=RequirementKindV1.DEAL_DAMAGE))
    family_key = CapabilityFamilyKeyV1(
        "1",
        NucleusKindV1.COMPOSITE,
        (
            (RequirementFamilyV1.EFFECT, RequirementKindV1.DRAW_CARDS),
            (RequirementFamilyV1.EFFECT, RequirementKindV1.DEAL_DAMAGE),
        ),
    )
    claim = _claim(
        kind=RequirementKindV1.DRAW_CARDS,
        family_key=family_key,
        composition=CompositionClaimV1(
            (
                CompositionComponentV1("draw_a", draw_a.capability_ref, True, 0),
                CompositionComponentV1("draw_b", draw_b.capability_ref, True, 1),
                CompositionComponentV1("damage", damage.capability_ref, True, 2),
            )
        ),
    )
    composite = CapabilityDefinitionV1(
        capability_family_id=capability_family_id_for(claim.family_key),
        capability_version=claim.capability_version,
        claim_digest=capability_claim_digest_for(claim),
        claim=claim,
        display_name="Synthetic multi-component composite",
        lifecycle=CapabilityLifecycleStateV1.ACTIVE,
        provenance=CapabilityProvenanceV1(
            corpus.m3_analysis_manifest_sha256,
            (),
            tuple(
                CapabilityRequirementProvenanceV1.from_requirement(item)
                for item in corpus.requirements
            ),
        ),
        review_ref="mrv_" + "0" * 64,
    )
    composite_review = CapabilityReviewRecordV1.create(
        authority_id="m4.capability-review",
        authority_version="1",
        subject=CapabilityDefinitionReviewSubjectV1(
            composite.capability_family_id,
            composite.capability_version,
            composite.claim_digest,
        ),
        decision=ReviewDecisionV1.ACCEPTED,
        reviewer_id="maintainer:test",
        generalization_basis=GeneralizationBasisV1.MULTI_SOURCE_REUSE,
    )
    composite = replace(composite, review_ref=composite_review.record_id)
    group_id = "rcg_" + "a" * 64
    links = []
    for requirement, component, component_key, review_suffix in (
        (draw_requirement, draw_a, "draw_a", "b"),
        (draw_requirement, draw_b, "draw_b", "c"),
        (loaded_damage, damage, "damage", "d"),
    ):
        admissibility = SourceRequirementAdmissibilityV1.for_requirement(
            requirement,
            m3_analysis_manifest_sha256=corpus.m3_analysis_manifest_sha256,
            authority_id="m4.source-requirement-admissibility",
            authority_version="1",
            reviewer_id="maintainer:test",
        )
        member = composition_member_link(
            requirement=requirement,
            capability=component,
            m3_manifest_sha256=corpus.m3_analysis_manifest_sha256,
            admissibility=admissibility,
            composition_context=CompositionContextV1(
                group_id,
                composite.capability_ref,
                component_key,
            ),
        )
        links.append(replace(member, review_ref="mrv_" + review_suffix * 64))

    validate_activation_eligibility(
        composite,
        composite_review,
        corpus,
        tuple(links),
    )
