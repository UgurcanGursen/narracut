from __future__ import annotations

import ast
import copy
import dataclasses
import gc
import hashlib
import inspect
import json
import weakref

import pytest

import engine.contracts as contracts
import engine.contracts.caption_groups as caption_contracts
from engine.contracts import (
    CAPTION_GROUP_HASH_V1,
    CAPTION_GROUP_V1,
    CAPTION_GROUPS_HASH_V1,
    CAPTION_GROUPS_V1,
    PHRASE_GROUPING_POLICY_V1,
    CaptionGroup,
    CaptionGroupWordCountPolicy,
    CaptionGroupingRejectionReason,
    CaptionGroupsArtifact,
    CaptionGroupsContractError,
    compile_caption_groups,
    load_caption_groups,
    serialize_caption_groups,
)
from tests.test_alignment_result import _dependencies, _materialize, _result_value


GOLDEN_HASH = "12670fe861389bfe8e25f05a126c7ea355c361c2b2848e9b02a216ed83baaec7"
GOLDEN_ID = "cgs_12670fe861389bfe8e25f05a126c7ea3"
GOLDEN_ENVELOPE_SHA256 = "fec81a32ef81b7ac4fb785b059d1f713edb90ea91197f72cd8a22992941da942"
GOLDEN_BYTES = b'{"alignment_result_hash":"1521f195a591df09edaa968d8f5fa91ed367be1c7190a3f614823d74b3cd36bb","alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","caption_groups":[{"alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","caption_group_hash":"2bdd1bc0e985d5d45784956cb0818fb9c4333d0dea5adf907edb4cebf9e9b8fb","caption_group_id":"cgrp_2bdd1bc0e985d5d45784956cb0818fb9","confidence_millionths":960000,"display_text":"Alpha beta.","end_exclusive_word_ordinal":2,"end_ms":900,"end_word_id":"nword_0cc9d55672a3cb4e9199","grouping_policy_version":"PHRASE-GROUPING-POLICY-V1","hash_scope_version":"CAPTION-GROUP-HASH-V1","narration_revision_id":"narrev_d60d7ae087efb0e309d4","ordinal":0,"schema_version":"CAPTION-GROUP-V1","sentence_id":"nsen_626e5f802472c1d68a83","start_ms":100,"start_word_id":"nword_5321ba14c2c4b28c31ab","start_word_ordinal":0,"word_count_policy":"SHORT_SENTENCE_1_TO_3","word_ids":["nword_5321ba14c2c4b28c31ab","nword_0cc9d55672a3cb4e9199"]},{"alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","caption_group_hash":"5b9b84abe4eba87d448e56b87ff277d6b7739a7dcef152c3098d0f289be1f613","caption_group_id":"cgrp_5b9b84abe4eba87d448e56b87ff277d6","confidence_millionths":920000,"display_text":"Gamma delta.","end_exclusive_word_ordinal":4,"end_ms":2300,"end_word_id":"nword_d81fe913754f8b49c296","grouping_policy_version":"PHRASE-GROUPING-POLICY-V1","hash_scope_version":"CAPTION-GROUP-HASH-V1","narration_revision_id":"narrev_d60d7ae087efb0e309d4","ordinal":1,"schema_version":"CAPTION-GROUP-V1","sentence_id":"nsen_154597301f10fae98161","start_ms":1200,"start_word_id":"nword_49e85bb034c88ef36f26","start_word_ordinal":2,"word_count_policy":"SHORT_SENTENCE_1_TO_3","word_ids":["nword_49e85bb034c88ef36f26","nword_d81fe913754f8b49c296"]}],"caption_groups_hash":"12670fe861389bfe8e25f05a126c7ea355c361c2b2848e9b02a216ed83baaec7","caption_groups_id":"cgs_12670fe861389bfe8e25f05a126c7ea3","confidence_availability":"AVAILABLE","document_id":"nardoc_fx34","grouping_policy_version":"PHRASE-GROUPING-POLICY-V1","hash_scope_version":"CAPTION-GROUPS-HASH-V1","narration_revision_hash":"sha256:d60d7ae087efb0e309d4e3f28fedea074d15e11405046249a23b2c7bb42fe0c0","narration_revision_id":"narrev_d60d7ae087efb0e309d4","project_id":"prj_fx34","schema_version":"CAPTION-GROUPS-V1"}'


@pytest.fixture(scope="module")
def fx():
    dependencies = _dependencies()
    result = _materialize(_result_value(dependencies), dependencies)
    _, document, revision, *_ = dependencies
    return document, revision, result


def _compile(fx):
    document, revision, result = fx
    return compile_caption_groups(
        narration_document=document,
        narration_revision=revision,
        alignment_result=result,
    )


def _load(source: bytes, fx):
    document, revision, result = fx
    return load_caption_groups(
        source,
        narration_document=document,
        narration_revision=revision,
        alignment_result=result,
    )


def _canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()


def _assert_error(error, pointer, reason, issue=None):
    assert type(error.value) is CaptionGroupsContractError
    assert str(error.value) == f"Caption groups rejected: {reason.value}"
    assert error.value.pointer == pointer
    assert error.value.reason is reason
    assert error.value.issue_code == issue


def test_public_api_shape_is_exact() -> None:
    assert CAPTION_GROUP_V1 == "CAPTION-GROUP-V1"
    assert CAPTION_GROUP_HASH_V1 == "CAPTION-GROUP-HASH-V1"
    assert CAPTION_GROUPS_V1 == "CAPTION-GROUPS-V1"
    assert CAPTION_GROUPS_HASH_V1 == "CAPTION-GROUPS-HASH-V1"
    assert PHRASE_GROUPING_POLICY_V1 == "PHRASE-GROUPING-POLICY-V1"
    assert [item.value for item in CaptionGroupWordCountPolicy] == [
        "PREFERRED_4_TO_9", "SHORT_SENTENCE_1_TO_3"
    ]
    assert [item.value for item in CaptionGroupingRejectionReason] == [
        "STRUCTURE_INVALID", "UNSUPPORTED_VALUE", "DEPENDENCY_CONTENT_DRIFT",
        "DEPENDENCY_BINDING_INVALID", "CANONICAL_COVERAGE_INVALID",
        "GROUPING_POLICY_INVALID", "DISPLAY_TEXT_INVALID", "TIMING_INVALID",
        "CONFIDENCE_INVALID", "NON_CANONICAL_SERIALIZATION", "IDENTITY_MISMATCH",
        "CONTENT_DRIFT", "NOT_MATERIALIZED",
    ]
    assert [field.name for field in dataclasses.fields(CaptionGroup)] == list(caption_contracts._GROUP_FIELDS)
    assert [field.name for field in dataclasses.fields(CaptionGroupsArtifact)] == list(caption_contracts._ROOT_FIELDS)
    assert list(inspect.signature(compile_caption_groups).parameters) == [
        "narration_document", "narration_revision", "alignment_result"
    ]
    assert list(inspect.signature(load_caption_groups).parameters) == [
        "source", "narration_document", "narration_revision", "alignment_result"
    ]
    assert list(inspect.signature(serialize_caption_groups).parameters) == ["artifact"]


def test_exact_public_export_delta_and_private_non_exports() -> None:
    expected = {
        "CAPTION_GROUP_V1", "CAPTION_GROUP_HASH_V1", "CAPTION_GROUPS_V1",
        "CAPTION_GROUPS_HASH_V1", "PHRASE_GROUPING_POLICY_V1",
        "CaptionGroupWordCountPolicy", "CaptionGroupingRejectionReason",
        "CaptionGroup", "CaptionGroupsArtifact", "CaptionGroupsContractError",
        "compile_caption_groups", "load_caption_groups", "serialize_caption_groups",
    }
    assert expected <= set(contracts.__all__)
    for name in ("_partition_sizes", "_MATERIALIZED_CAPTION_GROUPS", "_derive", "_hash"):
        assert name not in contracts.__all__
        assert not hasattr(contracts, name)


def test_fx_cgs_01_exact_literal_bytes_hashes_ids_and_round_trip(fx) -> None:
    artifact = _compile(fx)
    assert artifact.caption_groups_hash == GOLDEN_HASH
    assert artifact.caption_groups_id == GOLDEN_ID
    assert len(GOLDEN_BYTES) == 2300
    assert hashlib.sha256(GOLDEN_BYTES).hexdigest() == GOLDEN_ENVELOPE_SHA256
    assert serialize_caption_groups(artifact) == GOLDEN_BYTES
    loaded = _load(GOLDEN_BYTES, fx)
    assert loaded == artifact
    assert serialize_caption_groups(loaded) == GOLDEN_BYTES
    assert _compile(fx) == artifact


def test_golden_group_projection_and_envelope_evidence(fx) -> None:
    artifact = _compile(fx)
    expected = (
        (650, "2bdd1bc0e985d5d45784956cb0818fb9c4333d0dea5adf907edb4cebf9e9b8fb", 797, "22e4b1a9d645a81366aa58cd26e7e10de215912926d3f3d4d78663d88c375ee4"),
        (653, "5b9b84abe4eba87d448e56b87ff277d6b7739a7dcef152c3098d0f289be1f613", 800, "465cb62737661567909dbf918870888ba37647d57e03771dbad39282f9855808"),
    )
    for group, evidence in zip(artifact.caption_groups, expected):
        projection = _canonical(caption_contracts._group_projection(group))
        envelope = _canonical(caption_contracts._group_envelope(group))
        assert (len(projection), hashlib.sha256(projection).hexdigest(), len(envelope), hashlib.sha256(envelope).hexdigest()) == evidence


@pytest.mark.parametrize("length", range(1, 1001))
def test_partition_is_total_deterministic_and_remainder_safe(length: int) -> None:
    first = caption_contracts._partition_sizes(length, 0, {})
    second = caption_contracts._partition_sizes(length, 0, {})
    assert first == second
    assert sum(first) == length
    if length <= 3:
        assert first == (length,)
    else:
        assert all(4 <= size <= 9 for size in first)


@pytest.mark.parametrize("length", range(4, 25))
def test_partition_exhaustive_legal_window(length: int) -> None:
    sizes = caption_contracts._partition_sizes(length, 17, {})
    assert sum(sizes) == length
    assert all(4 <= size <= 9 for size in sizes)


def test_boundary_rank_target_distance_and_larger_tie_break() -> None:
    assert caption_contracts._partition_sizes(10, 0, {}) == (6, 4)
    assert caption_contracts._partition_sizes(10, 0, {3: 0}) == (4, 6)
    assert caption_contracts._partition_sizes(11, 0, {4: 1, 6: 1}) == (7, 4)
    assert caption_contracts._partition_sizes(12, 0, {4: 0, 5: 0, 6: 0}) == (6, 6)


@pytest.mark.parametrize("mode", ["wrong_type", "copy"])
def test_wrong_or_non_genuine_dependencies_raise_sanitized_type_error(fx, mode) -> None:
    document, revision, result = fx
    bad_result = object() if mode == "wrong_type" else copy.copy(result)
    with pytest.raises(TypeError) as error:
        compile_caption_groups(
            narration_document=document,
            narration_revision=revision,
            alignment_result=bad_result,
        )
    assert "genuine exact dependency" in str(error.value)


@pytest.mark.parametrize(
    "source",
    [b"", b"{}\n", b"\xef\xbb\xbf{}", b'{"a":1,"a":2}', b'{"x":1.0}', b"\xff"],
)
def test_noncanonical_wire_inputs_have_one_closed_outcome(source: bytes, fx) -> None:
    with pytest.raises(CaptionGroupsContractError) as error:
        _load(source, fx)
    _assert_error(error, "/", CaptionGroupingRejectionReason.NON_CANONICAL_SERIALIZATION)


def test_loader_requires_exact_bytes_after_dependency_preflight(fx) -> None:
    with pytest.raises(TypeError, match="exact bytes"):
        _load(bytearray(GOLDEN_BYTES), fx)


@pytest.mark.parametrize(
    ("mutator", "pointer", "reason", "issue"),
    [
        (lambda v: v.update(extra="x"), "/", CaptionGroupingRejectionReason.STRUCTURE_INVALID, None),
        (lambda v: v.pop("project_id"), "/", CaptionGroupingRejectionReason.STRUCTURE_INVALID, None),
        (lambda v: v.update(schema_version="OTHER"), "/", CaptionGroupingRejectionReason.UNSUPPORTED_VALUE, "UNSUPPORTED_CONTRACT_ENUM"),
        (lambda v: v.update(project_id="prj_other"), "/", CaptionGroupingRejectionReason.DEPENDENCY_BINDING_INVALID, "ALIGNMENT_REQUEST_IDENTITY_MISMATCH"),
        (lambda v: v.update(confidence_availability="UNAVAILABLE"), "/", CaptionGroupingRejectionReason.CONFIDENCE_INVALID, "ADAPTER_PRECISION_OVERSTATED"),
        (lambda v: v.update(caption_groups=[]), "/caption_groups", CaptionGroupingRejectionReason.CANONICAL_COVERAGE_INVALID, "CANONICAL_COVERAGE_BLOCKER"),
        (lambda v: v["caption_groups"][0].update(ordinal=1), "/caption_groups/0", CaptionGroupingRejectionReason.GROUPING_POLICY_INVALID, "CANONICAL_WORD_ORDER_INVALID"),
        (lambda v: v["caption_groups"][0].update(start_word_ordinal=2, end_exclusive_word_ordinal=1), "/caption_groups/0", CaptionGroupingRejectionReason.CANONICAL_COVERAGE_INVALID, "WORD_RANGE_REVERSED"),
        (lambda v: v["caption_groups"][0].update(start_word_ordinal=0, end_exclusive_word_ordinal=0), "/caption_groups/0", CaptionGroupingRejectionReason.CANONICAL_COVERAGE_INVALID, "WORD_RANGE_OUT_OF_BOUNDS"),
        (lambda v: v["caption_groups"][0].update(display_text="changed"), "/caption_groups/0", CaptionGroupingRejectionReason.DISPLAY_TEXT_INVALID, None),
        (lambda v: v["caption_groups"][0].update(start_ms=101), "/caption_groups/0", CaptionGroupingRejectionReason.TIMING_INVALID, "TIMESTAMP_NON_MONOTONIC"),
        (lambda v: v["caption_groups"][0].update(confidence_millionths=None), "/caption_groups/0", CaptionGroupingRejectionReason.CONFIDENCE_INVALID, "CONFIDENCE_REQUIRED_UNAVAILABLE"),
        (lambda v: v["caption_groups"][0].update(caption_group_hash="0" * 64), "/caption_groups/0", CaptionGroupingRejectionReason.IDENTITY_MISMATCH, None),
        (lambda v: v.update(caption_groups_hash="0" * 64), "/", CaptionGroupingRejectionReason.IDENTITY_MISMATCH, None),
        (lambda v: v.update(caption_groups_id="cgs_" + "0" * 32), "/", CaptionGroupingRejectionReason.IDENTITY_MISMATCH, None),
    ],
)
def test_closed_loader_oracle_representative_rows(mutator, pointer, reason, issue, fx) -> None:
    value = json.loads(GOLDEN_BYTES)
    mutator(value)
    with pytest.raises(CaptionGroupsContractError) as error:
        _load(_canonical(value), fx)
    _assert_error(error, pointer, reason, issue)


def test_unknown_key_precedes_missing_and_lower_group_index_wins(fx) -> None:
    value = json.loads(GOLDEN_BYTES)
    value.pop("project_id")
    value["attacker-secret"] = "do-not-echo"
    value["caption_groups"][0]["attacker-secret"] = "first"
    value["caption_groups"][1]["attacker-secret"] = "second"
    with pytest.raises(CaptionGroupsContractError) as error:
        _load(_canonical(value), fx)
    _assert_error(error, "/", CaptionGroupingRejectionReason.STRUCTURE_INVALID)
    assert "attacker" not in str(error.value)


def test_serialization_is_provenance_bound_mutation_resistant_and_collectable(fx) -> None:
    artifact = _compile(fx)
    clone = dataclasses.replace(artifact)
    with pytest.raises(CaptionGroupsContractError) as error:
        serialize_caption_groups(clone)
    _assert_error(error, "/", CaptionGroupingRejectionReason.NOT_MATERIALIZED)

    object.__setattr__(artifact, "caption_groups_hash", "0" * 64)
    with pytest.raises(CaptionGroupsContractError) as error:
        serialize_caption_groups(artifact)
    _assert_error(error, "/", CaptionGroupingRejectionReason.CONTENT_DRIFT)

    fresh = _compile(fx)
    identity = id(fresh)
    reference = weakref.ref(fresh)
    assert identity in caption_contracts._MATERIALIZED_CAPTION_GROUPS
    del fresh
    for _ in range(5):
        gc.collect()
    assert reference() is None
    assert identity not in caption_contracts._MATERIALIZED_CAPTION_GROUPS


def test_static_import_boundary_and_no_io_or_runtime_dependencies() -> None:
    source = inspect.getsource(caption_contracts)
    tree = ast.parse(source)
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    forbidden = {
        "requests", "httpx", "socket", "pathlib", "os", "subprocess", "threading",
        "time", "random", "fastapi", "v2", "renderer", "remotion", "ffmpeg",
    }
    assert not (imports & forbidden)
    assert "open(" not in source
    assert "Path(" not in source
