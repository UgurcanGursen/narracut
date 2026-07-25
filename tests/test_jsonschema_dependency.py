from importlib.metadata import version as package_version

import pytest
import jsonschema
from jsonschema import Draft202012Validator, FormatChecker, ValidationError


SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "count": {"type": "integer"},
        "started_at": {"type": "string", "format": "date-time"},
    },
    "required": ["count", "started_at"],
    "additionalProperties": False,
}

VALID_INSTANCE = {
    "count": 1,
    "started_at": "2026-07-25T12:34:56Z",
}

INVALID_TYPE_INSTANCE = {
    "count": "1",
    "started_at": "2026-07-25T12:34:56Z",
}

INVALID_FORMAT_INSTANCE = {
    "count": 1,
    "started_at": "not-a-date-time",
}


def test_jsonschema_draft_202012_schema_and_type_validation():
    assert package_version("jsonschema") == "4.26.0"
    assert jsonschema.__name__ == "jsonschema"

    Draft202012Validator.check_schema(SCHEMA)
    validator = Draft202012Validator(SCHEMA)

    validator.validate(VALID_INSTANCE)

    with pytest.raises(ValidationError):
        validator.validate(INVALID_TYPE_INSTANCE)


def test_jsonschema_format_checker_rejects_invalid_datetime():
    validator = Draft202012Validator(
        SCHEMA,
        format_checker=FormatChecker(),
    )

    with pytest.raises(ValidationError):
        validator.validate(INVALID_FORMAT_INSTANCE)
