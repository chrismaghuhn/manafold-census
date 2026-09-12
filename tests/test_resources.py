from pathlib import Path

from manafold_census.resources import project_data_root


def test_project_data_root_contains_normative_schemas_and_fixture_data() -> None:
    root = project_data_root()

    assert (root / "schemas" / "source-artifact.v1.schema.json").is_file()
    assert (root / "fixtures" / "source" / "example.txt").is_file()
    assert (root / "fixtures" / "specs" / "example-study.json").is_file()
    assert isinstance(root, Path)
