from __future__ import annotations

from tests.inventory_fixtures import records


def test_inventory_identity_and_serialization_are_traversal_order_independent() -> None:
    from manafold_census.inventory.grouping import group_surfaces
    from manafold_census.inventory.projection import project_surfaces

    first = group_surfaces(project_surfaces(records()))
    second = group_surfaces(project_surfaces(tuple(reversed(records()))))

    assert [item.to_wire() for item in first] == [item.to_wire() for item in second]


def test_inventory_directory_digest_is_path_independent(tmp_path) -> None:
    from manafold_census.inventory.build import directory_digest

    left = tmp_path / "left"
    right = tmp_path / "right"
    left.mkdir()
    right.mkdir()
    (left / "value.json").write_bytes(b'{"value":1}')
    (right / "value.json").write_bytes(b'{"value":1}')

    assert directory_digest(left) == directory_digest(right)


def test_inventory_reproduction_writes_path_free_evidence(
    tmp_path,
    monkeypatch,
) -> None:
    from manafold_census.inventory import reproduction
    from manafold_census.inventory.input import InventoryInputsV1
    from tests.test_inventory_build import _loaded_inputs

    monkeypatch.setattr(
        reproduction,
        "load_inventory_inputs",
        lambda _inputs: _loaded_inputs(),
    )
    inputs = InventoryInputsV1(
        source_lock_path=tmp_path / "source-lock.json",
        structural_output_directory=tmp_path / "m1",
        analysis_output_directory=tmp_path / "m3",
        m4_output_directory=tmp_path / "m4",
        parent_census_release_id=(
            "censusrel_55ff3102f75a64a0a2e1277810e709847803d085c6623ceeec14b7fe8f969e9f"
        ),
        expected_selected_count=5,
    )

    result = reproduction.reproduce_inventory(
        inputs,
        tmp_path / "inventory",
        tmp_path / "evidence.json",
        tmp_path / "evidence.md",
    )

    assert result.fileset_parity is True
    assert result.byte_parity is True
    evidence = (tmp_path / "evidence.json").read_text(encoding="utf-8")
    assert str(tmp_path) not in evidence
    assert '"offline_regeneration":true' in evidence
