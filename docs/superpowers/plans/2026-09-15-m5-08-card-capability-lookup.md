# M5-08 Card and Capability Lookup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Extend the frozen read-only Query Layer with exact/casefolded card
name resolution, explicit unknown/ambiguous results, and digest-bound Card and
Capability detail views.

**Architecture:** Keep `open_bundle()` as the only construction seam and reuse
the fully validated M5-07 reader state. `cards.py` continues to own the closed
semantic view and adds only deterministic name-key normalization; `lookup.py`
assembles resolution and detail values from validated records, while
`details.py` contains immutable M5-08 return models. Name resolution trims and
collapses lookup whitespace and applies `casefold()` without Unicode
normalization or fuzzy matching. Multiple matching Oracle identities always
produce an ambiguity value and are never silently selected.

**Tech Stack:** Python 3.12+, existing M5-07 reader and typed M1/M3/M4 models,
pytest, Ruff, mypy, PowerShell.

---

### Task 1: Add failing M5-08 lookup tests

**Files:**
- Create: `tests/test_card_lookup.py`
- Reuse: `tests/test_census_query.py` synthetic M5-06 bundle fixture.

- [ ] **Step 1: Write the failing tests.** Cover:
  - exact name resolution;
  - outer-whitespace trimming, internal lookup-whitespace collapsing, and
    casefolded matching while preserving the original source name;
  - unknown names returning an explicit `UNKNOWN` result;
  - near/fuzzy names remaining unknown;
  - duplicate source names returning an explicit `AMBIGUOUS` result with every
    matching Oracle identity;
  - resolved Card detail exposing structural facts, `CardSemanticViewV1`,
    Requirements, active mappings, typed bindings, capability lifecycle/review,
    and release provenance;
  - Capability detail exposing its exact definition/review, linked Requirements,
    mapped cards, and mapped-subset frequency denominator;
  - an empty mapped-card subset remaining an empty subset rather than an absence
    semantic claim;
  - unknown Oracle/Capability IDs remaining explicit not-found values;
  - repeated resolution/detail calls being deterministic and read-only.
- [ ] **Step 2: Run the focused tests and confirm RED.**

```powershell
$env:PYTHONPATH='src'; & C:\Python313\python.exe -m pytest tests/test_card_lookup.py -q
```

Expected: collection fails because the M5-08 detail/lookup modules and reader
methods do not yet exist.

### Task 2: Implement immutable M5-08 return models and lookup normalization

**Files:**
- Create: `src/manafold_census/query/details.py`
- Create: `src/manafold_census/query/lookup.py`
- Modify: `src/manafold_census/query/cards.py`

- [ ] **Step 1:** Define immutable `CardIdentityV1`,
  `CardNameResolutionStatusV1`, `CardNameResolutionV1`, `CardDetailViewV1`,
  `CapabilityDetailViewV1`, and mapped-subset frequency values. Use exact typed
  records and tuples; preserve release identities and source names.
- [ ] **Step 2:** Add one deterministic lookup-key function:

```python
def card_name_lookup_key(value: str) -> str:
    return " ".join(value.strip().split()).casefold()
```

Do not apply Unicode normalization, fuzzy matching, semantic parsing, or source
name rewriting.
- [ ] **Step 3:** Implement pure lookup/detail builders from the validated
  `ValidatedQueryBundleV1`. A name result is `UNKNOWN` for zero matches,
  `RESOLVED` for one match, and `AMBIGUOUS` for more than one. Capability and
  Card details must expose empty mapped subsets structurally without claiming
  semantic absence.
- [ ] **Step 4:** Keep each production module below the 500-line budget and run
  the model/normalization tests GREEN.

### Task 3: Extend the public `CensusReader` interface

**Files:**
- Modify: `src/manafold_census/query/api.py`
- Modify: `src/manafold_census/query/bundle.py`
- Modify: `src/manafold_census/query/__init__.py`
- Extend: `tests/test_card_lookup.py`

- [ ] **Step 1:** Materialize the normalized name index as an immutable mapping
  in `ValidatedQueryBundleV1`; retain tuples for all one-to-many values.
- [ ] **Step 2:** Add read-only methods:

```text
resolve_card_name(name)
get_card(oracle_id)
get_card_by_name(name)
get_capability(capability_ref)
get_capabilities_for_card(oracle_id)
get_cards_for_capability(capability_ref)
```

`get_card_by_name()` returns a Card detail only for one resolved identity; it
returns the explicit unknown or ambiguous resolution value otherwise. A known
Capability with no mapped cards returns a valid empty subset.
- [ ] **Step 3:** Add positive and negative lookup/detail tests, including the
  no-fuzzy and no-silent-selection cases.
- [ ] **Step 4:** Run all M5-07 and M5-08 focused tests GREEN.

### Task 4: Verify, commit, push, and stop for exact-head review

**Files:**
- No generated output is committed; tests create temporary derived trees.

- [ ] **Step 1:** Run:

```powershell
& C:\Python313\python.exe -m ruff format --check .
& C:\Python313\python.exe -m ruff check .
& C:\Python313\python.exe -m mypy src/manafold_census
$env:PYTHONPATH='src'; & C:\Python313\python.exe -m pytest -q
```

- [ ] **Step 2:** Run a fresh non-editable wheel smoke and import the M5-08
  lookup/detail interface without source-path injection.
- [ ] **Step 3:** Stage only this M5-08 plan, lookup/detail/query changes, and
  `tests/test_card_lookup.py`; do not change M5-06 reports/indexes, M4
  authority, deck parsing, Explorer, packaging, PR, or merge state.
- [ ] **Step 4:** Commit and push one standalone slice:

```powershell
git add -- docs/superpowers/plans/2026-09-15-m5-08-card-capability-lookup.md src/manafold_census/query tests/test_card_lookup.py
git commit -m "feat: add Census card and capability lookup"
git push origin feat/m5-census-0-1
```

- [ ] **Step 5:** Verify exact remote HEAD, clean worktree, exact parent, and no
  PR. Stop with `M5_08_STATUS = NOT_FROZEN`; M5-09, PR, and merge remain
  unauthorized until independent review.

Self-review:
- [ ] Exact/casefolded lookup never Unicode-normalizes or fuzzy-matches.
- [ ] Unknown and ambiguous names are explicit return values.
- [ ] Multiple Oracle identities are never silently selected.
- [ ] Card details expose semantic state before any empty-mapping display.
- [ ] Capability details expose lifecycle, review, links, mapped cards, and
  mapped-subset denominators without creating semantics.
- [ ] Query methods are read-only and deterministic.
- [ ] No deck grammar, Explorer rendering, network, rules execution, or new
  Requirement/Capability authority is introduced.
- [ ] Every production module remains below 500 lines.
