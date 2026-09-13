"""Structural JSON-Schema validation and Python cross-field invariants."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator  # type: ignore[import-untyped]
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from .canonical import canonical_json_bytes
from .digest import measure_file
from .models import SourceArtifact
from .resources import project_data_root

SCHEMA_DIRECTORY = project_data_root() / "schemas"


class SchemaValidationError(ValueError):
    """Raised when a wire document violates its structural or cross-field contract."""


def _resolve_schema_path(schema: str | Path) -> Path:
    schema_path = Path(schema)
    if not schema_path.is_absolute():
        schema_path = SCHEMA_DIRECTORY / schema_path
    if not schema_path.is_file():
        raise FileNotFoundError(f"schema file does not exist: {schema_path}")
    return schema_path


def _read_json_document(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        document = json.load(stream)
    if not isinstance(document, dict):
        raise ValueError(f"schema must be a JSON object: {path}")
    return document


def _schema_validator(schema_path: Path, schema_document: dict[str, Any]) -> Any:
    if schema_path.name != "source-lock.v1.schema.json":
        if schema_path.name == "semantic-requirement-bundle.v1.schema.json":
            requirement_path = SCHEMA_DIRECTORY / "semantic-requirement.v1.schema.json"
            requirement_document = _read_json_document(requirement_path)
            requirement_id = requirement_document.get("$id")
            if not isinstance(requirement_id, str):
                raise ValueError("requirement schema must define a string $id")
            registry = Registry().with_resource(
                requirement_id,
                Resource.from_contents(
                    requirement_document, default_specification=DRAFT202012
                ),
            )
            return Draft202012Validator(schema_document, registry=registry)
        return Draft202012Validator(schema_document)

    source_artifact_path = SCHEMA_DIRECTORY / "source-artifact.v1.schema.json"
    source_artifact_document = _read_json_document(source_artifact_path)
    source_artifact_id = source_artifact_document.get("$id")
    if not isinstance(source_artifact_id, str):
        raise ValueError("source artifact schema must define a string $id")
    registry = Registry().with_resource(
        source_artifact_id,
        Resource.from_contents(
            source_artifact_document, default_specification=DRAFT202012
        ),
    )
    return Draft202012Validator(schema_document, registry=registry)


def _error_path(error: Any) -> str:
    path = ".".join(str(part) for part in error.path)
    return path or "$"


def _format_schema_error(error: Any) -> str:
    path = _error_path(error)
    if error.validator == "additionalProperties":
        return f"{path}: additional properties are not allowed: {error.message}"
    if error.validator == "minimum":
        return f"{path} must be greater than or equal to {error.validator_value}"
    return f"{path}: {error.message}"


def _validate_cross_field_invariants(document: object, schema_name: str) -> None:
    if not isinstance(document, dict):
        return

    if schema_name == "source-lock.v1.schema.json":
        artifacts = document["artifacts"]
        source_ids = [artifact["source_id"] for artifact in artifacts]
        if len(source_ids) != len(set(source_ids)):
            raise SchemaValidationError("source lock contains duplicate source_id")
        if source_ids != sorted(source_ids):
            raise SchemaValidationError(
                "source lock artifacts must be sorted by source_id"
            )

    if schema_name == "study-spec.v1.schema.json":
        try:
            canonical_json_bytes(document["parameters"])
        except (TypeError, ValueError) as error:
            raise SchemaValidationError(
                f"study parameters are not canonical JSON: {error}"
            ) from error


def validate_document(document: object, schema: str | Path) -> None:
    """Validate one wire document against a repository JSON Schema and invariants."""

    schema_path = _resolve_schema_path(schema)
    schema_document = _read_json_document(schema_path)
    validator = _schema_validator(schema_path, schema_document)
    errors = sorted(
        validator.iter_errors(document),
        key=lambda error: tuple(str(part) for part in error.path),
    )
    if errors:
        error = errors[0]
        raise SchemaValidationError(_format_schema_error(error))
    _validate_cross_field_invariants(document, schema_path.name)


def validate_source_file(artifact: SourceArtifact, path: str | Path) -> None:
    """Verify that a local file matches a SourceArtifact's bytes and length."""

    measurement = measure_file(path)
    if measurement.sha256 != artifact.sha256:
        raise ValueError("source digest mismatch")
    if measurement.byte_length != artifact.byte_length:
        raise ValueError("source byte length mismatch")
