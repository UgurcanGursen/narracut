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
GOLDEN_GROUP_PROJECTIONS = (
    b'{"alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","confidence_millionths":960000,"display_text":"Alpha beta.","end_exclusive_word_ordinal":2,"end_ms":900,"end_word_id":"nword_0cc9d55672a3cb4e9199","grouping_policy_version":"PHRASE-GROUPING-POLICY-V1","hash_scope_version":"CAPTION-GROUP-HASH-V1","narration_revision_id":"narrev_d60d7ae087efb0e309d4","ordinal":0,"schema_version":"CAPTION-GROUP-V1","sentence_id":"nsen_626e5f802472c1d68a83","start_ms":100,"start_word_id":"nword_5321ba14c2c4b28c31ab","start_word_ordinal":0,"word_count_policy":"SHORT_SENTENCE_1_TO_3","word_ids":["nword_5321ba14c2c4b28c31ab","nword_0cc9d55672a3cb4e9199"]}',
    b'{"alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","confidence_millionths":920000,"display_text":"Gamma delta.","end_exclusive_word_ordinal":4,"end_ms":2300,"end_word_id":"nword_d81fe913754f8b49c296","grouping_policy_version":"PHRASE-GROUPING-POLICY-V1","hash_scope_version":"CAPTION-GROUP-HASH-V1","narration_revision_id":"narrev_d60d7ae087efb0e309d4","ordinal":1,"schema_version":"CAPTION-GROUP-V1","sentence_id":"nsen_154597301f10fae98161","start_ms":1200,"start_word_id":"nword_49e85bb034c88ef36f26","start_word_ordinal":2,"word_count_policy":"SHORT_SENTENCE_1_TO_3","word_ids":["nword_49e85bb034c88ef36f26","nword_d81fe913754f8b49c296"]}',
)
GOLDEN_GROUP_ENVELOPES = (
    b'{"alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","caption_group_hash":"2bdd1bc0e985d5d45784956cb0818fb9c4333d0dea5adf907edb4cebf9e9b8fb","caption_group_id":"cgrp_2bdd1bc0e985d5d45784956cb0818fb9","confidence_millionths":960000,"display_text":"Alpha beta.","end_exclusive_word_ordinal":2,"end_ms":900,"end_word_id":"nword_0cc9d55672a3cb4e9199","grouping_policy_version":"PHRASE-GROUPING-POLICY-V1","hash_scope_version":"CAPTION-GROUP-HASH-V1","narration_revision_id":"narrev_d60d7ae087efb0e309d4","ordinal":0,"schema_version":"CAPTION-GROUP-V1","sentence_id":"nsen_626e5f802472c1d68a83","start_ms":100,"start_word_id":"nword_5321ba14c2c4b28c31ab","start_word_ordinal":0,"word_count_policy":"SHORT_SENTENCE_1_TO_3","word_ids":["nword_5321ba14c2c4b28c31ab","nword_0cc9d55672a3cb4e9199"]}',
    b'{"alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","caption_group_hash":"5b9b84abe4eba87d448e56b87ff277d6b7739a7dcef152c3098d0f289be1f613","caption_group_id":"cgrp_5b9b84abe4eba87d448e56b87ff277d6","confidence_millionths":920000,"display_text":"Gamma delta.","end_exclusive_word_ordinal":4,"end_ms":2300,"end_word_id":"nword_d81fe913754f8b49c296","grouping_policy_version":"PHRASE-GROUPING-POLICY-V1","hash_scope_version":"CAPTION-GROUP-HASH-V1","narration_revision_id":"narrev_d60d7ae087efb0e309d4","ordinal":1,"schema_version":"CAPTION-GROUP-V1","sentence_id":"nsen_154597301f10fae98161","start_ms":1200,"start_word_id":"nword_49e85bb034c88ef36f26","start_word_ordinal":2,"word_count_policy":"SHORT_SENTENCE_1_TO_3","word_ids":["nword_49e85bb034c88ef36f26","nword_d81fe913754f8b49c296"]}',
)
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
    for index, (group, evidence) in enumerate(zip(artifact.caption_groups, expected)):
        projection = _canonical(caption_contracts._group_projection(group))
        envelope = _canonical(caption_contracts._group_envelope(group))
        assert projection == GOLDEN_GROUP_PROJECTIONS[index]
        assert envelope == GOLDEN_GROUP_ENVELOPES[index]
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


@pytest.mark.parametrize("source", [b"[]", b"1", b"null", b'"x"'])
def test_canonical_non_object_roots_are_structure_invalid(source: bytes, fx) -> None:
    with pytest.raises(CaptionGroupsContractError) as error:
        _load(source, fx)
    _assert_error(error, "/", CaptionGroupingRejectionReason.STRUCTURE_INVALID)


@pytest.mark.parametrize(
    ("row", "mutator", "pointer", "reason", "issue"),
    [
        (6, lambda v: v.update(extra="x"), "/", CaptionGroupingRejectionReason.STRUCTURE_INVALID, None),
        (6, lambda v: v.pop("project_id"), "/", CaptionGroupingRejectionReason.STRUCTURE_INVALID, None),
        (6, lambda v: v.update(project_id=1), "/", CaptionGroupingRejectionReason.STRUCTURE_INVALID, None),
        (7, lambda v: v.update(caption_groups={}), "/caption_groups", CaptionGroupingRejectionReason.STRUCTURE_INVALID, None),
        (8, lambda v: v["caption_groups"].__setitem__(0, []), "/caption_groups/0", CaptionGroupingRejectionReason.STRUCTURE_INVALID, None),
        (8, lambda v: v["caption_groups"][0].update(extra="x"), "/caption_groups/0", CaptionGroupingRejectionReason.STRUCTURE_INVALID, None),
        (9, lambda v: v.update(caption_groups_hash="Z" * 64), "/", CaptionGroupingRejectionReason.STRUCTURE_INVALID, None),
        (10, lambda v: v["caption_groups"][0].update(caption_group_hash="Z" * 64), "/caption_groups/0", CaptionGroupingRejectionReason.STRUCTURE_INVALID, None),
        (11, lambda v: v["caption_groups"][0].update(display_text=""), "/caption_groups/0", CaptionGroupingRejectionReason.DISPLAY_TEXT_INVALID, None),
        (12, lambda v: v.update(schema_version="OTHER"), "/", CaptionGroupingRejectionReason.UNSUPPORTED_VALUE, "UNSUPPORTED_CONTRACT_ENUM"),
        (13, lambda v: v["caption_groups"][0].update(schema_version="OTHER"), "/caption_groups/0", CaptionGroupingRejectionReason.UNSUPPORTED_VALUE, "UNSUPPORTED_CONTRACT_ENUM"),
        (14, lambda v: v.update(project_id="prj_other"), "/", CaptionGroupingRejectionReason.DEPENDENCY_BINDING_INVALID, "ALIGNMENT_REQUEST_IDENTITY_MISMATCH"),
        (15, lambda v: v.update(confidence_availability="UNAVAILABLE"), "/", CaptionGroupingRejectionReason.CONFIDENCE_INVALID, "ADAPTER_PRECISION_OVERSTATED"),
        (16, lambda v: v.update(caption_groups=[]), "/caption_groups", CaptionGroupingRejectionReason.CANONICAL_COVERAGE_INVALID, "CANONICAL_COVERAGE_BLOCKER"),
        (17, lambda v: v["caption_groups"][0].update(narration_revision_id="narrev_other"), "/caption_groups/0", CaptionGroupingRejectionReason.DEPENDENCY_BINDING_INVALID, "ALIGNMENT_REQUEST_IDENTITY_MISMATCH"),
        (18, lambda v: v["caption_groups"][0].update(ordinal=1), "/caption_groups/0", CaptionGroupingRejectionReason.GROUPING_POLICY_INVALID, "CANONICAL_WORD_ORDER_INVALID"),
        (19, lambda v: v["caption_groups"][0].update(start_word_ordinal=2, end_exclusive_word_ordinal=1), "/caption_groups/0", CaptionGroupingRejectionReason.CANONICAL_COVERAGE_INVALID, "WORD_RANGE_REVERSED"),
        (20, lambda v: v["caption_groups"][0].update(start_word_ordinal=0, end_exclusive_word_ordinal=0), "/caption_groups/0", CaptionGroupingRejectionReason.CANONICAL_COVERAGE_INVALID, "WORD_RANGE_OUT_OF_BOUNDS"),
        (21, lambda v: v["caption_groups"][0].update(start_word_ordinal=1), "/caption_groups/0", CaptionGroupingRejectionReason.CANONICAL_COVERAGE_INVALID, "CANONICAL_COVERAGE_BLOCKER"),
        (22, lambda v: v["caption_groups"][1].update(start_word_ordinal=3), "/caption_groups/1", CaptionGroupingRejectionReason.CANONICAL_COVERAGE_INVALID, "CANONICAL_COVERAGE_BLOCKER"),
        (23, lambda v: v["caption_groups"][1].update(start_word_ordinal=1), "/caption_groups/1", CaptionGroupingRejectionReason.CANONICAL_COVERAGE_INVALID, "CANONICAL_COVERAGE_BLOCKER"),
        (24, lambda v: v["caption_groups"][1].update(end_exclusive_word_ordinal=3), "/caption_groups/1", CaptionGroupingRejectionReason.CANONICAL_COVERAGE_INVALID, "CANONICAL_COVERAGE_BLOCKER"),
        (25, lambda v: v["caption_groups"][0].update(word_ids=[]), "/caption_groups/0", CaptionGroupingRejectionReason.CANONICAL_COVERAGE_INVALID, "CANONICAL_COVERAGE_BLOCKER"),
        (26, lambda v: v["caption_groups"][0].update(start_word_id="nword_other"), "/caption_groups/0", CaptionGroupingRejectionReason.CANONICAL_COVERAGE_INVALID, "CANONICAL_COVERAGE_BLOCKER"),
        (27, lambda v: v["caption_groups"][0].update(end_word_id="nword_other"), "/caption_groups/0", CaptionGroupingRejectionReason.CANONICAL_COVERAGE_INVALID, "CANONICAL_COVERAGE_BLOCKER"),
        (28, lambda v: v["caption_groups"][0].update(word_ids=list(reversed(v["caption_groups"][0]["word_ids"]))), "/caption_groups/0", CaptionGroupingRejectionReason.CANONICAL_COVERAGE_INVALID, "CANONICAL_WORD_ORDER_INVALID"),
        (29, lambda v: v["caption_groups"][0]["word_ids"].__setitem__(0, "nword_other"), "/caption_groups/0", CaptionGroupingRejectionReason.CANONICAL_COVERAGE_INVALID, "CANONICAL_COVERAGE_BLOCKER"),
        (30, lambda v: v["caption_groups"][0].update(sentence_id="nsen_other"), "/caption_groups/0", CaptionGroupingRejectionReason.GROUPING_POLICY_INVALID, "CANONICAL_COVERAGE_BLOCKER"),
        (33, lambda v: v["caption_groups"][0].update(word_count_policy="PREFERRED_4_TO_9"), "/caption_groups/0", CaptionGroupingRejectionReason.GROUPING_POLICY_INVALID, "CANONICAL_COVERAGE_BLOCKER"),
        (35, lambda v: v["caption_groups"][0].update(display_text="changed"), "/caption_groups/0", CaptionGroupingRejectionReason.DISPLAY_TEXT_INVALID, None),
        (36, lambda v: v["caption_groups"][0].update(start_ms=101), "/caption_groups/0", CaptionGroupingRejectionReason.TIMING_INVALID, "TIMESTAMP_NON_MONOTONIC"),
        (37, lambda v: v["caption_groups"][0].update(end_ms=899), "/caption_groups/0", CaptionGroupingRejectionReason.TIMING_INVALID, "TIMESTAMP_NON_MONOTONIC"),
        (38, lambda v: v["caption_groups"][0].update(confidence_millionths=None), "/caption_groups/0", CaptionGroupingRejectionReason.CONFIDENCE_INVALID, "CONFIDENCE_REQUIRED_UNAVAILABLE"),
        (39, lambda v: v["caption_groups"][0].update(confidence_millionths=1), "/caption_groups/0", CaptionGroupingRejectionReason.CONFIDENCE_INVALID, "ADAPTER_PRECISION_OVERSTATED"),
        (40, lambda v: v["caption_groups"][0].update(caption_group_hash="0" * 64), "/caption_groups/0", CaptionGroupingRejectionReason.IDENTITY_MISMATCH, None),
        (41, lambda v: v.update(caption_groups_hash="0" * 64), "/", CaptionGroupingRejectionReason.IDENTITY_MISMATCH, None),
        (42, lambda v: v.update(caption_groups_id="cgs_" + "0" * 32), "/", CaptionGroupingRejectionReason.IDENTITY_MISMATCH, None),
    ],
)
def test_closed_loader_oracle_rows(row, mutator, pointer, reason, issue, fx) -> None:
    value = json.loads(GOLDEN_BYTES)
    mutator(value)
    with pytest.raises(CaptionGroupsContractError) as error:
        _load(_canonical(value), fx)
    _assert_error(error, pointer, reason, issue)


def _synthetic_expected(sizes: tuple[int, ...]) -> CaptionGroupsArtifact:
    groups = []
    cursor = 0
    for ordinal, size in enumerate(sizes):
        word_ids = tuple(f"word_{index}" for index in range(cursor, cursor + size))
        groups.append(
            CaptionGroup(
                CAPTION_GROUP_V1,
                CAPTION_GROUP_HASH_V1,
                "cgrp_" + "a" * 32,
                "a" * 64,
                "revision_x",
                "result_x",
                PHRASE_GROUPING_POLICY_V1,
                ordinal,
                "sentence_x",
                cursor,
                cursor + size,
                word_ids[0],
                word_ids[-1],
                word_ids,
                CaptionGroupWordCountPolicy.PREFERRED_4_TO_9,
                "x",
                cursor * 100,
                (cursor + size) * 100,
                900000,
            )
        )
        cursor += size
    return CaptionGroupsArtifact(
        CAPTION_GROUPS_V1,
        CAPTION_GROUPS_HASH_V1,
        "cgs_" + "b" * 32,
        "b" * 64,
        "project_x",
        "document_x",
        "revision_x",
        "sha256:" + "c" * 64,
        "result_x",
        "d" * 64,
        PHRASE_GROUPING_POLICY_V1,
        contracts.ConfidenceAvailability.AVAILABLE,
        tuple(groups),
    )


@pytest.mark.parametrize(
    ("row", "sizes", "mutator", "issue"),
    [
        (31, (10,), lambda root: None, "WORD_RANGE_OUT_OF_BOUNDS"),
        (32, (4,), lambda root: root["caption_groups"][0].update(word_count_policy="SHORT_SENTENCE_1_TO_3"), "CANONICAL_COVERAGE_BLOCKER"),
    ],
)
def test_closed_policy_oracle_rows_with_independent_semantic_fixture(row, sizes, mutator, issue) -> None:
    expected = _synthetic_expected(sizes)
    root = caption_contracts._artifact_envelope(expected)
    mutator(root)
    with pytest.raises(CaptionGroupsContractError) as error:
        caption_contracts._validate_loaded_semantics(root, root["caption_groups"], expected)
    _assert_error(
        error,
        "/caption_groups/0",
        CaptionGroupingRejectionReason.GROUPING_POLICY_INVALID,
        issue,
    )


def test_closed_policy_oracle_row_34_rejects_alternate_valid_partition() -> None:
    expected = _synthetic_expected((6, 4))
    root = caption_contracts._artifact_envelope(expected)
    word_ids = [f"word_{index}" for index in range(10)]
    first, second = root["caption_groups"]
    first.update(
        end_exclusive_word_ordinal=4,
        end_word_id=word_ids[3],
        word_ids=word_ids[:4],
    )
    second.update(
        start_word_ordinal=4,
        start_word_id=word_ids[4],
        word_ids=word_ids[4:],
    )
    with pytest.raises(CaptionGroupsContractError) as error:
        caption_contracts._validate_loaded_semantics(root, root["caption_groups"], expected)
    _assert_error(
        error,
        "/caption_groups/0",
        CaptionGroupingRejectionReason.GROUPING_POLICY_INVALID,
        "CANONICAL_COVERAGE_BLOCKER",
    )


@pytest.mark.parametrize(
    ("case", "revision_change", "issue"),
    [
        ("empty", lambda revision: dataclasses.replace(revision, canonical_words=()), "CANONICAL_COVERAGE_BLOCKER"),
        (
            "duplicate_id",
            lambda revision: dataclasses.replace(
                revision,
                canonical_words=(
                    revision.canonical_words[0],
                    dataclasses.replace(revision.canonical_words[1], word_id=revision.canonical_words[0].word_id),
                    *revision.canonical_words[2:],
                ),
            ),
            "CANONICAL_COVERAGE_BLOCKER",
        ),
        (
            "ordinal",
            lambda revision: dataclasses.replace(
                revision,
                canonical_words=(dataclasses.replace(revision.canonical_words[0], ordinal=1), *revision.canonical_words[1:]),
            ),
            "CANONICAL_WORD_ORDER_INVALID",
        ),
    ],
)
def test_section_11_canonical_inventory_rows(case, revision_change, issue, fx) -> None:
    _, revision, result = fx
    with pytest.raises(CaptionGroupsContractError) as error:
        caption_contracts._inventory(revision_change(revision), result)
    _assert_error(
        error,
        "/narration_revision",
        CaptionGroupingRejectionReason.CANONICAL_COVERAGE_INVALID,
        issue,
    )


def test_section_11_noncontiguous_sentence_run_row(fx) -> None:
    _, revision, result = fx
    words = list(revision.canonical_words)
    tokens = list(revision.text_tokens)
    words[1] = dataclasses.replace(words[1], sentence_id=words[2].sentence_id)
    words[2] = dataclasses.replace(words[2], sentence_id=words[0].sentence_id)
    token_positions = {token.token_id: index for index, token in enumerate(tokens)}
    tokens[token_positions[words[1].token_id]] = dataclasses.replace(
        tokens[token_positions[words[1].token_id]], sentence_id=words[1].sentence_id
    )
    tokens[token_positions[words[2].token_id]] = dataclasses.replace(
        tokens[token_positions[words[2].token_id]], sentence_id=words[2].sentence_id
    )
    changed = dataclasses.replace(revision, canonical_words=tuple(words), text_tokens=tuple(tokens))
    with pytest.raises(CaptionGroupsContractError) as error:
        caption_contracts._inventory(changed, result)
    _assert_error(
        error,
        "/narration_revision",
        CaptionGroupingRejectionReason.CANONICAL_COVERAGE_INVALID,
        "CANONICAL_COVERAGE_BLOCKER",
    )


@pytest.mark.parametrize(
    ("case", "timings_change", "reason", "issue"),
    [
        ("length", lambda values: values[:-1], CaptionGroupingRejectionReason.CANONICAL_COVERAGE_INVALID, "CANONICAL_COVERAGE_BLOCKER"),
        ("word_id", lambda values: (dataclasses.replace(values[0], word_id="word_other"), *values[1:]), CaptionGroupingRejectionReason.CANONICAL_COVERAGE_INVALID, "CANONICAL_WORD_ORDER_INVALID"),
        ("type", lambda values: (dataclasses.replace(values[0], start_ms=1.5), *values[1:]), CaptionGroupingRejectionReason.TIMING_INVALID, "TIMESTAMP_NON_MONOTONIC"),
        ("negative", lambda values: (dataclasses.replace(values[0], start_ms=-1), *values[1:]), CaptionGroupingRejectionReason.TIMING_INVALID, "TIMESTAMP_OUT_OF_BOUNDS"),
        ("zero", lambda values: (dataclasses.replace(values[0], start_ms=values[0].end_ms), *values[1:]), CaptionGroupingRejectionReason.TIMING_INVALID, "ZERO_DURATION_WORD"),
        ("reversed", lambda values: (dataclasses.replace(values[0], start_ms=values[0].end_ms + 1), *values[1:]), CaptionGroupingRejectionReason.TIMING_INVALID, "TIMESTAMP_NON_MONOTONIC"),
        ("overlap", lambda values: (values[0], dataclasses.replace(values[1], start_ms=values[0].end_ms - 1), *values[2:]), CaptionGroupingRejectionReason.TIMING_INVALID, "TIMESTAMP_OVERLAP"),
    ],
)
def test_section_11_alignment_coverage_and_timing_rows(case, timings_change, reason, issue, fx) -> None:
    _, revision, result = fx
    changed = dataclasses.replace(result, word_timings=tuple(timings_change(result.word_timings)))
    with pytest.raises(CaptionGroupsContractError) as error:
        caption_contracts._inventory(revision, changed)
    _assert_error(error, "/alignment_result", reason, issue)


@pytest.mark.parametrize("bad_value", [True, 1.5, "1", -1, 1_000_001])
def test_section_14_available_confidence_type_and_bounds_row(bad_value, fx) -> None:
    _, revision, result = fx
    timings = (dataclasses.replace(result.word_timings[0], confidence_millionths=bad_value), *result.word_timings[1:])
    changed = dataclasses.replace(result, word_timings=timings)
    with pytest.raises(CaptionGroupsContractError) as error:
        caption_contracts._inventory(revision, changed)
    _assert_error(error, "/alignment_result", CaptionGroupingRejectionReason.CONFIDENCE_INVALID, "ADAPTER_PRECISION_OVERSTATED")


def test_section_14_available_null_and_null_mode_nonnull_rows(fx) -> None:
    _, revision, result = fx
    missing = dataclasses.replace(
        result,
        word_timings=(dataclasses.replace(result.word_timings[0], confidence_millionths=None), *result.word_timings[1:]),
    )
    with pytest.raises(CaptionGroupsContractError) as error:
        caption_contracts._inventory(revision, missing)
    _assert_error(error, "/alignment_result", CaptionGroupingRejectionReason.CONFIDENCE_INVALID, "CONFIDENCE_REQUIRED_UNAVAILABLE")

    unavailable = dataclasses.replace(result, confidence_availability=contracts.ConfidenceAvailability.UNAVAILABLE)
    with pytest.raises(CaptionGroupsContractError) as error:
        caption_contracts._inventory(revision, unavailable)
    _assert_error(error, "/alignment_result", CaptionGroupingRejectionReason.CONFIDENCE_INVALID, "ADAPTER_PRECISION_OVERSTATED")


def test_dependency_drift_and_binding_precedence_are_exact(fx) -> None:
    document, revision, result = fx
    original_source = revision.source_text
    try:
        object.__setattr__(revision, "source_text", original_source + " changed")
        with pytest.raises(CaptionGroupsContractError) as error:
            _compile(fx)
        _assert_error(error, "/narration_revision", CaptionGroupingRejectionReason.DEPENDENCY_CONTENT_DRIFT, "ALIGNMENT_REQUEST_IDENTITY_MISMATCH")
    finally:
        object.__setattr__(revision, "source_text", original_source)

    original_hash = result.alignment_result_hash
    try:
        object.__setattr__(result, "alignment_result_hash", "0" * 64)
        with pytest.raises(CaptionGroupsContractError) as error:
            _compile(fx)
        _assert_error(error, "/alignment_result", CaptionGroupingRejectionReason.DEPENDENCY_CONTENT_DRIFT, "REPLAY_HASH_MISMATCH")
    finally:
        object.__setattr__(result, "alignment_result_hash", original_hash)

    original_revision_id = document.current_revision_id
    try:
        object.__setattr__(document, "current_revision_id", "narrev_other")
        with pytest.raises(CaptionGroupsContractError) as error:
            _compile(fx)
        _assert_error(error, "/narration_document", CaptionGroupingRejectionReason.DEPENDENCY_BINDING_INVALID, "ALIGNMENT_REQUEST_IDENTITY_MISMATCH")
    finally:
        object.__setattr__(document, "current_revision_id", original_revision_id)


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


def test_registry_collision_rollback_and_stale_callback_safety(fx, monkeypatch) -> None:
    artifact = _compile(fx)
    envelope = serialize_caption_groups(artifact)
    with pytest.raises(RuntimeError, match="collision"):
        caption_contracts._register(artifact, envelope)
    key = id(artifact)
    caption_contracts._MATERIALIZED_CAPTION_GROUPS.pop(key)
    caption_contracts._OWNED_CAPTION_GROUP_REFERENCES.pop(key)

    class RejectingRegistry(dict):
        def __setitem__(self, key, value):
            raise RuntimeError("injected registration failure")

    owned = {}
    monkeypatch.setattr(caption_contracts, "_OWNED_CAPTION_GROUP_REFERENCES", owned)
    monkeypatch.setattr(caption_contracts, "_MATERIALIZED_CAPTION_GROUPS", RejectingRegistry())
    with pytest.raises(RuntimeError, match="injected"):
        caption_contracts._register(artifact, envelope)
    assert owned == {}

    materialized = {}
    owned = {}
    monkeypatch.setattr(caption_contracts, "_MATERIALIZED_CAPTION_GROUPS", materialized)
    monkeypatch.setattr(caption_contracts, "_OWNED_CAPTION_GROUP_REFERENCES", owned)
    caption_contracts._register(artifact, envelope)
    original_reference = materialized[key][0]
    replacement = dataclasses.replace(artifact)
    replacement_reference = weakref.ref(replacement)
    materialized[key] = (replacement_reference, b"replacement")
    owned[key] = replacement_reference
    del artifact
    for _ in range(5):
        gc.collect()
    assert original_reference() is None
    assert materialized[key] == (replacement_reference, b"replacement")
    assert owned[key] is replacement_reference


def test_artifact_does_not_retain_dependencies() -> None:
    dependencies = _dependencies()
    result = _materialize(_result_value(dependencies), dependencies)
    document = dependencies[1]
    revision = dependencies[2]
    references = (weakref.ref(document), weakref.ref(revision), weakref.ref(result))
    artifact = compile_caption_groups(
        narration_document=document,
        narration_revision=revision,
        alignment_result=result,
    )
    assert serialize_caption_groups(artifact) == GOLDEN_BYTES
    del document, revision, result, dependencies
    for _ in range(8):
        gc.collect()
    assert all(reference() is None for reference in references)
    assert serialize_caption_groups(artifact) == GOLDEN_BYTES


def test_literal_punctuation_sets_unicode_and_no_error_text_leak(fx) -> None:
    assert caption_contracts._HARD_BREAK_TOKEN_TEXTS == frozenset(
        (".", "!", "?", "…", "...", "?!", "!?", ";", ":", "—", "–")
    )
    assert caption_contracts._SOFT_BREAK_TOKEN_TEXTS == frozenset((",",))
    for invalid in ("e\u0301", "bad\x00", "bad\x7f", "\ud800"):
        with pytest.raises(ValueError):
            caption_contracts._safe_text(invalid)

    value = json.loads(GOLDEN_BYTES)
    attacker_text = "C:/private/provider-key?token=secret"
    value["caption_groups"][0]["display_text"] = attacker_text
    with pytest.raises(CaptionGroupsContractError) as error:
        _load(_canonical(value), fx)
    _assert_error(error, "/caption_groups/0", CaptionGroupingRejectionReason.DISPLAY_TEXT_INVALID)
    assert attacker_text not in str(error.value)


def test_non_materialized_proxy_subclass_and_object_new_are_rejected(fx) -> None:
    artifact = _compile(fx)

    class Proxy:
        def __init__(self, target):
            self.target = target

        def __getattr__(self, name):
            return getattr(self.target, name)

    class Subclass(CaptionGroupsArtifact):
        pass

    subclass = Subclass(*tuple(getattr(artifact, field) for field in caption_contracts._ROOT_FIELDS))
    for forged in (Proxy(artifact), subclass, object.__new__(CaptionGroupsArtifact)):
        with pytest.raises(CaptionGroupsContractError) as error:
            serialize_caption_groups(forged)
        _assert_error(error, "/", CaptionGroupingRejectionReason.NOT_MATERIALIZED)


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
