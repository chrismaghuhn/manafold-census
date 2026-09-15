# M5-03 Reviewed Authority Package Implementation Plan

> REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox syntax.

**Goal:** Persist and validate the first real Census 0.1 M4 authority package for the five locked M3 Requirements without building or publishing an M4 snapshot.

**Architecture:** Add release/authority_package.py as the sole package manifest, digest, descriptor, canonical JSONL reread, writer, and cross-layer validator. Reuse the existing typed M4 models. The real package contains one reviewed atomic draw-card Capability, five accepted SRA records, five reviewed active links, and five MAPPED decisions; relations and evolution stay empty. Do not call build_reference_m4.

**Tech Stack:** Python 3.12+, dataclasses, canonical JSON, JSON Schema Draft 2020-12, existing M2/M3/M4 models, pytest, Ruff, mypy, PowerShell.

---

### Task 1: Test the authority-package contract first

Files:
- Create tests/test_census_authority_package.py.
- Reuse the synthetic M3 and M4 fixture helpers already present in tests.

Steps:
- [ ] Write tests for manifest digest non-self-reference, exact seven package files, descriptor byte/count checks, canonical JSONL, exact five selected IDs, one SRA per Requirement, stale M3/wire/review/resolution rejection, active-link review/SRA binding, definition review and multi-source activation, mapping coverage, and unchanged M2 wires.
- [ ] Construct the positive test package only with existing CapabilityDefinitionV1, CapabilityReviewRecordV1, SourceRequirementAdmissibilityV1, RequirementCapabilityLinkV1, and RequirementMappingDecisionV1 constructors.
- [ ] Run: $env:PYTHONPATH='src'; & C:\Python313\python.exe -m pytest tests/test_census_authority_package.py -q.
- [ ] Confirm RED because release/authority_package.py does not exist.

### Task 2: Implement package wire models and schema

Files:
- Create src/manafold_census/release/authority_package.py.
- Create schemas/census-m4-authority-package.v1.schema.json.

Steps:
- [ ] Define AUTHORITY_PACKAGE_SCHEMA as census.m5-m4-authority-package.v1, the same digest domain, campaign m5.census-0.1, and these exact files: capability-definitions.jsonl, review-authority.jsonl, capability-relations.jsonl, requirement-admissibility.jsonl, links.jsonl, mapping-decisions.jsonl, evolution.jsonl.
- [ ] Implement frozen AuthorityFileDescriptorV1, AuthorityReviewPolicyV1, AuthorityPackageManifestV1, and AuthorityPackageContentsV1.
- [ ] Make the manifest fields exactly schema, campaign_id, m3_analysis_manifest_sha256, m4_requirement_set_digest, selected_requirement_ids, record_file_descriptors, review_policy, authority_package_digest.
- [ ] Compute authority_package_digest from every manifest field except authority_package_digest with domain separation; include no timestamps, absolute paths, or self-hash.
- [ ] Add strict Draft 2020-12 schema constraints, closed descriptor paths, digest patterns, selected srq IDs, and fixed review-policy multiplicities.
- [ ] Implement write_authority_package and load_authority_package. Refuse nonempty output directories, sort with existing M4 sort keys, write nonempty JSONL with final LF, write empty JSONL as zero bytes, and write the manifest without a trailing LF.
- [ ] Run the focused tests and confirm manifest/reread tests are GREEN.

### Task 3: Implement exact M5-03 validation and explicit CLI

Files:
- Modify src/manafold_census/release/authority_package.py.
- Modify src/manafold_census/release/commands.py, src/manafold_census/cli.py, and justfile.
- Extend tests/test_census_authority_package.py.

Steps:
- [ ] Implement validate_authority_package(package_dir, lock, corpus).
- [ ] Bind package manifest to the validated CensusInputLockV1 and M3RequirementCorpusV1.
- [ ] Require exactly five selected IDs equal to the sorted corpus IDs, exactly one accepted SRA per selected Requirement, one active reviewed direct link per Requirement, one active multi-source Capability definition, one definition review, one accepted link review per link, one MAPPED decision per Requirement, and empty relations/evolution.
- [ ] Validate exact M3 manifest, Requirement wire, M2 review/resolution, SRA route, link review, and mapping identities; then call existing validate_m4_inputs. Never mutate M2 and never call build_reference_m4.
- [ ] Add m5-authority-check requiring explicit --package, --lock, --source-lock, --structural-output, and --analysis-output. Run the existing M5-02 lock gate first. Missing paths are BLOCKED, malformed/mismatched data is FAIL, and only a complete package exits zero with m5-authority=PASS.
- [ ] Run focused tests and m5-authority-check --help.

### Task 4: Build the real Census 0.1 authority package

Files:
- Create reviewed/m4/census-0.1/authority-manifest.json.
- Create reviewed/m4/census-0.1/capability-definitions.jsonl.
- Create reviewed/m4/census-0.1/review-authority.jsonl.
- Create reviewed/m4/census-0.1/capability-relations.jsonl.
- Create reviewed/m4/census-0.1/requirement-admissibility.jsonl.
- Create reviewed/m4/census-0.1/links.jsonl.
- Create reviewed/m4/census-0.1/mapping-decisions.jsonl.
- Create reviewed/m4/census-0.1/evolution.jsonl.

Steps:
- [ ] Use the validated M5-02 corpus, campaign m5.census-0.1, SRA authority m4.source-requirement-admissibility/1, Capability review authority m4.capability-review/1, and reviewer maintainer:chris.
- [ ] Create one atomic EFFECT/DRAW_CARDS Capability with required DRAW_CARDS_DRAWER and DRAW_CARDS_QUANTITY dimensions, active lifecycle, all five exact Requirement references, an accepted MULTI_SOURCE_REUSE definition review, five accepted SRA records, five active direct links with exact known bindings, five accepted link reviews, and five MAPPED decisions.
- [ ] Keep relations and evolution empty. Create no real M4 output, bundle, Explorer, release, or M5-04 artifact.
- [ ] Run explicitly:
  m5-authority-check --package reviewed/m4/census-0.1 --lock locks/census-0.1-input-lock.v1.json --source-lock source-locks/scryfall-oracle-v1.json --structural-output dist/structural/scryfall-oracle-v1-run-a --analysis-output dist/analysis/m3-census-0-1-real-run-a
- [ ] Require all M5-02 checks and package/M4 validation to be PASS.

### Task 5: Verify, commit, push, and stop

Steps:
- [ ] Run Ruff format check, Ruff check, mypy, the full pytest suite, the explicit real M5-03 check, and existing reproduction/synthetic M3/M4 checks with PYTHONPATH=src and C:\Python313\python.exe.
- [ ] Verify no M4 publication, Census bundle, Explorer, or release artifact exists.
- [ ] Review git diff --check and git diff --stat. Stage only the listed M5-03 files and this plan. Commit with feat: add Census 0.1 reviewed authority package.
- [ ] Push origin feat/m5-census-0-1 and verify ls-remote, HEAD, parent, and clean worktree.
- [ ] Stop for independent exact-head review. M5-04, PR creation, and merge remain unauthorized.

Self-review:
- [ ] No placeholder, TODO, latest discovery, implicit artifact selection, M2 mutation, or M5-04 behavior.
- [ ] The package digest is non-self-referential.
- [ ] Every persisted M4 record is an existing frozen wire type.
- [ ] SRA multiplicity is exactly one per selected Requirement.
