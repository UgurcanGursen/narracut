from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import FrozenInstanceError, replace

import pytest

from engine.contracts import (
    NARRATION_REVISION_HASH_V1,
    NARRATION_REVISION_V1,
    NORMALIZATION_PROFILE_HASH_V1,
    NarrationContractError,
    NarrationRejectionReason,
    TokenKind,
    WordRangeConsumer,
    WordRangeReference,
    materialize_canonical_narration,
    normalization_profile_hash,
    resolve_word_range,
)


FX34_SOURCE_BYTES = b"Alpha beta. Gamma delta."
FX34_SOURCE_HASH = (
    "sha256:dd7aaf64a3e9ae29d44de682182fac0d9c4bd94d"
    "e36b1b30f247bb15c7a780eb"
)


def fx34_value() -> dict:
    profile = {
        "hash_scope_version": NORMALIZATION_PROFILE_HASH_V1,
        "language": "en",
        "locale": "en-US",
        "profile_id": "nprof_fx34",
        "profile_version": "1.0.0",
        "tokenization_rule_version": "fx34-token-v1",
        "number_policy_id": "num_none_v1",
        "pronunciation_policy_id": "pron_none_v1",
        "lexical_alias_policy_id": "alias_none_v1",
    }
    profile["profile_hash"] = normalization_profile_hash(profile)
    return {
        "schema_version": NARRATION_REVISION_V1,
        "project_id": "prj_fx34",
        "document_id": "nardoc_fx34",
        "language": "en",
        "locale": "en-US",
        "title": "FX-34",
        "parent_revision_id": None,
        "normalization_profile": profile,
        "sections": [
            {
                "order": 0,
                "source_start": 0,
                "source_end": 24,
                "paragraphs": [
                    {
                        "order": 0,
                        "source_start": 0,
                        "source_end": 24,
                        "sentences": [
                            {
                                "order": 0,
                                "source_start": 0,
                                "source_end": 11,
                                "segmentation_rule_version": "fx34-sentence-v1",
                                "extensions": {},
                            },
                            {
                                "order": 1,
                                "source_start": 12,
                                "source_end": 24,
                                "segmentation_rule_version": "fx34-sentence-v1",
                                "extensions": {},
                            },
                        ],
                        "extensions": {},
                    }
                ],
                "extensions": {},
            }
        ],
        "text_tokens": [
            {
                "kind": "SPOKEN",
                "display_text": "Alpha",
                "normalized_alignment_text": "alpha",
                "text_order": 0,
                "canonical_word_ordinal": 0,
                "source_start": 0,
                "source_end": 5,
                "section_order": 0,
                "paragraph_order": 0,
                "sentence_order": 0,
                "extensions": {},
            },
            {
                "kind": "SPOKEN",
                "display_text": "beta",
                "normalized_alignment_text": "beta",
                "text_order": 1,
                "canonical_word_ordinal": 1,
                "source_start": 6,
                "source_end": 10,
                "section_order": 0,
                "paragraph_order": 0,
                "sentence_order": 0,
                "extensions": {},
            },
            {
                "kind": "PUNCTUATION",
                "display_text": ".",
                "normalized_alignment_text": None,
                "text_order": 2,
                "canonical_word_ordinal": None,
                "source_start": 10,
                "source_end": 11,
                "section_order": 0,
                "paragraph_order": 0,
                "sentence_order": 0,
                "extensions": {},
            },
            {
                "kind": "SPOKEN",
                "display_text": "Gamma",
                "normalized_alignment_text": "gamma",
                "text_order": 3,
                "canonical_word_ordinal": 2,
                "source_start": 12,
                "source_end": 17,
                "section_order": 0,
                "paragraph_order": 0,
                "sentence_order": 1,
                "extensions": {},
            },
            {
                "kind": "SPOKEN",
                "display_text": "delta",
                "normalized_alignment_text": "delta",
                "text_order": 4,
                "canonical_word_ordinal": 3,
                "source_start": 18,
                "source_end": 23,
                "section_order": 0,
                "paragraph_order": 0,
                "sentence_order": 1,
                "extensions": {},
            },
            {
                "kind": "PUNCTUATION",
                "display_text": ".",
                "normalized_alignment_text": None,
                "text_order": 5,
                "canonical_word_ordinal": None,
                "source_start": 23,
                "source_end": 24,
                "section_order": 0,
                "paragraph_order": 0,
                "sentence_order": 1,
                "extensions": {},
            },
        ],
        "canonical_words": [
            {"text_order": 0, "canonical_word_ordinal": 0},
            {"text_order": 1, "canonical_word_ordinal": 1},
            {"text_order": 3, "canonical_word_ordinal": 2},
            {"text_order": 4, "canonical_word_ordinal": 3},
        ],
        "extensions": {},
    }


def materialize_fx34(
    value: dict | None = None,
    *,
    source_bytes: bytes = FX34_SOURCE_BYTES,
    predecessor=None,
):
    return materialize_canonical_narration(
        source_bytes,
        fx34_value() if value is None else value,
        predecessor=predecessor,
    )


def assert_rejected_without_revision(
    exc_info: pytest.ExceptionInfo[NarrationContractError],
) -> None:
    assert not hasattr(exc_info.value, "revision")
    assert not hasattr(exc_info.value, "revision_id")
    assert not hasattr(exc_info.value, "revision_hash")
    assert not hasattr(exc_info.value, "canonical_bytes")


def test_fx34_exact_source_hierarchy_and_canonical_bytes() -> None:
    result = materialize_fx34()
    revision = result.revision

    assert revision.source_text == "Alpha beta. Gamma delta."
    assert revision.source_byte_hash == FX34_SOURCE_HASH
    assert revision.hash_scope_version == NARRATION_REVISION_HASH_V1
    assert result.document.current_revision_id == revision.revision_id
    assert revision.revision_id == (
        "narrev_" + revision.revision_hash.removeprefix("sha256:")[:20]
    )
    assert [(item.source_start, item.source_end) for item in revision.sections] == [
        (0, 24)
    ]
    paragraph = revision.sections[0].paragraphs[0]
    assert (paragraph.source_start, paragraph.source_end) == (0, 24)
    assert [
        (sentence.source_start, sentence.source_end)
        for sentence in paragraph.sentences
    ] == [(0, 11), (12, 24)]
    assert revision.source_text[11:12] == " "
    assert [
        (token.kind.value, token.source_start, token.source_end)
        for token in revision.text_tokens
    ] == [
        ("SPOKEN", 0, 5),
        ("SPOKEN", 6, 10),
        ("PUNCTUATION", 10, 11),
        ("SPOKEN", 12, 17),
        ("SPOKEN", 18, 23),
        ("PUNCTUATION", 23, 24),
    ]
    assert [word.ordinal for word in revision.canonical_words] == [0, 1, 2, 3]
    assert [word.display_text for word in revision.canonical_words] == [
        "Alpha",
        "beta",
        "Gamma",
        "delta",
    ]
    assert not result.canonical_bytes.startswith(b"\xef\xbb\xbf")
    assert not result.canonical_bytes.endswith(b"\n")
    parsed = json.loads(result.canonical_bytes.decode("utf-8"))
    independently_encoded = json.dumps(
        parsed,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    assert result.canonical_bytes == independently_encoded


def test_revision_hash_is_direct_sha256_of_exact_versioned_scope() -> None:
    result = materialize_fx34()
    revision_data = json.loads(result.canonical_bytes.decode("utf-8"))[
        "revision"
    ]
    revision_data.pop("revision_id")
    declared_hash = revision_data.pop("revision_hash")

    def remove_self_revision_ids(value):
        if isinstance(value, dict):
            return {
                key: remove_self_revision_ids(item)
                for key, item in value.items()
                if key != "revision_id"
            }
        if isinstance(value, list):
            return [remove_self_revision_ids(item) for item in value]
        return value

    scope = remove_self_revision_ids(revision_data)
    scope_bytes = json.dumps(
        scope,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    assert scope["hash_scope_version"] == NARRATION_REVISION_HASH_V1
    assert declared_hash == "sha256:" + hashlib.sha256(scope_bytes).hexdigest()


def test_two_independent_materializations_match_all_identities() -> None:
    first = materialize_fx34()
    second = materialize_fx34(copy.deepcopy(fx34_value()))

    assert first.canonical_bytes == second.canonical_bytes
    assert first.revision.source_byte_hash == second.revision.source_byte_hash
    assert first.revision.revision_id == second.revision.revision_id
    assert first.revision.revision_hash == second.revision.revision_hash
    assert first.revision.sections == second.revision.sections
    assert [token.token_id for token in first.revision.text_tokens] == [
        token.token_id for token in second.revision.text_tokens
    ]
    assert [word.word_id for word in first.revision.canonical_words] == [
        word.word_id for word in second.revision.canonical_words
    ]


@pytest.mark.parametrize(
    ("source", "reason", "issue_code"),
    [
        (
            b"\xff",
            NarrationRejectionReason.INVALID_UTF8,
            "INPUT_TEXT_INVALID_UTF8",
        ),
        (
            b"\xef\xbb\xbfAlpha",
            NarrationRejectionReason.BOM_FORBIDDEN,
            None,
        ),
        (b"", NarrationRejectionReason.EMPTY_SOURCE, None),
    ],
)
def test_invalid_source_is_rejected_before_revision(
    source: bytes,
    reason: NarrationRejectionReason,
    issue_code: str | None,
) -> None:
    with pytest.raises(NarrationContractError) as exc_info:
        materialize_fx34(source_bytes=source)

    assert exc_info.value.reason is reason
    assert exc_info.value.issue_code == issue_code
    assert_rejected_without_revision(exc_info)


def test_source_text_preserves_exact_code_points_and_crlf() -> None:
    source = b"Alpha beta.\r\nGamma delta."
    value = fx34_value()
    value["sections"][0]["source_end"] = 25
    value["sections"][0]["paragraphs"][0]["source_end"] = 25
    sentence = value["sections"][0]["paragraphs"][0]["sentences"][1]
    sentence["source_start"] = 13
    sentence["source_end"] = 25
    for token in value["text_tokens"][3:]:
        token["source_start"] += 1
        token["source_end"] += 1

    result = materialize_fx34(value, source_bytes=source)

    assert result.revision.source_text == "Alpha beta.\r\nGamma delta."
    assert result.revision.source_text.encode("utf-8") == source
    assert result.revision.source_byte_hash == (
        "sha256:" + hashlib.sha256(source).hexdigest()
    )


def test_source_text_is_not_silently_nfc_normalized() -> None:
    source_text = "A\u0301lpha beta. Gamma delta."
    source = source_text.encode("utf-8")
    value = fx34_value()
    value["sections"][0]["source_end"] = 25
    paragraph = value["sections"][0]["paragraphs"][0]
    paragraph["source_end"] = 25
    paragraph["sentences"][0]["source_end"] = 12
    paragraph["sentences"][1]["source_start"] = 13
    paragraph["sentences"][1]["source_end"] = 25
    value["text_tokens"][0]["display_text"] = "A\u0301lpha"
    value["text_tokens"][0]["source_end"] = 6
    value["text_tokens"][0]["normalized_alignment_text"] = "\u00e1lpha"
    for token in value["text_tokens"][1:]:
        token["source_start"] += 1
        token["source_end"] += 1

    result = materialize_fx34(value, source_bytes=source)

    assert result.revision.source_text == source_text
    assert result.revision.source_text != "\u00c1lpha beta. Gamma delta."
    assert result.revision.source_text.encode("utf-8") == source


def test_derived_normalization_never_changes_source_hash_or_text() -> None:
    first = materialize_fx34()
    value = fx34_value()
    value["text_tokens"][0]["normalized_alignment_text"] = "ALPHA"
    second = materialize_fx34(value)

    assert second.revision.source_text == first.revision.source_text
    assert second.revision.source_byte_hash == first.revision.source_byte_hash
    assert second.revision.revision_hash != first.revision.revision_hash


def test_title_is_excluded_from_revision_identity() -> None:
    first = materialize_fx34()
    value = fx34_value()
    value["title"] = "A different UI title"
    second = materialize_fx34(value)

    assert second.revision.revision_hash == first.revision.revision_hash
    assert second.revision.revision_id == first.revision.revision_id
    assert second.canonical_bytes != first.canonical_bytes


def test_public_models_and_extensions_are_immutable() -> None:
    value = fx34_value()
    value["extensions"] = {"business-tech:review": {"status": "approved"}}
    result = materialize_fx34(value)

    with pytest.raises(FrozenInstanceError):
        result.revision.source_text = "changed"  # type: ignore[misc]
    with pytest.raises(TypeError):
        result.revision.extensions["business-tech:review"] = {}  # type: ignore[index]
    with pytest.raises(TypeError):
        result.revision.extensions["business-tech:review"]["status"] = "x"  # type: ignore[index]


def test_normalization_profile_hash_is_validated() -> None:
    value = fx34_value()
    value["normalization_profile"]["profile_hash"] = "sha256:" + "0" * 64

    with pytest.raises(NarrationContractError) as exc_info:
        materialize_fx34(value)

    assert exc_info.value.reason is NarrationRejectionReason.HASH_MISMATCH
    assert_rejected_without_revision(exc_info)


def test_unknown_top_level_field_is_fail_closed() -> None:
    value = fx34_value()
    value["unexpected"] = True

    with pytest.raises(NarrationContractError) as exc_info:
        materialize_fx34(value)

    assert (
        exc_info.value.reason
        is NarrationRejectionReason.CLOSED_FIELD_VIOLATION
    )


def test_namespaced_extension_is_accepted_and_canonicalized() -> None:
    value = fx34_value()
    value["extensions"] = {
        "business-tech:review": {
            "approved": True,
            "labels": ["canonical", "narration"],
        }
    }

    result = materialize_fx34(value)

    assert b'"business-tech:review"' in result.canonical_bytes


@pytest.mark.parametrize("key", ["review", "Business:review", "business:Review"])
def test_noncanonical_extension_key_is_rejected(key: str) -> None:
    value = fx34_value()
    value["extensions"] = {key: True}

    with pytest.raises(NarrationContractError) as exc_info:
        materialize_fx34(value)

    assert exc_info.value.reason is NarrationRejectionReason.EXTENSION_INVALID


def test_unknown_token_enum_uses_canonical_issue_code() -> None:
    value = fx34_value()
    value["text_tokens"][0]["kind"] = "spoken"

    with pytest.raises(NarrationContractError) as exc_info:
        materialize_fx34(value)

    assert exc_info.value.issue_code == "UNSUPPORTED_CONTRACT_ENUM"


def test_text_token_order_must_be_strictly_increasing() -> None:
    value = fx34_value()
    value["text_tokens"][1]["text_order"] = 0

    with pytest.raises(NarrationContractError) as exc_info:
        materialize_fx34(value)

    assert exc_info.value.reason is NarrationRejectionReason.TOKEN_ORDER_INVALID


def test_duplicate_declared_token_id_is_rejected() -> None:
    baseline = materialize_fx34()
    value = fx34_value()
    duplicate = baseline.revision.text_tokens[0].token_id
    value["text_tokens"][0]["token_id"] = duplicate
    value["text_tokens"][1]["token_id"] = duplicate

    with pytest.raises(NarrationContractError) as exc_info:
        materialize_fx34(value)

    assert exc_info.value.reason is NarrationRejectionReason.IDENTITY_MISMATCH


@pytest.mark.parametrize(
    "ordinal",
    [None, True, -1, 2**32],
)
def test_spoken_ordinal_requires_exact_uint32(ordinal) -> None:
    value = fx34_value()
    value["text_tokens"][0]["canonical_word_ordinal"] = ordinal

    with pytest.raises(NarrationContractError) as exc_info:
        materialize_fx34(value)

    assert exc_info.value.issue_code == "CANONICAL_WORD_ORDER_INVALID"


@pytest.mark.parametrize(
    "ordinals",
    [
        [0, 0, 2, 3],
        [0, 1, 3, 4],
        [1, 2, 3, 4],
    ],
)
def test_spoken_ordinals_must_be_unique_contiguous_and_zero_based(
    ordinals: list[int],
) -> None:
    value = fx34_value()
    spoken = [
        token for token in value["text_tokens"] if token["kind"] == "SPOKEN"
    ]
    for token, ordinal in zip(spoken, ordinals):
        token["canonical_word_ordinal"] = ordinal
    value["canonical_words"] = [
        {
            "text_order": token["text_order"],
            "canonical_word_ordinal": token["canonical_word_ordinal"],
        }
        for token in spoken
    ]

    with pytest.raises(NarrationContractError) as exc_info:
        materialize_fx34(value)

    assert exc_info.value.issue_code == "CANONICAL_WORD_ORDER_INVALID"


@pytest.mark.parametrize("kind", ["PUNCTUATION", "NON_SPOKEN"])
def test_nonspoken_token_kinds_require_null_alignment_and_ordinal(
    kind: str,
) -> None:
    value = fx34_value()
    value["text_tokens"][2]["kind"] = kind
    value["text_tokens"][2]["normalized_alignment_text"] = "dot"
    value["text_tokens"][2]["canonical_word_ordinal"] = 4

    with pytest.raises(NarrationContractError):
        materialize_fx34(value)


def test_nonspoken_token_is_preserved_but_not_projected() -> None:
    value = fx34_value()
    value["text_tokens"][2]["kind"] = "NON_SPOKEN"

    result = materialize_fx34(value)

    assert result.revision.text_tokens[2].kind is TokenKind.NON_SPOKEN
    assert all(
        word.token_id != result.revision.text_tokens[2].token_id
        for word in result.revision.canonical_words
    )


@pytest.mark.parametrize("mutation", ["missing", "punctuation", "duplicate"])
def test_canonical_words_must_exactly_project_spoken_tokens(
    mutation: str,
) -> None:
    value = fx34_value()
    if mutation == "missing":
        value["canonical_words"].pop()
    elif mutation == "punctuation":
        value["canonical_words"].append(
            {"text_order": 2, "canonical_word_ordinal": 4}
        )
    else:
        value["canonical_words"].append(copy.deepcopy(value["canonical_words"][-1]))

    with pytest.raises(NarrationContractError) as exc_info:
        materialize_fx34(value)

    assert exc_info.value.issue_code == "CANONICAL_WORD_ORDER_INVALID"


@pytest.mark.parametrize("mutation", ["reversed", "out_of_bounds", "overlap"])
def test_token_source_ranges_fail_closed(mutation: str) -> None:
    value = fx34_value()
    token = value["text_tokens"][1]
    if mutation == "reversed":
        token["source_start"] = 10
        token["source_end"] = 6
    elif mutation == "out_of_bounds":
        token["source_end"] = 25
    else:
        token["source_start"] = 4
        token["display_text"] = "a beta"

    with pytest.raises(NarrationContractError) as exc_info:
        materialize_fx34(value)

    assert exc_info.value.reason is NarrationRejectionReason.SOURCE_RANGE_INVALID


def test_token_display_text_must_match_exact_source_slice() -> None:
    value = fx34_value()
    value["text_tokens"][0]["display_text"] = "alpha"

    with pytest.raises(NarrationContractError) as exc_info:
        materialize_fx34(value)

    assert exc_info.value.reason is NarrationRejectionReason.SOURCE_RANGE_INVALID


def test_child_hierarchy_range_must_be_inside_parent() -> None:
    value = fx34_value()
    value["sections"][0]["paragraphs"][0]["source_end"] = 23

    with pytest.raises(NarrationContractError) as exc_info:
        materialize_fx34(value)

    assert exc_info.value.issue_code == "HIERARCHY_COVERAGE_BLOCKER"


def test_overlapping_hierarchy_siblings_are_rejected() -> None:
    value = fx34_value()
    value["sections"][0]["paragraphs"][0]["sentences"][1][
        "source_start"
    ] = 10

    with pytest.raises(NarrationContractError) as exc_info:
        materialize_fx34(value)

    assert exc_info.value.issue_code == "HIERARCHY_COVERAGE_BLOCKER"


def test_missing_token_parent_path_is_rejected() -> None:
    value = fx34_value()
    value["text_tokens"][0]["sentence_order"] = 99

    with pytest.raises(NarrationContractError) as exc_info:
        materialize_fx34(value)

    assert exc_info.value.issue_code == "HIERARCHY_COVERAGE_BLOCKER"


def test_fx34_wrong_sentence_range_leaves_word_uncovered() -> None:
    value = fx34_value()
    value["sections"][0]["paragraphs"][0]["sentences"][1]["source_end"] = 23

    with pytest.raises(NarrationContractError) as exc_info:
        materialize_fx34(value)

    assert exc_info.value.issue_code == "HIERARCHY_COVERAGE_BLOCKER"


def test_every_spoken_word_resolves_exact_parent_chain() -> None:
    revision = materialize_fx34().revision
    section = revision.sections[0]
    paragraph = section.paragraphs[0]
    sentence_ids = {item.sentence_id for item in paragraph.sentences}

    for word in revision.canonical_words:
        assert word.section_id == section.section_id
        assert word.paragraph_id == paragraph.paragraph_id
        assert word.sentence_id in sentence_ids


def test_changed_hierarchy_cannot_reuse_stale_stable_id() -> None:
    baseline = materialize_fx34()
    value = fx34_value()
    value["sections"][0]["section_id"] = (
        baseline.revision.sections[0].section_id
    )
    value["sections"][0]["order"] = 1

    with pytest.raises(NarrationContractError) as exc_info:
        materialize_fx34(value)

    assert exc_info.value.reason is NarrationRejectionReason.IDENTITY_MISMATCH


def test_noninitial_revision_requires_matching_predecessor_scope() -> None:
    first = materialize_fx34()
    value = fx34_value()
    value["parent_revision_id"] = first.revision.revision_id
    value["text_tokens"][-1]["display_text"] = "!"
    source = b"Alpha beta. Gamma delta!"

    second = materialize_fx34(
        value,
        source_bytes=source,
        predecessor=first.revision,
    )

    assert second.revision.parent_revision_id == first.revision.revision_id
    assert second.revision.revision_id != first.revision.revision_id
    assert (
        second.revision.sections[0].supersedes_id
        == first.revision.sections[0].section_id
    )
    assert all(
        current.supersedes_id == previous.token_id
        for current, previous in zip(
            second.revision.text_tokens,
            first.revision.text_tokens,
        )
    )

    with pytest.raises(NarrationContractError):
        materialize_fx34(value, source_bytes=source)


@pytest.mark.parametrize(
    ("start", "end", "expected"),
    [
        (3, 4, ["delta"]),
        (0, 4, ["Alpha", "beta", "Gamma", "delta"]),
        (4, 4, []),
        (2, 2, []),
    ],
)
def test_word_range_half_open_and_structural_empty_boundaries(
    start: int,
    end: int,
    expected: list[str],
) -> None:
    revision = materialize_fx34().revision
    reference = WordRangeReference(revision.revision_id, start, end)

    assert [
        word.display_text for word in resolve_word_range(revision, reference)
    ] == expected


@pytest.mark.parametrize(
    "consumer",
    [
        WordRangeConsumer.SEGMENT,
        WordRangeConsumer.CAPTION,
        WordRangeConsumer.PHRASE,
        WordRangeConsumer.EMPHASIS,
    ],
)
def test_timed_consumers_reject_empty_word_ranges(
    consumer: WordRangeConsumer,
) -> None:
    revision = materialize_fx34().revision
    reference = WordRangeReference(revision.revision_id, 2, 2)

    with pytest.raises(NarrationContractError) as exc_info:
        resolve_word_range(revision, reference, consumer=consumer)

    assert exc_info.value.issue_code == "WORD_RANGE_OUT_OF_BOUNDS"


@pytest.mark.parametrize(
    ("reference_factory", "issue_code"),
    [
        (
            lambda revision: WordRangeReference(revision.revision_id, 3, 2),
            "WORD_RANGE_REVERSED",
        ),
        (
            lambda revision: WordRangeReference(revision.revision_id, 0, 5),
            "WORD_RANGE_OUT_OF_BOUNDS",
        ),
        (
            lambda revision: WordRangeReference("narrev_foreign", 0, 1),
            "WORD_RANGE_REVISION_MISMATCH",
        ),
    ],
)
def test_word_range_failure_codes(reference_factory, issue_code: str) -> None:
    revision = materialize_fx34().revision

    with pytest.raises(NarrationContractError) as exc_info:
        resolve_word_range(revision, reference_factory(revision))

    assert exc_info.value.issue_code == issue_code
    assert_rejected_without_revision(exc_info)


def test_boolean_word_range_boundary_is_rejected() -> None:
    revision = materialize_fx34().revision

    with pytest.raises(NarrationContractError):
        WordRangeReference(revision.revision_id, True, 1)


def test_invalid_target_word_inventory_fails_before_resolution() -> None:
    revision = materialize_fx34().revision
    invalid = replace(
        revision,
        canonical_words=(
            revision.canonical_words[1],
            revision.canonical_words[0],
            *revision.canonical_words[2:],
        ),
    )
    reference = WordRangeReference(revision.revision_id, 0, 1)

    with pytest.raises(NarrationContractError) as exc_info:
        resolve_word_range(invalid, reference)

    assert exc_info.value.issue_code == "CANONICAL_WORD_ORDER_INVALID"


def test_import_surface_has_no_runtime_io_dependencies() -> None:
    import engine.contracts.narration as narration

    assert "Path" not in vars(narration)
    assert "socket" not in vars(narration)
    assert "requests" not in vars(narration)
