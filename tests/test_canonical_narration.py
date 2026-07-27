from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import FrozenInstanceError, replace

import pytest

from engine.contracts import (
    NARRATION_LINEAGE_V1,
    NARRATION_REVISION_HASH_V1,
    NARRATION_REVISION_V1,
    NORMALIZATION_PROFILE_HASH_V1,
    LineageNodeType,
    NarrationContractError,
    NarrationRejectionReason,
    NodeLineageRelation,
    SpokenFormOverrideSource,
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
    value = {
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
        "document_extensions": {},
        "revision_extensions": {},
    }
    value["lineage_manifest"] = _initial_lineage_manifest(
        value,
        FX34_SOURCE_BYTES,
    )
    return value


def _test_canonical_bytes(value) -> bytes:
    def encode(item) -> str:
        if item is None:
            return "null"
        if item is True:
            return "true"
        if item is False:
            return "false"
        if isinstance(item, int):
            return str(item)
        if isinstance(item, str):
            pieces = ['"']
            for character in item:
                codepoint = ord(character)
                if character == '"':
                    pieces.append('\\"')
                elif character == "\\":
                    pieces.append("\\\\")
                elif codepoint <= 0x1F:
                    pieces.append(f"\\u{codepoint:04x}")
                else:
                    pieces.append(character)
            pieces.append('"')
            return "".join(pieces)
        if isinstance(item, list):
            return "[" + ",".join(encode(child) for child in item) + "]"
        if isinstance(item, dict):
            return (
                "{"
                + ",".join(
                    f"{encode(key)}:{encode(item[key])}"
                    for key in sorted(item)
                )
                + "}"
            )
        raise TypeError(type(item).__name__)

    return encode(value).encode("utf-8")


def _test_stable_id(prefix: str, *parts) -> str:
    return prefix + hashlib.sha256(
        _test_canonical_bytes(list(parts))
    ).hexdigest()[:20]


def _test_node_inventory(value: dict, source_bytes: bytes) -> list[dict]:
    source_text = source_bytes.decode("utf-8")
    context = {
        "project_id": value["project_id"],
        "document_id": value["document_id"],
    }
    inventory: list[dict] = []
    hierarchy: dict[tuple[int, int, int], tuple[str, str, str]] = {}
    for section in value["sections"]:
        section_id = _test_stable_id(
            "nsec_",
            "narration-node-id-v1",
            {
                **context,
                "kind": "section",
                "order": section["order"],
                "source_start": section["source_start"],
                "source_end": section["source_end"],
                "source_text": source_text[
                    section["source_start"]:section["source_end"]
                ],
            },
        )
        inventory.append(
            {"node_type": "SECTION", "node_id": section_id, "raw": section}
        )
        for paragraph in section["paragraphs"]:
            paragraph_id = _test_stable_id(
                "npar_",
                "narration-node-id-v1",
                {
                    **context,
                    "kind": "paragraph",
                    "section_id": section_id,
                    "order": paragraph["order"],
                    "source_start": paragraph["source_start"],
                    "source_end": paragraph["source_end"],
                    "source_text": source_text[
                        paragraph["source_start"]:paragraph["source_end"]
                    ],
                },
            )
            inventory.append(
                {
                    "node_type": "PARAGRAPH",
                    "node_id": paragraph_id,
                    "raw": paragraph,
                }
            )
            for sentence in paragraph["sentences"]:
                sentence_id = _test_stable_id(
                    "nsen_",
                    "narration-node-id-v1",
                    {
                        **context,
                        "kind": "sentence",
                        "paragraph_id": paragraph_id,
                        "order": sentence["order"],
                        "source_start": sentence["source_start"],
                        "source_end": sentence["source_end"],
                        "source_text": source_text[
                            sentence["source_start"]:sentence["source_end"]
                        ],
                        "segmentation_rule_version": sentence[
                            "segmentation_rule_version"
                        ],
                        "language_override": sentence.get(
                            "language_override"
                        ),
                    },
                )
                inventory.append(
                    {
                        "node_type": "SENTENCE",
                        "node_id": sentence_id,
                        "raw": sentence,
                    }
                )
                hierarchy[
                    (
                        section["order"],
                        paragraph["order"],
                        sentence["order"],
                    )
                ] = (section_id, paragraph_id, sentence_id)
    token_inventory: list[dict] = []
    for token in value["text_tokens"]:
        section_id, paragraph_id, sentence_id = hierarchy[
            (
                token["section_order"],
                token["paragraph_order"],
                token["sentence_order"],
            )
        ]
        token_id = _test_stable_id(
            "ntok_",
            "narration-token-id-v1",
            {
                **context,
                "kind": token["kind"],
                "display_text": token["display_text"],
                "normalized_alignment_text": token[
                    "normalized_alignment_text"
                ],
                "text_order": token["text_order"],
                "canonical_word_ordinal": token[
                    "canonical_word_ordinal"
                ],
                "source_start": token["source_start"],
                "source_end": token["source_end"],
                "section_id": section_id,
                "paragraph_id": paragraph_id,
                "sentence_id": sentence_id,
                "spoken_form_override": token.get("spoken_form_override"),
                "trace_refs": token.get("trace_refs", []),
            },
        )
        token_inventory.append(
            {"node_type": "TOKEN", "node_id": token_id, "raw": token}
        )
    return [
        *[item for item in inventory if item["node_type"] == "SECTION"],
        *[item for item in inventory if item["node_type"] == "PARAGRAPH"],
        *[item for item in inventory if item["node_type"] == "SENTENCE"],
        *token_inventory,
    ]


def _initial_lineage_manifest(value: dict, source_bytes: bytes) -> dict:
    return {
        "schema_version": NARRATION_LINEAGE_V1,
        "predecessor_revision_id": None,
        "records": [
            {
                "node_type": item["node_type"],
                "successor_node_id": item["node_id"],
                "relation": "INITIAL",
                "predecessor_node_id": None,
            }
            for item in _test_node_inventory(value, source_bytes)
        ],
        "removed_predecessors": [],
    }


def _predecessor_inventory(revision) -> list[tuple[str, str]]:
    return [
        *[("SECTION", section.section_id) for section in revision.sections],
        *[
            ("PARAGRAPH", paragraph.paragraph_id)
            for section in revision.sections
            for paragraph in section.paragraphs
        ],
        *[
            ("SENTENCE", sentence.sentence_id)
            for section in revision.sections
            for paragraph in section.paragraphs
            for sentence in paragraph.sentences
        ],
        *[("TOKEN", token.token_id) for token in revision.text_tokens],
    ]


def _set_noninitial_manifest(
    value: dict,
    source_bytes: bytes,
    predecessor,
    *,
    supersedes: dict[tuple[str, str], str] | None = None,
) -> list[dict]:
    current = _test_node_inventory(value, source_bytes)
    previous = set(_predecessor_inventory(predecessor))
    supersedes = supersedes or {}
    claimed: set[tuple[str, str]] = set()
    records = []
    for item in current:
        key = (item["node_type"], item["node_id"])
        target = supersedes.get(key)
        if target is not None:
            relation = "SUPERSEDES"
            item["raw"]["supersedes_id"] = target
            claimed.add((item["node_type"], target))
        elif key in previous:
            relation = "UNCHANGED"
            target = item["node_id"]
            item["raw"].pop("supersedes_id", None)
            claimed.add(key)
        else:
            relation = "INSERTED"
            target = None
            item["raw"].pop("supersedes_id", None)
        records.append(
            {
                "node_type": item["node_type"],
                "successor_node_id": item["node_id"],
                "relation": relation,
                "predecessor_node_id": target,
            }
        )
    value["lineage_manifest"] = {
        "schema_version": NARRATION_LINEAGE_V1,
        "predecessor_revision_id": predecessor.revision_id,
        "records": records,
        "removed_predecessors": [
            {"node_type": node_type, "node_id": node_id}
            for node_type, node_id in _predecessor_inventory(predecessor)
            if (node_type, node_id) not in claimed
        ],
    }
    return current


def _noninitial_unchanged_value(predecessor) -> dict:
    value = fx34_value()
    value["parent_revision_id"] = predecessor.revision_id
    _set_noninitial_manifest(
        value,
        FX34_SOURCE_BYTES,
        predecessor,
    )
    return value


def _valid_override(
    *,
    spoken_form: str = "AL-fa",
    source: str = "USER_LEXICON",
    reason: str = "Preferred pronunciation",
    version: str = "1.0.0",
) -> dict:
    return {
        "spoken_form": spoken_form,
        "source": source,
        "reason": reason,
        "version": version,
    }


def materialize_fx34(
    value: dict | None = None,
    *,
    source_bytes: bytes = FX34_SOURCE_BYTES,
    predecessor=None,
    refresh_lineage: bool = True,
):
    candidate = fx34_value() if value is None else value
    if refresh_lineage:
        try:
            source_bytes.decode("utf-8")
        except UnicodeDecodeError:
            pass
        else:
            if (
                source_bytes
                and not source_bytes.startswith(b"\xef\xbb\xbf")
                and predecessor is None
            ):
                try:
                    candidate["lineage_manifest"] = (
                        _initial_lineage_manifest(candidate, source_bytes)
                    )
                except (KeyError, IndexError):
                    pass
    return materialize_canonical_narration(
        source_bytes,
        candidate,
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

    def semantic_projection(value):
        if isinstance(value, dict):
            return {
                key: semantic_projection(item)
                for key, item in value.items()
                if key not in {"revision_id", "extensions"}
            }
        if isinstance(value, list):
            return [semantic_projection(item) for item in value]
        return value

    scope = semantic_projection(revision_data)
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
    value["revision_extensions"] = {
        "business.example/review": {"status": "approved"}
    }
    result = materialize_fx34(value)

    with pytest.raises(FrozenInstanceError):
        result.revision.source_text = "changed"  # type: ignore[misc]
    with pytest.raises(TypeError):
        result.revision.extensions["business.example/review"] = {}  # type: ignore[index]
    with pytest.raises(TypeError):
        result.revision.extensions["business.example/review"]["status"] = "x"  # type: ignore[index]


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
    value["document_extensions"] = {
        "business.example/review": {
            "approved": True,
            "labels": ["canonical", "narration"],
        }
    }

    result = materialize_fx34(value)

    assert b'"business.example/review"' in result.canonical_bytes


@pytest.mark.parametrize(
    "key",
    ["review", "vendor/field", "Vendor.example/field", "vendor.example:"],
)
def test_noncanonical_extension_key_is_rejected(key: str) -> None:
    value = fx34_value()
    value["document_extensions"] = {key: True}

    with pytest.raises(NarrationContractError) as exc_info:
        materialize_fx34(value)

    assert exc_info.value.reason is NarrationRejectionReason.EXTENSION_INVALID


@pytest.mark.parametrize(
    "field",
    ["spoken_form", "source", "reason", "version"],
)
def test_spoken_form_override_requires_all_fields(field: str) -> None:
    value = fx34_value()
    override = _valid_override()
    override.pop(field)
    value["text_tokens"][0]["spoken_form_override"] = override

    with pytest.raises(NarrationContractError):
        materialize_fx34(value)


def test_bare_spoken_form_override_is_rejected() -> None:
    value = fx34_value()
    value["text_tokens"][0]["spoken_form_override"] = "AL-fa"

    with pytest.raises(NarrationContractError):
        materialize_fx34(value)


@pytest.mark.parametrize("source", ["user_lexicon", "USER_OVERRIDE", "User_Lexicon"])
def test_unknown_override_source_uses_canonical_issue_code(source: str) -> None:
    value = fx34_value()
    value["text_tokens"][0]["spoken_form_override"] = _valid_override(
        source=source
    )

    with pytest.raises(NarrationContractError) as exc_info:
        materialize_fx34(value)

    assert exc_info.value.issue_code == "UNSUPPORTED_CONTRACT_ENUM"


@pytest.mark.parametrize(
    "source",
    ["PROVIDER", "ALIGNER_TRANSCRIPT", "TTS_OBSERVATION"],
)
def test_observation_sources_are_not_authorized_overrides(source: str) -> None:
    value = fx34_value()
    value["text_tokens"][0]["spoken_form_override"] = _valid_override(
        source=source
    )

    with pytest.raises(NarrationContractError) as exc_info:
        materialize_fx34(value)

    assert exc_info.value.issue_code == "UNSUPPORTED_CONTRACT_ENUM"


@pytest.mark.parametrize(
    ("field", "invalid"),
    [
        ("spoken_form", ""),
        ("reason", ""),
        ("version", ""),
        ("spoken_form", "A\u0301l-fa"),
        ("reason", "Cafe\u0301 pronunciation"),
        ("version", "e\u0301"),
    ],
)
def test_override_strings_are_nonempty_nfc(field: str, invalid: str) -> None:
    value = fx34_value()
    override = _valid_override()
    override[field] = invalid
    value["text_tokens"][0]["spoken_form_override"] = override

    with pytest.raises(NarrationContractError):
        materialize_fx34(value)


@pytest.mark.parametrize(
    "source",
    [
        SpokenFormOverrideSource.USER_LEXICON.value,
        SpokenFormOverrideSource.PROJECT_LEXICON.value,
    ],
)
def test_structured_spoken_form_override_is_accepted(source: str) -> None:
    value = fx34_value()
    value["text_tokens"][0]["spoken_form_override"] = _valid_override(
        source=source
    )

    result = materialize_fx34(value)
    override = result.revision.text_tokens[0].spoken_form_override

    assert override is not None
    assert override.source.value == source
    assert override.spoken_form == "AL-fa"
    assert result.revision.source_text == FX34_SOURCE_BYTES.decode("utf-8")
    assert len(result.revision.text_tokens) == 6
    assert [word.ordinal for word in result.revision.canonical_words] == [
        0,
        1,
        2,
        3,
    ]
    with pytest.raises(FrozenInstanceError):
        override.reason = "changed"  # type: ignore[misc]


@pytest.mark.parametrize("kind", ["PUNCTUATION", "NON_SPOKEN"])
def test_nonspoken_tokens_reject_structured_override(kind: str) -> None:
    value = fx34_value()
    token = value["text_tokens"][2]
    token["kind"] = kind
    token["spoken_form_override"] = _valid_override()

    with pytest.raises(NarrationContractError):
        materialize_fx34(value)


@pytest.mark.parametrize(
    ("field", "changed"),
    [
        ("spoken_form", "AL-fah"),
        ("source", "PROJECT_LEXICON"),
        ("reason", "Project pronunciation"),
        ("version", "2.0.0"),
    ],
)
def test_each_override_semantic_field_changes_identity(
    field: str,
    changed: str,
) -> None:
    baseline_value = fx34_value()
    baseline_value["text_tokens"][0]["spoken_form_override"] = _valid_override()
    baseline = materialize_fx34(baseline_value)
    changed_value = fx34_value()
    override = _valid_override()
    override[field] = changed
    changed_value["text_tokens"][0]["spoken_form_override"] = override

    result = materialize_fx34(changed_value)

    assert result.revision.text_tokens[0].token_id != (
        baseline.revision.text_tokens[0].token_id
    )
    assert result.revision.revision_hash != baseline.revision.revision_hash
    assert result.revision.revision_id != baseline.revision.revision_id


@pytest.mark.parametrize("field", ["document_extensions", "revision_extensions"])
def test_top_level_extension_scopes_are_required(field: str) -> None:
    value = fx34_value()
    value.pop(field)

    with pytest.raises(NarrationContractError):
        materialize_fx34(value)


def test_legacy_top_level_extensions_is_rejected() -> None:
    value = fx34_value()
    value["extensions"] = {}

    with pytest.raises(NarrationContractError) as exc_info:
        materialize_fx34(value)

    assert (
        exc_info.value.reason
        is NarrationRejectionReason.CLOSED_FIELD_VIOLATION
    )


def test_document_and_revision_extensions_are_isolated() -> None:
    value = fx34_value()
    value["document_extensions"] = {
        "vendor.example/document": {"scope": "document"}
    }
    value["revision_extensions"] = {
        "vendor.example/revision": {"scope": "revision"}
    }

    result = materialize_fx34(value)

    assert set(result.document.extensions) == {"vendor.example/document"}
    assert set(result.revision.extensions) == {"vendor.example/revision"}
    assert result.document.extensions is not result.revision.extensions


@pytest.mark.parametrize(
    ("scope", "key"),
    [
        ("document_extensions", "vendor.example/field"),
        ("revision_extensions", "vendor.example/revision_id"),
        ("document_extensions", "vendor.example/source_text"),
        ("revision_extensions", "vendor.example/ordinal"),
    ],
)
def test_extension_grammar_allows_diagnostic_authoritative_local_names(
    scope: str,
    key: str,
) -> None:
    value = fx34_value()
    value[scope] = {key: True}

    result = materialize_fx34(value)

    assert key in (
        result.document.extensions
        if scope == "document_extensions"
        else result.revision.extensions
    )


def test_extension_changes_do_not_change_authoritative_identity() -> None:
    baseline = materialize_fx34()
    document_value = fx34_value()
    document_value["document_extensions"] = {
        "vendor.example/review": {"state": "approved"}
    }
    document = materialize_fx34(document_value)
    revision_value = fx34_value()
    revision_value["revision_extensions"] = {
        "vendor.example/review": {"state": "approved"}
    }
    revision = materialize_fx34(revision_value)
    nested_value = fx34_value()
    nested_value["text_tokens"][0]["extensions"] = {
        "vendor.example/review": {"state": "approved"}
    }
    nested = materialize_fx34(nested_value)

    for changed in (document, revision, nested):
        assert changed.revision.source_byte_hash == baseline.revision.source_byte_hash
        assert changed.revision.normalization_profile.profile_hash == (
            baseline.revision.normalization_profile.profile_hash
        )
        assert changed.revision.revision_hash == baseline.revision.revision_hash
        assert changed.revision.revision_id == baseline.revision.revision_id
        assert [token.token_id for token in changed.revision.text_tokens] == [
            token.token_id for token in baseline.revision.text_tokens
        ]
        assert [word.word_id for word in changed.revision.canonical_words] == [
            word.word_id for word in baseline.revision.canonical_words
        ]
    assert document.canonical_bytes != baseline.canonical_bytes
    assert revision.canonical_bytes != baseline.canonical_bytes
    assert nested.canonical_bytes != baseline.canonical_bytes


def test_extension_input_is_deep_copied_and_frozen() -> None:
    shared = {"vendor.example/review": {"labels": ["one"]}}
    value = fx34_value()
    value["document_extensions"] = shared
    value["revision_extensions"] = shared

    result = materialize_fx34(value)
    shared["vendor.example/review"]["labels"].append("two")

    assert result.document.extensions["vendor.example/review"]["labels"] == (
        "one",
    )
    assert result.revision.extensions["vendor.example/review"]["labels"] == (
        "one",
    )
    assert result.document.extensions is not result.revision.extensions


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
    current = _test_node_inventory(value, source)
    previous = _predecessor_inventory(first.revision)
    explicit = {
        (item["node_type"], item["node_id"]): previous_id
        for item, (previous_type, previous_id) in zip(current, previous)
        if item["node_type"] == previous_type
    }
    _set_noninitial_manifest(
        value,
        source,
        first.revision,
        supersedes=explicit,
    )

    second = materialize_fx34(
        value,
        source_bytes=source,
        predecessor=first.revision,
        refresh_lineage=False,
    )

    assert second.revision.parent_revision_id == first.revision.revision_id
    assert second.revision.revision_id != first.revision.revision_id
    assert (
        second.revision.sections[0].supersedes_id
        == first.revision.sections[0].section_id
    )
    assert all(
        current_token.supersedes_id == previous_token.token_id
        for current_token, previous_token in zip(
            second.revision.text_tokens,
            first.revision.text_tokens,
        )
    )

    missing_predecessor = copy.deepcopy(value)
    with pytest.raises(NarrationContractError):
        materialize_fx34(
            missing_predecessor,
            source_bytes=source,
            refresh_lineage=False,
        )


def _changed_token_revision_value(predecessor, relation: str) -> dict:
    value = fx34_value()
    value["parent_revision_id"] = predecessor.revision_id
    value["text_tokens"][0]["normalized_alignment_text"] = "alpha-v2"
    current = _test_node_inventory(value, FX34_SOURCE_BYTES)
    changed = next(
        item
        for item in current
        if item["raw"] is value["text_tokens"][0]
    )
    supersedes = (
        {("TOKEN", changed["node_id"]): predecessor.text_tokens[0].token_id}
        if relation == "SUPERSEDES"
        else None
    )
    _set_noninitial_manifest(
        value,
        FX34_SOURCE_BYTES,
        predecessor,
        supersedes=supersedes,
    )
    return value


def test_initial_lineage_manifest_is_exact_and_complete() -> None:
    revision = materialize_fx34().revision

    assert revision.lineage_manifest.schema_version == NARRATION_LINEAGE_V1
    assert revision.lineage_manifest.predecessor_revision_id is None
    assert revision.lineage_manifest.removed_predecessors == ()
    assert all(
        record.relation is NodeLineageRelation.INITIAL
        and record.predecessor_node_id is None
        for record in revision.lineage_manifest.records
    )
    assert [record.node_type for record in revision.lineage_manifest.records] == [
        LineageNodeType.SECTION,
        LineageNodeType.PARAGRAPH,
        LineageNodeType.SENTENCE,
        LineageNodeType.SENTENCE,
        *([LineageNodeType.TOKEN] * 6),
    ]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("node_type", "WORD"),
        ("node_type", "token"),
        ("relation", "initial"),
        ("relation", "CONTINUES"),
    ],
)
def test_lineage_enums_are_closed_and_byte_exact(
    field: str,
    value: str,
) -> None:
    narration = fx34_value()
    narration["lineage_manifest"]["records"][0][field] = value

    with pytest.raises(NarrationContractError) as exc_info:
        materialize_fx34(narration, refresh_lineage=False)

    assert exc_info.value.issue_code == "UNSUPPORTED_CONTRACT_ENUM"


@pytest.mark.parametrize("mutation", ["inserted", "removed", "missing", "duplicate"])
def test_initial_lineage_rejects_invalid_partition(mutation: str) -> None:
    value = fx34_value()
    manifest = value["lineage_manifest"]
    if mutation == "inserted":
        manifest["records"][0]["relation"] = "INSERTED"
    elif mutation == "removed":
        manifest["removed_predecessors"] = [
            {"node_type": "SECTION", "node_id": "nsec_removed"}
        ]
    elif mutation == "missing":
        manifest["records"].pop()
    else:
        manifest["records"].append(copy.deepcopy(manifest["records"][-1]))

    with pytest.raises(NarrationContractError):
        materialize_fx34(value, refresh_lineage=False)


def test_exact_lineage_manifest_field_and_alias_contract() -> None:
    accepted = materialize_fx34()
    assert accepted.revision.lineage_manifest.records
    value = fx34_value()
    value["narration_lineage_manifest"] = value.pop("lineage_manifest")

    with pytest.raises(NarrationContractError) as exc_info:
        materialize_fx34(value, refresh_lineage=False)

    assert (
        exc_info.value.reason
        is NarrationRejectionReason.CLOSED_FIELD_VIOLATION
    )


def test_revision_parent_must_match_manifest_predecessor() -> None:
    predecessor = materialize_fx34().revision
    value = _noninitial_unchanged_value(predecessor)
    value["lineage_manifest"]["predecessor_revision_id"] = "narrev_other"

    with pytest.raises(NarrationContractError):
        materialize_fx34(
            value,
            predecessor=predecessor,
            refresh_lineage=False,
        )


def test_valid_unchanged_supercedes_inserted_and_delete_plus_insert() -> None:
    predecessor = materialize_fx34().revision
    unchanged_value = _noninitial_unchanged_value(predecessor)
    unchanged = materialize_fx34(
        unchanged_value,
        predecessor=predecessor,
        refresh_lineage=False,
    )
    supersedes_value = _changed_token_revision_value(
        predecessor,
        "SUPERSEDES",
    )
    supersedes = materialize_fx34(
        supersedes_value,
        predecessor=predecessor,
        refresh_lineage=False,
    )
    inserted_value = _changed_token_revision_value(
        predecessor,
        "INSERTED",
    )
    inserted = materialize_fx34(
        inserted_value,
        predecessor=predecessor,
        refresh_lineage=False,
    )

    assert all(
        record.relation is NodeLineageRelation.UNCHANGED
        for record in unchanged.revision.lineage_manifest.records
    )
    assert supersedes.revision.text_tokens[0].supersedes_id == (
        predecessor.text_tokens[0].token_id
    )
    inserted_record = next(
        record
        for record in inserted.revision.lineage_manifest.records
        if record.successor_node_id
        == inserted.revision.text_tokens[0].token_id
    )
    assert inserted_record.relation is NodeLineageRelation.INSERTED
    assert inserted_record.predecessor_node_id is None
    assert inserted.revision.text_tokens[0].supersedes_id is None
    assert any(
        reference.node_id == predecessor.text_tokens[0].token_id
        for reference in inserted.revision.lineage_manifest.removed_predecessors
    )
    assert supersedes.revision.revision_hash != inserted.revision.revision_hash


def test_same_id_changed_payload_cannot_be_unchanged() -> None:
    predecessor = materialize_fx34().revision
    changed_token = replace(
        predecessor.text_tokens[0],
        normalized_alignment_text="tampered",
    )
    tampered = replace(
        predecessor,
        text_tokens=(changed_token, *predecessor.text_tokens[1:]),
    )
    value = _noninitial_unchanged_value(predecessor)

    with pytest.raises(NarrationContractError):
        materialize_fx34(
            value,
            predecessor=tampered,
            refresh_lineage=False,
        )


@pytest.mark.parametrize(
    "mutation",
    [
        "same_id_inserted",
        "missing_super_predecessor",
        "mismatched_supersedes",
        "self_supersession",
        "foreign_predecessor",
        "wrong_type",
    ],
)
def test_relation_validation_is_fail_closed(mutation: str) -> None:
    predecessor = materialize_fx34().revision
    if mutation == "same_id_inserted":
        value = _noninitial_unchanged_value(predecessor)
        record = value["lineage_manifest"]["records"][-1]
        record["relation"] = "INSERTED"
        record["predecessor_node_id"] = None
        value["lineage_manifest"]["removed_predecessors"].append(
            {
                "node_type": "TOKEN",
                "node_id": predecessor.text_tokens[-1].token_id,
            }
        )
    else:
        value = _changed_token_revision_value(predecessor, "SUPERSEDES")
        record = next(
            item
            for item in value["lineage_manifest"]["records"]
            if item["relation"] == "SUPERSEDES"
        )
        if mutation == "missing_super_predecessor":
            record["predecessor_node_id"] = None
        elif mutation == "mismatched_supersedes":
            value["text_tokens"][0]["supersedes_id"] = (
                predecessor.text_tokens[1].token_id
            )
        elif mutation == "self_supersession":
            record["predecessor_node_id"] = record["successor_node_id"]
            value["text_tokens"][0]["supersedes_id"] = record[
                "successor_node_id"
            ]
        elif mutation == "foreign_predecessor":
            record["predecessor_node_id"] = "ntok_foreign"
            value["text_tokens"][0]["supersedes_id"] = "ntok_foreign"
        else:
            record["predecessor_node_id"] = (
                predecessor.sections[0].section_id
            )
            value["text_tokens"][0]["supersedes_id"] = (
                predecessor.sections[0].section_id
            )

    with pytest.raises(NarrationContractError):
        materialize_fx34(
            value,
            predecessor=predecessor,
            refresh_lineage=False,
        )


def test_duplicate_referenced_removed_and_missing_partition_are_rejected() -> None:
    predecessor = materialize_fx34().revision
    duplicate = _changed_token_revision_value(predecessor, "SUPERSEDES")
    super_record = next(
        item
        for item in duplicate["lineage_manifest"]["records"]
        if item["relation"] == "SUPERSEDES"
    )
    second_token_record = duplicate["lineage_manifest"]["records"][-5]
    second_token_record["relation"] = "SUPERSEDES"
    second_token_record["predecessor_node_id"] = super_record[
        "predecessor_node_id"
    ]
    duplicate["text_tokens"][1]["supersedes_id"] = super_record[
        "predecessor_node_id"
    ]
    with pytest.raises(NarrationContractError):
        materialize_fx34(
            duplicate,
            predecessor=predecessor,
            refresh_lineage=False,
        )

    referenced_and_removed = _changed_token_revision_value(
        predecessor,
        "SUPERSEDES",
    )
    referenced_and_removed["lineage_manifest"]["removed_predecessors"].append(
        {
            "node_type": "TOKEN",
            "node_id": predecessor.text_tokens[0].token_id,
        }
    )
    with pytest.raises(NarrationContractError):
        materialize_fx34(
            referenced_and_removed,
            predecessor=predecessor,
            refresh_lineage=False,
        )

    missing = _changed_token_revision_value(predecessor, "INSERTED")
    missing["lineage_manifest"]["removed_predecessors"] = []
    with pytest.raises(NarrationContractError):
        materialize_fx34(
            missing,
            predecessor=predecessor,
            refresh_lineage=False,
        )


@pytest.mark.parametrize(
    ("parent_level", "child_type"),
    [
        ("section", "PARAGRAPH"),
        ("paragraph", "SENTENCE"),
        ("sentence", "TOKEN"),
    ],
)
def test_inserted_parent_cannot_preserve_child_continuity(
    parent_level: str,
    child_type: str,
) -> None:
    predecessor = materialize_fx34().revision
    value = fx34_value()
    value["parent_revision_id"] = predecessor.revision_id
    if parent_level == "section":
        value["sections"][0]["order"] = 1
        for token in value["text_tokens"]:
            token["section_order"] = 1
    elif parent_level == "paragraph":
        value["sections"][0]["paragraphs"][0]["order"] = 1
        for token in value["text_tokens"]:
            token["paragraph_order"] = 1
    else:
        value["sections"][0]["paragraphs"][0]["sentences"][0][
            "segmentation_rule_version"
        ] = "fx34-sentence-v2"
    current = _test_node_inventory(value, FX34_SOURCE_BYTES)
    child = next(item for item in current if item["node_type"] == child_type)
    old_id = next(
        node_id
        for node_type, node_id in _predecessor_inventory(predecessor)
        if node_type == child_type
    )
    _set_noninitial_manifest(
        value,
        FX34_SOURCE_BYTES,
        predecessor,
        supersedes={(child_type, child["node_id"]): old_id},
    )

    with pytest.raises(NarrationContractError):
        materialize_fx34(
            value,
            predecessor=predecessor,
            refresh_lineage=False,
        )


def test_valid_corresponding_parent_chain_is_accepted() -> None:
    predecessor = materialize_fx34().revision
    value = fx34_value()
    value["parent_revision_id"] = predecessor.revision_id
    value["sections"][0]["order"] = 1
    for token in value["text_tokens"]:
        token["section_order"] = 1
    current = _test_node_inventory(value, FX34_SOURCE_BYTES)
    previous = _predecessor_inventory(predecessor)
    explicit = {
        (item["node_type"], item["node_id"]): old_id
        for item, (old_type, old_id) in zip(current, previous)
        if item["node_type"] == old_type
    }
    _set_noninitial_manifest(
        value,
        FX34_SOURCE_BYTES,
        predecessor,
        supersedes=explicit,
    )

    result = materialize_fx34(
        value,
        predecessor=predecessor,
        refresh_lineage=False,
    )

    assert all(
        record.relation is NodeLineageRelation.SUPERSEDES
        for record in result.revision.lineage_manifest.records
    )


def test_prefix_insertion_has_only_explicit_nonpositional_lineage() -> None:
    predecessor = materialize_fx34().revision
    source = b"New Alpha beta. Gamma delta."
    value = fx34_value()
    value["parent_revision_id"] = predecessor.revision_id
    section = value["sections"][0]
    paragraph = section["paragraphs"][0]
    section["source_end"] = 28
    paragraph["source_end"] = 28
    first_sentence, second_sentence = paragraph["sentences"]
    first_sentence["source_end"] = 15
    second_sentence["source_start"] = 16
    second_sentence["source_end"] = 28
    new_token = {
        "kind": "SPOKEN",
        "display_text": "New",
        "normalized_alignment_text": "new",
        "text_order": 0,
        "canonical_word_ordinal": 0,
        "source_start": 0,
        "source_end": 3,
        "section_order": 0,
        "paragraph_order": 0,
        "sentence_order": 0,
        "extensions": {},
    }
    for token in value["text_tokens"]:
        token["text_order"] += 1
        token["source_start"] += 4
        token["source_end"] += 4
        if token["canonical_word_ordinal"] is not None:
            token["canonical_word_ordinal"] += 1
    value["text_tokens"].insert(0, new_token)
    value["canonical_words"] = [
        {
            "text_order": token["text_order"],
            "canonical_word_ordinal": token["canonical_word_ordinal"],
        }
        for token in value["text_tokens"]
        if token["kind"] == "SPOKEN"
    ]
    current = _test_node_inventory(value, source)
    current_by_type = {
        node_type: [
            item for item in current if item["node_type"] == node_type
        ]
        for node_type in ("SECTION", "PARAGRAPH", "SENTENCE", "TOKEN")
    }
    previous_by_type = {
        node_type: [
            node_id
            for previous_type, node_id in _predecessor_inventory(predecessor)
            if previous_type == node_type
        ]
        for node_type in ("SECTION", "PARAGRAPH", "SENTENCE", "TOKEN")
    }
    explicit: dict[tuple[str, str], str] = {}
    for node_type in ("SECTION", "PARAGRAPH", "SENTENCE"):
        explicit.update(
            {
                (node_type, item["node_id"]): old_id
                for item, old_id in zip(
                    current_by_type[node_type],
                    previous_by_type[node_type],
                )
            }
        )
    explicit.update(
        {
            ("TOKEN", item["node_id"]): old_id
            for item, old_id in zip(
                current_by_type["TOKEN"][1:],
                previous_by_type["TOKEN"],
            )
        }
    )
    _set_noninitial_manifest(
        value,
        source,
        predecessor,
        supersedes=explicit,
    )

    result = materialize_fx34(
        value,
        source_bytes=source,
        predecessor=predecessor,
        refresh_lineage=False,
    )
    token_records = [
        record
        for record in result.revision.lineage_manifest.records
        if record.node_type is LineageNodeType.TOKEN
    ]

    assert result.revision.text_tokens[0].display_text == "New"
    assert token_records[0].relation is NodeLineageRelation.INSERTED
    assert token_records[0].predecessor_node_id is None
    assert result.revision.text_tokens[0].supersedes_id is None
    assert all(
        record.relation is NodeLineageRelation.SUPERSEDES
        for record in token_records[1:]
    )
    assert [
        record.predecessor_node_id for record in token_records[1:]
    ] == [token.token_id for token in predecessor.text_tokens]


@pytest.mark.parametrize("mutation", ["type_order", "within_type", "removed_order"])
def test_manifest_order_is_exact(mutation: str) -> None:
    predecessor = materialize_fx34().revision
    if mutation == "removed_order":
        value = fx34_value()
        value["parent_revision_id"] = predecessor.revision_id
        value["text_tokens"][0]["normalized_alignment_text"] = "alpha-v2"
        value["text_tokens"][1]["normalized_alignment_text"] = "beta-v2"
        _set_noninitial_manifest(value, FX34_SOURCE_BYTES, predecessor)
        removed = value["lineage_manifest"]["removed_predecessors"]
        removed[-2], removed[-1] = removed[-1], removed[-2]
    else:
        value = _noninitial_unchanged_value(predecessor)
        records = value["lineage_manifest"]["records"]
        if mutation == "type_order":
            records[0], records[1] = records[1], records[0]
        else:
            records[2], records[3] = records[3], records[2]

    with pytest.raises(NarrationContractError):
        materialize_fx34(
            value,
            predecessor=predecessor,
            refresh_lineage=False,
        )


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
