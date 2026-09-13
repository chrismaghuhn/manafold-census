# M3 Corpus Campaign Configuration

Date: 2026-09-14

This document freezes the narrow semantic configuration for a future Task-11 offline campaign. It is configuration evidence, not campaign output and not card certification.

```text
SOURCE_LOCK_DIGEST            = 4767dccbb518b4009c235bb1ce531f509c0923ba0ebe190936c2dc2d14e2d4bd
M1_STRUCTURAL_MANIFEST_SHA256 = bdc74ec944798a8c1dd7627dae55a795c6fb72d3bbe067d2f2e50412c7155f2b
M1_STRUCTURAL_AGGREGATE_DIGEST = eb215ca6c904c26baa2d8f0a63928e8c9acab5bb9ea9493eacebcdab2fbb86bb

PATTERN_REGISTRY_PATH  = config/analysis/m3-corpus-pattern-registry.v1.json
PATTERN_REGISTRY_DIGEST = a27effa3d7f5497fca0d9d2e3e3abb562037278b17cf7b17b0f54523d58e5eb1

PRODUCER_REGISTRY_PATH  = config/analysis/m3-corpus-producer-registry.v1.json
PRODUCER_REGISTRY_DIGEST = fca4a0d9318669a372ee1dcded22c55e1fd1fdff7dd470ecd0bbfa9c07be498f

PRODUCER_ID      = m3.registry-exact-pattern
PRODUCER_VERSION = 1
M3_BUILD_PROFILE = census.m3-reference.v1
NEGATIVE_AUTHORITY = NONE

ACTIVE_REVIEWED_PATTERN_COUNT = 1
ACTIVE_PATTERN = m3.corpus.exact-field.draw-two-cards@1
REJECTED_PATTERN_COUNT = 1
EXPECTED_EXACT_FIELD_M1_MATCH_COUNT = 5
```

The active rule is whole-field equality on parent `oracle_text` with `NONE` normalization and the exact value `Draw two cards.`. The rejected fragment rule remains present only as historical non-active registry evidence.

For any non-match without an explicit negative authority, the M3 semantic outcome remains:

```text
NONMATCH_WITHOUT_NEGATIVE_AUTHORITY
→ UNRESOLVED_ANALYSIS
```

This configuration does not claim that five cards are certified, fully understood, or globally semantically covered. Approval authorizes deterministic candidate reuse only; it does not certify cards or the engine. `NEGATIVE_AUTHORITY = NONE` means no card-level absence closure is supplied by this campaign configuration.

The final campaign commit digest is intentionally not included in this document, because this report is part of the committed evidence itself.
