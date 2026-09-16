"""Frozen M6-03 policy constants and parent-identity binding checks.

The validator applies these on top of structural validation so that a
self-consistent but reworded packet, report, or policy identity cannot
pass input-bound validation.
"""

from __future__ import annotations

from ._common import (
    ASSESSMENT_POLICY_ID,
    ASSESSMENT_POLICY_VERSION,
    NON_AUTHORITY_STATEMENTS,
    PRIORITIZATION_VERSION,
    RANKING_POLICY_ID,
    RANKING_POLICY_VERSION,
    REVIEW_PACKET_LIMIT,
    REVIEW_QUESTIONS,
)
from .assessment import OpportunityAssessmentV1
from .input import LoadedPrioritizationInputsV1
from .manifest import PrioritizationManifestV1
from .report_model import PrioritizationReportV1
from .validate import PrioritizationValidationError
from .worklist import ReviewPacketV1


def check_frozen_constants(
    manifest: PrioritizationManifestV1,
    assessments: tuple[OpportunityAssessmentV1, ...],
    packet: ReviewPacketV1,
    report: PrioritizationReportV1,
) -> None:
    """Bind every planning artifact to the frozen M6-03 policy constants."""

    if manifest.prioritization_version != PRIORITIZATION_VERSION:
        raise PrioritizationValidationError("manifest prioritization version drifted")
    for label, actual, expected in (
        (
            "manifest assessment policy",
            manifest.assessment_policy_id,
            ASSESSMENT_POLICY_ID,
        ),
        (
            "manifest assessment policy version",
            manifest.assessment_policy_version,
            ASSESSMENT_POLICY_VERSION,
        ),
        ("manifest ranking policy", manifest.ranking_policy_id, RANKING_POLICY_ID),
        (
            "manifest ranking policy version",
            manifest.ranking_policy_version,
            RANKING_POLICY_VERSION,
        ),
    ):
        if actual != expected:
            raise PrioritizationValidationError(f"{label} drifted")
    if manifest.review_budget != REVIEW_PACKET_LIMIT:
        raise PrioritizationValidationError("manifest review budget drifted")
    for assessment in assessments:
        if (
            assessment.assessment_policy_id != ASSESSMENT_POLICY_ID
            or assessment.assessment_policy_version != ASSESSMENT_POLICY_VERSION
        ):
            raise PrioritizationValidationError("assessment policy identity drifted")
    for label, actual, expected in (
        ("packet ranking policy", packet.ranking_policy_id, RANKING_POLICY_ID),
        (
            "packet ranking policy version",
            packet.ranking_policy_version,
            RANKING_POLICY_VERSION,
        ),
        ("packet assessment policy", packet.assessment_policy_id, ASSESSMENT_POLICY_ID),
        (
            "packet assessment policy version",
            packet.assessment_policy_version,
            ASSESSMENT_POLICY_VERSION,
        ),
    ):
        if actual != expected:
            raise PrioritizationValidationError(f"{label} drifted")
    if packet.review_budget != REVIEW_PACKET_LIMIT:
        raise PrioritizationValidationError("packet review budget drifted")
    if tuple(packet.review_questions) != REVIEW_QUESTIONS:
        raise PrioritizationValidationError("packet review questions drifted")
    if tuple(packet.non_authority_statements) != NON_AUTHORITY_STATEMENTS:
        raise PrioritizationValidationError("packet non-authority statements drifted")
    for label, actual, expected in (
        ("report assessment policy", report.assessment_policy_id, ASSESSMENT_POLICY_ID),
        (
            "report assessment policy version",
            report.assessment_policy_version,
            ASSESSMENT_POLICY_VERSION,
        ),
        ("report ranking policy", report.ranking_policy_id, RANKING_POLICY_ID),
        (
            "report ranking policy version",
            report.ranking_policy_version,
            RANKING_POLICY_VERSION,
        ),
    ):
        if actual != expected:
            raise PrioritizationValidationError(f"{label} drifted")
    if report.review_packet_limit != REVIEW_PACKET_LIMIT:
        raise PrioritizationValidationError("report review budget drifted")
    if tuple(report.notes) != NON_AUTHORITY_STATEMENTS:
        raise PrioritizationValidationError("report non-authority statements drifted")


def check_parent_bindings(
    packet: ReviewPacketV1,
    report: PrioritizationReportV1,
    loaded: LoadedPrioritizationInputsV1,
) -> None:
    """Bind packet and report evidence to the validated parent inputs."""

    parents = loaded.inventory_inputs
    for label, actual, expected in (
        ("packet source lock", packet.source_lock_digest, parents.source_lock_digest),
        ("packet M1 manifest", packet.m1_manifest_sha256, parents.m1_manifest_sha256),
        ("packet M3 manifest", packet.m3_manifest_sha256, parents.m3_manifest_sha256),
        (
            "packet M4 parent",
            packet.parent_m4_manifest_sha256,
            parents.parent_m4_manifest_sha256,
        ),
        (
            "packet Census parent",
            packet.parent_census_release_id,
            parents.parent_census_release_id,
        ),
        (
            "packet M6-02 manifest",
            packet.m6_02_manifest_sha256,
            loaded.m6_02_manifest_sha256,
        ),
        (
            "packet M6-02 identity set",
            packet.m6_02_selected_identity_set_digest,
            loaded.m6_02_selected_identity_set_digest,
        ),
        ("report source lock", report.source_lock_digest, parents.source_lock_digest),
        ("report M1 manifest", report.m1_manifest_sha256, parents.m1_manifest_sha256),
        ("report M3 manifest", report.m3_manifest_sha256, parents.m3_manifest_sha256),
        (
            "report M4 parent",
            report.parent_m4_manifest_sha256,
            parents.parent_m4_manifest_sha256,
        ),
        (
            "report Census parent",
            report.parent_census_release_id,
            parents.parent_census_release_id,
        ),
        (
            "report M6-02 manifest",
            report.m6_02_manifest_sha256,
            loaded.m6_02_manifest_sha256,
        ),
        (
            "report M6-02 identity set",
            report.m6_02_selected_identity_set_digest,
            loaded.m6_02_selected_identity_set_digest,
        ),
    ):
        if actual != expected:
            raise PrioritizationValidationError(f"{label} is not bound to inputs")


__all__ = ["check_frozen_constants", "check_parent_bindings"]
