import json
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
