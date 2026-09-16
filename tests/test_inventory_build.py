from __future__ import annotations

import json
from dataclasses import replace

import pytest


def test_inventory_input_requires_all_explicit_parent_paths(tmp_path) -> None:
    from manafold_census.inventory.input import InventoryInputsV1, load_inventory_inputs

    inputs = InventoryInputsV1(
        source_lock_path=tmp_path / "source-lock.json",
        structural_output_directory=tmp_path / "m1",
        analysis_output_directory=tmp_path / "m3",
        m4_output_directory=tmp_path / "m4",
        parent_census_release_id=(
            "censusrel_55ff3102f75a64a0a2e1277810e709847803d085c6623ceeec14b7fe8f969e9f"
        ),
        expected_selected_count=None,
    )

    with pytest.raises((FileNotFoundError, ValueError)):
        load_inventory_inputs(inputs)


def test_inventory_models_do_not_construct_requirements_or_capabilities() -> None:
    from inventory_fixtures import records

    from manafold_census.inventory.grouping import group_surfaces
    from manafold_census.inventory.projection import project_surfaces

    groups = group_surfaces(project_surfaces(records()))

    assert groups
    assert not any(type(item).__name__.endswith("RequirementV1") for item in groups)
    assert not any(
        type(item).__name__.endswith("CapabilityDefinitionV1") for item in groups
    )


def _loaded_inputs():
    from inventory_fixtures import records

    from manafold_census.inventory.input import LoadedInventoryInputsV1

    selected = records()
    return LoadedInventoryInputsV1(
        source_lock_digest="a" * 64,
        source_lock_file_sha256="b" * 64,
        m1_manifest_sha256="c" * 64,
        m1_structural_aggregate_digest="d" * 64,
        m3_manifest_sha256="e" * 64,
        parent_m4_manifest_sha256="f" * 64,
        parent_census_release_id=(
            "censusrel_55ff3102f75a64a0a2e1277810e709847803d085c6623ceeec14b7fe8f969e9f"
        ),
        m1_record_count=len(selected),
        m3_record_count=len(selected),
        selected_records=selected,
        selected_oracle_ids=tuple(item.oracle_id for item in selected),
    )


def test_build_publishes_a_valid_non_authoritative_inventory(tmp_path) -> None:
    from manafold_census.inventory.build import build_inventory_from_loaded_inputs
    from manafold_census.inventory.validate import validate_inventory

    result = build_inventory_from_loaded_inputs(
        _loaded_inputs(),
        tmp_path / "inventory",
    )

    assert result.output_directory.is_dir()
    assert result.manifest.selected_identity_count == 5
    assert result.report.opportunity_count == len(result.opportunities)
    validated = validate_inventory(result.output_directory, expected_selected_count=5)
    assert validated.output_tree_digest == result.output_tree_digest
    assert all(item.authority_scope == "NON_AUTHORITATIVE" for item in validated.groups)


def test_inventory_validation_rejects_tampered_surface_identity(tmp_path) -> None:
    from manafold_census.canonical import canonical_json_bytes
    from manafold_census.inventory.build import build_inventory_from_loaded_inputs
    from manafold_census.inventory.validate import (
        InventoryValidationError,
        validate_inventory,
    )

    output = build_inventory_from_loaded_inputs(
        _loaded_inputs(),
        tmp_path / "inventory",
    ).output_directory
    path = output / "surfaces.jsonl"
    first = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    first["raw_text"] = "tampered\ntext"
    path.write_bytes(
        canonical_json_bytes(first)
        + b"\n"
        + b"\n".join(
            line.encode("utf-8")
            for line in path.read_text(encoding="utf-8").splitlines()[1:]
        )
        + b"\n"
    )

    with pytest.raises(InventoryValidationError, match="surface identity"):
        validate_inventory(output)


def test_population_selector_excludes_non_unresolved_outcomes() -> None:
    from analysis_fixtures import bundle
    from inventory_fixtures import structural_card

    from manafold_census.analysis.model import AnalysisOutcomeV1, CardAnalysisRecordV1
    from manafold_census.inventory.input import select_unresolved_records
    from manafold_census.semantic.evidence import SourceRecordRefV1
    from manafold_census.structural.model import StructuralCardRecordV1

    unresolved = structural_card(
        20,
        name="Unresolved",
        oracle_text="Unknown",
    )
    produced = structural_card(
        21,
        name="Produced",
        oracle_text="Draw",
    )

    def source_for(record: StructuralCardRecordV1) -> SourceRecordRefV1:
        return SourceRecordRefV1(
            record_schema=StructuralCardRecordV1.SCHEMA,
            source_lock_digest="a" * 64,
            oracle_id=record.oracle_id,
            source_card_id=record.source_card_id,
            source_record_sha256=record.source_record_sha256,
        )

    unresolved_source = source_for(unresolved)
    produced_source = source_for(produced)
    unresolved_analysis = CardAnalysisRecordV1(
        source=unresolved_source,
        outcome=AnalysisOutcomeV1.UNRESOLVED_ANALYSIS,
        bundle=None,
        no_requirements_basis=None,
    )
    produced_analysis = CardAnalysisRecordV1(
        source=produced_source,
        outcome=AnalysisOutcomeV1.REQUIREMENTS_PRODUCED,
        bundle=bundle(produced_source),
        no_requirements_basis=None,
    )

    selected = select_unresolved_records(
        (produced, unresolved),
        (produced_analysis, unresolved_analysis),
        expected_count=1,
    )

    assert selected == (unresolved,)


def test_build_rejects_existing_output_and_extra_artifact(tmp_path) -> None:
    from manafold_census.inventory.build import build_inventory_from_loaded_inputs
    from manafold_census.inventory.validate import (
        InventoryValidationError,
        validate_inventory,
    )

    output = tmp_path / "inventory"
    build_inventory_from_loaded_inputs(_loaded_inputs(), output)
    with pytest.raises(ValueError, match="must not already exist"):
        build_inventory_from_loaded_inputs(_loaded_inputs(), output)
    (output / "unexpected.json").write_text("{}", encoding="utf-8")
    with pytest.raises(InventoryValidationError, match="file set"):
        validate_inventory(output)


def test_input_bound_validator_rejects_self_consistent_source_projection_drift(
    tmp_path,
) -> None:
    from manafold_census.inventory.build import build_inventory_from_loaded_inputs
    from manafold_census.inventory.validate import (
        InventoryValidationError,
        validate_inventory_against_inputs,
    )

    original = _loaded_inputs()
    altered_records = tuple(
        replace(
            record,
            oracle_text="Altered\nsurface" if index == 0 else record.oracle_text,
        )
        for index, record in enumerate(original.selected_records)
    )
    altered = replace(original, selected_records=altered_records)
    output = build_inventory_from_loaded_inputs(
        altered,
        tmp_path / "inventory",
    ).output_directory

    with pytest.raises(
        InventoryValidationError,
        match="source surface projection",
    ):
        validate_inventory_against_inputs(output, original)
