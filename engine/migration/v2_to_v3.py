"""Deterministic, fail-closed V2 timeline to canonical V3 migration."""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote

from engine.contracts import (
    DomainPackError,
    DomainPolicyResolver,
    SchemaCatalog,
    WorkspaceLoader,
    policy_snapshot_hash,
)

from .models import (
    BLOCKING_CLASSIFICATIONS,
    CLASSIFICATIONS,
    SEVERITIES,
    STRICT_BLOCKING_CLASSIFICATIONS,
    MigrationIssue,
    MigrationMapping,
    MigrationOptions,
    MigrationOutcome,
    canonical_fingerprint,
    deterministic_token,
    source_type,
)
from .security import inspect_source_value


MIGRATION_VERSION = "1.0.0"
EPOCH = "1970-01-01T00:00:00Z"
SCHEMA_VERSION = "3.0.0"

ROOT_FIELDS = frozenset({"version", "bgm", "blocks"})
BGM_FIELDS = frozenset(
    {"enabled", "track_id", "gain_db", "fade_in", "fade_out"}
)
SFX_FIELDS = frozenset(
    {"enabled", "asset_id", "trigger_cue", "gain_db", "max_duration"}
)
BLOCK_FIELDS = frozenset(
    {
        "block_id",
        "narration",
        "audio_file",
        "pause_before",
        "pause_after",
        "bgm_drop",
        "sfx_category",
        "fill_policy",
        "visuals",
    }
)
VISUAL_FIELDS = frozenset(
    {
        "offset_start",
        "offset_end",
        "type",
        "clip_start",
        "clip_end",
        "query",
        "url",
        "target_text",
        "target_selector",
        "zoom",
        "scroll_duration",
        "highlight_target",
        "main_text",
        "sub_text",
        "background_style",
        "accent_animation",
        "logo_url",
        "start_val",
        "end_val",
        "prefix",
        "suffix",
        "label",
        "is_approximate",
        "max_height",
        "crop_mode",
        "fit_mode",
        "extra",
        "narration_cue_start",
        "narration_cue_end",
        "visual_purpose",
        "required_content",
        "forbidden_content",
        "fallback_queries",
        "allow_generic_stock",
        "transition_in",
        "transition_out",
        "timing_mode",
        "trigger_cue",
        "min_duration",
        "max_duration",
        "subtitle_policy",
        "fill_policy",
        "asset_locked",
        "selected_asset_url",
        "sfx_category",
        "preferred_duration",
        "sfx",
    }
)
LOSS_CODES = {
    "DEFAULTED": "MIGRATION_FIELD_DEFAULTED",
    "DROPPED": "MIGRATION_FIELD_DROPPED",
    "UNSUPPORTED": "MIGRATION_FIELD_UNSUPPORTED",
    "AMBIGUOUS": "MIGRATION_FIELD_AMBIGUOUS",
    "INVALID_SOURCE": "MIGRATION_SOURCE_INVALID",
}
LOSS_SEVERITY = {
    "DEFAULTED": "WARNING",
    "DROPPED": "WARNING",
    "UNSUPPORTED": "WARNING",
    "AMBIGUOUS": "ERROR",
    "INVALID_SOURCE": "ERROR",
}
VISUAL_ASSET_TYPES = {
    "stock": "video",
    "youtube": "video",
    "web_record": "document",
    "highlight_article": "document",
    "chart": "chart_data",
    "big_text": "generated_media",
    "counter": "generated_media",
    "quote": "generated_media",
    "black": "generated_media",
}
VISUAL_EVENT_TYPES = {
    "web_record": "source_focus",
    "highlight_article": "source_focus",
    "chart": "chart_draw",
    "big_text": "text_reveal",
    "counter": "metric_count",
}


def _escape(part: str) -> str:
    return part.replace("~", "~0").replace("/", "~1")


def _leaf_items(value: Any, pointer: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(value, Mapping):
        for key in sorted(value):
            yield from _leaf_items(value[key], f"{pointer}/{_escape(str(key))}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _leaf_items(item, f"{pointer}/{index}")
    else:
        yield pointer, value


def source_leaf_pointers(value: Any) -> tuple[str, ...]:
    """Return deterministic JSON leaf pointers used by coverage accounting."""
    return tuple(pointer for pointer, _ in _leaf_items(value))


def _field(pointer: str) -> str:
    return pointer.rsplit("/", 1)[-1].replace("~1", "/").replace("~0", "~")


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9_-]+", "_", value.lower()).strip("_-")
    return slug or "generated"


def _stable_id(prefix: str, raw: str | None, pointer: str) -> str:
    if raw:
        candidate = _slug(raw)
        if candidate.startswith(prefix):
            value = candidate
        else:
            value = prefix + candidate
    else:
        value = deterministic_token(prefix, pointer, length=20)
    suffix_limit = 63
    suffix = value[len(prefix) :]
    if len(suffix) > suffix_limit:
        tail = deterministic_token("", value, length=8)
        suffix = suffix[: suffix_limit - 9] + "_" + tail
    if len(suffix) < 3:
        suffix = (suffix + "_id")[:3]
    return prefix + suffix


def _cue_id(kind: str, pointer: str) -> str:
    return deterministic_token(f"cue_{kind}_", pointer, length=16)


def _cue(
    kind: str,
    pointer: str,
    anchor_ref: str,
    *,
    anchor_type: str = "semantic_marker",
    relation: str = "at",
) -> dict[str, Any]:
    return {
        "cue_id": _cue_id(kind, pointer),
        "anchor_type": anchor_type,
        "anchor_ref": anchor_ref,
        "relation": relation,
    }


def _semantic_offset(value: Any, fallback: str) -> str:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f"v2-offset:{value:g}"
    if isinstance(value, str) and value and value != "AUTO":
        return f"v2-offset:{value}"
    return fallback


class _MigrationBuilder:
    def __init__(self) -> None:
        self.mappings: list[MigrationMapping] = []
        self.issues: list[MigrationIssue] = []
        self.accounted: set[str] = set()
        self.ids: dict[tuple[str, str], str] = {}

    def account(
        self,
        pointer: str,
        value: Any,
        destination: str | None,
        classification: str,
        semantics: str,
        concept: str,
        transformation: str,
        *,
        notes: str = "",
        code: str | None = None,
        severity: str | None = None,
        action: str = "Review the migration report.",
    ) -> None:
        if classification not in CLASSIFICATIONS:
            raise ValueError(f"Unknown classification: {classification}")
        if pointer and pointer in self.accounted:
            return
        if pointer:
            self.accounted.add(pointer)
        resolved_severity = severity or LOSS_SEVERITY.get(classification, "NONE")
        self.mappings.append(
            MigrationMapping(
                source_pointer=pointer,
                source_field=_field(pointer) if pointer else "",
                source_type=source_type(value) if pointer else "derived",
                source_semantics=semantics,
                destination_pointer=destination,
                destination_concept=concept,
                classification=classification,
                transformation=transformation,
                loss_severity=resolved_severity,
                notes=notes,
            )
        )
        issue_code = code or LOSS_CODES.get(classification)
        if issue_code is not None:
            self.issue(
                resolved_severity,
                issue_code,
                notes or f"{classification} migration at {pointer or '/'}",
                pointer,
                destination,
                classification,
                action,
            )

    def issue(
        self,
        severity: str,
        code: str,
        message: str,
        source_pointer: str,
        destination_pointer: str | None,
        classification: str,
        action: str,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        self.issues.append(
            MigrationIssue(
                severity=severity,
                code=code,
                message=message,
                source_pointer=source_pointer,
                destination_pointer=destination_pointer,
                classification=classification,
                action=action,
                details=details,
            )
        )

    def register_id(
        self,
        collection: str,
        target_id: str,
        pointer: str,
    ) -> None:
        key = (collection, target_id)
        previous = self.ids.get(key)
        if previous is None:
            self.ids[key] = pointer
            return
        self.issue(
            "ERROR",
            "MIGRATION_ID_COLLISION",
            f"{previous} and {pointer} propose the same {target_id!r}.",
            pointer,
            f"/{collection}",
            "INVALID_SOURCE",
            "Assign unique stable source IDs before migration.",
            {
                "source_pointers": [previous, pointer],
                "proposed_target_id": target_id,
                "target_collection": collection,
            },
        )


class V2ToV3Migrator:
    """Pure V2 mapping with canonical schema and loader validation."""

    def __init__(self, catalog: SchemaCatalog):
        self.catalog = catalog

    def migrate(
        self,
        source: Mapping[str, Any],
        options: MigrationOptions | None = None,
    ) -> MigrationOutcome:
        options = options or MigrationOptions()
        source_copy = copy.deepcopy(source)
        fingerprint = canonical_fingerprint(source_copy)
        builder = _MigrationBuilder()

        if not isinstance(source_copy, Mapping):
            builder.issue(
                "ERROR",
                "MIGRATION_SOURCE_INVALID",
                "V2 timeline root must be a JSON object.",
                "",
                None,
                "INVALID_SOURCE",
                "Provide a V2 timeline object with a blocks array.",
            )
            return self._outcome(
                source_copy, fingerprint, options, builder, None, []
            )

        blocks = source_copy.get("blocks")
        if not isinstance(blocks, list) or not blocks:
            builder.issue(
                "ERROR",
                "MIGRATION_SOURCE_INVALID",
                "V2 timeline requires a non-empty blocks array.",
                "/blocks",
                "/sequences",
                "INVALID_SOURCE",
                "Provide at least one V2 narration block.",
            )
            return self._outcome(
                source_copy, fingerprint, options, builder, None, []
            )

        source_version = source_copy.get("version")
        if source_version is None:
            source_version_text = "2.x-unspecified"
            builder.account(
                "",
                None,
                "/source_schema_version",
                "DEFAULTED",
                "V2 source format version",
                "migration source version",
                "Use explicit deterministic unspecified V2 version.",
                notes="V2 source omitted version; recorded as 2.x-unspecified.",
            )
        elif not isinstance(source_version, (str, int, float)):
            builder.account(
                "/version",
                source_version,
                "/source_schema_version",
                "INVALID_SOURCE",
                "V2 source format version",
                "migration source version",
                "Reject non-scalar version metadata.",
                notes="V2 version must be a string or number.",
            )
            source_version_text = "invalid"
        else:
            source_version_text = str(source_version)
            builder.account(
                "/version",
                source_version,
                "/source_schema_version",
                "NORMALIZED",
                "V2 source format version",
                "migration source version",
                "Convert the orchestration version marker to text.",
                notes=(
                    "The active V2 detector accepts this field although the "
                    "Pydantic schema snapshot does not retain it."
                ),
            )

        domain = self._domain(options, builder)
        workspace = (
            self._workspace(source_copy, blocks, fingerprint, domain, builder)
            if domain is not None
            else None
        )
        self._account_remaining(source_copy, builder)

        target_issues: list[dict[str, str]] = []
        if workspace is not None and not any(
            issue.severity == "ERROR" for issue in builder.issues
        ):
            loader = WorkspaceLoader(
                self.catalog,
                registry=options.registry
                if options.resolution_mode == "domain_pack"
                else None,
            )
            validation = loader.validate_data(
                workspace, source_file="<migrated-workspace>"
            )
            for issue in validation.issues:
                target_issues.append(
                    {
                        "code": issue.code,
                        "pointer": issue.json_pointer,
                        "message": issue.message,
                    }
                )
                builder.issue(
                    "ERROR",
                    "MIGRATION_TARGET_INVALID",
                    f"{issue.code}: {issue.message}",
                    "",
                    issue.json_pointer or "/",
                    "INVALID_SOURCE",
                    "Correct the source mapping or canonical target contract.",
                )

        return self._outcome(
            source_copy,
            fingerprint,
            options,
            builder,
            workspace,
            target_issues,
            source_version_text,
        )

    def _domain(
        self,
        options: MigrationOptions,
        builder: _MigrationBuilder,
    ) -> dict[str, Any] | None:
        if options.resolution_mode == "core_only":
            profile = {
                "schema_version": SCHEMA_VERSION,
                "profile_id": "dpf_core_migrated",
                "domain_id": "core-generic",
                "domain_pack_version": "0.0.0",
                "enabled_extensions": [],
                "policy_overrides": {},
                "status": "ready",
                "version": 1,
            }
            payload = {
                "schema_version": SCHEMA_VERSION,
                "domain_id": "core-generic",
                "domain_pack_version": "0.0.0",
                "profile_id": profile["profile_id"],
                "manifest_hash": "sha256:" + "0" * 64,
                "resolved_policy": {},
                "immutable": True,
                "created_at": EPOCH,
                "version": 1,
            }
            canonical_hash = policy_snapshot_hash(payload)
            snapshot = {
                **payload,
                "snapshot_id": "dps_"
                + canonical_hash.removeprefix("sha256:")[:20],
                "canonical_hash": canonical_hash,
            }
        else:
            if (
                options.registry is None
                or options.domain_id is None
                or options.domain_pack_version is None
                or options.profile is None
            ):
                builder.issue(
                    "ERROR",
                    "MIGRATION_DOMAIN_CONFIGURATION_REQUIRED",
                    "domain_pack mode requires registry, domain_id, "
                    "domain_pack_version, and profile.",
                    "",
                    "/domain",
                    "INVALID_SOURCE",
                    "Provide all explicit domain-pack options.",
                )
                return None
            try:
                pack = options.registry.get(
                    options.domain_id, options.domain_pack_version
                )
                _, snapshot = DomainPolicyResolver(self.catalog).resolve(
                    pack, options.profile
                )
            except DomainPackError as exc:
                builder.issue(
                    "ERROR",
                    "MIGRATION_DOMAIN_CONFIGURATION_REQUIRED",
                    str(exc),
                    "",
                    "/domain",
                    "INVALID_SOURCE",
                    "Select a discovered domain/version and valid profile.",
                    {
                        "domain_issues": [
                            {
                                "code": item.code,
                                "pointer": item.json_pointer,
                                "message": item.message,
                            }
                            for item in exc.issues
                        ]
                    },
                )
                return None
            profile = copy.deepcopy(dict(options.profile))

        return {
            "resolution_mode": options.resolution_mode,
            "domain_id": profile["domain_id"],
            "domain_pack_version": profile["domain_pack_version"],
            "profile_id": profile["profile_id"],
            "policy_snapshot_id": snapshot["snapshot_id"],
            "policy_snapshot_ref": "domain/policy_snapshot.json",
            "profile": profile,
            "policy_snapshot": snapshot,
        }

    def _workspace(
        self,
        source: Mapping[str, Any],
        blocks: list[Any],
        fingerprint: str,
        domain: Mapping[str, Any],
        builder: _MigrationBuilder,
    ) -> dict[str, Any]:
        project_id = "prj_" + fingerprint.removeprefix("sha256:")[:20]
        workspace_id = "wsp_" + fingerprint.removeprefix("sha256:")[:20]
        chapter_id = "chp_migrated_timeline"
        video_track = "trk_video_migrated_base"
        audio_track = "trk_audio_migrated_narration"
        assets: list[dict[str, Any]] = []
        artifacts: list[dict[str, Any]] = []
        beats: list[dict[str, Any]] = []
        sequences: list[dict[str, Any]] = []

        builder.account(
            "",
            None,
            "/workspace_id",
            "DERIVED",
            "Canonical source identity",
            "workspace identity",
            "Derive from canonical source fingerprint.",
        )
        builder.account(
            "",
            None,
            "/project/project_id",
            "DERIVED",
            "Canonical source identity",
            "project identity",
            "Derive from canonical source fingerprint.",
        )

        for block_index, raw_block in enumerate(blocks):
            block_pointer = f"/blocks/{block_index}"
            if not isinstance(raw_block, Mapping):
                builder.account(
                    block_pointer,
                    raw_block,
                    None,
                    "INVALID_SOURCE",
                    "V2 narration block",
                    "V3 beat and sequence",
                    "Reject non-object narration block.",
                    notes="Each V2 block must be a JSON object.",
                )
                continue
            block = raw_block
            block_id_value = block.get("block_id")
            if block_id_value is not None and not isinstance(block_id_value, str):
                builder.account(
                    f"{block_pointer}/block_id",
                    block_id_value,
                    None,
                    "INVALID_SOURCE",
                    "V2 stable block identity",
                    "beat and sequence identity",
                    "Reject non-string stable identity.",
                    notes="block_id must be a string.",
                )
                block_id_value = None
            stable = block_id_value or deterministic_token(
                "block_", block_pointer, length=16
            )
            beat_id = _stable_id("beat_", stable, block_pointer)
            sequence_id = _stable_id("seq_", stable, block_pointer)
            builder.register_id("story/beats", beat_id, f"{block_pointer}/block_id")
            builder.register_id("sequences", sequence_id, f"{block_pointer}/block_id")
            if "block_id" in block:
                builder.account(
                    f"{block_pointer}/block_id",
                    block["block_id"],
                    f"/story/beats/{block_index}/beat_id",
                    "NORMALIZED",
                    "Stable V2 narration block identity",
                    "V3 beat and sequence stable IDs",
                    "Normalize to canonical beat_/seq_ namespaces.",
                    notes=f"Also derives sequence_id {sequence_id}.",
                )
            else:
                builder.account(
                    "",
                    None,
                    f"/story/beats/{block_index}/beat_id",
                    "DERIVED",
                    "Canonical source block pointer",
                    "V3 beat and sequence stable IDs",
                    "Derive IDs from the canonical source pointer.",
                )

            narration = block.get("narration")
            if not isinstance(narration, str):
                if "narration" in block:
                    builder.account(
                        f"{block_pointer}/narration",
                        narration,
                        f"/sequences/{block_index}/narrative_goal",
                        "INVALID_SOURCE",
                        "V2 narration text",
                        "V3 sequence narrative goal",
                        "Reject non-string narration.",
                        notes="narration must be a string.",
                    )
                narration = ""
            if narration.strip():
                builder.account(
                    f"{block_pointer}/narration",
                    narration,
                    f"/sequences/{block_index}/narrative_goal",
                    "NORMALIZED",
                    "Narrated editorial text",
                    "sequence and beat narrative goal",
                    "Preserve the complete text as the aggregate editorial goal.",
                    notes=(
                        "V3 Phase 1 has semantic narration references but no "
                        "canonical narration-text document."
                    ),
                )
                narrative_goal = narration
            else:
                narrative_goal = f"Migrated narration block {stable}"
                builder.account(
                    f"{block_pointer}/narration"
                    if "narration" in block
                    else "",
                    narration,
                    f"/sequences/{block_index}/narrative_goal",
                    "DEFAULTED",
                    "Narrated editorial text",
                    "sequence narrative goal",
                    "Use a deterministic non-empty fallback goal.",
                    notes="Empty V2 narration cannot satisfy the V3 narrative goal.",
                )

            visuals = block.get("visuals")
            if not isinstance(visuals, list) or not visuals:
                builder.issue(
                    "ERROR",
                    "MIGRATION_REFERENCE_MISSING",
                    "A V2 block needs at least one visual for a V3 base shot.",
                    f"{block_pointer}/visuals",
                    f"/sequences/{block_index}/base_shot",
                    "AMBIGUOUS",
                    "Add a concrete visual to the V2 block.",
                )
                continue

            sequence_assets: list[str] = []
            events: list[dict[str, Any]] = []
            for visual_index, raw_visual in enumerate(visuals):
                visual_pointer = f"{block_pointer}/visuals/{visual_index}"
                if not isinstance(raw_visual, Mapping):
                    builder.account(
                        visual_pointer,
                        raw_visual,
                        None,
                        "INVALID_SOURCE",
                        "V2 visual scene",
                        "V3 asset and edit event",
                        "Reject non-object visual scene.",
                        notes="Each V2 visual must be a JSON object.",
                    )
                    continue
                visual = raw_visual
                built = self._visual(
                    visual,
                    visual_pointer,
                    block_index,
                    visual_index,
                    len(assets),
                    project_id,
                    sequence_id,
                    video_track,
                    builder,
                )
                if built is None:
                    continue
                asset, artifact, event = built
                assets.append(asset)
                artifacts.append(artifact)
                events.append(event)
                sequence_assets.append(asset["asset_id"])

            if not sequence_assets:
                builder.issue(
                    "ERROR",
                    "MIGRATION_REFERENCE_MISSING",
                    "No valid visual remains for the V3 sequence base shot.",
                    f"{block_pointer}/visuals",
                    f"/sequences/{block_index}/base_shot",
                    "AMBIGUOUS",
                    "Correct invalid V2 visuals.",
                )
                continue

            fill_values = [
                block.get("fill_policy"),
                *[
                    item.get("fill_policy")
                    for item in visuals
                    if isinstance(item, Mapping)
                    and item.get("fill_policy") is not None
                ],
            ]
            fail_closed = any(value == "error" for value in fill_values)
            allow_generic = any(
                isinstance(item, Mapping)
                and item.get("allow_generic_stock") is True
                for item in visuals
            )
            fallback_policy = {
                "mode": "require_review"
                if allow_generic and not fail_closed
                else "fail_closed",
                "on_missing_asset": "block_sequence"
                if allow_generic
                else "error",
            }
            if "fill_policy" in block:
                builder.account(
                    f"{block_pointer}/fill_policy",
                    block["fill_policy"],
                    f"/sequences/{block_index}/fallback_policy",
                    "MERGED",
                    "V2 block missing-visual policy",
                    "V3 sequence fallback policy",
                    "Merge block and visual policies into one fail-closed policy.",
                )
            for visual_index, visual in enumerate(visuals):
                if not isinstance(visual, Mapping):
                    continue
                for name in ("fill_policy", "allow_generic_stock"):
                    if name in visual:
                        builder.account(
                            f"{block_pointer}/visuals/{visual_index}/{name}",
                            visual[name],
                            f"/sequences/{block_index}/fallback_policy",
                            "MERGED",
                            f"V2 visual {name} setting",
                            "V3 sequence fallback policy",
                            "Merge per-visual behavior into the sequence policy.",
                        )
            end_visual = visuals[-1]
            end_value = (
                end_visual.get("offset_end")
                if isinstance(end_visual, Mapping)
                else None
            )
            end_pointer = f"{block_pointer}/visuals/{len(visuals)-1}/offset_end"
            if end_value == "AUTO":
                builder.account(
                    end_pointer,
                    end_value,
                    f"/sequences/{block_index}/end_cue",
                    "DEFAULTED",
                    "V2 automatic visual end",
                    "semantic sequence end cue",
                    "Resolve AUTO to the deterministic narration-block end marker.",
                    notes="AUTO has no frame value in the Phase 1 semantic cue model.",
                )
            elif end_value is None:
                builder.account(
                    "",
                    None,
                    f"/sequences/{block_index}/end_cue",
                    "DERIVED",
                    "Canonical narration block boundary",
                    "semantic sequence end cue",
                    "Derive the end marker from the block boundary.",
                )
            first_visual = visuals[0]
            purpose = (
                first_visual.get("visual_purpose")
                if isinstance(first_visual, Mapping)
                else None
            )
            if not isinstance(purpose, str) or not purpose.strip():
                purpose = "Preserve the first V2 visual as the sequence base shot."
            else:
                builder.account(
                    f"{block_pointer}/visuals/0/visual_purpose",
                    purpose,
                    f"/sequences/{block_index}/base_shot/editorial_purpose",
                    "EXACT",
                    "V2 base visual editorial purpose",
                    "V3 base-shot editorial purpose",
                    "Copy the editorial purpose exactly.",
                )

            beats.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "beat_id": beat_id,
                    "chapter_id": chapter_id,
                    "narrative_goal": narrative_goal,
                    "editorial_role": "context",
                    "claim_ids": [
                        _stable_id("clm_", stable, f"{block_pointer}/narration")
                    ],
                    "order": block_index,
                    "sequence_ids": [sequence_id],
                    "status": "ready",
                    "version": 1,
                }
            )
            sequences.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "sequence_id": sequence_id,
                    "chapter_id": chapter_id,
                    "beat_id": beat_id,
                    "narrative_goal": narrative_goal,
                    "editorial_role": "context",
                    "claim_ids": beats[-1]["claim_ids"],
                    "start_cue": _cue(
                        "start",
                        block_pointer,
                        f"v2-block:{stable}:start",
                        anchor_type="beat_boundary",
                    ),
                    "end_cue": _cue(
                        "end",
                        block_pointer,
                        _semantic_offset(
                            end_value, f"v2-block:{stable}:narration-end"
                        ),
                        anchor_type="beat_boundary"
                        if end_value in {None, "AUTO"}
                        else "semantic_marker",
                        relation="after",
                    ),
                    "base_shot": {
                        "asset_ref": sequence_assets[0],
                        "track_ref": video_track,
                        "editorial_purpose": purpose,
                    },
                    "edit_events": events,
                    "overlay_events": [],
                    "text_emphasis_events": [],
                    "audio_events": [],
                    "continuity_constraints": {
                        "preserve_screen_direction": False,
                        "avoid_visual_family_refs": [],
                    },
                    "fallback_policy": fallback_policy,
                    "status": "ready",
                    "version": 1,
                    "track_refs": [video_track, audio_track],
                }
            )

        chapter = {
            "schema_version": SCHEMA_VERSION,
            "chapter_id": chapter_id,
            "project_id": project_id,
            "title": "Migrated V2 Timeline",
            "narrative_goal": "Preserve the V2 narration-block order.",
            "order": 0,
            "beat_ids": [item["beat_id"] for item in beats],
            "status": "ready",
            "version": 1,
        }
        claim_ids = [
            claim for beat in beats for claim in beat["claim_ids"]
        ]
        return {
            "schema_version": SCHEMA_VERSION,
            "workspace_id": workspace_id,
            "layout": "aggregate",
            "project_metadata": {
                "project_id": project_id,
                "title": "Migrated V2 Timeline",
            },
            "domain": dict(domain),
            "documents": [],
            "render_profile": {
                "profile_id": "rnd_migrated_full_hd",
                "aspect_ratio": "16:9",
                "resolution_preset": "full_hd",
                "audio_layout": "stereo",
            },
            "status": "ready",
            "version": 1,
            "project": {
                "schema_version": SCHEMA_VERSION,
                "project_id": project_id,
                "title": "Migrated V2 Timeline",
                "created_at": EPOCH,
                "updated_at": EPOCH,
                "domain_id": domain["domain_id"],
                "domain_pack_version": domain["domain_pack_version"],
                "policy_snapshot_id": domain["policy_snapshot_id"],
                "status": "ready",
                "version": 1,
            },
            "research": {
                "source_refs": [
                    deterministic_token("src_", fingerprint, length=20)
                ],
                "claim_refs": claim_ids,
                "chronology_ref": deterministic_token(
                    "chronology_", fingerprint, length=16
                ),
            },
            "story": {
                "outline_ref": deterministic_token(
                    "outline_", fingerprint, length=16
                ),
                "chapters": [chapter],
                "beats": beats,
            },
            "sequences": sequences,
            "assets": assets,
            "artifacts": artifacts,
            "timing": {
                "narration_ref": "migration/source-narration.txt",
                "cue_catalog_ref": "migration/semantic-cues.json",
                "timing_contract_status": "semantic_references_only",
            },
            "tracks": {
                "schema_version": SCHEMA_VERSION,
                "tracks": [
                    {
                        "track_id": video_track,
                        "track_type": "video",
                        "role": "base",
                        "layer": 0,
                        "status": "ready",
                        "version": 1,
                    },
                    {
                        "track_id": audio_track,
                        "track_type": "audio",
                        "role": "narration",
                        "layer": 0,
                        "status": "ready",
                        "version": 1,
                    },
                ],
            },
        }

    def _visual(
        self,
        visual: Mapping[str, Any],
        pointer: str,
        block_index: int,
        visual_index: int,
        target_asset_index: int,
        project_id: str,
        sequence_id: str,
        video_track: str,
        builder: _MigrationBuilder,
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]] | None:
        visual_type = visual.get("type")
        if not isinstance(visual_type, str) or not visual_type:
            if "type" in visual:
                builder.account(
                    f"{pointer}/type",
                    visual_type,
                    None,
                    "INVALID_SOURCE",
                    "V2 visual renderer type",
                    "V3 asset type",
                    "Reject missing or non-string visual type.",
                    notes="Visual type is required by the active V2 contract.",
                )
            else:
                builder.issue(
                    "ERROR",
                    "MIGRATION_SOURCE_INVALID",
                    "Visual type is required by the active V2 contract.",
                    f"{pointer}/type",
                    None,
                    "INVALID_SOURCE",
                    "Add a supported visual type.",
                )
            return None

        target_asset_type = VISUAL_ASSET_TYPES.get(
            visual_type, "generated_media"
        )
        if visual_type in VISUAL_ASSET_TYPES:
            builder.account(
                f"{pointer}/type",
                visual_type,
                f"/assets/{target_asset_index}/asset_type",
                "NORMALIZED",
                "V2 visual renderer type",
                "V3 asset media type and edit event type",
                "Map the known V2 renderer type to canonical asset semantics.",
            )
        else:
            builder.account(
                f"{pointer}/type",
                visual_type,
                f"/assets/{target_asset_index}/asset_type",
                "UNSUPPORTED",
                "V2 visual renderer type",
                "V3 generated-media placeholder",
                "Represent the visual as review-required generated media.",
                notes=f"V2 visual type {visual_type!r} has no canonical V3 type.",
            )

        extra = visual.get("extra")
        if extra is None:
            extra = {}
        if not isinstance(extra, Mapping):
            builder.account(
                f"{pointer}/extra",
                extra,
                None,
                "INVALID_SOURCE",
                "V2 visual extension payload",
                "asset provenance",
                "Reject non-object extra payload.",
                notes="Visual extra must be an object.",
            )
            return None

        raw_asset_id = extra.get("asset_id")
        if raw_asset_id is not None and not isinstance(raw_asset_id, str):
            builder.account(
                f"{pointer}/extra/asset_id",
                raw_asset_id,
                None,
                "INVALID_SOURCE",
                "V2 visual asset identity",
                "V3 asset identity",
                "Reject non-string asset identity.",
                notes="extra.asset_id must be a string.",
            )
            raw_asset_id = None
        asset_id = _stable_id("ast_", raw_asset_id, pointer)
        artifact_id = _stable_id("art_", asset_id.removeprefix("ast_"), pointer)
        builder.register_id("assets", asset_id, f"{pointer}/extra/asset_id")
        builder.register_id(
            "artifacts", artifact_id, f"{pointer}/extra/asset_id"
        )
        if raw_asset_id is not None:
            builder.account(
                f"{pointer}/extra/asset_id",
                raw_asset_id,
                f"/assets/{target_asset_index}/asset_id",
                "NORMALIZED",
                "Stable V2 resolved asset identity",
                "V3 asset and artifact stable IDs",
                "Normalize to canonical ast_/art_ namespaces.",
                notes=f"Artifact ID is {artifact_id}.",
            )
        else:
            builder.account(
                "",
                None,
                f"/assets/{target_asset_index}/asset_id",
                "DERIVED",
                "Canonical visual source pointer",
                "V3 asset identity",
                "Derive from the canonical source pointer.",
            )

        expected_hash = extra.get("expected_sha256")
        if isinstance(expected_hash, str) and re.fullmatch(
            r"(?:sha256:)?[0-9a-fA-F]{64}", expected_hash
        ):
            content_hash = (
                expected_hash.lower()
                if expected_hash.startswith("sha256:")
                else "sha256:" + expected_hash.lower()
            )
            builder.account(
                f"{pointer}/extra/expected_sha256",
                expected_hash,
                f"/assets/{target_asset_index}/content_hash",
                "NORMALIZED",
                "Resolved media content fingerprint",
                "V3 asset and artifact content hash",
                "Normalize the SHA-256 prefix and case.",
            )
        elif expected_hash is not None:
            content_hash = canonical_fingerprint(visual)
            builder.account(
                f"{pointer}/extra/expected_sha256",
                expected_hash,
                f"/assets/{target_asset_index}/content_hash",
                "INVALID_SOURCE",
                "Resolved media content fingerprint",
                "V3 content hash",
                "Reject malformed content fingerprint.",
                notes="expected_sha256 must contain exactly 64 hexadecimal digits.",
            )
        else:
            content_hash = canonical_fingerprint(visual)
            builder.account(
                "",
                None,
                f"/assets/{target_asset_index}/content_hash",
                "DEFAULTED",
                "Missing V2 content fingerprint",
                "V3 review-only descriptor fingerprint",
                "Hash the canonical visual descriptor, not media bytes.",
                notes=(
                    "Source content hash is absent; the deterministic descriptor "
                    "fingerprint requires manual media verification."
                ),
            )

        origin_uri, availability, origin_pointer = self._origin(
            visual, extra, pointer, builder
        )
        event_type = VISUAL_EVENT_TYPES.get(visual_type, "cut")
        transition = visual.get("transition_in")
        if transition is not None:
            builder.account(
                f"{pointer}/transition_in",
                transition,
                f"/sequences/{block_index}/edit_events/{visual_index}/event_type",
                "NORMALIZED"
                if transition in {"hard_cut", "cut"}
                else "UNSUPPORTED",
                "V2 incoming visual transition",
                "V3 typed edit event",
                "Map hard cuts to cut; retain the visual event for other transitions.",
                notes=(
                    ""
                    if transition in {"hard_cut", "cut"}
                    else f"Transition {transition!r} has no canonical event mapping."
                ),
            )
            if transition not in {"hard_cut", "cut"}:
                event_type = "cut"

        start_value = visual.get("offset_start")
        start_pointer = f"{pointer}/offset_start"
        trigger = visual.get("trigger_cue") or visual.get(
            "narration_cue_start"
        )
        if trigger:
            trigger_field = (
                "trigger_cue"
                if visual.get("trigger_cue")
                else "narration_cue_start"
            )
            builder.account(
                f"{pointer}/{trigger_field}",
                trigger,
                f"/sequences/{block_index}/edit_events/{visual_index}/timing_ref",
                "NORMALIZED",
                "V2 narration cue anchor",
                "V3 semantic cue",
                "Preserve narration cue text as the semantic anchor.",
            )
            anchor_ref = str(trigger)
            anchor_type = "narration_phrase"
        else:
            anchor_ref = _semantic_offset(
                start_value, f"v2-visual:{block_index}:{visual_index}:start"
            )
            anchor_type = "semantic_marker"
        if "offset_start" in visual:
            builder.account(
                start_pointer,
                start_value,
                f"/sequences/{block_index}/edit_events/{visual_index}/timing_ref",
                "NORMALIZED"
                if start_value != "AUTO"
                else "DEFAULTED",
                "V2 block-relative visual start",
                "V3 semantic event cue",
                "Encode explicit offsets as semantic markers.",
                notes=(
                    "AUTO resolves to deterministic visual order."
                    if start_value == "AUTO"
                    else ""
                ),
            )
        if "offset_end" in visual:
            end_value = visual["offset_end"]
            builder.account(
                f"{pointer}/offset_end",
                end_value,
                f"/sequences/{block_index}/edit_events/{visual_index}",
                "DEFAULTED" if end_value == "AUTO" else "NORMALIZED",
                "V2 block-relative visual end",
                "V3 semantic edit boundary",
                "Preserve an explicit semantic boundary or resolve AUTO by order.",
                notes=(
                    "AUTO has no frame value in the Phase 1 semantic cue model."
                    if end_value == "AUTO"
                    else "The following event/start or sequence end preserves the boundary."
                ),
            )

        parameters: dict[str, Any] = {}
        if event_type == "text_reveal" and isinstance(
            visual.get("main_text"), str
        ):
            parameters["text"] = visual["main_text"]
            builder.account(
                f"{pointer}/main_text",
                visual["main_text"],
                f"/sequences/{block_index}/edit_events/{visual_index}/parameters/text",
                "EXACT",
                "V2 primary on-screen text",
                "V3 event text parameter",
                "Copy text exactly.",
            )

        event = {
            "schema_version": SCHEMA_VERSION,
            "event_id": deterministic_token(
                "evt_", pointer, asset_id, length=20
            ),
            "event_type": event_type,
            "timing_ref": _cue(
                "visual",
                pointer,
                anchor_ref,
                anchor_type=anchor_type,
            ),
            "track_ref": video_track,
            "target": {"target_type": "asset", "target_id": asset_id},
            "status": "ready",
            "version": 1,
            "parameters": parameters,
            "extension_metadata": {},
        }
        source_ref = deterministic_token(
            "src_", origin_pointer or pointer, origin_uri, length=20
        )
        mime_type = {
            "video": "video/mp4",
            "audio": "audio/wav",
            "document": "application/octet-stream",
            "chart_data": "application/json",
            "generated_media": "application/octet-stream",
        }.get(target_asset_type, "application/octet-stream")
        approved = extra.get("asset_mode") == "locked_local"
        if "asset_mode" in extra:
            builder.account(
                f"{pointer}/extra/asset_mode",
                extra["asset_mode"],
                f"/assets/{target_asset_index}/availability",
                "NORMALIZED",
                "V2 resolved-asset mode",
                "V3 availability and review state",
                "Map locked_local to local approved media.",
            )
        asset = {
            "schema_version": SCHEMA_VERSION,
            "asset_id": asset_id,
            "asset_type": target_asset_type,
            "editorial_role": "visual_support",
            "provenance": {
                "source_ref": source_ref,
                "origin_uri": origin_uri,
                "license_state": "internal" if approved else "unknown",
            },
            "content_hash": content_hash,
            "media_metadata": {
                "mime_type": mime_type,
                "duration_hint": "unknown",
                "has_audio": target_asset_type == "audio",
            },
            "availability": availability,
            "review_state": "approved" if approved else "needs_review",
            "artifact_ref": artifact_id,
            "status": "approved" if approved else "ready",
            "version": 1,
        }
        artifact = {
            "schema_version": SCHEMA_VERSION,
            "artifact_id": artifact_id,
            "artifact_type": "source_media",
            "project_id": project_id,
            "sequence_id": sequence_id,
            "created_at": EPOCH,
            "last_accessed_at": EPOCH,
            "content_hash": content_hash,
            "size_bytes": 0,
            "retention_class": "provenance",
            "dependency_ids": [],
            "locked": approved,
            "pinned": False,
            "approved": approved,
            "cleanup_candidate": False,
            "producer": "v2-to-v3-migrator",
            "producer_version": MIGRATION_VERSION,
            "job_id": None,
            "status": "approved" if approved else "ready",
            "version": 1,
        }
        return asset, artifact, event

    def _origin(
        self,
        visual: Mapping[str, Any],
        extra: Mapping[str, Any],
        pointer: str,
        builder: _MigrationBuilder,
    ) -> tuple[str, str, str]:
        candidates = (
            ("url", visual.get("url")),
            ("selected_asset_url", visual.get("selected_asset_url")),
            ("extra/resolved_path", extra.get("resolved_path")),
            ("query", visual.get("query")),
        )
        for field_name, value in candidates:
            if not isinstance(value, str) or not value:
                continue
            source_pointer = f"{pointer}/{field_name}"
            if inspect_source_value(
                source_pointer, value, uri_reference=True
            ) is not None:
                builder.account(
                    source_pointer,
                    value,
                    None,
                    "DROPPED",
                    "Security-sensitive V2 source reference",
                    "redacted provenance",
                    "Redact the value completely.",
                    notes="Secret-like source data was not copied to V3 output.",
                    code="MIGRATION_SECRET_REDACTED",
                    severity="ERROR",
                    action="Remove and rotate the secret before retrying.",
                )
                continue
            normalized = value.replace("\\", "/")
            if ".." in normalized.split("/"):
                builder.account(
                    source_pointer,
                    value,
                    None,
                    "AMBIGUOUS",
                    "V2 source media reference",
                    "V3 asset provenance URI",
                    "Reject path traversal instead of rewriting it.",
                    notes="Source media reference contains a parent traversal segment.",
                    code="MIGRATION_REFERENCE_AMBIGUOUS",
                    severity="ERROR",
                    action="Provide a confined relative path or absolute URI.",
                )
                continue
            if re.match(r"^[A-Za-z]:[\\/]", value):
                uri = "urn:kurgu:v2-local:" + quote(normalized, safe="/")
                availability = "local"
            elif re.match(r"^[a-z][a-z0-9+.-]*:", value, re.IGNORECASE):
                uri = value
                availability = (
                    "remote"
                    if value.lower().startswith(("http:", "https:"))
                    else "local"
                )
            elif field_name == "query":
                uri = "urn:kurgu:v2-query:" + quote(value, safe="")
                availability = "remote"
            else:
                uri = "urn:kurgu:v2-local:" + quote(normalized, safe="/")
                availability = "local"
            builder.account(
                source_pointer,
                value,
                None,
                "NORMALIZED",
                "V2 visual source/provenance reference",
                "V3 asset provenance origin_uri",
                "Normalize local paths/search terms to a portable URN; retain URIs.",
                notes=f"Stored as {uri}.",
            )
            return uri, availability, source_pointer
        return (
            "urn:kurgu:v2-source:" + deterministic_token("", pointer, length=24),
            "missing",
            pointer,
        )

    def _account_remaining(
        self,
        source: Mapping[str, Any],
        builder: _MigrationBuilder,
    ) -> None:
        for pointer, value in _leaf_items(source):
            if pointer in builder.accounted:
                continue
            if inspect_source_value(pointer, value) is not None:
                builder.account(
                    pointer,
                    value,
                    None,
                    "DROPPED",
                    "Security-sensitive V2 source value",
                    "redacted value",
                    "Redact the value completely.",
                    notes="Secret-like source data was not copied to V3 output.",
                    code="MIGRATION_SECRET_REDACTED",
                    severity="ERROR",
                    action="Remove and rotate the secret before retrying.",
                )
                continue
            parts = pointer.strip("/").split("/")
            if len(parts) == 1 and parts[0] in ROOT_FIELDS:
                builder.account(
                    pointer,
                    value,
                    None,
                    "UNSUPPORTED",
                    "V2 root runtime/editorial option",
                    "migration report",
                    "Record without inventing a V3 core field.",
                    notes=f"V2 root field {_field(pointer)!r} has no V3 mapping.",
                )
                continue
            if (
                len(parts) == 2
                and parts[0] == "bgm"
                and _field(pointer) in BGM_FIELDS
            ):
                builder.account(
                    pointer,
                    value,
                    None,
                    "UNSUPPORTED",
                    f"V2 background-music {parts[1]} setting",
                    "migration report",
                    "Record without inventing an audio asset or timing event.",
                    notes=(
                        "V2 BGM configuration has no Phase 1 canonical "
                        "asset/provenance contract."
                    ),
                )
                continue
            if len(parts) >= 3 and parts[0] == "blocks":
                if parts[2] in BLOCK_FIELDS and (
                    len(parts) == 3 or parts[2] != "visuals"
                ):
                    classification = (
                        "DROPPED"
                        if parts[2]
                        in {"pause_before", "pause_after", "bgm_drop"}
                        else "UNSUPPORTED"
                    )
                    builder.account(
                        pointer,
                        value,
                        None,
                        classification,
                        f"V2 block {parts[2]} setting",
                        "migration report",
                        "Record without inventing timing/renderer state.",
                        notes=(
                            f"V2 block field {parts[2]!r} has no Phase 1 "
                            "canonical destination."
                        ),
                    )
                    continue
                if (
                    len(parts) >= 6
                    and parts[2] == "visuals"
                    and parts[4] == "extra"
                ):
                    builder.account(
                        pointer,
                        value,
                        None,
                        "UNSUPPORTED",
                        "Open-ended V2 visual extension value",
                        "migration report",
                        "Account for the extension without copying arbitrary payload.",
                        notes=(
                            f"V2 extra field {parts[5]!r} has no reviewed V3 mapping."
                        ),
                    )
                    continue
                if (
                    len(parts) == 6
                    and parts[2] == "visuals"
                    and parts[4] == "sfx"
                    and _field(pointer) in SFX_FIELDS
                ):
                    builder.account(
                        pointer,
                        value,
                        None,
                        "UNSUPPORTED",
                        f"V2 sound-effect {_field(pointer)} setting",
                        "migration report",
                        "Record without inventing an audio asset or timing event.",
                        notes=(
                            "V2 SFX configuration has no Phase 1 canonical "
                            "asset/provenance contract."
                        ),
                    )
                    continue
                if (
                    len(parts) >= 5
                    and parts[2] == "visuals"
                    and parts[4] != "sfx"
                ):
                    visual_field = parts[4]
                    if visual_field in VISUAL_FIELDS:
                        classification = (
                            "DROPPED"
                            if visual_field
                            in {
                                "clip_start",
                                "clip_end",
                                "zoom",
                                "scroll_duration",
                                "highlight_target",
                                "background_style",
                                "accent_animation",
                                "max_height",
                                "crop_mode",
                                "fit_mode",
                                "transition_out",
                                "min_duration",
                                "max_duration",
                                "preferred_duration",
                                "subtitle_policy",
                            }
                            else "UNSUPPORTED"
                        )
                        builder.account(
                            pointer,
                            value,
                            None,
                            classification,
                            f"V2 visual {visual_field} setting",
                            "migration report",
                            "Record without inventing renderer/timing contracts.",
                            notes=(
                                f"V2 visual field {visual_field!r} has no "
                                "Phase 1 canonical destination."
                            ),
                        )
                        continue
            builder.account(
                pointer,
                value,
                None,
                "INVALID_SOURCE",
                "Unrecognized V2 source field",
                "none",
                "Reject the unaccounted source leaf.",
                notes=f"No production mapping rule accounts for {pointer}.",
                code="MIGRATION_UNACCOUNTED_SOURCE_FIELD",
                severity="ERROR",
                action="Add a reviewed migration rule before retrying.",
            )

    def _outcome(
        self,
        source: Any,
        source_fingerprint: str,
        options: MigrationOptions,
        builder: _MigrationBuilder,
        workspace: Mapping[str, Any] | None,
        target_issues: list[dict[str, str]],
        source_version: str = "unknown",
    ) -> MigrationOutcome:
        errors = any(issue.severity == "ERROR" for issue in builder.issues)
        blocking_classes = (
            STRICT_BLOCKING_CLASSIFICATIONS
            if options.mode == "strict"
            else BLOCKING_CLASSIFICATIONS
        )
        policy_rejected = any(
            issue.classification in blocking_classes
            for issue in builder.issues
        )
        failed = errors or policy_rejected or workspace is None
        mappings = sorted(
            (item.to_dict() for item in builder.mappings),
            key=lambda item: (
                item["source_pointer"],
                item["destination_pointer"] or "",
                item["mapping_id"],
            ),
        )
        issues = sorted(
            (item.to_dict() for item in builder.issues),
            key=lambda item: (
                {"ERROR": 0, "WARNING": 1, "INFO": 2}.get(
                    item["severity"], 3
                ),
                item["source_pointer"],
                item["code"],
                item["issue_id"],
            ),
        )
        classification_counts = {
            name: sum(
                item["classification"] == name for item in mappings
            )
            for name in CLASSIFICATIONS
        }
        severity_counts = {
            name: sum(item["severity"] == name for item in issues)
            for name in SEVERITIES
        }
        lossy = any(
            item["classification"]
            in {"DEFAULTED", "DROPPED", "UNSUPPORTED", "AMBIGUOUS", "INVALID_SOURCE"}
            for item in mappings
        ) or bool(issues)
        status = (
            "FAILED"
            if failed
            else "SUCCESS_WITH_LOSS"
            if lossy
            else "SUCCESS"
        )
        target_fingerprint = (
            canonical_fingerprint(workspace)
            if not failed and workspace is not None
            else None
        )
        workspace_id = (
            str(workspace["workspace_id"])
            if not failed and workspace is not None
            else None
        )
        unknown_fields = sorted(
            {
                item["source_pointer"]
                for item in issues
                if item["code"] == "MIGRATION_UNACCOUNTED_SOURCE_FIELD"
            }
        )
        result: dict[str, Any] = {
            "source_schema_version": source_version,
            "target_schema_version": SCHEMA_VERSION,
            "source_path": options.source_path,
            "target_path": options.target_path,
            "lossy": lossy,
            "unknown_fields": unknown_fields,
            "issues": issues,
            "migration_version": MIGRATION_VERSION,
            "migration_id": deterministic_token(
                "mig_",
                source_fingerprint,
                options.mode,
                options.resolution_mode,
                options.domain_id,
                options.domain_pack_version,
            ),
            "source_format": "kurgu-v2-timeline",
            "target_format": "kurgu-v3-workspace",
            "mode": options.mode,
            "resolution_mode": options.resolution_mode,
            "source_fingerprint": source_fingerprint,
            "target_fingerprint": target_fingerprint,
            "status": status,
            "workspace_id": workspace_id,
            "counts": {
                "classifications": classification_counts,
                "severities": severity_counts,
            },
            "mappings": mappings,
            "validation": {
                "workspace_schema_valid": not failed
                and workspace is not None
                and not target_issues,
                "workspace_loader_valid": not failed
                and workspace is not None
                and not target_issues,
                "migration_result_schema_valid": True,
                "target_issues": target_issues,
            },
        }
        result_validation = self.catalog.validate(
            result, "migration_result.schema.json", "<migration-result>"
        )
        if not result_validation.is_valid:
            details = "; ".join(
                f"{item.code} {item.json_pointer}: {item.message}"
                for item in result_validation.issues
            )
            raise RuntimeError(
                f"Internal migration result contract violation: {details}"
            )
        published_workspace = None if failed else workspace
        return MigrationOutcome(published_workspace, result)


def migrate(
    source: Mapping[str, Any],
    *,
    catalog: SchemaCatalog,
    options: MigrationOptions | None = None,
) -> MigrationOutcome:
    return V2ToV3Migrator(catalog).migrate(source, options)
