from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest
from analysis_fixtures import source_ref, structural_record, trace_event

from manafold_census.analysis.manifest import (
    SHARD_NAMES,
    AnalysisManifestV1,
    AnalysisShardDescriptorV1,
    record_identity_set_digest,
)
from manafold_census.analysis.model import (
    AnalysisOutcomeV1,
    CardAnalysisRecordV1,
    NegativeReviewAuthorityRefV1,
    card_source_key,
)
from manafold_census.analysis.validate import (
    AnalysisClosureError,
    validate_analysis_closure,
)
from manafold_census.canonical import canonical_json_bytes
from manafold_census.models import SourceLock
from manafold_census.structural.index import (
    StructuralShardSummary,
    aggregate_structural_index_digest,
)
from manafold_census.structural.manifest import StructuralCardIndexManifestV1

REPOSITORY_ROOT = Path(__file__).parents[1]
SOURCE_LOCK_PATH = REPOSITORY_ROOT / "source-locks" / "scryfall-oracle-v1.json"


def source_lock_digest() -> str:
    document = json.loads(SOURCE_LOCK_PATH.read_bytes())
    return SourceLock.from_wire(document).digest()


def structural_fixture_records(count: int) -> list:
    records = [structural_record()]
    for index in range(1, count):
        suffix = format(index, "x")
        records.append(
            structural_record(
                oracle_id=f"abcdefab-abcd-4abc-8abc-abcdefabcde{suffix}",
                source_card_id=f"abcdefab-abcd-4abc-8abc-abcdefabcdf{suffix}",
                source_record_sha256=(str(index) * 64)[:64],
            )
        )
    return sorted(records, key=lambda record: record.oracle_id)


def write_m1_authority(
    tmp_path: Path, count: int = 1
) -> tuple[Path, list, StructuralCardIndexManifestV1]:
    root = tmp_path / "m1"
    records_dir = root / "records"
    records_dir.mkdir(parents=True)
    records = structural_fixture_records(count)
    raw_by_shard = {shard: bytearray() for shard in SHARD_NAMES}
    for record in records:
        raw_by_shard[record.oracle_id[0]].extend(
            canonical_json_bytes(record.to_wire()) + b"\n"
        )
    summaries = []
    for shard in SHARD_NAMES:
        raw = bytes(raw_by_shard[shard])
        (records_dir / f"{shard}.jsonl").write_bytes(raw)
        summaries.append(
            StructuralShardSummary(
                shard=shard,
                relative_path=f"records/{shard}.jsonl",
                sha256=hashlib.sha256(raw).hexdigest(),
                byte_length=len(raw),
                record_count=raw.count(b"\n"),
            )
        )
    manifest = StructuralCardIndexManifestV1(
        tuple(summaries),
        aggregate_structural_index_digest(tuple(summaries)),
    )
    (root / "structural-index-manifest.json").write_bytes(
        canonical_json_bytes(manifest.to_wire())
    )
    return root, records, manifest


def m3_card(record, lock_digest: str) -> CardAnalysisRecordV1:
    source = source_ref(
        source_lock_digest=lock_digest,
        oracle_id=record.oracle_id,
        source_card_id=record.source_card_id,
        source_record_sha256=record.source_record_sha256,
    )
    return CardAnalysisRecordV1(
        source=source,
        outcome=AnalysisOutcomeV1.UNRESOLVED_ANALYSIS,
        bundle=None,
        no_requirements_basis=None,
    )


def descriptor_for(
    path: Path, relative_path: str, record_count: int
) -> AnalysisShardDescriptorV1:
    raw = path.read_bytes()
    return AnalysisShardDescriptorV1(
        relative_path=relative_path,
        sha256=hashlib.sha256(raw).hexdigest(),
        byte_length=len(raw),
        record_count=record_count,
    )


def write_m3_artifact(
    tmp_path: Path,
    m1_root: Path,
    m1_manifest: StructuralCardIndexManifestV1,
    records: list,
) -> tuple[Path, list[CardAnalysisRecordV1]]:
    root = tmp_path / "m3"
    records_dir = root / "records"
    trace_dir = root / "trace"
    records_dir.mkdir(parents=True)
    trace_dir.mkdir(parents=True)
    lock_digest = source_lock_digest()
    cards = [m3_card(record, lock_digest) for record in records]
    record_raw = b"".join(
        canonical_json_bytes(card.to_wire()) + b"\n" for card in cards
    )
    (records_dir / "a.jsonl").write_bytes(record_raw)
    trace_raw = canonical_json_bytes(trace_event().to_wire()) + b"\n"
    (trace_dir / "a.jsonl").write_bytes(trace_raw)
    for shard in SHARD_NAMES:
        if shard != "a":
            (records_dir / f"{shard}.jsonl").write_bytes(b"")
            (trace_dir / f"{shard}.jsonl").write_bytes(b"")
    record_shards = tuple(
        descriptor_for(
            records_dir / f"{shard}.jsonl",
            f"records/{shard}.jsonl",
            len(cards) if shard == "a" else 0,
        )
        for shard in SHARD_NAMES
    )
    trace_shards = tuple(
        descriptor_for(
            trace_dir / f"{shard}.jsonl",
            f"trace/{shard}.jsonl",
            1 if shard == "a" else 0,
        )
        for shard in SHARD_NAMES
    )
    manifest = AnalysisManifestV1(
        analysis_schema="census.card-analysis.v1",
        source_lock_digest=lock_digest,
        structural_record_schema="census.structural-card.v1",
        structural_index_manifest_sha256=hashlib.sha256(
            (m1_root / "structural-index-manifest.json").read_bytes()
        ).hexdigest(),
        structural_index_aggregate_digest=m1_manifest.aggregate_digest,
        m2_requirement_schema="census.semantic-requirement.v1",
        m2_bundle_schema="census.semantic-requirement-bundle.v1",
        producer_registry_digest="d" * 64,
        pattern_registry_digest="e" * 64,
        build_profile="census.m3-reference.v1",
        record_count=len(cards),
        record_identity_set_digest=record_identity_set_digest(
            [card_source_key(card.source) for card in cards]
        ),
        record_shards=record_shards,
        trace_shards=trace_shards,
    )
    (root / "analysis-manifest.json").write_bytes(
        canonical_json_bytes(manifest.to_wire())
    )
    return root, cards


def test_validate_analysis_closure_reads_m1_and_m3_authority_independently(
    tmp_path: Path,
) -> None:
    m1_root, records, m1_manifest = write_m1_authority(tmp_path)
    m3_root, _ = write_m3_artifact(tmp_path, m1_root, m1_manifest, records)
    record_result, trace_result = validate_analysis_closure(
        m1_root,
        m3_root,
        SOURCE_LOCK_PATH,
    )
    assert len(record_result.values) == 1
    assert len(trace_result.values) == 1


def test_no_requirements_record_requires_applied_authority_trace(
    tmp_path: Path,
) -> None:
    m1_root, records, m1_manifest = write_m1_authority(tmp_path)
    m3_root, _ = write_m3_artifact(tmp_path, m1_root, m1_manifest, records)

    record_path = m3_root / "records" / "a.jsonl"
    record_document = json.loads(record_path.read_bytes())
    record_document["outcome"] = "NO_REQUIREMENTS_APPLICABLE"
    record_document["no_requirements_basis"] = NegativeReviewAuthorityRefV1(
        authority_id="fixture-negative-authority",
        authority_version="1",
        record_id="nra_" + "a" * 64,
        record_sha256="b" * 64,
        scope_digest="c" * 64,
    ).to_wire()
    record_path.write_bytes(canonical_json_bytes(record_document) + b"\n")

    manifest_path = m3_root / "analysis-manifest.json"
    manifest_document = json.loads(manifest_path.read_bytes())
    descriptor = manifest_document["record_shards"][SHARD_NAMES.index("a")]
    descriptor["sha256"] = hashlib.sha256(record_path.read_bytes()).hexdigest()
    descriptor["byte_length"] = record_path.stat().st_size
    manifest_path.write_bytes(canonical_json_bytes(manifest_document))

    with pytest.raises(AnalysisClosureError, match="missing negative authority trace"):
        validate_analysis_closure(m1_root, m3_root, SOURCE_LOCK_PATH)


def test_record_source_lock_digest_mismatch_fails_closed(tmp_path: Path) -> None:
    m1_root, records, m1_manifest = write_m1_authority(tmp_path)
    m3_root, _ = write_m3_artifact(tmp_path, m1_root, m1_manifest, records)

    record_path = m3_root / "records" / "a.jsonl"
    record_document = json.loads(record_path.read_bytes())
    record_document["source"]["source_lock_digest"] = "f" * 64
    record_path.write_bytes(canonical_json_bytes(record_document) + b"\n")

    manifest_path = m3_root / "analysis-manifest.json"
    manifest_document = json.loads(manifest_path.read_bytes())
    record_descriptor = manifest_document["record_shards"][10]
    record_descriptor["sha256"] = hashlib.sha256(record_path.read_bytes()).hexdigest()
    record_descriptor["byte_length"] = record_path.stat().st_size
    manifest_path.write_bytes(canonical_json_bytes(manifest_document))

    with pytest.raises(AnalysisClosureError, match="record source lock"):
        validate_analysis_closure(m1_root, m3_root, SOURCE_LOCK_PATH)


@pytest.mark.parametrize(
    "field, value, message",
    [
        ("source_lock_digest", "f" * 64, "source lock"),
        ("structural_index_manifest_sha256", "f" * 64, "manifest"),
        ("structural_index_aggregate_digest", "f" * 64, "aggregate"),
        ("record_count", 99, "record count"),
        ("record_identity_set_digest", "f" * 64, "identity"),
        ("record_shards", None, "record shard"),
        ("trace_shards", None, "trace shard"),
    ],
)
def test_manifest_authority_mutations_fail_closed(
    tmp_path: Path,
    field: str,
    value: object,
    message: str,
) -> None:
    m1_root, records, m1_manifest = write_m1_authority(tmp_path)
    m3_root, _ = write_m3_artifact(tmp_path, m1_root, m1_manifest, records)
    path = m3_root / "analysis-manifest.json"
    document = json.loads(path.read_bytes())
    if value is None:
        document[field] = copy.deepcopy(document[field])
        document[field][0]["sha256"] = "f" * 64
    else:
        document[field] = value
    path.write_bytes(canonical_json_bytes(document))
    with pytest.raises(AnalysisClosureError, match=message):
        validate_analysis_closure(m1_root, m3_root, SOURCE_LOCK_PATH)


def test_wrong_structural_manifest_bytes_fail_closed(tmp_path: Path) -> None:
    m1_root, records, m1_manifest = write_m1_authority(tmp_path)
    m3_root, _ = write_m3_artifact(tmp_path, m1_root, m1_manifest, records)
    path = m1_root / "structural-index-manifest.json"
    document = json.loads(path.read_bytes())
    document["aggregate_digest"] = "f" * 64
    path.write_bytes(canonical_json_bytes(document))
    with pytest.raises(AnalysisClosureError, match="structural"):
        validate_analysis_closure(m1_root, m3_root, SOURCE_LOCK_PATH)


@pytest.mark.parametrize(
    "mutation, message",
    [
        ("noncanonical", "noncanonical"),
        ("wrong_shard", "wrong shard"),
        ("missing_lf", "final LF"),
        ("duplicate", "duplicate"),
    ],
)
def test_record_jsonl_adversarial_mutations_fail_closed(
    tmp_path: Path,
    mutation: str,
    message: str,
) -> None:
    m1_root, records, m1_manifest = write_m1_authority(tmp_path)
    m3_root, _ = write_m3_artifact(tmp_path, m1_root, m1_manifest, records)
    path = m3_root / "records" / "a.jsonl"
    raw = path.read_bytes()
    if mutation == "noncanonical":
        path.write_bytes(raw.replace(b"}\n", b"} \n", 1))
    elif mutation == "wrong_shard":
        path.write_bytes(b"")
        (m3_root / "records" / "b.jsonl").write_bytes(raw)
    elif mutation == "missing_lf":
        path.write_bytes(raw[:-1])
    else:
        path.write_bytes(raw + raw)
    with pytest.raises(AnalysisClosureError, match=message):
        validate_analysis_closure(m1_root, m3_root, SOURCE_LOCK_PATH)


def test_trace_unknown_source_fails_closed(tmp_path: Path) -> None:
    m1_root, records, m1_manifest = write_m1_authority(tmp_path)
    m3_root, _ = write_m3_artifact(tmp_path, m1_root, m1_manifest, records)
    path = m3_root / "trace" / "a.jsonl"
    event = trace_event().to_wire()
    event["card_source_key"][1] = "abcdefab-abcd-4abc-8abc-abcdefabcdea"
    path.write_bytes(canonical_json_bytes(event) + b"\n")
    with pytest.raises(AnalysisClosureError, match="unknown source"):
        validate_analysis_closure(m1_root, m3_root, SOURCE_LOCK_PATH)
