"""Path safety helpers shared by workspace and domain-pack loaders."""

from __future__ import annotations

from pathlib import Path, PurePath


def resolve_relative(root: Path, raw_path: str) -> Path:
    candidate = PurePath(raw_path)
    if candidate.is_absolute() or candidate.drive:
        raise ValueError(f"Absolute paths are forbidden: {raw_path}")
    if ".." in candidate.parts:
        raise ValueError(f"Parent traversal is forbidden: {raw_path}")

    resolved_root = root.resolve()
    resolved = (resolved_root / Path(raw_path)).resolve()
    if not resolved.is_relative_to(resolved_root):
        raise ValueError(f"Path escapes configured root: {raw_path}")
    return resolved
