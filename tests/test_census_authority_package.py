from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path

import pytest
from capability_m3_fixtures import record_with_proposed_requirement, write_synthetic_m3

from manafold_census.analysis.manifest import AnalysisManifestV1
from manafold_census.canonical import canonical_json_bytes
from manafold_census.capability.admissibility import (
    AdmissibilityDecisionV1,
    SourceRequirementAdmissibilityV1,
)
from manafold_census.capability.binding import ParameterBindingV1
from manafold_census.capability.claim import CapabilityClaimV1
from manafold_census.capability.definition import (
    CapabilityDefinitionV1,
    CapabilityLifecycleStateV1,
    CapabilityProvenanceV1,
    CapabilityRequirementProvenanceV1,
)
from manafold_census.capability.dimensions import (
    CapabilityDimensionV1,
    DimensionDomainKindV1,
    DimensionKindV1,
    M2DimensionPathV1,
)
from manafold_census.capability.identity import (
    capability_claim_digest_for,
    capability_family_id_for,
)
from manafold_census.capability.input import load_m3_requirement_corpus
from manafold_census.capability.link_build import direct_link
from manafold_census.capability.manifest import M4_DIMENSION_REGISTRY_VERSION
from manafold_census.capability.mapping import (
    MappingDispositionV1,
    mapping_decision,
)
from manafold_census.capability.model import (
    CapabilityFamilyKeyV1,
    NucleusKindV1,
)
from manafold_census.capability.relations import requires_edge
from manafold_census.capability.review import (
    CapabilityDefinitionReviewSubjectV1,
    CapabilityLinkReviewSubjectV1,
    CapabilityReviewRecordV1,
    GeneralizationBasisV1,
    ReviewDecisionV1,
)
from manafold_census.capability.validate import validate_m4_inputs
from manafold_census.digest import sha256_bytes
from manafold_census.models import SourceLock
from manafold_census.release.authority_package import (
    AUTHORITY_PACKAGE_FILES,
    AuthorityFileDescriptorV1,
    AuthorityPackageManifestV1,
    AuthorityReviewPolicyV1,
    authority_package_digest_for,
    load_authority_package,
    validate_authority_package,
    write_authority_package,
)
from manafold_census.semantic.kinds import RequirementFamilyV1, RequirementKindV1
from manafold_census.structural.manifest import StructuralCardIndexManifestV1


@dataclass(frozen=True)
class _TestAuthorityPackage:
    root: Path
    lock: object
    corpus: object
    m3_input: object
    definitions: tuple[CapabilityDefinitionV1, ...]
    reviews: tuple[CapabilityReviewRecordV1, ...]
    admissibility: tuple[SourceRequirementAdmissibilityV1, ...]
    links: tuple[object, ...]
    mapping_decisions: tuple[object, ...]
    relations: tuple[object, ...]
    evolution: tuple[object, ...]


def _lock_and_corpus(tmp_path: Path):
    module = __import__("manafold_census.release.input_lock", fromlist=["unused"])
    m3_input = write_synthetic_m3(
        tmp_path / "m3",
        records=tuple(record_with_proposed_requirement(index) for index in range(5)),
    )
    corpus = load_m3_requirement_corpus(m3_input)
    source_raw = m3_input.source_lock_path.read_bytes()
    source_lock = SourceLock.from_wire(json.loads(source_raw))
    m1_path = m3_input.structural_output_directory / "structural-index-manifest.json"
    m1_raw = m1_path.read_bytes()
    m1 = StructuralCardIndexManifestV1.from_wire(json.loads(m1_raw))
    m3_path = m3_input.analysis_output_directory / "analysis-manifest.json"
    m3_raw = m3_path.read_bytes()
    m3 = AnalysisManifestV1.from_wire(json.loads(m3_raw))
    lock = module.CensusInputLockV1(
        source_lock_digest=source_lock.digest(),
        source_lock_file_sha256=sha256_bytes(source_raw),
        m1_structural_manifest_sha256=sha256_bytes(m1_raw),
        m1_structural_aggregate_digest=m1.aggregate_digest,
        m3_analysis_manifest_sha256=sha256_bytes(m3_raw),
        m3_record_identity_set_digest=m3.record_identity_set_digest,
        m3_record_index_digest=m3.record_index_digest,
        m3_trace_index_digest=m3.trace_index_digest,
        expected_m4_requirement_set_digest=corpus.requirement_set_digest,
        m1_structural_schema="census.structural-card.v1",
        m3_analysis_schema="census.card-analysis.v1",
        m2_requirement_schema="census.semantic-requirement.v1",
        m2_bundle_schema="census.semantic-requirement-bundle.v1",
        m4_ontology_schema="census.capability-ontology.v1",
        m4_dimension_registry_version=M4_DIMENSION_REGISTRY_VERSION,
        expected_oracle_identity_count=5,
        expected_structural_record_count=5,
        expected_analysis_record_count=5,
        expected_requirements_produced_card_count=5,
        expected_no_requirements_applicable_count=0,
        expected_unresolved_analysis_count=0,
        expected_requirement_count=5,
    )
    return lock, corpus, m3_input


def _policy() -> AuthorityReviewPolicyV1:
    return AuthorityReviewPolicyV1(
        sra_authority_id="m4.source-requirement-admissibility",
        sra_authority_version="1",
        sra_reviewer_id="maintainer:test",
        capability_review_authority_id="m4.capability-review",
        capability_review_authority_version="1",
        capability_reviewer_id="maintainer:test",
    )


def _records(corpus):
    claim = CapabilityClaimV1(
        family_key=CapabilityFamilyKeyV1(
            "1",
            NucleusKindV1.ATOMIC,
            ((RequirementFamilyV1.EFFECT, RequirementKindV1.DRAW_CARDS),),
        ),
        capability_version=1,
        m2_requirement_schema="census.semantic-requirement.v1",
        m2_interpretation_version="1",
        m4_dimension_registry_version=M4_DIMENSION_REGISTRY_VERSION,
        dimensions=(
            CapabilityDimensionV1(
                M2DimensionPathV1.DRAW_CARDS_DRAWER,
                DimensionKindV1.ENTITY_REF,
                True,
                DimensionDomainKindV1.ANY_TYPED_VALUE,
            ),
            CapabilityDimensionV1(
                M2DimensionPathV1.DRAW_CARDS_QUANTITY,
                DimensionKindV1.QUANTITY,
                True,
                DimensionDomainKindV1.ANY_TYPED_VALUE,
            ),
        ),
        exclusions=(),
        composition=None,
    )
    definition = CapabilityDefinitionV1(
        capability_family_id=capability_family_id_for(claim.family_key),
        capability_version=claim.capability_version,
        claim_digest=capability_claim_digest_for(claim),
        claim=claim,
        display_name="Draw exactly two cards",
        lifecycle=CapabilityLifecycleStateV1.ACTIVE,
        provenance=CapabilityProvenanceV1(
            corpus.m3_analysis_manifest_sha256,
            (),
            tuple(
                CapabilityRequirementProvenanceV1.from_requirement(item)
                for item in corpus.requirements
            ),
        ),
        review_ref=None,
    )
    definition_review = CapabilityReviewRecordV1.create(
        authority_id=_policy().capability_review_authority_id,
        authority_version=_policy().capability_review_authority_version,
        subject=CapabilityDefinitionReviewSubjectV1(
            definition.capability_family_id,
            definition.capability_version,
            definition.claim_digest,
        ),
        decision=ReviewDecisionV1.ACCEPTED,
        reviewer_id=_policy().capability_reviewer_id,
        generalization_basis=GeneralizationBasisV1.MULTI_SOURCE_REUSE,
    )
    definition = replace(definition, review_ref=definition_review.record_id)
    admissibility = []
    links = []
    link_reviews = []
    decisions = []
    for requirement in corpus.requirements:
        sra = SourceRequirementAdmissibilityV1.for_requirement(
            requirement,
            m3_analysis_manifest_sha256=corpus.m3_analysis_manifest_sha256,
            authority_id=_policy().sra_authority_id,
            authority_version=_policy().sra_authority_version,
            reviewer_id=_policy().sra_reviewer_id,
            decision=AdmissibilityDecisionV1.ACCEPTED_FOR_CAPABILITY_MAPPING,
        )
        proposal = direct_link(
            requirement=requirement,
            capability=definition,
            m3_manifest_sha256=corpus.m3_analysis_manifest_sha256,
            admissibility=sra,
            parameter_bindings=(
                ParameterBindingV1.known(
                    M2DimensionPathV1.DRAW_CARDS_DRAWER,
                    requirement.parameters.drawer.to_wire(),
                ),
                ParameterBindingV1.known(
                    M2DimensionPathV1.DRAW_CARDS_QUANTITY,
                    requirement.parameters.quantity.to_wire(),
                ),
            ),
        )
        link_review = CapabilityReviewRecordV1.create(
            authority_id=_policy().capability_review_authority_id,
            authority_version=_policy().capability_review_authority_version,
            subject=CapabilityLinkReviewSubjectV1(
                proposal.link_id,
                proposal.link_claim_digest,
            ),
            decision=ReviewDecisionV1.ACCEPTED,
            reviewer_id=_policy().capability_reviewer_id,
            generalization_basis=None,
        )
        link = replace(proposal, review_ref=link_review.record_id)
        admissibility.append(sra)
        links.append(link)
        link_reviews.append(link_review)
        decisions.append(
            mapping_decision(
                requirement,
                MappingDispositionV1.MAPPED,
                None,
                m3_analysis_manifest_sha256=corpus.m3_analysis_manifest_sha256,
                active_link_ids=(link.link_id,),
            )
        )
    return (
        (definition,),
        (definition_review, *link_reviews),
        tuple(admissibility),
        tuple(links),
        tuple(decisions),
        (),
        (),
    )


def _write_test_package(tmp_path: Path) -> _TestAuthorityPackage:
    lock, corpus, m3_input = _lock_and_corpus(tmp_path)
    definitions, reviews, admissibility, links, decisions, relations, evolution = (
        _records(corpus)
    )
    root = tmp_path / "package"
    write_authority_package(
        root,
        campaign_id="m5.census-0.1",
        m3_analysis_manifest_sha256=corpus.m3_analysis_manifest_sha256,
        m4_requirement_set_digest=corpus.requirement_set_digest,
        selected_requirement_ids=tuple(
            item.requirement_id for item in corpus.requirements
        ),
        review_policy=_policy(),
        capability_definitions=definitions,
        reviews=reviews,
        relations=relations,
        admissibility=admissibility,
        links=links,
        mapping_decisions=decisions,
        evolution=evolution,
    )
    return _TestAuthorityPackage(
        root,
        lock,
        corpus,
        m3_input,
        definitions,
        reviews,
        admissibility,
        links,
        decisions,
        relations,
        evolution,
    )


def _write_variant(
    package: _TestAuthorityPackage,
    root: Path,
    *,
    selected_requirement_ids=None,
    reviews=None,
    admissibility=None,
    links=None,
    mapping_decisions=None,
    relations=None,
) -> None:
    write_authority_package(
        root,
        campaign_id="m5.census-0.1",
        m3_analysis_manifest_sha256=package.corpus.m3_analysis_manifest_sha256,
        m4_requirement_set_digest=package.corpus.requirement_set_digest,
        selected_requirement_ids=(
            tuple(item.requirement_id for item in package.corpus.requirements)
            if selected_requirement_ids is None
            else selected_requirement_ids
        ),
        review_policy=_policy(),
        capability_definitions=package.definitions,
        reviews=package.reviews if reviews is None else reviews,
        relations=package.relations if relations is None else relations,
        admissibility=(
            package.admissibility if admissibility is None else admissibility
        ),
        links=package.links if links is None else links,
        mapping_decisions=(
            package.mapping_decisions
            if mapping_decisions is None
            else mapping_decisions
        ),
        evolution=package.evolution,
    )


def test_authority_manifest_digest_excludes_derived_digest() -> None:
    descriptors = tuple(
        AuthorityFileDescriptorV1(path, "0" * 64, 0, 0)
        for path in sorted(AUTHORITY_PACKAGE_FILES)
    )
    manifest = AuthorityPackageManifestV1.create(
        campaign_id="m5.census-0.1",
        m3_analysis_manifest_sha256="a" * 64,
        m4_requirement_set_digest="b" * 64,
        selected_requirement_ids=("srq_" + "c" * 64,),
        record_file_descriptors=descriptors,
        review_policy=_policy(),
    )
    assert manifest.authority_package_digest == authority_package_digest_for(manifest)
    mutated = replace(manifest, authority_package_digest="e" * 64)
    assert authority_package_digest_for(mutated) == manifest.authority_package_digest


def test_authority_package_binds_every_record_to_locked_m3_and_requirement_wires(
    tmp_path: Path,
) -> None:
    package = _write_test_package(tmp_path)
    before = tuple(item.to_wire() for item in package.corpus.requirements)

    validated = validate_authority_package(package.root, package.lock, package.corpus)

    assert validated.manifest.m3_analysis_manifest_sha256 == (
        package.corpus.m3_analysis_manifest_sha256
    )
    assert len(validated.admissibility) == len(package.corpus.requirements) == 5
    assert len(validated.links) == len(package.corpus.requirements) == 5
    assert len(validated.mapping_decisions) == len(package.corpus.requirements) == 5
    assert tuple(item.to_wire() for item in package.corpus.requirements) == before


def test_authority_package_passes_existing_m4_validation(tmp_path: Path) -> None:
    package = _write_test_package(tmp_path)

    contents = load_authority_package(package.root)
    validate_m4_inputs(
        package.corpus,
        None,
        None,
        contents.capability_definitions,
        contents.reviews,
        contents.relations,
        contents.admissibility,
        contents.links,
        contents.mapping_decisions,
        contents.evolution,
    )


def test_authority_package_requires_exactly_one_sra_per_selected_requirement(
    tmp_path: Path,
) -> None:
    package = _write_test_package(tmp_path)
    duplicate_root = tmp_path / "duplicate"
    _write_variant(
        package,
        duplicate_root,
        admissibility=package.admissibility + (package.admissibility[0],),
    )

    with pytest.raises(ValueError, match="exactly one.*SRA|duplicate.*admissibility"):
        validate_authority_package(duplicate_root, package.lock, package.corpus)


def test_authority_package_rejects_extra_files(tmp_path: Path) -> None:
    package = _write_test_package(tmp_path)
    (package.root / "unbound.jsonl").write_bytes(b"")

    with pytest.raises(ValueError, match="file set"):
        validate_authority_package(package.root, package.lock, package.corpus)


def test_authority_package_rejects_missing_sra(tmp_path: Path) -> None:
    package = _write_test_package(tmp_path)
    root = tmp_path / "missing-sra"
    _write_variant(package, root, admissibility=package.admissibility[:-1])

    with pytest.raises(ValueError, match="exactly one SRA"):
        validate_authority_package(root, package.lock, package.corpus)


def test_authority_package_rejects_stale_sra_manifest(tmp_path: Path) -> None:
    package = _write_test_package(tmp_path)
    stale = SourceRequirementAdmissibilityV1.for_requirement(
        package.corpus.requirements[0],
        m3_analysis_manifest_sha256="f" * 64,
        authority_id=_policy().sra_authority_id,
        authority_version=_policy().sra_authority_version,
        reviewer_id=_policy().sra_reviewer_id,
    )
    root = tmp_path / "stale-sra"
    _write_variant(package, root, admissibility=(stale, *package.admissibility[1:]))

    with pytest.raises(ValueError, match="M3 manifest"):
        validate_authority_package(root, package.lock, package.corpus)


def test_authority_package_rejects_unreviewed_active_link(tmp_path: Path) -> None:
    package = _write_test_package(tmp_path)
    root = tmp_path / "unreviewed-link"
    _write_variant(
        package,
        root,
        links=(replace(package.links[0], review_ref=None), *package.links[1:]),
    )

    with pytest.raises(ValueError, match="active link requires an accepted review"):
        validate_authority_package(root, package.lock, package.corpus)


def test_authority_package_rejects_missing_definition_review(tmp_path: Path) -> None:
    package = _write_test_package(tmp_path)
    root = tmp_path / "missing-definition-review"
    _write_variant(package, root, reviews=package.reviews[1:])

    with pytest.raises(
        ValueError, match="Capability requires exactly one accepted definition review"
    ):
        validate_authority_package(root, package.lock, package.corpus)


def test_authority_package_rejects_incomplete_mapping_decisions(tmp_path: Path) -> None:
    package = _write_test_package(tmp_path)
    root = tmp_path / "missing-mapping"
    _write_variant(package, root, mapping_decisions=package.mapping_decisions[:-1])

    with pytest.raises(ValueError, match="one link and mapping decision"):
        validate_authority_package(root, package.lock, package.corpus)


def test_authority_package_rejects_out_of_scope_selected_requirement(
    tmp_path: Path,
) -> None:
    package = _write_test_package(tmp_path)
    selected = tuple(
        item.requirement_id for item in package.corpus.requirements[:-1]
    ) + ("srq_" + "f" * 64,)
    root = tmp_path / "out-of-scope"
    _write_variant(package, root, selected_requirement_ids=tuple(sorted(selected)))

    with pytest.raises(ValueError, match="exactly the locked five"):
        validate_authority_package(root, package.lock, package.corpus)


def test_authority_package_rejects_relations_in_census_0_1(tmp_path: Path) -> None:
    package = _write_test_package(tmp_path)
    root = tmp_path / "relations"
    _write_variant(
        package,
        root,
        relations=(requires_edge(package.definitions[0], package.definitions[0]),),
    )

    with pytest.raises(ValueError, match="cannot contain relations"):
        validate_authority_package(root, package.lock, package.corpus)


def test_authority_cli_validates_explicit_package_and_inputs(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    package = _write_test_package(tmp_path)
    lock_path = tmp_path / "input-lock.json"
    lock_path.write_bytes(canonical_json_bytes(package.lock.to_wire()))

    from manafold_census.cli import main

    exit_code = main(
        [
            "m5-authority-check",
            "--package",
            str(package.root),
            "--lock",
            str(lock_path),
            "--source-lock",
            str(package.m3_input.source_lock_path),
            "--structural-output",
            str(package.m3_input.structural_output_directory),
            "--analysis-output",
            str(package.m3_input.analysis_output_directory),
        ]
    )

    assert exit_code == 0
    assert "m5-authority=PASS" in capsys.readouterr().out
