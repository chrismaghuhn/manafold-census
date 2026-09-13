"""Deterministic producer driven by an immutable exact-pattern registry."""

from __future__ import annotations

from manafold_census.semantic.evidence import (
    EvidenceV1,
    SourceRecordRefV1,
    StructuralFieldEvidenceV1,
    StructuralKeywordEvidenceV1,
)
from manafold_census.semantic.model import (
    DerivationMethodV1,
    DerivationV1,
    ProvenanceV1,
    RequirementV1,
    ResolutionReasonV1,
    ResolutionStateV1,
    ResolutionV1,
    ReviewStatusV1,
    ReviewV1,
)
from manafold_census.structural.model import StructuralCardRecordV1

from .patterns import (
    EffectivePatternRegistryV1,
    EvidencePolicyV1,
    PatternEligibilityStateV1,
    PatternRuleV1,
    PatternSourceFieldV1,
    pattern_rule_digest_for,
)
from .producer import (
    CandidateProducerV1,
    ProducerContextV1,
    ProducerContractError,
    ProducerDescriptorV1,
    ProducerFindingV1,
    ProducerResultV1,
)


class RegistryDrivenExactPatternProducerV1(CandidateProducerV1):
    """Execute only reviewed exact rules from the bound registry snapshot."""

    __slots__ = ("descriptor",)

    def __init__(self, *, pattern_registry_digest: str) -> None:
        self.descriptor = ProducerDescriptorV1(
            producer_id="m3.registry-exact-pattern",
            producer_version="1",
            derivation_method=DerivationMethodV1.DETERMINISTIC_RULE,
            input_schema=StructuralCardRecordV1.SCHEMA,
            input_fields=("faces", "keywords", "oracle_text"),
            pattern_registry_digest=pattern_registry_digest,
            deterministic=True,
            supports_relationships=False,
        )

    def produce(
        self,
        record: StructuralCardRecordV1,
        context: ProducerContextV1,
    ) -> ProducerResultV1:
        if not isinstance(record, StructuralCardRecordV1):
            raise ProducerContractError(
                "producer record must be structural card record"
            )
        if not isinstance(context, ProducerContextV1):
            raise ProducerContractError("producer context must be ProducerContextV1")
        snapshot = context.pattern_registry
        if snapshot is None:
            raise ProducerContractError("pattern registry snapshot is required")
        if snapshot.digest != self.descriptor.pattern_registry_digest:
            raise ProducerContractError(
                "producer pattern_registry_digest does not match context snapshot"
            )
        try:
            registry = EffectivePatternRegistryV1.from_wire(snapshot.to_wire())
        except (TypeError, ValueError) as error:
            raise ProducerContractError(
                "pattern registry snapshot is invalid"
            ) from error

        eligibilities = {
            (item.pattern_id, item.pattern_version): item
            for item in registry.eligibility
        }
        candidates: list[RequirementV1] = []
        findings: list[ProducerFindingV1] = []
        for rule in registry.rules:
            eligibility = eligibilities[(rule.pattern_id, rule.pattern_version)]
            if (
                eligibility.eligibility
                is not PatternEligibilityStateV1.REVIEWED_FOR_REUSE
            ):
                continue
            if (rule.producer_id, rule.producer_version) != (
                self.descriptor.producer_id,
                self.descriptor.producer_version,
            ):
                raise ProducerContractError(
                    "pattern rule producer does not match executing producer"
                )
            match = self._find_match(record, registry, rule)
            if match is None:
                continue
            source_text, face_index, keyword_index = match
            source = SourceRecordRefV1(
                record_schema=StructuralCardRecordV1.SCHEMA,
                source_lock_digest=context.source_lock_digest,
                oracle_id=record.oracle_id,
                source_card_id=record.source_card_id,
                source_record_sha256=record.source_record_sha256,
            )
            candidate_index = len(candidates)
            candidates.append(
                self._candidate(rule, source, source_text, face_index, keyword_index)
            )
            findings.append(
                ProducerFindingV1(
                    candidate_index=candidate_index,
                    pattern_id=rule.pattern_id,
                    pattern_version=rule.pattern_version,
                    pattern_digest=pattern_rule_digest_for(rule),
                    source_field=rule.source_scope.field,
                    face_index=face_index,
                    exact_fragment=(
                        rule.match_text
                        if rule.evidence_policy is EvidencePolicyV1.EXACT_FRAGMENT
                        else None
                    ),
                    clause_ordinal=None,
                    parser_span=None,
                )
            )
        if not candidates:
            return ProducerResultV1.no_match()
        return ProducerResultV1.emitted(candidates, findings=findings)

    @staticmethod
    def _find_match(
        record: StructuralCardRecordV1,
        registry: EffectivePatternRegistryV1,
        rule: PatternRuleV1,
    ) -> tuple[str, int | None, int | None] | None:
        field = rule.source_scope.field
        face_index = rule.source_scope.face_index
        if field is PatternSourceFieldV1.KEYWORDS:
            if record.keywords is None:
                return None
            for keyword_index, keyword in enumerate(record.keywords):
                if registry.matches_exact_text(
                    rule.pattern_id,
                    rule.pattern_version,
                    keyword,
                    face_index=None,
                ):
                    return keyword, None, keyword_index
            return None
        if face_index is None:
            text = record.oracle_text
        else:
            if record.faces is None or face_index >= len(record.faces):
                return None
            text = record.faces[face_index].oracle_text
        if not isinstance(text, str):
            return None
        if registry.matches_exact_text(
            rule.pattern_id,
            rule.pattern_version,
            text,
            face_index=face_index,
        ):
            return text, face_index, None
        return None

    def _candidate(
        self,
        rule: PatternRuleV1,
        source: SourceRecordRefV1,
        source_text: str,
        face_index: int | None,
        keyword_index: int | None,
    ) -> RequirementV1:
        if rule.source_scope.field is PatternSourceFieldV1.KEYWORDS:
            evidence: EvidenceV1 = StructuralKeywordEvidenceV1(
                source=source,
                keyword_index=keyword_index if keyword_index is not None else 0,
                keyword_value=source_text,
            )
        else:
            evidence = StructuralFieldEvidenceV1(
                source=source,
                field=rule.source_scope.field.value,
                face_index=face_index,
                fragment=(
                    rule.match_text
                    if rule.evidence_policy is EvidencePolicyV1.EXACT_FRAGMENT
                    else None
                ),
            )
        return RequirementV1.create(
            source=source,
            family=rule.output_template.family,
            kind=rule.output_template.kind,
            parameters=rule.output_template.parameters,
            evidence=(evidence,),
            provenance=ProvenanceV1(
                (
                    DerivationV1(
                        DerivationMethodV1.DETERMINISTIC_RULE,
                        self.descriptor.producer_id,
                        self.descriptor.producer_version,
                    ),
                )
            ),
            review=ReviewV1(ReviewStatusV1.PROPOSED, None, None),
            resolution=ResolutionV1(
                ResolutionStateV1.COMPLETE,
                ResolutionReasonV1.NONE,
                (),
            ),
        )


__all__ = ["RegistryDrivenExactPatternProducerV1"]
