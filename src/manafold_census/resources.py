"""Locate repository or installed project data without source-path injection."""

from __future__ import annotations

import sys
import sysconfig
from pathlib import Path

_INSTALLED_DATA_SUBDIRECTORY = Path("share") / "manafold-census"


def project_data_root() -> Path:
    """Return the root containing the normative schemas and fixture data."""

    package_file = Path(__file__).resolve()
    source_root = package_file.parents[2]
    package_parent = package_file.parent.parent
    interpreter_data_root = Path(sysconfig.get_path("data"))
    candidates = (
        source_root,
        package_parent / _INSTALLED_DATA_SUBDIRECTORY,
        interpreter_data_root / _INSTALLED_DATA_SUBDIRECTORY,
        Path(sys.prefix) / _INSTALLED_DATA_SUBDIRECTORY,
    )
    for candidate in candidates:
        if (candidate / "schemas" / "source-artifact.v1.schema.json").is_file():
            return candidate
    raise FileNotFoundError(
        "Census schemas are not available in the source tree or installation"
    )
