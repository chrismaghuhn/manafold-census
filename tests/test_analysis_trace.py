from __future__ import annotations

import copy

import pytest
from analysis_fixtures import trace_event

from manafold_census.analysis.model import NegativeReviewAuthorityRefV1
from manafold_census.analysis.trace import (
    NegativeAuthorityTraceDispositionV1,
    NegativeAuthorityTraceEventV1,
    RequirementTraceEventV1,
    TraceDispositionV1,
    trace_event_from_wire,
    trace_sort_key,
)
from manafold_census.validation import validate_document


def _authority_trace_event(
    disposition: NegativeAuthorityTraceDispositionV1 = (
        NegativeAuthorityTraceDispositionV1.NEGATIVE_AUTHORITY_APPLIED
    ),
) -> NegativeAuthorityTraceEventV1:
    return NegativeAuthorityTraceEventV1(
        card_source_key=trace_event().card_source_key,
        authority=NegativeReviewAuthorityRefV1(
            authority_id="fixture-negative-authority",
            authority_version="1",
            record_id="nra_" + "a" * 64,
            record_sha256="b" * 64,
            scope_digest="c" * 64,
        ),
        disposition=disposition,
    )


def test_trace_locator_does_not_change_requirement_identity() -> None:
    first = trace_event(span=(0, 15))
    second = trace_event(span=(20, 35))
    assert first.candidate_requirement_id == second.candidate_requirement_id
    assert first.to_wire()["parser_span"] != second.to_wire()["parser_span"]


def test_trace_events_have_deterministic_order() -> None:
    first = trace_event(
        span=(0, 15),
        pattern_digest="a" * 64,
        exact_fragment="Draw two cards.",
    )
    second = trace_event(
        span=(0, 15),
        pattern_digest="b" * 64,
        exact_fragment="Draw cards.",
    )
    expected = tuple(sorted((first, second), key=trace_sort_key))
    assert tuple(sorted((second, first), key=trace_sort_key)) == expected
    assert trace_sort_key(first) != trace_sort_key(second)


def test_trace_schema_accepts_a_valid_event() -> None:
    validate_document(
        trace_event().to_wire(),
        "analysis-trace.v1.schema.json",
    )


@pytest.mark.parametrize(
    "disposition",
    list(NegativeAuthorityTraceDispositionV1),
)
def test_negative_authority_trace_roundtrip_and_schema(
    disposition: NegativeAuthorityTraceDispositionV1,
) -> None:
    event = _authority_trace_event(disposition)
    wire = event.to_wire()
    validate_document(wire, "analysis-trace.v1.schema.json")
    assert trace_event_from_wire(wire).to_wire() == wire


def test_negative_authority_trace_rejects_malformed_identity_and_disposition() -> None:
    malformed = _authority_trace_event().to_wire()
    malformed["authority"]["record_sha256"] = "not-a-digest"
    with pytest.raises(ValueError, match="record_sha256"):
        trace_event_from_wire(malformed)
    with pytest.raises(ValueError):
        validate_document(malformed, "analysis-trace.v1.schema.json")

    unknown = _authority_trace_event().to_wire()
    unknown["disposition"] = "NEGATIVE_AUTHORITY_UNKNOWN"
    with pytest.raises(ValueError, match="disposition"):
        trace_event_from_wire(unknown)
    with pytest.raises(ValueError):
        validate_document(unknown, "analysis-trace.v1.schema.json")


def test_trace_union_order_is_input_order_independent() -> None:
    producer = trace_event()
    authority = _authority_trace_event(
        NegativeAuthorityTraceDispositionV1.NEGATIVE_AUTHORITY_CONFLICT
    )
    expected = tuple(sorted((producer, authority), key=trace_sort_key))
    assert tuple(sorted((authority, producer), key=trace_sort_key)) == expected


def test_trace_wire_rejects_unknown_fields_and_invalid_source_key() -> None:
    wire = copy.deepcopy(trace_event().to_wire())
    wire["unexpected"] = True
    with pytest.raises((TypeError, ValueError), match="unexpected"):
        RequirementTraceEventV1.from_wire(wire)

    invalid = trace_event().to_wire()
    invalid["card_source_key"][1] = "not-a-uuid"
    with pytest.raises(ValueError, match="oracle_id"):
        RequirementTraceEventV1.from_wire(invalid)


def test_trace_disposition_is_closed() -> None:
    assert TraceDispositionV1.CANDIDATE_EMITTED.value == "CANDIDATE_EMITTED"


def test_trace_model_and_schema_reject_partial_pattern_identity() -> None:
    wire = trace_event().to_wire()
    wire["pattern_version"] = None
    with pytest.raises((TypeError, ValueError), match="pattern"):
        RequirementTraceEventV1.from_wire(wire)
    with pytest.raises(ValueError):
        validate_document(wire, "analysis-trace.v1.schema.json")


def test_trace_model_and_schema_reject_keyword_fragment_scope() -> None:
    wire = trace_event().to_wire()
    wire["source_field"] = "keywords"
    with pytest.raises((TypeError, ValueError), match="oracle_text|fragment"):
        RequirementTraceEventV1.from_wire(wire)
    with pytest.raises(ValueError):
        validate_document(wire, "analysis-trace.v1.schema.json")
