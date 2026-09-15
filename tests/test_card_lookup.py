from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from analysis_fixtures import structural_record
from test_census_bundle import _build_bundle

from manafold_census.canonical import canonical_json_bytes
from manafold_census.capability.identity import capability_claim_digest_for
from manafold_census.capability.link_build import direct_link
from manafold_census.digest import sha256_bytes
from manafold_census.query.api import open_bundle
from manafold_census.query.cards import QueryNotFoundV1, RequirementSummaryV1
from manafold_census.query.details import (
    CapabilityDetailViewV1,
    MappedSubsetFrequencyV1,
    RequirementDetailViewV1,
)
from manafold_census.query.lookup import (
    CardNameResolutionStatusV1,
    card_name_lookup_key,
    resolve_card_name_from_index,
)
from manafold_census.reports.build import build_census_derived

ORACLE_ID = "abcdefab-abcd-4abc-8abc-abcdefabcdef"
UNKNOWN_ORACLE_ID = "00000000-0000-4000-8000-000000000000"


def _reader(tmp_path: Path):
    _package, bundle = _build_bundle(tmp_path / "fixture")
    derived = build_census_derived(bundle.output_dir, tmp_path / "derived")
    return open_bundle(derived.output_dir)


def test_lookup_key_collapses_lookup_whitespace_and_casefolds_without_normalizing() -> (
    None
):
    assert card_name_lookup_key("  Fixture\tCard  ") == "fixture card"
    assert card_name_lookup_key("Straße") == "strasse"
    assert card_name_lookup_key("A\u0308") != card_name_lookup_key("Ä")


def test_name_resolution_returns_resolved_unknown_and_ambiguous_values() -> None:
    first = structural_record(oracle_id=ORACLE_ID)
    second = replace(
        first,
        oracle_id="abcdefab-abcd-4abc-8abc-abcdefabcdea",
        source_card_id="abcdefab-abcd-4abc-8abc-abcdefabcdf0",
        source_record_sha256="c" * 64,
        name="Other Card",
    )
    index = {
        card_name_lookup_key(first.name): (first,),
        card_name_lookup_key(second.name): (second,),
    }

    resolved = resolve_card_name_from_index("  FIXTURE   CARD ", index)
    unknown = resolve_card_name_from_index("Fixture Car", index)
    ambiguous = resolve_card_name_from_index(
        "fixture card",
        {
            "fixture card": (first, replace(second, name="Fixture Card")),
        },
    )

    assert resolved.status is CardNameResolutionStatusV1.RESOLVED
    assert resolved.matches[0].oracle_id == ORACLE_ID
    assert unknown.status is CardNameResolutionStatusV1.UNKNOWN
    assert not unknown.matches
    assert ambiguous.status is CardNameResolutionStatusV1.AMBIGUOUS
    assert len(ambiguous.matches) == 2


def test_reader_reports_ambiguous_and_unknown_names_without_silent_selection(
    tmp_path: Path,
) -> None:
    reader = _reader(tmp_path)

    ambiguous = reader.resolve_card_name("  FIXTURE\tCARD ")
    unknown = reader.resolve_card_name("Fixture Car")
    by_name = reader.get_card_by_name("fixture card")

    assert ambiguous.status is CardNameResolutionStatusV1.AMBIGUOUS
    assert len(ambiguous.matches) == 5
    assert unknown.status is CardNameResolutionStatusV1.UNKNOWN
    assert isinstance(by_name, type(ambiguous))
    assert by_name.status is CardNameResolutionStatusV1.AMBIGUOUS


def test_open_bundle_rejects_cross_layer_name_index_mismatch(tmp_path: Path) -> None:
    _package, bundle = _build_bundle(tmp_path / "fixture")
    root = build_census_derived(bundle.output_dir, tmp_path / "derived").output_dir
    index_path = root / "indexes/cards-by-name.jsonl"
    rows = [json.loads(line) for line in index_path.read_bytes().splitlines()]
    rows[0]["name"] = "A Fixture Card"
    index_bytes = b"".join(canonical_json_bytes(row) + b"\n" for row in rows)
    index_path.write_bytes(index_bytes)
    manifest_path = root / "indexes/index-manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    descriptor = next(
        item
        for item in manifest["index_descriptors"]
        if item["relative_path"] == "indexes/cards-by-name.jsonl"
    )
    descriptor["sha256"] = sha256_bytes(index_bytes)
    descriptor["byte_length"] = len(index_bytes)
    manifest_path.write_bytes(canonical_json_bytes(manifest))

    with pytest.raises(ValueError, match="name index|cross-layer|source"):
        open_bundle(root)


def test_card_detail_exposes_semantic_view_and_capability_detail(
    tmp_path: Path,
) -> None:
    reader = _reader(tmp_path)

    detail = reader.get_card(ORACLE_ID)
    assert detail.structural_record.oracle_id == ORACLE_ID
    assert detail.semantic_view.semantic_state.value == "ESTABLISHED"
    assert len(detail.semantic_view.requirements) == 1
    assert len(detail.semantic_view.active_capability_mappings) == 1
    assert len(detail.requirement_details) == 1
    assert (
        detail.requirement_details[0].admissibility.decision.value
        == "ACCEPTED_FOR_CAPABILITY_MAPPING"
    )
    assert detail.requirement_details[0].mapping_decision.disposition.value == "MAPPED"
    assert len(detail.capability_details) == 1

    capability = detail.capability_details[0]
    assert capability.definition.display_name == "Draw cards"
    assert capability.definition.lifecycle.value == "ACTIVE"
    assert capability.definition_review is not None
    assert len(capability.links) == 5
    assert all(
        item.capability == capability.definition.capability_ref
        for item in capability.links
    )
    assert capability.to_wire()["links"] == [
        item.to_wire() for item in capability.links
    ]
    assert len(capability.linked_requirements) == 5
    assert capability.mapped_requirement_count == 5
    assert capability.mapped_subset_denominator == 5
    assert capability.mapped_subset_denominator_label == "MAPPED_REQUIREMENTS"


def test_capability_detail_keeps_an_empty_mapped_subset_structural(
    tmp_path: Path,
) -> None:
    package, _result = _build_bundle(tmp_path / "fixture")
    definition = package.definitions[0]
    definition_review = next(
        item for item in package.reviews if item.record_id == definition.review_ref
    )

    detail = CapabilityDetailViewV1(
        census_release_id="censusrel_" + "0" * 64,
        census_manifest_sha256="a" * 64,
        definition=definition,
        definition_review=definition_review,
        links=(),
        linked_requirements=(),
        mapped_cards=(),
        mapped_subset_frequency=MappedSubsetFrequencyV1(
            mapped_requirement_count=0,
            denominator=5,
            denominator_label="MAPPED_REQUIREMENTS",
        ),
    )

    assert detail.links == ()
    assert detail.mapped_cards == ()
    assert detail.mapped_requirement_count == 0
    assert detail.mapped_subset_denominator == 5
    assert detail.to_wire()["mapped_cards"] == []


def test_requirement_detail_accepts_multiple_links_in_query_canonical_order(
    tmp_path: Path,
) -> None:
    package, _result = _build_bundle(tmp_path / "fixture")
    requirement = package.corpus.requirements[0]
    first_link = package.links[0]
    base_definition = package.definitions[0]
    for version in range(2, 33):
        second_claim = replace(base_definition.claim, capability_version=version)
        second_definition = replace(
            base_definition,
            capability_version=version,
            claim=second_claim,
            claim_digest=capability_claim_digest_for(second_claim),
            review_ref=None,
        )
        candidate = direct_link(
            requirement=requirement,
            capability=second_definition,
            m3_manifest_sha256=package.corpus.m3_analysis_manifest_sha256,
            admissibility=package.admissibility[0],
            parameter_bindings=first_link.parameter_bindings,
        )
        candidate_links = tuple(
            sorted(
                (first_link, candidate),
                key=lambda item: (
                    item.relation.value,
                    item.capability.capability_family_id,
                    item.capability.capability_version,
                    item.capability.claim_digest,
                    item.link_id,
                ),
            )
        )
        if tuple(item.link_id for item in candidate_links) != tuple(
            sorted(item.link_id for item in candidate_links)
        ):
            second_link = candidate
            expected = candidate_links
            break
    else:
        raise AssertionError("could not construct distinct canonical link order")
    mapping_decision = replace(
        package.mapping_decisions[0],
        active_link_ids=(first_link.link_id, second_link.link_id),
    )

    detail = RequirementDetailViewV1(
        summary=RequirementSummaryV1.from_requirement(requirement),
        admissibility=package.admissibility[0],
        mapping_decision=mapping_decision,
        links=expected,
    )

    assert detail.links == expected


def test_capability_lookup_and_card_reverse_lookup_are_explicit(
    tmp_path: Path,
) -> None:
    reader = _reader(tmp_path)
    detail = reader.get_card(ORACLE_ID)
    capability_ref = detail.capability_details[0].definition.capability_ref

    capability = reader.get_capability(capability_ref)
    cards = reader.get_cards_for_capability(capability_ref)
    card_capabilities = reader.get_capabilities_for_card(ORACLE_ID)
    missing = reader.get_capability(replace(capability_ref, claim_digest="f" * 64))

    assert capability.definition.capability_ref == capability_ref
    assert len(cards) == 5
    assert len(card_capabilities) == 1
    assert isinstance(missing, QueryNotFoundV1)


def test_lookup_detail_calls_are_deterministic_and_read_only(tmp_path: Path) -> None:
    reader = _reader(tmp_path)
    before = reader.get_card(ORACLE_ID).to_wire()

    assert reader.get_card(ORACLE_ID).to_wire() == before
    assert reader.get_card_by_name("fixture card").to_wire() == (
        reader.get_card_by_name("fixture card").to_wire()
    )
