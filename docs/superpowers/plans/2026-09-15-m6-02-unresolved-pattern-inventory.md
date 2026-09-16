# M6-02 Unresolved Pattern Inventory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline execution). Steps use checkbox syntax for tracking.

**Goal:** Build an offline, deterministic, non-authoritative inventory of all
38,735 Census 0.1 UNRESOLVED_ANALYSIS cards using six overlapping source
grouping lenses, reproducible Opportunity records, reports, and worklists.

**Architecture:** Reuse the existing M1 structural and M3 analysis readers and
closure validators at an explicit-input seam. Add a focused inventory package
with immutable wire models, source-surface projection, exact/shape grouping,
atomic staging publication, independent validation, reporting, and a thin CLI
adapter. Candidate groups and Opportunities carry an explicit
NON_AUTHORITATIVE marker and never call M2/M4 mutation paths.

**Tech Stack:** Python 3.12+, frozen dataclasses, existing canonical JSON and
domain-digest helpers, JSONL, pytest, Ruff, mypy, and ignored dist output.

---

## Task 1: Define the test surface and synthetic fixtures

**Files:**
- Create: tests/inventory_fixtures.py
- Create: tests/test_inventory_projection.py
- Create: tests/test_inventory_grouping.py
- Create: tests/test_inventory_build.py
- Create: tests/test_inventory_reproduction.py
- Create: tests/test_inventory_cli.py

- [ ] Write fixture helpers for exact shared lines, shape-only literal
  differences, singleton groups, multi-face cards, null parent text, empty
  lines, multiline text, and lens overlap.
- [ ] Write assertions for the planned interfaces:

  ~~~python
  project_surfaces(records) -> tuple[SourceSurfaceV1, ...]
  group_surfaces(surfaces) -> tuple[CandidateGroupV1, ...]
  build_inventory(inputs, output) -> InventoryBuildResultV1
  validate_inventory(output) -> InventoryValidationResultV1
  ~~~

  Assert NON_AUTHORITATIVE records and no Requirement or Capability creation.
- [ ] Run the focused tests and observe the expected RED collection failure
  because the new inventory package does not yet exist:

  ~~~text
  C:\Python313\python.exe -m pytest tests/test_inventory_projection.py tests/test_inventory_grouping.py tests/test_inventory_build.py tests/test_inventory_reproduction.py tests/test_inventory_cli.py -q
  ~~~

## Task 2: Add immutable inventory models and identities

**Files:**
- Create: src/manafold_census/inventory/__init__.py
- Create: src/manafold_census/inventory/model.py
- Create: src/manafold_census/inventory/identity.py

- [ ] Implement frozen, slotted models for SourceSurfaceV1, SurfaceMemberV1,
  StructuralSummaryV1, CandidateGroupV1, CapabilityOpportunityV1,
  FileDescriptorV1, InventoryManifestV1, and InventoryReportV1.
- [ ] Enforce exact schema markers, NON_AUTHORITATIVE scope, strict types,
  sorted identity collections, recurrence status, and no semantic lifecycle
  values on candidate groups or Opportunities.
- [ ] Implement path-free domain-separated surface, group, and Opportunity
  identities with the existing canonical JSON and domain-digest helpers.
- [ ] Run the model and identity-focused tests and confirm expected failures
  have moved to the missing projection/grouping implementation.

## Task 3: Implement source projection and six grouping lenses

**Files:**
- Create: src/manafold_census/inventory/projection.py
- Create: src/manafold_census/inventory/grouping.py

- [ ] Project each StructuralCardRecordV1 into card-text, explicit face-text,
  and ability-line surfaces while preserving exact Oracle/source identity,
  face index, line index, raw text, null versus empty text, and scope.
- [ ] Implement CARD_TEXT_EXACT, FACE_TEXT_EXACT, and ABILITY_LINE_EXACT
  using only exact raw surface values.
- [ ] Implement policy m6-02.lexical-shape.v1 with only source self-name,
  brace-payload, numeric-literal, and stable-whitespace mechanical
  transformations. Retain raw and shaped text together.
- [ ] Implement CARD_TEXT_SHAPE, FACE_TEXT_SHAPE, and
  ABILITY_LINE_SHAPE. Do not Unicode-normalize, parse rules, or infer
  mechanics.
- [ ] Calculate occurrence count and distinct Oracle count independently,
  retain recurring and singleton groups, sort members deterministically, and
  compute source/structural summaries.
- [ ] Run projection and grouping tests until all synthetic edge cases pass.

## Task 4: Implement explicit input loading and atomic build

**Files:**
- Create: src/manafold_census/inventory/input.py
- Create: src/manafold_census/inventory/build.py

- [ ] Load only explicit source-lock, structural-output, analysis-output,
  M4-output, parent Census release ID, and output paths.
- [ ] Reuse existing M1/M3 closure validators and typed models. Verify source
  lock, M1 and M3 manifest identities, M4 manifest canonical bytes/schema,
  M4 manifest digest, M3 binding, and parent release identity.
- [ ] Select only records with exact outcome UNRESOLVED_ANALYSIS and require
  the selected identity set to be complete, unique, and exactly 38,735 for
  the real Census 0.1 inputs.
- [ ] Build only in a fresh staging directory, validate it, then atomically
  publish the requested output. Reject conflicting or non-empty outputs.
- [ ] Write surface inventory, candidate groups, recurring-group
  Opportunities with UNASSESSED planning state, deterministic worklists,
  manifest, and report.
- [ ] Run build and fail-closed tests, including assertions that M3/M4 inputs
  are not mutated.

## Task 5: Implement validation, reports, and CLI

**Files:**
- Create: src/manafold_census/inventory/validate.py
- Create: src/manafold_census/inventory/report.py
- Create: src/manafold_census/inventory/cli.py
- Modify: src/manafold_census/cli.py

- [ ] Validate exact file sets, canonical JSON/JSONL, descriptor hashes,
  counts, identity bindings, group/member closure, selected-union coverage,
  policies, recurrence, ordering, and NON_AUTHORITATIVE markers.
- [ ] Report selected cards, surfaces, groups by lens, recurring/singleton
  counts, recurring/singleton union coverage, Opportunity count, size
  distributions, top groups, and raw/shape examples.
- [ ] State repeatedly in reports that candidate grouping is
  non-authoritative and Opportunity count is not Capability count.
- [ ] Register explicit commands:

  ~~~text
  m6-02-inventory-build
  m6-02-inventory-check
  m6-02-inventory-report
  m6-02-inventory-reproduce
  ~~~

- [ ] Run CLI tests and help output; confirm unrelated commands retain their
  behavior.

## Task 6: Prove reproduction and record real evidence

**Files:**
- Create: docs/reports/2026-09-15-m6-02-unresolved-pattern-inventory.md
- Create: docs/reports/2026-09-15-m6-02-unresolved-pattern-inventory.json

- [ ] Run synthetic A/B builds in different temporary absolute paths with
  shuffled traversal and require identical file sets, bytes, identities, and
  tree digests.
- [ ] Run the real explicit-input build twice under:

  ~~~text
  dist/m6/inventory/m6-02-real-run-a
  dist/m6/inventory/m6-02-real-run-b
  ~~~

- [ ] Record observed counts only after the run. Keep evidence path-free and
  free of timestamps, machine names, usernames, and predeclared group targets.
- [ ] Require selected count 38,735, zero non-unresolved selections, zero
  missing/duplicate selected IDs, file-set parity, byte parity, path-free
  manifest, and offline regeneration.

## Task 7: Run quality gates, commit, and push

**Files:**
- Modify only the files listed above; do not change M2/M3/M4 authority,
  Census 0.1 evidence, README, packaging, or unrelated code.

- [ ] Run the focused suite, full pytest, Ruff format/check, mypy, and the
  applicable wheel/package smoke. Report any unaffected Windows gate
  accurately rather than inventing a result.
- [ ] Run git diff check, inspect the full origin/main-to-HEAD scope, verify
  ignored generated output, and confirm zero Requirements, Capabilities,
  links, mappings, or authority changes.
- [ ] Commit with:

  ~~~text
  feat: build M6-02 unresolved pattern inventory
  ~~~

- [ ] Push feat/m6-02-unresolved-pattern-inventory, verify local and remote
  heads match, leave the worktree clean, create no PR, and leave M6-02
  NOT_FROZEN with all later authorization flags NO.
