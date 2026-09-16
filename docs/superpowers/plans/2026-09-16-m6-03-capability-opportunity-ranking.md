# M6-03 Capability-Opportunity Analysis and Breadth-Aware Ranking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline execution). Steps use checkbox syntax for tracking.

**Goal:** Turn the frozen M6-02 recurring Capability Opportunities into a deterministic,
offline, non-authoritative planning surface: mechanical planning-noise control,
mechanical-overlap control, a full lexicographic breadth worklist, and a bounded
greedy marginal-Oracle-coverage review packet of at most 25 Opportunities, with
atomic publication, independent validation, and real-data A/B reproduction.

**Architecture:** Add a focused sibling package `src/manafold_census/prioritization/`
that consumes an explicit validated M6-02 output tree plus the same explicit
M1/M3/M4/source/Census parents through the existing input-bound M6-02 validation
path. It never mutates M6-02 internals, M2/M3/M4 authority, Census 0.1, README,
packaging, or workflows. CLI stays a thin adapter. All semantic planning
dimensions that cannot be derived mechanically remain `UNASSESSED`.

**Tech Stack:** Python 3.12+, frozen dataclasses, existing canonical JSON and
domain-digest helpers, JSONL, pytest, Ruff, mypy, ignored dist output.

**Base SHA:** `935dc5129d377521a4bd73c036e48d080d4752c6` (origin/main, PR #20 merge).

---

## Task 1: Define the test surface and synthetic fixtures

**Files:**

- Create: tests/prioritization_fixtures.py
- Create: tests/test_prioritization_assessment.py
- Create: tests/test_prioritization_ranking.py
- Create: tests/test_prioritization_overlap.py
- Create: tests/test_prioritization_selection.py
- Create: tests/test_prioritization_build.py
- Create: tests/test_prioritization_cli.py

- [ ] Write fixture helpers for synthetic M6-02 trees: recurring groups with
  known Oracle/surface/raw-text counts, EXACT vs SHAPE lens pairs, null-only
  groups, empty/whitespace-only groups, mixed null/empty groups, normal groups,
  exact surface-ID overlap pairs, disjoint surface sets, singleton groups, and
  shuffled-traversal variants.
- [ ] Write assertions for the planned interfaces:

  ~~~python
  classify_planning_noise(raw_texts) -> PlanningNoiseV1
  build_assessments(groups, surfaces) -> tuple[OpportunityAssessmentV1, ...]
  cluster_mechanical_overlaps(assessments) -> tuple[MechanicalOverlapClusterV1, ...]
  rank_worklist(assessments, clusters) -> tuple[RankedWorklistEntryV1, ...]
  select_review_packet(ranked, assessments) -> ReviewPacketV1
  build_prioritization(inputs, output) -> PrioritizationBuildResultV1
  validate_prioritization(output) -> PrioritizationValidationResultV1
  ~~~

  Assert NON_AUTHORITATIVE records, UNASSESSED semantic fields, no Requirement
  or Capability creation, no mapping creation, and read-only M4 context.
- [ ] Run the focused tests and observe the expected RED collection failure
  because the new prioritization package does not yet exist:

  ~~~text
  python -m pytest tests/test_prioritization_assessment.py tests/test_prioritization_ranking.py tests/test_prioritization_overlap.py tests/test_prioritization_selection.py tests/test_prioritization_build.py tests/test_prioritization_cli.py -q
  ~~~

## Task 2: Add immutable prioritization models and identities

**Files:**

- Create: src/manafold_census/prioritization/__init__.py
- Create: src/manafold_census/prioritization/_common.py
- Create: src/manafold_census/prioritization/identity.py
- Create: src/manafold_census/prioritization/assessment.py
- Create: src/manafold_census/prioritization/worklist.py
- Create: src/manafold_census/prioritization/manifest.py
- Create: src/manafold_census/prioritization/report_model.py

- [ ] Implement frozen, slotted models for OpportunityAssessmentV1,
  MechanicalOverlapClusterV1, RankedWorklistEntryV1, ReviewPacketEntryV1,
  ReviewPacketV1, FileDescriptorV1 (local, path-free), PrioritizationManifestV1,
  and PrioritizationReportV1.
- [ ] Freeze vocabularies: AUTHORITY_SCOPE = NON_AUTHORITATIVE;
  PlanningNoiseV1 = NONE | ALL_NULL | ALL_EMPTY_OR_WHITESPACE |
  NULL_OR_EMPTY_ONLY; StoppingReasonV1 = REVIEW_BUDGET_REACHED |
  NO_ADDITIONAL_ORACLE_COVERAGE; semantic planning fields fixed to UNASSESSED.
- [ ] Freeze policy identities: assessment policy
  `m6-03.opportunity-assessment.v1`, ranking policy
  `m6-03.breadth-ranking.v1`, review budget 25.
- [ ] Implement path-free domain-separated identities with existing canonical
  JSON and domain-digest helpers: assessment_id binds parent Opportunity ID +
  assessment policy + canonical planning content; cluster_id binds the exact
  sorted surface-ID set; surface-set digest binds the exact sorted surface IDs.
- [ ] Enforce strict types, sorted identity collections, canonical ordering,
  NON_AUTHORITATIVE scope, no semantic lifecycle values, no truth flags such as
  is_capability/approved.
- [ ] Keep every production module at or below 500 LOC; split by responsibility
  (assessment vs worklist vs manifest vs report models stay separate).

## Task 3: Implement explicit input binding through the frozen M6-02 path

**Files:**

- Create: src/manafold_census/prioritization/input.py

- [ ] Load only explicit paths: m6-02 output directory, source-lock file,
  structural-output directory, analysis-output directory, m4-output directory,
  parent Census release ID, expected opportunity count (default 10,732 for the
  real Census 0.1 parent, nullable for synthetic fixtures).
- [ ] Reuse `load_inventory_inputs` for M1/M3/M4/source/Census closure, then
  reuse `validate_inventory_against_inputs` for the M6-02 tree. Bind the exact
  validated M6-02 manifest identity/digest (selected-identity-set digest,
  manifest SHA-256, opportunity count, grouping/shape policy IDs).
- [ ] Fail closed when surface projection differs, group reconstruction differs,
  Opportunity reconstruction differs, manifest descriptors differ, M3 binding
  differs, M4 parent differs, source lock differs, or Census parent differs.
  A self-consistent but source-drifted fake M6-02 tree must be rejected because
  its projection does not match the explicit M1/M3 inputs.
- [ ] Read the active M4 family catalog as read-only reviewer context only:
  distinct ACTIVE `capability_family_id` values sorted, plus the parent M4
  manifest SHA-256. Never map an Opportunity to a family.
- [ ] Run input-binding tests, including the source-drift regression that builds
  a valid tree from altered records and requires rejection against the original
  loaded inputs.

## Task 4: Implement mechanical analysis, overlap control, and ranking

**Files:**

- Create: src/manafold_census/prioritization/analyze.py

- [ ] For every validated recurring M6-02 Opportunity derive exact
  source-derived values: distinct_oracle_count, occurrence_count,
  member_surface_count, distinct_raw_text_count (None counts as one distinct
  value), grouping_lens, recurrence status, sorted member surface IDs, sorted
  member Oracle IDs, member_surface_set_digest, planning-noise classification,
  representative example surface IDs (first 3 by canonical surface identity).
- [ ] Implement planning-noise classification from raw surface content only:
  ALL_NULL when every raw_text is None; ALL_EMPTY_OR_WHITESPACE when every
  raw_text is non-None and strips to empty; NULL_OR_EMPTY_ONLY when every
  raw_text is None or strips to empty (and neither of the above applies);
  otherwise NONE. Preserve all noise Opportunities in the complete output;
  exclude them from the primary bounded packet.
- [ ] Implement mechanical-overlap clustering on the exact sorted surface-ID
  set. Same set means same cluster (same participating source surfaces), never
  semantic equivalence. Every Opportunity stays traceable; the cluster records
  all member opportunity IDs sorted plus one deterministic representative
  (EXACT lens before SHAPE lens, then opportunity_id ascending).
- [ ] Implement the full versioned worklist ordering `m6-03.breadth-ranking.v1`
  lexicographically: non-noise before noise; distinct_oracle_count DESC;
  distinct_raw_text_count ASC; occurrence_count DESC; EXACT before SHAPE;
  opportunity_id ASC. All ties terminate in canonical identity. No filesystem,
  dict/set iteration, hash, timestamp, or random tie-breakers.
- [ ] Implement the bounded greedy marginal-Oracle-coverage selector on
  non-noise representatives only: at each step compute
  marginal = count(candidate.oracle_ids - covered); pick by marginal DESC,
  total distinct_oracle_count DESC, distinct_raw_text_count ASC,
  occurrence_count DESC, EXACT before SHAPE, opportunity_id ASC; accumulate
  coverage; stop at 25 selections (REVIEW_BUDGET_REACHED) or when max marginal
  is 0 (NO_ADDITIONAL_ORACLE_COVERAGE). Persist marginal and cumulative
  coverage per selected entry plus the top-25 marginal sequence.
- [ ] Store the fixed reviewer questions without answering them; expose M1/M3/
  M4/Census parent identities per packet entry; keep M4 context read-only.

## Task 5: Implement atomic build, independent validation, reports, and CLI

**Files:**

- Create: src/manafold_census/prioritization/build.py
- Create: src/manafold_census/prioritization/validate.py
- Create: src/manafold_census/prioritization/report.py
- Create: src/manafold_census/prioritization/reproduction.py
- Create: src/manafold_census/prioritization/cli.py
- Modify: src/manafold_census/cli.py

- [ ] Build only in a fresh staging directory, validate it, then atomically
  publish the six-file set: manifest.json, opportunity-assessments.jsonl,
  mechanical-overlap-clusters.jsonl, ranked-worklist.jsonl, review-packet.json,
  report.json. Reject conflicting/non-empty destinations, partial output, and
  invalid staging output.
- [ ] Validate by independently rederiving input bindings, Opportunity closure,
  surface-set digests, overlap clusters, noise classification, exact counts,
  full ranking keys/order, greedy selection, marginal/cumulative coverage,
  stopping reason, report aggregates, and manifest descriptors from validated
  inputs. Tampering with any persisted derived value must fail validation.
- [ ] Report input Opportunity count, non-noise/noise counts, overlap-cluster
  count, full-worklist count, bounded-packet count, packet Oracle-union
  coverage with denominator, stopping reason, top-25 marginal sequence, and
  exact parent identities. Repeat throughout that Opportunity assessment is not
  semantic review, ranking is not authority, mechanical overlap is not semantic
  equivalence, marginal Oracle coverage is not semantic breadth, and M6-03
  creates no Requirement, Capability, mapping, or M4 authority.
- [ ] Register explicit thin commands consistent with M6-02 conventions:

  ~~~text
  m6-03-opportunity-build
  m6-03-opportunity-check
  m6-03-opportunity-report
  m6-03-opportunity-reproduce
  ~~~

- [ ] Run CLI tests and help output; confirm unrelated M6-02 commands retain
  their behavior.

## Task 6: Prove reproduction and record real evidence

**Files:**

- Create: docs/reports/2026-09-16-m6-03-capability-opportunity-ranking.md
- Create: docs/reports/2026-09-16-m6-03-capability-opportunity-ranking.json

- [ ] Run synthetic A/B builds in different temporary absolute paths with
  shuffled traversal and require identical file sets, bytes, identities, and
  tree digests.
- [ ] Run the real explicit-input build twice from the frozen Census 0.1
  parents plus the validated M6-02 parent:

  ~~~text
  source-lock: source-locks/scryfall-oracle-v1.json
  structural-output: dist/structural/scryfall-oracle-v1-run-a
  analysis-output: dist/analysis/m3-census-0-1-real-run-a
  m4-output: dist/capability/m4-census-0-1-real-run-a
  m6-02-output: dist/m6/inventory/m6-02-real/run-a
  parent-census-release-id: censusrel_55ff3102f75a64a0a2e1277810e709847803d085c6623ceeec14b7fe8f969e9f
  ~~~

  under ignored output roots:

  ~~~text
  dist/m6/prioritization/m6-03-real/run-a
  dist/m6/prioritization/m6-03-real/run-b
  ~~~

- [ ] Record observed counts only after the run. Keep evidence path-free and
  free of timestamps, machine names, usernames, and predeclared packet targets.
- [ ] Require file-set parity, byte parity, path-free manifest, offline
  regeneration, input Opportunity count 10,732, full-worklist count 10,732,
  and bounded-packet count at most 25 with an explicit stopping reason.

## Task 7: Run quality gates, scope audit, commit, and push

**Files:**

- Modify only the files listed above plus this plan; do not change M2/M3/M4
  authority, Census 0.1 evidence, M6-02 behavior, README, packaging,
  dependencies, or workflows.

- [ ] Run the focused M6-03 suite, the existing M6-02 inventory regression
  suite, full pytest, Ruff format/check, mypy, and the applicable wheel/package
  smoke. Report any platform-specific gate accurately as NOT_RUN rather than
  inventing a result.
- [ ] Run git diff scope audit, inspect the full origin/main-to-HEAD scope,
  verify ignored generated output, confirm zero Requirements, Capabilities,
  links, mappings, M4 authority, Census 0.1, M6-02 behavior, dependency,
  workflow, or README changes, and confirm every production module is at or
  below 500 LOC.
- [ ] Commit with:

  ~~~text
  feat: rank M6-03 capability opportunities
  ~~~

- [ ] Push only feat/m6-03-opportunity-ranking, verify local and remote heads
  match, leave the worktree clean, create no PR, and leave M6-03 as
  IMPLEMENTED_AWAITING_INDEPENDENT_REVIEW with all later authorization flags NO.
