"""Bounded Phase 5 REPLAY runner for a verified template-render envelope."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from subprocess import PIPE, TimeoutExpired, run
from tempfile import TemporaryDirectory

from .template_contract import TemplateRenderInputV1, serialize_template_render_input


class TemplateRunnerError(RuntimeError):
    """The Node REPLAY adapter did not produce a canonical terminal result."""


@dataclass(frozen=True)
class TemplatePreviewResult:
    manifest_id: str
    manifest_hash: str
    manifest_path: Path


def _env() -> dict[str, str]:
    value = {"PATH": os.environ.get("PATH", ""), "TZ": "UTC", "LANG": "C", "NODE_ENV": "production"}
    if os.name == "nt":
        value |= {"SystemRoot": os.environ.get("SystemRoot", ""), "COMSPEC": os.environ.get("COMSPEC", "")}
    return value


def run_template_replay(
    *,
    input_value: TemplateRenderInputV1,
    output_root: Path,
    fixture_root: Path,
    work_root: Path,
    renderer_root: Path,
    node_executable: str = "node",
    timeout_seconds: int = 180,
) -> TemplatePreviewResult:
    """Render exactly one verified input through the additive Phase 5 runner.

    The function neither changes a Phase 4 request nor owns artifact lifecycle;
    it only materializes the immutable envelope into a private temporary file.
    """
    if not all(isinstance(value, Path) for value in (output_root, fixture_root, work_root, renderer_root)):
        raise TypeError("all roots must be Path")
    if type(node_executable) is not str or not node_executable or type(timeout_seconds) is not int or timeout_seconds <= 0:
        raise TypeError("invalid runner argument")
    if output_root.exists() or not fixture_root.is_dir() or not work_root.is_dir() or not renderer_root.is_dir():
        raise TemplateRunnerError("TEMPLATE_RENDER_ROOT_INVALID")
    script = renderer_root / "scripts" / "render-template-fixture.mjs"
    if not script.is_file():
        raise TemplateRunnerError("TEMPLATE_RENDERER_UNAVAILABLE")
    payload = serialize_template_render_input(input_value)
    with TemporaryDirectory(prefix="phase5-input-", dir=work_root) as temporary:
        input_path = Path(temporary) / "template-input.json"
        input_path.write_bytes(payload)
        try:
            completed = run(
                [node_executable, str(script), "--input", str(input_path), "--output", str(output_root),
                 "--fixture-root", str(fixture_root), "--work-root", str(work_root)],
                cwd=renderer_root, env=_env(), stdin=PIPE, stdout=PIPE, stderr=PIPE,
                timeout=timeout_seconds, check=False,
            )
        except (OSError, TimeoutExpired) as exc:
            raise TemplateRunnerError("TEMPLATE_RENDER_TIMEOUT") from exc
    if completed.returncode != 0:
        code = completed.stderr.decode("utf-8", errors="replace").split("\n", 1)[0]
        raise TemplateRunnerError(code or "TEMPLATE_RENDER_EXIT_NONZERO")
    try:
        result = json.loads(completed.stdout.decode("utf-8"))
        if set(result) != {"status", "manifest_path", "manifest_id", "manifest_hash"} or result["status"] != "SUCCEEDED":
            raise ValueError("shape")
        relative = Path(result["manifest_path"])
        target = (output_root / relative).resolve()
        if output_root.resolve() not in target.parents or not target.is_file():
            raise ValueError("path")
        if not all(type(result[key]) is str and result[key] for key in ("manifest_id", "manifest_hash")):
            raise ValueError("identity")
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise TemplateRunnerError("TEMPLATE_RENDER_RECEIPT_INVALID") from exc
    return TemplatePreviewResult(result["manifest_id"], result["manifest_hash"], target)
