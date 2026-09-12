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
- A `DatasetManifest` identifies a reproducible logical data product. It is not
  a research question or a semantic-support claim.
- A `StudySpec` identifies a deterministic operation and restricted data
  parameters applied to one or more datasets. It contains no executable code.
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
strings are separate layers.

Task 00 uses only a local synthetic fixture. It does not implement MTG
acquisition, parsing, rules, capability classification, interaction
generation, review, export, databases, or accelerators.
