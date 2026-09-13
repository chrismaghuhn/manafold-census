# M2 Semantic Requirement Contract — Design Specification

Status: design specification only; implementation is not authorized.

~~~text
TASK                         = M2_DESIGN_SPECIFICATION
ROADMAP_ISSUE                = #2
MILESTONE_ISSUE              = #5
BASELINE_MAIN                = b7b4b27567e1407d2580ec57f1ce1e2d5dab3cfa
BASELINE_DRIFT               = NO
M1_FROZEN                    = YES
DESIGN_SPECIFICATION         = AUTHORED_PENDING_INDEPENDENT_REVIEW
CONTRACT_CLARIFICATION_01    = APPLIED_PENDING_INDEPENDENT_REVIEW
IMPLEMENTATION_PLAN          = NOT_AUTHORIZED
M2_IMPLEMENTATION            = NOT_AUTHORIZED
GLOBAL_EXTRACTION            = NOT_STARTED
CAPABILITY_ONTOLOGY          = NOT_STARTED
~~~

This document freezes the semantic Requirement contract that a later M2
implementation may implement. It does not implement a model, schema, fixture,
extractor, CLI command, or dataset.

## 1. Status, authority, and verified baseline

The current implementation authority was fetched and verified before this
document was written:

~~~text
origin/main                         = b7b4b27567e1407d2580ec57f1ce1e2d5dab3cfa
PR #13                              = MERGED
PR #13 merge commit                 = b7b4b27567e1407d2580ec57f1ce1e2d5dab3cfa
M1 reviewed head                    = 79b823ca353c87c2add29dfc777cf68371712f5c
Issue #4                            = CLOSED
Issue #5                            = OPEN
~~~

Issue #2 still contains historical progress text such as 'M1 = NEXT'. That
text is stale for implementation status. The merged PR, closed Issue #4,
current 'main', M1 design specification, M1 implementation plan, and M1
closure report are the authority used by this design.

The verified source lock remains the M1 pinned lock:

~~~text
source-locks/scryfall-oracle-v1.json
source_lock_digest  = 4767dccbb518b4009c235bb1ce531f509c0923ba0ebe190936c2dc2d14e2d4bd
source_id           = 27bf3214-1271-490b-bdfe-c0be6c23d02e
source_sha256       = 4d4b77fd2668f789ea97a855dd49e1e505322c56e09771d8d2ffd9f48681d3a0
source_record_count = 38740
~~~

No repository-specific semantic claim in this document relies on the stale
roadmap wording. No M2 implementation was run or added while authoring it.

## 2. Scope

M2 defines a small, typed, versioned, deterministic wire contract for a
semantic requirement assertion derived from, proposed from, or reviewed
against an M1 structural card record.

The contract answers:

> How can one semantic need be represented without losing its source,
> derivation, uncertainty, review state, or deterministic identity?

The contract deliberately stops at a source-scoped requirement assertion.
It does not decide which occurrences are the same reusable capability. It
allows later analysis to cluster or group occurrences without forcing that
decision into the M2 identity.

## 3. Non-goals and forbidden scope

M2 does not:

- extract semantic requirements from all 38,740 cards;
- produce a global card-analysis dataset;
- implement a Magic rules engine, legality checker, or simulator;
- define the final Capability Ontology or its hierarchy;
- define capability dependencies, coverage percentages, or sole blockers;
- map a requirement to Manafold, Rust types, another engine, or certification;
- require an LLM, ML model, heuristic parser, database, or network service;
- change the M1 source lock, structural record, report, checker, or digest rules;
- add a card-named executor vocabulary;
- make a rules citation a correctness certificate;
- make a confidence score a substitute for review;
- define the M3 'CardAnalysisRecord' or global extraction artifact; or
- define an implementation plan.

The familiar terms in the kind table are typed representation shapes. They
are not the M4 capability names, hierarchy, or engine interface.

## 4. Existing frozen dependencies

M2 consumes M1; it does not reinterpret or extend it.

### 4.1 Structural record authority

The only card evidence authority for the M2 representative corpus is
'StructuralCardRecordV1' with schema 'census.structural-card.v1'. Its relevant
identity fields are:

~~~text
oracle_id
source_card_id
source_record_sha256
name / raw structural fields
~~~

M1 preserves raw strings, source array order, face order, absent-versus-empty
values, and opaque related-part values. M2 must not copy a complete structural
record into a Requirement. It references the record and optionally retains a
bounded exact source fragment for review context.

### 4.2 M1 validation and digest foundations

M2 reuses the existing Census foundations:

- 'canonical_json_bytes' for UTF-8, sorted-key, whitespace-free JSON;
- signed-64-bit integer bounds and no floating-point values;
- 'domain_digest' for domain-separated SHA-256 values;
- JSON Schema Draft 2020-12 validation;
- frozen, slot-based Python reference values with defensive copying; and
- fail-closed source and wire validation.

M2-bounded text values use a maximum of 4096 Unicode code points and must also
be encodable as valid UTF-8. The existing JSON Schema 'maxLength' meaning is
the normative length unit; Python validators must not apply a second UTF-8-byte
limit. This rule applies to bounded descriptor labels, unknown hints, question
text, and bounded evidence fragments. Source-preserved strings and stable
identifiers that are explicitly unbounded remain outside this limit.

There is no second M2 canonicalization or digest implementation.

### 4.3 Provenance boundary

The provenance chain remains:

~~~text
M1 pinned source bytes
  -> StructuralCardRecordV1
  -> explicit Requirement evidence reference
  -> Requirement wire value
~~~

'SOURCE_FACT' is an M1 evidence classification. It is not an alternative
Requirement status and cannot be used to make a semantic claim look like a
source fact.

### 4.4 Contract ownership

Ownership is deliberately split:

| Contract concern | Owner | M2 consequence |
| --- | --- | --- |
| Pinned source bytes, structural fields, faces, and source-record identity | M1 | M2 references and validates these facts; it does not redefine them. |
| Requirement assertion, kind/family grammar, typed parameters, evidence-reference union, derivation/review/resolution vocabulary, and fixture bundle | M2 | These are the only semantic contract concepts frozen here. |
| Global per-card analysis, extraction runs, coverage, and corpus-scale proposal aggregation | M3 | No M3 analysis record or global artifact is part of M2. |
| Requirement grouping, equivalence, capability names, hierarchy, and engine-independent ontology | M4 | No capability field or grouping decision enters Requirement v1. |
| Reviewer authentication, chronology, and repository change history | Maintainer workflow/VCS | The wire stores minimal review identity but is not a workflow platform. |

This ownership table is normative: a later consumer must adapt across these
seams rather than moving M3 or M4 concepts into the M2 Requirement model.

## 5. Semantic terminology

The following terms are normative:

| Term | Meaning | Not meaning |
| --- | --- | --- |
| Source fact | A value explicitly retained by M1 from the pinned source. | A rules interpretation. |
| Requirement assertion | One source-scoped assertion of one atomic semantic need. | A global deduplicated capability or a producer-specific occurrence. |
| Requirement | The persisted wire/model form of one assertion. | A card executor or engine method. |
| Requirement kind | A closed M2 representation shape for the need. | The final M4 capability ontology. |
| Requirement family | A small wire-validation partition of kinds. | A capability family or hierarchy. |
| Evidence | A typed reference to source, rules, or an external reviewed artifact. | Proof that review was correct. |
| Proposal | A Requirement with a non-terminal review state. | An accepted semantic result. |
| Reviewed result | A Requirement with an explicit human review outcome. | A guarantee that all parameters are complete. |
| Resolution | The completeness/uncertainty of the semantic representation. | Human approval. |
| Bundle | A small same-source collection plus required relationships. | The M3 global analysis record. |

The invariant is:

~~~text
Source Fact != Semantic Requirement
Requirement != Capability
Capability != Engine Implementation
Generated Proposal != Reviewed Result
Reproducible != Semantically Correct
~~~

## 6. Requirement granularity

### 6.1 Decision

One persisted Requirement is one **atomic, source-scoped semantic need
assertion** with one kind and one parameter payload. A card, face, ability, or
sentence may produce zero, one, or multiple Requirements. Structural field,
face, keyword, and optional fragment locators live in the evidence union; they
are review context and are not producer-defined identity coordinates.

If the same source record yields the same family, kind, and parameter payload
more than once, M2 v1 intentionally stores one Requirement assertion. This
coalescing is what lets independent producers reconcile an identical claim
without agreeing on parser positions. M2 v1 does not preserve a separate
occurrence multiplicity. A later analysis milestone may add a distinct
occurrence envelope if repeated-use multiplicity becomes a demonstrated need;
that envelope must not change this stable Requirement ID.

Examples of distinct assertions include:

- a zone transition;
- an object or token creation need;
- a selection need;
- a characteristic modification;
- a trigger or replacement relationship; and
- a cost need attached to an effect.

Compound text is represented by multiple Requirements plus typed bundle
relationships. A modal parent and its alternatives are not flattened into
one card-level record. A condition, cost, or sequence is not silently lost
when it requires a separate assertion.

### 6.2 Rejected granularity alternatives

- **One Requirement per card:** loses clause-level review and makes one
  unresolved clause contaminate unrelated effects.
- **One Requirement per ability or raw sentence:** ability/sentence boundaries
  are not stable semantic units and hide nested choices and costs.
- **One globally reusable Requirement per semantic need:** performs the M4
  cross-card equivalence decision too early and loses card-specific evidence
  scope.
- **A fully general parent/child semantic graph:** introduces a graph model
  before representative evidence demonstrates the need.
- **'implement_card_named_X':** couples the contract to card identity and an
  executor instead of a reusable semantic need.

### 6.3 Observation versus later normalization

M2 preserves source-scoped assertions as distinct observations. Two equal
payloads from different source records have different Requirement IDs because
their source identities differ. Two producer proposals for the same source,
family, kind, and parameters have the same Requirement ID even when their
evidence locators differ; reconciliation unions or reviews that evidence.
Exact duplicate uses on one source are intentionally one v1 assertion.

M4 may derive a normalized equivalence or capability grouping from these
assertions. M2 has no 'equivalent_to', 'capability_id', or global cluster
field.

## 7. Requirement identity and versioning

### 7.1 Stable identity

The persisted identity is a deterministic content-derived identifier for a
source-scoped semantic claim:

~~~text
requirement_id = 'srq_' + SHA256(
    ASCII('census.semantic-requirement-id.v1')
    + 0x00
    + canonical_json(identity_payload)
)
~~~

The wire pattern is:

~~~text
^srq_[0-9a-f]{64}$
~~~

'identity_payload' contains exactly the source identity, family, kind, and
typed parameters:

~~~json
{
  "identity_schema": "census.semantic-requirement-id.v1",
  "source_identity": {
    "record_schema": "census.structural-card.v1",
    "oracle_id": "...",
    "source_card_id": "...",
    "source_record_sha256": "..."
  },
  "family": "effect",
  "kind": "draw_cards",
  "parameters": {}
}
~~~

The displayed payload is illustrative; the parameter object is the exact
typed payload for the selected kind. The identity payload excludes evidence,
source-lock context, evidence locators, derivation provenance, review
metadata, resolution metadata, and bundle relationships.

### 7.2 Identity invariants

- Review-status changes do not change 'requirement_id'.
- Adding or removing evidence locators does not change 'requirement_id', but it
  does change the review binding and therefore requires review reopening.
- Adding a second derivation record does not change 'requirement_id', but it
  does change the review binding and therefore requires review reopening.
- Changing 'source_lock_digest' alone does not change 'requirement_id' when the
  exact M1 source-record identity is unchanged.
- Changing source record identity, kind, family, or any parameter creates a
  new 'requirement_id' and requires fresh review.
- Changing evidence field/face/fragment context does not change
  'requirement_id'; the changed review-bound content must be reopened.
- Changing a semantic field never mutates an old reviewed record in place.
  The old record remains available in its historical artifact and the new
  record may be related with 'SUPERSEDES'.
- Relationship additions do not change the endpoint Requirement IDs; they
  change the containing bundle's wire digest.
- A source card is part of identity. Cross-card equivalence is intentionally
  left for M4.

### 7.3 Duplicate and collision behavior

An individual Requirement is valid only when its 'requirement_id' equals the
recomputed identity. A bundle rejects duplicate IDs.

If two producers propose the exact same identity, they are not two semantic
Requirements. An explicit reconciliation step may union their distinct
derivation and evidence items into one Requirement. The direct bundle input
must not silently choose one proposal. Conflicting non-identity metadata is a
reconciliation error and fails closed until a maintainer resolves it.

If one ID appears with two different identity payloads, that is an identity
collision and is a hard validation failure; no random suffix or database row
ID is permitted.

### 7.4 Versioning

'census.semantic-requirement.v1' is a closed wire contract. A new kind,
changed parameter meaning, changed identity rule, changed status meaning, or
removed property requires a new major schema and identity domain. A prose
clarification that does not alter accepted bytes or meaning may be documented
without changing the schema ID, but no forward-unknown kind or property is
accepted by a v1 reader.

Producer IDs and producer versions record who produced a proposal; they do not
change M2 semantic versioning and do not enter Requirement identity.

## 8. Requirement wire data model

### 8.1 Individual wire shape

The individual wire object has exactly these required root properties:

~~~text
schema
requirement_id
source
family
kind
parameters
evidence
provenance
review
resolution
~~~

Unknown root properties fail closed. The normative schema ID is:

~~~text
census.semantic-requirement.v1
~~~

The reference model exposes one immutable 'RequirementV1' value and typed
value classes for the nested source, evidence, derivation, review,
resolution, kind, and parameter variants. The implementation may split those
classes across small modules; it must not replace them with an unvalidated
dictionary bag.

The nested root shapes are fixed as follows:

~~~text
source       = SourceRecordRefV1
provenance   = {derivations: [DerivationV1, ...]}
review       = {status, reviewed_by, reviewed_claim_digest}
resolution   = {state, reason, unknown_paths: [string, ...]}
evidence     = [EvidenceV1, ...]
parameters   = exactly the branch payload selected by kind
~~~

Each named nested value is a closed tagged union or fixed object described in
this specification. No nested object gets an implicit extension map.

### 8.2 Source record reference

'source' is a complete immutable reference to one M1 structural record:

~~~text
record_schema        = census.structural-card.v1
source_lock_digest   = lowercase SHA-256
oracle_id            = lowercase canonical UUID
source_card_id       = lowercase canonical UUID
source_record_sha256 = lowercase SHA-256 of the exact M1 source record line
~~~

The source lock digest is included so a Requirement cannot silently move
between pinned source snapshots. A later checker must verify the complete
reference against the selected M1 record and committed source lock; model
construction alone cannot prove that an external record exists.

### 8.3 Source evidence locators

M2 v1 has no producer-owned 'anchor', parser path, AST coordinate, or
occurrence ordinal in the Requirement wire or identity. Source location is
carried only by typed structural evidence. The canonical locator fields are
therefore exact M1 field names plus an optional face index, keyword index, and
bounded exact fragment as defined below. Two producers may cite different
locators for the same source-scoped claim; those locators are evidence to be
reviewed, not identity coordinates.

When 'face_index' is null, a structural field is interpreted in the parent
record. When it is non-null, the field must be one of the M1 face fields:
'name', 'mana_cost', 'type_line', 'oracle_text', 'colors', 'color_indicator',
'power', 'toughness', 'loyalty', or 'defense'. 'keywords', 'produced_mana',
'all_parts', and other parent-only fields cannot be paired with a face index.
The same field name, such as 'name' or 'oracle_text', is unambiguous by the
combination of field and face index.

### 8.4 Evidence references

Evidence is a non-empty list containing at least one structural evidence item
that refers to the Requirement's own source record. The v1 evidence union is:

| Evidence kind | Required information | Purpose |
| --- | --- | --- |
| 'STRUCTURAL_RECORD' | M1 source reference | Whole-record evidence. |
| 'STRUCTURAL_FACE' | M1 source reference and 'face_index' | Face identity without copying the face. |
| 'STRUCTURAL_FIELD' | M1 source reference, field, optional face index | Exact structural field evidence. |
| 'STRUCTURAL_KEYWORD' | M1 source reference, keyword index, exact keyword value | Ordered M1 keyword evidence. |
| 'RULES_CITATION' | Ruleset ID, ruleset version, rule ID, optional artifact digest | Optional external rules context. |
| 'EXTERNAL_REVIEW' | Authority ID, authority version, record ID, record digest | Optional imported reviewed evidence. |

All structural evidence in one Requirement must point to its declared source
reference. 'RULES_CITATION' and 'EXTERNAL_REVIEW' are distinguishable from
card evidence and never confer correctness by their presence.

The fixed evidence union keys are:

~~~text
STRUCTURAL_RECORD = {kind, source}
STRUCTURAL_FACE   = {kind, source, face_index}
STRUCTURAL_FIELD  = {kind, source, field, face_index, fragment}
STRUCTURAL_KEYWORD = {kind, source, keyword_index, keyword_value}
RULES_CITATION    = {kind, ruleset_id, ruleset_version, rule_id,
                     rules_artifact_sha256}
EXTERNAL_REVIEW   = {kind, authority_id, authority_version, record_id,
                     record_sha256}
~~~

Optional values above are explicit nulls, not missing keys. For structural
record/face/keyword evidence, fields that do not apply are null only where
the variant definition permits them. A structural field's 'face_index' is
null for a parent field and non-null for a face field. A keyword evidence item
always uses the parent record and its index/value pair must match the ordered
M1 'keywords' array.

'STRUCTURAL_FIELD' may carry an optional 'fragment' only when the field is
textual. It is an exact, bounded review hint, not a general span system:

~~~text
fragment is absent, or is at most 4096 Unicode code points and valid UTF-8
fragment is not the authoritative source value
fragment must be an exact substring when cross-checked against M1
~~~

M2 does not store character offsets, regexes, parser AST paths, full copied
Oracle text, or host paths. If an exact fragment cannot be safely identified,
the field reference is sufficient.

Rules citations use explicit 'ruleset_id', 'ruleset_version', and 'rule_id'.
An optional exact rules artifact SHA-256 binds a local citation artifact when
one exists. A URL alone is not an authority and is not required.

Evidence identity is distinct from Requirement identity. M2 derives an
evidence ordering/deduplication key with domain
'census.semantic-evidence.v1'; this key is not a Requirement ID and is not
used to make two source-card claims equivalent.

### 8.5 Root-level invariants

The model and schema must enforce:

- all required root keys are present exactly once;
- 'schema' is the fixed v1 value;
- 'requirement_id' matches the recomputed source-scoped claim identity;
- source identifiers and digests use lowercase canonical forms;
- 'family', 'kind', and 'parameters' select exactly one known typed branch;
- evidence is non-empty and contains structural evidence;
- derivation provenance is non-empty;
- review and resolution combinations obey the state rules below; and
- every nested unknown property is rejected.

## 9. Requirement kind/family design

### 9.1 Family is a wire-validation partition

'family' is a small M2 routing partition, not a capability family. It makes
schema validation and later extraction ergonomics clearer while remaining
non-hierarchical:

~~~text
effect     = effect-shape requirements
event      = event-observation or event-replacement requirements
choice     = selection or mode-choice requirements
cost       = payment or cost-modification requirements
control    = conditional composition requirements
reference  = source-keyword reference requirements
unknown    = valid unresolved semantic requirements
~~~

No family has a parent, coverage meaning, engine mapping, or capability ID.

### 9.2 Closed v1 kind vocabulary

The v1 'kind' and family pair is:

| Family | Kind | Purpose |
| --- | --- | --- |
| effect | 'move_between_zones' | Need to move a referenced object/card between zones. |
| effect | 'create_object' | Need to create an object, including a token-like object. |
| choice | 'select' | Need to choose an object, player, card, or zone. |
| effect | 'modify_characteristic' | Need to change a characteristic of a subject. |
| effect | 'apply_continuous_effect' | Need to apply a lasting/continuous modification shape. |
| effect | 'search_zone' | Need to inspect/search a zone and handle a selected result. |
| effect | 'draw_cards' | Need to move card quantity from a draw source to a hand-like destination. |
| effect | 'deal_damage' | Need to assign damage from a source to a recipient. |
| effect | 'create_delayed_effect' | Need to create an effect that occurs under a later timing condition. |
| event | 'trigger_from_event' | Need to react to an event or condition. |
| event | 'replace_event' | Need to replace or modify an event before its normal result. |
| cost | 'pay_cost' | Need to represent a payment/cost obligation. |
| cost | 'modify_cost' | Need to alter a cost shape. |
| choice | 'choose_mode' | Need to choose one or more alternatives. |
| control | 'conditional_effect' | Need to represent a condition attached to an effect shape. |
| reference | 'keyword_reference' | Need to preserve a keyword-derived semantic reference. |
| unknown | 'unresolved' | A semantic need is evidenced but cannot yet be classified in v1. |

These are atomic representation shapes, not final capabilities. For example,
M4 may group 'draw_cards', 'move_between_zones', and other requirements in a
different capability structure, or split one kind into multiple capability
families. M2 makes no such choice.

An unknown producer-supplied 'kind' is invalid. A real semantic need that is
not representable uses the valid 'unresolved' branch with an explicit reason.
Adding a new kind requires a new contract version rather than silently
accepting a string.

### 9.3 Typed parameter payloads

Every kind has a closed parameter object. The schema uses a discriminated
union and the model constructs a typed variant. No branch accepts arbitrary
additional parameter properties.

Reusable parameter atoms are:

- 'EntityRef': a non-executable reference with role 'source', 'target',
  'chosen', 'affected', 'created', 'event_subject', 'controller', 'owner',
  'payer', 'chooser', or 'unknown'; multiplicity is 'one', 'many', 'each', or
  'unknown'; optional ordinal is non-negative.
- 'ZoneRef': one of 'library', 'hand', 'battlefield', 'graveyard', 'exile',
  'stack', 'command', 'outside_game', or 'unknown', with an optional raw label
  only for review context.
- 'Quantity': 'exact' with a signed-64-bit integer, 'all', 'each', 'symbolic'
  with a non-empty label, or 'unknown' with an explicit reason. Exact counts
  used as cardinalities are non-negative.
- 'CharacteristicRef': one of 'power', 'toughness', 'color', 'type',
  'subtype', 'ability', 'controller', 'owner', 'zone', 'cost', 'base', or
  'other' with an explicit label.
- 'Duration': a typed descriptor with shape 'until_end_of_turn', 'this_turn',
  'permanent', 'delayed', or 'unknown'.
- 'ParameterValue': a tagged 'text', 'integer', 'boolean', 'descriptor', or
  'unknown' value. Unknown values are explicit objects, never ambiguous nulls.
- 'SemanticDescriptor': a fixed object with 'shape', 'label', 'subject',
  'object', 'value', and ordered 'children' fields. 'shape' is one of
  'event', 'condition', 'restriction', 'effect', 'replacement', 'duration',
  'cost', 'alternative', or 'unknown'. It is a non-executable description and
  does not form an open-ended map. 'label' is bounded source/review context,
  not a semantic escape hatch.

The 'unresolved' payload reuses this existing closed 'SemanticShapeV1'
vocabulary for 'observed_shape'. It does not introduce a separate
'ObservedShapeV1' wire vocabulary. The exact values are 'event', 'condition',
'restriction', 'effect', 'replacement', 'duration', 'cost', 'alternative', and
'unknown'. 'observed_shape' is a semantic observation shape, not a source
field and not a capability.

The exact v1 parameter keys are:

| Kind | Required parameter keys | Optional parameter keys |
| --- | --- | --- |
| 'move_between_zones' | 'subject', 'from_zone', 'to_zone', 'quantity' | 'cause' |
| 'create_object' | 'object_class', 'quantity', 'characteristics' | 'duration' |
| 'select' | 'chooser', 'subject_kind', 'quantity', 'restriction' | 'targeting' |
| 'modify_characteristic' | 'subject', 'characteristic', 'operation', 'value' | none |
| 'apply_continuous_effect' | 'subject', 'duration', 'effect' | none |
| 'search_zone' | 'searcher', 'zone', 'selection' | 'destination', 'reveal' |
| 'draw_cards' | 'drawer', 'quantity' | none |
| 'deal_damage' | 'source', 'recipient', 'amount' | none |
| 'create_delayed_effect' | 'delay', 'effect' | none |
| 'trigger_from_event' | 'event', 'controller' | 'condition' |
| 'replace_event' | 'event', 'replacement' | none |
| 'pay_cost' | 'payer', 'cost' | none |
| 'modify_cost' | 'subject', 'cost', 'operation' | none |
| 'choose_mode' | 'chooser', 'minimum', 'maximum', 'alternatives' | none |
| 'conditional_effect' | 'condition', 'then_effect' | 'else_effect' |
| 'keyword_reference' | 'keyword', 'keyword_index', 'expansion_state' | 'expansion' |
| 'unresolved' | 'observed_field', 'observed_shape', 'question', 'candidate_kinds' | 'fragment' |

'operation', 'subject_kind', and 'expansion_state' are closed enums;
'observed_shape' is the existing 'SemanticShapeV1' closed enum. The
'candidate_kinds' array contains only 'RequirementKindV1' values. The
'observed_field' value is a controlled M1 source-field locator from this exact
set:

~~~text
record, name, layout, mana_cost, type_line, oracle_text, colors,
color_identity, color_indicator, keywords, produced_mana, power, toughness,
loyalty, defense, hand_modifier, life_modifier, attraction_lights, faces,
all_parts
~~~

'observed_field' and 'observed_shape' are orthogonal: the former says where
the source observation came from, while the latter says which already-known
semantic descriptor shape was observed or remains unknown. 'characteristics'
and 'alternatives' are typed arrays; their
declared ordering is semantic where the source presents an order. The
'unresolved' payload may name candidate v1 kinds but may not invent a new
kind.

For resolution purposes, every semantic parameter enum member whose wire value
is 'unknown' is an explicit unresolved sentinel. This includes UNKNOWN values
of 'EntityRoleV1', 'MultiplicityV1', 'ZoneNameV1', 'SubjectKindV1',
'ModificationOperationV1', 'CostOperationV1', 'ExpansionStateV1',
'SemanticShapeV1', 'QuantityModeV1', 'ParameterValueTypeV1', and
'DurationKindV1'. The explicit tagged 'UnknownValueV1' forms remain unknown as
well. These sentinels are valid in PARTIAL or UNRESOLVED claims, but no such
sentinel may occur in a COMPLETE Requirement. 'RequirementKindV1.UNRESOLVED'
is governed by its dedicated UNRESOLVED rule below.

The payload grammar is deliberately descriptive. It does not evaluate zones,
quantities, targets, legality, timing, payment, or effects.

Free-form descriptor labels are limited to 4096 Unicode code points, must be
valid UTF-8, and are never a
substitute for a typed dimension. A descriptor whose necessary meaning exists
only in 'label', or only in a 'shape=unknown' label/child, cannot appear in a
'COMPLETE' Requirement. It requires an explicit unknown value and
'PARTIAL'/'UNRESOLVED' resolution. A complete descriptor must use its
non-unknown shape together with typed 'subject', 'object', 'value', or typed
children sufficient for the enclosing kind's required parameter.

The generic 'ParameterValue' text branch is allowed only for a parameter key
that explicitly calls for a bounded label or source value. It cannot carry a
whole effect, condition, cost, or event in prose. If a required semantic
dimension exists only as free text, the Requirement is not 'COMPLETE'.

## 10. Structured parameter design

### 10.1 Optionality and unknowns

Null is reserved for a genuinely optional field whose absence has contract
meaning, such as an absent 'else_effect', 'reviewed_by', or optional evidence
fragment. A semantic value that is unknown is represented with an explicit
'unknown' tagged value and named in 'resolution.unknown_paths'.

This prevents the following ambiguity:

~~~text
no else-effect exists  !=  else-effect is required but not understood
~~~

### 10.2 References and quantities

M2 references are roles, not object IDs. 'target', 'chosen', 'source', and
'created' describe the shape of an analysis claim without asserting legality
or a particular engine object. Zones are controlled labels plus an explicit
unknown case; they are not Manafold handles.

Quantities retain exact integers, symbolic labels, or explicit 'all'/'each'
forms. Numeric-looking source text is not silently parsed into an integer. A
producer that cannot justify the numeric interpretation uses a symbolic or
unknown value and a partial resolution.

### 10.3 Conditions, events, costs, and choices

Conditions, events, costs, alternatives, and restrictions use the fixed
'SemanticDescriptor' shape or a dedicated kind parameter. Descriptor children
are ordered. A descriptor is data only; it has no callback, Python expression,
engine object, or executable rule. Its label is review/source context only;
typed dimensions carry the semantic claim.

Modal and nested structures use bundle relationships in addition to these
parameters. The payload describes the local need; relationships preserve the
composition.

### 10.4 Parameter ordering and validation

- Object keys are fixed by the selected branch and canonicalized by the
  existing sorted-key encoder.
- Ordered arrays preserve source or declared semantic order.
- Set-like arrays, such as an unordered characteristic assignment collection,
  are sorted by the canonical bytes of their typed values before serialization
  and reject duplicates.
- Map keys, where a fixed nested object genuinely needs them, are explicit
  controlled names; arbitrary producer keys are forbidden.
- All indexes and counts are signed-64-bit integers with non-negative bounds
  where they are positions or cardinalities.
- Booleans are strict booleans, not integers; floats, NaN, infinity, sets,
  tuples, bytes, executable objects, and host paths are forbidden.

## 11. Derivation, review, and resolution states

The illustrative terms from Issue #5 are intentionally split into orthogonal
dimensions.

### 11.1 Derivation provenance

'provenance.derivations' is a non-empty, canonicalized list. Each entry is:

~~~text
method           = HUMAN_AUTHORED | DETERMINISTIC_RULE | PARSER
                   | HEURISTIC | MODEL | IMPORTED_ANNOTATION
producer_id      = stable non-empty producer identifier
producer_version = stable non-empty producer version
~~~

The list preserves that more than one producer contributed the same exact
identity. A future model or LLM is recorded as 'MODEL' with an explicit
producer/version; no LLM is required by the contract.

'SOURCE_FACT' is not a derivation method. Source facts live in the M1 record
and evidence union.

### 11.2 Review status

'review.status' is one of:

~~~text
PROPOSED
IN_REVIEW
ACCEPTED
REJECTED
~~~

'PROPOSED' is the required initial state for generated output. A producer
adapter may emit only 'PROPOSED'; it cannot claim human review by setting a
terminal state. 'ACCEPTED' and 'REJECTED' are review outcomes and require a
non-null stable 'reviewed_by' plus a current 'reviewed_claim_digest'. There is
no timestamp in the semantic record; repository history or a later workflow
artifact supplies chronology without changing semantic identity.

'SUPERSEDED' is not a review outcome. A later Requirement may point to an old
Requirement with the bundle relationship 'SUPERSEDES'; the old Requirement
retains its prior 'ACCEPTED' or 'REJECTED' review result. No individual
Requirement status is rewritten merely because another assertion supersedes
it.

Review means that a human reviewed the Requirement's evidence, kind,
parameters, and current resolution. It does not mean that the whole card was
reviewed. A card may therefore contain accepted, rejected, proposed, and
unresolved Requirements simultaneously.

'ACCEPTED' means the reviewer accepts the Requirement assertion at its stated
resolution. It does not require 'resolution.state=COMPLETE'.

The review object has exactly these fields:

~~~text
status                 = PROPOSED | IN_REVIEW | ACCEPTED | REJECTED
reviewed_by            = null for PROPOSED/IN_REVIEW, stable ID otherwise
reviewed_claim_digest  = null for PROPOSED/IN_REVIEW, required digest for
                         ACCEPTED/REJECTED
~~~

The binding digest uses domain 'census.semantic-requirement-review.v1' over
the canonical review-bound payload:

~~~text
source identity (record_schema, oracle_id, source_card_id,
                 source_record_sha256; source_lock_digest omitted)
family
kind
parameters
evidence (with source_lock_digest omitted from structural references)
provenance.derivations
resolution
~~~

The review binding covers the reviewed source claim, all evidence, derivation
provenance, and resolution while treating 'source_lock_digest' as snapshot
provenance rather than semantic content. A terminal review is valid only when
'reviewed_claim_digest' equals the recomputed digest. A changed reviewed
content value therefore cannot silently retain 'ACCEPTED' or 'REJECTED'.

### 11.3 Resolution status

'resolution.state' is one of:

~~~text
COMPLETE
PARTIAL
UNRESOLVED
~~~

'resolution.reason' is one of:

~~~text
NONE
INSUFFICIENT_EVIDENCE
AMBIGUOUS_SOURCE
UNSUPPORTED_SHAPE
CONFLICTING_INTERPRETATIONS
UNKNOWN_SEMANTICS
~~~

'resolution.unknown_paths' is an ordered list of JSON Pointer-like paths into
the 'kind' or 'parameters' value that contain unresolved information. It is
empty only for 'COMPLETE', and non-empty for 'PARTIAL' or 'UNRESOLVED'.

Cross-field rules are:

- 'COMPLETE' requires 'reason=NONE', no unknown paths, no unknown parameter
  values, no semantic enum sentinel with wire value 'unknown', and
  'kind != unresolved'. A 'keyword_reference' is COMPLETE only when
  'expansion_state=EXPANDED' and its typed 'expansion' is present; the
  'UNEXPANDED' and 'UNKNOWN' states are necessarily PARTIAL for a known kind.
- 'PARTIAL' requires a known v1 kind and at least one explicit unknown value or
  unknown path.
- 'UNRESOLVED' requires 'kind=unresolved' or a conflict reason with an
  explicit unresolved path. It is a valid semantic result, not a malformed
  input.
- 'resolution.state' never promotes a proposal to 'ACCEPTED'.
- 'review.status=ACCEPTED' with 'resolution.state=PARTIAL' or 'UNRESOLVED' is
  valid when the reviewer accepts the existence of the need but not a complete
  classification.
- Any change to evidence, derivation provenance, or resolution keeps the same
  Requirement ID only when source identity, family, kind, and parameters
  remain byte-equivalent; it must reopen review by setting
  'review.status=IN_REVIEW' and clearing the review binding before a new
  terminal review.
- Any change to source identity, family, kind, or parameters creates a new
  Requirement ID and requires fresh review. A 'PARTIAL' to 'COMPLETE' change
  follows this same split: replacing an unknown parameter value creates a new
  ID; changing only resolution metadata keeps the ID but requires reopening.
- A terminal review with a stale or missing binding digest is invalid, not an
  implicitly accepted historical state.

### 11.4 Invalid input versus unresolved meaning

The distinction is normative:

| Situation | Persisted result |
| --- | --- |
| Missing key, wrong type, unknown property, bad digest, unknown kind, or invalid parameter branch | Validation error; no Requirement is accepted. |
| Valid M1 evidence shows a semantic need but no v1 kind fits | 'kind=unresolved', 'resolution=UNRESOLVED', reason 'UNSUPPORTED_SHAPE' or 'UNKNOWN_SEMANTICS'. |
| A known kind has one or more unknown dimensions | Known kind with explicit unknown parameter values and 'PARTIAL'. |
| Two interpretations remain plausible | Separate proposal Requirements, plus 'CONFLICTS_WITH' in a bundle; an unresolved conflict record may also be retained. |
| Referenced M1 record is missing or cannot be verified | 'BLOCKED' at validation/report level; never guessed or rebound. |

## 12. Review lifecycle and immutability expectations

### 12.1 What is reviewed

The review unit is one Requirement, including:

- its M1 source reference and structural evidence locators;
- its structural/rules/external evidence references;
- its typed kind and parameters;
- its derivation provenance; and
- its resolution state.

Review is not a card-level boolean. A new Requirement may be added to a card
without invalidating unrelated accepted Requirements.

### 12.2 Changes after review

- Evidence additions that merely corroborate the same claim retain the
  Requirement ID but invalidate the old review binding. The reconciler must
  reopen the record to 'IN_REVIEW' and obtain a new terminal review; it may
  not keep 'ACCEPTED' silently.
- If new evidence reveals that the asserted kind or parameters were wrong, the
  corrected assertion receives a new ID and may use 'SUPERSEDES'; the old
  record remains immutable with its historical review outcome.
- Changing source identity, family, kind, or parameters always creates a new
  Requirement and requires fresh review. The source-lock wrapper alone is not
  an identity change and does not invalidate the review binding.
- Changing 'resolution' from partial/unresolved to complete reopens the same
  ID only when no identity payload field changes. Replacing an unknown
  parameter value creates a new ID; a pure resolution-state update clears the
  old binding and requires new explicit acceptance.
- Derivation provenance may gain an additional exact producer entry without
  changing identity, but that change also reopens review. Conflicting status
  metadata is not auto-merged.

The reference model is frozen and defensive: caller-owned lists, mappings,
and nested values are copied into immutable values; 'to_wire()' returns fresh
JSON-compatible containers; 'from_wire()' accepts only validated wire values.
The artifact is immutable once written. A later artifact snapshot may contain
a revised representation under the same ID only under the lifecycle rules
above.

## 13. Confidence and evidence strength

The authoritative M2 Requirement has **no numeric confidence field and no
confidence enum**.

The evidence list, derivation method, review state, and resolution state are
the smallest defensible evidence metadata. Numeric model confidence is
producer-specific, poorly calibrated across producers, and must not influence
acceptance or substitute for a human review. A future producer may keep its
score in a non-authoritative sidecar keyed by 'requirement_id' and producer
version; that sidecar is outside M2 identity and wire truth.

## 14. Requirement relationships and hierarchy

### 14.1 Bundle ownership

Relationships are owned by a small 'RequirementBundleV1', not by a general
graph database and not by the individual Requirement identity. The bundle is a
same-source envelope used for representative validation and later handoff.

Its exact root shape is:

~~~text
schema         = census.semantic-requirement-bundle.v1
source         = one M1 source reference
requirements   = non-empty sorted RequirementV1 values
relationships  = canonical relationship edge list
~~~

All Requirements and all relationship endpoints in a bundle must reference
the same source record. A multi-face card is still one source record; each
Requirement may identify its face in structural evidence.

M2 does not define a 'CardAnalysisRecord'. The bundle is a minimal fixture and
relationship envelope, not a claim that every card has been analyzed.

### 14.2 Required relationship vocabulary

The only v1 relationship types are:

| Type | Direction and use |
| --- | --- |
| 'PARENT_OF' | A composition/choice/conditional parent to a nested child need. |
| 'ALTERNATIVE_OF' | Two peer modal alternatives; endpoints are canonicalized. |
| 'CONDITION_OF' | A condition requirement to the effect it conditions. |
| 'COST_OF' | A cost/payment requirement to the effect or choice it belongs to. |
| 'SEQUENCE_BEFORE' | Earlier occurrence to later occurrence; 'ordinal' is required. |
| 'CONFLICTS_WITH' | Two competing interpretations; endpoints are canonicalized. |
| 'SUPERSEDES' | A newer reviewed representation to the older Requirement. |

There is no generic 'depends_on', arbitrary edge label, engine dependency, or
capability edge in v1. A relationship has fixed keys:

~~~text
type
from
to
ordinal = null except where SEQUENCE_BEFORE or ordered PARENT_OF requires it
~~~

Bundles reject self-edges, missing endpoints, duplicate edges, cross-source
edges, cycles in 'PARENT_OF' or 'SUPERSEDES', and non-canonical endpoint order
for symmetric relationships. A 'choose_mode' Requirement can be a parent of
branch Requirements; branch peers can be 'ALTERNATIVE_OF'. A condition or cost
is represented as its own Requirement and connected with the corresponding
typed relation.

## 15. Keywords

M1 keyword presence is source evidence only. A source keyword does not imply
that its rules meaning is understood.

The 'STRUCTURAL_KEYWORD' evidence item carries the top-level ordered keyword
index and exact source keyword string. A 'keyword_reference' Requirement may
record 'expansion_state=UNEXPANDED', 'EXPANDED', or 'UNKNOWN':

- 'UNEXPANDED' or 'UNKNOWN' uses 'resolution.state=PARTIAL' while the
  keyword-reference kind is known. If the need itself cannot be classified,
  the producer uses 'kind=unresolved' and 'resolution.state=UNRESOLVED'.
- 'EXPANDED' requires typed expansion parameters/evidence; the keyword source
  item alone is not enough.
- A COMPLETE 'keyword_reference' therefore requires 'EXPANDED' plus a present
  typed expansion whose required dimensions are themselves complete. The
  'UNEXPANDED' and 'UNKNOWN' states are valid unresolved knowledge only in a
  PARTIAL known-kind Requirement.
- A keyword may produce several Requirements, each with its own structural
  evidence locator
  and evidence. There is no one-keyword-one-capability rule.

An optional rules citation can support a keyword-derived interpretation, but
it cannot silently change review or resolution state.

## 16. Rules evidence

Rules citations are optional evidence items. They must identify:

~~~text
ruleset_id
ruleset_version
rule_id
optional rules_artifact_sha256
~~~

Card evidence and rules evidence remain separate. A citation may explain why
a reviewer accepted a semantic interpretation, but its presence does not
make a proposal accepted, does not resolve unknown parameters, and does not
certify compatibility with an engine.

M2 does not require a Comprehensive Rules citation for every representative
Requirement. Structural evidence is sufficient for a valid proposal; review
may remain unresolved where rules context is necessary.

## 17. Derivation and future producers

The contract is producer-neutral. The allowed derivation methods cover:

~~~text
human entry
deterministic extraction rule
parser
heuristic
model / LLM
imported annotation
~~~

Each producer entry includes an explicit stable ID and version. A producer
must emit 'review.status=PROPOSED', must include structural evidence, and must
use 'unresolved' or explicit unknown values rather than guessing.

Only a review operation may produce a terminal review state. The contract
records that state and reviewer ID but does not pretend to authenticate a
human; repository review and the maintainer's normal change history remain
the operational authority.

## 18. Canonical wire, schema, and digest contract

### 18.1 Normative schemas

M2 owns exactly two normative schemas:

~~~text
schemas/semantic-requirement.v1.schema.json
schemas/semantic-requirement-bundle.v1.schema.json
~~~

The individual schema contains the nested evidence, provenance, status,
parameter, and kind definitions. The bundle schema references the individual
schema through a local, offline schema registry. A separate evidence schema is
not justified because evidence has no independent artifact in M2. A
'card-analysis-record.v1' schema belongs to M3 and must not be added here.

### 18.2 Canonical JSON

M2 uses the existing 'canonical_json_bytes' rules exactly:

- UTF-8, no BOM, no insignificant whitespace, no trailing newline;
- object keys sorted by Unicode code point;
- strings preserved as supplied with no Unicode normalization;
- only null, strict booleans, signed-64-bit integers, strings, arrays, and
  objects with string keys;
- no floats, sets, tuples, bytes, paths, timestamps, randomness, or callbacks;
- fixed object keys and 'additionalProperties=false'; and
- array ordering follows the semantic ordering rules in this document.

For every bounded M2 text field, the normative limit is 4096 Unicode code
points plus valid UTF-8 encodability. JSON Schema 'maxLength' and Python
model validation must express that same code-point boundary; a separate
UTF-8-byte limit is not part of the v1 contract.

'to_wire()' returns fresh mutable JSON-compatible lists/dicts. A previous
'to_wire()' result may be mutated by a caller without changing the model or a
later digest.

### 18.3 Digest domains

The following domains are reserved:

~~~text
census.semantic-requirement-id.v1
census.semantic-evidence.v1
census.semantic-requirement-wire.v1
census.semantic-requirement-bundle.v1
census.semantic-requirement-review.v1
~~~

'requirement_id' uses the identity domain and identity payload defined above.
The full Requirement wire digest uses 'census.semantic-requirement-wire.v1'
over the complete canonical wire object. It is derived, not an additional
mutable field in the Requirement and therefore cannot become self-referential.
The bundle digest uses the bundle domain over its complete canonical wire.

'reviewed_claim_digest' uses 'census.semantic-requirement-review.v1' over the
review-bound payload defined in Section 11.2. The full wire digest includes
'source_lock_digest' and review metadata, so changing the source snapshot or
review state changes artifact bytes even when the stable Requirement ID is
unchanged.

Semantic identity and artifact byte identity are distinct:

~~~text
requirement_id       = stable source-scoped semantic claim identity
wire_digest          = exact current Requirement representation identity
bundle_digest        = exact current bundle representation identity
artifact file digest = exact bytes of a later artifact file
~~~

Evidence, review, resolution, and derivation changes may change wire/bundle
digests without changing 'requirement_id'.

### 18.4 Ordering

- A bundle's 'requirements' array is strictly ascending by 'requirement_id'.
- Evidence items are sorted by their derived evidence key; exact duplicates
  are rejected.
- Derivation entries are sorted by '(method, producer_id, producer_version)'
  and exact duplicates are rejected.
- Relationship edges are sorted by '(type, from, to, ordinal)' after applying
  symmetric endpoint canonicalization.
- 'candidate_kinds' is unique and lexicographically sorted.
- Source-local path arrays, alternatives, descriptor children, and sequence
  arrays preserve declared/source order.
- Set-like typed arrays are canonically sorted as specified by their branch.

## 19. Immutability and fail-closed parsing

The later Python reference model must preserve the project principles:

~~~text
constructed semantic values cannot be changed through caller mutation
to_wire() returns fresh JSON-compatible values
wire parsing fails closed
unknown properties fail
invalid values fail
~~~

Nested lists become tuples or equivalent immutable values. Nested maps become
immutable mappings. 'from_wire()' accepts JSON-shaped lists and objects only;
internal tuple/mapping forms are construction details, not a second wire
format.

The model validates local invariants. A source-aware validator separately
loads the referenced M1 record and validates oracle/source identity, source
lock, face index, field membership, keyword index/value, and optional fragment
substring. Missing pinned evidence is 'BLOCKED', not a reason to substitute a
different source.

## 20. Representative validation corpus

M2 uses a small reviewed corpus only. It does not claim semantic coverage of
the pinned dataset.

### 20.1 Fixture selection rule

The implementation may select at most twelve source-record cases, with one
case allowed to cover multiple rows below. The exact cards are not named in
this design; later selection must verify each 'oracle_id', 'source_card_id',
'source_record_sha256', face index, and field against the pinned M1 corpus.
No unverified card name is a fixture authority.

The minimum fixture matrix is:

| Case | Required shape |
| --- | --- |
| 1 | Simple single Requirement with complete resolution. |
| 2 | One source record with multiple atomic Requirements. |
| 3 | Modal choice, alternatives, and bundle relationships. |
| 4 | Multi-face record with separate face evidence locators. |
| 5 | Source keyword with unresolved or unexpanded semantics. |
| 6 | Triggered text with an event/condition relationship. |
| 7 | Replacement-like text. |
| 8 | Continuous-effect shape and characteristic modification. |
| 9 | Cost payment and cost modification. |
| 10 | Zone transition and object/token creation. |
| 11 | Selection/target-like parameters and a delayed effect. |
| 12 | Difficult/outlier text containing a partial or unresolved interpretation. |

The case count is a representational test budget, not a sample-size claim. If
one verified source record covers multiple rows, fewer than twelve records may
be used. If the matrix cannot be satisfied, the fixture review must add the
smallest number of records necessary and document why; it must not expand to
global extraction.

### 20.2 Fixture review

Each fixture bundle is reviewed at Requirement granularity. The review checks
that it demonstrates the contract dimension, not that the whole source card
has been exhaustively interpreted. A fixture may intentionally include
'PROPOSED', 'ACCEPTED', 'REJECTED', 'PARTIAL', and 'UNRESOLVED' records to
exercise state separation.

The fixture corpus must include at least one valid accepted-but-partial case,
one unresolved keyword or outlier case, and one conflicting-proposal pair.
No fixture may be used to infer global coverage statistics.

## 21. Per-card analysis question and M3 ownership

M2 does not define or generate the roadmap's eventual per-card analysis
record. A minimal 'RequirementBundleV1' is necessary only to test multiple
Requirements, source scoping, and relationships on representative fixtures.

M3 owns the future 'CardAnalysisRecordV1', including:

- one record for every pinned Oracle identity;
- analysis-level status and coverage accounting;
- the global requirement candidate extraction artifact;
- extraction provenance at corpus scale; and
- global reports and reproducibility evidence.

M2's bundle must not acquire M3 fields such as global analysis status,
coverage, extraction timestamp, parser run, or card completeness claims.

## 22. M2/M3 boundary

Until M2 is independently reviewed and frozen, the following are forbidden:

~~~text
iterating all 38,740 cards for semantic extraction
global Requirement candidate dataset generation
global parser, heuristic, ML, or LLM inference
semantic coverage statistics
bulk candidate clustering or deduplication
global CardAnalysisRecord generation
~~~

Representative fixtures, model/schema tests, source-aware reference
validation, and deterministic wire reproduction are allowed. A passing
fixture does not authorize M3.

## 23. M2/M4 boundary

M4 owns the bottom-up Capability Ontology. M2 therefore does not decide:

- final capability names;
- capability hierarchy or aliases;
- capability dependencies or composition;
- coverage or support percentages;
- sole blockers or certification levels; or
- engine mappings.

The M2 kind vocabulary is a closed, typed input grammar. It has no capability
IDs, capability names, Manafold IDs, Rust type names, engine support state, or
coverage field. M4 may cluster several Requirements of one kind, split a kind,
or form groups that cross the M2 family partition.

## 24. Validation and negative-test matrix

The later M2 implementation must define tests at the model, schema, source
aware, and fixture-envelope seams. The tests are contract tests, not global
semantic extraction tests.

| Test area | Required positive/negative proof |
| --- | --- |
| Wire round trip | Every typed branch round-trips to equal immutable values. |
| Canonical bytes | Repeated serialization is byte-identical and has no whitespace/newline drift. |
| Deterministic digest | Identity, evidence key, wire digest, and bundle digest are stable across process/order changes. |
| Producer-neutral identity | Same source identity, family, kind, and parameters produce one ID despite different producer evidence locators; changing only source lock preserves that ID. |
| Source-record identity change | Changing 'source_record_sha256', source card ID, kind, family, or parameters produces a new ID. |
| Unknown properties | Root and nested unknown properties fail closed. |
| Wrong schema | Wrong schema ID or unsupported major version fails closed. |
| Status combinations | Invalid review/resolution combinations fail; accepted-plus-partial succeeds; stale review bindings fail. |
| Proposal separation | Generated adapters emit only 'PROPOSED'; terminal states require reviewer metadata and a current binding digest; rules evidence never promotes status. |
| Unresolved | 'unresolved' and its reason/unknown paths round-trip as a valid Requirement. |
| Partial | A known kind with explicit unknown parameter values round-trips and cannot serialize as complete. |
| COMPLETE unknown sentinels | Every semantic enum value 'unknown' and keyword 'UNEXPANDED'/'UNKNOWN' fails COMPLETE; EXPANDED keyword references require typed expansion. |
| Source/face provenance | Oracle/source IDs, record SHA, source lock, field, face index, keyword index, and fragment are checked against M1. |
| Invalid source identity | Uppercase/malformed UUIDs, bad digests, mismatched lock, and missing record fail. |
| Parameter validation | Every kind accepts only its fixed keys, atom types, enums, and bounds. |
| Review binding | A terminal review with changed evidence/provenance/resolution digest fails; reopening clears the binding; source-lock-only changes preserve it. |
| Descriptor escape hatch | A label-only or unknown-shape descriptor cannot justify 'COMPLETE'; typed dimensions are required. |
| Ordering | Requirements, evidence, derivations, candidates, set-like arrays, and relationships follow their declared ordering rules. |
| Immutability | Mutating constructor input or prior 'to_wire()' output cannot alter a model or digest. |
| Duplicate identity | Duplicate bundle IDs, duplicate evidence/derivation keys, and identity collisions fail closed. |
| Review binding | Evidence, provenance, or resolution changes invalidate the old terminal binding; source-lock-only changes do not. |
| Schema/model parity | Representative valid wires pass both schema and model; each negative mutation fails both at the intended seam. |
| Fixture adequacy | The twelve-row matrix is satisfied by the smallest verified fixture set; no global count is asserted. |
| Capability independence | No 'capability_id', capability hierarchy, engine ID, Manafold ID, or support state enters wire/model/schema. |
| Engine independence | No engine object, executable callback, Rust type, or engine dependency is accepted. |
| Global extraction guard | M2 commands/tests never enumerate the full corpus or write a global analysis artifact. |
| Module LOC guard | Every production module remains at or below the project 500-line limit. |
| Bounded text parity | Multibyte and ASCII boundary cases agree at 4096 Unicode code points across Python and JSON Schema; valid UTF-8 remains required. |

Expected failure classes are 'ValueError'/schema validation failure for
malformed or unsupported wire, 'BLOCKED' for unavailable unverifiable M1
evidence, and explicit non-PASS status for incomplete semantic resolution.

## 25. Threat and failure analysis

| Failure mode | M2 mitigation | Residual handling |
| --- | --- | --- |
| Silent semantic guessing | Closed kinds, explicit unknown values, unresolved branch, and fail-closed unsupported shape. | Human review may still be wrong; M6 quality work owns that risk. |
| Proposal becomes truth | Producers emit 'PROPOSED'; review is orthogonal and terminal states require explicit reviewer metadata. | Authentication of a human remains workflow/repository responsibility. |
| Source provenance is lost | Full M1 source reference, explicit evidence union, source-aware cross-checker, no full-source copy. | Missing pinned bytes is 'BLOCKED'. |
| Card-specific requirement explosion | Atomic reusable kind shapes and no card names/executors; source card is identity context only. | M4 may still find bad decomposition; fixtures expose it early. |
| Premature capability ontology | M2 family is only a wire-validation partition; no capability fields or hierarchy. | M4 must review any later grouping. |
| Stringly typed parameter drift | Closed discriminated kind union, fixed parameter keys, typed atoms, 'additionalProperties=false'. | New shapes require a versioned contract change. |
| Status contradictions | Orthogonal review/resolution fields with explicit cross-field invariants. | Invalid combinations are rejected rather than normalized. |
| Review becomes stale after edits | Terminal review binds a digest of source identity, evidence, provenance, and resolution; any bound-content change reopens review. | VCS preserves historical snapshots. |
| Identity instability | Content-derived source/kind/parameter identity excludes producer locators, evidence, status, source-lock wrapper, and host/runtime data. | Exact source-record changes intentionally create new IDs; unchanged records retain IDs across locks. |
| Duplicate equivalent proposals | Same source/kind/parameter identity is reconciled explicitly even when producer locators differ; direct bundles reject duplicate IDs; cross-card claims remain distinct. | M4 owns cross-card grouping. |
| Fixture overfitting | A small dimension matrix includes modal, face, keyword, outlier, partial, and unresolved shapes; no global claims. | M3 must test corpus-scale behavior independently. |
| Global extraction starts early | M2 exit gate and explicit M3 prohibition; no global artifact schema or command. | Any attempted global run is out of scope and must stop. |
| Engine-specific contamination | Role-based references and descriptive descriptors only; no engine fields/dependencies. | Later consumers must adapt rather than redefine M2. |
| Rules citation treated as proof | Rules evidence is optional and typed separately; it cannot change review/resolution. | Reviewers must record their decision independently. |
| Raw source duplication drifts | M1 references are authoritative; fragments are bounded hints checked as substrings. | Fragment mismatch fails source-aware validation. |
| Recursive descriptor becomes a hidden bag | Descriptor shape and fields are fixed, labels are bounded context only, a label/unknown shape cannot yield 'COMPLETE', children are ordered, and arbitrary keys/callbacks are forbidden. | New typed descriptor shape requires v2. |

## 26. Maintainer ergonomics and module seams

The reference implementation should use a few deep modules with narrow
interfaces and strong local validation rather than a framework. The proposed
seams are:

~~~text
semantic/model.py       immutable public Requirement and nested value interface
semantic/kinds.py       closed kind/family registry and typed payload validation
semantic/evidence.py    evidence union and source-aware evidence checks
semantic/identity.py    identity payload, evidence key, and digest functions
semantic/bundle.py      bundle and relationship validation
semantic/validate.py    schema/model/source cross-check orchestration
~~~

These are ownership constraints, not an implementation task sequence. A
maintainer may combine or split them if each module remains cohesive and no
production module exceeds 500 lines. There must be one authoritative definition
for each kind, parameter, status, and relationship vocabulary; schemas and
tests must not carry hand-synchronized alternate enums.

The public interface should be small:

~~~text
RequirementV1.to_wire()
RequirementV1.from_wire(value)
RequirementV1.requirement_id / wire_digest()
RequirementBundleV1.to_wire()
RequirementBundleV1.from_wire(value)
validate_requirement_against_structural_record(...)
~~~

Callers should not need to know the internal representation of frozen tuples,
mapping proxies, or canonical digest payloads. No database, plugin system,
generic graph library, or runtime semantic executor is justified by M2.

## 27. Explicit decision table

| Question | DECISION | RATIONALE | REJECTED ALTERNATIVES | CONSEQUENCES |
| --- | --- | --- | --- | --- |
| Requirement granularity | One atomic source-scoped semantic claim; exact same-source/kind/parameter duplicates coalesce. | Preserves review locality while removing producer occurrence dependence. | One/card, one/ability, producer-specific occurrence identity, generic graph. | Multiple distinct claims share a card; repeated-use multiplicity is deferred. |
| Requirement identity | 'srq_' plus SHA-256 over source identity (without source lock), family, kind, and typed parameters. | Deterministic and producer-independent. | Random UUID, row ID, timestamp, host path, parser path, producer ID. | Same exact claim reconciles across producers; cross-card claims remain distinct until M4. |
| Source-lock identity | Required in source/provenance and full wire digest, excluded from stable Requirement ID and review binding. | Avoids global ID churn when an unchanged record appears in a new lock. | Snapshot-specific IDs for every lock, omitting source provenance. | Exact source-record changes still create new IDs; artifact bytes remain snapshot-bound. |
| Evidence additions | Excluded from identity but included in review binding. | Evidence can grow without inventing a new claim, while review cannot silently remain accepted. | Hash full record including evidence/status, or retain terminal review blindly. | Reconciler reopens review and obtains a new terminal binding. |
| Parameter changes | Create a new identity. | A changed semantic assertion must not mutate history. | In-place ID mutation, version counter only. | Use 'SUPERSEDES' for reviewed replacements. |
| Requirement versioning | Closed v1; new kinds/meanings require a new major contract. | Strict readers cannot safely interpret unknown branches. | Open-ended minor enum, permissive 'extra', unversioned JSON. | Conservative evolution and explicit migrations. |
| Kind/family representation | Closed 'family' plus discriminated 'kind' and typed branch payload. | Type safety without making M4 the contract owner. | Giant capability enum, arbitrary kind/JSON bag, raw text only. | New semantic shapes require deliberate contract work. |
| Parameter representation | Fixed per-kind objects plus typed atoms/descriptors and explicit unknowns; every semantic 'unknown' enum sentinel is unresolved. | Supports partial semantics without executable rules and prevents sentinel values from masquerading as COMPLETE. | Generic JSON map, callbacks, engine objects, null-as-unknown, silently accepted UNKNOWN enums. | More schema code, but COMPLETE/partial parity is explicit. |
| Source evidence | Typed structural record/face/field/keyword references with bounded optional fragments. | Auditable and sufficient without copying M1. | Full source duplication, character-span framework, URI dereference. | Source-aware validation is required for face/field checks. |
| Face linkage | 'face_index' in structural evidence; source record remains parent identity. | Preserves exact M1 face order and scope without producer anchor identity. | Parent/face inheritance, face names as IDs, separate card identity. | Multi-face claims remain same-record assertions. |
| Derivation model | List of producer/version entries, orthogonal to review. | Multiple producers may produce the same exact identity. | Single giant status, producer in ID, hidden provenance. | Explicit reconciliation is needed for duplicate proposals. |
| Review model | 'PROPOSED', 'IN_REVIEW', 'ACCEPTED', 'REJECTED'; terminal states require reviewer ID and 'reviewed_claim_digest'; 'SUPERSEDES' is a relationship only. | Human review is distinct from generation, resolution, and replacement lifecycle. | Model confidence as approval, 'SUPERSEDED' as review outcome, card-level boolean, timestamps as identity. | Accepted-but-partial is valid; stale bindings fail; old review outcomes remain auditable. |
| Review binding | Digest binds source identity, evidence, derivations, and resolution; bound changes reopen review; source-lock-only changes do not. | Prevents evidence/provenance/resolution edits from silently retaining a terminal review. | Reviewer flag without content binding, blind accepted metadata retention. | A new terminal review is required after reviewed-content changes. |
| Resolution model | 'COMPLETE', 'PARTIAL', 'UNRESOLVED' with explicit reason/paths; COMPLETE excludes tagged unknown sentinels and requires EXPANDED keyword references. | Represents uncertainty without malformed-data ambiguity. | Silent semantic guessing, null everywhere, one giant combined status enum. | Consumers must handle unresolved results explicitly. |
| Confidence | No authoritative confidence field. | Scores are producer-specific and not review. | Numeric probability, coarse confidence authority. | Sidecar scores may exist outside M2. |
| Relationship model | Minimal bundle edges: parent, alternative, condition, cost, sequence, conflict, supersedes. | Enough structure for representative nested cases. | General semantic graph, arbitrary edges, no relationships. | M3/M4 can extend only with a demonstrated need. |
| Keyword model | Keyword evidence plus 'keyword_reference'; UNEXPANDED/UNKNOWN is PARTIAL, while COMPLETE requires EXPANDED typed expansion. | Source keyword presence is not keyword meaning. | Automatic keyword semantics, keyword-as-capability, ignore keyword provenance. | Rules/evidence may support later review. |
| Rules citations | Optional typed evidence with explicit ruleset/version/rule. | Auditable context without mandatory rules dependency. | URL-only citation, mandatory citations, citation=proof. | Structural-only proposals remain valid. |
| Canonical wire | Reuse existing Census canonical JSON and SHA-256 domains. | Prevents a second incompatible identity system. | YAML, CBOR, Python repr, insertion-order JSON. | All v1 outputs are reproducible. |
| Schema ownership | Two schemas: individual Requirement and minimal bundle; evidence nested. | Few authoritative files and clear M3 boundary. | Separate schema per nested type, M2 analysis schema. | M3 owns 'CardAnalysisRecordV1'. |
| Per-card analysis | Not in M2; only fixture bundle. | Prevents accidental global extraction scope. | Full card analysis now, no grouping envelope. | M3 must define coverage/status independently. |
| Representative corpus | Up to twelve verified source-record cases covering a fixed shape matrix. | Small but dimensionally meaningful validation. | Hundreds of cards, named unverified cards, all-corpus sample. | No semantic coverage statistic is claimed. |
| Extension mechanism | New closed schema/kind version after review. | Avoids permissive semantic dumping ground. | Runtime plugins, arbitrary extensions, unknown-field tolerance. | Evolution is slower but auditable. |
| M2/M3 boundary | M2 freezes contract and fixtures only; M3 applies it globally. | Milestone responsibilities remain reviewable. | Start global inference while designing. | No global data may be generated here. |
| M2/M4 boundary | M4 owns grouping, capability names, hierarchy, and engine independence. | Preserves bottom-up Census ontology. | Put capability IDs in Requirements. | M4 consumes Requirements as observations. |

## 28. Proposed implementation decomposition constraints

The future implementation may be decomposed into independently reviewable
slices, but this document does not authorize or enumerate an implementation
plan. Any decomposition must preserve these constraints:

1. The individual model, nested typed variants, and two schemas must be kept in
   parity by focused tests.
2. Identity construction must have one implementation and one test vector;
   no caller may assemble 'requirement_id' manually.
3. Source-aware validation must reuse M1 'StructuralCardRecordV1' and must not
   read a second source or dereference related-part URIs.
4. Proposal producers must have an interface that cannot default to a terminal
   review state.
5. Bundle relationship validation must be separate from individual identity
   validation, so a standalone Requirement remains useful.
6. Model, schema, and source-aware errors must be fail-closed and classified as
   validation failure versus unavailable evidence ('BLOCKED').
7. No implementation slice may create a global extraction command, global
   artifact, capability vocabulary, engine adapter, database, or LLM service.
8. Production Python modules remain at or below 500 lines, and tests must
   cover the public interfaces rather than private representation details.
9. The only repository files authorized by the implementation phase are the
   M2-owned semantic modules, the two normative schemas, focused tests, the
   small reviewed fixture material, and narrowly necessary documentation.
10. M1 files, Task 00 files, Task 01 files, CLI commands unrelated to M2, CI,
    source locks, and generated global data remain unchanged unless separately
    authorized by a later milestone.

## 29. M2 exit gates

M2 may be considered complete only when an independently reviewed
implementation demonstrates every gate below honestly:

~~~text
REQUIREMENT_CONTRACT_VERSIONED        = PASS
REQUIREMENT_MODEL_SCHEMA_PARITY       = PASS
REQUIREMENT_ID_DETERMINISTIC          = PASS
REQUIREMENT_WIRE_CANONICAL            = PASS
REQUIREMENT_WIRE_ROUND_TRIP           = PASS
PRODUCER_NEUTRAL_IDENTITY             = PASS
REQUIREMENT_PROVENANCE_DEFINED        = PASS
SOURCE_FACE_PROVENANCE_VALIDATED      = PASS
DERIVATION_STATUS_EXPLICIT            = PASS
PROPOSAL_REVIEW_SEPARATION            = PASS
REVIEW_BINDING_INTEGRITY              = PASS
UNRESOLVED_STATE_SUPPORTED            = PASS
PARTIAL_STATE_SUPPORTED               = PASS
RELATIONSHIP_VALIDATION               = PASS
IMMUTABILITY                           = PASS
REPRESENTATIVE_FIXTURES_VALID         = PASS
NO_CARD_SPECIFIC_EXECUTORS            = PASS
NO_CAPABILITY_ONTOLOGY_DEPENDENCY     = PASS
NO_ENGINE_DEPENDENCY                  = PASS
NO_GLOBAL_EXTRACTION                  = PASS
MODULE_LOC_BUDGET                     = PASS
M1_FROZEN_CONTRACT_PRESERVED          = PASS
~~~

An unrun gate is 'NOT_RUN', an unavailable pinned evidence dependency is
'BLOCKED', and a malformed or contradictory contract result is 'FAIL'. No
M2 implementation claim may use a fixture pass as evidence of global semantic
correctness.

## 30. Explicit later-milestone decisions

The following are intentionally out of M2 and are not unresolved architecture
inside this contract:

- M3 decides the global 'CardAnalysisRecordV1' and all-corpus candidate
  extraction artifact.
- M3 decides whether and how producer proposals are aggregated at corpus scale.
- M4 decides bottom-up Requirement clustering, equivalence, capability names,
  capability hierarchy, and capability relationships.
- M6 decides semantic quality closure, broader review policy, and any rules
  certification evidence.
- M7 decides higher-order interaction and cross-requirement analysis.
- M8 decides consumers and any Manafold or other engine adapters.

Those later decisions must consume this M2 contract rather than back-porting
engine or capability concepts into Requirement v1.

## 31. Authorization boundary

This document authorizes design review only. It does not authorize:

~~~text
production code
schemas
fixtures
tests
CLI changes
CI changes
global semantic extraction
M3
M4
an implementation plan
a pull request
merge
~~~

The next permitted action after independent review is an explicitly
authorized M2 implementation plan. Until that approval exists:

~~~text
IMPLEMENTATION_PLAN_AUTHORIZED = NO
M2_IMPLEMENTATION_AUTHORIZED   = NO
NEXT_TASK_AUTHORIZED           = NO
PR_AUTHORIZED                  = NO
MERGE_AUTHORIZED               = NO
~~~

## 32. M2 Contract Clarification 01 — Task 4 cross-layer closure

This clarification records two normative corrections found during the Task 4
schema/model review. It changes no wire key, kind, family, evidence variant,
digest domain, or Requirement identity rule. It must be independently reviewed
before the corresponding implementation fix is authorized.

### 32.1 COMPLETE and explicit unknown sentinels

**DECISION**

`COMPLETE` means that no unresolved semantic meaning remains anywhere in the
typed parameter tree. In addition to `UnknownValueV1`, `shape=unknown`, and
label-only descriptors, every semantic parameter enum member whose wire value
is `unknown` is an unresolved sentinel and is forbidden under `COMPLETE`.
This includes the `UNKNOWN` members of `EntityRoleV1`, `MultiplicityV1`,
`ZoneNameV1`, `SubjectKindV1`, `ModificationOperationV1`, `CostOperationV1`,
`ExpansionStateV1`, `SemanticShapeV1`, `QuantityModeV1`,
`ParameterValueTypeV1`, and `DurationKindV1`.

`keyword_reference` has one additional closed rule: `UNEXPANDED` and `UNKNOWN`
are valid only as `PARTIAL` for a known kind. A `COMPLETE` keyword reference
must be `EXPANDED` and must carry a typed expansion whose own required
dimensions satisfy the same COMPLETE rules. `RequirementKindV1.UNRESOLVED`
continues to require `UNRESOLVED` resolution.

**RATIONALE**

An enum sentinel is an explicit statement that a semantic dimension is not
known. Treating it as complete would contradict the existing unknown-value and
keyword contracts while allowing the schema and model to certify incomplete
claims.

**REJECTED ALTERNATIVES**

Treating only `UnknownValueV1` as unresolved, accepting `UNEXPANDED` as
complete, or relying on human review to compensate for an unresolved enum all
silently promote incomplete semantics.

**CONSEQUENCES**

The next coordinated implementation fix must update the recursive model
unknown scan, complete keyword validation, complete-schema branches, and
positive/negative parity tests. No Task 5 bundle may rely on the old behavior.

### 32.2 Bounded text length authority

**DECISION**

The authoritative M2 bounded-text limit is **4096 Unicode code points**, with
valid UTF-8 encodability still required. JSON Schema Draft 2020-12 `maxLength`
and Python model validation use this same code-point unit. A separate
UTF-8-byte limit is not part of the M2 v1 contract.

**RATIONALE**

JSON Schema `maxLength` is defined over string length/code points, while a
byte-count rule would require a second non-portable validator beside the
normative schema. Code-point parity is deterministic across the project’s
Python model and schema consumers and still rejects invalid Unicode encoding.

**REJECTED ALTERNATIVES**

Keeping a hidden 4096-byte Python rule beside `maxLength: 4096` creates
model/schema drift for multibyte text. Removing the bound would weaken the
bounded descriptor/evidence context contract.

**CONSEQUENCES**

The next coordinated implementation fix must change every bounded-text
consumer that still counts UTF-8 bytes, including the existing primitive and
structural-fragment validators, to count Unicode code points after validating
UTF-8. It must add ASCII and multibyte boundary tests and keep source-preserved
unbounded strings/identifiers outside the cap. The schema’s existing
`maxLength: 4096` remains the correct representation after this alignment.

~~~text
M2_CONTRACT_CLARIFICATION_01 = APPLIED_PENDING_INDEPENDENT_REVIEW
PRODUCTION_FILES_CHANGED     = 0
SCHEMA_FILES_CHANGED         = 0
TEST_FILES_CHANGED           = 0
IMPLEMENTATION_FIX_AUTHORIZED = NO
TASK_5_AUTHORIZED             = NO
~~~
