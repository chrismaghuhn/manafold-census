# M3 Task 11 — Corpus-Scale Producer Configuration and Authority Design

Status: `DESIGN_ONLY / READY_FOR_INDEPENDENT_REVIEW`

Reference base:

```text
repository = manafold-census
branch     = feat/m3-global-requirement-candidate-extraction
reference_head = d75d0188480b18f5c72ba7f5b002740d05c8496b
task_11_state = BLOCKED_SEMANTIC_CONFIGURATION
```

This document defines the smallest trustworthy configuration that could later
permit the Task 11 offline corpus-closure campaign. It does not add a producer,
change a schema, run the pinned corpus, or authorize semantic claims.

## 1. Current blocker and decision

The frozen implementation has no corpus-scale producer configuration.

The concrete producer used by the Task 9 maintainer command is the private
CLI-local `m3.synthetic.no-match` adapter in
`src/manafold_census/analysis/cli_support.py`. It returns `NO_MATCH` for every
record and is intentionally bounded synthetic infrastructure. It is not a
corpus semantic producer.

The exact pattern producer used by the reference tests is `_ExactPatternProducer`
in `tests/test_analysis_build.py`. It is test-only. The related face, double,
conflict, unsupported, and invalid producers in that file are also test-only.

`fixtures/analysis/pattern-registry.v1.json` is a synthetic fixture. Its
`fixture-pattern-review` and `fixture-pattern-rejected` identifiers are fixture
review identities, not corpus review authority. It MUST NOT silently become the
global effective registry.

The authoritative corpus registry namespace is not under `fixtures/`:

```text
config/analysis/m3-corpus-pattern-registry.v1.json
```

`fixtures/analysis/*` remains synthetic/test material only. A future corpus
registry may be copied from a reviewed proposal only through an explicit
maintainer decision; it is never promoted by a test or coding agent.

Decision:

```text
TASK_11_RETRY_ALLOWED             = NO
GLOBAL_EXTRACTION_STARTED        = NO
NO_NEW_PRODUCER_IN_TASK_11       = YES
CORPUS_PRODUCER_CONFIGURATION    = REQUIRED_BEFORE_RETRY
CORPUS_PATTERN_AUTHORITY         = REQUIRED_BEFORE_RETRY
```

The first useful corpus configuration should be a tiny exact-pattern subset,
not a broad rules engine. Every other card remains an honest
`UNRESOLVED_ANALYSIS` unless a separately governed negative authority exists.

## 2. Existing reusable contracts

### `CandidateProducerV1` and descriptor

`src/manafold_census/analysis/producer.py` defines the protocol:

```text
producer.descriptor: ProducerDescriptorV1
producer.produce(record, context) -> ProducerResultV1
```

`ProducerDescriptorV1` binds:

```text
producer_id
producer_version
derivation_method
input_schema
input_fields
pattern_registry_digest | null
deterministic
supports_relationships
```

The descriptor is a contract declaration, not an implementation digest. The
authoritative registry admits only deterministic descriptors and rejects the
frozen `MODEL` path until a pinned-import contract exists. Producer results are
validated before reconciliation; normal candidates must be `PROPOSED`, and
terminal review metadata is rejected.

### `ProducerRegistryV1`

`src/manafold_census/analysis/registry.py` stores a non-empty, sorted, unique
descriptor set. Its canonical digest is domain-separated and binds the exact
descriptor wire values. `for_authoritative_run()` rejects nondeterministic
descriptors and the currently unsupported live/model admission path.

The registry does not prove that an implementation behind an identity is
semantically correct. That remains a code/version and review responsibility.

### `ProducerContextV1`

The context carries:

```text
source_lock_digest
m2_requirement_schema
m2_bundle_schema
immutable producer-registry snapshot
immutable effective-pattern-registry snapshot | null
```

Snapshot values are recursively frozen and digest-checked. A descriptor that
declares a pattern dependency must match the context snapshot digest before its
`produce()` method is called. No network, clock, client, live model, or hidden
mutable registry state is part of the context.

### `ProducerFindingV1`

`ProducerFindingV1` is a typed, locally validated finding with optional pattern
identity, source field, face, fragment, clause, span, and candidate index.
`finding_validation.py` cross-binds it to the effective registry rule, rule
eligibility, rule digest, producer identity, source scope, actual source text,
candidate output template, evidence, and producer provenance.

This is the right seam for corpus exact-pattern reuse: the trace can be trusted
because the finding is bound to the candidate and the immutable rule snapshot.

### Pattern contracts

`src/manafold_census/analysis/patterns.py` defines a deliberately closed V1
grammar:

```text
MatcherKindV1:
    EXACT_FIELD_TEXT
    EXACT_FACE_FIELD_TEXT
    EXACT_FRAGMENT

NormalizationProfileV1:
    NONE

PatternSourceFieldV1:
    oracle_text
    keywords

EvidencePolicyV1:
    EXACT_FIELD
    EXACT_FRAGMENT
```

`PatternRuleV1` binds source scope, exact match text, typed M2 output template,
evidence policy, producer identity, and the exact M2 contract version. There is
no regex language, capture language, expression evaluator, or free-form output
template.

`PatternEligibilityV1` binds `(pattern_id, pattern_version)` to either
`REVIEWED_FOR_REUSE` or `NOT_ELIGIBLE`, plus a review record identifier and
record SHA-256. `EffectivePatternRegistryV1` requires a non-empty, sorted,
matching rule/eligibility set and includes both arrays in its digest.

`EffectivePatternRegistryV1.matches_exact_text()` is the only public matching
path. It returns no match for `NOT_ELIGIBLE`; it does not promote Requirement
review state.

The current fixture registry therefore supplies a synthetic effective snapshot,
not a corpus authority snapshot.

### Build and closure

`build_reference_m3()` in `analysis/build.py` currently:

1. loads and validates the complete M1 lifecycle and source-lock authority;
2. admits deterministic producer descriptors;
3. snapshots producer and pattern registries;
4. executes producers over structural records;
5. validates candidates and findings;
6. reconciles producer-neutral candidates;
7. selects the frozen card outcome matrix;
8. writes canonical records and trace shards plus the analysis manifest;
9. rereads the output and runs independent closure validation before atomic publication.

`validate_analysis_closure()` rereads M1 authority, source lock, M3 records,
M3 traces, manifest fields, identity sets, source-lock bindings, shard bytes,
and negative-authority trace completeness. `build_reports()` is downstream and
must not become an input to analysis identity.

## 3. Preferred corpus producer architecture

The smallest production seam should be a generic,
registry-driven exact producer, tentatively named:

```text
RegistryDrivenExactPatternProducerV1
```

It is not a card executor and it is not a rules engine. Its algorithm is:

```text
immutable EffectivePatternRegistryV1 snapshot
        + exact StructuralCardRecordV1
        ↓
eligible exact rule lookup
        ↓
exact field/face/fragment match
        ↓
typed PatternOutputTemplateV1 constructor
        ↓
RequirementV1(review=PROPOSED)
        + exact source-aware evidence
        + DETERMINISTIC_RULE provenance
        + ProducerFindingV1
```

Required behavior:

- execute only `REVIEWED_FOR_REUSE` rules;
- fail closed for `NOT_ELIGIBLE`, missing, malformed, or mismatched rules;
- require the descriptor pattern digest to equal the context snapshot digest;
- enforce rule producer identity/version against the executing descriptor;
- use only existing typed M2 family/kind/parameter constructors;
- produce source-aware evidence consistent with the rule scope and policy;
- emit `PROPOSED` Requirements only;
- emit no relationships unless an explicit, separately validated proposal exists;
- emit no negative authority and no terminal review state;
- classify unsupported template/source combinations as execution/contract failure;
- remain a pure single-process function of exact source, context snapshots, and
  versioned implementation.

The producer implementation must not inspect card names, hard-code card IDs,
call a model, fetch a URL, load executable data, or infer a semantic meaning
outside the rule's typed template.

## 4. Review authority and corpus pattern registry

The authority split is:

```text
generic producer implementation
    != proposed pattern rule
    != REVIEWED_FOR_REUSE authority
    != negative review authority
```

The coding agent may implement the generic matcher, but it MUST NOT change a
rule's eligibility to `REVIEWED_FOR_REUSE` as part of implementation.

The maintainer review process must inspect, for every corpus rule:

```text
pattern_id / version
matcher kind
exact source field and face scope
exact match text
typed output family/kind/parameters
evidence policy
producer binding
known false-positive scope
known false-negative scope
reviewer identity
review decision
review record digest
```

The resulting effective corpus registry must be a separately pinned snapshot.
Its digest, producer registry digest, source-lock digest, M1 structural manifest
SHA, M1 aggregate digest, and build profile must be recorded in the campaign
evidence. The synthetic fixture registry must not be copied or renamed as a
corpus registry without a new maintainer decision.

### Review authority mechanism

For the first tiny corpus subset, no new schema is required. The existing
`PatternEligibilityV1` wire contract can carry the frozen eligibility state,
while a maintainer review packet outside the runtime wire contract records the
review evidence and exact digest. The effective registry digest binds the
runtime snapshot; the review packet binds the human decision that made the
eligibility state legitimate.

If future governance requires machine-readable review workflow records, a new
authority schema may be proposed separately. It is not needed for this first
unblock design and is not authorized here.

### Acyclic review-digest flow

The maintainer decision record MUST NOT contain the effective registry digest.
The dependency order is strictly:

```text
maintainer decision record
    ↓ SHA-256(decision record)
PatternEligibilityV1.review_record_sha256
    ↓
effective PatternRegistryV1 snapshot
    ↓ effective registry digest
downstream campaign configuration and evidence report
```

The registry digest is recorded only after the decision record is frozen. It is
never written back into that decision record, so the two digests cannot form a
hash cycle.

## 5. Minimum viable corpus semantic scope

The first corpus configuration should enable exactly one already-understood
exact fragment rule, with a new corpus-specific identity and corpus review
record. It should not reuse the fixture review IDs.

Proposed rule:

```text
pattern_id       = m3.corpus.exact-clause.draw-two-cards
pattern_version  = 1
matcher_kind     = EXACT_FRAGMENT
source_field     = oracle_text
face_index       = null
normalization    = NONE
match_text       = "Draw two cards."
evidence_policy  = EXACT_FRAGMENT
family           = effect
kind             = draw_cards
parameters.drawer.role         = source
parameters.drawer.multiplicity = one
parameters.drawer.ordinal      = null
parameters.quantity.mode       = exact
parameters.quantity.value      = 2
producer_id      = m3.registry-exact-pattern
producer_version = 1
eligibility      = NOT_ELIGIBLE until explicit maintainer review
requirement_review_status = PROPOSED always
```

The complete `DrawCardsParametersV1` payload above is part of the proposed
rule's typed output template. It is not inferred from the synthetic fixture at
runtime.

This is a proposal, not a corpus approval. Known limitations are explicit:

- false positives remain possible when the exact phrase appears in a context
  whose meaning is not the fixed template;
- all alternate draw syntax, quantities, costs, conditions, replacement effects,
  and paraphrases remain outside the scope;
- cards with no exact match remain unresolved unless separately closed by an
  explicit negative authority;
- a match is a deterministic candidate, not semantic certification.

No negative authority is proposed for the minimum configuration. The first
campaign therefore deliberately has sparse candidate coverage.

## 6. No-match and outcome semantics

The frozen outcome boundary remains:

```text
NO_MATCH from all active producers
+ no explicit negative authority
→ UNRESOLVED_ANALYSIS
```

The corpus report must distinguish:

```text
candidate extraction coverage
semantic support
review/certification authority
```

An honest run may contain tens of thousands of unresolved cards. It may prove
closure, reproducibility, and the exact behavior of the enabled subset without
claiming that unresolved cards have no requirements.

## 7. Immutable campaign configuration

The initial campaign can bind its identity using existing contracts:

```text
SourceLock digest
M1 structural manifest SHA-256
M1 structural aggregate digest
ProducerRegistryV1 digest
EffectivePatternRegistryV1 digest
producer_id / producer_version
exact repository HEAD containing the implementation
build profile
negative-authority configuration = NONE
```

No new persisted schema is required for the first configuration:

```text
NEW_SCHEMA_REQUIRED = NO
```

The exact repository HEAD is important because `ProducerDescriptorV1` currently
pins logical producer identity/version and registry digest, while implementation
bytes are supplied by the frozen repository commit. Run A/B byte parity detects
any nondeterministic implementation behavior. A future code-digest field may be
proposed if governance requires manifest-level binding of implementation bytes.

## 8. Security and determinism review

The proposed architecture requires:

```text
LIVE_NETWORK_REQUIRED          = NO
MODEL_API_REQUIRED             = NO
DYNAMIC_EXECUTION_REQUIRED     = NO
SYNTHETIC_FIXTURE_AS_AUTHORITY = NO
UNREVIEWED_PATTERN_ACTIVATION  = NO
```

Specific controls:

- registry data is canonical JSON and digest-bound, not executable;
- no `eval`, `exec`, `pickle`, dynamic import, subprocess, or network path is
  part of the producer;
- registry iteration is sorted and snapshot-backed;
- producer and pattern versions are included in the execution identity;
- pattern eligibility changes alter the effective registry digest;
- `NOT_ELIGIBLE` rules cannot be activated through the public matcher;
- no silent fallback turns a producer exception into `NO_MATCH`;
- no-match cannot become a semantic zero proof;
- output is canonical JSONL with independent reread/closure validation.

## 9. Required implementation decomposition

### UNBLOCK_02 — generic exact-pattern producer

```text
FILES:
  CREATE src/manafold_census/analysis/pattern_producer.py
  CREATE tests/test_analysis_pattern_producer.py
  OPTIONAL MODIFY src/manafold_census/analysis/__init__.py

RED TESTS:
  eligible exact fragment emits one typed PROPOSED Requirement
  finding binds candidate/rule/source/evidence
  NOT_ELIGIBLE produces no match
  registry digest mismatch fails before producer execution
  unsupported scope/template fails closed
  no network/model/dynamic execution path

GATES:
  focused tests, full pytest, format, Ruff, mypy
  production modules <=500 lines
  existing Task-10 conformance rerun

AUTHORITY:
  implementation only; no REVIEWED_FOR_REUSE promotion

COMMIT:
  feat: add registry-driven exact M3 producer

STOP:
  independent review before any corpus pattern is enabled
```

### UNBLOCK_03 — corpus pattern proposal and maintainer review packet

```text
FILES:
  CREATE config/analysis/m3-corpus-pattern-registry.v1.json
  CREATE docs/reports/2026-09-13-m3-corpus-pattern-review.md
  CREATE tests/test_analysis_corpus_pattern_registry.py

CONTENT:
  one proposed exact rule with a corpus-specific review identity
  initial eligibility = NOT_ELIGIBLE
  full typed DrawCardsParametersV1 output template
  explicit false-positive/false-negative analysis
  effective registry digest and producer binding

AUTHORITY:
  proposal remains NOT_ELIGIBLE until maintainer review

STOP:
  maintainer decision required; no Task 11 retry
```

### UNBLOCK_04 — apply explicit review decisions and freeze registry

```text
FILES:
  MODIFY config/analysis/m3-corpus-pattern-registry.v1.json
  MODIFY tests/test_analysis_corpus_pattern_registry.py
  CREATE docs/reports/2026-09-13-m3-corpus-pattern-approval.md

GATES:
  exact review packet identity/digest matches eligibility record
  decision-record SHA is computed before the registry digest
  decision record does not contain the resulting registry digest
  effective registry digest is recorded
  config/analysis namespace is used; no fixture review identity is reused
  producer remains PROPOSED-only
  Task-10 conformance rerun is PASS

STOP:
  independent review of the explicit maintainer decision
```

### UNBLOCK_05 — bind the offline campaign configuration

```text
FILES:
  CREATE tests/test_analysis_corpus_campaign_config.py
  CREATE docs/reports/2026-09-13-m3-corpus-campaign-config.md

CONTENT:
  exact SourceLock/M1/producer/pattern/build-profile identities
  config/analysis/m3-corpus-pattern-registry.v1.json path and digest
  downstream registry digest recording; no write-back into the decision record
  exact repository HEAD
  no negative authority
  semantic scope = one approved exact rule

GATES:
  configuration is reproducible without network access
  campaign runner can load frozen M1 and effective registry
  no global run occurs in this slice

STOP:
  independent review and explicit Task 11 retry authorization
```

### TASK_11_RETRY — post-implementation offline evidence campaign

Only after UNBLOCK_02 through UNBLOCK_05 pass review may the separately
authorized Run A/Run B 38,740-card campaign execute. It must use a killable
offline runner, a 3,600-second budget per run, independent reread/closure, and
byte-identical Run A/B output comparison. The campaign report must state the
small enabled semantic scope and unresolved/no-match counts without semantic
certification claims.

## 10. Final authority status

```text
CURRENT_BLOCKER = missing corpus-scale producer and corpus review authority
RECOMMENDED_ARCHITECTURE = registry-driven exact-pattern producer
PROPOSED_MINIMUM_SEMANTIC_SCOPE = one reviewed exact fragment rule
REVIEW_AUTHORITY_REQUIRED = YES
NEW_SCHEMA_REQUIRED = NO for the first configuration
PRODUCTION_CODE_REQUIRED = YES in UNBLOCK_02
TASK_10_REVALIDATION_REQUIRED = YES
TASK_11_RETRY_ALLOWED = NO
```
