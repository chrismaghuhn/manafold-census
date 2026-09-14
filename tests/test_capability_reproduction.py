from __future__ import annotations

import hashlib
from dataclasses import replace
from itertools import permutations
from pathlib import Path

from capability_m3_fixtures import (
    record_with_other_requirement,
    record_with_proposed_requirement,
    write_synthetic_m3,
)

from manafold_census.capability.build import build_reference_m4
from manafold_census.capability.definition import CapabilityLifecycleStateV1
from manafold_census.capability.evolution import (
    evolution_claim_digest_for,
    retirement_event,
)
from manafold_census.capability.input import load_m3_requirement_corpus
from manafold_census.capability.mapping import mapping_decision
from manafold_census.capability.review import (
    CapabilityReviewRecordV1,
    EvolutionReviewSubjectV1,
    ReviewDecisionV1,
)


def relative_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def directory_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for relative, value in sorted(relative_bytes(root).items()):
        name = relative.encode("utf-8")
        digest.update(len(name).to_bytes(8, "big"))
        digest.update(name)
        digest.update(len(value).to_bytes(8, "big"))
        digest.update(value)
    return digest.hexdigest()


def _empty_build(root: Path):
    from test_capability_build import build_synthetic_m4, empty_m3_input

    m3_input = empty_m3_input(root / "m3")
    return build_synthetic_m4(
        root / "m4",
        m3_input=m3_input,
        parent_m4_manifest_sha256=None,
        parent_m4_manifest=None,
    )


def test_two_clean_m4_builds_have_identical_bytes_and_directory_digest(
    tmp_path: Path,
) -> None:
    first = _empty_build(tmp_path / "first")
    second = _empty_build(tmp_path / "second")

    assert relative_bytes(first.output_dir) == relative_bytes(second.output_dir)
    assert directory_digest(first.output_dir) == directory_digest(second.output_dir)


def _permutation_inputs(tmp_path: Path) -> dict[str, object]:
    from test_capability_evolution import _claim, _definition
    from test_capability_validate import _active_definition_and_links

    from manafold_census.capability.definition import CapabilityDefinitionV1
    from manafold_census.capability.evolution import (
        requires_edge,
        specializes_edge,
    )

    m3_input = write_synthetic_m3(
        tmp_path / "m3",
        records=(record_with_proposed_requirement(0), record_with_other_requirement(1)),
    )
    corpus = load_m3_requirement_corpus(m3_input)
    active, definition_review, links, link_reviews, admissibility = (
        _active_definition_and_links(corpus, 2)
    )

    retired_one = _definition(
        _claim(kind=corpus.requirements[0].kind, version=2),
        lifecycle=CapabilityLifecycleStateV1.RETIRED,
    )
    retired_two = _definition(
        _claim(kind=corpus.requirements[0].kind, version=3),
        lifecycle=CapabilityLifecycleStateV1.RETIRED,
    )
    retired_one = replace(retired_one, review_ref=None)
    retired_two = replace(retired_two, review_ref=None)

    def reviewed_retirement(capability: CapabilityDefinitionV1):
        provisional = retirement_event(capability, review_ref="mrv_" + "1" * 64)
        review = CapabilityReviewRecordV1.create(
            authority_id="m4.capability-review",
            authority_version="1",
            subject=EvolutionReviewSubjectV1(
                provisional.event_id,
                evolution_claim_digest_for(provisional),
            ),
            decision=ReviewDecisionV1.ACCEPTED,
            reviewer_id="maintainer:test",
            generalization_basis=None,
        )
        return replace(provisional, review_ref=review.record_id), review

    first_event, first_event_review = reviewed_retirement(retired_one)
    second_event, second_event_review = reviewed_retirement(retired_two)
    relations = (
        requires_edge(active, retired_one),
        specializes_edge(active, retired_two),
    )
    decisions = tuple(
        mapping_decision(
            requirement,
            "MAPPED",
            None,
            m3_analysis_manifest_sha256=corpus.m3_analysis_manifest_sha256,
            active_link_ids=(link.link_id,),
        )
        for requirement, link in zip(corpus.requirements, links, strict=True)
    )
    return {
        "m3_input": m3_input,
        "definitions": (active, retired_one, retired_two),
        "reviews": (
            definition_review,
            *link_reviews,
            first_event_review,
            second_event_review,
        ),
        "relations": relations,
        "admissibility": admissibility,
        "links": links,
        "decisions": decisions,
        "evolution": (first_event, second_event),
    }


def _build_with_inputs(output: Path, values: dict[str, object]):
    return build_reference_m4(
        values["m3_input"],  # type: ignore[arg-type]
        None,
        None,
        values["definitions"],  # type: ignore[arg-type]
        values["reviews"],  # type: ignore[arg-type]
        values["relations"],  # type: ignore[arg-type]
        values["admissibility"],  # type: ignore[arg-type]
        values["links"],  # type: ignore[arg-type]
        values["decisions"],  # type: ignore[arg-type]
        values["evolution"],  # type: ignore[arg-type]
        output,
    )


def test_permuting_all_m4_input_sequences_preserves_canonical_bytes(
    tmp_path: Path,
) -> None:
    values = _permutation_inputs(tmp_path)
    baseline = _build_with_inputs(tmp_path / "baseline", values)
    expected = relative_bytes(baseline.output_dir)

    for field in (
        "definitions",
        "reviews",
        "relations",
        "admissibility",
        "links",
        "decisions",
        "evolution",
    ):
        original = values[field]
        assert isinstance(original, tuple)
        for index, shuffled in enumerate(permutations(original)):
            variant = dict(values)
            variant[field] = shuffled
            result = _build_with_inputs(tmp_path / f"{field}-{index}", variant)
            assert relative_bytes(result.output_dir) == expected
