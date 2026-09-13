from __future__ import annotations

import copy

import pytest
from analysis_fixtures import trace_event

from manafold_census.analysis.trace import (
    RequirementTraceEventV1,
    TraceDispositionV1,
    trace_sort_key,
)
from manafold_census.validation import validate_document


def test_trace_locator_does_not_change_requirement_identity() -> None:
    first = trace_event(span=(0, 15))
    second = trace_event(span=(20, 35))
    assert first.candidate_requirement_id == second.candidate_requirement_id
    assert first.to_wire()["parser_span"] != second.to_wire()["parser_span"]


def test_trace_events_have_deterministic_order() -> None:
    first = trace_event(span=(20, 35))
    second = trace_event(span=(0, 15))
    assert sorted((second, first), key=trace_sort_key) == sorted(
        (first, second),
        key=trace_sort_key,
    )


def test_trace_schema_accepts_a_valid_event() -> None:
    validate_document(
        trace_event().to_wire(),
        "analysis-trace.v1.schema.json",
    )


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
