from __future__ import annotations

import json
from pathlib import Path

from test_census_bundle import _build_bundle

from manafold_census.reports.build import build_census_derived

INDEX_PATHS = (
    "indexes/cards-by-name.jsonl",
    "indexes/cards-by-oracle-id.jsonl",
    "indexes/requirements-by-card.jsonl",
    "indexes/links-by-requirement.jsonl",
    "indexes/cards-by-capability.jsonl",
)


def _rows(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_bytes().splitlines()]


def test_indexes_are_canonical_and_preserve_one_to_many_relationships(
    tmp_path: Path,
) -> None:
    _package, bundle_result = _build_bundle(tmp_path / "fixture")
    result = build_census_derived(bundle_result.output_dir, tmp_path / "derived")

    name_rows = _rows(result.output_dir / INDEX_PATHS[0])
    oracle_rows = _rows(result.output_dir / INDEX_PATHS[1])
    requirement_rows = _rows(result.output_dir / INDEX_PATHS[2])
    link_rows = _rows(result.output_dir / INDEX_PATHS[3])
    capability_rows = _rows(result.output_dir / INDEX_PATHS[4])

    assert len(name_rows) == 5
    assert len(oracle_rows) == 5
    assert len(requirement_rows) == 5
    assert len(link_rows) == 5
    assert len(capability_rows) == 1
    assert [row["name"] for row in name_rows] == sorted(
        row["name"] for row in name_rows
    )
    assert [row["oracle_id"] for row in oracle_rows] == sorted(
        row["oracle_id"] for row in oracle_rows
    )
    assert all(row["requirement_ids"] for row in requirement_rows)
    assert all(len(row["links"]) == 1 for row in link_rows)
    assert capability_rows[0]["mapped_requirement_count"] == 5
    assert len(capability_rows[0]["card_refs"]) == 5


def test_every_index_row_is_canonical_jsonl(tmp_path: Path) -> None:
    _package, bundle_result = _build_bundle(tmp_path / "fixture")
    result = build_census_derived(bundle_result.output_dir, tmp_path / "derived")

    for relative_path in INDEX_PATHS:
        raw = (result.output_dir / relative_path).read_bytes()
        for line in raw.splitlines(keepends=True):
            document = json.loads(line)
            assert (
                line
                == json.dumps(
                    document,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                ).encode("utf-8")
                + b"\n"
            )
