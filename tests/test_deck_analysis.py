from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from capability_m3_fixtures import (
    no_requirements_applicable_record,
    unresolved_record_with_requirement,
)
from test_census_bundle import _build_bundle

from manafold_census.canonical import canonical_json_bytes
from manafold_census.capability.mapping import (
    MappingDispositionV1,
    MappingReasonV1,
    mapping_decision,
)
from manafold_census.query.api import open_bundle
from manafold_census.query.cards import (
    QueryNotFoundV1,
    build_card_semantic_view,
    card_name_lookup_key,
)
from manafold_census.query.deck import (
    DeckAnalysisV1,
    DeckInputError,
    DeckInvalidReasonV1,
    DeckSectionV1,
    analyze_deck_bytes,
    analyze_deck_file,
)
from manafold_census.query.details import (
    CardIdentityV1,
    CardNameResolutionStatusV1,
    CardNameResolutionV1,
)
from manafold_census.reports.build import build_census_derived
from manafold_census.validation import validate_document

ORACLE_ID = "abcdefab-abcd-4abc-8abc-abcdefabcdef"


def _reader(tmp_path: Path):
    _package, bundle = _build_bundle(tmp_path / "fixture")
    derived = build_census_derived(bundle.output_dir, tmp_path / "derived")
    return open_bundle(derived.output_dir)


class _AliasReader:
    def __init__(self, reader, aliases=None, details=None) -> None:
        self._reader = reader
        if aliases is None:
            result = reader.get_card(ORACLE_ID)
            assert not isinstance(result, QueryNotFoundV1)
            aliases = {
                "fixture card": CardIdentityV1.from_record(result.structural_record)
            }
        self._aliases = aliases
        self._details = details or {}

    def metadata(self):
        return self._reader.metadata()

    def resolve_card_name(self, name: str):
        key = card_name_lookup_key(name)
        identity = self._aliases.get(key)
        if identity is not None:
            return CardNameResolutionV1(
                name,
                key,
                CardNameResolutionStatusV1.RESOLVED,
                (identity,),
            )
        return self._reader.resolve_card_name(name)

    def get_card(self, oracle_id: str):
        if oracle_id in self._details:
            return self._details[oracle_id]
        return self._reader.get_card(oracle_id)

    def trace_requirement(self, requirement_id: str):
        return self._reader.trace_requirement(requirement_id)

    def trace_mapping(self, link_id: str):
        return self._reader.trace_mapping(link_id)


def _state_reader(tmp_path: Path):
    package, bundle = _build_bundle(tmp_path / "fixture")
    derived = build_census_derived(bundle.output_dir, tmp_path / "derived")
    reader = open_bundle(derived.output_dir)
    metadata = reader.metadata()
    base_established = reader.get_card(ORACLE_ID)
    base_partial = reader.get_card("abcdefab-abcd-4abc-8abc-abcdefabcde1")
    base_unresolved = reader.get_card("abcdefab-abcd-4abc-8abc-abcdefabcde2")
    base_negative = reader.get_card("abcdefab-abcd-4abc-8abc-abcdefabcde3")
    assert not isinstance(base_established, QueryNotFoundV1)
    assert not isinstance(base_partial, QueryNotFoundV1)
    assert not isinstance(base_unresolved, QueryNotFoundV1)
    assert not isinstance(base_negative, QueryNotFoundV1)

    partial_requirement = reader._bundle.requirements_by_id[
        base_partial.requirement_details[0].requirement_id
    ]
    partial_decision = mapping_decision(
        partial_requirement,
        MappingDispositionV1.UNMAPPED,
        MappingReasonV1.NO_REVIEWED_CAPABILITY,
        m3_analysis_manifest_sha256=metadata.m3_analysis_manifest_sha256,
    )
    partial_semantic = build_card_semantic_view(
        structural_record=base_partial.structural_record,
        analysis_record=reader.get_analysis_record(
            base_partial.structural_record.oracle_id
        ),
        requirements=(partial_requirement,),
        admissibility_by_requirement=reader._bundle.admissibility_by_requirement,
        decisions_by_requirement={partial_requirement.requirement_id: partial_decision},
        links_by_id=reader._bundle.links_by_id,
        definitions_by_ref=reader._bundle.definitions_by_ref,
        census_release_id=metadata.census_release_id,
        census_manifest_sha256=metadata.census_manifest_sha256,
        m3_analysis_manifest_sha256=metadata.m3_analysis_manifest_sha256,
    )
    partial_detail = replace(
        base_partial,
        semantic_view=partial_semantic,
        requirement_details=(
            replace(
                base_partial.requirement_details[0],
                mapping_decision=partial_decision,
            ),
        ),
        capability_details=(),
    )
    unresolved_record = unresolved_record_with_requirement(2)
    unresolved_requirement = reader._bundle.requirements_by_id[
        base_unresolved.requirement_details[0].requirement_id
    ]
    unresolved_semantic = build_card_semantic_view(
        structural_record=base_unresolved.structural_record,
        analysis_record=unresolved_record,
        requirements=(unresolved_requirement,),
        admissibility_by_requirement=reader._bundle.admissibility_by_requirement,
        decisions_by_requirement=reader._bundle.decisions_by_requirement,
        links_by_id=reader._bundle.links_by_id,
        definitions_by_ref=reader._bundle.definitions_by_ref,
        census_release_id=metadata.census_release_id,
        census_manifest_sha256=metadata.census_manifest_sha256,
        m3_analysis_manifest_sha256=metadata.m3_analysis_manifest_sha256,
    )
    unresolved_detail = replace(
        base_unresolved,
        semantic_view=unresolved_semantic,
    )
    negative_record = no_requirements_applicable_record(3)
    negative_semantic = build_card_semantic_view(
        structural_record=base_negative.structural_record,
        analysis_record=negative_record,
        requirements=(),
        admissibility_by_requirement={},
        decisions_by_requirement={},
        links_by_id={},
        definitions_by_ref={},
        census_release_id=metadata.census_release_id,
        census_manifest_sha256=metadata.census_manifest_sha256,
        m3_analysis_manifest_sha256=metadata.m3_analysis_manifest_sha256,
    )
    negative_detail = replace(
        base_negative,
        semantic_view=negative_semantic,
        requirement_details=(),
        capability_details=(),
    )
    details = {
        base_established.structural_record.oracle_id: replace(
            base_established,
            structural_record=replace(
                base_established.structural_record,
                name="Established Card",
            ),
        ),
        partial_detail.structural_record.oracle_id: replace(
            partial_detail,
            structural_record=replace(
                partial_detail.structural_record,
                name="Partial Card",
            ),
        ),
        unresolved_detail.structural_record.oracle_id: replace(
            unresolved_detail,
            structural_record=replace(
                unresolved_detail.structural_record,
                name="Unresolved Card",
            ),
        ),
        negative_detail.structural_record.oracle_id: replace(
            negative_detail,
            structural_record=replace(
                negative_detail.structural_record,
                name="Negative Card",
            ),
        ),
    }
    aliases = {
        detail.structural_record.name.casefold(): CardIdentityV1.from_record(
            detail.structural_record
        )
        for detail in details.values()
    }
    return _AliasReader(reader, aliases=aliases, details=details)


def test_main_and_sideboard_are_separate(tmp_path: Path) -> None:
    result = analyze_deck_bytes(
        b"\xef\xbb\xbf[MAIN]\n2 Fixture Card\n[sideboard]\n1 fixture\tcard\n",
        _AliasReader(_reader(tmp_path)),
    )

    assert result.main.section is DeckSectionV1.MAIN
    assert result.sideboard.section is DeckSectionV1.SIDEBOARD
    assert result.main.declared_card_count == 2
    assert result.sideboard.declared_card_count == 1
    assert result.main.resolved_card_count == 2
    assert result.sideboard.resolved_card_count == 1
    assert result.main.unique_resolved_oracle_identity_count == 1
    assert result.sideboard.unique_resolved_oracle_identity_count == 1


def test_inline_hash_is_preserved_in_card_name(tmp_path: Path) -> None:
    result = analyze_deck_bytes(
        b"[main]\n1 Fixture Card # keep\n",
        _reader(tmp_path),
    )

    assert result.main.unknown_names[0].name == "Fixture Card # keep"
    assert result.main.unknown_names[0].lookup_key == "fixture card # keep"


def test_unknown_and_ambiguous_names_remain_visible(tmp_path: Path) -> None:
    result = analyze_deck_bytes(
        b"[main]\n1 Does Not Exist\n1 Fixture Card\n",
        _reader(tmp_path),
    )

    assert result.main.unknown_names[0].name == "Does Not Exist"
    assert result.main.unknown_names[0].lookup_key == "does not exist"
    assert result.main.ambiguous_names[0].name == "Fixture Card"
    assert len(result.main.ambiguous_names[0].matches) == 5
    assert result.main.resolved_card_count == 0


def test_invalid_lines_and_unknown_sections_are_recorded(tmp_path: Path) -> None:
    result = analyze_deck_bytes(
        b"[main]\n0 Fixture Card\n-1 Fixture Card\n[commander]\n",
        _reader(tmp_path),
    )

    assert len(result.invalid_lines) == 3
    assert [item.reason for item in result.invalid_lines] == [
        DeckInvalidReasonV1.INVALID_QUANTITY,
        DeckInvalidReasonV1.INVALID_QUANTITY,
        DeckInvalidReasonV1.UNKNOWN_SECTION,
    ]
    assert result.main.declared_card_count == 0


def test_entries_before_a_section_are_not_assigned_to_main(tmp_path: Path) -> None:
    result = analyze_deck_bytes(b"1 Fixture Card\n", _reader(tmp_path))

    assert len(result.invalid_lines) == 1
    assert result.invalid_lines[0].section is None
    assert result.invalid_lines[0].reason is DeckInvalidReasonV1.ENTRY_BEFORE_SECTION


def test_quantities_and_strict_utf8_are_fail_closed(tmp_path: Path) -> None:
    accepted = analyze_deck_bytes(
        b"[main]\n1000000 Fixture Card\n",
        _AliasReader(_reader(tmp_path / "accepted")),
    )
    assert accepted.main.declared_card_count == 1_000_000

    limited = analyze_deck_bytes(
        b"[main]\n1000001 Fixture Card\n",
        _AliasReader(_reader(tmp_path / "limited")),
    )
    assert limited.main.declared_card_count == 0
    assert len(limited.invalid_lines) == 1
    assert limited.main.unknown_names == ()
    assert limited.main.ambiguous_names == ()
    assert limited.main.invalid_line_count == 1

    with pytest.raises(DeckInputError, match="UTF-8"):
        analyze_deck_bytes(b"[main]\n1 \xff\n", _reader(tmp_path / "utf8"))


def test_stray_bom_is_recorded_instead_of_removed(tmp_path: Path) -> None:
    result = analyze_deck_bytes(
        b"[main]\n1 Fixture \xef\xbb\xbfCard\n",
        _reader(tmp_path),
    )

    assert result.main.declared_card_count == 0
    assert result.invalid_lines[0].reason is DeckInvalidReasonV1.BOM_NOT_AT_FILE_START


def test_deck_file_analysis_uses_exact_file_bytes(tmp_path: Path) -> None:
    path = tmp_path / "deck.txt"
    raw = b"[main]\n1 Fixture Card\n"
    path.write_bytes(raw)

    result = analyze_deck_file(path, _AliasReader(_reader(tmp_path / "bundle")))

    assert result.deck_input_sha256
    assert result.main.declared_card_count == 1
    assert result.deck_input_sha256 == __import__("hashlib").sha256(raw).hexdigest()


def test_resolved_duplicates_aggregate_only_within_each_section(
    tmp_path: Path,
) -> None:
    result = analyze_deck_bytes(
        b"[main]\n2 Fixture Card\n1 FIXTURE\tCARD\n[sideboard]\n3 fixture card\n",
        _AliasReader(_reader(tmp_path)),
    )

    assert result.main.resolved_cards[0].quantity == 3
    assert result.sideboard.resolved_cards[0].quantity == 3
    assert result.main.resolved_cards[0].identity.oracle_id == ORACLE_ID


def test_all_semantic_states_and_capability_counts_remain_explicit(
    tmp_path: Path,
) -> None:
    reader = _state_reader(tmp_path)
    result = analyze_deck_bytes(
        b"[main]\n1 Established Card\n2 Partial Card\n"
        b"3 Unresolved Card\n4 Negative Card\n",
        reader,
    )

    assert result.main.declared_card_count == 10
    assert result.main.resolved_card_count == 10
    assert result.main.unique_resolved_oracle_identity_count == 4
    assert len(result.main.established_cards) == 1
    assert len(result.main.partially_established_cards) == 1
    assert len(result.main.unresolved_cards) == 1
    assert len(result.main.explicit_negative_cards) == 1
    assert result.main.analysis_outcome_counts == {
        "REQUIREMENTS_PRODUCED": 2,
        "NO_REQUIREMENTS_APPLICABLE": 1,
        "UNRESOLVED_ANALYSIS": 1,
    }
    assert result.main.m2_review_status_denominator == 3
    assert result.main.m4_mapping_disposition_counts["MAPPED"] == 2
    assert result.main.m4_mapping_disposition_counts["UNMAPPED"] == 1
    assert result.main.capability_counts[0].display_name == "Draw cards"
    assert result.main.capability_counts[0].unique_mapped_oracle_identity_count == 2
    assert result.main.capability_counts[0].quantity_weighted_mapped_card_count == 4
    assert len(result.main.provenance_traces) == 4
    negative_trace = next(
        item
        for item in result.main.provenance_traces
        if item.card.name == "Negative Card"
    )
    assert not negative_trace.requirement_traces
    assert not negative_trace.mapping_traces


def test_section_limit_and_invalid_quantity_forms_are_visible(
    tmp_path: Path,
) -> None:
    overflow = analyze_deck_bytes(
        b"[main]\n600000 Fixture Card\n400001 Fixture Card\n",
        _AliasReader(_reader(tmp_path / "overflow")),
    )
    assert overflow.main.declared_card_count == 600000
    assert overflow.main.invalid_line_count == 1
    assert overflow.invalid_lines[0].reason is (
        DeckInvalidReasonV1.SECTION_CARD_LIMIT_EXCEEDED
    )

    invalid = analyze_deck_bytes(
        b"[main]\n01 Fixture Card\n+1 Fixture Card\n0 Fixture Card\n-1 Fixture Card\n",
        _AliasReader(_reader(tmp_path / "invalid")),
    )
    assert invalid.main.declared_card_count == 0
    assert len(invalid.invalid_lines) == 4
    assert all(
        item.reason is DeckInvalidReasonV1.INVALID_QUANTITY
        for item in invalid.invalid_lines
    )


def test_deck_wire_is_canonical_and_schema_valid(tmp_path: Path) -> None:
    result = analyze_deck_bytes(
        b"[main]\n1 Fixture Card\n1 Does Not Exist\n",
        _AliasReader(_reader(tmp_path)),
    )
    wire = result.to_wire()

    validate_document(wire, "deck-analysis.v1.schema.json")
    assert canonical_json_bytes(wire) == canonical_json_bytes(result.to_wire())

    changed = json.loads(json.dumps(wire))
    changed["main"]["analysis_outcome_denominator_label"] = "WRONG"
    with pytest.raises(ValueError):
        validate_document(changed, "deck-analysis.v1.schema.json")

    extra = json.loads(json.dumps(wire))
    extra["unexpected"] = True
    with pytest.raises(ValueError):
        validate_document(extra, "deck-analysis.v1.schema.json")


def test_repeated_analysis_does_not_mutate_reader(tmp_path: Path) -> None:
    reader = _AliasReader(_reader(tmp_path))
    raw = b"[main]\n2 Fixture Card\n"

    first = analyze_deck_bytes(raw, reader)
    second = analyze_deck_bytes(raw, reader)

    assert isinstance(first, DeckAnalysisV1)
    assert first.to_wire() == second.to_wire()
    with pytest.raises(TypeError):
        first.main.analysis_outcome_counts["REQUIREMENTS_PRODUCED"] = 99
    assert reader.resolve_card_name("fixture card").status is (
        CardNameResolutionStatusV1.RESOLVED
    )
