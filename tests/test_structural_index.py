import gzip
import json
from pathlib import Path

import pytest

from manafold_census.canonical import canonical_json_bytes
from manafold_census.structural.extract import iter_structural_records
from manafold_census.structural.index import (
    SHARD_NAMES,
    StructuralIndexError,
    aggregate_structural_index_digest,
    build_structural_index,
    inspect_structural_index,
)
from manafold_census.structural.model import StructuralCardRecordV1

OID_0 = "00000000-0000-4000-8000-000000000000"
OID_0B = "00000000-0000-4000-8000-00000000000b"
OID_8 = "88888888-8888-4888-8888-888888888888"
OID_F = "ffffffff-ffff-4fff-8fff-ffffffffffff"
CID_0 = "00000000-0000-4000-8000-000000000001"
CID_0B = "00000000-0000-4000-8000-00000000000c"
CID_8 = "88888888-8888-4888-8888-888888888889"
CID_F = "ffffffff-ffff-4fff-8fff-fffffffffff0"


def _source_record(oracle_id: str, source_card_id: str, name: str) -> dict[str, object]:
    return {
        "object": "card",
        "oracle_id": oracle_id,
        "id": source_card_id,
        "name": name,
        "layout": "normal",
    }


def _write_gzip_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    with gzip.open(path, "wb") as stream:
        for record in records:
            stream.write(
                json.dumps(record, separators=(",", ":"), ensure_ascii=False).encode()
                + b"\n"
            )


def _source_with_records(path: Path) -> None:
    _write_gzip_jsonl(
        path,
        [
            _source_record(OID_F, CID_F, "F"),
            _source_record(OID_8, CID_8, "Eight"),
            _source_record(OID_0B, CID_0B, "Zero B"),
            _source_record(OID_0, CID_0, "Zero"),
        ],
    )


def test_build_writes_all_16_shards_and_sorts_each_shard(tmp_path: Path) -> None:
    source_path = tmp_path / "source.jsonl.gz"
    _source_with_records(source_path)
    output = tmp_path / "records"

    summary = build_structural_index(source_path, output)

    assert tuple(path.stem for path in sorted(output.glob("*.jsonl"))) == SHARD_NAMES
    assert summary.record_count == 4
    assert summary.unique_oracle_id_count == 4
    assert summary.duplicate_oracle_id_count == 0
    assert summary.shard_record_counts == {
        "0": 2,
        "1": 0,
        "2": 0,
        "3": 0,
        "4": 0,
        "5": 0,
        "6": 0,
        "7": 0,
        "8": 1,
        "9": 0,
        "a": 0,
        "b": 0,
        "c": 0,
        "d": 0,
        "e": 0,
        "f": 1,
    }
    assert [
        json.loads(line)["oracle_id"]
        for line in (output / "0.jsonl").read_bytes().splitlines()
    ] == [OID_0, OID_0B]
    for shard in SHARD_NAMES:
        shard_path = output / f"{shard}.jsonl"
        if shard_path.stat().st_size:
            assert shard_path.read_bytes().endswith(b"\n")


def test_shard_lines_are_exact_canonical_structural_jsonl(tmp_path: Path) -> None:
    source_path = tmp_path / "source.jsonl.gz"
    _write_gzip_jsonl(source_path, [_source_record(OID_8, CID_8, "Eight")])
    output = tmp_path / "records"
    build_structural_index(source_path, output)

    raw_line = (output / "8.jsonl").read_bytes()
    document = json.loads(raw_line)
    record = StructuralCardRecordV1.from_wire(document)

    assert raw_line == canonical_json_bytes(record.to_wire()) + b"\n"


def test_same_source_bytes_produce_byte_identical_shards_and_digest(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "source.jsonl.gz"
    _source_with_records(source_path)
    output_a = tmp_path / "records-a"
    output_b = tmp_path / "records-b"

    summary_a = build_structural_index(source_path, output_a)
    summary_b = build_structural_index(source_path, output_b)

    assert summary_a.aggregate_digest == summary_b.aggregate_digest
    assert summary_a.aggregate_digest == aggregate_structural_index_digest(
        summary_a.shards
    )
    for shard in SHARD_NAMES:
        assert (output_a / f"{shard}.jsonl").read_bytes() == (
            output_b / f"{shard}.jsonl"
        ).read_bytes()


def test_build_rejects_duplicate_oracle_ids_and_nonempty_output(tmp_path: Path) -> None:
    source_path = tmp_path / "source.jsonl.gz"
    _write_gzip_jsonl(
        source_path,
        [
            _source_record(OID_0, CID_0, "First"),
            _source_record(OID_0, CID_0B, "Second"),
        ],
    )

    with pytest.raises(StructuralIndexError, match="duplicate oracle_id"):
        build_structural_index(source_path, tmp_path / "duplicate-records")

    valid_source = tmp_path / "valid-source.jsonl.gz"
    _write_gzip_jsonl(valid_source, [_source_record(OID_0, CID_0, "Zero")])
    output = tmp_path / "records"
    build_structural_index(valid_source, output)

    with pytest.raises(StructuralIndexError, match="must be empty"):
        build_structural_index(valid_source, output)


def test_inspection_rejects_missing_and_extra_shards(tmp_path: Path) -> None:
    source_path = tmp_path / "source.jsonl.gz"
    _write_gzip_jsonl(source_path, [_source_record(OID_0, CID_0, "Zero")])
    output = tmp_path / "records"
    build_structural_index(source_path, output)

    (output / "f.jsonl").unlink()
    with pytest.raises(StructuralIndexError, match="missing shard"):
        inspect_structural_index(output)

    (output / "f.jsonl").write_bytes(b"")
    (output / "unexpected.jsonl").write_bytes(b"")
    with pytest.raises(StructuralIndexError, match="unexpected shard"):
        inspect_structural_index(output)


def test_inspection_rejects_wrong_shard(tmp_path: Path) -> None:
    source_path = tmp_path / "source.jsonl.gz"
    _write_gzip_jsonl(source_path, [_source_record(OID_0, CID_0, "Zero")])
    output = tmp_path / "records"
    build_structural_index(source_path, output)

    data = (output / "0.jsonl").read_bytes()
    (output / "0.jsonl").write_bytes(b"")
    (output / "1.jsonl").write_bytes(data)

    with pytest.raises(StructuralIndexError, match="wrong shard"):
        inspect_structural_index(output)


def test_inspection_rejects_out_of_order_records(tmp_path: Path) -> None:
    source_path = tmp_path / "source.jsonl.gz"
    _write_gzip_jsonl(
        source_path,
        [
            _source_record(OID_0, CID_0, "Zero"),
            _source_record(OID_0B, CID_0B, "Zero B"),
        ],
    )
    output = tmp_path / "records"
    build_structural_index(source_path, output)
    lines = (output / "0.jsonl").read_bytes().splitlines(keepends=True)
    (output / "0.jsonl").write_bytes(b"".join(reversed(lines)))

    with pytest.raises(StructuralIndexError, match="strictly ordered"):
        inspect_structural_index(output)


def test_inspection_rejects_noncanonical_line_bytes(tmp_path: Path) -> None:
    source_path = tmp_path / "source.jsonl.gz"
    _write_gzip_jsonl(source_path, [_source_record(OID_0, CID_0, "Zero")])
    output = tmp_path / "records"
    build_structural_index(source_path, output)
    document = json.loads((output / "0.jsonl").read_bytes())
    (output / "0.jsonl").write_bytes(
        json.dumps(document, separators=(", ", ": ")).encode("utf-8") + b"\n"
    )

    with pytest.raises(StructuralIndexError, match="canonical JSONL"):
        inspect_structural_index(output)


def test_inspection_rejects_missing_final_lf(tmp_path: Path) -> None:
    source_path = tmp_path / "source.jsonl.gz"
    _write_gzip_jsonl(source_path, [_source_record(OID_0, CID_0, "Zero")])
    output = tmp_path / "records"
    build_structural_index(source_path, output)
    path = output / "0.jsonl"
    path.write_bytes(path.read_bytes()[:-1])

    with pytest.raises(StructuralIndexError, match="final LF"):
        inspect_structural_index(output)


def test_iterated_structural_records_are_the_index_input(tmp_path: Path) -> None:
    source_path = tmp_path / "source.jsonl.gz"
    _source_with_records(source_path)

    records = list(iter_structural_records(source_path))

    assert len(records) == 4
    assert {record.oracle_id for record in records} == {
        OID_0,
        OID_0B,
        OID_8,
        OID_F,
    }
