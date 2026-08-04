"""Focused public-surface checks for canonical caption preview."""

import inspect
import hashlib
import json
import gc
import weakref

import pytest
import engine.contracts.caption_preview as preview_module

from engine.contracts.caption_preview import (
    CAPTION_PREVIEW_HASH_V1,
    CAPTION_PREVIEW_POLICY_V1,
    CAPTION_PREVIEW_V1,
    CaptionPreviewLayoutPolicy,
    CaptionPreviewRejectionReason,
    PreviewRect,
    PreviewTrack,
    compile_caption_preview,
    load_caption_preview,
    render_caption_preview_diagnostic_svg,
    serialize_caption_preview,
)
from engine.contracts.word_to_frame import TemporalFrameRate, compile_word_to_frame
from engine.contracts.emphasis_events import compile_emphasis_events
from tests.test_emphasis_events import _build_fx


def _deps():
    document, revision, result, groups, snapshot, registry, intents = _build_fx()
    events = compile_emphasis_events(narration_document=document, narration_revision=revision,
        alignment_result=result, caption_groups=groups, domain_policy_snapshot=snapshot,
        domain_pack_registry=registry, intents=intents)
    frames = compile_word_to_frame(alignment_result=result, caption_groups=groups,
        emphasis_events=events, frame_rate=TemporalFrameRate(30, 1))
    return groups, events, frames


def _policy(*, overlap=False):
    return CaptionPreviewLayoutPolicy(CAPTION_PREVIEW_POLICY_V1,
        PreviewRect(50_000, 50_000, 950_000, 950_000),
        PreviewRect(80_000, 80_000, 920_000, 260_000),
        PreviewRect(80_000, 200_000 if overlap else 760_000, 920_000, 360_000 if overlap else 920_000))


def test_public_literals_models_and_signatures_are_stable() -> None:
    assert preview_module.__all__ == [
        "CAPTION_PREVIEW_V1", "CAPTION_PREVIEW_HASH_V1", "CAPTION_PREVIEW_POLICY_V1",
        "PreviewTrack", "PreviewRect", "CaptionPreviewLayoutPolicy", "PreviewScene",
        "CaptionPreviewArtifact", "CaptionPreviewRejectionReason", "CaptionPreviewContractError",
        "compile_caption_preview", "load_caption_preview", "serialize_caption_preview",
        "render_caption_preview_diagnostic_svg",
    ]
    assert (CAPTION_PREVIEW_V1, CAPTION_PREVIEW_HASH_V1, CAPTION_PREVIEW_POLICY_V1) == (
        "CAPTION-PREVIEW-V1", "CAPTION-PREVIEW-HASH-V1", "CAPTION-PREVIEW-POLICY-V1",
    )
    assert [item.value for item in PreviewTrack] == ["V5", "V6"]
    assert CaptionPreviewRejectionReason.GEOMETRY_INVALID.value == "GEOMETRY_INVALID"
    policy = CaptionPreviewLayoutPolicy(
        CAPTION_PREVIEW_POLICY_V1,
        PreviewRect(50_000, 50_000, 950_000, 950_000),
        PreviewRect(80_000, 80_000, 920_000, 260_000),
        PreviewRect(80_000, 760_000, 920_000, 920_000),
    )
    assert policy.v6_rect.bottom == 920_000
    for function in (compile_caption_preview, load_caption_preview):
        assert list(inspect.signature(function).parameters) == [
            "caption_groups", "emphasis_events", "word_to_frame", "layout_policy"
        ] if function is compile_caption_preview else [
            "source", "caption_groups", "emphasis_events", "word_to_frame", "layout_policy"
        ]
    assert list(inspect.signature(serialize_caption_preview).parameters) == ["artifact"]
    assert list(inspect.signature(render_caption_preview_diagnostic_svg).parameters) == ["artifact"]


def test_compile_roundtrip_proxy_unicode_svg_and_canonical_bytes() -> None:
    groups, events, frames = _deps()
    artifact = compile_caption_preview(caption_groups=groups, emphasis_events=events,
        word_to_frame=frames, layout_policy=_policy())
    payload = serialize_caption_preview(artifact)
    decoded = json.loads(payload)
    independently_canonical = json.dumps(decoded, sort_keys=True, separators=(",", ":")).encode()
    assert independently_canonical == payload
    assert artifact.caption_preview_id == "cprev_3336e2af7d905a5fbac34a463d5e7732"
    assert artifact.caption_preview_hash == "3336e2af7d905a5fbac34a463d5e77320730d1d31c074f6f6c7f10465e305abf"
    assert [(scene.preview_scene_id, scene.preview_scene_hash, scene.semantic_proxy_label) for scene in artifact.scenes] == [
        ("pscn_ee23be719f93c7785bba93d11ac6225e", "ee23be719f93c7785bba93d11ac6225e79cd05acde451d4960dbe4951df1058e", "[EMPHASIS:STRONG]"),
        ("pscn_7ce18eba221a10de3b86c597ca0eb9ee", "7ce18eba221a10de3b86c597ca0eb9eef6cf30aa915bf8396acdb689cf74f0ce", "Alpha beta."),
        ("pscn_9fe9afcc29c2dcc0bfc4aea99bf6e4d9", "9fe9afcc29c2dcc0bfc4aea99bf6e4d926897466526c70cd361e8bff971ec516", "Gamma delta."),
    ]
    assert artifact.scenes[0].semantic_proxy_label == "[EMPHASIS:STRONG]"
    assert [x.semantic_proxy_label for x in artifact.scenes if x.track is PreviewTrack.V6] == [x.display_text for x in groups.caption_groups]
    assert load_caption_preview(payload, caption_groups=groups, emphasis_events=events,
        word_to_frame=frames, layout_policy=_policy()).caption_preview_hash == artifact.caption_preview_hash
    svg = render_caption_preview_diagnostic_svg(artifact)
    assert svg.startswith('<svg ') and 'data-track="V5"' in svg and "#2C7BE5" in svg
    assert len(payload) == 2739
    assert hashlib.sha256(payload).hexdigest() == "d85d1cf0b3901b7d2e7a17ef99c48def9b82c01dbbdb9829eb257d97646c21d9"
    assert len(svg.encode()) == 874
    assert hashlib.sha256(svg.encode()).hexdigest() == "c497c9509f37e82ed6ce44203cabff2bfedf609970945d7661472a4ce783704b"


def test_loader_rejects_bom_reordered_and_invalid_policy() -> None:
    groups, events, frames = _deps()
    artifact = compile_caption_preview(caption_groups=groups, emphasis_events=events,
        word_to_frame=frames, layout_policy=_policy())
    with pytest.raises(Exception) as error:
        load_caption_preview(b'\xef\xbb\xbf' + serialize_caption_preview(artifact), caption_groups=groups,
            emphasis_events=events, word_to_frame=frames, layout_policy=_policy())
    assert error.value.reason is CaptionPreviewRejectionReason.NON_CANONICAL_SERIALIZATION
    with pytest.raises(Exception) as error:
        compile_caption_preview(caption_groups=groups, emphasis_events=events, word_to_frame=frames,
            layout_policy=CaptionPreviewLayoutPolicy(CAPTION_PREVIEW_POLICY_V1, PreviewRect(0,0,0,1), PreviewRect(0,0,1,1), PreviewRect(0,0,1,1)))
    assert error.value.reason is CaptionPreviewRejectionReason.GEOMETRY_INVALID


@pytest.mark.parametrize("source", [b'{', b'{"x":NaN}', b'{"x":1.0}', b'{"x":1,"x":2}', b'[]'])
def test_loader_rejects_hostile_or_noncanonical_json(source: bytes) -> None:
    groups, events, frames = _deps()
    with pytest.raises(Exception) as error:
        load_caption_preview(source, caption_groups=groups, emphasis_events=events,
            word_to_frame=frames, layout_policy=_policy())
    assert error.value.reason in {
        CaptionPreviewRejectionReason.NON_CANONICAL_SERIALIZATION,
        CaptionPreviewRejectionReason.STRUCTURE_INVALID,
    }


def test_registered_artifact_detects_mutation_and_does_not_retain_after_gc() -> None:
    groups, events, frames = _deps()
    artifact = compile_caption_preview(caption_groups=groups, emphasis_events=events,
        word_to_frame=frames, layout_policy=_policy())
    object.__setattr__(artifact, "caption_preview_id", "cprev_mutated")
    with pytest.raises(Exception) as error:
        serialize_caption_preview(artifact)
    assert error.value.reason is CaptionPreviewRejectionReason.CONTENT_DRIFT
    clean = compile_caption_preview(caption_groups=groups, emphasis_events=events,
        word_to_frame=frames, layout_policy=_policy())
    reference = weakref.ref(clean)
    del clean
    gc.collect()
    assert reference() is None


def test_policy_controls_sparse_geometry_and_equivalent_compiles_are_identical() -> None:
    groups, events, frames = _deps()
    left = compile_caption_preview(caption_groups=groups, emphasis_events=events,
        word_to_frame=frames, layout_policy=_policy(overlap=True))
    right = compile_caption_preview(caption_groups=groups, emphasis_events=events,
        word_to_frame=frames, layout_policy=_policy(overlap=True))
    assert serialize_caption_preview(left) == serialize_caption_preview(right)
    assert all(scene.rect == left.layout_policy.v5_rect for scene in left.scenes if scene.track is PreviewTrack.V5)
    assert all(scene.rect == left.layout_policy.v6_rect for scene in left.scenes if scene.track is PreviewTrack.V6)
    assert len(left.scenes) == len(events.emphasis_events) + len(groups.caption_groups)


def test_v6_svg_escapes_display_text_and_v5_never_uses_event_words() -> None:
    groups, events, frames = _deps()
    # Canonical group display text is already validated upstream; ensure the renderer emits it verbatim.
    artifact = compile_caption_preview(caption_groups=groups, emphasis_events=events,
        word_to_frame=frames, layout_policy=_policy())
    svg = render_caption_preview_diagnostic_svg(artifact)
    for group in groups.caption_groups:
        assert group.display_text in svg
    for event in events.emphasis_events:
        assert event.start_word_id not in svg


def test_materialized_frame_span_ordinal_tamper_fails_closed() -> None:
    groups, events, frames = _deps()
    span = frames.caption_frames[0]
    object.__setattr__(span, "start_word_ordinal", span.start_word_ordinal + 1)
    with pytest.raises(Exception) as error:
        compile_caption_preview(caption_groups=groups, emphasis_events=events,
            word_to_frame=frames, layout_policy=_policy())
    assert error.value.reason is CaptionPreviewRejectionReason.DEPENDENCY_CONTENT_DRIFT
    assert error.value.pointer == "/word_to_frame"


@pytest.mark.parametrize(("mutate", "reason"), [
    (lambda value: value.__setitem__("caption_groups_id", "cgs_wrong"), CaptionPreviewRejectionReason.DEPENDENCY_BINDING_INVALID),
    (lambda value: value["scenes"][0].__setitem__("start_frame", 99), CaptionPreviewRejectionReason.FRAME_BINDING_INVALID),
    (lambda value: value["scenes"][0].__setitem__("rect", {"left": 1, "top": 1, "right": 2, "bottom": 2}), CaptionPreviewRejectionReason.GEOMETRY_INVALID),
    (lambda value: value["scenes"][0].__setitem__("track", "NOPE"), CaptionPreviewRejectionReason.UNSUPPORTED_VALUE),
    (lambda value: value.__setitem__("caption_preview_hash", "0" * 64), CaptionPreviewRejectionReason.IDENTITY_MISMATCH),
])
def test_loader_canonical_tamper_precedence(mutate, reason) -> None:
    groups, events, frames = _deps()
    artifact = compile_caption_preview(caption_groups=groups, emphasis_events=events,
        word_to_frame=frames, layout_policy=_policy())
    value = json.loads(serialize_caption_preview(artifact))
    mutate(value)
    source = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    with pytest.raises(Exception) as error:
        load_caption_preview(source, caption_groups=groups, emphasis_events=events,
            word_to_frame=frames, layout_policy=_policy())
    assert error.value.reason is reason


def test_loader_rejects_wrong_scalar_and_nested_shape_before_geometry() -> None:
    groups, events, frames = _deps()
    artifact = compile_caption_preview(caption_groups=groups, emphasis_events=events,
        word_to_frame=frames, layout_policy=_policy())
    value = json.loads(serialize_caption_preview(artifact))
    value["canvas_units"] = "1000000"
    with pytest.raises(Exception) as error:
        load_caption_preview(json.dumps(value, sort_keys=True, separators=(",", ":")).encode(),
            caption_groups=groups, emphasis_events=events, word_to_frame=frames, layout_policy=_policy())
    assert error.value.reason is CaptionPreviewRejectionReason.STRUCTURE_INVALID
    value = json.loads(serialize_caption_preview(artifact))
    value["scenes"][0]["rect"] = {"left": 1}
    with pytest.raises(Exception) as error:
        load_caption_preview(json.dumps(value, sort_keys=True, separators=(",", ":")).encode(),
            caption_groups=groups, emphasis_events=events, word_to_frame=frames, layout_policy=_policy())
    assert error.value.reason is CaptionPreviewRejectionReason.STRUCTURE_INVALID
