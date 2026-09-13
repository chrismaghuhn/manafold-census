from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from manafold_census.analysis.authority import (
    NegativeAuthorityScopeV1,
    negative_authority_scope_digest,
)
from manafold_census.analysis.build import (
    AnalysisBuildError,
    NegativeAuthorityInputV1,
    build_reference_m3,
)
from manafold_census.analysis.manifest import SHARD_NAMES, card_source_key
from manafold_census.analysis.model import (
    AnalysisOutcomeV1,
    CardAnalysisRecordV1,
    NegativeReviewAuthorityRefV1,
)
from manafold_census.analysis.patterns import EffectivePatternRegistryV1
from manafold_census.analysis.producer import (
    CandidateProducerV1,
    ProducerContextV1,
    ProducerDescriptorV1,
    ProducerResultV1,
)
from manafold_census.analysis.registry import ProducerRegistryV1
from manafold_census.canonical import canonical_json_bytes
from manafold_census.models import SourceLock
from manafold_census.semantic.evidence import (
    SourceRecordRefV1,
    StructuralFieldEvidenceV1,
)
from manafold_census.semantic.kind_payloads import DrawCardsParametersV1
from manafold_census.semantic.kinds import RequirementFamilyV1, RequirementKindV1
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
from manafold_census.semantic.primitives import (
    EntityRefV1,
    EntityRoleV1,
    MultiplicityV1,
    QuantityModeV1,
    QuantityV1,
)
from manafold_census.structural.index import (
    inspect_structural_index,
)
from manafold_census.structural.manifest import StructuralCardIndexManifestV1
from manafold_census.structural.model import StructuralCardRecordV1

REPOSITORY_ROOT = Path(__file__).parents[1]
GOLDEN_CARDS_PATH = REPOSITORY_ROOT / "fixtures" / "analysis" / "golden-cards.json"
PATTERN_REGISTRY_PATH = (
    REPOSITORY_ROOT / "fixtures" / "analysis" / "pattern-registry.v1.json"
)
NEGATIVE_AUTHORITY_PATH = (
    REPOSITORY_ROOT / "fixtures" / "analysis" / "negative-authority.v1.json"
)
SOURCE_LOCK_PATH = REPOSITORY_ROOT / "source-locks" / "scryfall-oracle-v1.json"


def _source_lock() -> SourceLock:
    return SourceLock.from_wire(json.loads(SOURCE_LOCK_PATH.read_bytes()))


def _load_golden_cards() -> list[StructuralCardRecordV1]:
    return [
        StructuralCardRecordV1.from_wire(document)
        for document in json.loads(GOLDEN_CARDS_PATH.read_bytes())
    ]


def _write_structural_fixture(
    root: Path,
) -> tuple[Path, Path, tuple[StructuralCardRecordV1, ...]]:
    records = tuple(sorted(_load_golden_cards(), key=lambda item: item.oracle_id))
    records_root = root / "records"
    records_root.mkdir(parents=True)
    source_lock_path = root / "source-lock.json"
    shutil.copyfile(SOURCE_LOCK_PATH, source_lock_path)
    for shard in SHARD_NAMES:
        raw = b"".join(
            canonical_json_bytes(record.to_wire()) + b"\n"
            for record in records
            if record.oracle_id[0] == shard
        )
        (records_root / f"{shard}.jsonl").write_bytes(raw)
    summary = inspect_structural_index(records_root)
    manifest = StructuralCardIndexManifestV1.from_summary(summary)
    (root / "structural-index-manifest.json").write_bytes(
        canonical_json_bytes(manifest.to_wire())
    )
    return root, source_lock_path, records


def _source_ref(
    record: StructuralCardRecordV1,
    source_lock_digest: str,
) -> SourceRecordRefV1:
    return SourceRecordRefV1(
        record_schema=StructuralCardRecordV1.SCHEMA,
        source_lock_digest=source_lock_digest,
        oracle_id=record.oracle_id,
        source_card_id=record.source_card_id,
        source_record_sha256=record.source_record_sha256,
    )


def _entity() -> EntityRefV1:
    return EntityRefV1(EntityRoleV1.SOURCE, MultiplicityV1.ONE, None)


def _draw_candidate(
    record: StructuralCardRecordV1,
    context: ProducerContextV1,
    descriptor: ProducerDescriptorV1,
    quantity: int,
    fragment: str,
    face_index: int | None = None,
) -> RequirementV1:
    source = _source_ref(record, context.source_lock_digest)
    return RequirementV1.create(
        source=source,
        family=RequirementFamilyV1.EFFECT,
        kind=RequirementKindV1.DRAW_CARDS,
        parameters=DrawCardsParametersV1(
            _entity(), QuantityV1(QuantityModeV1.EXACT, quantity)
        ),
        evidence=(
            StructuralFieldEvidenceV1(
                source,
                "oracle_text",
                face_index,
                fragment,
            ),
        ),
        provenance=ProvenanceV1(
            (
                DerivationV1(
                    DerivationMethodV1.DETERMINISTIC_RULE,
                    descriptor.producer_id,
                    descriptor.producer_version,
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


def _descriptor(
    producer_id: str,
    *,
    input_fields: tuple[str, ...],
    pattern_registry_digest: str | None = None,
) -> ProducerDescriptorV1:
    return ProducerDescriptorV1(
        producer_id=producer_id,
        producer_version="1",
        derivation_method=DerivationMethodV1.DETERMINISTIC_RULE,
        input_schema=StructuralCardRecordV1.SCHEMA,
        input_fields=input_fields,
        pattern_registry_digest=pattern_registry_digest,
        deterministic=True,
        supports_relationships=False,
    )


class _ExactPatternProducer:
    def __init__(self, pattern_registry_digest: str) -> None:
        self.descriptor = _descriptor(
            "m3.exact-rule",
            input_fields=("oracle_text",),
            pattern_registry_digest=pattern_registry_digest,
        )

    def produce(
        self,
        record: StructuralCardRecordV1,
        context: ProducerContextV1,
    ) -> ProducerResultV1:
        if context.pattern_registry is None or record.oracle_text is None:
            return ProducerResultV1.no_match()
        registry = EffectivePatternRegistryV1.from_wire(
            context.pattern_registry.to_wire()
        )
        rule = next(
            item for item in registry.rules if item.pattern_id == "m3.exact-clause.draw"
        )
        if not registry.matches_exact_text(
            rule.pattern_id,
            rule.pattern_version,
            record.oracle_text,
            face_index=None,
        ):
            return ProducerResultV1.no_match()
        source = _source_ref(record, context.source_lock_digest)
        candidate = RequirementV1.create(
            source=source,
            family=rule.output_template.family,
            kind=rule.output_template.kind,
            parameters=rule.output_template.parameters,
            evidence=(
                StructuralFieldEvidenceV1(
                    source,
                    "oracle_text",
                    None,
                    rule.match_text,
                ),
            ),
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
        return ProducerResultV1.emitted((candidate,))


class _DoubleDrawProducer:
    descriptor = _descriptor(
        "m3.fixture-double",
        input_fields=("oracle_text",),
    )

    def produce(
        self,
        record: StructuralCardRecordV1,
        context: ProducerContextV1,
    ) -> ProducerResultV1:
        if record.name != "Golden Double":
            return ProducerResultV1.no_match()
        return ProducerResultV1.emitted(
            (
                _draw_candidate(record, context, self.descriptor, 2, "Draw two cards."),
                _draw_candidate(record, context, self.descriptor, 1, "Draw one card."),
            )
        )


class _FaceProducer:
    descriptor = _descriptor(
        "m3.fixture-face",
        input_fields=("faces",),
    )

    def produce(
        self,
        record: StructuralCardRecordV1,
        context: ProducerContextV1,
    ) -> ProducerResultV1:
        if record.faces is None:
            return ProducerResultV1.no_match()
        candidates = []
        for face in record.faces:
            if face.oracle_text == "Draw two cards.":
                candidates.append(
                    _draw_candidate(
                        record,
                        context,
                        self.descriptor,
                        2,
                        face.oracle_text,
                        face.face_index,
                    )
                )
            elif face.oracle_text == "Draw one card.":
                candidates.append(
                    _draw_candidate(
                        record,
                        context,
                        self.descriptor,
                        1,
                        face.oracle_text,
                        face.face_index,
                    )
                )
        if not candidates:
            return ProducerResultV1.no_match()
        return ProducerResultV1.emitted(tuple(candidates))


class _UnsupportedProducer:
    descriptor = _descriptor(
        "m3.fixture-unsupported",
        input_fields=("layout", "oracle_text"),
    )

    def produce(
        self,
        record: StructuralCardRecordV1,
        context: ProducerContextV1,
    ) -> ProducerResultV1:
        if record.name == "Golden Unsupported":
            return ProducerResultV1.unsupported_shape("fixture unsupported shape")
        return ProducerResultV1.no_match()


class _ConflictProducer:
    descriptor = _descriptor(
        "m3.fixture-conflict",
        input_fields=("oracle_text",),
    )

    def produce(
        self,
        record: StructuralCardRecordV1,
        context: ProducerContextV1,
    ) -> ProducerResultV1:
        if record.name != "Golden No Match":
            return ProducerResultV1.no_match()
        return ProducerResultV1.emitted(
            (_draw_candidate(record, context, self.descriptor, 1, "No matching rule."),)
        )


class _RaisingProducer:
    descriptor = _descriptor(
        "m3.fixture-raising",
        input_fields=("oracle_text",),
    )

    def produce(
        self,
        record: StructuralCardRecordV1,
        context: ProducerContextV1,
    ) -> ProducerResultV1:
        raise RuntimeError("fixture producer failure")


class _InvalidProducer:
    descriptor = _descriptor(
        "m3.fixture-invalid",
        input_fields=("oracle_text",),
    )

    def produce(
        self,
        record: StructuralCardRecordV1,
        context: ProducerContextV1,
    ) -> ProducerResultV1:
        if record.name != "Golden Unsupported":
            return ProducerResultV1.no_match()
        wrong_source = SourceRecordRefV1(
            record_schema=StructuralCardRecordV1.SCHEMA,
            source_lock_digest=context.source_lock_digest,
            oracle_id="55555555-5555-4555-8555-555555555555",
            source_card_id="55555555-5555-4555-8555-555555555556",
            source_record_sha256="6" * 64,
        )
        candidate = RequirementV1.create(
            source=wrong_source,
            family=RequirementFamilyV1.EFFECT,
            kind=RequirementKindV1.DRAW_CARDS,
            parameters=DrawCardsParametersV1(
                _entity(), QuantityV1(QuantityModeV1.EXACT, 1)
            ),
            evidence=(
                StructuralFieldEvidenceV1(
                    wrong_source,
                    "oracle_text",
                    None,
                    "Choose an unsupported shape.",
                ),
            ),
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
        return ProducerResultV1.emitted((candidate,))


def _pattern_registry() -> EffectivePatternRegistryV1:
    return EffectivePatternRegistryV1.from_wire(
        json.loads(PATTERN_REGISTRY_PATH.read_bytes())
    )


def _producers(
    pattern_registry: EffectivePatternRegistryV1,
    variant: str = "base",
) -> tuple[CandidateProducerV1, ...]:
    if variant == "exception":
        return (_RaisingProducer(),)
    if variant == "invalid":
        return (_InvalidProducer(),)
    values: list[CandidateProducerV1] = [
        _FaceProducer(),
        _UnsupportedProducer(),
        _ExactPatternProducer(pattern_registry.digest()),
        _DoubleDrawProducer(),
    ]
    if variant == "conflict":
        values.append(_ConflictProducer())
    return tuple(values)


def _negative_authority_input(
    records: tuple[StructuralCardRecordV1, ...],
    source_lock_digest: str,
) -> NegativeAuthorityInputV1:
    document = json.loads(NEGATIVE_AUTHORITY_PATH.read_bytes())
    scope = NegativeAuthorityScopeV1(tuple(document["scope"]["source_fields"]))
    reference = NegativeReviewAuthorityRefV1.from_wire(
        {
            "authority_id": document["authority_id"],
            "authority_version": document["authority_version"],
            "record_id": document["record_id"],
            "record_sha256": document["record_sha256"],
            "scope_digest": negative_authority_scope_digest(scope),
        }
    )
    source_record = next(
        record for record in records if record.name == "Golden No Match"
    )
    return NegativeAuthorityInputV1(
        path=NEGATIVE_AUTHORITY_PATH,
        reference=reference,
        source=_source_ref(source_record, source_lock_digest),
    )


def _build(
    tmp_path: Path,
    *,
    variant: str = "base",
    with_negative_authority: bool = False,
):
    structural_root, source_lock_path, records = _write_structural_fixture(
        tmp_path / "structural"
    )
    source_lock_digest = _source_lock().digest()
    pattern_registry = _pattern_registry()
    producers = _producers(pattern_registry, variant)
    registry = ProducerRegistryV1.build([producer.descriptor for producer in producers])
    authority = (
        _negative_authority_input(records, source_lock_digest)
        if with_negative_authority
        else None
    )
    result = build_reference_m3(
        structural_root,
        registry,
        pattern_registry,
        tmp_path / "out",
        negative_authority=authority,
        producer_implementations=producers,
        source_lock_path=source_lock_path,
    )
    return result, records


def _by_name(
    records: tuple[CardAnalysisRecordV1, ...], name: str
) -> CardAnalysisRecordV1:
    return next(record for record in records if record.source.oracle_id == name)


def _record_for_name(result, name: str, structural_records):
    source = next(record for record in structural_records if record.name == name)
    return result.record_for(
        card_source_key(_source_ref(source, result.source_lock_digest))
    )


def _relative_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def test_reference_build_emits_one_record_per_synthetic_m1_card(tmp_path: Path) -> None:
    result, structural_records = _build(tmp_path)

    assert result.manifest.record_count == 5
    assert result.identity_set == tuple(
        card_source_key(_source_ref(record, result.source_lock_digest))
        for record in structural_records
    )
    assert result.output_dir.joinpath("analysis-manifest.json").is_file()
    assert len(result.records) == 5
    assert len(result.traces) >= 5

    outcomes = {record.source.oracle_id: record.outcome for record in result.records}
    assert (
        outcomes[structural_records[0].oracle_id]
        is AnalysisOutcomeV1.REQUIREMENTS_PRODUCED
    )
    assert (
        outcomes[structural_records[1].oracle_id]
        is AnalysisOutcomeV1.REQUIREMENTS_PRODUCED
    )
    assert (
        outcomes[structural_records[2].oracle_id]
        is AnalysisOutcomeV1.REQUIREMENTS_PRODUCED
    )
    assert (
        outcomes[structural_records[3].oracle_id]
        is AnalysisOutcomeV1.UNRESOLVED_ANALYSIS
    )
    assert (
        outcomes[structural_records[4].oracle_id]
        is AnalysisOutcomeV1.UNRESOLVED_ANALYSIS
    )

    double = result.record_for(
        card_source_key(_source_ref(structural_records[1], result.source_lock_digest))
    )
    assert double.bundle is not None
    assert len(double.bundle.requirements) == 2


def test_no_match_without_negative_authority_is_unresolved(tmp_path: Path) -> None:
    result, structural_records = _build(tmp_path)
    card = result.record_for(
        card_source_key(_source_ref(structural_records[4], result.source_lock_digest))
    )
    assert card.outcome is AnalysisOutcomeV1.UNRESOLVED_ANALYSIS
    assert card.bundle is None
    assert card.no_requirements_basis is None


def test_valid_negative_authority_allows_no_requirements_applicable(
    tmp_path: Path,
) -> None:
    result, structural_records = _build(tmp_path, with_negative_authority=True)
    card = result.record_for(
        card_source_key(_source_ref(structural_records[4], result.source_lock_digest))
    )
    assert card.outcome is AnalysisOutcomeV1.NO_REQUIREMENTS_APPLICABLE
    assert card.bundle is None
    assert card.no_requirements_basis is not None


def test_negative_authority_conflict_is_unresolved(tmp_path: Path) -> None:
    result, structural_records = _build(
        tmp_path,
        variant="conflict",
        with_negative_authority=True,
    )
    card = result.record_for(
        card_source_key(_source_ref(structural_records[4], result.source_lock_digest))
    )
    assert card.outcome is AnalysisOutcomeV1.UNRESOLVED_ANALYSIS
    assert card.bundle is not None
    requirement_id = card.bundle.requirements[0].requirement_id
    assert any(
        event.candidate_requirement_id == requirement_id
        and event.disposition.value == "CANDIDATE_RETAINED"
        for event in result.traces
    )


def test_producer_exception_aborts_without_manifest(tmp_path: Path) -> None:
    with pytest.raises(AnalysisBuildError, match="PRODUCER_EXCEPTION"):
        _build(tmp_path, variant="exception")
    assert not (tmp_path / "out" / "analysis-manifest.json").exists()


def test_invalid_requirement_aborts_without_card_failure_record(tmp_path: Path) -> None:
    with pytest.raises(AnalysisBuildError, match="INVALID_REQUIREMENT"):
        _build(tmp_path, variant="invalid")
    assert not (tmp_path / "out" / "analysis-manifest.json").exists()


def test_build_has_no_authoritative_cache_or_resume_path(tmp_path: Path) -> None:
    first, _ = _build(tmp_path / "first")
    second, _ = _build(tmp_path / "second")

    assert _relative_bytes(first.output_dir) == _relative_bytes(second.output_dir)
    assert not any(
        path.name in {"cache", "resume"} for path in first.output_dir.rglob("*")
    )
    assert not any(
        path.name in {"cache", "resume"} for path in second.output_dir.rglob("*")
    )
