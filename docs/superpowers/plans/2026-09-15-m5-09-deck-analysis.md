# M5-09 Deck Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic, read-only main/sideboard deck parser and analysis result on top of the frozen M5-08 Census lookup layer.

**Architecture:** Keep parsing and analysis in the deep query/deck.py module. The parser accepts strict UTF-8 bytes with an optional initial BOM, records invalid lines instead of guessing, and emits explicit unknown/ambiguous name records. The analyzer consumes an already opened CensusReader, aggregates only resolved Oracle identities within each section, reuses M5-08 semantic details and provenance traces, and performs no legality checks or Rules Execution.

**Tech Stack:** Python 3.12+, frozen CensusReader, typed M1/M3/M4 query models, jsonschema Draft 2020-12, canonical JSON, pytest, Ruff, mypy, PowerShell.

---

### Task 1: Add failing deck grammar and result-contract tests

**Files:**
- Create: tests/test_deck_analysis.py
- Read-only references: docs/superpowers/specs/2026-09-15-m5-census-0-1-design.md, src/manafold_census/query/api.py, src/manafold_census/query/details.py

- [ ] **Step 1: Write the failing tests.**

Build the existing synthetic M5-06 tree and open it through open_bundle. Call the future analyze_deck_bytes(raw_bytes, reader) seam and cover:

~~~python
def test_main_and_sideboard_are_separate(tmp_path):
    result = analyze_deck_bytes(
        b"\xef\xbb\xbf[MAIN]\n2 Fixture Card\n[sideboard]\n1 Fixture Card\n",
        _reader(tmp_path),
    )
    assert result.main.declared_card_count == 2
    assert result.sideboard.declared_card_count == 1


def test_inline_hash_is_preserved_in_card_name(tmp_path):
    result = analyze_deck_bytes(b"[main]\n1 Fixture Card # keep\n", _reader(tmp_path))
    assert result.main.unknown_names[0].name == "Fixture Card # keep"


def test_unknown_and_ambiguous_names_remain_visible(tmp_path):
    result = analyze_deck_bytes(
        b"[main]\n1 Does Not Exist\n1 Fixture Card\n", _reader(tmp_path)
    )
    assert result.main.unknown_names[0].lookup_key == "does not exist"
    assert len(result.main.ambiguous_names[0].matches) == 5


def test_invalid_lines_and_non_utf8_are_fail_closed(tmp_path):
    result = analyze_deck_bytes(
        b"[main]\n0 Fixture Card\n[commander]\n", _reader(tmp_path)
    )
    assert len(result.invalid_lines) == 2
    with pytest.raises(DeckInputError, match="UTF-8"):
        analyze_deck_bytes(b"[main]\n1 \xff\n", _reader(tmp_path))
~~~

- [ ] **Step 2: Run the focused tests and confirm RED.**

~~~powershell
$env:PYTHONPATH='src'; & C:\Python313\python.exe -m pytest tests/test_deck_analysis.py -q
~~~

Expected: collection fails because manafold_census.query.deck, analyze_deck_bytes, and DeckInputError do not yet exist.

### Task 2: Implement the strict parser and immutable result models

**Files:**
- Create: src/manafold_census/query/deck.py
- Create: src/manafold_census/query/deck_models.py
- Create: src/manafold_census/query/deck_result.py
- Create: schemas/deck-analysis.v1.schema.json
- Modify: src/manafold_census/query/__init__.py

- [ ] **Step 1: Define closed result values.**

Implement frozen DeckSectionV1 (MAIN and SIDEBOARD), DeckInvalidReasonV1, DeckInputError, DeckInvalidLineV1, DeckUnknownNameV1, DeckAmbiguousNameV1, DeckCardSummaryV1, DeckCapabilityCountV1, DeckProvenanceTraceV1, DeckSectionAnalysisV1, and DeckAnalysisV1. Keep parser/result atoms in deck_models.py, section and top-level result values in deck_result.py, and leave deck.py below 500 lines as the parser/analyzer seam. query.deck re-exports the public values from both focused model modules.

Use tuples for every collection and MappingProxyType for count maps. Require every closed enum member and these explicit denominator labels:

~~~text
analysis_outcome_counts       / UNIQUE_RESOLVED_ORACLE_IDENTITIES
m2_review_status_counts       / PERSISTED_REQUIREMENTS_ON_RESOLVED_CARDS
m4_mapping_disposition_counts / PERSISTED_REQUIREMENTS_ON_RESOLVED_CARDS
~~~

The top-level result carries raw deck-input SHA-256, Census release ID, Census manifest SHA-256, source-lock digest, M3 manifest SHA-256, and M4 manifest SHA-256. to_wire contains no absolute paths.

- [ ] **Step 2: Implement parse_deck_bytes(raw: bytes).**

Require bytes, strip only an initial UTF-8 BOM, and decode with errors="strict". Ignore blank lines and leading-whitespace # comments. Accept only [main] and [sideboard] headers case-insensitively. Require a valid section before entries. Parse the first whitespace separator only so # inside a card name is preserved. Accept exactly [1-9][0-9]*, cap each line at 1,000,000, and record a line that would exceed its section's 1,000,000 total as invalid. A U+FEFF after the initial BOM is invalid and is never silently removed.

- [ ] **Step 3: Export the interface and rerun parser tests.**

Export DeckAnalysisV1, DeckSectionAnalysisV1, DeckSectionV1, DeckInputError, parse_deck_bytes, analyze_deck_bytes, and analyze_deck_file from both query.deck and the query package.

### Task 3: Integrate M5-08 lookup, semantic aggregation, and traces

**Files:**
- Modify: src/manafold_census/query/deck.py
- Modify: src/manafold_census/query/provenance.py
- Extend: tests/test_deck_analysis.py

- [ ] **Step 1: Resolve entries through CensusReader.resolve_card_name.**

Unknown names become DeckUnknownNameV1; ambiguous names become DeckAmbiguousNameV1 containing every CardIdentityV1; only resolved names enter aggregation. No ambiguous identity is selected.

- [ ] **Step 2: Aggregate by section and Oracle identity.**

Use (section, oracle_id) as the key. Duplicate resolved names add quantities to one summary. declared_card_count includes all syntactically accepted entries; resolved_card_count includes resolved quantities; unique identity count is distinct resolved Oracle IDs. Use unique resolved Card details for analysis-outcome counts and persisted Requirements for M2/M4 counts. Partition each resolved card into exactly one of the four frozen SemanticState values; NO_REQUIREMENTS_APPLICABLE is the explicit-negative group. Empty Capability collections never become an absence claim.

- [ ] **Step 3: Build Capability counts and traces.**

Count each active Capability once per section/Oracle identity and also add the card's aggregate quantity. Call reader.trace_requirement for every persisted Requirement and reader.trace_mapping for every active mapping link. Sort Capabilities, summaries, and traces by frozen identity keys.

- [ ] **Step 4: Add integration regressions and run GREEN.**

Cover duplicate aggregation, main/sideboard isolation, inclusive and overflowing limits, 01/+1/zero/negative quantities, all four semantic partitions, unresolved-with-bundle preservation, unique/quantity-weighted Capability counts, deterministic traces, and reader immutability.

~~~powershell
$env:PYTHONPATH='src'; & C:\Python313\python.exe -m pytest tests/test_deck_analysis.py tests/test_card_lookup.py tests/test_census_query.py -q
~~~

### Task 4: Freeze the deck-analysis.v1 wire schema

**Files:**
- Modify: schemas/deck-analysis.v1.schema.json
- Modify: tests/test_deck_analysis.py

- [ ] **Step 1: Define the strict Draft 2020-12 schema.**

Use additionalProperties: false for all deck, section, invalid-line, unknown-name, ambiguous-name, summary, Capability-count, distribution, and provenance wrapper objects. Require both sections, every explicit count and denominator, all four semantic card partitions, unknown/ambiguous/invalid arrays, Capability counts, and provenance traces. Type nested M5-08 identities, Capability references, Requirement traces, and Mapping traces.

- [ ] **Step 2: Add canonical/schema and boundary tests.**

Validate DeckAnalysisV1.to_wire() with validate_document, compare repeated canonical JSON bytes, and reject changed denominator labels and unexpected properties. Assert repeated analysis is identical and the reader remains unchanged. Keep query/deck.py free of dynamic code, network, database, and Rules Execution calls.

### Task 5: Verify, commit, push, and stop for exact-head review

**Files:**
- No generated Census, M4, bundle, report, or Explorer output may be committed.
- The three M5-09 query modules must each remain below 500 lines.
- Modify: src/manafold_census/query/provenance.py only to move its bundle type import under TYPE_CHECKING and prevent the query/reports import cycle.

- [ ] **Step 1: Run quality, reproduction, and fresh-wheel gates.**

~~~powershell
& C:\Python313\python.exe -m ruff format --check .
& C:\Python313\python.exe -m ruff check .
& C:\Python313\python.exe -m mypy src/manafold_census
$env:PYTHONPATH='src'; & C:\Python313\python.exe -m pytest -q
& C:\Python313\python.exe -m manafold_census.cli reproduce
~~~

Build/install a wheel in a fresh temporary virtual environment, import manafold_census.query.deck without PYTHONPATH, and run the existing doctor and synthetic reproduction smoke.

- [ ] **Step 2: Check LOC, stage only M5-09 files, commit, and push.**

~~~powershell
$path = 'src/manafold_census/query/deck.py'
if ((Get-Content -LiteralPath $path).Count -ge 500) { throw 'deck.py exceeds the M5 module budget' }
foreach ($module in @('src/manafold_census/query/deck.py', 'src/manafold_census/query/deck_models.py', 'src/manafold_census/query/deck_result.py')) { if ((Get-Content -LiteralPath $module).Count -ge 500) { throw "$module exceeds the M5 module budget" } }
git add -- docs/superpowers/plans/2026-09-15-m5-09-deck-analysis.md schemas/deck-analysis.v1.schema.json src/manafold_census/query/deck.py src/manafold_census/query/deck_models.py src/manafold_census/query/deck_result.py src/manafold_census/query/__init__.py tests/test_deck_analysis.py
git diff --cached --name-only
git commit -m 'feat: add Census deck analysis'
git push origin feat/m5-census-0-1
~~~

Do not modify M4 authority, the Census bundle, Explorer, deck legality, Rules Execution, network code, PR, or merge state.

- [ ] **Step 3: Verify exact head and stop.**

~~~powershell
$head = git rev-parse HEAD
$remote = git rev-parse origin/feat/m5-census-0-1
if ($head -ne $remote) { throw 'remote head does not match local head' }
git status --short
gh pr list --head feat/m5-census-0-1 --state open --json number,url,title
~~~

Leave:

~~~text
M5_09_STATUS      = NOT_FROZEN
M5_10_AUTHORIZED  = NO
PR_AUTHORIZED     = NO
MERGE_AUTHORIZED  = NO
~~~

Self-review:

- [ ] Main and sideboard stay separate in parsing, counts, aggregation, and output.
- [ ] Strict UTF-8, initial-BOM, comments, inline #, quantities, duplicates, and limits match the frozen grammar.
- [ ] Unknown and ambiguous names remain visible; no ambiguous identity is selected.
- [ ] Unresolved and explicit-negative states remain distinct.
- [ ] Capability counts and provenance traces are derived only from the frozen reader.
- [ ] No legality, Rules Execution, network, database, dynamic code, or Explorer code is introduced.
- [ ] Every production module remains below the 500-line budget.
