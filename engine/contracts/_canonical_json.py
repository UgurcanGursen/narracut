"""Internal canonical JSON byte encoding shared by Phase 2 contracts."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def encode_canonical_json_bytes(value: Any) -> bytes:
    """Encode a validated JSON value with exact canonical separators."""
    return _encode_value(value).encode("utf-8")


def _encode_value(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return _encode_string(value)
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(_encode_value(item) for item in value) + "]"
    if isinstance(value, Mapping):
        return (
            "{"
            + ",".join(
                f"{_encode_string(key)}:{_encode_value(value[key])}"
                for key in sorted(value)
            )
            + "}"
        )
    raise TypeError(f"Unsupported canonical JSON value: {type(value).__name__}")


def _encode_string(value: str) -> str:
    encoded = ['"']
    for character in value:
        codepoint = ord(character)
        if character == '"':
            encoded.append('\\"')
        elif character == "\\":
            encoded.append("\\\\")
        elif codepoint <= 0x1F:
            encoded.append(f"\\u{codepoint:04x}")
        else:
            encoded.append(character)
    encoded.append('"')
    return "".join(encoded)
