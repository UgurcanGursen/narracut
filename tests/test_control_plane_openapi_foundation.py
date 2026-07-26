from __future__ import annotations

import hashlib
import json
import os
import re
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI


REPO_ROOT = Path(__file__).resolve().parents[1]
STUDIO_API_SRC = REPO_ROOT / "studio-api" / "src"
OPENAPI_PATH = REPO_ROOT / "shared-schemas" / "openapi" / "openapi.json"
PACKAGE_ROOT = STUDIO_API_SRC / "kurgu_studio_api"

sys.path.insert(0, str(STUDIO_API_SRC))

from kurgu_studio_api import create_app  # noqa: E402
from kurgu_studio_api.app import (  # noqa: E402
    APPLICATION_DESCRIPTION,
    APPLICATION_TITLE,
    APPLICATION_VERSION,
    OPENAPI_VERSION,
)
from kurgu_studio_api.openapi_export import _render_openapi_bytes  # noqa: E402


def _environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    inherited = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = os.pathsep.join(
        value
        for value in (str(STUDIO_API_SRC), inherited)
        if value
    )
    return environment


def _snapshot(paths: tuple[Path, ...]) -> dict[str, str]:
    return {
        str(path.relative_to(REPO_ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for root in paths
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _walk_keys(value: Any):
    if isinstance(value, dict):
        for key, nested in value.items():
            yield key
            yield from _walk_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_keys(nested)


def test_create_app_returns_fresh_routes_free_fastapi_instances() -> None:
    first = create_app()
    second = create_app()
    assert isinstance(first, FastAPI)
    assert isinstance(second, FastAPI)
    assert first is not second
    assert first.routes == []
    assert second.routes == []
    assert first.openapi_url is None


def test_application_metadata_and_openapi_are_deterministic() -> None:
    first = create_app()
    second = create_app()
    assert first.title == APPLICATION_TITLE
    assert first.version == APPLICATION_VERSION
    assert first.description == APPLICATION_DESCRIPTION
    assert first.openapi_version == OPENAPI_VERSION
    assert first.openapi_version.startswith("3.1.")
    assert first.openapi() == second.openapi()
    assert _render_openapi_bytes() == _render_openapi_bytes()


def test_committed_openapi_matches_runtime_and_contains_no_fake_endpoints() -> None:
    committed = OPENAPI_PATH.read_bytes()
    runtime = _render_openapi_bytes()
    document = json.loads(committed.decode("utf-8"))
    assert committed == runtime
    assert document["openapi"].startswith("3.1.")
    assert document["info"] == {
        "description": APPLICATION_DESCRIPTION,
        "title": APPLICATION_TITLE,
        "version": APPLICATION_VERSION,
    }
    assert document["paths"] == {}
    assert "servers" not in document
    lowered = committed.lower()
    for forbidden in (b"/health", b"/project", b"/artifacts", b"localhost"):
        assert forbidden not in lowered


def test_openapi_bytes_are_utf8_lf_and_machine_independent() -> None:
    content = OPENAPI_PATH.read_bytes()
    content.decode("utf-8")
    assert not content.startswith(b"\xef\xbb\xbf")
    assert b"\r\n" not in content
    assert content.endswith(b"\n")
    assert not re.search(rb"(?<![A-Za-z0-9])[A-Za-z]:[\\/]", content)
    assert str(REPO_ROOT).encode("utf-8") not in content
    assert Path.cwd().as_posix().encode("utf-8") not in content
    assert socket.gethostname().encode("utf-8") not in content
    assert not re.search(rb"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", content)
    assert set(_walk_keys(json.loads(content))).isdisjoint(
        {"generated_at", "timestamp", "hostname", "cwd"}
    )


def test_real_openapi_check_command_passes() -> None:
    result = subprocess.run(
        [sys.executable, "-B", "-m", "kurgu_studio_api.openapi_export", "--check"],
        cwd=REPO_ROOT,
        env=_environment(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "PASS"
    assert payload["mode"] == "check"
    assert payload["sha256"] == hashlib.sha256(OPENAPI_PATH.read_bytes()).hexdigest()


def test_package_import_does_not_mutate_repository_files() -> None:
    roots = (PACKAGE_ROOT, REPO_ROOT / "shared-schemas")
    before = _snapshot(roots)
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            "-c",
            "from kurgu_studio_api import create_app; create_app().openapi()",
        ],
        cwd=REPO_ROOT,
        env=_environment(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert _snapshot(roots) == before


def test_exporter_rejects_arbitrary_output_and_import_targets(tmp_path: Path) -> None:
    output = tmp_path / "not-allowed.json"
    for arguments in (
        ("--output", str(output)),
        ("--app", "untrusted.module:app"),
    ):
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "kurgu_studio_api.openapi_export",
                *arguments,
            ],
            cwd=REPO_ROOT,
            env=_environment(),
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode != 0
    assert not output.exists()
