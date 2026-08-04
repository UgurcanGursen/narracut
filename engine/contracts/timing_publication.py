"""Fail-closed, no-replacement publication of the three Phase 2 timing files."""

from __future__ import annotations

import hashlib
import os
import stat
import weakref
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from ._canonical_json import encode_canonical_json_bytes
from .alignment_result import AlignmentResult, serialize_alignment_result
from .caption_groups import CaptionGroupsArtifact, serialize_caption_groups
from .emphasis_events import EmphasisEventsArtifact, serialize_emphasis_events
from .word_to_frame import WordToFrameArtifact, serialize_word_to_frame


TIMING_PUBLICATION_V1 = "TIMING-PUBLICATION-V1"
TIMING_PUBLICATION_HASH_V1 = "TIMING-PUBLICATION-HASH-V1"

_NATIVE_PATH_TYPE = type(Path())
_FILE_PATHS = (
    "timing/word_timeline.json",
    "timing/caption_groups.json",
    "timing/emphasis_events.json",
)
_RECEIPT_FIELDS = (
    "schema_version", "hash_scope_version", "timing_publication_id",
    "timing_publication_hash", "project_id", "document_id",
    "narration_revision_id", "narration_revision_hash", "alignment_result_id",
    "alignment_result_hash", "caption_groups_id", "caption_groups_hash",
    "emphasis_events_id", "emphasis_events_hash", "word_to_frame_id",
    "word_to_frame_hash", "files",
)
_HEX = frozenset("0123456789abcdef")
_ALLOWED_POINTERS = frozenset({
    "/", "/alignment_result", "/caption_groups", "/emphasis_events",
    "/word_to_frame", "/project_root", "/timing",
    "/timing/word_timeline.json", "/timing/caption_groups.json",
    "/timing/emphasis_events.json",
})


class TimingPublicationRejectionReason(str, Enum):
    STRUCTURE_INVALID = "STRUCTURE_INVALID"
    DEPENDENCY_CONTENT_DRIFT = "DEPENDENCY_CONTENT_DRIFT"
    DEPENDENCY_BINDING_INVALID = "DEPENDENCY_BINDING_INVALID"
    PATH_INVALID = "PATH_INVALID"
    TARGET_EXISTS = "TARGET_EXISTS"
    WRITE_FAILED = "WRITE_FAILED"
    VERIFY_FAILED = "VERIFY_FAILED"
    PROMOTION_FAILED = "PROMOTION_FAILED"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    NOT_MATERIALIZED = "NOT_MATERIALIZED"


class TimingPublicationContractError(ValueError):
    def __init__(
        self,
        pointer: str,
        reason: TimingPublicationRejectionReason,
        issue_code: str | None = None,
    ) -> None:
        if (
            type(pointer) is not str
            or pointer not in _ALLOWED_POINTERS
            or type(reason) is not TimingPublicationRejectionReason
            or issue_code is not None
        ):
            raise TypeError("invalid timing publication error construction")
        super().__init__(f"Timing publication rejected: {reason.value}")
        self.pointer = pointer
        self.reason = reason
        self.issue_code = None


@dataclass(frozen=True)
class PublishedTimingFile:
    relative_path: str
    sha256: str
    byte_length: int


@dataclass(frozen=True)
class TimingPublicationReceipt:
    schema_version: str
    hash_scope_version: str
    timing_publication_id: str
    timing_publication_hash: str
    project_id: str
    document_id: str
    narration_revision_id: str
    narration_revision_hash: str
    alignment_result_id: str
    alignment_result_hash: str
    caption_groups_id: str
    caption_groups_hash: str
    emphasis_events_id: str
    emphasis_events_hash: str
    word_to_frame_id: str
    word_to_frame_hash: str
    files: tuple[PublishedTimingFile, ...]


_MATERIALIZED: dict[int, tuple[weakref.ReferenceType[TimingPublicationReceipt], bytes]] = {}


def _reject(pointer: str, reason: TimingPublicationRejectionReason) -> None:
    raise TimingPublicationContractError(pointer, reason)


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _file_dict(value: PublishedTimingFile) -> dict[str, Any]:
    return {
        "relative_path": value.relative_path,
        "sha256": value.sha256,
        "byte_length": value.byte_length,
    }


def _receipt_dict(value: TimingPublicationReceipt) -> dict[str, Any]:
    result = {field: getattr(value, field) for field in _RECEIPT_FIELDS if field != "files"}
    result["files"] = [_file_dict(item) for item in value.files]
    return result


def _receipt_projection(value: TimingPublicationReceipt) -> dict[str, Any]:
    result = _receipt_dict(value)
    result.pop("timing_publication_id")
    result.pop("timing_publication_hash")
    return result


def _receipt_has_exact_shape(value: Any) -> bool:
    if type(value) is not TimingPublicationReceipt:
        return False
    for field in _RECEIPT_FIELDS[:-1]:
        if type(getattr(value, field)) is not str or not getattr(value, field):
            return False
    if type(value.files) is not tuple or len(value.files) != 3:
        return False
    for path, item in zip(_FILE_PATHS, value.files):
        if (
            type(item) is not PublishedTimingFile
            or type(item.relative_path) is not str
            or item.relative_path != path
            or type(item.sha256) is not str
            or len(item.sha256) != 64
            or any(character not in _HEX for character in item.sha256)
            or type(item.byte_length) is not int
            or item.byte_length < 0
        ):
            return False
    return True


def _register(value: TimingPublicationReceipt, envelope: bytes) -> None:
    key = id(value)
    old = _MATERIALIZED.get(key)
    if old is not None and old[0]() is not None:
        raise RuntimeError("timing publication provenance collision")

    def forget(reference: weakref.ReferenceType[TimingPublicationReceipt]) -> None:
        entry = _MATERIALIZED.get(key)
        if entry is not None and entry[0] is reference:
            _MATERIALIZED.pop(key, None)

    reference = weakref.ref(value, forget)
    entry = (reference, bytes(envelope))
    _MATERIALIZED[key] = entry
    if _MATERIALIZED.get(key) is not entry or reference() is not value:
        _MATERIALIZED.pop(key, None)
        raise RuntimeError("timing publication provenance registration failed")


def _serialized_dependency(value: Any, exact_type: type, serializer: Any, pointer: str) -> bytes:
    if type(value) is not exact_type:
        _reject(pointer, TimingPublicationRejectionReason.DEPENDENCY_CONTENT_DRIFT)
    try:
        result = serializer(value)
        if type(result) is not bytes:
            raise ValueError
        return bytes(result)
    except TimingPublicationContractError:
        raise
    except Exception:
        _reject(pointer, TimingPublicationRejectionReason.DEPENDENCY_CONTENT_DRIFT)


def _binding(left: Any, right: Any, fields: tuple[str, ...], pointer: str) -> None:
    try:
        for field in fields:
            if getattr(left, field) != getattr(right, field):
                _reject(pointer, TimingPublicationRejectionReason.DEPENDENCY_BINDING_INVALID)
    except TimingPublicationContractError:
        raise
    except Exception:
        _reject(pointer, TimingPublicationRejectionReason.DEPENDENCY_BINDING_INVALID)


def _is_reparse(path: Path) -> bool:
    try:
        mode = path.lstat().st_mode
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except OSError:
        raise
    return stat.S_ISLNK(mode) or bool(
        attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


def _path_state(path: Path) -> tuple[bool, bool]:
    """Return (exists, is_reparse) without following a possibly hostile path."""
    try:
        path.lstat()
    except FileNotFoundError:
        return False, False
    except OSError:
        _reject("/project_root", TimingPublicationRejectionReason.PATH_INVALID)
    try:
        return True, _is_reparse(path)
    except OSError:
        _reject("/project_root", TimingPublicationRejectionReason.PATH_INVALID)


def _validate_root(project_root: Path) -> None:
    if type(project_root) is not _NATIVE_PATH_TYPE:
        raise TypeError("project_root must be an exact absolute pathlib.Path")
    if not project_root.is_absolute() or any(part in {".", ".."} for part in project_root.parts):
        _reject("/project_root", TimingPublicationRejectionReason.PATH_INVALID)
    exists, reparse = _path_state(project_root)
    if not exists or reparse:
        _reject("/project_root", TimingPublicationRejectionReason.PATH_INVALID)
    try:
        if not project_root.is_dir():
            _reject("/project_root", TimingPublicationRejectionReason.PATH_INVALID)
    except TimingPublicationContractError:
        raise
    except OSError:
        _reject("/project_root", TimingPublicationRejectionReason.PATH_INVALID)
    parent_exists, parent_reparse = _path_state(project_root.parent)
    if not parent_exists or parent_reparse:
        _reject("/project_root", TimingPublicationRejectionReason.PATH_INVALID)


def _check_target_and_staging(target: Path, staging: Path) -> None:
    for path in (target, staging):
        exists, reparse = _path_state(path)
        if reparse:
            _reject("/timing", TimingPublicationRejectionReason.PATH_INVALID)
        if exists:
            _reject("/timing", TimingPublicationRejectionReason.TARGET_EXISTS)


def _check_before_promotion(target: Path, staging: Path) -> None:
    target_exists, target_reparse = _path_state(target)
    if target_reparse:
        _reject("/timing", TimingPublicationRejectionReason.PATH_INVALID)
    if target_exists:
        _reject("/timing", TimingPublicationRejectionReason.TARGET_EXISTS)
    staging_exists, staging_reparse = _path_state(staging)
    if not staging_exists or staging_reparse:
        _reject("/timing", TimingPublicationRejectionReason.PROMOTION_FAILED)
    try:
        if not stat.S_ISDIR(staging.lstat().st_mode):
            _reject("/timing", TimingPublicationRejectionReason.PROMOTION_FAILED)
    except TimingPublicationContractError:
        raise
    except Exception:
        _reject("/timing", TimingPublicationRejectionReason.PROMOTION_FAILED)


def _safe_cleanup(staging: Path) -> None:
    """Remove only our three flat regular files; never follow a hostile replacement."""
    try:
        exists, reparse = _path_state(staging)
        if not exists or reparse:
            return
        for relative_path in _FILE_PATHS:
            candidate = staging / Path(relative_path).name
            try:
                file_exists, file_reparse = _path_state(candidate)
                if not file_exists or file_reparse:
                    continue
                mode = candidate.lstat().st_mode
                if stat.S_ISREG(mode):
                    candidate.unlink()
            except Exception:
                continue
        try:
            if not _is_reparse(staging):
                staging.rmdir()
        except Exception:
            pass
    except Exception:
        pass


def _write_checked(staging: Path, relative_path: str, payload: bytes) -> None:
    pointer = "/" + relative_path
    destination = staging / Path(relative_path).name
    descriptor: int | None = None
    try:
        descriptor = os.open(str(destination), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if type(written) is not int or written <= 0:
                raise OSError("short write")
            offset += written
        os.fsync(descriptor)
    except Exception:
        _reject(pointer, TimingPublicationRejectionReason.WRITE_FAILED)
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
    try:
        if _is_reparse(destination) or not stat.S_ISREG(destination.lstat().st_mode):
            raise OSError
        with destination.open("rb") as handle:
            actual = handle.read()
        if len(actual) != len(payload) or _digest(actual) != _digest(payload) or actual != payload:
            raise OSError
    except Exception:
        _reject(pointer, TimingPublicationRejectionReason.VERIFY_FAILED)


def _post_promotion_verify(target: Path, payloads: tuple[bytes, bytes, bytes]) -> None:
    try:
        exists, reparse = _path_state(target)
        parent_exists, parent_reparse = _path_state(target.parent)
        if not exists or reparse or not parent_exists or parent_reparse:
            raise OSError
        for relative_path, payload in zip(_FILE_PATHS, payloads):
            candidate = target / Path(relative_path).name
            if _is_reparse(candidate) or not stat.S_ISREG(candidate.lstat().st_mode):
                raise OSError
            with candidate.open("rb") as handle:
                actual = handle.read()
            if actual != payload or len(actual) != len(payload) or _digest(actual) != _digest(payload):
                raise OSError
    except Exception:
        _reject("/timing", TimingPublicationRejectionReason.PROMOTION_FAILED)


def publish_timing_artifacts(
    *,
    alignment_result: AlignmentResult,
    caption_groups: CaptionGroupsArtifact,
    emphasis_events: EmphasisEventsArtifact,
    word_to_frame: WordToFrameArtifact,
    project_root: Path,
) -> TimingPublicationReceipt:
    """Atomically publish canonical Phase 2 timing payloads into a fresh root."""
    if type(project_root) is not _NATIVE_PATH_TYPE:
        raise TypeError("project_root must be an exact absolute pathlib.Path")
    # Lexical path validity is part of the call signature boundary and does not
    # inspect the filesystem or invoke a dependency serializer.
    if not project_root.is_absolute() or any(part in {".", ".."} for part in project_root.parts):
        _reject("/project_root", TimingPublicationRejectionReason.PATH_INVALID)

    word_timeline = _serialized_dependency(
        alignment_result, AlignmentResult, serialize_alignment_result, "/alignment_result"
    )
    caption_payload = _serialized_dependency(
        caption_groups, CaptionGroupsArtifact, serialize_caption_groups, "/caption_groups"
    )
    emphasis_payload = _serialized_dependency(
        emphasis_events, EmphasisEventsArtifact, serialize_emphasis_events, "/emphasis_events"
    )
    _serialized_dependency(word_to_frame, WordToFrameArtifact, serialize_word_to_frame, "/word_to_frame")

    base_fields = (
        "project_id", "document_id", "narration_revision_id", "narration_revision_hash",
        "alignment_result_id", "alignment_result_hash",
    )
    _binding(alignment_result, caption_groups, base_fields, "/caption_groups")
    _binding(alignment_result, emphasis_events, base_fields, "/emphasis_events")
    _binding(caption_groups, emphasis_events, ("caption_groups_id", "caption_groups_hash"), "/emphasis_events")
    _binding(alignment_result, word_to_frame, base_fields, "/word_to_frame")
    _binding(caption_groups, word_to_frame, ("caption_groups_id", "caption_groups_hash"), "/word_to_frame")
    _binding(emphasis_events, word_to_frame, ("emphasis_events_id", "emphasis_events_hash"), "/word_to_frame")

    payloads = (word_timeline, caption_payload, emphasis_payload)
    files = tuple(
        PublishedTimingFile(relative_path=relative_path, sha256=_digest(payload), byte_length=len(payload))
        for relative_path, payload in zip(_FILE_PATHS, payloads)
    )
    base = dict(
        schema_version=TIMING_PUBLICATION_V1,
        hash_scope_version=TIMING_PUBLICATION_HASH_V1,
        timing_publication_id="pending",
        timing_publication_hash="pending",
        project_id=alignment_result.project_id,
        document_id=alignment_result.document_id,
        narration_revision_id=alignment_result.narration_revision_id,
        narration_revision_hash=alignment_result.narration_revision_hash,
        alignment_result_id=alignment_result.alignment_result_id,
        alignment_result_hash=alignment_result.alignment_result_hash,
        caption_groups_id=caption_groups.caption_groups_id,
        caption_groups_hash=caption_groups.caption_groups_hash,
        emphasis_events_id=emphasis_events.emphasis_events_id,
        emphasis_events_hash=emphasis_events.emphasis_events_hash,
        word_to_frame_id=word_to_frame.word_to_frame_id,
        word_to_frame_hash=word_to_frame.word_to_frame_hash,
        files=files,
    )
    projection = {
        key: ([_file_dict(item) for item in value] if key == "files" else value)
        for key, value in base.items()
        if key not in {"timing_publication_id", "timing_publication_hash"}
    }
    receipt_hash = _digest(encode_canonical_json_bytes(projection))
    receipt = TimingPublicationReceipt(
        **(base | {
            "timing_publication_id": "tpub_" + receipt_hash[:32],
            "timing_publication_hash": receipt_hash,
        })
    )
    if not _receipt_has_exact_shape(receipt):
        raise RuntimeError("timing publication receipt construction failed")

    _validate_root(project_root)
    target = project_root / "timing"
    staging = project_root / (".timing-publication-" + receipt.timing_publication_id + ".staging")
    _check_target_and_staging(target, staging)
    try:
        staging.mkdir(mode=0o700)
    except Exception:
        _reject("/timing", TimingPublicationRejectionReason.WRITE_FAILED)
    try:
        if _is_reparse(staging) or not staging.is_dir():
            _reject("/timing", TimingPublicationRejectionReason.PATH_INVALID)
        for relative_path, payload in zip(_FILE_PATHS, payloads):
            _write_checked(staging, relative_path, payload)
        _validate_root(project_root)
        _check_before_promotion(target, staging)
        try:
            # On Windows, os.rename is a no-replace directory promotion.  We never
            # call an overwrite-capable replacement primitive.
            os.rename(str(staging), str(target))
        except Exception:
            _reject("/timing", TimingPublicationRejectionReason.PROMOTION_FAILED)
        _post_promotion_verify(target, payloads)
        envelope = encode_canonical_json_bytes(_receipt_dict(receipt))
        _register(receipt, envelope)
        return receipt
    except TimingPublicationContractError:
        _safe_cleanup(staging)
        raise
    except Exception:
        _safe_cleanup(staging)
        _reject("/timing", TimingPublicationRejectionReason.PROMOTION_FAILED)


def serialize_timing_publication_receipt(receipt: TimingPublicationReceipt) -> bytes:
    entry = _MATERIALIZED.get(id(receipt))
    if type(receipt) is not TimingPublicationReceipt or entry is None or entry[0]() is not receipt:
        _reject("/", TimingPublicationRejectionReason.NOT_MATERIALIZED)
    if not _receipt_has_exact_shape(receipt):
        _reject("/", TimingPublicationRejectionReason.STRUCTURE_INVALID)
    try:
        projection_hash = _digest(encode_canonical_json_bytes(_receipt_projection(receipt)))
        envelope = encode_canonical_json_bytes(_receipt_dict(receipt))
    except Exception:
        _reject("/", TimingPublicationRejectionReason.STRUCTURE_INVALID)
    if (
        receipt.schema_version != TIMING_PUBLICATION_V1
        or receipt.hash_scope_version != TIMING_PUBLICATION_HASH_V1
        or receipt.timing_publication_hash != projection_hash
        or receipt.timing_publication_id != "tpub_" + projection_hash[:32]
        or envelope != entry[1]
    ):
        _reject("/", TimingPublicationRejectionReason.IDENTITY_MISMATCH)
    return bytes(entry[1])
