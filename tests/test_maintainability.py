import json
import re
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).parents[1]
MAX_PRODUCTION_MODULE_LINES = 500


def test_production_modules_stay_below_maintainability_budget() -> None:
    modules = sorted((REPOSITORY_ROOT / "src" / "manafold_census").rglob("*.py"))

    assert modules
    for module in modules:
        line_count = len(module.read_text(encoding="utf-8").splitlines())
        assert line_count <= MAX_PRODUCTION_MODULE_LINES, (
            f"{module.relative_to(REPOSITORY_ROOT)} has {line_count} lines; "
            f"split it before extending it past {MAX_PRODUCTION_MODULE_LINES}"
        )


def test_m2_semantic_modules_stay_below_maintainability_budget() -> None:
    modules = sorted(
        (REPOSITORY_ROOT / "src" / "manafold_census" / "semantic").glob("*.py")
    )

    assert modules
    for module in modules:
        line_count = len(module.read_text(encoding="utf-8").splitlines())
        assert line_count <= MAX_PRODUCTION_MODULE_LINES, (
            f"{module.relative_to(REPOSITORY_ROOT)} has {line_count} lines; "
            f"split it before extending it past {MAX_PRODUCTION_MODULE_LINES}"
        )


def test_m3_analysis_modules_stay_below_maintainability_budget() -> None:
    modules = sorted(
        (REPOSITORY_ROOT / "src" / "manafold_census" / "analysis").glob("*.py")
    )

    assert modules
    for module in modules:
        line_count = len(module.read_text(encoding="utf-8").splitlines())
        assert line_count <= MAX_PRODUCTION_MODULE_LINES, (
            f"{module.relative_to(REPOSITORY_ROOT)} has {line_count} lines; "
            f"split it before extending it past {MAX_PRODUCTION_MODULE_LINES}"
        )


def test_m3_analysis_scope_forbids_later_milestone_and_dynamic_execution_logic() -> (
    None
):
    forbidden = (
        (re.compile(r"\b38,?740\b"), "hard-coded global card count"),
        (
            re.compile(
                r"\b(?:capability|capability_id|engine_support|card_executor|"
                r"implement_card)\b",
                re.IGNORECASE,
            ),
            "engine/capability logic",
        ),
        (
            re.compile(
                r"\b(?:source-refresh|source-fetch-pinned|source-acquire|"
                r"requests|urllib|httpx|aiohttp|boto3|urlopen)\b"
            ),
            "source acquisition",
        ),
        (
            re.compile(
                r"(?<!\.)\b(?:eval|exec|compile|__import__)\s*\(|"
                r"\b(?:importlib|subprocess|pickle)\b"
            ),
            "dynamic execution",
        ),
        (
            re.compile(r"\b(?:m4|task[_ -]?(?:9|10|11))\b", re.IGNORECASE),
            "later milestone",
        ),
    )
    for module in sorted(
        (REPOSITORY_ROOT / "src" / "manafold_census" / "analysis").glob("*.py")
    ):
        text = module.read_text(encoding="utf-8")
        for pattern, label in forbidden:
            assert pattern.search(text) is None, (
                f"{module.relative_to(REPOSITORY_ROOT)} contains forbidden {label}"
            )


def test_source_lock_schema_references_the_normative_source_artifact_schema() -> None:
    schema_path = REPOSITORY_ROOT / "schemas" / "source-lock.v1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    assert schema["properties"]["artifacts"]["items"] == {
        "$ref": "source-artifact.v1.schema.json"
    }
    assert "$defs" not in schema


def test_maintainer_commands_do_not_inject_platform_specific_source_paths() -> None:
    justfile = (REPOSITORY_ROOT / "justfile").read_text(encoding="utf-8")
    pyproject = (REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "powershell.exe" not in justfile
    assert "PYTHONPATH" not in justfile
    assert "pythonpath" not in pyproject.lower()


def test_task_01_golden_path_separates_live_acquisition_from_offline_checks() -> None:
    justfile = (REPOSITORY_ROOT / "justfile").read_text(encoding="utf-8")

    for command in (
        "source-refresh",
        "source-fetch-pinned",
        "corpus-build",
        "corpus-check",
        "structural-build",
        "structural-check",
    ):
        assert f"{command}:" in justfile
    check_line = next(
        line for line in justfile.splitlines() if line.startswith("check:")
    )
    assert (
        check_line
        == "check: doctor lint typecheck test reproduce corpus-check structural-check"
    )
    assert "source-acquire" not in check_line


def test_ci_contains_fresh_non_editable_wheel_smoke_path() -> None:
    workflow = (REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )

    assert 'python-version: "3.12"' in workflow
    assert "pip wheel" in workflow
    assert "python -m venv" in workflow
    assert "non-editable" in workflow
    assert "corpus-check --synthetic" in workflow


def test_ci_contains_offline_structural_gate_and_all_m1_schema_smoke() -> None:
    workflow = (REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )

    assert "structural-check --synthetic" in workflow
    for schema in (
        "structural-card.v1.schema.json",
        "structural-card-index-manifest.v1.schema.json",
        "structural-card-report.v1.schema.json",
    ):
        assert schema in workflow
    assert 'cd "$RUNNER_TEMP"' in workflow


def test_directly_imported_referencing_dependency_is_declared() -> None:
    pyproject = (REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "referencing>=" in pyproject
