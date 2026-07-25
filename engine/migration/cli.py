"""Thin command-line interface for deterministic V2 to V3 migration."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from engine.contracts import DomainPackError, DomainPackRegistry, SchemaCatalog

from .io import MigrationIOError, migrate_file
from .models import MigrationOptions


EXIT_SUCCESS = 0
EXIT_STRICT_REJECTED = 2
EXIT_FAILED = 3
EXIT_USAGE = 4


class MigrationArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(EXIT_USAGE, f"configuration error: {message}\n")


def build_parser() -> argparse.ArgumentParser:
    parser = MigrationArgumentParser(
        prog="python -B -m engine.migration.cli",
        description="Migrate a Kurgu V2 timeline to canonical V3 artifacts.",
        epilog=(
            "Example:\n"
            "  python -B -m engine.migration.cli migrate "
            "--input samples/migration/v2-to-v3/input_v2.json "
            "--output migrated-output --mode permissive "
            "--resolution-mode core_only"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    migrate_parser = subparsers.add_parser(
        "migrate", help="migrate one V2 timeline JSON file"
    )
    migrate_parser.add_argument("--input", required=True)
    migrate_parser.add_argument("--output", required=True)
    migrate_parser.add_argument(
        "--mode", choices=("strict", "permissive"), required=True
    )
    migrate_parser.add_argument(
        "--resolution-mode",
        choices=("core_only", "domain_pack"),
        required=True,
    )
    migrate_parser.add_argument(
        "--domain-pack-root",
        action="append",
        default=[],
        help="domain pack root; repeatable and required for domain_pack",
    )
    migrate_parser.add_argument("--domain-id")
    migrate_parser.add_argument("--domain-pack-version")
    migrate_parser.add_argument("--profile")
    migrate_parser.add_argument("--overwrite", action="store_true")
    return parser


def _domain_options(
    args: argparse.Namespace,
    catalog: SchemaCatalog,
) -> tuple[DomainPackRegistry | None, dict | None]:
    if args.resolution_mode == "core_only":
        if any(
            (
                args.domain_pack_root,
                args.domain_id,
                args.domain_pack_version,
                args.profile,
            )
        ):
            raise MigrationIOError(
                "Domain-pack options are not accepted in core_only mode."
            )
        return None, None
    if not all(
        (
            args.domain_pack_root,
            args.domain_id,
            args.domain_pack_version,
            args.profile,
        )
    ):
        raise MigrationIOError(
            "domain_pack mode requires --domain-pack-root, --domain-id, "
            "--domain-pack-version, and --profile."
        )
    registry = DomainPackRegistry(args.domain_pack_root, catalog)
    registry.discover()
    try:
        profile = json.loads(Path(args.profile).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MigrationIOError(f"Unable to read domain profile: {exc}") from exc
    if not isinstance(profile, dict):
        raise MigrationIOError("Domain profile root must be an object.")
    return registry, profile


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    repo_root = Path(__file__).resolve().parents[2]
    catalog = SchemaCatalog(repo_root / "schema" / "v3")
    try:
        registry, profile = _domain_options(args, catalog)
        options = MigrationOptions(
            mode=args.mode,
            resolution_mode=args.resolution_mode,
            registry=registry,
            domain_id=args.domain_id,
            domain_pack_version=args.domain_pack_version,
            profile=profile,
        )
        outcome = migrate_file(
            args.input,
            args.output,
            catalog=catalog,
            options=options,
            overwrite=args.overwrite,
        )
    except (MigrationIOError, DomainPackError, ValueError) as exc:
        print(f"migration configuration error: {exc}", file=sys.stderr)
        return EXIT_USAGE

    report = Path(args.output).resolve() / "migration_report.md"
    print(f"status: {outcome.status}")
    print(f"report: {report}")
    if outcome.status in {"SUCCESS", "SUCCESS_WITH_LOSS"}:
        return EXIT_SUCCESS
    error_count = outcome.result["counts"]["severities"]["ERROR"]
    if args.mode == "strict" and error_count == 0:
        return EXIT_STRICT_REJECTED
    return EXIT_FAILED


if __name__ == "__main__":
    raise SystemExit(main())
