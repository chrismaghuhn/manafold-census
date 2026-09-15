# Manafold Census — M5 Census 0.1 Design Specification

Date: 2026-09-15
Repository: https://github.com/chrismaghuhn/manafold-census
Status: DESIGN CONTENT APPROVED / M5-00 RECONCILED / READY TO FREEZE

~~~text
M5_DESIGN_AMENDMENT_01              = APPLIED
M5_DESIGN_AMENDMENT_02              = APPLIED
M5_DESIGN_TEXT_CONSISTENCY_REPAIR   = APPLIED
M5_DESIGN_CONTENT_REVIEW            = PASS
M5_DESIGN_CONTENT                   = APPROVED
M5_00_AUTHORIZED                    = YES
M5_DESIGN_SPECIFICATION             = READY_TO_FREEZE_AFTER_M5_00
M5_00_STATUS                        = PASS
M5_IMPLEMENTATION_AUTHORIZED        = NO
M5_REAL_INPUT_CAMPAIGN_STARTED     = NO
M5_REAL_M4_BUILD_STARTED           = NO
M5_CENSUS_BUNDLE_CREATED           = NO
M5_EXPLORER_STARTED                = NO
M5_RELEASE_CREATED                 = NO
M6_STARTED                         = NO
PR_AUTHORIZED                      = NO
MERGE_AUTHORIZED                   = NO
~~~

This specification incorporates the design review repairs for the first
Manafold Census 0.1 end-to-end release. It defines architecture, contracts,
ownership, implementation decomposition, validation, and release gates. It
does not implement production code, create real M4 review records, map a real
Requirement, activate a real Capability, run a real global M4 build, create a
bundle, create the Explorer, build an executable, create a branch, create a
PR, or merge anything.

The current local checkout is intentionally not changed except for this
design document.

## 0. Normative repair record

This revision incorporates the design review findings without changing the
frozen M4 contracts:

1. SourceRequirementAdmissibilityV1 has exactly one authoritative decision
   per Requirement and current authority context. Additional human review is
   non-authoritative evidence unless a future M4 authority evolution defines
   quorum semantics.
2. The input lock uses expected_m4_requirement_set_digest. The digest is
   derived by the frozen M4 identity contract from the exact M3 manifest and
   Requirement wires; it is not M3-owned.
3. CensusInputLockV1 contains no parent Census release identity. Release
   lineage has one owner: CensusBundleManifestV1.
4. Human-reviewed M4 records have a durable source of truth in the small,
   version-controlled reviewed/m4/census-0.1 authority package.
5. The existing synthetic-only M4 CLI remains unchanged. M5 uses a separate
   explicit real-M4 orchestration entry point and starts the real M4 chain with
   parent_m4_manifest_sha256 = null.
6. Query results expose a closed semantic_state in CardSemanticView, so an
   empty Capability collection cannot be mistaken for semantic absence.
7. The recommendation names frozen M4 machinery plus future reviewed real
   records, not existing real records.
8. Windows executable byte parity is initially EXPERIMENTAL; authoritative
   Census bytes, report/index bytes, functional rebuild, and Windows smoke
   remain hard gates.
9. An UNRESOLVED_ANALYSIS record with a persisted Requirement bundle remains
   eligible for normal frozen M4 validation, review, and mapping. Only an
   unresolved record without a persisted bundle contributes no Requirement or
   M4 mapping row.
10. CardSemanticView applies explicit SemanticStateV1 precedence: the M3
    outcome UNRESOLVED_ANALYSIS or NO_REQUIREMENTS_APPLICABLE dominates mapping
    completeness.
11. authority_package_digest is a domain-separated digest of an explicit
    projection that excludes the digest field itself.
12. The published M4 snapshot must have exact canonical record-set parity with
    the reviewed authority package after flat/sharded representation is
    normalized.
13. Negative conformance cases contain only an attempted mapping for an
    unresolved record without a persisted Requirement; valid unresolved
    records with persisted Requirements are positive conformance cases.
14. Explorer text distinguishes unresolved records without a bundle from
    unresolved records with a persisted Requirement bundle.

## 1. Executive decision

~~~text
M5_DESIGN_RECOMMENDATION =
  Frozen M1/M3 input artifacts
  + existing frozen M4 authority machinery and contracts
  + new human-reviewed real M4 authority records
  + explicit real-M4 M5 orchestration
  + self-contained digest-bound Census bundle
  + derived canonical reports and indexes
  + deep read-only query module
  + Rich CLI/TUI consumer
  + PyInstaller onedir Windows distribution
~~~

Census 0.1 means:

> Every card in the exact pinned source corpus is accounted for structurally
> and analytically. Requirement and Capability authority exists only where the
> frozen M2/M4 contracts and explicit human review justify it. Uncertainty is
> visible. The resulting data product is deterministic, auditable, portable,
> and usable offline.

The architecture is:

~~~text
pinned SourceLock
    ↓
frozen M1 structural artifact
    ↓
frozen M3 analysis artifact
    ↓
small persisted reviewed M4 authority package
    ↓
explicit M5 real-M4 orchestration
    ↓
M4 ontology snapshot
    ↓
CensusBundleManifestV1
    ↓
self-contained Census 0.1 bundle
    ↓
derived reports and indexes
    ↓
read-only query module
    ↓
offline Explorer
    ↓
Windows executable
~~~

The corrected recommendation is deliberately not “existing real M4 authority
records.” M4 was closed with synthetic-only machinery. M5 introduces the first
new real M4 authority records through the reviewed authority package described
in Section 7.

## 2. Verified repository state

The remote branch was checked before authoring this specification.

| Fact | Verified value | Authority |
| --- | --- | --- |
| Remote main | 6a9cfe916c43e37499fdcfd7335fc473d73fff9f | live git ls-remote |
| Local checkout | 576c9414e8db9682151a8884056835fae1ffc061 | local HEAD |
| Local worktree | clean before this document | git status |
| M4 merge | PR #16 merged into main | GitHub |
| M4 merge commit | 6a9cfe916c43e37499fdcfd7335fc473d73fff9f | PR #16 |
| M4 real authority | not yet created | PR #16 delivery notes |
| M4 global real build | not yet run | PR #16 delivery notes |
| Issue #7 | closed, body historically says M4 = PLANNED | GitHub |
| Issue #8 | open, M5 = CENSUS 0.1 RELEASE TARGET | GitHub |
| Issue #12 | open, Explorer child deliverable | GitHub |
| Issue #2 | open, stale M0–M5 roadmap text | GitHub |
| Issue #9 | open, stale M6 = POST_V1 wording | GitHub |

PR #16 explicitly records synthetic-only M4 closure and no real Requirement
admission, real Capability activation, or 38,740-card M4 build:
https://github.com/chrismaghuhn/manafold-census/pull/16

Issue #8 is the current M5 scope authority:
https://github.com/chrismaghuhn/manafold-census/issues/8

The repository convention remains suitable for M5: small locks and schemas are
versioned, generated corpus outputs are outside Git, live acquisition is
explicit, and ordinary CI is offline:
https://github.com/chrismaghuhn/manafold-census/blob/6a9cfe916c43e37499fdcfd7335fc473d73fff9f/README.md

## 3. Authority reconciliation

### 3.1 M5 authority order

~~~text
1. Frozen M0–M4 contracts and exact artifact identities
2. Issue #8 for the current M5 scope and release meaning
3. This specification after independent approval and freeze
4. CensusInputLockV1 for one exact M1/M3 input snapshot
5. Existing M4 contracts and the persisted reviewed authority package
6. Issue #12 as a child deliverable subordinate to Issue #8
7. Reconciled roadmap and follow-up wording in Issues #2 and #9
8. Reports, indexes, query results, Explorer screens, and prose
   never override authoritative artifacts
~~~

The frozen upstream contracts include M1 source identity, M2 Requirement
identity and resolution, M3 outcome semantics, and the M4 typed Capability
dimensions, links, reviews, and activation gates. M5 consumes these contracts;
it does not redesign them.

### 3.2 Required roadmap changes before implementation

Issue #2 currently still describes M5 as a V1 target and M6 as post-V1.
Issue #9 still uses V1 as the M6 predecessor. Issue #12 still labels the
Explorer as required for V1.

Before M5 implementation:

~~~text
Issue #2:
  M5 = Census 0.1 end-to-end vertical slice
  M6 = first post-0.1 semantic coverage expansion
  1.0 = later evidence-based broad Census target

Issue #9:
  M6 = POST_0.1_SEMANTIC_EXPANSION
  M6 is not a retroactive M5 gate

Issue #12:
  M5.X is required for Census 0.1
  replace remaining V1 gate wording with 0.1 wording

Issue #7:
  preserve the closed M4 body as historical evidence
  do not silently rewrite it
~~~

The exact milestone numbers remain unchanged.

Issue #2 is stale in its current body:
https://github.com/chrismaghuhn/manafold-census/issues/2

Issue #9 is also stale in its current POST_V1 framing:
https://github.com/chrismaghuhn/manafold-census/issues/9

Issue #12 still says M5.X = REQUIRED FOR CENSUS V1:
https://github.com/chrismaghuhn/manafold-census/issues/12

The design decision is complete. Repository-level roadmap reconciliation is
now performed by M5-00 as recorded below. No implementation follows
automatically from that reconciliation.

### 3.3 M5-00 completion

On 2026-09-15 the current bodies of Issues #2, #9, and #12 were updated and
read back successfully:

~~~text
Issue #2  → M5 = Census 0.1 vertical slice; M6 = post-0.1 semantic expansion
Issue #9  → M6 = POST_0.1_SEMANTIC_EXPANSION; not a retroactive 0.1 gate
Issue #12 → M5.X is required for Census 0.1
~~~

Issue #7 remains unchanged as historical M4 evidence. README.md and
ARCHITECTURE.md contain no conflicting old M5/V1 roadmap declaration, so M5-00
does not modify them. Their detailed M5 architecture documentation remains a
later documentation concern within the staged implementation work.

~~~text
M5_AUTHORITY_RECONCILIATION = PASS
M5_00_STATUS                = PASS
M5_DESIGN_SPECIFICATION     = READY_TO_FREEZE_AFTER_M5_00
M5_IMPLEMENTATION_AUTHORIZED = NO
~~~

## 4. Domain model and terminology

| Term | M5 meaning | Explicit non-meaning |
| --- | --- | --- |
| Oracle identity | Exact source-bounded identity from the pinned corpus | Every historical printing or every possible card |
| Structural record | M1 source-fact projection | Semantic interpretation |
| Analysis outcome | M3 closure state for one source identity | Requirement review or Capability review |
| Requirement | One source-scoped M2 semantic need assertion | Reusable Capability |
| Capability | Reviewed reusable M4 semantic abstraction | Engine implementation or engine support |
| Reviewed authority package | Persisted source of human-reviewed M4 records | Worklist or generated suggestion |
| M4 snapshot | Validated publication of M4 records for one exact M3 input | One mapping per card |
| Census bundle | Release-bound consumer product | New semantic authority |
| Unresolved analysis | Explicit inability to close the semantic analysis; a nonempty M2 bundle may still be present | Does not mean no Requirement, no Capability, or negative authority |
| Active mapping | Validated, reviewed M4 link included by an accepted mapping decision | Complete semantic understanding of a card |
| Mapped subset | Cards or Requirements with active M4 mappings | Representative global Magic distribution |

The central invariant is:

~~~text
100% cards accounted for
!=
100% cards semantically understood
~~~

The query and Explorer layers must preserve this distinction in their return
types, not only in their text labels.

## 5. M5 architecture sequence

~~~text
M5-00  Roadmap and authority reconciliation
   ↓
M5-01  Census 0.1 design freeze
   ↓
M5-02  Frozen M1/M3 input provisioning and CensusInputLockV1
   ↓
M5-03  First real Requirement/Capability review campaign
   ↓
M5-04  Explicit real M4 global-snapshot build
   ↓
M5-05  CensusBundleManifestV1 and atomic bundle publication
   ↓
M5-06  Derived global reports and indexes
   ↓
M5-07  Validated read-only query layer
   ↓
M5-08  Card lookup and Capability browser query model
   ↓
M5-09  Deck parser and deck analysis
   ↓
M5-10  Offline Explorer
   ↓
M5-11  Windows standalone packaging
   ↓
M5-12  Release conformance and reproduction
   ↓
Manafold Census 0.1
~~~

The sequence is an authority sequence. A later consumer must not manufacture
an earlier authority layer.

## 6. CensusInputLockV1

### 6.1 Ownership

CensusInputLockV1 owns only the exact inputs consumed by the M5/M4 build:

~~~text
SourceLock
M1 structural snapshot
M3 analysis snapshot
M4 contract compatibility
expected population counts
~~~

It does not own Census release ancestry. Parent release lineage belongs only to
CensusBundleManifestV1.

The corrected field is:

~~~text
expected_m4_requirement_set_digest
~~~

It is not an M3-owned digest. The frozen M4 identity contract derives the
Requirement-set digest from the exact locked M3 manifest and exact Requirement
wires. The M4 ontology manifest owns the corresponding persisted
requirement_set_digest.

### 6.2 Fields

~~~text
schema
lock_version

source_lock_digest
source_lock_file_sha256

m1_structural_manifest_sha256
m1_structural_aggregate_digest

m3_analysis_manifest_sha256
m3_record_identity_set_digest
m3_record_index_digest
m3_trace_index_digest

expected_m4_requirement_set_digest

m1_structural_schema
m3_analysis_schema
m2_requirement_schema
m2_bundle_schema
m4_ontology_schema
m4_dimension_registry_version

expected_oracle_identity_count
expected_structural_record_count
expected_analysis_record_count
expected_requirements_produced_card_count
expected_no_requirements_applicable_count
expected_unresolved_analysis_count
expected_requirement_count
~~~

There is no parent_census_release_id in CensusInputLockV1.

### 6.3 Example wire

~~~json
{
  "schema": "census.census-input-lock.v1",
  "lock_version": 1,
  "source_lock_digest": "<source-lock-domain-digest>",
  "source_lock_file_sha256": "<raw-source-lock-sha256>",
  "m1_structural_manifest_sha256": "<m1-manifest-sha256>",
  "m1_structural_aggregate_digest": "<m1-aggregate-digest>",
  "m3_analysis_manifest_sha256": "<m3-analysis-manifest-sha256>",
  "m3_record_identity_set_digest": "<m3-identity-set-digest>",
  "m3_record_index_digest": "<m3-record-index-digest>",
  "m3_trace_index_digest": "<m3-trace-index-digest>",
  "expected_m4_requirement_set_digest": "<m4-requirement-set-digest>",
  "m1_structural_schema": "census.structural-card.v1",
  "m3_analysis_schema": "census.card-analysis.v1",
  "m2_requirement_schema": "census.semantic-requirement.v1",
  "m2_bundle_schema": "census.semantic-requirement-bundle.v1",
  "m4_ontology_schema": "census.capability-ontology.v1",
  "m4_dimension_registry_version": "1",
  "expected_oracle_identity_count": 38740,
  "expected_structural_record_count": 38740,
  "expected_analysis_record_count": 38740,
  "expected_requirements_produced_card_count": 5,
  "expected_no_requirements_applicable_count": 0,
  "expected_unresolved_analysis_count": 38735,
  "expected_requirement_count": 5
}
~~~

The numeric values are an example based on the currently recorded M3 baseline.
They are not permanent constants and become authoritative only after the lock
has been validated against the exact artifacts.

### 6.4 Provisioning

The small lock may be versioned in Git after review. The large generated
artifacts are provisioned separately:

~~~text
small input lock              → Git
M1/M3 generated artifacts     → immutable release assets or durable object store
pinned compressed source      → separate durable asset for full rebuilds
local artifact cache          → content-addressed and digest-keyed
~~~

A separate provisioning.json may record asset names, URLs, toolchain details,
and retrieval instructions. It is not input authority and cannot select a
different artifact when the expected digest does not match.

No latest-directory, timestamp selection, branch-head semantic identity, or
silent fallback is allowed.

### 6.5 Validation

The lock validator must:

1. read canonical JSON only;
2. verify the SourceLock file digest and semantic SourceLock digest;
3. validate the complete M1 output independently;
4. compare the M1 structural manifest SHA and aggregate digest;
5. verify the exact M3 analysis manifest SHA;
6. run the existing M3 closure validation against the selected M1 and
   SourceLock;
7. compare M3 source-lock, structural-manifest, schema, and index identities;
8. recompute the M4-owned Requirement-set digest from the exact M3 manifest and
   Requirements;
9. compare all expected counts;
10. reject any missing, extra, duplicate, stale, or noncanonical artifact.

### 6.6 Reuse versus rerun

Release-authoritative M5 path:

~~~text
consume frozen M1/M3 artifacts
~~~

Optional reproduction path:

~~~text
rebuild M1/M3 from the exact pinned source bytes
→ compare resulting manifest identities
~~~

A rerun that produces different bytes creates a different input snapshot. It
must not rewrite the existing lock or release.

## 7. Persisted reviewed M4 authority package

### 7.1 Source of truth

The real human-reviewed M4 records live before the build in a small,
version-controlled authority package:

~~~text
reviewed/m4/census-0.1/
├── authority-manifest.json
├── capability-definitions.jsonl
├── review-authority.jsonl
├── capability-relations.jsonl
├── requirement-admissibility.jsonl
├── links.jsonl
├── mapping-decisions.jsonl
└── evolution.jsonl
~~~

This package is the source of human-reviewed M4 authority.

The generated M4 output is a publication derived from this package and the
locked M3 corpus. It must not become the retrospective source of its own
inputs.

### 7.2 Authority manifest

authority-manifest.json is a small M5 control artifact. It binds:

~~~text
schema
campaign_id
m3_analysis_manifest_sha256
m4_requirement_set_digest
selected_requirement_ids
record-file descriptors
review policy
authority package digest
~~~

The record files contain only existing frozen M4 wire types. The package does
not introduce a second semantic representation.

The package manifest is not a Capability claim. It is release/control metadata
that prevents scope drift and supports reproducibility.

The persisted authority_package_digest is non-self-referential:

~~~text
authority_package_digest =
  domain_digest(
    "census.m5-m4-authority-package.v1",
    {
      schema,
      campaign_id,
      m3_analysis_manifest_sha256,
      m4_requirement_set_digest,
      selected_requirement_ids,
      record_file_descriptors,
      review_policy
    }
  )
~~~

The digest field itself is excluded from this projection. The projection uses
the canonical, sorted descriptor set and contains no timestamps, absolute
paths, filesystem order, or package-manifest self-hash. The raw SHA-256 of the
complete canonical authority-manifest.json may also be recorded externally,
but it is a separate file digest and is not substituted for the domain
identity above.

### 7.3 Record ownership

| File | Record type | Role |
| --- | --- | --- |
| capability-definitions.jsonl | CapabilityDefinitionV1 | Capability definition |
| review-authority.jsonl | CapabilityReviewRecordV1 | Definition/link/mapping/evolution reviews |
| capability-relations.jsonl | existing relation type | Capability relations |
| requirement-admissibility.jsonl | SourceRequirementAdmissibilityV1 | M4 admission decision |
| links.jsonl | RequirementCapabilityLinkV1 | exact Requirement mapping |
| mapping-decisions.jsonl | RequirementMappingDecisionV1 | per-Requirement disposition |
| evolution.jsonl | existing evolution type | version/evolution events |

Each file is canonical JSONL, sorted by its existing M4 sort key, with a final
line feed. The authority manifest records raw SHA-256, byte length, and count
for every file.

### 7.4 Review multiplicity and the SRA correction

The frozen M4 contract permits multiple CapabilityReviewRecordV1 records for a
review subject, provided there is no accepted/rejected conflict and the
referenced review is exact.

SourceRequirementAdmissibilityV1 is different. Under the frozen contract:

~~~text
one Requirement
+ one current authority context
→ exactly one authoritative SRA decision record
~~~

The first Census 0.1 campaign therefore requires:

~~~text
exactly one SRA decision record per selected Requirement
~~~

The record may be accepted or rejected. Two accepted SRA records for the same
Requirement are invalid. Accepted plus rejected is also invalid.

Multiple people may still participate:

- one stable reviewer_id is the authoritative SRA reviewer;
- a stable committee/session identity may be used if explicitly governed;
- additional comments or review notes remain non-authoritative evidence;
- additional reviewers must not be encoded as extra SRA decisions;
- real quorum semantics require a future M4 authority evolution.

This is a frozen-contract constraint, not an M5 implementation preference.

### 7.5 First campaign workflow

1. Validate CensusInputLockV1.
2. Generate a deterministic worklist for exactly the selected five Requirement
   IDs.
3. Verify each Requirement's exact wire, M2 review, resolution, evidence, and
   source identity.
4. Record exactly one authoritative SRA decision per selected Requirement.
5. Generate Capability candidate clusters as proposals only.
6. Human-authored Capability definitions use the existing typed M4 claim and
   dimension registry.
7. Create definition review records.
8. Create exact Requirement-to-Capability links with typed bindings.
9. Create link review records.
10. Create one mapping decision for every persisted Requirement in the M3 set.
11. Run existing M4 validation and activation eligibility.
12. Publish the reviewed authority package only after all records are
    canonical, scope-bound, and digest-validated.

The current five Requirements may support a reusable generic Capability. The
campaign must not pre-authorize that result.

Campaign scope is Requirement-based, not card-outcome-based. An
UNRESOLVED_ANALYSIS card with a nonempty persisted M2 Requirement bundle may
contribute those exact Requirements to the campaign. The unresolved card state
remains unchanged, and any mapping is attached to the persisted Requirement,
not to an assertion that the whole card is semantically closed.

### 7.6 Scope protection

The authority-package validator rejects:

~~~text
Requirement ID not in the locked M3 set
selected Requirement ID outside the explicit campaign scope
M4 record bound to a different M3 manifest
duplicate SRA decision
active link without the required review path
active definition without activation eligibility
mapping for an unresolved card without a persisted Requirement bundle
M2 status mutation
candidate-only artifact presented as active authority
~~~

An UNRESOLVED_ANALYSIS record without a persisted Requirement bundle contributes
no Requirement and receives no M4 mapping row. An UNRESOLVED_ANALYSIS record
with a nonempty persisted Requirement bundle contributes each exact Requirement
to the normal frozen M4 input set; those Requirements remain eligible for the
same validation, review, admissibility, and mapping path as any other persisted
Requirement. This does not change the card-level unresolved outcome.

## 8. Explicit real-M4 orchestration

The existing M4 command layer remains synthetic-only. It must not be
generalized from:

~~~text
m4-build --synthetic
~~~

to an unrestricted arbitrary-input command.

M5 introduces a separate explicit orchestration seam, for example:

~~~text
python -m manafold_census.cli m5-m4-build
  --input-lock <CensusInputLockV1>
  --authority-package <reviewed/m4/census-0.1>
  --output <m4-output>
~~~

The exact CLI spelling may be finalized during M5-02, but the separation is
normative.

The M5 entry point:

1. validates the input lock;
2. loads the persisted authority package;
3. loads the locked M3 Requirement corpus;
4. verifies the authority package's M3 and M4 Requirement-set identities;
5. calls the existing frozen build_reference_m4 seam;
6. validates the resulting M4 snapshot independently;
7. writes no output until validation succeeds.

The first real M4 snapshot must have:

~~~text
parent_m4_manifest_sha256 = null
~~~

Synthetic M4 artifacts can never be parents of the real M4 ontology history.
Later real M4 snapshots may form a real M4 parent chain.

## 9. Real M4 global snapshot

A real M4 snapshot is not a mapping for every card.

It contains:

~~~text
all locked M3 analysis records as context
all persisted M2 Requirements from that M3 snapshot
only reviewed/admissible M4 mappings
explicit non-mapped decisions for persisted Requirements where required
no M4 rows for cards with no persisted Requirement bundle
no synthesized Requirements for UNRESOLVED_ANALYSIS
persisted Requirements from UNRESOLVED_ANALYSIS bundles remain eligible for M4
mapping; the card outcome remains UNRESOLVED_ANALYSIS
~~~

The M3 outcome vocabulary remains:

~~~text
REQUIREMENTS_PRODUCED
NO_REQUIREMENTS_APPLICABLE
UNRESOLVED_ANALYSIS
~~~

The M4 mapping vocabulary remains the frozen set:

~~~text
MAPPED
UNMAPPED
AMBIGUOUS
OUTLIER
INSUFFICIENT_EVIDENCE
~~~

UNRESOLVED_ANALYSIS and M4 OUTLIER are different states. An unresolved card may
still have persisted Requirements and active mappings for the subset of its
semantic analysis that M3 did close.

### 9.1 Global counters

| Counter | Definition |
| --- | --- |
| TOTAL_ORACLE_IDENTITIES | unique Oracle IDs in the locked SourceLock |
| STRUCTURAL_RECORD_COUNT | validated M1 records |
| CARD_ANALYSIS_RECORD_COUNT | validated M3 records |
| CARDS_WITH_REQUIREMENTS | distinct Oracle IDs with a nonempty M3 bundle |
| REQUIREMENT_COUNT | persisted M2 Requirement count |
| NO_REQUIREMENTS_APPLICABLE | M3 explicit negative-authority outcomes |
| UNRESOLVED_ANALYSIS | M3 unresolved outcomes |
| CARDS_WITH_ACTIVE_CAPABILITY_MAPPINGS | distinct Oracle IDs with active validated M4 links |
| ACTIVE_REQUIREMENT_CAPABILITY_LINK_COUNT | active links included by mapped decisions |
| MAPPING_DECISION_COUNT | M4 decisions over persisted Requirements |
| CAPABILITY_DEFINITION_COUNT_BY_LIFECYCLE | counts by M4 lifecycle |

No generic coverage scalar is emitted.

## 10. CensusBundleManifestV1

### 10.1 Role

CensusBundleManifestV1 is the single owner of Census release identity and
Census release lineage.

CensusInputLockV1 does not contain parent release information.

The bundle manifest binds:

~~~text
source lock
M1 manifest
M3 manifest
M4 manifest
reviewed M4 authority package
population assertions
schema compatibility
parent Census release, if any
~~~

### 10.2 Proposed wire

~~~json
{
  "schema": "census.census-bundle-manifest.v1",
  "census_release_version": "0.1.0",
  "census_release_id": "censusrel_<domain-digest>",
  "source_lock_digest": "<source-lock-domain-digest>",
  "authoritative_components": [
    {
      "role": "source_lock",
      "manifest_path": "inputs/source-lock.json",
      "sha256": "<raw-sha256>",
      "byte_length": 1234,
      "schema": "census.source-lock.v1"
    },
    {
      "role": "m1",
      "manifest_path": "inputs/m1/structural-index-manifest.json",
      "sha256": "<raw-sha256>",
      "byte_length": 2345,
      "schema": "census.structural-card-index-manifest.v1",
      "aggregate_digest": "<m1-aggregate-digest>"
    },
    {
      "role": "m3",
      "manifest_path": "inputs/m3/analysis-manifest.json",
      "sha256": "<raw-sha256>",
      "byte_length": 3456,
      "schema": "census.analysis-manifest.v1"
    },
    {
      "role": "m4_authority",
      "manifest_path": "inputs/m4-authority/authority-manifest.json",
      "sha256": "<raw-sha256>",
      "byte_length": 4567,
      "schema": "census.m5-m4-authority-package.v1"
    },
    {
      "role": "m4",
      "manifest_path": "inputs/m4/m4-ontology-manifest.json",
      "sha256": "<raw-sha256>",
      "byte_length": 5678,
      "schema": "census.m4-ontology-manifest.v1"
    }
  ],
  "population": {
    "oracle_identity_count": 38740,
    "structural_record_count": 38740,
    "analysis_record_count": 38740,
    "requirement_count": 5,
    "requirements_produced_card_count": 5,
    "no_requirements_applicable_count": 0,
    "unresolved_analysis_count": 38735
  },
  "schemas": {
    "structural_record": "census.structural-card.v1",
    "analysis_record": "census.card-analysis.v1",
    "requirement": "census.semantic-requirement.v1",
    "requirement_bundle": "census.semantic-requirement-bundle.v1",
    "m4_manifest": "census.m4-ontology-manifest.v1"
  },
  "compatibility": {
    "bundle_format_major": 1,
    "query_contract": "census.query.v1",
    "minimum_explorer_version": "0.1.0"
  },
  "parent_census_release_id": null
}
~~~

The numeric values are illustrative and are authoritative only after the
locked artifacts have been validated.

### 10.3 Digest rules

~~~text
manifest_sha256 =
  raw SHA-256 of canonical_json_bytes(full_manifest)
~~~

The manifest does not contain its own SHA.

~~~text
census_release_id =
  "censusrel_" +
  domain_digest(
    "census.census-release-id.v1",
    identity_projection_without_release_id
  )
~~~

The identity projection includes authoritative component descriptors,
population assertions, schemas, compatibility, release version, source-lock
digest, and parent_census_release_id.

It excludes:

~~~text
reports
indexes
metadata
toolchain diagnostics
timestamps
absolute paths
~~~

Reports and indexes bind to the resulting manifest_sha256 but do not change
the authoritative Census release identity.

### 10.4 Validation and publication

A bundle validator must:

- read canonical manifest bytes;
- validate all component descriptors;
- validate nested M1, M3, authority-package, and M4 manifests;
- verify every descriptor SHA, byte length, and record count;
- verify cross-layer source and Requirement-set identities;
- verify authority_package_digest using its non-self-referential projection;
- compare the reviewed authority package and published M4 snapshot after
  canonical record normalization:
  - authority definitions = published capabilities;
  - authority reviews = published review-authority records;
  - authority relations = published capability-relations records;
  - authority admissibility = published requirement-admissibility records;
  - authority links = published sharded link records;
  - authority mapping decisions = published sharded decision records;
  - authority evolution = published evolution records;
- compare parsed canonical record sets, not physical file layout, because the
  published links and mapping decisions are sharded;
- verify no authority package record is outside the locked M3 corpus;
- reject unknown required schema versions;
- reject missing required components;
- reject path traversal and unexpected files;
- reread the staged bundle independently.

Publication is atomic. No final Census manifest exists after a failed build.

## 11. Physical bundle layout

~~~text
manafold-census-0.1.0/
├── census-manifest.json
├── inputs/
│   ├── source-lock.json
│   ├── m1/
│   │   ├── structural-index-manifest.json
│   │   └── records/
│   │       ├── 0.jsonl
│   │       ├── ...
│   │       └── f.jsonl
│   ├── m3/
│   │   ├── analysis-manifest.json
│   │   ├── records/
│   │   │   ├── 0.jsonl
│   │   │   ├── ...
│   │   │   └── f.jsonl
│   │   └── trace/
│   │       ├── 0.jsonl
│   │       ├── ...
│   │       └── f.jsonl
│   ├── m4-authority/
│   │   ├── authority-manifest.json
│   │   ├── capability-definitions.jsonl
│   │   ├── review-authority.jsonl
│   │   ├── capability-relations.jsonl
│   │   ├── requirement-admissibility.jsonl
│   │   ├── links.jsonl
│   │   ├── mapping-decisions.jsonl
│   │   └── evolution.jsonl
│   └── m4/
│       ├── m4-ontology-manifest.json
│       ├── capabilities.jsonl
│       ├── review-authority.jsonl
│       ├── capability-relations.jsonl
│       ├── requirement-admissibility.jsonl
│       ├── evolution.jsonl
│       ├── links/
│       └── mapping-decisions/
├── indexes/
│   ├── index-manifest.json
│   ├── cards-by-name.jsonl
│   ├── cards-by-oracle-id.jsonl
│   ├── requirements-by-card.jsonl
│   ├── links-by-requirement.jsonl
│   └── cards-by-capability.jsonl
├── reports/
│   ├── report-index.json
│   ├── census-report.json
│   ├── unresolved-analysis.jsonl
│   └── mapping-review-queue.jsonl
└── metadata/
    ├── README.txt
    └── provisioning.json
~~~

Authoritative files are the Census manifest, source lock, M1/M3 artifacts,
reviewed authority package, and generated M4 snapshot. Reports, indexes, and
metadata are derived or release metadata.

M1/M3/M4 files are copied into the bundle so the Explorer can operate without
hidden external services. The raw compressed source may remain a separate
release asset because the consumer does not need it.

## 12. Reports and indexes

Reports are:

~~~text
DERIVED
RELEASE_BOUND
REGENERABLE
not semantic authority
~~~

The report must state exact integer counts and denominator labels. A mapped
Capability frequency is always identified as a mapped-subset statistic.

Example:

~~~json
{
  "metric": "cards_with_active_capability_mappings",
  "numerator": 5,
  "denominator": 38740,
  "denominator_label": "TOTAL_ORACLE_IDENTITIES"
}
~~~

Required report dimensions include:

~~~text
source coverage
structural coverage
analysis-record coverage
Requirement presence
M2 review status
M2 resolution state
M4 admissibility status
M4 mapping disposition
active Capability mapping presence
Capability lifecycle
unresolved analysis
M4 outliers
ambiguities
review queues
mapped-subset Capability frequency
~~~

The report index is derived and binds its descriptors to the Census manifest
SHA. It must never be referenced by the authoritative Census manifest.

## 13. Read-only query layer

The query layer is a deep module. Its small Interface hides manifest
validation, cross-layer joins, index construction, ordering, trace assembly,
and epistemic-state derivation.

Conceptual Interface:

~~~text
open_bundle(path) -> CensusReader

CensusReader:
  metadata()
  search_cards(query)
  resolve_card_name(name)
  get_card(oracle_id)
  get_structural_record(oracle_id)
  get_analysis_record(oracle_id)
  get_card_semantic_view(oracle_id)
  get_capability(capability_ref)
  get_capabilities_for_card(oracle_id)
  get_requirements_for_capability(capability_ref)
  get_cards_for_capability(capability_ref)
  trace_requirement(requirement_id)
  trace_mapping(link_id)
  analyze_deck(deck_input)
~~~

The public card query must return a CardSemanticView, not merely a list of
Capabilities.

Conceptual shape:

~~~text
CardSemanticView:
  oracle_id
  analysis_outcome
  semantic_state
  requirements
  active_capability_mappings
  m2_review_summary
  m4_mapping_summary
  provenance
~~~

semantic_state is a closed query-layer value:

~~~text
ESTABLISHED
PARTIALLY_ESTABLISHED
UNRESOLVED_ANALYSIS
NO_REQUIREMENTS_APPLICABLE
~~~

The state is derived by these normative precedence rules; implementation order
must not decide the result:

~~~text
if analysis_outcome == UNRESOLVED_ANALYSIS:
    semantic_state = UNRESOLVED_ANALYSIS

elif analysis_outcome == NO_REQUIREMENTS_APPLICABLE:
    semantic_state = NO_REQUIREMENTS_APPLICABLE

elif analysis_outcome == REQUIREMENTS_PRODUCED:
    if every persisted Requirement has the required final active mapping:
        semantic_state = ESTABLISHED
    else:
        semantic_state = PARTIALLY_ESTABLISHED
~~~

Interpretation:

- UNRESOLVED_ANALYSIS always wins at card level, even when the record contains
  a nonempty Requirement bundle and every currently persisted Requirement has
  an active mapping.
- NO_REQUIREMENTS_APPLICABLE means explicit M3 negative authority exists and
  has precedence over mapping completeness.
- PARTIALLY_ESTABLISHED means M3 produced a Requirement bundle but one or more
  persisted Requirements lack the required final active mapping because they
  are proposal-only, ambiguous, unmapped, or otherwise non-final.
- ESTABLISHED means M3 produced Requirements and every persisted Requirement
  for the card has the required validated active mapping in this snapshot.

An unresolved card may therefore contain both Requirements and active
Capability mappings. The state remains UNRESOLVED_ANALYSIS because it describes
the completeness of the M3 card analysis, not only the completeness of the
currently persisted M4 subset.

The state does not claim broad Magic understanding.

Query-layer authority limits:

~~~text
may read, validate, join, index, filter, sort, aggregate, and format
may not parse Oracle text semantically
may not create or admit Requirements
may not create or activate Capabilities
may not change mappings
may not execute Magic rules
may not call an LLM
may not use network access
~~~

Invalid bundles fail at open. Unknown IDs return explicit not-found results.
Ambiguous human input returns an explicit ambiguity result.

## 14. Card lookup and Capability browser

Name lookup:

- trim outer whitespace;
- use deterministic case-folded lookup keys;
- collapse lookup whitespace only;
- do not Unicode-normalize source names;
- preserve original source text;
- do not use fuzzy matching;
- never silently select among multiple Oracle identities.

Card detail must expose:

~~~text
card name and Oracle identity
structural facts
M3 analysis outcome
M2 Requirement summaries
M2 review/resolution
M4 admissibility
M4 mapping disposition
active Capability references
Capability lifecycle and review state
typed bindings
source and release provenance
~~~

For UNRESOLVED_ANALYSIS, the Explorer must branch on whether the persisted M3
record contains a Requirement bundle.

Without a persisted bundle, display:

~~~text
UNRESOLVED_ANALYSIS

No persisted Requirement was established for this card in this Census snapshot.

This does NOT mean the card has no semantic requirements or capabilities.
~~~

With a nonempty persisted bundle, display:

~~~text
UNRESOLVED_ANALYSIS

This card has persisted Requirements for the semantic subset shown below,
but the overall card analysis remains unresolved.

Mapped Requirements do NOT imply complete semantic understanding of this card.
~~~

The second form may show active Capability mappings for the persisted subset.
The card-level semantic_state remains UNRESOLVED_ANALYSIS by the precedence
rules in Section 13.

The Capability browser shows:

~~~text
stable family identity
Capability version and claim digest
display name and typed dimensions
Requirement families/kinds
exact linked Requirements
mapped cards
mapped-subset frequency
lifecycle/review state
known exclusions
unresolved areas
Census release identity
~~~

## 15. Deck analysis

Input grammar:

~~~text
file          = strict UTF-8 text, optional BOM only at file start
blank line    = ignored
comment       = leading whitespace followed by '#'
section       = [main] or [sideboard], case-insensitive
entry         = quantity whitespace card-name
quantity      = [1-9][0-9]*
card-name     = nonempty remainder after first whitespace
~~~

Rules:

- no inline comments;
- # inside a card name is preserved;
- quantity per line is at most 1,000,000;
- total cards per section is at most 1,000,000;
- zero and negative quantities are invalid;
- duplicate resolved identities aggregate within a section;
- sideboard remains separate;
- unknown and ambiguous names remain visible;
- no deck legality or Magic rules execution occurs.

The result contains structurally separate:

~~~text
declared card count
resolved card count
unique resolved Oracle identity count
unknown names
ambiguous names
invalid lines
analysis-outcome distribution
M2 review distribution
M4 mapping distribution
established cards
partially established cards
unresolved cards
explicit-negative cards
mapped-subset Capability counts
provenance traces
~~~

Capability aggregation defaults to unique Oracle identities and may additionally
report quantity-weighted counts. It never collapses unresolved cards into an
absence claim.

## 16. Explorer

The Explorer is a presentation-layer consumer:

~~~text
validated Census bundle
    ↓
read-only query layer
    ↓
Rich CLI/TUI presentation
~~~

Recommended technology:

~~~text
argparse command mode
+ Rich rendering
+ small interactive shell over the same query Interface
~~~

Textual, Electron, Qt, web UI, and server infrastructure are deferred.

Suggested commands:

~~~text
explorer info
explorer card search <text>
explorer card show <name-or-oracle-id>
explorer requirement show <requirement-id>
explorer capability list
explorer capability show <capability-ref>
explorer unresolved
explorer trace requirement <requirement-id>
explorer trace mapping <link-id>
explorer deck analyze <file>
explorer shell
~~~

Every view displays:

~~~text
Explorer version
Census release version
Census manifest SHA
source-lock digest
M3 analysis manifest SHA
M4 manifest SHA
semantic coverage limitation
~~~

No semantic claim may exist only in Explorer code.

## 17. Windows standalone packaging

### 17.1 Recommendation

~~~text
canonical Windows distribution =
PyInstaller onedir
+
manafold-census-explorer.exe
+
separate versioned Census bundle
~~~

PyInstaller documents that onedir bundles contain the interpreter and
dependencies in an inspectable directory and that one-folder diagnosis is
simpler. Onefile embeds data and extracts it to a temporary directory at
startup, so it is not the canonical M5 artifact:
https://pyinstaller.org/en/stable/operating-mode.html
https://pyinstaller.org/en/stable/spec-files.html

Nuitka remains a viable future alternative, but adds a compiler/toolchain
requirement and should be evaluated only if evidence justifies it:
https://nuitka.net/user-documentation/user-manual.html

Python zipapp requires a suitable Python runtime and is therefore not the
general standalone Windows target:
https://docs.python.org/3/library/zipapp.html

### 17.2 Separate executable and bundle

The executable must not embed one fixed Census snapshot.

~~~text
manafold-census-explorer.exe
    +
C:\data\manafold-census-0.1.0\
~~~

One executable may load multiple compatible bundles sequentially. It must not
silently merge incompatible bundles.

Compatibility checks include:

~~~text
bundle schema major
query contract major
minimum Explorer version
M4 ontology schema
M4 dimension registry version
supported source/analysis schemas
~~~

Unknown or incompatible versions fail closed.

### 17.3 Reproducibility status

The hard M5 gates are:

~~~text
CENSUS_AUTHORITATIVE_BYTES_PARITY = PASS
REPORT_INDEX_BYTES_PARITY          = PASS
EXPLORER_FUNCTIONAL_REBUILD        = PASS
WINDOWS_PACKAGE_SMOKE              = PASS
~~~

Executable byte parity is initially an evidence target:

~~~text
WINDOWS_EXE_BYTE_PARITY = EXPERIMENTAL
~~~

It may be promoted to a hard gate only after the pinned Windows toolchain
demonstrates stable byte identity. This does not weaken Census data parity.

The build must pin Python, PyInstaller, dependency hashes, Windows builder,
locale, timezone, build root, PYTHONHASHSEED, and SOURCE_DATE_EPOCH.

## 18. Security and information boundaries

The bundle loader must:

~~~text
reject path traversal
reject absolute paths
reject unexpected symlinks/junctions
verify root containment
verify hashes and byte lengths
reject duplicate identities
reject stale cross-layer references
bound total file and record sizes
strictly decode Unicode
escape terminal control characters
disable untrusted Rich markup
~~~

The implementation must not use:

~~~text
eval
exec
pickle
dynamic imports
artifact-selected callbacks
executable expressions
network calls
LLM calls
database calls
Magic rules execution
~~~

The Explorer loads directories in 0.1. Archive extraction is a packaging/
provisioning concern and is not part of the trusted query path.

## 19. Testing and reproduction

Required test families:

~~~text
unit model tests
wire/schema/canonical-byte tests
negative contract tests
M1/M3/M4 cross-layer conformance
authority-package scope tests
SRA multiplicity tests
authority-package to published-M4 record-set parity tests
two-run reproduction
input-order permutation tests
report regeneration parity
index regeneration parity
bundle corruption tests
query state tests
ambiguity tests
deck parser tests
provenance trace tests
offline/no-network tests
Explorer smoke tests
fresh-wheel tests
Windows package smoke tests
synthetic golden bundle tests
~~~

Required negative cases include:

~~~text
wrong source lock
wrong M1 manifest
wrong M1 aggregate
wrong M3 manifest
wrong M4 Requirement-set digest
missing shard
duplicate identity
duplicate Requirement
duplicate SRA
accepted/rejected SRA conflict
stale M4 link
unaccepted review
active link to non-active definition
mapping for unresolved analysis without a persisted bundle
attempted mapping for UNRESOLVED_ANALYSIS without any persisted Requirement
unknown card name
ambiguous card name
negative deck quantity
unknown deck section
corrupt derived index
corrupt report descriptor
symlinked file
path traversal
~~~

Required positive conformance cases include:

~~~text
unresolved record with persisted bundle contributes its Requirements
persisted Requirements from unresolved bundle may map through normal M4 path
card semantic state remains UNRESOLVED_ANALYSIS after such mapping
~~~

The synthetic fixture must prove the query-layer state model. It must include
at least:

~~~text
one established card
one partially established card
one unresolved card
one explicit-negative card
one ambiguous name lookup
one mapped Capability trace
one rejected/corrupt bundle case
~~~

## 20. Repository and module ownership

No monolithic m5.py is allowed.

~~~text
src/manafold_census/
├── release/
│   ├── input_lock.py
│   ├── authority_package.py
│   ├── manifest.py
│   ├── bundle.py
│   ├── validate.py
│   └── publish.py
├── reports/
│   ├── model.py
│   └── build.py
├── query/
│   ├── api.py
│   ├── bundle.py
│   ├── indexes.py
│   ├── cards.py
│   ├── provenance.py
│   └── deck.py
└── explorer/
    ├── cli.py
    ├── render.py
    └── shell.py
~~~

Ownership:

| Responsibility | Owner |
| --- | --- |
| Input lock | release/input_lock.py |
| Reviewed authority package | release/authority_package.py |
| Census manifest | release/manifest.py |
| Bundle publication | release/publish.py |
| Bundle validation | release/validate.py |
| Reports | reports/* |
| Indexes | query/indexes.py |
| Query Interface | query/api.py |
| Card resolution | query/cards.py |
| Provenance | query/provenance.py |
| Deck parsing | query/deck.py |
| Explorer | explorer/* |
| Packaging | packaging/ and CI |
| Final conformance | release validation and dedicated tests |

The query module is the deep module at the consumer seam. The Explorer remains
a thin presentation adapter. Every production Python module stays below the
repository's 500-line maintainability budget.

## 21. Exact staged implementation decomposition

### M5-00 — Roadmap and authority reconciliation

Files likely touched:

~~~text
issue #2
issue #9
issue #12
README.md
ARCHITECTURE.md
~~~

Dependencies:

~~~text
verified remote main
Issue #8
this design
~~~

Allowed:

~~~text
update stale milestone wording
record M5 authority order
~~~

Forbidden:

~~~text
production code
real data
M4 records
M6 implementation
~~~

Exit gate:

~~~text
roadmap wording agrees with Issue #8
Issue #12 is explicitly a Census 0.1 child deliverable
M6 is explicitly post-0.1 semantic expansion
~~~

### M5-01 — Design freeze

Files likely touched:

~~~text
docs/superpowers/specs/2026-09-15-m5-census-0-1-design.md
~~~

Dependencies:

~~~text
M5-00
frozen M4 contracts
design review repairs
~~~

Allowed:

~~~text
independent review
spec corrections
contract freeze
~~~

Forbidden:

~~~text
implementation
real M4 review data
bundle creation
~~~

Exit gate:

~~~text
M5_DESIGN_SPECIFICATION = FROZEN
M5 implementation remains explicitly unauthorized until separately approved
~~~

### M5-02 — Input lock and provisioning

Files likely touched:

~~~text
src/manafold_census/release/input_lock.py
schemas/census-input-lock.v1.schema.json
tests/test_census_input_lock.py
justfile
~~~

Dependencies:

~~~text
frozen M1/M3 artifacts
M5-01
~~~

Allowed:

~~~text
CensusInputLockV1
explicit artifact paths
digest validation
provisioning diagnostics
~~~

Forbidden:

~~~text
latest discovery
timestamp selection
silent M1/M3 rerun
parent Census lineage
M4 review records
~~~

Exit gate:

~~~text
M1/M3 closure and lock cross-check PASS
missing artifact = BLOCKED
mismatch/corruption = FAIL
~~~

### M5-03 — Reviewed authority campaign

Files likely touched:

~~~text
src/manafold_census/release/authority_package.py
schemas/census-m4-authority-package.v1.schema.json
tests/test_census_authority_package.py
reviewed/m4/census-0.1/*
~~~

Dependencies:

~~~text
validated CensusInputLockV1
existing frozen M4 types
~~~

Allowed:

~~~text
exact five-Requirement scope
one SRA decision per Requirement/current authority context
human-reviewed definitions, links, decisions
~~~

Forbidden:

~~~text
multiple SRA decisions for one Requirement
M2 status mutation
mass admission
LLM authority
mapping an unresolved card without a persisted Requirement bundle
~~~

Exit gate:

~~~text
authority package digest and scope PASS
all records canonical and M4-valid
SRA multiplicity PASS
no active record outside scope
~~~

### M5-04 — Real M4 snapshot

Files likely touched:

~~~text
src/manafold_census/cli.py
src/manafold_census/release/m4_orchestration.py
tests/test_m5_m4_build.py
~~~

Dependencies:

~~~text
M5-02
M5-03
existing capability.build.build_reference_m4()
~~~

Allowed:

~~~text
new explicit M5 real-M4 entry point
locked real M3 input
persisted reviewed authority package
~~~

Forbidden:

~~~text
generalizing synthetic M4 CLI
synthetic parent manifest
automatic candidate promotion
bundle/explorer work
~~~

Exit gate:

~~~text
real M4 snapshot reread PASS
parent_m4_manifest_sha256 = null
M4 validators PASS
authority-package to published-M4 record-set parity PASS
~~~

### M5-05 — Census bundle

Files likely touched:

~~~text
src/manafold_census/release/manifest.py
src/manafold_census/release/bundle.py
src/manafold_census/release/publish.py
schemas/census-bundle-manifest.v1.schema.json
tests/test_census_bundle.py
~~~

Dependencies:

~~~text
validated input lock
reviewed authority package
real M4 snapshot
~~~

Allowed:

~~~text
copy exact authoritative inputs
CensusBundleManifestV1
atomic publication
nested manifest validation
~~~

Forbidden:

~~~text
reports/indexes in release identity
self-referential digest
partial final publication
~~~

Exit gate:

~~~text
bundle manifest PASS
bundle reread PASS
authoritative byte descriptors PASS
~~~

### M5-06 — Reports and indexes

Files likely touched:

~~~text
src/manafold_census/reports/model.py
src/manafold_census/reports/build.py
src/manafold_census/query/indexes.py
schemas/census-report.v1.schema.json
schemas/census-index-manifest.v1.schema.json
tests/test_census_reports.py
tests/test_census_indexes.py
~~~

Dependencies:

~~~text
M5-05
~~~

Allowed:

~~~text
derived counters
denominator-labelled ratios
mapped-subset statistics
canonical indexes
~~~

Forbidden:

~~~text
new Requirements
new Capabilities
implicit semantic conclusions
~~~

Exit gate:

~~~text
reports/indexes regenerate byte-identically
all denominators explicit
unresolved and explicit-negative states remain separate
~~~

### M5-07 — Query layer

Files likely touched:

~~~text
src/manafold_census/query/api.py
src/manafold_census/query/bundle.py
src/manafold_census/query/cards.py
src/manafold_census/query/provenance.py
tests/test_census_query.py
~~~

Dependencies:

~~~text
validated Census bundle
M5-06 indexes
~~~

Allowed:

~~~text
read-only deep module
CardSemanticView
SemanticStateV1
cross-layer trace
~~~

Forbidden:

~~~text
bare-list-only card API
semantic parsing
mutations
network
rules execution
~~~

Exit gate:

~~~text
corrupted bundle rejected
unresolved state structurally visible
explicit-negative state structurally visible
trace is complete and deterministic
~~~

### M5-08 — Card and Capability lookup

Files likely touched:

~~~text
src/manafold_census/query/cards.py
src/manafold_census/query/provenance.py
tests/test_card_lookup.py
~~~

Dependencies:

~~~text
M5-07
~~~

Allowed:

~~~text
exact/casefolded name lookup
ambiguity results
card detail and Capability detail views
~~~

Forbidden:

~~~text
fuzzy silent selection
inference from empty Capability arrays
~~~

Exit gate:

~~~text
resolved, unknown, and ambiguous lookup cases PASS
all semantic states are exposed by the return type
~~~

### M5-09 — Deck analysis

Files likely touched:

~~~text
src/manafold_census/query/deck.py
schemas/deck-analysis.v1.schema.json
tests/test_deck_analysis.py
~~~

Dependencies:

~~~text
M5-07
M5-08
~~~

Allowed:

~~~text
simple main/sideboard grammar
quantity aggregation
mapped-subset analysis
~~~

Forbidden:

~~~text
deck legality
Magic rules
unresolved-as-absence claims
~~~

Exit gate:

~~~text
grammar, Unicode, duplicates, ambiguity, limits, and trace tests PASS
~~~

### M5-10 — Explorer

Files likely touched:

~~~text
src/manafold_census/explorer/*
tests/test_explorer_smoke.py
~~~

Dependencies:

~~~text
M5-08
M5-09
~~~

Allowed:

~~~text
Rich CLI/TUI presentation
offline navigation
~~~

Forbidden:

~~~text
semantic claims only in UI code
new parser or Capability logic
~~~

Exit gate:

~~~text
card lookup PASS
Capability browser PASS
deck analysis PASS
provenance and unresolved views PASS
~~~

### M5-11 — Windows packaging

Files likely touched:

~~~text
packaging/explorer.spec
.github/workflows/windows-explorer.yml
tests/test_windows_package_smoke.py
~~~

Dependencies:

~~~text
M5-10
~~~

Allowed:

~~~text
PyInstaller onedir
external bundle loading
compatibility rejection
~~~

Forbidden:

~~~text
fixed Census snapshot embedded in executable
network requirement
~~~

Exit gate:

~~~text
standalone Windows smoke PASS
offline execution PASS
functional rebuild PASS
EXE byte parity remains EXPERIMENTAL unless demonstrated
~~~

### M5-12 — Release conformance

Files likely touched:

~~~text
release conformance scripts
tests/test_m5_release_conformance.py
release evidence documents
~~~

Dependencies:

~~~text
all M5-00 through M5-11 gates
~~~

Allowed:

~~~text
two clean runs
byte parity checks
release candidate evidence
~~~

Forbidden:

~~~text
new semantic coverage
new M4 records
scope expansion
~~~

Exit gate:

~~~text
all hard M5 gates PASS
no required gate is BLOCKED, FAIL, NOT_RUN, or EXPERIMENTAL
release candidate is reproducible and auditable
~~~

## 22. Gate matrix

~~~text
PINNED_SOURCE_COVERAGE             = 100%
STRUCTURAL_RECORD_COVERAGE         = 100%
CARD_ANALYSIS_RECORD_COVERAGE      = 100%
SILENTLY_MISSING_CARDS             = 0
ANALYSIS_STATUS_EXPLICIT           = 100%
UNRESOLVED_EXPLICIT                = PASS
SILENT_GUESSES                     = 0

REAL_M4_SNAPSHOT_BUILD             = PASS
REQUIREMENT_CAPABILITY_LINKS       = AUDITABLE
SRA_MULTIPLICITY                   = PASS
AUTHORITY_PACKAGE_REPRODUCTION     = PASS
AUTHORITY_M4_RECORD_SET_PARITY     = PASS

CENSUS_0_1_BUNDLE                  = PASS
BUNDLE_REREAD                      = PASS
GLOBAL_REPORTS                     = PASS
REPORT_INDEX_BYTES_PARITY          = PASS
QUERY_LAYER                        = PASS

CARD_LOOKUP                        = PASS
CAPABILITY_BROWSER                 = PASS
DECK_ANALYSIS                      = PASS
WHY_TRACE                          = PASS

OFFLINE_EXECUTION                  = PASS
STANDALONE_WINDOWS_EXE             = PASS
EXPLORER_FUNCTIONAL_REBUILD       = PASS
CENSUS_AUTHORITATIVE_BYTES_PARITY = PASS

WINDOWS_EXE_BYTE_PARITY           = EXPERIMENTAL
MODULES_OVER_LOC_BUDGET            = 0

EXPLORER_SEMANTIC_INFERENCE        = 0
EXPLORER_RULES_LOGIC               = 0
~~~

The following are not M5 gates:

~~~text
UNRESOLVED_ITEMS = 0
ALL_CARDS_HAVE_REQUIREMENTS = YES
ALL_CARDS_HAVE_CAPABILITIES = YES
BROAD_MAGIC_SEMANTIC_COVERAGE = YES
GLOBAL_CAPABILITY_DISTRIBUTION_REPRESENTATIVE = YES
~~~

## 23. Open decisions

### MUST DECIDE BEFORE IMPLEMENTATION

~~~text
exact issue wording updates
exact authority-package manifest schema
exact five Requirement IDs after lock validation
authority_id and reviewer policy
durable release-asset retention
exact CensusBundleManifestV1 schema
exact query compatibility matrix
Rich dependency policy
pinned PyInstaller/Python toolchain
deck-analysis schema and limits
~~~

These decisions do not change the repaired normative direction.

### CAN DEFER

~~~text
fuzzy search
archive loading inside Explorer
interactive keybindings
color theme
binary indexes
installer generation
report pagination
Census 1.0 threshold
~~~

### FUTURE RESEARCH

~~~text
SQLite at demonstrated 100k+ scale
GUI consumer
server/API
multi-user review
M6 semantic coverage expansion
M7 higher-order interaction census
engine integration
Magic rules execution
ML or live inference
~~~

## 24. Final design status

~~~text
M5_REPOSITORY_BASE             = 6a9cfe916c43e37499fdcfd7335fc473d73fff9f

M5_AUTHORITY_RECONCILIATION    = PASS
M5_DESIGN_REVIEW_READINESS     = PASS
M5_DESIGN_CONTENT_REVIEW       = PASS
M5_DESIGN_CONTENT              = APPROVED
M5_DESIGN_SPECIFICATION        = READY_TO_FREEZE_AFTER_M5_00
M5_00_AUTHORIZED               = YES
M5_00_STATUS                   = PASS

M5_IMPLEMENTATION_AUTHORIZED   = NO
M5_REAL_INPUT_CAMPAIGN_STARTED = NO
M5_REAL_M4_BUILD_STARTED       = NO
M5_CENSUS_BUNDLE_CREATED       = NO
M5_EXPLORER_STARTED            = NO
M5_RELEASE_CREATED             = NO

M6_STARTED                     = NO
PR_AUTHORIZED                  = NO
MERGE_AUTHORIZED               = NO
~~~

M5_DESIGN_CONTENT_REVIEW = PASS records that the design content and the final
text consistency repairs are complete. M5_DESIGN_SPECIFICATION remains
READY_TO_FREEZE_AFTER_M5_00; the separate M5-01 step formalizes the freeze.

M5_AUTHORITY_RECONCILIATION = PASS records that Issues #2, #9, and #12 now
agree with the Census 0.1 authority. M5-01 is the next documentation-only
step; M5-02 follows it, but no M5 implementation is authorized yet.

This document is the repaired design artifact. No M5 implementation has been
executed, and no M5 implementation is authorized by this specification alone.
