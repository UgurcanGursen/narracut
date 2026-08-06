"""Phase 12 immutable continuity and executable editorial-plan compiler."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from engine.acquisition import AssetCatalogV1, AssetRecordV1
from engine.audio_director import AudioDirectionPlanV1
from engine.contracts._canonical_json import encode_canonical_json_bytes
from engine.contracts.domain import policy_snapshot_hash
from engine.contracts.models import DomainPolicySnapshot
from engine.contracts.edl import CueWordRange, SourceDescriptor, TimelineTrack, VideoEditIntent, VideoEdlArtifact, compile_video_edl
from engine.planner.contracts import PlannerContractError, validate_record
from engine.rendering.template_contract import TemplateDefinition, TemplateId, template_policy_from_policy_snapshot
from engine.rendering.template_registry import TemplateRegistry
from engine.visualization import VisualizationArtifactV1


EDITORIAL_INTEGRATION_POLICY_V1 = "EDITORIAL-INTEGRATION-POLICY-V1"
EXECUTABLE_EDITORIAL_PLAN_V1 = "PHASE12-EXECUTABLE-EDITORIAL-PLAN-V1"


class EditorialIntegrationError(ValueError):
    pass


def _fail(code: str) -> None: raise EditorialIntegrationError(code)
def _hash(value: object) -> str: return "sha256:" + hashlib.sha256(encode_canonical_json_bytes(value)).hexdigest()
def _hash_ok(value: object) -> bool: return type(value) is str and len(value) == 71 and value.startswith("sha256:") and all(x in "0123456789abcdef" for x in value[7:])
def _id(value: object, prefix: str) -> bool: return type(value) is str and value.startswith(prefix) and len(value) > len(prefix)
def _pair(value: object, prefix: str) -> tuple[str, str]:
    if type(value) is not tuple or len(value) != 2 or not _id(value[0], prefix) or not _hash_ok(value[1]): _fail("EDITORIAL_PAIR_INVALID")
    return value
def _tokens(value: object) -> tuple[str, ...]:
    if type(value) is not tuple or not value or len(value) != len(set(value)) or any(type(x) is not str or not x or x != x.strip() or x != x.lower() for x in value): _fail("EDITORIAL_POLICY_INVALID")
    return value


@dataclass(frozen=True)
class EditorialIntegrationPolicyV1:
    policy_snapshot_id: str; policy_snapshot_hash: str; max_consecutive_template_uses: int; max_consecutive_visual_family_uses: int; allowed_execution_modes: tuple[str, ...]; allowed_pacing_roles: tuple[str, ...]
    @property
    def policy_hash(self) -> str:
        return _hash({"policy_snapshot_id": self.policy_snapshot_id, "policy_snapshot_hash": self.policy_snapshot_hash, "max_consecutive_template_uses": self.max_consecutive_template_uses, "max_consecutive_visual_family_uses": self.max_consecutive_visual_family_uses, "allowed_execution_modes": list(self.allowed_execution_modes), "allowed_pacing_roles": list(self.allowed_pacing_roles)})


def editorial_integration_policy_from_snapshot(snapshot: DomainPolicySnapshot) -> EditorialIntegrationPolicyV1:
    if type(snapshot) is not DomainPolicySnapshot or not snapshot.immutable: _fail("EDITORIAL_POLICY_SNAPSHOT_INVALID")
    raw_snapshot = {field: getattr(snapshot, field) for field in snapshot.__dataclass_fields__}
    if snapshot.canonical_hash != policy_snapshot_hash(raw_snapshot): _fail("EDITORIAL_POLICY_SNAPSHOT_INVALID")
    bundles = snapshot.resolved_policy.get("policy_bundles") if type(snapshot.resolved_policy) is dict else None
    matches = [bundle["policy"]["editorial"]["editorial_integration_policy"] for bundle in bundles or () if type(bundle) is dict and type(bundle.get("policy")) is dict and type(bundle["policy"].get("editorial")) is dict and "editorial_integration_policy" in bundle["policy"]["editorial"]]
    required = {"policy_version", "max_consecutive_template_uses", "max_consecutive_visual_family_uses", "allowed_execution_modes", "allowed_pacing_roles"}
    if len(matches) != 1 or type(matches[0]) is not dict or set(matches[0]) != required or matches[0]["policy_version"] != EDITORIAL_INTEGRATION_POLICY_V1: _fail("EDITORIAL_POLICY_MISSING")
    raw = matches[0]; modes, roles = _tokens(tuple(raw["allowed_execution_modes"])) if type(raw["allowed_execution_modes"]) is list else _fail("EDITORIAL_POLICY_INVALID"), _tokens(tuple(raw["allowed_pacing_roles"])) if type(raw["allowed_pacing_roles"]) is list else _fail("EDITORIAL_POLICY_INVALID")
    if set(modes) != {"asset_only", "asset_with_visualization"} or any(type(raw[x]) is not int or raw[x] < 1 for x in ("max_consecutive_template_uses", "max_consecutive_visual_family_uses")): _fail("EDITORIAL_POLICY_INVALID")
    return EditorialIntegrationPolicyV1(snapshot.snapshot_id, snapshot.canonical_hash, raw["max_consecutive_template_uses"], raw["max_consecutive_visual_family_uses"], modes, roles)


@dataclass(frozen=True)
class TemplateCapabilityV1:
    capability_id: str; capability_hash: str; template_id: TemplateId; template_version: str; editorial_roles: tuple[str, ...]; policy_snapshot_id: str; policy_snapshot_hash: str


def template_capabilities_from_snapshot(snapshot: DomainPolicySnapshot) -> tuple[TemplateCapabilityV1, ...]:
    policy = template_policy_from_policy_snapshot(snapshot); registry = TemplateRegistry(); result = []
    for definition in registry.definitions():
        if definition.template_id in policy.banned_template_ids: continue
        body = {"template_id": definition.template_id.value, "template_version": definition.template_version, "editorial_roles": list(definition.supported_editorial_roles), "policy_snapshot_id": snapshot.snapshot_id, "policy_snapshot_hash": snapshot.canonical_hash}
        digest = _hash(body); result.append(TemplateCapabilityV1("cap_" + digest[7:27], digest, definition.template_id, definition.template_version, definition.supported_editorial_roles, snapshot.snapshot_id, snapshot.canonical_hash))
    return tuple(result)


def _validate_capability(value: TemplateCapabilityV1, policy: EditorialIntegrationPolicyV1) -> None:
    if type(value) is not TemplateCapabilityV1 or (value.policy_snapshot_id, value.policy_snapshot_hash) != (policy.policy_snapshot_id, policy.policy_snapshot_hash) or type(value.template_id) is not TemplateId or type(value.template_version) is not str or type(value.editorial_roles) is not tuple:
        _fail("TEMPLATE_CAPABILITY_INVALID")
    definition = next((item for item in TemplateRegistry().definitions() if item.template_id is value.template_id), None)
    body = {"template_id": value.template_id.value, "template_version": value.template_version, "editorial_roles": list(value.editorial_roles), "policy_snapshot_id": value.policy_snapshot_id, "policy_snapshot_hash": value.policy_snapshot_hash}
    digest = _hash(body)
    if definition is None or (value.template_version, value.editorial_roles) != (definition.template_version, definition.supported_editorial_roles) or (value.capability_id, value.capability_hash) != ("cap_" + digest[7:27], digest): _fail("TEMPLATE_CAPABILITY_INVALID")


@dataclass(frozen=True)
class ApprovedAssetSelectionV1:
    planner_asset_brief_pair: tuple[str, str]; asset_id: str; asset_hash: str; range_id: str; range_hash: str; crop_left_millionths: int; crop_top_millionths: int; crop_right_millionths: int; crop_bottom_millionths: int; approval_provenance: str
    def data(self, *, asset: AssetRecordV1) -> dict[str, object]:
        brief = _pair(self.planner_asset_brief_pair, "pbrief_")
        crop = (self.crop_left_millionths, self.crop_top_millionths, self.crop_right_millionths, self.crop_bottom_millionths)
        if type(asset) is not AssetRecordV1 or (self.asset_id, self.asset_hash) != (asset.asset_id, asset.asset_hash) or not _id(self.range_id, "rng_") or not _hash_ok(self.range_hash) or any(type(x) is not int or not 0 <= x <= 1_000_000 for x in crop) or not crop[0] < crop[2] or not crop[1] < crop[3] or self.approval_provenance not in {"replay_approved", "manual_approved"} or not any((row.get("range_id"), row.get("range_hash")) == (self.range_id, self.range_hash) for row in asset.selected_ranges): _fail("APPROVED_ASSET_SELECTION_INVALID")
        body = {"planner_asset_brief_id_hash": list(brief), "asset_id": self.asset_id, "asset_hash": self.asset_hash, "range_id": self.range_id, "range_hash": self.range_hash, "crop": list(crop), "approval_provenance": self.approval_provenance}; digest = _hash(body)
        return {"selection_id": "asel_" + digest[7:27], "selection_hash": digest, **body}


@dataclass(frozen=True)
class ContinuityStateV1:
    sequence_plan_id: str; position: int; visual_family_id: str; template_capability_id: str; visualization_id: str | None; audio_intensity: str
    def data(self, *, previous: dict[str, object] | None, policy: EditorialIntegrationPolicyV1) -> dict[str, object]:
        if not _id(self.sequence_plan_id, "splan_") or type(self.position) is not int or self.position < 0 or not _id(self.visual_family_id, "fam_") or not _id(self.template_capability_id, "cap_") or (self.visualization_id is not None and not _id(self.visualization_id, "viz_")) or self.audio_intensity not in {"low", "medium", "high"}: _fail("CONTINUITY_STATE_INVALID")
        if previous is not None and (previous["position"] != self.position - 1): _fail("CONTINUITY_STATE_ORDER_INVALID")
        template_run = 1 if previous is None or previous["template_capability_id"] != self.template_capability_id else int(previous["template_run"]) + 1
        family_run = 1 if previous is None or previous["visual_family_id"] != self.visual_family_id else int(previous["family_run"]) + 1
        if template_run > policy.max_consecutive_template_uses or family_run > policy.max_consecutive_visual_family_uses: _fail("CONTINUITY_REUSE_DENIED")
        body = {"sequence_plan_id": self.sequence_plan_id, "position": self.position, "visual_family_id": self.visual_family_id, "template_capability_id": self.template_capability_id, "visualization_id": self.visualization_id, "audio_intensity": self.audio_intensity, "template_run": template_run, "family_run": family_run}; digest = _hash(body)
        return {"continuity_state_id": "cont_" + digest[7:27], "continuity_state_hash": digest, **body}


@dataclass(frozen=True)
class ExecutableEditorialPlanV1:
    project_id: str; assembly_request_pair: tuple[str, str]; policy: EditorialIntegrationPolicyV1; sequence_rows: tuple[dict[str, object], ...]
    def data(self) -> dict[str, object]:
        request = _pair(self.assembly_request_pair, "pareq_")
        if not _id(self.project_id, "prj_") or type(self.sequence_rows) is not tuple or not self.sequence_rows or any(type(row) is not dict for row in self.sequence_rows): _fail("EXECUTABLE_EDITORIAL_PLAN_INVALID")
        body = {"schema_version": EXECUTABLE_EDITORIAL_PLAN_V1, "project_id": self.project_id, "assembly_request_id_hash": list(request), "policy_snapshot_id": self.policy.policy_snapshot_id, "policy_snapshot_hash": self.policy.policy_snapshot_hash, "editorial_integration_policy_hash": self.policy.policy_hash, "sequences": list(self.sequence_rows)}; digest = _hash(body)
        return {"executable_editorial_plan_id": "eeplan_" + digest[7:27], "executable_editorial_plan_hash": digest, **body}


class EditorialIntegrationCompiler:
    """Binds accepted cross-phase decisions; it does not schedule media."""
    def compile(self, *, project_id: str, assembly_request: dict[str, object], policy: EditorialIntegrationPolicyV1, sequence_plans: tuple[dict[str, object], ...], catalog: AssetCatalogV1, selections: tuple[ApprovedAssetSelectionV1, ...], capabilities: tuple[TemplateCapabilityV1, ...], audio_plan: AudioDirectionPlanV1, chapter_audio_direction_pairs: tuple[tuple[str, str], ...], visualizations: tuple[VisualizationArtifactV1 | None, ...]) -> ExecutableEditorialPlanV1:
        if type(assembly_request) is not dict or type(policy) is not EditorialIntegrationPolicyV1 or type(sequence_plans) is not tuple or type(catalog) is not AssetCatalogV1 or type(selections) is not tuple or type(capabilities) is not tuple or type(audio_plan) is not AudioDirectionPlanV1 or type(chapter_audio_direction_pairs) is not tuple or type(visualizations) is not tuple or len(sequence_plans) != len(visualizations) or len(sequence_plans) != len(chapter_audio_direction_pairs): _fail("EDITORIAL_INTEGRATION_INPUT_INVALID")
        if (catalog.project_id, catalog.policy_snapshot_id, catalog.policy_snapshot_hash) != (project_id, policy.policy_snapshot_id, policy.policy_snapshot_hash): _fail("EDITORIAL_INTEGRATION_POLICY_MISMATCH")
        audio = audio_plan.data()
        if (audio["project_id"], audio["policy_snapshot_id"], audio["policy_snapshot_hash"]) != (project_id, policy.policy_snapshot_id, policy.policy_snapshot_hash): _fail("EDITORIAL_INTEGRATION_POLICY_MISMATCH")
        if set(assembly_request) != {"request_id", "request_hash", "schema_version", "project_id", "policy_snapshot_id", "policy_snapshot_hash", "ordered_sequence_plan_id_hash_pairs", "claim_evidence_snapshot_id_hash", "asset_catalog_snapshot_id_hash", "template_capability_snapshot_id_hash", "continuity_snapshot_id_hash"} or (assembly_request["project_id"], assembly_request["policy_snapshot_id"], assembly_request["policy_snapshot_hash"]) != (project_id, policy.policy_snapshot_id, policy.policy_snapshot_hash): _fail("EDITORIAL_ASSEMBLY_INVALID")
        request_body = {key: value for key, value in assembly_request.items() if key not in {"request_id", "request_hash"}}
        request_digest = _hash(request_body)
        if (assembly_request["request_id"], assembly_request["request_hash"]) != ("pareq_" + request_digest[7:27], request_digest): _fail("EDITORIAL_ASSEMBLY_INVALID")
        request_pair = (assembly_request["request_id"], assembly_request["request_hash"])
        _pair(request_pair, "pareq_")
        assets = {(item.asset_id, item.asset_hash): item for item in catalog.records}; caps = {(item.capability_id, item.capability_hash): item for item in capabilities}
        if len(assets) != len(catalog.records) or len(caps) != len(capabilities): _fail("EDITORIAL_INTEGRATION_INPUT_INVALID")
        for item in capabilities: _validate_capability(item, policy)
        if tuple(tuple(item) for item in assembly_request["ordered_sequence_plan_id_hash_pairs"]) != tuple((plan.get("sequence_plan_id"), plan.get("sequence_plan_hash")) for plan in sequence_plans): _fail("EDITORIAL_SEQUENCE_ORDER_INVALID")
        selection_by_brief = {item.planner_asset_brief_pair: item for item in selections}
        if len(selection_by_brief) != len(selections): _fail("APPROVED_ASSET_SELECTION_INVALID")
        audio_directions = {(item["chapter_audio_direction_id"], item["chapter_audio_direction_hash"]): item for item in audio["chapter_directions"]}
        rows: list[dict[str, object]] = []; previous = None
        for position, (plan, visualization, direction_pair) in enumerate(zip(sequence_plans, visualizations, chapter_audio_direction_pairs, strict=True)):
            try: sequence_id, sequence_hash, record = validate_record("sequence_plan", plan)
            except PlannerContractError: _fail("EDITORIAL_SEQUENCE_PLAN_INVALID")
            if (record["project_id"], record["policy_snapshot_id"], record["policy_snapshot_hash"]) != (project_id, policy.policy_snapshot_id, policy.policy_snapshot_hash): _fail("EDITORIAL_SEQUENCE_PLAN_INVALID")
            briefs = tuple(map(tuple, record["planner_asset_brief_id_hash_pairs"])); selected = []
            for brief in briefs:
                selection = selection_by_brief.get(brief)
                if selection is None or (selection.asset_id, selection.asset_hash) not in assets: _fail("APPROVED_ASSET_SELECTION_MISSING")
                selected.append(selection.data(asset=assets[(selection.asset_id, selection.asset_hash)]))
            if not selected: _fail("APPROVED_ASSET_SELECTION_MISSING")
            capability_pairs = tuple(map(tuple, record["template_capability_id_hash_pairs"])); available = [caps[pair] for pair in capability_pairs if pair in caps]
            if not available: _fail("TEMPLATE_CAPABILITY_MISSING")
            capability = sorted(available, key=lambda item: item.capability_id)[0]
            if visualization is not None and (type(visualization) is not VisualizationArtifactV1 or (visualization.policy.policy_snapshot_id, visualization.policy.policy_snapshot_hash) != (policy.policy_snapshot_id, policy.policy_snapshot_hash)) : _fail("VISUALIZATION_BINDING_INVALID")
            mode = "asset_with_visualization" if visualization is not None else "asset_only"
            if mode not in policy.allowed_execution_modes: _fail("EDITORIAL_EXECUTION_MODE_DENIED")
            direction = audio_directions.get(_pair(direction_pair, "cad_"))
            if direction is None: _fail("AUDIO_DIRECTION_BINDING_INVALID")
            state = ContinuityStateV1(sequence_id, position, assets[(selected[0]["asset_id"], selected[0]["asset_hash"])].visual_family_id, capability.capability_id, None if visualization is None else visualization.visualization_id, str(direction["music_intensity"])).data(previous=previous, policy=policy)
            row = {"sequence_plan_id": sequence_id, "sequence_plan_hash": sequence_hash, "approved_asset_selections": selected, "template_capability_id_hash": [capability.capability_id, capability.capability_hash], "visualization_id_hash": None if visualization is None else [visualization.visualization_id, visualization.visualization_hash], "chapter_audio_direction_id_hash": [direction["chapter_audio_direction_id"], direction["chapter_audio_direction_hash"]], "incoming_continuity_state_id_hash": None if previous is None else [previous["continuity_state_id"], previous["continuity_state_hash"]], "outgoing_continuity_state_id_hash": [state["continuity_state_id"], state["continuity_state_hash"]], "execution_mode": mode}
            digest = _hash(row); rows.append({"executable_sequence_id": "eseq_" + digest[7:27], "executable_sequence_hash": digest, **row}); previous = state
        return ExecutableEditorialPlanV1(project_id, request_pair, policy, tuple(rows))


def canonical_executable_editorial_plan_json(plan: ExecutableEditorialPlanV1) -> bytes:
    if type(plan) is not ExecutableEditorialPlanV1: _fail("EXECUTABLE_EDITORIAL_PLAN_INVALID")
    return encode_canonical_json_bytes(plan.data())


def compile_phase3_video_edl_from_execution(*, execution: dict[str, object], cue: CueWordRange, source: SourceDescriptor, caption_groups: object, emphasis_events: object, word_to_frame: object, caption_preview: object, v5_v6_collision_report: object, fps_numerator: int, fps_denominator: int) -> VideoEdlArtifact:
    """Compile one explicit approved execution through the existing Phase 3 compiler."""
    if type(execution) is not dict or type(cue) is not CueWordRange or type(source) is not SourceDescriptor:
        _fail("PHASE3_HANDOFF_INVALID")
    required = {"executable_sequence_id", "executable_sequence_hash", "sequence_plan_id", "sequence_plan_hash", "approved_asset_selections", "template_capability_id_hash", "visualization_id_hash", "chapter_audio_direction_id_hash", "incoming_continuity_state_id_hash", "outgoing_continuity_state_id_hash", "execution_mode"}
    if set(execution) != required or not _id(execution["executable_sequence_id"], "eseq_") or not _hash_ok(execution["executable_sequence_hash"]) or type(execution["approved_asset_selections"]) is not list or not execution["approved_asset_selections"]:
        _fail("PHASE3_HANDOFF_INVALID")
    selected = execution["approved_asset_selections"][0]
    if type(selected) is not dict or source.source_ref != selected.get("asset_id") or [source.crop_left_millionths, source.crop_top_millionths, source.crop_right_millionths, source.crop_bottom_millionths] != selected.get("crop"):
        _fail("PHASE3_HANDOFF_INVALID")
    intent = VideoEditIntent("phase12_" + execution["executable_sequence_id"], TimelineTrack.V1, cue, source, "phase12_execution", 0)
    try:
        return compile_video_edl(intents=(intent,), sequence_id=execution["executable_sequence_id"], sequence_start_word_id=cue.start_word_id, sequence_end_word_id=cue.end_word_id, caption_groups=caption_groups, emphasis_events=emphasis_events, word_to_frame=word_to_frame, caption_preview=caption_preview, v5_v6_collision_report=v5_v6_collision_report, fps_numerator=fps_numerator, fps_denominator=fps_denominator)
    except Exception as exc:
        if exc.__class__.__module__.startswith("engine.contracts"):
            raise
        _fail("PHASE3_HANDOFF_INVALID")
