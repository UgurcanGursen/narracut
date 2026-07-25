"""Fail-closed inspection for credentials in V2 migration source values."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qsl, unquote_plus, urlsplit


_SENSITIVE_KEYS = frozenset(
    {
        "token",
        "accesstoken",
        "refreshtoken",
        "idtoken",
        "auth",
        "authorization",
        "apikey",
        "clientsecret",
        "secret",
        "password",
        "passwd",
        "pwd",
        "credential",
        "credentials",
        "signature",
        "sig",
        "xamzsignature",
        "xamzcredential",
        "xamzsecuritytoken",
        "xgoogsignature",
        "xgoogcredential",
        "awsaccesskeyid",
        "xapikey",
        "keypairid",
        "cookie",
    }
)
_SENSITIVE_KEY_SEGMENTS = frozenset(
    {
        "token",
        "auth",
        "authorization",
        "secret",
        "password",
        "passwd",
        "pwd",
        "credential",
        "credentials",
        "signature",
        "sig",
        "cookie",
    }
)
_SECRET_VALUE = re.compile(
    r"(?i)(?:bearer\s+[a-z0-9._-]{8,}|"
    r"(?:api[_-]?key|access[_-]?token|refresh[_-]?token|id[_-]?token|"
    r"auth|authorization|client[_-]?secret|token|secret|password|passwd|pwd|"
    r"credential|credentials|signature|sig)="
    r"[^&\s]{1,}|sk-[a-z0-9_-]{8,})"
)
_USERINFO_LIKE = re.compile(
    r"(?i)(?:[a-z][a-z0-9+.-]*:)?/{1,2}[^/?#@\s]+@"
    r"|[^/?#@\s:]+:[^/?#@\s]+@"
)
_CONTROL_CHARACTER = re.compile(r"[\x00-\x1f\x7f]")


@dataclass(frozen=True)
class SensitiveValueFinding:
    """A safe classification that never retains the inspected raw value."""

    category: str
    key_name: str | None = None


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def _safe_sensitive_key(value: str) -> str | None:
    decoded = unquote_plus(value)
    normalized = _normalize_key(decoded)
    if normalized in _SENSITIVE_KEYS:
        return normalized
    segments = {
        _normalize_key(part)
        for part in re.split(r"[^a-z0-9]+", decoded.casefold())
        if part
    }
    if segments & _SENSITIVE_KEY_SEGMENTS:
        return normalized
    return None


def _query_finding(value: str) -> SensitiveValueFinding | None:
    for key, _ in parse_qsl(value, keep_blank_values=True):
        normalized = _safe_sensitive_key(key)
        if normalized is not None:
            return SensitiveValueFinding("sensitive_query_key", normalized)
    return None


def inspect_uri_reference(value: str) -> SensitiveValueFinding | None:
    """Inspect one URI/path/query candidate before any normalization or copying."""

    if _CONTROL_CHARACTER.search(value):
        return SensitiveValueFinding("control_character")
    if _SECRET_VALUE.search(value):
        return SensitiveValueFinding("credential_pattern")
    if _USERINFO_LIKE.search(value):
        return SensitiveValueFinding("uri_user_info")

    try:
        parsed = urlsplit(value)
        if parsed.username is not None or parsed.password is not None:
            return SensitiveValueFinding("uri_user_info")
    except ValueError:
        decoded = unquote_plus(value)
        if _USERINFO_LIKE.search(decoded) or _SECRET_VALUE.search(decoded):
            return SensitiveValueFinding("malformed_credential_uri")
        return None

    query_finding = _query_finding(parsed.query)
    if query_finding is not None:
        return query_finding

    fragment_finding = _query_finding(parsed.fragment.lstrip("?"))
    if fragment_finding is not None:
        return SensitiveValueFinding(
            "sensitive_fragment_key", fragment_finding.key_name
        )

    if not parsed.query and not parsed.fragment and "=" in value:
        return _query_finding(value.lstrip("?"))
    return None


def inspect_source_value(
    pointer: str,
    value: Any,
    *,
    uri_reference: bool = False,
) -> SensitiveValueFinding | None:
    """Inspect field names, generic credential patterns, and URI-like strings."""

    for part in pointer.split("/"):
        if part and _safe_sensitive_key(part) is not None:
            return SensitiveValueFinding("sensitive_field")
    if not isinstance(value, str):
        return None
    if uri_reference or "://" in value or value.startswith("//"):
        return inspect_uri_reference(value)
    if _SECRET_VALUE.search(value):
        return SensitiveValueFinding("credential_pattern")
    return None
