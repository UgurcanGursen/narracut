"""Aggregate/split workspace loading with root confinement and invariants."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .artifacts import validate_artifact_graph
from .domain import (
    DomainPackError,
    DomainPackRegistry,
    DomainPolicyResolver,
    canonical_json,
    policy_snapshot_hash,
)
from .models import Workspace
from .paths import resolve_relative
from .validation import SchemaCatalog, ValidationIssue, ValidationResult


_DOCUMENT_SCHEMAS = {
    "project": "project.schema.json",
    "domain_profile": "domain_profile.schema.json",
    "domain_policy_snapshot": "domain_policy_snapshot.schema.json",
    "chapter": "chapter.schema.json",
    "beat": "beat.schema.json",
    "sequence": "sequence.schema.json",
    "asset_manifest": "manifests.schema.json",
    "artifact_manifest": "manifests.schema.json",
    "research_manifest": "manifests.schema.json",
    "timing_manifest": "manifests.schema.json",
    "track_manifest": "tracks.schema.json",
}
_SPLIT_REQUIRED_KINDS = frozenset(_DOCUMENT_SCHEMAS)
_MANIFEST_KIND_TYPES = {
    "asset_manifest": "asset_manifest",
    "artifact_manifest": "artifact_manifest",
    "research_manifest": "research_manifest",
    "timing_manifest": "timing_manifest",
}
_CORE_TARGET_TYPES = frozenset(
    {
        "asset",
        "video_track",
        "audio_track",
        "overlay_track",
        "sequence",
        "base_shot",
        "claim",
    }
)
_EVENT_TARGET_COMPATIBILITY = {
    "edit_events": frozenset({"asset", "video_track", "base_shot"}),
    "overlay_events": frozenset(
        {"asset", "video_track", "overlay_track", "base_shot", "claim"}
    ),
    "text_emphasis_events": frozenset({"asset", "overlay_track", "claim"}),
    "audio_events": frozenset({"audio_track"}),
}


@dataclass(frozen=True)
class LoadedWorkspace:
    root_file: Path
    workspace: Workspace | None
    data: Mapping[str, Any] | None
    documents: Mapping[str, Mapping[str, Any]]
    validation: ValidationResult


class WorkspaceLoader:
    def __init__(
        self,
        catalog: SchemaCatalog,
        *,
        registry: DomainPackRegistry | None = None,
        resolver: DomainPolicyResolver | None = None,
    ):
        self.catalog = catalog
        self.registry = registry
        self.resolver = resolver or (
            DomainPolicyResolver(catalog) if registry is not None else None
        )

    def load(self, root_file: Path | str) -> LoadedWorkspace:
        root_path = Path(root_file).resolve()
        issues: list[ValidationIssue] = []
        try:
            root_data = json.loads(root_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            issue = ValidationIssue(
                str(root_path), "", "WORKSPACE_READ_ERROR", str(exc)
            )
            return LoadedWorkspace(
                root_path, None, None, {}, ValidationResult((issue,))
            )

        root_result = self.catalog.validate(
            root_data, "workspace.schema.json", root_path
        )
        issues.extend(root_result.issues)
        if not root_result.is_valid:
            return LoadedWorkspace(
                root_path, None, root_data, {}, ValidationResult(tuple(issues))
            )

        documents: dict[str, Mapping[str, Any]] = {}
        workspace_root = root_path.parent
        if root_data["layout"] == "split":
            seen_paths: set[Path] = set()
            seen_ids: set[str] = set()
            kinds: set[str] = set()
            for index, document_ref in enumerate(root_data["documents"]):
                raw_path = document_ref["path"]
                try:
                    document_path = resolve_relative(workspace_root, raw_path)
                except ValueError as exc:
                    issues.append(
                        ValidationIssue(
                            str(root_path),
                            f"/documents/{index}/path",
                            "WORKSPACE_PATH_TRAVERSAL",
                            str(exc),
                        )
                    )
                    continue
                if document_path in seen_paths:
                    issues.append(
                        ValidationIssue(
                            str(root_path),
                            f"/documents/{index}/path",
                            "WORKSPACE_DUPLICATE_DOCUMENT_PATH",
                            f"Duplicate document path: {raw_path}",
                        )
                    )
                    continue
                if document_ref["document_id"] in seen_ids:
                    issues.append(
                        ValidationIssue(
                            str(root_path),
                            f"/documents/{index}/document_id",
                            "WORKSPACE_DUPLICATE_DOCUMENT_ID",
                            f"Duplicate document_id: {document_ref['document_id']}",
                        )
                    )
                    continue
                seen_paths.add(document_path)
                seen_ids.add(document_ref["document_id"])
                kind = document_ref["kind"]
                kinds.add(kind)
                try:
                    value = json.loads(document_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    issues.append(
                        ValidationIssue(
                            str(document_path),
                            "",
                            "WORKSPACE_DOCUMENT_READ_ERROR",
                            str(exc),
                        )
                    )
                    continue
                manifest_issue = self._manifest_kind_issue(
                    document_ref, value, document_path
                )
                if manifest_issue is not None:
                    issues.append(manifest_issue)
                    continue
                document_result = self.catalog.validate(
                    value, _DOCUMENT_SCHEMAS[kind], document_path
                )
                issues.extend(document_result.issues)
                if document_result.is_valid:
                    documents[document_ref["document_id"]] = value

            for kind in sorted(_SPLIT_REQUIRED_KINDS - kinds):
                issues.append(
                    ValidationIssue(
                        str(root_path),
                        "/documents",
                        "WORKSPACE_MISSING_DOCUMENT_KIND",
                        f"Split workspace is missing document kind: {kind}",
                    )
                )

        snapshot_from_ref = self._load_snapshot_reference(
            root_path, root_data, issues
        )
        self._validate_consistency(
            root_path,
            root_data,
            documents,
            issues,
            snapshot_from_ref=snapshot_from_ref,
        )
        model = Workspace._from_validated_dict(root_data) if not issues else None
        return LoadedWorkspace(
            root_path,
            model,
            root_data,
            documents,
            ValidationResult(tuple(issues)),
        )

    def _validate_consistency(
        self,
        root_path: Path,
        root_data: Mapping[str, Any],
        documents: Mapping[str, Mapping[str, Any]],
        issues: list[ValidationIssue],
        *,
        snapshot_from_ref: Mapping[str, Any] | None = None,
    ) -> None:
        project: Mapping[str, Any] | None = root_data.get("project")
        profile: Mapping[str, Any] | None = root_data["domain"].get("profile")
        snapshot: Mapping[str, Any] | None = root_data["domain"].get(
            "policy_snapshot"
        )
        chapters = list(root_data.get("story", {}).get("chapters", []))
        beats = list(root_data.get("story", {}).get("beats", []))
        sequences = list(root_data.get("sequences", []))
        assets = list(root_data.get("assets", []))
        artifacts = list(root_data.get("artifacts", []))
        tracks_document: Mapping[str, Any] | None = root_data.get("tracks")

        if root_data["layout"] == "split":
            project = self._first_kind(root_data, documents, "project")
            profile = self._first_kind(root_data, documents, "domain_profile")
            snapshot = self._first_kind(
                root_data, documents, "domain_policy_snapshot"
            )
            chapters = self._all_kind(root_data, documents, "chapter")
            beats = self._all_kind(root_data, documents, "beat")
            sequences = self._all_kind(root_data, documents, "sequence")
            asset_manifest = self._first_kind(
                root_data, documents, "asset_manifest"
            )
            artifact_manifest = self._first_kind(
                root_data, documents, "artifact_manifest"
            )
            tracks_document = self._first_kind(
                root_data, documents, "track_manifest"
            )
            assets = list(asset_manifest.get("assets", [])) if asset_manifest else []
            artifacts = (
                list(artifact_manifest.get("artifacts", []))
                if artifact_manifest
                else []
            )

        domain = root_data["domain"]
        if profile is None:
            issues.append(
                ValidationIssue(
                    str(root_path),
                    "/domain/profile",
                    "DOMAIN_PROFILE_NOT_FOUND",
                    "The selected domain profile document is required.",
                )
            )
        elif profile.get("profile_id") != domain["profile_id"]:
            issues.append(
                ValidationIssue(
                    str(root_path),
                    "/domain/profile_id",
                    "DOMAIN_PROFILE_ID_MISMATCH",
                    "Workspace profile_id does not match the loaded profile.",
                )
            )

        if snapshot is None:
            issues.append(
                ValidationIssue(
                    str(root_path),
                    "/domain/policy_snapshot",
                    "POLICY_SNAPSHOT_NOT_FOUND",
                    "The selected policy snapshot document is required.",
                )
            )
        elif snapshot_from_ref is not None and canonical_json(snapshot) != canonical_json(
            snapshot_from_ref
        ):
            issues.append(
                ValidationIssue(
                    str(root_path),
                    "/domain/policy_snapshot_ref",
                    "POLICY_SNAPSHOT_RESOLUTION_MISMATCH",
                    "The policy_snapshot_ref content differs from the loaded snapshot.",
                )
            )

        if profile is not None and snapshot is not None:
            if snapshot.get("profile_id") != profile.get("profile_id"):
                issues.append(
                    ValidationIssue(
                        str(root_path),
                        "/domain/policy_snapshot/profile_id",
                        "POLICY_SNAPSHOT_PROFILE_MISMATCH",
                        "Policy snapshot profile_id does not match the selected profile.",
                    )
                )
            if snapshot.get("domain_id") != domain["domain_id"]:
                issues.append(
                    ValidationIssue(
                        str(root_path),
                        "/domain/policy_snapshot/domain_id",
                        "POLICY_SNAPSHOT_DOMAIN_MISMATCH",
                        "Policy snapshot domain_id does not match the workspace domain.",
                    )
                )
            if snapshot.get("domain_pack_version") != domain[
                "domain_pack_version"
            ]:
                issues.append(
                    ValidationIssue(
                        str(root_path),
                        "/domain/policy_snapshot/domain_pack_version",
                        "POLICY_SNAPSHOT_PACK_VERSION_MISMATCH",
                        "Policy snapshot pack version does not match the selected pack.",
                    )
                )
            self._validate_resolver_parity(root_path, domain, profile, snapshot, issues)

        expected_project_id = root_data["project_metadata"]["project_id"]
        if project is not None:
            checks = (
                (
                    project.get("project_id"),
                    expected_project_id,
                    "WORKSPACE_PROJECT_ID_MISMATCH",
                ),
                (
                    project.get("domain_id"),
                    domain["domain_id"],
                    "WORKSPACE_DOMAIN_ID_MISMATCH",
                ),
                (
                    project.get("domain_pack_version"),
                    domain["domain_pack_version"],
                    "WORKSPACE_PACK_VERSION_MISMATCH",
                ),
                (
                    project.get("policy_snapshot_id"),
                    domain["policy_snapshot_id"],
                    "WORKSPACE_SNAPSHOT_ID_MISMATCH",
                ),
            )
            for actual, expected, code in checks:
                if actual != expected:
                    issues.append(
                        ValidationIssue(
                            str(root_path),
                            "/project_metadata",
                            code,
                            f"Expected {expected!r}, got {actual!r}.",
                        )
                    )

        for value, kind in ((profile, "profile"), (snapshot, "snapshot")):
            if value is None:
                continue
            if (
                value.get("domain_id") != domain["domain_id"]
                or value.get("domain_pack_version")
                != domain["domain_pack_version"]
            ):
                issues.append(
                    ValidationIssue(
                        str(root_path),
                        "/domain",
                        "WORKSPACE_DOMAIN_RESOLUTION_MISMATCH",
                        f"Embedded {kind} does not preserve selected pack version.",
                    )
                )
        if snapshot is not None and snapshot.get("snapshot_id") != domain[
            "policy_snapshot_id"
        ]:
            issues.append(
                ValidationIssue(
                    str(root_path),
                    "/domain/policy_snapshot_id",
                    "WORKSPACE_SNAPSHOT_ID_MISMATCH",
                    "Resolved snapshot identity does not match workspace metadata.",
                )
            )
        if snapshot is not None:
            expected_hash = policy_snapshot_hash(snapshot)
            if snapshot.get("canonical_hash") != expected_hash:
                issues.append(
                    ValidationIssue(
                        str(root_path),
                        "/domain/policy_snapshot/canonical_hash",
                        "WORKSPACE_SNAPSHOT_HASH_MISMATCH",
                        "Policy snapshot canonical hash does not match its content.",
                    )
                )
            expected_snapshot_id = (
                "dps_" + expected_hash.removeprefix("sha256:")[:20]
            )
            if snapshot.get("snapshot_id") != expected_snapshot_id:
                issues.append(
                    ValidationIssue(
                        str(root_path),
                        "/domain/policy_snapshot/snapshot_id",
                        "WORKSPACE_SNAPSHOT_ID_NOT_DETERMINISTIC",
                        "Policy snapshot ID does not match the canonical hash.",
                    )
                )

        chapter_map = self._unique_index(
            root_path,
            chapters,
            "chapter_id",
            "/story/chapters",
            "DUPLICATE_CHAPTER_ID",
            issues,
        )
        beat_map = self._unique_index(
            root_path,
            beats,
            "beat_id",
            "/story/beats",
            "DUPLICATE_BEAT_ID",
            issues,
        )
        sequence_map = self._unique_index(
            root_path,
            sequences,
            "sequence_id",
            "/sequences",
            "DUPLICATE_SEQUENCE_ID",
            issues,
        )
        asset_map = self._unique_index(
            root_path,
            assets,
            "asset_id",
            "/assets",
            "DUPLICATE_ASSET_ID",
            issues,
        )
        artifact_map = self._unique_index(
            root_path,
            artifacts,
            "artifact_id",
            "/artifacts",
            "DUPLICATE_ARTIFACT_ID",
            issues,
        )
        tracks = list((tracks_document or {}).get("tracks", []))
        track_map = self._unique_index(
            root_path,
            tracks,
            "track_id",
            "/tracks/tracks",
            "DUPLICATE_TRACK_ID",
            issues,
        )
        sequence_ids = set(sequence_map)
        asset_ids = set(asset_map)
        artifact_ids = set(artifact_map)
        declared_event_types = {
            item["name"]
            for item in (snapshot or {})
            .get("resolved_policy", {})
            .get("extensions", {})
            .get("event_types", [])
        }
        declared_target_types = {
            item["name"]: item["base_target_type"]
            for item in (snapshot or {})
            .get("resolved_policy", {})
            .get("extensions", {})
            .get("target_types", [])
        }
        claim_ids = {
            claim_id
            for sequence in sequences
            for claim_id in sequence["claim_ids"]
        }

        self._validate_hierarchy_integrity(
            root_path,
            chapters,
            beats,
            sequences,
            chapter_map,
            beat_map,
            sequence_map,
            issues,
        )

        for sequence_index, sequence in enumerate(sequences):
            if sequence["base_shot"]["asset_ref"] not in asset_ids:
                issues.append(
                    ValidationIssue(
                        str(root_path),
                        f"/sequences/{sequence_index}/base_shot/asset_ref",
                        "WORKSPACE_UNKNOWN_ASSET",
                        f"Unknown workspace reference: "
                        f"{sequence['base_shot']['asset_ref']}",
                    )
                )
            self._validate_base_shot_track(
                root_path, sequence_index, sequence, track_map, issues
            )
            for track_ref_index, track_ref in enumerate(sequence["track_refs"]):
                if track_ref not in track_map:
                    issues.append(
                        ValidationIssue(
                            str(root_path),
                            f"/sequences/{sequence_index}/track_refs/"
                            f"{track_ref_index}",
                            "WORKSPACE_UNKNOWN_TRACK",
                            f"Unknown workspace reference: {track_ref}",
                        )
                    )
            event_groups = (
                ("edit_events", sequence["edit_events"]),
                ("overlay_events", sequence["overlay_events"]),
                ("text_emphasis_events", sequence["text_emphasis_events"]),
                ("audio_events", sequence["audio_events"]),
            )
            self._validate_duplicate_event_ids(
                root_path, sequence_index, event_groups, issues
            )
            for group_name, group in event_groups:
                for event_index, event in enumerate(group):
                    self._validate_event_track_routing(
                        root_path,
                        sequence_index,
                        sequence,
                        group_name,
                        event_index,
                        event,
                        track_map,
                        issues,
                    )
                    if ":" in event["event_type"]:
                        namespace, event_name = event["event_type"].split(":", 1)
                        parameter_namespace = event["parameters"].get("namespace")
                        if (
                            namespace != domain["domain_id"]
                            or parameter_namespace != namespace
                        ):
                            issues.append(
                                ValidationIssue(
                                    str(root_path),
                                    "",
                                    "WORKSPACE_EVENT_NAMESPACE_MISMATCH",
                                    f"Event namespace is inconsistent: {event['event_type']}",
                                )
                            )
                        if event_name not in declared_event_types:
                            issues.append(
                                ValidationIssue(
                                    str(root_path),
                                    "",
                                    "WORKSPACE_UNDECLARED_DOMAIN_EVENT",
                                    f"Domain event is not declared by the policy snapshot: "
                                    f"{event['event_type']}",
                                )
                            )
                    self._validate_event_target(
                        root_path,
                        sequence_index,
                        group_name,
                        event_index,
                        event,
                        sequence,
                        asset_ids,
                        sequence_ids,
                        claim_ids,
                        track_map,
                        domain["domain_id"],
                        declared_target_types,
                        issues,
                    )

        for asset in assets:
            if asset["artifact_ref"] not in artifact_ids:
                issues.append(
                    self._reference_issue(
                        root_path,
                        "WORKSPACE_UNKNOWN_ARTIFACT",
                        asset["artifact_ref"],
                    )
                )

        graph_result = validate_artifact_graph(
            artifacts,
            source_file=str(root_path),
            project_ids={expected_project_id},
            sequence_ids=sequence_ids,
        )
        issues.extend(graph_result.issues)

    def _manifest_kind_issue(
        self,
        document_ref: Mapping[str, Any],
        value: Mapping[str, Any],
        document_path: Path,
    ) -> ValidationIssue | None:
        kind = document_ref["kind"]
        expected = _MANIFEST_KIND_TYPES.get(kind)
        actual = value.get("manifest_type")
        if expected is not None and actual != expected:
            return ValidationIssue(
                str(document_path),
                "/manifest_type",
                "MANIFEST_KIND_MISMATCH",
                f"Document kind {kind!r} requires manifest_type {expected!r}; "
                f"got {actual!r}.",
            )
        if kind == "track_manifest" and actual is not None:
            return ValidationIssue(
                str(document_path),
                "/manifest_type",
                "MANIFEST_KIND_MISMATCH",
                "Document kind 'track_manifest' requires a track contract, "
                f"not manifest_type {actual!r}.",
            )
        return None

    def _load_snapshot_reference(
        self,
        root_path: Path,
        root_data: Mapping[str, Any],
        issues: list[ValidationIssue],
    ) -> Mapping[str, Any] | None:
        raw_ref = root_data["domain"]["policy_snapshot_ref"]
        try:
            snapshot_path = resolve_relative(root_path.parent, raw_ref)
            value = json.loads(snapshot_path.read_text(encoding="utf-8"))
        except (ValueError, OSError, json.JSONDecodeError) as exc:
            issues.append(
                ValidationIssue(
                    str(root_path),
                    "/domain/policy_snapshot_ref",
                    "POLICY_SNAPSHOT_NOT_FOUND",
                    f"Policy snapshot reference is unavailable: {exc}",
                )
            )
            return None
        result = self.catalog.validate(
            value, "domain_policy_snapshot.schema.json", snapshot_path
        )
        if not result.is_valid:
            issues.extend(result.issues)
            issues.append(
                ValidationIssue(
                    str(snapshot_path),
                    "",
                    "POLICY_SNAPSHOT_NOT_FOUND",
                    "Policy snapshot reference is not a valid policy snapshot.",
                )
            )
            return None
        return value

    def _validate_resolver_parity(
        self,
        root_path: Path,
        domain: Mapping[str, Any],
        profile: Mapping[str, Any],
        snapshot: Mapping[str, Any],
        issues: list[ValidationIssue],
    ) -> None:
        if domain["resolution_mode"] == "core_only":
            return
        if self.registry is None or self.resolver is None:
            issues.append(
                ValidationIssue(
                    str(root_path),
                    "/domain/resolution_mode",
                    "DOMAIN_REGISTRY_REQUIRED",
                    "Domain-pack workspaces require a DomainPackRegistry-backed "
                    "resolver to verify the policy snapshot.",
                )
            )
            return
        try:
            pack = self.registry.get(
                domain["domain_id"], domain["domain_pack_version"]
            )
            _, expected = self.resolver.resolve(pack, profile)
        except DomainPackError as exc:
            issues.extend(exc.issues)
            return
        if canonical_json(expected) != canonical_json(snapshot):
            issues.append(
                ValidationIssue(
                    str(root_path),
                    "/domain/policy_snapshot",
                    "POLICY_SNAPSHOT_RESOLUTION_MISMATCH",
                    "Loaded policy snapshot does not match deterministic resolver output.",
                )
            )

    @staticmethod
    def _validate_hierarchy_integrity(
        root_path: Path,
        chapters: list[Mapping[str, Any]],
        beats: list[Mapping[str, Any]],
        sequences: list[Mapping[str, Any]],
        chapter_map: Mapping[str, Mapping[str, Any]],
        beat_map: Mapping[str, Mapping[str, Any]],
        sequence_map: Mapping[str, Mapping[str, Any]],
        issues: list[ValidationIssue],
    ) -> None:
        for chapter_index, chapter in enumerate(chapters):
            chapter_id = chapter["chapter_id"]
            for beat_ref_index, beat_id in enumerate(chapter["beat_ids"]):
                beat = beat_map.get(beat_id)
                if beat is None or beat["chapter_id"] != chapter_id:
                    issues.append(
                        ValidationIssue(
                            str(root_path),
                            f"/story/chapters/{chapter_index}/beat_ids/"
                            f"{beat_ref_index}",
                            "CHAPTER_BEAT_MEMBERSHIP_MISMATCH",
                            f"Chapter {chapter_id!r} lists beat {beat_id!r}, but "
                            "that beat is missing or belongs to another chapter.",
                        )
                    )

        for beat_index, beat in enumerate(beats):
            chapter = chapter_map.get(beat["chapter_id"])
            if chapter is None or beat["beat_id"] not in chapter["beat_ids"]:
                issues.append(
                    ValidationIssue(
                        str(root_path),
                        f"/story/beats/{beat_index}/chapter_id",
                        "CHAPTER_BEAT_MEMBERSHIP_MISMATCH",
                        f"Beat {beat['beat_id']!r} is not listed by its declared "
                        f"chapter {beat['chapter_id']!r}.",
                    )
                )
            for sequence_ref_index, sequence_id in enumerate(
                beat["sequence_ids"]
            ):
                sequence = sequence_map.get(sequence_id)
                if (
                    sequence is None
                    or sequence["beat_id"] != beat["beat_id"]
                    or sequence["chapter_id"] != beat["chapter_id"]
                ):
                    issues.append(
                        ValidationIssue(
                            str(root_path),
                            f"/story/beats/{beat_index}/sequence_ids/"
                            f"{sequence_ref_index}",
                            "BEAT_SEQUENCE_MEMBERSHIP_MISMATCH",
                            f"Beat {beat['beat_id']!r} lists sequence "
                            f"{sequence_id!r}, but the sequence is missing or "
                            "declares a different beat/chapter.",
                        )
                    )

        for sequence_index, sequence in enumerate(sequences):
            chapter = chapter_map.get(sequence["chapter_id"])
            beat = beat_map.get(sequence["beat_id"])
            if chapter is None:
                issues.append(
                    ValidationIssue(
                        str(root_path),
                        f"/sequences/{sequence_index}/chapter_id",
                        "SEQUENCE_CHAPTER_NOT_FOUND",
                        f"Sequence {sequence['sequence_id']!r} references missing "
                        f"chapter {sequence['chapter_id']!r}.",
                    )
                )
            if beat is None:
                issues.append(
                    ValidationIssue(
                        str(root_path),
                        f"/sequences/{sequence_index}/beat_id",
                        "SEQUENCE_BEAT_NOT_FOUND",
                        f"Sequence {sequence['sequence_id']!r} references missing "
                        f"beat {sequence['beat_id']!r}.",
                    )
                )
            if (
                chapter is not None
                and beat is not None
                and (
                    beat["chapter_id"] != sequence["chapter_id"]
                    or beat["beat_id"] not in chapter["beat_ids"]
                )
            ):
                issues.append(
                    ValidationIssue(
                        str(root_path),
                        f"/sequences/{sequence_index}/beat_id",
                        "SEQUENCE_BEAT_CHAPTER_MISMATCH",
                        f"Sequence {sequence['sequence_id']!r} pairs chapter "
                        f"{sequence['chapter_id']!r} with beat "
                        f"{sequence['beat_id']!r}, but that beat does not belong "
                        "to the chapter.",
                    )
                )
            if (
                beat is not None
                and sequence["sequence_id"] not in beat["sequence_ids"]
            ):
                issues.append(
                    ValidationIssue(
                        str(root_path),
                        f"/sequences/{sequence_index}/beat_id",
                        "BEAT_SEQUENCE_MEMBERSHIP_MISMATCH",
                        f"Sequence {sequence['sequence_id']!r} is not listed by "
                        f"its declared beat {sequence['beat_id']!r}.",
                    )
                )

    @staticmethod
    def _validate_base_shot_track(
        root_path: Path,
        sequence_index: int,
        sequence: Mapping[str, Any],
        track_map: Mapping[str, Mapping[str, Any]],
        issues: list[ValidationIssue],
    ) -> None:
        base_track_ref = sequence["base_shot"]["track_ref"]
        base_track = track_map.get(base_track_ref)
        pointer = f"/sequences/{sequence_index}/base_shot/track_ref"
        if base_track is None:
            issues.append(
                ValidationIssue(
                    str(root_path),
                    pointer,
                    "WORKSPACE_UNKNOWN_TRACK",
                    f"Unknown workspace reference: {base_track_ref}",
                )
            )
        elif base_track["track_type"] != "video":
            issues.append(
                ValidationIssue(
                    str(root_path),
                    pointer,
                    "BASE_SHOT_TRACK_TYPE_MISMATCH",
                    f"Base shot for sequence {sequence['sequence_id']!r} "
                    f"references {base_track_ref!r}, a "
                    f"{base_track['track_type']!r} track; expected 'video'.",
                )
            )

    @staticmethod
    def _validate_event_track_routing(
        root_path: Path,
        sequence_index: int,
        sequence: Mapping[str, Any],
        group_name: str,
        event_index: int,
        event: Mapping[str, Any],
        track_map: Mapping[str, Mapping[str, Any]],
        issues: list[ValidationIssue],
    ) -> None:
        track_ref = event["track_ref"]
        track = track_map.get(track_ref)
        pointer = (
            f"/sequences/{sequence_index}/{group_name}/{event_index}/track_ref"
        )
        if track is None:
            issues.append(
                ValidationIssue(
                    str(root_path),
                    pointer,
                    "WORKSPACE_UNKNOWN_TRACK",
                    f"Unknown workspace reference: {track_ref}",
                )
            )
            return
        expected_track_type = (
            "audio" if group_name == "audio_events" else "video"
        )
        if track["track_type"] != expected_track_type:
            issues.append(
                ValidationIssue(
                    str(root_path),
                    pointer,
                    "EVENT_TRACK_TYPE_MISMATCH",
                    f"Sequence {sequence['sequence_id']!r} event "
                    f"{event['event_id']!r} in {group_name} references "
                    f"{track_ref!r}, a {track['track_type']!r} track; "
                    f"expected {expected_track_type!r}.",
                )
            )

    @staticmethod
    def _unique_index(
        root_path: Path,
        items: list[Mapping[str, Any]],
        id_field: str,
        pointer_root: str,
        code: str,
        issues: list[ValidationIssue],
    ) -> dict[str, Mapping[str, Any]]:
        index: dict[str, Mapping[str, Any]] = {}
        first_paths: dict[str, str] = {}
        for item_index, item in enumerate(items):
            item_id = item[id_field]
            pointer = f"{pointer_root}/{item_index}/{id_field}"
            if item_id in index:
                collection_type = (
                    code.removeprefix("DUPLICATE_")
                    .removesuffix("_ID")
                    .lower()
                )
                issues.append(
                    ValidationIssue(
                        str(root_path),
                        pointer,
                        code,
                        f"Duplicate {collection_type} ID {item_id!r}; "
                        "first occurrence at "
                        f"{first_paths[item_id]}, second occurrence at {pointer}.",
                    )
                )
                continue
            index[item_id] = item
            first_paths[item_id] = pointer
        return index

    @staticmethod
    def _validate_duplicate_event_ids(
        root_path: Path,
        sequence_index: int,
        event_groups: tuple[tuple[str, list[Mapping[str, Any]]], ...],
        issues: list[ValidationIssue],
    ) -> None:
        first_paths: dict[str, str] = {}
        for group_name, group in event_groups:
            for event_index, event in enumerate(group):
                event_id = event["event_id"]
                pointer = (
                    f"/sequences/{sequence_index}/{group_name}/"
                    f"{event_index}/event_id"
                )
                if event_id in first_paths:
                    issues.append(
                        ValidationIssue(
                            str(root_path),
                            pointer,
                            "DUPLICATE_EVENT_ID",
                            f"Duplicate event ID {event_id!r} within sequence; "
                            f"first occurrence at {first_paths[event_id]}, "
                            f"second occurrence at {pointer}.",
                        )
                    )
                    continue
                first_paths[event_id] = pointer

    @staticmethod
    def _validate_event_target(
        root_path: Path,
        sequence_index: int,
        group_name: str,
        event_index: int,
        event: Mapping[str, Any],
        sequence: Mapping[str, Any],
        asset_ids: set[str],
        sequence_ids: set[str],
        claim_ids: set[str],
        track_map: Mapping[str, Mapping[str, Any]],
        domain_id: str,
        declared_target_types: Mapping[str, str],
        issues: list[ValidationIssue],
    ) -> None:
        target = event["target"]
        target_type = target["target_type"]
        target_id = target["target_id"]
        effective_type = target_type
        if target_type not in _CORE_TARGET_TYPES:
            if ":" not in target_type:
                effective_type = ""
            else:
                namespace, name = target_type.split(":", 1)
                effective_type = (
                    declared_target_types.get(name, "")
                    if namespace == domain_id
                    else ""
                )
        pointer = (
            f"/sequences/{sequence_index}/{group_name}/{event_index}/target"
        )
        if not effective_type:
            issues.append(
                ValidationIssue(
                    str(root_path),
                    f"{pointer}/target_type",
                    "EVENT_TARGET_TYPE_INVALID",
                    f"Unknown or undeclared target type: {target_type}",
                )
            )
            return
        if effective_type not in _EVENT_TARGET_COMPATIBILITY[group_name]:
            issues.append(
                ValidationIssue(
                    str(root_path),
                    f"{pointer}/target_type",
                    "EVENT_TARGET_TYPE_MISMATCH",
                    f"{group_name} cannot target {target_type}.",
                )
            )
            return

        exists = {
            "asset": target_id in asset_ids,
            "video_track": target_id in track_map
            and track_map[target_id]["track_type"] == "video",
            "audio_track": target_id in track_map
            and track_map[target_id]["track_type"] == "audio",
            "overlay_track": target_id in track_map
            and track_map[target_id]["track_type"] == "video"
            and track_map[target_id]["role"] == "overlay",
            "sequence": target_id in sequence_ids,
            "base_shot": target_id == sequence["sequence_id"],
            "claim": target_id in claim_ids,
        }[effective_type]
        if not exists:
            issues.append(
                ValidationIssue(
                    str(root_path),
                    f"{pointer}/target_id",
                    "EVENT_TARGET_NOT_FOUND",
                    f"Target {target_id!r} was not found in the {effective_type} collection.",
                )
            )

    @staticmethod
    def _first_kind(
        root_data: Mapping[str, Any],
        documents: Mapping[str, Mapping[str, Any]],
        kind: str,
    ) -> Mapping[str, Any] | None:
        values = WorkspaceLoader._all_kind(root_data, documents, kind)
        return values[0] if values else None

    @staticmethod
    def _all_kind(
        root_data: Mapping[str, Any],
        documents: Mapping[str, Mapping[str, Any]],
        kind: str,
    ) -> list[Mapping[str, Any]]:
        return [
            documents[item["document_id"]]
            for item in root_data["documents"]
            if item["kind"] == kind and item["document_id"] in documents
        ]

    @staticmethod
    def _reference_issue(
        root_path: Path,
        code: str,
        reference: str,
    ) -> ValidationIssue:
        return ValidationIssue(
            str(root_path),
            "",
            code,
            f"Unknown workspace reference: {reference}",
        )
