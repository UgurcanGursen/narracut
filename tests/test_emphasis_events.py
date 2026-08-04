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

import engine.contracts as contracts
import engine.contracts.emphasis_events as emphasis_contracts
import engine.contracts.narration as narration_contracts
from engine.contracts import (
    EMPHASIS_EVENT_HASH_V1,
    EMPHASIS_EVENT_V1,
    EMPHASIS_EVENTS_HASH_V1,
    EMPHASIS_EVENTS_V1,
    EMPHASIS_MAPPING_POLICY_V1,
    ConfidenceAvailability,
    DomainPackRegistry,
    DomainPolicyResolver,
    EmphasisEvent,
    EmphasisEventsArtifact,
    EmphasisEventsContractError,
    EmphasisEventsRejectionReason,
    EmphasisIntent,
    EmphasisIntensity,
    EmphasisTypeRef,
    SchemaCatalog,
    WordRangeReference,
    compile_caption_groups,
    compile_emphasis_events,
    load_emphasis_events,
    serialize_emphasis_events,
)
from tests.test_alignment_result import _dependencies, _materialize, _result_value
from tests.test_canonical_narration import fx34_value, materialize_fx34


ROOT = Path(__file__).resolve().parents[1]
GOLDEN_HASH = "e6286517914a305715e42460d27092370bf304f6715e28a6c483407758a04b7d"
GOLDEN_ID = "emps_e6286517914a305715e42460d2709237"
GOLDEN_EVENT_HASH = "3b919932a4e05683fe94c9eae048341b705259b7dcacfb8d552f9ca6531437d5"
GOLDEN_EVENT_ID = "emph_3b919932a4e05683fe94c9eae048341b"
GOLDEN_ENVELOPE_SHA = "008e79e10b989f54377af498c269eca00df09b426b4d8a0ec86441e55a13111c"
GOLDEN_BYTES = b'{"alignment_result_hash":"1521f195a591df09edaa968d8f5fa91ed367be1c7190a3f614823d74b3cd36bb","alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","caption_groups_hash":"12670fe861389bfe8e25f05a126c7ea355c361c2b2848e9b02a216ed83baaec7","caption_groups_id":"cgs_12670fe861389bfe8e25f05a126c7ea3","confidence_availability":"AVAILABLE","document_id":"nardoc_fx34","domain_id":"business-tech","domain_pack_version":"0.1.0","emphasis_events":[{"alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","caption_group_id":"cgrp_2bdd1bc0e985d5d45784956cb0818fb9","caption_groups_id":"cgs_12670fe861389bfe8e25f05a126c7ea3","confidence_millionths":960000,"emphasis_event_hash":"3b919932a4e05683fe94c9eae048341b705259b7dcacfb8d552f9ca6531437d5","emphasis_event_id":"emph_3b919932a4e05683fe94c9eae048341b","emphasis_type_ref":{"domain_id":"business-tech","name":"earnings_sting","version":"0.1.0"},"end_exclusive_word_ordinal":2,"end_ms":900,"end_word_id":"nword_0cc9d55672a3cb4e9199","hash_scope_version":"EMPHASIS-EVENT-HASH-V1","intensity":"STRONG","mapping_policy_version":"EMPHASIS-MAPPING-POLICY-V1","narration_revision_id":"narrev_d60d7ae087efb0e309d4","ordinal":0,"policy_snapshot_hash":"sha256:d18e9981c3f4bcca8e3f5a8f62c838d0e0ecbd14e6cd229e2702c08e2a3f3f2c","policy_snapshot_id":"dps_d18e9981c3f4bcca8e3f","schema_version":"EMPHASIS-EVENT-V1","start_ms":100,"start_word_id":"nword_5321ba14c2c4b28c31ab","start_word_ordinal":0,"word_ids":["nword_5321ba14c2c4b28c31ab","nword_0cc9d55672a3cb4e9199"]}],"emphasis_events_hash":"e6286517914a305715e42460d27092370bf304f6715e28a6c483407758a04b7d","emphasis_events_id":"emps_e6286517914a305715e42460d2709237","hash_scope_version":"EMPHASIS-EVENTS-HASH-V1","mapping_policy_version":"EMPHASIS-MAPPING-POLICY-V1","narration_revision_hash":"sha256:d60d7ae087efb0e309d4e3f28fedea074d15e11405046249a23b2c7bb42fe0c0","narration_revision_id":"narrev_d60d7ae087efb0e309d4","policy_snapshot_hash":"sha256:d18e9981c3f4bcca8e3f5a8f62c838d0e0ecbd14e6cd229e2702c08e2a3f3f2c","policy_snapshot_id":"dps_d18e9981c3f4bcca8e3f","project_id":"prj_fx34","schema_version":"EMPHASIS-EVENTS-V1"}'
EMPTY_GOLDEN_HASH = "e38b5b45a5264b38763fa7cd43877a8a97f306428643662558ccabe575267da6"
EMPTY_GOLDEN_ID = "emps_e38b5b45a5264b38763fa7cd43877a8a"
EMPTY_GOLDEN_ENVELOPE_SHA = "8a03afcf5d627d2a824bd81b6381656fe8c9786f1d4b3a4b7b8764b202c39a54"
EMPTY_GOLDEN_BYTES = b'{"alignment_result_hash":"1521f195a591df09edaa968d8f5fa91ed367be1c7190a3f614823d74b3cd36bb","alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","caption_groups_hash":"12670fe861389bfe8e25f05a126c7ea355c361c2b2848e9b02a216ed83baaec7","caption_groups_id":"cgs_12670fe861389bfe8e25f05a126c7ea3","confidence_availability":"AVAILABLE","document_id":"nardoc_fx34","domain_id":"business-tech","domain_pack_version":"0.1.0","emphasis_events":[],"emphasis_events_hash":"e38b5b45a5264b38763fa7cd43877a8a97f306428643662558ccabe575267da6","emphasis_events_id":"emps_e38b5b45a5264b38763fa7cd43877a8a","hash_scope_version":"EMPHASIS-EVENTS-HASH-V1","mapping_policy_version":"EMPHASIS-MAPPING-POLICY-V1","narration_revision_hash":"sha256:d60d7ae087efb0e309d4e3f28fedea074d15e11405046249a23b2c7bb42fe0c0","narration_revision_id":"narrev_d60d7ae087efb0e309d4","policy_snapshot_hash":"sha256:d18e9981c3f4bcca8e3f5a8f62c838d0e0ecbd14e6cd229e2702c08e2a3f3f2c","policy_snapshot_id":"dps_d18e9981c3f4bcca8e3f","project_id":"prj_fx34","schema_version":"EMPHASIS-EVENTS-V1"}'


def _build_fx():
    dependencies = _dependencies()
    result = _materialize(_result_value(dependencies), dependencies)
    _, document, revision, *_ = dependencies
    groups = compile_caption_groups(
        narration_document=document,
        narration_revision=revision,
        alignment_result=result,
    )
    catalog = SchemaCatalog(ROOT / "schema" / "v3")
    registry = DomainPackRegistry([ROOT / "domain-packs"], catalog)
    registry.discover()
    profile = json.loads((ROOT / "samples/v3/business-tech/domain/profile.json").read_text(encoding="utf-8"))
    snapshot, _ = DomainPolicyResolver(catalog).resolve(
        registry.get("business-tech", "0.1.0"), profile
    )
    intents = (
        EmphasisIntent(
            WordRangeReference(revision.revision_id, 0, 2),
            EmphasisTypeRef("business-tech", "earnings_sting", "0.1.0"),
            EmphasisIntensity.STRONG,
        ),
    )
    return document, revision, result, groups, snapshot, registry, intents


@pytest.fixture(scope="module")
def fx():
    return _build_fx()


def _kwargs(fx, **updates):
    document, revision, result, groups, snapshot, registry, intents = fx
    values = dict(
        narration_document=document,
        narration_revision=revision,
        alignment_result=result,
        caption_groups=groups,
        domain_policy_snapshot=snapshot,
        domain_pack_registry=registry,
        intents=intents,
    )
    values.update(updates)
    return values


def _error(exc, reason, pointer, issue=None):
    assert type(exc.value) is EmphasisEventsContractError
    assert exc.value.reason is reason
    assert exc.value.pointer == pointer
    assert exc.value.issue_code == issue
    assert "Alpha" not in str(exc.value)
    assert "earnings_sting" not in str(exc.value)


def _canonical(value):
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def _load_mutation(fx, mutate, *, intents=None):
    value = json.loads(GOLDEN_BYTES)
    mutate(value)
    return load_emphasis_events(
        _canonical(value), **_kwargs(fx, intents=fx[6] if intents is None else intents)
    )


def test_public_shape_and_exact_exports():
    assert [EMPHASIS_EVENT_V1, EMPHASIS_EVENT_HASH_V1, EMPHASIS_EVENTS_V1, EMPHASIS_EVENTS_HASH_V1, EMPHASIS_MAPPING_POLICY_V1] == [
        "EMPHASIS-EVENT-V1", "EMPHASIS-EVENT-HASH-V1", "EMPHASIS-EVENTS-V1",
        "EMPHASIS-EVENTS-HASH-V1", "EMPHASIS-MAPPING-POLICY-V1",
    ]
    assert [x.value for x in EmphasisIntensity] == ["SUBTLE", "MEDIUM", "STRONG"]
    assert [item.value for item in EmphasisEventsRejectionReason] == [
        "STRUCTURE_INVALID", "UNSUPPORTED_VALUE", "DEPENDENCY_CONTENT_DRIFT",
        "DEPENDENCY_BINDING_INVALID", "POLICY_INVALID", "INTENT_INVALID",
        "WORD_RANGE_INVALID", "ORDERING_INVALID", "OVERLAP_INVALID",
        "CAPTION_GROUP_BINDING_INVALID", "TIMING_INVALID", "CONFIDENCE_INVALID",
        "NON_CANONICAL_SERIALIZATION", "IDENTITY_MISMATCH", "CONTENT_DRIFT",
        "NOT_MATERIALIZED",
    ]
    assert [f.name for f in dataclasses.fields(EmphasisTypeRef)] == ["domain_id", "name", "version"]
    assert [f.name for f in dataclasses.fields(EmphasisIntent)] == ["word_range", "emphasis_type_ref", "intensity"]
    assert [f.name for f in dataclasses.fields(EmphasisEvent)] == [
        "schema_version", "hash_scope_version", "emphasis_event_id",
        "emphasis_event_hash", "narration_revision_id", "alignment_result_id",
        "caption_groups_id", "policy_snapshot_id", "policy_snapshot_hash",
        "mapping_policy_version", "ordinal", "caption_group_id",
        "start_word_ordinal", "end_exclusive_word_ordinal", "start_word_id",
        "end_word_id", "word_ids", "emphasis_type_ref", "intensity",
        "start_ms", "end_ms", "confidence_millionths",
    ]
    assert [f.name for f in dataclasses.fields(EmphasisEventsArtifact)] == [
        "schema_version", "hash_scope_version", "emphasis_events_id",
        "emphasis_events_hash", "project_id", "document_id",
        "narration_revision_id", "narration_revision_hash", "alignment_result_id",
        "alignment_result_hash", "caption_groups_id", "caption_groups_hash",
        "mapping_policy_version", "domain_id", "domain_pack_version",
        "policy_snapshot_id", "policy_snapshot_hash", "confidence_availability",
        "emphasis_events",
    ]
    assert list(inspect.signature(compile_emphasis_events).parameters) == [
        "narration_document", "narration_revision", "alignment_result", "caption_groups",
        "domain_policy_snapshot", "domain_pack_registry", "intents",
    ]
    assert list(inspect.signature(load_emphasis_events).parameters) == [
        "source", "narration_document", "narration_revision", "alignment_result",
        "caption_groups", "domain_policy_snapshot", "domain_pack_registry", "intents",
    ]
    expected = {
        "EMPHASIS_EVENT_V1", "EMPHASIS_EVENT_HASH_V1", "EMPHASIS_EVENTS_V1",
        "EMPHASIS_EVENTS_HASH_V1", "EMPHASIS_MAPPING_POLICY_V1", "EmphasisIntensity",
        "EmphasisEventsRejectionReason", "EmphasisTypeRef", "EmphasisIntent",
        "EmphasisEvent", "EmphasisEventsArtifact", "EmphasisEventsContractError",
        "compile_emphasis_events", "load_emphasis_events", "serialize_emphasis_events",
    }
    assert expected <= set(contracts.__all__)
    for name in ("_MATERIALIZED", "_ResolvedEmphasisPolicy", "_resolve_policy"):
        assert name not in contracts.__all__ and not hasattr(contracts, name)


def test_fx_eme_01_golden_roundtrip(fx):
    artifact = compile_emphasis_events(**_kwargs(fx))
    assert artifact.emphasis_events_hash == GOLDEN_HASH
    assert artifact.emphasis_events_id == GOLDEN_ID
    assert artifact.emphasis_events[0].emphasis_event_hash == GOLDEN_EVENT_HASH
    assert artifact.emphasis_events[0].emphasis_event_id == GOLDEN_EVENT_ID
    assert len(GOLDEN_BYTES) == 2121
    assert hashlib.sha256(GOLDEN_BYTES).hexdigest() == GOLDEN_ENVELOPE_SHA
    assert serialize_emphasis_events(artifact) == GOLDEN_BYTES
    loaded = load_emphasis_events(GOLDEN_BYTES, **_kwargs(fx))
    assert loaded == artifact
    assert serialize_emphasis_events(loaded) == GOLDEN_BYTES


def test_all_four_golden_projections_are_independently_recomputed_from_literal_envelope():
    root_envelope = json.loads(GOLDEN_BYTES)
    event_envelope = root_envelope["emphasis_events"][0]
    event_projection = dict(event_envelope)
    event_projection.pop("emphasis_event_id")
    event_projection.pop("emphasis_event_hash")
    event_projection_bytes = json.dumps(event_projection, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
    event_envelope_bytes = json.dumps(event_envelope, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
    artifact_projection = dict(root_envelope)
    artifact_projection.pop("emphasis_events_id")
    artifact_projection.pop("emphasis_events_hash")
    artifact_projection_bytes = json.dumps(artifact_projection, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
    assert (len(event_projection_bytes), hashlib.sha256(event_projection_bytes).hexdigest()) == (913, GOLDEN_EVENT_HASH)
    assert (len(event_envelope_bytes), hashlib.sha256(event_envelope_bytes).hexdigest()) == (1062, "3fa29852cb8dd7c22c10d69f5afd9123bddac3431ff8f2f27230bfc22e71d8e9")
    assert (len(artifact_projection_bytes), hashlib.sha256(artifact_projection_bytes).hexdigest()) == (1970, GOLDEN_HASH)
    assert (len(GOLDEN_BYTES), hashlib.sha256(GOLDEN_BYTES).hexdigest()) == (2121, GOLDEN_ENVELOPE_SHA)


def test_empty_intents_are_valid_and_deterministic(fx):
    first = compile_emphasis_events(**_kwargs(fx, intents=()))
    second = compile_emphasis_events(**_kwargs(fx, intents=()))
    assert first == second
    assert first.emphasis_events == ()
    assert first.emphasis_events_hash == EMPTY_GOLDEN_HASH
    assert first.emphasis_events_id == EMPTY_GOLDEN_ID
    assert len(EMPTY_GOLDEN_BYTES) == 1059
    assert hashlib.sha256(EMPTY_GOLDEN_BYTES).hexdigest() == EMPTY_GOLDEN_ENVELOPE_SHA
    assert serialize_emphasis_events(first) == EMPTY_GOLDEN_BYTES
    assert serialize_emphasis_events(second) == EMPTY_GOLDEN_BYTES
    assert load_emphasis_events(EMPTY_GOLDEN_BYTES, **_kwargs(fx, intents=())) == first


def test_available_confidence_uses_selected_subset_minimum_not_group_minimum(fx):
    revision = fx[1]
    intent = EmphasisIntent(
        WordRangeReference(revision.revision_id, 0, 1),
        EmphasisTypeRef("business-tech", "earnings_sting", "0.1.0"),
        EmphasisIntensity.SUBTLE,
    )
    artifact = compile_emphasis_events(**_kwargs(fx, intents=(intent,)))
    assert artifact.confidence_availability is ConfidenceAvailability.AVAILABLE
    assert artifact.emphasis_events[0].confidence_millionths == 980000
    assert fx[3].caption_groups[0].confidence_millionths == 960000


@pytest.mark.parametrize(
    "availability",
    [ConfidenceAvailability.UNAVAILABLE, ConfidenceAvailability.NOT_APPLICABLE],
)
def test_non_available_confidence_compiles_null_without_group_copy(fx, monkeypatch, availability):
    result = dataclasses.replace(
        fx[2],
        confidence_availability=availability,
        word_timings=tuple(
            dataclasses.replace(timing, confidence_millionths=None)
            for timing in fx[2].word_timings
        ),
    )
    groups = dataclasses.replace(
        fx[3],
        confidence_availability=availability,
        caption_groups=tuple(
            dataclasses.replace(group, confidence_millionths=None)
            for group in fx[3].caption_groups
        ),
    )
    monkeypatch.setattr(emphasis_contracts, "_preflight", lambda *args: None)
    artifact = compile_emphasis_events(
        **_kwargs(fx, alignment_result=result, caption_groups=groups)
    )
    assert artifact.confidence_availability is availability
    assert artifact.emphasis_events[0].confidence_millionths is None


def test_available_missing_selected_confidence_is_closed(fx, monkeypatch):
    result = dataclasses.replace(
        fx[2],
        word_timings=(
            dataclasses.replace(fx[2].word_timings[0], confidence_millionths=None),
            *fx[2].word_timings[1:],
        ),
    )
    monkeypatch.setattr(emphasis_contracts, "_preflight", lambda *args: None)
    with pytest.raises(EmphasisEventsContractError) as exc:
        compile_emphasis_events(**_kwargs(fx, alignment_result=result))
    _error(
        exc,
        EmphasisEventsRejectionReason.CONFIDENCE_INVALID,
        "/intents/0",
        "CONFIDENCE_REQUIRED_UNAVAILABLE",
    )


def test_intent_container_exact_type_and_ten_thousand_bound(fx):
    with pytest.raises(TypeError, match="intents must be exact tuple"):
        compile_emphasis_events(**_kwargs(fx, intents=list(fx[6])))
    with pytest.raises(EmphasisEventsContractError) as exc:
        compile_emphasis_events(**_kwargs(fx, intents=(fx[6][0],) * 10_001))
    _error(exc, EmphasisEventsRejectionReason.STRUCTURE_INVALID, "/intents")


def test_compile_intent_closed_oracle_matrix(fx):
    revision = fx[1]
    valid_type = EmphasisTypeRef("business-tech", "earnings_sting", "0.1.0")
    cases = [
        (object(), EmphasisEventsRejectionReason.STRUCTURE_INVALID, None),
        (
            EmphasisIntent(
                WordRangeReference(revision.revision_id, 2, 1),
                valid_type,
                EmphasisIntensity.STRONG,
            ),
            EmphasisEventsRejectionReason.WORD_RANGE_INVALID,
            "WORD_RANGE_REVERSED",
        ),
        (
            EmphasisIntent(
                WordRangeReference(revision.revision_id, 1, 1),
                valid_type,
                EmphasisIntensity.STRONG,
            ),
            EmphasisEventsRejectionReason.WORD_RANGE_INVALID,
            "WORD_RANGE_OUT_OF_BOUNDS",
        ),
        (
            EmphasisIntent(
                WordRangeReference(revision.revision_id, 0, 99),
                valid_type,
                EmphasisIntensity.STRONG,
            ),
            EmphasisEventsRejectionReason.WORD_RANGE_INVALID,
            "WORD_RANGE_OUT_OF_BOUNDS",
        ),
        (
            EmphasisIntent(
                WordRangeReference(revision.revision_id, 0, 1),
                EmphasisTypeRef("business-tech", "ATTACKER", "0.1.0"),
                EmphasisIntensity.STRONG,
            ),
            EmphasisEventsRejectionReason.STRUCTURE_INVALID,
            None,
        ),
        (
            EmphasisIntent(
                WordRangeReference(revision.revision_id, 0, 1),
                EmphasisTypeRef("other-domain", "earnings_sting", "0.1.0"),
                EmphasisIntensity.STRONG,
            ),
            EmphasisEventsRejectionReason.POLICY_INVALID,
            None,
        ),
        (
            EmphasisIntent(
                WordRangeReference(revision.revision_id, 0, 1),
                valid_type,
                "STRONG",
            ),
            EmphasisEventsRejectionReason.UNSUPPORTED_VALUE,
            "UNSUPPORTED_CONTRACT_ENUM",
        ),
    ]
    for intent, reason, issue in cases:
        with pytest.raises(EmphasisEventsContractError) as exc:
            compile_emphasis_events(**_kwargs(fx, intents=(intent,)))
        _error(exc, reason, "/intents/0", issue)


@pytest.mark.parametrize("field", ["start_ordinal", "end_exclusive_ordinal"])
@pytest.mark.parametrize("bad_value", [-1, 2**32, True, 1.0, "1"])
def test_word_range_ordinals_are_exact_uint32(fx, field, bad_value):
    revision = fx[1]
    word_range = WordRangeReference(revision.revision_id, 0, 1)
    object.__setattr__(word_range, field, bad_value)
    intent = EmphasisIntent(
        word_range,
        EmphasisTypeRef("business-tech", "earnings_sting", "0.1.0"),
        EmphasisIntensity.STRONG,
    )
    with pytest.raises(EmphasisEventsContractError) as exc:
        compile_emphasis_events(**_kwargs(fx, intents=(intent,)))
    _error(exc, EmphasisEventsRejectionReason.STRUCTURE_INVALID, "/intents/0")


@pytest.mark.parametrize("domain_id", ["Business-Tech", "business tech", "business.tech"])
def test_noncanonical_domain_id_syntax_is_structure_invalid(fx, domain_id):
    intent = dataclasses.replace(
        fx[6][0],
        emphasis_type_ref=EmphasisTypeRef(domain_id, "earnings_sting", "0.1.0"),
    )
    with pytest.raises(EmphasisEventsContractError) as exc:
        compile_emphasis_events(**_kwargs(fx, intents=(intent,)))
    _error(exc, EmphasisEventsRejectionReason.STRUCTURE_INVALID, "/intents/0")


def test_genuine_dependency_drift_and_cross_binding_mapping(fx):
    document, revision, result, groups, *_ = fx
    mutations = [
        (revision, "source_text", revision.source_text + " attacker", "/narration_revision", EmphasisEventsRejectionReason.DEPENDENCY_CONTENT_DRIFT, "ALIGNMENT_REQUEST_IDENTITY_MISMATCH"),
        (result, "alignment_result_hash", "0" * 64, "/alignment_result", EmphasisEventsRejectionReason.DEPENDENCY_CONTENT_DRIFT, "REPLAY_HASH_MISMATCH"),
        (groups, "caption_groups_hash", "0" * 64, "/caption_groups", EmphasisEventsRejectionReason.DEPENDENCY_CONTENT_DRIFT, "REPLAY_HASH_MISMATCH"),
        (document, "current_revision_id", "narrev_" + "0" * 20, "/narration_document", EmphasisEventsRejectionReason.DEPENDENCY_CONTENT_DRIFT, "ALIGNMENT_REQUEST_IDENTITY_MISMATCH"),
    ]
    for target, field, replacement, pointer, reason, issue in mutations:
        original = getattr(target, field)
        object.__setattr__(target, field, replacement)
        try:
            with pytest.raises(EmphasisEventsContractError) as exc:
                compile_emphasis_events(**_kwargs(fx))
            _error(exc, reason, pointer, issue)
        finally:
            object.__setattr__(target, field, original)


def test_distinct_genuine_document_cross_binding_is_not_reported_as_drift(fx):
    other_value = fx34_value()
    other_value["project_id"] = "prj_other"
    other = materialize_fx34(other_value)
    assert narration_contracts._is_materialized_narration_document(
        other.document
    )
    with pytest.raises(EmphasisEventsContractError) as exc:
        compile_emphasis_events(
            **_kwargs(fx, narration_document=other.document)
        )
    _error(
        exc,
        EmphasisEventsRejectionReason.DEPENDENCY_BINDING_INVALID,
        "/narration_document",
        "ALIGNMENT_REQUEST_IDENTITY_MISMATCH",
    )


@pytest.mark.parametrize(
    ("dependency_index", "field", "replacement", "pointer"),
    [
        (0, "title", "FX-34 provenance mutation", "/narration_document"),
        (1, "source_text", "Alpha beta. Gamma delta!", "/narration_revision"),
    ],
)
def test_public_compile_rejects_mutated_genuine_narration_dependency(
    dependency_index, field, replacement, pointer
):
    local_fx = _build_fx()
    dependency = local_fx[dependency_index]
    original = getattr(dependency, field)
    object.__setattr__(dependency, field, replacement)
    try:
        with pytest.raises(EmphasisEventsContractError) as exc:
            compile_emphasis_events(**_kwargs(local_fx))
        _error(
            exc,
            EmphasisEventsRejectionReason.DEPENDENCY_CONTENT_DRIFT,
            pointer,
            "ALIGNMENT_REQUEST_IDENTITY_MISMATCH",
        )
    finally:
        object.__setattr__(dependency, field, original)


@pytest.mark.parametrize(
    ("argument", "dependency_index"),
    [("narration_document", 0), ("narration_revision", 1)],
)
def test_public_compile_keeps_unregistered_exact_copy_as_type_error(
    argument, dependency_index
):
    local_fx = _build_fx()
    unregistered_copy = dataclasses.replace(local_fx[dependency_index])
    with pytest.raises(TypeError, match="genuine exact dependency"):
        compile_emphasis_events(
            **_kwargs(local_fx, **{argument: unregistered_copy})
        )


def test_two_intents_derive_exact_timing_without_per_intent_range_resolution(fx, monkeypatch):
    revision = fx[1]
    type_ref = EmphasisTypeRef("business-tech", "earnings_sting", "0.1.0")
    intents = (
        EmphasisIntent(WordRangeReference(revision.revision_id, 0, 1), type_ref, EmphasisIntensity.SUBTLE),
        EmphasisIntent(WordRangeReference(revision.revision_id, 1, 2), type_ref, EmphasisIntensity.MEDIUM),
    )
    original = getattr(emphasis_contracts, "resolve_word_range", None)
    calls = []

    def observed(*args, **kwargs):
        calls.append((args, kwargs))
        return original(*args, **kwargs)

    if original is not None:
        monkeypatch.setattr(emphasis_contracts, "resolve_word_range", observed)
    artifact = compile_emphasis_events(**_kwargs(fx, intents=intents))
    assert [(event.start_ms, event.end_ms) for event in artifact.emphasis_events] == [
        (100, 500), (520, 900)
    ]
    assert len(calls) <= 1


def test_compile_loop_uses_preindexed_ranges_and_caption_groups():
    source = inspect.getsource(emphasis_contracts._compile)
    tree = ast.parse(source)
    intent_loop = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.For) and "enumerate(intents)" in ast.unparse(node.iter)
    )
    nested_source = ast.unparse(intent_loop)
    assert "resolve_word_range" not in nested_source
    assert "for group in caption_groups.caption_groups" not in nested_source
    assert source.index("caption_groups.caption_groups") < source.index("enumerate(intents)")


@pytest.mark.parametrize("source", [b"[]", b"null", b"1", b'"x"'])
def test_canonical_non_object_roots_are_structure_invalid(fx, source):
    with pytest.raises(EmphasisEventsContractError) as exc:
        load_emphasis_events(source, **_kwargs(fx))
    _error(exc, EmphasisEventsRejectionReason.STRUCTURE_INVALID, "/")


@pytest.mark.parametrize("source", [b"", GOLDEN_BYTES + b"\n", b"\xef\xbb\xbf{}", b'{"x":1,"x":2}', b'{"x":1.0}'])
def test_noncanonical_sources_fail_closed(fx, source):
    with pytest.raises(EmphasisEventsContractError) as exc:
        load_emphasis_events(source, **_kwargs(fx))
    _error(exc, EmphasisEventsRejectionReason.NON_CANONICAL_SERIALIZATION, "/")


def test_range_revision_unknown_type_overlap_and_cross_group(fx):
    revision = fx[1]
    type_ref = EmphasisTypeRef("business-tech", "earnings_sting", "0.1.0")
    cases = [
        ((EmphasisIntent(WordRangeReference("narrev_wrong", 0, 1), type_ref, EmphasisIntensity.STRONG),), EmphasisEventsRejectionReason.WORD_RANGE_INVALID, "WORD_RANGE_REVISION_MISMATCH"),
        ((EmphasisIntent(WordRangeReference(revision.revision_id, 0, 1), EmphasisTypeRef("business-tech", "unknown", "0.1.0"), EmphasisIntensity.STRONG),), EmphasisEventsRejectionReason.POLICY_INVALID, None),
        ((EmphasisIntent(WordRangeReference(revision.revision_id, 0, 2), type_ref, EmphasisIntensity.STRONG), EmphasisIntent(WordRangeReference(revision.revision_id, 1, 2), type_ref, EmphasisIntensity.MEDIUM)), EmphasisEventsRejectionReason.OVERLAP_INVALID, "CANONICAL_COVERAGE_BLOCKER"),
        ((EmphasisIntent(WordRangeReference(revision.revision_id, 1, 3), type_ref, EmphasisIntensity.STRONG),), EmphasisEventsRejectionReason.WORD_RANGE_INVALID, "CANONICAL_COVERAGE_BLOCKER"),
    ]
    for intents, reason, issue in cases:
        with pytest.raises(EmphasisEventsContractError) as exc:
            compile_emphasis_events(**_kwargs(fx, intents=intents))
        _error(exc, reason, "/intents/0" if len(intents) == 1 else "/intents/1", issue)


def test_adjacent_intents_pass_and_reverse_order_fails(fx):
    revision = fx[1]
    type_ref = EmphasisTypeRef("business-tech", "earnings_sting", "0.1.0")
    first = EmphasisIntent(WordRangeReference(revision.revision_id, 0, 1), type_ref, EmphasisIntensity.SUBTLE)
    second = EmphasisIntent(WordRangeReference(revision.revision_id, 1, 2), type_ref, EmphasisIntensity.MEDIUM)
    artifact = compile_emphasis_events(**_kwargs(fx, intents=(first, second)))
    assert [event.start_word_ordinal for event in artifact.emphasis_events] == [0, 1]
    with pytest.raises(EmphasisEventsContractError) as exc:
        compile_emphasis_events(**_kwargs(fx, intents=(second, first)))
    _error(exc, EmphasisEventsRejectionReason.ORDERING_INVALID, "/intents/1", "CANONICAL_WORD_ORDER_INVALID")


def test_policy_snapshot_immutable_and_raw_manifest_drift_fail_closed(fx):
    snapshot, registry = fx[4], fx[5]
    object.__setattr__(snapshot, "immutable", False)
    try:
        with pytest.raises(EmphasisEventsContractError) as exc:
            compile_emphasis_events(**_kwargs(fx))
        _error(exc, EmphasisEventsRejectionReason.POLICY_INVALID, "/domain_policy_snapshot")
    finally:
        object.__setattr__(snapshot, "immutable", True)
    pack = registry._packs[("business-tech", "0.1.0")]
    original = pack.raw_manifest
    object.__setattr__(pack, "raw_manifest", {**original, "display_name": "drift"})
    try:
        with pytest.raises(EmphasisEventsContractError) as exc:
            compile_emphasis_events(**_kwargs(fx))
        _error(exc, EmphasisEventsRejectionReason.POLICY_INVALID, "/domain_policy_snapshot")
    finally:
        object.__setattr__(pack, "raw_manifest", original)


def test_serialization_rejects_direct_copy_proxy_subclass_and_mutation(fx):
    artifact = compile_emphasis_events(**_kwargs(fx))
    class Subclass(EmphasisEventsArtifact):
        pass
    class Proxy:
        def __init__(self, value): self.__dict__.update(value.__dict__)
    for forged in (dataclasses.replace(artifact), Subclass(**artifact.__dict__), Proxy(artifact), object.__new__(EmphasisEventsArtifact)):
        with pytest.raises((EmphasisEventsContractError, TypeError)):
            serialize_emphasis_events(forged)
    object.__setattr__(artifact, "emphasis_events_hash", "0" * 64)
    with pytest.raises(EmphasisEventsContractError) as exc:
        serialize_emphasis_events(artifact)
    _error(exc, EmphasisEventsRejectionReason.CONTENT_DRIFT, "/")


@pytest.mark.parametrize(
    ("path", "value", "reason", "issue"),
    [
        (("schema_version",), "OTHER", EmphasisEventsRejectionReason.UNSUPPORTED_VALUE, "UNSUPPORTED_CONTRACT_ENUM"),
        (("schema_version",), 1, EmphasisEventsRejectionReason.STRUCTURE_INVALID, None),
        (("emphasis_events", 0, "intensity"), "OTHER", EmphasisEventsRejectionReason.UNSUPPORTED_VALUE, "UNSUPPORTED_CONTRACT_ENUM"),
        (("emphasis_events", 0, "ordinal"), "0", EmphasisEventsRejectionReason.STRUCTURE_INVALID, None),
    ],
)
def test_loader_type_and_literal_oracle(fx, path, value, reason, issue):
    data = json.loads(GOLDEN_BYTES)
    target = data
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value
    source = json.dumps(data, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
    with pytest.raises(EmphasisEventsContractError) as exc:
        load_emphasis_events(source, **_kwargs(fx))
    pointer = "/" if len(path) == 1 else "/emphasis_events/0"
    _error(exc, reason, pointer, issue)


@pytest.mark.parametrize(
    ("mutation", "pointer"),
    [
        (lambda root: root.__setitem__("attacker_unknown", "secret"), "/"),
        (lambda root: root.pop("project_id"), "/"),
        (lambda root: root["emphasis_events"][0].__setitem__("attacker_unknown", "secret"), "/emphasis_events/0"),
        (lambda root: root["emphasis_events"][0].pop("caption_group_id"), "/emphasis_events/0"),
        (lambda root: root["emphasis_events"][0]["emphasis_type_ref"].__setitem__("attacker_unknown", "secret"), "/emphasis_events/0"),
        (lambda root: root["emphasis_events"][0]["emphasis_type_ref"].pop("version"), "/emphasis_events/0"),
    ],
)
def test_loader_unknown_and_missing_key_matrix(fx, mutation, pointer):
    with pytest.raises(EmphasisEventsContractError) as exc:
        _load_mutation(fx, mutation)
    _error(exc, EmphasisEventsRejectionReason.STRUCTURE_INVALID, pointer)
    assert "attacker_unknown" not in str(exc.value)
    assert "secret" not in str(exc.value)


def test_loader_event_container_and_count_oracles(fx):
    cases = [
        (lambda root: root.__setitem__("emphasis_events", {}), "/emphasis_events", EmphasisEventsRejectionReason.STRUCTURE_INVALID, None),
        (lambda root: root.__setitem__("emphasis_events", []), "/emphasis_events", EmphasisEventsRejectionReason.INTENT_INVALID, "CANONICAL_COVERAGE_BLOCKER"),
        (lambda root: root["emphasis_events"][0].__setitem__("word_ids", {}), "/emphasis_events/0", EmphasisEventsRejectionReason.STRUCTURE_INVALID, None),
        (lambda root: root["emphasis_events"][0].__setitem__("emphasis_type_ref", []), "/emphasis_events/0", EmphasisEventsRejectionReason.STRUCTURE_INVALID, None),
    ]
    for mutation, pointer, reason, issue in cases:
        with pytest.raises(EmphasisEventsContractError) as exc:
            _load_mutation(fx, mutation)
        _error(exc, reason, pointer, issue)


@pytest.mark.parametrize(
    ("field", "value", "reason", "issue"),
    [
        ("ordinal", 2, EmphasisEventsRejectionReason.ORDERING_INVALID, "CANONICAL_WORD_ORDER_INVALID"),
        ("start_word_ordinal", 1, EmphasisEventsRejectionReason.INTENT_INVALID, None),
        ("end_exclusive_word_ordinal", 1, EmphasisEventsRejectionReason.INTENT_INVALID, None),
        ("intensity", "MEDIUM", EmphasisEventsRejectionReason.INTENT_INVALID, None),
        ("caption_group_id", "cgrp_attacker", EmphasisEventsRejectionReason.CAPTION_GROUP_BINDING_INVALID, "CANONICAL_COVERAGE_BLOCKER"),
        ("start_word_id", "nword_attacker", EmphasisEventsRejectionReason.CAPTION_GROUP_BINDING_INVALID, "CANONICAL_COVERAGE_BLOCKER"),
        ("end_ms", 901, EmphasisEventsRejectionReason.TIMING_INVALID, "TIMESTAMP_NON_MONOTONIC"),
        ("confidence_millionths", None, EmphasisEventsRejectionReason.CONFIDENCE_INVALID, "CONFIDENCE_REQUIRED_UNAVAILABLE"),
        ("confidence_millionths", 950000, EmphasisEventsRejectionReason.CONFIDENCE_INVALID, "ADAPTER_PRECISION_OVERSTATED"),
        ("emphasis_event_hash", "0" * 64, EmphasisEventsRejectionReason.IDENTITY_MISMATCH, None),
        ("emphasis_event_id", "emph_" + "0" * 32, EmphasisEventsRejectionReason.IDENTITY_MISMATCH, None),
    ],
)
def test_loader_event_closed_oracle_matrix(fx, field, value, reason, issue):
    with pytest.raises(EmphasisEventsContractError) as exc:
        _load_mutation(fx, lambda root: root["emphasis_events"][0].__setitem__(field, value))
    _error(exc, reason, "/emphasis_events/0", issue)


@pytest.mark.parametrize("field", ["project_id", "alignment_result_id"])
def test_loader_root_dependency_declaration_drift(fx, field):
    with pytest.raises(EmphasisEventsContractError) as exc:
        _load_mutation(fx, lambda root: root.__setitem__(field, "attacker_secret"))
    _error(
        exc,
        EmphasisEventsRejectionReason.DEPENDENCY_BINDING_INVALID,
        "/",
        "ALIGNMENT_REQUEST_IDENTITY_MISMATCH",
    )
    assert "attacker_secret" not in str(exc.value)


@pytest.mark.parametrize(
    ("container", "field", "pointer"),
    [
        ("root", "policy_snapshot_id", "/"),
        ("root", "policy_snapshot_hash", "/"),
        ("event", "policy_snapshot_id", "/emphasis_events/0"),
        ("event", "policy_snapshot_hash", "/emphasis_events/0"),
    ],
)
def test_loader_policy_declaration_drift_has_null_issue(fx, container, field, pointer):
    def mutate(root):
        target = root if container == "root" else root["emphasis_events"][0]
        target[field] = "attacker_secret"

    with pytest.raises(EmphasisEventsContractError) as exc:
        _load_mutation(fx, mutate)
    _error(
        exc,
        EmphasisEventsRejectionReason.DEPENDENCY_BINDING_INVALID,
        pointer,
        None,
    )
    assert "attacker_secret" not in str(exc.value)


def test_loader_root_confidence_declaration_drift(fx):
    with pytest.raises(EmphasisEventsContractError) as exc:
        _load_mutation(
            fx,
            lambda root: root.__setitem__(
                "confidence_availability", ConfidenceAvailability.UNAVAILABLE.value
            ),
        )
    _error(
        exc,
        EmphasisEventsRejectionReason.CONFIDENCE_INVALID,
        "/",
        "ADAPTER_PRECISION_OVERSTATED",
    )


@pytest.mark.parametrize("field", ["emphasis_events_hash", "emphasis_events_id"])
def test_loader_root_identity_oracle(fx, field):
    replacement = "0" * 64 if field.endswith("hash") else "emps_" + "0" * 32
    with pytest.raises(EmphasisEventsContractError) as exc:
        _load_mutation(fx, lambda root: root.__setitem__(field, replacement))
    _error(exc, EmphasisEventsRejectionReason.IDENTITY_MISMATCH, "/")


def test_loader_multi_fault_precedence(fx):
    def unknown_before_missing(root):
        root["attacker_unknown"] = "secret"
        root.pop("project_id")

    with pytest.raises(EmphasisEventsContractError) as exc:
        _load_mutation(fx, unknown_before_missing)
    _error(exc, EmphasisEventsRejectionReason.STRUCTURE_INVALID, "/")

    def event_structure_before_literal(root):
        root["emphasis_events"][0]["ordinal"] = "0"
        root["emphasis_events"][0]["intensity"] = "ATTACKER_SECRET"

    with pytest.raises(EmphasisEventsContractError) as exc:
        _load_mutation(fx, event_structure_before_literal)
    _error(exc, EmphasisEventsRejectionReason.STRUCTURE_INVALID, "/emphasis_events/0")

    bad_intent = dataclasses.replace(
        fx[6][0],
        word_range=dataclasses.replace(
            fx[6][0].word_range, narration_revision_id="narrev_" + "0" * 20
        ),
    )
    with pytest.raises(EmphasisEventsContractError) as exc:
        load_emphasis_events(b"not-json", **_kwargs(fx, intents=(bad_intent,)))
    _error(
        exc,
        EmphasisEventsRejectionReason.WORD_RANGE_INVALID,
        "/intents/0",
        "WORD_RANGE_REVISION_MISMATCH",
    )


def test_loader_root_declaration_precedes_event_fault(fx):
    def mutate(root):
        root["project_id"] = "prj_attacker"
        root["emphasis_events"][0]["ordinal"] = 99
        root["emphasis_events"][0]["emphasis_event_hash"] = "0" * 64

    with pytest.raises(EmphasisEventsContractError) as exc:
        _load_mutation(fx, mutate)
    _error(
        exc,
        EmphasisEventsRejectionReason.DEPENDENCY_BINDING_INVALID,
        "/",
        "ALIGNMENT_REQUEST_IDENTITY_MISMATCH",
    )


def test_loader_event_semantics_precede_event_identity(fx):
    def mutate(root):
        event = root["emphasis_events"][0]
        event["start_ms"] = 101
        event["emphasis_event_hash"] = "0" * 64
        event["emphasis_event_id"] = "emph_" + "0" * 32

    with pytest.raises(EmphasisEventsContractError) as exc:
        _load_mutation(fx, mutate)
    _error(
        exc,
        EmphasisEventsRejectionReason.TIMING_INVALID,
        "/emphasis_events/0",
        "TIMESTAMP_NON_MONOTONIC",
    )


@pytest.mark.parametrize("scope", ["event", "root"])
def test_loader_hash_and_id_multi_fault_is_identity_mismatch(fx, scope):
    def mutate(root):
        target = root["emphasis_events"][0] if scope == "event" else root
        prefix = "emphasis_event" if scope == "event" else "emphasis_events"
        target[f"{prefix}_hash"] = "0" * 64
        target[f"{prefix}_id"] = ("emph_" if scope == "event" else "emps_") + "0" * 32

    with pytest.raises(EmphasisEventsContractError) as exc:
        _load_mutation(fx, mutate)
    _error(
        exc,
        EmphasisEventsRejectionReason.IDENTITY_MISMATCH,
        "/emphasis_events/0" if scope == "event" else "/",
    )


def test_loader_declares_hash_before_id_comparison_order_statically():
    source = inspect.getsource(load_emphasis_events)
    assert source.index('if actual["emphasis_event_hash"]') < source.index(
        'if actual["emphasis_event_id"]'
    )
    assert source.index('if value["emphasis_events_hash"]') < source.index(
        'if value["emphasis_events_id"]'
    )


def test_type_present_only_in_event_types_is_not_a_visual_grammar(fx):
    registry = fx[5]
    key = ("business-tech", "0.1.0")
    original = registry._packs[key]
    extensions = copy.deepcopy(original.raw_manifest["extensions"])
    extensions["event_types"] = [
        {"name": "audio_only", "version": "0.1.0", "description": "attacker policy secret"}
    ]
    raw_manifest = copy.deepcopy(original.raw_manifest)
    raw_manifest["extensions"] = extensions
    forged = dataclasses.replace(
        original,
        raw_manifest=raw_manifest,
        manifest=dataclasses.replace(original.manifest, extensions=copy.deepcopy(extensions)),
    )
    registry._packs[key] = forged
    try:
        profile = json.loads(
            (ROOT / "samples/v3/business-tech/domain/profile.json").read_text(encoding="utf-8")
        )
        snapshot, _ = DomainPolicyResolver(SchemaCatalog(ROOT / "schema" / "v3")).resolve(
            forged, profile
        )
        intent = dataclasses.replace(
            fx[6][0], emphasis_type_ref=EmphasisTypeRef("business-tech", "audio_only", "0.1.0")
        )
        with pytest.raises(EmphasisEventsContractError) as exc:
            compile_emphasis_events(
                **_kwargs(fx, domain_policy_snapshot=snapshot, intents=(intent,))
            )
        _error(exc, EmphasisEventsRejectionReason.POLICY_INVALID, "/intents/0")
        assert "audio_only" not in str(exc.value)
        assert "attacker policy secret" not in str(exc.value)
    finally:
        registry._packs[key] = original


def test_forged_registry_manifest_model_is_rejected(fx):
    registry = fx[5]
    key = ("business-tech", "0.1.0")
    pack = registry._packs[key]
    forged_manifest = dataclasses.replace(pack.manifest, domain_id="forged")
    registry._packs[key] = dataclasses.replace(pack, manifest=forged_manifest)
    try:
        with pytest.raises(EmphasisEventsContractError) as exc:
            compile_emphasis_events(**_kwargs(fx))
        _error(exc, EmphasisEventsRejectionReason.POLICY_INVALID, "/domain_policy_snapshot")
    finally:
        registry._packs[key] = pack


@pytest.mark.parametrize("mutation", ["events_list", "word_ids_list", "equal_type_ref"])
def test_recursive_equal_value_mutations_are_rejected(fx, mutation):
    artifact = compile_emphasis_events(**_kwargs(fx))
    event = artifact.emphasis_events[0]
    if mutation == "events_list":
        object.__setattr__(artifact, "emphasis_events", list(artifact.emphasis_events))
    elif mutation == "word_ids_list":
        object.__setattr__(event, "word_ids", list(event.word_ids))
    else:
        object.__setattr__(event, "emphasis_type_ref", dataclasses.replace(event.emphasis_type_ref))
    with pytest.raises(EmphasisEventsContractError) as exc:
        serialize_emphasis_events(artifact)
    _error(exc, EmphasisEventsRejectionReason.CONTENT_DRIFT, "/")


def test_registry_releases_artifact_and_does_not_retain_dependencies(fx):
    artifact = compile_emphasis_events(**_kwargs(fx))
    key = id(artifact)
    reference = weakref.ref(artifact)
    assert key in emphasis_contracts._MATERIALIZED
    del artifact
    gc.collect()
    assert reference() is None and key not in emphasis_contracts._MATERIALIZED


def test_registry_collision_rollback_and_stale_callback_safety(monkeypatch):
    local_fx = _build_fx()
    artifact = emphasis_contracts._compile(**_kwargs(local_fx))
    envelope = emphasis_contracts.encode_canonical_json_bytes(
        emphasis_contracts._artifact_dict(artifact)
    )
    materialized = {}
    monkeypatch.setattr(emphasis_contracts, "_MATERIALIZED", materialized)
    emphasis_contracts._register(artifact, envelope)
    with pytest.raises(RuntimeError, match="registry collision"):
        emphasis_contracts._register(artifact, envelope)

    class RejectingRegistry(dict):
        def __setitem__(self, key, value):
            raise KeyError("attacker filesystem credential secret")

    rejecting = RejectingRegistry()
    monkeypatch.setattr(emphasis_contracts, "_MATERIALIZED", rejecting)
    fresh = emphasis_contracts._compile(**_kwargs(local_fx))
    with pytest.raises(RuntimeError) as exc:
        emphasis_contracts._register(fresh, envelope)
    assert not rejecting
    assert "attacker" not in str(exc.value)
    assert "credential" not in str(exc.value)
    assert "secret" not in str(exc.value)

    replacement_registry = {}
    monkeypatch.setattr(emphasis_contracts, "_MATERIALIZED", replacement_registry)
    original = emphasis_contracts._compile(**_kwargs(local_fx))
    emphasis_contracts._register(original, envelope)
    key = id(original)
    old_reference = replacement_registry[key][0]
    replacement = emphasis_contracts._compile(**_kwargs(local_fx))
    replacement_entry = (
        weakref.ref(replacement),
        b"replacement",
        emphasis_contracts._identity_signature(replacement),
    )
    replacement_registry[key] = replacement_entry
    del original
    gc.collect()
    assert old_reference() is None
    assert replacement_registry[key] is replacement_entry


def test_artifact_does_not_retain_dependencies_or_caller_values():
    def materialize_with_references():
        local_fx = _build_fx()
        tracked = [*local_fx[:6], local_fx[6][0], local_fx[6][0].word_range, local_fx[6][0].emphasis_type_ref]
        references = [weakref.ref(value) for value in tracked]
        artifact = compile_emphasis_events(**_kwargs(local_fx))
        return artifact, references

    artifact, references = materialize_with_references()
    gc.collect()
    assert all(reference() is None for reference in references)
    assert serialize_emphasis_events(artifact) == GOLDEN_BYTES


def test_direct_unregistered_artifact_has_closed_not_materialized_oracle(fx):
    artifact = emphasis_contracts._compile(**_kwargs(fx))
    with pytest.raises(EmphasisEventsContractError) as exc:
        serialize_emphasis_events(artifact)
    _error(exc, EmphasisEventsRejectionReason.NOT_MATERIALIZED, "/")


def test_registry_and_attacker_policy_failures_do_not_leak_payloads(fx, monkeypatch):
    secret = "C:/attacker/private/key.txt?credential=secret"

    def fail_get(*args, **kwargs):
        raise RuntimeError(secret)

    monkeypatch.setattr(DomainPackRegistry, "get", fail_get)
    with pytest.raises(EmphasisEventsContractError) as exc:
        compile_emphasis_events(**_kwargs(fx))
    _error(exc, EmphasisEventsRejectionReason.POLICY_INVALID, "/domain_policy_snapshot")
    assert secret not in str(exc.value)
    assert "credential" not in str(exc.value)
    assert "private" not in str(exc.value)


def test_static_import_and_no_string_search_boundary():
    source = (ROOT / "engine/contracts/emphasis_events.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert not any(any(part in name for part in ("provider", "fastapi", "renderer", "frame", "v2", "requests")) for name in imports)
    assert "text_span" not in source
    assert ".find(" not in source and "re.search" not in source
    assert "open(" not in source and "Path(" not in source
