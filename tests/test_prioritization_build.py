from __future__ import annotations

import json
from dataclasses import replace


def test_build_publishes_a_valid_non_authoritative_prioritization(tmp_path) -> None:
    from prioritization_fixtures import default_loaded_inputs

    from manafold_census.prioritization.build import (
        build_prioritization_from_loaded_inputs,
    )
    from manafold_census.prioritization.validate import validate_prioritization

    result = build_prioritization_from_loaded_inputs(
        default_loaded_inputs(), tmp_path / "output"
    )
    assert result.output_directory.is_dir()
    assert result.manifest.input_opportunity_count == len(result.assessments)
    assert result.manifest.full_ranked_worklist_count == len(result.worklist)
    validated = validate_prioritization(result.output_directory)
    assert validated.output_tree_digest == result.output_tree_digest
    assert all(
        item.authority_scope == "NON_AUTHORITATIVE" for item in validated.assessments
    )


def test_manifest_bindings_reject_tampered_parent_identity(tmp_path) -> None:
    from prioritization_fixtures import default_loaded_inputs

    from manafold_census.canonical import canonical_json_bytes
    from manafold_census.prioritization.build import (
        build_prioritization_from_loaded_inputs,
    )
    from manafold_census.prioritization.validate import (
        PrioritizationValidationError,
        validate_prioritization,
    )

    output = build_prioritization_from_loaded_inputs(
        default_loaded_inputs(), tmp_path / "output"
    ).output_directory
    path = output / "manifest.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    document["input_opportunity_count"] = document["input_opportunity_count"] + 1
    path.write_bytes(canonical_json_bytes(document))
    try:
        validate_prioritization(output)
    except PrioritizationValidationError:
        return
    raise AssertionError("tampered manifest binding was accepted")


def test_input_bound_validator_rejects_source_drift(tmp_path) -> None:
    from inventory_fixtures import records
    from prioritization_fixtures import default_loaded_inputs

    from manafold_census.inventory.projection import project_surfaces
    from manafold_census.prioritization.build import (
        build_prioritization_from_loaded_inputs,
    )
    from manafold_census.prioritization.validate import (
        PrioritizationValidationError,
        validate_prioritization_against_inputs,
    )

    original = default_loaded_inputs()
    altered_records = tuple(
        replace(
            record,
            oracle_text="Altered\nsurface" if index == 0 else record.oracle_text,
        )
        for index, record in enumerate(records())
    )
    altered_surfaces = project_surfaces(altered_records)
    from manafold_census.inventory.grouping import (
        build_capability_opportunities,
        group_surfaces,
    )

    altered_groups = group_surfaces(altered_surfaces)
    altered_opportunities = build_capability_opportunities(altered_groups)
    altered = replace(
        original,
        surfaces=altered_surfaces,
        groups=altered_groups,
        opportunities=altered_opportunities,
        m6_02_opportunity_count=len(altered_opportunities),
    )
    output = build_prioritization_from_loaded_inputs(
        altered, tmp_path / "output"
    ).output_directory
    try:
        validate_prioritization_against_inputs(output, original)
    except PrioritizationValidationError:
        return
    raise AssertionError("source-drifted prioritization was accepted")


def test_large_null_empty_groups_stay_present_but_leave_the_packet(tmp_path) -> None:
    from prioritization_fixtures import loaded_inputs_for, noise_records, pipeline

    from manafold_census.prioritization._common import PlanningNoiseV1
    from manafold_census.prioritization.build import (
        build_prioritization_from_loaded_inputs,
    )

    selected = noise_records()
    surfaces, groups, opportunities = pipeline(selected)
    selected_ids = tuple(item.oracle_id for item in selected)
    loaded = loaded_inputs_for(surfaces, groups, opportunities, selected, selected_ids)
    result = build_prioritization_from_loaded_inputs(loaded, tmp_path / "output")
    noise = [
        item
        for item in result.assessments
        if item.planning_noise is not PlanningNoiseV1.NONE
    ]
    assert noise
    assert len(result.assessments) == len(opportunities)
    packet_ids = {item.opportunity_id for item in result.packet.entries}
    assert not (packet_ids & {item.opportunity_id for item in noise})


def test_output_files_are_canonical_with_verified_descriptors(tmp_path) -> None:
    import json

    from prioritization_fixtures import default_loaded_inputs

    from manafold_census.digest import measure_file
    from manafold_census.prioritization.build import (
        build_prioritization_from_loaded_inputs,
    )

    result = build_prioritization_from_loaded_inputs(
        default_loaded_inputs(), tmp_path / "output"
    )
    descriptors = {
        item.relative_path: item for item in result.manifest.file_descriptors
    }
    assert set(descriptors) == {
        "opportunity-assessments.jsonl",
        "mechanical-overlap-clusters.jsonl",
        "ranked-worklist.jsonl",
        "review-packet.json",
        "report.json",
    }
    for relative_path, descriptor in descriptors.items():
        measurement = measure_file(result.output_directory / relative_path)
        assert descriptor.sha256 == measurement.sha256
        assert descriptor.byte_length == measurement.byte_length
    packet = json.loads(
        (result.output_directory / "review-packet.json").read_text(encoding="utf-8")
    )
    assert packet["authority_scope"] == "NON_AUTHORITATIVE"


def test_output_bytes_contain_no_absolute_paths(tmp_path) -> None:
    from prioritization_fixtures import default_loaded_inputs

    from manafold_census.prioritization.build import (
        build_prioritization_from_loaded_inputs,
    )

    output = build_prioritization_from_loaded_inputs(
        default_loaded_inputs(), tmp_path / "output"
    ).output_directory
    needle = str(tmp_path)
    for path in output.rglob("*"):
        if path.is_file():
            content = path.read_bytes()
            assert needle.encode("utf-8") not in content


def test_two_builds_in_different_roots_keep_byte_parity(tmp_path) -> None:
    from prioritization_fixtures import default_loaded_inputs

    from manafold_census.prioritization.build import (
        build_prioritization_from_loaded_inputs,
        compare_directories,
    )

    loaded = default_loaded_inputs()
    first = build_prioritization_from_loaded_inputs(
        loaded, tmp_path / "root-a" / "output"
    )
    second = build_prioritization_from_loaded_inputs(
        loaded, tmp_path / "root-b" / "output"
    )
    fileset_parity, byte_parity = compare_directories(
        first.output_directory, second.output_directory
    )
    assert fileset_parity is True
    assert byte_parity is True
    assert first.output_tree_digest == second.output_tree_digest


def test_build_rejects_existing_output_and_extra_artifact(tmp_path) -> None:
    from prioritization_fixtures import default_loaded_inputs

    from manafold_census.prioritization.build import (
        build_prioritization_from_loaded_inputs,
    )
    from manafold_census.prioritization.validate import (
        PrioritizationValidationError,
        validate_prioritization,
    )

    output = tmp_path / "output"
    build_prioritization_from_loaded_inputs(default_loaded_inputs(), output)
    try:
        build_prioritization_from_loaded_inputs(default_loaded_inputs(), output)
    except ValueError:
        pass
    else:
        raise AssertionError("existing output was overwritten")
    (output / "unexpected.json").write_text("{}", encoding="utf-8")
    try:
        validate_prioritization(output)
    except PrioritizationValidationError:
        return
    raise AssertionError("extra artifact was accepted")


def test_tampered_ranking_packet_and_report_are_rejected(tmp_path) -> None:
    import json

    from prioritization_fixtures import default_loaded_inputs

    from manafold_census.canonical import canonical_json_bytes
    from manafold_census.prioritization.build import (
        build_prioritization_from_loaded_inputs,
    )
    from manafold_census.prioritization.validate import (
        PrioritizationValidationError,
        validate_prioritization,
    )

    def fresh(name: str):
        return build_prioritization_from_loaded_inputs(
            default_loaded_inputs(), tmp_path / name
        ).output_directory

    ranking_path = fresh("ranking") / "ranked-worklist.jsonl"
    ranking_body = [line for line in ranking_path.read_bytes().split(b"\n") if line]
    if len(ranking_body) >= 2:
        ranking_body[0], ranking_body[1] = ranking_body[1], ranking_body[0]
        ranking_path.write_bytes(b"\n".join(ranking_body) + b"\n")
        try:
            validate_prioritization(ranking_path.parent)
        except PrioritizationValidationError:
            pass
        else:
            raise AssertionError("tampered ranking was accepted")

    packet_path = fresh("packet") / "review-packet.json"
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    if packet["entries"]:
        packet["entries"][0]["marginal_oracle_count"] += 1
        packet_path.write_bytes(canonical_json_bytes(packet))
        try:
            validate_prioritization(packet_path.parent)
        except PrioritizationValidationError:
            pass
        else:
            raise AssertionError("tampered packet was accepted")

    report_path = fresh("report") / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["review_packet_count"] = report["review_packet_count"] + 1
    report_path.write_bytes(canonical_json_bytes(report))
    try:
        validate_prioritization(report_path.parent)
    except PrioritizationValidationError:
        pass
    else:
        raise AssertionError("tampered report was accepted")


def test_reproduction_writes_path_free_offline_evidence(tmp_path, monkeypatch) -> None:
    from prioritization_fixtures import default_loaded_inputs

    from manafold_census.prioritization import reproduction
    from manafold_census.prioritization.input import PrioritizationInputsV1

    monkeypatch.setattr(
        reproduction,
        "load_prioritization_inputs",
        lambda _inputs: default_loaded_inputs(),
    )
    inputs = PrioritizationInputsV1(
        m6_02_output_directory=tmp_path / "m6-02",
        source_lock_path=tmp_path / "source-lock.json",
        structural_output_directory=tmp_path / "m1",
        analysis_output_directory=tmp_path / "m3",
        m4_output_directory=tmp_path / "m4",
        parent_census_release_id=(
            "censusrel_55ff3102f75a64a0a2e1277810e709847803d085c6623ceeec14b7fe8f969e9f"
        ),
        expected_opportunity_count=None,
    )
    result = reproduction.reproduce_prioritization(
        inputs,
        tmp_path / "prioritization",
        tmp_path / "evidence.json",
        tmp_path / "evidence.md",
    )
    assert result.fileset_parity is True
    assert result.byte_parity is True
    evidence = (tmp_path / "evidence.json").read_text(encoding="utf-8")
    assert str(tmp_path) not in evidence
    assert '"offline_regeneration":true' in evidence


def _refresh_descriptor(output, relative_path: str) -> None:
    import json

    from manafold_census.canonical import canonical_json_bytes
    from manafold_census.digest import measure_file

    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    measurement = measure_file(output / relative_path)
    refreshed = []
    for descriptor in manifest["file_descriptors"]:
        if descriptor["relative_path"] == relative_path:
            descriptor = {
                **descriptor,
                "sha256": measurement.sha256,
                "byte_length": measurement.byte_length,
            }
        refreshed.append(descriptor)
    manifest["file_descriptors"] = refreshed
    manifest_path.write_bytes(canonical_json_bytes(manifest))


def test_self_consistent_packet_tamper_is_rejected_with_inputs(tmp_path) -> None:
    import json

    from prioritization_fixtures import default_loaded_inputs

    from manafold_census.canonical import canonical_json_bytes
    from manafold_census.prioritization.build import (
        build_prioritization_from_loaded_inputs,
    )
    from manafold_census.prioritization.validate import (
        PrioritizationValidationError,
        validate_prioritization_against_inputs,
    )

    loaded = default_loaded_inputs()
    output = build_prioritization_from_loaded_inputs(
        loaded, tmp_path / "output"
    ).output_directory
    packet_path = output / "review-packet.json"
    packet = json.loads(packet_path.read_bytes())
    assert packet["entries"]
    assert packet["entries"][0]["example_surfaces"]
    packet["entries"][0]["example_surfaces"][0]["raw_text"] = "tampered evidence"
    packet_path.write_bytes(canonical_json_bytes(packet))
    _refresh_descriptor(output, "review-packet.json")
    try:
        validate_prioritization_against_inputs(output, loaded)
    except PrioritizationValidationError:
        return
    raise AssertionError("self-consistent packet tamper was accepted")


def test_self_consistent_report_tamper_is_rejected_with_inputs(tmp_path) -> None:
    import json

    from prioritization_fixtures import default_loaded_inputs

    from manafold_census.canonical import canonical_json_bytes
    from manafold_census.prioritization.build import (
        build_prioritization_from_loaded_inputs,
    )
    from manafold_census.prioritization.validate import (
        PrioritizationValidationError,
        validate_prioritization_against_inputs,
    )

    loaded = default_loaded_inputs()
    output = build_prioritization_from_loaded_inputs(
        loaded, tmp_path / "output"
    ).output_directory
    report_path = output / "report.json"
    report = json.loads(report_path.read_bytes())
    report["notes"] = ["tampered note"]
    report_path.write_bytes(canonical_json_bytes(report))
    _refresh_descriptor(output, "report.json")
    try:
        validate_prioritization_against_inputs(output, loaded)
    except PrioritizationValidationError:
        return
    raise AssertionError("self-consistent report tamper was accepted")


def test_frozen_policy_constants_are_enforced(tmp_path) -> None:
    import json

    from prioritization_fixtures import default_loaded_inputs

    from manafold_census.canonical import canonical_json_bytes
    from manafold_census.prioritization.build import (
        build_prioritization_from_loaded_inputs,
    )
    from manafold_census.prioritization.validate import (
        PrioritizationValidationError,
        validate_prioritization,
    )

    output = build_prioritization_from_loaded_inputs(
        default_loaded_inputs(), tmp_path / "output"
    ).output_directory
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["ranking_policy_version"] = "999"
    manifest_path.write_bytes(canonical_json_bytes(manifest))
    try:
        validate_prioritization(output)
    except PrioritizationValidationError:
        return
    raise AssertionError("drifted policy constant was accepted")
