"""REPLAY-only Phase 5 core template contract checks."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import shutil
from pathlib import Path

import pytest
from PIL import Image

from engine.contracts import DomainPackRegistry, DomainPolicyResolver, SchemaCatalog
from engine.contracts.word_to_frame import TemporalFrameRate, compile_word_to_frame, serialize_word_to_frame
from engine.rendering import (
    CORE_TEMPLATE_DEFINITIONS, CONTENT_SAFE_AREA_V1, SUBTITLE_SAFE_AREA_V1,
    TemplateCandidateV1, TemplateContractError, TemplateContractRejectionReason,
    TemplateCompilationInputV1,
    TemplateId, TemplateInvocationV1, TemplateRectV1, TemplateRegistry,
    WordBindingV1, build_template_render_input, compile_template_render_plan,
    compile_template_render_plan_from_canonical,
    core_neutral_style_preset, load_template_render_plan,
    run_template_replay,
    serialize_template_render_input, serialize_template_render_plan,
    style_preset_from_policy_snapshot,
)
from engine.rendering.bridge import build_render_props, renderer_version
from engine.rendering.bridge import serialize_render_props
from engine.rendering.fixture_assets import FixtureAssetResolver
from tests.test_render_bridge import FIXTURE_ROOT as PHASE4_FIXTURE_ROOT, build_phase4a_rich_replay_inputs
from tests.test_word_to_frame import _fixture_values


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "phase5"


def _props_and_word():
    replay = build_phase4a_rich_replay_inputs()
    props = build_render_props(
        video_edl=replay["video_edl"], audio_edl=replay["audio_edl"],
        fixture_assets=FixtureAssetResolver.load(PHASE4_FIXTURE_ROOT),
        renderer_version_value=renderer_version((ROOT / "renderer-remotion" / "package-lock.json").read_bytes()),
    )
    result, groups, emphasis = _fixture_values()
    word = compile_word_to_frame(
        alignment_result=result, caption_groups=groups, emphasis_events=emphasis,
        frame_rate=TemporalFrameRate(30, 1),
    )
    return props, word


def _payload(template_id: TemplateId) -> dict[str, object]:
    if template_id in {TemplateId.COLD_OPEN_SOURCE_MONTAGE, TemplateId.ARTICLE_FOCUS_SCAN, TemplateId.HEADLINE_TO_PARAGRAPH_ZOOM, TemplateId.HIGHLIGHT_WIPE, TemplateId.NEWS_CLIP_CONTEXT}:
        return {"headline": "Replay headline", "body": "Replay body"}
    if template_id in {TemplateId.CHAPTER_TITLE, TemplateId.FINAL_THESIS_CARD}:
        return {"title": "Replay title", "body": "Replay body"}
    if template_id is TemplateId.EXPERT_QUOTE_CARD:
        return {"quote": "Replay quote", "attribution": "Replay source"}
    if template_id is TemplateId.METRIC_REVEAL:
        return {"label": "Replay metric", "value": "42%", "qualifier": "reported"}
    if template_id is TemplateId.METRIC_COMPARISON:
        return {"left_label": "Before", "left_value": "1", "right_label": "After", "right_value": "2", "qualifier": "reported"}
    if template_id is TemplateId.PROCESS_DIAGRAM:
        return {"nodes": [{"node_id": "a", "label": "A"}, {"node_id": "b", "label": "B"}], "edges": [{"from_node_id": "a", "to_node_id": "b"}]}
    if template_id is TemplateId.TIMELINE_PROGRESSION:
        return {"points": [{"point_id": "p1", "label": "Start", "ordinal": 1}, {"point_id": "p2", "label": "Finish", "ordinal": 2}]}
    if template_id is TemplateId.SPLIT_SCREEN_COMPARISON:
        return {"left_label": "Before", "right_label": "After", "conclusion": "Changed"}
    return {"display_text": "Replay words"}


def _variant_payload(value: dict[str, object]) -> dict[str, object]:
    result = json.loads(json.dumps(value))
    for key, item in result.items():
        if isinstance(item, str):
            result[key] = item + " variant"
            return result
        if isinstance(item, list) and item and isinstance(item[0], dict):
            for nested_key, nested_value in item[0].items():
                if isinstance(nested_value, str) and nested_key == "label":
                    item[0][nested_key] = nested_value + "v"
                    return result
    raise AssertionError("fixture payload has no deterministic legal variant")


def _invocations(props, word) -> tuple[TemplateInvocationV1, ...]:
    source_event = props.asset_bindings[0]["event_id"]
    start, end = word.word_frames[0], word.word_frames[1]
    binding = WordBindingV1(word.narration_revision_id, word.word_to_frame_id, word.word_to_frame_hash, start.start_word_id, end.end_word_id, start.start_frame, end.end_exclusive_frame)
    values = []
    for ordinal, definition in enumerate(CORE_TEMPLATE_DEFINITIONS):
        kinetic = definition.template_id in {TemplateId.KINETIC_KEYWORD, TemplateId.CAPTION_PHRASE}
        values.append(TemplateInvocationV1(
            template_id=definition.template_id, template_version="1.0.0", editorial_role=definition.supported_editorial_roles[0],
            start_frame=start.start_frame if kinetic else ordinal * 2,
            end_exclusive_frame=end.end_exclusive_frame if kinetic else ordinal * 2 + 2,
            layout=TemplateRectV1(*(SUBTITLE_SAFE_AREA_V1 if kinetic else CONTENT_SAFE_AREA_V1)),
            source_event_id=source_event if definition.requires_source_asset else None,
            target_region=TemplateRectV1(*CONTENT_SAFE_AREA_V1) if definition.supports_target_region else None,
            entry_animation="fade_in", exit_animation="fade_out", camera_motion="static",
            caption="Replay caption" if definition.supports_caption else None,
            source_label="Replay source" if definition.supports_source_label else None,
            style_preset_id="core-neutral-v1", payload=_payload(definition.template_id),
            word_binding=binding if definition.supports_word_binding else None,
            safe_area_policy="SAFE-AREA-V1",
        ))
    return tuple(values)


def test_replay_core_inventory_compiles_and_round_trips() -> None:
    fixture = json.loads((FIXTURE_ROOT / "core_no_pack.json").read_text(encoding="utf-8"))
    assert [item.template_id.value for item in CORE_TEMPLATE_DEFINITIONS] == fixture["template_ids"]
    props, word = _props_and_word()
    plan = compile_template_render_plan(render_props=props, word_to_frame_artifact=word, invocations=_invocations(props, word))
    encoded = serialize_template_render_plan(plan, render_props=props, word_to_frame_artifact=word)
    assert load_template_render_plan(encoded, render_props=props, word_to_frame_artifact=word) == plan
    envelope = build_template_render_input(render_props=props, template_render_plan=plan, word_to_frame_artifact=word)
    assert json.loads(serialize_template_render_input(envelope))["template_input_hash"] == envelope.template_input_hash
    assert plan.style_preset == core_neutral_style_preset()


def test_word_binding_is_exact_and_three_consecutive_templates_fail_closed() -> None:
    props, word = _props_and_word()
    invocations = list(_invocations(props, word))
    kinetic_index = next(index for index, invocation in enumerate(invocations) if invocation.word_binding is not None)
    forged = dataclasses.replace(invocations[kinetic_index], word_binding=dataclasses.replace(invocations[kinetic_index].word_binding, start_frame=4))
    invocations[kinetic_index] = forged
    with pytest.raises(TemplateContractError) as rejected:
        compile_template_render_plan(render_props=props, word_to_frame_artifact=word, invocations=tuple(invocations))
    assert rejected.value.reason is TemplateContractRejectionReason.WORD_BINDING_INVALID
    repeated = (_invocations(props, word)[0],) * 3
    with pytest.raises(TemplateContractError) as rejected:
        compile_template_render_plan(render_props=props, word_to_frame_artifact=word, invocations=repeated)
    assert rejected.value.reason is TemplateContractRejectionReason.CONSECUTIVE_TEMPLATE_LIMIT


def test_canonical_ingress_revalidates_word_to_frame_before_compilation() -> None:
    props, word = _props_and_word()
    result, groups, emphasis = _fixture_values()
    value = TemplateCompilationInputV1(
        render_props_bytes=serialize_render_props(props), word_to_frame_bytes=serialize_word_to_frame(word),
        alignment_result=result, caption_groups=groups, emphasis_events=emphasis,
        frame_rate=TemporalFrameRate(30, 1), invocations=_invocations(props, word),
    )
    assert compile_template_render_plan_from_canonical(value).word_to_frame_hash == word.word_to_frame_hash


def test_business_tech_snapshot_policy_selects_declared_preferences() -> None:
    catalog = SchemaCatalog(ROOT / "schema" / "v3")
    registry = DomainPackRegistry([ROOT / "domain-packs"], catalog)
    registry.discover()
    profile = json.loads((ROOT / "samples" / "v3" / "business-tech" / "workspace.json").read_text(encoding="utf-8"))["domain"]["profile"]
    snapshot, _ = DomainPolicyResolver(catalog).resolve(registry.get("business-tech", "0.1.0"), profile)
    assert style_preset_from_policy_snapshot(snapshot).preset_id == "business-tech-editorial-v1"
    fixture = json.loads((FIXTURE_ROOT / "business_tech_policy.json").read_text(encoding="utf-8"))
    templates = TemplateRegistry()
    for case in fixture["selection_cases"]:
        selected = templates.select(editorial_role=case["editorial_role"], candidates=tuple(TemplateCandidateV1(TemplateId(item), case["editorial_role"]) for item in case["candidate_ids"]), policy_snapshot=snapshot)
        assert selected.template_id.value == case["expected_template_id"]


def test_each_template_variant_renders_with_visual_golden_and_contact_sheet(tmp_path: Path) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is unavailable")
    props, word = _props_and_word()
    work_root = tmp_path / "work"
    work_root.mkdir()
    golden = json.loads((FIXTURE_ROOT / "visual_golden_v1.json").read_text(encoding="utf-8"))
    expected = {(item["template_id"], item["frame_index"]): item for item in golden["primary_frames"]}
    primary_starts: list[Image.Image] = []
    alternate_source = props.asset_bindings[1]["event_id"]

    def render(*, invocation: TemplateInvocationV1, label: str) -> tuple[dict[str, object], Path]:
        plan = compile_template_render_plan(render_props=props, word_to_frame_artifact=word, invocations=(invocation,))
        envelope = build_template_render_input(render_props=props, template_render_plan=plan, word_to_frame_artifact=word)
        output = tmp_path / "renders" / label
        result = run_template_replay(input_value=envelope, output_root=output, fixture_root=PHASE4_FIXTURE_ROOT, work_root=work_root, renderer_root=ROOT / "renderer-remotion", node_executable=node)
        manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
        assert manifest["manifest_id"] == result.manifest_id
        assert manifest["manifest_hash"] == result.manifest_hash
        return manifest, output

    for invocation in _invocations(props, word):
        primary_manifest, primary_output = render(invocation=invocation, label=f"primary-{invocation.template_id.value}")
        variant = dataclasses.replace(invocation, payload=_variant_payload(dict(invocation.payload)), source_event_id=alternate_source if invocation.source_event_id is not None else None)
        variant_manifest, variant_output = render(invocation=variant, label=f"variant-{invocation.template_id.value}")
        assert [frame["frame_index"] for frame in primary_manifest["frames"]] == [frame["frame_index"] for frame in variant_manifest["frames"]]
        primary_start_rgba = None
        variant_start_rgba = None
        for frame in primary_manifest["frames"]:
            path = primary_output / frame["relative_path"]
            assert path.is_file()
            with Image.open(path) as image:
                rgba = image.convert("RGBA")
                digest = "sha256:" + hashlib.sha256(rgba.tobytes()).hexdigest()
                expected_frame = expected[(invocation.template_id.value, frame["frame_index"])]
                assert frame["png_sha256"] == expected_frame["png_sha256"]
                assert digest == expected_frame["rgba_sha256"]
                if frame["frame_index"] == invocation.start_frame:
                    primary_start_rgba = digest
                    primary_starts.append(rgba.copy())
        for frame in variant_manifest["frames"]:
            path = variant_output / frame["relative_path"]
            assert path.is_file()
            if frame["frame_index"] == variant.start_frame:
                with Image.open(path) as image:
                    variant_start_rgba = "sha256:" + hashlib.sha256(image.convert("RGBA").tobytes()).hexdigest()
        assert primary_start_rgba is not None and variant_start_rgba is not None and primary_start_rgba != variant_start_rgba

    sheet = Image.new("RGBA", (1280, 720), (13, 20, 30, 255))
    assert len(primary_starts) == len(CORE_TEMPLATE_DEFINITIONS) == 15
    for index, rgba in enumerate(primary_starts):
        sheet.paste(rgba.resize((320, 180), Image.Resampling.NEAREST), ((index % 4) * 320, (index // 4) * 180))
    contact_sheet = tmp_path / "phase5-contact-sheet.png"
    sheet.save(contact_sheet)
    assert "sha256:" + hashlib.sha256(sheet.tobytes()).hexdigest() == golden["contact_sheet_rgba_sha256"]
    with Image.open(ROOT / "baseline" / "phase5_contact_sheet.png") as accepted:
        assert accepted.convert("RGBA").tobytes() == sheet.tobytes()
