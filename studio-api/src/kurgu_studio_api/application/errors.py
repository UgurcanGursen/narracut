"""Sanitized application failures independent of HTTP."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApplicationIssue:
    code: str
    json_pointer: str
    message: str


class ApplicationError(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        issues: tuple[ApplicationIssue, ...] = (),
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.issues = issues or (ApplicationIssue(code, "", message),)
