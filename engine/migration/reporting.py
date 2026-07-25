"""Deterministic human-readable views of canonical migration results."""

from __future__ import annotations

from typing import Any, Mapping

from .models import CLASSIFICATIONS, MigrationOutcome


def render_migration_report(outcome: MigrationOutcome) -> str:
    result = outcome.result
    counts = result["counts"]["classifications"]
    lines = [
        "# V2 to V3 Migration Report",
        "",
        "## Summary",
        "",
        f"- Source: `{result['source_path']}`",
        f"- Source format/version: `{result['source_format']}` / "
        f"`{result['source_schema_version']}`",
        f"- Target format/version: `{result['target_format']}` / "
        f"`{result['target_schema_version']}`",
        f"- Mode: `{result['mode']}`",
        f"- Resolution mode: `{result['resolution_mode']}`",
        f"- Status: **{result['status']}**",
        f"- Source fingerprint: `{result['source_fingerprint']}`",
        f"- Target fingerprint: `{result['target_fingerprint']}`",
        f"- Workspace ID: `{result['workspace_id']}`",
        "",
        "## Classification counts",
        "",
        "| Classification | Count |",
        "|---|---:|",
    ]
    lines.extend(f"| {name} | {counts[name]} |" for name in CLASSIFICATIONS)
    lines.extend(
        [
            "",
            "## Losses and issues",
            "",
        ]
    )
    if result["issues"]:
        for issue in result["issues"]:
            destination = issue["destination_pointer"] or "(none)"
            lines.extend(
                [
                    f"### {issue['code']} — {issue['severity']}",
                    "",
                    f"- Issue ID: `{issue['issue_id']}`",
                    f"- Source: `{issue['source_pointer'] or '/'}`",
                    f"- Destination: `{destination}`",
                    f"- Classification: `{issue['classification']}`",
                    f"- Message: {issue['message']}",
                    f"- Resolution: {issue['action']}",
                    "",
                ]
            )
    else:
        lines.append("No migration loss or issue was recorded.")
        lines.append("")

    lines.extend(
        [
            "## Source to destination mapping",
            "",
            "| Source | Destination | Classification | Transformation |",
            "|---|---|---|---|",
        ]
    )
    for mapping in result["mappings"]:
        source = mapping["source_pointer"] or "/"
        destination = mapping["destination_pointer"] or "(report only)"
        transformation = mapping["transformation"].replace("|", "\\|")
        lines.append(
            f"| `{source}` | `{destination}` | "
            f"{mapping['classification']} | {transformation} |"
        )
    lines.extend(
        [
            "",
            "## Manual review",
            "",
        ]
    )
    review_items = [
        issue
        for issue in result["issues"]
        if issue["severity"] in {"WARNING", "ERROR"}
    ]
    if review_items:
        lines.extend(
            f"- `{item['issue_id']}`: {item['action']}"
            for item in review_items
        )
    else:
        lines.append("- No manual review required.")
    lines.extend(
        [
            "",
            "## Validation",
            "",
            f"- Workspace schema: "
            f"`{result['validation']['workspace_schema_valid']}`",
            f"- Workspace loader: "
            f"`{result['validation']['workspace_loader_valid']}`",
            f"- Migration result schema: "
            f"`{result['validation']['migration_result_schema_valid']}`",
            "",
        ]
    )
    return "\n".join(lines)

def workspace_counts(workspace: Mapping[str, Any] | None) -> dict[str, int]:
    if workspace is None:
        return {
            "chapters": 0,
            "beats": 0,
            "sequences": 0,
            "assets": 0,
            "artifacts": 0,
            "tracks": 0,
            "events": 0,
        }
    sequences = workspace["sequences"]
    return {
        "chapters": len(workspace["story"]["chapters"]),
        "beats": len(workspace["story"]["beats"]),
        "sequences": len(sequences),
        "assets": len(workspace["assets"]),
        "artifacts": len(workspace["artifacts"]),
        "tracks": len(workspace["tracks"]["tracks"]),
        "events": sum(
            len(sequence[group])
            for sequence in sequences
            for group in (
                "edit_events",
                "overlay_events",
                "text_emphasis_events",
                "audio_events",
            )
        ),
    }


def render_inspection_summary(outcome: MigrationOutcome) -> str:
    result = outcome.result
    counts = workspace_counts(outcome.workspace)
    severity = result["counts"]["severities"]
    output_files = [
        "migration_result.json",
        "migration_report.md",
        "inspection_summary.txt",
    ]
    if outcome.workspace is not None:
        output_files.insert(0, "workspace.json")
    lines = [
        f"input: {result['source_path']}",
        f"source_fingerprint: {result['source_fingerprint']}",
        f"status: {result['status']}",
        f"target_workspace_id: {result['workspace_id']}",
        "counts: "
        + ", ".join(f"{name}={value}" for name, value in counts.items()),
        f"warnings: {severity['WARNING']}",
        f"errors: {severity['ERROR']}",
        "output_files: " + ", ".join(output_files),
        "manual_review_required: "
        + ("yes" if severity["WARNING"] or severity["ERROR"] else "no"),
        "",
    ]
    return "\n".join(lines)
