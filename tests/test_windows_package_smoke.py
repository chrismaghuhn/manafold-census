"""Windows standalone Explorer packaging contract and smoke tests."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import cast

import pytest

from manafold_census.canonical import JSONValue, canonical_json_bytes

ROOT = Path(__file__).parents[1]
_PINNED_PACKAGES = {
    "altgraph": "0.17.5",
    "attrs": "26.1.0",
    "jsonschema": "4.26.0",
    "jsonschema-specifications": "2025.9.1",
    "markdown-it-py": "4.2.0",
    "mdurl": "0.1.2",
    "packaging": "26.3",
    "pefile": "2024.8.26",
    "pygments": "2.21.0",
    "pyinstaller": "6.22.3",
    "pyinstaller-hooks-contrib": "2026.7",
    "pywin32-ctypes": "0.2.3",
    "referencing": "0.37.0",
    "rpds-py": "2026.6.3",
    "rich": "13.9.4",
    "setuptools": "84.0.0",
    "typing-extensions": "4.16.0",
}


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
    assert '"locks"' not in spec
    assert '"reviewed"' not in spec
    assert '"dist"' not in spec
    exe_block = spec.split("exe = EXE(", 1)[1].split("COLLECT(", 1)[0]
    collect_block = spec.split("COLLECT(", 1)[1]
    assert "exclude_binaries=True" in exe_block
    assert "a.binaries" not in exe_block
    assert "a.datas" not in exe_block
    assert "a.binaries" in collect_block
    assert "a.datas" in collect_block


def test_windows_workflow_pins_reproducible_build_inputs() -> None:
    workflow = (ROOT / ".github" / "workflows" / "windows-explorer.yml").read_text(
        encoding="utf-8"
    )
    assert "runs-on: windows-2022" in workflow
    assert 'python-version: "3.12.10"' in workflow
    assert 'PYTHONHASHSEED: "0"' in workflow
    assert 'SOURCE_DATE_EPOCH: "946684800"' in workflow
    assert "TZ: UTC" in workflow
    assert "PYINSTALLER_CONFIG_DIR" in workflow
    assert "--require-hashes -r packaging/windows-requirements.txt" in workflow
    assert "dist-a" in workflow and "dist-b" in workflow


def test_windows_requirements_are_hash_locked() -> None:
    path = ROOT / "packaging" / "windows-requirements.txt"
    lines = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert len(lines) == len(_PINNED_PACKAGES)
    seen: set[str] = set()
    for line in lines:
        package, version_and_hash = line.split("==", 1)
        version = version_and_hash.split(" ", 1)[0]
        assert package in _PINNED_PACKAGES
        assert version == _PINNED_PACKAGES[package]
        assert "--hash=sha256:" in line
        seen.add(package)
    assert seen == set(_PINNED_PACKAGES)


def _package_context() -> tuple[Path, Path, Path]:
    if platform.system() != "Windows":
        pytest.skip("M5-11 executable smoke is Windows-only")
    values = tuple(
        os.environ.get(name)
        for name in ("M5_11_EXE_A", "M5_11_EXE_B", "M5_11_BUNDLE_PATH")
    )
    if any(value is None for value in values):
        pytest.skip("M5-11 executable paths were not provisioned")
    paths = tuple(Path(cast(str, value)) for value in values)
    if not paths[0].is_file() or not paths[1].is_file() or not paths[2].is_dir():
        pytest.skip("M5-11 executable or bundle path is unavailable")
    return paths


def _run_info(executable: Path, bundle: Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    for name in (
        "PYTHONPATH",
        "PYTHONHOME",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    ):
        environment.pop(name, None)
    environment["PYTHONHASHSEED"] = "0"
    environment["TZ"] = "UTC"
    return subprocess.run(
        [str(executable), "--bundle", str(bundle), "info"],
        cwd=executable.parent,
        env=environment,
        capture_output=True,
        check=False,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )


def test_windows_package_loads_external_bundle_and_rebuilds_functionally() -> None:
    executable_a, executable_b, bundle = _package_context()
    outputs: list[str] = []
    for executable in (executable_a, executable_b):
        package_root = executable.parent
        assert not (package_root / "inputs").exists()
        assert not any(
            item.name == "census-manifest.json" for item in package_root.rglob("*")
        )
        result = _run_info(executable, bundle)
        assert result.returncode == 0, result.stderr
        assert "Census Explorer context" in result.stdout
        assert "Census release version" in result.stdout
        assert "Semantic coverage limitation" in result.stdout
        outputs.append(result.stdout)
    assert outputs[0] == outputs[1]


def test_windows_package_rejects_incompatible_external_bundle(
    tmp_path: Path,
) -> None:
    executable_a, _executable_b, bundle = _package_context()
    incompatible = tmp_path / "incompatible-bundle"
    shutil.copytree(bundle, incompatible)
    manifest_path = incompatible / "census-manifest.json"
    manifest = cast(dict[str, JSONValue], json.loads(manifest_path.read_bytes()))
    compatibility = cast(dict[str, JSONValue], manifest["compatibility"])
    compatibility["query_contract"] = "census.query.v999"
    manifest_path.write_bytes(canonical_json_bytes(manifest))

    result = _run_info(executable_a, incompatible)
    assert result.returncode != 0
    assert "query_contract" in result.stderr
