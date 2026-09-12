# Architecture

This repository is independent of Manafold and has no privileged relationship
with any MTG engine. Other projects may consume Census outputs later, but they
remain responsible for their own validation and acceptance.

## Lifecycle

```text
SourceArtifact → SourceLock → DatasetManifest → StudySpec → ArtifactManifest
```

The conceptual boundaries are:

- A `SourceArtifact` records the provenance and exact digest of immutable input
  bytes. Its locator does not guarantee byte identity.
- A `SourceLock` records the exact ordered source set needed for a build.
  `SourceLock.build()` is the normalizing construction boundary; persisted
  `from_wire()` input must already be sorted and is rejected otherwise.
- A `DatasetManifest` identifies a reproducible logical data product. It is not
  a research question or a semantic-support claim.
- A `StudySpec` identifies a deterministic operation and restricted data
  parameters applied to one or more datasets. Its restricted JSON parameters
  are recursively copied into immutable values. It contains no executable
  code.
- An `ArtifactManifest` records the study provenance and exact bytes of an
  output. It does not certify semantic authority, support, or correctness.

Therefore:

```text
Dataset != Study
Source bytes != normalized records
Generated result != semantic authority
```

Canonical semantic JSON accepts only null, booleans, signed 64-bit integers,
strings, arrays, and objects with string keys. It is UTF-8, whitespace-free,
sorted by object keys, and contains no timestamp, randomness, host path, or
implicit Python serialization. Raw external bytes and normalized semantic
strings are separate layers. `SourceArtifact` measurements hash and count the
same opened file stream. Each public structure has one normative schema; the
source-lock schema references the source-artifact schema rather than copying
it.

Task 01 source flow
-------------------

The first real-data slice is deliberately source-bounded:

```text
Scryfall /bulk-data (oracle_cards)
  -> exact compressed gzip bytes
  -> generic SourceArtifact / SourceLock
  -> gzip JSONL record boundaries
  -> four-field SOURCE_FACT inventory
  -> oracle_id sort
  -> records/0.jsonl ... records/f.jsonl
```

The compressed download is the source identity. Each inventory record hashes
the exact decompressed JSONL line bytes, including its line framing; the
canonical generated JSONL line is a separate representation. The 16 shard
files are generated and ignored. `source-refresh` may place a new snapshot in
the content-addressed cache and write a proposed lock, while
`source-fetch-pinned` resolves only the committed lock's locator and expected
digest/length. These operations remain separate so multiple snapshots can
coexist safely.

The multi-file index has a small `OracleRecordIndexManifestV1` containing all
16 relative shard paths, byte digests, lengths, and record counts plus the
aggregate index digest. The existing `ArtifactManifestV1` binds the exact
canonical bytes of that aggregate manifest in `content_sha256` and
`byte_length`; it is not repurposed to make an aggregate digest look like the
SHA-256 of the shard bytes.

The source and corpus packages have separate ownership. Task 01 does not
inspect Oracle text, normalize faces, infer types or abilities, assign
capabilities, cite rules, call an LLM, or depend on Manafold. A reported 100%
coverage value means every valid record in the exact pinned Scryfall
`oracle_cards` snapshot was indexed exactly once.

Task 00's foundation and Task 01's synthetic tests remain offline. Live
discovery/acquisition is an explicit maintainer operation, not part of normal
CI or `just check`.
