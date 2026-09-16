"""Shared strict helpers and closed vocabularies for M6-03 planning."""

from __future__ import annotations

from enum import StrEnum

AUTHORITY_SCOPE = "NON_AUTHORITATIVE"
UNASSESSED = "UNASSESSED"

ASSESSMENT_POLICY_ID = "m6-03.opportunity-assessment"
ASSESSMENT_POLICY_VERSION = "1"
RANKING_POLICY_ID = "m6-03.breadth-ranking"
RANKING_POLICY_VERSION = "1"
RANKING_POLICY_LABEL = "m6-03.breadth-ranking.v1"

REVIEW_PACKET_LIMIT = 25


class PlanningNoiseV1(StrEnum):
    NONE = "NONE"
    ALL_NULL = "ALL_NULL"
    ALL_EMPTY_OR_WHITESPACE = "ALL_EMPTY_OR_WHITESPACE"
    NULL_OR_EMPTY_ONLY = "NULL_OR_EMPTY_ONLY"


class StoppingReasonV1(StrEnum):
    REVIEW_BUDGET_REACHED = "REVIEW_BUDGET_REACHED"
    NO_ADDITIONAL_ORACLE_COVERAGE = "NO_ADDITIONAL_ORACLE_COVERAGE"


REVIEW_QUESTIONS: tuple[str, ...] = (
    "Does this evidence represent one reusable semantic nucleus?",
    "Does it reuse an existing M4 family?",
    "Are observed differences merely typed parameter values?",
    "Would a new family be justified?",
    "Does the existing M2/M3/M4 contract represent it?",
    "Does any part belong to M7 rather than card-local M6?",
    "What additional primary rules evidence is required?",
)

NON_AUTHORITY_STATEMENTS: tuple[str, ...] = (
    "Capability Opportunity != Capability.",
    "Opportunity assessment != semantic review.",
    "Ranking != authority.",
    "Mechanical overlap != semantic equivalence.",
    "Marginal Oracle coverage != semantic breadth.",
    "Review packet != accepted campaign result.",
    "M6-03 creates no Requirement, Capability, mapping, or M4 authority.",
)


def is_exact_lens(lens_value: str) -> bool:
    return lens_value.endswith("_EXACT")


def lens_rank(lens_value: str) -> int:
    return 0 if is_exact_lens(lens_value) else 1


__all__ = [
    "ASSESSMENT_POLICY_ID",
    "ASSESSMENT_POLICY_VERSION",
    "AUTHORITY_SCOPE",
    "NON_AUTHORITY_STATEMENTS",
    "REVIEW_PACKET_LIMIT",
    "RANKING_POLICY_ID",
    "RANKING_POLICY_LABEL",
    "RANKING_POLICY_VERSION",
    "REVIEW_QUESTIONS",
    "UNASSESSED",
    "PlanningNoiseV1",
    "StoppingReasonV1",
    "is_exact_lens",
    "lens_rank",
]
