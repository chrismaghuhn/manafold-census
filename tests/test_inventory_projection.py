from __future__ import annotations

from tests.inventory_fixtures import records


def test_projection_preserves_card_face_null_and_empty_surfaces() -> None:
    from manafold_census.inventory.model import SurfaceScopeV1
    from manafold_census.inventory.projection import project_surfaces

    surfaces = project_surfaces(records())

    card_surfaces = [
        item for item in surfaces if item.scope is SurfaceScopeV1.CARD_TEXT
    ]
    face_surfaces = [
        item for item in surfaces if item.scope is SurfaceScopeV1.FACE_TEXT
    ]
    line_surfaces = [
        item for item in surfaces if item.scope is SurfaceScopeV1.ABILITY_LINE
    ]

    assert len(card_surfaces) == 5
    assert len(face_surfaces) == 2
    assert len(line_surfaces) == 9
    assert (
        next(item for item in card_surfaces if item.card_name == "Double").raw_text
        is None
    )
    assert any(
        item.face_index == 1 and item.raw_text == "Unicode λ" for item in line_surfaces
    )
    assert any(item.raw_text == "" for item in line_surfaces)
    assert all(item.authority_scope == "NON_AUTHORITATIVE" for item in surfaces)


def test_projection_keeps_face_provenance_distinct_from_parent_provenance() -> None:
    from manafold_census.inventory.model import SurfaceScopeV1
    from manafold_census.inventory.projection import project_surfaces

    surfaces = project_surfaces(records())
    double = [item for item in surfaces if item.card_name == "Double"]

    assert {(item.scope, item.face_index, item.line_index) for item in double} == {
        (SurfaceScopeV1.CARD_TEXT, None, None),
        (SurfaceScopeV1.FACE_TEXT, 0, None),
        (SurfaceScopeV1.FACE_TEXT, 1, None),
        (SurfaceScopeV1.ABILITY_LINE, 0, 0),
        (SurfaceScopeV1.ABILITY_LINE, 1, 0),
        (SurfaceScopeV1.ABILITY_LINE, 1, 1),
    }
