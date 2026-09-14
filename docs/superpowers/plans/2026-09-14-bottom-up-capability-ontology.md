# M4 Bottom-Up Capability Ontology Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task after separate authorization. Steps use checkbox syntax for tracking.

**Goal:** Add the deterministic, engine-independent M4 Capability Ontology
machinery defined by the frozen M4 design, while keeping M2 Requirements
unchanged, preserving unresolved semantics, and preventing proposal artifacts
from becoming ontology authority.

**Architecture:** Add a focused manafold_census.capability package behind
small deep-module interfaces. It consumes a validated frozen M3 artifact,
projects typed M2 values through a code-owned dimension registry, and publishes
immutable Capability definitions, source-Requirement admissibility records,
review records, mapping links, mapping dispositions, evolution records,
manifests, and derived reports. The first reference path is single-process,
offline, canonical-JSON based, and synthetic-fixture driven. Real M3 corpus
mapping and Capability activation remain separately authorized data and review
actions.

**Tech Stack:** Python 3.12+, standard-library dataclasses, enum, json,
hashlib, pathlib, tempfile, the existing canonical_json_bytes, domain_digest,
sha256_bytes, M2 semantic models and identity helpers, M3 manifest/model/
closure validation, existing JSON Schema validation, pytest, Ruff, mypy,
setuptools resource packaging, the existing Justfile, and GitHub Actions. No
database, LLM runtime, new runtime dependency, engine dependency, or network
operation is introduced.

---

## Authorization, freeze, and preservation protocol

This document is a plan artifact only. Creating it does not authorize any
numbered implementation task.

~~~text
DESIGN_HEAD                       = 0f787e7807dad3f730b4013e6a768616000666c2
DESIGN_STATE                      = FROZEN_BY_INDEPENDENT_REVIEW
PLAN_ARTIFACT                     = docs/superpowers/plans/2026-09-14-bottom-up-capability-ontology.md
M4_IMPLEMENTATION_PLAN_AUTHORIZED = YES
M4_IMPLEMENTATION_PLAN_REVIEW     = NOT_RUN
M4_IMPLEMENTATION_PLAN            = NOT_FROZEN
M4_IMPLEMENTATION_AUTHORIZED      = NO
REAL_REQUIREMENT_MAPPING_STARTED  = NO
REAL_CAPABILITY_ACTIVATION        = NO
M5_STARTED                        = NO
PR_AUTHORIZED                     = NO
MERGE_AUTHORIZED                  = NO
~~~

The frozen design document at DESIGN_HEAD is immutable during plan execution.
The freeze is the independent-review decision recorded by the user; the plan
does not rewrite the design document's pre-freeze status text. Every future
implementation task must preserve:

~~~text
M1 structural records, source lock, and pinned source configuration
M2 Requirement identity, payloads, evidence, review, resolution, and schemas
M3 CardAnalysisRecordV1, producer/pattern registries, closure reports, and artifacts
M3 proposal-only producer behavior
M3 UNRESOLVED_ANALYSIS semantics
~~~

Before each separately authorized implementation task, run:

~~~powershell
git status --short --branch
git diff --name-only
git diff --cached --name-only
git diff -- source-locks config/sources
git diff -- src/manafold_census/semantic src/manafold_census/structural src/manafold_census/analysis
~~~

The expected result is a clean worktree before the task and only that task's
declared paths after its changes. The scope check must include new files:

~~~powershell
$tracked = @(git diff --name-only)
$staged = @(git diff --cached --name-only)
$untracked = @(git ls-files --others --exclude-standard)
$all = @($tracked) + @($staged) + @($untracked) | Sort-Object -Unique
$forbidden = $all | Where-Object {
    $_ -match '^(source-locks|config/sources|src/manafold_census/(semantic|structural|analysis))'
}
if ($forbidden) {
    $forbidden
    throw 'M1, M2, or M3 authority changed'
}
~~~

The implementation branch is separate from this design/plan branch:

~~~text
IMPLEMENTATION_BRANCH = feat/m4-bottom-up-capability-ontology
IMPLEMENTATION_BASE   = final approved plan HEAD
~~~

Create IMPLEMENTATION_BRANCH from the final approved plan commit only after
the plan review passes and M4 implementation authorization is granted. Do not
place production M4 code on design/m4-bottom-up-capability-ontology-20260914.

### Per-task delivery checkpoint

Every separately authorized task ends at this checkpoint before the next task
is considered:

~~~text
implement declared slice
-> run focused RED/GREEN checks and the complete local gates
-> inspect tracked, staged, and untracked scope
-> stage only the task's declared paths
-> git diff --cached --check
-> create the task's standalone commit
-> push feat/m4-bottom-up-capability-ontology
-> verify REMOTE_HEAD == LOCAL_HEAD
-> verify WORKTREE = CLEAN
-> stop for independent review
~~~

The next task cannot consume an unpushed or unreviewed task commit. A push is
not a PR, and a PR is not merge authorization.

Every implementation task requires explicit authorization for its exact task
number. A task may use synthetic M3 artifacts only. It must not enumerate,
download, or map the real 38,740-card artifact. A task that needs real
Requirement review or activation stops at the explicit data/review gate.

The required repository gates are run separately after every implementation
slice:

~~~powershell
python -m pytest -q
ruff format --check .
ruff check .
mypy src/manafold_census
~~~

Expected local evidence is an exit code of zero, zero test failures, no
formatting changes, no Ruff findings, and no mypy findings. The known runtime
labels remain:

~~~text
PER_TEST_TIMEOUT_ENFORCEMENT      = BLOCKED
LOCAL_COMMAND_TIMEOUT_ENFORCEMENT = EXTERNAL_EXECUTION_ENVIRONMENT
HOSTED_PER_STEP_600S_ENFORCEMENT  = NOT_IMPLEMENTED
~~~

## Frozen design decisions that the plan must implement

The plan implements these closed decisions from the frozen design:

~~~text
Requirement != Capability
Capability != Engine Implementation
Generated Cluster != Reviewed Capability
M4 admissibility != M2 ACCEPTED
Unresolved != Missing
Reproducible != Semantically Correct
~~~

The M4 input is the exact SHA-256 of a canonical M3
analysis-manifest.json. M4 reads only actual RequirementV1 values inside M3
bundles. An M3 UNRESOLVED_ANALYSIS record with bundle = null contributes no
Requirement and never becomes negative authority.

CapabilityFamilyKeyV1 contains only a stable semantic nucleus:

~~~text
nucleus_kind
operation_anchor: sorted exact M2 family/kind anchors
nucleus_contract_version

ATOMIC
    -> exactly one operation anchor
COMPOSITE
    -> at least two sorted operation anchors
~~~

It does not contain dimension path keys, dimensions, requiredness, domains,
unknown policy, exclusions, M2 interpretation version, filesystem paths,
reviewers, source cards, patterns, producers, timestamps, or engine names.
Those versionable values belong to CapabilityClaimV1.

~~~text
same family nucleus + changed semantic claim
    -> same capability_family_id
    -> capability_version increments
    -> claim_digest changes

changed family nucleus
    -> new capability_family_id
    -> explicit evolution relation when applicable
~~~

Review identity is non-cyclic:

~~~text
review_claim_payload
    excludes record_id, review_digest, future manifest digest,
    filesystem path, timestamp, and runtime order

review_digest = domain_digest(
    "census.capability-review-record.v1",
    review_claim_payload
)

record_id = "mrv_" + review_digest
~~~

The same projection rule applies to the
SOURCE_REQUIREMENT_ADMISSIBILITY record, whose ID uses the sra_ prefix.

An active Requirement-to-Capability link uses exactly one admissibility route:

~~~text
M2 review = ACCEPTED
M2 resolution = COMPLETE
valid reviewed_claim_digest_for(requirement)
    -> basis = M2_TERMINAL_ACCEPTANCE

M2 review = PROPOSED or IN_REVIEW
M2 resolution = COMPLETE
accepted exact SOURCE_REQUIREMENT_ADMISSIBILITY record
    -> basis = SOURCE_REQUIREMENT_ADMISSIBILITY
~~~

M2 REJECTED, PARTIAL, and UNRESOLVED Requirements cannot support an active
link. The M4 admissibility record does not mutate RequirementV1.

## File map and ownership

The following paths are planned future implementation paths. None is created
by this planning task.

### Production package

| File | Single responsibility |
| --- | --- |
| src/manafold_census/capability/__init__.py | Small public exports; no CLI, network, engine, or source enumeration |
| src/manafold_census/capability/model.py | Capability family keys, references, claims, definitions, and lifecycle values |
| src/manafold_census/capability/identity.py | Family IDs, claim digests, link digests, review digests, and Requirement-set digest |
| src/manafold_census/capability/dimensions.py | Code-owned M2 path registry, typed domains, and parameter bindings |
| src/manafold_census/capability/review.py | M4 review authority and SOURCE_REQUIREMENT_ADMISSIBILITY validation |
| src/manafold_census/capability/link.py | Exact Requirement-to-Capability links and one-row mapping dispositions |
| src/manafold_census/capability/evolution.py | Composition, dependency, specialization, and append-only evolution records |
| src/manafold_census/capability/input.py | Frozen M3 manifest loading and actual Requirement extraction |
| src/manafold_census/capability/manifest.py | M4 file descriptors, shard identity, and ontology manifest |
| src/manafold_census/capability/validate.py | Independent wire, stale-link, closure, graph, and publication validation |
| src/manafold_census/capability/build.py | Single-process staging, reread, and atomic publication |
| src/manafold_census/capability/candidates.py | Deterministic grouping proposals and ranked review worklists |
| src/manafold_census/capability/report.py | Derived reports only; never an authority input |

Every production module remains at or below the existing 500-line budget.
identity.py, dimensions.py, link.py, and validate.py are deep module seams:
callers provide typed values and frozen inputs, while canonicalization,
binding, and failure rules remain behind small interfaces.

### Normative schemas and synthetic fixtures

The implementation phase creates these schemas:

~~~text
schemas/capability-claim.v1.schema.json
schemas/capability-definition.v1.schema.json
schemas/capability-review.v1.schema.json
schemas/source-requirement-admissibility.v1.schema.json
schemas/requirement-capability-link.v1.schema.json
schemas/requirement-mapping-decision.v1.schema.json
schemas/capability-evolution.v1.schema.json
schemas/capability-ontology-manifest.v1.schema.json
schemas/capability-candidate-cluster.v1.schema.json
schemas/capability-report.v1.schema.json
~~~

Synthetic-only fixture files use:

~~~text
fixtures/capability/requirements.json
fixtures/capability/claims.json
fixtures/capability/reviews.json
fixtures/capability/evolution.json
~~~

These fixtures test wire and authority behavior. They are never real M3
ontology data and never justify a global Magic claim.

### Tests and integration files

The implementation phase adds focused tests:

~~~text
tests/capability_fixtures.py
tests/test_capability_model.py
tests/test_capability_identity.py
tests/test_capability_dimensions.py
tests/test_capability_review.py
tests/test_capability_admissibility.py
tests/test_capability_link.py
tests/test_capability_evolution.py
tests/test_capability_input.py
tests/test_capability_manifest.py
tests/test_capability_validate.py
tests/test_capability_build.py
tests/test_capability_candidates.py
tests/test_capability_report.py
tests/test_capability_reproduction.py
tests/test_capability_conformance.py
~~~

Only the integration slice may modify:

~~~text
tests/test_resources.py
tests/test_maintainability.py
src/manafold_census/cli.py
justfile
pyproject.toml
.github/workflows/ci.yml
~~~

M4 does not modify any M1, M2, or M3 source, schema, registry, closure report,
or pinned source file.

### Shared synthetic fixture interface

tests/capability_fixtures.py owns the synthetic-only factories used by later
tasks. It may import existing M2 models and the M4 public values created by
earlier tasks, but it never reads real generated M3 output. The shared factory
names and meanings are fixed:

~~~text
draw_family_key
proposed_draw_definition
accepted_capability_review
definition_with_lifecycle
proposed_complete_requirement
accepted_complete_requirement
requirement_with_status_and_resolution
proposed_draw_requirement
proposed_damage_requirement
record_with_proposed_requirement
record_with_requirement
record_with_other_requirement
unresolved_record_without_bundle
no_requirements_applicable_record
accepted_admissibility_record
active_draw_capability
another_active_capability
composite_capability
active_narrow_capability
active_other_narrow_capability
direct_link
proposed_direct_link
activate
mapping_decision
corpus_for_requirements
validate_mapping_candidates
validate_active_links
composes_edge
requires_edge
split_event
links_for_two_distinct_m1_sources
links_for_one_m1_source
build_synthetic_m4
build_synthetic_m4_with_stale_link
build_capability_reports
report_for_synthetic_sparse_m3
~~~

Each factory returns a complete typed value with deterministic fixture IDs,
source references, evidence, and digests. The fixture module includes the
relative-bytes helper used by build/reproduction tests. The separate
tests/capability_m3_fixtures.py module exposes write_synthetic_m3 and returns
one FrozenM3InputV1 descriptor with the temporary M1 root, M3 root, source-lock
path, and actual canonical manifest SHA. A factory name in a test always refers
to one of these fixed meanings; it is not an implicit production API.

## Task 1: Stable Capability nucleus and reference identity

**Files:**

- Create: src/manafold_census/capability/__init__.py
- Create: src/manafold_census/capability/model.py
- Create: src/manafold_census/capability/identity.py
- Create: tests/capability_fixtures.py
- Create: tests/test_capability_model.py
- Create: tests/test_capability_identity.py

**Dependency:** Frozen M4 design only. No M3 input loader is used in this
task.

**Authorization:** This task requires separate implementation authorization.
The plan does not provide it.

### Step 1: Write the failing family-key tests

Add this test contract:

~~~python
import pytest

from manafold_census.capability.identity import capability_family_id_for
from manafold_census.capability.model import (
    CapabilityFamilyKeyV1,
    NucleusKindV1,
)
from manafold_census.semantic.kinds import (
    RequirementFamilyV1,
    RequirementKindV1,
)


def draw_family_key() -> CapabilityFamilyKeyV1:
    return CapabilityFamilyKeyV1(
        nucleus_contract_version="1",
        nucleus_kind=NucleusKindV1.ATOMIC,
        operation_anchor=(
            (
                RequirementFamilyV1.EFFECT,
                RequirementKindV1.DRAW_CARDS,
            ),
        ),
    )


def test_family_id_is_derived_only_from_the_stable_nucleus() -> None:
    first = draw_family_key()
    second = CapabilityFamilyKeyV1(
        nucleus_contract_version="1",
        nucleus_kind=NucleusKindV1.ATOMIC,
        operation_anchor=(
            (
                RequirementFamilyV1.EFFECT,
                RequirementKindV1.DRAW_CARDS,
            ),
        ),
    )

    assert capability_family_id_for(first) == capability_family_id_for(second)
    assert capability_family_id_for(first).startswith("capfam_")


def test_operation_anchor_order_is_canonical() -> None:
    first = CapabilityFamilyKeyV1(
        nucleus_contract_version="1",
        nucleus_kind=NucleusKindV1.COMPOSITE,
        operation_anchor=(
            (RequirementFamilyV1.EFFECT, RequirementKindV1.DRAW_CARDS),
            (RequirementFamilyV1.EFFECT, RequirementKindV1.DEAL_DAMAGE),
        ),
    )
    second = CapabilityFamilyKeyV1(
        nucleus_contract_version="1",
        nucleus_kind=NucleusKindV1.COMPOSITE,
        operation_anchor=(
            (RequirementFamilyV1.EFFECT, RequirementKindV1.DEAL_DAMAGE),
            (RequirementFamilyV1.EFFECT, RequirementKindV1.DRAW_CARDS),
        ),
    )

    assert capability_family_id_for(first) == capability_family_id_for(second)


def test_atomic_requires_exactly_one_operation_anchor() -> None:
    with pytest.raises(ValueError, match="exactly one operation anchor"):
        CapabilityFamilyKeyV1(
            nucleus_contract_version="1",
            nucleus_kind=NucleusKindV1.ATOMIC,
            operation_anchor=(
                (RequirementFamilyV1.EFFECT, RequirementKindV1.DRAW_CARDS),
                (RequirementFamilyV1.EFFECT, RequirementKindV1.DEAL_DAMAGE),
            ),
        )


def test_composite_requires_multiple_operation_anchors() -> None:
    with pytest.raises(ValueError, match="at least two operation anchors"):
        CapabilityFamilyKeyV1(
            nucleus_contract_version="1",
            nucleus_kind=NucleusKindV1.COMPOSITE,
            operation_anchor=(
                (RequirementFamilyV1.EFFECT, RequirementKindV1.DRAW_CARDS),
            ),
        )


def test_duplicate_operation_anchor_is_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate operation anchor"):
        CapabilityFamilyKeyV1(
            nucleus_contract_version="1",
            nucleus_kind=NucleusKindV1.COMPOSITE,
            operation_anchor=(
                (RequirementFamilyV1.EFFECT, RequirementKindV1.DRAW_CARDS),
                (RequirementFamilyV1.EFFECT, RequirementKindV1.DRAW_CARDS),
            ),
        )


def test_changed_nucleus_contract_version_changes_family_id() -> None:
    first = draw_family_key()
    second = CapabilityFamilyKeyV1(
        nucleus_contract_version="2",
        nucleus_kind=first.nucleus_kind,
        operation_anchor=first.operation_anchor,
    )

    assert capability_family_id_for(first) != capability_family_id_for(second)
~~~

Run:

~~~powershell
python -m pytest tests/test_capability_model.py tests/test_capability_identity.py -q
~~~

Expected: collection fails because the capability package and identity
functions do not exist.

### Step 2: Implement the stable nucleus model

Implement the following closed values in model.py:

~~~python
class NucleusKindV1(StrEnum):
    ATOMIC = "ATOMIC"
    COMPOSITE = "COMPOSITE"


@dataclass(frozen=True, slots=True)
class CapabilityFamilyKeyV1:
    nucleus_contract_version: str
    nucleus_kind: NucleusKindV1
    operation_anchor: tuple[tuple[RequirementFamilyV1, RequirementKindV1], ...]

    SCHEMA: ClassVar[str] = "census.capability-family-key.v1"
~~~

The constructor must:

* accept only NucleusKindV1;
* require a non-empty operation anchor;
* sort anchor pairs into canonical family/kind wire order without normalizing
  duplicates;
* require exactly one anchor for ATOMIC and at least two anchors for COMPOSITE;
* reject duplicate anchors fail-closed;
* validate every pair with the existing validate_kind_family;
* accept only a stable non-empty version identifier; and
* reject unknown fields when reading wire data.

The wire projection contains exactly:

~~~text
family_key_schema
nucleus_contract_version
nucleus_kind
operation_anchor
~~~

It contains no dimension, path, registry, source, review, or implementation
field.

### Step 3: Implement family identity and exact Capability references

Add this identity projection:

~~~python
FAMILY_ID_DOMAIN = "census.capability-family-id.v1"
FAMILY_ID_PREFIX = "capfam_"


def capability_family_id_for(key: CapabilityFamilyKeyV1) -> str:
    return FAMILY_ID_PREFIX + domain_digest(
        FAMILY_ID_DOMAIN,
        key.to_wire(),
    )
~~~

Define:

~~~python
@dataclass(frozen=True, slots=True)
class CapabilityRefV1:
    capability_family_id: str
    capability_version: int
    claim_digest: str
~~~

Validate family IDs as capfam_ plus 64 lowercase hexadecimal characters,
versions as integers greater than or equal to one, and claim digests as 64
lowercase hexadecimal characters.

### Step 4: Add negative identity tests

Test that the model rejects:

~~~text
empty operation anchor
family/kind mismatch
duplicate anchor
unsorted direct wire construction
unknown field
dimension path in the family-key wire
noncanonical family-key array
invalid family ID prefix
zero or negative Capability version
non-hexadecimal claim digest
~~~

Run:

~~~powershell
python -m pytest tests/test_capability_model.py tests/test_capability_identity.py -q
ruff format --check src/manafold_census/capability tests/test_capability_model.py tests/test_capability_identity.py
ruff check src/manafold_census/capability tests/test_capability_model.py tests/test_capability_identity.py
mypy src/manafold_census/capability
~~~

Expected after implementation: all focused tests PASS, Ruff reports no
findings, and mypy reports no findings.

### Step 5: Commit only the nucleus slice

~~~powershell
git add src/manafold_census/capability tests/capability_fixtures.py tests/test_capability_model.py tests/test_capability_identity.py
git diff --cached --check
git commit -m "feat: add M4 capability nucleus identity"
~~~

After separate authorization, apply the per-task delivery checkpoint above:
push the Task 1 commit to feat/m4-bottom-up-capability-ontology, verify the
remote SHA and clean worktree, and stop for independent review before Task 2.

## Task 2: Typed M2 dimension paths, domains, and bindings

**Files:**

- Create: src/manafold_census/capability/dimensions.py
- Modify: src/manafold_census/capability/model.py
- Modify: src/manafold_census/capability/identity.py
- Create: schemas/capability-claim.v1.schema.json
- Create: tests/test_capability_dimensions.py
- Modify: tests/test_capability_model.py
- Modify: tests/test_capability_identity.py

**Dependency:** Task 1.

**Authorization:** Separate implementation authorization is required.

### Step 1: Write the failing dimension tests

Add exact draw-card parameter cases:

~~~python
def test_draw_quantity_is_a_dimension_not_a_family_identity() -> None:
    quantity = CapabilityDimensionV1(
        path_key=M2DimensionPathV1.DRAW_CARDS_QUANTITY,
        dimension_kind=DimensionKindV1.QUANTITY,
        required=True,
        domain_kind=DimensionDomainKindV1.ANY_TYPED_VALUE,
    )

    assert quantity.path_key is M2DimensionPathV1.DRAW_CARDS_QUANTITY
    assert quantity.dimension_kind is DimensionKindV1.QUANTITY
    assert quantity.required is True


def test_unknown_dimension_path_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown M2 dimension path"):
        M2DimensionPathV1.from_wire("DRAW_CARDS_FREE_FORM")


def test_parameter_binding_preserves_unknown_values() -> None:
    binding = ParameterBindingV1.unknown(
        M2DimensionPathV1.DRAW_CARDS_QUANTITY,
        "UNKNOWN_SEMANTICS",
        "/parameters/quantity",
    )

    assert binding.state is BindingStateV1.UNKNOWN
    assert binding.m2_unknown_path == "/parameters/quantity"
    assert binding.value is None
~~~

Run:

~~~powershell
python -m pytest tests/test_capability_dimensions.py -q
~~~

Expected: collection fails because the typed path and binding values do not
exist.

### Step 2: Define the closed dimension vocabulary

Implement these values in dimensions.py:

~~~python
class DimensionKindV1(StrEnum):
    ENTITY_REF = "ENTITY_REF"
    QUANTITY = "QUANTITY"
    ZONE_REF = "ZONE_REF"
    CHARACTERISTIC_REF = "CHARACTERISTIC_REF"
    PARAMETER_VALUE = "PARAMETER_VALUE"
    SEMANTIC_DESCRIPTOR = "SEMANTIC_DESCRIPTOR"
    DURATION = "DURATION"
    M2_ENUM = "M2_ENUM"
    BOOLEAN = "BOOLEAN"
    RELATIONSHIP_ORDINAL = "RELATIONSHIP_ORDINAL"


class DimensionDomainKindV1(StrEnum):
    ANY_TYPED_VALUE = "ANY_TYPED_VALUE"
    M2_ENUM_SUBSET = "M2_ENUM_SUBSET"
    M2_SHAPE_SUBSET = "M2_SHAPE_SUBSET"


class BindingStateV1(StrEnum):
    KNOWN = "KNOWN"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class UnknownPolicyV1(StrEnum):
    EXPLICIT_BUT_NOT_ACTIVE = "EXPLICIT_BUT_NOT_ACTIVE"
~~~

The code-owned M2DimensionPathV1 enum contains these exact entries:

~~~text
DRAW_CARDS_DRAWER
DRAW_CARDS_QUANTITY
MOVE_BETWEEN_ZONES_SUBJECT
MOVE_BETWEEN_ZONES_FROM_ZONE
MOVE_BETWEEN_ZONES_TO_ZONE
MOVE_BETWEEN_ZONES_QUANTITY
MOVE_BETWEEN_ZONES_CAUSE
CREATE_OBJECT_OBJECT_CLASS
CREATE_OBJECT_QUANTITY
CREATE_OBJECT_DURATION
SELECT_CHOOSER
SELECT_SUBJECT_KIND
SELECT_QUANTITY
SELECT_RESTRICTION
SELECT_TARGETING
MODIFY_CHARACTERISTIC_SUBJECT
MODIFY_CHARACTERISTIC_CHARACTERISTIC
MODIFY_CHARACTERISTIC_OPERATION
MODIFY_CHARACTERISTIC_VALUE
APPLY_CONTINUOUS_EFFECT_SUBJECT
APPLY_CONTINUOUS_EFFECT_DURATION
APPLY_CONTINUOUS_EFFECT_EFFECT
SEARCH_ZONE_SEARCHER
SEARCH_ZONE_ZONE
SEARCH_ZONE_SELECTION
SEARCH_ZONE_DESTINATION
SEARCH_ZONE_REVEAL
DEAL_DAMAGE_SOURCE
DEAL_DAMAGE_RECIPIENT
DEAL_DAMAGE_AMOUNT
CREATE_DELAYED_EFFECT_DELAY
CREATE_DELAYED_EFFECT_EFFECT
TRIGGER_FROM_EVENT_EVENT
TRIGGER_FROM_EVENT_CONTROLLER
TRIGGER_FROM_EVENT_CONDITION
REPLACE_EVENT_EVENT
REPLACE_EVENT_REPLACEMENT
PAY_COST_PAYER
PAY_COST_COST
MODIFY_COST_SUBJECT
MODIFY_COST_COST
MODIFY_COST_OPERATION
CHOOSE_MODE_CHOOSER
CHOOSE_MODE_MINIMUM
CHOOSE_MODE_MAXIMUM
CONDITIONAL_EFFECT_CONDITION
CONDITIONAL_EFFECT_THEN_EFFECT
CONDITIONAL_EFFECT_ELSE_EFFECT
KEYWORD_REFERENCE_EXPANSION
~~~

Each enum member maps to one exact M2 family/kind, one exact parameter path,
one existing M2 value type, and its null/unknown policy. The mapping is
code-owned and tested. It is not read from artifact-provided strings.

M2 fields that are fixed compound collections, such as
create_object.characteristics and choose_mode.alternatives, are not traversed
by arbitrary child paths in M4 V1. They remain part of the exact operation
claim unless a later versioned registry entry gives them a specific typed path.
The implementation never substitutes a free-form recursive path.

### Step 3: Implement typed domains and bindings

Implement:

~~~python
@dataclass(frozen=True, slots=True)
class CapabilityDimensionV1:
    path_key: M2DimensionPathV1
    dimension_kind: DimensionKindV1
    required: bool
    domain_kind: DimensionDomainKindV1
    allowed_enum_values: tuple[str, ...]
    allowed_shapes: tuple[SemanticShapeV1, ...]
    unknown_policy: UnknownPolicyV1


@dataclass(frozen=True, slots=True)
class ExclusionV1:
    path_key: M2DimensionPathV1
    domain_kind: DimensionDomainKindV1
    excluded_enum_values: tuple[str, ...]
    excluded_shapes: tuple[SemanticShapeV1, ...]


@dataclass(frozen=True, slots=True)
class CompositionComponentV1:
    component_key: str
    capability: CapabilityRefV1
    required: bool
    ordinal: int


@dataclass(frozen=True, slots=True)
class CompositionClaimV1:
    components: tuple[CompositionComponentV1, ...]


@dataclass(frozen=True, slots=True)
class ParameterBindingV1:
    path_key: M2DimensionPathV1
    state: BindingStateV1
    value: JSONValue | None
    reason: str | None
    m2_unknown_path: str | None
~~~

Validation rules:

~~~text
path_key resolves to one registered M2 path
dimension_kind matches the registry
allowed enum/shape values belong to the registered M2 domain
ANY_TYPED_VALUE has empty allowed subsets
KNOWN has the exact typed M2 wire value
UNKNOWN has a closed M2 reason and exact unknown path
NOT_APPLICABLE is permitted only for a declared optional null branch
active links cannot contain UNKNOWN
~~~

value is a restricted JSON projection of an already validated M2 value. It is
never evaluated as code. The binding validator recomputes the value from the
Requirement rather than trusting a duplicated artifact value.

### Step 4: Add versioned claims

Extend model.py with:

~~~python
@dataclass(frozen=True, slots=True)
class CapabilityClaimV1:
    family_key: CapabilityFamilyKeyV1
    capability_version: int
    m2_requirement_schema: str
    m2_interpretation_version: str
    m4_dimension_registry_version: str
    dimensions: tuple[CapabilityDimensionV1, ...]
    exclusions: tuple[ExclusionV1, ...]
    composition: CompositionClaimV1 | None
~~~

The claim digest projection contains all fields above in canonical order. It
contains no display name, lifecycle, reviewer, Requirement IDs, M3 manifest,
pattern, producer, source locator, filesystem path, timestamp, or report
counter.

Add:

~~~python
CLAIM_DIGEST_DOMAIN = "census.capability-claim.v1"


def capability_claim_digest_for(claim: CapabilityClaimV1) -> str:
    return domain_digest(CLAIM_DIGEST_DOMAIN, claim.to_wire())
~~~

The claim includes dimension paths and registry versions. The family key does
not. A changed claim under an unchanged family key increments the Capability
version and changes the claim digest.

### Step 5: Test dimension evolution and negative boundaries

Test that:

~~~text
draw quantity 2 and draw quantity 3 use one family nucleus
changing a dimension path changes claim_digest but not family_id
changing requiredness changes claim_digest but not family_id
changing registry version changes claim_digest but not family_id
changing operation_anchor changes family_id
wrong M2 path/kind pair fails
free-form path text fails
arbitrary expression, regex, callback, and executable values fail
unknown values round-trip without being guessed
~~~

Run:

~~~powershell
python -m pytest tests/test_capability_dimensions.py tests/test_capability_model.py tests/test_capability_identity.py -q
ruff format --check src/manafold_census/capability tests/test_capability_dimensions.py tests/test_capability_model.py tests/test_capability_identity.py
ruff check src/manafold_census/capability tests/test_capability_dimensions.py tests/test_capability_model.py tests/test_capability_identity.py
mypy src/manafold_census/capability
~~~

Expected: focused tests and all static checks PASS.

### Step 6: Commit the dimension slice

~~~powershell
git add src/manafold_census/capability tests/test_capability_dimensions.py tests/test_capability_model.py tests/test_capability_identity.py schemas/capability-claim.v1.schema.json
git diff --cached --check
git commit -m "feat: add typed M4 capability dimensions"
~~~

## Task 3: Capability definitions, lifecycle, and review authority

**Files:**

- Modify: src/manafold_census/capability/model.py
- Modify: src/manafold_census/capability/identity.py
- Create: src/manafold_census/capability/review.py
- Create: schemas/capability-definition.v1.schema.json
- Create: schemas/capability-review.v1.schema.json
- Create: tests/test_capability_review.py
- Modify: tests/test_capability_model.py
- Modify: tests/test_capability_identity.py

**Dependency:** Tasks 1 and 2.

**Authorization:** Separate implementation authorization is required.

### Step 1: Add failing lifecycle tests

Add:

~~~python
def test_proposed_definition_cannot_be_active() -> None:
    definition = proposed_draw_definition()

    assert definition.lifecycle is CapabilityLifecycleStateV1.PROPOSED
    with pytest.raises(ValueError, match="active definition requires accepted review"):
        validate_active_definition(definition, reviews=())


def test_same_claim_can_change_display_name_without_claim_digest_change() -> None:
    first = proposed_draw_definition(display_name="Draw cards")
    second = proposed_draw_definition(display_name="Card draw")

    assert first.claim_digest == second.claim_digest
    assert first.capability_family_id == second.capability_family_id


def test_superseded_and_retired_definitions_cannot_receive_new_active_links() -> None:
    superseded = definition_with_lifecycle(CapabilityLifecycleStateV1.SUPERSEDED)
    retired = definition_with_lifecycle(CapabilityLifecycleStateV1.RETIRED)

    assert can_receive_active_link(superseded) is False
    assert can_receive_active_link(retired) is False


def test_definition_review_requires_a_closed_generalization_basis() -> None:
    review = accepted_capability_review(
        proposed_draw_definition(),
        generalization_basis=GeneralizationBasisV1.MULTI_SOURCE_REUSE,
    )

    assert review.generalization_basis is GeneralizationBasisV1.MULTI_SOURCE_REUSE
    with pytest.raises(ValueError, match="generalization_basis"):
        accepted_capability_review(
            proposed_draw_definition(),
            generalization_basis="CARD_SPECIFIC_EXCEPTION",
        )
~~~

Run:

~~~powershell
python -m pytest tests/test_capability_review.py tests/test_capability_model.py -q
~~~

Expected: collection fails because lifecycle and review modules are not
implemented.

### Step 2: Add the closed lifecycle and definition model

Implement:

~~~python
class CapabilityLifecycleStateV1(StrEnum):
    PROPOSED = "PROPOSED"
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    RETIRED = "RETIRED"
~~~

CapabilityDefinitionV1 has exactly these root fields:

~~~text
schema
capability_family_id
capability_version
claim_digest
claim
display_name
lifecycle
provenance
review_ref
~~~

The constructor recomputes capability_family_id from claim.family_key and
claim_digest from the exact claim. It rejects mismatches, unknown fields,
invalid display text, and lifecycle values outside the closed enum.

Lifecycle transitions are:

~~~text
PROPOSED --accepted review + explicit activation--> ACTIVE
ACTIVE --explicit evolution--> SUPERSEDED
ACTIVE --explicit retirement--> RETIRED
~~~

Rejected or unselected proposals remain proposal history and are not relabeled
SUPERSEDED. Historical definitions are never modified in place.

### Step 3: Implement the non-cyclic review record

Implement:

~~~python
class ReviewDecisionV1(StrEnum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class GeneralizationBasisV1(StrEnum):
    MULTI_SOURCE_REUSE = "MULTI_SOURCE_REUSE"
    SINGLE_OBSERVATION_GENERALIZATION = "SINGLE_OBSERVATION_GENERALIZATION"


@dataclass(frozen=True, slots=True)
class CapabilityReviewRecordV1:
    authority_id: str
    authority_version: str
    record_id: str
    subject: ReviewSubjectV1
    decision: ReviewDecisionV1
    reviewer_id: str
    generalization_basis: GeneralizationBasisV1 | None
    review_digest: str


REVIEW_RECORD_DOMAIN = "census.capability-review-record.v1"
REVIEW_RECORD_PREFIX = "mrv_"


def review_claim_payload(record: CapabilityReviewRecordV1) -> dict[str, JSONValue]:
    return {
        "review_schema": record.REVIEW_SCHEMA,
        "authority_id": record.authority_id,
        "authority_version": record.authority_version,
        "subject": record.subject.to_wire(),
        "decision": record.decision.value,
        "reviewer_id": record.reviewer_id,
        "generalization_basis": (
            None
            if record.generalization_basis is None
            else record.generalization_basis.value
        ),
    }


def review_digest_for(record: CapabilityReviewRecordV1) -> str:
    return domain_digest(REVIEW_RECORD_DOMAIN, review_claim_payload(record))


def review_record_id_for(record: CapabilityReviewRecordV1) -> str:
    return REVIEW_RECORD_PREFIX + review_digest_for(record)
~~~

ReviewSubjectV1 is a closed tagged union with one typed subject branch for
CAPABILITY_DEFINITION, CAPABILITY_LINK, MAPPING_DECISION, or EVOLUTION. Each
branch has fixed fields and a to_wire method; an arbitrary subject dictionary
is invalid.

The full wire carries record_id and review_digest, but review_claim_payload
excludes both. It also carries generalization_basis, which is null for
CAPABILITY_LINK, MAPPING_DECISION, and EVOLUTION subjects and is required for
an ACCEPTED CAPABILITY_DEFINITION review. The projection excludes future
manifest digests, filesystem paths, timestamps, and runtime order. The review
decision is exactly ACCEPTED or REJECTED; absence of a record means pending.

Review subjects are a closed tagged union:

~~~text
CAPABILITY_DEFINITION
CAPABILITY_LINK
MAPPING_DECISION
EVOLUTION
~~~

The subject carries the exact Capability or link claim digest. A review for a
different claim is invalid. Conflicting accepted and rejected decisions for
one subject abort active publication.

For a CAPABILITY_DEFINITION subject, an ACCEPTED review must carry exactly one
generalization_basis value: MULTI_SOURCE_REUSE or
SINGLE_OBSERVATION_GENERALIZATION. Other subject types must carry null. The
basis is review metadata, not Capability identity. Task 3 validates that the
field is closed; Task 8 checks its supporting Requirement evidence during
activation.

### Step 4: Add active-definition preconditions

Implement validate_active_definition with these checks:

~~~text
claim digest recomputes
family ID recomputes from the stable family key
review_ref points to an ACCEPTED exact capability review
definition lifecycle is ACTIVE
~~~

No function in this task reads a card name, source phrase, M3 pattern, engine
module, or live model output to establish authority.

The supporting-link and M3/M2 admissibility checks are intentionally deferred
to the link and build validation seams in Tasks 5 and 8. Task 3 validates the
intrinsic definition and its review; it does not invent link objects before the
link interface exists.

### Step 5: Run focused checks and commit

~~~powershell
python -m pytest tests/test_capability_review.py tests/test_capability_model.py tests/test_capability_identity.py -q
ruff format --check src/manafold_census/capability tests/test_capability_review.py tests/test_capability_model.py tests/test_capability_identity.py
ruff check src/manafold_census/capability tests/test_capability_review.py tests/test_capability_model.py tests/test_capability_identity.py
mypy src/manafold_census/capability
git add src/manafold_census/capability tests/test_capability_review.py tests/test_capability_model.py tests/test_capability_identity.py schemas/capability-definition.v1.schema.json schemas/capability-review.v1.schema.json
git diff --cached --check
git commit -m "feat: add M4 capability lifecycle and review"
~~~

Expected: focused tests and static checks PASS; no M3 or real-corpus command
is run.

## Task 4: Source Requirement admissibility

**Files:**

- Modify: src/manafold_census/capability/review.py
- Modify: src/manafold_census/capability/identity.py
- Create: schemas/source-requirement-admissibility.v1.schema.json
- Create: tests/test_capability_admissibility.py
- Modify: tests/test_capability_review.py

**Dependency:** Tasks 1–3.

**Authorization:** Separate implementation authorization is required. This
task creates only authority machinery and synthetic records; it does not
admit any real current M3 Requirement.

### Step 1: Add the red authority cases

Add:

~~~python
def test_proposed_complete_requirement_requires_m4_admissibility() -> None:
    requirement = proposed_complete_requirement()

    assert requirement.review.status is ReviewStatusV1.PROPOSED
    assert requirement.resolution.state is ResolutionStateV1.COMPLETE
    assert active_admissibility_for(requirement, records=()) is False


def test_accepted_admissibility_binds_exact_m3_m2_digests() -> None:
    requirement = proposed_complete_requirement()
    record = accepted_admissibility_record(
        requirement,
        m3_manifest_sha256="a" * 64,
    )

    assert active_admissibility_for(requirement, records=(record,)) is True


@pytest.mark.parametrize(
    ("status", "resolution"),
    [
        (ReviewStatusV1.REJECTED, ResolutionStateV1.COMPLETE),
        (ReviewStatusV1.PROPOSED, ResolutionStateV1.PARTIAL),
        (ReviewStatusV1.PROPOSED, ResolutionStateV1.UNRESOLVED),
    ],
)
def test_rejected_or_incomplete_requirement_is_never_admissible(
    status: ReviewStatusV1,
    resolution: ResolutionStateV1,
) -> None:
    requirement = requirement_with_status_and_resolution(status, resolution)

    with pytest.raises(ValueError, match="not admissible"):
        accepted_admissibility_record(requirement, m3_manifest_sha256="a" * 64)
~~~

Run:

~~~powershell
python -m pytest tests/test_capability_admissibility.py -q
~~~

Expected: collection fails because the admissibility model does not exist.

### Step 2: Implement the closed admissibility record

Implement:

~~~python
class AdmissibilityDecisionV1(StrEnum):
    ACCEPTED_FOR_CAPABILITY_MAPPING = "ACCEPTED_FOR_CAPABILITY_MAPPING"
    REJECTED_FOR_CAPABILITY_MAPPING = "REJECTED_FOR_CAPABILITY_MAPPING"
~~~

The exact record fields are:

~~~text
schema
authority_id
authority_version
record_id
review_digest
m3_analysis_manifest_sha256
requirement_id
requirement_wire_digest
m2_review_status_observed
m2_resolution_state_observed
m2_reviewed_claim_digest
decision
reviewer_id
~~~

The corresponding typed value is:

~~~python
@dataclass(frozen=True, slots=True)
class SourceRequirementAdmissibilityV1:
    authority_id: str
    authority_version: str
    record_id: str
    review_digest: str
    m3_analysis_manifest_sha256: str
    requirement_id: str
    requirement_wire_digest: str
    m2_review_status_observed: ReviewStatusV1
    m2_resolution_state_observed: ResolutionStateV1
    m2_reviewed_claim_digest: str
    decision: AdmissibilityDecisionV1
    reviewer_id: str
~~~

An accepted record requires:

~~~text
m2_review_status_observed in {PROPOSED, IN_REVIEW}
m2_resolution_state_observed = COMPLETE
requirement_wire_digest = wire_digest_for(requirement)
m2_reviewed_claim_digest = reviewed_claim_digest_for(requirement)
decision = ACCEPTED_FOR_CAPABILITY_MAPPING
~~~

M2 ACCEPTED plus COMPLETE does not need this record. A link records
M2_TERMINAL_ACCEPTANCE instead. M2 REJECTED cannot be accepted by this
record, and incomplete resolution cannot be upgraded by M4.

### Step 3: Implement non-cyclic admissibility identity

Implement:

~~~python
ADMISSIBILITY_DOMAIN = "census.source-requirement-admissibility.v1"
ADMISSIBILITY_PREFIX = "sra_"


def admissibility_claim_payload(
    record: SourceRequirementAdmissibilityV1,
) -> dict[str, JSONValue]:
    return {
        "schema": record.SCHEMA,
        "authority_id": record.authority_id,
        "authority_version": record.authority_version,
        "m3_analysis_manifest_sha256": record.m3_analysis_manifest_sha256,
        "requirement_id": record.requirement_id,
        "requirement_wire_digest": record.requirement_wire_digest,
        "m2_review_status_observed": record.m2_review_status_observed.value,
        "m2_resolution_state_observed": record.m2_resolution_state_observed.value,
        "m2_reviewed_claim_digest": record.m2_reviewed_claim_digest,
        "decision": record.decision.value,
        "reviewer_id": record.reviewer_id,
    }


def admissibility_review_digest_for(
    record: SourceRequirementAdmissibilityV1,
) -> str:
    return domain_digest(
        ADMISSIBILITY_DOMAIN,
        admissibility_claim_payload(record),
    )
~~~

record_id and review_digest are derived fields and are excluded from the
projection. The record does not hash a complete wire containing itself.

### Step 4: Add status-separation tests

Test that a later consumer can display independently:

~~~text
M2 review status
M2 resolution state
M4 admissibility basis
M4 admissibility decision
M4 Capability/link review status
~~~

Test that accepting M4 admissibility leaves
requirement.review.to_wire() byte-identical.

### Step 5: Run gates and commit

~~~powershell
python -m pytest tests/test_capability_admissibility.py tests/test_capability_review.py -q
ruff format --check src/manafold_census/capability tests/test_capability_admissibility.py tests/test_capability_review.py
ruff check src/manafold_census/capability tests/test_capability_admissibility.py tests/test_capability_review.py
mypy src/manafold_census/capability
git add src/manafold_census/capability tests/test_capability_admissibility.py tests/test_capability_review.py schemas/source-requirement-admissibility.v1.schema.json
git diff --cached --check
git commit -m "feat: add M4 source requirement admissibility"
~~~

Expected: no real M3 file, Requirement, or authority record is created.

## Task 5: Exact Requirement-to-Capability links and mapping dispositions

**Files:**

- Create: src/manafold_census/capability/link.py
- Modify: src/manafold_census/capability/identity.py
- Modify: src/manafold_census/capability/review.py
- Create: schemas/requirement-capability-link.v1.schema.json
- Create: schemas/requirement-mapping-decision.v1.schema.json
- Create: tests/test_capability_link.py

**Dependency:** Tasks 1–4.

**Authorization:** Separate implementation authorization is required.

### Step 1: Add failing link tests

Add:

~~~python
def test_direct_link_binds_requirement_and_capability_claims() -> None:
    requirement = proposed_complete_requirement()
    capability = active_draw_capability()
    admissibility = accepted_admissibility_record(
        requirement,
        m3_manifest_sha256="a" * 64,
    )

    link = direct_link(
        requirement=requirement,
        capability=capability,
        m3_manifest_sha256="a" * 64,
        admissibility=admissibility,
    )

    assert link.relation is LinkRelationV1.DIRECT
    assert link.requirement_id == requirement.requirement_id
    assert link.requirement_wire_digest == wire_digest_for(requirement)
    assert link.capability.claim_digest == capability.claim_digest


def test_two_active_direct_links_fail_but_proposals_remain_visible() -> None:
    requirement = accepted_complete_requirement()
    first = proposed_direct_link(requirement, active_draw_capability())
    second = proposed_direct_link(requirement, another_active_capability())

    assert validate_mapping_candidates((first, second)).is_ambiguous is True
    with pytest.raises(ValueError, match="multiple active DIRECT"):
        validate_active_links((activate(first), activate(second)))


def test_mapping_decision_preserves_unmapped_requirement() -> None:
    decision = mapping_decision(
        proposed_complete_requirement(),
        MappingDispositionV1.UNMAPPED,
        MappingReasonV1.NO_REVIEWED_CAPABILITY,
    )

    assert decision.active_link_ids == ()
    assert decision.disposition is MappingDispositionV1.UNMAPPED
~~~

Run:

~~~powershell
python -m pytest tests/test_capability_link.py -q
~~~

Expected: collection fails because link and mapping modules do not exist.

### Step 2: Implement link identity and relation values

Implement:

~~~python
class LinkRelationV1(StrEnum):
    DIRECT = "DIRECT"
    COMPOSITION_MEMBER = "COMPOSITION_MEMBER"


class LinkAdmissibilityBasisV1(StrEnum):
    M2_TERMINAL_ACCEPTANCE = "M2_TERMINAL_ACCEPTANCE"
    SOURCE_REQUIREMENT_ADMISSIBILITY = "SOURCE_REQUIREMENT_ADMISSIBILITY"


LINK_ID_DOMAIN = "census.requirement-capability-link-id.v1"
LINK_ID_PREFIX = "rcl_"
~~~

The link claim contains exactly:

~~~text
link_schema
m3_analysis_manifest_sha256
requirement_id
requirement_wire_digest
requirement_reviewed_claim_digest
Capability reference: family ID, version, claim digest
relation
parameter_bindings
m4_requirement_admissibility: basis, record ID, review digest
composition_context
~~~

The link ID is the domain digest of that claim. Review fields and report
fields are outside the claim. A changed Requirement wire, M3 manifest, or
Capability claim produces a stale or different link.

### Step 3: Implement active-link route validation

Implement validate_active_link with this exact branch:

~~~python
if requirement.review.status is ReviewStatusV1.ACCEPTED:
    require(requirement.resolution.state is ResolutionStateV1.COMPLETE)
    require(requirement.review.reviewed_claim_digest)
    require(basis is LinkAdmissibilityBasisV1.M2_TERMINAL_ACCEPTANCE)
    require(admissibility_record is None)
elif requirement.review.status in {
    ReviewStatusV1.PROPOSED,
    ReviewStatusV1.IN_REVIEW,
}:
    require(requirement.resolution.state is ResolutionStateV1.COMPLETE)
    require(basis is LinkAdmissibilityBasisV1.SOURCE_REQUIREMENT_ADMISSIBILITY)
    require(accepted_exact_admissibility_record)
else:
    raise ValueError("M2 REJECTED requirement is not admissible")
~~~

The function rejects PARTIAL, UNRESOLVED, stale digests, unknown Capability
versions, superseded/retired versions, unknown dimensions, and unknown
binding values. It never changes RequirementV1.

### Step 4: Implement mapping dispositions

Implement:

~~~python
class MappingDispositionV1(StrEnum):
    MAPPED = "MAPPED"
    UNMAPPED = "UNMAPPED"
    AMBIGUOUS = "AMBIGUOUS"
    OUTLIER = "OUTLIER"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
~~~

Implement these closed reason values:

~~~text
NO_REVIEWED_CAPABILITY
M2_REVIEW_NOT_TERMINAL
M4_ADMISSIBILITY_REVIEW_PENDING
M2_RESOLUTION_INCOMPLETE
MULTIPLE_PLAUSIBLE_CAPABILITIES
NO_REUSABLE_GENERALIZATION
SPECIAL_CASE
EXPLICIT_REVIEW_CONFLICT
~~~

RequirementMappingDecisionV1 has one row for every actual persisted M2
Requirement in the selected M3 artifact. Its active_link_ids are empty unless
the disposition is MAPPED. UNMAPPED means not selected in this snapshot, not
“no Capability exists.” OUTLIER and AMBIGUOUS require an accepted M4 mapping
review. INSUFFICIENT_EVIDENCE preserves the exact reason and does not create
a Capability.

### Step 5: Add stale and many-to-many tests

Test:

~~~text
unknown Requirement ID fails
unknown Capability reference fails
changed Requirement wire digest fails
changed Capability claim digest fails
M2 PROPOSED without SRA fails
M2 PROPOSED with accepted SRA succeeds when COMPLETE
M2 ACCEPTED plus COMPLETE succeeds without SRA
M2 REJECTED never succeeds
M2 PARTIAL and UNRESOLVED never succeeds
one Capability maps to many Requirements
one Requirement has multiple proposals
multiple active DIRECT links fail
multiple COMPOSITION_MEMBER links require explicit context
unmapped, ambiguous, outlier, and insufficient rows remain visible
~~~

### Step 6: Run gates and commit

~~~powershell
python -m pytest tests/test_capability_link.py -q
ruff format --check src/manafold_census/capability tests/test_capability_link.py
ruff check src/manafold_census/capability tests/test_capability_link.py
mypy src/manafold_census/capability
git add src/manafold_census/capability tests/test_capability_link.py schemas/requirement-capability-link.v1.schema.json schemas/requirement-mapping-decision.v1.schema.json
git diff --cached --check
git commit -m "feat: add M4 requirement capability links"
~~~

## Task 6: Composition, dependency, specialization, and evolution

**Files:**

- Create: src/manafold_census/capability/evolution.py
- Modify: src/manafold_census/capability/model.py
- Modify: src/manafold_census/capability/link.py
- Create: schemas/capability-evolution.v1.schema.json
- Create: tests/test_capability_evolution.py

**Dependency:** Tasks 1–5.

**Authorization:** Separate implementation authorization is required.

### Step 1: Add failing graph and evolution tests

Add:

~~~python
def test_composes_edges_are_directional_and_acyclic() -> None:
    composite = composite_capability()
    component = active_draw_capability()
    edge = composes_edge(composite, component)

    assert edge.from_capability == composite.reference
    assert edge.to_capability == component.reference
    validate_capability_edges((edge,))


def test_self_edge_and_cycle_fail_closed() -> None:
    capability = active_draw_capability()
    self_edge = requires_edge(capability, capability)

    with pytest.raises(ValueError, match="self-edge"):
        validate_capability_edges((self_edge,))

    other = another_active_capability()
    cycle = (
        requires_edge(capability, other),
        requires_edge(other, capability),
    )
    with pytest.raises(ValueError, match="cycle"):
        validate_capability_edges(cycle)


def test_split_preserves_old_references_and_requires_two_targets() -> None:
    old = active_draw_capability()
    first = active_narrow_capability()
    second = active_other_narrow_capability()
    event = split_event(old, (first, second))

    assert event.operation is EvolutionOperationV1.SPLIT
    assert event.from_references == (old.reference,)
    assert event.to_references == (first.reference, second.reference)
~~~

Run:

~~~powershell
python -m pytest tests/test_capability_evolution.py -q
~~~

Expected: collection fails because the evolution module does not exist.

### Step 2: Implement typed semantic edges

Implement the closed edge values:

~~~text
COMPOSES
REQUIRES
SPECIALIZES
~~~

Edges are directional and target exact Capability references including claim
digest. SHARES_DIMENSION is a derived report view and is not persisted.

The CompositionComponentV1 and CompositionClaimV1 types declared in Task 2 are
validated here against exact component references. Component keys are unique
non-empty identifiers scoped to one claim. Their meaning comes from the exact
component Capability reference and ordinal; they are not free-form executable
labels.

Validation:

~~~text
self-edge fails
COMPOSES graph is acyclic
REQUIRES graph is acyclic
SPECIALIZES graph is acyclic
component Capability reference exists exactly
new active composite references active non-retired components
composition component keys are unique
required component keys are covered exactly once
~~~

These edges assert semantic relationships only. They do not assert package
dependencies, runtime dependencies, engine support, or implementation order.

### Step 3: Implement evolution events

Implement:

~~~python
class EvolutionOperationV1(StrEnum):
    ADDITION = "ADDITION"
    SPLIT = "SPLIT"
    MERGE = "MERGE"
    SUPERSESSION = "SUPERSESSION"
    RETIREMENT = "RETIREMENT"
~~~

Implement exact cardinalities:

~~~text
ADDITION: no from, one to
SPLIT: one from, at least two to
MERGE: at least two from, one to
SUPERSESSION: one from, one to
RETIREMENT: one from, no to
~~~

An evolution event contains an identity derived from operation and exact
references, plus an accepted evolution review reference. It does not hash a
future manifest. Old definitions and links remain in historical artifacts.
New links to successors are explicit. There is no automatic migration.

### Step 4: Add history and invalid-input tests

Reject:

~~~text
split with one target
merge with one source
supersession to the same version
retirement with a replacement
evolution reference with stale claim digest
new link to superseded or retired version
cycle in any semantic edge relation
component key duplication
implicit composition inferred from link count
~~~

### Step 5: Run gates and commit

~~~powershell
python -m pytest tests/test_capability_evolution.py tests/test_capability_link.py -q
ruff format --check src/manafold_census/capability tests/test_capability_evolution.py tests/test_capability_link.py
ruff check src/manafold_census/capability tests/test_capability_evolution.py tests/test_capability_link.py
mypy src/manafold_census/capability
git add src/manafold_census/capability tests/test_capability_evolution.py schemas/capability-evolution.v1.schema.json
git diff --cached --check
git commit -m "feat: add M4 capability evolution relations"
~~~

## Task 7: Frozen M3 input adapter and Requirement-set identity

**Files:**

- Create: src/manafold_census/capability/input.py
- Modify: src/manafold_census/capability/identity.py
- Create: tests/test_capability_input.py
- Create: tests/capability_m3_fixtures.py

**Dependency:** Tasks 1–6 and the existing M3 implementation.

**Authorization:** Separate implementation authorization is required. Use
only temporary synthetic M3 artifacts assembled by test helpers. Do not use
ignored real Run-A/Run-B directories and do not run the full corpus.

The input seam is explicit:

~~~python
@dataclass(frozen=True, slots=True)
class FrozenM3InputV1:
    structural_output_directory: Path
    analysis_output_directory: Path
    source_lock_path: Path
    expected_analysis_manifest_sha256: str
~~~

The descriptor is the only input to load_m3_requirement_corpus and the same
descriptor is passed through build_reference_m4. It supplies all three inputs
required by the existing validate_analysis_closure function.

### Step 1: Add input-boundary tests

Build synthetic M3 artifacts with the existing M3 model helpers and add:

~~~python
def test_input_collects_only_requirements_in_nonempty_bundles(tmp_path: Path) -> None:
    m3_input = write_synthetic_m3(
        tmp_path / "m3",
        records=(
            record_with_proposed_requirement(),
            unresolved_record_without_bundle(),
            no_requirements_applicable_record(),
        ),
    )

    loaded = load_m3_requirement_corpus(m3_input)

    assert len(loaded.requirements) == 1
    assert loaded.unresolved_analysis_count == 1
    assert loaded.no_requirements_applicable_count == 1


def test_changed_m3_manifest_sha_fails_before_requirement_mapping(
    tmp_path: Path,
) -> None:
    m3_input = write_synthetic_m3(
        tmp_path / "m3",
        records=(record_with_requirement(),),
    )

    with pytest.raises(ValueError, match="M3 manifest SHA"):
        load_m3_requirement_corpus(
            replace(m3_input, expected_analysis_manifest_sha256="f" * 64)
        )


def test_requirement_set_digest_is_order_independent(tmp_path: Path) -> None:
    first_input = write_synthetic_m3(
        tmp_path / "first",
        records=(record_with_requirement(), record_with_other_requirement()),
    )
    second_input = write_synthetic_m3(
        tmp_path / "second",
        records=(record_with_other_requirement(), record_with_requirement()),
    )

    first = load_m3_requirement_corpus(first_input)
    second = load_m3_requirement_corpus(second_input)

    assert first.requirement_set_digest == second.requirement_set_digest
~~~

Run:

~~~powershell
python -m pytest tests/test_capability_input.py -q
~~~

Expected: the first run fails because the input adapter does not exist.

### Step 2: Implement the M3 input value

Implement:

~~~python
from dataclasses import replace


@dataclass(frozen=True, slots=True)
class M3RequirementCorpusV1:
    m3_analysis_manifest_sha256: str
    m3_analysis_schema: str
    m2_requirement_schema: str
    m2_bundle_schema: str
    requirements: tuple[RequirementV1, ...]
    requirement_set_digest: str
    m3_record_count: int
    requirements_produced_card_count: int
    no_requirements_applicable_count: int
    unresolved_analysis_count: int
~~~

load_m3_requirement_corpus(input_descriptor: FrozenM3InputV1) must:

* read canonical analysis-manifest.json;
* calculate its raw SHA-256 with the existing helper;
* require input_descriptor.expected_analysis_manifest_sha256 to match;
* invoke the existing M3 validate_analysis_closure with
  input_descriptor.structural_output_directory,
  input_descriptor.analysis_output_directory, and
  input_descriptor.source_lock_path for independent
  record/trace/manifest/source binding;
* collect Requirements only from non-null bundles;
* preserve M3 outcome counts;
* reject duplicate Requirement IDs with different wire digests; and
* never infer a Requirement from UNRESOLVED_ANALYSIS with no bundle.

The loader does not inspect live source data, call a producer, call an engine,
or call a model.

### Step 3: Implement Requirement-set digest

Add:

~~~python
REQUIREMENT_SET_DOMAIN = "census.m4-requirement-set.v1"


def requirement_set_digest_for(
    m3_manifest_sha256: str,
    requirements: Sequence[RequirementV1],
) -> str:
    entries = [
        {
            "requirement_id": requirement.requirement_id,
            "requirement_wire_digest": wire_digest_for(requirement),
        }
        for requirement in requirements
    ]
    entries.sort(key=lambda item: str(item["requirement_id"]))
    return domain_digest(
        REQUIREMENT_SET_DOMAIN,
        {
            "m3_analysis_manifest_sha256": m3_manifest_sha256,
            "requirements": entries,
        },
    )
~~~

The M2 Requirement ID remains M2-owned. The M4 digest only binds the exact
selected M3 snapshot and the exact Requirement wires consumed by M4.

### Step 4: Add input negative tests

Reject:

~~~text
noncanonical M3 manifest
wrong M3 manifest SHA
wrong M3 analysis schema
wrong M2 schema binding
M3 closure failure
duplicate Requirement ID with different wire
Requirement source not validated by M3
Requirement outside a persisted M3 bundle
NO_REQUIREMENTS_APPLICABLE treated as a Requirement
UNRESOLVED_ANALYSIS without bundle treated as a Requirement
~~~

### Step 5: Run gates and commit

~~~powershell
python -m pytest tests/test_capability_input.py -q
ruff format --check src/manafold_census/capability tests/test_capability_input.py tests/capability_m3_fixtures.py
ruff check src/manafold_census/capability tests/test_capability_input.py tests/capability_m3_fixtures.py
mypy src/manafold_census/capability
git add src/manafold_census/capability tests/test_capability_input.py tests/capability_m3_fixtures.py
git diff --cached --check
git commit -m "feat: bind M4 to frozen M3 requirements"
~~~

## Task 8: M4 manifest, deterministic reference build, and publication validation

**Files:**

- Create: src/manafold_census/capability/manifest.py
- Create: src/manafold_census/capability/validate.py
- Create: src/manafold_census/capability/build.py
- Create: schemas/capability-ontology-manifest.v1.schema.json
- Create: tests/test_capability_manifest.py
- Create: tests/test_capability_validate.py
- Create: tests/test_capability_build.py

**Dependency:** Tasks 1–7.

**Authorization:** Separate implementation authorization is required. The
reference build uses synthetic M3 input and synthetic review records only.

### Step 1: Add manifest and build red tests

Add:

~~~python
def test_m4_manifest_binds_m3_and_all_authoritative_files(tmp_path: Path) -> None:
    m3_input = write_synthetic_m3(tmp_path / "m3")
    result = build_synthetic_m4(
        tmp_path / "output",
        m3_input=m3_input,
        parent_m4_manifest_sha256=None,
        parent_m4_manifest=None,
    )

    assert result.manifest.m3_analysis_manifest_sha256
    assert result.manifest.requirement_set_digest
    assert len(result.manifest.link_shards) == 16
    assert len(result.manifest.mapping_decision_shards) == 16
    assert "report_index_digest" not in result.manifest.to_wire()


def test_failed_build_never_publishes_manifest(tmp_path: Path) -> None:
    output = tmp_path / "output"

    with pytest.raises(CapabilityBuildError, match="stale Capability"):
        build_synthetic_m4_with_stale_link(
            output,
            m3_input=write_synthetic_m3(tmp_path / "m3"),
            parent_m4_manifest_sha256=None,
            parent_m4_manifest=None,
        )

    assert not (output / "m4-ontology-manifest.json").exists()


def test_same_synthetic_inputs_produce_identical_bytes(tmp_path: Path) -> None:
    m3_input = write_synthetic_m3(tmp_path / "m3")
    first = build_synthetic_m4(
        tmp_path / "first",
        m3_input=m3_input,
        parent_m4_manifest_sha256=None,
        parent_m4_manifest=None,
    )
    second = build_synthetic_m4(
        tmp_path / "second",
        m3_input=m3_input,
        parent_m4_manifest_sha256=None,
        parent_m4_manifest=None,
    )

    assert relative_bytes(first.output_dir) == relative_bytes(second.output_dir)
    assert directory_digest(first.output_dir) == directory_digest(second.output_dir)


def test_parent_manifest_is_explicit_and_genesis_is_null(tmp_path: Path) -> None:
    m3_input = write_synthetic_m3(tmp_path / "m3")
    genesis = build_synthetic_m4(
        tmp_path / "genesis",
        m3_input=m3_input,
        parent_m4_manifest_sha256=None,
        parent_m4_manifest=None,
    )
    child = build_synthetic_m4(
        tmp_path / "child",
        m3_input=m3_input,
        parent_m4_manifest_sha256=genesis.manifest.digest(),
        parent_m4_manifest=genesis.manifest,
    )

    assert genesis.manifest.parent_m4_manifest_sha256 is None
    assert child.manifest.parent_m4_manifest_sha256 == genesis.manifest.digest()


def test_parent_manifest_cannot_be_inferred_or_mismatched(tmp_path: Path) -> None:
    m3_input = write_synthetic_m3(tmp_path / "m3")
    genesis = build_synthetic_m4(
        tmp_path / "genesis",
        m3_input=m3_input,
        parent_m4_manifest_sha256=None,
        parent_m4_manifest=None,
    )

    with pytest.raises(ValueError, match="parent M4 manifest"):
        build_synthetic_m4(
            tmp_path / "mismatched",
            m3_input=m3_input,
            parent_m4_manifest_sha256="f" * 64,
            parent_m4_manifest=genesis.manifest,
        )


def test_activation_checks_multi_source_generalization_basis(tmp_path: Path) -> None:
    m3_input = write_synthetic_m3(tmp_path / "m3")
    definition = active_draw_capability()
    review = accepted_capability_review(
        definition,
        generalization_basis=GeneralizationBasisV1.MULTI_SOURCE_REUSE,
    )
    links = links_for_two_distinct_m1_sources(definition, m3_input)

    validate_activation_eligibility(
        definition,
        review,
        load_m3_requirement_corpus(m3_input),
        links,
    )


def test_singleton_activation_requires_explicit_generalization_basis(
    tmp_path: Path,
) -> None:
    m3_input = write_synthetic_m3(tmp_path / "m3")
    definition = active_draw_capability()
    review = accepted_capability_review(
        definition,
        generalization_basis=GeneralizationBasisV1.SINGLE_OBSERVATION_GENERALIZATION,
    )
    links = links_for_one_m1_source(definition, m3_input)

    validate_activation_eligibility(
        definition,
        review,
        load_m3_requirement_corpus(m3_input),
        links,
    )
~~~

Run:

~~~powershell
python -m pytest tests/test_capability_manifest.py tests/test_capability_build.py -q
~~~

Expected: collection fails because manifest and build modules do not exist.

### Step 2: Implement the authoritative layout

The reference output layout is:

~~~text
capabilities.jsonl
review-authority.jsonl
requirement-admissibility.jsonl
evolution.jsonl
links/0.jsonl through links/f.jsonl
mapping-decisions/0.jsonl through mapping-decisions/f.jsonl
m4-ontology-manifest.json
~~~

Reports and worklists are added only by the downstream report task.

Definitions, reviews, admissibility, and evolution use canonical JSONL sorted
by their stable keys. Links and mapping decisions use 16 shards keyed by the
first hexadecimal character after the srq_ prefix in requirement_id. Empty
shards are retained.

### Step 3: Implement manifest fields and descriptors

M4OntologyManifestV1 contains:

~~~text
schema
ontology_schema
build_profile
m3_analysis_manifest_sha256
m3_analysis_schema
m2_requirement_schema
m2_bundle_schema
m4_dimension_registry_version
parent_m4_manifest_sha256
requirement_set_digest
capability_file
review_file
admissibility_file
evolution_file
link_shards
mapping_decision_shards
~~~

Each descriptor contains exactly:

~~~text
relative_path
sha256
byte_length
record_count
~~~

The manifest never includes report bytes or report-index digests. A later
report index points to the finalized M4 manifest.

Define these manifest values before the build function:

~~~python
@dataclass(frozen=True, slots=True)
class M4FileDescriptorV1:
    relative_path: str
    sha256: str
    byte_length: int
    record_count: int


@dataclass(frozen=True, slots=True)
class M4OntologyManifestV1:
    schema: str
    ontology_schema: str
    build_profile: str
    m3_analysis_manifest_sha256: str
    m3_analysis_schema: str
    m2_requirement_schema: str
    m2_bundle_schema: str
    m4_dimension_registry_version: str
    parent_m4_manifest_sha256: str | None
    requirement_set_digest: str
    capability_file: M4FileDescriptorV1
    review_file: M4FileDescriptorV1
    admissibility_file: M4FileDescriptorV1
    evolution_file: M4FileDescriptorV1
    link_shards: tuple[M4FileDescriptorV1, ...]
    mapping_decision_shards: tuple[M4FileDescriptorV1, ...]
~~~

### Step 4: Implement the reference build

Define the build result before implementing the public interface:

~~~python
@dataclass(frozen=True, slots=True)
class M4BuildResultV1:
    output_dir: Path
    manifest: M4OntologyManifestV1
    requirements: tuple[RequirementV1, ...]
    definitions: tuple[CapabilityDefinitionV1, ...]
    links: tuple[RequirementCapabilityLinkV1, ...]
    mapping_decisions: tuple[RequirementMappingDecisionV1, ...]


def build_reference_m4(
    m3_input: FrozenM3InputV1,
    parent_m4_manifest_sha256: str | None,
    parent_m4_manifest: M4OntologyManifestV1 | None,
    capability_definitions: Sequence[CapabilityDefinitionV1],
    reviews: Sequence[CapabilityReviewRecordV1],
    admissibility_records: Sequence[SourceRequirementAdmissibilityV1],
    links: Sequence[RequirementCapabilityLinkV1],
    mapping_decisions: Sequence[RequirementMappingDecisionV1],
    evolution_records: Sequence[CapabilityEvolutionV1],
    output_dir: str | Path,
) -> M4BuildResultV1:
    input_corpus = load_m3_requirement_corpus(m3_input)
    validate_m4_inputs(
        input_corpus,
        parent_m4_manifest_sha256,
        parent_m4_manifest,
        capability_definitions,
        reviews,
        admissibility_records,
        links,
        mapping_decisions,
        evolution_records,
    )
    return publish_validated_m4(
        input_corpus,
        capability_definitions,
        reviews,
        admissibility_records,
        links,
        mapping_decisions,
        evolution_records,
        output_dir,
        parent_m4_manifest_sha256,
    )
~~~

validate_m4_inputs is the private pure validator in validate.py, and
publish_validated_m4 is the private staging/publication seam in build.py. They
accept the typed values shown above and return the M4BuildResultV1 after the
complete reread; neither call performs network access or semantic inference.

The implementation body must:

* reject an existing non-empty output directory;
* load and validate the frozen M3 Requirement corpus;
* validate all Capability definitions and exact claim digests;
* validate review and admissibility records;
* validate every link against the loaded Requirement and Capability sets;
* require exactly one mapping decision per actual Requirement;
* validate evolution and semantic edges;
* write all authoritative files into a fresh temporary directory;
* write the canonical manifest;
* reread every file through independent parser/validator functions;
* recompute descriptors and manifest identity; and
* atomically publish the completed directory only after all checks pass.

Exceptions are classified as invalid M3 input, invalid wire, stale link,
review disagreement, graph failure, digest failure, or publication failure.
They never become an unresolved semantic disposition.

The parent input is explicit: for the genesis snapshot,
parent_m4_manifest_sha256 and parent_m4_manifest are both null. For every
later snapshot, both are required; the supplied parent manifest is reread and
its canonical digest must equal parent_m4_manifest_sha256. The builder never
discovers a parent from a directory, branch, timestamp, or latest-file rule.
The M4 manifest stores the exact parent SHA without mutating the parent.

Define the global activation seam separately from intrinsic definition
validation:

~~~python
def validate_activation_eligibility(
    definition: CapabilityDefinitionV1,
    definition_review: CapabilityReviewRecordV1,
    corpus: M3RequirementCorpusV1,
    supporting_links: Sequence[RequirementCapabilityLinkV1],
) -> None:
    validate_active_definition(definition, definition_review)
    admitted = admitted_requirements(corpus, supporting_links)
    basis = definition_review.generalization_basis
    if basis is GeneralizationBasisV1.MULTI_SOURCE_REUSE:
        if distinct_m1_source_count(admitted) < 2:
            raise ValueError("multi-source reuse requires two M1 sources")
    elif basis is GeneralizationBasisV1.SINGLE_OBSERVATION_GENERALIZATION:
        if len(admitted) != 1:
            raise ValueError("singleton generalization requires one M1 source")
    else:
        raise ValueError("active definition requires generalization_basis")
~~~

This is the only seam that may use supporting Requirements to evaluate the
multi-source versus singleton rule. It verifies that every supporting link
uses an active Capability, a complete Requirement, and either terminal M2
acceptance or an accepted exact SOURCE_REQUIREMENT_ADMISSIBILITY record. The
single-observation path is valid only with the exact closed review basis; it is
never inferred from a one-row count.

admitted_requirements and distinct_m1_source_count are private pure helpers in
validate.py. They return only Requirements already validated by the M3 input
and link seams.

### Step 5: Add closure and deterministic ordering tests

Test:

~~~text
definitions sorted by family ID/version
review records sorted by subject/record ID
admissibility records sorted by Requirement ID/record ID
evolution records sorted by operation/from/to/event ID
links sorted by Requirement ID/relation/Capability/link ID
mapping decisions sorted by Requirement ID
link shard assignment uses only Requirement ID
missing mapping decision fails
duplicate mapping decision fails
missing or extra link endpoint fails
manifest descriptors match exact bytes
reports are absent from manifest identity
failed publication leaves no authoritative manifest
~~~

### Step 6: Run gates and commit

~~~powershell
python -m pytest tests/test_capability_manifest.py tests/test_capability_validate.py tests/test_capability_build.py -q
ruff format --check src/manafold_census/capability tests/test_capability_manifest.py tests/test_capability_validate.py tests/test_capability_build.py
ruff check src/manafold_census/capability tests/test_capability_manifest.py tests/test_capability_validate.py tests/test_capability_build.py
mypy src/manafold_census/capability
git add src/manafold_census/capability tests/test_capability_manifest.py tests/test_capability_validate.py tests/test_capability_build.py schemas/capability-ontology-manifest.v1.schema.json
git diff --cached --check
git commit -m "feat: add deterministic M4 ontology publication"
~~~

## Task 9: Deterministic candidate grouping and review worklists

**Files:**

- Create: src/manafold_census/capability/candidates.py
- Create: schemas/capability-candidate-cluster.v1.schema.json
- Create: tests/test_capability_candidates.py

**Dependency:** Tasks 1, 2, 7, and 8.

**Authorization:** Separate implementation authorization is required. This
task creates proposal artifacts only and does not activate a Capability.

### Step 1: Add grouping red tests

Add:

~~~python
def test_quantity_variants_share_one_candidate_signature() -> None:
    first = proposed_draw_requirement(quantity=2)
    second = proposed_draw_requirement(quantity=3, other_source=True)
    corpus = corpus_for_requirements((first, second))

    result = group_requirement_candidates(corpus)

    assert len(result.clusters) == 1
    assert result.clusters[0].distinct_source_count == 2
    assert result.clusters[0].requirement_count == 2


def test_different_operation_kinds_do_not_share_signature() -> None:
    draw = proposed_draw_requirement(quantity=2)
    damage = proposed_damage_requirement()
    corpus = corpus_for_requirements((draw, damage))

    result = group_requirement_candidates(corpus)

    assert len(result.clusters) == 2


def test_cluster_is_not_a_capability_definition() -> None:
    corpus = corpus_for_requirements((proposed_draw_requirement(quantity=2),))
    cluster = group_requirement_candidates(corpus).clusters[0]

    assert cluster.status is CandidateClusterStatusV1.PROPOSED
    assert cluster.capability_definition is None


def test_candidate_identity_requires_the_frozen_m3_corpus() -> None:
    with pytest.raises(TypeError, match="M3RequirementCorpusV1"):
        group_requirement_candidates((proposed_draw_requirement(quantity=2),))
~~~

Run:

~~~powershell
python -m pytest tests/test_capability_candidates.py -q
~~~

Expected: collection fails because candidate grouping is not implemented.

### Step 2: Implement deterministic grouping

Implement the proposal-only state:

~~~python
class CandidateClusterStatusV1(StrEnum):
    PROPOSED = "PROPOSED"
~~~

The public grouping interface accepts only the validated M3 corpus envelope:

~~~python
def group_requirement_candidates(
    corpus: M3RequirementCorpusV1,
) -> CandidateGroupingResultV1:
    if not isinstance(corpus, M3RequirementCorpusV1):
        raise TypeError("grouping requires M3RequirementCorpusV1")
    return group_validated_requirements(corpus)
~~~

group_validated_requirements is a private deterministic seam in candidates.py;
it reads corpus.requirements, corpus.m3_analysis_manifest_sha256, and
corpus.requirement_set_digest. There is no public overload that accepts a raw
Requirement sequence without the M3 envelope.

The grouping signature contains:

~~~text
M2 family/kind operation anchor
registered path keys
typed M2 value shapes and enum values
known, unknown, or optional state
M2 relationship shape where explicitly supplied
dimension-mask policy
~~~

The generator may mask a concrete value only when the corresponding
code-owned path is declared as a Capability dimension. It must not mask
operation, actor, zone, timing, event, selection, replacement, condition, or
payment semantics merely to increase frequency.

candidate_id is:

~~~text
ccg_ + domain_digest(
    "census.capability-candidate-cluster.v1",
    {
        "m3_analysis_manifest_sha256": corpus.m3_analysis_manifest_sha256,
        "requirement_set_digest": corpus.requirement_set_digest,
        "generator_id": generator_id,
        "generator_version": generator_version,
        "group_signature": canonical_group_signature,
        "requirement_ids": sorted_requirement_ids,
    }
)
~~~

The candidate record contains exact Requirement IDs, integer counts, typed
variation summaries, and a proposed claim sketch. It never has lifecycle
ACTIVE or an accepted review reference.

### Step 3: Implement deterministic ranking and worklists

Sort groups by:

~~~text
descending distinct_source_count
descending requirement_count
ascending group_signature_digest
ascending candidate_id
~~~

Worklist rows include:

~~~text
candidate_id
requirement_count
distinct_source_count
M2 family/kind counts
typed dimension variation summaries
representative Requirement IDs
unknown and unresolved counts
singleton and outlier indicators
current M4 review and mapping state
~~~

All counts are integers. No floating-point confidence participates in identity
or authority.

### Step 4: Add the optional proposal-import boundary

Define a disabled-by-default importer for a pinned model proposal artifact.
The importer validates:

~~~text
generator_id/version
exact M3 manifest SHA
exact Requirement-set digest
canonical output bytes
closed candidate fields
status = PROPOSED
~~~

It has no live model call, no credential input, no dynamic import, and no path
selected by artifact data. It cannot create a review record or active
Capability.

### Step 5: Run gates and commit

~~~powershell
python -m pytest tests/test_capability_candidates.py -q
ruff format --check src/manafold_census/capability tests/test_capability_candidates.py
ruff check src/manafold_census/capability tests/test_capability_candidates.py
mypy src/manafold_census/capability
git add src/manafold_census/capability tests/test_capability_candidates.py schemas/capability-candidate-cluster.v1.schema.json
git diff --cached --check
git commit -m "feat: add deterministic M4 candidate grouping"
~~~

## Task 10: Derived reports, offline CLI, and resource packaging

**Files:**

- Create: src/manafold_census/capability/report.py
- Create: schemas/capability-report.v1.schema.json
- Create: tests/test_capability_report.py
- Modify: src/manafold_census/cli.py
- Modify: justfile
- Modify: pyproject.toml
- Modify: tests/test_resources.py

**Dependency:** Tasks 1–9.

**Authorization:** Separate implementation authorization is required. The
commands use synthetic fixtures and never run real M3 extraction or source
acquisition.

### Step 1: Add report red tests

Add:

~~~python
def test_report_is_downstream_of_m4_manifest(tmp_path: Path) -> None:
    result = build_synthetic_m4(tmp_path / "m4")
    report = build_capability_reports(result)

    assert report.m4_manifest_sha256 == result.manifest.digest()
    assert report.report_index.m4_manifest_sha256 == result.manifest.digest()


def test_report_keeps_m3_unresolved_context_separate() -> None:
    report = report_for_synthetic_sparse_m3()

    assert report.m3_context.unresolved_analysis_count == 1
    assert report.mapping_counts["INSUFFICIENT_EVIDENCE"] == 1
    assert report.capability_counts["ACTIVE"] == 0
~~~

Run:

~~~powershell
python -m pytest tests/test_capability_report.py -q
~~~

Expected: collection fails because report generation is not implemented.

### Step 2: Implement non-authoritative reports

Reports may contain:

~~~text
Requirements per Capability version
Capabilities by M2 family/kind
parameter-dimension distributions
active, superseded, and retired counts
mapped, unmapped, ambiguous, outlier, and insufficient counts
reuse counts
distinct source-card counts
exact parameter variation summaries
candidate cluster ranking
review queue sizes
evolution summaries
M3 card outcome context
~~~

Reports are generated only after a finalized M4 manifest. The report index
binds the exact M4 manifest SHA and report file descriptors. The M4 manifest
does not bind report bytes. Rates use integer numerator/denominator pairs.

CapabilityReportV1 exposes the derived report document, and
CapabilityReportIndexV1 exposes m4_manifest_sha256 plus sorted report file
descriptors. Neither type is accepted by M4 manifest validation.

### Step 3: Add bounded synthetic commands

Add CLI functions with explicit synthetic-only behavior:

~~~python
def m4_command(
    command: str,
    repository_root: str | Path,
    output: str | Path | None,
    synthetic: bool,
) -> int:
    if not synthetic:
        raise ValueError("M4 commands require --synthetic until separately authorized")
    if command == "build":
        build_synthetic_m4_command(repository_root, output)
    elif command == "check":
        check_synthetic_m4_command(repository_root, output)
    elif command == "report":
        report_synthetic_m4_command(repository_root, output)
    else:
        raise ValueError("unsupported M4 command")
    return 0
~~~

Expose:

~~~text
python -m manafold_census.cli m4-build --synthetic
python -m manafold_census.cli m4-check --synthetic
python -m manafold_census.cli m4-report --synthetic
~~~

The command tests must prove that default execution never calls source
acquisition, M3 producer execution, an engine, a database, or a model API.

Add Justfile recipes:

~~~text
m4-build:
    python -m manafold_census.cli m4-build --synthetic

m4-check:
    python -m manafold_census.cli m4-check --synthetic

m4-report:
    python -m manafold_census.cli m4-report --synthetic
~~~

Keep the commands outside the broad check recipe until their bounded runtime
is measured and a separate CI-scope decision includes them.

### Step 4: Package schemas and fixtures

The existing pyproject.toml schema glob already includes JSON schemas. Extend
tool.setuptools.data-files with:

~~~toml
"share/manafold-census/fixtures/capability" = ["fixtures/capability/*.json"]
~~~

Extend tests/test_resources.py to require every M4 schema and every synthetic
Capability fixture in a fresh non-editable wheel. Generated M4 artifacts are
never wheel resources.

### Step 5: Run gates and commit

~~~powershell
python -m pytest tests/test_capability_report.py tests/test_resources.py -q
ruff format --check src/manafold_census/capability src/manafold_census/cli.py tests/test_capability_report.py tests/test_resources.py
ruff check src/manafold_census/capability src/manafold_census/cli.py tests/test_capability_report.py tests/test_resources.py
mypy src/manafold_census
python -m manafold_census.cli m4-build --synthetic
python -m manafold_census.cli m4-check --synthetic
python -m manafold_census.cli m4-report --synthetic
git add src/manafold_census/capability src/manafold_census/cli.py justfile pyproject.toml tests/test_capability_report.py tests/test_resources.py schemas fixtures/capability
git diff --cached --check
git commit -m "feat: add offline M4 reports and commands"
~~~

Expected: all commands use synthetic data, report PASS, and do not create real
Capability ontology data.

## Task 11: Maintainability, security, reproduction, and conformance closure

**Files:**

- Create: tests/test_capability_reproduction.py
- Create: tests/test_capability_conformance.py
- Modify: tests/test_maintainability.py
- Modify: .github/workflows/ci.yml

**Dependency:** Tasks 1–10.

**Authorization:** Separate implementation authorization is required. This
task closes synthetic M4 implementation gates only; it does not authorize
real Requirement mapping or M5.

### Step 1: Add complete conformance tests

Add one synthetic matrix covering:

~~~text
Capability family identity excludes dimensions
same nucleus plus changed claim keeps family ID and increments version
changed nucleus creates a new family ID
display-name changes do not change claim digest
review digest projection excludes record ID and digest
admissibility digest projection excludes record ID and digest
M2 PROPOSED plus COMPLETE plus accepted SRA enables active link
M2 ACCEPTED plus COMPLETE enables active link without SRA
M2 REJECTED never enables active link
M2 PARTIAL and UNRESOLVED never enable active link
M3 unresolved card without bundle contributes no Requirement
one Requirement receives exactly one mapping decision
one Capability explains many Requirements
one Requirement has multiple proposals but no implicit ambiguity resolution
composition-member links require explicit composite context
all evolution operation cardinalities
all semantic edge cycle failures
same frozen inputs produce byte-identical output
input-order and mapping-order permutations preserve bytes
duplicate insertion is idempotent only for identical claims
stale M3, Requirement, and Capability digests fail
generated cluster cannot become ACTIVE
partial publication leaves no manifest
no model, network, database, or dynamic execution path is required
~~~

Run the focused conformance suite first:

~~~powershell
python -m pytest tests/test_capability_conformance.py -q
~~~

Expected before implementation of this task: the new cases fail at the first
missing integration assertion. After implementation: all focused cases PASS.

### Step 2: Add reproduction tests

Implement:

~~~python
def test_two_clean_m4_builds_have_identical_bytes_and_directory_digest(
    tmp_path: Path,
) -> None:
    first = build_synthetic_m4(tmp_path / "first")
    second = build_synthetic_m4(tmp_path / "second")

    assert relative_bytes(first.output_dir) == relative_bytes(second.output_dir)
    assert directory_digest(first.output_dir) == directory_digest(second.output_dir)
~~~

Also test shuffled Requirement, definition, review, admissibility, link,
evolution, and mapping-decision input. Every permutation must produce
identical canonical bytes. A future optimized backend cannot be added without
parity with this single-process path.

### Step 3: Extend maintainability and security guards

Extend tests/test_maintainability.py to:

~~~text
scan src/manafold_census/capability/*.py for <=500 lines
reject eval, exec, compile, __import__, importlib, pickle, and artifact callbacks
reject engine names, engine support fields, card executors, and source acquisition
reject live HTTP, model, and database dependencies
reject hard-coded 38,740 loops
reject Capability identity fields containing source/card/pattern/producer paths
~~~

The guard must permit ordinary words in documentation tests only where the
scope is code scanning. It must not alter existing M1, M2, or M3 guard
semantics.

### Step 4: Add bounded offline CI

Add M4 synthetic commands after existing bounded M3 synthetic steps:

~~~yaml
- name: Build bounded synthetic M4
  run: python -m manafold_census.cli m4-build --synthetic
- name: Check bounded synthetic M4
  run: python -m manafold_census.cli m4-check --synthetic
- name: Report bounded synthetic M4
  run: python -m manafold_census.cli m4-report --synthetic
~~~

Do not add:

~~~text
real M3 artifact acquisition
real full-corpus M4 mapping
live LLM or model calls
database services
engine integration
M5 Explorer
~~~

Extend fresh-wheel smoke to verify all M4 schemas and synthetic fixtures from
outside the repository working directory.

### Step 5: Run the complete local gate

Run each command separately:

~~~powershell
python -m pytest -q
ruff format --check .
ruff check .
mypy src/manafold_census
python -m manafold_census.cli reproduce
python -m manafold_census.cli corpus-check --synthetic
python -m manafold_census.cli structural-check --synthetic
python -m manafold_census.cli m3-check --synthetic
python -m manafold_census.cli m4-build --synthetic
python -m manafold_census.cli m4-check --synthetic
python -m manafold_census.cli m4-report --synthetic
~~~

Record every result separately as PASS, FAIL, NOT_RUN, or BLOCKED. Successful
local tests do not substitute for hosted CI.

### Step 6: Verify final implementation scope

Use:

~~~powershell
$all = @(
    @(git diff --name-only)
    @(git diff --cached --name-only)
    @(git ls-files --others --exclude-standard)
) | Sort-Object -Unique
$all
~~~

The implementation slice may contain only the declared M4 package, M4 schemas,
synthetic M4 fixtures/tests, and the explicitly declared packaging, CLI, and
CI integration paths. It must not contain M1, M2, M3, source-lock, engine, M5,
real ontology, or real mapping changes.

### Step 7: Commit the conformance slice

After the tests pass, verify the staged name set is exactly the four Task 11
paths below. Do not stage earlier Task 1–10 files through a package/schema
glob.

~~~powershell
git add tests/test_capability_reproduction.py tests/test_capability_conformance.py tests/test_maintainability.py .github/workflows/ci.yml
if (@(git diff --cached --name-only).Count -ne 4) { throw 'Task 11 staged scope is not exact' }
git diff --cached --name-only
git diff --cached --check
git commit -m "test: close M4 ontology conformance gates"
~~~

Do not label M4 implementation complete merely because this synthetic slice
passes. Real M3 Requirement admissibility, real Capability definition review,
real mapping, and M5 publication remain separate authority gates.

## Implementation dependency graph

The task dependencies are:

~~~text
Task 1: stable nucleus and reference identity
    ↓
Task 2: typed dimensions and claim digest
    ↓
Task 3: definitions, lifecycle, Capability review
    ↓
Task 4: SOURCE_REQUIREMENT_ADMISSIBILITY
    ↓
Task 5: links and mapping dispositions
    ↓
Task 6: composition and evolution
    ↓
Task 7: frozen M3 input and Requirement-set digest
    ↓
Task 8: manifest, build, validation, publication
    ├──────────────→ Task 9: candidate grouping/worklists
    └──────────────→ Task 10: reports, CLI, resources
                             ↓
                    Task 11: conformance and CI closure
~~~

Task 9 may read the Task 7 input seam and Task 2 dimension registry. Task 10
may begin after Task 8 has a validated synthetic artifact. Task 11 is the only
task that modifies CI and maintainability integration.

## Scope gates and forbidden transitions

The following transitions are never implicit:

~~~text
M3 PROPOSED Requirement
    ↛ M2 ACCEPTED
    ↛ M4 ACTIVE link without SRA or terminal M2 acceptance

candidate cluster
    ↛ Capability definition
    ↛ accepted review
    ↛ ACTIVE lifecycle

M3 UNRESOLVED_ANALYSIS without bundle
    ↛ negative authority
    ↛ synthetic Requirement
    ↛ mapping decision row

M4 mapping
    ↛ engine support
    ↛ Manafold, Forge, or XMage compatibility
    ↛ M5 completion by itself

M4 implementation
    ↛ real 38,740-card build
    ↛ M6 semantic closure
    ↛ M7 interaction analysis
~~~

The current five M3 draw_cards Requirements remain data-free in this plan.
Synthetic tests may exercise the complete SRA route, but no current real
Requirement receives an admissibility record, Capability link, or active
Capability definition as part of this plan.

## Plan self-review checklist

Before any implementation authorization, review this plan against the frozen
design:

~~~text
family nucleus versus versioned claim is covered by Tasks 1–2
non-cyclic review and SRA identity are covered by Tasks 3–4
M3-to-M5 authority bridge is covered by Task 4
exact links, stale detection, ambiguity, and outliers are covered by Task 5
composition, dependencies, cycles, and evolution are covered by Task 6
exact M3 binding and Requirement-set digest are covered by Task 7
manifest DAG, atomic publication, and reproduction are covered by Task 8
candidate clustering and batch worklists are covered by Task 9
derived reports and M5/Explorer status separation are covered by Task 10
maintainability, security, packaging, and CI are covered by Task 11
real Requirement mapping and Capability activation remain unauthorized
~~~

The plan contains no production implementation authorization, no real
Capability data, no real Requirement mapping, and no PR or merge action.
