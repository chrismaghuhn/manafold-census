# M5-06 Derived Reports and Canonical Indexes Implementation Plan

> REQUIRED SUB-SKILL: Use superpowers:executing-plans. Execute the tasks in
> order and stop after the standalone M5-06 commit for exact-head review.

**Goal:** Add the first derived Census 0.1 reports and canonical lookup indexes
without changing the frozen authoritative bundle, release identity, M3/M4
records, or semantic coverage.

**Architecture:** Treat the frozen M5-05 bundle as the sole explicit input.
Validate its authoritative contents and reconstruct the existing M5-02 input
lock from the nested manifests so the frozen M1/M3/M4 validators remain the
authority. Read structural cards, analysis records, Requirements, and the
published M4 records into immutable derived views. Write a fresh sibling copy
of the bundle with `reports/` and `indexes/` only, binding both derived
manifests to the unchanged Census manifest SHA and release ID. Reports and
indexes are regenerated from typed frozen records, canonically sorted, and
verified by a complete reread before atomic publication.

**Tech Stack:** Python 3.12+, existing canonical JSON and digest helpers,
existing M5-05 bundle/M1/M3/M4 validators, JSON Schema Draft 2020-12, pytest,
Ruff, mypy, PowerShell.

---

### Task 1: Add failing M5-06 contract tests

Files:
- Create `tests/test_census_reports.py`.
- Create `tests/test_census_indexes.py`.
- Reuse the frozen M5-05 synthetic bundle fixture and existing typed M3/M4
  fixtures; do not add new semantic authority fixtures.

Steps:
- [ ] Test report and index model round-trips, strict schemas, canonical bytes,
  digest-bound Census manifest SHA/release ID, and descriptor byte/length/count
  checks.
- [ ] Test a fresh derived bundle build copies all 98 authoritative files
  byte-for-byte and adds exactly the four report files and six index files.
- [ ] Test exact deterministic output across two fresh destinations and across
  input-order permutations.
- [ ] Test report counters reconcile to the frozen M5-05 population and expose
  explicit denominator labels for ratios/statistics.
- [ ] Test `UNRESOLVED_ANALYSIS`, `NO_REQUIREMENTS_APPLICABLE`, and
  `REQUIREMENTS_PRODUCED` remain separate, including unresolved records with a
  persisted Requirement bundle.
- [ ] Test mapping-review queue rows contain only persisted Requirements and
  preserve every frozen M4 mapping disposition; no new Requirement or
  Capability appears in any derived output.
- [ ] Test all five canonical indexes are sorted, duplicate-free where their
  key contract requires it, and retain one-to-many relationships and mapping
  multiplicity.
- [ ] Test corrupt report/index descriptors, extra derived files, missing
  derived files, modified authoritative bytes, and a pre-existing destination
  fail closed without mutating the frozen input or final destination.
- [ ] Test the explicit maintainer command with `--bundle` and `--output` only;
  no latest/timestamp discovery is permitted.
- [ ] Run: `$env:PYTHONPATH='src'; & C:\Python313\python.exe -m pytest tests/test_census_reports.py tests/test_census_indexes.py -q`.
- [ ] Confirm RED because the M5-06 modules, schemas, and command do not yet
  exist.

### Task 2: Implement closed report/index models and schemas

Files:
- Create `src/manafold_census/reports/__init__.py`.
- Create `src/manafold_census/reports/model.py`.
- Create `src/manafold_census/query/__init__.py`.
- Create `src/manafold_census/query/indexes.py`.
- Create `schemas/census-report.v1.schema.json`.
- Create `schemas/census-index-manifest.v1.schema.json`.

Steps:
- [ ] Define `census.census-report.v1` and `census.census-index-manifest.v1`
  with closed wire keys, digest/length/count validation, and strict relative
  path rules.
- [ ] Define immutable report metrics with integer numerator/denominator and
  explicit `denominator_label`; never encode a floating-point ratio.
- [ ] Define the report index and index manifest descriptors with exact
  canonical paths, SHA-256, byte length, and JSONL record count.
- [ ] Define closed derived row models for unresolved analysis, mapping review
  queue, and each index; each row must carry the frozen Census release binding
  and exact source/Requirement/Capability references it repeats.
- [ ] Keep model validation descriptive only: it may reject malformed or
  inconsistent derived data, but it must not choose a semantic outcome or
  manufacture authority.
- [ ] Run focused model/schema tests GREEN.

### Task 3: Implement validated derived build and canonical indexes

Files:
- Create `src/manafold_census/reports/build.py`.
- Extend `src/manafold_census/query/indexes.py`.
- Extend `tests/test_census_reports.py` and `tests/test_census_indexes.py`.

Steps:
- [ ] Load the explicitly supplied frozen M5-05 bundle and run its existing
  self-contained authority/M1/M3/M4 validation before any derived read.
- [ ] Reuse frozen typed parsers and validators to read M1 structural records,
  M3 analysis records, M3 traces, Requirements, and M4 definitions/reviews,
  admissibility, links, mapping decisions, relations, and evolution.
- [ ] Build the global report dimensions required by the spec: source,
  structural, analysis, Requirement presence, M2 review/resolution, M4
  admissibility/mapping, active Capability presence/lifecycle, unresolved
  analysis, outliers, ambiguities, review queues, and mapped-subset Capability
  frequency.
- [ ] Emit explicit state counters and denominator-labelled mapped-subset
  metrics. Keep unresolved cards distinct from explicit negative authority and
  do not turn missing Requirements into negative claims.
- [ ] Build exactly these canonical JSONL indexes: cards by name, cards by
  Oracle identity, Requirements by card, links by Requirement, and cards by
  Capability. Preserve exact Requirement IDs, link IDs, mapping dispositions,
  typed binding wires, and source identity/provenance references.
- [ ] Sort every row with a documented total key, write canonical JSON/JSONL,
  and create descriptors from the exact published bytes.
- [ ] Copy the frozen bundle into a fresh sibling staging tree, add only
  `reports/` and `indexes/`, reread every authoritative and derived file, and
  atomically publish. Never overwrite the M5-05 input or an existing output.
- [ ] Verify release identity and authoritative census-manifest bytes are
  unchanged; reports/indexes bind to the raw census-manifest SHA and never
  enter its release-ID projection.

### Task 4: Add the explicit M5-06 maintainer command

Files:
- Modify `src/manafold_census/release/commands.py`.
- Modify `src/manafold_census/release/cli.py`.
- Modify `justfile`.
- Extend the focused tests.

Steps:
- [ ] Add `m5-derived-build --bundle <frozen-bundle> --output <fresh-output>`.
- [ ] Report missing input as `BLOCKED`, malformed/corrupt or inconsistent
  input as `FAIL`, and print `reports/indexes` identities only after atomic
  publication succeeds.
- [ ] Do not add M5-07 query APIs, Explorer behavior, new semantic authority,
  bundle release identity fields, or a generalized discovery mode.
- [ ] Run command help and focused CLI tests.

### Task 5: Real A/B reproduction, quality gates, commit, and push

Files:
- Generated ignored output only: `dist/derived/manafold-census-0.1.0-run-a`
  and `dist/derived/manafold-census-0.1.0-run-b`.

Steps:
- [ ] Run the explicit M5-06 command against the frozen real bundle into fresh
  Run-A and Run-B destinations.
- [ ] Compare every authoritative and derived file byte-for-byte, including
  both derived manifests and all descriptor counts; require report/index
  regeneration parity.
- [ ] Confirm the original M5-05 bundle is byte-identical before and after the
  run, and that no authoritative Census manifest fields changed.
- [ ] Run focused tests, full pytest, Ruff format/check, mypy, LOC budget,
  `just --dry-run`, wheel build, and fresh non-editable wheel smoke.
- [ ] Stage only the M5-06 plan, source modules, schemas, CLI/just changes, and
  tests. Do not stage generated `dist/` output.
- [ ] Commit with message: `feat: add Census reports and indexes`.
- [ ] Push `origin feat/m5-census-0-1` and verify exact remote HEAD, parent,
  narrow scope, clean worktree, and no PR creation.
- [ ] Stop for independent exact-head review. M5-07, PR, and merge remain
  unauthorized.

Self-review:
- [ ] Reports and indexes are derived/release-bound only.
- [ ] No new Requirement, Capability, mapping, or semantic conclusion is
  created.
- [ ] Every ratio/statistic has an explicit denominator label.
- [ ] `UNRESOLVED_ANALYSIS` and `NO_REQUIREMENTS_APPLICABLE` remain separate.
- [ ] The original 98-file authoritative bundle remains unchanged.
- [ ] Two fresh runs are byte-identical.
