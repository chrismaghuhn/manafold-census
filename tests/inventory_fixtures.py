from __future__ import annotations

from manafold_census.structural.model import (
    StructuralCardRecordV1,
    StructuralFaceV1,
)


def _uuid(number: int) -> str:
    return f"{number:08x}-0000-4000-8000-{number:012x}"


def structural_card(
    number: int,
    *,
    name: str,
    oracle_text: str | None,
    faces: tuple[StructuralFaceV1, ...] | None = None,
    layout: str = "normal",
    keywords: tuple[str, ...] | None = ("Fixture",),
) -> StructuralCardRecordV1:
    return StructuralCardRecordV1(
        oracle_id=_uuid(number),
        source_card_id=_uuid(number + 100),
        source_record_sha256=f"{number:064x}",
        name=name,
        layout=layout,
        mana_cost="{1}{G}",
        type_line="Creature",
        oracle_text=oracle_text,
        colors=("G",),
        color_identity=("G",),
        color_indicator=None,
        keywords=keywords,
        produced_mana=None,
        power="2",
        toughness="2",
        loyalty=None,
        defense=None,
        hand_modifier=None,
        life_modifier=None,
        attraction_lights=None,
        faces=faces,
        all_parts=None,
    )


def face(
    index: int,
    *,
    name: str,
    oracle_text: str | None,
    type_line: str = "Creature",
) -> StructuralFaceV1:
    return StructuralFaceV1(
        face_index=index,
        name=name,
        mana_cost="{G}",
        type_line=type_line,
        oracle_text=oracle_text,
        colors=("G",),
        color_indicator=None,
        power="2",
        toughness="2",
        loyalty=None,
        defense=None,
    )


def records() -> tuple[StructuralCardRecordV1, ...]:
    return (
        structural_card(
            1,
            name="Alpha",
            oracle_text="Shared line.\nValue 1 {G}",
        ),
        structural_card(
            2,
            name="Beta",
            oracle_text="Shared line.\nValue 2 {U}",
        ),
        structural_card(3, name="Singleton", oracle_text="Rare one-off."),
        structural_card(
            4,
            name="Double",
            oracle_text=None,
            layout="modal_dfc",
            faces=(
                face(0, name="Double Front", oracle_text="Shared line."),
                face(1, name="Double Back", oracle_text="Unicode λ\n"),
            ),
        ),
        structural_card(5, name="Empty", oracle_text=""),
    )
