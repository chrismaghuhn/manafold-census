# M5-10 Offline Explorer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Rich-based offline Explorer that navigates the frozen Census Query Layer and Deck Analysis without adding semantic inference, parser logic, Capability logic, network access, or Rules Execution.

**Architecture:** Keep the root CLI as a registration/dispatch seam and put Explorer command parsing in explorer/cli.py. Put only presentation formatting in explorer/render.py; renderers receive typed M5-07/M5-08/M5-09 values and never read private bundle state or derive semantic states. Add only small read-only enumeration methods to CensusReader so Explorer navigation crosses the existing public query interface.

**Tech Stack:** Python 3.12+, Rich runtime dependency, argparse, shlex, frozen CensusReader, M5-08 lookup models, M5-09 DeckAnalysisV1, pytest, Ruff, mypy, PowerShell.

---

### Task 1: Add failing Explorer smoke tests

**Files:**
- Create: tests/test_explorer_smoke.py
- Read-only references: docs/superpowers/specs/2026-09-15-m5-census-0-1-design.md, src/manafold_census/query/api.py, src/manafold_census/query/deck.py, src/manafold_census/cli.py

- [ ] **Step 1: Write the failing tests.**

Build the existing synthetic M5-06 derived tree through open_bundle. Call the future root CLI with explicit bundle paths and assert the presentation delegates to the Query Layer:

~~~python
def test_explorer_info_and_exact_card_search(tmp_path, capsys):
    root = _derived_bundle(tmp_path)
    assert main(["explorer", "--bundle", str(root), "info"]) == 0
    assert "Census release" in capsys.readouterr().out

    assert (
        main(["explorer", "--bundle", str(root), "card", "search", "Fixture Card"]) == 0
    )
    output = capsys.readouterr().out
    assert "AMBIGUOUS" in output
    assert "5" in output


def test_explorer_card_show_and_capability_list_are_offline(tmp_path, capsys):
    root = _derived_bundle(tmp_path)
    assert (
        main(
            [
                "explorer",
                "--bundle",
                str(root),
                "card",
                "show",
                ORACLE_ID,
            ]
        )
        == 0
    )
    assert "semantic_state" in capsys.readouterr().out

    assert main(["explorer", "--bundle", str(root), "capability", "list"]) == 0
    assert "Draw cards" in capsys.readouterr().out


def test_explorer_unknown_and_ambiguous_card_show_are_explicit(tmp_path, capsys):
    root = _derived_bundle(tmp_path)
    assert (
        main(["explorer", "--bundle", str(root), "card", "show", "Fixture Card"]) == 0
    )
    assert "AMBIGUOUS" in capsys.readouterr().out
    assert main(["explorer", "--bundle", str(root), "card", "show", "not a card"]) == 0
    assert "UNKNOWN" in capsys.readouterr().out
~~~

Also cover requirement/capability traces, unresolved output, deck analyze, shell exit, and the absence of network/rules calls through the same explicit-bundle command path.

- [ ] **Step 2: Run the focused tests and confirm RED.**

~~~powershell
$env:PYTHONPATH='src'; & C:\Python313\python.exe -m pytest tests/test_explorer_smoke.py -q
~~~

Expected: collection fails because manafold_census.explorer and its root CLI registration do not yet exist.

### Task 2: Complete only the read-only Query Layer enumeration seams

**Files:**
- Modify: src/manafold_census/query/api.py
- Extend: tests/test_explorer_smoke.py

- [ ] **Step 1: Add public, semantics-preserving navigation methods.**

Add these methods to CensusReader:

~~~text
search_cards(query) -> CardNameResolutionV1
list_card_semantic_views() -> tuple[CardSemanticViewV1, ...]
list_capabilities() -> tuple[CapabilityDetailViewV1, ...]
get_requirements_for_capability(ref) -> tuple[RequirementSummaryV1, ...] | QueryNotFoundV1
~~~

search_cards delegates to the existing exact/casefolded resolve_card_name seam. list_card_semantic_views delegates to get_card_semantic_view for the validated structural identities in canonical Oracle order. list_capabilities delegates to build_capability_detail for validated Capability definitions in family/version/claim order. get_requirements_for_capability delegates to get_capability and returns its exact linked Requirement summaries or the existing explicit QueryNotFoundV1.

These methods must not inspect names, source text, M3 patterns, or Capability claims themselves; they only reuse existing Query Layer builders and validated joins.

- [ ] **Step 2: Add read-only enumeration tests.**

Assert that the new methods return canonical order, preserve the existing CardSemanticView before any empty Capability interpretation, return explicit not-found for an unknown Capability reference, and do not write any bundle bytes.

- [ ] **Step 3: Run Query Layer tests GREEN.**

~~~powershell
$env:PYTHONPATH='src'; & C:\Python313\python.exe -m pytest tests/test_census_query.py tests/test_card_lookup.py tests/test_deck_analysis.py tests/test_explorer_smoke.py -q
~~~

### Task 3: Implement safe Rich renderers

**Files:**
- Create: src/manafold_census/explorer/render.py
- Create: src/manafold_census/explorer/__init__.py
- Modify: pyproject.toml

- [ ] **Step 1: Add Rich as a runtime dependency.**

Add rich>=13.7,<14 to project dependencies so an installed Explorer has its declared renderer dependency. Do not add Textual, Electron, Qt, web, server, database, or network dependencies.

- [ ] **Step 2: Implement render-only functions.**

Use Console(markup=False, highlight=False) and Rich Text/Table/Panel values. Implement renderers for:

~~~text
render_info(metadata)
render_card_search(resolution)
render_card_detail(detail)
render_capability_list(details)
render_capability_detail(detail)
render_requirement_trace(trace)
render_mapping_trace(trace)
render_unresolved(semantic_views)
render_deck_analysis(analysis)
~~~

Every renderer displays the exact typed state, outcome, IDs, quantities, denominators, lifecycle/review values, or trace fields already supplied by the Query/Deck Layer. It must not call semantic_state_for, infer meaning from empty arrays, normalize names, parse card text, execute rules, or access private bundle members. Use Text objects or markup-disabled Console for source names, claims, trace fragments, and deck names so untrusted brackets/control text is not treated as Rich markup.

- [ ] **Step 3: Add renderer tests.**

Assert that unresolved and NO_REQUIREMENTS_APPLICABLE values are printed as distinct exact labels, empty Capability collections do not print an absence claim, mapped-subset denominators remain visible, ambiguous matches list all Oracle identities, and bracket/control text is rendered as text.

### Task 4: Implement offline Explorer commands and shell

**Files:**
- Create: src/manafold_census/explorer/cli.py
- Modify: src/manafold_census/cli.py
- Extend: tests/test_explorer_smoke.py

- [ ] **Step 1: Register the explicit command grammar.**

Register this root CLI shape:

~~~text
manafold_census explorer --bundle BUNDLE info
manafold_census explorer --bundle BUNDLE card search TEXT...
manafold_census explorer --bundle BUNDLE card show NAME_OR_ORACLE_ID...
manafold_census explorer --bundle BUNDLE requirement show REQUIREMENT_ID
manafold_census explorer --bundle BUNDLE capability list
manafold_census explorer --bundle BUNDLE capability show CAPABILITY_REF
manafold_census explorer --bundle BUNDLE unresolved
manafold_census explorer --bundle BUNDLE trace requirement REQUIREMENT_ID
manafold_census explorer --bundle BUNDLE trace mapping LINK_ID
manafold_census explorer --bundle BUNDLE deck analyze DECK_FILE
manafold_census explorer --bundle BUNDLE shell
~~~

The bundle path is mandatory and explicit. open_bundle is called once per command before any render. Missing/corrupt bundles follow the existing root CLI failure path and return exit code 1.

- [ ] **Step 2: Keep lookup and Capability reference parsing deterministic.**

card search delegates directly to reader.search_cards. card show first attempts exact Oracle lookup, then delegates the complete remaining text to reader.get_card_by_name; UNKNOWN and AMBIGUOUS are rendered without selection. capability show accepts one deterministic display form, family_id/version/claim_digest separated by a single slash, constructs CapabilityRefV1, and lets reader.get_capability return the typed detail or QueryNotFoundV1. This is display syntax only; it does not parse semantic claims.

- [ ] **Step 3: Implement deck and trace commands through existing seams.**

deck analyze reads the exact path with analyze_deck_file(reader) and renders DeckAnalysisV1. trace commands call reader.trace_requirement or reader.trace_mapping. unresolved calls reader.list_card_semantic_views and filters only the returned SemanticStateV1 enum in Explorer navigation; no state is inferred from mappings or requirements.

- [ ] **Step 4: Implement a bounded shell over the same dispatcher.**

shell reads one line at a time with input("explorer> "), uses shlex.split, supports the same subcommands without a second bundle argument, exits on exit/quit/EOF, prints parse errors without mutating the Reader, and never executes arbitrary Python or shell text. Add a smoke test for info, card search, and exit.

### Task 5: Verify Explorer boundaries and finish the M5-10 slice

**Files:**
- Extend: tests/test_explorer_smoke.py
- No generated Census, report, bundle, or Explorer output may be committed.
- Modify: .github/workflows/ci.yml so the --no-deps Fresh Wheel smoke installs the declared Rich runtime dependency.

- [ ] **Step 1: Add boundary tests.**

Test missing/corrupt bundle rejection, explicit unknown/ambiguous values, all required command families, deterministic repeated output, shell exit, deck analysis delegation, no bundle writes, and a source scan proving explorer modules contain no eval, exec, pickle, network, database, or Rules Execution usage.

- [ ] **Step 2: Run local quality and full tests.**

~~~powershell
& C:\Python313\python.exe -m ruff format --check .
& C:\Python313\python.exe -m ruff check .
& C:\Python313\python.exe -m mypy src/manafold_census
$env:PYTHONPATH='src'; & C:\Python313\python.exe -m pytest -q
& C:\Python313\python.exe -m manafold_census.cli reproduce
~~~

- [ ] **Step 3: Run fresh wheel smoke.**

Build a wheel in a fresh temporary directory, install it into a fresh virtual environment with its declared dependencies, import manafold_census.explorer.cli without PYTHONPATH, run doctor, and execute one explicit offline Explorer info command against a temporary synthetic derived tree.

- [ ] **Step 4: Check module LOC and exact scope.**

~~~powershell
$modules = @(
  'src/manafold_census/explorer/cli.py',
  'src/manafold_census/explorer/render.py',
  'src/manafold_census/query/api.py',
  'src/manafold_census/cli.py'
)
foreach ($module in $modules) {
  if ((Get-Content -LiteralPath $module).Count -ge 500) {
    throw "$module exceeds the M5 module budget"
  }
}
~~~

Stage only the M5-10 plan, Explorer package, Query Layer navigation methods, root CLI registration, dependency declaration, and Explorer tests. Do not modify deck parsing, Capability validation, M4 authority, Census bundles, reports, indexes, network code, Rules Execution, or packaging beyond the runtime Rich dependency.

- [ ] **Step 5: Commit, push, and stop for exact-head review.**

~~~powershell
git add -- docs/superpowers/plans/2026-09-15-m5-10-offline-explorer.md .github/workflows/ci.yml src/manafold_census/explorer src/manafold_census/query/api.py src/manafold_census/cli.py pyproject.toml tests/test_explorer_smoke.py
git diff --cached --name-only
git commit -m 'feat: add offline Census Explorer'
git push origin feat/m5-census-0-1
~~~

Verify the local and origin heads match, worktree is clean, and no open PR exists. Leave:

~~~text
M5_10_STATUS      = NOT_FROZEN
M5_11_AUTHORIZED  = NO
PR_AUTHORIZED     = NO
MERGE_AUTHORIZED  = NO
~~~
