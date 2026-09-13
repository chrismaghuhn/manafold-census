from __future__ import annotations

import hashlib
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
    NegativeReviewAuthorityRefV1,
)
from manafold_census.analysis.patterns import (
    EffectivePatternRegistryV1,
    PatternSourceFieldV1,
    pattern_rule_digest_for,
)
from manafold_census.analysis.producer import (
    CandidateProducerV1,
    ProducerContextV1,
    ProducerDescriptorV1,
    ProducerFindingV1,
    ProducerResultV1,
)
from manafold_census.analysis.registry import ProducerRegistryV1
from manafold_census.analysis.trace import (
    NegativeAuthorityTraceDispositionV1,
    NegativeAuthorityTraceEventV1,
)
from manafold_census.analysis.validate import (
    AnalysisClosureError,
    validate_analysis_closure,
)
from manafold_census.canonical import canonical_json_bytes
from manafold_census.digest import sha256_bytes
from manafold_census.models import (
    ArtifactManifest,
    DatasetManifest,
    SourceLock,
    StudySpec,
)
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
from manafold_census.structural.build import (
    SHARD_COUNT,
    STRUCTURAL_ARTIFACT_ID,
    STRUCTURAL_ARTIFACT_KIND,
    STRUCTURAL_DATASET_ID,
    STRUCTURAL_DATASET_VERSION,
    STRUCTURAL_NORMALIZATION_PROFILE,
    STRUCTURAL_OPERATION,
    STRUCTURAL_STUDY_ID,
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
    source_lock = _source_lock()
    dataset = DatasetManifest(
        STRUCTURAL_DATASET_ID,
        STRUCTURAL_DATASET_VERSION,
        source_lock.digest(),
        STRUCTURAL_NORMALIZATION_PROFILE,
        summary.record_count,
    )
    study = StudySpec(
        STRUCTURAL_STUDY_ID,
        (STRUCTURAL_DATASET_ID,),
        STRUCTURAL_OPERATION,
        {"shard_count": SHARD_COUNT, "source_lock_digest": source_lock.digest()},
    )
    manifest_bytes = canonical_json_bytes(manifest.to_wire())
    artifact = ArtifactManifest(
        STRUCTURAL_ARTIFACT_ID,
        STRUCTURAL_ARTIFACT_KIND,
        study.digest(),
        sha256_bytes(manifest_bytes),
        len(manifest_bytes),
    )
    for name, document in (
        ("dataset-manifest.json", dataset.to_wire()),
        ("study-spec.json", study.to_wire()),
        ("artifact-manifest.json", artifact.to_wire()),
    ):
        (root / name).write_bytes(canonical_json_bytes(document))
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
    resolution: ResolutionV1 | None = None,
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
        resolution=(
            ResolutionV1(ResolutionStateV1.COMPLETE, ResolutionReasonV1.NONE, ())
            if resolution is None
            else resolution
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
        return ProducerResultV1.emitted(
            (candidate,),
            findings=(
                ProducerFindingV1(
                    candidate_index=0,
                    pattern_id=rule.pattern_id,
                    pattern_version=rule.pattern_version,
                    pattern_digest=pattern_rule_digest_for(rule),
                    source_field=PatternSourceFieldV1.ORACLE_TEXT,
                    face_index=None,
                    exact_fragment=rule.match_text,
                    clause_ordinal=0,
                    parser_span=None,
                ),
            ),
        )


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


class _MixedUnsupportedProducer:
    descriptor = _descriptor(
        "m3.fixture-mixed-unsupported",
        input_fields=("layout", "oracle_text"),
    )

    def produce(
        self,
        record: StructuralCardRecordV1,
        context: ProducerContextV1,
    ) -> ProducerResultV1:
        if record.name == "Golden No Match":
            return ProducerResultV1.unsupported_shape("fixture mixed unsupported")
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


class _DisputedProducer:
    descriptor = _descriptor(
        "m3.fixture-disputed",
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
            (
                _draw_candidate(
                    record,
                    context,
                    self.descriptor,
                    1,
                    "No matching rule.",
                    resolution=ResolutionV1(
                        ResolutionStateV1.PARTIAL,
                        ResolutionReasonV1.INSUFFICIENT_EVIDENCE,
                        ("/parameters",),
                    ),
                ),
            )
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
    if variant == "mixed":
        values.extend((_ConflictProducer(), _MixedUnsupportedProducer()))
    if variant == "disputed":
        values.extend((_ConflictProducer(), _DisputedProducer()))
    return tuple(values)


def _invoke_build(
    structural_root: Path,
    source_lock_path: Path,
    output_path: Path,
    *,
    variant: str = "base",
    authority: NegativeAuthorityInputV1 | None = None,
):
    pattern_registry = _pattern_registry()
    producers = _producers(pattern_registry, variant)
    registry = ProducerRegistryV1.build([producer.descriptor for producer in producers])
    return build_reference_m3(
        structural_root,
        registry,
        pattern_registry,
        output_path,
        negative_authority=authority,
        producer_implementations=producers,
        source_lock_path=source_lock_path,
    )


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
    authority = (
        _negative_authority_input(records, source_lock_digest)
        if with_negative_authority
        else None
    )
    result = _invoke_build(
        structural_root,
        source_lock_path,
        tmp_path / "out",
        variant=variant,
        authority=authority,
    )
    return result, records


def _relative_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def test_valid_wrong_source_lock_is_rejected_before_publication(tmp_path: Path) -> None:
    structural_root, source_lock_path, _ = _write_structural_fixture(
        tmp_path / "structural"
    )
    wrong_lock_path = tmp_path / "wrong-source-lock.json"
    wrong_lock = json.loads(source_lock_path.read_bytes())
    wrong_lock["artifacts"][0]["sha256"] = "0" * 64
    wrong_lock_path.write_bytes(canonical_json_bytes(wrong_lock))

    with pytest.raises(AnalysisBuildError, match="INVALID_M1_INPUT"):
        _invoke_build(structural_root, wrong_lock_path, tmp_path / "out")
    assert not (tmp_path / "out" / "analysis-manifest.json").exists()


@pytest.mark.parametrize("manifest_name", ["dataset", "study", "artifact"])
def test_m1_lifecycle_binding_failures_are_rejected(
    tmp_path: Path,
    manifest_name: str,
) -> None:
    structural_root, source_lock_path, _ = _write_structural_fixture(
        tmp_path / "structural"
    )
    path = (
        structural_root
        / {
            "dataset": "dataset-manifest.json",
            "study": "study-spec.json",
            "artifact": "artifact-manifest.json",
        }[manifest_name]
    )
    document = json.loads(path.read_bytes())
    if manifest_name == "dataset":
        document["source_lock_digest"] = "f" * 64
    elif manifest_name == "study":
        document["parameters"]["source_lock_digest"] = "f" * 64
    else:
        document["content_sha256"] = "f" * 64
    path.write_bytes(canonical_json_bytes(document))

    with pytest.raises(AnalysisBuildError, match="INVALID_M1_INPUT"):
        _invoke_build(structural_root, source_lock_path, tmp_path / "out")
    assert not (tmp_path / "out" / "analysis-manifest.json").exists()


def test_exact_pattern_match_trace_preserves_pattern_provenance(
    tmp_path: Path,
) -> None:
    result, structural_records = _build(tmp_path)
    exact_source = _source_ref(structural_records[0], result.source_lock_digest)
    event = next(
        item
        for item in result.traces
        if item.card_source_key == card_source_key(exact_source)
        and item.producer_id == "m3.exact-rule"
        and item.candidate_requirement_id is not None
    )
    rule = next(
        item
        for item in _pattern_registry().rules
        if item.pattern_id == "m3.exact-clause.draw"
    )
    assert event.pattern_id == rule.pattern_id
    assert event.pattern_version == rule.pattern_version
    assert event.pattern_digest == pattern_rule_digest_for(rule)
    assert event.source_field is PatternSourceFieldV1.ORACLE_TEXT
    assert event.exact_fragment == "Draw two cards."


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
    authority = _negative_authority_input(structural_records, result.source_lock_digest)
    events = [
        event
        for event in result.traces
        if isinstance(event, NegativeAuthorityTraceEventV1)
    ]
    assert len(events) == 1
    assert events[0].authority == authority.reference
    assert (
        events[0].disposition
        is NegativeAuthorityTraceDispositionV1.NEGATIVE_AUTHORITY_APPLIED
    )


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
        getattr(event, "candidate_requirement_id", None) == requirement_id
        and getattr(event, "disposition", None).value == "CANDIDATE_RETAINED"
        for event in result.traces
    )
    authority_events = [
        event
        for event in result.traces
        if isinstance(event, NegativeAuthorityTraceEventV1)
    ]
    assert len(authority_events) == 1
    assert (
        authority_events[0].disposition
        is NegativeAuthorityTraceDispositionV1.NEGATIVE_AUTHORITY_CONFLICT
    )


def test_mixed_negative_authority_and_unsupported_emits_both_trace_causes(
    tmp_path: Path,
) -> None:
    result, structural_records = _build(
        tmp_path,
        variant="mixed",
        with_negative_authority=True,
    )
    card = result.record_for(
        card_source_key(_source_ref(structural_records[4], result.source_lock_digest))
    )
    assert card.outcome is AnalysisOutcomeV1.UNRESOLVED_ANALYSIS
    assert card.bundle is not None
    assert any(
        isinstance(event, NegativeAuthorityTraceEventV1)
        and event.disposition
        is NegativeAuthorityTraceDispositionV1.NEGATIVE_AUTHORITY_CONFLICT
        for event in result.traces
    )
    assert any(
        event.card_source_key == card_source_key(card.source)
        and getattr(event, "producer_id", None) == "m3.fixture-conflict"
        and getattr(event, "candidate_requirement_id", None) is not None
        for event in result.traces
    )
    assert any(
        event.card_source_key == card_source_key(card.source)
        and getattr(event, "producer_id", None) == "m3.fixture-mixed-unsupported"
        and getattr(event, "disposition", None).value == "PRODUCER_UNSUPPORTED_SHAPE"
        for event in result.traces
    )


def test_negative_authority_and_disputed_candidates_preserve_both_causes(
    tmp_path: Path,
) -> None:
    result, structural_records = _build(
        tmp_path,
        variant="disputed",
        with_negative_authority=True,
    )
    card = result.record_for(
        card_source_key(_source_ref(structural_records[4], result.source_lock_digest))
    )
    assert card.outcome is AnalysisOutcomeV1.UNRESOLVED_ANALYSIS
    assert card.bundle is None
    assert any(
        isinstance(event, NegativeAuthorityTraceEventV1)
        and event.disposition
        is NegativeAuthorityTraceDispositionV1.NEGATIVE_AUTHORITY_CONFLICT
        for event in result.traces
    )
    assert {
        getattr(event, "producer_id", None)
        for event in result.traces
        if getattr(event, "disposition", None).value == "DISPUTED_IDENTITY_OMITTED"
    } == {"m3.fixture-conflict", "m3.fixture-disputed"}


def test_persisted_negative_authority_trace_unknown_source_fails_closed(
    tmp_path: Path,
) -> None:
    structural_root, source_lock_path, records = _write_structural_fixture(
        tmp_path / "structural"
    )
    source_lock_digest = _source_lock().digest()
    authority = _negative_authority_input(records, source_lock_digest)
    result = _invoke_build(
        structural_root,
        source_lock_path,
        tmp_path / "out",
        authority=authority,
    )
    trace_path = result.output_dir / "trace" / "4.jsonl"
    documents = [json.loads(line) for line in trace_path.read_bytes().splitlines()]
    authority_document = next(
        document for document in documents if "authority" in document
    )
    authority_document["card_source_key"][1] = "44444444-4444-4444-8444-444444444443"
    trace_path.write_bytes(
        b"".join(canonical_json_bytes(document) + b"\n" for document in documents)
    )
    with pytest.raises(AnalysisClosureError, match="unknown source"):
        validate_analysis_closure(structural_root, result.output_dir, source_lock_path)


def test_persisted_negative_authority_trace_must_match_card_outcome(
    tmp_path: Path,
) -> None:
    structural_root, source_lock_path, records = _write_structural_fixture(
        tmp_path / "structural"
    )
    source_lock_digest = _source_lock().digest()
    authority = _negative_authority_input(records, source_lock_digest)
    result = _invoke_build(
        structural_root,
        source_lock_path,
        tmp_path / "out",
        variant="conflict",
        authority=authority,
    )
    trace_path = result.output_dir / "trace" / "4.jsonl"
    documents = [json.loads(line) for line in trace_path.read_bytes().splitlines()]
    authority_document = next(
        document for document in documents if "authority" in document
    )
    authority_document["disposition"] = "NEGATIVE_AUTHORITY_APPLIED"
    trace_path.write_bytes(
        b"".join(canonical_json_bytes(document) + b"\n" for document in documents)
    )
    manifest_path = result.output_dir / "analysis-manifest.json"
    manifest_document = json.loads(manifest_path.read_bytes())
    descriptor = manifest_document["trace_shards"][SHARD_NAMES.index("4")]
    descriptor["sha256"] = hashlib.sha256(trace_path.read_bytes()).hexdigest()
    descriptor["byte_length"] = trace_path.stat().st_size
    manifest_path.write_bytes(canonical_json_bytes(manifest_document))
    with pytest.raises(AnalysisClosureError, match="applied trace"):
        validate_analysis_closure(structural_root, result.output_dir, source_lock_path)


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
