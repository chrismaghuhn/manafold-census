
# CENSUS_02 Global Structural Card Census — Design Specification

Status: design approved; implementation not authorized.

~~~
CENSUS_02_DESIGN_REVIEW          = APPROVE
DESIGN_SPECIFICATION_AUTHORIZED  = YES
PRODUCTION_CODE_AUTHORIZED       = NO
M1_IMPLEMENTATION_AUTHORIZED     = NO
M2_AUTHORIZED                    = NO
~~~

This specification freezes the Task 02 structural contract before production
implementation begins. It defines a source-fact projection of the exact Task
01 corpus. It does not define Magic rules semantics, requirements,
capabilities, or authority.

## 1. Authority, baseline, and evidence

Task 02 is governed by roadmap Issue #2 and milestone Issue #4 in
chrismaghuhn/manafold-census.

The verified implementation baseline is:

~~~
BASE / origin/main = ed57a31af5ddfbf52fe5d791f35b31a7ac9934fd
PR #1              = MERGED
Issue #4           = OPEN
WORKTREE           = CLEAN before this specification was added
EXISTING TESTS     = 89 passed
~~~

Task 02 must use the committed Task 01 source lock without refreshing or
substituting the source:

~~~
source_lock_path    = source-locks/scryfall-oracle-v1.json
source_lock_digest  = 4767dccbb518b4009c235bb1ce531f509c0923ba0ebe190936c2dc2d14e2d4bd
source_id           = 27bf3214-1271-490b-bdfe-c0be6c23d02e
source_sha256       = 4d4b77fd2668f789ea97a855dd49e1e505322c56e09771d8d2ffd9f48681d3a0
source_byte_length  = 24601964
source_record_count = 38740
~~~

The shape inspection covered every record in the pinned compressed JSONL
source. The observations below are evidence for this contract version, not a
universal claim about future Scryfall snapshots.

## 2. Scope and non-goals

The M1 question is:

> What structural card information is explicitly present in the pinned source
> data?

The pipeline is:

~~~
exact pinned source bytes
    -> raw source record
    -> Task 01 identity projection
    -> StructuralCardRecordV1
    -> deterministic 16-shard JSONL index
    -> manifests, report, and provenance closure
~~~

The projection may copy source facts. It must not interpret them.

M1 must not implement or emit:

- ability, effect, target, event, zone, cost, mode, trigger, replacement, or
  continuous-effect interpretation;
- semantic parsing of Oracle text, keyword expansion, or mana-cost tokenization;
- mana-value calculation, payment possibilities, or targeting legality;
- Requirements, Capabilities, rules citations, semantic status ontologies, or
  engine support mappings;
- clustering, embeddings, LLM calls, search, deck parsing, or an Explorer;
- URI dereferencing, network calls during structural build/check, or a second
  dataset source;
- a database, Rust accelerator, or heavy data-processing dependency.

The raw pinned source remains the authority for facts outside this projection.

## 3. Structural record contract

The persisted card record has the fixed schema identifier:

~~~
census.structural-card.v1
~~~

Every property listed below is required in the wire object. A nullable value
means that the corresponding source property was absent. A present source
property with an empty value remains an empty value. The extractor must reject
an explicitly present JSON null for a retained source field because this
contract uses null exclusively to encode source absence.

The normative JSON Schema is:

~~~
schemas/structural-card.v1.schema.json
~~~

It must use JSON Schema Draft 2020-12, signed-64-bit bounds for persisted
integers, explicit nested definitions, and additionalProperties=false for the
record and its nested values.

### 3.1 StructuralCardRecordV1 wire fields

| Field | Wire type | Source rule |
| --- | --- | --- |
| schema | fixed string | Always census.structural-card.v1. |
| oracle_id | lowercase UUID string | Task 01 normalized identity. |
| source_card_id | lowercase UUID string | Task 01 normalized source card identity. |
| source_record_sha256 | lowercase SHA-256 string | SHA-256 of the exact decompressed source JSONL line, including framing bytes. |
| name | non-empty string | Exact Task 01 identity value. |
| layout | non-empty string | Exact source layout; no layout interpretation. |
| mana_cost | string or null | Exact source value or source absence. |
| type_line | string or null | Exact source value or source absence. |
| oracle_text | string or null | Exact source value or source absence. |
| colors | ordered string array or null | Exact source array and order, including []. |
| color_identity | ordered string array or null | Exact source array and order, including []. |
| color_indicator | ordered string array or null | Exact source array and order, including []. |
| keywords | ordered string array or null | Exact source array and order, including []; no keyword inference. |
| produced_mana | ordered string array or null | Exact source array and order, including []; no mana interpretation. |
| power | string or null | Exact source string; no formula or number parsing. |
| toughness | string or null | Exact source string; no formula or number parsing. |
| loyalty | string or null | Exact source string; no number parsing. |
| defense | string or null | Exact source string; no number parsing. |
| hand_modifier | string or null | Exact source string; no number parsing. |
| life_modifier | string or null | Exact source string; no number parsing. |
| attraction_lights | ordered signed-64-bit integer array or null | Exact source array and order, including []. |
| faces | ordered StructuralFaceV1 array or null | Null when source card_faces is absent; otherwise exact source order. |
| all_parts | ordered StructuralRelatedPartV1 array or null | Null when source all_parts is absent; otherwise exact source order. |

The fixed wire shape intentionally uses faces rather than copying the source
property name card_faces. This is a direct source-fact projection. It does not
imply transform, front/back, modal, adventure, split, or any other behavior.

Structural strings must be preserved exactly after JSON decoding. The
implementation must not strip, trim, case-fold, Unicode-normalize, replace
punctuation, normalize whitespace, or rewrite line breaks. It must preserve
array order and duplicate values. It must not convert numeric-looking strings
to integers.

### 3.2 StructuralFaceV1 wire fields

Each face object has exactly these required properties:

| Field | Wire type | Rule |
| --- | --- | --- |
| face_index | signed-64-bit integer, >= 0 | Census-owned zero-based source-array position. |
| name | non-empty string | Exact face-level source name. |
| mana_cost | string or null | Exact face-level source value or absence. |
| type_line | string or null | Exact face-level source value or absence. |
| oracle_text | string or null | Exact face-level source value or absence. |
| colors | ordered string array or null | Exact face-level source array and order, including []. |
| color_indicator | ordered string array or null | Exact face-level source array and order, including []. |
| power | string or null | Exact face-level source string or absence. |
| toughness | string or null | Exact face-level source string or absence. |
| loyalty | string or null | Exact face-level source string or absence. |
| defense | string or null | Exact face-level source string or absence. |

There is no parent-to-face or face-to-parent inheritance. A field is present
in a structural position only when it is present in that exact source object:

~~~
parent field present, face field absent -> parent value, face null
parent field absent, face field present -> parent null, face value
~~~

No face is merged, concatenated, reordered, or inferred from layout. If the
source contains card_faces: [], the build fails closed; it does not convert
that array to null.

### 3.3 StructuralRelatedPartV1 wire fields

Each related-part object has exactly these required string properties, copied
from the corresponding source relationship:

~~~
component
id
name
object
type_line
uri
~~~

id, object, and uri remain opaque source values in this nested contract. The
parent card's Task 01 identity remains the only identity projection used for
Task 01 parity.

The related-part URI has these explicit semantics:

~~~
uri = opaque SOURCE_FACT locator
uri != identity
uri != provenance authority
uri != dependency
~~~

The structural builder and validator must never dereference it. Relationship
facts are complete when copied from the pinned source bytes.

### 3.4 Absence and unknown-field policy

The wire contract requires every projected property, using null for source
absence:

~~~
source property absent        -> null
source property present as "" -> ""
source property present as [] -> []
source property present value -> exact value
~~~

The source extractor may ignore source fields outside the structural
projection. The persisted model, JSON Schema, and checker reject unknown wire
properties. This prevents output drift while keeping the pinned raw source
available for future projections.

## 4. Identity and provenance invariants

Task 01 owns source-record identity. M1 must call or reuse the Task 01
validation path rather than creating a second UUID, name, or record-hash rule.

For every one of the 38,740 records:

~~~
structural.oracle_id
    == task01.oracle_id

structural.source_card_id
    == task01.source_card_id

structural.name
    == task01.name

structural.source_record_sha256
    == task01.source_record_sha256
~~~

The required full-corpus gate is:

~~~
TASK01_RECORD_IDENTITY_PARITY = PASS
~~~

The provenance chain is:

~~~
exact pinned compressed source
    -> exact decompressed JSONL line bytes
    -> Task 01 RecordIndexEntry identity
    -> structural source-fact projection
    -> canonical structural JSONL bytes
~~~

The checker must reconstruct this chain from the pinned source and generated
shards. It must reject missing, extra, duplicate, mismatched, or unbound
identities. Structural provenance is SOURCE_FACT; it is not semantic
authority.

## 5. Immutability and canonical representation

The typed Python models must be frozen and slot-based where consistent with the
foundation. Internally, mutable arrays become immutable tuples or equivalent
defensive values. Nested values must be copied before construction.

Mutation attempts against these source-owned values must not change a record or
its wire digest:

~~~
colors
keywords
faces
face colors
all_parts
attraction_lights
~~~

to_wire may return fresh mutable JSON-compatible containers. Repeated to_wire
calls and record digests must remain byte-identical after callers mutate any
previously returned container.

Canonical JSON uses the existing project rules: UTF-8, sorted object keys,
whitespace-free encoding, no floating-point values, and signed-64-bit integer
limits. Structural JSONL uses:

~~~
canonical_json_bytes(record) + b"\n"
~~~

Every non-empty shard ends with LF, contains no BOM or trailing spaces, and is
validated byte-for-byte against its parsed record.

## 6. Extraction and build ownership

The new implementation belongs under:

~~~
src/manafold_census/structural/
~~~

The intended ownership boundaries are:

~~~
model.py     typed immutable card, face, and related-part models
extract.py   raw source record projection and source-shape validation
index.py     structural JSONL sharding, sorting, and shard inspection
manifest.py  structural aggregate manifest and digest closure
build.py     pinned build, dataset/study/artifact/report orchestration
check.py     fail-closed full-output validation and provenance reconstruction
__init__.py  narrow public exports
~~~

No production module may exceed 500 lines. The existing Task 00 foundation
models.py and Task 01 corpus contracts remain owned by their current packages.
M1 may reuse them; it must not redefine or alter their evidence.

The extractor must:

1. open only the exact content-addressed source selected by the committed
   lock;
2. stream the gzip JSONL input one line at a time;
3. hash and validate each raw line through the Task 01 identity path;
4. parse the source object and project only the fixed structural fields;
5. reject malformed or unsupported structural shapes rather than skipping them;
6. preserve parent fields, faces, and related parts in their source positions;
7. retain compact structural records for deterministic sorting; and
8. write no network-derived or machine-specific value into semantic output.

The normal structural build never refreshes Scryfall and never invokes a
network operation. The maintainer runs source-fetch-pinned separately when the
exact pinned cache is missing.

## 7. Deterministic structural index

The generated artifact is:

~~~
dist/structural/scryfall-oracle-v1/
  records/
    0.jsonl
    1.jsonl
    2.jsonl
    3.jsonl
    4.jsonl
    5.jsonl
    6.jsonl
    7.jsonl
    8.jsonl
    9.jsonl
    a.jsonl
    b.jsonl
    c.jsonl
    d.jsonl
    e.jsonl
    f.jsonl
  structural-index-manifest.json
  dataset-manifest.json
  study-spec.json
  artifact-manifest.json
  structural-report.json
~~~

The 38,740 generated structural records are ignored and must not be committed.
The output directory must start empty. The checker rejects missing, unexpected,
or extra files.

### 7.1 Sharding

M1 uses exactly the Task 01 partition principle:

~~~
shard = first lowercase hexadecimal character of normalized oracle_id
~~~

Every shard exists, including empty shards. Within each shard, oracle_id is
strictly ascending. The implementation must not use Python hashes, input
order, source ordinal, randomness, or filesystem order.

### 7.2 StructuralCardIndexManifestV1

M1 defines a new aggregate manifest and does not reuse the Task 01 index
manifest with a different meaning:

~~~
schema        = census.structural-card-index-manifest.v1
schema_path   = schemas/structural-card-index-manifest.v1.schema.json
digest domain = census.structural-card-index.v1
~~~

The normative manifest schema is JSON Schema Draft 2020-12 at the fixed
repository path above. It owns the exact manifest wire shape and rejects
unknown manifest properties.

The manifest contains exactly 16 ordered shard descriptors. Each descriptor
contains:

~~~
relative_path
sha256
byte_length
record_count
~~~

The checker requires the exact ordered paths records/0.jsonl through
records/f.jsonl, lowercase digest syntax, and non-negative signed-64-bit
lengths and counts. The aggregate digest is recomputed from the ordered
descriptor list using the structural digest domain.

The canonical bytes of structural-index-manifest.json are the bytes bound by
the existing ArtifactManifestV1 contract:

~~~
ArtifactManifest.content_sha256 = SHA256(exact manifest bytes)
ArtifactManifest.byte_length   = len(exact manifest bytes)
~~~

The structural aggregate digest must not be placed directly in
ArtifactManifest.content_sha256.

## 8. Dataset, study, artifact, and report identities

The generic foundation models remain the identity owners. M1 supplies these
fixed values:

~~~
dataset_id            = scryfall-oracle-structural-census
dataset_version       = 1.0.0
normalization_profile = scryfall-oracle-structural-v1

study_id              = scryfall-oracle-structural-build
operation             = scryfall-oracle-structural.v1
parameters            = {
  "shard_count": 16,
  "source_lock_digest": 4767dccbb518b4009c235bb1ce531f509c0923ba0ebe190936c2dc2d14e2d4bd
}

artifact_id           = scryfall-oracle-structural-index
artifact_kind         = census.structural-card-index.v1
~~~

The dataset record count is the recomputed structural record count. The study
contains no timestamp, wall-clock duration, hostname, machine path, or random
value.

structural-report.json is canonical and has this fixed report identity:

~~~
schema      = census.structural-card-report.v1
schema_path = schemas/structural-card-report.v1.schema.json
~~~

The normative report schema is JSON Schema Draft 2020-12. The report root has
exactly the fields listed below and uses additionalProperties=false. Every
count and byte length is a non-negative signed-64-bit integer. Every digest is
a lowercase SHA-256 string. task01_record_identity_parity is a boolean.

The complete report wire field set is:

~~~
schema
record_provenance = SOURCE_FACT
source_lock_digest
source_id
source_locator
source_artifact_sha256
source_artifact_byte_length
source_media_type

task01_record_identity_parity
task01_identity_count

structural_record_count
unique_oracle_id_count
duplicate_oracle_id_count
missing_oracle_id_count
extra_oracle_id_count

cards_with_faces
cards_without_faces
total_face_count
max_face_count
face_count_distribution
layout_counts

top_level_field_presence
face_field_presence

shard_count
shard_record_counts
structural_index_aggregate_digest
structural_index_manifest_sha256
structural_index_manifest_byte_length
dataset_manifest_digest
study_digest
artifact_manifest_digest
~~~

The report maps have these exact contracts:

~~~
face_count_distribution:
  object with decimal non-negative face-count strings as keys
  value = non-negative signed-64-bit card count
  key pattern = [1-9][0-9]*
  additionalProperties = count schema; no other map metadata

layout_counts:
  object with exact non-empty source layout strings as keys
  value = non-negative signed-64-bit record count
  property names are not normalized
  additionalProperties = count schema; no other map metadata

top_level_field_presence:
  fixed object with exactly these keys:
    mana_cost
    type_line
    oracle_text
    colors
    color_identity
    color_indicator
    keywords
    produced_mana
    power
    toughness
    loyalty
    defense
    hand_modifier
    life_modifier
    attraction_lights
    card_faces
    all_parts
  each value = non-negative signed-64-bit source-record count
  additionalProperties = false

face_field_presence:
  fixed object with exactly these keys:
    name
    mana_cost
    type_line
    oracle_text
    colors
    color_indicator
    power
    toughness
    loyalty
    defense
  each value = non-negative signed-64-bit source-face count
  additionalProperties = false

shard_record_counts:
  fixed object with exactly the keys 0, 1, 2, 3, 4, 5, 6, 7,
  8, 9, a, b, c, d, e, f
  each value = non-negative signed-64-bit record count
  additionalProperties = false
~~~

Face-count statistics have this exact population rule:

- face_count_distribution counts only source records where the card_faces
  property is present;
- each key is the decimal representation of len(card_faces) for one such
  source record;
- records where card_faces is absent do not contribute a 0 bucket;
- a present empty card_faces array is invalid, so key 0 must not occur in a
  valid report;
- total_face_count is the sum of len(card_faces) over records where
  card_faces is present; and
- max_face_count is the maximum len(card_faces) over records where card_faces
  is present, or 0 when no source record has card_faces.

Therefore, for the pinned source, the required values are:

~~~
cards_with_faces       = 3221
cards_without_faces    = 35519
total_face_count       = 6447
max_face_count         = 5
face_count_distribution = {"2": 3218, "3": 2, "5": 1}
~~~

Presence means source property membership. It does not mean non-null,
non-empty, truthy, or semantically populated. A present empty string or empty
array increments its field's presence count. A source property that is absent
does not. An explicitly present source JSON null fails extraction and is not
counted as absence.

The field-presence maps contain only these structural presence facts. They must
not contain categories such as draws cards, targets, activated ability, or any
other semantic classification. The report contains no timestamps, local paths,
runtime measurements, or hidden source downloads.

The checker recomputes every count and digest from source and output bytes. It
does not accept a report merely because its JSON Schema is valid.

## 9. Fail-closed validator

structural-check must validate:

- exact output file set and directory shape;
- canonical JSON bytes for every structural JSONL line and semantic document;
- structural-card schema and nested shape rules;
- raw string, array-order, nullability, and signed-integer rules;
- exact 16-shard assignment and strict per-shard Oracle-ID ordering;
- global Oracle-ID uniqueness and full source coverage;
- structural aggregate manifest closure;
- exact-byte ArtifactManifestV1 closure;
- dataset and study identity values;
- report closure against recomputed facts;
- committed source-lock identity and exact source artifact digest/length;
- Task 01 four-field identity parity for all records; and
- full structural projection equality between pinned source records and output
  records.

The checker must fail closed for malformed source data, unsupported field
types, empty card_faces, non-object faces, missing face names, invalid
related-part shapes, duplicate identities, misplaced or out-of-order records,
noncanonical bytes, digest mismatches, source-lock mismatches, report count
mismatches, and unexpected generated files.

The checker must never dereference all_parts.uri and must not use a fallback
source. Missing or unverifiable pinned bytes produce BLOCKED at the command or
final-report level; malformed or inconsistent data produces FAIL.

## 10. Offline synthetic reproduction

M1 adds a small deterministic synthetic source that covers:

- a simple single-face record;
- a multi-face record with source order preserved;
- raw characteristic strings, including non-numeric formulas;
- ordered colors, color identity, keywords, and produced mana;
- absent optional fields represented as null;
- present empty strings and arrays preserved distinctly;
- a related-parts array containing all six retained relationship fields; and
- attraction-light integers if the retained field is exercised.

The synthetic gzip source uses deterministic bytes with mtime=0. It is a
mechanics fixture only and does not become a semantic authority.

The synthetic command builds two independent empty output directories, checks
both outputs, and compares every relative file name and every byte. It must run
without Scryfall access.

## 11. Required tests

Positive tests must cover:

- single-face extraction;
- multi-face extraction and exact face order;
- absence versus empty-value preservation;
- raw string and source-array order preservation;
- explicit absence of parent-to-face and face-to-parent inheritance;
- opaque related-part URI preservation without dereferencing;
- Task 01 identity and source-record SHA parity;
- model immutability and stable record wire digest;
- canonical structural JSONL output;
- all 16 deterministic shards and strict ordering;
- stable aggregate manifest and exact ArtifactManifest binding;
- source provenance closure;
- byte-identical repeated builds from the same pinned bytes;
- synthetic full structural reproduction; and
- fresh non-editable wheel structural smoke with schemas available outside
  repository CWD.

Negative tests must cover representative failures for:

- missing or invalid Oracle ID, source card ID, name, or layout;
- invalid retained scalar, array, element, face, or related-part types;
- explicit null source values where the source-presence contract cannot
  distinguish them from absence;
- invalid card_faces, empty faces, non-object faces, or missing face names;
- duplicate Oracle IDs, missing IDs, extra IDs, wrong shards, and out-of-order
  shards;
- noncanonical JSONL and semantic document bytes;
- missing or unexpected shard files;
- structural manifest or ArtifactManifest digest mismatch;
- source-lock, source-record identity, or Task 01 parity mismatch;
- report count or digest mismatch; and
- unexpected generated output files.

Every negative test must protect a real M1 invariant. The suite must not use a
large mechanical mutation matrix in place of contract-focused tests.

## 12. CLI, Justfile, CI, and packaging

The maintainer CLI adds only these M1 commands:

~~~
python -m manafold_census.cli structural-build
python -m manafold_census.cli structural-check
python -m manafold_census.cli structural-check --synthetic
~~~

structural-build uses the committed lock and exact local pinned cache and
writes a fresh dist/structural/scryfall-oracle-v1 output. It does not fetch or
refresh source bytes. structural-check validates a supplied output, while
--synthetic runs the offline two-build reproduction.

The Justfile adds:

~~~
just structural-build
just structural-check
~~~

The ordinary just check path includes only the synthetic/offline structural
check. It remains network-independent. Hosted CI continues to use Python 3.12
and runs formatting, Ruff, mypy, pytest, Task 00 reproduction, Task 01
synthetic reproduction, M1 synthetic reproduction, wheel build, fresh
non-editable wheel smoke, and the recursive 500-line maintainability guard.
CI never acquires live Scryfall data.

The new schema must be included in the existing wheel resource path. The fresh
wheel smoke must import the structural package and validate a synthetic output
from outside the repository working directory.

## 13. Documentation and implementation boundaries

M1 documentation may describe:

- the source-fact boundary;
- the three structural record types;
- null and empty-value semantics;
- face order and face_index;
- raw string and array preservation;
- opaque non-dereferenced related-part URIs;
- 16 structural shards;
- source provenance and Task 01 parity;
- generated output location; and
- offline structural checking.

M1 documentation must not introduce M2 terminology as an implemented model.
The following remain explicitly absent:

~~~
SemanticRequirement
RequirementKind
RequirementFamily
Capability
CapabilityFamily
semantic parser
ability parser
rules citation model
~~~

Task 01 source locks, source digests, source byte lengths, record counts, and
existing Task 01 contracts remain unchanged.

## 14. M1 exit gates

The implementation must report each gate honestly as PASS, FAIL, BLOCKED, or
NOT_RUN:

~~~
STRUCTURAL_RECORDS              = 100% of pinned Oracle IDs
MISSING_ORACLE_IDENTITIES       = 0
EXTRA_ORACLE_IDENTITIES         = 0
DUPLICATE_STRUCTURAL_IDENTITIES = 0
FACE_ORDER_PRESERVATION         = PASS
SOURCE_PROVENANCE               = PASS
TASK01_RECORD_IDENTITY_PARITY   = PASS
STRUCTURAL_SCHEMA_VALIDATION    = PASS
STRUCTURAL_MANIFEST_CLOSURE     = PASS
ARTIFACT_BYTE_IDENTITY          = PASS
CANONICAL_OUTPUT                = PASS
PINNED_SOURCE_ONLY              = PASS
BYTE_REPRODUCTION               = PASS
NO_SEMANTIC_INFERENCE           = PASS
MODULE_LOC_BUDGET               = PASS
~~~

M1 is complete only when every required gate passes. A real full-corpus build
that was not executed is NOT_RUN, not PASS. A missing or unverifiable exact
pinned source is BLOCKED, not a reason to substitute another dataset.

The implementation phase must end with one unmerged PR against main containing
independently reviewable task commits. It must not merge the PR, start M2, or
implement Issue #5.

## 15. Mandatory staged implementation protocol

After this specification is approved, the workflow is staged and fail-closed:

1. Write the implementation plan only.
2. Stop.
3. Wait for independent review and explicit authorization of the plan.

The implementation plan may contain multiple numbered tasks, but authorization
of the plan does not authorize all tasks. No full-plan execution is permitted.

For implementation:

- execute exactly one numbered task;
- do not pre-stage later tasks;
- run only that task's required verification;
- commit that task as a standalone reviewable commit;
- report the exact commit SHA, parent SHA, changed files, and executed gates;
- stop after the task report.

The next numbered task is always:

~~~
NEXT_TASK_AUTHORIZED = NO
~~~

It remains unauthorized until independently reviewed and explicitly
authorized. No agent may execute Task N+1 merely because Task N passed.

## Evidence Appendix A — observed top-level layouts

Observed in the pinned source identified above:

~~~
adventure           170
art_series        2243
augment             14
case                15
class               38
double_faced_token   80
emblem               87
flip                26
front_card         291
host                20
leveler             26
meld                21
modal_dfc          100
mutate              34
normal           33429
planar             207
prepare             64
prototype           21
saga               194
scheme             102
split              137
token              913
transform          401
vanguard           107
~~~

There are 25 observed layout values and 38,740 total records.

## Evidence Appendix B — observed top-level field shapes

Counts are records with the property present; absent is the complement of
38,740. Array element counts count all elements across present arrays.

| Field | Present | Absent | Observed value type | Array element types/count |
| --- | ---: | ---: | --- | --- |
| mana_cost | 35,916 | 2,824 | string | — |
| type_line | 38,740 | 0 | string | — |
| oracle_text | 35,519 | 3,221 | string | — |
| colors | 35,916 | 2,824 | array | string / 36,381 |
| color_identity | 38,740 | 0 | array | string / 40,014 |
| color_indicator | 42 | 38,698 | array | string / 46 |
| keywords | 38,740 | 0 | array | string / 25,031 |
| produced_mana | 2,762 | 35,978 | array | string / 7,222 |
| power | 19,987 | 18,753 | string | — |
| toughness | 19,987 | 18,753 | string | — |
| loyalty | 333 | 38,407 | string | — |
| defense | 2 | 38,738 | string | — |
| hand_modifier | 107 | 38,633 | string | — |
| life_modifier | 107 | 38,633 | string | — |
| attraction_lights | 50 | 38,690 | array | integer / 136 |
| card_faces | 3,221 | 35,519 | array | object / 6,447 |
| all_parts | 6,901 | 31,839 | array | object / 19,951 |

The full top-level source-object key set has 2,776 distinct shapes. M1 retains
only the fixed structural projection defined above.

## Evidence Appendix C — observed faces

~~~
cards_with_card_faces     = 3221
cards_without_card_faces  = 35519
total_face_records        = 6447
max_face_count             = 5
face_count_distribution    = 2:3218, 3:2, 5:1
full face-object key shapes = 29
~~~

Observed projected face-field shapes across 6,447 face objects:

| Field | Present | Observed value type | Array element types/count |
| --- | ---: | --- | --- |
| name | 6,447 | string | — |
| mana_cost | 6,447 | string | — |
| type_line | 6,437 | string | — |
| oracle_text | 6,447 | string | — |
| colors | 5,648 | array | string / 1,116 |
| color_indicator | 332 | array | string / 422 |
| power | 913 | string | — |
| toughness | 913 | string | — |
| loyalty | 25 | string | — |
| defense | 37 | string | — |

The complete observed face key universe also contains source fields outside the
M1 projection: artist, artist_id, flavor_text, illustration_id, image_uris,
object, and watermark. These fields are deliberately excluded as presentation
or catalog metadata.

## Evidence Appendix D — observed related parts

~~~
cards_with_all_parts    = 6901
cards_without_all_parts = 31839
relation_count          = 19951
relation_key_shapes     = one shape across all relations
~~~

Every observed relation has exactly these keys:

~~~
component, id, name, object, type_line, uri
~~~

Every observed value for each of those six keys is a string. The complete
source all_parts array-length distribution is:

~~~
2:5785, 3:563, 4:160, 5:51, 6:174, 7:39, 8:10, 9:12,
10:9, 11:8, 12:4, 13:3, 14:9, 15:2, 16:5, 17:6, 18:1,
19:2, 20:1, 21:1, 22:6, 23:1, 24:1, 25:4, 26:2, 27:2,
28:1, 29:2, 30:1, 32:1, 33:1, 34:3, 37:1, 38:1, 39:1,
41:2, 42:1, 43:3, 49:1, 51:1, 52:2, 53:1, 54:2, 55:1,
62:1, 66:1, 73:1, 85:1, 88:1, 108:1, 124:1, 144:1,
150:1, 157:1, 166:1, 185:1, 356:1, 373:1
~~~

These relationship counts describe source shape only. They do not establish
ownership, creation semantics, meld behavior, transform behavior, or linked
object behavior.

## 16. Authorization boundary

This file authorizes the design specification only. It does not authorize
production code, generated M1 output, a branch, a commit, a push, a pull
request, an implementation plan, or M2 work. The implementation plan is the
next separately authorized artifact; its authorization still does not
authorize any numbered implementation task.
