from __future__ import annotations

import copy

import pytest
from analysis_fixtures import (
    OTHER_SOURCE_LOCK_DIGEST,
    bundle,
    bundle_from_other_source,
    source_ref,
)

from manafold_census.analysis.model import (
    AnalysisOutcomeV1,
    CardAnalysisRecordV1,
    NegativeReviewAuthorityRefV1,
    card_source_key,
)
from manafold_census.validation import validate_document


def test_requirements_produced_requires_one_bundle() -> None:
    with pytest.raises(ValueError, match="bundle"):
        CardAnalysisRecordV1(
            source=source_ref(),
            outcome=AnalysisOutcomeV1.REQUIREMENTS_PRODUCED,
            bundle=None,
            no_requirements_basis=None,
        )


def test_no_requirements_requires_negative_authority_reference() -> None:
    with pytest.raises(ValueError, match="authority"):
        CardAnalysisRecordV1(
            source=source_ref(),
            outcome=AnalysisOutcomeV1.NO_REQUIREMENTS_APPLICABLE,
            bundle=None,
            no_requirements_basis=None,
        )


def test_unresolved_may_have_zero_or_more_retained_requirements() -> None:
    record = CardAnalysisRecordV1(
        source=source_ref(),
        outcome=AnalysisOutcomeV1.UNRESOLVED_ANALYSIS,
        bundle=None,
        no_requirements_basis=None,
    )
    assert record.to_wire()["bundle"] is None

    retained = CardAnalysisRecordV1(
        source=source_ref(),
        outcome=AnalysisOutcomeV1.UNRESOLVED_ANALYSIS,
        bundle=bundle(),
        no_requirements_basis=None,
    )
    assert retained.to_wire()["bundle"] is not None


def test_source_key_excludes_source_lock_context_like_m2_identity() -> None:
    first = source_ref()
    second = source_ref(source_lock_digest=OTHER_SOURCE_LOCK_DIGEST)
    assert card_source_key(first) == card_source_key(second)


def test_card_record_rejects_bundle_from_another_source() -> None:
    with pytest.raises(ValueError, match="source"):
        CardAnalysisRecordV1(
            source=source_ref(),
            outcome=AnalysisOutcomeV1.REQUIREMENTS_PRODUCED,
            bundle=bundle_from_other_source(),
            no_requirements_basis=None,
        )


def test_card_analysis_wire_rejects_unknown_fields_and_wrong_schema() -> None:
    record = CardAnalysisRecordV1(
        source=source_ref(),
        outcome=AnalysisOutcomeV1.REQUIREMENTS_PRODUCED,
        bundle=bundle(),
        no_requirements_basis=None,
    )
    unknown = copy.deepcopy(record.to_wire())
    unknown["unexpected"] = True
    with pytest.raises((TypeError, ValueError), match="unexpected"):
        CardAnalysisRecordV1.from_wire(unknown)

    wrong_schema = copy.deepcopy(record.to_wire())
    wrong_schema["schema"] = "census.card-analysis.v2"
    with pytest.raises(ValueError, match="schema"):
        CardAnalysisRecordV1.from_wire(wrong_schema)


def test_card_analysis_schema_accepts_a_valid_record() -> None:
    record = CardAnalysisRecordV1(
        source=source_ref(),
        outcome=AnalysisOutcomeV1.REQUIREMENTS_PRODUCED,
        bundle=bundle(),
        no_requirements_basis=None,
    )
    validate_document(record.to_wire(), "card-analysis.v1.schema.json")


def test_negative_authority_reference_requires_deterministic_record_id() -> None:
    with pytest.raises(ValueError, match="record_id"):
        NegativeReviewAuthorityRefV1(
            authority_id="fixture-negative-authority",
            authority_version="1",
            record_id="arbitrary-record",
            record_sha256="d" * 64,
            scope_digest="e" * 64,
        )
