# Global Oracle Corpus Task 01

## Goal

Create an independent, source-bounded inventory of every valid record in one
exactly pinned Scryfall `oracle_cards` bulk snapshot. The output is source
provenance only; Task 01 does not infer card semantics or capabilities.

## Observed source contract

The live discovery response on 2026-09-12 selected exactly one bulk entry with
`type=oracle_cards`. It advertised `jsonl_download_uri`, an upstream UUID, an
`updated_at` value, and `compressed_size`. The advertised payload is gzip
compressed JSONL. The compressed file is the `SourceArtifact` identity; each
decompressed JSONL line, including its exact line-framing bytes, is the input
for `source_record_sha256`.

## Boundaries and data flow

`source` owns discovery, HTTPS streaming, temporary-file promotion, the
content-addressed cache, and the existing generic `SourceArtifact`/`SourceLock`
contracts.
`corpus` owns gzip/JSONL record validation, the four-field source inventory,
sorting, 16-shard writing, aggregate index identity, and generated manifests.
The source cache is ignored; only the acquisition specification, current
source lock, code, tests, small schemas/configuration, and documentation are
committed. Live refresh writes a proposed lock; pinned fetch never rewrites
the committed lock.

The committed lock's `source_id` is provenance only and is not a cache key.
Refresh and pinned fetch both address the cache by the exact source SHA-256,
so a reused upstream bulk ID cannot conflate two snapshots.

The deterministic flow is:

```text
Scryfall /bulk-data
  -> oracle_cards metadata
  -> HTTPS stream to temporary .jsonl.gz
  -> one-pass compressed-byte measurement
  -> atomic SHA-256-addressed cache promotion
  -> SourceLock
  -> gzip -> JSONL -> validated four-field records
  -> oracle_id sort
  -> shards 0..f
  -> DatasetManifest + StudySpec + ArtifactManifest + report
```

Each output record contains only `oracle_id`, `source_card_id`, `name`, and
`source_record_sha256`. Oracle IDs are normalized to lowercase canonical UUID
text for sorting and sharding. Duplicate normalized Oracle IDs fail closed.

## Failure and reproducibility rules

Only HTTPS and the observed gzip JSONL representation are supported. Discovery
and download use explicit `User-Agent` and `Accept` headers, with no unbounded
retry loop. Existing cache bytes are reused only when the expected digest and
length match; a mismatched cache fails without mutation. Every generated
semantic JSON document is canonical JSON without a trailing newline. Every
non-empty shard is JSONL with LF separators and a final LF. All 16 shard names
are always present, including empty shards.

Offline tests use injected fake HTTP responses and temporary gzip sources.
Hosted CI keeps the existing Python 3.12 checks, adds an offline synthetic
corpus check, and installs a built wheel into a fresh non-editable virtual
environment outside the repository working directory.
