# M5-04 Real M4 Snapshot Implementation Plan

> REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox syntax.

**Goal:** Build the first real M4 snapshot from the frozen M5-02 input lock and M5-03 reviewed authority package, with genesis lineage, independent reread, and exact authority/publication record-set parity.

**Architecture:** Add release/m4_orchestration.py as a separate real-M4 adapter. It validates the already explicit M5-02 input and M5-03 package, stages build_reference_m4 output in a temporary directory, rereads it through the existing M4 reader, reruns frozen M4 validation, compares every authority record set after flattening M4 link/mapping shards, and atomically publishes only after all gates pass. Do not modify capability/build.py and do not generalize the synthetic M4 CLI.

**Tech Stack:** Python 3.12+, existing frozen M4 build/reread/validation, canonical JSON bytes, pytest, Ruff, mypy, PowerShell.

---

### Task 1: Add failing orchestration and CLI tests

Files:
- Create tests/test_m5_m4_build.py.
- Read tests/test_census_authority_package.py for typed package fixtures.

Steps:
- [ ] Add a positive test that constructs a synthetic M3 input and complete typed authority package, calls build_real_m4_snapshot, asserts output publication, parent_m4_manifest_sha256 is None, and exact record-set parity is PASS.
- [ ] Add a positive test with five rejected SRAs, no definitions/links/reviews, and five UNMAPPED/NO_REVIEWED_CAPABILITY decisions; the real-M4 seam must accept it because the frozen M4 validator accepts it.
- [ ] Add tests that an existing output directory is never overwritten and a missing/invalid package fails before final publication.
- [ ] Add a CLI test requiring explicit --input-lock, --authority-package, --source-lock, --structural-output, --analysis-output, and --output, and asserting m5-m4-build=PASS.
- [ ] Run: $env:PYTHONPATH='src'; & C:\Python313\python.exe -m pytest tests/test_m5_m4_build.py -q.
- [ ] Confirm RED because release/m4_orchestration.py and m5-m4-build do not exist.

### Task 2: Implement the isolated real-M4 orchestration seam

Files:
- Create src/manafold_census/release/m4_orchestration.py.
- Modify tests/test_m5_m4_build.py.

Steps:
- [ ] Implement M5M4BuildError and M5M4BuildResultV1.
- [ ] Implement build_real_m4_snapshot(authority_package_directory, m3_input, lock, corpus, output_directory).
- [ ] Require exact CensusInputLockV1, M3RequirementCorpusV1, and FrozenM3InputV1 types; require corpus and lock M3/Requirement-set identity equality.
- [ ] Validate the authority package with validate_authority_package before starting the build.
- [ ] Reject an existing final output path. Create a temporary sibling staging root and call frozen build_reference_m4 with parent_m4_manifest_sha256=None and parent_m4_manifest=None.
- [ ] Reread staging through the existing capability.build._reread_output function and rerun frozen validate_m4_inputs on the reread records.
- [ ] Require reread.manifest.parent_m4_manifest_sha256 is None and require M3 manifest, M4 Requirement-set digest, and schemas to match the lock/package.
- [ ] Compare canonical wire-byte multisets for definitions, reviews, relations, admissibility, evolution, links, and mapping decisions. Flatten published links and mapping-decision shards before comparison. Raise on any parity mismatch and leave no final output.
- [ ] Atomically os.replace the validated staging root to the requested final output, then return the manifest and PASS parity result. Do not create a bundle, Explorer, report, or later lineage.

### Task 3: Add the explicit m5-m4-build command

Files:
- Modify src/manafold_census/release/commands.py.
- Modify src/manafold_census/cli.py.
- Modify justfile.
- Modify tests/test_m5_m4_build.py.

Steps:
- [ ] Add m5-m4-build with required explicit flags: --input-lock, --authority-package, --source-lock, --structural-output, --analysis-output, and --output.
- [ ] Load and validate the M5-02 lock with the existing explicit provisioning paths, print every lock check, and stop with BLOCKED/FAIL if it does not PASS.
- [ ] Call build_real_m4_snapshot with the returned corpus and explicit FrozenM3InputV1. Print m4-parent=null, authority-m4-record-set-parity=PASS, m4-manifest-sha256, and m5-m4-build=PASS only after atomic publication.
- [ ] Do not add a non-synthetic mode to m4-build/m4-check/m4-report.
- [ ] Run the focused tests and m5-m4-build --help.

### Task 4: Run the first real M4 snapshot

Files:
- Generated ignored output only: dist/capability/m4-census-0-1-real-run-a.

Steps:
- [ ] Run the explicit command with locks/census-0.1-input-lock.v1.json, reviewed/m4/census-0.1, source-locks/scryfall-oracle-v1.json, dist/structural/scryfall-oracle-v1-run-a, dist/analysis/m3-census-0-1-real-run-a, and dist/capability/m4-census-0-1-real-run-a.
- [ ] Verify parent_m4_manifest_sha256=null, full M4 reread/validator PASS, and all seven authority/publication record-set comparisons PASS.
- [ ] Verify no Census bundle, Explorer, or release artifact is produced.

### Task 5: Verify, commit, push, and stop for independent review

Steps:
- [ ] Run focused and full pytest, Ruff format/check, mypy, LOC budget, the real m5-m4-build, fresh Synthetic M3/M4 checks, reproduction, and Fresh-Wheel-Smoke.
- [ ] Review git diff --check and stage only the M5-04 plan, orchestration/CLI/just changes, and M5-04 tests. Do not stage generated dist output.
- [ ] Commit with message: feat: build first real M4 snapshot.
- [ ] Push origin feat/m5-census-0-1 and verify remote HEAD, parent, exact scope, and clean worktree.
- [ ] Stop for independent exact-head review. M5-05, bundle, Explorer, PR, and merge remain unauthorized.

Self-review:
- [ ] First real M4 parent is always null; synthetic M4 is never a parent.
- [ ] Authority/publication parity compares parsed canonical record sets, not physical sharding.
- [ ] No implicit artifact discovery, latest selection, source rerun, M3 rerun, M2 mutation, or automatic candidate promotion.
- [ ] No M5-05 output exists.
