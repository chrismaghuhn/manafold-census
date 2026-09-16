from __future__ import annotations

from manafold_census.inventory._common import (
    GROUPING_POLICY_ID,
    GROUPING_POLICY_VERSION,
)
from manafold_census.inventory.grouping import (
    build_capability_opportunities,
    group_surfaces,
)
from manafold_census.inventory.identity import (
    candidate_group_id,
    source_surface_id,
)
from manafold_census.inventory.input import LoadedInventoryInputsV1
from manafold_census.inventory.model import GroupingLensV1
from manafold_census.prioritization._common import (
    ASSESSMENT_POLICY_ID,
    ASSESSMENT_POLICY_VERSION,
)
from manafold_census.prioritization.analyze import (
    build_assessments,
    classify_planning_noise,
    cluster_mechanical_overlaps,
)
from manafold_census.prioritization.assessment import OpportunityAssessmentV1
from manafold_census.prioritization.identity import (
    opportunity_assessment_id,
    surface_set_digest,
)
from manafold_census.prioritization.input import LoadedPrioritizationInputsV1

CENSUS_RELEASE = (
    "censusrel_55ff3102f75a64a0a2e1277810e709847803d085c6623ceeec14b7fe8f969e9f"
)


def _uuid(number: int) -> str:
    return f"{number:08x}-0000-4000-8000-{number:012x}"


def pipeline(records: tuple[object, ...]):
    from manafold_census.inventory.projection import project_surfaces

    surfaces = project_surfaces(records)  # type: ignore[arg-type]
    groups = group_surfaces(surfaces)
    opportunities = build_capability_opportunities(groups)
    return surfaces, groups, opportunities


def default_pipeline():
    from inventory_fixtures import records

    return pipeline(records())


def loaded_inputs_for(
    surfaces: tuple[object, ...],
    groups: tuple[object, ...],
    opportunities: tuple[object, ...],
    selected_records: tuple[object, ...],
    selected_ids: tuple[str, ...],
    families: tuple[str, ...] = (),
):
    inventory_inputs = LoadedInventoryInputsV1(
        source_lock_digest="a" * 64,
        source_lock_file_sha256="b" * 64,
        m1_manifest_sha256="c" * 64,
        m1_structural_aggregate_digest="d" * 64,
        m3_manifest_sha256="e" * 64,
        parent_m4_manifest_sha256="f" * 64,
        parent_census_release_id=CENSUS_RELEASE,
        m1_record_count=len(selected_records),
        m3_record_count=len(selected_records),
        selected_records=selected_records,  # type: ignore[arg-type]
        selected_oracle_ids=selected_ids,
    )
    from manafold_census.inventory.identity import selected_identity_set_digest

    return LoadedPrioritizationInputsV1(
        inventory_inputs=inventory_inputs,
        m6_02_manifest_sha256="9" * 64,
        m6_02_opportunity_count=len(opportunities),
        m6_02_selected_identity_set_digest=selected_identity_set_digest(selected_ids),
        surfaces=surfaces,  # type: ignore[arg-type]
        groups=groups,  # type: ignore[arg-type]
        opportunities=opportunities,  # type: ignore[arg-type]
        m4_active_family_ids=families,
    )


def default_loaded_inputs():
    from inventory_fixtures import records

    selected = records()
    surfaces, groups, opportunities = pipeline(selected)
    selected_ids = tuple(item.oracle_id for item in selected)
    return loaded_inputs_for(surfaces, groups, opportunities, selected, selected_ids)


def assessed_default():
    loaded = default_loaded_inputs()
    surfaces_by_id = {item.surface_id: item for item in loaded.surfaces}
    assessments = build_assessments(loaded.groups, loaded.opportunities, surfaces_by_id)
    clusters = cluster_mechanical_overlaps(assessments)
    return loaded, assessments, clusters


def make_surface_id(number: int, scope: str = "CARD_TEXT") -> str:
    return source_surface_id(
        oracle_id=_uuid(number),
        source_card_id=_uuid(number + 1000),
        source_record_sha256=f"{number:064x}",
        scope=scope,
        face_index=None,
        line_index=None if scope == "CARD_TEXT" else 0,
        raw_text=f"text-{number}",
    )


def make_assessment(
    tag: int,
    *,
    lens: GroupingLensV1 = GroupingLensV1.ABILITY_LINE_EXACT,
    oracle_ids: tuple[str, ...],
    raw_texts: tuple[str | None, ...] | None = None,
    surface_ids: tuple[str, ...] | None = None,
) -> OpportunityAssessmentV1:
    generated = tuple(
        make_surface_id(tag * 100 + index) for index in range(len(oracle_ids))
    )
    surfaces = (
        tuple(sorted(generated)) if surface_ids is None else tuple(sorted(surface_ids))
    )
    texts = (
        tuple(f"raw-{tag}-{index}" for index in range(len(oracle_ids)))
        if raw_texts is None
        else tuple(raw_texts)
    )
    if len(texts) != len(surfaces):
        raise ValueError("raw_texts must align one-to-one with surfaces")
    noise = classify_planning_noise(texts)
    set_digest = surface_set_digest(surfaces)
    group_id = candidate_group_id(
        lens=lens.value,
        policy_id=GROUPING_POLICY_ID,
        policy_version=GROUPING_POLICY_VERSION,
        group_key=f"key-{tag}",
    )
    from manafold_census.inventory.identity import capability_opportunity_id as opp_id

    opportunity_id = opp_id(
        candidate_group_ids=(group_id,),
        policy_id=GROUPING_POLICY_ID,
        policy_version=GROUPING_POLICY_VERSION,
    )
    ordered_oracles = tuple(sorted(oracle_ids))
    return OpportunityAssessmentV1(
        assessment_id=opportunity_assessment_id(
            opportunity_id=opportunity_id,
            assessment_policy_id=ASSESSMENT_POLICY_ID,
            assessment_policy_version=ASSESSMENT_POLICY_VERSION,
            grouping_lens=lens.value,
            member_surface_set_digest=set_digest,
            distinct_oracle_count=len(ordered_oracles),
            distinct_raw_text_count=len(set(texts)),
            occurrence_count=len(surfaces),
            planning_noise=noise.value,
        ),
        opportunity_id=opportunity_id,
        candidate_group_id=group_id,
        grouping_lens=lens,
        assessment_policy_id=ASSESSMENT_POLICY_ID,
        assessment_policy_version=ASSESSMENT_POLICY_VERSION,
        distinct_oracle_count=len(ordered_oracles),
        occurrence_count=len(surfaces),
        member_surface_count=len(surfaces),
        distinct_raw_text_count=len(set(texts)),
        planning_noise=noise,
        member_surface_set_digest=set_digest,
        member_surface_ids=surfaces,
        member_oracle_ids=ordered_oracles,
        representative_surface_ids=surfaces[:3] if len(surfaces) >= 1 else surfaces,
    )


def noise_records():
    from inventory_fixtures import structural_card

    return (
        structural_card(101, name="NullA", oracle_text=None),
        structural_card(102, name="NullB", oracle_text=None),
        structural_card(103, name="EmptyA", oracle_text=""),
        structural_card(104, name="EmptyB", oracle_text="   "),
        structural_card(105, name="NormalA", oracle_text="Draw a card."),
        structural_card(106, name="NormalB", oracle_text="Draw a card."),
    )


__all__ = [
    "CENSUS_RELEASE",
    "assessed_default",
    "default_loaded_inputs",
    "default_pipeline",
    "loaded_inputs_for",
    "make_assessment",
    "make_surface_id",
    "noise_records",
    "pipeline",
]
