"""Task 6A test-harness report for independent semantic fixture review."""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any

from manafold_census.corpus.index import parse_source_record
from manafold_census.digest import measure_file
from manafold_census.models import SourceLock
from manafold_census.resources import project_data_root
from manafold_census.semantic.bundle import RequirementBundleV1
from manafold_census.semantic.evidence import (
    StructuralFaceEvidenceV1,
    StructuralFieldEvidenceV1,
    StructuralKeywordEvidenceV1,
    StructuralRecordEvidenceV1,
    evidence_to_wire,
)
from manafold_census.semantic.identity import (
    reviewed_claim_digest_for,
    reviewed_claim_payload_for,
)
from manafold_census.semantic.model import ReviewStatusV1
from manafold_census.semantic.validate import (
    validate_bundle_against_structural_record,
)
from manafold_census.structural.extract import parse_structural_source_record
from manafold_census.structural.model import StructuralCardRecordV1

REPOSITORY_ROOT = project_data_root()
FIXTURE_PATH = REPOSITORY_ROOT / "fixtures" / "semantic" / "representative-bundles.json"
SOURCE_LOCK_PATH = REPOSITORY_ROOT / "source-locks" / "scryfall-oracle-v1.json"
REVIEW_REPORT_PATH = (
    REPOSITORY_ROOT / "dist" / "m2-semantic-fixture-review" / "task6a-review.json"
)


class PinnedEvidenceBlocked(RuntimeError):
    """The committed pinned source bytes are unavailable for Task 6A review."""


def load_fixture_cases() -> list[dict[str, Any]]:
    if not FIXTURE_PATH.is_file():
        raise PinnedEvidenceBlocked(f"BLOCKED: missing fixture file {FIXTURE_PATH}")
    document = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    if not isinstance(document, list):
        raise ValueError("representative fixture wrapper must be an array")
    return document


def _load_source_lock() -> tuple[SourceLock, Path]:
    if not SOURCE_LOCK_PATH.is_file():
        raise PinnedEvidenceBlocked(f"BLOCKED: missing source lock {SOURCE_LOCK_PATH}")
    lock = SourceLock.from_wire(
        json.loads(SOURCE_LOCK_PATH.read_text(encoding="utf-8"))
    )
    if len(lock.artifacts) != 1:
        raise ValueError("Task 6A expects one pinned Oracle source artifact")
    artifact = lock.artifacts[0]
    source_path = (
        REPOSITORY_ROOT
        / ".cache"
        / "sources"
        / "scryfall"
        / (f"{artifact.source_id}.jsonl.gz")
    )
    if not source_path.is_file():
        raise PinnedEvidenceBlocked(
            f"BLOCKED: missing pinned source bytes {source_path}"
        )
    measurement = measure_file(source_path)
    if (
        measurement.sha256 != artifact.sha256
        or measurement.byte_length != artifact.byte_length
    ):
        raise PinnedEvidenceBlocked(
            f"BLOCKED: pinned source artifact mismatch {source_path}"
        )
    if (
        lock.digest()
        != "4767dccbb518b4009c235bb1ce531f509c0923ba0ebe190936c2dc2d14e2d4bd"
    ):
        raise PinnedEvidenceBlocked(
            "BLOCKED: source lock digest is not the M1 pinned lock"
        )
    return lock, source_path


def load_pinned_records(
    cases: list[dict[str, Any]],
) -> tuple[dict[str, StructuralCardRecordV1], str]:
    lock, source_path = _load_source_lock()
    references = []
    for case in cases:
        bundle = RequirementBundleV1.from_wire(case["bundle"])
        references.append(bundle.source)
        if bundle.source.source_lock_digest != lock.digest():
            raise ValueError("fixture source lock does not match the pinned lock")
    wanted = {reference.oracle_id for reference in references}
    records: dict[str, StructuralCardRecordV1] = {}
    with gzip.open(source_path, "rb") as stream:
        for line_number, raw_line in enumerate(stream, start=1):
            identity = parse_source_record(raw_line, line_number)
            if identity.oracle_id not in wanted:
                continue
            record = parse_structural_source_record(raw_line, line_number)
            if record.source_record_sha256 != identity.source_record_sha256:
                raise ValueError("structural record SHA does not match source line")
            records[record.oracle_id] = record
            if records.keys() >= wanted:
                break
    if records.keys() != wanted:
        raise PinnedEvidenceBlocked(
            "BLOCKED: one or more pinned fixture records are missing"
        )
    return records, lock.digest()


def _evidence_context(
    bundle: RequirementBundleV1, record: StructuralCardRecordV1
) -> list[dict[str, Any]]:
    context: list[dict[str, Any]] = []
    for requirement in bundle.requirements:
        for evidence in requirement.evidence:
            if isinstance(evidence, StructuralRecordEvidenceV1):
                context.append({"kind": evidence.kind.value, "field": "record"})
            elif isinstance(evidence, StructuralFaceEvidenceV1):
                face = record.faces[evidence.face_index]  # type: ignore[index]
                context.append(
                    {
                        "kind": evidence.kind.value,
                        "face_index": evidence.face_index,
                        "field": "face",
                        "value": face.to_wire(),
                    }
                )
            elif isinstance(evidence, StructuralFieldEvidenceV1):
                value: object
                if evidence.face_index is None:
                    value = getattr(record, evidence.field)
                else:
                    value = getattr(record.faces[evidence.face_index], evidence.field)  # type: ignore[index]
                context.append(
                    {
                        "kind": evidence.kind.value,
                        "field": evidence.field,
                        "face_index": evidence.face_index,
                        "value": value,
                        "fragment": evidence.fragment,
                    }
                )
            elif isinstance(evidence, StructuralKeywordEvidenceV1):
                context.append(
                    {
                        "kind": evidence.kind.value,
                        "field": "keywords",
                        "keyword_index": evidence.keyword_index,
                        "keyword_value": evidence.keyword_value,
                    }
                )
    return context


def build_review_report() -> list[dict[str, Any]]:
    cases = load_fixture_cases()
    records, source_lock_digest = load_pinned_records(cases)
    report: list[dict[str, Any]] = []
    for case in cases:
        bundle = RequirementBundleV1.from_wire(case["bundle"])
        record = records[bundle.source.oracle_id]
        validate_bundle_against_structural_record(bundle, record, source_lock_digest)
        requirements = []
        for requirement in bundle.requirements:
            if requirement.review.status not in (
                ReviewStatusV1.PROPOSED,
                ReviewStatusV1.IN_REVIEW,
            ):
                raise ValueError("Task 6A fixture contains a terminal review status")
            requirements.append(
                {
                    "requirement_id": requirement.requirement_id,
                    "candidate_reviewed_claim_digest": reviewed_claim_digest_for(
                        requirement
                    ),
                    "reviewed_claim_payload": reviewed_claim_payload_for(requirement),
                    "canonical_evidence": [
                        evidence_to_wire(item) for item in requirement.evidence
                    ],
                    "canonical_derivation_provenance": requirement.provenance.to_wire(),
                    "proposed_family": requirement.family.value,
                    "proposed_kind": requirement.kind.value,
                    "proposed_parameters": requirement.parameters.to_wire(),
                    "proposed_resolution": requirement.resolution.to_wire(),
                    "review_status": requirement.review.status.value,
                }
            )
        face_indexes = sorted(
            {
                evidence.face_index
                for requirement in bundle.requirements
                for evidence in requirement.evidence
                if isinstance(
                    evidence, StructuralFaceEvidenceV1 | StructuralFieldEvidenceV1
                )
                and evidence.face_index is not None
            }
        )
        report.append(
            {
                "case_id": case["case_id"],
                "card_name_for_reviewer": record.name,
                "oracle_id": record.oracle_id,
                "face_index": face_indexes,
                "relevant_exact_pinned_source_fields": _evidence_context(
                    bundle, record
                ),
                "requirements": requirements,
                "proposed_relationships": list(bundle.to_wire()["relationships"]),
                "review_status": "PROPOSED",
            }
        )
    return report


def write_review_report(path: str | Path = REVIEW_REPORT_PATH) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(build_review_report(), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    return output


if __name__ == "__main__":
    print(write_review_report())
