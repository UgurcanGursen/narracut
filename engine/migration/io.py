"""Safe deterministic file IO for migration artifacts."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping

from engine.contracts import SchemaCatalog, WorkspaceLoader

from .models import MigrationOptions, MigrationOutcome
from .reporting import render_inspection_summary, render_migration_report
from .v2_to_v3 import V2ToV3Migrator


class MigrationIOError(RuntimeError):
    pass


def deterministic_json(value: Any) -> str:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n"
    )


def read_source(path: Path | str) -> Mapping[str, Any]:
    source = Path(path)
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MigrationIOError(f"Unable to read V2 JSON: {exc}") from exc
    if not isinstance(value, Mapping):
        raise MigrationIOError("V2 JSON root must be an object.")
    return value


def _safe_output_path(path: Path | str) -> Path:
    raw = os.fspath(path)
    normalized = raw.replace("\\", "/")
    if ".." in normalized.split("/"):
        raise MigrationIOError("Output path traversal is not allowed.")
    target = Path(path).resolve()
    if target == target.parent:
        raise MigrationIOError("Filesystem root cannot be an output directory.")
    return target


def _atomic_write(path: Path, content: str) -> None:
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="\n",
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        delete=False,
    )
    temporary = Path(handle.name)
    try:
        with handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def write_outcome(
    outcome: MigrationOutcome,
    output_directory: Path | str,
    *,
    catalog: SchemaCatalog,
    options: MigrationOptions,
    overwrite: bool = False,
) -> tuple[Path, ...]:
    output = _safe_output_path(output_directory)
    if output.exists() and not output.is_dir():
        raise MigrationIOError("Output target exists and is not a directory.")
    if output.exists() and any(output.iterdir()) and not overwrite:
        raise MigrationIOError(
            "Output directory is not empty; use explicit overwrite."
        )
    output.mkdir(parents=True, exist_ok=True)

    workspace_path = output / "workspace.json"
    result_path = output / "migration_result.json"
    report_path = output / "migration_report.md"
    summary_path = output / "inspection_summary.txt"

    if outcome.workspace is not None:
        candidate = output / ".workspace.validation.json"
        try:
            candidate.write_text(
                deterministic_json(outcome.workspace),
                encoding="utf-8",
                newline="\n",
            )
            loader = WorkspaceLoader(
                catalog,
                registry=options.registry
                if options.resolution_mode == "domain_pack"
                else None,
            )
            loaded = loader.load(candidate)
            if not loaded.validation.is_valid:
                details = "; ".join(
                    f"{item.code} {item.json_pointer}: {item.message}"
                    for item in loaded.validation.issues
                )
                raise MigrationIOError(
                    f"Public WorkspaceLoader rejected output: {details}"
                )
        finally:
            candidate.unlink(missing_ok=True)

    payloads: list[tuple[Path, str]] = [
        (result_path, deterministic_json(outcome.result)),
        (report_path, render_migration_report(outcome)),
        (summary_path, render_inspection_summary(outcome)),
    ]
    if outcome.workspace is not None:
        payloads.insert(
            0, (workspace_path, deterministic_json(outcome.workspace))
        )
    elif workspace_path.exists():
        workspace_path.unlink()

    written: list[Path] = []
    try:
        for path, content in payloads:
            _atomic_write(path, content)
            written.append(path)
    except BaseException as exc:
        if outcome.workspace is not None:
            workspace_path.unlink(missing_ok=True)
        raise MigrationIOError(f"Unable to write migration output: {exc}") from exc
    return tuple(written)


def migrate_file(
    input_path: Path | str,
    output_directory: Path | str,
    *,
    catalog: SchemaCatalog,
    options: MigrationOptions | None = None,
    overwrite: bool = False,
) -> MigrationOutcome:
    source_path = Path(input_path)
    source = read_source(source_path)
    resolved_options = options or MigrationOptions()
    resolved_options = replace(
        resolved_options,
        source_path=source_path.name,
        target_path="workspace.json",
    )
    outcome = V2ToV3Migrator(catalog).migrate(source, resolved_options)
    write_outcome(
        outcome,
        output_directory,
        catalog=catalog,
        options=resolved_options,
        overwrite=overwrite,
    )
    return outcome
