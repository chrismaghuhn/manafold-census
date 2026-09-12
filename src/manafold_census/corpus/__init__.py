"""Deterministic source-record inventory construction for Census."""

from .build import (
    BuildResult,
    build_corpus,
    build_pinned_corpus,
    run_synthetic_reproduction,
)
from .check import validate_corpus_output
from .index import (
    CorpusIndexError,
    IndexSummary,
    RecordIndexEntry,
    ShardSummary,
    aggregate_index_digest,
    build_record_index,
    inspect_record_index,
    iter_source_records,
)
from .manifest import IndexManifestError, IndexRecordManifest

__all__ = [
    "BuildResult",
    "CorpusIndexError",
    "IndexSummary",
    "IndexManifestError",
    "IndexRecordManifest",
    "RecordIndexEntry",
    "ShardSummary",
    "aggregate_index_digest",
    "build_corpus",
    "build_pinned_corpus",
    "build_record_index",
    "inspect_record_index",
    "iter_source_records",
    "run_synthetic_reproduction",
    "validate_corpus_output",
]
