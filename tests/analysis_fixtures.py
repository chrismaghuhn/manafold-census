from __future__ import annotations

from manafold_census.semantic.bundle import RequirementBundleV1
from manafold_census.semantic.evidence import (
    SourceRecordRefV1,
    StructuralFieldEvidenceV1,
)
from manafold_census.semantic.identity import reviewed_claim_digest_for
from manafold_census.semantic.kind_payloads import DrawCardsParametersV1
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
from manafold_census.structural.model import StructuralCardRecordV1

SOURCE_LOCK_DIGEST = "a" * 64
OTHER_SOURCE_LOCK_DIGEST = "c" * 64
SOURCE_RECORD_SHA256 = "b" * 64
ORACLE_ID = "abcdefab-abcd-4abc-8abc-abcdefabcdef"
OTHER_ORACLE_ID = "abcdefab-abcd-4abc-8abc-abcdefabcdea"
SOURCE_CARD_ID = "abcdefab-abcd-4abc-8abc-abcdefabcdeb"


def source_ref(
    *,
    source_lock_digest: str = SOURCE_LOCK_DIGEST,
    oracle_id: str = ORACLE_ID,
    source_card_id: str = SOURCE_CARD_ID,
    source_record_sha256: str = SOURCE_RECORD_SHA256,
) -> SourceRecordRefV1:
    return SourceRecordRefV1(
        record_schema="census.structural-card.v1",
        source_lock_digest=source_lock_digest,
        oracle_id=oracle_id,
        source_card_id=source_card_id,
        source_record_sha256=source_record_sha256,
    )


def structural_record(
    *,
    oracle_id: str = ORACLE_ID,
    source_card_id: str = SOURCE_CARD_ID,
    source_record_sha256: str = SOURCE_RECORD_SHA256,
) -> StructuralCardRecordV1:
    return StructuralCardRecordV1(
        oracle_id=oracle_id,
        source_card_id=source_card_id,
        source_record_sha256=source_record_sha256,
        name="Fixture Card",
        layout="normal",
        mana_cost="{1}{U}",
        type_line="Creature",
        oracle_text="Draw two cards.",
        colors=("U",),
        color_identity=("U",),
        color_indicator=None,
        keywords=("Flying",),
        produced_mana=None,
        power="2",
        toughness="2",
        loyalty=None,
        defense=None,
        hand_modifier=None,
        life_modifier=None,
        attraction_lights=None,
        faces=None,
        all_parts=None,
    )


def source_lock_digest() -> str:
    return SOURCE_LOCK_DIGEST


def _entity() -> EntityRefV1:
    return EntityRefV1(EntityRoleV1.SOURCE, MultiplicityV1.ONE, None)


def _provenance() -> ProvenanceV1:
    return ProvenanceV1((DerivationV1(DerivationMethodV1.PARSER, "fixture", "1"),))


def _draw(source: SourceRecordRefV1) -> RequirementV1:
    return RequirementV1.create(
        source=source,
        family=RequirementFamilyV1.EFFECT,
        kind=RequirementKindV1.DRAW_CARDS,
        parameters=DrawCardsParametersV1(
            _entity(), QuantityV1(QuantityModeV1.EXACT, 2)
        ),
        evidence=(StructuralFieldEvidenceV1(source, "oracle_text", None, "Draw"),),
        provenance=_provenance(),
        review=ReviewV1(ReviewStatusV1.PROPOSED, None, None),
        resolution=ResolutionV1(
            ResolutionStateV1.COMPLETE,
            ResolutionReasonV1.NONE,
            (),
        ),
    )


def bundle(source: SourceRecordRefV1 | None = None) -> RequirementBundleV1:
    actual_source = source or source_ref()
    return RequirementBundleV1(actual_source, (_draw(actual_source),), ())


def bundle_from_other_source() -> RequirementBundleV1:
    other_source = source_ref(oracle_id=OTHER_ORACLE_ID)
    return bundle(other_source)


def accepted_requirement() -> RequirementV1:
    proposal = bundle().requirements[0]
    return RequirementV1.create(
        source=proposal.source,
        family=proposal.family,
        kind=proposal.kind,
        parameters=proposal.parameters,
        evidence=proposal.evidence,
        provenance=proposal.provenance,
        review=ReviewV1(
            ReviewStatusV1.ACCEPTED,
            "fixture-reviewer",
            reviewed_claim_digest_for(proposal),
        ),
        resolution=proposal.resolution,
    )
