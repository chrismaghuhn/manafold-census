from __future__ import annotations

from pathlib import Path

import pytest
from capability_m3_fixtures import (
    record_with_proposed_requirement,
    unresolved_record_without_bundle,
    write_synthetic_m3,
)

from manafold_census.capability.build import (
    CapabilityBuildError,
    M4BuildResultV1,
    build_reference_m4,
)
from manafold_census.capability.input import FrozenM3InputV1
from manafold_census.capability.link import LinkRelationV1, RequirementCapabilityLinkV1
from manafold_census.capability.mapping import (
    MappingDispositionV1,
    MappingReasonV1,
    mapping_decision,
)
from manafold_census.capability.model import CapabilityRefV1
from manafold_census.semantic.identity import wire_digest_for


def empty_m3_input(root: Path) -> FrozenM3InputV1:
    return write_synthetic_m3(
        root,
        records=(unresolved_record_without_bundle(),),
    )


def build_synthetic_m4(
    output_dir: Path,
    *,
    m3_input: FrozenM3InputV1,
    parent_m4_manifest_sha256: str | None,
    parent_m4_manifest,
) -> M4BuildResultV1:
    return build_reference_m4(
        m3_input,
        parent_m4_manifest_sha256,
        parent_m4_manifest,
        (),
        (),
        (),
        (),
        (),
        (),
        (),
        output_dir,
    )


def build_synthetic_m4_with_stale_link(
    output_dir: Path,
    *,
    m3_input: FrozenM3InputV1,
    parent_m4_manifest_sha256: str | None,
    parent_m4_manifest,
) -> M4BuildResultV1:
    from manafold_census.capability.input import load_m3_requirement_corpus

    corpus = load_m3_requirement_corpus(m3_input)
    requirement = corpus.requirements[0]
    link = RequirementCapabilityLinkV1.create(
        m3_analysis_manifest_sha256=corpus.m3_analysis_manifest_sha256,
        requirement_id=requirement.requirement_id,
        requirement_wire_digest=wire_digest_for(requirement),
        requirement_reviewed_claim_digest=None,
        capability=CapabilityRefV1("capfam_" + "f" * 64, 1, "e" * 64),
        relation=LinkRelationV1.DIRECT,
        parameter_bindings=(),
        m4_requirement_admissibility=None,
        composition_context=None,
    )
    decision = mapping_decision(
        requirement,
        MappingDispositionV1.INSUFFICIENT_EVIDENCE,
        MappingReasonV1.M4_ADMISSIBILITY_REVIEW_PENDING,
        m3_analysis_manifest_sha256=corpus.m3_analysis_manifest_sha256,
    )
    return build_reference_m4(
        m3_input,
        parent_m4_manifest_sha256,
        parent_m4_manifest,
        (),
        (),
        (),
        (),
        (link,),
        (decision,),
        (),
        output_dir,
    )


def test_failed_build_never_publishes_manifest(tmp_path: Path) -> None:
    output = tmp_path / "output"

    with pytest.raises(CapabilityBuildError, match="Capability"):
        build_synthetic_m4_with_stale_link(
            output,
            m3_input=write_synthetic_m3(
                tmp_path / "m3",
                records=(record_with_proposed_requirement(),),
            ),
            parent_m4_manifest_sha256=None,
            parent_m4_manifest=None,
        )

    assert not (output / "m4-ontology-manifest.json").exists()


def test_same_synthetic_inputs_produce_identical_bytes(tmp_path: Path) -> None:
    m3_input = empty_m3_input(tmp_path / "m3")
    first = build_synthetic_m4(
        tmp_path / "first",
        m3_input=m3_input,
        parent_m4_manifest_sha256=None,
        parent_m4_manifest=None,
    )
    second = build_synthetic_m4(
        tmp_path / "second",
        m3_input=m3_input,
        parent_m4_manifest_sha256=None,
        parent_m4_manifest=None,
    )

    def relative_bytes(root: Path) -> dict[str, bytes]:
        return {
            path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*")
            if path.is_file()
        }

    assert relative_bytes(first.output_dir) == relative_bytes(second.output_dir)


def test_parent_manifest_is_explicit_and_genesis_is_null(tmp_path: Path) -> None:
    m3_input = empty_m3_input(tmp_path / "m3")
    genesis = build_synthetic_m4(
        tmp_path / "genesis",
        m3_input=m3_input,
        parent_m4_manifest_sha256=None,
        parent_m4_manifest=None,
    )
    child = build_synthetic_m4(
        tmp_path / "child",
        m3_input=m3_input,
        parent_m4_manifest_sha256=genesis.manifest.digest(),
        parent_m4_manifest=genesis.manifest,
    )

    assert genesis.manifest.parent_m4_manifest_sha256 is None
    assert child.manifest.parent_m4_manifest_sha256 == genesis.manifest.digest()


def test_parent_manifest_cannot_be_inferred_or_mismatched(tmp_path: Path) -> None:
    m3_input = empty_m3_input(tmp_path / "m3")
    genesis = build_synthetic_m4(
        tmp_path / "genesis",
        m3_input=m3_input,
        parent_m4_manifest_sha256=None,
        parent_m4_manifest=None,
    )

    with pytest.raises(ValueError, match="parent M4 manifest"):
        build_synthetic_m4(
            tmp_path / "mismatched",
            m3_input=m3_input,
            parent_m4_manifest_sha256="f" * 64,
            parent_m4_manifest=genesis.manifest,
        )


def test_existing_output_is_never_overwritten(tmp_path: Path) -> None:
    output = tmp_path / "output"
    output.mkdir()
    sentinel = output / "sentinel.txt"
    sentinel.write_bytes(b"keep")

    with pytest.raises(CapabilityBuildError, match="already exists"):
        build_synthetic_m4(
            output,
            m3_input=empty_m3_input(tmp_path / "m3"),
            parent_m4_manifest_sha256=None,
            parent_m4_manifest=None,
        )

    assert sentinel.read_bytes() == b"keep"


def test_semantic_relations_are_persisted_and_reread(tmp_path: Path) -> None:
    from dataclasses import replace

    from test_capability_definition import _definition, _draw_claim

    from manafold_census.capability.relations import requires_edge

    first = _definition()
    second = _definition(
        claim=replace(_draw_claim(), capability_version=2),
        display_name="Synthetic dependent Capability",
    )
    relation = requires_edge(first, second)
    result = build_reference_m4(
        empty_m3_input(tmp_path / "m3"),
        None,
        None,
        (first, second),
        (),
        (relation,),
        (),
        (),
        (),
        (),
        tmp_path / "output",
    )

    relation_path = result.output_dir / "capability-relations.jsonl"
    assert relation_path.read_bytes().count(b"\n") == 1
    assert result.manifest.relation_file.record_count == 1
    assert result.semantic_relations == (relation,)


def test_semantic_relation_input_permutation_preserves_output_bytes(
    tmp_path: Path,
) -> None:
    from dataclasses import replace

    from test_capability_definition import _definition, _draw_claim

    from manafold_census.capability.relations import requires_edge, specializes_edge

    first = _definition()
    second = _definition(
        claim=replace(_draw_claim(), capability_version=2),
        display_name="Synthetic dependent Capability",
    )
    third = _definition(
        claim=replace(_draw_claim(), capability_version=3),
        display_name="Synthetic specialized Capability",
    )
    requires = requires_edge(first, second)
    specializes = specializes_edge(second, third)
    m3_input = empty_m3_input(tmp_path / "m3")
    first_result = build_reference_m4(
        m3_input,
        None,
        None,
        (first, second, third),
        (),
        (requires, specializes),
        (),
        (),
        (),
        (),
        tmp_path / "first",
    )
    second_result = build_reference_m4(
        m3_input,
        None,
        None,
        (first, second, third),
        (),
        (specializes, requires),
        (),
        (),
        (),
        (),
        tmp_path / "second",
    )

    def relative_bytes(root: Path) -> dict[str, bytes]:
        return {
            path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*")
            if path.is_file()
        }

    assert relative_bytes(first_result.output_dir) == relative_bytes(
        second_result.output_dir
    )
