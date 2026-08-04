from __future__ import annotations

import ast
import copy
import dataclasses
import gc
import hashlib
import inspect
import json
from pathlib import Path
import weakref

import pytest

from engine.contracts import (
    ConfidenceAvailability,
    compile_caption_groups,
    compile_emphasis_events,
)
import engine.contracts.word_to_frame as word_contracts
from engine.contracts.word_to_frame import (
    WORD_TO_FRAME_HASH_V1,
    WORD_TO_FRAME_POLICY_V1,
    WORD_TO_FRAME_V1,
    TemporalCompiledFrameSpan,
    TemporalFrameRate,
    TemporalFrameSpanKind,
    WordToFrameArtifact,
    WordToFrameContractError,
    WordToFrameRejectionReason,
    compile_word_to_frame,
    load_word_to_frame,
    serialize_word_to_frame,
)
import tests.test_alignment_result as alignment_test_helpers
from tests.test_canonical_narration import fx34_value, materialize_fx34
from tests.test_emphasis_events import _build_fx


ROOT = Path(__file__).resolve().parents[1]
GOLDEN_HASH = "285a114d06e92fe5c431ea1e51ebafd9be72476034a7093cc6ad0ca71b090374"
GOLDEN_ID = "w2f_285a114d06e92fe5c431ea1e51ebafd9"
GOLDEN_ENVELOPE_SHA256 = "1727ca57a98fb839e0cc94ada5ef828002fdd0387e5c91fa72be76b08b547a1b"
GOLDEN_BYTES = b'{"alignment_result_hash":"1521f195a591df09edaa968d8f5fa91ed367be1c7190a3f614823d74b3cd36bb","alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","caption_frames":[{"end_exclusive_frame":27,"end_exclusive_word_ordinal":2,"end_ms":900,"end_word_id":"nword_0cc9d55672a3cb4e9199","ordinal":0,"source_id":"cgrp_2bdd1bc0e985d5d45784956cb0818fb9","source_kind":"CAPTION_GROUP","start_frame":3,"start_ms":100,"start_word_id":"nword_5321ba14c2c4b28c31ab","start_word_ordinal":0},{"end_exclusive_frame":69,"end_exclusive_word_ordinal":4,"end_ms":2300,"end_word_id":"nword_d81fe913754f8b49c296","ordinal":1,"source_id":"cgrp_5b9b84abe4eba87d448e56b87ff277d6","source_kind":"CAPTION_GROUP","start_frame":36,"start_ms":1200,"start_word_id":"nword_49e85bb034c88ef36f26","start_word_ordinal":2}],"caption_groups_hash":"12670fe861389bfe8e25f05a126c7ea355c361c2b2848e9b02a216ed83baaec7","caption_groups_id":"cgs_12670fe861389bfe8e25f05a126c7ea3","confidence_availability":"AVAILABLE","document_id":"nardoc_fx34","emphasis_events_hash":"e6286517914a305715e42460d27092370bf304f6715e28a6c483407758a04b7d","emphasis_events_id":"emps_e6286517914a305715e42460d2709237","emphasis_frames":[{"end_exclusive_frame":27,"end_exclusive_word_ordinal":2,"end_ms":900,"end_word_id":"nword_0cc9d55672a3cb4e9199","ordinal":0,"source_id":"emph_3b919932a4e05683fe94c9eae048341b","source_kind":"EMPHASIS_EVENT","start_frame":3,"start_ms":100,"start_word_id":"nword_5321ba14c2c4b28c31ab","start_word_ordinal":0}],"frame_rate":{"denominator":1,"numerator":30},"hash_scope_version":"WORD-TO-FRAME-HASH-V1","mapping_policy_version":"WORD-TO-FRAME-POLICY-V1","narration_revision_hash":"sha256:d60d7ae087efb0e309d4e3f28fedea074d15e11405046249a23b2c7bb42fe0c0","narration_revision_id":"narrev_d60d7ae087efb0e309d4","project_id":"prj_fx34","schema_version":"WORD-TO-FRAME-V1","word_frames":[{"end_exclusive_frame":15,"end_exclusive_word_ordinal":1,"end_ms":500,"end_word_id":"nword_5321ba14c2c4b28c31ab","ordinal":0,"source_id":"nword_5321ba14c2c4b28c31ab","source_kind":"WORD","start_frame":3,"start_ms":100,"start_word_id":"nword_5321ba14c2c4b28c31ab","start_word_ordinal":0},{"end_exclusive_frame":27,"end_exclusive_word_ordinal":2,"end_ms":900,"end_word_id":"nword_0cc9d55672a3cb4e9199","ordinal":1,"source_id":"nword_0cc9d55672a3cb4e9199","source_kind":"WORD","start_frame":15,"start_ms":520,"start_word_id":"nword_0cc9d55672a3cb4e9199","start_word_ordinal":1},{"end_exclusive_frame":51,"end_exclusive_word_ordinal":3,"end_ms":1700,"end_word_id":"nword_49e85bb034c88ef36f26","ordinal":2,"source_id":"nword_49e85bb034c88ef36f26","source_kind":"WORD","start_frame":36,"start_ms":1200,"start_word_id":"nword_49e85bb034c88ef36f26","start_word_ordinal":2},{"end_exclusive_frame":69,"end_exclusive_word_ordinal":4,"end_ms":2300,"end_word_id":"nword_d81fe913754f8b49c296","ordinal":3,"source_id":"nword_d81fe913754f8b49c296","source_kind":"WORD","start_frame":51,"start_ms":1720,"start_word_id":"nword_d81fe913754f8b49c296","start_word_ordinal":3}],"word_to_frame_hash":"285a114d06e92fe5c431ea1e51ebafd9be72476034a7093cc6ad0ca71b090374","word_to_frame_id":"w2f_285a114d06e92fe5c431ea1e51ebafd9"}'


def _fixture_values():
    document, revision, result, groups, snapshot, registry, intents = _build_fx()
    events = compile_emphasis_events(
        narration_document=document,
        narration_revision=revision,
        alignment_result=result,
        caption_groups=groups,
        domain_policy_snapshot=snapshot,
        domain_pack_registry=registry,
        intents=intents,
    )
    return result, groups, events


@pytest.fixture(scope="module")
def fx():
    return _fixture_values()


def _kwargs(fx, **updates):
    result, groups, events = fx
    values = {
        "alignment_result": result,
        "caption_groups": groups,
        "emphasis_events": events,
        "frame_rate": TemporalFrameRate(30, 1),
    }
    values.update(updates)
    return values


def _canonical(value):
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def _error(exc, reason, pointer, issue=None):
    assert type(exc.value) is WordToFrameContractError
    assert exc.value.reason is reason
    assert exc.value.pointer == pointer
    assert exc.value.issue_code == issue
    assert "Alpha" not in str(exc.value)
    assert "attacker" not in str(exc.value)


def _load_mutation(fx, mutate, **updates):
    value = json.loads(GOLDEN_BYTES)
    mutate(value)
    return load_word_to_frame(_canonical(value), **_kwargs(fx, **updates))


def test_public_shape_constants_enum_order_fields_and_signatures():
    assert [WORD_TO_FRAME_V1, WORD_TO_FRAME_HASH_V1, WORD_TO_FRAME_POLICY_V1] == [
        "WORD-TO-FRAME-V1",
        "WORD-TO-FRAME-HASH-V1",
        "WORD-TO-FRAME-POLICY-V1",
    ]
    assert [item.value for item in TemporalFrameSpanKind] == [
        "WORD",
        "CAPTION_GROUP",
        "EMPHASIS_EVENT",
    ]
    assert [item.value for item in WordToFrameRejectionReason] == [
        "STRUCTURE_INVALID",
        "UNSUPPORTED_VALUE",
        "DEPENDENCY_CONTENT_DRIFT",
        "DEPENDENCY_BINDING_INVALID",
        "FRAME_RATE_INVALID",
        "SOURCE_RANGE_INVALID",
        "TIMING_INVALID",
        "FRAME_MAPPING_INVALID",
        "NON_CANONICAL_SERIALIZATION",
        "IDENTITY_MISMATCH",
        "CONTENT_DRIFT",
        "NOT_MATERIALIZED",
    ]
    assert [field.name for field in dataclasses.fields(TemporalFrameRate)] == [
        "numerator",
        "denominator",
    ]
    assert [
        field.name for field in dataclasses.fields(TemporalCompiledFrameSpan)
    ] == [
        "source_kind",
        "source_id",
        "ordinal",
        "start_word_ordinal",
        "end_exclusive_word_ordinal",
        "start_word_id",
        "end_word_id",
        "start_ms",
        "end_ms",
        "start_frame",
        "end_exclusive_frame",
    ]
    assert [field.name for field in dataclasses.fields(WordToFrameArtifact)] == [
        "schema_version",
        "hash_scope_version",
        "word_to_frame_id",
        "word_to_frame_hash",
        "project_id",
        "document_id",
        "narration_revision_id",
        "narration_revision_hash",
        "alignment_result_id",
        "alignment_result_hash",
        "caption_groups_id",
        "caption_groups_hash",
        "emphasis_events_id",
        "emphasis_events_hash",
        "confidence_availability",
        "mapping_policy_version",
        "frame_rate",
        "word_frames",
        "caption_frames",
        "emphasis_frames",
    ]
    assert list(inspect.signature(compile_word_to_frame).parameters) == [
        "alignment_result",
        "caption_groups",
        "emphasis_events",
        "frame_rate",
    ]
    assert list(inspect.signature(load_word_to_frame).parameters) == [
        "source",
        "alignment_result",
        "caption_groups",
        "emphasis_events",
        "frame_rate",
    ]
    assert list(inspect.signature(serialize_word_to_frame).parameters) == [
        "artifact"
    ]
    assert not hasattr(word_contracts, "FrameRate")
    assert not hasattr(word_contracts, "FrameSpan")


def test_fx_w2f_01_literal_golden_roundtrip(fx):
    artifact = compile_word_to_frame(**_kwargs(fx))
    assert artifact.word_to_frame_hash == GOLDEN_HASH
    assert artifact.word_to_frame_id == GOLDEN_ID
    assert len(GOLDEN_BYTES) == 3155
    assert hashlib.sha256(GOLDEN_BYTES).hexdigest() == GOLDEN_ENVELOPE_SHA256
    assert serialize_word_to_frame(artifact) == GOLDEN_BYTES
    assert [(span.start_frame, span.end_exclusive_frame) for span in artifact.word_frames] == [
        (3, 15),
        (15, 27),
        (36, 51),
        (51, 69),
    ]
    assert [(span.start_frame, span.end_exclusive_frame) for span in artifact.caption_frames] == [
        (3, 27),
        (36, 69),
    ]
    assert [(span.start_frame, span.end_exclusive_frame) for span in artifact.emphasis_frames] == [
        (3, 27)
    ]
    loaded = load_word_to_frame(GOLDEN_BYTES, **_kwargs(fx))
    assert loaded == artifact
    assert serialize_word_to_frame(loaded) == GOLDEN_BYTES


def test_literal_projection_hash_is_independently_recomputed():
    value = json.loads(GOLDEN_BYTES)
    projection = dict(value)
    projection.pop("word_to_frame_id")
    projection.pop("word_to_frame_hash")
    projection_bytes = _canonical(projection)
    assert len(projection_bytes) == 3009
    assert hashlib.sha256(projection_bytes).hexdigest() == GOLDEN_HASH
    assert value["word_to_frame_id"] == "w2f_" + GOLDEN_HASH[:32]


def test_golden_envelope_oracle_is_one_authored_bytes_literal():
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    assignments = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "GOLDEN_BYTES"
            for target in node.targets
        )
    ]
    assert len(assignments) == 1
    assert isinstance(assignments[0].value, ast.Constant)
    assert type(assignments[0].value.value) is bytes
    assert assignments[0].value.value == GOLDEN_BYTES


def test_two_independent_equivalent_dependency_chains_have_identical_identity():
    left_dependencies = _fixture_values()
    right_dependencies = _fixture_values()
    assert all(
        left is not right
        for left, right in zip(left_dependencies, right_dependencies, strict=True)
    )

    left = compile_word_to_frame(**_kwargs(left_dependencies))
    right = compile_word_to_frame(**_kwargs(right_dependencies))
    left_bytes = serialize_word_to_frame(left)
    right_bytes = serialize_word_to_frame(right)

    assert left is not right
    assert left_bytes == right_bytes == GOLDEN_BYTES
    assert left.word_to_frame_hash == right.word_to_frame_hash == GOLDEN_HASH
    assert left.word_to_frame_id == right.word_to_frame_id == GOLDEN_ID


def test_repeated_word_texts_map_by_distinct_stable_ids_and_ordinals(monkeypatch):
    narration_value = fx34_value()
    narration_value["text_tokens"][3].update(
        display_text="Alpha",
        normalized_alignment_text="alpha",
    )
    repeated_narration = materialize_fx34(
        narration_value,
        source_bytes=b"Alpha beta. Alpha delta.",
    )
    repeated_words = repeated_narration.revision.canonical_words
    assert repeated_words[0].normalized_alignment_text == "alpha"
    assert repeated_words[2].normalized_alignment_text == "alpha"
    assert repeated_words[0].word_id != repeated_words[2].word_id
    _, _, _, _, snapshot, registry, _ = _build_fx()

    monkeypatch.setattr(
        alignment_test_helpers,
        "materialize_fx34",
        lambda: repeated_narration,
    )
    payload = json.loads(alignment_test_helpers.PAYLOAD_BYTES)
    payload["narration_revision_id"] = repeated_narration.revision.revision_id
    payload["narration_revision_hash"] = repeated_narration.revision.revision_hash
    payload["tokens"][3]["normalized_alignment_text"] = "alpha"
    dependencies = alignment_test_helpers._dynamic_dependencies(payload, monkeypatch)
    result_value = alignment_test_helpers._result_value(dependencies)
    for timing, word in zip(
        result_value["word_timings"], repeated_words, strict=True
    ):
        timing["word_id"] = word.word_id
    result_value = alignment_test_helpers._rehash(
        result_value,
        "alignment_result_id",
        "alignment_result_hash",
        "alr_",
    )
    result = alignment_test_helpers._materialize(result_value, dependencies)
    groups = compile_caption_groups(
        narration_document=repeated_narration.document,
        narration_revision=repeated_narration.revision,
        alignment_result=result,
    )
    events = compile_emphasis_events(
        narration_document=repeated_narration.document,
        narration_revision=repeated_narration.revision,
        alignment_result=result,
        caption_groups=groups,
        domain_policy_snapshot=snapshot,
        domain_pack_registry=registry,
        intents=(),
    )

    artifact = compile_word_to_frame(
        alignment_result=result,
        caption_groups=groups,
        emphasis_events=events,
        frame_rate=TemporalFrameRate(30, 1),
    )
    assert artifact.word_frames[0].source_id == repeated_words[0].word_id
    assert artifact.word_frames[2].source_id == repeated_words[2].word_id
    assert artifact.word_frames[0].ordinal == 0
    assert artifact.word_frames[2].ordinal == 2
    assert artifact.word_frames[0].start_frame == 3
    assert artifact.word_frames[2].start_frame == 36


@pytest.mark.parametrize(
    "rate",
    [
        TemporalFrameRate(1, 1),
        TemporalFrameRate(24_000, 1001),
        TemporalFrameRate(30_000, 1001),
        TemporalFrameRate(60_000, 1001),
        TemporalFrameRate(240, 1),
    ],
)
def test_valid_reduced_rational_rates_have_strict_integer_drift_proof(fx, rate):
    artifact = compile_word_to_frame(**_kwargs(fx, frame_rate=rate))
    scale = 1000 * rate.denominator
    for collection in (
        artifact.word_frames,
        artifact.caption_frames,
        artifact.emphasis_frames,
    ):
        for span in collection:
            assert span.end_exclusive_frame > span.start_frame
            assert abs(span.start_frame * scale - span.start_ms * rate.numerator) < scale
            assert abs(span.end_exclusive_frame * scale - span.end_ms * rate.numerator) < scale


def test_floor_start_ceil_end_and_owned_rate(fx):
    caller_rate = TemporalFrameRate(30, 1)
    artifact = compile_word_to_frame(**_kwargs(fx, frame_rate=caller_rate))
    assert artifact.frame_rate == caller_rate
    assert artifact.frame_rate is not caller_rate
    assert word_contracts._frames(100, 110, caller_rate, "/word_frames/0") == (
        3,
        4,
    )
    assert word_contracts._frames(520, 900, caller_rate, "/word_frames/0") == (
        15,
        27,
    )


@pytest.mark.parametrize(
    "rate",
    [
        TemporalFrameRate(True, 1),
        TemporalFrameRate(30, False),
        TemporalFrameRate(0, 1),
        TemporalFrameRate(1, 0),
        TemporalFrameRate(-1, 1),
        TemporalFrameRate(30, -1),
        TemporalFrameRate(60, 2),
        TemporalFrameRate(1, 2),
        TemporalFrameRate(241, 1),
        TemporalFrameRate(2**32, 1),
        TemporalFrameRate(1, 2**32),
    ],
)
def test_invalid_frame_rate_closed_oracle(fx, rate):
    with pytest.raises(WordToFrameContractError) as exc:
        compile_word_to_frame(**_kwargs(fx, frame_rate=rate))
    _error(
        exc,
        WordToFrameRejectionReason.FRAME_RATE_INVALID,
        "/frame_rate",
        "FRAME_RATE_INVALID",
    )


def test_frame_rate_requires_exact_public_type_after_dependencies(fx):
    class Subclass(TemporalFrameRate):
        pass

    for rate in (object(), (30, 1), Subclass(30, 1)):
        with pytest.raises(TypeError, match="frame_rate"):
            compile_word_to_frame(**_kwargs(fx, frame_rate=rate))


def test_js_safe_frame_limit_is_fail_closed():
    with pytest.raises(WordToFrameContractError) as exc:
        word_contracts._frames(
            0,
            (2**53) * 1000,
            TemporalFrameRate(1, 1),
            "/word_frames/0",
        )
    _error(
        exc,
        WordToFrameRejectionReason.FRAME_MAPPING_INVALID,
        "/word_frames/0",
        None,
    )


@pytest.mark.parametrize("position", [0, 1, 2])
def test_dependency_copy_is_not_genuine(fx, position):
    values = list(fx)
    values[position] = dataclasses.replace(values[position])
    with pytest.raises(TypeError, match="genuine exact dependency"):
        compile_word_to_frame(
            alignment_result=values[0],
            caption_groups=values[1],
            emphasis_events=values[2],
            frame_rate=TemporalFrameRate(30, 1),
        )


@pytest.mark.parametrize(
    ("position", "field", "pointer"),
    [
        (0, "alignment_result_hash", "/alignment_result"),
        (1, "caption_groups_hash", "/caption_groups"),
        (2, "emphasis_events_hash", "/emphasis_events"),
    ],
)
def test_registered_dependency_mutation_is_content_drift(fx, position, field, pointer):
    dependency = fx[position]
    original = getattr(dependency, field)
    object.__setattr__(dependency, field, "0" * 64)
    try:
        with pytest.raises(WordToFrameContractError) as exc:
            compile_word_to_frame(**_kwargs(fx))
        _error(
            exc,
            WordToFrameRejectionReason.DEPENDENCY_CONTENT_DRIFT,
            pointer,
            "REPLAY_HASH_MISMATCH",
        )
    finally:
        object.__setattr__(dependency, field, original)


@pytest.mark.parametrize(
    "field",
    [
        "project_id",
        "document_id",
        "narration_revision_id",
        "narration_revision_hash",
        "alignment_result_id",
        "alignment_result_hash",
    ],
)
def test_caption_root_all_identity_bindings(fx, monkeypatch, field):
    forged_groups = dataclasses.replace(fx[1], **{field: "binding_mismatch"})
    monkeypatch.setattr(word_contracts, "serialize_caption_groups", lambda _: b"{}")
    with pytest.raises(WordToFrameContractError) as exc:
        compile_word_to_frame(**_kwargs(fx, caption_groups=forged_groups))
    _error(
        exc,
        WordToFrameRejectionReason.DEPENDENCY_BINDING_INVALID,
        "/caption_groups",
        "ALIGNMENT_REQUEST_IDENTITY_MISMATCH",
    )


@pytest.mark.parametrize(
    "field",
    [
        "project_id",
        "document_id",
        "narration_revision_id",
        "narration_revision_hash",
        "alignment_result_id",
        "alignment_result_hash",
        "caption_groups_id",
        "caption_groups_hash",
    ],
)
def test_emphasis_root_all_identity_bindings(fx, monkeypatch, field):
    forged_events = dataclasses.replace(fx[2], **{field: "binding_mismatch"})
    monkeypatch.setattr(word_contracts, "serialize_emphasis_events", lambda _: b"{}")
    with pytest.raises(WordToFrameContractError) as exc:
        compile_word_to_frame(**_kwargs(fx, emphasis_events=forged_events))
    _error(
        exc,
        WordToFrameRejectionReason.DEPENDENCY_BINDING_INVALID,
        "/emphasis_events",
        "ALIGNMENT_REQUEST_IDENTITY_MISMATCH",
    )


@pytest.mark.parametrize("dependency_index,pointer", [(1, "/caption_groups"), (2, "/emphasis_events")])
def test_all_root_confidence_bindings(fx, monkeypatch, dependency_index, pointer):
    other = next(
        item
        for item in type(fx[dependency_index].confidence_availability)
        if item is not fx[dependency_index].confidence_availability
    )
    values = list(fx)
    values[dependency_index] = dataclasses.replace(
        values[dependency_index], confidence_availability=other
    )
    monkeypatch.setattr(
        word_contracts,
        "serialize_caption_groups" if dependency_index == 1 else "serialize_emphasis_events",
        lambda _: b"{}",
    )
    with pytest.raises(WordToFrameContractError) as exc:
        compile_word_to_frame(**_kwargs(tuple(values)))
    _error(
        exc,
        WordToFrameRejectionReason.DEPENDENCY_BINDING_INVALID,
        pointer,
        "ADAPTER_PRECISION_OVERSTATED",
    )


def test_dependency_preflight_precedes_loader_bytes(fx):
    forged = dataclasses.replace(fx[0])
    with pytest.raises(TypeError):
        load_word_to_frame(
            b"not-json", **_kwargs(fx, alignment_result=forged)
        )


@pytest.mark.parametrize(
    ("mutation", "pointer"),
    [
        (lambda root: root.__setitem__("attacker_unknown", "secret"), "/"),
        (lambda root: root.pop("project_id"), "/"),
        (
            lambda root: root["word_frames"][0].__setitem__(
                "attacker_unknown", "secret"
            ),
            "/word_frames/0",
        ),
        (lambda root: root["word_frames"][0].pop("source_id"), "/word_frames/0"),
        (lambda root: root["frame_rate"].__setitem__("extra", 1), "/frame_rate"),
        (lambda root: root["frame_rate"].pop("denominator"), "/frame_rate"),
    ],
)
def test_loader_unknown_and_missing_key_matrix(fx, mutation, pointer):
    with pytest.raises(WordToFrameContractError) as exc:
        _load_mutation(fx, mutation)
    _error(exc, WordToFrameRejectionReason.STRUCTURE_INVALID, pointer)


@pytest.mark.parametrize(
    ("mutation", "pointer"),
    [
        (lambda root: root.__setitem__("word_frames", {}), "/word_frames"),
        (lambda root: root.__setitem__("caption_frames", {}), "/caption_frames"),
        (lambda root: root.__setitem__("emphasis_frames", {}), "/emphasis_frames"),
        (lambda root: root.__setitem__("frame_rate", []), "/frame_rate"),
        (lambda root: root["word_frames"].__setitem__(0, []), "/word_frames/0"),
    ],
)
def test_loader_container_shape_matrix(fx, mutation, pointer):
    with pytest.raises(WordToFrameContractError) as exc:
        _load_mutation(fx, mutation)
    _error(exc, WordToFrameRejectionReason.STRUCTURE_INVALID, pointer)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", "OTHER"),
        ("hash_scope_version", "OTHER"),
        ("mapping_policy_version", "OTHER"),
        ("confidence_availability", "OTHER"),
    ],
)
def test_loader_root_unsupported_literal_oracle(fx, field, value):
    with pytest.raises(WordToFrameContractError) as exc:
        _load_mutation(fx, lambda root: root.__setitem__(field, value))
    _error(
        exc,
        WordToFrameRejectionReason.UNSUPPORTED_VALUE,
        "/",
        "UNSUPPORTED_CONTRACT_ENUM",
    )


def test_loader_span_unsupported_kind_oracle(fx):
    with pytest.raises(WordToFrameContractError) as exc:
        _load_mutation(
            fx,
            lambda root: root["word_frames"][0].__setitem__(
                "source_kind", "OTHER"
            ),
        )
    _error(
        exc,
        WordToFrameRejectionReason.UNSUPPORTED_VALUE,
        "/word_frames/0",
        "UNSUPPORTED_CONTRACT_ENUM",
    )


@pytest.mark.parametrize(
    ("field", "pointer"),
    [
        ("project_id", "/alignment_result"),
        ("alignment_result_id", "/alignment_result"),
        ("caption_groups_hash", "/caption_groups"),
        ("emphasis_events_hash", "/emphasis_events"),
    ],
)
def test_loader_root_dependency_declaration_drift(fx, field, pointer):
    with pytest.raises(WordToFrameContractError) as exc:
        _load_mutation(fx, lambda root: root.__setitem__(field, "attacker"))
    _error(
        exc,
        WordToFrameRejectionReason.DEPENDENCY_BINDING_INVALID,
        pointer,
        "ALIGNMENT_REQUEST_IDENTITY_MISMATCH",
    )


def test_loader_confidence_declaration_drift(fx):
    with pytest.raises(WordToFrameContractError) as exc:
        _load_mutation(
            fx,
            lambda root: root.__setitem__(
                "confidence_availability", "UNAVAILABLE"
            ),
        )
    _error(
        exc,
        WordToFrameRejectionReason.DEPENDENCY_BINDING_INVALID,
        "/alignment_result",
        "ADAPTER_PRECISION_OVERSTATED",
    )


@pytest.mark.parametrize(
    ("mutation", "expected_reason"),
    [
        (
            lambda root: root["frame_rate"].__setitem__("numerator", 60),
            WordToFrameRejectionReason.FRAME_RATE_INVALID,
        ),
        (
            lambda root: root["frame_rate"].__setitem__("denominator", 0),
            WordToFrameRejectionReason.FRAME_RATE_INVALID,
        ),
        (
            lambda root: root["frame_rate"].__setitem__("numerator", True),
            WordToFrameRejectionReason.STRUCTURE_INVALID,
        ),
    ],
)
def test_loader_frame_rate_oracles(fx, mutation, expected_reason):
    with pytest.raises(WordToFrameContractError) as exc:
        _load_mutation(fx, mutation)
    assert exc.value.pointer == "/frame_rate"
    assert exc.value.reason is expected_reason


@pytest.mark.parametrize(
    ("field", "value", "reason", "issue"),
    [
        ("ordinal", 9, WordToFrameRejectionReason.SOURCE_RANGE_INVALID, "CANONICAL_WORD_ORDER_INVALID"),
        ("source_id", "nword_attacker", WordToFrameRejectionReason.SOURCE_RANGE_INVALID, "CANONICAL_COVERAGE_BLOCKER"),
        ("start_word_ordinal", 0, WordToFrameRejectionReason.SOURCE_RANGE_INVALID, "CANONICAL_COVERAGE_BLOCKER"),
        ("start_ms", 101, WordToFrameRejectionReason.TIMING_INVALID, "ADAPTER_PRECISION_OVERSTATED"),
        ("start_frame", 16, WordToFrameRejectionReason.FRAME_MAPPING_INVALID, None),
        ("start_frame", 17, WordToFrameRejectionReason.FRAME_MAPPING_INVALID, "FRAME_BOUNDARY_DRIFT_EXCEEDED"),
    ],
)
def test_loader_span_closed_semantic_oracle(fx, field, value, reason, issue):
    with pytest.raises(WordToFrameContractError) as exc:
        _load_mutation(
            fx,
            lambda root: root["word_frames"][1].__setitem__(field, value),
        )
    _error(exc, reason, "/word_frames/1", issue)


@pytest.mark.parametrize("field", ["word_to_frame_hash", "word_to_frame_id"])
def test_loader_root_identity_oracle(fx, field):
    replacement = "0" * 64 if field.endswith("hash") else "w2f_" + "0" * 32
    with pytest.raises(WordToFrameContractError) as exc:
        _load_mutation(fx, lambda root: root.__setitem__(field, replacement))
    _error(exc, WordToFrameRejectionReason.IDENTITY_MISMATCH, "/")


@pytest.mark.parametrize(
    "source",
    [
        b"\xef\xbb\xbf" + GOLDEN_BYTES,
        GOLDEN_BYTES + b"\n",
        b"\xff",
        b'{"schema_version":"A","schema_version":"B"}',
        b'{"value":1.0}',
        b'{"value":-0}',
    ],
)
def test_loader_noncanonical_wire_matrix(fx, source):
    with pytest.raises(WordToFrameContractError) as exc:
        load_word_to_frame(source, **_kwargs(fx))
    _error(
        exc,
        WordToFrameRejectionReason.NON_CANONICAL_SERIALIZATION,
        "/",
    )


def test_loader_requires_exact_bytes(fx):
    with pytest.raises(TypeError, match="source must be exact bytes"):
        load_word_to_frame(bytearray(GOLDEN_BYTES), **_kwargs(fx))


def test_loader_multi_fault_precedence(fx):
    def mutate(root):
        root["project_id"] = "attacker"
        root["word_frames"][0]["ordinal"] = 99
        root["word_to_frame_hash"] = "0" * 64

    with pytest.raises(WordToFrameContractError) as exc:
        _load_mutation(fx, mutate)
    _error(
        exc,
        WordToFrameRejectionReason.DEPENDENCY_BINDING_INVALID,
        "/alignment_result",
        "ALIGNMENT_REQUEST_IDENTITY_MISMATCH",
    )


def test_loader_reordered_but_semantically_equal_bytes_are_noncanonical(fx):
    value = json.loads(GOLDEN_BYTES)
    reordered = {key: value[key] for key in reversed(tuple(value))}
    source = json.dumps(
        reordered, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    with pytest.raises(WordToFrameContractError) as exc:
        load_word_to_frame(source, **_kwargs(fx))
    _error(
        exc,
        WordToFrameRejectionReason.NON_CANONICAL_SERIALIZATION,
        "/",
    )


@pytest.mark.parametrize("field", ["word_frames", "caption_frames", "emphasis_frames"])
def test_loader_span_count_mismatch_is_coverage_failure(fx, field):
    with pytest.raises(WordToFrameContractError) as exc:
        _load_mutation(fx, lambda root: root[field].pop())
    _error(
        exc,
        WordToFrameRejectionReason.SOURCE_RANGE_INVALID,
        f"/{field}",
        "CANONICAL_COVERAGE_BLOCKER",
    )


def test_word_inventory_duplicate_and_overlap_oracles(fx, monkeypatch):
    duplicate = dataclasses.replace(
        fx[0].word_timings[1], word_id=fx[0].word_timings[0].word_id
    )
    forged = dataclasses.replace(
        fx[0], word_timings=(fx[0].word_timings[0], duplicate, *fx[0].word_timings[2:])
    )
    monkeypatch.setattr(word_contracts, "serialize_alignment_result", lambda _: b"{}")
    with pytest.raises(WordToFrameContractError) as exc:
        compile_word_to_frame(**_kwargs(fx, alignment_result=forged))
    _error(
        exc,
        WordToFrameRejectionReason.SOURCE_RANGE_INVALID,
        "/word_frames/1",
        "CANONICAL_COVERAGE_BLOCKER",
    )

    overlap = dataclasses.replace(fx[0].word_timings[1], start_ms=400)
    forged = dataclasses.replace(
        fx[0], word_timings=(fx[0].word_timings[0], overlap, *fx[0].word_timings[2:])
    )
    with pytest.raises(WordToFrameContractError) as exc:
        compile_word_to_frame(**_kwargs(fx, alignment_result=forged))
    _error(
        exc,
        WordToFrameRejectionReason.TIMING_INVALID,
        "/word_frames/1",
        "ADAPTER_PRECISION_OVERSTATED",
    )


def test_caption_partition_range_endpoint_and_timing_oracles(fx, monkeypatch):
    group = fx[1].caption_groups[0]
    monkeypatch.setattr(word_contracts, "serialize_caption_groups", lambda _: b"{}")
    forged_group = dataclasses.replace(group, end_exclusive_word_ordinal=1)
    forged = dataclasses.replace(
        fx[1], caption_groups=(forged_group, *fx[1].caption_groups[1:])
    )
    with pytest.raises(WordToFrameContractError) as exc:
        compile_word_to_frame(**_kwargs(fx, caption_groups=forged))
    _error(
        exc,
        WordToFrameRejectionReason.SOURCE_RANGE_INVALID,
        "/caption_frames/0",
        "CANONICAL_COVERAGE_BLOCKER",
    )

    forged_group = dataclasses.replace(group, start_word_id="nword_attacker")
    forged = dataclasses.replace(
        fx[1], caption_groups=(forged_group, *fx[1].caption_groups[1:])
    )
    with pytest.raises(WordToFrameContractError) as exc:
        compile_word_to_frame(**_kwargs(fx, caption_groups=forged))
    _error(
        exc,
        WordToFrameRejectionReason.SOURCE_RANGE_INVALID,
        "/caption_frames/0",
        "CANONICAL_COVERAGE_BLOCKER",
    )

    forged_group = dataclasses.replace(group, end_ms=901)
    forged = dataclasses.replace(
        fx[1], caption_groups=(forged_group, *fx[1].caption_groups[1:])
    )
    with pytest.raises(WordToFrameContractError) as exc:
        compile_word_to_frame(**_kwargs(fx, caption_groups=forged))
    _error(
        exc,
        WordToFrameRejectionReason.TIMING_INVALID,
        "/caption_frames/0",
        "ADAPTER_PRECISION_OVERSTATED",
    )


def test_emphasis_source_caption_endpoint_and_timing_oracles(fx, monkeypatch):
    event = fx[2].emphasis_events[0]
    monkeypatch.setattr(word_contracts, "serialize_emphasis_events", lambda _: b"{}")
    forged_event = dataclasses.replace(event, caption_group_id="cgrp_attacker")
    forged = dataclasses.replace(fx[2], emphasis_events=(forged_event,))
    with pytest.raises(WordToFrameContractError) as exc:
        compile_word_to_frame(**_kwargs(fx, emphasis_events=forged))
    _error(
        exc,
        WordToFrameRejectionReason.SOURCE_RANGE_INVALID,
        "/emphasis_frames/0",
        "CANONICAL_COVERAGE_BLOCKER",
    )

    forged_event = dataclasses.replace(event, end_word_id="nword_attacker")
    forged = dataclasses.replace(fx[2], emphasis_events=(forged_event,))
    with pytest.raises(WordToFrameContractError) as exc:
        compile_word_to_frame(**_kwargs(fx, emphasis_events=forged))
    _error(
        exc,
        WordToFrameRejectionReason.SOURCE_RANGE_INVALID,
        "/emphasis_frames/0",
        "CANONICAL_COVERAGE_BLOCKER",
    )

    forged_event = dataclasses.replace(event, start_ms=101)
    forged = dataclasses.replace(fx[2], emphasis_events=(forged_event,))
    with pytest.raises(WordToFrameContractError) as exc:
        compile_word_to_frame(**_kwargs(fx, emphasis_events=forged))
    _error(
        exc,
        WordToFrameRejectionReason.TIMING_INVALID,
        "/emphasis_frames/0",
        "ADAPTER_PRECISION_OVERSTATED",
    )


def _compile_forged_inventory(
    fx,
    monkeypatch,
    *,
    alignment_result=None,
    caption_groups=None,
    emphasis_events=None,
):
    monkeypatch.setattr(word_contracts, "serialize_alignment_result", lambda _: b"{}")
    monkeypatch.setattr(word_contracts, "serialize_caption_groups", lambda _: b"{}")
    monkeypatch.setattr(word_contracts, "serialize_emphasis_events", lambda _: b"{}")
    return compile_word_to_frame(
        alignment_result=fx[0] if alignment_result is None else alignment_result,
        caption_groups=fx[1] if caption_groups is None else caption_groups,
        emphasis_events=fx[2] if emphasis_events is None else emphasis_events,
        frame_rate=TemporalFrameRate(30, 1),
    )


@pytest.mark.parametrize(
    ("case", "pointer", "reason", "issue"),
    [
        ("container_list", "/word_frames", WordToFrameRejectionReason.SOURCE_RANGE_INVALID, "CANONICAL_COVERAGE_BLOCKER"),
        ("empty", "/word_frames", WordToFrameRejectionReason.SOURCE_RANGE_INVALID, "CANONICAL_COVERAGE_BLOCKER"),
        ("item_type", "/word_frames/0", WordToFrameRejectionReason.SOURCE_RANGE_INVALID, "CANONICAL_COVERAGE_BLOCKER"),
        ("word_id_type", "/word_frames/0", WordToFrameRejectionReason.SOURCE_RANGE_INVALID, "CANONICAL_COVERAGE_BLOCKER"),
        ("duplicate_id", "/word_frames/1", WordToFrameRejectionReason.SOURCE_RANGE_INVALID, "CANONICAL_COVERAGE_BLOCKER"),
        ("start_type", "/word_frames/0", WordToFrameRejectionReason.TIMING_INVALID, "ADAPTER_PRECISION_OVERSTATED"),
        ("negative_start", "/word_frames/0", WordToFrameRejectionReason.TIMING_INVALID, "ADAPTER_PRECISION_OVERSTATED"),
        ("empty_interval", "/word_frames/0", WordToFrameRejectionReason.TIMING_INVALID, "ADAPTER_PRECISION_OVERSTATED"),
        ("overlap", "/word_frames/1", WordToFrameRejectionReason.TIMING_INVALID, "ADAPTER_PRECISION_OVERSTATED"),
        ("available_confidence_type", "/alignment_result", WordToFrameRejectionReason.DEPENDENCY_CONTENT_DRIFT, "REPLAY_HASH_MISMATCH"),
        ("available_confidence_range", "/alignment_result", WordToFrameRejectionReason.DEPENDENCY_CONTENT_DRIFT, "REPLAY_HASH_MISMATCH"),
        ("unavailable_confidence_present", "/alignment_result", WordToFrameRejectionReason.DEPENDENCY_CONTENT_DRIFT, "REPLAY_HASH_MISMATCH"),
    ],
)
def test_word_inventory_every_validation_branch(
    fx, monkeypatch, case, pointer, reason, issue
):
    timings = list(fx[0].word_timings)
    groups = fx[1]
    events = fx[2]
    if case == "container_list":
        forged = dataclasses.replace(fx[0], word_timings=timings)
    elif case == "empty":
        forged = dataclasses.replace(fx[0], word_timings=())
    elif case == "item_type":
        timings[0] = object()
        forged = dataclasses.replace(fx[0], word_timings=tuple(timings))
    elif case == "word_id_type":
        timings[0] = dataclasses.replace(
            timings[0], word_id=type("WordIdSubclass", (str,), {})(timings[0].word_id)
        )
        forged = dataclasses.replace(fx[0], word_timings=tuple(timings))
    elif case == "duplicate_id":
        timings[1] = dataclasses.replace(timings[1], word_id=timings[0].word_id)
        forged = dataclasses.replace(fx[0], word_timings=tuple(timings))
    elif case == "start_type":
        timings[0] = dataclasses.replace(timings[0], start_ms=True)
        forged = dataclasses.replace(fx[0], word_timings=tuple(timings))
    elif case == "negative_start":
        timings[0] = dataclasses.replace(timings[0], start_ms=-1)
        forged = dataclasses.replace(fx[0], word_timings=tuple(timings))
    elif case == "empty_interval":
        timings[0] = dataclasses.replace(timings[0], end_ms=timings[0].start_ms)
        forged = dataclasses.replace(fx[0], word_timings=tuple(timings))
    elif case == "overlap":
        timings[1] = dataclasses.replace(timings[1], start_ms=timings[0].end_ms - 1)
        forged = dataclasses.replace(fx[0], word_timings=tuple(timings))
    elif case == "available_confidence_type":
        timings[0] = dataclasses.replace(timings[0], confidence_millionths=True)
        forged = dataclasses.replace(fx[0], word_timings=tuple(timings))
    elif case == "available_confidence_range":
        timings[0] = dataclasses.replace(timings[0], confidence_millionths=1_000_001)
        forged = dataclasses.replace(fx[0], word_timings=tuple(timings))
    else:
        timings = [dataclasses.replace(item, confidence_millionths=None) for item in timings]
        timings[0] = dataclasses.replace(timings[0], confidence_millionths=1)
        forged = dataclasses.replace(
            fx[0],
            confidence_availability=ConfidenceAvailability.UNAVAILABLE,
            word_timings=tuple(timings),
        )
        groups = dataclasses.replace(
            groups, confidence_availability=ConfidenceAvailability.UNAVAILABLE
        )
        events = dataclasses.replace(
            events, confidence_availability=ConfidenceAvailability.UNAVAILABLE
        )
    with pytest.raises(WordToFrameContractError) as exc:
        _compile_forged_inventory(
            fx,
            monkeypatch,
            alignment_result=forged,
            caption_groups=groups,
            emphasis_events=events,
        )
    _error(exc, reason, pointer, issue)


@pytest.mark.parametrize(
    ("case", "pointer", "issue"),
    [
        ("container_list", "/caption_frames", "CANONICAL_COVERAGE_BLOCKER"),
        ("empty", "/caption_frames", "CANONICAL_COVERAGE_BLOCKER"),
        ("item_type", "/caption_frames/0", "CANONICAL_COVERAGE_BLOCKER"),
        ("ordinal_type", "/caption_frames/0", "CANONICAL_WORD_ORDER_INVALID"),
        ("ordinal_order", "/caption_frames/0", "CANONICAL_WORD_ORDER_INVALID"),
        ("id_type", "/caption_frames/0", "CANONICAL_COVERAGE_BLOCKER"),
        ("duplicate_id", "/caption_frames/1", "CANONICAL_COVERAGE_BLOCKER"),
        ("start_range_type", "/caption_frames/0", "CANONICAL_COVERAGE_BLOCKER"),
        ("end_range_type", "/caption_frames/0", "CANONICAL_COVERAGE_BLOCKER"),
        ("partition_gap", "/caption_frames/1", "CANONICAL_COVERAGE_BLOCKER"),
        ("empty_range", "/caption_frames/0", "CANONICAL_COVERAGE_BLOCKER"),
        ("range_overflow", "/caption_frames/1", "CANONICAL_COVERAGE_BLOCKER"),
        ("word_ids_container", "/caption_frames/0", "CANONICAL_COVERAGE_BLOCKER"),
        ("word_ids_item_type", "/caption_frames/0", "CANONICAL_COVERAGE_BLOCKER"),
        ("word_ids_value", "/caption_frames/0", "CANONICAL_COVERAGE_BLOCKER"),
        ("start_id_type", "/caption_frames/0", "CANONICAL_COVERAGE_BLOCKER"),
        ("start_id_value", "/caption_frames/0", "CANONICAL_COVERAGE_BLOCKER"),
        ("end_id_type", "/caption_frames/0", "CANONICAL_COVERAGE_BLOCKER"),
        ("end_id_value", "/caption_frames/0", "CANONICAL_COVERAGE_BLOCKER"),
        ("alignment_binding", "/caption_frames/0", "CANONICAL_COVERAGE_BLOCKER"),
        ("revision_binding", "/caption_frames/0", "CANONICAL_COVERAGE_BLOCKER"),
        ("incomplete_partition", "/caption_frames", "CANONICAL_COVERAGE_BLOCKER"),
    ],
)
def test_caption_inventory_every_range_and_binding_branch(
    fx, monkeypatch, case, pointer, issue
):
    source = list(fx[1].caption_groups)
    group = source[0]
    text_subclass = type("CaptionIdSubclass", (str,), {})
    if case == "container_list":
        groups = dataclasses.replace(fx[1], caption_groups=source)
    elif case == "empty":
        groups = dataclasses.replace(fx[1], caption_groups=())
    elif case == "item_type":
        source[0] = object()
        groups = dataclasses.replace(fx[1], caption_groups=tuple(source))
    elif case == "ordinal_type":
        source[0] = dataclasses.replace(group, ordinal=True)
        groups = dataclasses.replace(fx[1], caption_groups=tuple(source))
    elif case == "ordinal_order":
        source[0] = dataclasses.replace(group, ordinal=1)
        groups = dataclasses.replace(fx[1], caption_groups=tuple(source))
    elif case == "id_type":
        source[0] = dataclasses.replace(
            group, caption_group_id=text_subclass(group.caption_group_id)
        )
        groups = dataclasses.replace(fx[1], caption_groups=tuple(source))
    elif case == "duplicate_id":
        source[1] = dataclasses.replace(
            source[1], caption_group_id=group.caption_group_id
        )
        groups = dataclasses.replace(fx[1], caption_groups=tuple(source))
    elif case == "start_range_type":
        source[0] = dataclasses.replace(group, start_word_ordinal=True)
        groups = dataclasses.replace(fx[1], caption_groups=tuple(source))
    elif case == "end_range_type":
        source[0] = dataclasses.replace(group, end_exclusive_word_ordinal=True)
        groups = dataclasses.replace(fx[1], caption_groups=tuple(source))
    elif case == "partition_gap":
        source[1] = dataclasses.replace(source[1], start_word_ordinal=3)
        groups = dataclasses.replace(fx[1], caption_groups=tuple(source))
    elif case == "empty_range":
        source[0] = dataclasses.replace(group, end_exclusive_word_ordinal=0)
        groups = dataclasses.replace(fx[1], caption_groups=tuple(source))
    elif case == "range_overflow":
        source[1] = dataclasses.replace(source[1], end_exclusive_word_ordinal=5)
        groups = dataclasses.replace(fx[1], caption_groups=tuple(source))
    elif case == "word_ids_container":
        source[0] = dataclasses.replace(group, word_ids=list(group.word_ids))
        groups = dataclasses.replace(fx[1], caption_groups=tuple(source))
    elif case == "word_ids_item_type":
        source[0] = dataclasses.replace(
            group, word_ids=(text_subclass(group.word_ids[0]), group.word_ids[1])
        )
        groups = dataclasses.replace(fx[1], caption_groups=tuple(source))
    elif case == "word_ids_value":
        source[0] = dataclasses.replace(group, word_ids=tuple(reversed(group.word_ids)))
        groups = dataclasses.replace(fx[1], caption_groups=tuple(source))
    elif case == "start_id_type":
        source[0] = dataclasses.replace(
            group, start_word_id=text_subclass(group.start_word_id)
        )
        groups = dataclasses.replace(fx[1], caption_groups=tuple(source))
    elif case == "start_id_value":
        source[0] = dataclasses.replace(group, start_word_id="wrong")
        groups = dataclasses.replace(fx[1], caption_groups=tuple(source))
    elif case == "end_id_type":
        source[0] = dataclasses.replace(
            group, end_word_id=text_subclass(group.end_word_id)
        )
        groups = dataclasses.replace(fx[1], caption_groups=tuple(source))
    elif case == "end_id_value":
        source[0] = dataclasses.replace(group, end_word_id="wrong")
        groups = dataclasses.replace(fx[1], caption_groups=tuple(source))
    elif case == "alignment_binding":
        source[0] = dataclasses.replace(group, alignment_result_id="wrong")
        groups = dataclasses.replace(fx[1], caption_groups=tuple(source))
    elif case == "revision_binding":
        source[0] = dataclasses.replace(group, narration_revision_id="wrong")
        groups = dataclasses.replace(fx[1], caption_groups=tuple(source))
    else:
        selected = fx[0].word_timings[2:3]
        source[1] = dataclasses.replace(
            source[1],
            end_exclusive_word_ordinal=3,
            end_word_id=selected[-1].word_id,
            word_ids=tuple(item.word_id for item in selected),
            end_ms=selected[-1].end_ms,
        )
        groups = dataclasses.replace(fx[1], caption_groups=tuple(source))
    with pytest.raises(WordToFrameContractError) as exc:
        _compile_forged_inventory(fx, monkeypatch, caption_groups=groups)
    _error(
        exc,
        WordToFrameRejectionReason.SOURCE_RANGE_INVALID,
        pointer,
        issue,
    )


@pytest.mark.parametrize("case", ["start_ms", "end_ms"])
def test_caption_inventory_both_timing_endpoints(fx, monkeypatch, case):
    source = list(fx[1].caption_groups)
    source[0] = dataclasses.replace(
        source[0], **{case: getattr(source[0], case) + 1}
    )
    groups = dataclasses.replace(fx[1], caption_groups=tuple(source))
    with pytest.raises(WordToFrameContractError) as exc:
        _compile_forged_inventory(fx, monkeypatch, caption_groups=groups)
    _error(
        exc,
        WordToFrameRejectionReason.TIMING_INVALID,
        "/caption_frames/0",
        "ADAPTER_PRECISION_OVERSTATED",
    )


def _valid_second_emphasis_event(fx):
    event = fx[2].emphasis_events[0]
    group = fx[1].caption_groups[1]
    selected = fx[0].word_timings[2:4]
    return dataclasses.replace(
        event,
        emphasis_event_id="emph_second_distinct",
        ordinal=1,
        caption_group_id=group.caption_group_id,
        start_word_ordinal=2,
        end_exclusive_word_ordinal=4,
        start_word_id=selected[0].word_id,
        end_word_id=selected[-1].word_id,
        word_ids=tuple(item.word_id for item in selected),
        start_ms=selected[0].start_ms,
        end_ms=selected[-1].end_ms,
    )


@pytest.mark.parametrize(
    ("case", "pointer", "issue"),
    [
        ("container_list", "/emphasis_frames", "CANONICAL_COVERAGE_BLOCKER"),
        ("item_type", "/emphasis_frames/0", "CANONICAL_COVERAGE_BLOCKER"),
        ("ordinal_type", "/emphasis_frames/0", "CANONICAL_WORD_ORDER_INVALID"),
        ("ordinal_order", "/emphasis_frames/0", "CANONICAL_WORD_ORDER_INVALID"),
        ("id_type", "/emphasis_frames/0", "CANONICAL_COVERAGE_BLOCKER"),
        ("duplicate_id", "/emphasis_frames/1", "CANONICAL_COVERAGE_BLOCKER"),
        ("start_range_type", "/emphasis_frames/0", "CANONICAL_COVERAGE_BLOCKER"),
        ("end_range_type", "/emphasis_frames/0", "CANONICAL_COVERAGE_BLOCKER"),
        ("negative_start", "/emphasis_frames/0", "CANONICAL_COVERAGE_BLOCKER"),
        ("overlap", "/emphasis_frames/1", "CANONICAL_COVERAGE_BLOCKER"),
        ("empty_range", "/emphasis_frames/0", "CANONICAL_COVERAGE_BLOCKER"),
        ("range_overflow", "/emphasis_frames/0", "CANONICAL_COVERAGE_BLOCKER"),
        ("word_ids_container", "/emphasis_frames/0", "CANONICAL_COVERAGE_BLOCKER"),
        ("word_ids_item_type", "/emphasis_frames/0", "CANONICAL_COVERAGE_BLOCKER"),
        ("word_ids_value", "/emphasis_frames/0", "CANONICAL_COVERAGE_BLOCKER"),
        ("start_id_type", "/emphasis_frames/0", "CANONICAL_COVERAGE_BLOCKER"),
        ("start_id_value", "/emphasis_frames/0", "CANONICAL_COVERAGE_BLOCKER"),
        ("end_id_type", "/emphasis_frames/0", "CANONICAL_COVERAGE_BLOCKER"),
        ("end_id_value", "/emphasis_frames/0", "CANONICAL_COVERAGE_BLOCKER"),
        ("alignment_binding", "/emphasis_frames/0", "CANONICAL_COVERAGE_BLOCKER"),
        ("revision_binding", "/emphasis_frames/0", "CANONICAL_COVERAGE_BLOCKER"),
        ("caption_root_binding", "/emphasis_frames/0", "CANONICAL_COVERAGE_BLOCKER"),
        ("caption_source_missing", "/emphasis_frames/0", "CANONICAL_COVERAGE_BLOCKER"),
        ("caption_containment", "/emphasis_frames/0", "CANONICAL_COVERAGE_BLOCKER"),
    ],
)
def test_emphasis_inventory_every_range_and_binding_branch(
    fx, monkeypatch, case, pointer, issue
):
    source = list(fx[2].emphasis_events)
    event = source[0]
    text_subclass = type("EmphasisIdSubclass", (str,), {})
    if case == "container_list":
        events = dataclasses.replace(fx[2], emphasis_events=source)
    elif case == "item_type":
        source[0] = object()
        events = dataclasses.replace(fx[2], emphasis_events=tuple(source))
    elif case == "ordinal_type":
        source[0] = dataclasses.replace(event, ordinal=True)
        events = dataclasses.replace(fx[2], emphasis_events=tuple(source))
    elif case == "ordinal_order":
        source[0] = dataclasses.replace(event, ordinal=1)
        events = dataclasses.replace(fx[2], emphasis_events=tuple(source))
    elif case == "id_type":
        source[0] = dataclasses.replace(
            event, emphasis_event_id=text_subclass(event.emphasis_event_id)
        )
        events = dataclasses.replace(fx[2], emphasis_events=tuple(source))
    elif case == "duplicate_id":
        second = dataclasses.replace(
            _valid_second_emphasis_event(fx),
            emphasis_event_id=event.emphasis_event_id,
        )
        events = dataclasses.replace(fx[2], emphasis_events=(event, second))
    elif case == "start_range_type":
        source[0] = dataclasses.replace(event, start_word_ordinal=True)
        events = dataclasses.replace(fx[2], emphasis_events=tuple(source))
    elif case == "end_range_type":
        source[0] = dataclasses.replace(event, end_exclusive_word_ordinal=True)
        events = dataclasses.replace(fx[2], emphasis_events=tuple(source))
    elif case == "negative_start":
        source[0] = dataclasses.replace(event, start_word_ordinal=-1)
        events = dataclasses.replace(fx[2], emphasis_events=tuple(source))
    elif case == "overlap":
        second = dataclasses.replace(
            _valid_second_emphasis_event(fx),
            caption_group_id=fx[1].caption_groups[0].caption_group_id,
            start_word_ordinal=1,
            end_exclusive_word_ordinal=2,
            start_word_id=fx[0].word_timings[1].word_id,
            end_word_id=fx[0].word_timings[1].word_id,
            word_ids=(fx[0].word_timings[1].word_id,),
            start_ms=fx[0].word_timings[1].start_ms,
            end_ms=fx[0].word_timings[1].end_ms,
        )
        events = dataclasses.replace(fx[2], emphasis_events=(event, second))
    elif case == "empty_range":
        source[0] = dataclasses.replace(event, end_exclusive_word_ordinal=0)
        events = dataclasses.replace(fx[2], emphasis_events=tuple(source))
    elif case == "range_overflow":
        source[0] = dataclasses.replace(event, end_exclusive_word_ordinal=5)
        events = dataclasses.replace(fx[2], emphasis_events=tuple(source))
    elif case == "word_ids_container":
        source[0] = dataclasses.replace(event, word_ids=list(event.word_ids))
        events = dataclasses.replace(fx[2], emphasis_events=tuple(source))
    elif case == "word_ids_item_type":
        source[0] = dataclasses.replace(
            event, word_ids=(text_subclass(event.word_ids[0]), event.word_ids[1])
        )
        events = dataclasses.replace(fx[2], emphasis_events=tuple(source))
    elif case == "word_ids_value":
        source[0] = dataclasses.replace(event, word_ids=tuple(reversed(event.word_ids)))
        events = dataclasses.replace(fx[2], emphasis_events=tuple(source))
    elif case == "start_id_type":
        source[0] = dataclasses.replace(
            event, start_word_id=text_subclass(event.start_word_id)
        )
        events = dataclasses.replace(fx[2], emphasis_events=tuple(source))
    elif case == "start_id_value":
        source[0] = dataclasses.replace(event, start_word_id="wrong")
        events = dataclasses.replace(fx[2], emphasis_events=tuple(source))
    elif case == "end_id_type":
        source[0] = dataclasses.replace(
            event, end_word_id=text_subclass(event.end_word_id)
        )
        events = dataclasses.replace(fx[2], emphasis_events=tuple(source))
    elif case == "end_id_value":
        source[0] = dataclasses.replace(event, end_word_id="wrong")
        events = dataclasses.replace(fx[2], emphasis_events=tuple(source))
    elif case == "alignment_binding":
        source[0] = dataclasses.replace(event, alignment_result_id="wrong")
        events = dataclasses.replace(fx[2], emphasis_events=tuple(source))
    elif case == "revision_binding":
        source[0] = dataclasses.replace(event, narration_revision_id="wrong")
        events = dataclasses.replace(fx[2], emphasis_events=tuple(source))
    elif case == "caption_root_binding":
        source[0] = dataclasses.replace(event, caption_groups_id="wrong")
        events = dataclasses.replace(fx[2], emphasis_events=tuple(source))
    elif case == "caption_source_missing":
        source[0] = dataclasses.replace(event, caption_group_id="missing")
        events = dataclasses.replace(fx[2], emphasis_events=tuple(source))
    else:
        selected = fx[0].word_timings[1:3]
        source[0] = dataclasses.replace(
            event,
            start_word_ordinal=1,
            end_exclusive_word_ordinal=3,
            start_word_id=selected[0].word_id,
            end_word_id=selected[-1].word_id,
            word_ids=tuple(item.word_id for item in selected),
            start_ms=selected[0].start_ms,
            end_ms=selected[-1].end_ms,
        )
        events = dataclasses.replace(fx[2], emphasis_events=tuple(source))
    with pytest.raises(WordToFrameContractError) as exc:
        _compile_forged_inventory(fx, monkeypatch, emphasis_events=events)
    _error(
        exc,
        WordToFrameRejectionReason.SOURCE_RANGE_INVALID,
        pointer,
        issue,
    )


@pytest.mark.parametrize("case", ["start_ms", "end_ms"])
def test_emphasis_inventory_both_timing_endpoints(fx, monkeypatch, case):
    event = fx[2].emphasis_events[0]
    forged_event = dataclasses.replace(
        event, **{case: getattr(event, case) + 1}
    )
    events = dataclasses.replace(fx[2], emphasis_events=(forged_event,))
    with pytest.raises(WordToFrameContractError) as exc:
        _compile_forged_inventory(fx, monkeypatch, emphasis_events=events)
    _error(
        exc,
        WordToFrameRejectionReason.TIMING_INVALID,
        "/emphasis_frames/0",
        "ADAPTER_PRECISION_OVERSTATED",
    )


def test_hash_is_compared_before_id_statically():
    source = inspect.getsource(load_word_to_frame)
    assert source.index('value["word_to_frame_hash"]') < source.index(
        'value["word_to_frame_id"]'
    )


def test_serialization_rejects_copy_proxy_subclass_and_mutation(fx):
    artifact = compile_word_to_frame(**_kwargs(fx))

    class Subclass(WordToFrameArtifact):
        pass

    class Proxy:
        def __init__(self, value):
            self.__dict__.update(value.__dict__)

    for forged in (
        dataclasses.replace(artifact),
        Subclass(**artifact.__dict__),
        Proxy(artifact),
        object.__new__(WordToFrameArtifact),
    ):
        with pytest.raises((TypeError, WordToFrameContractError)):
            serialize_word_to_frame(forged)
    original = artifact.word_to_frame_hash
    object.__setattr__(artifact, "word_to_frame_hash", "0" * 64)
    try:
        with pytest.raises(WordToFrameContractError) as exc:
            serialize_word_to_frame(artifact)
        _error(exc, WordToFrameRejectionReason.CONTENT_DRIFT, "/")
    finally:
        object.__setattr__(artifact, "word_to_frame_hash", original)


@pytest.mark.parametrize("mutation", ["rate", "tuple", "span"])
def test_recursive_equal_value_replacement_is_content_drift(fx, mutation):
    artifact = compile_word_to_frame(**_kwargs(fx))
    if mutation == "rate":
        object.__setattr__(
            artifact, "frame_rate", dataclasses.replace(artifact.frame_rate)
        )
    elif mutation == "tuple":
        object.__setattr__(artifact, "word_frames", tuple(list(artifact.word_frames)))
    else:
        object.__setattr__(
            artifact.word_frames[0],
            "source_id",
            copy.copy(artifact.word_frames[0].source_id),
        )
        object.__setattr__(
            artifact,
            "word_frames",
            (dataclasses.replace(artifact.word_frames[0]), *artifact.word_frames[1:]),
        )
    with pytest.raises(WordToFrameContractError) as exc:
        serialize_word_to_frame(artifact)
    _error(exc, WordToFrameRejectionReason.CONTENT_DRIFT, "/")


@pytest.mark.parametrize("mutation", ["root_str", "span_str", "span_int"])
def test_nested_scalar_subclass_mutation_is_content_drift(fx, mutation):
    class Text(str):
        pass

    class Number(int):
        pass

    artifact = compile_word_to_frame(**_kwargs(fx))
    if mutation == "root_str":
        object.__setattr__(
            artifact, "schema_version", Text(artifact.schema_version)
        )
    elif mutation == "span_str":
        object.__setattr__(
            artifact.word_frames[0],
            "source_id",
            Text(artifact.word_frames[0].source_id),
        )
    else:
        object.__setattr__(
            artifact.word_frames[0],
            "start_frame",
            Number(artifact.word_frames[0].start_frame),
        )
    with pytest.raises(WordToFrameContractError) as exc:
        serialize_word_to_frame(artifact)
    _error(exc, WordToFrameRejectionReason.CONTENT_DRIFT, "/")


def test_direct_unregistered_artifact_is_not_materialized(fx):
    artifact = word_contracts._compile(**_kwargs(fx))
    with pytest.raises(WordToFrameContractError) as exc:
        serialize_word_to_frame(artifact)
    _error(exc, WordToFrameRejectionReason.NOT_MATERIALIZED, "/")


def test_registry_releases_artifact(fx):
    artifact = compile_word_to_frame(**_kwargs(fx))
    key = id(artifact)
    reference = weakref.ref(artifact)
    assert key in word_contracts._MATERIALIZED
    del artifact
    gc.collect()
    assert reference() is None
    assert key not in word_contracts._MATERIALIZED


def test_registry_collision_rollback_and_stale_callback(monkeypatch, fx):
    artifact = word_contracts._compile(**_kwargs(fx))
    envelope = word_contracts.encode_canonical_json_bytes(
        word_contracts._artifact_dict(artifact)
    )
    materialized = {}
    monkeypatch.setattr(word_contracts, "_MATERIALIZED", materialized)
    word_contracts._register(artifact, envelope)
    with pytest.raises(RuntimeError, match="collision"):
        word_contracts._register(artifact, envelope)

    class RejectingRegistry(dict):
        def __setitem__(self, key, value):
            raise KeyError("attacker credential secret")

    rejecting = RejectingRegistry()
    monkeypatch.setattr(word_contracts, "_MATERIALIZED", rejecting)
    fresh = word_contracts._compile(**_kwargs(fx))
    with pytest.raises(RuntimeError) as exc:
        word_contracts._register(fresh, envelope)
    assert not rejecting
    assert "attacker" not in str(exc.value)
    assert "credential" not in str(exc.value)

    replacement_registry = {}
    monkeypatch.setattr(word_contracts, "_MATERIALIZED", replacement_registry)
    original = word_contracts._compile(**_kwargs(fx))
    word_contracts._register(original, envelope)
    key = id(original)
    old_reference = replacement_registry[key][0]
    replacement = word_contracts._compile(**_kwargs(fx))
    replacement_entry = (
        weakref.ref(replacement),
        b"replacement",
        word_contracts._identity_signature(replacement),
    )
    replacement_registry[key] = replacement_entry
    del original
    gc.collect()
    assert old_reference() is None
    assert replacement_registry[key] is replacement_entry


def test_artifact_does_not_retain_dependencies_or_caller_rate():
    def materialize_with_refs():
        result, groups, events = _fixture_values()
        rate = TemporalFrameRate(30, 1)
        references = [weakref.ref(value) for value in (result, groups, events, rate)]
        artifact = compile_word_to_frame(
            alignment_result=result,
            caption_groups=groups,
            emphasis_events=events,
            frame_rate=rate,
        )
        return artifact, references

    artifact, references = materialize_with_refs()
    gc.collect()
    assert all(reference() is None for reference in references)
    assert serialize_word_to_frame(artifact) == GOLDEN_BYTES


def test_static_import_complexity_and_no_legacy_boundary():
    source = (ROOT / "engine/contracts/word_to_frame.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    imported = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    forbidden = (
        "provider",
        "fastapi",
        "renderer",
        "preview",
        "remotion",
        "editorial",
        "v2",
        "requests",
        "subprocess",
        "thread",
    )
    assert not any(any(part in name for part in forbidden) for name in imported)
    assert "round(" not in source
    assert "FPS" not in source
    assert ".find(" not in source and "re.search" not in source
    assert "open(" not in source and "Path(" not in source
    called_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "float" not in called_names and "round" not in called_names
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "range"
        for node in ast.walk(tree)
    )
