"""Canonical narration identity, hierarchy, and word-range contracts."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from enum import Enum
from types import MappingProxyType
from typing import Any

from ._canonical_json import encode_canonical_json_bytes


CANONICAL_NARRATION_DOCUMENT_V1 = "CANONICAL-NARRATION-DOCUMENT-V1"
NARRATION_REVISION_V1 = "NARRATION-REVISION-V1"
NARRATION_REVISION_HASH_V1 = "narration-revision-hash-v1"
NORMALIZATION_PROFILE_HASH_V1 = "normalization-profile-hash-v1"

_HASH_PATTERN = re.compile(r"sha256:[0-9a-f]{64}")
_STABLE_ID_PATTERN = re.compile(
    r"[a-z][a-z0-9]*_[a-z0-9][a-z0-9_-]{2,63}"
)
_EXTENSION_KEY_PATTERN = re.compile(
    r"[a-z][a-z0-9-]*:[a-z][a-z0-9_]*"
)
_UINT32_MAX = 2**32 - 1


class TokenKind(str, Enum):
    SPOKEN = "SPOKEN"
    PUNCTUATION = "PUNCTUATION"
    NON_SPOKEN = "NON_SPOKEN"


class WordRangeConsumer(str, Enum):
    STRUCTURAL = "STRUCTURAL"
    SEGMENT = "SEGMENT"
    CAPTION = "CAPTION"
    PHRASE = "PHRASE"
    EMPHASIS = "EMPHASIS"


class NarrationRejectionReason(str, Enum):
    BOM_FORBIDDEN = "bom_forbidden"
    CLOSED_FIELD_VIOLATION = "closed_field_violation"
    EMPTY_SOURCE = "empty_source"
    EXTENSION_INVALID = "extension_invalid"
    HASH_INVALID = "hash_invalid"
    HASH_MISMATCH = "hash_mismatch"
    HIERARCHY_INVALID = "hierarchy_invalid"
    IDENTITY_MISMATCH = "identity_mismatch"
    INVALID_UTF8 = "invalid_utf8"
    SOURCE_RANGE_INVALID = "source_range_invalid"
    STRUCTURE_INVALID = "structure_invalid"
    TOKEN_ORDER_INVALID = "token_order_invalid"
    UNSUPPORTED_ENUM = "unsupported_enum"
    WORD_RANGE_INVALID = "word_range_invalid"


class NarrationContractError(ValueError):
    """Fail-closed validation error with no publishable revision output."""

    def __init__(
        self,
        reason: NarrationRejectionReason,
        pointer: str,
        message: str,
        *,
        issue_code: str | None = None,
    ):
        super().__init__(message)
        self.reason = reason
        self.pointer = pointer
        self.issue_code = issue_code


@dataclass(frozen=True)
class NormalizationProfileRef:
    hash_scope_version: str
    language: str
    locale: str
    profile_id: str
    profile_version: str
    profile_hash: str
    tokenization_rule_version: str
    number_policy_id: str
    pronunciation_policy_id: str
    lexical_alias_policy_id: str


@dataclass(frozen=True)
class NarrationSentence:
    sentence_id: str
    revision_id: str
    paragraph_id: str
    order: int
    source_start: int
    source_end: int
    segmentation_rule_version: str
    language_override: str | None
    supersedes_id: str | None
    extensions: Mapping[str, Any]


@dataclass(frozen=True)
class NarrationParagraph:
    paragraph_id: str
    revision_id: str
    section_id: str
    order: int
    source_start: int
    source_end: int
    supersedes_id: str | None
    sentences: tuple[NarrationSentence, ...]
    extensions: Mapping[str, Any]


@dataclass(frozen=True)
class NarrationSection:
    section_id: str
    revision_id: str
    order: int
    source_start: int
    source_end: int
    supersedes_id: str | None
    paragraphs: tuple[NarrationParagraph, ...]
    extensions: Mapping[str, Any]


@dataclass(frozen=True)
class CanonicalTextToken:
    token_id: str
    kind: TokenKind
    display_text: str
    normalized_alignment_text: str | None
    text_order: int
    canonical_word_ordinal: int | None
    source_start: int
    source_end: int
    section_id: str
    paragraph_id: str
    sentence_id: str
    spoken_form_override: str | None
    trace_refs: tuple[str, ...]
    supersedes_id: str | None
    extensions: Mapping[str, Any]


@dataclass(frozen=True)
class CanonicalWord:
    word_id: str
    token_id: str
    ordinal: int
    text_order: int
    display_text: str
    normalized_alignment_text: str
    source_start: int
    source_end: int
    section_id: str
    paragraph_id: str
    sentence_id: str


@dataclass(frozen=True)
class NarrationRevision:
    schema_version: str
    hash_scope_version: str
    revision_id: str
    revision_hash: str
    project_id: str
    document_id: str
    parent_revision_id: str | None
    source_byte_hash: str
    source_text: str
    normalization_profile: NormalizationProfileRef
    text_tokens: tuple[CanonicalTextToken, ...]
    canonical_words: tuple[CanonicalWord, ...]
    sections: tuple[NarrationSection, ...]
    extensions: Mapping[str, Any]


@dataclass(frozen=True)
class CanonicalNarrationDocument:
    schema_version: str
    project_id: str
    document_id: str
    current_revision_id: str
    language: str
    locale: str
    title: str | None
    extensions: Mapping[str, Any]


@dataclass(frozen=True)
class CanonicalNarrationMaterialization:
    document: CanonicalNarrationDocument
    revision: NarrationRevision
    canonical_bytes: bytes


@dataclass(frozen=True)
class WordRangeReference:
    narration_revision_id: str
    start_ordinal: int
    end_exclusive_ordinal: int

    def __post_init__(self) -> None:
        _require_stable_id(
            self.narration_revision_id,
            "$.narration_revision_id",
        )
        _require_uint32(self.start_ordinal, "$.start_ordinal")
        _require_uint32(
            self.end_exclusive_ordinal,
            "$.end_exclusive_ordinal",
        )


@dataclass(frozen=True)
class _SentenceDraft:
    sentence_id: str
    paragraph_id: str
    order: int
    source_start: int
    source_end: int
    segmentation_rule_version: str
    language_override: str | None
    supersedes_id: str | None
    extensions: Mapping[str, Any]


@dataclass(frozen=True)
class _ParagraphDraft:
    paragraph_id: str
    section_id: str
    order: int
    source_start: int
    source_end: int
    supersedes_id: str | None
    sentences: tuple[_SentenceDraft, ...]
    extensions: Mapping[str, Any]


@dataclass(frozen=True)
class _SectionDraft:
    section_id: str
    order: int
    source_start: int
    source_end: int
    supersedes_id: str | None
    paragraphs: tuple[_ParagraphDraft, ...]
    extensions: Mapping[str, Any]


_TOP_LEVEL_REQUIRED = {
    "schema_version",
    "project_id",
    "document_id",
    "language",
    "locale",
    "parent_revision_id",
    "normalization_profile",
    "sections",
    "text_tokens",
    "canonical_words",
    "extensions",
}
_TOP_LEVEL_ALLOWED = _TOP_LEVEL_REQUIRED | {"title"}
_PROFILE_REQUIRED_WITHOUT_HASH = {
    "hash_scope_version",
    "language",
    "locale",
    "profile_id",
    "profile_version",
    "tokenization_rule_version",
    "number_policy_id",
    "pronunciation_policy_id",
    "lexical_alias_policy_id",
}
_PROFILE_ALLOWED = _PROFILE_REQUIRED_WITHOUT_HASH | {"profile_hash"}
_SECTION_REQUIRED = {
    "order",
    "source_start",
    "source_end",
    "paragraphs",
    "extensions",
}
_SECTION_ALLOWED = _SECTION_REQUIRED | {"section_id", "supersedes_id"}
_PARAGRAPH_REQUIRED = {
    "order",
    "source_start",
    "source_end",
    "sentences",
    "extensions",
}
_PARAGRAPH_ALLOWED = _PARAGRAPH_REQUIRED | {
    "paragraph_id",
    "supersedes_id",
}
_SENTENCE_REQUIRED = {
    "order",
    "source_start",
    "source_end",
    "segmentation_rule_version",
    "extensions",
}
_SENTENCE_ALLOWED = _SENTENCE_REQUIRED | {
    "sentence_id",
    "language_override",
    "supersedes_id",
}
_TOKEN_REQUIRED = {
    "kind",
    "display_text",
    "normalized_alignment_text",
    "text_order",
    "canonical_word_ordinal",
    "source_start",
    "source_end",
    "section_order",
    "paragraph_order",
    "sentence_order",
    "extensions",
}
_TOKEN_ALLOWED = _TOKEN_REQUIRED | {
    "token_id",
    "spoken_form_override",
    "trace_refs",
    "supersedes_id",
}
_WORD_PROJECTION_REQUIRED = {"text_order", "canonical_word_ordinal"}


def normalization_profile_hash(profile: Mapping[str, Any]) -> str:
    """Calculate the exact declared normalization-profile identity hash."""
    profile_data = _require_mapping(profile, "$.normalization_profile")
    _require_closed_fields(
        profile_data,
        _PROFILE_REQUIRED_WITHOUT_HASH,
        _PROFILE_ALLOWED,
        "$.normalization_profile",
        allow_missing={"profile_hash"},
    )
    payload = {
        field: profile_data[field]
        for field in sorted(_PROFILE_REQUIRED_WITHOUT_HASH)
    }
    _validate_profile_payload(payload, "$.normalization_profile")
    return _sha256(payload)


def materialize_canonical_narration(
    source_bytes: bytes,
    value: Mapping[str, Any],
    *,
    predecessor: NarrationRevision | None = None,
) -> CanonicalNarrationMaterialization:
    """Validate and deterministically materialize one narration revision."""
    source_text, source_byte_hash = _decode_source(source_bytes)
    data = _require_mapping(value, "$")
    _require_closed_fields(
        data,
        _TOP_LEVEL_REQUIRED,
        _TOP_LEVEL_ALLOWED,
        "$",
    )

    if data["schema_version"] != NARRATION_REVISION_V1:
        _reject(
            NarrationRejectionReason.UNSUPPORTED_ENUM,
            "$.schema_version",
            f"schema_version must be {NARRATION_REVISION_V1}.",
            issue_code="UNSUPPORTED_CONTRACT_ENUM",
        )

    project_id = _require_stable_id(data["project_id"], "$.project_id")
    document_id = _require_stable_id(data["document_id"], "$.document_id")
    language = _require_nonempty_string(data["language"], "$.language")
    locale = _require_nonempty_string(data["locale"], "$.locale")
    title = data.get("title")
    if title is not None:
        title = _require_string(title, "$.title")

    parent_revision_id = data["parent_revision_id"]
    if parent_revision_id is not None:
        parent_revision_id = _require_stable_id(
            parent_revision_id,
            "$.parent_revision_id",
        )
    _validate_predecessor(
        predecessor,
        parent_revision_id,
        project_id,
        document_id,
    )

    document_extensions = _validate_extensions(data["extensions"], "$.extensions")
    profile = _parse_normalization_profile(
        data["normalization_profile"],
        language,
        locale,
    )
    stable_identity_context = {
        "project_id": project_id,
        "document_id": document_id,
    }

    sections = _build_hierarchy(
        data["sections"],
        stable_identity_context,
        source_text,
    )
    sections = _apply_hierarchy_lineage(sections, predecessor)
    hierarchy_lookup = _hierarchy_lookup(sections)
    tokens = _build_tokens(
        data["text_tokens"],
        stable_identity_context,
        source_text,
        hierarchy_lookup,
    )
    tokens = _apply_token_lineage(tokens, predecessor)
    words = _build_canonical_words(
        tokens,
        data["canonical_words"],
        stable_identity_context,
    )
    _validate_hierarchy_word_coverage(sections, words)

    revision_extensions = document_extensions
    revision_scope = {
        "schema_version": NARRATION_REVISION_V1,
        "hash_scope_version": NARRATION_REVISION_HASH_V1,
        "project_id": project_id,
        "document_id": document_id,
        "parent_revision_id": parent_revision_id,
        "source_byte_hash": source_byte_hash,
        "source_text": source_text,
        "normalization_profile": _profile_to_dict(profile),
        "text_tokens": [_token_to_dict(token) for token in tokens],
        "canonical_words": [_word_to_dict(word) for word in words],
        "sections": [_section_draft_to_dict(section) for section in sections],
        "extensions": _thaw_json(revision_extensions),
    }
    revision_hash = _sha256(revision_scope)
    revision_id = (
        "narrev_" + revision_hash.removeprefix("sha256:")[:20]
    )

    final_sections = _bind_revision_to_hierarchy(sections, revision_id)
    revision = NarrationRevision(
        schema_version=NARRATION_REVISION_V1,
        hash_scope_version=NARRATION_REVISION_HASH_V1,
        revision_id=revision_id,
        revision_hash=revision_hash,
        project_id=project_id,
        document_id=document_id,
        parent_revision_id=parent_revision_id,
        source_byte_hash=source_byte_hash,
        source_text=source_text,
        normalization_profile=profile,
        text_tokens=tokens,
        canonical_words=words,
        sections=final_sections,
        extensions=revision_extensions,
    )
    document = CanonicalNarrationDocument(
        schema_version=CANONICAL_NARRATION_DOCUMENT_V1,
        project_id=project_id,
        document_id=document_id,
        current_revision_id=revision_id,
        language=language,
        locale=locale,
        title=title,
        extensions=document_extensions,
    )
    canonical_bytes = encode_canonical_json_bytes(
        {
            "document": _document_to_dict(document),
            "revision": _revision_to_dict(revision),
        }
    )
    return CanonicalNarrationMaterialization(
        document=document,
        revision=revision,
        canonical_bytes=canonical_bytes,
    )


def resolve_word_range(
    revision: NarrationRevision,
    reference: WordRangeReference,
    *,
    consumer: WordRangeConsumer = WordRangeConsumer.STRUCTURAL,
) -> tuple[CanonicalWord, ...]:
    """Resolve an exact half-open range against canonical word order."""
    if not isinstance(consumer, WordRangeConsumer):
        _reject(
            NarrationRejectionReason.UNSUPPORTED_ENUM,
            "$consumer",
            "Word-range consumer must be an exact WordRangeConsumer value.",
            issue_code="UNSUPPORTED_CONTRACT_ENUM",
        )
    if reference.narration_revision_id != revision.revision_id:
        _reject(
            NarrationRejectionReason.WORD_RANGE_INVALID,
            "$.narration_revision_id",
            "Word range belongs to a different narration revision.",
            issue_code="WORD_RANGE_REVISION_MISMATCH",
        )
    _validate_revision_word_inventory(revision)

    start = reference.start_ordinal
    end = reference.end_exclusive_ordinal
    if start > end:
        _reject(
            NarrationRejectionReason.WORD_RANGE_INVALID,
            "$",
            "Word-range start exceeds its exclusive end.",
            issue_code="WORD_RANGE_REVERSED",
        )
    word_count = len(revision.canonical_words)
    if start > word_count or end > word_count:
        _reject(
            NarrationRejectionReason.WORD_RANGE_INVALID,
            "$",
            "Word range is outside the target revision.",
            issue_code="WORD_RANGE_OUT_OF_BOUNDS",
        )
    if start == end and consumer is not WordRangeConsumer.STRUCTURAL:
        _reject(
            NarrationRejectionReason.WORD_RANGE_INVALID,
            "$",
            "This consumer requires a non-empty canonical word range.",
            issue_code="WORD_RANGE_OUT_OF_BOUNDS",
        )
    return revision.canonical_words[start:end]


def _decode_source(source_bytes: bytes) -> tuple[str, str]:
    if not isinstance(source_bytes, bytes):
        _reject(
            NarrationRejectionReason.STRUCTURE_INVALID,
            "$source_bytes",
            "Canonical narration source must be exact bytes.",
        )
    if source_bytes.startswith(b"\xef\xbb\xbf"):
        _reject(
            NarrationRejectionReason.BOM_FORBIDDEN,
            "$source_bytes",
            "UTF-8 BOM is forbidden.",
        )
    try:
        source_text = source_bytes.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise NarrationContractError(
            NarrationRejectionReason.INVALID_UTF8,
            "$source_bytes",
            "Canonical narration source is not valid UTF-8.",
            issue_code="INPUT_TEXT_INVALID_UTF8",
        ) from exc
    if source_text == "":
        _reject(
            NarrationRejectionReason.EMPTY_SOURCE,
            "$source_bytes",
            "Canonical narration source cannot be empty.",
        )
    return source_text, "sha256:" + hashlib.sha256(source_bytes).hexdigest()


def _parse_normalization_profile(
    value: Any,
    language: str,
    locale: str,
) -> NormalizationProfileRef:
    data = _require_mapping(value, "$.normalization_profile")
    _require_closed_fields(
        data,
        _PROFILE_REQUIRED_WITHOUT_HASH | {"profile_hash"},
        _PROFILE_ALLOWED,
        "$.normalization_profile",
    )
    _validate_profile_payload(data, "$.normalization_profile")
    profile_hash = data["profile_hash"]
    _require_hash(profile_hash, "$.normalization_profile.profile_hash")
    expected_hash = normalization_profile_hash(data)
    if profile_hash != expected_hash:
        _reject(
            NarrationRejectionReason.HASH_MISMATCH,
            "$.normalization_profile.profile_hash",
            "Normalization profile hash does not match its identity fields.",
        )
    if data["language"] != language or data["locale"] != locale:
        _reject(
            NarrationRejectionReason.STRUCTURE_INVALID,
            "$.normalization_profile",
            "Normalization profile language/locale must match the document.",
        )
    return NormalizationProfileRef(
        **{field: data[field] for field in NormalizationProfileRef.__dataclass_fields__}
    )


def _validate_profile_payload(data: Mapping[str, Any], pointer: str) -> None:
    if data["hash_scope_version"] != NORMALIZATION_PROFILE_HASH_V1:
        _reject(
            NarrationRejectionReason.UNSUPPORTED_ENUM,
            f"{pointer}.hash_scope_version",
            f"hash_scope_version must be {NORMALIZATION_PROFILE_HASH_V1}.",
            issue_code="UNSUPPORTED_CONTRACT_ENUM",
        )
    for field in _PROFILE_REQUIRED_WITHOUT_HASH - {"hash_scope_version"}:
        value = _require_nonempty_string(data[field], f"{pointer}.{field}")
        _require_nfc(value, f"{pointer}.{field}")


def _validate_predecessor(
    predecessor: NarrationRevision | None,
    parent_revision_id: str | None,
    project_id: str,
    document_id: str,
) -> None:
    if parent_revision_id is None:
        if predecessor is not None:
            _reject(
                NarrationRejectionReason.STRUCTURE_INVALID,
                "$predecessor",
                "An initial revision cannot carry a predecessor.",
            )
        return
    if predecessor is None:
        _reject(
            NarrationRejectionReason.STRUCTURE_INVALID,
            "$predecessor",
            "A non-initial revision requires its predecessor artifact.",
        )
    if predecessor.revision_id != parent_revision_id:
        _reject(
            NarrationRejectionReason.IDENTITY_MISMATCH,
            "$.parent_revision_id",
            "Parent revision identity does not match the predecessor.",
        )
    if (
        predecessor.project_id != project_id
        or predecessor.document_id != document_id
    ):
        _reject(
            NarrationRejectionReason.IDENTITY_MISMATCH,
            "$predecessor",
            "Predecessor must belong to the same project and document.",
        )


def _build_hierarchy(
    value: Any,
    identity_context: Mapping[str, Any],
    source_text: str,
) -> tuple[_SectionDraft, ...]:
    sections_data = _require_array(value, "$.sections")
    sections: list[_SectionDraft] = []
    previous_order: int | None = None
    previous_end: int | None = None
    for index, item in enumerate(sections_data):
        pointer = f"$.sections[{index}]"
        data = _require_mapping(item, pointer)
        _require_closed_fields(
            data,
            _SECTION_REQUIRED,
            _SECTION_ALLOWED,
            pointer,
        )
        order = _require_nonnegative_int(data["order"], f"{pointer}.order")
        start, end = _require_source_range(
            data["source_start"],
            data["source_end"],
            len(source_text),
            pointer,
            allow_empty=True,
        )
        _require_sibling_order(
            previous_order,
            previous_end,
            order,
            start,
            pointer,
        )
        supersedes_id = _optional_stable_id(
            data.get("supersedes_id"),
            f"{pointer}.supersedes_id",
        )
        extensions = _validate_extensions(
            data["extensions"],
            f"{pointer}.extensions",
        )
        identity = {
            **identity_context,
            "kind": "section",
            "order": order,
            "source_start": start,
            "source_end": end,
            "source_text": source_text[start:end],
        }
        section_id = _stable_token("nsec_", "narration-node-id-v1", identity)
        _validate_expected_id(
            data.get("section_id"),
            section_id,
            f"{pointer}.section_id",
        )
        paragraphs = _build_paragraphs(
            data["paragraphs"],
            identity_context,
            source_text,
            section_id,
            start,
            end,
            pointer,
        )
        sections.append(
            _SectionDraft(
                section_id=section_id,
                order=order,
                source_start=start,
                source_end=end,
                supersedes_id=supersedes_id,
                paragraphs=paragraphs,
                extensions=extensions,
            )
        )
        previous_order = order
        previous_end = end
    return tuple(sections)


def _build_paragraphs(
    value: Any,
    identity_context: Mapping[str, Any],
    source_text: str,
    section_id: str,
    parent_start: int,
    parent_end: int,
    parent_pointer: str,
) -> tuple[_ParagraphDraft, ...]:
    paragraphs_data = _require_array(value, f"{parent_pointer}.paragraphs")
    paragraphs: list[_ParagraphDraft] = []
    previous_order: int | None = None
    previous_end: int | None = None
    for index, item in enumerate(paragraphs_data):
        pointer = f"{parent_pointer}.paragraphs[{index}]"
        data = _require_mapping(item, pointer)
        _require_closed_fields(
            data,
            _PARAGRAPH_REQUIRED,
            _PARAGRAPH_ALLOWED,
            pointer,
        )
        order = _require_nonnegative_int(data["order"], f"{pointer}.order")
        start, end = _require_source_range(
            data["source_start"],
            data["source_end"],
            len(source_text),
            pointer,
            allow_empty=True,
        )
        _require_contained(start, end, parent_start, parent_end, pointer)
        _require_sibling_order(
            previous_order,
            previous_end,
            order,
            start,
            pointer,
        )
        supersedes_id = _optional_stable_id(
            data.get("supersedes_id"),
            f"{pointer}.supersedes_id",
        )
        extensions = _validate_extensions(
            data["extensions"],
            f"{pointer}.extensions",
        )
        identity = {
            **identity_context,
            "kind": "paragraph",
            "section_id": section_id,
            "order": order,
            "source_start": start,
            "source_end": end,
            "source_text": source_text[start:end],
        }
        paragraph_id = _stable_token(
            "npar_",
            "narration-node-id-v1",
            identity,
        )
        _validate_expected_id(
            data.get("paragraph_id"),
            paragraph_id,
            f"{pointer}.paragraph_id",
        )
        sentences = _build_sentences(
            data["sentences"],
            identity_context,
            source_text,
            paragraph_id,
            start,
            end,
            pointer,
        )
        paragraphs.append(
            _ParagraphDraft(
                paragraph_id=paragraph_id,
                section_id=section_id,
                order=order,
                source_start=start,
                source_end=end,
                supersedes_id=supersedes_id,
                sentences=sentences,
                extensions=extensions,
            )
        )
        previous_order = order
        previous_end = end
    return tuple(paragraphs)


def _build_sentences(
    value: Any,
    identity_context: Mapping[str, Any],
    source_text: str,
    paragraph_id: str,
    parent_start: int,
    parent_end: int,
    parent_pointer: str,
) -> tuple[_SentenceDraft, ...]:
    sentences_data = _require_array(value, f"{parent_pointer}.sentences")
    sentences: list[_SentenceDraft] = []
    previous_order: int | None = None
    previous_end: int | None = None
    for index, item in enumerate(sentences_data):
        pointer = f"{parent_pointer}.sentences[{index}]"
        data = _require_mapping(item, pointer)
        _require_closed_fields(
            data,
            _SENTENCE_REQUIRED,
            _SENTENCE_ALLOWED,
            pointer,
        )
        order = _require_nonnegative_int(data["order"], f"{pointer}.order")
        start, end = _require_source_range(
            data["source_start"],
            data["source_end"],
            len(source_text),
            pointer,
            allow_empty=True,
        )
        _require_contained(start, end, parent_start, parent_end, pointer)
        _require_sibling_order(
            previous_order,
            previous_end,
            order,
            start,
            pointer,
        )
        rule_version = _require_nonempty_string(
            data["segmentation_rule_version"],
            f"{pointer}.segmentation_rule_version",
        )
        _require_nfc(rule_version, f"{pointer}.segmentation_rule_version")
        language_override = data.get("language_override")
        if language_override is not None:
            language_override = _require_nonempty_string(
                language_override,
                f"{pointer}.language_override",
            )
            _require_nfc(
                language_override,
                f"{pointer}.language_override",
            )
        supersedes_id = _optional_stable_id(
            data.get("supersedes_id"),
            f"{pointer}.supersedes_id",
        )
        extensions = _validate_extensions(
            data["extensions"],
            f"{pointer}.extensions",
        )
        identity = {
            **identity_context,
            "kind": "sentence",
            "paragraph_id": paragraph_id,
            "order": order,
            "source_start": start,
            "source_end": end,
            "source_text": source_text[start:end],
            "segmentation_rule_version": rule_version,
            "language_override": language_override,
        }
        sentence_id = _stable_token(
            "nsen_",
            "narration-node-id-v1",
            identity,
        )
        _validate_expected_id(
            data.get("sentence_id"),
            sentence_id,
            f"{pointer}.sentence_id",
        )
        sentences.append(
            _SentenceDraft(
                sentence_id=sentence_id,
                paragraph_id=paragraph_id,
                order=order,
                source_start=start,
                source_end=end,
                segmentation_rule_version=rule_version,
                language_override=language_override,
                supersedes_id=supersedes_id,
                extensions=extensions,
            )
        )
        previous_order = order
        previous_end = end
    return tuple(sentences)


def _apply_hierarchy_lineage(
    sections: tuple[_SectionDraft, ...],
    predecessor: NarrationRevision | None,
) -> tuple[_SectionDraft, ...]:
    if predecessor is None:
        for section in sections:
            _require_initial_node_has_no_supersedes(section.supersedes_id)
            for paragraph in section.paragraphs:
                _require_initial_node_has_no_supersedes(
                    paragraph.supersedes_id
                )
                for sentence in paragraph.sentences:
                    _require_initial_node_has_no_supersedes(
                        sentence.supersedes_id
                    )
        return sections

    previous_sections = {
        section.order: section for section in predecessor.sections
    }
    previous_section_ids = {
        section.section_id for section in predecessor.sections
    }
    previous_paragraph_ids = {
        paragraph.paragraph_id
        for section in predecessor.sections
        for paragraph in section.paragraphs
    }
    previous_sentence_ids = {
        sentence.sentence_id
        for section in predecessor.sections
        for paragraph in section.paragraphs
        for sentence in paragraph.sentences
    }
    resolved_sections: list[_SectionDraft] = []
    for section in sections:
        previous_section = previous_sections.get(section.order)
        resolved_paragraphs: list[_ParagraphDraft] = []
        previous_paragraphs = (
            {
                paragraph.order: paragraph
                for paragraph in previous_section.paragraphs
            }
            if previous_section is not None
            else {}
        )
        for paragraph in section.paragraphs:
            previous_paragraph = previous_paragraphs.get(paragraph.order)
            resolved_sentences: list[_SentenceDraft] = []
            previous_sentences = (
                {
                    sentence.order: sentence
                    for sentence in previous_paragraph.sentences
                }
                if previous_paragraph is not None
                else {}
            )
            for sentence in paragraph.sentences:
                previous_sentence = previous_sentences.get(sentence.order)
                resolved_sentences.append(
                    replace(
                        sentence,
                        supersedes_id=_resolve_supersedes(
                            sentence.sentence_id,
                            sentence.supersedes_id,
                            (
                                previous_sentence.sentence_id
                                if previous_sentence is not None
                                else None
                            ),
                            "$.sections[].paragraphs[].sentences[]",
                            previous_sentence_ids,
                        ),
                    )
                )
            resolved_paragraphs.append(
                replace(
                    paragraph,
                    supersedes_id=_resolve_supersedes(
                        paragraph.paragraph_id,
                        paragraph.supersedes_id,
                        (
                            previous_paragraph.paragraph_id
                            if previous_paragraph is not None
                            else None
                        ),
                        "$.sections[].paragraphs[]",
                        previous_paragraph_ids,
                    ),
                    sentences=tuple(resolved_sentences),
                )
            )
        resolved_sections.append(
            replace(
                section,
                supersedes_id=_resolve_supersedes(
                    section.section_id,
                    section.supersedes_id,
                    (
                        previous_section.section_id
                        if previous_section is not None
                        else None
                    ),
                    "$.sections[]",
                    previous_section_ids,
                ),
                paragraphs=tuple(resolved_paragraphs),
            )
        )
    return tuple(resolved_sections)


def _apply_token_lineage(
    tokens: tuple[CanonicalTextToken, ...],
    predecessor: NarrationRevision | None,
) -> tuple[CanonicalTextToken, ...]:
    if predecessor is None:
        for token in tokens:
            _require_initial_node_has_no_supersedes(token.supersedes_id)
        return tokens

    previous_tokens = {
        token.text_order: token for token in predecessor.text_tokens
    }
    previous_token_ids = {
        token.token_id for token in predecessor.text_tokens
    }
    return tuple(
        replace(
            token,
            supersedes_id=_resolve_supersedes(
                token.token_id,
                token.supersedes_id,
                (
                    previous_tokens[token.text_order].token_id
                    if token.text_order in previous_tokens
                    else None
                ),
                "$.text_tokens[]",
                previous_token_ids,
            ),
        )
        for token in tokens
    )


def _require_initial_node_has_no_supersedes(
    supersedes_id: str | None,
) -> None:
    if supersedes_id is not None:
        _reject(
            NarrationRejectionReason.IDENTITY_MISMATCH,
            "$.supersedes_id",
            "Initial-revision identities cannot supersede prior nodes.",
        )


def _resolve_supersedes(
    current_id: str,
    declared_supersedes_id: str | None,
    previous_id: str | None,
    pointer: str,
    valid_previous_ids: set[str],
) -> str | None:
    if previous_id is None:
        if declared_supersedes_id is None:
            return None
        if declared_supersedes_id not in valid_previous_ids:
            _reject(
                NarrationRejectionReason.IDENTITY_MISMATCH,
                f"{pointer}.supersedes_id",
                "supersedes_id does not resolve in the predecessor graph.",
            )
        return declared_supersedes_id
    expected = (
        previous_id
        if current_id != previous_id
        else None
    )
    if declared_supersedes_id is not None and declared_supersedes_id != expected:
        _reject(
            NarrationRejectionReason.IDENTITY_MISMATCH,
            f"{pointer}.supersedes_id",
            "supersedes_id does not match predecessor identity lineage.",
        )
    return expected


def _hierarchy_lookup(
    sections: tuple[_SectionDraft, ...],
) -> dict[tuple[int, int, int], tuple[_SectionDraft, _ParagraphDraft, _SentenceDraft]]:
    lookup: dict[
        tuple[int, int, int],
        tuple[_SectionDraft, _ParagraphDraft, _SentenceDraft],
    ] = {}
    for section in sections:
        for paragraph in section.paragraphs:
            for sentence in paragraph.sentences:
                key = (section.order, paragraph.order, sentence.order)
                if key in lookup:
                    _reject(
                        NarrationRejectionReason.HIERARCHY_INVALID,
                        "$.sections",
                        "Hierarchy order path is not unique.",
                        issue_code="HIERARCHY_COVERAGE_BLOCKER",
                    )
                lookup[key] = (section, paragraph, sentence)
    return lookup


def _build_tokens(
    value: Any,
    identity_context: Mapping[str, Any],
    source_text: str,
    hierarchy_lookup: Mapping[
        tuple[int, int, int],
        tuple[_SectionDraft, _ParagraphDraft, _SentenceDraft],
    ],
) -> tuple[CanonicalTextToken, ...]:
    token_data = _require_array(value, "$.text_tokens")
    tokens: list[CanonicalTextToken] = []
    supplied_ids: set[str] = set()
    generated_ids: set[str] = set()
    previous_order: int | None = None
    previous_end: int | None = None
    for index, item in enumerate(token_data):
        pointer = f"$.text_tokens[{index}]"
        data = _require_mapping(item, pointer)
        _require_closed_fields(
            data,
            _TOKEN_REQUIRED,
            _TOKEN_ALLOWED,
            pointer,
        )
        kind = _parse_token_kind(data["kind"], f"{pointer}.kind")
        display_text = _require_string(
            data["display_text"],
            f"{pointer}.display_text",
        )
        text_order = _require_nonnegative_int(
            data["text_order"],
            f"{pointer}.text_order",
        )
        start, end = _require_source_range(
            data["source_start"],
            data["source_end"],
            len(source_text),
            pointer,
            allow_empty=False,
        )
        if previous_order is not None and text_order <= previous_order:
            _reject(
                NarrationRejectionReason.TOKEN_ORDER_INVALID,
                f"{pointer}.text_order",
                "text_order must be strictly increasing.",
            )
        if previous_end is not None and start < previous_end:
            _reject(
                NarrationRejectionReason.SOURCE_RANGE_INVALID,
                pointer,
                "Text-token source ranges cannot overlap or move backward.",
            )
        if source_text[start:end] != display_text:
            _reject(
                NarrationRejectionReason.SOURCE_RANGE_INVALID,
                f"{pointer}.display_text",
                "display_text must exactly equal its source code-point slice.",
            )

        hierarchy_key = (
            _require_nonnegative_int(
                data["section_order"],
                f"{pointer}.section_order",
            ),
            _require_nonnegative_int(
                data["paragraph_order"],
                f"{pointer}.paragraph_order",
            ),
            _require_nonnegative_int(
                data["sentence_order"],
                f"{pointer}.sentence_order",
            ),
        )
        hierarchy = hierarchy_lookup.get(hierarchy_key)
        if hierarchy is None:
            _reject(
                NarrationRejectionReason.HIERARCHY_INVALID,
                pointer,
                "Text token does not resolve to a hierarchy parent path.",
                issue_code="HIERARCHY_COVERAGE_BLOCKER",
            )
        section, paragraph, sentence = hierarchy
        _require_contained(
            start,
            end,
            sentence.source_start,
            sentence.source_end,
            pointer,
        )

        normalized = data["normalized_alignment_text"]
        ordinal = data["canonical_word_ordinal"]
        if kind is TokenKind.SPOKEN:
            normalized = _require_nonempty_string(
                normalized,
                f"{pointer}.normalized_alignment_text",
            )
            _require_nfc(
                normalized,
                f"{pointer}.normalized_alignment_text",
            )
            ordinal = _require_canonical_ordinal(
                ordinal,
                f"{pointer}.canonical_word_ordinal",
            )
        elif normalized is not None or ordinal is not None:
            _reject(
                NarrationRejectionReason.STRUCTURE_INVALID,
                pointer,
                "PUNCTUATION and NON_SPOKEN tokens require null normalized text and ordinal.",
            )

        spoken_form_override = data.get("spoken_form_override")
        if spoken_form_override is not None:
            spoken_form_override = _require_nonempty_string(
                spoken_form_override,
                f"{pointer}.spoken_form_override",
            )
            _require_nfc(
                spoken_form_override,
                f"{pointer}.spoken_form_override",
            )
            if kind is not TokenKind.SPOKEN:
                _reject(
                    NarrationRejectionReason.STRUCTURE_INVALID,
                    f"{pointer}.spoken_form_override",
                    "Only SPOKEN tokens may carry a spoken-form override.",
                )
        trace_refs = _validate_trace_refs(
            data.get("trace_refs", []),
            f"{pointer}.trace_refs",
        )
        if kind is not TokenKind.SPOKEN and trace_refs:
            _reject(
                NarrationRejectionReason.STRUCTURE_INVALID,
                f"{pointer}.trace_refs",
                "Only SPOKEN tokens may carry normalization trace references.",
            )
        supersedes_id = _optional_stable_id(
            data.get("supersedes_id"),
            f"{pointer}.supersedes_id",
        )
        extensions = _validate_extensions(
            data["extensions"],
            f"{pointer}.extensions",
        )

        supplied_id = data.get("token_id")
        if supplied_id is not None:
            supplied_id = _require_stable_id(
                supplied_id,
                f"{pointer}.token_id",
            )
            if supplied_id in supplied_ids:
                _reject(
                    NarrationRejectionReason.IDENTITY_MISMATCH,
                    f"{pointer}.token_id",
                    "Token IDs must be unique within a revision.",
                )
            supplied_ids.add(supplied_id)
        identity = {
            **identity_context,
            "kind": kind.value,
            "display_text": display_text,
            "normalized_alignment_text": normalized,
            "text_order": text_order,
            "canonical_word_ordinal": ordinal,
            "source_start": start,
            "source_end": end,
            "section_id": section.section_id,
            "paragraph_id": paragraph.paragraph_id,
            "sentence_id": sentence.sentence_id,
            "spoken_form_override": spoken_form_override,
            "trace_refs": list(trace_refs),
        }
        token_id = _stable_token(
            "ntok_",
            "narration-token-id-v1",
            identity,
        )
        _validate_expected_id(
            supplied_id,
            token_id,
            f"{pointer}.token_id",
        )
        if token_id in generated_ids:
            _reject(
                NarrationRejectionReason.IDENTITY_MISMATCH,
                f"{pointer}.token_id",
                "Distinct token identities produced a duplicate stable ID.",
            )
        generated_ids.add(token_id)
        tokens.append(
            CanonicalTextToken(
                token_id=token_id,
                kind=kind,
                display_text=display_text,
                normalized_alignment_text=normalized,
                text_order=text_order,
                canonical_word_ordinal=ordinal,
                source_start=start,
                source_end=end,
                section_id=section.section_id,
                paragraph_id=paragraph.paragraph_id,
                sentence_id=sentence.sentence_id,
                spoken_form_override=spoken_form_override,
                trace_refs=trace_refs,
                supersedes_id=supersedes_id,
                extensions=extensions,
            )
        )
        previous_order = text_order
        previous_end = end
    return tuple(tokens)


def _build_canonical_words(
    tokens: tuple[CanonicalTextToken, ...],
    value: Any,
    identity_context: Mapping[str, Any],
) -> tuple[CanonicalWord, ...]:
    spoken_tokens = tuple(
        token for token in tokens if token.kind is TokenKind.SPOKEN
    )
    ordinals = [token.canonical_word_ordinal for token in spoken_tokens]
    if ordinals != list(range(len(spoken_tokens))):
        _reject(
            NarrationRejectionReason.TOKEN_ORDER_INVALID,
            "$.text_tokens",
            "SPOKEN token ordinals must be unique and contiguous [0,N).",
            issue_code="CANONICAL_WORD_ORDER_INVALID",
        )

    projection_data = _require_array(value, "$.canonical_words")
    declared_projection: list[tuple[int, int]] = []
    for index, item in enumerate(projection_data):
        pointer = f"$.canonical_words[{index}]"
        data = _require_mapping(item, pointer)
        _require_closed_fields(
            data,
            _WORD_PROJECTION_REQUIRED,
            _WORD_PROJECTION_REQUIRED,
            pointer,
        )
        declared_projection.append(
            (
                _require_nonnegative_int(
                    data["text_order"],
                    f"{pointer}.text_order",
                ),
                _require_uint32(
                    data["canonical_word_ordinal"],
                    f"{pointer}.canonical_word_ordinal",
                ),
            )
        )
    expected_projection = [
        (token.text_order, token.canonical_word_ordinal)
        for token in spoken_tokens
    ]
    if declared_projection != expected_projection:
        _reject(
            NarrationRejectionReason.TOKEN_ORDER_INVALID,
            "$.canonical_words",
            "canonical_words must exactly project all and only SPOKEN tokens.",
            issue_code="CANONICAL_WORD_ORDER_INVALID",
        )

    words: list[CanonicalWord] = []
    for token in spoken_tokens:
        assert token.canonical_word_ordinal is not None
        assert token.normalized_alignment_text is not None
        word_id = _stable_token(
            "nword_",
            "canonical-word-id-v1",
            identity_context,
            token.token_id,
            token.canonical_word_ordinal,
        )
        words.append(
            CanonicalWord(
                word_id=word_id,
                token_id=token.token_id,
                ordinal=token.canonical_word_ordinal,
                text_order=token.text_order,
                display_text=token.display_text,
                normalized_alignment_text=token.normalized_alignment_text,
                source_start=token.source_start,
                source_end=token.source_end,
                section_id=token.section_id,
                paragraph_id=token.paragraph_id,
                sentence_id=token.sentence_id,
            )
        )
    return tuple(words)


def _validate_hierarchy_word_coverage(
    sections: tuple[_SectionDraft, ...],
    words: tuple[CanonicalWord, ...],
) -> None:
    section_ids = {section.section_id for section in sections}
    paragraph_ids = {
        paragraph.paragraph_id
        for section in sections
        for paragraph in section.paragraphs
    }
    sentence_ids = {
        sentence.sentence_id
        for section in sections
        for paragraph in section.paragraphs
        for sentence in paragraph.sentences
    }
    words_by_section: dict[str, int] = {}
    words_by_paragraph: dict[str, int] = {}
    words_by_sentence: dict[str, int] = {}
    for word in words:
        if (
            word.section_id not in section_ids
            or word.paragraph_id not in paragraph_ids
            or word.sentence_id not in sentence_ids
        ):
            _reject(
                NarrationRejectionReason.HIERARCHY_INVALID,
                "$.canonical_words",
                "Every canonical word must resolve to its complete hierarchy path.",
                issue_code="HIERARCHY_COVERAGE_BLOCKER",
            )
        words_by_sentence[word.sentence_id] = (
            words_by_sentence.get(word.sentence_id, 0) + 1
        )
        words_by_paragraph[word.paragraph_id] = (
            words_by_paragraph.get(word.paragraph_id, 0) + 1
        )
        words_by_section[word.section_id] = (
            words_by_section.get(word.section_id, 0) + 1
        )

    for section in sections:
        if (
            section.source_start == section.source_end
            and words_by_section.get(section.section_id, 0)
        ):
            _reject(
                NarrationRejectionReason.HIERARCHY_INVALID,
                "$.sections",
                "Empty structural nodes cannot contain lexical words.",
                issue_code="HIERARCHY_COVERAGE_BLOCKER",
            )
        for paragraph in section.paragraphs:
            if (
                paragraph.source_start == paragraph.source_end
                and words_by_paragraph.get(paragraph.paragraph_id, 0)
            ):
                _reject(
                    NarrationRejectionReason.HIERARCHY_INVALID,
                    "$.sections",
                    "Empty structural nodes cannot contain lexical words.",
                    issue_code="HIERARCHY_COVERAGE_BLOCKER",
                )
            for sentence in paragraph.sentences:
                if (
                    sentence.source_start == sentence.source_end
                    and words_by_sentence.get(sentence.sentence_id, 0)
                ):
                    _reject(
                        NarrationRejectionReason.HIERARCHY_INVALID,
                        "$.sections",
                        "Empty structural nodes cannot contain lexical words.",
                        issue_code="HIERARCHY_COVERAGE_BLOCKER",
                    )


def _validate_revision_word_inventory(revision: NarrationRevision) -> None:
    ordinals = [word.ordinal for word in revision.canonical_words]
    if ordinals != list(range(len(ordinals))):
        _reject(
            NarrationRejectionReason.TOKEN_ORDER_INVALID,
            "$.canonical_words",
            "Target revision has an invalid canonical ordinal inventory.",
            issue_code="CANONICAL_WORD_ORDER_INVALID",
        )
    token_ids = {
        token.token_id
        for token in revision.text_tokens
        if token.kind is TokenKind.SPOKEN
    }
    if (
        len(token_ids) != len(revision.canonical_words)
        or any(word.token_id not in token_ids for word in revision.canonical_words)
    ):
        _reject(
            NarrationRejectionReason.TOKEN_ORDER_INVALID,
            "$.canonical_words",
            "Target revision projection does not match its SPOKEN tokens.",
            issue_code="CANONICAL_WORD_ORDER_INVALID",
        )


def _bind_revision_to_hierarchy(
    sections: tuple[_SectionDraft, ...],
    revision_id: str,
) -> tuple[NarrationSection, ...]:
    return tuple(
        NarrationSection(
            section_id=section.section_id,
            revision_id=revision_id,
            order=section.order,
            source_start=section.source_start,
            source_end=section.source_end,
            supersedes_id=section.supersedes_id,
            paragraphs=tuple(
                NarrationParagraph(
                    paragraph_id=paragraph.paragraph_id,
                    revision_id=revision_id,
                    section_id=section.section_id,
                    order=paragraph.order,
                    source_start=paragraph.source_start,
                    source_end=paragraph.source_end,
                    supersedes_id=paragraph.supersedes_id,
                    sentences=tuple(
                        NarrationSentence(
                            sentence_id=sentence.sentence_id,
                            revision_id=revision_id,
                            paragraph_id=paragraph.paragraph_id,
                            order=sentence.order,
                            source_start=sentence.source_start,
                            source_end=sentence.source_end,
                            segmentation_rule_version=(
                                sentence.segmentation_rule_version
                            ),
                            language_override=sentence.language_override,
                            supersedes_id=sentence.supersedes_id,
                            extensions=sentence.extensions,
                        )
                        for sentence in paragraph.sentences
                    ),
                    extensions=paragraph.extensions,
                )
                for paragraph in section.paragraphs
            ),
            extensions=section.extensions,
        )
        for section in sections
    )


def _profile_to_dict(profile: NormalizationProfileRef) -> dict[str, Any]:
    return {
        field: getattr(profile, field)
        for field in NormalizationProfileRef.__dataclass_fields__
    }


def _token_to_dict(token: CanonicalTextToken) -> dict[str, Any]:
    return {
        "token_id": token.token_id,
        "kind": token.kind.value,
        "display_text": token.display_text,
        "normalized_alignment_text": token.normalized_alignment_text,
        "text_order": token.text_order,
        "canonical_word_ordinal": token.canonical_word_ordinal,
        "source_start": token.source_start,
        "source_end": token.source_end,
        "section_id": token.section_id,
        "paragraph_id": token.paragraph_id,
        "sentence_id": token.sentence_id,
        "spoken_form_override": token.spoken_form_override,
        "trace_refs": list(token.trace_refs),
        "supersedes_id": token.supersedes_id,
        "extensions": _thaw_json(token.extensions),
    }


def _word_to_dict(word: CanonicalWord) -> dict[str, Any]:
    return {
        field: getattr(word, field)
        for field in CanonicalWord.__dataclass_fields__
    }


def _sentence_draft_to_dict(sentence: _SentenceDraft) -> dict[str, Any]:
    return {
        "sentence_id": sentence.sentence_id,
        "paragraph_id": sentence.paragraph_id,
        "order": sentence.order,
        "source_start": sentence.source_start,
        "source_end": sentence.source_end,
        "segmentation_rule_version": sentence.segmentation_rule_version,
        "language_override": sentence.language_override,
        "supersedes_id": sentence.supersedes_id,
        "extensions": _thaw_json(sentence.extensions),
    }


def _paragraph_draft_to_dict(paragraph: _ParagraphDraft) -> dict[str, Any]:
    return {
        "paragraph_id": paragraph.paragraph_id,
        "section_id": paragraph.section_id,
        "order": paragraph.order,
        "source_start": paragraph.source_start,
        "source_end": paragraph.source_end,
        "supersedes_id": paragraph.supersedes_id,
        "sentences": [
            _sentence_draft_to_dict(sentence)
            for sentence in paragraph.sentences
        ],
        "extensions": _thaw_json(paragraph.extensions),
    }


def _section_draft_to_dict(section: _SectionDraft) -> dict[str, Any]:
    return {
        "section_id": section.section_id,
        "order": section.order,
        "source_start": section.source_start,
        "source_end": section.source_end,
        "supersedes_id": section.supersedes_id,
        "paragraphs": [
            _paragraph_draft_to_dict(paragraph)
            for paragraph in section.paragraphs
        ],
        "extensions": _thaw_json(section.extensions),
    }


def _sentence_to_dict(sentence: NarrationSentence) -> dict[str, Any]:
    return {
        field: (
            _thaw_json(sentence.extensions)
            if field == "extensions"
            else getattr(sentence, field)
        )
        for field in NarrationSentence.__dataclass_fields__
    }


def _paragraph_to_dict(paragraph: NarrationParagraph) -> dict[str, Any]:
    return {
        "paragraph_id": paragraph.paragraph_id,
        "revision_id": paragraph.revision_id,
        "section_id": paragraph.section_id,
        "order": paragraph.order,
        "source_start": paragraph.source_start,
        "source_end": paragraph.source_end,
        "supersedes_id": paragraph.supersedes_id,
        "sentences": [
            _sentence_to_dict(sentence) for sentence in paragraph.sentences
        ],
        "extensions": _thaw_json(paragraph.extensions),
    }


def _section_to_dict(section: NarrationSection) -> dict[str, Any]:
    return {
        "section_id": section.section_id,
        "revision_id": section.revision_id,
        "order": section.order,
        "source_start": section.source_start,
        "source_end": section.source_end,
        "supersedes_id": section.supersedes_id,
        "paragraphs": [
            _paragraph_to_dict(paragraph)
            for paragraph in section.paragraphs
        ],
        "extensions": _thaw_json(section.extensions),
    }


def _revision_to_dict(revision: NarrationRevision) -> dict[str, Any]:
    return {
        "schema_version": revision.schema_version,
        "hash_scope_version": revision.hash_scope_version,
        "revision_id": revision.revision_id,
        "revision_hash": revision.revision_hash,
        "project_id": revision.project_id,
        "document_id": revision.document_id,
        "parent_revision_id": revision.parent_revision_id,
        "source_byte_hash": revision.source_byte_hash,
        "source_text": revision.source_text,
        "normalization_profile": _profile_to_dict(
            revision.normalization_profile
        ),
        "text_tokens": [
            _token_to_dict(token) for token in revision.text_tokens
        ],
        "canonical_words": [
            _word_to_dict(word) for word in revision.canonical_words
        ],
        "sections": [
            _section_to_dict(section) for section in revision.sections
        ],
        "extensions": _thaw_json(revision.extensions),
    }


def _document_to_dict(document: CanonicalNarrationDocument) -> dict[str, Any]:
    return {
        "schema_version": document.schema_version,
        "project_id": document.project_id,
        "document_id": document.document_id,
        "current_revision_id": document.current_revision_id,
        "language": document.language,
        "locale": document.locale,
        "title": document.title,
        "extensions": _thaw_json(document.extensions),
    }


def _require_mapping(value: Any, pointer: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _reject(
            NarrationRejectionReason.STRUCTURE_INVALID,
            pointer,
            "Expected an object.",
        )
    if any(not isinstance(key, str) for key in value):
        _reject(
            NarrationRejectionReason.STRUCTURE_INVALID,
            pointer,
            "Object keys must be strings.",
        )
    return value


def _require_array(value: Any, pointer: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(
        value, Sequence
    ):
        _reject(
            NarrationRejectionReason.STRUCTURE_INVALID,
            pointer,
            "Expected an ordered array.",
        )
    return value


def _require_closed_fields(
    data: Mapping[str, Any],
    required: set[str],
    allowed: set[str],
    pointer: str,
    *,
    allow_missing: set[str] | None = None,
) -> None:
    missing = required - set(data)
    if allow_missing:
        missing -= allow_missing
    if missing:
        _reject(
            NarrationRejectionReason.STRUCTURE_INVALID,
            pointer,
            f"Required fields are missing: {', '.join(sorted(missing))}.",
        )
    unknown = set(data) - allowed
    if unknown:
        _reject(
            NarrationRejectionReason.CLOSED_FIELD_VIOLATION,
            pointer,
            f"Unknown fields are forbidden: {', '.join(sorted(unknown))}.",
        )


def _require_string(value: Any, pointer: str) -> str:
    if not isinstance(value, str):
        _reject(
            NarrationRejectionReason.STRUCTURE_INVALID,
            pointer,
            "Expected a string.",
        )
    _validate_unicode(value, pointer)
    return value


def _require_nonempty_string(value: Any, pointer: str) -> str:
    text = _require_string(value, pointer)
    if text == "":
        _reject(
            NarrationRejectionReason.STRUCTURE_INVALID,
            pointer,
            "String cannot be empty.",
        )
    return text


def _require_nonnegative_int(value: Any, pointer: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        _reject(
            NarrationRejectionReason.STRUCTURE_INVALID,
            pointer,
            "Expected a non-negative integer.",
        )
    return value


def _require_uint32(value: Any, pointer: str) -> int:
    integer = _require_nonnegative_int(value, pointer)
    if integer > _UINT32_MAX:
        _reject(
            NarrationRejectionReason.WORD_RANGE_INVALID,
            pointer,
            "Ordinal exceeds the uint32 contract.",
            issue_code="WORD_RANGE_OUT_OF_BOUNDS",
        )
    return integer


def _require_canonical_ordinal(value: Any, pointer: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 0
        or value > _UINT32_MAX
    ):
        _reject(
            NarrationRejectionReason.TOKEN_ORDER_INVALID,
            pointer,
            "SPOKEN canonical word ordinal must be a uint32 integer.",
            issue_code="CANONICAL_WORD_ORDER_INVALID",
        )
    return value


def _require_source_range(
    start_value: Any,
    end_value: Any,
    source_length: int,
    pointer: str,
    *,
    allow_empty: bool,
) -> tuple[int, int]:
    start = _require_nonnegative_int(
        start_value,
        f"{pointer}.source_start",
    )
    end = _require_nonnegative_int(end_value, f"{pointer}.source_end")
    if start > end or (not allow_empty and start == end):
        _reject(
            NarrationRejectionReason.SOURCE_RANGE_INVALID,
            pointer,
            "Source range is reversed or illegally empty.",
        )
    if end > source_length:
        _reject(
            NarrationRejectionReason.SOURCE_RANGE_INVALID,
            pointer,
            "Source range exceeds the source code-point boundary.",
        )
    return start, end


def _require_contained(
    start: int,
    end: int,
    parent_start: int,
    parent_end: int,
    pointer: str,
) -> None:
    if start < parent_start or end > parent_end:
        _reject(
            NarrationRejectionReason.HIERARCHY_INVALID,
            pointer,
            "Child source range must be contained by its parent.",
            issue_code="HIERARCHY_COVERAGE_BLOCKER",
        )


def _require_sibling_order(
    previous_order: int | None,
    previous_end: int | None,
    order: int,
    start: int,
    pointer: str,
) -> None:
    if previous_order is not None and order <= previous_order:
        _reject(
            NarrationRejectionReason.HIERARCHY_INVALID,
            f"{pointer}.order",
            "Sibling order must be strictly increasing.",
            issue_code="HIERARCHY_COVERAGE_BLOCKER",
        )
    if previous_end is not None and start < previous_end:
        _reject(
            NarrationRejectionReason.HIERARCHY_INVALID,
            pointer,
            "Sibling source ranges cannot overlap.",
            issue_code="HIERARCHY_COVERAGE_BLOCKER",
        )


def _require_stable_id(value: Any, pointer: str) -> str:
    text = _require_nonempty_string(value, pointer)
    if _STABLE_ID_PATTERN.fullmatch(text) is None:
        _reject(
            NarrationRejectionReason.STRUCTURE_INVALID,
            pointer,
            "Value is not a canonical stable ID.",
        )
    return text


def _optional_stable_id(value: Any, pointer: str) -> str | None:
    if value is None:
        return None
    return _require_stable_id(value, pointer)


def _require_hash(value: Any, pointer: str) -> str:
    text = _require_nonempty_string(value, pointer)
    if _HASH_PATTERN.fullmatch(text) is None:
        _reject(
            NarrationRejectionReason.HASH_INVALID,
            pointer,
            "Hash must be sha256:<64 lowercase hexadecimal digits>.",
        )
    return text


def _parse_token_kind(value: Any, pointer: str) -> TokenKind:
    try:
        return TokenKind(value)
    except (TypeError, ValueError) as exc:
        raise NarrationContractError(
            NarrationRejectionReason.UNSUPPORTED_ENUM,
            pointer,
            "Unknown canonical token kind.",
            issue_code="UNSUPPORTED_CONTRACT_ENUM",
        ) from exc


def _validate_trace_refs(value: Any, pointer: str) -> tuple[str, ...]:
    refs = _require_array(value, pointer)
    validated = tuple(
        _require_stable_id(item, f"{pointer}[{index}]")
        for index, item in enumerate(refs)
    )
    if len(set(validated)) != len(validated):
        _reject(
            NarrationRejectionReason.STRUCTURE_INVALID,
            pointer,
            "Trace references must be unique.",
        )
    return validated


def _validate_extensions(value: Any, pointer: str) -> Mapping[str, Any]:
    data = _require_mapping(value, pointer)
    for key, item in data.items():
        if (
            not isinstance(key, str)
            or _EXTENSION_KEY_PATTERN.fullmatch(key) is None
        ):
            _reject(
                NarrationRejectionReason.EXTENSION_INVALID,
                pointer,
                "Extension keys must use the V3 domain:name namespace form.",
            )
        _validate_json_value(item, f"{pointer}.{key}")
    return _freeze_json(data)


def _validate_json_value(value: Any, pointer: str) -> None:
    if value is None or isinstance(value, (bool, int)):
        return
    if isinstance(value, float):
        _reject(
            NarrationRejectionReason.EXTENSION_INVALID,
            pointer,
            "Floating-point extension values are forbidden.",
        )
    if isinstance(value, str):
        _validate_unicode(value, pointer)
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_value(item, f"{pointer}[{index}]")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                _reject(
                    NarrationRejectionReason.EXTENSION_INVALID,
                    pointer,
                    "Extension object keys must be strings.",
                )
            _validate_unicode(key, pointer)
            _validate_json_value(item, f"{pointer}.{key}")
        return
    _reject(
        NarrationRejectionReason.EXTENSION_INVALID,
        pointer,
        "Extension value is not canonical JSON.",
    )


def _require_nfc(value: str, pointer: str) -> None:
    if unicodedata.normalize("NFC", value) != value:
        _reject(
            NarrationRejectionReason.STRUCTURE_INVALID,
            pointer,
            "Derived canonical string fields must already be NFC.",
        )


def _validate_unicode(value: str, pointer: str) -> None:
    for character in value:
        codepoint = ord(character)
        if (
            0xD800 <= codepoint <= 0xDFFF
            or 0xFDD0 <= codepoint <= 0xFDEF
            or codepoint & 0xFFFF in {0xFFFE, 0xFFFF}
        ):
            _reject(
                NarrationRejectionReason.STRUCTURE_INVALID,
                pointer,
                "Unicode surrogate/noncharacter is forbidden.",
            )


def _validate_expected_id(
    declared: Any,
    expected: str,
    pointer: str,
) -> None:
    if declared is None:
        return
    declared_id = _require_stable_id(declared, pointer)
    if declared_id != expected:
        _reject(
            NarrationRejectionReason.IDENTITY_MISMATCH,
            pointer,
            "Declared stable ID does not match canonical identity content.",
        )


def _stable_token(prefix: str, *parts: Any) -> str:
    payload = encode_canonical_json_bytes(list(parts))
    return prefix + hashlib.sha256(payload).hexdigest()[:20]


def _sha256(value: Any) -> str:
    digest = hashlib.sha256(encode_canonical_json_bytes(value)).hexdigest()
    return f"sha256:{digest}"


def _freeze_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {key: _freeze_json(item) for key, item in value.items()}
        )
    if isinstance(value, list):
        return tuple(_freeze_json(item) for item in value)
    return value


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


def _reject(
    reason: NarrationRejectionReason,
    pointer: str,
    message: str,
    *,
    issue_code: str | None = None,
) -> None:
    raise NarrationContractError(
        reason,
        pointer,
        message,
        issue_code=issue_code,
    )
