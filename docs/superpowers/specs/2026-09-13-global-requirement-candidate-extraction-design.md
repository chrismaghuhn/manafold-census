# M3 Global Requirement Candidate Extraction — Design Specification

Status: design specification only; implementation is not authorized.

```text
TASK                         = M3_DESIGN_SPECIFICATION
MILESTONE_ISSUE              = #6
BASELINE_MAIN                = d73e611b8acbb22ddbbbdfe84eae73b080efe56e
M2_MERGED_HEAD               = 4196357e0815aaa593aa148f2b90b2917bf668e8
PR_14                        = MERGED
ISSUE_5                      = CLOSED
ISSUE_6                      = OPEN
M3_DESIGN_STATUS             = READY_FOR_INDEPENDENT_REVIEW
M3_IMPLEMENTATION_PLAN       = NOT_AUTHORIZED
M3_IMPLEMENTATION             = NOT_AUTHORIZED
GLOBAL_EXTRACTION             = NOT_STARTED
M4_CAPABILITY_ONTOLOGY        = NOT_STARTED
```

This document is the normative architecture proposal for the later M3
implementation. It does not add production code, schemas, fixtures, commands,
CI configuration, or a global analysis dataset.

## 1. Status and authority

### 1.1 Verified repository facts

The following facts were verified before this specification was authored.

| Fact | Verified value | Authority |
| --- | --- | --- |
| Repository | `chrismaghuhn/manafold-census` | configured `origin` |
| Baseline | `origin/main = d73e611b8acbb22ddbbbdfe84eae73b080efe56e` | live remote ref |
| M2 implementation parent | `4196357e0815aaa593aa148f2b90b2917bf668e8` | merged PR #14 first parent |
| PR #14 | merged | GitHub live state |
| Issue #5 | closed | GitHub live state |
| Issue #6 | open | GitHub live state |
| Current pinned structural record count | `38,740` | M1 source lock/corpus evidence |
| M1 shard set | `records/0.jsonl` through `records/f.jsonl` | `src/manafold_census/structural/index.py` |
| M1 shard order | `oracle_id` ascending within first-hex shard | M1 index checker |

The repository-specific implementation inspection covered the structural,
corpus, and semantic packages; the structural and semantic schemas; the pinned
source lock; the M1 design; the M2 design and plan; and the requested test
families. The local M2 checkout was clean before this design branch was created.

The pinned M1 source-lock digest is:

```text
4767dccbb518b4009c235bb1ce531f509c0923ba0ebe190936c2dc2d14e2d4bd
```

The source-lock, structural index, and source bytes remain upstream authority.
This specification does not replace them with a M3 interpretation.

### 1.2 Authority labels

Every normative statement in this document is one of the following:

* **VERIFIED REPOSITORY FACT** — present in the inspected repository or live
  authority state.
* **DESIGN DECISION** — selected by this M3 specification and intended to be
  frozen for implementation.
* **RECOMMENDATION** — a safe implementation default that may be revisited at
  the stated open-decision point without changing the core contract.
* **OPEN DECISION** — deliberately deferred because it is not required to
  implement the M3 reference path safely.

An implementation must not turn a recommendation or an open decision into a
new semantic authority without a follow-up design change.

## 2. Goals

M3 consumes the exact frozen M1 structural corpus and the frozen M2 semantic
Requirement contract. Its primary global invariant is:

```text
one explicit CardAnalysisRecordV1 per pinned StructuralCardRecordV1
```

For the current pinned corpus this means an expected count of 38,740. The
number is bound to the current structural index manifest; it is not a universal
future constant.

M3 must:

1. make every pinned card visible in an explicit analysis outcome;
2. preserve M2 `RequirementV1` identity, evidence, provenance, review, and
   resolution semantics without reinterpretation;
3. produce deterministic candidate proposals with explicit producer and
   pattern provenance;
4. reconcile multiple producers without hidden semantic priority;
5. distinguish a proven zero-requirement result from an unresolved analysis;
6. fail closed on execution, input, validation, and publication errors;
7. support exact reproduction from pinned source, registry, and artifact
   identities;
8. remain usable without a database, network service, or live model call; and
9. provide rebuildable reports and review worklists without making them
   authoritative semantic records.

M3 is a census and candidate-extraction layer. It is not a semantic truth
certificate, engine-support report, or capability ontology.

## 3. Non-goals

M3 does not:

* implement a global extractor in this task;
* process the 38,740-card corpus in this task;
* change M1 or M2 source, identity, schema, evidence, review, resolution, or
  digest contracts;
* make `RequirementBundleV1` accept zero Requirements;
* define capability IDs, capability groups, ontology hierarchy, or Manafold
  engine support;
* create card-specific executors or card-name semantic identities;
* make deterministic output equivalent to human-reviewed truth;
* let a pattern review inherit into Requirement review;
* require an LLM, ML model, network service, database, or message queue;
* call a live LLM during an authoritative deterministic build;
* make a cache hidden semantic state;
* add a second canonical JSON or digest implementation;
* add CLI commands, CI changes, Justfile changes, or runtime dependencies;
* modify the frozen M2 representative fixtures;
* create a PR or merge implementation; or
* write an M3 implementation plan as part of this design task.

## 4. Frozen upstream contracts

The normative flow is:

```text
pinned source bytes
    -> M1 StructuralCardRecordV1
    -> M2 RequirementV1 / RequirementBundleV1
    -> M3 CardAnalysisRecordV1 and run artifact
    -> future M4 capability analysis
```

The following distinctions are preserved:

```text
Source Fact              != Semantic Requirement
Requirement              != Capability
Capability               != Engine Implementation
Imported                 != Understood
Parsed                   != Proven
Generated Proposal       != Reviewed Result
Reproducible             != Semantically Correct
Census Coverage          != Engine Support
```

### 4.1 M1 input authority

M3 consumes the persisted M1 structural corpus and verifies its manifests
before candidate production. A structural card is identified by the M1 source
identity fields:

```text
record_schema
oracle_id
source_card_id
source_record_sha256
```

The `source_lock_digest` in the M2 `SourceRecordRefV1` remains a required
binding and is checked against the frozen lock. It is authority context, not an
additional parser coordinate.

M1 preserves raw strings, absent-versus-empty values, source array order, face
order, face indices, and opaque related parts. M3 may inspect these facts but
must not normalize them into a new M1 identity.

### 4.2 M2 Requirement authority

M2 owns:

* `RequirementV1` kind and family grammar;
* typed parameters;
* structural, rules, and external-review evidence;
* `DerivationV1` and `ProvenanceV1`;
* `ReviewV1` and its terminal review binding;
* `ResolutionV1` and its uncertainty semantics;
* producer-neutral `requirement_id`; and
* `RequirementBundleV1` relationships.

M2 `requirement_id` is derived from source identity, family, kind, and typed
parameters. It excludes evidence locators, source-lock context, derivation,
review, resolution, and relationships. M3 must not put pattern IDs, parser
offsets, clause indices, or worker information into that identity.

`RequirementBundleV1` requires at least one Requirement. M3 solves the
card-level zero-result case with an absent optional bundle, never by weakening
the M2 bundle invariant.

### 4.3 M2 review boundary

M2 `ReviewStatusV1.ACCEPTED` and `REJECTED` require explicit terminal review
metadata and a matching `reviewed_claim_digest`. A producer generated during
ordinary M3 extraction has no authority to create either state.

The frozen M2 rule is therefore extended into M3 as follows:

```text
normal CandidateProducer     -> PROPOSED only
M3 reconciliation             -> no review promotion
pattern-rule review           -> reuse permission only
external review authority     -> future explicit terminal decisions only
```

## 5. Terminology

| Term | M3 meaning | Explicit non-meaning |
| --- | --- | --- |
| Card analysis record | One M3 envelope for one M1 source record | A bundle with zero Requirements |
| Candidate | A valid M2 Requirement emitted for M3 consideration | A reviewed semantic truth |
| Producer | An allowlisted algorithm adapter that emits candidates or typed analysis findings | An authority over M2 review |
| Pattern | A versioned matching definition used by a producer | A Requirement, capability, or engine implementation |
| Pattern registry | Immutable data describing the pattern snapshot used by a run | A review authority |
| Producer trace | Extraction-local audit data explaining production and reconciliation | M2 Requirement identity or evidence |
| Reconciliation | Deterministic combination and conflict classification | A semantic priority selector |
| Analysis outcome | M3 extraction closure state for one card | M2 review status or resolution state |
| Run artifact | One complete, reproducible M3 build plus manifests | A global semantic truth claim |
| Review authority | A separately governed, versioned source of explicit terminal decisions | A normal pattern registry |

The record and report layers must keep M3 extraction outcomes separate from
M2 `review.status` and `resolution.state`. M2 summaries are derived from the
Requirements contained in a record.

## 6. M3 record boundary

### 6.1 Decision

The authoritative M3 output unit is `CardAnalysisRecordV1`: exactly one record
for exactly one complete M1 source identity.

The record is a thin envelope. It contains the source binding, one small M3
analysis outcome, and zero-or-one M2 bundle. It does not contain producer
groups, pattern groups, parser traces, report counters, or review queues.

M3 V1 does not require a separate artificial `analysis_id`. The natural record
key is the complete source identity tuple:

```text
(
    record_schema,
    oracle_id,
    source_card_id,
    source_record_sha256
)
```

If a future index needs a compact identifier, it may derive one under a new
versioned domain from this tuple. Such an identifier must not be random and
must not replace the source identity as the closure key.

### 6.2 Persisted outcome vocabulary

The M3 V1 persisted outcome vocabulary is deliberately smaller than the set of
run failure diagnostics:

```text
REQUIREMENTS_PRODUCED
NO_REQUIREMENTS_APPLICABLE
UNRESOLVED_ANALYSIS
```

These are M3 extraction outcomes, not M2 review or resolution values.

#### `REQUIREMENTS_PRODUCED`

The card produced at least one valid, reconciled `RequirementV1`; the record
contains exactly one non-null `RequirementBundleV1`. The bundle may contain
Requirements whose M2 resolution is `PARTIAL` or `UNRESOLVED`, and whose M2
review status is `PROPOSED`. The M3 outcome does not promote or hide those M2
states.

#### `NO_REQUIREMENTS_APPLICABLE`

The record contains no bundle and carries a reference to an explicit,
versioned, digest-bound negative review authority. That authority must state
that this exact source identity has no applicable Requirements for its declared
M3 semantic scope. It is a separate authority artifact, not an ordinary
producer, pattern rule, or classifier result.

The following is not sufficient:

```text
all ordinary producers returned []
```

If no producer matches and no explicit negative review authority is supplied,
the outcome is `UNRESOLVED_ANALYSIS`. Deterministic negative matching does not
have more semantic authority than deterministic positive matching.

The negative authority reference is M3 extraction closure evidence, not a new
M2 semantic assertion or an M2 terminal Requirement review. Its exact meaning
and scope are supplied by the separately governed authority artifact and are
also recorded in the trace sidecar.

#### `UNRESOLVED_ANALYSIS`

The analysis completed without a software execution failure, but M3 could not
close the semantic candidate set. Examples include an explicitly unsupported
semantic shape, competing interpretations that cannot be reconciled, or an
empty producer result without a positive no-result basis.

The record may contain no bundle or a bundle containing the valid proposals
that could be retained. If a valid bundle is retained, it still contains only
M2-valid Requirements and relationships; unresolved extraction facts remain in
the outcome and trace. This makes the card visible without pretending that
candidate absence proves semantic absence.

### 6.3 Execution failures are not card outcomes

The following are run/build failures, not valid persisted semantic outcomes:

```text
PRODUCER_EXCEPTION
INVALID_REQUIREMENT
INVALID_RELATIONSHIP
RECONCILIATION_FAILURE
SHARD_WRITE_FAILURE
SOURCE_MISMATCH
MANIFEST_MISMATCH
```

They are recorded, when possible, in non-authoritative run diagnostics keyed by
the source identity and stage. They prevent publication of the authoritative
M3 manifest and artifact. They never create a fake `CardAnalysisRecordV1`.

This yields the fail-closed rule:

```text
semantic uncertainty  -> explicit UNRESOLVED_ANALYSIS record
software/input failure -> failed run, no authoritative publication
```

### 6.4 Proposed wire model

The future wire model is:

```json
{
  "schema": "census.card-analysis.v1",
  "source": {
    "record_schema": "census.structural-card.v1",
    "source_lock_digest": "<sha256>",
    "oracle_id": "<uuid>",
    "source_card_id": "<uuid>",
    "source_record_sha256": "<sha256>"
  },
  "outcome": "REQUIREMENTS_PRODUCED",
  "bundle": {
    "schema": "census.semantic-requirement-bundle.v1",
    "source": "<same SourceRecordRefV1>",
    "requirements": ["<one or more RequirementV1>"],
    "relationships": ["<zero or more M2 relationships>"]
  },
  "no_requirements_basis": null
}
```

The wire model has these invariants:

| Field | Meaning | Required/optional | Canonical/identity rule |
| --- | --- | --- | --- |
| `schema` | M3 record schema | required | exact `census.card-analysis.v1` |
| `source` | M2 source reference bound to M1 | required | exact M1 identity and frozen source lock |
| `outcome` | M3 extraction outcome | required | one of the three values above |
| `bundle` | Same-source M2 requirements and relationships | required key, nullable value | null only for zero-result outcomes; non-null bundle has at least one Requirement |
| `no_requirements_basis` | Positive zero-result proof | required key, nullable value | non-null only for `NO_REQUIREMENTS_APPLICABLE`; sorted typed evidence |

For `REQUIREMENTS_PRODUCED`, `bundle` is non-null and
`no_requirements_basis` is null. For `NO_REQUIREMENTS_APPLICABLE`, `bundle` is
null and the basis is non-null. For `UNRESOLVED_ANALYSIS`, the bundle may be
null or non-null, but the basis is null unless a future schema explicitly
defines a combined unresolved/no-result proof; V1 does not do so.

The card record has no empty `requirements` array and no producer-group field.
All requirements in the optional bundle must use exactly the record's source
reference. M2 continues to own requirement and relationship validation.

The V1 `no_requirements_basis` value has this controlled authority-reference
shape:

```json
{
  "authority_id": "<negative requirement authority>",
  "authority_version": "<immutable version>",
  "record_id": "<exact authority record ID>",
  "record_sha256": "<sha256 of the exact authority record>",
  "scope_digest": "<sha256 of the declared negative-review scope>"
}
```

The implementation must validate the authority record, its source identity,
its declared scope, and its exact digest before accepting this outcome. A
future authority may itself be produced from a deterministic classifier, but
the classifier must not directly emit `NO_REQUIREMENTS_APPLICABLE` in an
ordinary M3 run. `record_sha256` and `scope_digest` bind the negative decision
without adding any field to M2 Requirement identity.

### 6.5 Multi-face cards

One physical M1 record produces one card-analysis record, even when it has many
faces. Requirements derived from the parent or a face use the existing M2
structural evidence variants and their `face_index` values. M3 does not copy
face data into the record envelope or create a separate card-analysis record
per face.

The source and face checks are performed against the actual M1 structural
record. A stale, missing, or out-of-range face reference is an execution
failure, not an unresolved semantic result.

## 7. Candidate producer contract

### 7.1 Deep module interface

The producer seam is a small, algorithm-independent interface. A producer is
an adapter behind that seam; its matcher/parser implementation is not part of
the M3 record contract.

Conceptually:

```text
produce(
    structural_record: StructuralCardRecordV1,
    context: ProducerContextV1
) -> ProducerResultV1
```

`ProducerContextV1` is read-only and contains:

* the expected M1 source-lock digest;
* the M2 schema and bundle schema identifiers;
* the immutable producer registry snapshot;
* the immutable pattern registry snapshot, when applicable; and
* no network client, engine state, hidden global state, or current time.

The implementation may use smaller internal seams, but callers of the M3
builder learn only the registry and producer result contract.

### 7.2 Producer descriptor

Each registered producer has an immutable descriptor containing:

```text
producer_id
producer_version
derivation_method       # one M2 DerivationMethodV1 value
input_schema
input_fields
pattern_registry_digest or null
deterministic           # required boolean
supports_relationships  # required boolean
```

`producer_id` and `producer_version` are stable identifiers, not display
names. A changed matching algorithm, parameter template, source scope, or
failure behavior requires a new version. The registry rejects duplicate
identity pairs and sorts descriptors by `(producer_id, producer_version)`.

The registry digest is the canonical digest of the sorted descriptor set. It
is part of the M3 manifest identity.

An authoritative M3 build may activate only producers whose descriptor has
`deterministic = true`. A registry entry with `deterministic = false` is
rejected from the active build with an execution failure; it is not silently
skipped and it cannot contribute a fallback result. A model producer may be
active only when it is the deterministic importer of a pinned external
proposal artifact described in Section 17.

### 7.3 Producer result

A producer result contains zero or more candidate proposals, zero or more
typed relationship proposals, and a deterministic execution classification:

```text
EMITTED
NO_MATCH
UNSUPPORTED_SHAPE
```

`NO_MATCH` is only an observation about that producer. It is never by itself a
card-level zero-requirement proof. `UNSUPPORTED_SHAPE` is an expected semantic
boundary and contributes to `UNRESOLVED_ANALYSIS`.

An exception, invalid result shape, timeout in a deterministic local adapter,
or contract violation is a producer execution failure. It aborts the run.

Each candidate must be materialized as an M2-valid `RequirementV1` with:

```text
review.status = PROPOSED
review.reviewed_by = null
review.reviewed_claim_digest = null
```

The producer may choose `DerivationMethodV1.DETERMINISTIC_RULE`, `PARSER`,
`HEURISTIC`, `MODEL`, `IMPORTED_ANNOTATION`, or `HUMAN_AUTHORED` only when the
descriptor and execution mode justify it. In ordinary M3 extraction, terminal
review metadata is forbidden regardless of the derivation method.

The future implementation should expose a candidate-construction helper that
can only construct a producer proposal with `PROPOSED`. The producer seam must
not expose an operation for setting `ACCEPTED` or `REJECTED`.

### 7.4 Candidate validation

Before reconciliation, every emitted candidate is checked by the existing M2
model and M2 source-aware validation:

1. the candidate parses as the frozen M2 Requirement wire;
2. its `requirement_id` recomputes exactly;
3. its source matches the current M1 record and source lock;
4. all structural evidence references exact existing fields/faces/fragments;
5. all M2 kind/family, parameter, evidence, provenance, review, and resolution
   invariants hold; and
6. the review status is `PROPOSED` with null terminal metadata.

Failure of any validation is `INVALID_REQUIREMENT`, not
`UNRESOLVED_ANALYSIS` and not an empty result.

### 7.5 Relationship proposals

Producers may propose relationships, but the proposal is not an M2 relationship
until reconciliation validates it. A relationship proposal contains candidate
identities or producer-local handles, a relationship type, and the evidence or
trace needed to explain the assertion.

Reconciliation may canonicalize a valid symmetric relationship and include it
in the final `RequirementBundleV1`. It may not invent a relationship merely
because two producers disagree, because two IDs differ, or because one
producer ran first.

`CONFLICTS_WITH` is emitted only when a producer or a future explicit review
authority supplies that relation. It is not inferred from candidate mismatch.
An invalid endpoint, self-edge, forbidden ordinal, duplicate, or cycle
violates the M2 bundle contract and fails the run.

### 7.6 Determinism requirement

A producer marked deterministic must be a pure function of the exact source
record, the exact registry snapshots, and the declared producer version. It
must not depend on:

* registration order;
* filesystem enumeration;
* thread scheduling;
* process ID or host name;
* wall-clock time;
* random values;
* network responses; or
* mutable hidden state.

The producer returns canonicalizable values. It does not choose semantic
priority over another producer.

For an authoritative M3 run, this is a hard admission rule rather than a
descriptive flag:

```text
active producer.deterministic == true
```

The only permitted `MODEL` path is a deterministic import of an already pinned
proposal artifact. A live or otherwise nondeterministic model adapter is not an
authoritative producer.

## 8. Pattern reuse architecture

### 8.1 Decision

M3 uses a versioned declarative pattern registry as an input to deterministic
pattern producers. A pattern is a reusable matching rule, not a Requirement,
Capability, review authority, or engine operation.

The pattern registry is a separate immutable effective snapshot whose identity
is bound to the M3 run. The snapshot includes pattern definitions and their
review-eligibility records. Pattern IDs are semantic rule identities and must
never be named after a specific card.

### 8.2 Pattern rule identity

A `PatternRuleV1` definition conceptually contains:

```text
pattern_id
pattern_version
matcher_kind
source_scope
normalization_profile
capture/parameter template
expected M2 family and kind
evidence policy
producer_id
producer_version
M2 contract version
```

The pattern identity is the pair `(pattern_id, pattern_version)` and its
content digest is computed from the complete canonical rule body. The digest
includes matcher behavior, normalization, capture names, parameter template,
source scope, expected M2 shape, evidence policy, and producer binding.

The effective pattern registry snapshot contains both the pattern definitions
and the immutable `REVIEWED_FOR_REUSE` eligibility records that govern which
rules may be active. A review record may be authored as a separate source file,
but it must be incorporated into the effective snapshot before the snapshot
digest is calculated. There is no execution-affecting review eligibility input
outside that digest.

`REVIEWED_FOR_REUSE` never changes the emitted Requirement review status. It
means that the rule is eligible for deterministic reuse, not that its
instances are human-reviewed. Changing eligibility changes the effective
pattern registry digest and therefore changes the M3 run identity.

### 8.3 Matching progression

M3 supports a conservative progression, with each level remaining proposal
only:

| Level | Matching mode | M3 authority |
| --- | --- | --- |
| 0 | exact frozen reviewed fixture mapping | deterministic proposal |
| 1 | exact source-text or exact clause reuse | deterministic proposal |
| 2 | deterministic parameterized recurring syntax | deterministic proposal |
| 3 | versioned parser proposal | proposal only |
| 4 | versioned heuristic proposal | proposal only |
| 5 | imported model proposal artifact | proposal only |

The first reference implementation should start with exact literal/clause
matching and add broader levels only when a versioned matcher contract and
fixtures exist. A broader matcher must not silently reinterpret an old pattern
version.

### 8.4 Invalidation

The following changes invalidate reuse under the old rule identity and require
a new pattern version and digest:

* matcher algorithm or tokenization;
* normalization profile;
* source-field or face scope;
* capture-to-parameter mapping;
* output family, kind, or parameter template;
* evidence construction;
* producer version or M2 contract binding; and
* rule-review scope.

Historical runs retain their old registry digest and remain reproducible. A
new run cannot silently use a changed rule under an old identity.

### 8.5 Exact-text and source-location policy

M2 evidence remains the minimal source-aware semantic evidence: source record,
face, field, keyword, and optional exact fragment. M3 extraction-local details
do not enter M2 identity.

The trace sidecar may record:

```text
source identity
producer ID/version
pattern ID/version/digest
source field
face index
exact raw fragment
clause ordinal
parser span or local parse node
candidate fingerprint
reconciliation disposition
```

Parser spans and clause ordinals are audit locators, not stable semantic
coordinates. Reproduction uses the pinned source bytes, the exact registry
digests, the producer version, and the raw fragment/source binding. A changed
parser must create a new producer or pattern version.

## 9. Proposal reconciliation

### 9.1 Pipeline position

The authoritative conceptual pipeline is:

```text
M1 source record
    -> candidate producers
    -> proposal set and trace events
    -> deterministic reconciliation
    -> CardAnalysisRecordV1
    -> optional independent review workflow
```

Reconciliation canonicalizes valid proposals. It does not promote review
status, assign capability meaning, or select a producer as a semantic winner.

### 9.2 Identical Requirement IDs

Candidates with the same `requirement_id` have the same producer-neutral M2
identity payload. Reconciliation may merge only the non-identity information
that has an explicit monotone operation:

* evidence is set-unioned and canonically sorted;
* derivation records are set-unioned and canonically sorted;
* identical `review` values are retained; and
* identical `resolution` values are retained.

All contributing candidates must be `PROPOSED`. A terminal or in-review value
from a normal producer is a producer contract violation and fails the run; it
is not downgraded silently.

If candidates with the same ID have different resolution values, the
reconciler applies this exact V1 rule:

```text
same ID + same resolution
    -> union evidence
    -> union provenance
    -> retain one canonical Requirement

same ID + different resolution
    -> do not synthesize a Requirement
    -> do not choose a producer
    -> omit the disputed identity from the retained bundle
    -> preserve every contributing proposal in the trace
    -> set card outcome to UNRESOLVED_ANALYSIS
```

Other undisputed Requirements from the same card may remain in the optional
bundle. If no undisputed Requirement remains, the bundle is null. This is a
semantic unresolved result, not an execution failure, and there is no implicit
"more complete" or producer-priority resolution operator.

### 9.3 Different Requirement IDs

Different IDs are distinct M2 assertions. Reconciliation retains both when
each is valid. It does not deduplicate them by normalized text, producer name,
pattern ID, family, kind, or similar parameters. Cross-card or cross-ID
equivalence remains outside M3 and belongs to a future M4 analysis.

If a producer explicitly proposes `ALTERNATIVE_OF` or `CONFLICTS_WITH`, the
reconciler validates and canonicalizes it. If there is no explicit relation,
the existence of multiple IDs is not itself a conflict.

### 9.4 Conflict classes

The implementation distinguishes:

| Class | Meaning | Result |
| --- | --- | --- |
| Compatible duplicate | Same ID, mergeable evidence/provenance | one canonical Requirement |
| Semantic disagreement | Same ID with incompatible non-identity claims, or explicit competing interpretation | `UNRESOLVED_ANALYSIS`, trace retains disagreement |
| Independent assertions | Different IDs without a conflict relation | all valid Requirements retained |
| Explicit conflict | Producer supplied a valid `CONFLICTS_WITH` relation | relation retained; card may remain unresolved |
| Contract failure | malformed candidate or invalid M2 relation | run fails; no publication |

Producer ordering is never a tie-breaker for these classes.

### 9.5 Canonical ordering

The canonical bundle order is the existing M2 order: Requirements strictly
ascending by `requirement_id`, with relationships ordered by the existing M2
relationship sort key. Evidence and provenance use their existing canonical
sorts. Candidate and trace order is independent of execution order and uses
explicit keys containing source identity, producer identity/version, candidate
identity, and trace kind.

## 10. Human-review boundary

### 10.1 M3 V1 rule

M3 V1 has no automatic Pattern-to-`ACCEPTED` pipeline. The frozen decision is:

```text
deterministic pattern match -> RequirementV1(PROPOSED)
```

This remains true when the pattern was reviewed once and matches thousands of
cards. Pattern review establishes trust in reuse of the producer rule; it does
not establish an M2 human review of each emitted claim.

### 10.2 Review worklists

M3 may generate a derived review worklist containing one row per Requirement
and grouping hints such as pattern ID, producer, or repeated exact fragment.
The worklist is not an authority and is not stored inside the card-analysis
record. Applying a review decision requires an explicit external workflow that
creates a new versioned review artifact or changes the specific Requirement
wire through the frozen M2 review contract.

No hidden bulk-acceptance operation is allowed. A pattern group may reduce
reviewer navigation cost, but it cannot mutate terminal status for members.

### 10.3 Future review authority extension

A future `ExternalReviewAuthority` may be imported as a pinned artifact. It
must identify exact Requirement IDs and exact reviewed claim digests, bind the
source and M2 contract versions, and be independently versioned and digested.
M3 would validate the supplied terminal `ReviewV1` against the M2 model and
the authority artifact before materialization.

That extension is not required for M3 V1. Normal producers and reconciliation
have no API for it.

## 11. Global corpus closure

### 11.1 Input and output key sets

The build derives the expected key set from the verified M1 structural corpus,
not from a configured integer:

```text
expected_keys = {
    (record_schema, oracle_id, source_card_id, source_record_sha256)
    for every M1 structural record
}
```

The output key set is derived from the `source` field of every M3 record. The
authoritative closure validator requires:

```text
expected_keys == actual_keys
len(expected_keys) == len(actual_keys)
duplicate_output_keys == 0
unknown_extra_keys == 0
```

A count comparison alone is insufficient. One missing card plus one extra card
must fail.

### 11.2 Ordering and partitioning

M3 reuses the established M1 partitioning function:

```text
shard = first lowercase hexadecimal character of oracle_id
```

The same source identity always maps to the same shard, regardless of worker
count, producer execution order, filesystem enumeration, or retry sequence.

Within each shard, records are strictly ordered by `oracle_id`. The shard set
is exactly `0` through `f`; empty shards are still present and measured. The
global order is shard order followed by the shard's strict `oracle_id` order,
which is equivalent to full canonical `oracle_id` order.

### 11.3 Closure outcome

Closure is a publication gate. A run with an execution failure, missing card,
duplicate card, or extra card has no authoritative M3 manifest. A run with an
explicit `UNRESOLVED_ANALYSIS` record can publish because unresolved semantics
are a valid census outcome and remain visible.

## 12. M3 run artifact: artifact and sharding model

### 12.1 Decision

M3 V1 uses an inspectable directory artifact with:

```text
records/0.jsonl ... records/f.jsonl
analysis-manifest.json
trace/0.jsonl ... trace/f.jsonl
report-index.json
reports/*.json                         # derived artifacts
```

The exact report file set can evolve under the report versioning rule, but the
authoritative card records, trace shard descriptors, and the input/producer/
pattern identities are fixed by `analysis-manifest.json`. The manifest has a
`record_shards` array and a `trace_shards` array; no second trace manifest is
required for V1.

This is a canonical-shard design, not a database design. It follows the
already-established M1 layout and supports streaming validation, local
inspection, small fixture tests, and future deterministic parallel workers.

### 12.2 Canonical JSONL rules

Each card record line is:

```text
canonical_json_bytes(record.to_wire()) + b"\n"
```

The validator rejects missing final LF, noncanonical JSON, invalid UTF-8,
unexpected fields, wrong shard assignment, non-strict order, duplicate source
identity, and invalid M2 nested values.

Trace lines use the same canonical JSONL framing and deterministic ordering but
are not part of M2 identity. Empty trace shards are retained when the artifact
layout requires them.

### 12.3 Publication atomicity

The builder writes to a fresh temporary output directory, validates the complete
record and trace set, writes and re-reads manifests, and only then publishes a
completed artifact directory. A partially written directory must never be
advertised as an authoritative run.

If final publication cannot be completed, the run is failed and any temporary
directory is diagnostic only. A publication retry must start from the validated
inputs and produce the same canonical bytes; it must not mutate a published
artifact in place.

## 13. Manifest, digests, and canonicalization ownership

### 13.1 Analysis manifest

The normative run manifest is a future `census.analysis-manifest.v1` document.
It binds:

```text
analysis_schema
source_lock_digest
structural_record_schema
structural_index_manifest_sha256
structural_index_aggregate_digest
m2_requirement_schema
m2_bundle_schema
producer_registry_digest
pattern_registry_digest
build_profile
record_count
record_identity_set_digest
record_shards
trace_shards
```

The analysis manifest deliberately does not bind `report-index.json`, any
individual report, or a report-package digest. This direction is one-way:

```text
authoritative records, trace, and registries
    -> analysis-manifest.json
    -> analysis-manifest digest
    -> derived reports and report-index.json
```

`report-index.json` is a derived artifact. It contains the exact
`analysis_manifest_sha256` it summarizes and descriptors for the canonical
report bytes. Reports may repeat that input manifest digest, but neither the
report index nor any report is an input to `analysis-manifest.json`.

If a later delivery package needs an "all files" digest, it is a separate
packaging-layer manifest above the analysis manifest and derived reports. It
does not define semantic analysis identity.

Each record shard descriptor contains only:

```text
relative_path
sha256
byte_length
record_count
```

The descriptors are ordered by the fixed shard names. The manifest itself is
canonical JSON and its file identity is the SHA-256 of those exact canonical
bytes, following the existing manifest convention.

### 13.2 Identity-set digest

`record_identity_set_digest` is a domain-separated digest over the canonically
sorted array of M1 source identity objects. It is independent of shard byte
layout and makes the closure set explicit in the manifest.

The recommended future domain is:

```text
census.card-analysis-identity-set.v1
```

It contains no runtime paths, timestamps, host names, random values, or
diagnostic stack traces.

### 13.3 Shard aggregate digest

The ordered shard descriptor list is digested with a new versioned M3 domain,
recommended as:

```text
census.card-analysis-index.v1
```

This reuses the existing `domain_digest` implementation and the established
descriptor shape. It does not create a second canonical JSON system.

### 13.4 Semantic versus diagnostic metadata

Semantic/reproduction identity includes only pinned inputs, schema versions,
registry identities, build profile, record identity, and exact bytes. It
excludes:

```text
wall-clock timestamps
machine paths
hostname
process ID
random temporary names
unbounded exception text
```

Run diagnostics may contain operational details, but diagnostics are not
authoritative M3 records and are not included in semantic identity.

### 13.5 Existing canonicalization ownership

All future M3 wire and digest code must reuse:

```text
manafold_census.canonical.canonical_json_bytes
manafold_census.digest.domain_digest
manafold_census.digest.sha256_bytes
```

No M3-specific serializer, Unicode normalization rule, or digest implementation
may be introduced.

## 14. Deterministic build algorithm

The reference build is single-process and deterministic. The following
pseudocode is normative at the operation level:

```text
load and validate the committed M1 source lock
load and validate the complete M1 structural index and manifests
verify the source-lock digest, structural manifest digest, and aggregate digest
load and validate the producer registry
load and validate the pattern registry snapshot
reject any active producer whose descriptor has deterministic = false
derive the expected M1 source-identity set

for structural_record in canonical_oracle_id_order:
    source_ref = exact SourceRecordRefV1 for structural_record
    proposal_events = []
    relationship_events = []
    no_result_findings = []
    unresolved_findings = []

    for producer in sorted producer registry:
        result = producer.produce(structural_record, immutable_context)
        if result raises:
            fail run with PRODUCER_EXCEPTION
        if result violates producer result contract:
            fail run with INVALID_PRODUCER_RESULT
        collect candidates, relationship proposals, and typed findings

    validate every candidate as an M2 Requirement against structural_record
    reconcile duplicate IDs, compatible evidence/provenance, and relations

    if reconciliation has an execution failure:
        fail run with RECONCILIATION_FAILURE
    if a valid negative review authority exists, no valid candidates exist,
       and no unresolved finding contradicts it:
        outcome = NO_REQUIREMENTS_APPLICABLE
        bundle = null
    elif a negative review authority conflicts with a valid candidate or
         unresolved finding:
        outcome = UNRESOLVED_ANALYSIS
        bundle = valid retained bundle or null
    elif reconciliation or producer findings remain semantically unresolved:
        outcome = UNRESOLVED_ANALYSIS
        bundle = valid retained bundle or null
    elif valid retained candidates exist:
        outcome = REQUIREMENTS_PRODUCED
        bundle = one RequirementBundleV1
    else:
        outcome = UNRESOLVED_ANALYSIS
        bundle = null

    emit exactly one CardAnalysisRecordV1 for source_ref
    emit deterministic trace entries for all successful producer findings

validate output key set equals expected M1 key set
validate no duplicate or extra records
write canonical record and trace shards to a temporary directory
measure shard hashes, lengths, and counts
write canonical analysis manifest
re-read every published candidate record, shard, trace, and manifest
recompute all digests and closure identities
generate deterministic derived reports from validated canonical records/traces
publish the complete artifact atomically
```

The build never converts an exception, invalid candidate, source mismatch, or
write failure into `UNRESOLVED_ANALYSIS`. Those conditions abort publication.

## 15. Failure semantics

### 15.1 Failure matrix

| Condition | Classification | Card record | Run publication |
| --- | --- | --- | --- |
| Producer returns no match | normal producer result | continue; not a zero proof | allowed if another outcome closes |
| Valid explicit negative review authority with no conflicting candidate | reviewed negative closure | `NO_REQUIREMENTS_APPLICABLE` | allowed |
| Negative review authority conflicts with a candidate/finding | semantic unresolved | `UNRESOLVED_ANALYSIS` plus trace | allowed |
| Unsupported semantic shape | semantic unresolved | `UNRESOLVED_ANALYSIS` | allowed |
| No-match without explicit negative review authority | semantic unresolved | `UNRESOLVED_ANALYSIS` | allowed |
| Active producer is nondeterministic | execution failure | none | forbidden |
| Producer exception | execution failure | none for failed card | forbidden |
| Invalid Requirement wire/model | execution failure | none | forbidden |
| Invalid evidence/source/face | execution failure | none | forbidden |
| Incompatible reconciliation that cannot be represented | semantic unresolved | `UNRESOLVED_ANALYSIS` plus trace | allowed |
| Invalid relationship or cycle | execution failure | none | forbidden |
| M1 source or manifest mismatch | input failure | none | forbidden |
| Missing, duplicate, or extra card | closure failure | no authoritative set | forbidden |
| Shard write or manifest write failure | publication failure | no published record set | forbidden |

### 15.2 No fallback

M3 has no fallback producer, hidden parser, automatic retry that changes
semantics, or silent omission path. A retry of a deterministic producer may be
operationally allowed only if it is expected to produce the same result; a
different result is a determinism failure and aborts the run.

### 15.3 Diagnostics

Run diagnostics are append-only or immutable after a failed attempt and use a
controlled failure-code vocabulary. They may identify a source identity and
stage, but they cannot be read as a completed M3 analysis dataset. A failed
run has no valid manifest that claims corpus closure.

## 16. Reference versus optimized execution and deterministic parallelism

### 16.1 Reference execution first

M3 V1 starts with a single-process reference execution. It is the conformance
oracle and the simplest way to prove record closure and byte identity. No
distributed runtime or worker queue is part of the baseline.

### 16.2 Future worker partitioning

Future workers may process fixed M1 shard assignments or fixed `oracle_id`
ranges. A worker writes only worker-local temporary output and trace entries.
The coordinator:

1. verifies each worker's declared input range;
2. rejects duplicate worker keys;
3. rejects missing and extra keys;
4. sorts all accepted records by canonical shard/order;
5. recomputes record and trace digests; and
6. publishes only after the same full validation as the reference path.

Producer execution order inside a worker is still registry order only for
operational consistency; it has no semantic priority. The merge order is fixed
and independent of completion time.

### 16.3 Equivalence requirement

For the same pinned inputs and deterministic registry snapshots:

```text
workers=1 == workers=2 == workers=8 == workers=N
```

means byte-identical card shards, trace shards, manifest content, and derived
report content after canonical packaging. Any difference is a failed
determinism test, not an acceptable optimization variation.

## 17. Optional LLM boundary

M3 is fully usable without a model. A live model call is forbidden in an
authoritative deterministic build because output, provider state, prompts, and
sampling can drift.

If model proposals are later used, they enter through an imported, pinned
proposal artifact containing at least:

```text
source identity
model/provider identity and version
prompt/template digest
parameter/configuration digest
raw proposal digest
M2 candidate wire or a deterministically reconstructible proposal
```

The import adapter is deterministic over the pinned artifact. The resulting
Requirements remain `PROPOSED` and carry `DerivationMethodV1.MODEL` with
explicit producer provenance. Model output never bypasses M2 validation,
review binding, or source evidence validation.

The imported proposal artifact is input data, not a review authority. A human
review authority must be separately versioned and explicitly applied.

## 18. Reports and derived views

### 18.1 Report ownership

Reports are derived, rebuildable views of a validated M3 run. They are not
source records, Requirements, or authority artifacts. A report must name the
input analysis-manifest digest it summarizes and must be regenerated when the
input manifest changes.

Reports may be canonical JSON documents with their own report schema versions.
They must not store mutable counters inside `CardAnalysisRecordV1`.

The derived `report-index.json` is the single downstream index for packaged
reports. It contains:

```text
report_index_schema
analysis_manifest_sha256
report descriptors (relative_path, sha256, byte_length)
```

It is written only after `analysis-manifest.json` has been finalized and is
never referenced by that authoritative manifest. A report/package consumer can
therefore verify the analysis input first and the derived report bytes second,
without a hash cycle.

### 18.2 Card-analysis review summaries and required dimensions

Card-level review summaries are derived by scanning the Requirements in each
validated bundle. Examples include cards containing at least one accepted
Requirement, cards containing proposals, cards containing unresolved
Requirements, and cards containing rejected alternatives. These summaries are
never duplicated as mutable counters in the card record.

The report layer must support deterministic counts for:

* cards by M3 analysis outcome;
* cards with zero produced Requirements;
* Requirements by M2 review status;
* Requirements by M2 resolution state and reason;
* Requirements by M2 derivation method;
* Requirements by family and kind;
* producer contribution and no-match counts;
* producer conflict and unresolved counts;
* top recurring patterns;
* largest unresolved groups;
* single-card/outlier patterns; and
* multi-face and face-source distributions.

`ACCEPTED` and `REJECTED` counts are read from M2 Requirements. M3 does not
infer them from producer type or pattern review. In a baseline M3 run with no
external review import, generated candidates are all `PROPOSED`.

### 18.3 Pattern reuse metrics

Reports avoid floating-point identity values. A reuse summary stores integer
counts, for example:

```text
distinct_pattern_count
matched_card_count
matched_requirement_count
reused_match_count = sum(max(match_count - 1, 0) per pattern)
```

Consumers may compute a ratio from the numerator/denominator, but the
canonical report does not depend on float formatting.

Top lists sort by descending count and then ascending stable pattern,
producer, or kind identity. Ties never depend on source or filesystem order.

## 19. Schema and version evolution

### 19.1 Version ownership

The following are independently versioned:

```text
census.card-analysis.v1
census.analysis-manifest.v1
census.card-analysis-index.v1
census.card-analysis-identity-set.v1
pattern rule versions
producer versions
derived report schemas
```

The names are design recommendations to freeze before implementation. Each
version is immutable after publication.

### 19.2 Compatibility rules

* A change to the M2 Requirement or Bundle schema requires an explicit M3
  builder compatibility decision and a new M3 profile or schema version.
* A wire-field addition that changes canonical bytes requires a new M3 record
  version or an explicitly compatible schema migration; silent unknown-field
  acceptance is forbidden.
* A change to source binding, outcome semantics, or bundle cardinality requires
  a new record schema version.
* A change to matcher or producer behavior requires a new pattern or producer
  version and a new registry digest.
* Reports may evolve independently but must continue to bind their input
  manifest digest.

Historical artifacts are immutable and remain readable with their exact
schema/registry versions. No in-place upgrade rewrites an old artifact.

### 19.3 M2 and M4 boundaries

No M3 schema change adds fields to M2 `RequirementV1`, changes M2 identity, or
adds capability IDs. M4 consumes M3 observations through an explicit future
adapter rather than being embedded in the M3 record.

## 20. Testing and conformance

The future implementation must test the interfaces and invariants, not only
happy-path serialization.

### Unit tests

Cover:

* `CardAnalysisRecordV1` wire/model invariants;
* source identity binding and natural-key validation;
* zero-or-one bundle rules and positive no-result basis;
* producer descriptor and registry validation;
* producer result classification;
* pattern rule matching and pattern digest;
* trace sidecar ordering and source binding;
* duplicate candidate reconciliation;
* relationship reconciliation;
* analysis manifest and shard measurements; and
* deterministic derived report generation.

### Negative tests

At minimum reject:

```text
missing input card
duplicate input card
extra output card
duplicate output key
wrong source lock
wrong structural manifest or aggregate digest
producer exception
invalid producer result
terminal producer review status
invalid Requirement ID
invalid Requirement evidence/source/face
invalid relationship endpoint or cycle
incompatible record outcome/bundle combination
non-positive zero-result basis
stale producer version
stale pattern digest
wrong shard assignment
noncanonical JSONL
missing final LF
shard write failure
nondeterministic producer ordering
```

### Determinism tests

Verify:

* same input and registries twice produce identical bytes and digests;
* shuffled producer registration is canonicalized to the same result;
* shuffled candidate arrival is canonicalized to the same result;
* different worker counts produce byte-equivalent artifacts;
* filesystem enumeration order does not affect output;
* a fresh checkout with the same pinned inputs reproduces the artifact; and
* a changed producer or pattern version changes the bound registry identity.

### Corpus-closure tests

The checker must prove identity-set equality, not merely count equality. A
fixture with 38,740 records is bound to the current pinned structural manifest;
the test must not make that integer a future universal contract.

The full real-corpus closure gate is a maintainer/reproduction gate. Synthetic
fixtures remain suitable for ordinary offline CI.

### Golden fixtures

The implementation test corpus should include small records for:

1. exact pattern reuse;
2. multiple Requirements from one card;
3. a multi-face card with parent and face evidence;
4. keyword evidence;
5. duplicate candidate reconciliation;
6. competing candidate interpretations;
7. an explicit relationship proposal;
8. a positive zero-requirement applicability basis;
9. an unresolved no-match case;
10. an unsupported semantic shape;
11. a producer exception; and
12. invalid M2 candidate/relationship data.

### Property tests

Where the repository's existing test dependencies support it, test that:

* candidate arrival permutation does not change the canonical result;
* duplicate insertion is idempotent for mergeable duplicates;
* source identity closure rejects any missing/extra substitution;
* canonical serialization round-trips without digest change;
* shard assignment is a pure function of `oracle_id`; and
* a failed run never creates a publishable manifest.

## 21. Module ownership proposal

Future production code should add a focused `analysis` package rather than
extend one giant extractor:

```text
src/manafold_census/analysis/
    __init__.py
    model.py          # CardAnalysisRecord and M3 outcome/basis values
    producer.py       # producer interface and result contract
    registry.py       # producer registry and registry digest
    patterns.py       # declarative pattern values and matching seam
    trace.py          # extraction-local trace model and ordering
    reconcile.py      # candidate/relation reconciliation
    manifest.py       # shard and run manifest values
    build.py          # reference build orchestration
    validate.py       # independent closure/publication checks
    report.py         # derived deterministic reports
```

These are modules with small interfaces and deep implementations. The proposed
seams are:

* `producer.py`: one adapter contract for algorithms;
* `reconcile.py`: one canonical merge/conflict contract;
* `validate.py`: one independent publication/closure contract; and
* `report.py`: one derived-view contract over already validated records.

Each planned production module targets fewer than 500 lines, with review before
approximately 400 lines. If a module approaches that size, the design should
deepen a seam rather than add conditionals to a shared `extract.py`.

No module in this layout is created by this design task.

## 22. Dependency policy, maintainer ergonomics, and workflow

### 22.1 Dependencies

The baseline assumes the standard library and dependencies already used by the
repository, including the existing JSON Schema validation path. No new runtime
dependency is justified by the current 38,740-record target.

If implementation evidence later suggests a dependency, the proposal must
document the concrete correctness problem, benefit, risk, current-library
shortfall, and reproducibility impact before adding it.

### 22.2 Maintainer golden path

The eventual maintainer workflow should remain small and local. A likely shape
is:

```text
just m3-build
just m3-check
just m3-report
```

These commands are design examples only and are not added in M3 design work.
The baseline must not require a database server, distributed system, always-
online model API, or manual review of every card.

### 22.3 Rebuild and resume policy

M3 V1 uses a full deterministic rebuild as the authoritative path. There is no
authoritative incremental cache or semantic resume state.

A future non-authoritative cache may be considered only with a key containing
the complete source identity, all schema versions, structural manifest
identity, producer registry digest, pattern registry digest, and build profile.
Every cache hit would still need full M2 and closure validation. A cache must
never override a fresh reference rebuild or change published bytes.

## 23. Security and information model

The trust model has four inputs:

1. pinned source and M1 structural artifacts;
2. reviewed code implementing allowlisted producers;
3. declarative producer/pattern registry data; and
4. optional imported proposal or future review-authority artifacts.

### 23.1 Unsafe generic execution

Pattern and registry artifacts are data, not executable programs. The
implementation must not use `eval`, unpickle arbitrary values, dynamically
import an artifact-supplied class, or execute card-specific code selected by a
pattern file. Registry entries select only reviewed, allowlisted producer and
matcher adapters already present in the implementation.

The implementation must:

* reject arbitrary executable code in pattern artifacts;
* never `eval`, unpickle, or dynamically import an artifact-supplied class;
* allowlist producer IDs and versions in the registry;
* reject path traversal and unexpected artifact files;
* bound candidate and trace text through the existing M2/source policies;
* keep model/network credentials outside the build interface;
* distinguish public source text from semantic authority; and
* treat external proposal/review artifacts as untrusted until exact digest and
  schema validation succeeds.

Pattern matching data may select an allowlisted matcher kind, but it may not
carry executable regex engines, callbacks, or card-specific code. A future
matcher implementation must also address pathological input cost before it is
enabled for the global corpus.

## 24. Explicitly rejected alternatives

### One card-specific extractor per card

Rejected because it creates 38,740 semantic implementations, prevents generic
pattern reuse, increases maintenance cost, and turns card names into hidden
authority.

### LLM as semantic authority

Rejected because model output is not a human review decision, can drift, and
cannot replace M2 evidence, identity, resolution, or review binding.

### Live LLM calls in the authoritative build

Rejected because live responses are not reproducible. If model proposals are
needed, import a pinned proposal artifact and retain `PROPOSED` status.

### Silent skip on extraction failure

Rejected because it violates corpus closure and makes software failure look
like semantic absence. A failure aborts publication; semantic uncertainty gets
an explicit unresolved card outcome.

### One giant global JSON document

Rejected for the baseline because it is less streamable, harder to recover and
inspect incrementally, and unnecessary for 38,740 records. Canonical JSONL
shards retain inspectability while preserving exact bytes.

### Database-first architecture

Rejected because it adds operational state and dependencies before evidence of
need. The artifact is a research/census product and must be independently
reproducible from files.

### M3 defining capability IDs

Rejected because grouping Requirements into capabilities is the M4 contract and
would collapse source-scoped observation into ontology prematurely.

### M3 modifying M2 identity

Rejected because parser spans, pattern IDs, and producer order are extraction
metadata, not semantic claim identity.

### Producer-priority-wins reconciliation

Rejected because execution order or registry order is not semantic authority.
Conflicts remain explicit or unresolved; invalid contract output fails closed.

### Pickle or custom executable rule storage

Rejected for security, portability, and reproducibility reasons. Rule data is
declarative and code is versioned in reviewed adapters.

### Random analysis IDs

Rejected because deterministic source identity already supplies a stable natural
key and random IDs would contaminate reproduction.

### Wall-clock timestamps in identity

Rejected because timestamps make identical semantic runs differ without changing
source, rules, or results. Operational timestamps belong only in diagnostics.

## 25. Open decisions

Core M3 semantics are resolved. The following decisions are genuinely
deferrable and do not block the safe reference architecture.

| OD-ID | Question | Recommended decision | Reason | Deadline | Safe default |
| --- | --- | --- | --- | --- | --- |
| OD-M3-REVIEW-001 | May reviewed pattern rules emit terminal Requirements? | **RESOLVED: no**; only a future explicit review authority may supply terminal claims | Preserves M2 human-review semantics and limits blast radius | Before any terminal-review importer | `PROPOSED` only |
| OD-M3-NEGATIVE-001 | May an ordinary deterministic classifier emit `NO_REQUIREMENTS_APPLICABLE`? | **RESOLVED: no**; only an explicit negative review authority may supply that outcome | Prevents negative extraction results from having stronger authority than positive proposals | Before any negative-authority importer | `UNRESOLVED_ANALYSIS` |
| OD-M3-PATTERN-001 | Which normalized matcher grammar is implemented first? | Start with exact literal/clause matchers; add parameterized/parser levels only with versioned fixtures | Exact matching is easiest to audit and reproduce | Before first producer implementation | Exact source-text reuse only |
| OD-M3-REPORT-001 | What exact report file names are packaged? | Canonical JSON reports with a small report index bound to the analysis manifest | Keeps reports rebuildable and avoids a new tabular dependency | Before report implementation | Summary report only |
| OD-M3-REVIEW-AUTH-001 | When is an external review-authority artifact needed? | Defer until a real review workflow requires terminal bulk import; design it separately | M3 V1 does not need automatic terminal review | Before first importer | No terminal importer |
| OD-M3-CACHE-001 | Should authoritative incremental caching be added? | No for V1; profile full rebuild first | Prevents hidden semantic state and invalidation complexity | After measured rebuild evidence | Full rebuild |

No open decision may change the M1 source identity, M2 Requirement identity,
M2 bundle minimum, producer `PROPOSED` rule, execution-failure publication
gate, or M4 boundary without a new reviewed design.

## 26. Exit gates for this M3 design specification

The following gates are defined and are expected to remain true for this
design-only milestone:

```text
CARD_ANALYSIS_RECORD_BOUNDARY            = DEFINED
ZERO_REQUIREMENT_CARD_SEMANTICS          = DEFINED
PRODUCER_CONTRACT                        = DEFINED
PROPOSAL_AUTHORITY_BOUNDARY              = DEFINED
RECONCILIATION                           = DEFINED
PATTERN_REUSE_MODEL                      = DEFINED
GLOBAL_CORPUS_CLOSURE                    = DEFINED
GLOBAL_ARTIFACT_MODEL                    = DEFINED
MANIFEST_MODEL                           = DEFINED
DETERMINISTIC_ORDERING                   = DEFINED
PARALLELISM_SEMANTICS                    = DEFINED
FAILURE_VS_UNRESOLVED_BOUNDARY           = DEFINED
LLM_BOUNDARY                             = DEFINED
REVIEW_SCALING_BOUNDARY                  = DEFINED
SCHEMA_VERSIONING                        = DEFINED
TESTING_STRATEGY                         = DEFINED
MAINTAINABILITY_BOUNDARY                 = DEFINED

M2_CONTRACT_MODIFIED                     = NO
M4_CAPABILITY_ONTOLOGY_STARTED           = NO
GLOBAL_EXTRACTION_STARTED                = NO
PRODUCTION_CODE_IMPLEMENTED              = NO
```

The design is ready for independent review when the document itself is the
only changed file, the existing frozen repository gates remain green, and the
branch/commit/remote evidence is reported separately from design status.

## 27. Implementation boundary after review

The next authorized action, if independently approved, is a separately scoped
implementation plan. This document does not authorize that plan, M3
production code, corpus-scale extraction, M4 ontology work, PR creation, or
merge.
