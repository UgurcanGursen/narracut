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
from engine.contracts import (
    EMPHASIS_EVENT_HASH_V1,
    EMPHASIS_EVENT_V1,
    EMPHASIS_EVENTS_HASH_V1,
    EMPHASIS_EVENTS_V1,
    EMPHASIS_MAPPING_POLICY_V1,
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


ROOT = Path(__file__).resolve().parents[1]
GOLDEN_HASH = "e6286517914a305715e42460d27092370bf304f6715e28a6c483407758a04b7d"
GOLDEN_ID = "emps_e6286517914a305715e42460d2709237"
GOLDEN_EVENT_HASH = "3b919932a4e05683fe94c9eae048341b705259b7dcacfb8d552f9ca6531437d5"
GOLDEN_EVENT_ID = "emph_3b919932a4e05683fe94c9eae048341b"
GOLDEN_ENVELOPE_SHA = "008e79e10b989f54377af498c269eca00df09b426b4d8a0ec86441e55a13111c"
GOLDEN_BYTES = b'{"alignment_result_hash":"1521f195a591df09edaa968d8f5fa91ed367be1c7190a3f614823d74b3cd36bb","alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","caption_groups_hash":"12670fe861389bfe8e25f05a126c7ea355c361c2b2848e9b02a216ed83baaec7","caption_groups_id":"cgs_12670fe861389bfe8e25f05a126c7ea3","confidence_availability":"AVAILABLE","document_id":"nardoc_fx34","domain_id":"business-tech","domain_pack_version":"0.1.0","emphasis_events":[{"alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","caption_group_id":"cgrp_2bdd1bc0e985d5d45784956cb0818fb9","caption_groups_id":"cgs_12670fe861389bfe8e25f05a126c7ea3","confidence_millionths":960000,"emphasis_event_hash":"3b919932a4e05683fe94c9eae048341b705259b7dcacfb8d552f9ca6531437d5","emphasis_event_id":"emph_3b919932a4e05683fe94c9eae048341b","emphasis_type_ref":{"domain_id":"business-tech","name":"earnings_sting","version":"0.1.0"},"end_exclusive_word_ordinal":2,"end_ms":900,"end_word_id":"nword_0cc9d55672a3cb4e9199","hash_scope_version":"EMPHASIS-EVENT-HASH-V1","intensity":"STRONG","mapping_policy_version":"EMPHASIS-MAPPING-POLICY-V1","narration_revision_id":"narrev_d60d7ae087efb0e309d4","ordinal":0,"policy_snapshot_hash":"sha256:d18e9981c3f4bcca8e3f5a8f62c838d0e0ecbd14e6cd229e2702c08e2a3f3f2c","policy_snapshot_id":"dps_d18e9981c3f4bcca8e3f","schema_version":"EMPHASIS-EVENT-V1","start_ms":100,"start_word_id":"nword_5321ba14c2c4b28c31ab","start_word_ordinal":0,"word_ids":["nword_5321ba14c2c4b28c31ab","nword_0cc9d55672a3cb4e9199"]}],"emphasis_events_hash":"e6286517914a305715e42460d27092370bf304f6715e28a6c483407758a04b7d","emphasis_events_id":"emps_e6286517914a305715e42460d2709237","hash_scope_version":"EMPHASIS-EVENTS-HASH-V1","mapping_policy_version":"EMPHASIS-MAPPING-POLICY-V1","narration_revision_hash":"sha256:d60d7ae087efb0e309d4e3f28fedea074d15e11405046249a23b2c7bb42fe0c0","narration_revision_id":"narrev_d60d7ae087efb0e309d4","policy_snapshot_hash":"sha256:d18e9981c3f4bcca8e3f5a8f62c838d0e0ecbd14e6cd229e2702c08e2a3f3f2c","policy_snapshot_id":"dps_d18e9981c3f4bcca8e3f","project_id":"prj_fx34","schema_version":"EMPHASIS-EVENTS-V1"}'


@pytest.fixture(scope="module")
def fx():
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


def test_public_shape_and_exact_exports():
    assert [EMPHASIS_EVENT_V1, EMPHASIS_EVENT_HASH_V1, EMPHASIS_EVENTS_V1, EMPHASIS_EVENTS_HASH_V1, EMPHASIS_MAPPING_POLICY_V1] == [
        "EMPHASIS-EVENT-V1", "EMPHASIS-EVENT-HASH-V1", "EMPHASIS-EVENTS-V1",
        "EMPHASIS-EVENTS-HASH-V1", "EMPHASIS-MAPPING-POLICY-V1",
    ]
    assert [x.value for x in EmphasisIntensity] == ["SUBTLE", "MEDIUM", "STRONG"]
    assert len(EmphasisEventsRejectionReason) == 16
    assert [f.name for f in dataclasses.fields(EmphasisTypeRef)] == ["domain_id", "name", "version"]
    assert [f.name for f in dataclasses.fields(EmphasisIntent)] == ["word_range", "emphasis_type_ref", "intensity"]
    assert len(dataclasses.fields(EmphasisEvent)) == 22
    assert len(dataclasses.fields(EmphasisEventsArtifact)) == 19
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
    assert serialize_emphasis_events(first) == serialize_emphasis_events(second)


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


def test_static_import_and_no_string_search_boundary():
    source = (ROOT / "engine/contracts/emphasis_events.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert not any(any(part in name for part in ("provider", "fastapi", "renderer", "frame", "v2", "requests")) for name in imports)
    assert "text_span" not in source
    assert ".find(" not in source and "re.search" not in source
    assert "open(" not in source and "Path(" not in source
