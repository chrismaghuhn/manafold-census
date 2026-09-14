from __future__ import annotations

import pytest

from manafold_census.capability.binding import (
    BindingStateV1,
    ParameterBindingV1,
    validate_binding_against_requirement,
)
from manafold_census.capability.dimensions import M2DimensionPathV1
from manafold_census.semantic.evidence import (
    SourceRecordRefV1,
    StructuralFieldEvidenceV1,
)
from manafold_census.semantic.kind_payloads import (
    DrawCardsParametersV1,
    MoveBetweenZonesParametersV1,
)
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
    UnknownReasonV1,
    UnknownValueV1,
    ZoneNameV1,
    ZoneRefV1,
)

ORACLE_ID = "abcdefab-abcd-4abc-8abc-abcdefabcdef"
SOURCE_CARD_ID = "abcdefab-abcd-4abc-8abc-abcdefabcdea"


def _source() -> SourceRecordRefV1:
    return SourceRecordRefV1(
        "census.structural-card.v1",
        "a" * 64,
        ORACLE_ID,
        SOURCE_CARD_ID,
        "b" * 64,
    )


def _provenance() -> ProvenanceV1:
    return ProvenanceV1((DerivationV1(DerivationMethodV1.PARSER, "task2-test", "1"),))


def _entity(role: EntityRoleV1 = EntityRoleV1.SOURCE) -> EntityRefV1:
    return EntityRefV1(role, MultiplicityV1.ONE, None)


def _requirement(
    parameters: object,
    kind: RequirementKindV1,
    resolution: ResolutionV1 | None = None,
) -> RequirementV1:
    source = _source()
    family = (
        RequirementFamilyV1.EFFECT
        if kind is not RequirementKindV1.UNRESOLVED
        else RequirementFamilyV1.UNKNOWN
    )
    return RequirementV1.create(
        source=source,
        family=family,
        kind=kind,
        parameters=parameters,  # type: ignore[arg-type]
        evidence=(StructuralFieldEvidenceV1(source, "oracle_text", None, None),),
        provenance=_provenance(),
        review=ReviewV1(ReviewStatusV1.PROPOSED, None, None),
        resolution=resolution
        or ResolutionV1(ResolutionStateV1.COMPLETE, ResolutionReasonV1.NONE, ()),
    )


def _draw_requirement(quantity: QuantityV1) -> RequirementV1:
    return _requirement(
        DrawCardsParametersV1(_entity(EntityRoleV1.CONTROLLER), quantity),
        RequirementKindV1.DRAW_CARDS,
    )


def _unknown_draw_requirement() -> RequirementV1:
    return _requirement(
        DrawCardsParametersV1(
            _entity(EntityRoleV1.CONTROLLER),
            QuantityV1(
                QuantityModeV1.UNKNOWN,
                UnknownValueV1(UnknownReasonV1.UNKNOWN_SEMANTICS, None),
            ),
        ),
        RequirementKindV1.DRAW_CARDS,
        ResolutionV1(
            ResolutionStateV1.PARTIAL,
            ResolutionReasonV1.UNKNOWN_SEMANTICS,
            ("/parameters/quantity",),
        ),
    )


def _move_requirement_without_cause() -> RequirementV1:
    return _requirement(
        MoveBetweenZonesParametersV1(
            _entity(),
            ZoneRefV1(ZoneNameV1.LIBRARY, None),
            ZoneRefV1(ZoneNameV1.HAND, None),
            QuantityV1(QuantityModeV1.EXACT, 1),
            None,
        ),
        RequirementKindV1.MOVE_BETWEEN_ZONES,
    )


def test_known_binding_requires_the_registered_m2_wire_type() -> None:
    with pytest.raises(ValueError, match="quantity"):
        ParameterBindingV1.known(
            M2DimensionPathV1.DRAW_CARDS_QUANTITY,
            {"completely": "wrong"},
        )


def test_known_binding_is_canonicalized_as_the_typed_m2_value() -> None:
    binding = ParameterBindingV1.known(
        M2DimensionPathV1.DRAW_CARDS_QUANTITY,
        {"mode": "exact", "value": 2},
    )

    assert binding.state is BindingStateV1.KNOWN
    assert binding.value == {"mode": "exact", "value": 2}


def test_known_binding_rejects_a_semantically_unknown_m2_value() -> None:
    with pytest.raises(ValueError, match="unknown M2 value"):
        ParameterBindingV1.known(
            M2DimensionPathV1.DRAW_CARDS_QUANTITY,
            {
                "mode": "unknown",
                "value": {
                    "reason": "UNKNOWN_SEMANTICS",
                    "hint": None,
                },
            },
        )


def test_binding_recompute_matches_the_exact_requirement_value() -> None:
    requirement = _draw_requirement(QuantityV1(QuantityModeV1.EXACT, 2))
    matching = ParameterBindingV1.known(
        M2DimensionPathV1.DRAW_CARDS_QUANTITY,
        {"mode": "exact", "value": 2},
    )
    validate_binding_against_requirement(requirement, matching)

    stale = ParameterBindingV1.known(
        M2DimensionPathV1.DRAW_CARDS_QUANTITY,
        {"mode": "exact", "value": 3},
    )
    with pytest.raises(ValueError, match="does not match"):
        validate_binding_against_requirement(requirement, stale)


def test_known_binding_cannot_bind_an_unknown_requirement_value() -> None:
    requirement = _unknown_draw_requirement()
    binding = ParameterBindingV1.known(
        M2DimensionPathV1.DRAW_CARDS_QUANTITY,
        {"mode": "exact", "value": 2},
    )

    with pytest.raises(ValueError, match="unknown Requirement value"):
        validate_binding_against_requirement(requirement, binding)


def test_binding_recompute_rejects_a_cross_kind_path() -> None:
    requirement = _draw_requirement(QuantityV1(QuantityModeV1.EXACT, 2))
    binding = ParameterBindingV1.known(
        M2DimensionPathV1.DEAL_DAMAGE_AMOUNT,
        {"mode": "exact", "value": 2},
    )

    with pytest.raises(ValueError, match="family/kind"):
        validate_binding_against_requirement(requirement, binding)


def test_unknown_binding_requires_requirement_resolution_evidence() -> None:
    requirement = _unknown_draw_requirement()
    binding = ParameterBindingV1.unknown(
        M2DimensionPathV1.DRAW_CARDS_QUANTITY,
        "UNKNOWN_SEMANTICS",
        "/parameters/quantity",
    )

    validate_binding_against_requirement(requirement, binding)

    wrong_reason = ParameterBindingV1.unknown(
        M2DimensionPathV1.DRAW_CARDS_QUANTITY,
        "INSUFFICIENT_EVIDENCE",
        "/parameters/quantity",
    )
    with pytest.raises(ValueError, match="resolution reason"):
        validate_binding_against_requirement(requirement, wrong_reason)


def test_not_applicable_requires_an_actual_optional_null_value() -> None:
    requirement = _move_requirement_without_cause()
    binding = ParameterBindingV1.not_applicable(
        M2DimensionPathV1.MOVE_BETWEEN_ZONES_CAUSE
    )

    validate_binding_against_requirement(requirement, binding)
