from __future__ import annotations

import copy

import pytest
from analysis_fixtures import source_ref

from manafold_census.analysis.manifest import (
    ANALYSIS_INDEX_DIGEST_DOMAIN,
    TRACE_INDEX_DIGEST_DOMAIN,
    AnalysisManifestV1,
    AnalysisShardDescriptorV1,
    analysis_shard_for,
    index_digest_for,
    merge_partitioned_records,
    partition_records,
    record_identity_set_digest,
)
from manafold_census.analysis.model import (
    AnalysisOutcomeV1,
    CardAnalysisRecordV1,
    card_source_key,
)


def card_record(index: int) -> CardAnalysisRecordV1:
    suffix = format(index, "x")
    source = source_ref(
        oracle_id=f"abcdefab-abcd-4abc-8abc-abcdefabcde{suffix}",
        source_card_id=f"abcdefab-abcd-4abc-8abc-abcdefabcdf{suffix}",
        source_record_sha256=(str(index) * 64)[:64],
    )
    return CardAnalysisRecordV1(
        source=source,
        outcome=AnalysisOutcomeV1.UNRESOLVED_ANALYSIS,
        bundle=None,
        no_requirements_basis=None,
    )


def shard_descriptors(prefix: str) -> tuple[AnalysisShardDescriptorV1, ...]:
    return tuple(
        AnalysisShardDescriptorV1(
            relative_path=f"{prefix}/{shard}.jsonl",
            sha256="a" * 64,
            byte_length=0,
            record_count=0,
        )
        for shard in "0123456789abcdef"
    )


def manifest_for_fixture() -> AnalysisManifestV1:
    record = card_record(1)
    records = list(shard_descriptors("records"))
    records[1] = AnalysisShardDescriptorV1(
        relative_path="records/1.jsonl",
        sha256="b" * 64,
        byte_length=512,
        record_count=1,
    )
    trace = list(shard_descriptors("trace"))
    trace[1] = AnalysisShardDescriptorV1(
        relative_path="trace/1.jsonl",
        sha256="c" * 64,
        byte_length=256,
        record_count=1,
    )
    return AnalysisManifestV1(
        analysis_schema="census.card-analysis.v1",
        source_lock_digest="a" * 64,
        structural_record_schema="census.structural-card.v1",
        structural_index_manifest_sha256="b" * 64,
        structural_index_aggregate_digest="c" * 64,
        m2_requirement_schema="census.semantic-requirement.v1",
        m2_bundle_schema="census.semantic-requirement-bundle.v1",
        producer_registry_digest="d" * 64,
        pattern_registry_digest="e" * 64,
        build_profile="census.m3-reference.v1",
        record_count=1,
        record_identity_set_digest=record_identity_set_digest(
            [card_source_key(record.source)]
        ),
        record_shards=tuple(records),
        trace_shards=tuple(trace),
        record_index_digest=index_digest_for(
            tuple(records), ANALYSIS_INDEX_DIGEST_DOMAIN
        ),
        trace_index_digest=index_digest_for(tuple(trace), TRACE_INDEX_DIGEST_DOMAIN),
    )


def test_oracle_id_first_hex_selects_the_existing_m1_shard() -> None:
    assert analysis_shard_for("0" + "1" * 31) == "0"
    assert analysis_shard_for("f" + "1" * 31) == "f"


def test_manifest_contains_trace_descriptors_but_no_report_digest() -> None:
    wire = manifest_for_fixture().to_wire()
    assert "trace_shards" in wire
    assert "derived_report_index_digest" not in wire
    assert "report_index_digest" not in wire


def test_manifest_round_trip_and_digest_are_deterministic() -> None:
    first = manifest_for_fixture()
    second = AnalysisManifestV1.from_wire(copy.deepcopy(first.to_wire()))
    assert second == first
    assert second.digest() == first.digest()


def test_identity_set_digest_is_order_independent() -> None:
    first = card_source_key(card_record(1).source)
    second = card_source_key(card_record(2).source)
    assert record_identity_set_digest([first, second]) == record_identity_set_digest(
        [second, first]
    )


def test_partition_merge_parity_is_not_a_worker_backend() -> None:
    records = [card_record(1), card_record(2)]
    reference = merge_partitioned_records(partition_records(records, 1))
    for count in (2, 8, 16):
        assert merge_partitioned_records(partition_records(records, count)) == reference


def test_manifest_rejects_report_identity_fields_and_bad_shard_set() -> None:
    wire = manifest_for_fixture().to_wire()
    wire["report_index_digest"] = "f" * 64
    with pytest.raises((TypeError, ValueError), match="unexpected"):
        AnalysisManifestV1.from_wire(wire)

    missing = manifest_for_fixture().to_wire()
    missing["record_shards"] = missing["record_shards"][:-1]
    with pytest.raises((TypeError, ValueError), match="16|shard"):
        AnalysisManifestV1.from_wire(missing)
