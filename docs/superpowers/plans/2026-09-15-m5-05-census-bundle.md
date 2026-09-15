# M5-05 Census Bundle Implementation Plan

> REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox syntax.

**Goal:** Build the first self-contained Census 0.1 bundle from the frozen SourceLock/M1/M3 input, reviewed M4 authority package, and real M4 snapshot without including reports or indexes in release identity.

**Architecture:** Add release/manifest.py for the closed CensusBundleManifestV1 wire model, component descriptors, population/schema/compatibility records, raw manifest digest, and non-self-referential census release ID. Add release/publish.py for exact tree copying and atomic staging/publish. Add release/bundle.py for explicit-input validation, nested M1/M3/authority/M4 reread, authority/publication parity, population checks, and atomic bundle build. Do not change existing M1/M3/M4 core builders and do not implement M5-06 reports/indexes.

**Tech Stack:** Python 3.12+, canonical JSON, JSON Schema Draft 2020-12, existing M5-02/M5-03/M5-04 validators, shutil/os atomic filesystem operations, pytest, Ruff, mypy, PowerShell.

---

### Task 1: Add failing bundle contract tests

Files:
- Create tests/test_census_bundle.py.
- Read tests/test_census_authority_package.py and tests/test_m5_m4_build.py for exact synthetic fixtures.

Steps:
- [ ] Test manifest round-trip, raw canonical manifest digest, release ID projection without release ID, fixed five authoritative component roles, population/schema/compatibility fields, and null parent lineage.
- [ ] Test a positive self-contained bundle build from synthetic M1/M3/authority/M4 fixtures and assert bundle reread and component descriptors.
- [ ] Test that reports, indexes, metadata, unexpected files, missing nested files, altered bytes, and an existing output path fail closed without replacing the existing output.
- [ ] Test the real-package-shaped bundle path and a zero-mapping rejected/unmapped authority package; both must use existing validators.
- [ ] Test the explicit CLI command with --input-lock, --authority-package, --source-lock, --structural-output, --analysis-output, --m4-output, and --output.
- [ ] Run: $env:PYTHONPATH='src'; & C:\Python313\python.exe -m pytest tests/test_census_bundle.py -q.
- [ ] Confirm RED because release/manifest.py, release/bundle.py, release/publish.py, and m5-bundle-build do not exist.

### Task 2: Implement CensusBundleManifestV1 and schema

Files:
- Create src/manafold_census/release/manifest.py.
- Create schemas/census-bundle-manifest.v1.schema.json.

Steps:
- [ ] Define the fixed schema census.census-bundle-manifest.v1, release version 0.1.0, and component roles source_lock, m1, m3, m4_authority, m4.
- [ ] Implement frozen component descriptor, population, schema-compatibility, bundle-compatibility, and manifest models with exact keys, closed paths/roles, digest identities, sorted components, and parent_census_release_id.
- [ ] Use manifest_sha256 as the raw SHA-256 of canonical manifest bytes without persisting that hash in the manifest.
- [ ] Compute census_release_id as censusrel_ plus domain_digest("census.census-release-id.v1", identity projection) where the projection excludes census_release_id, reports, indexes, metadata, timestamps, and absolute paths.
- [ ] Add strict JSON Schema constraints for the exact five roles, fixed paths, population counts, schema versions, compatibility, and null first parent.
- [ ] Add canonical round-trip and digest tests; run them GREEN.

### Task 3: Implement self-contained copy, nested validation, and atomic publication

Files:
- Create src/manafold_census/release/publish.py.
- Create src/manafold_census/release/bundle.py.
- Extend tests/test_census_bundle.py.

Steps:
- [ ] Implement an explicit bundle input descriptor using the already validated CensusInputLockV1, M3RequirementCorpusV1, authority package, M4 output, and their source paths.
- [ ] Validate the external lock, authority package, and real M4 snapshot before staging; require M4 parent null and exact Authority/M4 canonical record-set parity.
- [ ] Copy source-lock.json, every exact M1/M3 file, every authority-package file, and every M4 publication file into the fixed inputs/ tree. Copy bytes exactly; do not copy reports/indexes/metadata.
- [ ] Build in a fresh sibling staging directory. Write census-manifest.json only after all component copies and descriptor/population construction are complete.
- [ ] Reread staging independently: enforce the exact bundle file set, canonical manifest, component SHA/length/schema/aggregate bindings, nested M3 corpus/authority/M4 validation, population equality, parent null, and Authority/M4 parity.
- [ ] Remove staging on any failure and atomically os.replace the validated staging root to the requested final output only after every gate passes.
- [ ] Verify an existing output directory is never overwritten and a failed validation leaves no final manifest.

### Task 4: Add explicit m5-bundle-build command

Files:
- Modify src/manafold_census/release/commands.py.
- Modify src/manafold_census/release/cli.py.
- Modify src/manafold_census/cli.py only as needed through the existing M5 parser seam.
- Modify justfile.
- Extend tests/test_census_bundle.py.

Steps:
- [ ] Add m5-bundle-build requiring --input-lock, --authority-package, --source-lock, --structural-output, --analysis-output, --m4-output, and --output.
- [ ] Run the existing M5-02 lock gate first with all explicit paths, then the bundle builder. Missing paths report BLOCKED; mismatches/corruption report FAIL.
- [ ] Print m4-manifest-sha256, census-release-id, census-manifest-sha256, bundle-authoritative-components=5, bundle-reread=PASS, and m5-bundle-build=PASS only after atomic publication.
- [ ] Do not add reports, indexes, Explorer, release packaging, or a generalized non-synthetic m4 command.
- [ ] Run focused CLI tests and m5-bundle-build --help.

### Task 5: Build Census 0.1, verify, commit, push, and stop

Files:
- Generated ignored output only: dist/bundle/manafold-census-0.1.0.

Steps:
- [ ] Run the explicit real command using the frozen lock, authority package, M1/M3, and real M4 run-A paths.
- [ ] Verify the bundle contains only census-manifest.json and fixed inputs/authoritative files; no reports/indexes/metadata exist.
- [ ] Run a second explicit bundle build into run-B and compare all bundle bytes and manifest identities.
- [ ] Run full pytest, Ruff format/check, mypy, LOC budget, fresh-wheel smoke, and the explicit real m5-bundle-build.
- [ ] Stage only the M5-05 plan, manifest/bundle/publish code, schema, CLI/just changes, and tests. Do not stage generated dist output.
- [ ] Commit with message: feat: publish first Census 0.1 bundle.
- [ ] Push origin feat/m5-census-0-1 and verify remote HEAD, parent, exact scope, clean worktree, and no PR.
- [ ] Stop for independent exact-head review. M5-06, reports, indexes, query, Explorer, PR, and merge remain unauthorized.

Self-review:
- [ ] Reports, indexes, and metadata do not affect census_release_id.
- [ ] The manifest has no self-referential manifest hash.
- [ ] parent_census_release_id is null for the first bundle.
- [ ] All nested authoritative bytes are copied unchanged and reread.
- [ ] No hidden artifact discovery, latest selection, source/M1/M3 rerun, or semantic expansion occurs.
