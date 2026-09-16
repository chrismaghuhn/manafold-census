"""Deterministic source-surface projection from validated M1 records."""

from __future__ import annotations

from collections.abc import Iterable

from ..structural.model import StructuralCardRecordV1, StructuralFaceV1
from .identity import source_surface_id
from .model import SourceSurfaceV1, SurfaceScopeV1


def _line_count(value: str | None) -> int:
    return 0 if value is None else value.count("\n") + 1


def _surface(
    record: StructuralCardRecordV1,
    *,
    scope: SurfaceScopeV1,
    raw_text: str | None,
    face: StructuralFaceV1 | None = None,
    line_index: int | None = None,
) -> SourceSurfaceV1:
    face_index = None if face is None else face.face_index
    return SourceSurfaceV1(
        surface_id=source_surface_id(
            oracle_id=record.oracle_id,
            source_card_id=record.source_card_id,
            source_record_sha256=record.source_record_sha256,
            scope=scope.value,
            face_index=face_index,
            line_index=line_index,
            raw_text=raw_text,
        ),
        oracle_id=record.oracle_id,
        source_card_id=record.source_card_id,
        source_record_sha256=record.source_record_sha256,
        card_name=record.name,
        face_name=None if face is None else face.name,
        layout=record.layout,
        type_line=record.type_line if face is None else face.type_line,
        keywords=record.keywords,
        face_index=face_index,
        line_index=line_index,
        scope=scope,
        raw_text=raw_text,
        face_count=1 if record.faces is None else len(record.faces),
        line_count=_line_count(raw_text),
    )


def _line_surfaces(
    record: StructuralCardRecordV1,
    *,
    face: StructuralFaceV1 | None,
    raw_text: str | None,
) -> Iterable[SourceSurfaceV1]:
    if raw_text is None:
        return ()
    return (
        _surface(
            record,
            scope=SurfaceScopeV1.ABILITY_LINE,
            raw_text=line,
            face=face,
            line_index=index,
        )
        for index, line in enumerate(raw_text.split("\n"))
    )


def _surface_sort_key(
    surface: SourceSurfaceV1,
) -> tuple[str, str, int, int, int, str]:
    scope_order = {
        SurfaceScopeV1.CARD_TEXT: 0,
        SurfaceScopeV1.FACE_TEXT: 1,
        SurfaceScopeV1.ABILITY_LINE: 2,
    }
    return (
        surface.oracle_id,
        surface.source_card_id,
        surface.face_index if surface.face_index is not None else -1,
        surface.line_index if surface.line_index is not None else -1,
        scope_order[surface.scope],
        surface.surface_id,
    )


def project_surfaces(
    records: Iterable[StructuralCardRecordV1],
) -> tuple[SourceSurfaceV1, ...]:
    """Project each validated M1 record into recoverable source surfaces."""

    ordered_records = sorted(
        records,
        key=lambda item: (
            item.oracle_id,
            item.source_card_id,
            item.source_record_sha256,
        ),
    )
    seen_oracle_ids: set[str] = set()
    surfaces: list[SourceSurfaceV1] = []
    for record in ordered_records:
        if not isinstance(record, StructuralCardRecordV1):
            raise TypeError("records must contain StructuralCardRecordV1 values")
        if record.oracle_id in seen_oracle_ids:
            raise ValueError(f"duplicate source oracle_id: {record.oracle_id}")
        seen_oracle_ids.add(record.oracle_id)
        surfaces.append(
            _surface(
                record,
                scope=SurfaceScopeV1.CARD_TEXT,
                raw_text=record.oracle_text,
            )
        )
        if record.faces is not None:
            for face in record.faces:
                surfaces.append(
                    _surface(
                        record,
                        scope=SurfaceScopeV1.FACE_TEXT,
                        raw_text=face.oracle_text,
                        face=face,
                    )
                )
        surfaces.extend(_line_surfaces(record, face=None, raw_text=record.oracle_text))
        if record.faces is not None:
            for face in record.faces:
                surfaces.extend(
                    _line_surfaces(record, face=face, raw_text=face.oracle_text)
                )
    return tuple(sorted(surfaces, key=_surface_sort_key))


__all__ = ["project_surfaces"]
