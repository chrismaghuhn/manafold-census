
# CENSUS_02 Global Structural Card Census Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to execute this plan task-by-task after independent authorization. Steps use checkbox syntax for tracking.

**Goal:** Implement the frozen M1 source-fact structural census for every record in the exact Task 01 pinned snapshot, with immutable typed records, deterministic shards, manifest/report closure, offline reproduction, and full-corpus evidence.

**Architecture:** A dedicated structural package will reuse Task 01 identity parsing and the generic lifecycle models without changing their contracts. It will stream the pinned gzip JSONL source into immutable structural records, sort and shard canonical JSONL by normalized Oracle ID, bind the exact structural manifest bytes through ArtifactManifestV1, and reconstruct every output fact during validation. Each numbered task produces one independently reviewable commit and then stops.

**Tech Stack:** Python 3.12+, standard-library gzip/json/hashlib/tempfile/pathlib/dataclasses, existing jsonschema/referencing validation, pytest, Ruff, mypy, setuptools wheel, the existing Justfile, and GitHub Actions. No new runtime dependency.

---

## Authorization and execution protocol

This document is a plan-only artifact. It does not authorize any numbered
implementation task.

The frozen design specification is:

~~~
docs/superpowers/specs/2026-09-12-global-structural-card-census-design.md
~~~

The implementation branch and plan base are:

~~~
branch = feat/m1-global-structural-card-census
base   = 48d17fc7e618f73a97ef6babe4035d7fdf857203
~~~

The branch contains the frozen specification and its docs-only review commits.
Task 1 remains unauthorized until the user reviews and explicitly approves this
plan.

For every authorized task:

1. obtain authorization for exactly that numbered task;
2. execute only that task;
3. do not pre-stage later-task files, tests, schemas, CLI changes,
   documentation, or generated outputs;
4. run only that task's required verification and the shared preservation
   checks;
5. commit the task as one standalone reviewable commit;
6. push the authorized task commit to
   feat/m1-global-structural-card-census;
7. verify that the remote branch head equals the local task commit;
8. report the exact commit SHA, parent SHA, changed files, executed gates,
   findings, and stop conditions;
9. set NEXT_TASK_AUTHORIZED = NO;
10. stop.

Authorization of this plan does not authorize all tasks. A passing task does
not authorize the next task.

Push authorization is not PR authorization. PR authorization is not merge
authorization. Every task push remains a branch-only review checkpoint.

### Mandatory post-commit push verification

Immediately after every numbered task commit, run:

~~~powershell
git push origin feat/m1-global-structural-card-census
$localTaskHead = git rev-parse HEAD
$remoteTaskHead = git ls-remote origin refs/heads/feat/m1-global-structural-card-census
if ($remoteTaskHead -notmatch $localTaskHead) { throw "remote task head does not match local task head" }
~~~

Do not create a PR or merge as part of this verification.

### Shared preservation checks

Run these commands before and after every authorized task:

~~~powershell
git status --short --branch
git diff --name-only
git diff --cached --name-only
git diff -- source-locks/scryfall-oracle-v1.json config/sources/scryfall-oracle.v1.json
git diff -- src/manafold_census/models.py src/manafold_census/corpus src/manafold_census/source
~~~

The expected result is that only the current task's declared files change. The
Task 01 source lock, acquisition configuration, foundation models, corpus
package, and source package remain unchanged. No raw source, cache file, or
generated structural record is staged.

Stop with BLOCKED if a task needs a Task 01 contract change, semantic
interpretation, a new dependency, or a source shape that the frozen contract
cannot represent without guessing.

---

## File map and ownership

The following files are created or modified by later authorized tasks. Writing
this plan creates none of them.

### Structural production package

- Create src/manafold_census/structural/__init__.py for narrow public exports.
- Create src/manafold_census/structural/model.py for
  StructuralCardRecordV1, StructuralFaceV1, StructuralRelatedPartV1, wire
  conversion, identity validation, and defensive copying.
- Create src/manafold_census/structural/extract.py for streaming source parsing,
  Task 01 identity reuse, source-shape validation, and projection.
- Create src/manafold_census/structural/index.py for sorting, 16-shard JSONL
  writing, shard inspection, counts, and aggregate-digest input.
- Create src/manafold_census/structural/manifest.py for the independent
  StructuralCardIndexManifestV1.
- Create src/manafold_census/structural/report.py for fixed report keys and
  source-presence statistics.
- Create src/manafold_census/structural/synthetic.py for deterministic mtime=0
  synthetic gzip bytes and two-run reproduction.
- Create src/manafold_census/structural/build.py for pinned build orchestration,
  lifecycle identities, output writing, and report assembly.
- Create src/manafold_census/structural/check.py for complete fail-closed
  output/source reconstruction.

Every production module must remain at or below 500 lines.

### Normative schemas

- Create schemas/structural-card.v1.schema.json.
- Create schemas/structural-card-index-manifest.v1.schema.json.
- Create schemas/structural-card-report.v1.schema.json.

All three schemas use JSON Schema Draft 2020-12. Fixed objects use
additionalProperties=false.

### Tests

- Create tests/test_structural_model.py.
- Create tests/test_structural_extract.py.
- Create tests/test_structural_index.py.
- Create tests/test_structural_manifest.py.
- Create tests/test_structural_report.py.
- Create tests/test_structural_build.py.
- Create tests/test_structural_check.py.
- Create tests/test_structural_reproduction.py.
- Create tests/test_structural_cli.py.
- Modify tests/test_resources.py.
- Modify tests/test_maintainability.py.

### Existing orchestration, docs, and CI

- Modify src/manafold_census/cli.py only for the frozen structural commands.
- Modify justfile only for structural-build, structural-check, and the offline
  check target.
- Modify .github/workflows/ci.yml for the offline structural gate and fresh
  wheel smoke.
- Modify README.md, ARCHITECTURE.md, and CONTRIBUTING.md for the frozen M1
  boundary and workflow.
- Create docs/reports/2026-09-12-m1-global-structural-card-census-closure.md
  only in Task 10 after real evidence exists.

### Files that remain unchanged

~~~
source-locks/scryfall-oracle-v1.json
config/sources/scryfall-oracle.v1.json
src/manafold_census/models.py
src/manafold_census/canonical.py
src/manafold_census/digest.py
src/manafold_census/corpus/
src/manafold_census/source/
~~~

The existing setuptools data-files glob already includes schemas. A packaging
change is not planned unless the fresh wheel smoke proves the current mapping
cannot expose the new schemas.

---

## Task 1: Immutable structural models and card schema

**Scope:** Add only the typed immutable structural model layer and the normative
StructuralCardRecordV1 schema. Do not read the real corpus, write shards, add a
manifest/report schema, build output, or add CLI commands.

**Files:**

- Create src/manafold_census/structural/__init__.py
- Create src/manafold_census/structural/model.py
- Create schemas/structural-card.v1.schema.json
- Create tests/test_structural_model.py

**Invariants:**

- Wire schema is census.structural-card.v1.
- Every projected wire property is required.
- Source absence is null; present empty string and present empty array remain
  empty.
- None/null is a valid StructuralCardRecordV1 value for every nullable
  projected field and represents source absence at the structural model
  boundary.
- The model does not determine whether null originated from source absence or
  from an untrusted source value; explicit source-null rejection belongs only
  to Task 2 extraction.
- Face and related-part nested objects reject unknown properties.
- face_index is non-negative and within signed 64-bit range.
- Raw characteristics remain strings.
- Arrays preserve order and duplicates.
- Caller mutation cannot change a constructed record or a prior wire digest.
- Identity validation reuses RecordIndexEntry and its Task 01 rules.
- No semantic enum, parser, Requirement, or Capability type is introduced.

The Python model has these exact value groups:

~~~text
StructuralCardRecordV1:
  oracle_id, source_card_id, source_record_sha256, name, layout
  mana_cost, type_line, oracle_text
  colors, color_identity, color_indicator, keywords, produced_mana
  power, toughness, loyalty, defense, hand_modifier, life_modifier
  attraction_lights, faces, all_parts

StructuralFaceV1:
  face_index, name, mana_cost, type_line, oracle_text
  colors, color_indicator, power, toughness, loyalty, defense

StructuralRelatedPartV1:
  component, id, name, object, type_line, uri
~~~

The Python related-part attribute may be named object_kind to avoid shadowing
the builtin; its wire key remains object and its source value remains exact.

**Steps:**

- [ ] Add model tests for the exact top-level, face, and related-part key sets,
  fixed schema ID, a valid null-containing record, a valid ordered multi-face
  record, and a valid six-field related part.
- [ ] Add an explicit model test that constructs every nullable field with
  None, serializes successfully, and asserts that the model treats None as a
  valid structural absence value without source-origin metadata.
- [ ] Add tests for round-trip equality, unknown keys, wrong scalar types,
  wrong array element types, negative face_index, and values above
  MAX_INTEGER.
- [ ] Add tests proving missing values serialize as null while empty strings
  and arrays remain empty.
- [ ] Add tests that mutate constructor inputs and previous to_wire outputs,
  then assert a fresh to_wire result and canonical digest are unchanged.
- [ ] Add a test that extracts the four identity fields through
  RecordIndexEntry.from_wire and asserts exact equality.
- [ ] Run the focused test file.

~~~powershell
python -m pytest tests/test_structural_model.py -q
~~~

Expected RED: import failure because the structural package and schema are
absent.

- [ ] Implement the frozen dataclasses with tuple-backed nested values, fresh
  JSON-compatible to_wire containers, raw string validation, signed-64-bit
  bounds, and Task 01 identity projection.
- [ ] Implement the Draft 2020-12 card schema with nested definitions,
  required properties, nullable unions, UUID/digest patterns, integer bounds,
  and additionalProperties=false.
- [ ] Run the focused test file again.

~~~powershell
python -m pytest tests/test_structural_model.py -q
~~~

Expected GREEN: all model and schema-parity tests pass.

- [ ] Run focused lint and typing.

~~~powershell
python -m ruff check src/manafold_census/structural/model.py tests/test_structural_model.py
python -m mypy src/manafold_census/structural
~~~

- [ ] Run shared preservation checks, stage only Task 1 files, and commit:

~~~powershell
git add src/manafold_census/structural/__init__.py src/manafold_census/structural/model.py schemas/structural-card.v1.schema.json tests/test_structural_model.py
git diff --cached --check
git commit -m "feat: add immutable structural card models"
~~~

**Expected outputs:**

- One production model module below 500 lines.
- One normative card schema.
- Focused model/schema/immutability tests.
- One standalone Task 1 commit.

**Stop conditions:**

- BLOCKED if Task 01 identity code must change.
- BLOCKED if a frozen field cannot represent a real source value without
  interpretation.
- FAIL if any model/schema parity test remains red.
- No Task 2 or later files may be created.

---

## Task 2: Streaming extraction and Task 01 identity parity

**Scope:** Project one raw source line into StructuralCardRecordV1 while
preserving source position, absence, raw values, and Task 01 identity. Do not
sort, shard, write manifests, build reports, or add CLI commands.

**Files:**

- Create src/manafold_census/structural/extract.py
- Create tests/test_structural_extract.py

**Invariants:**

- Gzip JSONL is streamed one decompressed line at a time.
- The exact raw line, including LF, feeds the Task 01 source-record hash.
- Source object must be object=card with valid Oracle ID, card ID, name, and
  layout.
- Parent fields are read only from the parent object.
- Face fields are read only from the exact face object.
- No parent/face inheritance occurs.
- face_index is the zero-based source-array position.
- Missing card_faces becomes faces=None; present empty card_faces fails.
- Missing all_parts becomes all_parts=None; present relationships preserve order
  and all six opaque source values.
- all_parts.uri is copied but never dereferenced.
- Present empty values remain empty; explicit source null fails.
- Explicit source-null rejection is owned by this extractor before the model
  receives a structural None value.
- Source fields outside the projection are ignored.
- No text, cost, keyword, layout, or relationship semantics are inferred.

The extractor exposes:

~~~text
parse_structural_source_record(raw_line, line_number)
iter_structural_records(source_path)
~~~

**Steps:**

- [ ] Add tests for one, two, three, and five source faces, asserting exact
  face_index and source order.
- [ ] Add two tests that prove a parent-only field stays absent on a face and a
  face-only field stays absent on the parent.
- [ ] Add tests for missing fields, empty strings, empty arrays, Unicode,
  newline-containing Oracle text, formula strings, and ordered keyword values.
- [ ] Add a test for all six related-part fields that asserts exact URI
  preservation and no network operation.
- [ ] Add negative tests for explicit source null, wrong optional types,
  wrong element types, non-object faces, missing face name, empty faces, and
  malformed related parts.
- [ ] Add a test comparing the structural four-field identity with the
  RecordIndexEntry created from the same raw line.
- [ ] Run the focused test file.

~~~powershell
python -m pytest tests/test_structural_extract.py -q
~~~

Expected RED: import failure because extract.py is absent.

- [ ] Implement the raw-line parser by calling the existing Task 01 parser
  before projecting the parsed source object.
- [ ] Implement typed missing-versus-empty helpers and exact face/relationship
  projection.
- [ ] Implement the gzip iterator with fail-closed read errors.
- [ ] Run the focused tests again; expected GREEN is all extraction tests pass.
- [ ] Run Ruff and mypy for the new module.
- [ ] Run shared preservation checks and commit:

~~~powershell
git add src/manafold_census/structural/extract.py tests/test_structural_extract.py
git diff --cached --check
git commit -m "feat: extract immutable structural source facts"
~~~

**Expected outputs:**

- Streaming source extractor with no semantic helper.
- Positive and negative source-shape tests.
- Unit-level Task 01 identity parity.
- One standalone Task 2 commit.

**Stop conditions:**

- BLOCKED if source projection requires inference.
- FAIL if any parent/face inheritance occurs.
- BLOCKED if URI dereferencing would be needed.
- No Task 3 or later files may be created.

---

## Task 3: Deterministic structural shards and index inspection

**Scope:** Convert extracted structural records to exact canonical 16-shard JSONL
and inspect the shard set. Do not emit manifests, reports, lifecycle documents,
or CLI commands.

**Files:**

- Create src/manafold_census/structural/index.py
- Create tests/test_structural_index.py

**Invariants:**

- Shard names are exactly 0 through f.
- Assignment is the first lowercase hexadecimal character of normalized
  oracle_id.
- Every shard exists, including empty files.
- Each non-empty line is canonical JSON plus LF.
- Each shard is strictly Oracle-ID ascending.
- Oracle IDs are globally unique.
- Output must start empty.
- Unexpected/missing files and misplaced records fail.
- Aggregate descriptor input is ordered by shard and uses
  census.structural-card-index.v1.

The index exposes:

~~~text
build_structural_index(source_path, output_dir)
inspect_structural_index(output_dir)
StructuralShardSummary
StructuralIndexSummary
~~~

**Steps:**

- [ ] Add reverse-input tests spanning shard 0, 8, and f. Assert all 16 files,
  sorted lines, exact counts, and final LF behavior.
- [ ] Add byte-level canonicality tests and identical-source two-directory
  tests.
- [ ] Add negative tests for duplicate IDs, wrong shard, out-of-order records,
  missing/extra shards, missing LF, noncanonical JSON, invalid records, and
  non-empty output.
- [ ] Run the focused test file; expected RED is missing index.py.
- [ ] Implement deterministic collection, duplicate rejection, Oracle-ID sort,
  canonical line writing, exact shard set creation, and byte-level inspection.
- [ ] Run the focused test file; expected GREEN is all index tests pass.
- [ ] Run focused Ruff and mypy.
- [ ] Run shared preservation checks and commit:

~~~powershell
git add src/manafold_census/structural/index.py tests/test_structural_index.py
git diff --cached --check
git commit -m "feat: write deterministic structural shards"
~~~

**Expected outputs:**

- Deterministic structural shard writer and inspector.
- Canonicality, ordering, uniqueness, and reproduction tests.
- One standalone Task 3 commit.

**Stop conditions:**

- FAIL if any shard is missing, extra, misplaced, or unordered.
- BLOCKED if canonical encoding would change a retained source value.
- No Task 4 or later files may be created.

---

## Task 4: Structural aggregate manifest

**Scope:** Add the independent 16-shard aggregate manifest contract. Do not
orchestrate the complete build or write final output documents.

**Files:**

- Create src/manafold_census/structural/manifest.py
- Create schemas/structural-card-index-manifest.v1.schema.json
- Create tests/test_structural_manifest.py

**Invariants:**

- Schema ID is census.structural-card-index-manifest.v1.
- Schema path is schemas/structural-card-index-manifest.v1.schema.json.
- Digest domain is census.structural-card-index.v1.
- Exactly 16 ordered descriptors bind records/0.jsonl through records/f.jsonl.
- Descriptor keys are relative_path, sha256, byte_length, record_count.
- Paths, lowercase digest syntax, order, and signed-64-bit bounds are checked.
- Aggregate digest is recomputed from ordered descriptors.
- ArtifactManifest later binds exact canonical manifest bytes, not aggregate
  digest.

The manifest exposes:

~~~text
StructuralCardIndexManifestV1.from_summary(summary)
StructuralCardIndexManifestV1.from_wire(value)
StructuralCardIndexManifestV1.to_wire()
StructuralCardIndexManifestV1.canonical_bytes()
StructuralCardIndexManifestV1.digest()
~~~

**Steps:**

- [ ] Add tests for a valid all-16 manifest, stable canonical bytes, stable
  manifest SHA-256, and digest-domain separation.
- [ ] Add negative tests for missing/extra shards, wrong order/path, uppercase
  digest, negative/oversized lengths, unknown properties, and aggregate
  mismatch.
- [ ] Run the focused test file; expected RED is missing manifest.py/schema.
- [ ] Implement the frozen manifest class using Task 3 shard summaries.
- [ ] Implement the Draft 2020-12 schema with fixed keys,
  additionalProperties=false, exact path pattern, and non-negative int64
  lengths/counts.
- [ ] Validate the schema through project_data_root and the existing
  validate_document function.
- [ ] Run focused tests; expected GREEN is all manifest tests pass.
- [ ] Run focused Ruff and mypy.
- [ ] Run shared preservation checks and commit:

~~~powershell
git add src/manafold_census/structural/manifest.py schemas/structural-card-index-manifest.v1.schema.json tests/test_structural_manifest.py
git diff --cached --check
git commit -m "feat: bind structural shard manifest"
~~~

**Expected outputs:**

- Independent manifest model and schema.
- Stable canonical manifest bytes and aggregate digest.
- One standalone Task 4 commit.

**Stop conditions:**

- FAIL if a different shard set/order is accepted.
- BLOCKED if ArtifactManifestV1 must change.
- No Task 5 or later files may be created.

---

## Task 5: Structural statistics and report contract

**Scope:** Add the deterministic report statistics collector and complete report
schema. Keep statistics pure and free of file I/O or semantic interpretation.

**Files:**

- Create src/manafold_census/structural/report.py
- Create schemas/structural-card-report.v1.schema.json
- Create tests/test_structural_report.py

**Invariants:**

- Schema ID is census.structural-card-report.v1.
- Schema path is schemas/structural-card-report.v1.schema.json.
- Report root has exactly the frozen fields.
- task01_record_identity_parity is boolean.
- Counts and byte lengths are non-negative signed-64-bit integers.
- top_level_field_presence has exactly the 17 frozen source-property keys.
- face_field_presence has exactly the 10 frozen face-property keys.
- shard_record_counts has exactly the 16 lowercase shard keys.
- Presence means source property membership, including empty values.
- face_count_distribution counts only records where card_faces is present.
- Absent card_faces records create no zero bucket.
- Present empty card_faces is invalid; valid keys match [1-9][0-9]*.
- total_face_count sums present face-array lengths.
- max_face_count is the maximum present length, or 0 if none are present.
- No semantic categories, timestamps, paths, or timings enter the report.

The exact presence keys are:

~~~text
top_level_field_presence:
  mana_cost, type_line, oracle_text, colors, color_identity,
  color_indicator, keywords, produced_mana, power, toughness,
  loyalty, defense, hand_modifier, life_modifier,
  attraction_lights, card_faces, all_parts

face_field_presence:
  name, mana_cost, type_line, oracle_text, colors,
  color_indicator, power, toughness, loyalty, defense
~~~

**Steps:**

- [ ] Add tests for no-face, two-face, three-face, and five-face records.
  Assert absent faces create no zero key and assert exact total/max values.
- [ ] Add tests proving empty strings and arrays increment membership counts.
- [ ] Add tests for exact fixed keys, all 16 shard keys, boolean parity, and
  int64 lower/upper bounds.
- [ ] Add negative schema tests for key 0, missing/extra fixed keys, negative
  or floating counts, string parity, and unknown root fields.
- [ ] Run the focused test file; expected RED is missing report.py/schema.
- [ ] Implement the pure statistics collector from structural records and shard
  counts without reading Oracle text or deriving semantics.
- [ ] Implement the Draft 2020-12 report schema with exact root keys, fixed
  maps, dynamic layout names, face-count key pattern [1-9][0-9]*, and int64
  bounds.
- [ ] Run focused tests; expected GREEN is all report tests pass.
- [ ] Run focused Ruff and mypy.
- [ ] Run shared preservation checks and commit:

~~~powershell
git add src/manafold_census/structural/report.py schemas/structural-card-report.v1.schema.json tests/test_structural_report.py
git diff --cached --check
git commit -m "feat: define structural census report contract"
~~~

**Expected outputs:**

- Pure structural statistics collector.
- Complete deterministic report schema.
- Tests proving source-membership and face-count semantics.
- One standalone Task 5 commit.

**Stop conditions:**

- FAIL if statistics use truthiness or non-null checks.
- BLOCKED if a report field requires semantic interpretation.
- No Task 6 or later files may be created.

---

## Task 6: Pinned build and lifecycle identities

**Scope:** Orchestrate a complete structural build using the generic lifecycle
models and the Task 3-5 components.

**Files:**

- Create src/manafold_census/structural/build.py
- Create tests/test_structural_build.py

**Invariants:**

- Exactly one source artifact is loaded from the committed lock.
- validate_source_file runs before extraction.
- The builder resolves the exact content-addressed cache path and never
  refreshes or substitutes source.
- Output starts empty and contains records plus the five specified documents.
- Dataset identity is scryfall-oracle-structural-census, version 1.0.0,
  normalization profile scryfall-oracle-structural-v1.
- Study identity is scryfall-oracle-structural-build with operation
  scryfall-oracle-structural.v1, shard_count 16, and the exact lock digest.
- Artifact identity is scryfall-oracle-structural-index and
  census.structural-card-index.v1.
- ArtifactManifest content_sha256 and byte_length bind exact canonical
  structural-index-manifest.json bytes.
- Report contains fixed v1 identity and all manifest/dataset/study/artifact
  digests.
- No timestamp, path, hostname, timing, or raw source enters semantic output.

The public build functions are:

~~~text
build_structural_corpus(source_path, source_lock_path, output_dir)
build_pinned_structural(repository_root, output_dir)
StructuralBuildResult
~~~

**Steps:**

- [ ] Add a temporary-source build test asserting the exact output file set,
  structural records, and absence of raw gzip bytes in output.
- [ ] Add assertions for every dataset, study, artifact, report, and manifest
  identity, including artifact_id and artifact_kind.
- [ ] Add assertions that ArtifactManifest content_sha256 and byte_length equal
  the exact structural manifest bytes.
- [ ] Run the focused test file; expected RED is missing build.py.
- [ ] Implement source-lock loading, cache resolution, empty-output checking,
  index build, structural manifest, generic lifecycle documents, report
  assembly, and canonical writes.
- [ ] Implement the pinned wrapper using the committed lock and cache_path_for.
- [ ] Run focused tests; expected GREEN is all build tests pass.
- [ ] Run focused Ruff and mypy.
- [ ] Run shared preservation checks and commit:

~~~powershell
git add src/manafold_census/structural/build.py tests/test_structural_build.py
git diff --cached --check
git commit -m "feat: build structural census artifacts"
~~~

**Expected outputs:**

- Complete temporary-source structural output.
- Generic lifecycle identity closure.
- Exact ArtifactManifest byte binding.
- One standalone Task 6 commit.

**Stop conditions:**

- BLOCKED if exact pinned bytes are absent or fail digest/length verification.
- FAIL if output contains a path, timestamp, timing, or raw source bytes.
- BLOCKED if a generic foundation model must change.
- No Task 7 or later files may be created.

---

## Task 7: Fail-closed structural checker

**Scope:** Validate completed output against exact source and reconstruct all
provenance, identity, manifest, artifact, dataset, study, and report facts.

**Files:**

- Create src/manafold_census/structural/check.py
- Create tests/test_structural_check.py

**Invariants:**

- Exact output file set is checked before document trust.
- Every JSON document and JSONL line is byte-canonical.
- All three new schemas and all generic schemas are validated.
- Shards, aggregate digest, manifest bytes, and report statistics are
  recomputed from actual bytes.
- Source structural projection is recomputed from pinned source.
- All four Task 01 identity fields match for every record.
- Missing, extra, duplicate, wrong-shard, out-of-order, and mismatched records
  fail closed.
- URI is never dereferenced and checker performs no network I/O.
- Report values never serve as the checker source of truth.

The checker exposes:

~~~text
validate_structural_output(output_dir, source_path, source_lock_path)
validate_pinned_structural_output(repository_root, output_dir)
~~~

**Steps:**

- [ ] Add a positive temporary build/check test.
- [ ] Add corruption tests for missing/extra files, noncanonical documents,
  wrong shard/order, duplicate identity, wrong source hash/card ID/name/raw
  field, wrong face order, wrong related-part URI, manifest mismatch,
  ArtifactManifest mismatch, report count/map mismatch, source-lock mismatch,
  and Task 01 parity mismatch.
- [ ] Add a test proving a modified URI is detected without URI access.
- [ ] Run the focused test file; expected RED is missing check.py.
- [ ] Implement canonical readers, exact file-set checks, source reconstruction,
  identity comparison, projection comparison, schema validation, generic
  lifecycle closure, structural manifest closure, artifact byte closure, and
  report closure.
- [ ] Run focused tests; expected GREEN is all checker tests pass.
- [ ] Run focused Ruff and mypy.
- [ ] Run shared preservation checks and commit:

~~~powershell
git add src/manafold_census/structural/check.py tests/test_structural_check.py
git diff --cached --check
git commit -m "feat: validate structural provenance closure"
~~~

**Expected outputs:**

- Independent fail-closed source/output validator.
- Corruption tests for all required closure classes.
- One standalone Task 7 commit.

**Stop conditions:**

- FAIL if the checker trusts report values without reconstruction.
- BLOCKED if parity cannot be reconstructed from pinned bytes.
- BLOCKED if validation needs network access.
- No Task 8 or later files may be created.

---

## Task 8: Offline synthetic reproduction and maintainer CLI

**Scope:** Add deterministic synthetic source/reproduction and the frozen
structural-build and structural-check commands.

**Files:**

- Create src/manafold_census/structural/synthetic.py
- Modify src/manafold_census/structural/build.py
- Modify src/manafold_census/cli.py
- Modify justfile
- Create tests/test_structural_reproduction.py
- Create tests/test_structural_cli.py
- Modify tests/test_maintainability.py

**Invariants:**

- Synthetic gzip bytes use mtime=0 and a fixed empty filename.
- Synthetic input covers single face, multiple faces, raw characteristic
  strings, ordered lists, absent values, empty values, related parts, and
  attraction lights.
- Two independent synthetic outputs match in file set and every byte.
- structural-build uses pinned cache and never refreshes.
- structural-check validates a pinned output.
- structural-check --synthetic is fully offline.
- CLI failures return non-zero and no M2 command is added.

The commands are:

~~~text
python -m manafold_census.cli structural-build --repository-root . --output dist/structural/scryfall-oracle-v1
python -m manafold_census.cli structural-check --repository-root . --output dist/structural/scryfall-oracle-v1
python -m manafold_census.cli structural-check --synthetic
~~~

**Steps:**

- [ ] Add tests for deterministic gzip bytes and each required synthetic shape.
- [ ] Add two-run tests comparing all relative names and every byte.
- [ ] Add CLI tests for synthetic success, missing output failure, invalid root
  failure, and non-zero exception behavior.
- [ ] Update maintainability tests for structural recipes and the offline check.
- [ ] Run the focused tests; expected RED is missing command behavior.
- [ ] Implement synthetic generation, two-run reproduction, CLI parser branches,
  pinned output resolution, and error reporting.
- [ ] Add Justfile recipes structural-build and structural-check, with the
  structural-check recipe invoking the synthetic offline path.
- [ ] Run focused tests; expected GREEN is all reproduction/CLI tests pass.
- [ ] Run the synthetic command and assert equal run digests.

~~~powershell
python -m manafold_census.cli structural-check --synthetic
~~~

- [ ] Run Ruff and mypy, run shared preservation checks, and commit:

~~~powershell
git add src/manafold_census/structural/synthetic.py src/manafold_census/structural/build.py src/manafold_census/cli.py justfile tests/test_structural_reproduction.py tests/test_structural_cli.py tests/test_maintainability.py
git diff --cached --check
git commit -m "feat: add offline structural census commands"
~~~

**Expected outputs:**

- Stable offline structural reproduction.
- Structural CLI commands with explicit failure behavior.
- Network-independent Justfile path.
- One standalone Task 8 commit.

**Stop conditions:**

- FAIL if synthetic outputs differ.
- BLOCKED if CLI behavior requires network access.
- Stop if any semantic parser, Requirement, Capability, or search concept
  appears.
- No Task 9 or later files may be created.

---

## Task 9: Packaging, documentation, CI, and maintainability

**Scope:** Make the frozen M1 workflow discoverable and enforce offline
structural gates locally and in hosted CI. Do not build or commit the real
38,740-record output.

**Files:**

- Modify .github/workflows/ci.yml
- Modify README.md
- Modify ARCHITECTURE.md
- Modify CONTRIBUTING.md
- Modify tests/test_resources.py
- Modify tests/test_maintainability.py

**Invariants:**

- Existing Task 00 and Task 01 commands remain valid.
- just check remains network-independent and includes synthetic structural
  checking.
- CI uses Python 3.12 and runs all required offline gates.
- Fresh non-editable wheel smoke finds all three M1 schemas outside repository
  CWD and runs structural-check --synthetic.
- Documentation describes source-fact scope, null/empty semantics, face order,
  raw values, opaque URI, parity, output path, and offline checking.
- Documentation does not claim real-corpus PASS before Task 10.
- No raw source, cache file, generated shard, or semantic output is committed.

**Steps:**

- [ ] Add resource assertions for all three M1 schemas.
- [ ] Add the structural synthetic check to the Justfile check target and test
  that no live source command appears there.
- [ ] Add the CI structural synthetic check after the existing synthetic corpus
  check.
- [ ] Extend fresh-wheel smoke to import structural resources and run the
  synthetic structural check from the temporary directory.
- [ ] Update README.md with the explicit live source command boundary and M1
  structural commands.
- [ ] Update ARCHITECTURE.md with projection, shards, manifest-byte binding,
  provenance, and fail-closed validation.
- [ ] Update CONTRIBUTING.md with staged authorization and honest gate states.
- [ ] Run focused resource and maintainability tests; expected GREEN is all
  repository contract tests pass.
- [ ] Run the complete offline gate set.

~~~powershell
ruff format --check .
ruff check .
mypy src/manafold_census
python -m pytest -q
python -m manafold_census.cli reproduce
python -m manafold_census.cli corpus-check --synthetic
python -m manafold_census.cli structural-check --synthetic
~~~

- [ ] Build a wheel and install it in a fresh non-editable environment outside
  the repository; run schema lookup and structural synthetic checking there.
- [ ] Run shared preservation checks, stage only Task 9 files, and commit:

~~~powershell
git add .github/workflows/ci.yml README.md ARCHITECTURE.md CONTRIBUTING.md tests/test_resources.py tests/test_maintainability.py
git diff --cached --check
git commit -m "chore: enforce offline structural census gates"
~~~

**Expected outputs:**

- Local and hosted offline M1 gates.
- Fresh-wheel resource proof.
- M1 workflow documentation.
- One standalone Task 9 commit.

**Stop conditions:**

- FAIL if wheel smoke cannot find any M1 schema outside repository CWD.
- BLOCKED if packaging requires unrelated redesign.
- Stop if CI would fetch Scryfall.
- No real output or closure report may be created.

---

## Task 10: Real pinned corpus evidence and closure report

**Scope:** Execute the real build and checker against the exact pinned source,
run the independent second build, capture required accounting and gate
evidence, and create the tracked closure report. Do not modify source locks,
commit generated shards, merge, or start M2.

**Files:**

- Create docs/reports/2026-09-12-m1-global-structural-card-census-closure.md
- Generated output remains ignored under dist/structural.

**Preconditions:**

- Tasks 1 through 9 have separate reviewed commits.
- Worktree is clean.
- origin/main and the committed source lock remain unchanged.
- All offline gates and fresh-wheel checks pass.
- Exact pinned cache is available through source-fetch-pinned.

**Commands:**

~~~powershell
python -m manafold_census.cli source-fetch-pinned --repository-root .

python -m manafold_census.cli structural-build --repository-root . --output dist/structural/scryfall-oracle-v1-run-a
python -m manafold_census.cli structural-check --repository-root . --output dist/structural/scryfall-oracle-v1-run-a

python -m manafold_census.cli structural-build --repository-root . --output dist/structural/scryfall-oracle-v1-run-b
python -m manafold_census.cli structural-check --repository-root . --output dist/structural/scryfall-oracle-v1-run-b
~~~

If an output path already exists, do not delete it implicitly. Stop, record the
collision, and choose a fresh ignored output path.

Compare every relative file name and every file byte between run A and run B.
Report directory digests separately from semantic manifest digests.

**Required real accounting:**

~~~text
SOURCE_RECORD_COUNT             = 38740
STRUCTURAL_RECORD_COUNT         = 38740
UNIQUE_STRUCTURAL_ORACLE_IDS    = 38740
DUPLICATE_STRUCTURAL_IDENTITIES = 0
MISSING_ORACLE_IDENTITIES       = 0
EXTRA_ORACLE_IDENTITIES         = 0
CARDS_WITH_FACES                = 3221
CARDS_WITHOUT_FACES             = 35519
TOTAL_FACE_RECORDS              = 6447
MAX_FACE_COUNT                  = 5
FACE_COUNT_DISTRIBUTION         = 2:3218, 3:2, 5:1
~~~

The closure report records actual observed values for source identity, every
shard count, all layout and field-presence counts, every structural/lifecycle
digest, run A/B directory digests, byte parity, toolchain gates, wall time,
memory state, Task 01 preservation, and all M1 acceptance gates. It uses
PASS, FAIL, BLOCKED, or NOT_RUN honestly.

**Steps:**

- [ ] Run source-fetch-pinned and confirm source ID, digest, and byte length.
- [ ] Run the first build/check and record wall time separately from semantic
  output.
- [ ] Run the second build/check in a distinct empty directory.
- [ ] Compare complete file sets and every byte.
- [ ] Recompute directory digests and inspect the report against required
  accounting.
- [ ] Re-run the complete local offline gate set, wheel smoke, and
  maintainability check.
- [ ] Write the closure report only from observed command output.
- [ ] Confirm no raw source or generated shard is tracked and Task 01 files are
  unchanged.
- [ ] Stage only the closure report, run the staged diff check, and commit:

~~~powershell
git add docs/reports/2026-09-12-m1-global-structural-card-census-closure.md
git diff --cached --check
git commit -m "docs: record M1 structural census closure evidence"
~~~

- [ ] Report Task 10 SHA, parent SHA, changed files, all gate states, and
  NEXT_TASK_AUTHORIZED = NO.

**Expected outputs:**

- Two independently built and validated real output directories in ignored
  paths.
- Required 38,740-record accounting and actual digest identities.
- One tracked closure report and one docs-only evidence commit.
- No generated structural records committed.

**Stop conditions:**

- BLOCKED if exact pinned bytes cannot be fetched or verified.
- FAIL if any real count, identity, schema, ordering, provenance, canonicality,
  manifest, artifact, or byte-reproduction gate fails.
- NOT_RUN for any required command not executed.
- No PR from an incomplete or failed closure.
- No merge, M2, or Issue #5 work.

---

## Final delivery gate after accepted task reports

This is not an implementation task and cannot run with Task 10.

After every numbered task has been independently reviewed and delivery is
explicitly authorized:

- fetch current origin/main and verify branch parent and complete diff;
- run git diff --check and inspect the complete diff;
- verify only intended source, schema, test, docs, CI, and closure-report files
  are tracked;
- verify generated outputs and source cache remain ignored;
- verify every reviewed task commit is already synchronized with
  origin/feat/m1-global-structural-card-census;
- create one unmerged PR against main;
- use Relates to #4 unless every M1 gate is PASS, then use Closes #4;
- do not merge and do not start M2.

The delivery report must state:

~~~text
PR_STATE = OPEN
MERGED = NO
M2_STARTED = NO
NEXT_TASK_AUTHORIZED = NO
~~~

---

## Plan self-review

The task sequence covers every frozen-spec area:

- Task 1 covers immutable models, exact card schema, nullability, raw values,
  array order, integer limits, and model/schema parity.
- Task 2 covers streaming extraction, Task 01 identity, source provenance,
  parent/face separation, face order, all_parts fields, URI opacity, and
  fail-closed source shapes.
- Task 3 covers 16 shards, canonical JSONL, sort order, uniqueness, file set,
  and deterministic index identity.
- Task 4 covers the independent structural manifest, schema path, digest domain,
  ordered descriptors, and exact-byte binding input.
- Task 5 covers the report schema, fixed maps, presence membership, face-count
  population, zero-key exclusion, and signed-64-bit bounds.
- Task 6 covers dataset, study, artifact, report, source lock, output layout,
  and manifest-byte ArtifactManifest binding.
- Task 7 covers source reconstruction, parity, canonicality, file-set closure,
  digest closure, corruption rejection, and report distrust.
- Task 8 covers synthetic mtime=0 reproduction, CLI, Justfile, and offline
  behavior.
- Task 9 covers packaging, wheel smoke, documentation, CI, and maintainability.
- Task 10 covers the real source, 38,740-record accounting, A/B parity, closure
  evidence, and honest gate states.
- The execution protocol and each task boundary prohibit pre-staging later
  work, Task N+1 execution, M2, merge, and semantic interpretation.

No unfinished marker or unresolved design choice remains in the task sequence.

## Plan state

~~~text
IMPLEMENTATION_PLAN_WRITTEN = YES
IMPLEMENTATION_PLAN_REVIEW  = PENDING
IMPLEMENTATION_TASK_1       = NOT_AUTHORIZED
NEXT_TASK_AUTHORIZED        = NO
PRODUCTION_CODE             = NOT_TOUCHED
M2                          = NOT_AUTHORIZED
~~~
