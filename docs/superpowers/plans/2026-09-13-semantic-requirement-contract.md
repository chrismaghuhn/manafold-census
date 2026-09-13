# M2 Semantic Requirement Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task after independent authorization. Steps use checkbox syntax for tracking.

**Goal:** Implement the frozen M2 semantic Requirement contract as immutable typed Python values, two offline JSON Schemas, source-aware validation, a small reviewed representative fixture set, and deterministic contract tests without starting M3 or M4.

**Architecture:** Add one cohesive semantic package behind a small public interface. Split primitives, closed kind payloads, evidence, identity/review binding, individual Requirement values, bundles, and source-aware validation into focused modules that each remain at or below 500 lines. Reuse the M1 StructuralCardRecordV1, existing canonical JSON, existing SHA-256 domain separation, and the repository schema-resource loader. M2 produces no global card-analysis artifact and makes no CLI, CI, engine, database, or LLM changes.

**Tech Stack:** Python 3.12+, standard-library dataclasses/enum/json/hashlib/pathlib, existing jsonschema/referencing validation, pytest, Ruff, mypy, setuptools resource packaging, and the frozen M1 structural model. No new runtime dependency.

---

## Authorization and execution protocol

This plan is authorized by the approved M2 design review, but no numbered
implementation task is authorized by this plan.

~~~text
DESIGN_SPECIFICATION = docs/superpowers/specs/2026-09-12-semantic-requirement-contract-design.md
DESIGN_HEAD          = 003de7ce53477157bcac23b4c6d21869dba46e13
TASK_4_CONTRACT_CLARIFICATION = APPLIED_PENDING_INDEPENDENT_REVIEW
BRANCH               = feat/m2-semantic-requirement-contract
BASELINE_MAIN        = b7b4b27567e1407d2580ec57f1ce1e2d5dab3cfa
M2_IMPLEMENTATION     = NOT_AUTHORIZED
PR                   = NOT_AUTHORIZED
MERGE                = NOT_AUTHORIZED
~~~

For every numbered task:

1. obtain explicit authorization for exactly that task;
2. execute only that task and its declared files;
3. use test-first steps: write focused failing tests, observe the failure,
   implement the smallest contract slice, and rerun the focused tests;
4. run the task's focused tests and focused static checks;
5. run the complete regression gate below; every command must exit 0 for a
   task to be reported PASS;
6. run the shared preservation checks below;
7. stage only the declared files;
8. run git diff --cached --check;
9. create one standalone commit with the task's exact commit message;
10. push only feat/m2-semantic-requirement-contract;
11. verify the remote branch head equals the local task commit;
12. report the exact SHA, parent SHA, changed files, gates, and findings; and
13. stop with NEXT_TASK_AUTHORIZED=NO.

Push authorization is not PR authorization. PR authorization is not merge
authorization. No task may start M3 global extraction or M4 capability work.

### Shared preservation checks

Run these commands before and after every authorized task:

~~~powershell
git status --short --branch
git diff --name-only
git diff --cached --name-only
git diff -- source-locks/scryfall-oracle-v1.json config/sources/scryfall-oracle.v1.json
git diff -- src/manafold_census/models.py src/manafold_census/canonical.py src/manafold_census/digest.py src/manafold_census/corpus src/manafold_census/source src/manafold_census/structural
git diff -- .github justfile pyproject.toml src/manafold_census/cli.py
~~~

The expected result is that only the current task's declared files change.
M1 source locks, foundation models, canonicalization, digest domains, corpus,
source acquisition, structural models/checkers, CLI, CI, and Justfile remain
unchanged.

The scope check must union tracked changes with untracked files:

~~~powershell
$tracked = @(git diff --name-only)
$untracked = @(git ls-files --others --exclude-standard)
$all = @($tracked) + @($untracked)
$bad = $all | Where-Object {
  $_ -match '^(source-locks|config|\\.github|justfile|pyproject\\.toml|src/manafold_census/(models|canonical|digest|corpus|source|structural|cli))'
}
if ($bad) { $bad; throw "M1 or out-of-scope file changed" }
~~~

If a task needs to change an M1 contract, a source lock, a second canonical
system, or an engine-specific type, stop as BLOCKED.

### Mandatory per-task regression gate

Run this complete repository gate after the task-focused checks and before
staging the task commit:

~~~powershell
python -m pytest -q
ruff format --check .
ruff check .
mypy src/manafold_census
~~~

The expected result is zero test failures, zero formatting differences, zero
Ruff findings, and zero mypy findings. If a command cannot be run for a
documented environmental reason, report that gate as NOT_RUN and do not report
the task as PASS.

---

## File map and ownership

Writing this plan creates none of the implementation files below.

### Semantic production package

Create the following cohesive modules:

- src/manafold_census/semantic/__init__.py
  - narrow public exports only;
  - no extraction, I/O, CLI, or engine imports.
- src/manafold_census/semantic/primitives.py
  - immutable typed atoms: entity references, zones, quantities,
    characteristics, unknown values, parameter values, and semantic
    descriptors;
  - bounded labels and free-text escape-hatch validation.
- src/manafold_census/semantic/kind_payloads.py
  - immutable payload dataclasses for the 17 closed v1 kinds;
  - exact payload key sets and typed nested values.
- src/manafold_census/semantic/kinds.py
  - v1 family/kind enums and the one authoritative family-to-kind registry;
  - dispatch from kind/family to the typed payload class.
- src/manafold_census/semantic/evidence.py
  - M1 source reference and the six evidence union variants;
  - evidence ordering keys and local source-reference checks.
- src/manafold_census/semantic/identity.py
  - producer-neutral Requirement identity payload;
  - evidence, wire, bundle, and review-binding digests;
  - review-bound projection that removes only snapshot wrapper fields.
- src/manafold_census/semantic/model.py
  - derivation, review, resolution, and immutable RequirementV1 root model;
  - exact wire round trip and cross-field invariants.
- src/manafold_census/semantic/bundle.py
  - RequirementBundleV1 and the seven relationship types;
  - source scoping, endpoint, ordering, duplicate, and cycle validation.
- src/manafold_census/semantic/validate.py
  - source-aware checks against M1 StructuralCardRecordV1;
  - face/field/keyword/fragment validation;
  - no network access and no source fallback.

Every production module must remain at or below 500 lines. If a module reaches
the limit, split it by responsibility before adding more behavior.

### Normative schemas

Create exactly:

- schemas/semantic-requirement.v1.schema.json
- schemas/semantic-requirement-bundle.v1.schema.json

The individual schema owns nested definitions for primitives, kinds, evidence,
provenance, review, and resolution. The bundle schema references the local
individual schema through the existing offline validation registry. No
standalone evidence schema and no M3 CardAnalysisRecord schema are created.

### Tests

Create:

- tests/test_semantic_primitives.py
- tests/test_semantic_kinds.py
- tests/test_semantic_evidence.py
- tests/test_semantic_identity.py
- tests/test_semantic_model.py
- tests/test_semantic_schema.py
- tests/test_semantic_bundle.py
- tests/test_semantic_validation.py
- tests/test_semantic_fixtures.py
- tests/test_semantic_scope.py

Modify only:

- tests/test_resources.py to assert both M2 schemas are packaged;
- tests/test_maintainability.py to assert semantic modules and forbidden
  dependency strings remain within the M2 boundary;
- src/manafold_census/validation.py only to register local M2 schema
  references, without changing existing M0/M1 validation behavior.

### Representative fixture material

Create one test-only wrapper:

- fixtures/semantic/representative-bundles.json

It contains at most twelve objects with a non-empty case_id and a complete
RequirementBundleV1 wire object under bundle. The test loader unwraps each
bundle and validates it against the normative bundle schema; fixture content
must use real SourceRecordRefV1 fields and at least one Requirement.

The wrapper is not a third normative schema. Each nested bundle must pass
RequirementBundleV1 parsing and both M2 schemas.

The twelve case IDs must cover:

~~~text
simple
multiple_requirements
modal_relationships
multi_face
keyword_unresolved
trigger_condition
replacement
continuous_characteristic
cost_and_cost_modification
zone_and_object_creation
selection_and_delayed
outlier_partial_or_unresolved
~~~

Each fixture source reference must be selected from the pinned M1 corpus with
exact oracle_id, source_card_id, source_record_sha256, and the current M1
source-lock digest. Do not store full raw source records or card names in the
fixture wrapper. The source-aware acceptance run validates the selected
references against the local pinned source cache. If that cache is unavailable,
the acceptance gate is BLOCKED, not silently skipped.

---

## Task 1: Immutable semantic primitives and closed kind registry

Scope: Add the typed atoms, bounded descriptor, v1 family/kind vocabulary, and
payload branch classes. Do not add Requirement root identity, evidence,
schemas, bundles, relationships, or representative fixture files.

Files:

- Create src/manafold_census/semantic/__init__.py
- Create src/manafold_census/semantic/primitives.py
- Create src/manafold_census/semantic/kind_payloads.py
- Create src/manafold_census/semantic/kinds.py
- Create tests/test_semantic_primitives.py
- Create tests/test_semantic_kinds.py

### Required public types

Implement frozen, slot-based values with fresh wire output:

~~~python
class UnknownReasonV1(StrEnum):
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    AMBIGUOUS_SOURCE = "AMBIGUOUS_SOURCE"
    UNSUPPORTED_SHAPE = "UNSUPPORTED_SHAPE"
    CONFLICTING_INTERPRETATIONS = "CONFLICTING_INTERPRETATIONS"
    UNKNOWN_SEMANTICS = "UNKNOWN_SEMANTICS"


@dataclass(frozen=True, slots=True)
class UnknownValueV1:
    reason: UnknownReasonV1
    hint: str | None

@dataclass(frozen=True, slots=True)
class EntityRefV1:
    role: EntityRoleV1
    multiplicity: MultiplicityV1
    ordinal: int | None

@dataclass(frozen=True, slots=True)
class ZoneRefV1:
    zone: ZoneNameV1
    label: str | None

@dataclass(frozen=True, slots=True)
class QuantityV1:
    mode: QuantityModeV1
    value: int | str | UnknownValueV1 | None

@dataclass(frozen=True, slots=True)
class DurationV1:
    kind: DurationKindV1
    value: SemanticDescriptorV1 | UnknownValueV1 | None

@dataclass(frozen=True, slots=True)
class CharacteristicRefV1:
    name: CharacteristicNameV1
    label: str | None

@dataclass(frozen=True, slots=True)
class ParameterValueV1:
    value_type: ParameterValueTypeV1
    value: str | int | bool | SemanticDescriptorV1 | UnknownValueV1
~~~

The unresolved payload uses existing closed vocabularies rather than inventing
an implementation-only wire enum:

~~~text
observed_field   = controlled M1 source-field locator from the design spec
observed_shape   = SemanticShapeV1
candidate_kinds  = tuple[RequirementKindV1, ...]
~~~

There is no ObservedShapeV1. observed_field and observed_shape are orthogonal:
the field identifies the source location, while SemanticShapeV1 identifies the
known semantic descriptor shape or explicit unknown state. Candidate kinds are
validated against the complete v1 RequirementKindV1 set.

Use object_ref as the Python attribute for the wire key object. Do not use an
arbitrary mapping for any typed atom.

The descriptor wire shape is exactly:

~~~json
{
  "shape": "condition",
  "label": null,
  "subject": null,
  "object": null,
  "value": null,
  "children": []
}
~~~

Enforce:

- signed-64-bit bounds through MAX_INTEGER and MIN_INTEGER;
- non-negative bounds for ordinals and cardinalities;
- strict booleans, with bool rejected where an integer is required;
- valid UTF-8 and a 4096 Unicode-code-point limit for bounded descriptor labels
  and hints; JSON Schema and Python use the same code-point unit;
- no floats, sets, tuples, bytes, callbacks, paths, or arbitrary keys;
- from_wire accepts JSON-shaped dict/list/scalar values only; internal tuples,
  enums, model instances, and other Python objects are rejected recursively;
  direct constructors may still normalize immutable internal tuples;
- descriptor children are ordered and recursively immutable;
- QuantityV1 cross-field rules:
  - exact uses an integer;
  - symbolic uses a non-empty string;
  - all and each use null;
  - unknown uses an UnknownValueV1 with an explicit reason;
- DurationV1 uses exactly until_end_of_turn, this_turn, permanent, delayed,
  and unknown; delayed carries a typed descriptor and unknown carries an
  UnknownValueV1 with an explicit reason;
- ZoneRefV1 and CharacteristicRefV1 permit free labels only as bounded context
  for the explicit unknown/other variants.

The v1 enums and family mapping must exactly match Section 9 of the design
specification. The registry must reject an unknown kind rather than preserve
it as an arbitrary string.

### Test-first steps

- [ ] Add complete matrices for every primitive enum value, the exact closed
  SemanticShapeV1 vocabulary, the complete RequirementKindV1 vocabulary,
  and family-to-kind mapping; add exact fixed keys,
  signed-64-bit boundaries, immutable nested values, and fresh to_wire().
- [ ] Add tests for DurationV1's five exact kinds, delayed descriptor payload,
  explicit unknown reason, and immutability.
- [ ] Add tests that prove the generic text ParameterValue cannot carry a
  descriptor's required semantic dimensions.
- [ ] Add tests that reject arbitrary observed_shape strings and arbitrary
  candidate_kinds strings, while accepting only SemanticShapeV1 and
  RequirementKindV1 values.
- [ ] Add negative tests proving tuple-valued JSON arrays and nested Python
  model/enum objects are rejected by from_wire().
- [ ] Add tests for every kind's required and optional parameter key set.
- [ ] Run:

~~~powershell
python -m pytest tests/test_semantic_primitives.py tests/test_semantic_kinds.py -q
~~~

Expected initial result: collection/import failure because the semantic package
does not exist.

- [ ] Implement the frozen primitive, DurationV1, and kind payload classes.
- [ ] Rerun the focused tests and expect all primitive/kind tests to pass.
- [ ] Run:

~~~powershell
python -m ruff check src/manafold_census/semantic/primitives.py src/manafold_census/semantic/kind_payloads.py src/manafold_census/semantic/kinds.py tests/test_semantic_primitives.py tests/test_semantic_kinds.py
python -m mypy src/manafold_census/semantic
~~~

- [ ] Stage only Task 1 files, verify the staged diff, and commit:

~~~powershell
git add src/manafold_census/semantic tests/test_semantic_primitives.py tests/test_semantic_kinds.py
git diff --cached --check
git commit -m "feat: add M2 semantic parameter types"
~~~

- [ ] Push and verify REMOTE_HEAD == LOCAL_HEAD; stop with
  NEXT_TASK_AUTHORIZED=NO.

---

## Task 2: M1 source references and typed evidence union

Scope: Add the immutable M1 source reference and six evidence variants. Do not
add Requirement root identity, review state, bundle relationships, or
representative fixture files.

Files:

- Create src/manafold_census/semantic/evidence.py
- Create tests/test_semantic_evidence.py

### Required public types

Implement:

~~~python
@dataclass(frozen=True, slots=True)
class SourceRecordRefV1:
    record_schema: Literal["census.structural-card.v1"]
    source_lock_digest: str
    oracle_id: str
    source_card_id: str
    source_record_sha256: str


@dataclass(frozen=True, slots=True)
class StructuralRecordEvidenceV1:
    kind: Literal["STRUCTURAL_RECORD"]
    source: SourceRecordRefV1

@dataclass(frozen=True, slots=True)
class StructuralFaceEvidenceV1:
    kind: Literal["STRUCTURAL_FACE"]
    source: SourceRecordRefV1
    face_index: int

@dataclass(frozen=True, slots=True)
class StructuralFieldEvidenceV1:
    kind: Literal["STRUCTURAL_FIELD"]
    source: SourceRecordRefV1
    field: str
    face_index: int | None
    fragment: str | None

@dataclass(frozen=True, slots=True)
class StructuralKeywordEvidenceV1:
    kind: Literal["STRUCTURAL_KEYWORD"]
    source: SourceRecordRefV1
    keyword_index: int
    keyword_value: str

@dataclass(frozen=True, slots=True)
class RulesCitationEvidenceV1:
    kind: Literal["RULES_CITATION"]
    ruleset_id: str
    ruleset_version: str
    rule_id: str
    rules_artifact_sha256: str | None

@dataclass(frozen=True, slots=True)
class ExternalReviewEvidenceV1:
    kind: Literal["EXTERNAL_REVIEW"]
    authority_id: str
    authority_version: str
    record_id: str
    record_sha256: str
~~~

Use a tagged EvidenceV1 union. Wire variants must have exactly the keys
specified by Section 8.4:

~~~text
STRUCTURAL_RECORD  = {kind, source}
STRUCTURAL_FACE    = {kind, source, face_index}
STRUCTURAL_FIELD   = {kind, source, field, face_index, fragment}
STRUCTURAL_KEYWORD = {kind, source, keyword_index, keyword_value}
RULES_CITATION     = {kind, ruleset_id, ruleset_version, rule_id,
                      rules_artifact_sha256}
EXTERNAL_REVIEW    = {kind, authority_id, authority_version, record_id,
                      record_sha256}
~~~

Enforce:

- canonical lowercase UUID and SHA-256 syntax;
- exact M1 record schema;
- non-negative signed-64-bit face and keyword indexes;
- structural field names from the frozen M1 parent/face sets;
- parent-only fields cannot carry a face index;
- keyword evidence is parent-level and preserves exact keyword value;
- fragments are optional, textual, exact-context hints at most 4096 Unicode
  code points and valid UTF-8;
- rules citations and external review records remain distinguishable from
  structural evidence;
- all nested values are immutable and to_wire() is fresh.

The evidence ordering key is the domain-separated canonical digest from
census.semantic-evidence.v1. It must not use insertion order or producer ID.

### Test-first steps

- [ ] Add positive tests for each evidence variant, exact key sets, source
  identity, face evidence, keyword ordering, rules citation, external review,
  and fragment limits.
- [ ] Add negative tests for uppercase IDs, wrong schema, wrong face field,
  face index on parent-only field, wrong keyword value/index, unknown
  properties, bad digests, negative indexes, and oversized fragments.
- [ ] Add a test that two structural evidence locators may differ while their
  source identity remains equal.
- [ ] Run the focused evidence test before implementation and observe the
  expected import failure.
- [ ] Implement evidence.py using the existing canonical/digest helpers.
- [ ] Rerun focused tests and then:

~~~powershell
python -m ruff check src/manafold_census/semantic/evidence.py tests/test_semantic_evidence.py
python -m mypy src/manafold_census/semantic
~~~

- [ ] Commit only Task 2 files:

~~~powershell
git add src/manafold_census/semantic/evidence.py tests/test_semantic_evidence.py
git diff --cached --check
git commit -m "feat: add M2 source evidence references"
~~~

- [ ] Push, verify remote parity, report, and stop.

---

## Task 3: Requirement identity, review binding, and immutable root model

Scope: Add the individual RequirementV1 model and all deterministic identity and
lifecycle rules. Do not add JSON Schema files, bundles, relationships, or
fixtures.

Files:

- Create src/manafold_census/semantic/identity.py
- Create src/manafold_census/semantic/model.py
- Modify src/manafold_census/semantic/__init__.py
- Create tests/test_semantic_identity.py
- Create tests/test_semantic_model.py

### Required wire and model shape

The individual Requirement root has exactly:

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

Implement:

~~~python
@dataclass(frozen=True, slots=True)
class DerivationV1:
    method: DerivationMethodV1
    producer_id: str
    producer_version: str


@dataclass(frozen=True, slots=True)
class ProvenanceV1:
    derivations: tuple[DerivationV1, ...]


@dataclass(frozen=True, slots=True)
class ReviewV1:
    status: ReviewStatusV1
    reviewed_by: str | None
    reviewed_claim_digest: str | None


@dataclass(frozen=True, slots=True)
class ResolutionV1:
    state: ResolutionStateV1
    reason: ResolutionReasonV1
    unknown_paths: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RequirementV1:
    requirement_id: str
    source: SourceRecordRefV1
    family: RequirementFamilyV1
    kind: RequirementKindV1
    parameters: KindPayloadV1
    evidence: tuple[EvidenceV1, ...]
    provenance: ProvenanceV1
    review: ReviewV1
    resolution: ResolutionV1
~~~

The implementation must not add an anchor/path/occurrence property.

### Identity implementation

Implement one authoritative function with this public interface:

~~~python
def requirement_identity_payload(
    requirement: RequirementV1,
) -> dict[str, JSONValue]
~~~

It must return only:

~~~json
{
  "identity_schema": "census.semantic-requirement-id.v1",
  "source_identity": {
    "record_schema": "census.structural-card.v1",
    "oracle_id": "abcdefab-abcd-4abc-8abc-abcdefabcdef",
    "source_card_id": "abcdefab-abcd-4abc-8abc-abcdefabcdea",
    "source_record_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  },
  "family": "effect",
  "kind": "draw_cards",
  "parameters": {
    "drawer": {"role": "source", "multiplicity": "one", "ordinal": null},
    "quantity": {"mode": "exact", "value": 2}
  }
}
~~~

source_lock_digest, evidence locators, derivation provenance, review,
resolution, and bundle relationships are excluded from Requirement identity.

Implement these public functions with the exact return types shown:

~~~python
def requirement_id_for(requirement: RequirementV1) -> str
def evidence_digest_for(evidence: EvidenceV1) -> str
def wire_digest_for(requirement: RequirementV1) -> str
def reviewed_claim_digest_for(requirement: RequirementV1) -> str
~~~

Use these exact domains:

~~~text
census.semantic-requirement-id.v1
census.semantic-evidence.v1
census.semantic-requirement-wire.v1
census.semantic-requirement-review.v1
~~~

The review-bound projection must include source identity without
source_lock_digest, family, kind, parameters, all evidence with nested
structural source locks removed, derivations, and resolution. It must exclude
requirement ID and the review object itself. This lets a new snapshot preserve
the stable ID and review binding when the exact M1 record is unchanged, while
still changing full wire/artifact bytes.

### Lifecycle invariants

Enforce:

- generated records use PROPOSED;
- PROPOSED and IN_REVIEW require null reviewer and null binding digest;
- ACCEPTED and REJECTED require non-null reviewer and a recomputed binding
  digest;
- SUPERSEDED is not a review status;
- evidence, provenance, or resolution changes keep the same ID only when
  source identity/family/kind/parameters are unchanged, and require reopening
  to IN_REVIEW;
- source identity/family/kind/parameter changes create a new ID;
- a partial-to-complete transition creates a new ID if any unknown parameter is
  replaced, otherwise keeps the ID but reopens review;
- accepted-plus-partial and accepted-plus-unresolved are valid;
- complete requires no unknown value/path, no semantic parameter enum sentinel
  whose wire value is 'unknown', and kind not equal to unresolved;
- complete keyword_reference requires expansion_state=EXPANDED with typed
  expansion; UNEXPANDED and UNKNOWN are PARTIAL for a known kind;
- complete also rejects any required SemanticDescriptor whose necessary
  meaning exists only in label/text or shape=unknown; this cross-field rule
  belongs to RequirementV1 rather than the primitive layer;
- unknown kind, malformed wire, or unsupported payload is a validation error;
- unresolved semantic meaning is valid and fail-closed.

### Test-first steps

- [ ] Add model factories for a complete draw claim, a partial known-kind
  claim, an unresolved claim, and an accepted-but-partial claim.
- [ ] Add identity tests proving:
  - shuffled evidence does not change Requirement ID;
  - different producer evidence locators do not change Requirement ID;
  - different source-lock digests do not change Requirement ID;
  - changing source-record SHA, kind, family, or parameters changes ID;
  - wire digest changes when source lock/evidence/review changes.
- [ ] Add review-binding tests proving an accepted record with stale evidence,
  derivation, or resolution digest is rejected, while reopening to IN_REVIEW
  with a cleared digest is accepted.
- [ ] Add tests for all review/resolution combinations, unknown paths, accepted
  unresolved claims, invalid terminal metadata, proposal separation, every
  semantic UNKNOWN enum sentinel, keyword UNEXPANDED/UNKNOWN versus EXPANDED,
  and label-only/unknown-shape descriptors rejected under COMPLETE.
- [ ] Add immutability tests for constructor input, nested values, previous
  to_wire() output, and repeated digest calls.
- [ ] Run the two focused test files before implementation and record the
  expected import failure.
- [ ] Implement identity/model code with existing canonical_json_bytes and
  domain_digest; do not create a second encoder.
- [ ] Rerun focused tests, then:

~~~powershell
python -m ruff check src/manafold_census/semantic/identity.py src/manafold_census/semantic/model.py tests/test_semantic_identity.py tests/test_semantic_model.py
python -m mypy src/manafold_census/semantic
~~~

- [ ] Commit only the declared Task 3 files:

~~~powershell
git add src/manafold_census/semantic/identity.py src/manafold_census/semantic/model.py src/manafold_census/semantic/__init__.py tests/test_semantic_identity.py tests/test_semantic_model.py
git diff --cached --check
git commit -m "feat: add deterministic M2 Requirement identity"
~~~

- [ ] Push, verify remote parity, report, and stop.

---

## Task 4: Individual Requirement schema and model parity

Scope: Add only the individual Requirement v1 JSON Schema and its model/schema
parity tests. Do not add the bundle schema, bundle model, relationships,
fixtures, CLI commands, CI changes, or global data.

Files:

- Create schemas/semantic-requirement.v1.schema.json
- Create tests/test_semantic_schema.py

### Schema requirements

The individual schema must have:

~~~json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://manafold-census.invalid/schemas/semantic-requirement.v1.schema.json",
  "type": "object",
  "additionalProperties": false
}
~~~

Its root required set is exactly:

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

Use closed oneOf branches for every kind payload and every evidence variant.
Use fixed keys and additionalProperties=false at every nested object. Encode
signed-64-bit bounds, lowercase UUID/SHA-256 patterns, enum values, null rules,
4096 Unicode-code-point fragment/label lengths, terminal review binding
requirements, semantic UNKNOWN-sentinel exclusion from COMPLETE,
keyword-reference EXPANDED requirements for COMPLETE, and the
complete-resolution descriptor restriction. The bundle schema and local
cross-schema registry are owned by Task 5.

### Test-first steps

- [ ] Add tests that load semantic-requirement.v1.schema.json through
  project_data_root().
- [ ] Add model/schema parity cases for every kind family, unresolved/partial
  values, semantic UNKNOWN sentinels, keyword expansion states, all evidence
  variants, and COMPLETE/label-only descriptor rejection.
- [ ] Add negative schema tests for unknown properties, wrong schema, bad
  source IDs/digests, wrong kind/family branch, missing review binding,
  terminal review without digest, label-only COMPLETE descriptor, unknown
  enum values, COMPLETE UNKNOWN sentinels, multibyte length boundaries,
  floats, and negative indexes.
- [ ] Run the focused schema tests before implementation and observe the
  expected missing-resource failure.
- [ ] Implement the Draft 2020-12 individual Requirement schema.
- [ ] Rerun:

~~~powershell
python -m pytest tests/test_semantic_schema.py -q
python -m ruff check tests/test_semantic_schema.py
python -m mypy src/manafold_census
~~~

- [ ] Verify the individual schema is included by the existing setuptools
  schemas/*.json data-files glob without changing pyproject.toml.
- [ ] Commit only Task 4 files:

~~~powershell
git add schemas/semantic-requirement.v1.schema.json tests/test_semantic_schema.py
git diff --cached --check
git commit -m "feat: define M2 Requirement schema"
~~~

- [ ] Push, verify remote parity, report, and stop.

---

## Task 5: Requirement bundles and minimal relationships

Scope: Add same-source RequirementBundleV1 and only the seven relationship types
from the design. Do not add global analysis records or capability edges.

Files:

- Create src/manafold_census/semantic/bundle.py
- Modify src/manafold_census/semantic/__init__.py
- Create schemas/semantic-requirement-bundle.v1.schema.json
- Modify src/manafold_census/validation.py
- Modify tests/test_semantic_schema.py
- Modify tests/test_resources.py
- Create tests/test_semantic_bundle.py

### Required bundle and relation types

Implement:

~~~python
class RelationshipTypeV1(StrEnum):
    PARENT_OF = "PARENT_OF"
    ALTERNATIVE_OF = "ALTERNATIVE_OF"
    CONDITION_OF = "CONDITION_OF"
    COST_OF = "COST_OF"
    SEQUENCE_BEFORE = "SEQUENCE_BEFORE"
    CONFLICTS_WITH = "CONFLICTS_WITH"
    SUPERSEDES = "SUPERSEDES"


@dataclass(frozen=True, slots=True)
class RequirementRelationshipV1:
    relationship_type: RelationshipTypeV1
    from_requirement_id: str
    to_requirement_id: str
    ordinal: int | None


@dataclass(frozen=True, slots=True)
class RequirementBundleV1:
    source: SourceRecordRefV1
    requirements: tuple[RequirementV1, ...]
    relationships: tuple[RequirementRelationshipV1, ...]
~~~

Bundle wire root keys are exactly:

~~~text
schema
source
requirements
relationships
~~~

Enforce:

- all requirements and relationship endpoints use the same source record;
- requirements are strictly sorted by Requirement ID;
- duplicate requirement IDs fail;
- relation endpoints exist;
- self-edges fail;
- symmetric relation endpoints are canonicalized;
- SEQUENCE_BEFORE requires a non-negative ordinal;
- ordered PARENT_OF may use an ordinal;
- ALTERNATIVE_OF/CONFLICTS_WITH reject duplicates;
- PARENT_OF and SUPERSEDES are acyclic;
- arbitrary relation types and capability/engine edges fail;
- SUPERSEDES changes lifecycle interpretation only through the bundle edge;
  it does not mutate either endpoint's review status.

The M2 watchpoint is tested explicitly: exact duplicate same-source claims
share one Requirement ID and cannot be represented as duplicate requirements or
duplicate relationship edges. Distinct modal branches must use distinct typed
Requirements or explicit relationship context; the bundle must not invent a
second occurrence ID.

### Test-first steps

- [ ] Add tests for an empty relationship list, a modal parent/alternative
  bundle, condition/cost edges, ordered sequence, conflicts, and supersedes.
- [ ] Add negative tests for cross-source requirements, unsorted requirements,
  duplicate IDs, missing endpoints, self-edges, bad symmetric ordering,
  duplicate edges, cycles, bad ordinals, arbitrary edge labels, and unknown
  bundle root/nested properties.
- [ ] Add the explicit coalescing watchpoint test:
  - build two Requirements with the same source/family/kind/parameters;
  - give them different structural evidence locators;
  - assert equal Requirement IDs;
  - assert a bundle rejects both as duplicate requirements;
  - reconcile evidence into one Requirement and assert one valid bundle.
- [ ] Run the focused bundle tests before implementation and observe the
  expected import failure.
- [ ] Implement bundle/relation value classes, the bundle schema, and the
  narrowly scoped offline registry entry for the local Requirement schema.
- [ ] Add the second M2 schema resource assertions and local $ref resolution
  test in tests/test_semantic_schema.py and tests/test_resources.py; preserve
  the existing source-lock registry behavior.
- [ ] Rerun focused tests, then:

~~~powershell
python -m ruff check src/manafold_census/semantic/bundle.py tests/test_semantic_bundle.py
python -m mypy src/manafold_census/semantic
~~~

- [ ] Commit only Task 5 files:

~~~powershell
git add src/manafold_census/semantic/bundle.py src/manafold_census/semantic/__init__.py schemas/semantic-requirement-bundle.v1.schema.json src/manafold_census/validation.py tests/test_semantic_schema.py tests/test_resources.py tests/test_semantic_bundle.py
git diff --cached --check
git commit -m "feat: add M2 Requirement bundles and schema"
~~~

- [ ] Push, verify remote parity, report, and stop.

---

## Task 6A: Source-aware validation and representative fixture proposals

Scope: Validate Requirement and bundle source references against M1
StructuralCardRecordV1 values and produce only proposed representative
fixtures. Do not enumerate the corpus, build an analysis dataset, add a
semantic extractor, or write a terminal human review outcome.

Files:

- Create src/manafold_census/semantic/validate.py
- Create fixtures/semantic/representative-bundles.json
- Create tests/test_semantic_validation.py
- Create tests/test_semantic_fixtures.py
- Create tests/semantic_fixture_review_report.py

### Required source-aware API

Implement these pure source-aware functions:

~~~python
def validate_requirement_against_structural_record(
    requirement: RequirementV1,
    record: StructuralCardRecordV1,
    expected_source_lock_digest: str,
) -> None

def validate_bundle_against_structural_record(
    bundle: RequirementBundleV1,
    record: StructuralCardRecordV1,
    expected_source_lock_digest: str,
) -> None
~~~

These functions must:

- compare record schema, source lock, Oracle ID, source card ID, and record SHA;
- validate every structural evidence source reference;
- validate parent versus face field membership;
- validate face index existence and exact M1 face position;
- validate keyword index and exact keyword value;
- validate optional text fragment as an exact substring of the referenced M1
  string field;
- reject a missing or altered source rather than falling back;
- never read a URL, dereference all_parts.uri, or use an engine;
- classify missing pinned source bytes as unavailable evidence for the
  acceptance report, not as a semantic PASS.

The source-aware validator does not infer a kind or fill an unknown value. It only
checks references and contract invariants.

### Proposal fixture construction

Select at most twelve exact source records from the pinned M1 corpus. Use the
case matrix in the design specification. For each case:

1. verify exact M1 identity against the pinned source record;
2. create only the Requirement/Bundle wire, not a copied raw source record;
3. persist every generated Requirement as PROPOSED or IN_REVIEW only;
4. include at least one proposed accepted-but-partial candidate without
   terminal review;
5. include a proposed unresolved keyword/outlier Requirement;
6. include a proposed conflicting pair with CONFLICTS_WITH;
7. exercise multi-face evidence without a producer anchor;
8. keep all fixture evidence and derivations canonicalized.

The implementation agent must not set ACCEPTED or REJECTED on a real fixture.
The fixture wrapper is test-only. Its bundle values must pass the normative
bundle schema, and its case IDs must be unique. No fixture test may assert
global semantic coverage or iterate all 38,740 records.

### Non-committed review report

tests/semantic_fixture_review_report.py is test-harness code only. It writes
dist/m2-semantic-fixture-review/task6a-review.json, which is ignored and is not
committed. Each report case must contain:

~~~text
case_id
card_name_for_reviewer
oracle_id
face_index where applicable
relevant exact pinned source fields or bounded fragments
requirement_id
candidate_reviewed_claim_digest
reviewed_claim_payload (canonical JSON projection containing source identity,
                         family, kind, parameters, evidence, provenance,
                         and resolution)
canonical evidence representation
canonical derivation provenance representation
proposed family
proposed kind
proposed parameters
proposed resolution
proposed relationships
review_status = PROPOSED
~~~

The report gives an independent semantic reviewer enough pinned context to
accept, reject, or request changes. The candidate digest is computed by the
same reviewed_claim_digest_for function used by RequirementV1. The canonical
claim projection is the exact object hashed for that digest; the evidence and
provenance fields are included both for audit readability and to prevent a
reviewer from reconstructing a different claim. The report is not a semantic
authority and does not alter the persisted fixture contract.

### Test-first steps

- [ ] Add source-aware tests using small in-memory StructuralCardRecordV1
  values for parent fields, face fields, keyword arrays, and fragments.
- [ ] Add negative tests for wrong source lock, Oracle ID, source card ID,
  record SHA, face index, parent/face field mismatch, keyword mismatch,
  fragment mismatch, and missing face.
- [ ] Add fixture matrix tests that assert no more than twelve cases and all
  twelve required case IDs.
- [ ] Add tests that fail if a real fixture has ACCEPTED or REJECTED status in
  Task 6A, while unresolved and partial proposals remain valid.
- [ ] Add report-generation tests that include the exact pinned context fields
  without persisting card names or raw source records in the bundle file.
- [ ] Run the focused tests before implementation and observe the expected
  import/fixture failure.
- [ ] Implement validate.py and the test-only review report helper without
  importing CLI, source acquisition, or network modules.
- [ ] Populate and validate the proposed representative bundles against the
  local pinned M1 source cache. If that cache is unavailable, record the
  source-aware gate as BLOCKED and do not substitute another source.
- [ ] Generate the non-committed review report and stop for independent
  semantic review.
- [ ] Rerun focused tests and:

~~~powershell
python -m pytest tests/test_semantic_validation.py tests/test_semantic_fixtures.py -q
python -m ruff check src/manafold_census/semantic/validate.py tests/test_semantic_validation.py tests/test_semantic_fixtures.py tests/semantic_fixture_review_report.py
python -m mypy src/manafold_census/semantic
~~~

- [ ] Commit only Task 6A files:

~~~powershell
git add src/manafold_census/semantic/validate.py fixtures/semantic/representative-bundles.json tests/test_semantic_validation.py tests/test_semantic_fixtures.py tests/semantic_fixture_review_report.py
git diff --cached --check
git commit -m "feat: add M2 representative fixture proposals"
~~~

- [ ] Push, verify remote parity, report source-cache status and the
  non-committed review-report path, and stop with
  TASK_6B_AUTHORIZED=NO.

---

## Task 6B: Apply independently reviewed fixture outcomes

Scope: Apply only an externally supplied semantic review decision to the
Task 6A proposals. This task does not select cards, alter proposed family/kind/
parameters, invent evidence, or perform semantic interpretation.

Precondition:

~~~text
TASK_6A_COMMIT = reviewed and pushed
INDEPENDENT_FIXTURE_REVIEW = PASS
REVIEW_DECISIONS = supplied for every terminal outcome
REVIEW_DECISIONS_PATH = dist/m2-semantic-fixture-review/task6b-decisions.json
~~~

Files:

- Modify fixtures/semantic/representative-bundles.json
- Modify tests/test_semantic_fixtures.py

The independent reviewer supplies, per case and Requirement ID:

~~~text
requirement_id
reviewed_claim_digest
review.status
reviewed_by
decision = ACCEPTED | REJECTED
any required correction request
~~~

The decisions file is external, ignored, and not committed. The implementation
agent may mechanically apply only those supplied values. If the file is absent,
Task 6B is BLOCKED and no terminal status may be written.
If a correction to family, kind, parameters, evidence, or resolution is
requested, stop and report it for a new proposal revision; do not invent the
correction in Task 6B.

For every terminal decision, Task 6B must load the referenced proposal,
recompute reviewed_claim_digest_for from its current source identity, evidence,
provenance, and resolution, and require exact equality with both the report's
candidate_reviewed_claim_digest and the decision file's reviewed_claim_digest. A
digest mismatch is FAIL/BLOCKED and prevents ACCEPTED/REJECTED from being
written. The implementation agent never invents a digest or review decision.

Task 6B must preserve:

- unresolved and partial resolutions exactly where the reviewer accepts them;
- at least one accepted-but-partial Requirement after independent approval;
- terminal digest equality against the exact reviewed claim projection;
- historical proposal identity and evidence provenance;
- the existing SUPERSEDES relationship semantics, if a reviewed correction
  creates a new Requirement ID.

### Test-first steps

- [ ] Add a fixture test that loads the externally supplied decision set and
  confirms every ACCEPTED/REJECTED entry echoes the exact requirement_id and
  candidate digest from Task 6A, has the supplied reviewer, and matches a
  freshly recomputed reviewed_claim_digest.
- [ ] Add a negative test for an agent-authored terminal status whose reviewer
  decision is absent.
- [ ] Add a negative test that changes evidence, provenance, or resolution
  between 6A and 6B and proves the digest mismatch blocks terminal review.
- [ ] Apply only the supplied terminal review fields and rerun the fixture
  tests.
- [ ] Run the full per-task regression gate from the authorization protocol.
- [ ] Commit only the reviewed fixture/test changes:

~~~powershell
git add fixtures/semantic/representative-bundles.json tests/test_semantic_fixtures.py
git diff --cached --check
git commit -m "test: record independently reviewed M2 fixtures"
~~~

- [ ] Push, verify remote parity, report the external review decision source,
  and stop with TASK_7_AUTHORIZED=NO.

---

## Task 7: Complete M2 contract gates and maintainability guard

Scope: Add final contract-only tests and resource/LOC guards. Run the full
offline M2 test set. Do not modify CI, CLI, Justfile, M1 files, or generate
global data.

Files:

- Create tests/test_semantic_scope.py
- Modify tests/test_maintainability.py

### Scope and maintainability tests

test_semantic_scope.py must assert through static file inspection that:

- no semantic module imports Manafold, Rust, an engine package, database client,
  network client, or LLM SDK;
- no semantic module defines Capability, CapabilityFamily, capability_id,
  engine support, coverage, or CardAnalysisRecord;
- no semantic module reads the 38,740-card source or enumerates a global corpus;
- no CLI/CI/Justfile change is required by the M2 contract;
- the only global-like vocabulary is the explicitly allowed Requirement kind
  vocabulary and M2 review/resolution vocabulary.

Extend test_maintainability.py to keep every production module under 500 lines.
Task 5 owns the resource assertions for both M2 schemas; Task 7 reuses that
test without modifying its file.

### Full verification commands

Run all commands from the repository root:

~~~powershell
python -m pytest tests/test_semantic_primitives.py tests/test_semantic_kinds.py tests/test_semantic_evidence.py tests/test_semantic_identity.py tests/test_semantic_model.py tests/test_semantic_schema.py tests/test_semantic_bundle.py tests/test_semantic_validation.py tests/test_semantic_fixtures.py tests/test_semantic_scope.py -q
python -m pytest -q
ruff format --check .
ruff check .
mypy src/manafold_census
git diff --check
~~~

Expected result: all tests pass, formatting/Ruff/mypy exit 0, and no generated
global semantic artifact exists. The real pinned source-aware fixture run must
be reported separately from synthetic/offline tests.

Run a fresh non-editable wheel smoke outside the repository CWD:

~~~powershell
$wheelRoot = Join-Path $env:TEMP "manafold-census-m2-wheel"
python -m pip wheel . --no-deps --wheel-dir $wheelRoot
$venv = Join-Path $env:TEMP "manafold-census-m2-wheel-venv"
python -m venv $venv
& (Join-Path $venv "Scripts/python.exe") -m pip install --no-deps (Get-ChildItem $wheelRoot "*.whl" | Select-Object -Last 1).FullName
Push-Location $env:TEMP
try {
  & (Join-Path $venv "Scripts/python.exe") -c "from manafold_census.resources import project_data_root; from pathlib import Path; root=project_data_root(); assert (root / 'schemas' / 'semantic-requirement.v1.schema.json').is_file(); assert (root / 'schemas' / 'semantic-requirement-bundle.v1.schema.json').is_file()"
} finally {
  Pop-Location
}
~~~

The wheel smoke proves resource packaging only; it does not perform global
semantic extraction.

### Final M2 gates

Record each gate as PASS, FAIL, BLOCKED, or NOT_RUN:

~~~text
REQUIREMENT_CONTRACT_VERSIONED        = PASS
REQUIREMENT_MODEL_SCHEMA_PARITY       = PASS
REQUIREMENT_ID_DETERMINISTIC          = PASS
PRODUCER_NEUTRAL_IDENTITY             = PASS
SNAPSHOT_ID_STABILITY                 = PASS
REQUIREMENT_WIRE_CANONICAL            = PASS
REQUIREMENT_WIRE_ROUND_TRIP           = PASS
REQUIREMENT_PROVENANCE_DEFINED        = PASS
SOURCE_FACE_PROVENANCE_VALIDATED      = PASS
DERIVATION_STATUS_EXPLICIT            = PASS
PROPOSAL_REVIEW_SEPARATION            = PASS
REVIEW_BINDING_INTEGRITY              = PASS
STALE_REVIEW_PREVENTION               = PASS
SUPERSEDES_SEPARATION                 = PASS
UNRESOLVED_STATE_SUPPORTED            = PASS
PARTIAL_STATE_SUPPORTED               = PASS
DESCRIPTOR_ESCAPE_HATCH               = PASS
RELATIONSHIP_VALIDATION                = PASS
IMMUTABILITY                           = PASS
REPRESENTATIVE_FIXTURES_VALID         = PASS
NO_CARD_SPECIFIC_EXECUTORS            = PASS
NO_CAPABILITY_ONTOLOGY_DEPENDENCY     = PASS
NO_ENGINE_DEPENDENCY                  = PASS
NO_GLOBAL_EXTRACTION                  = PASS
MODULE_LOC_BUDGET                     = PASS
M1_FROZEN_CONTRACT_PRESERVED          = PASS
~~~

M2 is not complete if any source-aware pinned fixture gate is BLOCKED or if
synthetic tests pass while a required invariant is untested.

### Final task commit and stop

- [ ] Run the full gate set and inspect the complete output.
- [ ] Verify only Task 7 files are changed.
- [ ] Commit:

~~~powershell
git add tests/test_semantic_scope.py tests/test_maintainability.py
git diff --cached --check
git commit -m "test: enforce M2 semantic contract boundaries"
~~~

- [ ] Push and verify exact remote parity.
- [ ] Report all gate states, including source-cache status.
- [ ] Stop. Do not create a PR, merge, begin M3, or start M4.

---

## Task 4 contract clarification 01

The Task 4 schema/model review identified two cross-layer invariants that must
be closed before Task 5. This clarification changes no root key, kind, family,
evidence variant, digest domain, or Requirement identity rule.

**DECISION — COMPLETE unknowns**

`COMPLETE` excludes every semantic parameter enum sentinel whose wire value is
`unknown`, not only `UnknownValueV1`. This includes UNKNOWN entity roles,
multiplicities, zones, subject kinds, modification/cost operations,
expansion states, semantic shapes, quantity modes, parameter-value types, and
durations. A known `keyword_reference` is `PARTIAL` for `UNEXPANDED` or
`UNKNOWN`; COMPLETE requires `EXPANDED` plus typed expansion. The model’s
recursive unknown scan and the schema’s complete branches must agree.

**DECISION — bounded text**

The normative limit for bounded descriptor labels, hints, question text, and
fragments is 4096 Unicode code points plus valid UTF-8 encodability. Python
must count code points, not UTF-8 bytes, and JSON Schema `maxLength: 4096` is
the same authority. Source-preserved strings and stable identifiers that are
unbounded remain uncapped.

The next coordinated implementation fix must update all bounded-text
consumers, including the existing primitive/evidence validators, the Task 3
complete scan, the Task 4 schema, and their parity tests. No implementation
fix, schema rewrite, Task 5 work, or new authorization is granted by this
clarification.

~~~text
M2_CONTRACT_CLARIFICATION_01 = APPLIED_PENDING_INDEPENDENT_REVIEW
TASK_4_FIX_AUTHORIZED         = NO
TASK_5_AUTHORIZED             = NO
~~~

## Spec coverage map

| Frozen design section | Plan task |
| --- | --- |
| M1 authority and ownership | Authorization protocol; Tasks 2 and 6A |
| Requirement granularity and coalescing | Tasks 3 and 5 |
| Producer-neutral identity and snapshot stability | Task 3 identity tests; Task 5 coalescing watchpoint |
| Individual wire data model | Tasks 2, 3, and 4 |
| Kind/family and typed parameters | Task 1 |
| Evidence, face linkage, keywords, and rules citations | Task 2 |
| Derivation/review/resolution orthogonality | Task 3 |
| Review binding and stale-review prevention | Task 3 |
| Minimal relationships/hierarchy | Task 5 |
| Canonical wire and digest domains | Tasks 3, 4, and 5 |
| Immutability and fail-closed parsing | Tasks 1 through 4 |
| Representative fixture proposals and independent review outcomes | Tasks 6A and 6B |
| M2/M3 and M2/M4 boundaries | Task 7 scope tests and all task protocols |
| Threat mitigations | Tasks 1, 3, 5, 6A, 6B, and 7 |
| Maintainability and LOC budget | Task 7 |
| Explicit exit gates | Task 7 |

## Plan self-review

- [ ] Every M2 design section has a task in the coverage map.
- [ ] The producer-neutral identity watchpoint is tested with different evidence
  locators and source-lock values.
- [ ] The review-binding digest is tested against evidence, derivation,
  resolution, and source-lock changes.
- [ ] Task 6A cannot persist a real ACCEPTED/REJECTED fixture, and Task 6B
  requires externally supplied review decisions before applying terminal state.
- [ ] SUPERSEDED is present only as the SUPERSEDES relationship and never as a
  review status.
- [ ] The Descriptor label/text escape hatch has positive and negative tests.
- [ ] The plan contains no M3 global extraction, M4 ontology, engine, database,
  Rust, LLM, CLI, CI, or merge task.
- [ ] The plan contains no placeholder markers or tentative task wording.
- [ ] The plan uses one consistent root field set, status vocabulary, digest
  domain list, and public function names throughout.
- [ ] COMPLETE excludes every semantic UNKNOWN sentinel and keyword
  UNEXPANDED/UNKNOWN, and bounded text uses the shared 4096-code-point rule.
- [ ] No production module exceeds the 500-line budget.
- [ ] No fixture task stores raw corpus data or asserts global semantic coverage.

## Plan state

~~~text
IMPLEMENTATION_PLAN_WRITTEN        = YES
IMPLEMENTATION_PLAN_PATH            = docs/superpowers/plans/2026-09-13-semantic-requirement-contract.md
IMPLEMENTATION_PLAN_REVIEW          = PENDING
TASK_4_CONTRACT_CLARIFICATION_01   = APPLIED_PENDING_INDEPENDENT_REVIEW
M2_IMPLEMENTATION_AUTHORIZED       = NO
NEXT_TASK_AUTHORIZED                = IMPLEMENTATION_PLAN_ONLY
PR_AUTHORIZED                       = NO
MERGE_AUTHORIZED                    = NO
~~~
