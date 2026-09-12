"""Deterministic offline structural source and reproduction runner."""

from __future__ import annotations

import filecmp
import gzip
import io
import tempfile
from pathlib import Path
from typing import cast

from ..canonical import JSONValue, canonical_json_bytes
from ..digest import REPRODUCTION_DOMAIN, domain_digest, measure_file
from ..models import SourceArtifact, SourceLock
from .build import build_structural_corpus
from .check import validate_structural_output


def _synthetic_records() -> tuple[dict[str, JSONValue], ...]:
    return (
        {
            "object": "card",
            "oracle_id": "00000000-0000-4000-8000-000000000000",
            "id": "00000000-0000-4000-8000-000000000001",
            "name": "Synthetic Simple",
            "layout": "normal",
        },
        {
            "object": "card",
            "oracle_id": "88888888-8888-4888-8888-888888888888",
            "id": "88888888-8888-4888-8888-888888888889",
            "name": "Synthetic Faces",
            "layout": "modal_dfc",
            "mana_cost": "{2}{G}",
            "type_line": "Creature",
            "oracle_text": "",
            "colors": [],
            "color_identity": ["G"],
            "color_indicator": [],
            "keywords": [],
            "produced_mana": ["G"],
            "power": "1+*",
            "toughness": "7-*",
            "attraction_lights": [1, 5],
            "card_faces": [
                {
                    "name": "Synthetic Front",
                    "mana_cost": "{G}",
                    "type_line": "Creature",
                    "oracle_text": "",
                    "colors": [],
                    "color_indicator": [],
                    "power": "*",
                    "toughness": "1+*",
                },
                {
                    "name": "Synthetic Back",
                    "mana_cost": "",
                    "type_line": "Land",
                    "oracle_text": "Unicode λ",
                    "colors": ["G"],
                    "color_indicator": ["G"],
                },
            ],
            "all_parts": [
                {
                    "component": "related",
                    "id": "00000000-0000-4000-8000-000000000001",
                    "name": "Synthetic Simple",
                    "object": "card",
                    "type_line": "Normal",
                    "uri": "fixture://opaque-related-uri",
                }
            ],
        },
        {
            "object": "card",
            "oracle_id": "ffffffff-ffff-4fff-8fff-ffffffffffff",
            "id": "ffffffff-ffff-4fff-8fff-fffffffffff0",
            "name": "Synthetic Raw",
            "layout": "normal",
            "oracle_text": "Raw\ntext",
            "colors": ["U", "R"],
            "color_identity": ["R", "U"],
            "keywords": ["Second", "First"],
            "power": "*",
            "toughness": "1+*",
            "loyalty": "3",
            "defense": "*",
            "hand_modifier": "-1",
            "life_modifier": "+2",
        },
    )


def synthetic_source_bytes() -> bytes:
    """Return deterministic gzip JSONL bytes for the offline M1 check."""

    output = io.BytesIO()
    with gzip.GzipFile(fileobj=output, mode="wb", filename="", mtime=0) as stream:
        for record in _synthetic_records():
            stream.write(canonical_json_bytes(record) + b"\n")
    return output.getvalue()


def _write_synthetic_input(root: Path) -> tuple[Path, Path]:
    source_path = root / "source.jsonl.gz"
    source_path.write_bytes(synthetic_source_bytes())
    measurement = measure_file(source_path)
    lock = SourceLock(
        (
            SourceArtifact(
                source_id="synthetic-structural-source",
                locator="fixture://synthetic-structural-source.jsonl.gz",
                sha256=measurement.sha256,
                byte_length=measurement.byte_length,
                media_type="application/gzip",
            ),
        )
    )
    lock_path = root / "source-lock.json"
    lock_path.write_bytes(canonical_json_bytes(lock.to_wire()))
    return source_path, lock_path


def _file_map(directory: Path) -> dict[str, Path]:
    return {
        path.relative_to(directory).as_posix(): path
        for path in directory.rglob("*")
        if path.is_file()
    }


def _directory_digest(directory: Path) -> str:
    entries: list[dict[str, JSONValue]] = []
    for relative_path, path in sorted(_file_map(directory).items()):
        measurement = measure_file(path)
        entries.append(
            {
                "path": relative_path,
                "sha256": measurement.sha256,
                "byte_length": measurement.byte_length,
            }
        )
    return domain_digest(REPRODUCTION_DOMAIN, cast(JSONValue, entries))


def run_synthetic_reproduction() -> tuple[str, str]:
    """Build and independently check two complete synthetic output trees."""

    with (
        tempfile.TemporaryDirectory(prefix="census-structural-a-") as temp_a,
        tempfile.TemporaryDirectory(prefix="census-structural-b-") as temp_b,
    ):
        root_a = Path(temp_a)
        root_b = Path(temp_b)
        source_a, lock_a = _write_synthetic_input(root_a)
        source_b, lock_b = _write_synthetic_input(root_b)
        output_a = root_a / "build"
        output_b = root_b / "build"
        build_structural_corpus(source_a, lock_a, output_a)
        build_structural_corpus(source_b, lock_b, output_b)
        validate_structural_output(output_a, source_a, lock_a)
        validate_structural_output(output_b, source_b, lock_b)

        files_a = _file_map(output_a)
        files_b = _file_map(output_b)
        if set(files_a) != set(files_b):
            raise RuntimeError("structural synthetic file sets differ")
        for relative_path in sorted(files_a):
            if not filecmp.cmp(
                files_a[relative_path], files_b[relative_path], shallow=False
            ):
                raise RuntimeError(
                    f"structural synthetic output differs: {relative_path}"
                )
        digest_a = _directory_digest(output_a)
        digest_b = _directory_digest(output_b)
        if digest_a != digest_b:
            raise RuntimeError("structural synthetic directory digests differ")
        return digest_a, digest_b
