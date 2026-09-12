"""Deterministic source-record inventory construction for Census."""

from .build import (
    BuildResult,
    build_corpus,
    build_pinned_corpus,
    run_synthetic_reproduction,
    validate_corpus_output,
)
from .index import (
    CorpusIndexError,
    IndexSummary,
    RecordIndexEntry,
    ShardSummary,
    build_record_index,
    inspect_record_index,
    iter_source_records,
)

__all__ = [
    "BuildResult",
    "CorpusIndexError",
    "IndexSummary",
    "RecordIndexEntry",
    "ShardSummary",
    "build_corpus",
    "build_pinned_corpus",
    "build_record_index",
    "inspect_record_index",
    "iter_source_records",
    "run_synthetic_reproduction",
    "validate_corpus_output",
]
