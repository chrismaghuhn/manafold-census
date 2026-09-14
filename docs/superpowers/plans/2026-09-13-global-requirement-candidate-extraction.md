
# M3 Global Requirement Candidate Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task after independent authorization. Steps use checkbox syntax for tracking.

**Goal:** Implement the frozen M3 design as a deterministic, fail-closed,
source-bound candidate-extraction pipeline that emits exactly one thin analysis
record per M1 card without changing M1, M2, or M4 semantics.

**Architecture:** Add a focused analysis package with immutable wire models,
allowlisted producer and effective-pattern registries, a separate extraction
trace, producer-neutral reconciliation, canonical 16-way JSONL artifact
publication, independent closure validation, and derived reports. The first
reference path is single-process and synthetic-fixture-driven; a separately
authorized corpus task may run it against the pinned 38,740-card M1 artifact.
Execution failures abort publication, while only semantic uncertainty becomes
UNRESOLVED_ANALYSIS.

**Tech Stack:** Python 3.12+, standard-library dataclasses/enum/json/hashlib/
pathlib/tempfile/subprocess, existing canonical_json_bytes, existing
domain_digest, existing M1/M2 models and JSON-Schema validation, pytest,
Ruff, mypy, setuptools packaging, the existing Justfile, and GitHub Actions.
No new runtime dependency.

---

## Authorization and execution protocol

This plan is authorized as a plan artifact only. Its numbered tasks are not
implementation authorization.

~~~text
DESIGN_SPECIFICATION              = docs/superpowers/specs/2026-09-13-global-requirement-candidate-extraction-design.md
DESIGN_HEAD                       = 557972423e56060e3331c410ba47c706d9817e5c
BASELINE_MAIN                     = d73e611b8acbb22ddbbbdfe84eae73b080efe56e
BRANCH                            = feat/m3-global-requirement-candidate-extraction
M3_DESIGN_FROZEN                  = YES
M3_IMPLEMENTATION_PLAN_AUTHORIZED = YES
M3_IMPLEMENTATION_AUTHORIZED      = NO
GLOBAL_EXTRACTION_STARTED         = NO
M4_STARTED                        = NO
PR_AUTHORIZED                     = NO
MERGE_AUTHORIZED                  = NO
~~~

For every numbered implementation task:

1. obtain explicit authorization for exactly that task;
2. run the preservation checks before touching a declared file;
3. write the focused failing tests first;
4. run the focused test and record the expected failure;
5. implement only the smallest declared slice;
6. run the focused tests and focused Ruff/mypy checks;
7. run the complete repository regression gates;
8. run the runtime-budget checks described below;
9. inspect tracked plus untracked scope;
10. stage only the task's declared files;
11. run git diff --cached --check;
12. create one standalone commit with the task's exact commit message;
13. push only feat/m3-global-requirement-candidate-extraction;
14. verify the remote branch head equals the local task commit;
15. report exact SHA, parent, files, gates, timeout statuses, and findings; and
16. stop with NEXT_TASK_AUTHORIZED=NO.

Pushing a task branch is not PR authorization. PR authorization is not merge
authorization. No task may start M4 or silently run the full corpus.

### Shared preservation checks

Run before and after each authorized task:

~~~powershell
git status --short --branch
git diff --name-only
git diff --cached --name-only
git diff -- source-locks/scryfall-oracle-v1.json config/sources/scryfall-oracle.v1.json
git diff -- src/manafold_census/models.py src/manafold_census/canonical.py src/manafold_census/digest.py src/manafold_census/corpus src/manafold_census/source src/manafold_census/structural src/manafold_census/semantic
git diff -- .github justfile pyproject.toml src/manafold_census/cli.py
~~~

The expected result is that only the current task's declared files change.
M1 source locks, source configuration, foundation models, canonicalization,
digest helpers, corpus/source/structural packages, and frozen M2 semantic
modules remain unchanged unless a task explicitly declares a compatibility
registration-only edit.

The scope check must union tracked and untracked paths:

~~~powershell
$tracked = @(git diff --name-only)
$staged = @(git diff --cached --name-only)
$untracked = @(git ls-files --others --exclude-standard)
$all = @($tracked) + @($staged) + @($untracked) | Sort-Object -Unique
$bad = $all | Where-Object {
    $_ -match '^(source-locks|config|\.github|justfile|pyproject\.toml|'
        + 'src/manafold_census/(models|canonical|digest|corpus|source|structural|semantic))'
}
if ($bad) { $bad; throw 'M1, M2, or out-of-scope file changed' }
~~~

The only planned exceptions are the explicitly declared changes to
src/manafold_census/cli.py, justfile, .github/workflows/ci.yml,
tests/test_resources.py, and tests/test_maintainability.py in their named
tasks.

### Mandatory repository gates

Every implementation task must run these commands from the repository root:

~~~powershell
python -m pytest -q
ruff format --check .
ruff check .
mypy src/manafold_census
~~~

Expected result: exit code 0, zero test failures, zero formatting changes, zero
Ruff findings, and zero mypy findings. A blocked or unrun command is reported
BLOCKED or NOT_RUN; it is never reported PASS.

## Verification runtime budget

The normal verification contract is:

~~~text
MAX_SINGLE_TEST_RUNTIME_SECONDS            = 600
MAX_SINGLE_GATE_SUBPROCESS_RUNTIME_SECONDS = 600
~~~

This plan does not claim that the repository currently enforces a true
per-test timeout. The inspected repository is Python-only: it has no Rust
files, no pytest-timeout dependency, and its CI invokes pytest, Ruff, mypy,
reproduction, corpus, structural, wheel, and fresh-wheel commands directly.
Several existing Python tests invoke subprocesses without a timeout argument.
Therefore the implementation plan records:

~~~text
PER_TEST_TIMEOUT_ENFORCEMENT      = BLOCKED
LOCAL_COMMAND_TIMEOUT_ENFORCEMENT = EXTERNAL_EXECUTION_ENVIRONMENT
HOSTED_PER_STEP_600S_ENFORCEMENT  = NOT_IMPLEMENTED
~~~

No dependency or runner architecture is added implicitly by this M3 plan. A
separately authorized verification-tooling task must add true per-test timeout
enforcement if that status is to change. Until then, every normal gate command
must be launched under an externally enforced 600-second subprocess budget in
the execution environment, and each task must record the observed elapsed time.

Any timeout must fail the command with a diagnostic containing:

~~~text
TIMEOUT
command/test identity
configured limit = 600 seconds
elapsed time when available
RERUN command
~~~

No normal PR gate may contain a soak test, large fuzz campaign, benchmark,
offline corpus build, or research/provisioning workload. The pinned 38,740-card
build is a separately authorized evidence workload and is never part of the
ordinary fixture/PR gate.

## File map and ownership

Writing this plan creates no implementation files other than this plan.

### Analysis production package

Create these focused modules under src/manafold_census/analysis/:

* __init__.py — narrow public exports; no CLI or filesystem enumeration.
* model.py — AnalysisOutcomeV1, NegativeReviewAuthorityRefV1,
  CardAnalysisRecordV1, source-key construction, and strict wire invariants.
* authority.py — NegativeRequirementAuthorityRecordV1, the closed negative
  scope value, deterministic record/scope digests, and authority loading.
* producer.py — producer protocol, descriptor, immutable context, result
  status, candidate and relationship proposal values, and proposal-only guard.
* registry.py — producer registry validation, deterministic admission, sorted
  registry wire, and registry digest.
* patterns.py — declarative pattern definitions, effective eligibility
  snapshot, exact matcher dispatch seam, and pattern registry digest.
* trace.py — extraction-local producer/pattern/source-locator trace values,
  deterministic event ordering, and trace shard wire values.
* reconcile.py — duplicate identity merge, divergent-resolution omission,
  relationship validation, and unresolved classification.
* manifest.py — record/trace shard descriptors, identity-set digest,
  canonical partition/merge helpers, analysis manifest, and manifest/index
  digests with no report references.
* validate.py — independent input, record, trace, shard, manifest, and
  closure reconstruction.
* build.py — single-process reference orchestration, temporary output,
  failure handling, and atomic publication.
* report.py — rebuildable reports and downstream report-index.json.

Every production module must remain at or below 500 lines. Split by seam before
extending a module past the existing maintainability limit.

### Normative schemas

Create these schemas in separate tasks:

* schemas/card-analysis.v1.schema.json
* schemas/negative-requirement-authority.v1.schema.json
* schemas/producer-registry.v1.schema.json
* schemas/pattern-registry.v1.schema.json
* schemas/analysis-trace.v1.schema.json
* schemas/analysis-manifest.v1.schema.json
* schemas/analysis-report.v1.schema.json

Use Draft 2020-12, additionalProperties=false for fixed objects, and the
existing local referencing registry. The card-analysis schema references the
frozen M2 bundle schema; it does not copy or alter M2 definitions.

### Test and fixture files

Create focused tests:

* tests/test_analysis_model.py
* tests/analysis_fixtures.py — shared fixed M1/M2/M3 fixture constructors used
  by all focused tests.
* tests/test_analysis_authority.py
* tests/test_analysis_producer.py
* tests/test_analysis_registry.py
* tests/test_analysis_patterns.py
* tests/test_analysis_trace.py
* tests/test_analysis_reconcile.py
* tests/test_analysis_manifest.py
* tests/test_analysis_validate.py
* tests/test_analysis_build.py
* tests/test_analysis_report.py
* tests/test_analysis_reproduction.py
* tests/test_analysis_conformance.py

Create the bounded synthetic fixture package:

* fixtures/analysis/golden-cards.json
* fixtures/analysis/producer-registry.v1.json
* fixtures/analysis/pattern-registry.v1.json
* fixtures/analysis/negative-authority.v1.json

Modify only the following existing files in the named integration tasks:

* src/manafold_census/validation.py — register new local schema references;
* src/manafold_census/cli.py — add the explicitly scoped M3 commands;
* justfile — add offline synthetic M3 commands;
* .github/workflows/ci.yml — add only bounded synthetic M3 validation;
* tests/test_resources.py — assert packaged M3 schemas;
* tests/test_maintainability.py — assert M3 module size and scope rules.

Do not modify source locks, M1/M2 schemas/models, the M1/M2 fixtures, or any
engine/Rust repository from this plan.

## Task 1: Card-analysis wire model and outcome boundary

**Scope:** Add only the thin card-analysis model, the complete negative review
authority artifact contract, source identity keys, and their schemas. Do not add
producers, patterns, reconciliation, build I/O, CLI, reports, or corpus
processing.

**Files:**

* Create src/manafold_census/analysis/__init__.py.
* Create src/manafold_census/analysis/model.py.
* Create src/manafold_census/analysis/authority.py.
* Create schemas/card-analysis.v1.schema.json.
* Create schemas/negative-requirement-authority.v1.schema.json.
* Create tests/test_analysis_model.py.
* Create tests/test_analysis_authority.py.
* Create tests/analysis_fixtures.py.
* Modify src/manafold_census/validation.py only if the schema registry needs
  the card-analysis-to-M2 bundle reference.

### Step 1: Write failing model tests

Create tests/analysis_fixtures.py with fixed constructors named
source_ref(), structural_record(), bundle_from_other_source(), and
source_lock_digest(). Use fixed UUIDs and digests and never use randomness or
current time. Add tests for one valid M1 StructuralCardRecordV1, one matching
M2 SourceRecordRefV1, and one minimal RequirementBundleV1.

Add tests with these behaviors:

~~~python
def test_requirements_produced_requires_one_bundle() -> None:
    with pytest.raises(ValueError, match="bundle"):
        CardAnalysisRecordV1(
            source=source_ref(),
            outcome=AnalysisOutcomeV1.REQUIREMENTS_PRODUCED,
            bundle=None,
            no_requirements_basis=None,
        )


def test_no_requirements_requires_negative_authority_reference() -> None:
    with pytest.raises(ValueError, match="authority"):
        CardAnalysisRecordV1(
            source=source_ref(),
            outcome=AnalysisOutcomeV1.NO_REQUIREMENTS_APPLICABLE,
            bundle=None,
            no_requirements_basis=None,
        )


def test_unresolved_may_have_zero_or_more_retained_requirements() -> None:
    record = CardAnalysisRecordV1(
        source=source_ref(),
        outcome=AnalysisOutcomeV1.UNRESOLVED_ANALYSIS,
        bundle=None,
        no_requirements_basis=None,
    )
    assert record.to_wire()["bundle"] is None


def test_source_key_excludes_source_lock_context_like_m2_identity() -> None:
    first = source_ref(source_lock_digest=FIXED_LOCK_DIGEST)
    second = source_ref(source_lock_digest=OTHER_LOCK_DIGEST)
    assert card_source_key(first) == card_source_key(second)


def test_card_record_rejects_bundle_from_another_source() -> None:
    with pytest.raises(ValueError, match="source"):
        CardAnalysisRecordV1(
            source=source_ref(),
            outcome=AnalysisOutcomeV1.REQUIREMENTS_PRODUCED,
            bundle=bundle_from_other_source(),
            no_requirements_basis=None,
        )


def test_card_analysis_wire_rejects_unknown_fields_and_wrong_schema() -> None:
    # Parse a valid wire value, add one key, and mutate schema.
    # Both mutations must raise before a record is returned.
~~~

Add authority tests with these exact requirements:

~~~python
def test_negative_authority_record_id_is_deterministic() -> None:
    first = negative_authority_record()
    second = negative_authority_record()
    assert first.record_id == second.record_id
    assert first.record_sha256 == second.record_sha256


def test_negative_authority_record_rejects_any_decision_other_than_no_requirements() -> None:
    with pytest.raises(ValueError, match="decision"):
        negative_authority_record(decision="UNRESOLVED_ANALYSIS")


def test_negative_authority_scope_digest_is_the_digest_of_the_closed_scope_wire() -> None:
    record = negative_authority_record()
    assert record.scope_digest == negative_authority_scope_digest(record.scope)


def test_negative_authority_record_digest_excludes_only_record_sha256() -> None:
    record = negative_authority_record()
    assert record.record_sha256 == negative_authority_record_sha256(record)


def test_card_reference_requires_exact_authority_source_and_scope() -> None:
    # A reference to another source, another scope, or another record digest
    # must fail authority validation before NO_REQUIREMENTS_APPLICABLE is used.
~~~

### Step 2: Run the focused tests and record the expected failure

~~~powershell
python -m pytest tests/test_analysis_model.py tests/test_analysis_authority.py -q
~~~

Expected: collection fails because manafold_census.analysis and
CardAnalysisRecordV1 do not exist.

### Step 3: Implement the minimal model

Define:

~~~python
class AnalysisOutcomeV1(StrEnum):
    REQUIREMENTS_PRODUCED = "REQUIREMENTS_PRODUCED"
    NO_REQUIREMENTS_APPLICABLE = "NO_REQUIREMENTS_APPLICABLE"
    UNRESOLVED_ANALYSIS = "UNRESOLVED_ANALYSIS"


@dataclass(frozen=True, slots=True)
class NegativeReviewAuthorityRefV1:
    authority_id: str
    authority_version: str
    record_id: str
    record_sha256: str
    scope_digest: str


@dataclass(frozen=True, slots=True)
class CardAnalysisRecordV1:
    source: SourceRecordRefV1
    outcome: AnalysisOutcomeV1
    bundle: RequirementBundleV1 | None
    no_requirements_basis: NegativeReviewAuthorityRefV1 | None
~~~

Use strict wire keys and existing M2 source/bundle values. Define
card_source_key(source) as the tuple
(record_schema, oracle_id, source_card_id, source_record_sha256). Do not add
an artificial analysis_id.

Enforce these cross-field invariants:

* REQUIREMENTS_PRODUCED requires a non-null bundle and null authority basis;
* NO_REQUIREMENTS_APPLICABLE requires a null bundle and non-null authority
  reference;
* UNRESOLVED_ANALYSIS allows either a null or non-null bundle and requires a
  null authority reference;
* a non-null bundle source equals the record source; and
* the M2 bundle remains non-empty.

The negative authority reference is only a pinned external record reference.
No ordinary classifier or producer can construct the semantic outcome through
this model.

### Step 4: Implement the negative review authority contract

Define NegativeAuthorityScopeV1 as a closed value with exactly these fields:

~~~text
scope_schema       = census.m3-negative-authority-scope.v1
scope_id           = census.m3-semantic-requirement-applicability
scope_version      = v1
analysis_schema    = census.card-analysis.v1
m2_requirement_schema = census.semantic-requirement.v1
m2_bundle_schema   = census.semantic-requirement-bundle.v1
source_fields      = sorted non-empty tuple of controlled M1 field names
~~~

The allowed source_fields vocabulary is exactly oracle_text, keywords, and
face.oracle_text. No arbitrary expression, matcher,
predicate, JSON object, or executable rule is allowed in the scope.

Define NegativeRequirementAuthorityRecordV1 with exactly these fields:

~~~text
schema
authority_id
authority_version
record_id
source
scope
decision = NO_REQUIREMENTS_APPLICABLE
record_sha256
~~~

The record identity payload is the canonical object containing schema,
authority_id, authority_version, source, scope, and decision, excluding
record_id and record_sha256. Derive:

~~~text
record_id = nra_ + domain_digest(
    census.m3-negative-authority-record-id.v1,
    identity_payload
)
scope_digest = domain_digest(
    census.m3-negative-authority-scope.v1,
    scope.to_wire()
)
record_sha256 = sha256_bytes(
    canonical_json_bytes(
        {
            **identity_payload,
            "record_id": record_id,
        }
    )
)
~~~

The authority loader must parse the exact schema, recompute record_id,
record_sha256, and scope_digest, require decision exactly
NO_REQUIREMENTS_APPLICABLE, and require source equality with the M1 card. The
CardAnalysisRecordV1 reference carries authority_id, authority_version,
record_id, record_sha256, and scope_digest; the builder resolves that reference
against the loaded authority record before persisting the negative outcome.

### Step 5: Add the normative schemas and schema registration

Create schemas/card-analysis.v1.schema.json and
schemas/negative-requirement-authority.v1.schema.json. The authority schema
must close the scope and decision vocabularies and reject arbitrary scope
objects. Register both schemas through the existing validator without changing
M1 or M2 behavior.

### Step 6: Run focused checks

~~~powershell
python -m pytest tests/test_analysis_model.py tests/test_analysis_authority.py tests/test_resources.py -q
ruff format --check src/manafold_census/analysis tests/test_analysis_model.py
ruff check src/manafold_census/analysis tests/test_analysis_model.py
mypy src/manafold_census/analysis
~~~

Expected: all focused tests pass and static checks exit 0.

### Step 7: Commit the task

Before staging, confirm no producer, pattern, report, CLI, or corpus files are
changed.

~~~powershell
git add src/manafold_census/analysis/__init__.py src/manafold_census/analysis/model.py src/manafold_census/analysis/authority.py schemas/card-analysis.v1.schema.json schemas/negative-requirement-authority.v1.schema.json tests/test_analysis_model.py tests/test_analysis_authority.py tests/analysis_fixtures.py src/manafold_census/validation.py
git diff --cached --check
git commit -m 'feat: add M3 card analysis and negative authority contract'
~~~

## Task 2: Producer contract, registry, and deterministic admission

**Scope:** Define producer descriptors, candidate result values, the immutable
producer registry, proposal-only review enforcement, and deterministic admission.
Do not implement pattern matching, reconciliation, build orchestration, or live
model calls.

**Files:**

* Create src/manafold_census/analysis/producer.py.
* Create src/manafold_census/analysis/registry.py.
* Create schemas/producer-registry.v1.schema.json.
* Create tests/test_analysis_producer.py.
* Create tests/test_analysis_registry.py.
* Modify tests/analysis_fixtures.py with fixed producer descriptors and valid
  proposal constructors.

### Step 1: Write failing producer and registry tests

~~~python
def test_producer_descriptor_round_trips_and_registry_is_sorted() -> None:
    registry = ProducerRegistryV1.build([parser_descriptor(), exact_rule_descriptor()])
    assert [item.producer_id for item in registry.producers] == [
        "m3.exact-rule",
        "m3.parser",
    ]


def test_authoritative_registry_rejects_nondeterministic_active_producer() -> None:
    with pytest.raises(ProducerRegistryError, match="deterministic"):
        ProducerRegistryV1.build(
            [nondeterministic_model_descriptor()]
        ).for_authoritative_run()


def test_producer_candidate_with_terminal_review_is_invalid() -> None:
    candidate = requirement_with_review(ReviewStatusV1.ACCEPTED)
    with pytest.raises(ProducerContractError, match="PROPOSED"):
        validate_producer_candidate(
            candidate, structural_record(), source_lock_digest()
        )


def test_no_match_is_not_a_negative_card_result() -> None:
    result = ProducerResultV1.no_match()
    assert result.status is ProducerResultStatusV1.NO_MATCH
    assert result.negative_authority is None


def test_exception_is_not_converted_to_no_match() -> None:
    with pytest.raises(ProducerExecutionError):
        invoke_producer(raising_producer(), structural_record())
~~~

### Step 2: Run the focused tests and record the expected failure

~~~powershell
python -m pytest tests/test_analysis_producer.py tests/test_analysis_registry.py -q
~~~

Expected: collection fails because the producer package does not exist.

### Step 3: Implement producer values and the narrow interface

Define immutable values with strict wire conversion:

~~~python
class ProducerResultStatusV1(StrEnum):
    EMITTED = "EMITTED"
    NO_MATCH = "NO_MATCH"
    UNSUPPORTED_SHAPE = "UNSUPPORTED_SHAPE"


@dataclass(frozen=True, slots=True)
class ProducerDescriptorV1:
    producer_id: str
    producer_version: str
    derivation_method: DerivationMethodV1
    input_schema: str
    input_fields: tuple[str, ...]
    pattern_registry_digest: str | None
    deterministic: bool
    supports_relationships: bool


class CandidateProducerV1(Protocol):
    descriptor: ProducerDescriptorV1

    def produce(
        self,
        record: StructuralCardRecordV1,
        context: ProducerContextV1,
    ) -> ProducerResultV1: ...
~~~

ProducerContextV1 is read-only and contains the frozen source-lock digest, M2
schema IDs, the effective registry snapshots, and no network/client/time state.
ProducerResultV1 contains RequirementV1 candidates, explicit relationship
proposals, and typed semantic findings. Every candidate passes the existing M2
Requirement and source-aware validators before reconciliation.

Implement a proposal-only constructor/validator that requires:

~~~text
review.status = PROPOSED
reviewed_by = null
reviewed_claim_digest = null
~~~

Terminal and IN_REVIEW values from a normal producer are contract failures.
UNSUPPORTED_SHAPE is semantic unresolved input; exceptions and invalid result
shapes are execution failures.

### Step 4: Implement the registry and digest

ProducerRegistryV1.build() rejects duplicate
(producer_id, producer_version) pairs, unexpected fields, invalid M2 derivation
methods, and unsorted wire input. It sorts descriptors by
(producer_id, producer_version) and computes a domain-separated digest over the
sorted descriptor wire.

for_authoritative_run() rejects any active descriptor with deterministic false.
A model descriptor can pass only when its adapter is the deterministic importer
of a pinned proposal artifact; a live model adapter cannot pass.

### Step 5: Add schema and focused checks

Create schemas/producer-registry.v1.schema.json for descriptor and registry wire.
Run:

~~~powershell
python -m pytest tests/test_analysis_producer.py tests/test_analysis_registry.py tests/test_resources.py -q
ruff format --check src/manafold_census/analysis tests/test_analysis_producer.py tests/test_analysis_registry.py
ruff check src/manafold_census/analysis tests/test_analysis_producer.py tests/test_analysis_registry.py
mypy src/manafold_census/analysis
~~~

### Step 6: Commit the task

~~~powershell
git add src/manafold_census/analysis/producer.py src/manafold_census/analysis/registry.py schemas/producer-registry.v1.schema.json tests/test_analysis_producer.py tests/test_analysis_registry.py tests/analysis_fixtures.py
git diff --cached --check
git commit -m 'feat: define M3 producer contract'
~~~

## Task 3: Effective pattern registry and extraction trace

**Scope:** Add declarative pattern definitions, immutable review eligibility in
the effective snapshot, exact matcher metadata, and the non-authoritative trace
model. Do not add candidate reconciliation or report generation.

**Files:**

* Create src/manafold_census/analysis/patterns.py.
* Create src/manafold_census/analysis/trace.py.
* Create schemas/pattern-registry.v1.schema.json.
* Create schemas/analysis-trace.v1.schema.json.
* Create tests/test_analysis_patterns.py.
* Create tests/test_analysis_trace.py.
* Create fixtures/analysis/pattern-registry.v1.json.
* Modify tests/analysis_fixtures.py with exact rule and trace constructors.

### Step 1: Write failing pattern and trace tests

Cover:

~~~python
def test_effective_pattern_registry_digest_changes_when_eligibility_changes() -> None:
    eligible = effective_registry(reviewed_for_reuse=True)
    ineligible = effective_registry(reviewed_for_reuse=False)
    assert eligible.digest() != ineligible.digest()


def test_v1_rejects_arbitrary_output_templates_and_non_none_normalization() -> None:
    with pytest.raises(ValueError, match="typed output"):
        exact_clause_rule(output_template={"kind": "arbitrary"})
    with pytest.raises(ValueError, match="NONE"):
        exact_clause_rule(normalization_profile="LOWERCASE")


def test_pattern_identity_contains_behavior_but_not_card_name() -> None:
    rule = exact_clause_rule(
        pattern_id="m3.exact-clause.draw",
        version="1",
    )
    assert not hasattr(rule, "card_name")


def test_trace_locator_does_not_change_requirement_identity() -> None:
    first = requirement_from_fragment("draw a card", span=(0, 12))
    second = requirement_from_fragment("draw a card", span=(15, 27))
    assert first.requirement_id == second.requirement_id


def test_trace_events_have_deterministic_order() -> None:
    assert sorted(trace_events_in_reverse_order()) == canonical_trace_events()
~~~

### Step 2: Run the focused tests and record the expected failure

~~~powershell
python -m pytest tests/test_analysis_patterns.py tests/test_analysis_trace.py -q
~~~

Expected: collection fails because pattern and trace modules do not exist.

### Step 3: Implement effective pattern registry values

Define these closed V1 types in patterns.py:

~~~python
class MatcherKindV1(StrEnum):
    EXACT_FIELD_TEXT = "EXACT_FIELD_TEXT"
    EXACT_FACE_FIELD_TEXT = "EXACT_FACE_FIELD_TEXT"
    EXACT_FRAGMENT = "EXACT_FRAGMENT"


class NormalizationProfileV1(StrEnum):
    NONE = "NONE"


class PatternSourceFieldV1(StrEnum):
    ORACLE_TEXT = "oracle_text"
    KEYWORDS = "keywords"


class EvidencePolicyV1(StrEnum):
    EXACT_FIELD = "EXACT_FIELD"
    EXACT_FRAGMENT = "EXACT_FRAGMENT"


@dataclass(frozen=True, slots=True)
class PatternSourceScopeV1:
    field: PatternSourceFieldV1
    face_index: int | None


@dataclass(frozen=True, slots=True)
class PatternOutputTemplateV1:
    family: RequirementFamilyV1
    kind: RequirementKindV1
    parameters: KindPayloadV1
~~~

PatternOutputTemplateV1 contains an already typed M2 payload. It is not a JSON
mapping, expression, capture template, interpolation language, or executable
rule. MatcherKindV1 and PatternSourceScopeV1 enforce these combinations:

~~~text
EXACT_FIELD_TEXT       -> oracle_text or keywords, face_index = null
EXACT_FACE_FIELD_TEXT  -> oracle_text, face_index >= 0
EXACT_FRAGMENT         -> oracle_text, face_index = null or >= 0
normalization_profile  -> NONE only
evidence_policy        -> EXACT_FIELD or EXACT_FRAGMENT only
~~~

Define PatternRuleV1 with these fields:

~~~text
pattern_id
pattern_version
matcher_kind
source_scope
normalization_profile
match_text
output_template
evidence_policy
producer_id
producer_version
m2_contract_version
~~~

Define PatternEligibilityV1 with:

~~~text
pattern_id
pattern_version
eligibility = REVIEWED_FOR_REUSE | NOT_ELIGIBLE
review_record_id
review_record_sha256
~~~

Define EffectivePatternRegistryV1 as the sorted pair of definitions and
eligibility records. Its digest covers the complete effective snapshot,
including eligibility. Reject a definition without an eligibility entry, an
eligibility entry for an unknown rule, duplicate pairs, wrong versions, and
unsorted wire input.

Only declarative matcher kinds are accepted. The registry does not load code,
callbacks, regex engines, pickles, or card-specific executors.

### Step 4: Implement extraction trace values

Define RequirementTraceEventV1 values that can reference:

~~~text
card_source_key
producer_id/version
pattern_id/version/digest or null
source field and face index
exact raw fragment
clause ordinal or parser span when available
candidate requirement_id or local candidate key
reconciliation disposition
~~~

Trace values are audit/reproduction data. They are not M2 evidence, do not
participate in requirement_id, and do not change review status. Sort trace
events by source key, producer identity, pattern identity, candidate identity,
and trace kind; never by completion time.

### Step 5: Add schemas, fixture, and focused checks

Create strict pattern and trace schemas and a small registry fixture containing
one eligible exact clause rule and one ineligible rule. Run:

~~~powershell
python -m pytest tests/test_analysis_patterns.py tests/test_analysis_trace.py tests/test_resources.py -q
ruff format --check src/manafold_census/analysis tests/test_analysis_patterns.py tests/test_analysis_trace.py
ruff check src/manafold_census/analysis tests/test_analysis_patterns.py tests/test_analysis_trace.py
mypy src/manafold_census/analysis
~~~

### Step 6: Commit the task

~~~powershell
git add src/manafold_census/analysis/patterns.py src/manafold_census/analysis/trace.py schemas/pattern-registry.v1.schema.json schemas/analysis-trace.v1.schema.json tests/test_analysis_patterns.py tests/test_analysis_trace.py tests/analysis_fixtures.py fixtures/analysis/pattern-registry.v1.json
git diff --cached --check
git commit -m 'feat: add M3 pattern registry and trace'
~~~

## Task 4: Producer-neutral reconciliation

**Scope:** Implement exact candidate reconciliation and relationship handling.
Do not write shards, manifests, reports, CLI commands, or full-corpus code.

**Files:**

* Create src/manafold_census/analysis/reconcile.py.
* Create tests/test_analysis_reconcile.py.
* Modify tests/analysis_fixtures.py with compatible, disputed, and explicit
  relationship proposal constructors.

### Step 1: Write failing reconciliation tests

Add these required cases:

~~~python
def test_same_id_same_resolution_unions_evidence_and_provenance() -> None:
    result = reconcile([candidate_a(), candidate_b_with_other_evidence()])
    assert [item.requirement_id for item in result.requirements] == [
        candidate_a().requirement_id
    ]
    assert result.requirements[0].evidence == expected_union()
    assert result.requirements[0].provenance == expected_provenance_union()


def test_same_id_different_resolution_is_omitted_not_synthesized() -> None:
    result = reconcile([complete_candidate(), partial_candidate_same_id()])
    assert result.requirements == ()
    assert result.outcome_is_unresolved is True
    assert result.trace_dispositions == ("DISPUTED_IDENTITY_OMITTED",)


def test_other_undisputed_requirements_survive_a_disputed_identity() -> None:
    result = reconcile(
        [complete_candidate(), partial_candidate_same_id(), other_candidate()]
    )
    assert [item.requirement_id for item in result.requirements] == [
        other_candidate().requirement_id
    ]


def test_different_ids_are_not_deduplicated_or_priority_selected() -> None:
    result = reconcile([candidate_a(), competing_candidate_b()])
    assert {item.requirement_id for item in result.requirements} == {
        candidate_a().requirement_id,
        competing_candidate_b().requirement_id,
    }


def test_conflicts_with_requires_explicit_producer_proposal() -> None:
    without_relation = reconcile([candidate_a(), candidate_b()])
    assert without_relation.relationships == ()
    with_relation = reconcile([candidate_a(), candidate_b()], [explicit_conflict()])
    assert with_relation.relationships == (canonical_conflict(),)


def test_terminal_producer_review_is_execution_failure() -> None:
    with pytest.raises(ReconciliationFailure, match="PROPOSED"):
        reconcile([accepted_producer_candidate()])
~~~

### Step 2: Run the focused tests and record the expected failure

~~~powershell
python -m pytest tests/test_analysis_reconcile.py -q
~~~

Expected: collection fails because reconciliation is not implemented.

### Step 3: Implement the exact same-ID rule

Group candidates by requirement_id after M2 validation. For each group:

* if every resolution wire is identical, union evidence and provenance,
  preserve one PROPOSED review, and retain one canonical Requirement;
* if any resolution wire differs, retain no Requirement for that ID, emit a
  deterministic DISPUTED_IDENTITY_OMITTED trace disposition, mark the card
  unresolved, and preserve every candidate in trace data;
* never synthesize a third resolution, choose the more complete value, or use
  producer order as a tie-breaker.

The reconciler returns retained Requirements, validated relationships, an
unresolved flag, and trace dispositions. Other undisputed IDs remain retained.

### Step 4: Implement relationships and canonical ordering

Require relationship endpoints to be retained candidate IDs. Canonicalize
existing M2 symmetric relationships, reject self-edges, invalid ordinals,
duplicates, and cycles. Add CONFLICTS_WITH only when a producer explicitly
supplies it; never infer it from different IDs or different producers.

Sort final Requirements, relationships, evidence, provenance, and trace keys with
the frozen M2/canonical ordering rules.

### Step 5: Run focused checks and commit

~~~powershell
python -m pytest tests/test_analysis_reconcile.py -q
ruff format --check src/manafold_census/analysis tests/test_analysis_reconcile.py
ruff check src/manafold_census/analysis tests/test_analysis_reconcile.py
mypy src/manafold_census/analysis
git add src/manafold_census/analysis/reconcile.py tests/test_analysis_reconcile.py tests/analysis_fixtures.py
git diff --cached --check
git commit -m 'feat: reconcile M3 requirement proposals'
~~~

## Task 5: Canonical shards, manifest identity, and closure validation

**Scope:** Implement 16-way record/trace shard descriptors, identity-set
digests, the analysis manifest, and independent structural closure validation.
The manifest must not reference reports or report-index.json.

**Files:**

* Create src/manafold_census/analysis/manifest.py.
* Create src/manafold_census/analysis/validate.py.
* Create schemas/analysis-manifest.v1.schema.json.
* Create tests/test_analysis_manifest.py.
* Create tests/test_analysis_validate.py.

### Step 1: Write failing manifest and closure tests

~~~python
def test_oracle_id_first_hex_selects_the_existing_m1_shard() -> None:
    assert analysis_shard_for("0" + "1" * 31) == "0"
    assert analysis_shard_for("f" + "1" * 31) == "f"


def test_manifest_contains_trace_descriptors_but_no_report_digest() -> None:
    wire = manifest_for_fixture().to_wire()
    assert "trace_shards" in wire
    assert "derived_report_index_digest" not in wire
    assert "report_index_digest" not in wire


def test_identity_set_validator_rejects_missing_card_with_equal_count() -> None:
    with pytest.raises(AnalysisClosureError, match="missing"):
        validate_identity_set(
            expected=[source_key_a(), source_key_b()],
            actual=[source_key_a(), source_key_c()],
        )


def test_duplicate_and_extra_records_fail_closed() -> None:
    with pytest.raises(AnalysisClosureError, match="duplicate"):
        validate_identity_set(
            expected=[source_key_a()],
            actual=[source_key_a(), source_key_a()],
        )


def test_manifest_round_trip_rejects_noncanonical_order_and_unknown_fields() -> None:
    # Reverse shard order and add one unknown field; both mutations must raise.


def test_partition_merge_parity_is_not_a_worker_backend() -> None:
    records = synthetic_records_in_canonical_order()
    reference = merge_partitioned_records(
        partition_records(records, partition_count=1)
    )
    for count in (2, 8, 16):
        assert merge_partitioned_records(
            partition_records(records, partition_count=count)
        ) == reference
~~~

### Step 2: Run focused tests and record the expected failure

~~~powershell
python -m pytest tests/test_analysis_manifest.py tests/test_analysis_validate.py -q
~~~

Expected: collection fails because the manifest and closure modules do not
exist.

### Step 3: Implement shard descriptors and identity digests

Reuse the M1 partition function exactly: shard by the first lowercase
hexadecimal character of oracle_id, keep all 16 shard names, sort records
strictly by oracle_id, and frame every line as canonical JSON plus LF.

Define record_identity_set_digest() over the canonical sorted array of source
identity objects with domain:

~~~text
census.card-analysis-identity-set.v1
~~~

Define the ordered descriptor aggregate with:

~~~text
census.card-analysis-index.v1
~~~

Use only the existing canonical_json_bytes, domain_digest, and sha256_bytes
helpers. Each descriptor contains exactly relative_path, sha256, byte_length,
and record_count.

Implement the only V1 partition/merge seam here. partition_records(records,
partition_count) sorts records by canonical source order and assigns ordinal
index modulo partition_count. merge_partitioned_records(partitions) rejects
duplicate, missing, extra, or out-of-order source keys, then sorts the validated
records through the same canonical shard writer used by the reference build.
This is an in-process partition simulation only: it creates no workers,
processes, threads, queue, or workers= API.

### Step 4: Implement the report-independent analysis manifest

AnalysisManifestV1 must bind:

~~~text
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
~~~

It must not contain any report path, report digest, report-index digest, or
delivery-package digest. Its own identity is the SHA-256 of exact canonical
manifest bytes.

### Step 5: Implement independent closure validation

validate.py must read the M1 structural index and M3 artifact independently,
reject noncanonical JSONL, wrong shard, missing final LF, duplicates, extras,
source-lock mismatch, wrong structural manifest/aggregate digest, and outcome
wire inconsistencies. It must validate the exact identity set, not just counts.

It must not trust reports, trace-derived counts, or a caller-provided expected
record count as closure authority.

### Step 6: Add schema and focused checks

Create schemas/analysis-manifest.v1.schema.json with no report binding. Run:

~~~powershell
python -m pytest tests/test_analysis_manifest.py tests/test_analysis_validate.py tests/test_resources.py -q
ruff format --check src/manafold_census/analysis tests/test_analysis_manifest.py tests/test_analysis_validate.py
ruff check src/manafold_census/analysis tests/test_analysis_manifest.py tests/test_analysis_validate.py
mypy src/manafold_census/analysis
~~~

### Step 7: Commit the task

~~~powershell
git add src/manafold_census/analysis/manifest.py src/manafold_census/analysis/validate.py schemas/analysis-manifest.v1.schema.json tests/test_analysis_manifest.py tests/test_analysis_validate.py
git diff --cached --check
git commit -m 'feat: add M3 artifact manifest and closure'
~~~

## Task 6: Reference build, semantic outcomes, failure atomicity, and no cache

**Scope:** Implement the single-process M3 reference build using synthetic M1
records and registered producers. Add explicit semantic-unresolved handling,
negative authority validation, execution-failure aborts, temporary output, and
atomic publication. Do not run the pinned corpus.

**Files:**

* Create src/manafold_census/analysis/build.py.
* Modify src/manafold_census/analysis/model.py only if build cross-field
  validation requires a previously tested invariant correction.
* Create tests/test_analysis_build.py.
* Create fixtures/analysis/golden-cards.json.
* Create fixtures/analysis/negative-authority.v1.json.

### Step 1: Write failing build tests

Use a bounded synthetic corpus of exactly five cards:

~~~text
one exact pattern candidate
one card with two independent Requirements
one multi-face card
one unsupported-shape card
one no-match card with no negative authority
~~~

Add tests for:

~~~python
def test_reference_build_emits_one_record_per_synthetic_m1_card(tmp_path) -> None:
    result = build_reference_m3(
        synthetic_structural_dir(),
        fixture_registries(),
        tmp_path / "out",
    )
    assert result.manifest.record_count == 5
    assert result.identity_set == synthetic_m1_identity_set()


def test_no_match_without_negative_authority_is_unresolved(tmp_path) -> None:
    result = build_reference_m3(
        no_match_fixture(),
        fixture_registries(),
        tmp_path / "out",
    )
    card = result.record_for(no_match_source_key())
    assert card.outcome is AnalysisOutcomeV1.UNRESOLVED_ANALYSIS
    assert card.bundle is None


def test_valid_negative_authority_allows_no_requirements_applicable(tmp_path) -> None:
    result = build_reference_m3(
        negative_authority_fixture(),
        fixture_registries(),
        tmp_path / "out",
    )
    card = result.record_for(negative_authority_source_key())
    assert card.outcome is AnalysisOutcomeV1.NO_REQUIREMENTS_APPLICABLE


def test_negative_authority_conflict_is_unresolved(tmp_path) -> None:
    # A valid negative authority plus a valid candidate must retain the
    # candidate in trace and classify the card as unresolved.


def test_producer_exception_aborts_without_manifest(tmp_path) -> None:
    with pytest.raises(AnalysisBuildError, match="PRODUCER_EXCEPTION"):
        build_reference_m3(
            exception_fixture(),
            fixture_registries(),
            tmp_path / "out",
        )
    assert not (tmp_path / "out" / "analysis-manifest.json").exists()


def test_invalid_requirement_aborts_without_card_failure_record(tmp_path) -> None:
    # The failed card is present only in diagnostics, never in published records.


def test_build_has_no_authoritative_cache_or_resume_path(tmp_path) -> None:
    # Two clean builds read the same fixture inputs and produce the same bytes;
    # no cache directory is consulted or published.
~~~

### Step 2: Run focused tests and record the expected failure

~~~powershell
python -m pytest tests/test_analysis_build.py -q
~~~

Expected: collection fails because the reference build does not exist.

### Step 3: Implement the reference build loop

Implement build_reference_m3(structural_index, producer_registry,
pattern_registry, output_dir, negative_authority=None) with this order:

1. validate the frozen M1 structural input and all bound digests;
2. call producer_registry.for_authoritative_run() and reject any
   deterministic=False producer;
3. validate the effective pattern registry and its digest;
4. derive the expected M1 source identity set;
5. iterate cards in canonical oracle_id order;
6. invoke every producer against the same immutable context;
7. re-raise producer exceptions as execution failures;
8. validate every candidate through the existing M2 model and source-aware
   validator;
9. reconcile candidates and explicit relationships;
10. load NegativeRequirementAuthorityRecordV1 through the Task 1 authority
    loader and use NO_REQUIREMENTS_APPLICABLE only after exact
    record/source/scope/digest validation and no conflicting candidate;
11. use UNRESOLVED_ANALYSIS for unsupported shapes, empty no-match without
    authority, disputed same-ID resolution, or negative-authority conflict;
12. emit no CardAnalysisRecord for an execution failure;
13. validate identity-set closure before publication; and
14. write and re-read the complete artifact before publishing it.

### Step 4: Implement authority loading, temporary output, and atomic publication

The build must call the authority loader from analysis.authority; Task 6 must
not parse the negative-authority fixture with ad hoc JSON logic. The loader
recomputes the deterministic record ID, record SHA-256, and scope digest,
requires the exact source identity, and rejects an authority record with an
unknown field, unsupported scope field, or decision other than
NO_REQUIREMENTS_APPLICABLE.

Write records and trace to a fresh temporary directory. Do not overwrite a
published directory. On producer, validation, reconciliation, source, shard,
manifest, or publication failure, leave only non-authoritative diagnostics and
do not write an authoritative analysis-manifest.json.

The output layout is fixed:

~~~text
records/0.jsonl ... records/f.jsonl
trace/0.jsonl ... trace/f.jsonl
analysis-manifest.json
~~~

No reports are produced by this task; report generation follows manifest
publication in Task 7.

### Step 5: Add fixtures and run focused checks

Keep fixtures small, synthetic, deterministic, and independent of the Scryfall
cache. Run:

~~~powershell
python -m pytest tests/test_analysis_build.py tests/test_analysis_model.py tests/test_analysis_reconcile.py -q
ruff format --check src/manafold_census/analysis tests/test_analysis_build.py
ruff check src/manafold_census/analysis tests/test_analysis_build.py
mypy src/manafold_census/analysis
~~~

### Step 6: Commit the task

~~~powershell
git add src/manafold_census/analysis/build.py tests/test_analysis_build.py fixtures/analysis/golden-cards.json fixtures/analysis/negative-authority.v1.json
git diff --cached --check
git commit -m 'feat: build deterministic M3 analysis artifacts'
~~~

## Task 7: Derived reports and downstream report index

**Scope:** Add deterministic reports and report-index.json downstream of the
finalized analysis manifest. Never add report hashes to AnalysisManifestV1.

**Files:**

* Create src/manafold_census/analysis/report.py.
* Create schemas/analysis-report.v1.schema.json.
* Create tests/test_analysis_report.py.

### Step 1: Write failing report tests

~~~python
def test_report_index_binds_analysis_manifest_and_report_bytes(tmp_path) -> None:
    report_index = build_reports(validated_fixture_run(), tmp_path / "reports")
    assert report_index.analysis_manifest_sha256 == validated_fixture_manifest_sha256()
    assert report_index.report_descriptors


def test_analysis_manifest_does_not_change_when_report_bytes_change() -> None:
    before = validated_fixture_manifest_bytes()
    mutate_derived_report_only()
    after = validated_fixture_manifest_bytes()
    assert before == after


def test_report_index_is_not_an_analysis_manifest_input() -> None:
    assert "report-index" not in analysis_manifest_wire_text()


def test_report_order_and_reuse_counts_are_integer_and_deterministic() -> None:
    first = build_reports(validated_fixture_run(), first_output())
    second = build_reports(validated_fixture_run(), second_output())
    assert first.to_wire() == second.to_wire()
    assert first.reuse_summary.reused_match_count >= 0
~~~

### Step 2: Run focused tests and record the expected failure

~~~powershell
python -m pytest tests/test_analysis_report.py -q
~~~

Expected: collection fails because report generation is not implemented.

### Step 3: Implement rebuildable reports

Generate canonical JSON reports from validated records and trace only. Include:

* cards by M3 outcome;
* cards with zero retained Requirements;
* Requirements by M2 review status, resolution state/reason, derivation,
  family, and kind;
* producer contribution, no-match, conflict, and unresolved counts;
* recurring pattern counts and single-card/outlier patterns;
* multi-face/face-source distributions; and
* integer pattern reuse counts using
  reused_match_count = sum(max(match_count - 1, 0) per pattern).

Sort all maps/lists by stable keys and use no floating-point identity value.
Reports remain derived views; no report counter is added to a card record.

### Step 4: Implement one-way report packaging

Write the finalized analysis-manifest.json first. Then write report files and
report-index.json containing:

~~~text
report_index_schema
analysis_manifest_sha256
report descriptors: relative_path, sha256, byte_length
~~~

The report index is never referenced by the analysis manifest. If a future
delivery package needs an aggregate digest, it is a separate package-layer
artifact outside this module.

### Step 5: Add schema and focused checks

~~~powershell
python -m pytest tests/test_analysis_report.py tests/test_analysis_manifest.py -q
ruff format --check src/manafold_census/analysis tests/test_analysis_report.py
ruff check src/manafold_census/analysis tests/test_analysis_report.py
mypy src/manafold_census/analysis
~~~

### Step 6: Commit the task

~~~powershell
git add src/manafold_census/analysis/report.py schemas/analysis-report.v1.schema.json tests/test_analysis_report.py
git diff --cached --check
git commit -m 'feat: add deterministic M3 reports'
~~~

## Task 8: Reproduction, maintainability, and schema/resource integration

**Scope:** Add bounded end-to-end fixture reproduction, packaged schema checks,
M3 maintainability guards, and explicit forbidden-scope tests. Do not call the
pinned source, do not add CLI/CI commands, and do not generate 38,740 records.

**Files:**

* Create tests/test_analysis_reproduction.py.
* Modify tests/test_resources.py.
* Modify tests/test_maintainability.py.
* Modify src/manafold_census/analysis/__init__.py only for public exports.

### Step 1: Write failing integration tests

Add:

~~~python
def test_two_clean_fixture_builds_have_identical_analysis_bytes(tmp_path) -> None:
    first = build_fixture_m3(tmp_path / "first")
    second = build_fixture_m3(tmp_path / "second")
    assert relative_bytes(first) == relative_bytes(second)
    assert directory_digest(first) == directory_digest(second)


def test_m3_public_exports_do_not_import_cli_or_engine() -> None:
    assert public_analysis_exports() == expected_public_exports()


def test_analysis_modules_stay_below_500_lines() -> None:
    for module in analysis_modules():
        assert (
            len(module.read_text(encoding="utf-8").splitlines())
            <= MAX_PRODUCTION_MODULE_LINES
        )


def test_m3_scope_guard_rejects_later_milestone_names() -> None:
    # Parse analysis source files and reject capability/engine vocabulary,
    # source acquisition, dynamic execution, and hard-coded 38,740 logic.
~~~

### Step 2: Run focused tests and record the expected failure

~~~powershell
python -m pytest tests/test_analysis_reproduction.py tests/test_resources.py tests/test_maintainability.py -q
~~~

Expected: the new M3 test names fail because fixture build/export/guard support
does not exist.

### Step 3: Implement fixture reproduction and guards

Use only the bounded fixtures/analysis corpus. Run the reference build twice
into separate temporary directories, compare every relative path byte-for-byte,
and compare the canonical directory digest. Do not add source acquisition or
full-corpus enumeration to the fixture helper.

Extend maintainability checks for the new analysis package and reject imports or
declarations that introduce:

~~~text
Capability / capability_id
engine_support
live download/fetch/open-url paths
card-specific executors
38,740 hard-coded extraction loops
eval / pickle / artifact-supplied dynamic imports
~~~

Extend resource tests for every new schema and fixture file that must be present
in a fresh wheel. Keep existing M0/M1/M2 packaging assertions unchanged.

### Step 4: Run focused checks and commit

~~~powershell
python -m pytest tests/test_analysis_reproduction.py tests/test_resources.py tests/test_maintainability.py -q
ruff format --check src/manafold_census/analysis tests/test_analysis_reproduction.py tests/test_resources.py tests/test_maintainability.py
ruff check src/manafold_census/analysis tests/test_analysis_reproduction.py tests/test_resources.py tests/test_maintainability.py
mypy src/manafold_census
git add src/manafold_census/analysis/__init__.py tests/test_analysis_reproduction.py tests/test_resources.py tests/test_maintainability.py
git diff --cached --check
git commit -m 'test: close M3 fixture reproduction and scope gates'
~~~

## Task 9: Maintainer commands and bounded synthetic CI gate

**Scope:** Expose the already-implemented fixture path through explicit M3
commands and add only bounded synthetic M3 verification to CI. Do not make the
full pinned corpus part of normal PR feedback.

**Files:**

* Modify src/manafold_census/cli.py.
* Modify justfile.
* Modify .github/workflows/ci.yml.
* Create tests/test_analysis_cli.py.

### Step 1: Write failing command tests

Add tests that invoke the command module with a temporary output path and assert:

~~~text
m3-build --synthetic -> exit 0 and writes five-card fixture artifact
m3-check --synthetic -> exit 0 and prints closure PASS
m3-report --synthetic -> exit 0 and writes report-index.json
~~~

Add negative command tests for an output containing a missing card and a report
index that points at a different analysis manifest. Both must exit nonzero and
print a stable diagnostic.

### Step 2: Run focused tests and record the expected failure

~~~powershell
python -m pytest tests/test_analysis_cli.py -q
~~~

Expected: the command parser rejects the new command names before the change.

### Step 3: Add commands without hidden acquisition

Implement commands that accept an explicit synthetic fixture mode and explicit
input/output paths. The default PR/synthetic path must not call source
discovery, source download, the Scryfall cache, an engine, or a model API.

Add these Justfile recipes:

~~~text
m3-build:
    python -m manafold_census.cli m3-build --synthetic

m3-check:
    python -m manafold_census.cli m3-check --synthetic

m3-report:
    python -m manafold_census.cli m3-report --synthetic
~~~

Keep them out of the existing check target until their command-level runtime is
measured and the normal-gate budget is satisfied. If they are added to check,
the existing CI command must remain bounded by the 600-second gate budget.

Add CI steps after the existing offline structural checks for the synthetic M3
build/check/report path only. Do not add a full-corpus download or extraction
step to CI.

### Step 4: Run focused checks and commit

~~~powershell
python -m pytest tests/test_analysis_cli.py -q
ruff format --check src/manafold_census/cli.py tests/test_analysis_cli.py
ruff check src/manafold_census/cli.py tests/test_analysis_cli.py
mypy src/manafold_census
git add src/manafold_census/cli.py justfile .github/workflows/ci.yml tests/test_analysis_cli.py
git diff --cached --check
git commit -m 'feat: add bounded M3 maintainer commands'
~~~

## Task 10: Reference-path final regression and independent review package

**Scope:** Verify the complete synthetic implementation against every frozen M3
invariant, package the exact design/implementation evidence, and stop before
the pinned 38,740-card run. This task does not change production behavior.

**Files:**

* Create tests/test_analysis_conformance.py.
* Modify tests/test_maintainability.py only if a missing cross-module guard is
  discovered and the change is limited to M3 scope.
* Create docs/reports/2026-09-13-m3-reference-conformance.md only after all
  gates below pass and only for synthetic evidence.

### Step 1: Write conformance tests

Cover the frozen matrix:

~~~text
one M1 record -> exactly one CardAnalysisRecordV1
zero bundle with no authority -> UNRESOLVED_ANALYSIS
zero bundle with valid negative authority -> NO_REQUIREMENTS_APPLICABLE
pattern match -> PROPOSED only
terminal producer review -> execution failure
same ID/same resolution -> merge evidence/provenance
same ID/different resolution -> omit disputed identity and mark unresolved
different IDs -> retain both without implicit conflict
explicit conflict -> retain only explicitly supplied relation
report -> downstream from finalized manifest
partition counts 1, 2, 8, and 16 -> byte-equivalent canonical output
parallel backend -> NOT_IMPLEMENTED
missing/duplicate/extra source key -> closure failure
~~~

The parity test feeds the same validated records through the in-process
partition/merge/package seam for partition counts 1, 2, 8, and 16. It does not
spawn workers or claim parallel execution. The conformance report records:

~~~text
PARTITION_MERGE_PARITY = PASS
PARALLEL_BACKEND       = NOT_IMPLEMENTED
~~~

### Step 2: Run the complete reference gate

Run each command as a separately timed subprocess with the 600-second limit:

~~~powershell
python -m pytest -q
ruff format --check .
ruff check .
mypy src/manafold_census
python -m manafold_census.cli reproduce
python -m manafold_census.cli corpus-check --synthetic
python -m manafold_census.cli structural-check --synthetic
python -m manafold_census.cli m3-check --synthetic
~~~

Also run the fresh-wheel smoke path from .github/workflows/ci.yml locally if the
environment supports it. Report every command separately; a timed-out or unrun
command is not a pass.

### Step 3: Verify scope and commit the reference evidence

Confirm:

~~~text
M1_FILES_CHANGED = 0
M2_FILES_CHANGED = 0
M4_FILES_CHANGED = 0
GLOBAL_EXTRACTION_STARTED = NO
~~~

Commit only the synthetic conformance test and evidence report:

~~~powershell
git add tests/test_analysis_conformance.py docs/reports/2026-09-13-m3-reference-conformance.md
git diff --cached --check
git commit -m 'test: verify M3 reference conformance'
~~~

Stop after the reference conformance checkpoint. This task does not authorize
the pinned corpus run, capability ontology, PR, or merge.

## Task 11: Pinned corpus closure evidence (separately authorized)

This is a post-implementation evidence task, not part of normal development or
PR verification. It requires a new explicit authorization after Tasks 1–10,
fresh verification of the pinned M1 artifacts, and confirmation that the
600-second normal-gate boundary does not apply to the explicitly separated
corpus workload.

**Files:**

* Create docs/reports/2026-09-13-m3-global-corpus-closure.md only after the
  evidence run succeeds.
* Do not commit generated records, raw source bytes, caches, or temporary
  diagnostics.

The task must:

1. verify origin/main/branch authority and the exact M1 structural manifest;
2. classify the workload as a long-running offline corpus campaign;
3. use explicit progress, a deterministic input, a campaign budget, and a
   killable process;
4. build from the pinned M1 artifact, not from a live source refresh;
5. prove exact input/output identity-set equality;
6. prove no duplicate, missing, or extra records;
7. compare a rerun or canonical digest according to the frozen reproducibility
   design; and
8. report local, hosted, semantic, and review statuses separately.

An interrupted or timed-out campaign is TIMEOUT/NOT_RUN, never PASS. The campaign
must not be added to ordinary PR CI.

## Implementation task file/dependency map

| Task | Primary module seam | Depends on | Normal output |
| --- | --- | --- | --- |
| 1 | card-analysis model | frozen M1/M2 models | record wire/model/schema |
| 2 | producer interface/registry | Task 1 source key and M2 validation | proposal-only registry |
| 3 | pattern registry/trace | Task 2 producer identity | effective registry and trace |
| 4 | reconciliation | Tasks 1–3 proposal values | canonical retained candidates |
| 5 | manifest/closure | Task 1 record and Task 3 trace | shards and report-independent manifest |
| 6 | reference build | Tasks 1–5 | synthetic authoritative artifact |
| 7 | reports | Tasks 5–6 | downstream reports/report-index |
| 8 | reproduction/guards | Tasks 1–7 | bounded fixture conformance |
| 9 | CLI/Justfile/CI | Tasks 6–8 | maintainer synthetic commands |
| 10 | final conformance | Tasks 1–9 | independent review package |
| 11 | pinned evidence | Tasks 1–10 plus new authorization | global closure report |

No task may bypass its dependency to start corpus-scale extraction.

## Spec coverage map

| Frozen design area | Implementing task(s) |
| --- | --- |
| M3 record boundary and natural source key | 1, 5 |
| Three persisted outcomes and failure separation | 1, 6 |
| Negative authority artifact/model/schema/digests | 1, 6, 10 |
| Zero-result negative-authority boundary | 1, 6, 10 |
| Candidate producer interface/provenance | 2 |
| Deterministic producer admission | 2, 6, 10 |
| Exact-only pattern grammar and eligibility binding | 3, 5, 6 |
| Exact text/source-local trace | 3, 8 |
| Producer-neutral reconciliation | 4, 10 |
| Divergent same-ID resolution rule | 4, 10 |
| Explicit relationship/conflict handling | 4 |
| M1 multi-face source binding | 1, 6, 10 |
| 16-way M1-compatible sharding | 5 |
| Identity-set closure | 5, 6, 10, 11 |
| Manifest/report one-way identity | 5, 7, 10 |
| Atomicity and execution failures | 6 |
| Single-process reference path | 6 |
| In-process partition/merge parity seam | 5, 10 |
| Optional pinned model proposal import | 2, 6 |
| Human review and future authority boundary | 1, 2, 6, 10 |
| Derived reports and review summaries | 7 |
| Schema evolution and resource packaging | 1, 2, 3, 5, 7, 8 |
| Maintainer commands and synthetic PR gate | 9 |
| Maintainability/security/scope guards | 2, 3, 8, 9 |
| Full pinned corpus evidence | 11, separately authorized |

## Plan self-review

### Spec coverage

Every normative M3 design section has an implementing task or an explicit
separate-authorization gate in the coverage map. The report identity direction,
negative authority restriction, divergent-resolution omission, deterministic
producer admission, M1 shard function, and no-38,740-card PR boundary each have
dedicated tests or validation steps.

### Placeholder scan

The plan contains no incomplete or unspecified implementation task. Any future
authority or corpus action is represented as a named, separately authorized
task with an exact safe default and explicit stop condition.

### Type and name consistency

The names used across tasks are fixed:

~~~text
AnalysisOutcomeV1
NegativeReviewAuthorityRefV1
NegativeAuthorityScopeV1
NegativeRequirementAuthorityRecordV1
CardAnalysisRecordV1
ProducerDescriptorV1
ProducerResultV1
ProducerRegistryV1
MatcherKindV1
NormalizationProfileV1
PatternSourceFieldV1
EvidencePolicyV1
PatternSourceScopeV1
PatternOutputTemplateV1
PatternRuleV1
PatternEligibilityV1
EffectivePatternRegistryV1
RequirementTraceEventV1
AnalysisManifestV1
~~~

The source key is always card_source_key(source). Reports consume a finalized
analysis_manifest_sha256; the analysis manifest never consumes report bytes.

### Scope review

The plan creates no M4 capability vocabulary, no engine integration, no Rust
files, no source acquisition, no ordinary PR corpus job, and no automatic
terminal review promotion. It keeps the full corpus run as Task 11 behind a
new explicit authorization.

## Plan state

~~~text
M3_DESIGN_FROZEN                  = YES
M3_IMPLEMENTATION_PLAN_WRITTEN   = YES
M3_IMPLEMENTATION_PLAN_PATH      = docs/superpowers/plans/2026-09-13-global-requirement-candidate-extraction.md
PER_TEST_TIMEOUT_ENFORCEMENT     = BLOCKED
LOCAL_COMMAND_TIMEOUT_ENFORCEMENT = EXTERNAL_EXECUTION_ENVIRONMENT
HOSTED_PER_STEP_600S_ENFORCEMENT = NOT_IMPLEMENTED
M3_IMPLEMENTATION_AUTHORIZED     = NO
GLOBAL_EXTRACTION_STARTED        = NO
M4_STARTED                       = NO
PR_AUTHORIZED                    = NO
MERGE_AUTHORIZED                 = NO
NEXT_TASK_AUTHORIZED             = NO
~~~
