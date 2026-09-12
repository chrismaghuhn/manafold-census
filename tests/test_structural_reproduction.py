import gzip
import json

from manafold_census.structural.synthetic import (
    run_synthetic_reproduction,
    synthetic_source_bytes,
)


def test_synthetic_source_bytes_are_deterministic_and_mtime_free() -> None:
    first = synthetic_source_bytes()
    second = synthetic_source_bytes()

    assert first == second
    assert first[:3] == b"\x1f\x8b\x08"
    assert first[3] == 0
    assert first[4:8] == b"\x00\x00\x00\x00"


def test_synthetic_source_covers_required_structural_shapes() -> None:
    records = [
        json.loads(line)
        for line in gzip.decompress(synthetic_source_bytes()).splitlines()
    ]

    assert any("card_faces" not in record for record in records)
    assert any(len(record.get("card_faces", [])) > 1 for record in records)
    assert any(record.get("power") == "1+*" for record in records)
    assert any(record.get("keywords") == [] for record in records)
    assert any(record.get("oracle_text") == "" for record in records)
    assert any(record.get("all_parts") for record in records)
    assert any(record.get("attraction_lights") == [1, 5] for record in records)


def test_synthetic_reproduction_compares_two_complete_output_trees() -> None:
    run_a_digest, run_b_digest = run_synthetic_reproduction()

    assert run_a_digest == run_b_digest
    assert len(run_a_digest) == 64
