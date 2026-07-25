"""Read-only typed views of data already accepted by canonical JSON Schema.

These dataclasses never replace SchemaCatalog validation.  Public loaders create
them only after validation succeeds; direct mapping conversion is intentionally
limited to internal invariant helpers working on already schema-checked data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


def _require(data: Mapping[str, Any], *fields: str) -> None:
    missing = [field for field in fields if field not in data]
    if missing:
        raise ValueError(f"Missing critical fields: {', '.join(missing)}")


@dataclass(frozen=True)
class Project:
    schema_version: str
    project_id: str
    title: str
    created_at: str
    updated_at: str
    domain_id: str
    domain_pack_version: str
    policy_snapshot_id: str
    status: str
    version: int

    @classmethod
    def _from_validated_dict(cls, data: Mapping[str, Any]) -> "Project":
        _require(
            data,
            "project_id",
            "title",
            "domain_id",
            "domain_pack_version",
            "policy_snapshot_id",
            "status",
            "version",
        )
        return cls(*(data[field] for field in cls.__dataclass_fields__))


@dataclass(frozen=True)
class Chapter:
    schema_version: str
    chapter_id: str
    project_id: str
    title: str
    narrative_goal: str
    order: int
    beat_ids: tuple[str, ...]
    status: str
    version: int

    @classmethod
    def _from_validated_dict(cls, data: Mapping[str, Any]) -> "Chapter":
        _require(data, *cls.__dataclass_fields__)
        return cls(
            schema_version=data["schema_version"],
            chapter_id=data["chapter_id"],
            project_id=data["project_id"],
            title=data["title"],
            narrative_goal=data["narrative_goal"],
            order=data["order"],
            beat_ids=tuple(data["beat_ids"]),
            status=data["status"],
            version=data["version"],
        )


@dataclass(frozen=True)
class Beat:
    schema_version: str
    beat_id: str
    chapter_id: str
    narrative_goal: str
    editorial_role: str
    claim_ids: tuple[str, ...]
    order: int
    sequence_ids: tuple[str, ...]
    status: str
    version: int

    @classmethod
    def _from_validated_dict(cls, data: Mapping[str, Any]) -> "Beat":
        _require(data, *cls.__dataclass_fields__)
        return cls(
            schema_version=data["schema_version"],
            beat_id=data["beat_id"],
            chapter_id=data["chapter_id"],
            narrative_goal=data["narrative_goal"],
            editorial_role=data["editorial_role"],
            claim_ids=tuple(data["claim_ids"]),
            order=data["order"],
            sequence_ids=tuple(data["sequence_ids"]),
            status=data["status"],
            version=data["version"],
        )


@dataclass(frozen=True)
class EventEnvelope:
    schema_version: str
    event_id: str
    event_type: str
    timing_ref: Mapping[str, Any]
    track_ref: str
    target: Mapping[str, Any]
    status: str
    version: int
    parameters: Mapping[str, Any]
    extension_metadata: Mapping[str, Any]

    @classmethod
    def _from_validated_dict(cls, data: Mapping[str, Any]) -> "EventEnvelope":
        _require(data, *cls.__dataclass_fields__)
        return cls(*(data[field] for field in cls.__dataclass_fields__))


@dataclass(frozen=True)
class EditorialSequence:
    schema_version: str
    sequence_id: str
    chapter_id: str
    beat_id: str
    narrative_goal: str
    editorial_role: str
    claim_ids: tuple[str, ...]
    start_cue: Mapping[str, Any]
    end_cue: Mapping[str, Any]
    base_shot: Mapping[str, Any]
    edit_events: tuple[EventEnvelope, ...]
    overlay_events: tuple[EventEnvelope, ...]
    text_emphasis_events: tuple[EventEnvelope, ...]
    audio_events: tuple[EventEnvelope, ...]
    continuity_constraints: Mapping[str, Any]
    fallback_policy: Mapping[str, Any]
    status: str
    version: int
    track_refs: tuple[str, ...]

    @classmethod
    def _from_validated_dict(
        cls, data: Mapping[str, Any]
    ) -> "EditorialSequence":
        _require(data, *cls.__dataclass_fields__)
        return cls(
            schema_version=data["schema_version"],
            sequence_id=data["sequence_id"],
            chapter_id=data["chapter_id"],
            beat_id=data["beat_id"],
            narrative_goal=data["narrative_goal"],
            editorial_role=data["editorial_role"],
            claim_ids=tuple(data["claim_ids"]),
            start_cue=data["start_cue"],
            end_cue=data["end_cue"],
            base_shot=data["base_shot"],
            edit_events=tuple(
                EventEnvelope._from_validated_dict(item)
                for item in data["edit_events"]
            ),
            overlay_events=tuple(
                EventEnvelope._from_validated_dict(item)
                for item in data["overlay_events"]
            ),
            text_emphasis_events=tuple(
                EventEnvelope._from_validated_dict(item)
                for item in data["text_emphasis_events"]
            ),
            audio_events=tuple(
                EventEnvelope._from_validated_dict(item)
                for item in data["audio_events"]
            ),
            continuity_constraints=data["continuity_constraints"],
            fallback_policy=data["fallback_policy"],
            status=data["status"],
            version=data["version"],
            track_refs=tuple(data["track_refs"]),
        )


@dataclass(frozen=True)
class Asset:
    schema_version: str
    asset_id: str
    asset_type: str
    editorial_role: str
    provenance: Mapping[str, Any]
    content_hash: str
    media_metadata: Mapping[str, Any]
    availability: str
    review_state: str
    artifact_ref: str
    status: str
    version: int

    @classmethod
    def _from_validated_dict(cls, data: Mapping[str, Any]) -> "Asset":
        _require(data, *cls.__dataclass_fields__)
        return cls(*(data[field] for field in cls.__dataclass_fields__))


@dataclass(frozen=True)
class ArtifactRecord:
    schema_version: str
    artifact_id: str
    artifact_type: str
    project_id: str
    sequence_id: str | None
    created_at: str
    last_accessed_at: str
    content_hash: str
    size_bytes: int
    retention_class: str
    dependency_ids: tuple[str, ...]
    locked: bool
    pinned: bool
    approved: bool
    cleanup_candidate: bool
    producer: str
    producer_version: str
    job_id: str | None
    status: str
    version: int

    @classmethod
    def _from_validated_dict(
        cls, data: Mapping[str, Any]
    ) -> "ArtifactRecord":
        _require(data, *cls.__dataclass_fields__)
        values = dict(data)
        values["dependency_ids"] = tuple(values["dependency_ids"])
        return cls(**{field: values[field] for field in cls.__dataclass_fields__})


@dataclass(frozen=True)
class RetentionPolicy:
    schema_version: str
    policy_id: str
    rules: tuple[Mapping[str, Any], ...]
    status: str
    version: int

    @classmethod
    def _from_validated_dict(
        cls, data: Mapping[str, Any]
    ) -> "RetentionPolicy":
        _require(data, *cls.__dataclass_fields__)
        return cls(
            schema_version=data["schema_version"],
            policy_id=data["policy_id"],
            rules=tuple(data["rules"]),
            status=data["status"],
            version=data["version"],
        )


@dataclass(frozen=True)
class DomainPackManifest:
    schema_version: str
    domain_id: str
    domain_pack_version: str
    display_name: str
    published_at: str
    contract_status: str
    policy_bundle_refs: tuple[str, ...]
    prompt_bundle_refs: tuple[str, ...]
    extensions: Mapping[str, Any]
    status: str
    version: int

    @classmethod
    def _from_validated_dict(
        cls, data: Mapping[str, Any]
    ) -> "DomainPackManifest":
        _require(data, *cls.__dataclass_fields__)
        return cls(
            schema_version=data["schema_version"],
            domain_id=data["domain_id"],
            domain_pack_version=data["domain_pack_version"],
            display_name=data["display_name"],
            published_at=data["published_at"],
            contract_status=data["contract_status"],
            policy_bundle_refs=tuple(data["policy_bundle_refs"]),
            prompt_bundle_refs=tuple(data["prompt_bundle_refs"]),
            extensions=data["extensions"],
            status=data["status"],
            version=data["version"],
        )


@dataclass(frozen=True)
class DomainProfile:
    schema_version: str
    profile_id: str
    domain_id: str
    domain_pack_version: str
    enabled_extensions: tuple[Mapping[str, Any], ...]
    policy_overrides: Mapping[str, Any]
    status: str
    version: int

    @classmethod
    def _from_validated_dict(
        cls, data: Mapping[str, Any]
    ) -> "DomainProfile":
        _require(data, *cls.__dataclass_fields__)
        return cls(
            schema_version=data["schema_version"],
            profile_id=data["profile_id"],
            domain_id=data["domain_id"],
            domain_pack_version=data["domain_pack_version"],
            enabled_extensions=tuple(data["enabled_extensions"]),
            policy_overrides=data["policy_overrides"],
            status=data["status"],
            version=data["version"],
        )


@dataclass(frozen=True)
class DomainPolicySnapshot:
    schema_version: str
    snapshot_id: str
    domain_id: str
    domain_pack_version: str
    profile_id: str
    manifest_hash: str
    resolved_policy: Mapping[str, Any]
    canonical_hash: str
    immutable: bool
    created_at: str
    version: int

    @classmethod
    def _from_validated_dict(
        cls, data: Mapping[str, Any]
    ) -> "DomainPolicySnapshot":
        _require(data, *cls.__dataclass_fields__)
        return cls(*(data[field] for field in cls.__dataclass_fields__))


@dataclass(frozen=True)
class Workspace:
    schema_version: str
    workspace_id: str
    layout: str
    project_metadata: Mapping[str, Any]
    domain: Mapping[str, Any]
    documents: tuple[Mapping[str, Any], ...]
    render_profile: Mapping[str, Any]
    status: str
    version: int

    @classmethod
    def _from_validated_dict(cls, data: Mapping[str, Any]) -> "Workspace":
        _require(data, *cls.__dataclass_fields__)
        return cls(
            schema_version=data["schema_version"],
            workspace_id=data["workspace_id"],
            layout=data["layout"],
            project_metadata=data["project_metadata"],
            domain=data["domain"],
            documents=tuple(data["documents"]),
            render_profile=data["render_profile"],
            status=data["status"],
            version=data["version"],
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Workspace":
        raise TypeError(
            "Workspace typed views require SchemaCatalog validation; "
            "use WorkspaceLoader.load()."
        )
