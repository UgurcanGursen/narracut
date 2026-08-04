"""Canonical Phase 2 semantic emphasis-event contract."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
import weakref
from dataclasses import dataclass
from enum import Enum
from typing import Any

from ._canonical_json import encode_canonical_json_bytes
from .alignment_execution import ConfidenceAvailability
from .alignment_result import AlignmentResult, serialize_alignment_result
from .caption_groups import (
    CaptionGroupsArtifact,
    CaptionGroupsContractError,
    compile_caption_groups,
    serialize_caption_groups,
)
from .domain import DomainPackRegistry, canonical_json, policy_snapshot_hash
from .models import DomainPolicySnapshot
from .narration import (
    CanonicalNarrationDocument,
    NarrationRevision,
    WordRangeConsumer,
    WordRangeReference,
    resolve_word_range,
)


EMPHASIS_EVENT_V1 = "EMPHASIS-EVENT-V1"
EMPHASIS_EVENT_HASH_V1 = "EMPHASIS-EVENT-HASH-V1"
EMPHASIS_EVENTS_V1 = "EMPHASIS-EVENTS-V1"
EMPHASIS_EVENTS_HASH_V1 = "EMPHASIS-EVENTS-HASH-V1"
EMPHASIS_MAPPING_POLICY_V1 = "EMPHASIS-MAPPING-POLICY-V1"

_MAX_EVENTS = 10_000
_TYPE_NAME = re.compile(r"^[a-z][a-z0-9_]*$")
_SEMVER = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:[-+][0-9A-Za-z.-]+)?$")
_FORBIDDEN = frozenset({0x2028, 0x2029})


class EmphasisIntensity(str, Enum):
    SUBTLE = "SUBTLE"
    MEDIUM = "MEDIUM"
    STRONG = "STRONG"


class EmphasisEventsRejectionReason(str, Enum):
    STRUCTURE_INVALID = "STRUCTURE_INVALID"
    UNSUPPORTED_VALUE = "UNSUPPORTED_VALUE"
    DEPENDENCY_CONTENT_DRIFT = "DEPENDENCY_CONTENT_DRIFT"
    DEPENDENCY_BINDING_INVALID = "DEPENDENCY_BINDING_INVALID"
    POLICY_INVALID = "POLICY_INVALID"
    INTENT_INVALID = "INTENT_INVALID"
    WORD_RANGE_INVALID = "WORD_RANGE_INVALID"
    ORDERING_INVALID = "ORDERING_INVALID"
    OVERLAP_INVALID = "OVERLAP_INVALID"
    CAPTION_GROUP_BINDING_INVALID = "CAPTION_GROUP_BINDING_INVALID"
    TIMING_INVALID = "TIMING_INVALID"
    CONFIDENCE_INVALID = "CONFIDENCE_INVALID"
    NON_CANONICAL_SERIALIZATION = "NON_CANONICAL_SERIALIZATION"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    CONTENT_DRIFT = "CONTENT_DRIFT"
    NOT_MATERIALIZED = "NOT_MATERIALIZED"


class EmphasisEventsContractError(ValueError):
    def __init__(
        self,
        reason: EmphasisEventsRejectionReason,
        pointer: str,
        message: str,
        *,
        issue_code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.reason = reason
        self.pointer = pointer
        self.issue_code = issue_code


@dataclass(frozen=True)
class EmphasisTypeRef:
    domain_id: str
    name: str
    version: str


@dataclass(frozen=True)
class EmphasisIntent:
    word_range: WordRangeReference
    emphasis_type_ref: EmphasisTypeRef
    intensity: EmphasisIntensity


@dataclass(frozen=True)
class EmphasisEvent:
    schema_version: str
    hash_scope_version: str
    emphasis_event_id: str
    emphasis_event_hash: str
    narration_revision_id: str
    alignment_result_id: str
    caption_groups_id: str
    policy_snapshot_id: str
    policy_snapshot_hash: str
    mapping_policy_version: str
    ordinal: int
    caption_group_id: str
    start_word_ordinal: int
    end_exclusive_word_ordinal: int
    start_word_id: str
    end_word_id: str
    word_ids: tuple[str, ...]
    emphasis_type_ref: EmphasisTypeRef
    intensity: EmphasisIntensity
    start_ms: int
    end_ms: int
    confidence_millionths: int | None


@dataclass(frozen=True)
class EmphasisEventsArtifact:
    schema_version: str
    hash_scope_version: str
    emphasis_events_id: str
    emphasis_events_hash: str
    project_id: str
    document_id: str
    narration_revision_id: str
    narration_revision_hash: str
    alignment_result_id: str
    alignment_result_hash: str
    caption_groups_id: str
    caption_groups_hash: str
    mapping_policy_version: str
    domain_id: str
    domain_pack_version: str
    policy_snapshot_id: str
    policy_snapshot_hash: str
    confidence_availability: ConfidenceAvailability
    emphasis_events: tuple[EmphasisEvent, ...]


@dataclass(frozen=True)
class _ResolvedEmphasisPolicy:
    domain_id: str
    domain_pack_version: str
    snapshot_id: str
    snapshot_hash: str
    allowed: frozenset[tuple[str, str]]


_MATERIALIZED: dict[int, tuple[weakref.ReferenceType[EmphasisEventsArtifact], bytes, tuple[int, ...]]] = {}


def _identity_signature(artifact: EmphasisEventsArtifact) -> tuple[int, ...]:
    values = [id(artifact.emphasis_events)]
    for event in artifact.emphasis_events:
        values.extend((id(event), id(event.word_ids), id(event.emphasis_type_ref), id(event.intensity)))
    return tuple(values)


def _reject(
    pointer: str,
    reason: EmphasisEventsRejectionReason,
    issue_code: str | None = None,
) -> None:
    raise EmphasisEventsContractError(
        reason, pointer, "Canonical emphasis-events contract rejected input.", issue_code=issue_code
    )


def _plain(value: Any, pointer: str = "/domain_policy_snapshot") -> Any:
    if value is None or type(value) in (str, int, bool):
        return value
    if type(value) is list:
        return [_plain(item, pointer) for item in value]
    if type(value) is tuple:
        return [_plain(item, pointer) for item in value]
    if type(value) is dict:
        if not all(type(key) is str for key in value):
            _reject(pointer, EmphasisEventsRejectionReason.STRUCTURE_INVALID)
        return {key: _plain(item, pointer) for key, item in value.items()}
    _reject(pointer, EmphasisEventsRejectionReason.STRUCTURE_INVALID)


def _snapshot_dict(snapshot: DomainPolicySnapshot) -> dict[str, Any]:
    return {
        "schema_version": snapshot.schema_version,
        "snapshot_id": snapshot.snapshot_id,
        "domain_id": snapshot.domain_id,
        "domain_pack_version": snapshot.domain_pack_version,
        "profile_id": snapshot.profile_id,
        "manifest_hash": snapshot.manifest_hash,
        "resolved_policy": _plain(snapshot.resolved_policy),
        "canonical_hash": snapshot.canonical_hash,
        "immutable": snapshot.immutable,
        "created_at": snapshot.created_at,
        "version": snapshot.version,
    }


def _safe(value: Any, *, name: bool = False, semver: bool = False) -> bool:
    if type(value) is not str or not value or unicodedata.normalize("NFC", value) != value:
        return False
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F or ord(ch) in _FORBIDDEN for ch in value):
        return False
    if name and (len(value) > 128 or _TYPE_NAME.fullmatch(value) is None):
        return False
    if semver and _SEMVER.fullmatch(value) is None:
        return False
    return True


def _resolve_policy(
    snapshot: DomainPolicySnapshot, registry: DomainPackRegistry
) -> _ResolvedEmphasisPolicy:
    data = _snapshot_dict(snapshot)
    if type(snapshot.immutable) is not bool or snapshot.immutable is not True:
        _reject("/domain_policy_snapshot", EmphasisEventsRejectionReason.POLICY_INVALID)
    try:
        actual_hash = policy_snapshot_hash(data)
    except Exception:
        _reject("/domain_policy_snapshot", EmphasisEventsRejectionReason.DEPENDENCY_CONTENT_DRIFT)
    if snapshot.canonical_hash != actual_hash or snapshot.snapshot_id != "dps_" + actual_hash[7:27]:
        _reject("/domain_policy_snapshot", EmphasisEventsRejectionReason.DEPENDENCY_CONTENT_DRIFT)
    try:
        pack = registry.get(snapshot.domain_id, snapshot.domain_pack_version)
        manifest = _plain(pack.raw_manifest)
        manifest_hash = "sha256:" + hashlib.sha256(canonical_json(manifest).encode("utf-8")).hexdigest()
    except Exception:
        _reject("/domain_policy_snapshot", EmphasisEventsRejectionReason.POLICY_INVALID)
    if snapshot.manifest_hash != manifest_hash:
        _reject("/domain_policy_snapshot", EmphasisEventsRejectionReason.POLICY_INVALID)
    model_manifest = {
        field: _plain(getattr(pack.manifest, field))
        for field in pack.manifest.__dataclass_fields__
    }
    if model_manifest != manifest:
        _reject("/domain_policy_snapshot", EmphasisEventsRejectionReason.POLICY_INVALID)
    resolved = data["resolved_policy"]
    if type(resolved) is not dict or set(resolved) != {
        "policy_bundles", "extensions", "enabled_extensions", "overrides"
    }:
        _reject("/domain_policy_snapshot", EmphasisEventsRejectionReason.POLICY_INVALID)
    extensions = resolved["extensions"]
    if extensions != manifest.get("extensions") or type(extensions) is not dict:
        _reject("/domain_policy_snapshot", EmphasisEventsRejectionReason.POLICY_INVALID)
    grammars = extensions.get("visual_grammars")
    if type(grammars) is not list or not grammars:
        _reject("/domain_policy_snapshot", EmphasisEventsRejectionReason.POLICY_INVALID)
    allowed: set[tuple[str, str]] = set()
    for item in grammars:
        if type(item) is not dict or set(item) != {"name", "version", "description"}:
            _reject("/domain_policy_snapshot", EmphasisEventsRejectionReason.POLICY_INVALID)
        if not _safe(item["name"], name=True) or not _safe(item["version"], semver=True):
            _reject("/domain_policy_snapshot", EmphasisEventsRejectionReason.POLICY_INVALID)
        key = (item["name"], item["version"])
        if key in allowed:
            _reject("/domain_policy_snapshot", EmphasisEventsRejectionReason.POLICY_INVALID)
        allowed.add(key)
    return _ResolvedEmphasisPolicy(
        snapshot.domain_id, snapshot.domain_pack_version, snapshot.snapshot_id,
        snapshot.canonical_hash, frozenset(allowed)
    )


def _type_ref_dict(value: EmphasisTypeRef) -> dict[str, str]:
    return {"domain_id": value.domain_id, "name": value.name, "version": value.version}


def _event_projection(value: EmphasisEvent) -> dict[str, Any]:
    data = _event_dict(value)
    data.pop("emphasis_event_id")
    data.pop("emphasis_event_hash")
    return data


def _event_dict(value: EmphasisEvent) -> dict[str, Any]:
    return {
        "schema_version": value.schema_version,
        "hash_scope_version": value.hash_scope_version,
        "emphasis_event_id": value.emphasis_event_id,
        "emphasis_event_hash": value.emphasis_event_hash,
        "narration_revision_id": value.narration_revision_id,
        "alignment_result_id": value.alignment_result_id,
        "caption_groups_id": value.caption_groups_id,
        "policy_snapshot_id": value.policy_snapshot_id,
        "policy_snapshot_hash": value.policy_snapshot_hash,
        "mapping_policy_version": value.mapping_policy_version,
        "ordinal": value.ordinal,
        "caption_group_id": value.caption_group_id,
        "start_word_ordinal": value.start_word_ordinal,
        "end_exclusive_word_ordinal": value.end_exclusive_word_ordinal,
        "start_word_id": value.start_word_id,
        "end_word_id": value.end_word_id,
        "word_ids": list(value.word_ids),
        "emphasis_type_ref": _type_ref_dict(value.emphasis_type_ref),
        "intensity": value.intensity.value,
        "start_ms": value.start_ms,
        "end_ms": value.end_ms,
        "confidence_millionths": value.confidence_millionths,
    }


def _artifact_dict(value: EmphasisEventsArtifact) -> dict[str, Any]:
    return {
        "schema_version": value.schema_version,
        "hash_scope_version": value.hash_scope_version,
        "emphasis_events_id": value.emphasis_events_id,
        "emphasis_events_hash": value.emphasis_events_hash,
        "project_id": value.project_id,
        "document_id": value.document_id,
        "narration_revision_id": value.narration_revision_id,
        "narration_revision_hash": value.narration_revision_hash,
        "alignment_result_id": value.alignment_result_id,
        "alignment_result_hash": value.alignment_result_hash,
        "caption_groups_id": value.caption_groups_id,
        "caption_groups_hash": value.caption_groups_hash,
        "mapping_policy_version": value.mapping_policy_version,
        "domain_id": value.domain_id,
        "domain_pack_version": value.domain_pack_version,
        "policy_snapshot_id": value.policy_snapshot_id,
        "policy_snapshot_hash": value.policy_snapshot_hash,
        "confidence_availability": value.confidence_availability.value,
        "emphasis_events": [_event_dict(event) for event in value.emphasis_events],
    }


def _artifact_projection(value: EmphasisEventsArtifact) -> dict[str, Any]:
    data = _artifact_dict(value)
    data.pop("emphasis_events_id")
    data.pop("emphasis_events_hash")
    return data


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _preflight(
    document: CanonicalNarrationDocument,
    revision: NarrationRevision,
    result: AlignmentResult,
    groups: CaptionGroupsArtifact,
) -> None:
    if type(document) is not CanonicalNarrationDocument:
        raise TypeError("narration_document must be exact CanonicalNarrationDocument")
    if type(revision) is not NarrationRevision:
        raise TypeError("narration_revision must be exact NarrationRevision")
    if type(result) is not AlignmentResult:
        raise TypeError("alignment_result must be exact AlignmentResult")
    if type(groups) is not CaptionGroupsArtifact:
        raise TypeError("caption_groups must be exact CaptionGroupsArtifact")
    try:
        expected = compile_caption_groups(
            narration_document=document, narration_revision=revision, alignment_result=result
        )
        expected_bytes = serialize_caption_groups(expected)
    except TypeError:
        raise
    except CaptionGroupsContractError as error:
        pointer = error.pointer if error.pointer in {
            "/narration_document", "/narration_revision", "/alignment_result"
        } else "/alignment_result"
        code = "REPLAY_HASH_MISMATCH" if pointer == "/alignment_result" else "ALIGNMENT_REQUEST_IDENTITY_MISMATCH"
        _reject(pointer, EmphasisEventsRejectionReason.DEPENDENCY_CONTENT_DRIFT, code)
    try:
        actual_bytes = serialize_caption_groups(groups)
    except TypeError:
        raise
    except Exception:
        _reject("/caption_groups", EmphasisEventsRejectionReason.DEPENDENCY_CONTENT_DRIFT, "REPLAY_HASH_MISMATCH")
    if expected_bytes != actual_bytes:
        _reject("/caption_groups", EmphasisEventsRejectionReason.DEPENDENCY_BINDING_INVALID, "ALIGNMENT_REQUEST_IDENTITY_MISMATCH")


def _compile(
    *,
    narration_document: CanonicalNarrationDocument,
    narration_revision: NarrationRevision,
    alignment_result: AlignmentResult,
    caption_groups: CaptionGroupsArtifact,
    domain_policy_snapshot: DomainPolicySnapshot,
    domain_pack_registry: DomainPackRegistry,
    intents: tuple[EmphasisIntent, ...],
) -> EmphasisEventsArtifact:
    _preflight(narration_document, narration_revision, alignment_result, caption_groups)
    if type(domain_policy_snapshot) is not DomainPolicySnapshot:
        raise TypeError("domain_policy_snapshot must be exact DomainPolicySnapshot")
    if type(domain_pack_registry) is not DomainPackRegistry:
        raise TypeError("domain_pack_registry must be exact DomainPackRegistry")
    policy = _resolve_policy(domain_policy_snapshot, domain_pack_registry)
    if type(intents) is not tuple:
        raise TypeError("intents must be exact tuple")
    if len(intents) > _MAX_EVENTS:
        _reject("/intents", EmphasisEventsRejectionReason.STRUCTURE_INVALID)
    timings = {item.word_id: item for item in alignment_result.word_timings}
    events: list[EmphasisEvent] = []
    previous_key: tuple[Any, ...] | None = None
    previous_end = -1
    for index, intent in enumerate(intents):
        pointer = f"/intents/{index}"
        if type(intent) is not EmphasisIntent or type(intent.word_range) is not WordRangeReference or type(intent.emphasis_type_ref) is not EmphasisTypeRef:
            _reject(pointer, EmphasisEventsRejectionReason.STRUCTURE_INVALID)
        ref = intent.word_range
        if ref.narration_revision_id != narration_revision.revision_id:
            _reject(pointer, EmphasisEventsRejectionReason.WORD_RANGE_INVALID, "WORD_RANGE_REVISION_MISMATCH")
        if type(ref.start_ordinal) is not int or type(ref.end_exclusive_ordinal) is not int:
            _reject(pointer, EmphasisEventsRejectionReason.STRUCTURE_INVALID)
        if ref.start_ordinal > ref.end_exclusive_ordinal:
            _reject(pointer, EmphasisEventsRejectionReason.WORD_RANGE_INVALID, "WORD_RANGE_REVERSED")
        try:
            words = resolve_word_range(narration_revision, ref, consumer=WordRangeConsumer.EMPHASIS)
        except Exception:
            _reject(pointer, EmphasisEventsRejectionReason.WORD_RANGE_INVALID, "WORD_RANGE_OUT_OF_BOUNDS")
        if len({word.sentence_id for word in words}) != 1:
            _reject(pointer, EmphasisEventsRejectionReason.WORD_RANGE_INVALID, "CANONICAL_COVERAGE_BLOCKER")
        type_ref = intent.emphasis_type_ref
        if not _safe(type_ref.domain_id) or not _safe(type_ref.name, name=True) or not _safe(type_ref.version, semver=True):
            _reject(pointer, EmphasisEventsRejectionReason.STRUCTURE_INVALID)
        if type_ref.domain_id != policy.domain_id or (type_ref.name, type_ref.version) not in policy.allowed:
            _reject(pointer, EmphasisEventsRejectionReason.POLICY_INVALID)
        if type(intent.intensity) is not EmphasisIntensity:
            _reject(pointer, EmphasisEventsRejectionReason.UNSUPPORTED_VALUE, "UNSUPPORTED_CONTRACT_ENUM")
        key = (ref.start_ordinal, ref.end_exclusive_ordinal, type_ref.domain_id, type_ref.name, type_ref.version, intent.intensity.value)
        if previous_key is not None and key < previous_key:
            _reject(pointer, EmphasisEventsRejectionReason.ORDERING_INVALID, "CANONICAL_WORD_ORDER_INVALID")
        if ref.start_ordinal < previous_end:
            _reject(pointer, EmphasisEventsRejectionReason.OVERLAP_INVALID, "CANONICAL_COVERAGE_BLOCKER")
        previous_key, previous_end = key, ref.end_exclusive_ordinal
        matches = [group for group in caption_groups.caption_groups if group.start_word_ordinal <= ref.start_ordinal and ref.end_exclusive_ordinal <= group.end_exclusive_word_ordinal]
        if len(matches) != 1:
            _reject(pointer, EmphasisEventsRejectionReason.CAPTION_GROUP_BINDING_INVALID, "CANONICAL_COVERAGE_BLOCKER")
        group = matches[0]
        selected = [timings[word.word_id] for word in words]
        confidence = None
        if alignment_result.confidence_availability is ConfidenceAvailability.AVAILABLE:
            if any(item.confidence_millionths is None for item in selected):
                _reject(pointer, EmphasisEventsRejectionReason.CONFIDENCE_INVALID, "CONFIDENCE_REQUIRED_UNAVAILABLE")
            confidence = min(item.confidence_millionths for item in selected if item.confidence_millionths is not None)
        base = EmphasisEvent(
            EMPHASIS_EVENT_V1, EMPHASIS_EVENT_HASH_V1, "", "",
            narration_revision.revision_id, alignment_result.alignment_result_id,
            caption_groups.caption_groups_id, policy.snapshot_id, policy.snapshot_hash,
            EMPHASIS_MAPPING_POLICY_V1, index, group.caption_group_id,
            ref.start_ordinal, ref.end_exclusive_ordinal, words[0].word_id,
            words[-1].word_id, tuple(word.word_id for word in words),
            EmphasisTypeRef(type_ref.domain_id, type_ref.name, type_ref.version),
            intent.intensity, selected[0].start_ms, selected[-1].end_ms, confidence,
        )
        event_hash = _digest(encode_canonical_json_bytes(_event_projection(base)))
        events.append(EmphasisEvent(*(
            base.schema_version, base.hash_scope_version, "emph_" + event_hash[:32], event_hash,
            *tuple(getattr(base, field) for field in list(base.__dataclass_fields__)[4:])
        )))
    base_artifact = EmphasisEventsArtifact(
        EMPHASIS_EVENTS_V1, EMPHASIS_EVENTS_HASH_V1, "", "",
        narration_document.project_id, narration_document.document_id,
        narration_revision.revision_id, narration_revision.revision_hash,
        alignment_result.alignment_result_id, alignment_result.alignment_result_hash,
        caption_groups.caption_groups_id, caption_groups.caption_groups_hash,
        EMPHASIS_MAPPING_POLICY_V1, policy.domain_id, policy.domain_pack_version,
        policy.snapshot_id, policy.snapshot_hash, alignment_result.confidence_availability,
        tuple(events),
    )
    artifact_hash = _digest(encode_canonical_json_bytes(_artifact_projection(base_artifact)))
    return EmphasisEventsArtifact(
        base_artifact.schema_version, base_artifact.hash_scope_version,
        "emps_" + artifact_hash[:32], artifact_hash,
        *tuple(getattr(base_artifact, field) for field in list(base_artifact.__dataclass_fields__)[4:])
    )


def _register(artifact: EmphasisEventsArtifact, envelope: bytes) -> None:
    key = id(artifact)
    old = _MATERIALIZED.get(key)
    if old is not None and old[0]() is not None:
        raise RuntimeError("emphasis artifact registry collision")
    def forget(reference: weakref.ReferenceType[EmphasisEventsArtifact]) -> None:
        current = _MATERIALIZED.get(key)
        if current is not None and current[0] is reference:
            _MATERIALIZED.pop(key, None)
    reference = weakref.ref(artifact, forget)
    entry = (reference, envelope, _identity_signature(artifact))
    try:
        _MATERIALIZED[key] = entry
        if _MATERIALIZED.get(key) is not entry:
            raise RuntimeError("emphasis artifact registration failed")
    except Exception:
        if _MATERIALIZED.get(key) is entry:
            _MATERIALIZED.pop(key, None)
        raise


def compile_emphasis_events(
    *,
    narration_document: CanonicalNarrationDocument,
    narration_revision: NarrationRevision,
    alignment_result: AlignmentResult,
    caption_groups: CaptionGroupsArtifact,
    domain_policy_snapshot: DomainPolicySnapshot,
    domain_pack_registry: DomainPackRegistry,
    intents: tuple[EmphasisIntent, ...],
) -> EmphasisEventsArtifact:
    artifact = _compile(
        narration_document=narration_document,
        narration_revision=narration_revision,
        alignment_result=alignment_result,
        caption_groups=caption_groups,
        domain_policy_snapshot=domain_policy_snapshot,
        domain_pack_registry=domain_pack_registry,
        intents=intents,
    )
    envelope = encode_canonical_json_bytes(_artifact_dict(artifact))
    _register(artifact, envelope)
    return artifact


class _Pairs(list):
    pass


def _parse_source(source: bytes) -> Any:
    if type(source) is not bytes:
        raise TypeError("source must be exact bytes")
    try:
        if source.startswith(b"\xef\xbb\xbf"):
            raise ValueError
        value = json.loads(
            source.decode("utf-8"), object_pairs_hook=_Pairs,
            parse_float=lambda _: (_ for _ in ()).throw(ValueError()),
            parse_int=lambda text: int(text) if text == str(int(text)) else (_ for _ in ()).throw(ValueError()),
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
        )
    except Exception:
        _reject("/", EmphasisEventsRejectionReason.NON_CANONICAL_SERIALIZATION)
    def convert(item: Any) -> Any:
        if type(item) is _Pairs:
            keys = [key for key, _ in item]
            if len(keys) != len(set(keys)):
                _reject("/", EmphasisEventsRejectionReason.NON_CANONICAL_SERIALIZATION)
            return {key: convert(value) for key, value in item}
        if type(item) is list:
            return [convert(value) for value in item]
        return item
    return convert(value)


def load_emphasis_events(
    source: bytes,
    *,
    narration_document: CanonicalNarrationDocument,
    narration_revision: NarrationRevision,
    alignment_result: AlignmentResult,
    caption_groups: CaptionGroupsArtifact,
    domain_policy_snapshot: DomainPolicySnapshot,
    domain_pack_registry: DomainPackRegistry,
    intents: tuple[EmphasisIntent, ...],
) -> EmphasisEventsArtifact:
    expected = _compile(
        narration_document=narration_document,
        narration_revision=narration_revision,
        alignment_result=alignment_result,
        caption_groups=caption_groups,
        domain_policy_snapshot=domain_policy_snapshot,
        domain_pack_registry=domain_pack_registry,
        intents=intents,
    )
    value = _parse_source(source)
    if type(value) is not dict:
        _reject("/", EmphasisEventsRejectionReason.STRUCTURE_INVALID)
    expected_value = _artifact_dict(expected)
    if set(value) != set(expected_value):
        _reject("/", EmphasisEventsRejectionReason.STRUCTURE_INVALID)
    root_string_fields = set(expected_value) - {"emphasis_events"}
    for field in root_string_fields:
        if type(value[field]) is not str:
            _reject("/", EmphasisEventsRejectionReason.STRUCTURE_INVALID)
    if value["schema_version"] != EMPHASIS_EVENTS_V1 or value["hash_scope_version"] != EMPHASIS_EVENTS_HASH_V1 or value["mapping_policy_version"] != EMPHASIS_MAPPING_POLICY_V1 or value["confidence_availability"] not in {item.value for item in ConfidenceAvailability}:
        _reject("/", EmphasisEventsRejectionReason.UNSUPPORTED_VALUE, "UNSUPPORTED_CONTRACT_ENUM")
    events = value.get("emphasis_events")
    if type(events) is not list:
        _reject("/emphasis_events", EmphasisEventsRejectionReason.STRUCTURE_INVALID)
    if len(events) != len(expected.emphasis_events):
        _reject("/emphasis_events", EmphasisEventsRejectionReason.INTENT_INVALID, "CANONICAL_COVERAGE_BLOCKER")
    for index, (actual, wanted) in enumerate(zip(events, expected_value["emphasis_events"])):
        pointer = f"/emphasis_events/{index}"
        if type(actual) is not dict or set(actual) != set(wanted):
            _reject(pointer, EmphasisEventsRejectionReason.STRUCTURE_INVALID)
        string_fields = set(wanted) - {
            "ordinal", "start_word_ordinal", "end_exclusive_word_ordinal",
            "word_ids", "emphasis_type_ref", "start_ms", "end_ms",
            "confidence_millionths",
        }
        if any(type(actual[field]) is not str for field in string_fields):
            _reject(pointer, EmphasisEventsRejectionReason.STRUCTURE_INVALID)
        if any(type(actual[field]) is not int for field in ("ordinal", "start_word_ordinal", "end_exclusive_word_ordinal", "start_ms", "end_ms")):
            _reject(pointer, EmphasisEventsRejectionReason.STRUCTURE_INVALID)
        if actual["confidence_millionths"] is not None and type(actual["confidence_millionths"]) is not int:
            _reject(pointer, EmphasisEventsRejectionReason.STRUCTURE_INVALID)
        if type(actual["word_ids"]) is not list or not all(type(item) is str for item in actual["word_ids"]):
            _reject(pointer, EmphasisEventsRejectionReason.STRUCTURE_INVALID)
        type_value = actual["emphasis_type_ref"]
        if type(type_value) is not dict or set(type_value) != {"domain_id", "name", "version"} or not all(type(item) is str for item in type_value.values()):
            _reject(pointer, EmphasisEventsRejectionReason.STRUCTURE_INVALID)
        if actual["schema_version"] != EMPHASIS_EVENT_V1 or actual["hash_scope_version"] != EMPHASIS_EVENT_HASH_V1 or actual["mapping_policy_version"] != EMPHASIS_MAPPING_POLICY_V1 or actual["intensity"] not in {item.value for item in EmphasisIntensity}:
            _reject(pointer, EmphasisEventsRejectionReason.UNSUPPORTED_VALUE, "UNSUPPORTED_CONTRACT_ENUM")
        for field in wanted:
            if actual[field] == wanted[field]:
                continue
            if field in {"emphasis_event_hash", "emphasis_event_id"}:
                _reject(pointer, EmphasisEventsRejectionReason.IDENTITY_MISMATCH)
            if field in {"start_ms", "end_ms"}:
                _reject(pointer, EmphasisEventsRejectionReason.TIMING_INVALID, "TIMESTAMP_NON_MONOTONIC")
            if field == "confidence_millionths":
                code = "CONFIDENCE_REQUIRED_UNAVAILABLE" if actual[field] is None else "ADAPTER_PRECISION_OVERSTATED"
                _reject(pointer, EmphasisEventsRejectionReason.CONFIDENCE_INVALID, code)
            if field in {"caption_group_id", "word_ids", "start_word_id", "end_word_id"}:
                _reject(pointer, EmphasisEventsRejectionReason.CAPTION_GROUP_BINDING_INVALID, "CANONICAL_COVERAGE_BLOCKER")
            if field in {"ordinal"}:
                _reject(pointer, EmphasisEventsRejectionReason.ORDERING_INVALID, "CANONICAL_WORD_ORDER_INVALID")
            if field in {"start_word_ordinal", "end_exclusive_word_ordinal", "emphasis_type_ref", "intensity"}:
                _reject(pointer, EmphasisEventsRejectionReason.INTENT_INVALID)
            _reject(pointer, EmphasisEventsRejectionReason.DEPENDENCY_BINDING_INVALID, "ALIGNMENT_REQUEST_IDENTITY_MISMATCH")
    for field in expected_value:
        if field == "emphasis_events" or value[field] == expected_value[field]:
            continue
        if field in {"emphasis_events_hash", "emphasis_events_id"}:
            _reject("/", EmphasisEventsRejectionReason.IDENTITY_MISMATCH)
        if field == "confidence_availability":
            _reject("/", EmphasisEventsRejectionReason.CONFIDENCE_INVALID, "ADAPTER_PRECISION_OVERSTATED")
        _reject("/", EmphasisEventsRejectionReason.DEPENDENCY_BINDING_INVALID, "ALIGNMENT_REQUEST_IDENTITY_MISMATCH")
    canonical = encode_canonical_json_bytes(value)
    if canonical != source:
        _reject("/", EmphasisEventsRejectionReason.NON_CANONICAL_SERIALIZATION)
    envelope = encode_canonical_json_bytes(expected_value)
    _register(expected, envelope)
    return expected


def serialize_emphasis_events(artifact: EmphasisEventsArtifact) -> bytes:
    if type(artifact) is not EmphasisEventsArtifact:
        raise TypeError("artifact must be exact EmphasisEventsArtifact")
    entry = _MATERIALIZED.get(id(artifact))
    if entry is None or entry[0]() is not artifact:
        _reject("/", EmphasisEventsRejectionReason.NOT_MATERIALIZED)
    if _identity_signature(artifact) != entry[2]:
        _reject("/", EmphasisEventsRejectionReason.CONTENT_DRIFT)
    if type(artifact.emphasis_events) is not tuple:
        _reject("/", EmphasisEventsRejectionReason.CONTENT_DRIFT)
    for event in artifact.emphasis_events:
        if type(event) is not EmphasisEvent or type(event.word_ids) is not tuple or type(event.emphasis_type_ref) is not EmphasisTypeRef or type(event.intensity) is not EmphasisIntensity:
            _reject("/", EmphasisEventsRejectionReason.CONTENT_DRIFT)
    try:
        current = encode_canonical_json_bytes(_artifact_dict(artifact))
        projection_hash = _digest(encode_canonical_json_bytes(_artifact_projection(artifact)))
    except Exception:
        _reject("/", EmphasisEventsRejectionReason.CONTENT_DRIFT)
    if projection_hash != artifact.emphasis_events_hash or artifact.emphasis_events_id != "emps_" + projection_hash[:32] or current != entry[1]:
        _reject("/", EmphasisEventsRejectionReason.CONTENT_DRIFT)
    for event in artifact.emphasis_events:
        event_hash = _digest(encode_canonical_json_bytes(_event_projection(event)))
        if event_hash != event.emphasis_event_hash or event.emphasis_event_id != "emph_" + event_hash[:32]:
            _reject("/", EmphasisEventsRejectionReason.CONTENT_DRIFT)
    return entry[1]
