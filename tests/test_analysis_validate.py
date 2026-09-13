from __future__ import annotations

import pytest
from analysis_fixtures import trace_event
from test_analysis_manifest import card_record

from manafold_census.analysis.manifest import card_source_key
from manafold_census.analysis.validate import (
    AnalysisClosureError,
    validate_identity_set,
)


def test_identity_set_validator_rejects_missing_card_with_equal_count() -> None:
    expected = [
        card_source_key(card_record(1).source),
        card_source_key(card_record(2).source),
    ]
    actual = [expected[0], card_source_key(card_record(3).source)]
    with pytest.raises(AnalysisClosureError, match="missing|extra"):
        validate_identity_set(expected, actual)


def test_duplicate_and_extra_records_fail_closed() -> None:
    key = card_source_key(card_record(1).source)
    with pytest.raises(AnalysisClosureError, match="duplicate"):
        validate_identity_set([key], [key, key])


def test_trace_fixture_has_a_source_key_compatible_with_closure() -> None:
    event = trace_event()
    assert event.card_source_key[0] == "census.structural-card.v1"
