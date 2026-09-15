# Manafold Census — M6 Semantic Expansion Campaign and Scaling Contract

Status: DESIGN_ONLY / M6-01
M6_00_STATUS: FROZEN
M6_01_STATUS: NOT_FROZEN
M6_01_AUTHORIZED: YES

This document freezes the design contract for future M6 semantic-expansion
campaigns. It does not perform semantic expansion, create Requirements,
activate Capabilities, change M4 authority, or define a future wire schema.
Only M6-01 is authorized by this task.

## 1. Purpose

M6 exists to increase useful semantic coverage after the Census 0.1
vertical slice. Its purpose is not to make the historical 0.1 snapshot look
more complete and not to maximize the number of records called Capabilities.

This specification defines:

- the unit of work called a Semantic Expansion Campaign;
- the distinction between candidate groups, Capability Opportunities,
  Requirements, and Capabilities;
- a breadth objective based on distinct reusable semantic nuclei;
- deterministic, denominator-explicit quality metrics;
- the boundary between non-authoritative M6 discovery and existing
  M2/M3/M4 authority;
- the M6-02 inventory and prioritization contract;
- lineage, before/after accounting, stopping rules, and fail-closed
  escalation; and
- the planning sequence through a future broader Census release candidate.

The contract is intentionally implementation-independent. A later task may
mechanically derive schemas and tooling from it, but M6-01 itself changes no
production code or data contract.

## 2. Historical Census 0.1 baseline

Census 0.1 is the immutable historical parent for M6. The baseline was
verified from the merged M5 release evidence and the locked M4 authority
package before this specification was authored.

The M5 release merge is PR #17 at:

~~~text
99b8eea2613c8362a101b59a89f1e30bf6de95a1
~~~

The verified current remote main at M6-01 entry is:

~~~text
1cd637c9863bfcc9313e817868b8ee90c2fa76a6
~~~

The difference is the documentation-only PR #18 README follow-up. It does
not change the M5 semantic snapshot, source lock, schemas, or reviewed
authority package.

### 2.1 Frozen release and source identities

~~~text
CENSUS_RELEASE_VERSION       = 0.1.0
CENSUS_RELEASE_ID             = censusrel_55ff3102f75a64a0a2e1277810e709847803d085c6623ceeec14b7fe8f969e9f
SOURCE_LOCK_DIGEST            = 4767dccbb518b4009c235bb1ce531f509c0923ba0ebe190936c2dc2d14e2d4bd
~~~

### 2.2 Frozen population and semantic counts

~~~text
PINNED_ORACLE_IDENTITIES      = 38,740
STRUCTURAL_RECORDS            = 38,740
ANALYSIS_RECORDS              = 38,740

REQUIREMENTS_PRODUCED_CARDS   = 5
NO_REQUIREMENTS_APPLICABLE    = 0
UNRESOLVED_ANALYSIS           = 38,735

PERSISTED_REQUIREMENTS        = 5
ACTIVE_CAPABILITIES            = 1
ACTIVE_MAPPED_REQUIREMENTS    = 5
~~~

These numbers describe a particular versioned snapshot. They do not mean
that 38,740 cards are semantically understood, that five mapped Requirements
are five fully reviewed cards, or that one active Capability is representative
of global Magic semantics.

### 2.3 Historical immutability

The lineage direction is append-only and versioned:

~~~text
Census 0.1
    ↓
M6 campaign inventory and proposals
    ↓
new versioned M3/M4 semantic snapshots
    ↓
future Census release candidate
~~~

M6 outputs must never rewrite, relabel, delete, or silently reinterpret the
historical 0.1 evidence. A later classification is a new versioned result
with explicit parent lineage. Reports may compare snapshots, but comparison
does not mutate either snapshot.

## 3. Authority boundaries

M6 preserves the existing bottom-up authority chain:

~~~text
M1 source facts
    → M2 source-scoped Requirements
    → M3 per-card analysis and persisted Requirement corpus
    → M4 reviewed Capability definitions and links
    → Census release publication
~~~

The following distinctions remain normative:

| Concept | Owns | Does not own |
|---|---|---|
| M1 source fact | Exact source and structural observation | Semantic interpretation |
| M2 Requirement | One source-scoped semantic need, typed parameters, evidence, derivation, review, and resolution | Cross-card equivalence, Capability identity, or global reuse |
| M3 producer/pattern | Versioned deterministic matching and proposal production | M2 terminal review, semantic truth, or Capability authority |
| M3 analysis outcome | Explicit per-card analysis closure state | M2 review status, M2 resolution state, or proof that unresolved means no Requirement |
| M6 candidate group | Deterministic grouping proposal and worklist input | Requirement, Capability, review result, or active mapping |
| M6 Capability Opportunity | Non-authoritative hypothesis about reuse or a possible new nucleus | Ontology membership, Requirement admission, or activation |
| M4 Capability | Reviewed reusable semantic abstraction with typed claim and lifecycle | Card occurrence, source phrase, producer code, engine support, or rules execution |
| M4 admissibility/review | Explicit authority decisions for exact Requirements, definitions, links, and mappings | Global semantic completeness |
| Derived report | Counts, distributions, ranking, examples, and comparison views | Input authority or semantic truth |

The following invariants are unchanged:

~~~text
Source Fact != Semantic Requirement
Requirement != Capability
Capability != Engine Implementation

Pattern Match != Semantic Authority
Candidate Cluster != Requirement
Capability Opportunity != Capability
Producer != Reviewer

Generated Proposal != Reviewed Result
Mapped != Globally Complete
Imported != Understood
Parsed != Proven

UNRESOLVED is valid
Silent guessing is forbidden
~~~

M6 may consume existing M1/M3/M4 snapshots as read-only inputs. It may not
create a parallel truth state, hidden Explorer semantics, an LLM authority,
an ad-hoc card-support flag, or a manually maintained string tag that acts as
Capability truth.

## 4. Capability-breadth objective

M6 should discover and establish as many genuinely distinct, reusable
semantic Capability families as the evidence supports. That objective is
constrained by quality:

~~~text
useful breadth
    = distinct justified semantic nuclei
      × reusable recurring coverage
      × mapped-card coverage
      × reviewed evidence
~~~

This expression is an optimization lens, not a single unbound score. A
campaign must report its component counts and evidence rather than collapse
them into a number whose meaning cannot be audited.

The anti-objective is:

~~~text
MORE CAPABILITY IDS != BETTER CENSUS
~~~

Breadth is valuable when one reviewed family represents a real reusable
semantic nucleus across multiple Requirements and cards. A narrow card-specific
claim, a renamed version, or a new parameter value is not additional breadth.

### 4.1 Family breadth versus definition breadth

M4 has two different identities:

~~~text
capability_family_id = stable identity of the semantic nucleus
capability_version   = explicit revision within that family
~~~

The canonical breadth metric is:

~~~text
ACTIVE_CAPABILITY_FAMILY_COUNT
    = count(distinct capability_family_id)
      among ACTIVE Capability definitions in the applicable M4 snapshot
~~~

The contract separately reports:

~~~text
ACTIVE_CAPABILITY_DEFINITION_COUNT
    = count(distinct (capability_family_id, capability_version))
      among ACTIVE definitions in the applicable M4 snapshot
~~~

Definition count is useful for lifecycle and evolution reporting. It must
never be presented as semantic breadth. New family count compares family IDs
between explicitly bound parent and after snapshots.

## 5. Anti-capability-inflation rules

The accepted M4 family rule remains binding:

~~~text
same semantic nucleus
    → same Capability family

same semantic nucleus with a materially revised claim
    → same family, new version/evolution as required

different semantic nucleus
    → new Capability family
~~~

The default granularity rule is:

~~~text
same operation + same typed dimension layout + different dimension values
    = one family with different Requirement-side link bindings
~~~

Quantity, card name, color, mana cost, target identity, zone object, and
superficial wording differences do not create a family by themselves. A
quantity is a typed parameter when the operation and semantic contract remain
the same. A separate family requires a reviewed change in the operation
anchor, actor or zone relation, event/replacement shape, composition, or
another material semantic contract.

The following never count as new semantic families by themselves:

- a new Capability version;
- a changed claim digest within the same family;
- a changed parameter value;
- a card-specific display name;
- a card-specific source phrase;
- a wording or template variant;
- a producer or pattern identity;
- a new report counter or representative example.

Capability family identity must not depend on a card, Oracle ID, source phrase,
pattern, producer, reviewer, filesystem path, timestamp, runtime order, or
engine name. The existing M4 identity and claim-digest rules govern all future
definitions.

### 5.1 Singleton discipline

One observed Requirement may create a non-authoritative candidate group or
Opportunity. It is not enough for an ACTIVE generic Capability by default.

Existing M4 activation discipline remains required:

- normally, an ACTIVE Capability needs at least two exact, accepted, complete
  Requirements from distinct M1 source identities satisfying the same typed
  claim; or
- the explicit permitted singleton-generalization review path must prove a
  reusable semantic boundary and exclusions.

The singleton-generalization path is an exception, not a metric shortcut.
One-card outliers remain visible as proposal, OUTLIER, UNMAPPED, or another
existing non-active result as appropriate.

## 6. Semantic Expansion Campaign model

A Semantic Expansion Campaign is a bounded, reviewable unit of M6 work. It
investigates one or more candidate groups under one explicit set of frozen
inputs and policies, then records what was proposed, reviewed, admitted,
mapped, reused, deferred, or left unresolved.

A campaign is a planning and provenance object, not a new semantic authority.
Its conceptual Interface must expose enough information for a reviewer to
reproduce its scope and compare its before/after result.

### 6.1 Required conceptual campaign bindings

Every future campaign must bind, at minimum, the following:

| Binding | Required meaning |
|---|---|
| Campaign identity | Stable, versioned identity for this bounded work unit |
| Parent Census release | Exact release identity where a release parent exists |
| Parent M3 identity | Exact analysis snapshot and manifest identity |
| Parent M4 identity | Exact authority context and published M4 snapshot identity |
| Source-lock identity | Exact source lock and source population |
| Selection policy | Versioned rule defining which cards/groups are in scope |
| Grouping policy | Versioned deterministic grouping policy |
| Producer identities | Stable producer IDs and versions used to create proposals |
| Target groups | Exact candidate-group identities selected for this campaign |
| Scope | Included cards, Requirement families/kinds, semantic waves, and limits |
| Exclusions | Explicitly excluded shapes, cards, waves, or M7 concerns |
| Nuclei under investigation | Non-authoritative hypotheses, not pre-authorized ontology names |
| Evidence requirements | Required source, structural, semantic, and review evidence |
| Before metrics | Bound metrics from the parent snapshot |
| After metrics | Bound metrics from the resulting snapshot or candidate output |
| Outcome | Exact campaign disposition, including zero, deferred, or unresolved results |

This list describes the future contract. It is not a machine schema and does
not authorize creating fields or records in M6-01.

### 6.2 Campaign lifecycle

The normative conceptual lifecycle is:

~~~text
frozen Census parent snapshot
        ↓
unresolved corpus selection
        ↓
deterministic candidate grouping
        ↓
candidate / opportunity inventory
        ↓
ranked campaign worklist
        ↓
bounded producer implementation
        ↓
PROPOSED Requirements
        ↓
existing M2 review / resolution and M4 admissibility path
        ↓
Capability reuse OR justified new family
        ↓
Requirement → Capability mappings
        ↓
new versioned M3/M4 snapshot
        ↓
coverage / breadth metrics
        ↓
future Census release candidate
~~~

The lifecycle is an authority sequence, not an instruction to automate every
transition. In particular:

- M6 grouping and ranking are non-authoritative;
- producer output is PROPOSED;
- existing M2 review and resolution remain explicit;
- existing M4 SRA, Capability review, activation, and mapping rules remain
  explicit; and
- no score or worklist position promotes a record.

### 6.3 Multiple nuclei per campaign

One campaign may investigate multiple distinct semantic nuclei. The campaign
must remain bounded through its selected groups, policy versions, evidence
requirements, and review budget. It must not assume:

~~~text
1 campaign = 1 Capability
~~~

A multi-nucleus campaign reports each Opportunity and resulting family
separately. A failure or deferral for one group does not justify silently
changing another group's classification.

## 7. Capability Opportunity model

A Capability Opportunity is a non-authoritative, reviewable hypothesis that a
candidate group may support reuse of an existing Capability family, a
materially distinct new family, or a later contract/wave.

An Opportunity may conceptually retain:

- its stable Opportunity identity and policy version;
- one or more candidate-group identities;
- the exact M1/M3 source and Requirement references used as evidence;
- the operation anchor and typed differences observed in the candidates;
- a proposed relation to an existing family, if any;
- proposed dimensions, exclusions, and unresolved fields;
- evidence references and review questions;
- frequency, coverage opportunity, semantic impact, uncertainty, and effort
  as planning dimensions; and
- a disposition such as reuse candidate, new-family candidate,
  contract gap, unresolved, or DEFER_TO_M7.

These values are hypotheses and worklist data. An Opportunity is not:

- an M2 Requirement;
- an accepted M2 review;
- an M4 Capability definition;
- an active family;
- an active mapping;
- proof of semantic equivalence; or
- a substitute for a reviewer.

The Opportunity model must not contain a hidden truth bit that bypasses M2
or M4. When a proposed Opportunity is promoted, the exact M2 and M4 records
that establish authority are created through their existing contracts and
remain separately auditable.

## 8. Candidate-group authority boundary

Candidate groups are deterministic groupings of observed unresolved or
otherwise selected surfaces. Their purpose is to make review work reusable
and bounded. They are not semantic conclusions.

M6-02 grouping may:

- inspect exact, frozen source, structural, and analysis information;
- group recurring unresolved surfaces;
- compute exact group frequency and structural characteristics;
- retain source and Requirement references;
- assign versioned heuristic labels or candidate classifications; and
- emit a deterministic review worklist.

M6-02 grouping may not:

- create an authoritative Requirement;
- promote M2 review or resolution state;
- create an ACTIVE Capability;
- create a Requirement-to-Capability mapping;
- modify M4 authority;
- claim semantic correctness;
- turn a source phrase into a family identity; or
- require a model call to reproduce the inventory.

Candidate groups and Opportunity artifacts must be safe to delete and
regenerate. Deleting them must not delete or alter an M2 Requirement, an M4
review, a Capability definition, a mapping, or a historical Census snapshot.

## 9. Prioritization dimensions

M6 prioritizes reusable closure, not arbitrary card order. The retained
principle is:

~~~text
frequency × semantic impact × uncertainty
~~~

This is a decision lens, not a frozen numeric formula or weight set.

### 9.1 Required planning dimensions

Every ranking policy should make the following dimensions visible:

| Dimension | Exact planning question |
|---|---|
| Frequency | How many distinct Oracle identities or exact source occurrences are represented? |
| Semantic impact | How much useful card-level or family-level meaning would closure add? |
| Uncertainty | What evidence, representation, or semantic ambiguity remains? |
| Reuse leverage | Can one reviewed result cover a recurring group without card-specific exceptions? |
| Coverage opportunity | How many currently unresolved or partially established cards could change state? |
| Contract fit | Can existing M2/M3/M4 contracts represent the result without an ad-hoc extension? |
| Review effort | Is the evidence and review packet bounded for the maintainer? |
| Risk of inflation | Could the grouping create many nominal families for one nucleus? |
| Wave and M7 fit | Is the candidate appropriate for the current wave and card-local M6 scope? |

Frequency must be an exact count over a stated population. Impact,
uncertainty, effort, and risk are planning assessments until a later task
defines a more specific policy. No dimension, weight, or ranking score may
create authority.

### 9.2 Deterministic ordering

If a future policy emits one ordered worklist, its policy version must define
all tie-breakers using canonical identities. No runtime order, Python hash
iteration, filesystem traversal, or reviewer arrival order may decide a tie.

The ranking policy and its output are reproducible planning evidence, not
semantic truth.

## 10. Semantic wave planning

Semantic waves are non-authoritative planning levels. They help sequence
review work; they do not freeze Capability names or guarantee that a card is
representable.

### WAVE_A

Simple recurring atomic and card-local semantic nuclei that fit the existing
M2 Requirement and M4 typed-claim contracts with limited decomposition.

### WAVE_B

Selection, search, reveal, ordering, and zone-manipulation structures that can
be represented as isolated card-local Requirements when the existing
contracts preserve their material dimensions.

### WAVE_C

Static, continuous, and reusable modifier structures where the existing
typed representation and evidence path can express the relevant scope,
objects, timing, and exclusions.

### WAVE_D

Replacement-like, linked, conditional, reflexive, and other higher-complexity
card-local structures. These are only M6 candidates when existing contracts
can represent them without semantic loss; otherwise they are a contract gap
or a later-scope item.

The wave labels contain no authoritative list of Magic mechanics or
Capability names. A candidate that fundamentally needs multi-object or
cross-card interaction analysis may be classified DEFER_TO_M7 rather than
forced into an isolated card-local Requirement.

## 11. Exact M6 metric contract

Metrics are valid only when their inputs, predicates, population, and
denominator are explicit. Every future M6 metric set must be bound to:

~~~text
source lock
M1 structural snapshot
M3 analysis snapshot
M4 authority package / authority context
M4 published snapshot
parent Census release where applicable
metric policy version
campaign identity where applicable
~~~

The metric set must retain exact integer numerators and denominators. A
presentation layer may round a displayed percentage, but the underlying
integer values and the formula remain available for audit.

For the definitions below, let:

- O be the distinct Oracle identities in the applicable locked source;
- S1 be the validated M1 structural records for O;
- S3 be the validated M3 analysis records for O;
- R be the distinct persisted M2 Requirement IDs in S3 bundles; and
- A4 and C4 be the applicable M4 authority and published Capability records.

If the required population or identity join does not validate, the metric set
is invalid or BLOCKED. It must not silently substitute a smaller population.

### 11.1 Corpus metrics

| Metric | Exact definition | Canonical denominator |
|---|---|---|
| TOTAL_ORACLE_IDENTITIES | Cardinality of O, the distinct Oracle IDs in the locked SourceLock | None for the count |
| STRUCTURAL_RECORD_COUNT | Count of validated M1 structural records bound to the source lock | None for the count |
| ANALYSIS_RECORD_COUNT | Count of validated M3 analysis records bound to the M1 snapshot and source lock | None for the count |

The expected one-record-per-identity invariants must be validated before
these counts are compared as coverage.

### 11.2 Analysis-state metrics

| Metric | Exact definition | Canonical denominator |
|---|---|---|
| REQUIREMENTS_PRODUCED_CARD_COUNT | Distinct Oracle IDs whose M3 outcome is REQUIREMENTS_PRODUCED | TOTAL_ORACLE_IDENTITIES for a percentage |
| NO_REQUIREMENTS_APPLICABLE_COUNT | Distinct Oracle IDs whose M3 outcome is NO_REQUIREMENTS_APPLICABLE | TOTAL_ORACLE_IDENTITIES for a percentage |
| UNRESOLVED_ANALYSIS_COUNT | Distinct Oracle IDs whose M3 outcome is UNRESOLVED_ANALYSIS | TOTAL_ORACLE_IDENTITIES for a percentage |

These are M3 analysis outcomes. They do not replace M2 review status,
M2 resolution state, M4 admissibility, or M4 mapping disposition.

### 11.3 Requirement metrics

| Metric | Exact definition | Canonical denominator |
|---|---|---|
| PERSISTED_REQUIREMENT_COUNT | Distinct persisted Requirement IDs in the M3 bundles | None for the count |
| M2_ACCEPTED_REQUIREMENT_COUNT | Distinct Requirement IDs whose M2 review.status is ACCEPTED | PERSISTED_REQUIREMENT_COUNT if a percentage is explicitly named |
| M2_PROPOSED_REQUIREMENT_COUNT | Distinct Requirement IDs whose M2 review.status is PROPOSED | PERSISTED_REQUIREMENT_COUNT if a percentage is explicitly named |
| M4_ADMISSIBLE_REQUIREMENT_COUNT | Distinct Requirement IDs with exactly one current M4 SRA decision ACCEPTED_FOR_CAPABILITY_MAPPING in the bound authority context | PERSISTED_REQUIREMENT_COUNT if a percentage is explicitly named |
| M4_MAPPED_REQUIREMENT_COUNT | Distinct Requirement IDs with a current M4 mapping decision MAPPED and its required active link in the bound authority context | PERSISTED_REQUIREMENT_COUNT if a percentage is explicitly named |
| UNRESOLVED_REQUIREMENT_COUNT | Distinct persisted Requirement IDs whose existing M2 resolution.state is UNRESOLVED | PERSISTED_REQUIREMENT_COUNT if a percentage is explicitly named |

M2 review status and M2 resolution state are separate dimensions. An ACCEPTED
Requirement may still have PARTIAL or UNRESOLVED resolution under the existing
contract. M4 admissibility is not M2 acceptance, and M4 mapping is not
semantic completeness of the card.

All other closed M2 review statuses and resolution states must remain
reportable. They may not be folded into ACCEPTED, PROPOSED, or unresolved
without an explicit future policy.

### 11.4 Card semantic-state metrics

These metrics use the existing Query semantic-state contract and its
precedence rules:

~~~text
UNRESOLVED_ANALYSIS always wins at card level.
NO_REQUIREMENTS_APPLICABLE has explicit M3 negative-authority precedence.
REQUIREMENTS_PRODUCED is ESTABLISHED only when every persisted Requirement
has the required final active mapping.
Otherwise REQUIREMENTS_PRODUCED is PARTIALLY_ESTABLISHED.
~~~

| Metric | Exact definition | Canonical denominator |
|---|---|---|
| ESTABLISHED_CARD_COUNT | Distinct Oracle IDs with semantic state ESTABLISHED | TOTAL_ORACLE_IDENTITIES |
| PARTIALLY_ESTABLISHED_CARD_COUNT | Distinct Oracle IDs with semantic state PARTIALLY_ESTABLISHED | TOTAL_ORACLE_IDENTITIES |
| UNRESOLVED_ANALYSIS_CARD_COUNT | Distinct Oracle IDs with semantic state UNRESOLVED_ANALYSIS | TOTAL_ORACLE_IDENTITIES |
| NO_REQUIREMENTS_APPLICABLE_CARD_COUNT | Distinct Oracle IDs with semantic state NO_REQUIREMENTS_APPLICABLE | TOTAL_ORACLE_IDENTITIES |

An UNRESOLVED_ANALYSIS card may contain persisted Requirements and active
Capability mappings for a subset of its semantics. It remains unresolved at
card level under the existing precedence rule.

### 11.5 Capability metrics

| Metric | Exact definition | Canonical denominator |
|---|---|---|
| ACTIVE_CAPABILITY_FAMILY_COUNT | Count of distinct family IDs among ACTIVE definitions in the bound M4 snapshot | None for the count |
| ACTIVE_CAPABILITY_DEFINITION_COUNT | Count of distinct active family/version definitions in the bound M4 snapshot | None for the count |
| NEW_ACTIVE_CAPABILITY_FAMILY_COUNT | Count of family IDs ACTIVE in the after snapshot and absent from the parent snapshot's ACTIVE family-ID set | None for the count |
| CARDS_WITH_ACTIVE_CAPABILITY_MAPPINGS | Distinct Oracle IDs with at least one validated active M4 link | TOTAL_ORACLE_IDENTITIES |
| ACTIVE_MAPPED_REQUIREMENT_COUNT | Distinct Requirement IDs with at least one validated active M4 link included by a MAPPED decision | PERSISTED_REQUIREMENT_COUNT if a percentage is explicitly named |

The family metrics count semantic families, not definitions, versions, claim
revisions, parameter values, or candidate Opportunities.

### 11.6 Campaign metrics

| Metric | Exact definition | Canonical denominator |
|---|---|---|
| CANDIDATE_GROUP_COUNT | Count of unique candidate-group identities in the campaign inventory after the bound grouping policy | None for the count |
| REVIEWED_CANDIDATE_GROUP_COUNT | Count of inventory groups with an explicit campaign grouping-review disposition | CANDIDATE_GROUP_COUNT if a percentage is explicitly named |
| RECURRING_PATTERN_GROUP_COUNT | Count of groups marked recurring by the bound deterministic grouping policy | CANDIDATE_GROUP_COUNT if a percentage is explicitly named |
| CAMPAIGN_SELECTED_CARD_COUNT | Cardinality of the union of distinct Oracle IDs in all selected groups | Parent TOTAL_ORACLE_IDENTITIES |
| CAMPAIGN_REQUIREMENTS_PRODUCED | Count of distinct new Requirement IDs in the after snapshot whose producer provenance binds the campaign | None for the count |
| CAMPAIGN_NEW_ACTIVE_CAPABILITY_FAMILIES | Distinct family IDs newly ACTIVE in the after snapshot and linked to a campaign-produced Requirement | None for the count |
| CAMPAIGN_REUSED_CAPABILITY_FAMILIES | Distinct family IDs that were ACTIVE in the parent, remain/usefully ACTIVE in the after snapshot, and receive at least one campaign-produced active link | None for the count |

Campaign grouping review is review of the grouping artifact. It is not M2
Requirement review or M4 Capability review. Campaign-produced counts must
remain distinct from total snapshot counts.

### 11.7 Allowed percentage form

A percentage is a separate, explicit metric whose name or definition states
its denominator. The general form is:

~~~text
PERCENT = 100 × exact numerator / exact denominator
~~~

Canonical examples include:

~~~text
ESTABLISHED_CARD_PERCENT_OF_TOTAL_ORACLE_IDENTITIES
UNRESOLVED_ANALYSIS_CARD_PERCENT_OF_TOTAL_ORACLE_IDENTITIES
CARDS_WITH_ACTIVE_CAPABILITY_MAPPINGS_PERCENT_OF_TOTAL_ORACLE_IDENTITIES
M4_MAPPED_REQUIREMENT_PERCENT_OF_PERSISTED_REQUIREMENTS
REVIEWED_CANDIDATE_GROUP_PERCENT_OF_CANDIDATE_GROUPS
~~~

These names are examples of explicit denominator encoding. A generic
reviewed-card percentage, coverage percentage, or mapping percentage is not
valid unless its exact predicate and denominator are supplied.

## 12. Metric denominators

The denominator is part of metric meaning, not presentation metadata.

The following denominator rules are frozen:

| Metric subject | Allowed denominator |
|---|---|
| Card semantic state or card mapping coverage | TOTAL_ORACLE_IDENTITIES in the same bound source snapshot |
| Requirement review, resolution, admissibility, or mapping | PERSISTED_REQUIREMENT_COUNT in the same bound M3/M4 snapshot |
| Candidate-group review or recurrence | CANDIDATE_GROUP_COUNT in the same campaign inventory |
| Selected campaign-card population | Parent TOTAL_ORACLE_IDENTITIES, unless an explicit metric names another parent population |
| Before/after family delta | Set comparison between explicitly bound parent and after M4 snapshots, not a percentage unless separately named |

The following populations must never be silently mixed:

~~~text
all cards
cards with Requirements
review-selected Requirements
MAPPED Requirements
ACTIVE definitions
candidate groups
~~~

Every report must retain the snapshot identities, exact numerator, exact
denominator, denominator label, metric-policy version, and campaign identity
when applicable. A dashboard or export that cannot carry those bindings must
not display the aggregate as release evidence.

## 13. Ambiguous legacy metrics

Issue #9 uses several human-readable metric phrases. M6-01 resolves them
without fabricating semantics.

| Legacy phrase | M6-01 resolution |
|---|---|
| reviewed-card percentage | Rejected as a canonical cross-layer metric. Use the exact Query semantic-state counts and separately named M2, M4 SRA, Capability-review, and mapping metrics. An active mapping is not a fully reviewed card. |
| high-confidence-derived percentage | NOT_DEFINED_WITH_CURRENT_CONTRACTS. No probabilistic confidence contract exists. ESTABLISHED is not a confidence score. A future confidence contract requires separate authorization. |
| proposal-only percentage | Rejected as a vague cross-layer metric. Use M2_PROPOSED_REQUIREMENT_COUNT and exact M4 disposition/admissibility metrics. A percentage is allowed only after an exact predicate and denominator are defined. |
| unresolved-card count | Canonically represented by UNRESOLVED_ANALYSIS_CARD_COUNT using the existing Query semantic-state contract. |
| unresolved-requirement count | Canonically represented only by the exact M2 resolution.state=UNRESOLVED predicate over persisted Requirements. It must not be inferred from an unresolved card outcome. |
| reviewed recurring-pattern count | Represented by REVIEWED_CANDIDATE_GROUP_COUNT only when the grouping-review disposition is explicit. It is grouping/worklist review, not semantic or Capability authority. |

M6-01 therefore records no percentage baseline for the ambiguous phrases.
The historical 0.1 counts remain exact; undefined metrics remain explicitly
undefined until a later contract is accepted.

## 14. Snapshot and lineage binding

Every future M6 metric set, candidate inventory, campaign, and semantic output
must identify the exact inputs from which it was derived:

~~~text
SourceLock
M1 structural snapshot
M3 analysis snapshot
M4 authority package and current authority context
M4 published snapshot
parent Census release, where applicable
selection/grouping/producer policy versions
campaign identity
metric policy version
~~~

M6 output is a new versioned snapshot or non-authoritative campaign artifact.
It is never an in-place edit to Census 0.1. The parent release identity remains
available for audit and comparison.

M6 does not automatically equal Census 0.2. A future 0.2 candidate requires
its own release identity, explicit parent lineage, release policy, and
conformance evidence. No numeric 0.2 threshold is frozen here.

## 15. Campaign before/after accounting

Every completed or intentionally stopped campaign should report:

~~~text
before
after
delta
~~~

At minimum, the accounting should answer:

- how many selected cards changed semantic state;
- how many new Requirements were produced;
- how many Requirements changed M2 review or resolution state through the
  existing review path;
- how many Requirements became M4-admissible or M4-mapped;
- how many existing Capability families were reused;
- how many genuinely new Capability families became ACTIVE;
- how many cards gained active mappings;
- how many candidate groups were reviewed or left unresolved; and
- how card coverage and semantic-family breadth changed.

The parent and after snapshots must use compatible, explicitly bound
populations. If the source population changes, the report must state that it
is a new population rather than presenting the result as a campaign delta.

Zero and negative deltas are valid. A campaign can be successful because it
rejects an inflationary hypothesis, proves a contract gap, or produces a
high-value review inventory without activating a new family.

Changed classifications are append-only/versioned outputs. A comparison
report may explain a change, but it cannot rewrite the parent record.

## 16. M6-02 boundary

M6-02 is:

~~~text
DETERMINISTIC
GLOBAL
NON-AUTHORITATIVE
UNRESOLVED-PATTERN INVENTORY
CAPABILITY-OPPORTUNITY INVENTORY
PRIORITIZATION INPUT
~~~

M6-02 may inspect exact source, structural, and analysis information and may
read the parent M4 snapshot to identify possible reuse. It may:

- enumerate the unresolved or selected population;
- group recurring surfaces under a versioned policy;
- compute exact frequencies and typed structural characteristics;
- emit candidate and Opportunity records;
- assign heuristic, versioned planning classifications; and
- emit deterministic worklists and reports.

M6-02 may not:

- create authoritative Requirements;
- promote M2 review or resolution;
- create ACTIVE Capabilities;
- create Requirement-to-Capability mappings;
- modify M4 authority or historical release bytes;
- claim semantic correctness;
- treat ranking as a review decision; or
- require an LLM, network call, or live source acquisition for regeneration.

M6-02 output must be safe to delete and regenerate. The only durable meaning
of a later semantic result comes from the existing M2/M3/M4 contracts and
their explicit snapshot lineage.

## 17. Determinism requirements

For a fixed source population and policy set:

~~~text
same frozen inputs
+ same selection/grouping/producer policy versions
    → same candidate inventory bytes
~~~

Future candidate-group and Opportunity identities must be derived from
explicit canonical, versioned domain inputs. They must not depend on:

~~~text
filesystem path
wall-clock time
process order
randomness
Python hash iteration
machine identity
~~~

The identity design must use domain separation. The exact future domain names,
hash format, and wire schema are intentionally deferred. Canonical ordering,
stable tie-breakers, and path-free evidence are not deferred.

Ordinary reproduction must be offline. A model call is never a prerequisite
for regenerating a deterministic inventory or any authoritative semantic
snapshot. If an LLM or external research tool assists a human, its output is
proposal/research evidence only and must be retained as such.

## 18. Evidence and review expectations

M6 semantic review should prefer evidence in approximately this order:

~~~text
official Comprehensive Rules
official release notes and rulings
official Oracle/source facts
other trusted primary Magic sources
secondary references for cross-checking where useful
~~~

M6-01 does not freeze exact rules citations for future families. It freezes
the requirement that a later review packet retain enough evidence provenance
to audit why a Requirement was accepted, why it was admissible, why a
Capability was reused or newly proposed, and why a mapping was admitted.

Each review packet should make visible:

- exact source and snapshot identities;
- the candidate-group and Opportunity inputs;
- the M2 Requirement claim, typed parameters, evidence, derivation, review,
  and resolution state;
- the proposed reusable semantic nucleus and all typed dimensions;
- exclusions and known unresolved dimensions;
- the existing M4 family/version/claim context, if reuse is proposed;
- the M4 SRA, Capability review, activation, and mapping decisions; and
- the before/after metric binding.

Human review is necessary. Manual duplication of 38,740 card decisions is
not the scaling strategy. A recurring group may be reviewed once only when
the typed semantic boundary genuinely applies to every included Requirement.

## 19. Fail-closed escalation rules

If a candidate requires a concept not represented by the accepted M2, M3, or
M4 contracts:

~~~text
stop semantic promotion
record the contract/model gap
preserve the candidate as unresolved or deferred
request a separately authorized contract evolution
~~~

Do not encode the missing concept as an ad-hoc string, hidden status, parser
flag, or card-specific executor.

Examples that commonly require this treatment include:

- replacement effects;
- continuous effects whose scope or layer cannot be represented;
- linked abilities;
- reflexive triggers;
- intervening-if conditions;
- complex object references; and
- copy semantics.

Invalid producer output is not silently converted into UNRESOLVED. It is
rejected or quarantined under the existing validation/error contract. A
genuine unresolved semantic result remains an explicit unresolved result.

Conflicting evidence, ambiguous grouping, insufficient typed dimensions, or
inadequate review evidence must not be resolved by producer priority,
frequency, ranking score, runtime order, or guesswork.

## 20. M6 versus M7 boundary

M6 covers reusable, card-local semantic Requirements and Capabilities that can
be represented and reviewed under the existing contracts.

M6 may include a card with multiple local clauses when the M2 representation,
typed dimensions, relationships, and review path preserve the semantics.
M6 must not force a candidate into a card-local abstraction when its meaning
fundamentally depends on:

- simultaneous or cross-card interaction not represented by the current
  Requirement model;
- higher-order effects across multiple objects or abilities;
- interaction sequencing that requires a rules engine;
- a global game-state invariant; or
- a future M7 interaction model.

Such a candidate may be classified DEFER_TO_M7. Deferral is a valid result,
not a failed attempt and not a reason to create an inflationary proxy family.

M6 remains:

~~~text
NOT a rules engine
NOT a simulator
NOT Manafold engine semantics
~~~

M6 must not resolve spells, apply replacement effects, modify game state,
evaluate layers, select targets, or perform zone transitions.

## 21. Solo-maintainer ergonomics

The design must remain executable by one maintainer. A practical campaign
therefore prefers:

~~~text
ranked bounded campaigns
high-reuse recurring groups
small review packets
deterministic regeneration
mechanical reports
one authoritative definition
~~~

It explicitly avoids:

~~~text
38,735-card manual queue
all-pairs analysis
massive manual ontology files
giant YAML taxonomies
daily hand-maintained spreadsheets
card_name → Capability list as semantic authority
oracle_id → manually typed semantic tags at corpus scale
~~~

Campaign scope and review budget must be explicit. A bounded campaign may
stop when the budget is reached, a group is too ambiguous, or the remaining
work belongs to another wave or M7. The result must preserve the worklist and
stopping reason so that the next campaign can resume from evidence instead of
repeating hidden work.

## 22. M6-01 implementation and production-code constraint

M6-01 is a design/specification slice only. Its implementation scope is one
new document:

~~~text
docs/superpowers/specs/2026-09-15-m6-semantic-expansion-contract.md
~~~

M6-01 must not modify:

~~~text
src/
schemas/
fixtures/
reviewed/
locks/
packaging/
.github/workflows/
tests/
dist/
README.md
Issue #2
Issue #9
~~~

No new producer, Requirement, Capability, mapping, M4 authority record,
semantic fixture, metric schema, campaign runner, database, Rust migration,
or Explorer behavior is part of M6-01.

## 23. Explicit non-decisions

M6-01 does not freeze:

- exact first Wave-A Capability names;
- the exact number of M6 Capability families;
- a target number of cards;
- a target percentage of resolved cards;
- a Census 0.2 release threshold;
- an M6 completion percentage;
- a specific M6-02 clustering algorithm;
- specific numeric priority weights;
- a specific future wire schema;
- a confidence scalar or probabilistic confidence contract;
- a database design;
- a Rust migration;
- an M7 interaction model; or
- any handwritten global mechanic list as ontology authority.

These items require later evidence and explicit authorization. Examples used
to explain a wave or semantic shape do not become ontology members merely
because they appear in this document.

## 24. Downstream M6 sequence

The intended planning sequence is:

~~~text
M6-00
roadmap + entry baseline
COMPLETE

M6-01
semantic-expansion campaign + metric contract
CURRENT / AUTHORIZED / NOT_FROZEN

M6-02
global deterministic unresolved-pattern inventory

M6-03
Capability-opportunity analysis + breadth-aware ranking

M6-04
first bounded multi-Capability semantic wave

M6-05
review / admissibility / Capability reuse-or-extension campaign

M6-06
new versioned M3/M4 semantic snapshot

M6-07
broader Census release candidate + before/after quality report
~~~

Only M6-01 is authorized by this document. M6-02 through M6-07 remain
planning direction until separately authorized.

## 25. M6-01 frozen decisions

The following decisions are frozen by M6-01 and are the acceptance boundary
for later M6 work:

| ID | Frozen decision | Operational consequence |
|---|---|---|
| D1 | M6 optimizes semantic breadth plus reuse plus mapped-card coverage plus reviewed evidence, not raw Capability count. | Campaigns report useful coverage and evidence, not only family totals. |
| D2 | Capability breadth counts distinct semantic family IDs, not versions or claim revisions. | ACTIVE_CAPABILITY_FAMILY_COUNT and ACTIVE_CAPABILITY_DEFINITION_COUNT remain separate. |
| D3 | Candidate grouping and Capability Opportunities are non-authoritative. | They can rank and explain work but cannot create semantic authority. |
| D4 | M6 producer outputs remain proposals until the existing authority path permits downstream use. | Producers cannot set terminal M2 review, M4 admissibility, Capability review, activation, or active mapping. |
| D5 | M6 uses bounded campaigns, not arbitrary card-by-card expansion. | Scope, exclusions, policies, target groups, review budget, and stopping reason are explicit. |
| D6 | Campaigns may cover multiple potential semantic nuclei. | One campaign is not restricted to one family, but each Opportunity and result remains separately auditable. |
| D7 | M6 metrics are snapshot-bound and denominator-explicit. | Every aggregate carries exact inputs, policy identity, numerator, denominator, and lineage. |
| D8 | M2 review, M4 admissibility, Capability review, and mapping states remain distinct metrics. | No cross-layer reviewed or coverage scalar may collapse their meanings. |
| D9 | No probabilistic confidence metric is invented without an explicit confidence contract. | HIGH_CONFIDENCE_DERIVED_PERCENTAGE remains NOT_DEFINED_WITH_CURRENT_CONTRACTS. |
| D10 | Census 0.1 remains immutable historical evidence. | Later classifications are new versioned outputs and never in-place corrections to 0.1. |
| D11 | M6-02 is inventory and ranking only and creates no semantic authority. | M6-02 output is deterministic, regenerable, and safe to delete. |
| D12 | Semantics requiring interaction or higher-order modeling may be deferred to M7. | DEFER_TO_M7 is a valid fail-closed result. |
| D13 | A new Capability family requires a genuinely distinct semantic nucleus. | Parameters, wording, card identity, and versions do not justify family inflation. |
| D14 | UNRESOLVED remains a legitimate campaign result. | A campaign may stop or return candidates to UNRESOLVED without forcing closure. |
| D15 | Future M6 semantic outputs preserve deterministic provenance and version lineage. | Reproduction and before/after comparison require exact parent snapshots and policy identities. |

These decisions do not authorize M6-02 or any semantic implementation. The
remaining authorization state is:

~~~text
M6_01_STATUS = NOT_FROZEN

M6_02_AUTHORIZED = NO
M6_03_AUTHORIZED = NO
M6_04_AUTHORIZED = NO

SEMANTIC_EXPANSION_AUTHORIZED = NO
NEW_REQUIREMENT_PRODUCERS_AUTHORIZED = NO
NEW_REQUIREMENTS_AUTHORIZED = NO
NEW_CAPABILITIES_AUTHORIZED = NO
NEW_M4_AUTHORITY_AUTHORIZED = NO

PR_AUTHORIZED = NO
MERGE_AUTHORIZED = NO
~~~
