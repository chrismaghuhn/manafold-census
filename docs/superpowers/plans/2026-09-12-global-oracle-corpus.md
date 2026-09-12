# Global Oracle Corpus Task 01 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pin the observed Scryfall `oracle_cards` gzip JSONL snapshot and build a deterministic source-record index with 16 Oracle-ID shards.

**Architecture:** Keep source acquisition and corpus indexing in separate subpackages. Reuse the existing immutable lifecycle models and canonical/digest primitives; add only a small aggregate index identity/report around the existing single-file artifact contract.

**Tech Stack:** Python 3.12+ standard library (`urllib`, `gzip`, `json`, `hashlib`, `tempfile`), existing `jsonschema`, pytest, Ruff, mypy, setuptools wheel build, and the current `justfile`/GitHub Actions workflow.

---

## Files and ownership

- `src/manafold_census/source/config.py`: typed loading of the committed acquisition specification.
- `src/manafold_census/source/errors.py`: shared fail-closed acquisition exception.
- `src/manafold_census/source/scryfall.py`: observed Scryfall metadata parsing, config-driven HTTPS discovery, refresh, and proposal writing.
- `src/manafold_census/source/transfer.py`: streamed transfer, digest-addressed cache validation, pinned fetch, and atomic lock writing.
- `src/manafold_census/source/__init__.py`: public source package exports.
- `src/manafold_census/corpus/index.py`: gzip JSONL source-record parsing, identity validation, deterministic shard files, shard validation, and aggregate index digest.
- `src/manafold_census/corpus/build.py`: source-lock loading, cache resolution, dataset/study/artifact/report construction, and output-directory orchestration.
- `src/manafold_census/corpus/check.py`: canonical output reading, provenance reconstruction, manifest closure, and task-specific contract validation.
- `src/manafold_census/corpus/manifest.py`: the separate aggregate manifest that binds all 16 shard descriptors.
- `src/manafold_census/corpus/__init__.py`: public corpus package exports.
- `src/manafold_census/cli.py`: minimal `source-discover`, `source-refresh`, `source-fetch-pinned`, `corpus-build`, and offline `corpus-check` commands, preserving `doctor` and `reproduce`.
- `config/sources/scryfall-oracle.v1.json`: committed discovery configuration with no machine-specific state.
- `source-locks/scryfall-oracle-v1.json`: the exact real snapshot lock produced after offline implementation gates pass.
- `tests/test_source.py`: offline discovery/download/cache/lock behavior and all source failure cases.
- `tests/test_corpus.py`: offline record validation, sorting/sharding, aggregate identity, report/manifests, and corruption cases.
- `tests/test_maintainability.py`: recursive module guard remains authoritative for the new packages.
- `README.md`, `ARCHITECTURE.md`, `CONTRIBUTING.md`: concise Task-01 source-bounded workflow and no-semantic-inference documentation.
- `.github/workflows/ci.yml`, `justfile`: offline synthetic and fresh-wheel gates, with live acquisition kept explicit.

## Task 1: Add failing source-contract tests

- [ ] Add tests that construct fake discovery and download responses without network access, including same-ID refreshes and exact pinned fetches.
- [ ] Assert exactly one `oracle_cards` entry is selected, `jsonl_download_uri` is required, HTTPS is required, and observed gzip JSONL metadata is accepted.
- [ ] Assert explicit `User-Agent` and `Accept` request headers.
- [ ] Assert streamed bytes are written to a temporary file, measured once, and atomically promoted only after complete length/digest verification.
- [ ] Assert HTTP failures, unsupported metadata, missing locator, truncated content, and mismatched existing cache fail without trusting or replacing the cache.
- [ ] Assert `SourceLock` round-trips through the existing schema/model and its digest binds the exact compressed bytes.
- [ ] Run `python -m pytest tests/test_source.py -q`; the new imports must fail because the source package does not exist yet.

## Task 2: Implement source acquisition minimally

- [ ] Add `BulkDataObservation` with validated upstream UUID, `oracle_cards` type, `jsonl_download_uri`, `updated_at`, `compressed_size`, and the fixed observed representation `gzip-jsonl`.
- [ ] Implement `discover_oracle_cards()` with one HTTPS `urllib.request` request, config-driven headers, JSON object/list validation, exactly-one selection, and no fallback dataset.
- [ ] Implement `download_source()` using `tempfile.NamedTemporaryFile` in the destination directory, bounded reads, optional advertised-length checking, `measure_file()` after close, and `os.replace()` only on success.
- [ ] Derive the ignored cache filename from the downloaded SHA-256. Reuse only a matching expected digest/length; keep same-ID refreshes separate and fail on mismatched cache bytes.
- [ ] Build the existing `SourceArtifact` and `SourceLock` models with media type from the response `Content-Type`, and write canonical lock JSON to the requested repository path.
- [ ] Run `python -m pytest tests/test_source.py -q`; all source tests must pass.

## Task 3: Add failing corpus-index tests

- [ ] Add temporary gzip JSONL fixtures with valid records and records whose input order differs from Oracle-ID order.
- [ ] Assert only four inventory fields are emitted, exact decompressed raw line bytes are hashed, every record lands in the shard named by its first lowercase Oracle-ID hex digit, all 16 shard files exist, and each shard ends with LF when non-empty.
- [ ] Assert duplicate/missing/invalid Oracle ID, invalid source card UUID, missing/empty name, non-object JSON, malformed JSONL, and non-card records fail.
- [ ] Assert each shard is Oracle-ID sorted, unexpected/missing shards and misplaced/out-of-order records fail, and the aggregate digest is stable across repeated builds.
- [ ] Run `python -m pytest tests/test_corpus.py -q`; the new corpus imports must fail because the corpus package does not exist yet.

## Task 4: Implement deterministic corpus indexing

- [ ] Add `RecordIndexEntry` and a streaming gzip JSONL iterator that hashes each raw line before JSON parsing and never retains full card objects.
- [ ] Validate Scryfall `object=card`, canonical UUID syntax for `oracle_id` and `id`, and non-empty `name`; normalize UUID text only for the compact inventory output.
- [ ] Sort compact entries by normalized `oracle_id`, write exactly `0.jsonl` through `f.jsonl`, encode each line with `canonical_json_bytes(entry)` plus one LF, and reject a non-empty output directory.
- [ ] Implement shard inspection that validates the exact 16-file set, line JSON shape, shard assignment, strict intra-shard ordering, and aggregate descriptor list of path/digest/length/count.
- [ ] Use domain `census.oracle-record-index.v1` for the aggregate digest.
- [ ] Run `python -m pytest tests/test_corpus.py -q`; all corpus tests must pass.

## Task 5: Add build/report/manifests and CLI tests

- [ ] Add tests for source-lock loading and wrong source-file digest rejection, deterministic `DatasetManifest`, `StudySpec`, `ArtifactManifest`, and source-fact corpus report output.
- [ ] Add two-run parity tests using the same temporary pinned gzip bytes and separate empty output directories; compare file names and every byte.
- [ ] Add CLI tests for non-zero failure on invalid/incomplete inputs and an offline `corpus-check` synthetic run.
- [ ] Run the focused tests; failures should identify missing build and CLI behavior.

## Task 6: Implement build orchestration and commands

- [ ] Resolve `.cache/sources/scryfall/<sha256>.jsonl.gz` from the committed lock without placing a local path in any semantic document.
- [ ] Build the existing `DatasetManifest` (`scryfall-oracle-corpus`, `1.0.0`, `scryfall-oracle-record-index.v1`, actual count), a deterministic `StudySpec`, a separate canonical `IndexRecordManifest`, and an `ArtifactManifest` whose `content_sha256`/`byte_length` bind the exact index-manifest bytes.
- [ ] Emit canonical `dataset-manifest.json`, `study-spec.json`, `artifact-manifest.json`, and a small deterministic `corpus-report.json` with source facts, `SOURCE_FACT`, counts, source digest/length, shard counts, and aggregate index digest.
- [ ] Add `source-discover`, `source-refresh`, `source-fetch-pinned`, `corpus-build`, and offline `corpus-check` to the existing argparse CLI without a framework dependency; preserve current commands and non-zero error handling.
- [ ] Add the acquisition config and update package data so installed-resource lookup remains valid.
- [ ] Run focused tests, then `python -m pytest -q`; all must pass before lint/type gates.

## Task 7: Documentation, maintainability, and CI golden path

- [ ] Update README/architecture/contributing with source-bounded completeness, compressed-vs-record identity, ignored raw cache, explicit refresh, 16-shard output, and no semantic inference.
- [ ] Keep `just check` network-independent; add `source-discover`, `source-refresh`, `source-fetch-pinned`, `corpus-build`, and synthetic `corpus-check` recipes.
- [ ] Add CI steps for wheel build and a fresh non-editable install executed outside the repository CWD, including import, doctor, schema lookup, and synthetic reproduction.
- [ ] Run the recursive LOC test and inspect every production module; no new module may exceed 500 lines.

## Task 8: Offline verification and real acquisition evidence

- [ ] Run Python version, format, Ruff, mypy, pytest, synthetic reproduction, wheel build, fresh-wheel smoke, and maintainability gates; record each as `PASS`, `FAIL`, `BLOCKED`, or `NOT_RUN`.
- [ ] Run one live `source-discover`/`source-refresh` and verify the committed source with `source-fetch-pinned`; record the observed source ID/update/locator/media type, compressed SHA-256/length, record and shard counts, and aggregate digest without exposing host details.
- [ ] Build twice from the same pinned compressed cache bytes into two fresh directories and require exact file-set, shard, manifest, report, and aggregate-digest parity.
- [ ] Inspect the complete diff and verify no raw bulk data, semantic inference, database, Rust, LLM, or Task-02 changes exist.

## Task 9: Single final commit

- [ ] Verify `git status --short` contains only the Task-01 files and the generated cache/output paths remain ignored.
- [ ] Create exactly one local commit with message `feat: acquire and index the global oracle corpus`.
- [ ] Verify the final commit parent, SHA, worktree cleanliness, and absence of push/PR/Task-02 activity. Do not amend, push, or create a PR afterward.
