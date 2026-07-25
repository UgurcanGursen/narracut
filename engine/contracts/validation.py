"""Draft 2020-12 validation with stable, structured error reporting."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


@dataclass(frozen=True)
class ValidationIssue:
    source_file: str
    json_pointer: str
    code: str
    message: str


@dataclass(frozen=True)
class ValidationResult:
    issues: tuple[ValidationIssue, ...] = ()

    @property
    def is_valid(self) -> bool:
        return not self.issues

    def extend(self, issues: Iterable[ValidationIssue]) -> "ValidationResult":
        return ValidationResult(self.issues + tuple(issues))


def json_pointer(parts: Iterable[Any]) -> str:
    encoded = [
        str(part).replace("~", "~0").replace("/", "~1")
        for part in parts
    ]
    return "/" + "/".join(encoded) if encoded else ""


_VALIDATOR_CODES = {
    "additionalProperties": "SCHEMA_ADDITIONAL_PROPERTIES",
    "const": "SCHEMA_CONST",
    "enum": "SCHEMA_ENUM",
    "format": "SCHEMA_FORMAT",
    "minimum": "SCHEMA_MINIMUM",
    "minItems": "SCHEMA_MIN_ITEMS",
    "oneOf": "SCHEMA_ONE_OF",
    "pattern": "SCHEMA_PATTERN",
    "required": "SCHEMA_REQUIRED",
    "type": "SCHEMA_TYPE",
    "uniqueItems": "SCHEMA_UNIQUE_ITEMS",
}


class SchemaCatalog:
    """Loads the canonical schema directory without maintaining Python copies."""

    def __init__(self, schema_root: Path | str):
        self.schema_root = Path(schema_root).resolve()
        self._schemas: dict[str, dict[str, Any]] = {}
        resources: list[tuple[str, Resource[Any]]] = []

        for path in sorted(self.schema_root.glob("*.schema.json")):
            schema = json.loads(path.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)
            schema_id = schema.get("$id")
            if not isinstance(schema_id, str) or not schema_id:
                raise ValueError(f"Schema has no stable $id: {path}")
            self._schemas[path.name] = schema
            resources.append((schema_id, Resource.from_contents(schema)))

        if not self._schemas:
            raise ValueError(f"No canonical schemas found under {self.schema_root}")

        self._registry = Registry().with_resources(resources)
        self._format_checker = FormatChecker()

    @property
    def schema_names(self) -> tuple[str, ...]:
        return tuple(sorted(self._schemas))

    def schema(self, schema_name: str) -> dict[str, Any]:
        try:
            return self._schemas[schema_name]
        except KeyError as exc:
            raise KeyError(f"Unknown canonical schema: {schema_name}") from exc

    def validate(
        self,
        instance: Any,
        schema_name: str,
        source_file: Path | str,
    ) -> ValidationResult:
        validator = Draft202012Validator(
            self.schema(schema_name),
            registry=self._registry,
            format_checker=self._format_checker,
        )
        issues = []
        for error in sorted(
            validator.iter_errors(instance),
            key=lambda item: (
                tuple(str(part) for part in item.absolute_path),
                item.message,
            ),
        ):
            issues.append(
                ValidationIssue(
                    source_file=str(source_file),
                    json_pointer=json_pointer(error.absolute_path),
                    code=_VALIDATOR_CODES.get(
                        error.validator, "SCHEMA_VALIDATION"
                    ),
                    message=error.message,
                )
            )
        return ValidationResult(tuple(issues))

    def validate_file(
        self,
        path: Path | str,
        schema_name: str,
    ) -> ValidationResult:
        source = Path(path)
        try:
            instance = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return ValidationResult(
                (
                    ValidationIssue(
                        source_file=str(source),
                        json_pointer="",
                        code="JSON_READ_ERROR",
                        message=str(exc),
                    ),
                )
            )
        return self.validate(instance, schema_name, source)
