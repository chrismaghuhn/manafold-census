# M3 Exact-Field M1 Match Census Review

Date: 2026-09-14

## Frozen M1 authority

```text
SOURCE_LOCK_DIGEST              = 4767dccbb518b4009c235bb1ce531f509c0923ba0ebe190936c2dc2d14e2d4bd
M1_STRUCTURAL_MANIFEST_SHA256   = bdc74ec944798a8c1dd7627dae55a795c6fb72d3bbe067d2f2e50412c7155f2b
M1_STRUCTURAL_AGGREGATE_DIGEST  = eb215ca6c904c26baa2d8f0a63928e8c9acab5bb9ea9493eacebcdab2fbb86bb
M1_RECORD_COUNT                  = 38740
M1_UNIQUE_SOURCE_IDENTITIES      = 38740
M1_DUPLICATES                    = 0
```

## Exact predicate

```text
field         = oracle_text
operator      = EXACT_FIELD_TEXT
normalization = NONE
value         = "Draw two cards."
face_index    = null
```

The scan read all sixteen persisted structural shards and required canonical JSONL, shard placement, complete record count, unique identities, and zero duplicates. It did not inspect faces and did not apply trimming, case folding, Unicode normalization, regex, substring matching, or punctuation rewriting.

## Match census

The complete match table is persisted in `2026-09-14-m3-draw-two-exact-field-match-census.json`.

| oracle_id | name | layout | type_line | oracle_text | source_record_sha256 |
| --- | --- | --- | --- | --- | --- |
| `273b339c-964b-4a18-8eb5-ceb8abcdfd9e` | Divination | normal | Sorcery | `Draw two cards.` | `d8441fb753bfb007b9ef632f921cd135f84ebdf6fd671cd2499dedeefb1f1fe0` |
| `62ddc5ae-ced9-4319-854c-1a114c6afc3f` | Counsel of the Soratami | normal | Sorcery | `Draw two cards.` | `04e489d4f5c2d1d5872d0e04b87e332971f9940ad049419de9d4eee750e3f501` |
| `6365aba1-78d3-416c-89cd-9449578eedbf` | Touch of Brilliance | normal | Sorcery | `Draw two cards.` | `9612ca8c0355c1601d2862f443e23b80bdca1d55abe7b23a315f7f2ba4874e86` |
| `7bff8d4a-1c7d-48b8-b3e3-737dd6f01823` | Quick Study | normal | Instant | `Draw two cards.` | `73a67e164e127aeb0babf7626405a20edd9ebb94ceb560be5044b090b7e5c7c0` |
| `ff568a29-e31a-4bc3-b8a3-8fa56f91d52d` | Weave Fate | normal | Instant | `Draw two cards.` | `6d65eadc22b4c041fd81cdfda4325280fd29de53ddf7f2eb91462750e7366729` |

All five matches have normal layout and the complete parent Oracle field exactly equal to the proposed value. This is finite predicate evidence only; it does not approve semantic reuse or card certification.

## Reproduction

```text
RUN_A_SCANNED       = 38740
RUN_B_SCANNED       = 38740
RUN_A_MATCH_COUNT   = 5
RUN_B_MATCH_COUNT   = 5
RUN_A_SHA256        = 6795a7bbd1e9340589a0b182d129c8ad67dd8fdf376dd5a6935b6a2b9c274d89
RUN_B_SHA256        = 6795a7bbd1e9340589a0b182d129c8ad67dd8fdf376dd5a6935b6a2b9c274d89
CANONICAL_BYTES_EQUAL = YES
```

The producer and M3 authoritative build were not executed over these records. This is a read-only M1 predicate census only.

```text
MATCH_CENSUS_COMPLETE = PASS
MATCH_CENSUS_REPRODUCTION = PASS

MAINTAINER_SEMANTIC_DECISION = PENDING
REPLACEMENT_PATTERN_APPROVED = NO
REPLACEMENT_PATTERN_ELIGIBLE = NO

M1_MATCH_CENSUS_STARTED = YES
GLOBAL_M3_EXTRACTION_STARTED = NO
TASK_11_RUN_A = NOT_RUN
TASK_11_RUN_B = NOT_RUN
TASK_11_RETRY_AUTHORIZED = NO
```
