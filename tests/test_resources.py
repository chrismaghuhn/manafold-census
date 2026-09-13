import json
from pathlib import Path

from manafold_census.resources import project_data_root


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
