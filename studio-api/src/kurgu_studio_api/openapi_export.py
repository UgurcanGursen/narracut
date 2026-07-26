"""Deterministic OpenAPI exporter for the thin Studio API."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from .app import create_app


MODULE_PATH = Path(__file__).resolve()
REPO_ROOT = MODULE_PATH.parents[3]
OPENAPI_PATH = REPO_ROOT / "shared-schemas" / "openapi" / "openapi.json"
ATOMIC_TEMP_ROOT = Path("C:/tmp")


class OpenAPIExportError(RuntimeError):
    """A sanitized deterministic OpenAPI export failure."""


def _render_openapi_bytes() -> bytes:
    document: Mapping[str, Any] = create_app().openapi()
    return (
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _atomic_write(path: Path, content: bytes) -> None:
    if path.exists() and path.is_symlink():
        raise OpenAPIExportError("OpenAPI output cannot be a symlink.")
    path.parent.mkdir(parents=True, exist_ok=True)
    ATOMIC_TEMP_ROOT.mkdir(parents=True, exist_ok=True)
    descriptor, raw_temp_path = tempfile.mkstemp(
        prefix="kurgu-openapi-",
        suffix=".tmp",
        dir=ATOMIC_TEMP_ROOT,
    )
    temp_path = Path(raw_temp_path)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def write_openapi() -> tuple[int, str]:
    content = _render_openapi_bytes()
    _atomic_write(OPENAPI_PATH, content)
    return len(content), hashlib.sha256(content).hexdigest()


def check_openapi() -> tuple[int, str]:
    expected = _render_openapi_bytes()
    try:
        actual = OPENAPI_PATH.read_bytes()
    except OSError as exc:
        raise OpenAPIExportError("Committed OpenAPI artifact is unavailable.") from exc
    if actual != expected:
        raise OpenAPIExportError("Committed OpenAPI artifact has drifted.")
    return len(expected), hashlib.sha256(expected).hexdigest()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Write or check the deterministic Kurgu Studio API OpenAPI artifact."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        size, digest = write_openapi() if args.write else check_openapi()
    except OpenAPIExportError as exc:
        print(
            json.dumps(
                {"error": str(exc), "status": "FAIL"},
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 1
    except OSError:
        print(
            json.dumps(
                {"error": "OpenAPI filesystem operation failed.", "status": "FAIL"},
                sort_keys=True,
            )
        )
        return 1
    print(
        json.dumps(
            {
                "bytes": size,
                "mode": "write" if args.write else "check",
                "sha256": digest,
                "status": "PASS",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
