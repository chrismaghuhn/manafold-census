import gzip
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from manafold_census.corpus.build import (
    build_corpus,
    run_synthetic_reproduction,
    validate_corpus_output,
)
from manafold_census.corpus.index import (
    CorpusIndexError,
    build_record_index,
    inspect_record_index,
    iter_source_records,
)
from manafold_census.digest import sha256_bytes
from manafold_census.models import SourceArtifact, SourceLock

OID_0 = "00000000-0000-4000-8000-000000000000"
OID_0B = "00000000-0000-4000-8000-00000000000b"
OID_8 = "88888888-8888-4888-8888-888888888888"
OID_F = "ffffffff-ffff-4fff-8fff-ffffffffffff"
CID_0 = "00000000-0000-4000-8000-000000000001"
CID_0B = "00000000-0000-4000-8000-00000000000c"
CID_8 = "88888888-8888-4888-8888-888888888889"
CID_F = "ffffffff-ffff-4fff-8fff-fffffffffff0"


def _record(oracle_id: str, card_id: str, name: str) -> dict[str, object]:
    return {
        "object": "card",
        "oracle_id": oracle_id,
        "id": card_id,
        "name": name,
        "oracle_text": "This must not appear in the inventory.",
    }


def _write_gzip_jsonl(path: Path, records: list[dict[str, object]]) -> list[bytes]:
    raw_lines = [
        (
            json.dumps(record, ensure_ascii=False, separators=(",", ":")).encode(
                "utf-8"
            )
            + b"\n"
        )
        for record in records
    ]
    with gzip.open(path, "wb") as stream:
        for raw_line in raw_lines:
            stream.write(raw_line)
    return raw_lines


def _write_lock(source_path: Path, lock_path: Path) -> SourceLock:
    data = source_path.read_bytes()
    lock = SourceLock(
        (
            SourceArtifact(
                source_id="synthetic-oracle-source",
                locator="fixture://synthetic-oracle.jsonl.gz",
                sha256=sha256_bytes(data),
                byte_length=len(data),
                media_type="application/gzip",
            ),
        )
    )
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_bytes(
        json.dumps(lock.to_wire(), sort_keys=True, separators=(",", ":")).encode()
    )
    return lock


def test_source_records_hash_exact_raw_decompressed_jsonl_lines(tmp_path: Path) -> None:
    source_path = tmp_path / "source.jsonl.gz"
    raw_lines = _write_gzip_jsonl(
        source_path,
        [_record(OID_8, CID_8, "Eight")],
    )

    entries = list(iter_source_records(source_path))

    assert entries[0].oracle_id == OID_8
    assert entries[0].source_card_id == CID_8
    assert entries[0].name == "Eight"
    assert entries[0].source_record_sha256 == hashlib.sha256(raw_lines[0]).hexdigest()
    assert set(entries[0].to_wire()) == {
        "oracle_id",
        "source_card_id",
        "name",
        "source_record_sha256",
    }


def test_index_sorts_oracle_ids_and_writes_exactly_16_shards(tmp_path: Path) -> None:
    source_path = tmp_path / "source.jsonl.gz"
    _write_gzip_jsonl(
        source_path,
        [
            _record(OID_F, CID_F, "F"),
            _record(OID_0, CID_0, "Zero"),
            _record(OID_8, CID_8, "Eight"),
        ],
    )
    output = tmp_path / "records"

    summary = build_record_index(source_path, output)

    assert sorted(path.name for path in output.iterdir()) == [
        f"{shard}.jsonl" for shard in "0123456789abcdef"
    ]
    assert summary.record_count == 3
    assert summary.unique_oracle_id_count == 3
    assert summary.duplicate_oracle_id_count == 0
    assert summary.shard_record_counts == {
        "0": 1,
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
    for path in output.iterdir():
        if path.stat().st_size:
            assert path.read_bytes().endswith(b"\n")

    inspected = inspect_record_index(output)
    assert inspected.aggregate_digest == summary.aggregate_digest


def test_same_source_bytes_produce_byte_identical_index_outputs(tmp_path: Path) -> None:
    source_path = tmp_path / "source.jsonl.gz"
    _write_gzip_jsonl(
        source_path, [_record(OID_F, CID_F, "F"), _record(OID_0, CID_0, "Zero")]
    )
    output_a = tmp_path / "records-a"
    output_b = tmp_path / "records-b"

    first = build_record_index(source_path, output_a)
    second = build_record_index(source_path, output_b)

    assert first.aggregate_digest == second.aggregate_digest
    for name in [*"0123456789abcdef"]:
        assert (output_a / f"{name}.jsonl").read_bytes() == (
            output_b / f"{name}.jsonl"
        ).read_bytes()


@pytest.mark.parametrize(
    "records",
    [
        [{"object": "card", "id": CID_0, "name": "Missing Oracle"}],
        [_record("not-a-uuid", CID_0, "Invalid Oracle")],
        [_record(OID_0, "not-a-uuid", "Invalid Card ID")],
        [{"object": "card", "oracle_id": OID_0, "id": CID_0, "name": ""}],
        [
            {
                "object": "not-card",
                "oracle_id": OID_0,
                "id": CID_0,
                "name": "Wrong object",
            }
        ],
        [{"oracle_id": OID_0, "id": CID_0, "name": "No object"}],
    ],
)
def test_invalid_source_records_fail_closed(
    tmp_path: Path, records: list[dict[str, object]]
) -> None:
    source_path = tmp_path / "source.jsonl.gz"
    _write_gzip_jsonl(source_path, records)

    with pytest.raises(CorpusIndexError):
        list(iter_source_records(source_path))


def test_non_object_and_malformed_jsonl_records_fail_closed(tmp_path: Path) -> None:
    source_path = tmp_path / "source.jsonl.gz"
    with gzip.open(source_path, "wb") as stream:
        stream.write(b"[]\n")
        stream.write(b"{not-json}\n")

    with pytest.raises(CorpusIndexError):
        list(iter_source_records(source_path))


def test_duplicate_oracle_ids_fail_instead_of_deduplicating(tmp_path: Path) -> None:
    source_path = tmp_path / "source.jsonl.gz"
    _write_gzip_jsonl(
        source_path,
        [_record(OID_0, CID_0, "First"), _record(OID_0, CID_8, "Second")],
    )

    with pytest.raises(CorpusIndexError, match="duplicate oracle_id"):
        build_record_index(source_path, tmp_path / "records")


def test_index_validator_rejects_missing_unexpected_and_misordered_shards(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "source.jsonl.gz"
    _write_gzip_jsonl(
        source_path, [_record(OID_0, CID_0, "Zero"), _record(OID_8, CID_8, "Eight")]
    )
    output = tmp_path / "records"
    build_record_index(source_path, output)

    (output / "f.jsonl").unlink()
    with pytest.raises(CorpusIndexError, match="missing shard"):
        inspect_record_index(output)

    (output / "f.jsonl").write_bytes(b"")
    (output / "unexpected.jsonl").write_bytes(b"")
    with pytest.raises(CorpusIndexError, match="unexpected shard"):
        inspect_record_index(output)
    (output / "unexpected.jsonl").unlink()

    zero = (output / "0.jsonl").read_bytes()
    eight = (output / "8.jsonl").read_bytes()
    (output / "0.jsonl").write_bytes(eight)
    (output / "8.jsonl").write_bytes(zero)
    with pytest.raises(CorpusIndexError, match="shard"):
        inspect_record_index(output)


def test_index_validator_rejects_out_of_order_records_within_one_shard(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "source.jsonl.gz"
    _write_gzip_jsonl(
        source_path,
        [_record(OID_0, CID_0, "Zero"), _record(OID_0B, CID_0B, "Zero B")],
    )
    output = tmp_path / "records"
    build_record_index(source_path, output)
    lines = (output / "0.jsonl").read_bytes().splitlines(keepends=True)
    (output / "0.jsonl").write_bytes(b"".join(reversed(lines)))

    with pytest.raises(CorpusIndexError, match="not strictly ordered"):
        inspect_record_index(output)


def test_build_emits_manifests_and_source_fact_report(tmp_path: Path) -> None:
    source_path = tmp_path / "source.jsonl.gz"
    _write_gzip_jsonl(
        source_path, [_record(OID_8, CID_8, "Eight"), _record(OID_0, CID_0, "Zero")]
    )
    lock_path = tmp_path / "source-lock.json"
    lock = _write_lock(source_path, lock_path)
    output = tmp_path / "build"

    result = build_corpus(source_path, lock_path, output)

    assert result.dataset.record_count == 2
    assert result.dataset.source_lock_digest == lock.digest()
    assert result.artifact.content_sha256 == result.index.aggregate_digest
    report = json.loads((output / "corpus-report.json").read_text(encoding="utf-8"))
    assert report["record_provenance"] == "SOURCE_FACT"
    assert report["record_count"] == 2
    assert report["unique_oracle_id_count"] == 2
    assert report["duplicate_oracle_id_count"] == 0
    assert report["shard_count"] == 16
    assert report["aggregate_index_digest"] == result.index.aggregate_digest
    assert "oracle_text" not in (output / "records" / "0.jsonl").read_text(
        encoding="utf-8"
    )


def test_two_corpus_builds_have_complete_byte_parity(tmp_path: Path) -> None:
    source_path = tmp_path / "source.jsonl.gz"
    _write_gzip_jsonl(
        source_path, [_record(OID_F, CID_F, "F"), _record(OID_0, CID_0, "Zero")]
    )
    lock_path = tmp_path / "source-lock.json"
    _write_lock(source_path, lock_path)
    output_a = tmp_path / "build-a"
    output_b = tmp_path / "build-b"

    build_corpus(source_path, lock_path, output_a)
    build_corpus(source_path, lock_path, output_b)

    files_a = sorted(path.relative_to(output_a) for path in output_a.rglob("*"))
    files_b = sorted(path.relative_to(output_b) for path in output_b.rglob("*"))
    assert files_a == files_b
    for relative in files_a:
        if (output_a / relative).is_file():
            assert (output_a / relative).read_bytes() == (
                output_b / relative
            ).read_bytes()


def test_source_lock_digest_mismatch_rejects_corpus_build(tmp_path: Path) -> None:
    source_path = tmp_path / "source.jsonl.gz"
    _write_gzip_jsonl(source_path, [_record(OID_0, CID_0, "Zero")])
    lock_path = tmp_path / "source-lock.json"
    _write_lock(source_path, lock_path)
    source_path.write_bytes(b"changed")

    with pytest.raises(ValueError, match="source digest mismatch"):
        build_corpus(source_path, lock_path, tmp_path / "build")


def test_corpus_validator_rejects_index_aggregate_digest_mismatch(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "source.jsonl.gz"
    _write_gzip_jsonl(source_path, [_record(OID_0, CID_0, "Zero")])
    lock_path = tmp_path / "source-lock.json"
    _write_lock(source_path, lock_path)
    output = tmp_path / "build"
    build_corpus(source_path, lock_path, output)
    artifact = json.loads(
        (output / "artifact-manifest.json").read_text(encoding="utf-8")
    )
    artifact["content_sha256"] = "0" * 64
    (output / "artifact-manifest.json").write_bytes(
        json.dumps(artifact, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )

    with pytest.raises(ValueError, match="aggregate digest mismatch"):
        validate_corpus_output(output)


def test_corpus_validator_rejects_report_count_mismatch(tmp_path: Path) -> None:
    source_path = tmp_path / "source.jsonl.gz"
    _write_gzip_jsonl(source_path, [_record(OID_0, CID_0, "Zero")])
    lock_path = tmp_path / "source-lock.json"
    _write_lock(source_path, lock_path)
    output = tmp_path / "build"
    build_corpus(source_path, lock_path, output)
    report = json.loads((output / "corpus-report.json").read_text(encoding="utf-8"))
    report["unique_oracle_id_count"] = 0
    (output / "corpus-report.json").write_bytes(
        json.dumps(report, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )

    with pytest.raises(ValueError, match="unique Oracle ID count"):
        validate_corpus_output(output)


def test_offline_synthetic_reproduction_is_byte_identical() -> None:
    digest_a, digest_b = run_synthetic_reproduction()

    assert digest_a == digest_b


def test_corpus_check_cli_runs_the_offline_synthetic_reproduction() -> None:
    repository_root = Path(__file__).parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "manafold_census.cli", "corpus-check", "--synthetic"],
        cwd=repository_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "synthetic_reproduction=PASS" in result.stdout


def test_corpus_build_cli_fails_nonzero_without_a_pinned_source_lock(
    tmp_path: Path,
) -> None:
    repository_root = Path(__file__).parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "manafold_census.cli",
            "corpus-build",
            "--repository-root",
            str(tmp_path),
            "--output",
            str(tmp_path / "build"),
        ],
        cwd=repository_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "corpus-build=FAIL" in result.stderr
