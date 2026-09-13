"""Cross-binding validation for producer findings and PatternRule output."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, cast

from ..semantic.evidence import StructuralFieldEvidenceV1, StructuralKeywordEvidenceV1
from ..semantic.model import DerivationMethodV1
from ..structural.model import StructuralCardRecordV1
from .patterns import (
    EffectivePatternRegistryV1,
    EvidencePolicyV1,
    MatcherKindV1,
    PatternEligibilityStateV1,
    PatternSourceFieldV1,
    pattern_rule_digest_for,
)

if TYPE_CHECKING:
    from .producer import (
        ProducerContextV1,
        ProducerDescriptorV1,
        ProducerFindingV1,
        ProducerResultV1,
    )

_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _validate_finding_shape(finding: ProducerFindingV1) -> None:
    if finding.candidate_index is not None and (
        type(finding.candidate_index) is not int or finding.candidate_index < 0
    ):
        raise ValueError("finding candidate_index is invalid")
    fields = (finding.pattern_id, finding.pattern_version, finding.pattern_digest)
    if any(item is not None for item in fields) and not all(
        item is not None for item in fields
    ):
        raise ValueError("finding pattern identity must be complete")
    if finding.pattern_id is None:
        raise ValueError("pattern finding requires pattern identity")
    if not isinstance(finding.pattern_id, str) or not isinstance(
        finding.pattern_version, str
    ):
        raise ValueError("pattern finding identity is not text")
    if not isinstance(finding.pattern_digest, str) or not _DIGEST_PATTERN.fullmatch(
        finding.pattern_digest
    ):
        raise ValueError("pattern finding digest is invalid")
    if not isinstance(finding.source_field, PatternSourceFieldV1):
        raise ValueError("pattern finding requires a source field")
    if finding.face_index is not None and (
        type(finding.face_index) is not int or finding.face_index < 0
    ):
        raise ValueError("finding face_index is invalid")
    if finding.exact_fragment is not None and not isinstance(
        finding.exact_fragment, str
    ):
        raise ValueError("finding exact_fragment is not text")
    if finding.clause_ordinal is not None and (
        type(finding.clause_ordinal) is not int or finding.clause_ordinal < 0
    ):
        raise ValueError("finding clause_ordinal is invalid")
    if finding.parser_span is not None:
        if (
            not isinstance(finding.parser_span, tuple | list)
            or len(finding.parser_span) != 2
        ):
            raise ValueError("finding parser_span is invalid")
        start, end = finding.parser_span
        if type(start) is not int or type(end) is not int or start < 0 or end < start:
            raise ValueError("finding parser_span is invalid")


def _require_rule_evidence(
    candidate: object,
    rule: object,
    record: StructuralCardRecordV1,
) -> None:
    from ..semantic.model import RequirementV1
    from .patterns import PatternRuleV1

    if not isinstance(candidate, RequirementV1) or not isinstance(rule, PatternRuleV1):
        raise TypeError("pattern validation received an invalid value")
    if candidate.family is not rule.output_template.family:
        raise ValueError("pattern output family does not match candidate")
    if candidate.kind is not rule.output_template.kind:
        raise ValueError("pattern output kind does not match candidate")
    if candidate.parameters.to_wire() != rule.output_template.parameters.to_wire():
        raise ValueError("pattern output parameters do not match candidate")
    if not any(
        derivation.method is DerivationMethodV1.DETERMINISTIC_RULE
        and derivation.producer_id == rule.producer_id
        and derivation.producer_version == rule.producer_version
        for derivation in candidate.provenance.derivations
    ):
        raise ValueError("pattern producer provenance is missing")
    if rule.source_scope.field is PatternSourceFieldV1.KEYWORDS:
        expected_index = (
            None
            if record.keywords is None
            else next(
                (
                    index
                    for index, value in enumerate(record.keywords)
                    if value == rule.match_text
                ),
                None,
            )
        )
        if expected_index is None or not any(
            isinstance(evidence, StructuralKeywordEvidenceV1)
            and evidence.source == candidate.source
            and evidence.keyword_index == expected_index
            and evidence.keyword_value == rule.match_text
            for evidence in candidate.evidence
        ):
            raise ValueError("pattern keyword evidence does not match candidate")
        return
    expected_fragment = (
        rule.match_text
        if rule.evidence_policy is EvidencePolicyV1.EXACT_FRAGMENT
        else None
    )
    if not any(
        isinstance(evidence, StructuralFieldEvidenceV1)
        and evidence.source == candidate.source
        and evidence.field == rule.source_scope.field.value
        and evidence.face_index == rule.source_scope.face_index
        and evidence.fragment == expected_fragment
        for evidence in candidate.evidence
    ):
        raise ValueError("pattern field evidence does not match candidate")


def _validate_finding_match(
    finding: ProducerFindingV1,
    candidate: object,
    descriptor: ProducerDescriptorV1,
    record: StructuralCardRecordV1,
    registry: EffectivePatternRegistryV1,
) -> None:
    _validate_finding_shape(finding)
    key = (cast(str, finding.pattern_id), cast(str, finding.pattern_version))
    rules = {(item.pattern_id, item.pattern_version): item for item in registry.rules}
    eligibilities = {
        (item.pattern_id, item.pattern_version): item for item in registry.eligibility
    }
    rule = rules.get(key)
    eligibility = eligibilities.get(key)
    if rule is None or eligibility is None:
        raise ValueError("pattern finding references an unknown rule")
    if eligibility.eligibility is not PatternEligibilityStateV1.REVIEWED_FOR_REUSE:
        raise ValueError("pattern finding references an ineligible rule")
    if finding.pattern_digest != pattern_rule_digest_for(rule):
        raise ValueError("pattern finding digest does not match rule")
    if (rule.producer_id, rule.producer_version) != (
        descriptor.producer_id,
        descriptor.producer_version,
    ):
        raise ValueError("pattern finding producer does not match descriptor")
    if finding.source_field is not rule.source_scope.field:
        raise ValueError("pattern finding source field does not match rule")
    if finding.face_index != rule.source_scope.face_index:
        raise ValueError("pattern finding face index does not match rule")
    expected_fragment = (
        rule.match_text
        if rule.evidence_policy is EvidencePolicyV1.EXACT_FRAGMENT
        else None
    )
    if finding.exact_fragment != expected_fragment:
        raise ValueError("pattern finding fragment does not match rule policy")
    if rule.source_scope.field is PatternSourceFieldV1.KEYWORDS:
        actual_match = (
            record.keywords is not None and rule.match_text in record.keywords
        )
    else:
        text = record.oracle_text
        if finding.face_index is not None:
            if record.faces is None or finding.face_index >= len(record.faces):
                raise ValueError("pattern finding face is missing")
            text = record.faces[finding.face_index].oracle_text
        actual_match = isinstance(text, str) and (
            rule.match_text in text
            if rule.matcher_kind is MatcherKindV1.EXACT_FRAGMENT
            else rule.match_text == text
        )
    if not actual_match:
        raise ValueError("pattern finding does not match the M1 source")
    _require_rule_evidence(candidate, rule, record)


def validate_producer_findings(
    result: ProducerResultV1,
    descriptor: ProducerDescriptorV1,
    record: StructuralCardRecordV1,
    context: ProducerContextV1,
) -> None:
    from .producer import ProducerContractError, ProducerResultStatusV1

    if descriptor.pattern_registry_digest is None:
        if result.findings:
            raise ProducerContractError(
                "producer findings require a pattern registry dependency"
            )
        return
    if context.pattern_registry is None:
        raise ProducerContractError("pattern finding requires a registry snapshot")
    if not result.findings:
        if result.status is ProducerResultStatusV1.EMITTED:
            raise ProducerContractError(
                "pattern-dependent producer requires one finding per candidate"
            )
        return
    try:
        registry = EffectivePatternRegistryV1.from_wire(
            context.pattern_registry.to_wire()
        )
        if result.status is ProducerResultStatusV1.EMITTED and {
            item.candidate_index for item in result.findings
        } != set(range(len(result.candidates))):
            raise ValueError(
                "pattern-dependent producer requires one finding per candidate"
            )
        for finding in result.findings:
            candidate = result.candidates[cast(int, finding.candidate_index)]
            _validate_finding_match(finding, candidate, descriptor, record, registry)
    except (TypeError, ValueError) as error:
        raise ProducerContractError(str(error)) from error
