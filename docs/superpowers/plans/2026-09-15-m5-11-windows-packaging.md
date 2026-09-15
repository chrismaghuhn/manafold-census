# M5-11 Windows Packaging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and verify a Windows PyInstaller `onedir` Explorer executable that loads compatible Census bundles from an explicit external path without embedding a Census snapshot or requiring network access.

**Architecture:** Add a packaging-only entry point that translates direct executable arguments into the existing read-only `manafold_census.cli explorer` command. The PyInstaller spec packages application modules and normative schemas only; the Census bundle remains external. A Windows-only workflow builds two isolated directories with one pinned toolchain and compares their functional Explorer output.

**Tech Stack:** Python 3.12.10, PyInstaller 6.22.3, PyInstaller hooks 2026.7, PyInstaller onedir, Windows Server 2022 runner, existing Query Layer compatibility validation, pytest, PowerShell, GitHub Actions.

---

### Task 1: Add the packaging contract tests

**Files:**
- Create: `tests/test_windows_package_smoke.py`
- Read-only references: `docs/superpowers/specs/2026-09-15-m5-census-0-1-design.md`, `src/manafold_census/cli.py`, `src/manafold_census/query/api.py`, `src/manafold_census/release/manifest.py`

- [ ] **Step 1: Write the failing static test.**

Require a console onedir spec named `manafold-census-explorer`, schema data under `share/manafold-census/schemas`, and no bundle data mapping:

~~~python
from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_explorer_spec_is_external_bundle_onedir() -> None:
    spec = (ROOT / "packaging" / "explorer.spec").read_text(encoding="utf-8")
    assert "COLLECT(" in spec
    assert 'name="manafold-census-explorer"' in spec
    assert '"share/manafold-census/schemas"' in spec
    assert "console=True" in spec
    assert '"inputs"' not in spec
    assert '"census-manifest.json"' not in spec
    assert '"reports"' not in spec
    assert '"indexes"' not in spec
~~~

Add a requirements-file test that requires exact PyInstaller/runtime pins and one `--hash=sha256:` token on every non-comment package line. Add executable tests gated by Windows and the exact variables `M5_11_EXE_A`, `M5_11_EXE_B`, and `M5_11_BUNDLE_PATH`.

- [ ] **Step 2: Run RED.**

~~~powershell
$env:PYTHONPATH='src'; & C:\Python313\python.exe -m pytest tests/test_windows_package_smoke.py::test_explorer_spec_is_external_bundle_onedir -q
~~~

Expected: collection succeeds and the test fails because `packaging/explorer.spec` is absent.

### Task 2: Add the direct executable entry point and onedir spec

**Files:**
- Create: `packaging/explorer_entry.py`
- Create: `packaging/explorer.spec`
- Test: `tests/test_windows_package_smoke.py`

- [ ] **Step 1: Implement the packaging-only entry point.**

~~~python
from __future__ import annotations

import sys
from collections.abc import Sequence

from manafold_census.cli import main


def run(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments and arguments[0] == "explorer":
        arguments = arguments[1:]
    return main(["explorer", *arguments])


if __name__ == "__main__":
    raise SystemExit(run())
~~~

It must not read bundles, add semantic/parser logic, or import network functionality.

- [ ] **Step 2: Implement the PyInstaller spec.**

Resolve `PROJECT_ROOT = Path(__file__).resolve().parents[1]`, require `packaging/explorer_entry.py` and `schemas/`, put `src` on `pathex`, and map only `schemas/` to `share/manafold-census/schemas`:

~~~python
PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = PROJECT_ROOT / "packaging" / "explorer_entry.py"
SCHEMA_ROOT = PROJECT_ROOT / "schemas"
datas = [(str(SCHEMA_ROOT), "share/manafold-census/schemas")]
~~~

Use the standard `Analysis` → `PYZ` → `EXE` → `COLLECT` graph with `name="manafold-census-explorer"`, `console=True`, `upx=False`, and no `inputs`, `locks`, `reviewed`, `reports`, `indexes`, `dist`, or Census manifest data. Fail during spec evaluation if the entry point or schema root is missing.

- [ ] **Step 3: Run the static test GREEN.**

~~~powershell
$env:PYTHONPATH='src'; & C:\Python313\python.exe -m pytest tests/test_windows_package_smoke.py::test_explorer_spec_is_external_bundle_onedir -q
~~~

### Task 3: Pin the Windows build/runtime dependencies

**Files:**
- Create: `packaging/windows-requirements.txt`
- Test: `tests/test_windows_package_smoke.py`

- [ ] **Step 1: Add hashes for this exact package set.**

~~~text
altgraph==0.17.5
attrs==26.1.0
jsonschema==4.26.0
jsonschema-specifications==2025.9.1
markdown-it-py==4.2.0
mdurl==0.1.2
packaging==26.3
pefile==2024.8.26
pygments==2.21.0
pyinstaller==6.22.3
pyinstaller-hooks-contrib==2026.7
pywin32-ctypes==0.2.3
referencing==0.37.0
rpds-py==2026.6.3
rich==13.9.4
setuptools==84.0.0
~~~

Every package line must carry the verified wheel SHA-256; the PyInstaller line must select `py3-none-win_amd64` and `rpds-py` must select `cp312-cp312-win_amd64` on the Windows runner.

- [ ] **Step 2: Run the requirements regression.**

~~~powershell
$env:PYTHONPATH='src'; & C:\Python313\python.exe -m pytest tests/test_windows_package_smoke.py -k requirements -q
~~~

### Task 4: Add the pinned Windows build and smoke workflow

**Files:**
- Create: `.github/workflows/windows-explorer.yml`
- Extend: `tests/test_windows_package_smoke.py`

- [ ] **Step 1: Pin the workflow.**

Use `runs-on: windows-2022`, `actions/setup-python@v5`, and `python-version: "3.12.10"`. Set `PYTHONHASHSEED: "0"`, `SOURCE_DATE_EPOCH: "0"`, `TZ: UTC`, `LC_ALL: C.UTF-8`, `LANG: C.UTF-8`, and `PIP_DISABLE_PIP_VERSION_CHECK: "1"`. Use `$env:RUNNER_TEMP\m5-11-build-root`, a `PYI_CONFIG_DIR` below it, and separate `dist-a/work-a` and `dist-b/work-b` directories.

- [ ] **Step 2: Build two external-bundle executables.**

Install the project development extras and then the hash-locked requirements. Invoke PyInstaller twice with:

~~~powershell
python -m PyInstaller --noconfirm --clean --distpath "$buildRoot\dist-a" --workpath "$buildRoot\work-a" packaging\explorer.spec
python -m PyInstaller --noconfirm --clean --distpath "$buildRoot\dist-b" --workpath "$buildRoot\work-b" packaging\explorer.spec
~~~

Create a synthetic Derived Tree under `RUNNER_TEMP` with the existing test fixture builder. Export exact executable paths and the external bundle as `M5_11_EXE_A`, `M5_11_EXE_B`, and `M5_11_BUNDLE_PATH`.

- [ ] **Step 3: Run the Windows smoke tests.**

~~~powershell
$env:PYTHONPATH='src;tests'; & python -m pytest tests/test_windows_package_smoke.py -q
~~~

The tests must prove external `info` execution, absence of an embedded `census-manifest.json` or `inputs` tree, equal functional output from both builds, and nonzero rejection after changing a copied bundle's `compatibility.query_contract` to `census.query.v999`. Executable byte equality is evidence only, never a hard assertion.

### Task 5: Verify, commit, push, and stop for exact-head review

**Files:**
- `packaging/explorer_entry.py`
- `packaging/explorer.spec`
- `packaging/windows-requirements.txt`
- `.github/workflows/windows-explorer.yml`
- `tests/test_windows_package_smoke.py`
- `docs/superpowers/plans/2026-09-15-m5-11-windows-packaging.md`

- [ ] **Step 1: Run local quality gates.**

~~~powershell
C:\Python313\python.exe -m ruff format --check .
C:\Python313\python.exe -m ruff check .
$env:PYTHONPATH='src'; & C:\Python313\python.exe -m mypy src/manafold_census
$env:PYTHONPATH='src'; & C:\Python313\python.exe -m pytest -q
~~~

The normal source suite may skip the environment-gated executable tests; the Windows workflow is the standalone package gate.

- [ ] **Step 2: Verify scope and publish.**

Confirm no M5-12 code, generated Census bundle, generated `dist` output, network code, or Query/M4/report/index/deck semantic change is staged. Then run:

~~~powershell
git add -- .github/workflows/windows-explorer.yml packaging/explorer.spec packaging/explorer_entry.py packaging/windows-requirements.txt tests/test_windows_package_smoke.py docs/superpowers/plans/2026-09-15-m5-11-windows-packaging.md
git diff --cached --name-only
git commit -m "feat: add standalone Windows Explorer packaging"
git push origin feat/m5-census-0-1
~~~

- [ ] **Step 3: Verify the pushed exact head.**

~~~powershell
git status --porcelain=v1
git rev-parse HEAD
git rev-parse origin/feat/m5-census-0-1
gh run list --workflow windows-explorer.yml --branch feat/m5-census-0-1 --limit 1 --json databaseId,headSha,status,conclusion,url
gh pr list --head feat/m5-census-0-1 --state open --json number,title,url
~~~

Leave `M5_11_STATUS = NOT_FROZEN`, `M5_12_AUTHORIZED = NO`, `PR_AUTHORIZED = NO`, and `MERGE_AUTHORIZED = NO` for exact-head review.
