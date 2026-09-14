import json
import subprocess
import sys
from pathlib import Path

from manafold_census.resources import project_data_root

M4_SCHEMA_NAMES = (
    "capability-claim.v1.schema.json",
    "capability-definition.v1.schema.json",
    "capability-evolution.v1.schema.json",
    "capability-ontology-manifest.v1.schema.json",
    "capability-relations.v1.schema.json",
    "capability-review.v1.schema.json",
    "capability-candidate-cluster.v1.schema.json",
    "candidate-grouping-policy.v1.schema.json",
    "requirement-capability-link.v1.schema.json",
    "requirement-mapping-decision.v1.schema.json",
    "source-requirement-admissibility.v1.schema.json",
    "capability-report.v1.schema.json",
)


def test_project_data_root_contains_normative_schemas_and_fixture_data() -> None:
    root = project_data_root()

    assert (root / "schemas" / "source-artifact.v1.schema.json").is_file()
    assert (root / "schemas" / "oracle-corpus-report.v1.schema.json").is_file()
    assert (root / "schemas" / "oracle-record-index-manifest.v1.schema.json").is_file()
    assert (root / "schemas" / "structural-card.v1.schema.json").is_file()
    assert (
        root / "schemas" / "structural-card-index-manifest.v1.schema.json"
    ).is_file()
    assert (root / "schemas" / "structural-card-report.v1.schema.json").is_file()
    assert (root / "schemas" / "semantic-requirement.v1.schema.json").is_file()
    assert (root / "schemas" / "semantic-requirement-bundle.v1.schema.json").is_file()
    assert (root / "config" / "sources" / "scryfall-oracle.v1.json").is_file()
    assert (root / "fixtures" / "source" / "example.txt").is_file()
    assert (root / "fixtures" / "specs" / "example-study.json").is_file()
    assert isinstance(root, Path)


def test_project_data_root_contains_all_m3_schema_resources() -> None:
    root = project_data_root()
    for schema_name in (
        "analysis-manifest.v1.schema.json",
        "analysis-report.v1.schema.json",
        "analysis-trace.v1.schema.json",
        "card-analysis.v1.schema.json",
        "negative-requirement-authority.v1.schema.json",
        "pattern-registry.v1.schema.json",
        "producer-registry.v1.schema.json",
    ):
        path = root / "schemas" / schema_name
        assert path.is_file()
        assert json.loads(path.read_text(encoding="utf-8"))["$schema"] == (
            "https://json-schema.org/draft/2020-12/schema"
        )


def test_project_data_root_contains_all_required_m3_analysis_fixtures() -> None:
    root = project_data_root()
    for fixture_name in (
        "golden-cards.json",
        "negative-authority.v1.json",
        "pattern-registry.v1.json",
    ):
        path = root / "fixtures" / "analysis" / fixture_name
        assert path.is_file()
        assert isinstance(json.loads(path.read_text(encoding="utf-8")), object)


def test_project_data_root_contains_all_m4_schema_resources() -> None:
    root = project_data_root()
    for schema_name in M4_SCHEMA_NAMES:
        path = root / "schemas" / schema_name
        assert path.is_file()
        assert json.loads(path.read_text(encoding="utf-8"))["$schema"] == (
            "https://json-schema.org/draft/2020-12/schema"
        )


def test_project_data_root_contains_synthetic_m4_fixtures() -> None:
    root = project_data_root()
    fixtures = sorted((root / "fixtures" / "capability").glob("*.json"))

    assert fixtures
    for path in fixtures:
        document = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(document, dict)
        assert document["real_corpus"] is False
        assert document["real_requirement_mapping"] is False
        assert document["real_capability_activation"] is False


def test_fresh_non_editable_wheel_contains_all_m4_resources(
    tmp_path: Path,
) -> None:
    wheel_dir = tmp_path / "wheel"
    wheel_dir.mkdir()
    build = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            ".",
            "--no-deps",
            "--wheel-dir",
            str(wheel_dir),
        ],
        cwd=Path(__file__).parents[1],
        capture_output=True,
        text=True,
        check=False,
    )
    assert build.returncode == 0, build.stdout + build.stderr
    wheels = tuple(wheel_dir.glob("*.whl"))
    assert len(wheels) == 1

    venv_dir = tmp_path / "venv"
    create_venv = subprocess.run(
        [sys.executable, "-m", "venv", str(venv_dir)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert create_venv.returncode == 0, create_venv.stdout + create_venv.stderr
    venv_python = venv_dir / (
        "Scripts/python.exe" if sys.platform == "win32" else "bin/python"
    )
    install = subprocess.run(
        [str(venv_python), "-m", "pip", "install", "--no-deps", str(wheels[0])],
        capture_output=True,
        text=True,
        check=False,
    )
    assert install.returncode == 0, install.stdout + install.stderr

    probe = (
        "import json\n"
        "from manafold_census.resources import project_data_root\n"
        f"root = project_data_root()\n"
        f"schemas = {M4_SCHEMA_NAMES!r}\n"
        "assert all((root / 'schemas' / name).is_file() for name in schemas)\n"
        "fixtures = sorted((root / 'fixtures' / 'capability').glob('*.json'))\n"
        "assert fixtures\n"
        "for path in fixtures:\n"
        "    document = json.loads(path.read_text(encoding='utf-8'))\n"
        "    assert document['real_corpus'] is False\n"
        "    assert document['real_requirement_mapping'] is False\n"
        "    assert document['real_capability_activation'] is False\n"
        "print('m4-wheel-resources=PASS')\n"
    )
    smoke = subprocess.run(
        [str(venv_python), "-c", probe],
        capture_output=True,
        text=True,
        check=False,
    )
    assert smoke.returncode == 0, smoke.stdout + smoke.stderr
    assert "m4-wheel-resources=PASS" in smoke.stdout
