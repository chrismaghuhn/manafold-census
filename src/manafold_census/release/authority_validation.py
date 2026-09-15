"""Cross-layer validation for the Census 0.1 authority package."""

from __future__ import annotations

from pathlib import Path

from ..capability.admissibility import (
    AdmissibilityDecisionV1,
    SourceRequirementAdmissibilityV1,
)
from ..capability.definition import (
    CapabilityLifecycleStateV1,
    CapabilityRequirementProvenanceV1,
    validate_provenance_against_m3,
)
from ..capability.input import M3RequirementCorpusV1
from ..capability.link import (
    LinkAdmissibilityBasisV1,
    LinkRelationV1,
    RequirementCapabilityLinkV1,
)
from ..capability.mapping import MappingDispositionV1
from ..capability.review import (
    CapabilityDefinitionReviewSubjectV1,
    CapabilityLinkReviewSubjectV1,
    CapabilityReviewRecordV1,
    ReviewDecisionV1,
)
from ..capability.validate import validate_m4_inputs
from ..semantic.model import RequirementV1
from .authority_package import (
    CENSUS_0_1_CAMPAIGN_ID,
    AuthorityPackageContentsV1,
    AuthorityReviewPolicyV1,
)
from .authority_package_io import load_authority_package
from .input_lock import CensusInputLockV1


def _require_policy(record: object, policy: AuthorityReviewPolicyV1) -> None:
    if isinstance(record, SourceRequirementAdmissibilityV1):
        actual = record.authority_id, record.authority_version, record.reviewer_id
        expected = (
            policy.sra_authority_id,
            policy.sra_authority_version,
            policy.sra_reviewer_id,
        )
        if actual != expected:
            raise ValueError("SRA authority policy mismatch")
    elif isinstance(record, CapabilityReviewRecordV1):
        actual = record.authority_id, record.authority_version, record.reviewer_id
        expected = (
            policy.capability_review_authority_id,
            policy.capability_review_authority_version,
            policy.capability_reviewer_id,
        )
        if actual != expected:
            raise ValueError("Capability review authority policy mismatch")


def _validate_sra(
    contents: AuthorityPackageContentsV1,
    requirements: dict[str, RequirementV1],
    policy: AuthorityReviewPolicyV1,
    manifest_sha256: str,
) -> dict[str, SourceRequirementAdmissibilityV1]:
    if len(contents.admissibility) != len(requirements):
        raise ValueError(
            "authority package requires exactly one SRA per selected Requirement"
        )
    result: dict[str, SourceRequirementAdmissibilityV1] = {}
    for record in contents.admissibility:
        _require_policy(record, policy)
        if record.requirement_id in result:
            raise ValueError("duplicate SRA decision for a Requirement")
        requirement = requirements.get(record.requirement_id)
        if requirement is None:
            raise ValueError("SRA Requirement is outside the selected scope")
        record.validate_m3_manifest(manifest_sha256)
        record.validate_against_requirement(requirement)
        if (
            record.decision
            is not AdmissibilityDecisionV1.ACCEPTED_FOR_CAPABILITY_MAPPING
        ):
            raise ValueError("Census 0.1 SRA must accept every locked Requirement")
        result[record.requirement_id] = record
    if set(result) != set(requirements):
        raise ValueError("SRA coverage does not equal the selected Requirement set")
    return result


def _validate_definition(
    contents: AuthorityPackageContentsV1,
    corpus: M3RequirementCorpusV1,
    policy: AuthorityReviewPolicyV1,
) -> None:
    if len(contents.capability_definitions) != 1:
        raise ValueError("Census 0.1 requires exactly one Capability definition")
    definition = contents.capability_definitions[0]
    if definition.lifecycle is not CapabilityLifecycleStateV1.ACTIVE:
        raise ValueError("Census 0.1 Capability must be ACTIVE")
    refs = tuple(
        CapabilityRequirementProvenanceV1.from_requirement(item)
        for item in corpus.requirements
    )
    if (
        definition.provenance.candidate_cluster_ids
        or definition.provenance.requirement_refs != refs
    ):
        raise ValueError(
            "Capability provenance does not cover exactly the selected Requirements"
        )
    validate_provenance_against_m3(
        definition.provenance,
        corpus.m3_analysis_manifest_sha256,
        corpus.requirements,
    )
    subject = CapabilityDefinitionReviewSubjectV1(
        definition.capability_family_id,
        definition.capability_version,
        definition.claim_digest,
    )
    matching = [item for item in contents.reviews if item.subject == subject]
    if len(matching) != 1 or matching[0].decision is not ReviewDecisionV1.ACCEPTED:
        raise ValueError(
            "active Capability requires exactly one accepted definition review"
        )
    for review in contents.reviews:
        _require_policy(review, policy)


def _validate_links_and_decisions(
    contents: AuthorityPackageContentsV1,
    corpus: M3RequirementCorpusV1,
    sra_by_requirement: dict[str, SourceRequirementAdmissibilityV1],
) -> None:
    requirements = {item.requirement_id: item for item in corpus.requirements}
    if len(contents.links) != 5 or len(contents.mapping_decisions) != 5:
        raise ValueError(
            "Census 0.1 requires one link and mapping decision per Requirement"
        )
    links: dict[str, RequirementCapabilityLinkV1] = {}
    link_review_ids: set[str] = set()
    for link in contents.links:
        if link.requirement_id in links:
            raise ValueError("duplicate active link for a Requirement")
        requirement = requirements.get(link.requirement_id)
        if requirement is None or link.relation is not LinkRelationV1.DIRECT:
            raise ValueError("link is outside the selected direct-link scope")
        if link.m3_analysis_manifest_sha256 != corpus.m3_analysis_manifest_sha256:
            raise ValueError("link M3 manifest does not match corpus")
        route = link.m4_requirement_admissibility
        sra = sra_by_requirement[link.requirement_id]
        if (
            route is None
            or route.basis
            is not LinkAdmissibilityBasisV1.SOURCE_REQUIREMENT_ADMISSIBILITY
            or (route.record_id, route.review_digest)
            != (sra.record_id, sra.review_digest)
        ):
            raise ValueError("active link requires the exact SRA route")
        if link.review_ref is None:
            raise ValueError("active link requires an accepted review")
        matching = [
            item
            for item in contents.reviews
            if item.subject
            == CapabilityLinkReviewSubjectV1(link.link_id, link.link_claim_digest)
        ]
        if (
            len(matching) != 1
            or matching[0].decision is not ReviewDecisionV1.ACCEPTED
            or matching[0].record_id != link.review_ref
        ):
            raise ValueError("active link requires exactly one accepted exact review")
        link_review_ids.add(matching[0].record_id)
        links[link.requirement_id] = link
    if set(links) != set(requirements):
        raise ValueError("link coverage does not equal the selected Requirement set")
    if len(contents.reviews) != 1 + len(link_review_ids):
        raise ValueError("review authority contains an out-of-scope record")
    decisions: dict[str, object] = {}
    for decision in contents.mapping_decisions:
        if decision.requirement_id in decisions:
            raise ValueError("duplicate mapping decision for a Requirement")
        decision_link = links.get(decision.requirement_id)
        if (
            decision.requirement_id not in requirements
            or decision_link is None
            or decision.disposition is not MappingDispositionV1.MAPPED
            or decision.active_link_ids != (decision_link.link_id,)
        ):
            raise ValueError("mapping decision is outside the selected MAPPED scope")
        decisions[decision.requirement_id] = decision
    if set(decisions) != set(requirements):
        raise ValueError(
            "mapping decision coverage does not equal the selected Requirement set"
        )


def validate_authority_package(
    package_dir: str | Path,
    lock: CensusInputLockV1,
    corpus: M3RequirementCorpusV1,
) -> AuthorityPackageContentsV1:
    if not isinstance(lock, CensusInputLockV1):
        raise TypeError("lock must be CensusInputLockV1")
    if not isinstance(corpus, M3RequirementCorpusV1):
        raise TypeError("corpus must be M3RequirementCorpusV1")
    if corpus.requirement_set_digest != lock.expected_m4_requirement_set_digest:
        raise ValueError("M3 corpus Requirement-set digest does not match lock")
    contents = load_authority_package(package_dir)
    manifest = contents.manifest
    if manifest.campaign_id != CENSUS_0_1_CAMPAIGN_ID:
        raise ValueError("authority package campaign is not Census 0.1")
    if manifest.m3_analysis_manifest_sha256 != lock.m3_analysis_manifest_sha256:
        raise ValueError("authority package M3 manifest does not match lock")
    if manifest.m3_analysis_manifest_sha256 != corpus.m3_analysis_manifest_sha256:
        raise ValueError("authority package M3 manifest does not match corpus")
    if manifest.m4_requirement_set_digest != lock.expected_m4_requirement_set_digest:
        raise ValueError("authority package Requirement-set digest does not match lock")
    requirements = {item.requirement_id: item for item in corpus.requirements}
    selected = tuple(sorted(requirements))
    if len(selected) != 5 or manifest.selected_requirement_ids != selected:
        raise ValueError(
            "authority package must select exactly the locked five Requirements"
        )
    sra = _validate_sra(
        contents,
        requirements,
        manifest.review_policy,
        manifest.m3_analysis_manifest_sha256,
    )
    _validate_definition(contents, corpus, manifest.review_policy)
    _validate_links_and_decisions(contents, corpus, sra)
    if contents.relations or contents.evolution:
        raise ValueError(
            "Census 0.1 M5-03 package cannot contain relations or evolution"
        )
    validate_m4_inputs(
        corpus,
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
    return contents


__all__ = ["validate_authority_package"]
