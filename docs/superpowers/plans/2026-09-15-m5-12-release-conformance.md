# M5-12 Release Conformance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Validate the frozen Census 0.1 release inputs through two fresh bundle/derived candidate runs, prove authoritative and report/index byte parity, and write auditable release evidence without adding semantic or M4 authority.

**Architecture:** Add `release/conformance.py` as a small orchestration and parity seam. It receives every authoritative input path explicitly, calls the existing M5-05 bundle and M5-06 derived builders twice into a fresh candidate workspace, rereads both results through the frozen validators, compares complete authoritative trees and the exact ten derived files, and writes one canonical evidence document only after all hard gates pass. The CLI and Justfile expose this as an explicit maintainer command.

**Tech Stack:** Python 3.12+, existing M5-02 through M5-06 validators/builders, canonical JSON, streamed SHA-256, pytest, Ruff, mypy, PowerShell.

---

### Task 1: Add failing release-conformance tests

**Files:**
- Create: `tests/test_m5_release_conformance.py`
- Read-only references: `src/manafold_census/release/bundle.py`, `src/manafold_census/reports/build.py`, `src/manafold_census/release/manifest.py`, `docs/superpowers/specs/2026-09-15-m5-census-0-1-design.md`

- [ ] **Step 1: Write the synthetic two-candidate test.**

Build the existing synthetic M5 fixture, write its lock, and call the future `run_release_conformance` function with explicit lock, SourceLock, M1, M3, authority, M4, output-root, and evidence paths. Assert that the result creates `bundle-a`, `bundle-b`, `derived-a`, and `derived-b`; every hard gate is `PASS`; the experimental Windows EXE parity gate is not in the hard-gate map; the evidence file is canonical JSON; and the result records 98 authoritative and 108 derived files.

- [ ] **Step 2: Add failure/immutability tests.**

Assert that a pre-existing candidate workspace is rejected without changing its sentinel file, and that an evidence path is not written when candidate construction fails. Assert that the conformance module contains no call to `build_real_m4_snapshot` and that its hard-gate set excludes Windows EXE byte parity.

- [ ] **Step 3: Run the focused tests and verify RED.**

~~~powershell
$env:PYTHONPATH='src'; & C:\Python313\python.exe -m pytest tests/test_m5_release_conformance.py -q
~~~

Expected: collection fails because the release-conformance seam does not yet exist.

### Task 2: Implement the release-conformance seam

**Files:**
- Create: `src/manafold_census/release/conformance.py`
- Test: `tests/test_m5_release_conformance.py`

- [ ] **Step 1: Add explicit candidate orchestration.**

Implement:

~~~python
def run_release_conformance(
    *,
    input_lock_path: str | Path,
    source_lock_path: str | Path,
    structural_output_directory: str | Path,
    analysis_output_directory: str | Path,
    authority_package_directory: str | Path,
    m4_output_directory: str | Path,
    output_root: str | Path,
    evidence_path: str | Path,
) -> ReleaseConformanceResultV1:
~~~

Load and validate the existing `CensusInputLockV1` through explicit provisioning, require its M3 corpus, reject an existing/nonempty output root, and call `build_census_bundle` twice with the exact frozen M5-02/M5-03/M5-04 inputs. Call `build_census_derived` once for each fresh bundle. Do not call M3 or M4 builders, discover artifacts, select latest paths, or mutate any authoritative input.

- [ ] **Step 2: Add complete byte-parity checks.**

Use streamed `measure_file` values and a versioned conformance tree digest. Require identical relative file sets and exact bytes for every file in both 98-file bundle trees. Separately compare the sorted ten paths in `reports/` and `indexes/` from both 108-file derived trees. Also require equal Census release IDs, manifest SHAs, report/index identities, and population values.

- [ ] **Step 3: Add typed result and canonical evidence.**

Return a frozen `ReleaseConformanceResultV1` with release identity, candidate counts/digests, hard-gate statuses, and the explicit experimental Windows EXE parity status. Write `evidence_path` only after success using canonical JSON bytes, with relative labels such as `bundle-a` and `derived-b`; never persist absolute paths or a self-hash. Reject an existing evidence file before running.

- [ ] **Step 4: Run the focused tests GREEN.**

~~~powershell
$env:PYTHONPATH='src'; & C:\Python313\python.exe -m pytest tests/test_m5_release_conformance.py -q
~~~

### Task 3: Add the maintainer CLI and Justfile seam

**Files:**
- Modify: `src/manafold_census/release/cli.py`
- Modify: `src/manafold_census/release/commands.py`
- Modify: `justfile`
- Extend: `tests/test_m5_release_conformance.py`

- [ ] **Step 1: Register the explicit command.**

Add `m5-release-conformance` with required flags:

~~~text
--input-lock
--source-lock
--structural-output
--analysis-output
--authority-package
--m4-output
--output-root
--evidence
~~~

Dispatch to the conformance command and print every hard gate, candidate tree digest, file count, Census release identity, report/index parity, `windows-exe-byte-parity=EXPERIMENTAL`, and `m5-release-conformance=PASS` only after evidence publication succeeds.

- [ ] **Step 2: Add the explicit Just recipe.**

Add:

~~~text
m5-release-conformance input_lock source_lock structural_output analysis_output authority_package m4_output output_root evidence:
    python -m manafold_census.cli m5-release-conformance --input-lock "{{input_lock}}" --source-lock "{{source_lock}}" --structural-output "{{structural_output}}" --analysis-output "{{analysis_output}}" --authority-package "{{authority_package}}" --m4-output "{{m4_output}}" --output-root "{{output_root}}" --evidence "{{evidence}}"
~~~

- [ ] **Step 3: Test CLI success and fail-closed paths.**

Use the synthetic fixture to invoke `main` with all eight required M5-12 flags, assert the PASS lines and canonical evidence, and assert missing/invalid explicit paths return nonzero without writing evidence.

### Task 4: Run real release conformance and write evidence

**Files:**
- Generated ignored outputs: `dist/release-conformance/`
- Create: `docs/reports/2026-09-15-m5-census-0-1-release-conformance.md`

- [ ] **Step 1: Run the explicit real command twice through the conformance seam.**

Use:

~~~powershell
$env:PYTHONPATH='src'; & C:\Python313\python.exe -m manafold_census.cli m5-release-conformance --input-lock locks/census-0.1-input-lock.v1.json --source-lock source-locks/scryfall-oracle-v1.json --structural-output dist/structural/scryfall-oracle-v1-run-a --analysis-output dist/analysis/m3-census-0-1-real-run-a --authority-package reviewed/m4/census-0.1 --m4-output dist/capability/m4-census-0-1-real-run-a --output-root dist/release-conformance/2026-09-15-real --evidence docs/reports/2026-09-15-m5-census-0-1-release-conformance.json
~~~

The command must build fresh `bundle-a`, `bundle-b`, `derived-a`, and `derived-b` under the explicit ignored output root and must not overwrite an existing root or evidence file.

- [ ] **Step 2: Write the Markdown evidence document from observed output.**

Record the exact implementation HEAD, explicit relative inputs, two candidate identities, complete file counts, tree digests, hard-gate statuses, and the prior frozen M5-00 through M5-11 gate references. Record `WINDOWS_EXE_BYTE_PARITY_GATE = EXPERIMENTAL` as non-hard and do not claim physical network isolation of a runner.

- [ ] **Step 3: Verify the real evidence.**

Require:

~~~text
CENSUS_AUTHORITATIVE_BYTES_PARITY = PASS
REPORT_INDEX_BYTES_PARITY          = PASS
EXPLORER_FUNCTIONAL_REBUILD       = PASS
WINDOWS_PACKAGE_SMOKE              = PASS
WINDOWS_EXE_BYTE_PARITY_GATE      = EXPERIMENTAL
release candidate reproducible     = PASS
release candidate auditable        = PASS
~~~

### Task 5: Verify, commit, push, and stop for exact-head review

**Files:**
- `src/manafold_census/release/conformance.py`
- `src/manafold_census/release/cli.py`
- `src/manafold_census/release/commands.py`
- `justfile`
- `tests/test_m5_release_conformance.py`
- `docs/reports/2026-09-15-m5-census-0-1-release-conformance.json`
- `docs/reports/2026-09-15-m5-census-0-1-release-conformance.md`
- `docs/superpowers/plans/2026-09-15-m5-12-release-conformance.md`

- [ ] **Step 1: Run quality and full tests.**

~~~powershell
C:\Python313\python.exe -m ruff format --check .
C:\Python313\python.exe -m ruff check .
$env:PYTHONPATH='src'; & C:\Python313\python.exe -m mypy src/manafold_census
$env:PYTHONPATH='src'; & C:\Python313\python.exe -m pytest -q
~~~

- [ ] **Step 2: Verify scope.**

Confirm no new M4 record, semantic coverage, source acquisition, network call, M6 code, generated `dist` output, or absolute path appears in tracked evidence. Confirm Windows EXE parity remains experimental and is not a required hard gate.

- [ ] **Step 3: Commit and push.**

~~~powershell
git add -- justfile src/manafold_census/release tests/test_m5_release_conformance.py docs/reports/2026-09-15-m5-census-0-1-release-conformance.json docs/reports/2026-09-15-m5-census-0-1-release-conformance.md docs/superpowers/plans/2026-09-15-m5-12-release-conformance.md
git diff --cached --name-only
git commit -m "feat: add Census 0.1 release conformance"
git push origin feat/m5-census-0-1
~~~

- [ ] **Step 4: Verify exact head and stop.**

~~~powershell
git status --porcelain=v1
git rev-parse HEAD
git rev-parse origin/feat/m5-census-0-1
gh pr list --head feat/m5-census-0-1 --state open --json number,title,url
~~~

Leave `M5_12_STATUS = NOT_FROZEN`, `M6_AUTHORIZED = NO`, `PR_AUTHORIZED = NO`, and `MERGE_AUTHORIZED = NO` for independent exact-head review.
