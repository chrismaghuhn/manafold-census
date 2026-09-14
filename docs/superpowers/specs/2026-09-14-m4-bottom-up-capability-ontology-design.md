# M4 Bottom-Up Capability Ontology — Design Specification

Date: 2026-09-14
Repository: `https://github.com/chrismaghuhn/manafold-census`
Roadmap: [Issue #2](https://github.com/chrismaghuhn/manafold-census/issues/2)
Milestone: [Issue #7](https://github.com/chrismaghuhn/manafold-census/issues/7)
Status: `DESIGN_ONLY / READY_FOR_INDEPENDENT_REVIEW`

This document is the M4 architecture and specification only. It creates no
production module, schema, ontology data, Requirement-to-Capability mapping,
database, model dependency, engine integration, or implementation plan.

```text
M4_IMPLEMENTATION_PLAN_AUTHORIZED = NO
M4_IMPLEMENTATION_AUTHORIZED      = NO
CAPABILITY_SCHEMA_CREATED          = NO
CAPABILITY_ONTOLOGY_CREATED       = NO
REAL_REQUIREMENT_MAPPING_STARTED  = NO
M5_STARTED                        = NO
PR_AUTHORIZED                     = NO
MERGE_AUTHORIZED                  = NO
```

## Verified baseline and authority

The live repository was fetched and checked before this design was written.
The verified base is:

```text
BASE = 576c9414e8db9682151a8884056835fae1ffc061
```

`main`, `origin/main`, `origin/HEAD`, and the requested base all resolve
to that SHA. `git log 576c9414..origin/main` is empty. The design branch is
created from that clean base:

```text
BRANCH = design/m4-bottom-up-capability-ontology-20260914
```

The current merge commit is `Merge M3 global requirement candidate extraction`
and states that M3 Tasks 1–11 were independently reviewed PASS while M4
remained unauthorized. The merge is PR #15. M2 is merged by PR #14 at
`d73e611b8acbb22ddbbbdfe84eae73b080efe56e`.

### Milestone state

The following is the current repository-grounded state, not a copy of the
stale status text in the parent roadmap body:

| Milestone | Current evidence | State used by this design |
| --- | --- | --- |
| M0 | Closed Issue #3, merged PR #1 at `ed57a31`; deterministic foundation and exact pinned Oracle corpus | `COMPLETE` |
| M1 | Closed Issue #4, merged PR #13; closure report records 38,740 structural records, zero missing/extra/duplicates, and `M1_COMPLETE=YES` | `COMPLETE` |
| M2 | Closed Issue #5, merged PR #14; typed Requirement contract, identity, evidence, review, resolution, bundle, and schema gates | `COMPLETE` |
| M3 | Closed Issue #6, merged PR #15; current `main` contains the implementation and committed closure/conformance evidence | `COMPLETE / MERGED` |
| M4 | Open Issue #7; no M4 production artifact or implementation exists | `DESIGN ONLY` |

Issue #2 still says `main = ed57a31`, `M1 = NEXT`, and M2/M3 are planned.
Issue #7 still says `M4 = PLANNED`. Those issue-body values are historical
documentation gaps and are not used as current implementation evidence. This
task does not edit either issue.

### M3 closure facts

The committed [M3 global corpus closure report](../../reports/2026-09-13-m3-global-corpus-closure.md)
records an offline two-run campaign over the frozen M1 structural artifact:

```text
RUN_A_RECORD_COUNT              = 38,740
RUN_B_RECORD_COUNT              = 38,740
RUN_A_TRACE_COUNT               = 38,740
RUN_B_TRACE_COUNT               = 38,740

RUN_A_MISSING_SOURCE_IDENTITIES = 0
RUN_A_EXTRA_SOURCE_IDENTITIES   = 0
RUN_A_DUPLICATE_IDENTITIES      = 0
RUN_B_MISSING_SOURCE_IDENTITIES = 0
RUN_B_EXTRA_SOURCE_IDENTITIES   = 0
RUN_B_DUPLICATE_IDENTITIES      = 0

M1_M3_IDENTITY_SET_EQUALITY     = PASS
PERSISTED_REREAD                = PASS
CLOSURE_VALIDATION              = PASS

REQUIREMENTS_PRODUCED           = 5
NO_REQUIREMENTS_APPLICABLE      = 0
UNRESOLVED_ANALYSIS             = 38,735
```

The five produced records each contain exactly one `effect/draw_cards`
Requirement with `drawer=source/one/null`, `quantity=exact/2`, and
`review.status=PROPOSED`. The other 38,735 cards are explicit
`UNRESOLVED_ANALYSIS` records because no negative authority was configured and
no other semantic producer was active. They do not mean that those cards have
no Requirements.

The frozen M3 evidence also records:

```text
SOURCE_LOCK_DIGEST             = 4767dccbb518b4009c235bb1ce531f509c0923ba0ebe190936c2dc2d14e2d4bd
M1_STRUCTURAL_MANIFEST_SHA256  = bdc74ec944798a8c1dd7627dae55a795c6fb72d3bbe067d2f2e50412c7155f2b
M1_STRUCTURAL_AGGREGATE_DIGEST = eb215ca6c904c26baa2d8f0a63928e8c9acab5bb9ea9493eacebcdab2fbb86bb
ANALYSIS_MANIFEST_SHA256       = f69cd3890de54278c231bb6bd8fb0125a31903c2b01d85c81ad1e5d732f9276f
```

The recorded campaign input head is `a8d94958a762ce8e6ecfb54a25e739f460c1272f`,
which predates the M3 merge commit. This is not a contradiction: the
authoritative M4 input is the exact M3 artifact identity, especially the
canonical `analysis-manifest.json` SHA-256, not an assumption that the M3
campaign must be rerun at every later Git commit. The generated Run-A and
Run-B directories are ignored and are not present in this checkout. Their
recorded digests are evidence, not locally recomputable files. A future M4
build must independently reread and validate the supplied M3 artifact.

The [M3 reference conformance report](../../reports/2026-09-13-m3-reference-conformance.md)
records synthetic conformance PASS, partition/merge byte parity PASS, and
`PARALLEL_BACKEND = NOT_IMPLEMENTED`. The M3 runtime labels remain unchanged:

```text
PER_TEST_TIMEOUT_ENFORCEMENT      = BLOCKED
LOCAL_COMMAND_TIMEOUT_ENFORCEMENT = EXTERNAL_EXECUTION_ENVIRONMENT
HOSTED_PER_STEP_600S_ENFORCEMENT  = NOT_IMPLEMENTED
```

These labels are not changed by M4 design work.

### Relevant existing authority

The design is grounded in the following current sources:

| Source | Authority used here |
| --- | --- |
| `src/manafold_census/canonical.py` | Existing canonical UTF-8 JSON; sorted object keys; no floats, sets, tuples, timestamps, or Unicode normalization |
| `src/manafold_census/digest.py` | Existing domain-separated SHA-256 and streamed file measurement |
| `src/manafold_census/semantic/model.py` | Immutable `RequirementV1`, `ReviewStatusV1`, `ResolutionStateV1`, provenance, review binding, and resolution invariants |
| `src/manafold_census/semantic/identity.py` | M2 `requirement_id_for`, `wire_digest_for`, and `reviewed_claim_digest_for` projections |
| `src/manafold_census/semantic/kind_payloads.py` | Closed typed M2 payload variants and payload-specific fields |
| `src/manafold_census/semantic/kinds.py` | Closed M2 family/kind vocabulary; family is a validation partition, not a capability family |
| `src/manafold_census/semantic/bundle.py` | Same-source Requirements, explicit relationships, canonical ordering, and cycle checks |
| `src/manafold_census/semantic/evidence.py` and `validate.py` | Source-bound M1 evidence and exact structural validation |
| `src/manafold_census/analysis/model.py` | `CardAnalysisRecordV1` and the three M3 outcomes |
| `src/manafold_census/analysis/manifest.py` | M3 manifest fields, identity-set digest, fixed 16-shard descriptors, and manifest SHA-256 |
| `src/manafold_census/analysis/build.py` and `validate.py` | Single-process reference build, independent reread, closure validation, and atomic publication |
| `src/manafold_census/analysis/patterns.py` | Declarative pattern definition and eligibility; pattern is not semantic authority |
| `src/manafold_census/analysis/producer.py` and `reconcile.py` | Proposal-only producer seam, M2 validation, producer-neutral reconciliation, and explicit disagreement |
| `src/manafold_census/analysis/report.py` | Derived reports downstream of the M3 manifest; reports are not input authority |
| `docs/superpowers/specs/2026-09-12-semantic-requirement-contract-design.md` | M2 ownership and the explicit `Requirement != Capability` boundary |
| `docs/superpowers/specs/2026-09-13-global-requirement-candidate-extraction-design.md` | M3 boundary, proposal/review separation, closure, digest direction, and security rules |
| `docs/superpowers/plans/2026-09-13-global-requirement-candidate-extraction.md` | M3 implementation seams, conformance expectations, and explicit M4 non-start |
| `tests/test_maintainability.py` | Recursive 500-line guard and M3 prohibition of capability/engine/dynamic execution logic |
| `tests/test_resources.py`, `pyproject.toml`, `.github/workflows/ci.yml` | Resource packaging, dependency policy, and offline CI shape |

## Normative M4 boundary

M4 preserves the bottom-up authority chain:

```text
M1 source facts
  → M2 source-scoped Requirements
  → M3 per-card analysis and persisted Requirement corpus
  → M4 reviewed Capability groupings and links
  → M5 global Capability Census publication
```

The crucial distinction is:

```text
Requirement                = one source-scoped semantic need assertion
Requirement family/kind    = closed M2 representation/routing vocabulary
M3 Pattern                = a producer matching definition
M3 Candidate              = a valid M2 proposal emitted for consideration
Capability                = a reusable, reviewed semantic abstraction
Capability link           = an auditable downstream relation to one exact M2 claim
Engine implementation      = a later consumer concern
```

M4 may normalize across Requirements. It may not move semantic meaning
backwards into M2 identity, M3 extraction, or an engine vocabulary.

### What a Capability represents

A Capability is a reviewed, reusable abstraction over one or more observed M2
Requirements. It states the semantic operation or explicitly reviewed
composition that a sufficiently general rules/simulation system would need to
represent, together with typed parameter dimensions and exclusions that define
the abstraction's scope.

A Capability is not an occurrence, a card, a source phrase, a parser rule, a
Requirement kind by itself, a pattern, a Python class, a Rust type, an engine
subsystem, an engine-support claim, or a certification claim.

The capability claim is intentionally narrower than an implementation promise:

```text
Capability = reviewed reusable semantic abstraction
Capability != rules execution
Capability != engine support
Capability != complete Magic semantics
```

### Boundary table

| Concept | Owns | Explicitly does not own |
| --- | --- | --- |
| M2 `RequirementV1` | One source identity, one closed kind/family, typed parameters, evidence, derivation, review, and resolution | Cross-card equivalence, capability names, or global reuse |
| M2 family/kind | A closed wire-validation partition and atomic representation shape | A hierarchy, capability family, engine vocabulary, or coverage claim |
| M3 Pattern | A versioned source matcher, output template, producer binding, and reuse eligibility | Semantic equivalence, M2 terminal review, or Capability authority |
| M3 CardAnalysisRecord | One explicit outcome for one M1 source identity, with zero-or-one non-empty M2 bundle | A zero-Requirement bundle, a Capability, or a proof that unresolved cards have no Requirements |
| Candidate cluster | A deterministic grouping proposal and review worklist | An ontology member, a reviewed semantic definition, or an active link |
| Capability definition | A versioned semantic claim, typed dimensions, exclusions, lifecycle, and review reference | Card names, pattern IDs, source text, producer code, or engine support |
| Requirement-to-Capability link | Exact M3 snapshot, exact M2 Requirement wire/review identity, Capability version, parameter binding, relation, and M4 review | Mutation of the Requirement or an engine acceptance result |
| Derived report | Counts, distributions, ranked worklists, examples, and evolution summaries | Semantic authority or an input to the authoritative manifest |

### Ownership of information

The M2 Requirement retains:

* the source-scoped `requirement_id` and exact typed payload;
* M1 source and structural evidence;
* producer provenance and M2 review/resolution state;
* source-specific relationships inside its bundle; and
* exact semantic uncertainty and unknown paths.

M4 owns:

* the reusable capability claim and its typed dimension contract;
* the stable Capability family/version reference and claim digest;
* explicit Requirement-to-Capability links and parameter bindings;
* mapping dispositions for Requirements that are not currently linkable;
* composition/dependency/specialization assertions between Capability versions;
* M4 review authority, evolution history, and reproduction identity.

Reports own only derived views: representative Requirement IDs, source counts,
pattern frequencies, distribution summaries, candidate ranking, and review
queue state. A report may cite a card or M3 pattern for navigation, but neither
becomes part of Capability identity.

## Granularity discipline

M4 uses an auditable generalization rule rather than a subjective name-based
test. The rule is evaluated over exact typed M2 payloads.

### Generalization rule

A Capability candidate is eligible for review only when all of the following
hold:

* It has an operation anchor consisting of one or more exact M2
  `(family, kind)` pairs, or a reviewed composite whose components already
  have exact Capability references.
* Every semantic difference between the grouped Requirements is either an
  explicitly declared typed dimension or an explicitly declared optional
  dimension. Values are never hidden in a display name or prose label.
* The candidate has a finite, closed set of M2 parameter-path bindings. An
  unregistered path, arbitrary expression, regular expression, or callback is
  not a dimension definition.
* The candidate states what it excludes when the same M2 kind contains a
  materially different operation, actor, zone, timing, selection, event,
  replacement, continuous-effect, information, ordering, or payment shape.
* Its operation and all required dimensions remain meaningful without naming
  a card, source phrase, producer, pattern, engine, or implementation module.

The candidate is rejected as too narrow if a concrete value is being used as
the operation identity. In particular, an exact integer, card name, Oracle
ID, source phrase, pattern ID, producer ID, parser span, or source path must
be a Requirement-side parameter binding or evidence, never a Capability family
identity.

The candidate is rejected as too broad if it erases the operation anchor or
drops a required M2 dimension so that Requirements with materially different
typed shapes would share the same active claim. `do_magic_effect` is not a
valid operation anchor. A grouping across different M2 kinds requires an
explicit typed composition or a separately reviewed family key; name
similarity is insufficient.

### Reusable parameters versus separate Capabilities

The default rule is:

```text
same operation + same typed dimension layout + different dimension values
    = one Capability family/version with different link bindings
```

For example, these Requirements may share one eventual generic draw
Capability if their M2 reviews are accepted and complete:

```text
effect/draw_cards
  drawer = EntityRef(role=source, multiplicity=one, ordinal=null)
  quantity = Quantity(mode=exact, value=2)

effect/draw_cards
  drawer = EntityRef(role=source, multiplicity=one, ordinal=null)
  quantity = Quantity(mode=exact, value=3)
```

The Capability has a `QUANTITY` dimension whose value is bound separately by
each link. It is not `draw_two` or `draw_three`.

A separate Capability family/version is justified only when the difference is
not a value of an existing dimension, for example a changed operation anchor,
changed actor relation, changed zone relation, changed event/replacement
shape, or changed composition semantics. The justification is a reviewed
claim boundary, not a count threshold alone.

### Singleton and outlier discipline

One observed Requirement is enough to create a non-authoritative candidate
cluster. It is not enough for an `ACTIVE` generic Capability by default.

An active Capability requires either:

* at least two exact, accepted, complete Requirements from distinct M1 source
  identities that satisfy the same claim and dimension contract; or
* an explicit `SINGLE_OBSERVATION_GENERALIZATION` review decision proving that
  the abstraction is reusable and not card-specific.

The second route is an exception, not an automatic singleton promotion. Its
review record must state the reusable semantic boundary and exclusions through
the typed claim fields; free-form justification may be retained as review
context but never enters the identity digest.

The default for a one-card case is an explicit M4 `OUTLIER` or `UNMAPPED`
decision, not a one-card Capability. This prevents thousands of fake
Capabilities while keeping unusual Requirements visible.

## Typed parameter dimensions

M4 does not introduce an open parameter language. It introduces a small
closed adapter vocabulary over the already frozen M2 value types.

### Code-owned dimension path registry

Every dimension uses a `path_key` from a code-owned, versioned M4 registry.
The registry maps a key to:

```text
(M2 family, M2 kind, exact parameter path, M2 value type, allowed null/unknown policy)
```

The wire may carry the stable key, but a caller may not invent a path string.
The implementation validates the key against the selected M2 schema and the
typed payload branch. The initial registry is derived from the frozen M2
payload variants in `kind_payloads.py`; it is not a second semantic
vocabulary.

Examples of code-owned keys are conceptually:

```text
DRAW_CARDS_DRAWER       -> draw_cards / /parameters/drawer       / EntityRefV1
DRAW_CARDS_QUANTITY     -> draw_cards / /parameters/quantity     / QuantityV1
MOVE_FROM_ZONE          -> move_between_zones / /parameters/from_zone / ZoneRefV1
MOVE_TO_ZONE            -> move_between_zones / /parameters/to_zone   / ZoneRefV1
MODIFY_CHARACTERISTIC   -> modify_characteristic / /parameters/characteristic / CharacteristicRefV1
```

The exact registry is implementation-owned and versioned with M4. Unknown
keys fail closed. A new M2 kind or a new nested path cannot silently become an
M4 dimension under an old registry version.

M4 V1 treats a nested `SemanticDescriptorV1` as a typed descriptor value by
default. It does not expose arbitrary recursive child paths as an expression
language. A future nested path may be added only as a new code-owned registry
entry with its own tests and version policy.

### Dimension kinds

The `dimension_kind` value is also closed. The initial set is:

```text
ENTITY_REF
QUANTITY
ZONE_REF
CHARACTERISTIC_REF
PARAMETER_VALUE
SEMANTIC_DESCRIPTOR
DURATION
M2_ENUM
BOOLEAN
RELATIONSHIP_ORDINAL
```

The path registry is authoritative for which kind a path supplies. A human
label such as `actor` cannot override a path's typed kind. If a future M2
payload requires a new type, that is a versioned M4 registry extension, not a
free-form dimension.

### Capability dimension wire sketch

This is a wire-shape sketch, not a schema file:

```json
{
  "path_key": "DRAW_CARDS_QUANTITY",
  "dimension_kind": "QUANTITY",
  "required": true,
  "domain": {
    "kind": "ANY_TYPED_VALUE",
    "allowed_enum_values": [],
    "allowed_shapes": []
  },
  "unknown_policy": "EXPLICIT_BUT_NOT_ACTIVE"
}
```

The permitted domain forms are closed:

```text
ANY_TYPED_VALUE   = any value accepted by the registered M2 path
M2_ENUM_SUBSET    = a sorted subset of the registered M2 enum
M2_SHAPE_SUBSET   = a sorted subset of SemanticShapeV1
```

There is no arbitrary predicate, expression, regex, callback, executable
condition, or exact-value capability domain. Concrete integers and strings
remain link bindings. The `allowed_enum_values` and `allowed_shapes` arrays
are typed values, not semantic prose.

Required dimensions must have exactly one compatible binding in an active
link. Optional dimensions may be omitted only when the M2 payload contains
the explicit absent/null branch; omission never means unknown. An unknown M2
value must be represented as an explicit `UNKNOWN` binding with its M2 reason
and path and can never satisfy an active link.

### Requirement link binding wire sketch

```json
{
  "path_key": "DRAW_CARDS_QUANTITY",
  "binding": {
    "state": "KNOWN",
    "value": {"mode": "exact", "value": 2}
  }
}
```

An unresolved value is preserved rather than guessed:

```json
{
  "path_key": "DRAW_CARDS_QUANTITY",
  "binding": {
    "state": "UNKNOWN",
    "reason": "UNKNOWN_SEMANTICS",
    "m2_unknown_path": "/parameters/quantity"
  }
}
```

The implementation extracts the registered path from the exact M2
Requirement wire and compares its canonical typed value with the binding.
It does not trust a duplicated binding value without recomputation.

### Dimension evolution

The following changes alter a semantic claim and require a new
`capability_version` within the same family when the family nucleus remains
valid:

* adding, removing, or renaming a required semantic dimension;
* changing a path key or its M2 value type;
* changing requiredness or the allowed typed domain;
* changing the unknown policy or exclusions; and
* changing an atomic claim into a composition or changing composition roles.

If the operation nucleus itself changes, or a correction splits one abstraction
into distinct semantic abstractions, the result receives a new Capability
family identity and an explicit evolution record. Adding a report annotation,
changing a display name, or adding non-semantic review context does not change
the claim digest or Capability version, although the new M4 manifest must keep
the old artifact available for historical reproduction.

## Capability identity and versioning

Display names are never stable identities. M4 separates four values:

```text
capability_family_id = stable identity of the semantic nucleus
capability_version   = explicit integer revision within that family
claim_digest         = digest of the exact typed semantic claim at that version
display_name         = human-readable navigation text, outside claim identity
```

### Family key and family identity

The family key is a closed, canonical projection containing no card,
Requirement occurrence, pattern, producer, reviewer, filesystem path,
timestamp, or engine data. Controlled M2 parameter path keys are deliberately
included because they identify typed semantic dimensions, not storage
locations:

```json
{
  "family_key_schema": "census.capability-family-key.v1",
  "m2_requirement_schema": "census.semantic-requirement.v1",
  "operation_kinds": [
    {"family": "effect", "kind": "draw_cards"}
  ],
  "dimension_path_keys": [
    "DRAW_CARDS_DRAWER",
    "DRAW_CARDS_QUANTITY"
  ],
  "composition_shape": null
}
```

The family identity is:

```text
capability_family_id = "capfam_" + domain_digest(
    "census.capability-family-id.v1",
    canonical_family_key
)
```

The exact M2 kind/path registry version is included in the canonical family
key so a future incompatible registry cannot collide with a historical
family. A family key is not a display string and is never derived from the
name of a card or an engine.

### Versioned claim

The claim payload is separate from lifecycle and review metadata:

```json
{
  "claim_schema": "census.capability-claim.v1",
  "family_key": "<canonical family key>",
  "capability_version": 1,
  "dimensions": [
    {
      "path_key": "DRAW_CARDS_DRAWER",
      "dimension_kind": "ENTITY_REF",
      "required": true,
      "domain": {"kind": "ANY_TYPED_VALUE"},
      "unknown_policy": "EXPLICIT_BUT_NOT_ACTIVE"
    },
    {
      "path_key": "DRAW_CARDS_QUANTITY",
      "dimension_kind": "QUANTITY",
      "required": true,
      "domain": {"kind": "ANY_TYPED_VALUE"},
      "unknown_policy": "EXPLICIT_BUT_NOT_ACTIVE"
    }
  ],
  "exclusions": [],
  "composition": null
}
```

```text
claim_digest = domain_digest(
    "census.capability-claim.v1",
    canonical_claim_payload
)
```

The full definition wire shape is conceptually:

```json
{
  "schema": "census.capability-definition.v1",
  "capability_family_id": "capfam_<sha256>",
  "capability_version": 1,
  "claim_digest": "<sha256>",
  "claim": "<canonical typed claim>",
  "display_name": "Draw cards",
  "lifecycle": "PROPOSED",
  "provenance": "<closed M4 provenance object>",
  "review_ref": null
}
```

`claim_digest` is recomputed from `claim`; it is not accepted as an
unverified label. The claim digest excludes:

```text
card name, Oracle ID, source locator, source text, pattern ID, producer ID,
reviewer, filesystem path, database row, timestamp, runtime order,
implementation module, engine name, and report counters
```

Provenance may record the M3 snapshot, candidate cluster, or exact Requirement
IDs that motivated a definition, but such basis data is not the capability
identity. It is review-bound provenance and can never turn a source-specific
observation into a generic identity.

### Changes and new versions

The following do not create a new semantic Capability version by themselves:

* changing `display_name` or non-semantic explanatory text;
* adding a derived representative example;
* adding a report-only count; or
* recording an additional, exact provenance source while the claim is unchanged.

The following require a new version or family:

* any change to the claim payload, dimensions, typed domains, exclusions, or
  composition;
* changing the M2 schema or M4 path registry used to interpret the claim;
* changing the operation nucleus; and
* changing a previously atomic capability into a different abstraction.

If the family nucleus remains the same, increment the explicit version and
create a new claim digest. If the nucleus changes, create a new family ID.
There is no in-place mutation of a historical definition.

## Capability lifecycle and review authority

M4 uses the smallest lifecycle vocabulary that separates publication state
from historical state:

```text
PROPOSED
ACTIVE
SUPERSEDED
RETIRED
```

Human review is not hidden in the lifecycle enum. It is an exact, separately
versioned review-authority record. Thus a proposed definition can be
machine-generated, human-drafted, or human-reviewed in a staging artifact,
while only an accepted review plus explicit activation can make it `ACTIVE`.

### State machine

```text
PROPOSED --accepted review + activation--> ACTIVE
    |                                         | \
    | rejected / not selected                 |  \
    v                                         v   v
proposal history                         SUPERSEDED  RETIRED
```

The diagram describes authority transitions, not an implementation workflow.
The exact rules are:

* `PROPOSED` is not ontology authority and may not receive an active mapping.
* A rejected or unselected proposal is retained only in non-authoritative
  proposal history; it is not relabeled `SUPERSEDED`.
* `ACTIVE` requires a valid typed claim, an accepted M4 capability review, and
  an activation recorded in the authoritative manifest.
* `SUPERSEDED` means an explicit successor or split/merge evolution exists;
  old links remain historical and no new active links may target the old
  version.
* `RETIRED` means the version is intentionally no longer used and has no
  replacement assertion; historical links remain valid historical records.
* `SUPERSEDED` and `RETIRED` are terminal for new active mapping. A
  correction requires a new Capability version/family, never a reverse
  transition.

### Review record

The review artifact is a closed M4 authority record, not an authentication
system:

```json
{
  "schema": "census.capability-review.v1",
  "authority_id": "m4.capability-review",
  "authority_version": "1",
  "record_id": "mrv_<sha256>",
  "subject": {
    "type": "CAPABILITY_DEFINITION",
    "capability_family_id": "capfam_<sha256>",
    "capability_version": 1,
    "claim_digest": "<sha256>"
  },
  "decision": "ACCEPTED",
  "reviewer_id": "maintainer:<stable-id>",
  "record_sha256": "<sha256>"
}
```

The subject type is closed to:

```text
CAPABILITY_DEFINITION
CAPABILITY_LINK
MAPPING_DECISION
EVOLUTION
```

`record_sha256` is recomputed from canonical record bytes. The review record
binds the exact claim digest and subject fields. Reviewer identity is stored as
minimal stable workflow metadata; it does not claim external authentication.
The review decision is closed to `ACCEPTED` or `REJECTED`; a missing decision
is pending and is not an authority value.

Only an explicitly authorized maintainer/review operation may produce an
accepted record or activate a Capability. A candidate generator, clustering
algorithm, pattern registry, M3 producer, or model output cannot set
`ACTIVE`, `ACCEPTED`, or an active link.

Conflicting accepted and rejected decisions for the same subject are an
authority disagreement and block active publication until a new explicit
review authority record resolves the disagreement. There is no majority vote,
producer priority, or runtime-order tie-breaker.

## Requirement-to-Capability link contract

M4 links are a downstream layer. They never add a `capability_id` to M2 and
never rewrite an M2 Requirement.

### Link identity

The link claim binds the exact M3 snapshot, exact M2 wire, exact Capability
version, relation, and typed parameter bindings:

```json
{
  "link_schema": "census.requirement-capability-link.v1",
  "m3_analysis_manifest_sha256": "<sha256>",
  "requirement_id": "srq_<sha256>",
  "requirement_wire_digest": "<existing M2 wire digest>",
  "requirement_reviewed_claim_digest": "<M2 reviewed digest or null>",
  "capability": {
    "capability_family_id": "capfam_<sha256>",
    "capability_version": 1,
    "claim_digest": "<sha256>"
  },
  "relation": "DIRECT",
  "parameter_bindings": ["<sorted binding objects>"],
  "composition_context": null
}
```

```text
link_id = "rcl_" + domain_digest(
    "census.requirement-capability-link-id.v1",
    canonical_link_claim
)
```

The link claim excludes the M4 review reference, reviewer, report fields, and
filesystem path. The link record may carry those values outside the claim.
`requirement_wire_digest` is calculated with the existing M2
`wire_digest_for()` helper. `requirement_id` is the existing stable
source-scoped M2 identity; both values are required so a changed Requirement
wire is detectably stale even when its source-scoped identity remains the same.

An active link to an accepted Requirement also records and validates the exact
M2 `reviewed_claim_digest`. A proposal link may carry a null M2 review digest,
but it cannot enter the active ontology manifest.

### Link relation vocabulary

The link relation is closed:

```text
DIRECT
COMPOSITION_MEMBER
```

`DIRECT` means that one exact, complete M2 Requirement is fully represented by
one atomic Capability version and its bindings. `DIRECT` cannot point to a
composite definition.

`COMPOSITION_MEMBER` means that the Requirement supplies one explicitly named
component of a reviewed composite Capability use. The composite definition
lists the component Capability references and component keys. The link points
to the exact component version and carries a composition context that names
the composite version and component key.

There is no untyped `MAPS_TO`, `SIMILAR_TO`, `DEPENDS_ON`, or catch-all edge.

### Link cardinality and ambiguity

The model supports many-to-many relationships with explicit rules:

* one Capability version may explain many exact Requirements;
* one Requirement may have multiple proposed links;
* at most one active `DIRECT` link may explain a Requirement in one mapping
  context;
* multiple active `COMPOSITION_MEMBER` links for one Requirement are allowed
  only when they share a reviewed composition context and the composite
  definition declares every component key;
* a Requirement may not have both an active `DIRECT` link and active component
  links in the same mapping context; and
* a Capability version with no accepted complete supporting Requirement may be
  proposed but not active.

Multiple plausible links are represented as `AMBIGUOUS` in the mapping
decision artifact. They are not resolved by choosing the first candidate,
highest frequency, shortest name, or producer order. An explicitly reviewed
composition is the only route for multiple active component links.

### Mapping decision and preserved non-links

The link file alone cannot represent a Requirement that is not mapped. M4
therefore has a separate one-row-per-Requirement mapping decision artifact:

```json
{
  "schema": "census.requirement-mapping-decision.v1",
  "m3_analysis_manifest_sha256": "<sha256>",
  "requirement_id": "srq_<sha256>",
  "requirement_wire_digest": "<existing M2 wire digest>",
  "disposition": "INSUFFICIENT_EVIDENCE",
  "active_link_ids": [],
  "candidate_link_claims": [],
  "reason": "M2_REVIEW_NOT_TERMINAL",
  "review_ref": null
}
```

The closed dispositions are:

```text
MAPPED
UNMAPPED
AMBIGUOUS
OUTLIER
INSUFFICIENT_EVIDENCE
```

Their meanings are distinct:

| Disposition | Meaning | Active link allowed? |
| --- | --- | --- |
| `MAPPED` | Exact reviewed link set is accepted and satisfies all binding rules | Yes, if link reviews and Capability are also active |
| `UNMAPPED` | No Capability has been selected in this M4 snapshot; this is not a claim that none exists | No |
| `AMBIGUOUS` | Two or more plausible candidate mappings or review interpretations remain | No |
| `OUTLIER` | A reviewed decision says the Requirement is not currently generalizable without a card-specific abstraction | No |
| `INSUFFICIENT_EVIDENCE` | M2/M3 evidence or review state is insufficient for a Capability mapping | No |

The mapping reason is also closed. It uses only codes such as
`NO_REVIEWED_CAPABILITY`, `M2_REVIEW_NOT_TERMINAL`,
`M2_RESOLUTION_INCOMPLETE`, `MULTIPLE_PLAUSIBLE_CAPABILITIES`,
`NO_REUSABLE_GENERALIZATION`, `SPECIAL_CASE`, and
`EXPLICIT_REVIEW_CONFLICT`, selected according to disposition. It is never
an arbitrary expression or executable predicate.

`UNMAPPED` is a coverage state, not a negative semantic authority statement.
`OUTLIER` and `AMBIGUOUS` are authoritative M4 review metadata because they
record an explicit decision about the mapping attempt; they are not
Capabilities and do not alter M2. `INSUFFICIENT_EVIDENCE` preserves the
underlying uncertainty and exact reason.

Every actual persisted Requirement in the selected M3 artifact receives
exactly one current mapping decision. This is an M4 closure invariant. The
decision may be generated as a deterministic `UNMAPPED` default, but a
positive mapping, ambiguity, or outlier classification requires the relevant
M4 review authority. No Requirement may disappear because no Capability was
found.

### Stale-link detection

A link is stale and cannot be active when any of the following is true:

* `m3_analysis_manifest_sha256` is not the exact selected M3 manifest;
* the referenced `requirement_id` is absent from the M3 bundle corpus;
* the stored Requirement wire digest differs from the reread M2 wire;
* an active link claims an M2 reviewed digest that is missing or mismatched;
* the Capability family/version is absent or its claim digest differs;
* a required dimension binding is missing, duplicated, unknown, or mismatched;
* a retired or superseded Capability is targeted for a new active link; or
* the relation/composition context no longer matches the Capability definition.

Staleness is a validation failure for an authoritative build, not an automatic
remap. A new M4 snapshot may produce a new link after explicit review; the old
link remains in the historical artifact.

## Composition, dependencies, and specialization

M4 does not add a generic graph abstraction. It persists only three distinct
edge meanings where the Capability definitions demonstrate the need:

```text
COMPOSES
REQUIRES
SPECIALIZES
```

All edge endpoints are exact `(capability_family_id, capability_version,
claim_digest)` references.

### Edge semantics

* `COMPOSES` is directional from a composite Capability to a component
  Capability. The composite's typed component key, requiredness, and order
  are part of its claim. It means the composite claim is formed from those
  component claims; it does not mean an engine has implemented either one.
* `REQUIRES` is directional from a Capability to a prerequisite semantic
  Capability needed to interpret the claim. It is not a runtime dependency,
  package dependency, or engine-support assertion.
* `SPECIALIZES` is directional from the narrower Capability to the broader
  Capability whose claim it refines. It is not supersession and does not make
  the broader version obsolete.

Shared dimensions are not persisted as edges. A report may derive a
`SHARES_DIMENSION` view from the typed claims; the view has no authority.

### Graph invariants

* self-edges are invalid;
* `COMPOSES`, `REQUIRES`, and `SPECIALIZES` are each acyclic;
* every component reference exists at the exact version and claim digest;
* a new active composite may reference only active, non-retired components;
* an edge cannot target a mismatched claim digest;
* a composition context must cover every required component key exactly once;
* cycles, duplicate component keys, and missing endpoints abort authoritative
  publication; and
* evolution edges are validated separately from semantic dependency edges.

The graph is therefore a small typed relation set, not an arbitrary user
defined graph language.

## Outliers and unresolved semantics

M4 preserves all visible Requirements and distinguishes several reasons for
not producing an active mapping:

```text
M3 UNRESOLVED_ANALYSIS with no bundle
    = no persisted M2 Requirement exists for this M3 card snapshot

M4 INSUFFICIENT_EVIDENCE
    = a persisted Requirement exists, but its M2 evidence/review/resolution
      is not sufficient for an active Capability link

M4 AMBIGUOUS
    = multiple Capability interpretations remain plausible

M4 OUTLIER
    = an explicit review says no reusable abstraction is justified currently

M4 UNMAPPED
    = no mapping has been selected in this snapshot; future mapping remains open
```

An `UNRESOLVED_ANALYSIS` M3 record with `bundle = null` has no Requirement ID
and cannot be used as an M4 Capability input. M4 must not manufacture a
Requirement from the card name, Oracle text, pattern frequency, or unresolved
trace. It may report the count and M3 unresolved group, but it cannot call the
record an unmapped Requirement.

The outlier/mapping decision artifact is authoritative M4 review metadata,
while reports are derived views of it. This preserves explicit decisions
without pretending that an outlier is a semantic ontology member.

## Sparse-current-corpus decision

### Machinery can be designed now

M4 architecture and eventual implementation can be prepared now because its
interfaces do not require broad semantic coverage. The following are valid
M4 machinery against synthetic or empty authoritative sets:

```text
Capability typed model and identity
Capability version/review model
M2 path/dimension validation
Requirement-to-Capability link model
mapping decision and outlier model
composition/evolution validation
M3 input binding
manifest and deterministic reproduction
synthetic conformance fixtures
derived reports and review worklists
```

This is contract machinery, not semantic population.

### No real active member from the current five

The current five Requirements cannot create an `ACTIVE` Capability member.
They are all `review.status=PROPOSED`, even though each has a complete-looking
`draw_cards` payload. M2's review contract deliberately distinguishes a
proposal from a human-reviewed result. M4 therefore cannot claim that the
observed draw phrase is established Capability authority.

A future active-member gate is:

* the supplied M3 artifact rereads and validates against its exact manifest SHA;
* all linked Requirements are present in that M3 bundle corpus;
* every linked Requirement is M2 `ACCEPTED` and `COMPLETE`;
* the Capability claim and all typed dimensions validate;
* default reuse evidence has at least two distinct M1 source identities, or an
  accepted `SINGLE_OBSERVATION_GENERALIZATION` decision exists;
* every active link has exact M3/M2/Capability digests and accepted M4 review;
* composition/evolution edges are valid and acyclic; and
* the authoritative M4 manifest is built, reread, and published atomically.

For the present five, the only truthful M4 staging result would be one
non-authoritative candidate group for `effect/draw_cards`, plus five explicit
`INSUFFICIENT_EVIDENCE` mapping decisions with reason
`M2_REVIEW_NOT_TERMINAL`. It would create no Capability definition in the
authoritative ontology and no active link.

### Claims that remain unmade

With the current M3 input, M4 must not claim:

```text
global Magic Capability coverage
representative Magic Capability distribution
complete Capability vocabulary
semantic closure of the 38,735 unresolved cards
that unresolved cards have no Requirements
engine completeness or engine support
Manafold / Forge / XMage compatibility
card certification or Comprehensive Rules proof
that five proposed Requirements are globally representative
```

It may claim only that the M4 machinery is defined for a frozen M3 artifact,
that the observed five Requirements are eligible for candidate grouping, and
that no active ontology member is authorized from their current review state.

### Future M3 expansion

Each new M3 `analysis-manifest.json` is a new frozen input snapshot. It may
produce:

```text
new persisted Requirements
  → deterministic grouping candidates
  → reviewed Capability proposals
  → links to an existing Capability version when the claim digest matches
  → a new Capability version when dimensions/exclusions change
  → explicit split/merge/supersession/retirement evolution when boundaries change
```

Existing M2 and M3 historical artifacts remain unchanged. A new M3 snapshot
does not make a missing Requirement appear, does not promote old proposals,
and does not silently migrate old links. The M4 parent-manifest reference and
explicit evolution records make the transition inspectable.

## Candidate generation and clustering

Candidate generation is a scalable proposal mechanism, not a semantic
authority.

### Deterministic candidate features

The reference candidate generator reads only actual persisted M2 Requirements
from validated M3 bundles. Its feature projection may include:

* exact M2 family/kind;
* code-owned M2 parameter path keys;
* typed parameter shapes and enum values;
* whether a parameter is present, optional, or explicitly unknown;
* M2 relationship shape where it is part of the reviewed composition input;
* integer variation summaries represented as counts and exact values in a
  review artifact; and
* exact Requirement IDs for navigation and audit.

The candidate identity must not include card names, Oracle text, source paths,
pattern IDs, producer order, reviewer identity, runtime order, or an engine
label. Those values may appear as non-identity provenance or report examples.

An exact-value masking policy is explicit: a value is masked from a grouping
signature only when the corresponding path is declared as a Capability
dimension. The generator cannot mask an operation, actor, zone, timing, event,
selection, replacement, or condition just to increase reuse.

### Candidate cluster wire sketch

```json
{
  "schema": "census.capability-candidate-cluster.v1",
  "m3_analysis_manifest_sha256": "<sha256>",
  "generator_id": "m4.deterministic-shape-grouping",
  "generator_version": "1",
  "candidate_id": "ccg_<sha256>",
  "group_signature_digest": "<sha256>",
  "requirement_ids": ["srq_<sha256>", "srq_<sha256>"],
  "requirement_count": 2,
  "distinct_source_count": 2,
  "parameter_variations": "<typed integer/count summary>",
  "proposed_claim": "<typed Capability claim sketch>",
  "status": "PROPOSED"
}
```

`candidate_id` is a proposal-artifact identity, not a Capability family ID.
It may be recomputed from the exact M3 manifest, generator version, sorted
Requirement IDs, and typed grouping signature. A candidate cluster can be
rejected, split, merged, or replaced without affecting Requirement or
Capability identity.

### Ranked review worklists

The derived worklist is deterministic and maintainer-oriented. It groups many
Requirements behind one review surface and provides:

```text
frequency-ranked candidate groups
distinct source and Requirement counts
typed parameter variation summaries
representative Requirement IDs
M2 family/kind and path-shape summaries
known unknown/unresolved counts
possible split/merge signals
single-card and singleton flags
outlier candidates
current review/mapping state
```

Ranking uses integer counts and stable digest tie-breakers, for example
descending `distinct_source_count`, then descending `requirement_count`, then
ascending `group_signature_digest`. It does not use floating-point confidence
as identity or authority.

Batch review is allowed to reduce navigation cost. A batch decision must
materialize one exact review record and one exact mapping/Capability reference
for every member; a hidden `accept_all_similar` operation is not part of the
contract. If one member fails a binding or authority precondition, it remains
explicitly unmapped/insufficient rather than being silently accepted.

### Optional model-assisted proposals

The project remains fully usable without an LLM or other model. If a model is
ever used, its output enters only as a pinned proposal artifact with:

```text
generator_id
generator_version
input_m3_analysis_manifest_sha256
input_requirement_set_digest
exact output bytes/digest
proposal status = PROPOSED
```

No live model call is permitted in an authoritative deterministic M4 build.
The proposal importer must validate the pinned bytes, exact input identity,
closed wire fields, and candidate-only status. It cannot create a review
record, activate a Capability, or replace deterministic grouping.

## Ontology evolution

Evolution is represented by explicit immutable records, not by mutating old
definitions or inferring relationships from matching names.

### Evolution operations

The closed operation set is:

```text
ADDITION
SPLIT
MERGE
SUPERSESSION
RETIREMENT
```

Each record binds exact old/new Capability references and an accepted M4
evolution review:

```json
{
  "schema": "census.capability-evolution.v1",
  "event_id": "cev_<sha256>",
  "operation": "SPLIT",
  "from": [
    {
      "capability_family_id": "capfam_<sha256>",
      "capability_version": 1,
      "claim_digest": "<sha256>"
    }
  ],
  "to": [
    {
      "capability_family_id": "capfam_<sha256>",
      "capability_version": 1,
      "claim_digest": "<sha256>"
    },
    {
      "capability_family_id": "capfam_<sha256>",
      "capability_version": 1,
      "claim_digest": "<sha256>"
    }
  ],
  "review_ref": "<accepted evolution review>"
}
```

The exact semantics are:

| Operation | Old references | New references | Required result |
| --- | --- | --- | --- |
| `ADDITION` | none | one new family/version | A new reviewed active member with no claim that it covers any unobserved Requirement |
| `SPLIT` | exactly one old version | at least two new references | Old version becomes `SUPERSEDED`; new definitions have distinct reviewed claims |
| `MERGE` | at least two old references | exactly one new reference | All old versions become `SUPERSEDED`; the new claim is reviewed as a distinct abstraction |
| `SUPERSESSION` | exactly one old reference | exactly one successor | Old version remains historical; same-family version increase is preferred when the nucleus remains stable |
| `RETIREMENT` | exactly one old reference | none | Old version becomes `RETIRED`; no replacement or new active links are implied |

Historical Requirement links remain bound to their old Capability reference.
New links to a successor are explicit. Migration is never automatic. A
separate, reviewed migration artifact may be created in a later task if a
consumer needs a cross-version view, but that artifact cannot rewrite the old
link set.

### Evolution validation

The validator requires:

* every old and new reference exists with the exact claim digest;
* operation cardinality matches the table above;
* the old state is compatible with the transition;
* `SUPERSESSION` does not point to the same version and cannot form a cycle;
* split/merge groups are complete and have no duplicate endpoints;
* a retired version has no new active link; and
* evolution review is accepted before the new manifest publishes the state.

An evolution digest covers the operation and exact references, not report
text, reviewer identity, timestamps, or a future manifest digest.

## Artifact hierarchy and wire ownership

M4 uses distinct artifacts because definitions, links, review authority,
evolution, and derived views have different owners and cardinalities.

### Authoritative and derived artifacts

| Artifact | Role | Authority |
| --- | --- | --- |
| `capability-candidate-clusters` | Deterministic or pinned model proposal groups | Non-authoritative proposal |
| `capability-definitions` | Versioned typed Capability claims and lifecycle | Authoritative M4 definition set |
| `capability-review-authority` | Exact accepted/rejected review records | Authoritative review input |
| `requirement-capability-links` | Exact active/historical mapping links | Authoritative downstream mapping |
| `requirement-mapping-decisions` | One explicit current disposition per M3 Requirement | Authoritative M4 mapping coverage |
| `capability-evolution` | Immutable split/merge/supersession/retirement events | Authoritative M4 history |
| `m4-ontology-manifest` | Input bindings, file descriptors, and artifact identity | Root M4 authority |
| `reports/*` and `worklists/*` | Counts, distributions, navigation, and review queues | Derived only |

### Initial layout and scale choice

The initial reference artifact uses canonical JSONL rather than a database:

```text
capabilities.jsonl
review-authority.jsonl
evolution.jsonl
links/0.jsonl ... links/f.jsonl
mapping-decisions/0.jsonl ... mapping-decisions/f.jsonl
m4-ontology-manifest.json
reports/*.json
worklists/*.json
```

Definitions, reviews, and evolution are expected to be much smaller than the
Requirement link set and remain single canonical JSONL files initially. Links
and one-row mapping decisions use 16 deterministic shards keyed by the first
hexadecimal character after the `srq_` prefix in `requirement_id`. This makes
the high-cardinality layer streamable while keeping the reference build
simple. The fixed 16-way layout is a starting contract, not a license to add
parallel execution; a future shard-count change requires a manifest/build
profile version and byte-parity evidence.

Generated data may be large. Semantic definitions and review decisions remain
small, typed, and hand-reviewable; they are not synchronized as one giant
manual file.

### M4 manifest wire sketch

```json
{
  "schema": "census.m4-ontology-manifest.v1",
  "ontology_schema": "census.capability-ontology.v1",
  "build_profile": "census.m4-reference.v1",
  "m3_analysis_manifest_sha256": "<exact canonical M3 manifest SHA-256>",
  "m3_analysis_schema": "census.card-analysis.v1",
  "m2_requirement_schema": "census.semantic-requirement.v1",
  "m2_bundle_schema": "census.semantic-requirement-bundle.v1",
  "m4_dimension_registry_version": "1",
  "parent_m4_manifest_sha256": null,
  "requirement_set_digest": "<M4 requirement-set digest>",
  "capability_file": "<descriptor>",
  "review_file": "<descriptor>",
  "evolution_file": "<descriptor>",
  "link_shards": ["<16 ordered descriptors>"],
  "mapping_decision_shards": ["<16 ordered descriptors>"]
}
```

`requirement_set_digest` is a domain-separated digest over sorted exact pairs
of `requirement_id` and existing M2 `wire_digest_for()` value, with the M3
manifest SHA included in the domain input. It is an M4 audit projection; the
M2 Requirement ID remains owned by M2.

The manifest contains no report bytes or report counters that can affect
semantic identity. A report index, if added, points to the M4 manifest and is
downstream in the same way M3's `report-index.json` is downstream of its
analysis manifest.

## Final digest dependency graph

The selected one-way digest DAG is:

```text
frozen M3 analysis-manifest.json bytes
        │
        ├── exact persisted M2 Requirement wires
        │       │
        │       └── requirement_set_digest
        │
        ├── deterministic candidate clusters (proposal only)
        │
        ├── Capability family keys
        │       └── capability_family_id
        │
        ├── Capability claim payloads
        │       └── claim_digest
        │
        ├── accepted review records
        │       └── review record digests
        │
        ├── links and mapping decisions
        │       └── link/decision claim digests
        │
        ├── evolution records
        │
        └── m4-ontology-manifest.json
                └── derived reports and worklists
```

The exact dependency rules are:

* candidate clusters may read M3 and Requirement data but are not inputs to a
  Capability claim unless a separate accepted review materializes the claim;
* a Capability claim digest depends only on its typed family key, dimensions,
  exclusions, and composition claim;
* a review record depends on the exact subject and claim digest, never on the
  future M4 manifest digest;
* a link depends on the exact M3 manifest SHA, Requirement ID/wire/review
  projection, Capability reference, relation, and bindings;
* mapping decisions depend on exact Requirement/link claim references but not
  on the M4 manifest digest;
* evolution depends on exact old/new Capability references and its review;
* the M4 manifest hashes authoritative files and records the M3 input SHA;
  authoritative files do not hash the M4 manifest; and
* reports/worklists consume the finalized M4 manifest and never feed bytes back
  into it.

This avoids cycles such as definition → review → definition-file digest or
report → manifest → report. The existing `canonical_json_bytes`,
`domain_digest`, and `sha256_bytes` helpers remain the only serialization and
digest implementations.

## M3 input binding

M4 accepts a path to a frozen, already-built M3 artifact. It does not rerun M3
or infer Requirements from source text.

The input adapter must:

* read canonical `analysis-manifest.json` bytes and calculate its exact
  SHA-256;
* validate the M3 manifest wire and all 16 record/trace shard descriptors;
* independently reread M3 records and traces using the existing M3 closure
  validator;
* validate source-lock, M1 structural-manifest, and M2 schema bindings from
  the M3 manifest;
* collect only `RequirementV1` values in non-null M3 bundles;
* reject duplicate Requirement IDs with different wires and reject a
  Requirement whose wire digest or source reference fails M2/M3 validation;
* compute the M4 `requirement_set_digest`; and
* retain M3 outcome counts, including `UNRESOLVED_ANALYSIS`, only as context
  for derived reports.

The M3 outcome rules are binding:

```text
REQUIREMENTS_PRODUCED       + non-empty bundle = Requirements may enter M4
NO_REQUIREMENTS_APPLICABLE  + null bundle      = no Requirement enters M4
UNRESOLVED_ANALYSIS         + null bundle      = no Requirement enters M4;
                                                   do not infer a negative result
UNRESOLVED_ANALYSIS         + non-null bundle  = the actual bundled Requirements
                                                   may enter M4, with M3 unresolved
                                                   context preserved
```

The M4 manifest records the exact M3 manifest SHA rather than duplicating the
M3 producer/pattern registry digests. A report may display those upstream
values after rereading M3, but M4 does not create a second owner for them.

## Determinism and reproduction

The authoritative M4 reference build is single-process and offline. It is a
pure function of:

```text
frozen M3 artifact bytes and manifest
frozen M4 dimension-path registry
reviewed Capability definitions/references
review authority records
reviewed Requirement-to-Capability links/decisions
evolution records
build profile
```

The same frozen inputs must produce byte-identical:

```text
Capability definitions
review records
evolution records
link shards
mapping-decision shards
m4-ontology-manifest.json
derived reports/worklists
all digest values
```

### Ordering

Canonical ordering is explicit:

```text
Capability definitions    = (capability_family_id, capability_version)
Review records            = (subject type, subject stable key, record_id)
Evolution records         = (operation, sorted from refs, sorted to refs, event_id)
Links                     = (requirement_id, relation, capability ref, link_id)
Mapping decisions         = (requirement_id)
Dimension arrays          = path_key order
Binding arrays            = path_key order
Enum/domain arrays        = wire-value order
```

All objects use the existing canonical JSON rules. Arrays are never ordered by
filesystem enumeration, insertion order, reviewer, wall clock, or worker
completion order. No floating-point values appear in identity or canonical
reports where integer counts or numerator/denominator pairs suffice.

### Publication and reread

The reference builder writes a fresh staging directory, validates every input
and output, independently rereads every canonical JSONL line and manifest,
recomputes all descriptors/digests, and atomically publishes only after the
complete artifact is valid. A final output directory is never overwritten.

Any failure before publication leaves only temporary diagnostics and no
authoritative M4 manifest. A retry begins from the same frozen inputs; it does
not resume from hidden semantic cache state.

Parallel or incremental backends are not part of M4 V1. A future optimization
must first preserve the single-process reference output and demonstrate
partition/merge byte parity with explicit tests and a versioned build profile.

## Failure semantics

The following classes remain separate:

| Condition | M4 representation | Publication behavior |
| --- | --- | --- |
| M2 Requirement is proposed, partial, unresolved, or lacks exact review | `INSUFFICIENT_EVIDENCE` or proposal-only link | May publish explicit coverage state; never active mapping |
| Two plausible Capability mappings remain | `AMBIGUOUS` with exact candidate claims | May publish if decision wire is valid; no active link |
| Maintainer decides no reusable abstraction is justified | `OUTLIER` with closed reason and review | May publish; no Capability is created |
| No mapping has been selected yet | `UNMAPPED` | May publish as explicit not-yet-mapped state |
| Two reviewers/authority records disagree | explicit authority disagreement | Abort active publication until resolved by a new review record |
| Link has unknown endpoint, stale version, wrong digest, missing binding, or invalid relation | validation error | Abort; do not downgrade to unresolved |
| Capability definition has duplicate identity or invalid claim | validation error | Abort; do not select a winner |
| M3 manifest/input is missing, noncanonical, stale, or closure-invalid | invalid M3 input | Abort; no M4 manifest |
| M4 wire/schema has unknown fields, wrong type, bad digest, or noncanonical bytes | wire/schema failure | Abort; no M4 manifest |
| Definition/link/evolution review is missing for an active subject | review incompleteness | Keep proposal/unmapped state or abort active publication; never auto-promote |
| Staging write, reread, digest, or atomic replace fails | publication failure | Abort; no authoritative publication |

Software failures are never encoded as semantic `UNMAPPED`, `OUTLIER`, or
`INSUFFICIENT_EVIDENCE`. Semantic uncertainty is publishable only when it is
a valid, explicit M4 decision with the exact Requirement still visible.

## Derived reports and worklists

Reports are non-authoritative outputs built only after the M4 manifest is
finalized. They may include:

```text
requirements per Capability version
Capabilities by M2 family/kind
typed parameter-dimension distributions
active, historical, superseded, and retired counts
unmapped Requirements
ambiguous candidate mappings
outlier groups and reasons
insufficient-evidence Requirements
Capability reuse counts
distinct source-card counts
exact parameter variation summaries
top candidate clusters
review queue sizes
split/merge/supersession/retirement summaries
M3 context: card outcomes, persisted Requirement count, unresolved-card count
```

Reports must label the M3 context clearly. `38,740 analysis records` is not
`38,740 Requirements`, and `5 persisted Requirements` is not global
Capability coverage. A report must not convert `UNRESOLVED_ANALYSIS` into a
zero Requirement assertion.

Counts are integers. If a rate is useful, the canonical report stores an
integer numerator and denominator; a formatted percentage is a derived display
value and never a digest input.

## Testing and conformance strategy

The implementation phase must add tests across the same authority seams. This
section is a test contract, not an implementation plan.

### Unit coverage

Unit tests must cover:

```text
Capability family-key validation
family identity stability and version separation
claim digest and display-name separation
dimension path registry and typed domain validation
required/optional/unknown dimension semantics
link identity and exact M3/M2 binding
parameter extraction and binding equality
DIRECT versus COMPOSITION_MEMBER relations
mapping decision disposition invariants
review subject/claim binding and lifecycle transitions
composition/dependency/specialization edge validation
split/merge/supersession/retirement evolution cardinality
canonical ordering and shard assignment
manifest descriptors, requirement-set digest, and report direction
```

### Negative coverage

The implementation must reject:

```text
Capability identity containing a card name, Oracle ID, source path, pattern ID,
producer ID, reviewer, engine label, runtime order, timestamp, or filesystem path
card-specific Capability family such as draw_exactly_two_cards
catch-all Capability with no operation anchor
unknown dimension/path key
unregistered M2 parameter path
wrong dimension kind for a path
arbitrary dimension expression, regex, callback, or executable value
exact-value domain used to create one Capability per quantity
missing required dimension
duplicate dimension or binding
unknown binding in an active link
binding value that differs from the reread M2 payload
link to an unknown Requirement
link to an unknown Capability family/version
link with a stale Capability claim digest
link with a stale M2 Requirement wire/review digest
active link to PROPOSED, SUPERSEDED, or RETIRED Capability
active link to M2 PROPOSED/PARTIAL/UNRESOLVED Requirement
multiple active DIRECT links in one context
composition link missing a declared component or required component
implicit composition inferred from link count
duplicate Capability identity
generated cluster promoted automatically to ACTIVE
review record for a different claim or subject
conflicting accepted review decisions
invalid lifecycle transition
self-edge, duplicate component, missing endpoint, or cycle
invalid split/merge/supersession/retirement history
silent omission of a persisted Requirement mapping decision
M3 UNRESOLVED_ANALYSIS treated as NO_REQUIREMENTS_APPLICABLE
M3 record with no bundle turned into a synthetic Requirement
M3 manifest SHA mismatch or changed Requirement-set digest
unknown wire fields
noncanonical bytes
digest-cycle attempt
partial publication or stale temporary output presented as authoritative
eval, exec, pickle, dynamic imports, arbitrary Python callbacks, or live model calls
```

### Property tests

Where the repository's test dependencies support them, properties must include:

```text
input Requirement order does not change candidate grouping
mapping/link permutation does not change canonical output
duplicate insertion is idempotent only for the same exact claim
same frozen M3 and reviewed inputs produce identical bytes and digests
changed Capability claim changes claim digest
changed display name does not change family/version/claim digest
historical Capability versions and links remain byte-immutable
shard assignment depends only on Requirement ID
round-trip wire parsing preserves canonical bytes
every Requirement gets exactly one mapping decision
failed validation creates no authoritative manifest
composition/dependency/specialization graphs remain acyclic
```

### Synthetic conformance fixtures

Fixtures are testing material only and must not become claims about unresolved
real cards. The fixture set must include:

```text
two draw Requirements with different exact quantities sharing one candidate
two different operation kinds that must not share a Capability
one accepted complete Requirement mapping directly to one Capability
one Requirement with two accepted composition-member links
unmapped Requirement
ambiguous Requirement with two candidate links
insufficient-evidence Requirement
reviewed semantic outlier
Capability addition
same-family Capability version/supersession
Capability split
Capability merge
Capability retirement
invalid and cyclic composition/dependency/specialization examples
M3 snapshot change that makes an old link stale
```

No synthetic fixture is included in the authoritative real M3 corpus or
Capability ontology data.

## Maintainability and module layout

M4 should add a focused package rather than turn `analysis/` or one
`ontology.py` file into a god object. A proposed future package is:

```text
src/manafold_census/capability/
    __init__.py       # small public exports only
    model.py          # Capability refs, definitions, lifecycle values
    identity.py       # family keys, claim/link/evolution digests
    dimensions.py     # code-owned M2 path registry and typed bindings
    review.py         # M4 review authority and transition validation
    link.py           # Requirement-to-Capability links and dispositions
    evolution.py      # split/merge/supersession/retirement records
    manifest.py       # M4 artifact descriptors and input identity
    candidates.py     # deterministic grouping and proposal worklists
    build.py          # single-process reference build and staging
    validate.py       # independent input/output and graph validation
    report.py         # derived reports only
```

These are proposed module seams, not files created by this task. Each
production module remains at or below the existing 500-line budget, with a
review checkpoint before it approaches the limit. Deep module interfaces are
preferred:

| Module seam | Small interface | Complexity hidden behind it |
| --- | --- | --- |
| `dimensions.py` | resolve a registered path and validate a binding | M2 branch/path/type rules |
| `identity.py` | compute stable typed digests | canonical projections and domain ownership |
| `link.py` | validate one exact mapping relation | M3/M2/Capability binding and cardinality |
| `validate.py` | validate a complete candidate artifact | closure, graph, stale-link, and digest checks |
| `report.py` | build reports from a validated manifest | aggregation and deterministic formatting |

M4 may import the existing public semantic models and identity helpers,
`canonical_json_bytes`, `domain_digest`, `sha256_bytes`, M3 manifest/model
values, and the independent M3 closure validator. It must not redefine M2
identity, source evidence, structural facts, M3 outcome semantics, producer
admission, pattern eligibility, or M3 closure.

The following remain untouched by M4 design and by the future initial M4
implementation unless a separately authorized contract change says otherwise:

```text
M1 structural modules and schemas
M1 source lock and pinned source configuration
M2 semantic modules and schemas
M3 analysis model, producer/pattern registries, closure reports, and run artifacts
M3 source acquisition and corpus campaign code
Manafold, Forge, XMage, or any other engine
M5 census publication and explorer
```

The existing maintainability guard must be extended in a later implementation
task to cover the new package and to forbid executable/artifact-selected
behavior. This design does not edit that guard.

If a later implementation adds normative M4 schemas or synthetic fixtures,
their packaging must follow the existing `pyproject.toml`
`tool.setuptools.data-files` layout and extend `tests/test_resources.py`. M4
generated ontology/link artifacts are outputs, not wheel resources. A fresh
non-editable wheel must resolve the same normative schemas and fixtures without
source-tree path injection. This task creates none of those resources.

## Security and unsafe execution boundary

Capability artifacts are data. They must never be executable programs.

The implementation must reject or avoid:

```text
eval
exec
pickle/unpickle
artifact-selected dynamic imports
arbitrary Python callbacks
arbitrary expressions or regular-expression programs
code stored in Capability definitions
card-specific executors selected by data
live model execution as authoritative build logic
```

Registries may select only allowlisted, reviewed implementation adapters that
already exist in code. Artifact paths must be constrained to the expected
layout; path traversal and unexpected files fail closed. Model-assisted
outputs are untrusted pinned proposal artifacts and remain `PROPOSED` until a
separate human review authority accepts an exact claim.

No Capability field may carry an engine module path, engine class, executable
rule, or support assertion. A later engine consumer may map itself to the
finished independent ontology, but that mapping belongs outside M4 and does
not change Capability identity.

## Cross-milestone boundary and tempting scope leaks

M4 owns:

```text
Capability ontology definitions
Requirement-to-Capability mapping
typed dimensions and binding validation
composition/dependency/specialization semantics
ontology evolution
M4 review and provenance
M3 input binding for M4
M4 deterministic reproduction and reports
```

M4 does not own:

```text
M3 Requirement extraction or new M3 patterns
M3 registry changes or source-lock changes
re-reviewing all 38,740 cards as a hidden prerequisite
M5 final Global Capability Census publication
M5 Census Explorer
M6 semantic quality closure
M7 interaction/higher-order census
M8 engine/deck/set/format coverage
Manafold engine implementation or support certification
Forge/XMage vocabulary import
database or server infrastructure
ML training or live LLM inference
```

In particular, increasing M3 semantic coverage is a separate M3 authorization.
M4 consumes whatever exact M3 artifact is supplied and remains honest about
its coverage.

## Critical audit of Issue #7

Issue #7 establishes the right direction and the important
`Requirement != Capability` and engine-independence boundaries, but it is not
implementation-ready without the contracts below. The findings are an audit
of the issue, not edits to it.

| ID | Severity | Classification | Finding and recommended clarification |
| --- | --- | --- | --- |
| M4-AUDIT-01 | `MAJOR` | Missing invariant / terminology gap | “Global Requirement corpus” is ambiguous against current M3 reality. It must mean “all actual persisted `RequirementV1` values in the selected frozen M3 bundles,” not all 38,740 analysis records. M3 `UNRESOLVED_ANALYSIS` without a bundle is not a Requirement and must not be treated as negative authority. |
| M4-AUDIT-02 | `MAJOR` | Architectural authority gap | The issue's `semantic clustering / review → definitions` flow does not explicitly say that a generated cluster is a proposal. Add the closed promotion gate: only an accepted M4 review plus explicit manifest activation creates `ACTIVE`. |
| M4-AUDIT-03 | `MAJOR` | Identity/versioning gap | Required “stable/versioned identity” does not separate family identity, version, claim digest, and display name. Add the digest projections and state exactly which semantic changes create a new family/version. |
| M4-AUDIT-04 | `MAJOR` | Validation gap | The issue does not bind M4 to an exact M3 manifest SHA and exact Requirement wire set. Add the M3 input anchor, Requirement-set digest, and stale-link checks. |
| M4-AUDIT-05 | `MAJOR` | Mapping/composition gap | “Covered Requirement families” and “dependencies/composition” do not define exact links, cardinality, parameter bindings, ambiguity, many-to-many composition, or historical link preservation. Add the closed link relation and mapping-decision contracts. |
| M4-AUDIT-06 | `MAJOR` | Failure-semantics gap | The issue does not distinguish semantic uncertainty, outliers, review incompleteness, stale links, invalid wires, invalid M3 input, and publication failures. Add fail-closed categories and explicit publish/abort behavior. |
| M4-AUDIT-07 | `MINOR` | Maintainer ergonomics gap | Batch review, frequency-ranked worklists, representative examples, and outlier navigation are implied but not specified. Add deterministic candidate IDs, integer ranking, exact member materialization, and no hidden bulk acceptance. |
| M4-AUDIT-08 | `MINOR` | Provenance/security gap | The issue names representative cards/patterns but does not state that these are evidence/report context and cannot enter Capability identity. Add the identity exclusion list and the optional pinned-model proposal boundary. |
| M4-AUDIT-09 | `MINOR` | Documentation gap | Issue #7 remains `M4 = PLANNED`, which is correct as an authorization state, but parent/child status prose is stale after M3 merge. The issue should later be reconciled with current milestone evidence without weakening authorization gates. |

There is no blocker to completing the M4 design. The `MAJOR` findings are
implementation-authority blockers if left unspecified; this document resolves
them normatively without changing Issue #7.

## Open decisions

Core Capability identity, authority, versioning, mapping, failure semantics,
and M3 binding are closed above. The following residual decisions are
deliberately non-blocking and have safe fail-closed defaults.

| OD-ID | Question | Recommended direction | Deadline | Safe default |
| --- | --- | --- | --- | --- |
| OD-01 | Should the initial code-owned path registry be handwritten or mechanically derived from M2 payload classes? | Generate its inventory mechanically from the frozen M2 branch/key/type table, then review semantic aliases manually. | Before the first M4 implementation commit | Reject any path not present in the checked-in registry |
| OD-02 | When may a single accepted Requirement justify an active Capability? | Require an explicit `SINGLE_OBSERVATION_GENERALIZATION` review with typed exclusions and no source-specific identity. | Before the first singleton candidate is reviewed | Keep it `OUTLIER` or `UNMAPPED` |
| OD-03 | When should model-assisted proposal import be enabled? | Defer until deterministic grouping has been measured against a broad M3 Requirement snapshot and a maintainer documents the review-cost benefit. | Before the first model proposal artifact is admitted | Model importer disabled; authoritative build remains offline |
| OD-04 | Should the link shard count ever exceed 16? | Keep 16 until measured link size or inspection latency requires a change; introduce a new build-profile version with parity evidence if it changes. | Before any shard-count change | Keep the 16-way reference layout |
| OD-05 | How much historical M4 data should a new manifest inline versus reference? | Keep a required `parent_m4_manifest_sha256` and retain immutable prior artifacts; do not inline unbounded history into current definitions. | Before mapping a second M3 snapshot to an existing ontology | Require a parent hash or use a genesis `null` only for the first manifest |
| OD-06 | What external reviewer identifier format should the authority adapter accept? | Use a stable non-empty opaque identifier with no implied authentication semantics. | Before the first external review adapter | Reject missing or unstable reviewer IDs |
| OD-07 | How should report fields evolve without changing ontology authority? | Version derived report schemas independently; reports always bind the finalized M4 manifest and never feed it. | Before the first published M4 report format | Publish only the minimal integer-count report set |

## Design acceptance criteria

This design is implementation-ready for independent review because it defines:

```text
Capability semantic boundary and non-boundary
Requirement/family/pattern/engine/report distinctions
auditable granularity and anti-singleton rules
typed, code-owned parameter dimensions
required/optional/unknown binding semantics
stable family identity, version, claim digest, and display-name separation
closed Capability lifecycle and human review authority
exact Requirement-to-Capability link identity and cardinality
many-to-many composition and ambiguity representation
explicit unmapped/ambiguous/outlier/insufficient states
directional composition/dependency/specialization edges and cycle rules
addition/split/merge/supersession/retirement evolution
exact M3 manifest and Requirement-set binding
one-way digest DAG without report or review cycles
single-process deterministic reproduction and atomic publication
software failure versus semantic uncertainty behavior
derived report boundary
unit, negative, property, and synthetic conformance strategy
solo-maintainer module/dependency/security boundaries
critical Issue #7 audit and residual open decisions
```

The current sparse corpus is represented honestly: M4 machinery is permitted,
one non-authoritative draw candidate group is conceivable, and no real active
Capability or Requirement mapping is authorized from the five proposed M2
Requirements.

```text
M4_DESIGN_SPECIFICATION = READY_FOR_INDEPENDENT_REVIEW
```
