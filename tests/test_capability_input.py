from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from capability_m3_fixtures import (
    SOURCE_LOCK_DIGEST,
    no_requirements_applicable_record,
    record_with_other_requirement,
    record_with_proposed_requirement,
    record_with_wrong_source_lock,
    trace_for_requirement_outside_bundle,
    unresolved_record_with_requirement,
    unresolved_record_without_bundle,
    write_synthetic_m3,
)

from manafold_census.analysis.validate import ShardReadResultV1
from manafold_census.canonical import canonical_json_bytes
from manafold_census.capability import input as capability_input
from manafold_census.capability.identity import requirement_set_digest_for
from manafold_census.capability.input import (
    load_m3_requirement_corpus,
)
from manafold_census.digest import sha256_bytes


def _rewrite_manifest(m3_input, mutate, *, canonical: bool = True):
    path = m3_input.analysis_output_directory / "analysis-manifest.json"
    document = json.loads(path.read_bytes())
    mutate(document)
    raw = (
        canonical_json_bytes(document)
        if canonical
        else b" " + canonical_json_bytes(document)
    )
    path.write_bytes(raw)
    return replace(m3_input, expected_analysis_manifest_sha256=sha256_bytes(raw))


def test_input_collects_only_requirements_in_nonempty_bundles(tmp_path: Path) -> None:
    m3_input = write_synthetic_m3(
        tmp_path / "m3",
        records=(
            record_with_proposed_requirement(),
            unresolved_record_without_bundle(),
            no_requirements_applicable_record(),
        ),
    )

    loaded = load_m3_requirement_corpus(m3_input)

    assert len(loaded.requirements) == 1
    assert loaded.requirements_produced_card_count == 1
    assert loaded.unresolved_analysis_count == 1
    assert loaded.no_requirements_applicable_count == 1
    assert loaded.m3_record_count == 3


def test_unresolved_record_with_bundle_contributes_its_requirement(
    tmp_path: Path,
) -> None:
    loaded = load_m3_requirement_corpus(
        write_synthetic_m3(
            tmp_path / "m3",
            records=(unresolved_record_with_requirement(),),
        )
    )

    assert len(loaded.requirements) == 1
    assert loaded.unresolved_analysis_count == 1


def test_changed_m3_manifest_sha_fails_before_requirement_mapping(
    tmp_path: Path,
) -> None:
    m3_input = write_synthetic_m3(
        tmp_path / "m3",
        records=(record_with_proposed_requirement(),),
    )

    with pytest.raises(ValueError, match="M3 manifest SHA"):
        load_m3_requirement_corpus(
            replace(m3_input, expected_analysis_manifest_sha256="f" * 64)
        )


def test_requirement_set_digest_is_order_independent(tmp_path: Path) -> None:
    first_input = write_synthetic_m3(
        tmp_path / "first",
        records=(record_with_proposed_requirement(), record_with_other_requirement()),
    )
    second_input = write_synthetic_m3(
        tmp_path / "second",
        records=(record_with_other_requirement(), record_with_proposed_requirement()),
    )

    first = load_m3_requirement_corpus(first_input)
    second = load_m3_requirement_corpus(second_input)

    assert first.requirement_set_digest == second.requirement_set_digest
    assert first.requirement_set_digest == requirement_set_digest_for(
        first.m3_analysis_manifest_sha256, first.requirements
    )
    assert requirement_set_digest_for(
        "a" * 64, first.requirements
    ) != requirement_set_digest_for("b" * 64, first.requirements)


def test_noncanonical_m3_manifest_fails_closed(tmp_path: Path) -> None:
    m3_input = write_synthetic_m3(
        tmp_path / "m3",
        records=(record_with_proposed_requirement(),),
    )
    noncanonical = _rewrite_manifest(m3_input, lambda document: None, canonical=False)

    with pytest.raises(ValueError, match="canonical"):
        load_m3_requirement_corpus(noncanonical)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("analysis_schema", "census.invalid-analysis.v1", "analysis_schema"),
        ("m2_requirement_schema", "census.invalid-requirement.v1", "m2"),
        ("m2_bundle_schema", "census.invalid-bundle.v1", "m2"),
    ],
)
def test_m3_manifest_schema_bindings_fail_closed(
    tmp_path: Path,
    field: str,
    value: str,
    message: str,
) -> None:
    m3_input = write_synthetic_m3(
        tmp_path / field,
        records=(record_with_proposed_requirement(),),
    )
    mutated = _rewrite_manifest(
        m3_input,
        lambda document: document.__setitem__(field, value),
    )

    with pytest.raises(ValueError, match=message):
        load_m3_requirement_corpus(mutated)


def test_m3_closure_rejects_requirement_source_not_bound_to_source_lock(
    tmp_path: Path,
) -> None:
    m3_input = write_synthetic_m3(
        tmp_path / "m3",
        records=(record_with_wrong_source_lock(),),
    )

    with pytest.raises(ValueError, match="source lock"):
        load_m3_requirement_corpus(m3_input)


def test_requirement_source_must_be_validated_by_selected_m3_input(
    tmp_path: Path,
) -> None:
    first = write_synthetic_m3(
        tmp_path / "first",
        records=(record_with_proposed_requirement(0),),
    )
    other = write_synthetic_m3(
        tmp_path / "other",
        records=(record_with_other_requirement(1),),
    )

    with pytest.raises(ValueError, match="identity set mismatch"):
        load_m3_requirement_corpus(
            replace(
                first, structural_output_directory=other.structural_output_directory
            )
        )


def test_requirement_outside_persisted_bundle_is_not_collected(tmp_path: Path) -> None:
    outside = record_with_proposed_requirement().bundle
    assert outside is not None
    unresolved = unresolved_record_without_bundle()
    m3_input = write_synthetic_m3(
        tmp_path / "m3",
        records=(unresolved,),
        extra_traces=(
            trace_for_requirement_outside_bundle(
                unresolved,
                outside.requirements[0].requirement_id,
            ),
        ),
    )

    loaded = load_m3_requirement_corpus(m3_input)

    assert loaded.requirements == ()


def test_duplicate_requirement_id_with_different_wire_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = record_with_proposed_requirement(0)
    second = record_with_proposed_requirement(1)
    assert first.bundle is not None
    assert second.bundle is not None
    first_requirement = first.bundle.requirements[0]
    second_requirement = second.bundle.requirements[0]
    object.__setattr__(
        second_requirement, "requirement_id", first_requirement.requirement_id
    )
    fake_result = ShardReadResultV1(
        descriptors=(),
        values=(first, second),
    )
    monkeypatch.setattr(
        capability_input,
        "validate_analysis_closure",
        lambda *_args: (fake_result, ShardReadResultV1((), ())),
    )
    m3_input = write_synthetic_m3(
        tmp_path / "m3",
        records=(record_with_proposed_requirement(),),
    )

    with pytest.raises(ValueError, match="duplicate Requirement ID"):
        load_m3_requirement_corpus(m3_input)


def test_no_requirements_applicable_and_unresolved_without_bundle_are_not_requirements(
    tmp_path: Path,
) -> None:
    loaded = load_m3_requirement_corpus(
        write_synthetic_m3(
            tmp_path / "m3",
            records=(
                no_requirements_applicable_record(),
                unresolved_record_without_bundle(),
            ),
        )
    )

    assert loaded.requirements == ()
    assert loaded.no_requirements_applicable_count == 1
    assert loaded.unresolved_analysis_count == 1
    assert SOURCE_LOCK_DIGEST
