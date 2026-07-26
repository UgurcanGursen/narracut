from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[1]
CANONICAL_ROOT = REPO_ROOT / "schema" / "v3"
DISTRIBUTION_ROOT = REPO_ROOT / "shared-schemas" / "v3"
MANIFEST_PATH = REPO_ROOT / "shared-schemas" / "manifest.json"
ATOMIC_TEMP_ROOT = Path("C:/tmp")


class DistributionError(RuntimeError):
    """A sanitized, deterministic schema distribution failure."""


@dataclass(frozen=True)
class SchemaEntry:
    name: str
    canonical_path: str
    distribution_path: str
    sha256: str
    schema_id: str
    content: bytes

    def manifest_value(self) -> dict[str, Any]:
        return {
            "canonical_path": self.canonical_path,
            "distribution_path": self.distribution_path,
            "name": self.name,
            "schema_id": self.schema_id,
            "sha256": self.sha256,
        }


def _canonical_inventory(canonical_root: Path) -> tuple[SchemaEntry, ...]:
    if not canonical_root.is_dir() or canonical_root.is_symlink():
        raise DistributionError("Canonical schema root is unavailable.")

    directory_entries = sorted(canonical_root.iterdir(), key=lambda item: item.name)
    unexpected = [
        item.name
        for item in directory_entries
        if item.is_symlink()
        or not item.is_file()
        or not item.name.endswith(".schema.json")
    ]
    if unexpected:
        raise DistributionError(
            "Canonical schema root contains unsupported entries: "
            + ", ".join(unexpected)
        )

    paths = directory_entries
    if not paths:
        raise DistributionError("Canonical schema inventory is empty.")

    casefolded: set[str] = set()
    schema_ids: set[str] = set()
    inventory: list[SchemaEntry] = []
    for path in paths:
        folded = path.name.casefold()
        if folded in casefolded:
            raise DistributionError(
                f"Duplicate canonical schema filename: {path.name}"
            )
        casefolded.add(folded)

        content = path.read_bytes()
        try:
            value = json.loads(content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise DistributionError(
                f"Invalid canonical schema JSON: {path.name}"
            ) from exc
        if not isinstance(value, dict):
            raise DistributionError(
                f"Canonical schema root must be an object: {path.name}"
            )
        schema_id = value.get("$id")
        if not isinstance(schema_id, str) or not schema_id:
            raise DistributionError(
                f"Canonical schema has no stable $id: {path.name}"
            )
        if schema_id in schema_ids:
            raise DistributionError(f"Duplicate canonical schema $id: {schema_id}")
        schema_ids.add(schema_id)
        inventory.append(
            SchemaEntry(
                name=path.name,
                canonical_path=f"schema/v3/{path.name}",
                distribution_path=f"shared-schemas/v3/{path.name}",
                sha256=hashlib.sha256(content).hexdigest(),
                schema_id=schema_id,
                content=content,
            )
        )
    return tuple(inventory)


def _manifest_bytes(inventory: Sequence[SchemaEntry]) -> bytes:
    value = {
        "canonical_source": "schema/v3",
        "distribution_root": "shared-schemas/v3",
        "format_version": 1,
        "schema_count": len(inventory),
        "schemas": [entry.manifest_value() for entry in inventory],
    }
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _atomic_write(path: Path, content: bytes) -> None:
    if path.exists() and path.is_symlink():
        raise DistributionError(f"Generated output cannot be a symlink: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    ATOMIC_TEMP_ROOT.mkdir(parents=True, exist_ok=True)
    descriptor, raw_temp_path = tempfile.mkstemp(
        prefix="kurgu-shared-schema-",
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


def _distribution_drift(
    inventory: Sequence[SchemaEntry],
    distribution_root: Path,
    manifest_path: Path,
    *,
    allow_missing: bool,
) -> tuple[str, ...]:
    expected_names = {entry.name for entry in inventory}
    if distribution_root.exists():
        if not distribution_root.is_dir() or distribution_root.is_symlink():
            return ("Generated schema root must be a real directory.",)
        actual_entries = sorted(
            distribution_root.iterdir(), key=lambda item: item.name
        )
    else:
        actual_entries = []

    actual_names = {item.name for item in actual_entries}
    invalid_entries = [
        item.name
        for item in actual_entries
        if item.is_symlink()
        or not item.is_file()
        or not item.name.endswith(".schema.json")
    ]
    extra = sorted(actual_names - expected_names)
    missing = sorted(expected_names - actual_names)
    issues: list[str] = []
    if invalid_entries:
        issues.append(
            "unsupported generated entries: " + ", ".join(invalid_entries)
        )
    if extra:
        issues.append("extra generated schemas: " + ", ".join(extra))
    if missing and not allow_missing:
        issues.append("missing generated schemas: " + ", ".join(missing))

    for entry in inventory:
        output = distribution_root / entry.name
        if output.is_file() and not output.is_symlink():
            if output.read_bytes() != entry.content:
                issues.append(f"modified generated schema: {entry.name}")

    if not allow_missing:
        if not manifest_path.is_file() or manifest_path.is_symlink():
            issues.append("generated manifest is missing or unsafe")
        elif manifest_path.read_bytes() != _manifest_bytes(inventory):
            issues.append("generated manifest drift")
    return tuple(issues)


def write_distribution(
    canonical_root: Path = CANONICAL_ROOT,
    distribution_root: Path = DISTRIBUTION_ROOT,
    manifest_path: Path = MANIFEST_PATH,
) -> tuple[SchemaEntry, ...]:
    inventory = _canonical_inventory(canonical_root)
    drift = _distribution_drift(
        inventory,
        distribution_root,
        manifest_path,
        allow_missing=True,
    )
    stale = tuple(
        issue
        for issue in drift
        if issue.startswith("unsupported") or issue.startswith("extra")
    )
    if stale:
        raise DistributionError("; ".join(stale))

    for entry in inventory:
        _atomic_write(distribution_root / entry.name, entry.content)
    _atomic_write(manifest_path, _manifest_bytes(inventory))
    return inventory


def check_distribution(
    canonical_root: Path = CANONICAL_ROOT,
    distribution_root: Path = DISTRIBUTION_ROOT,
    manifest_path: Path = MANIFEST_PATH,
) -> tuple[SchemaEntry, ...]:
    inventory = _canonical_inventory(canonical_root)
    drift = _distribution_drift(
        inventory,
        distribution_root,
        manifest_path,
        allow_missing=False,
    )
    if drift:
        raise DistributionError("; ".join(drift))
    return inventory


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Write or check the deterministic shared V3 schema distribution."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        inventory = write_distribution() if args.write else check_distribution()
    except DistributionError as exc:
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
                {"error": "Schema distribution filesystem operation failed.", "status": "FAIL"},
                sort_keys=True,
            )
        )
        return 1
    print(
        json.dumps(
            {
                "mode": "write" if args.write else "check",
                "schema_count": len(inventory),
                "status": "PASS",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
