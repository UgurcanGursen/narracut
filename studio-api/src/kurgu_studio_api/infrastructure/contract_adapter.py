"""Fixed-schema validation adapter over the public engine contract."""

from __future__ import annotations

from typing import Any, Mapping

from engine.contracts import SchemaCatalog, validate_artifact_graph

from ..application.errors import ApplicationError, ApplicationIssue


_SCHEMA_MESSAGES = {
    "SCHEMA_ADDITIONAL_PROPERTIES": "An unexpected field is not allowed.",
    "SCHEMA_CONST": "The field has an unsupported constant value.",
    "SCHEMA_ENUM": "The field has an unsupported value.",
    "SCHEMA_FORMAT": "The field has an invalid format.",
    "SCHEMA_MINIMUM": "The field is below its minimum value.",
    "SCHEMA_MIN_ITEMS": "The collection has too few items.",
    "SCHEMA_ONE_OF": "The field does not match exactly one allowed shape.",
    "SCHEMA_PATTERN": "The field does not match the required format.",
    "SCHEMA_REQUIRED": "A required field is missing.",
    "SCHEMA_TYPE": "The field has an invalid type.",
    "SCHEMA_UNIQUE_ITEMS": "The collection contains duplicate items.",
}


class EngineContractValidationAdapter:
    def __init__(self, catalog: SchemaCatalog):
        self.catalog = catalog

    def validate_project(self, value: Mapping[str, Any]) -> None:
        self._validate(value, "project.schema.json")

    def validate_profile(self, value: Mapping[str, Any]) -> None:
        self._validate(value, "domain_profile.schema.json")

    def validate_policy_snapshot(self, value: Mapping[str, Any]) -> None:
        self._validate(value, "domain_policy_snapshot.schema.json")

    def validate_artifacts(
        self,
        values: tuple[Mapping[str, Any], ...],
        *,
        project_id: str,
    ) -> None:
        issues = []
        for value in values:
            issues.extend(
                self.catalog.validate(
                    value,
                    "artifact.schema.json",
                    "<api-artifact>",
                ).issues
            )
        if not issues:
            issues.extend(
                validate_artifact_graph(
                    values,
                    catalog=self.catalog,
                    source_file="<api-artifacts>",
                    project_ids={project_id},
                ).issues
            )
        if issues:
            self._raise_contract_error(tuple(issues))

    def _validate(self, value: Mapping[str, Any], schema_name: str) -> None:
        result = self.catalog.validate(value, schema_name, "<api-contract>")
        if not result.is_valid:
            self._raise_contract_error(result.issues)

    @staticmethod
    def _raise_contract_error(issues: tuple[Any, ...]) -> None:
        message = "The generated data failed canonical contract validation."
        safe_issues = tuple(
            ApplicationIssue(
                issue.code,
                issue.json_pointer,
                _SCHEMA_MESSAGES.get(
                    issue.code,
                    "The generated data violates a canonical contract rule.",
                ),
            )
            for issue in issues
        )
        raise ApplicationError(
            "CONTRACT_VALIDATION_FAILED",
            message,
            safe_issues,
        )
