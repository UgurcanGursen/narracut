"""Phase 8 local-REPLAY semantic asset catalog.

This module deliberately has no transport, provider SDK, browser, queue or
EDL dependency.  It turns exact caller-provided bytes plus trusted replay
evidence into immutable, hash-bound catalog records.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field, is_dataclass, replace
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

from engine.contracts._canonical_json import encode_canonical_json_bytes
from engine.contracts.domain import policy_snapshot_hash
from engine.contracts.models import DomainPolicySnapshot


ASSET_CATALOG_POLICY_V1 = "ASSET-CATALOG-POLICY-V1"
ASSET_CATALOG_SCHEMA_V1 = "ASSET-CATALOG-V1"
TRUSTED_REPLAY_MANIFEST_ID = "phase8_fixture_manifest"
TRUSTED_REPLAY_MANIFEST_HASH = "sha256:704855f25612d261eb74d5ddd781946b0dfc31829665e314e0cd246b45519329"
TRUSTED_REPLAY_MANIFEST_PATH = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "phase8_replay_evidence_manifest.json"
_HASH_PREFIX = "sha256:"


class AssetCatalogError(ValueError):
    """Closed, fail-closed error code for Phase 8 compilation."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _reject(code: str) -> None:
    raise AssetCatalogError(code)


def _hash(value: object) -> str:
    return _HASH_PREFIX + hashlib.sha256(encode_canonical_json_bytes(value)).hexdigest()


def _bytes_hash(value: bytes) -> str:
    return _HASH_PREFIX + hashlib.sha256(value).hexdigest()


def _token(value: object) -> bool:
    return type(value) is str and bool(value) and value == value.strip() and value == value.lower()


def _hash_value(value: object) -> bool:
    return type(value) is str and len(value) == 71 and value.startswith(_HASH_PREFIX) and all(ch in "0123456789abcdef" for ch in value[7:])


def _tokens(value: object) -> tuple[str, ...]:
    if type(value) not in (tuple, list) or any(not _token(item) for item in value) or len(set(value)) != len(value):
        _reject("ASSET_CATALOG_TOKEN_INVALID")
    return tuple(value)


def _json_value(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _json_value(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    return value


def _canonical_json_load(payload: bytes, code: str) -> object:
    def reject_duplicate(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                _reject(code)
            result[key] = value
        return result
    try:
        raw = json.loads(payload.decode("utf-8"), object_pairs_hook=reject_duplicate)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
        _reject(code)
    if encode_canonical_json_bytes(raw) != payload:
        _reject(code)
    return raw


class MediaType(str, Enum):
    IMAGE = "image"
    VIDEO = "video"
    DOCUMENT = "document"
    AUDIO = "audio"


class SourceAudioStatus(str, Enum):
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"
    REVIEW_REQUIRED = "review_required"
    NOT_APPLICABLE = "not_applicable"


class DuplicateKind(str, Enum):
    SAME_SOURCE = "same_source"
    EXACT_BYTES = "exact_bytes"
    PERCEPTUAL_MATCH = "perceptual_match"
    LOCAL_FEATURE_MATCH = "local_feature_match"
    SELECTED_RANGE_OVERLAP = "selected_range_overlap"
    DISTINCT = "distinct"


class ReuseStatus(str, Enum):
    EVALUATED = "evaluated"
    NOT_EVALUATED = "not_evaluated"


@dataclass(frozen=True)
class SourceDescriptorV1:
    provider_id: str
    source_uri: str
    license_mode: str
    allowed_uses: tuple[str, ...]
    origin_kind: str
    attribution: str | None = None

    def data(self) -> dict[str, object]:
        if not all(_token(value) for value in (self.provider_id, self.license_mode, self.origin_kind)) or type(self.source_uri) is not str or not self.source_uri.strip() or (self.attribution is not None and (type(self.attribution) is not str or self.attribution != self.attribution.strip())):
            _reject("SOURCE_DESCRIPTOR_INVALID")
        if self.origin_kind != "local_replay":
            _reject("SOURCE_DESCRIPTOR_INVALID")
        payload = {"provider_id": self.provider_id, "source_uri": self.source_uri, "license_mode": self.license_mode, "allowed_uses": list(_tokens(self.allowed_uses)), "origin_kind": self.origin_kind, "attribution": self.attribution}
        digest = _hash(payload)
        return {"descriptor_id": "desc_" + digest[7:27], "descriptor_hash": digest, **payload}

    @property
    def descriptor_hash(self) -> str:
        return str(self.data()["descriptor_hash"])

    @property
    def same_source_key(self) -> str:
        data = self.data()
        return _hash((data["provider_id"], data["source_uri"], data["origin_kind"]))


@dataclass(frozen=True)
class MediaProbeEvidenceV1:
    fixture_id: str
    fixture_hash: str
    source_hash: str
    media_type: MediaType
    duration_ms: int | None
    width: int | None
    height: int | None
    fps_numerator: int | None
    fps_denominator: int | None
    codec: str | None
    has_audio: bool

    def data(self) -> dict[str, object]:
        if not _token(self.fixture_id) or not _hash_value(self.fixture_hash) or not _hash_value(self.source_hash) or type(self.media_type) is not MediaType or type(self.has_audio) is not bool:
            _reject("MEDIA_PROBE_INVALID")
        ints = (self.duration_ms, self.width, self.height, self.fps_numerator, self.fps_denominator)
        if any(value is not None and (type(value) is not int or value < 0) for value in ints) or (self.codec is not None and not _token(self.codec)):
            _reject("MEDIA_PROBE_INVALID")
        if self.media_type is MediaType.VIDEO and (not self.duration_ms or not self.width or not self.height or not self.fps_numerator or not self.fps_denominator):
            _reject("MEDIA_PROBE_INVALID")
        if self.media_type is MediaType.VIDEO and math.gcd(self.fps_numerator, self.fps_denominator) != 1:
            _reject("MEDIA_PROBE_INVALID")
        facts = {"source_hash": self.source_hash, "media_type": self.media_type.value, "duration_ms": self.duration_ms, "width": self.width, "height": self.height, "fps_numerator": self.fps_numerator, "fps_denominator": self.fps_denominator, "codec": self.codec, "has_audio": self.has_audio}
        if self.fixture_hash != _hash(facts):
            _reject("MEDIA_PROBE_INVALID")
        payload = {"fixture_id": self.fixture_id, "fixture_hash": self.fixture_hash, **facts}
        digest = _hash(payload)
        return {"probe_id": "probe_" + digest[7:27], "probe_hash": digest, **payload}

    @property
    def probe_hash(self) -> str:
        return str(self.data()["probe_hash"])


@dataclass(frozen=True)
class FingerprintEvidenceV1:
    fixture_id: str
    fixture_hash: str
    source_hash: str
    descriptor_hash: str
    perceptual_frame_hashes: tuple[str, ...]
    local_feature_hashes: tuple[str, ...]
    same_source_key: str

    def data(self) -> dict[str, object]:
        values = (self.fixture_id, self.fixture_hash, self.source_hash, self.descriptor_hash, self.same_source_key)
        if not _token(self.fixture_id) or any(not _hash_value(value) for value in values[1:]):
            _reject("FINGERPRINT_EVIDENCE_INVALID")
        perceptual, local = _tokens(self.perceptual_frame_hashes), _tokens(self.local_feature_hashes)
        if any(not _hash_value(value) for value in perceptual + local):
            _reject("FINGERPRINT_EVIDENCE_INVALID")
        facts = {"source_hash": self.source_hash, "descriptor_hash": self.descriptor_hash, "perceptual_frame_hashes": list(perceptual), "local_feature_hashes": list(local), "same_source_key": self.same_source_key}
        if self.fixture_hash != _hash(facts):
            _reject("FINGERPRINT_EVIDENCE_INVALID")
        payload = {"fixture_id": self.fixture_id, "fixture_hash": self.fixture_hash, **facts}
        digest = _hash(payload)
        return {"evidence_id": "fp_" + digest[7:27], "evidence_hash": digest, **payload}

    @property
    def evidence_hash(self) -> str:
        return str(self.data()["evidence_hash"])


@dataclass(frozen=True)
class SemanticDeclarationV1:
    subjects: tuple[str, ...]
    actions: tuple[str, ...]
    setting: str | None
    mood: str | None
    semantic_tags: tuple[str, ...]
    avoid_contexts: tuple[str, ...]
    domain_roles: tuple[str, ...]
    domain_sensitivity_tags: tuple[str, ...]

    def data(self) -> dict[str, object]:
        if any(value is not None and not _token(value) for value in (self.setting, self.mood)):
            _reject("SEMANTIC_DECLARATION_INVALID")
        return {"subjects": list(_tokens(self.subjects)), "actions": list(_tokens(self.actions)), "setting": self.setting, "mood": self.mood, "semantic_tags": list(_tokens(self.semantic_tags)), "avoid_contexts": list(_tokens(self.avoid_contexts)), "domain_roles": list(_tokens(self.domain_roles)), "domain_sensitivity_tags": list(_tokens(self.domain_sensitivity_tags))}


@dataclass(frozen=True)
class SelectedRangeV1:
    start_inclusive: int
    end_exclusive: int

    def data(self, source_hash: str) -> dict[str, object]:
        if type(self.start_inclusive) is not int or type(self.end_exclusive) is not int or self.start_inclusive < 0 or self.end_exclusive <= self.start_inclusive:
            _reject("SELECTED_RANGE_INVALID")
        value = {"source_hash": source_hash, "timebase": "media_ms_v1", "start_inclusive": self.start_inclusive, "end_exclusive": self.end_exclusive}
        return {"range_id": "rng_" + _hash(value)[7:27], "range_hash": _hash(value), **value}


@dataclass(frozen=True)
class SourceAudioEligibilityV1:
    status: SourceAudioStatus
    reason_tokens: tuple[str, ...]
    evidence_ids: tuple[str, ...]

    def data(self, snapshot: DomainPolicySnapshot) -> dict[str, object]:
        if type(self.status) is not SourceAudioStatus:
            _reject("SOURCE_AUDIO_ELIGIBILITY_INVALID")
        return {"status": self.status.value, "reason_tokens": list(_tokens(self.reason_tokens)), "evidence_ids": list(_tokens(self.evidence_ids)), "policy_snapshot_id": snapshot.snapshot_id, "policy_snapshot_hash": snapshot.canonical_hash}


@dataclass(frozen=True)
class AssetCatalogPolicyV1:
    policy_version: str
    allowed_asset_brief_roles: tuple[str, ...]
    allowed_preferred_type_tokens: tuple[str, ...]
    allowed_avoid_context_tokens: tuple[str, ...]
    allowed_domain_role_tokens: tuple[str, ...]
    allowed_domain_sensitivity_tokens: tuple[str, ...]
    source_audio_reason_tokens: tuple[str, ...]
    generic_stock_provider_tokens: tuple[str, ...]
    reuse_cooldown_frames: int
    chapter_family_budget: int
    snapshot_id: str
    snapshot_hash: str

    def _payload(self) -> dict[str, object]:
        lists = {name: list(_tokens(getattr(self, name))) for name in self.__dataclass_fields__ if name.startswith("allowed_") or name.endswith("_tokens")}
        if self.policy_version != ASSET_CATALOG_POLICY_V1 or any(type(value) is not int or value < 0 for value in (self.reuse_cooldown_frames, self.chapter_family_budget)) or not _token(self.snapshot_id) or not _hash_value(self.snapshot_hash):
            _reject("ASSET_CATALOG_POLICY_INVALID")
        return {"version": self.policy_version, **lists, "reuse_cooldown_frames": self.reuse_cooldown_frames, "chapter_family_budget": self.chapter_family_budget, "policy_snapshot_id": self.snapshot_id, "policy_snapshot_hash": self.snapshot_hash}

    @property
    def policy_hash(self) -> str:
        return _hash(self._payload())

    @property
    def policy_id(self) -> str:
        return "apol_" + self.policy_hash[7:27]

    def data(self) -> dict[str, object]:
        return {"policy_id": self.policy_id, "policy_hash": self.policy_hash, **self._payload()}


@dataclass(frozen=True)
class AssetBriefV1:
    """Policy-bound editorial request; deliberately not an EDL selection."""

    editorial_role: str
    subject: str | None
    action: str | None
    setting: str | None
    avoid_contexts: tuple[str, ...]
    preferred_asset_type_tokens: tuple[str, ...]
    policy_snapshot_id: str
    policy_snapshot_hash: str
    resolved_visual_policy_hash: str

    def data(self, policy: AssetCatalogPolicyV1) -> dict[str, object]:
        if type(policy) is not AssetCatalogPolicyV1 or (self.policy_snapshot_id, self.policy_snapshot_hash, self.resolved_visual_policy_hash) != (policy.snapshot_id, policy.snapshot_hash, policy.policy_hash):
            _reject("ASSET_BRIEF_POLICY_MISMATCH")
        if not _token(self.editorial_role) or self.editorial_role not in policy.allowed_asset_brief_roles or any(value is not None and not _token(value) for value in (self.subject, self.action, self.setting)):
            _reject("ASSET_BRIEF_INVALID")
        avoid = _tokens(self.avoid_contexts); preferred = _tokens(self.preferred_asset_type_tokens)
        if any(token not in policy.allowed_avoid_context_tokens for token in avoid) or any(token not in policy.allowed_preferred_type_tokens for token in preferred):
            _reject("ASSET_BRIEF_POLICY_DENIED")
        value = {"editorial_role": self.editorial_role, "subject": self.subject, "action": self.action, "setting": self.setting, "avoid_contexts": list(avoid), "preferred_asset_type_tokens": list(preferred), "policy_snapshot_id": self.policy_snapshot_id, "policy_snapshot_hash": self.policy_snapshot_hash, "resolved_visual_policy_hash": self.resolved_visual_policy_hash}
        digest = _hash(value)
        return {"brief_id": "brief_" + digest[7:27], "brief_hash": digest, **value}


def asset_catalog_policy_from_snapshot(snapshot: DomainPolicySnapshot) -> AssetCatalogPolicyV1:
    if type(snapshot) is not DomainPolicySnapshot or not snapshot.immutable:
        _reject("POLICY_SNAPSHOT_INVALID")
    raw_snapshot = {field: getattr(snapshot, field) for field in snapshot.__dataclass_fields__}
    if snapshot.canonical_hash != policy_snapshot_hash(raw_snapshot):
        _reject("POLICY_SNAPSHOT_INVALID")
    bundles = snapshot.resolved_policy.get("policy_bundles") if type(snapshot.resolved_policy) is dict else None
    matches: list[object] = []
    if type(bundles) is list:
        for bundle in bundles:
            visual = bundle.get("policy", {}).get("visual") if type(bundle) is dict and type(bundle.get("policy")) is dict else None
            if type(visual) is dict and "asset_catalog_policy" in visual:
                matches.append(visual["asset_catalog_policy"])
    expected = {"policy_version", "allowed_asset_brief_roles", "allowed_preferred_type_tokens", "allowed_avoid_context_tokens", "allowed_domain_role_tokens", "allowed_domain_sensitivity_tokens", "source_audio_reason_tokens", "generic_stock_provider_tokens", "reuse_cooldown_frames", "chapter_family_budget"}
    if len(matches) != 1 or type(matches[0]) is not dict or set(matches[0]) != expected:
        _reject("ASSET_CATALOG_POLICY_MISSING")
    raw = matches[0]
    return AssetCatalogPolicyV1(snapshot_id=snapshot.snapshot_id, snapshot_hash=snapshot.canonical_hash, **raw)


class ReplayAssetEvidenceRegistry:
    """Immutable local manifest authority; callers cannot register evidence."""

    def __init__(self) -> None:
        self._probes: dict[str, MediaProbeEvidenceV1] = {}
        self._fingerprints: dict[str, FingerprintEvidenceV1] = {}

    @classmethod
    def load(cls, manifest_path: Path) -> "ReplayAssetEvidenceRegistry":
        try:
            raw = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            _reject("REPLAY_EVIDENCE_MANIFEST_INVALID")
        if type(raw) is not dict or set(raw) != {"schema_version", "manifest_id", "manifest_hash", "entries"} or raw["schema_version"] != "REPLAY-ASSET-EVIDENCE-MANIFEST-V1" or not _token(raw["manifest_id"]) or not _hash_value(raw["manifest_hash"]) or type(raw["entries"]) is not list:
            _reject("REPLAY_EVIDENCE_MANIFEST_INVALID")
        if raw["manifest_hash"] != _hash({"schema_version": raw["schema_version"], "manifest_id": raw["manifest_id"], "entries": raw["entries"]}) or (raw["manifest_id"], raw["manifest_hash"]) != (TRUSTED_REPLAY_MANIFEST_ID, TRUSTED_REPLAY_MANIFEST_HASH):
            _reject("REPLAY_EVIDENCE_MANIFEST_INVALID")
        registry = cls()
        for entry in raw["entries"]:
            if type(entry) is not dict or set(entry) != {"probe", "fingerprints"}:
                _reject("REPLAY_EVIDENCE_MANIFEST_INVALID")
            try:
                probe_raw, fingerprint_raw = entry["probe"], entry["fingerprints"]
                probe_values = {key: probe_raw[key] for key in ("fixture_id", "fixture_hash", "source_hash", "media_type", "duration_ms", "width", "height", "fps_numerator", "fps_denominator", "codec", "has_audio")}
                fingerprint_values = {key: fingerprint_raw[key] for key in ("fixture_id", "fixture_hash", "source_hash", "descriptor_hash", "perceptual_frame_hashes", "local_feature_hashes", "same_source_key")}
                probe = MediaProbeEvidenceV1(**{**probe_values, "media_type": MediaType(probe_values["media_type"])})
                fingerprints = FingerprintEvidenceV1(**{**fingerprint_values, "perceptual_frame_hashes": tuple(fingerprint_values["perceptual_frame_hashes"]), "local_feature_hashes": tuple(fingerprint_values["local_feature_hashes"])})
            except (TypeError, ValueError):
                _reject("REPLAY_EVIDENCE_MANIFEST_INVALID")
            if type(probe) is not MediaProbeEvidenceV1 or type(fingerprints) is not FingerprintEvidenceV1 or probe.source_hash != fingerprints.source_hash:
                _reject("REPLAY_EVIDENCE_MANIFEST_INVALID")
            probe.data(); fingerprints.data()
            if probe.source_hash in registry._probes:
                _reject("REPLAY_EVIDENCE_MANIFEST_INVALID")
            registry._probes[probe.source_hash], registry._fingerprints[probe.source_hash] = probe, fingerprints
        return registry

    def resolve(self, source_hash: str) -> tuple[MediaProbeEvidenceV1, FingerprintEvidenceV1]:
        try:
            return self._probes[source_hash], self._fingerprints[source_hash]
        except KeyError:
            _reject("UNTRUSTED_REPLAY_EVIDENCE")


@dataclass(frozen=True)
class AssetIngestionInputV1:
    asset_bytes: bytes
    project_id: str
    sequence_id: str | None
    source_descriptor: SourceDescriptorV1
    semantic_declaration: SemanticDeclarationV1
    selected_ranges: tuple[SelectedRangeV1, ...]
    source_audio_eligibility: SourceAudioEligibilityV1


class AssetMaterializationRegistry:
    """Private in-memory byte store; handles are opaque and re-hashed on read."""

    def __init__(self) -> None:
        self._entries: dict[str, tuple[str, bytes]] = {}

    def register(self, value: AssetIngestionInputV1) -> str:
        if type(value) is not AssetIngestionInputV1 or type(value.asset_bytes) is not bytes or not value.asset_bytes:
            _reject("ASSET_INPUT_INVALID")
        source_hash = _bytes_hash(value.asset_bytes)
        handle = "mat_" + _hash((source_hash, len(value.asset_bytes), len(self._entries)))[7:27]
        self._entries[handle] = (source_hash, value.asset_bytes)
        return handle

    def resolve(self, handle: str) -> bytes:
        if not _token(handle):
            _reject("MATERIALIZATION_UNAVAILABLE")
        try:
            expected, value = self._entries[handle]
        except KeyError:
            _reject("MATERIALIZATION_UNAVAILABLE")
        if type(value) is not bytes or _bytes_hash(value) != expected:
            _reject("MATERIALIZATION_UNAVAILABLE")
        return value


@dataclass(frozen=True)
class AssetIngestionPackageV1:
    schema_version: str
    package_id: str
    package_hash: str
    project_id: str
    sequence_id: str | None
    policy_snapshot_id: str
    policy_snapshot_hash: str
    source_hash: str
    source_byte_length: int
    source_descriptor: dict[str, object]
    media_probe_evidence: dict[str, object]
    fingerprint_evidence: dict[str, object]
    semantic_declaration: dict[str, object]
    selected_ranges: tuple[dict[str, object], ...]
    source_audio_eligibility: dict[str, object]


def canonical_ingestion_package_json(package: AssetIngestionPackageV1) -> bytes:
    if type(package) is not AssetIngestionPackageV1:
        _reject("ASSET_PACKAGE_INVALID")
    payload = {key: _json_value(value) for key, value in package.__dict__.items() if key not in {"package_id", "package_hash"}}
    if package.schema_version != ASSET_CATALOG_SCHEMA_V1 or package.package_hash != _hash(payload) or package.package_id != "pkg_" + package.package_hash[7:27]:
        _reject("ASSET_PACKAGE_INVALID")
    return encode_canonical_json_bytes(_json_value(package))


def load_ingestion_package_json(*, payload: bytes, asset_bytes: bytes, policy: AssetCatalogPolicyV1, evidence_manifest_path: Path = TRUSTED_REPLAY_MANIFEST_PATH) -> AssetIngestionPackageV1:
    raw = _canonical_json_load(payload, "ASSET_PACKAGE_INVALID")
    fields = tuple(AssetIngestionPackageV1.__dataclass_fields__)
    if type(raw) is not dict or set(raw) != set(fields) or type(asset_bytes) is not bytes or not asset_bytes or type(policy) is not AssetCatalogPolicyV1:
        _reject("ASSET_PACKAGE_INVALID")
    try:
        package = AssetIngestionPackageV1(**{**raw, "selected_ranges": tuple(raw["selected_ranges"])})
    except TypeError:
        _reject("ASSET_PACKAGE_INVALID")
    if package.source_hash != _bytes_hash(asset_bytes) or package.source_byte_length != len(asset_bytes) or canonical_ingestion_package_json(package) != payload or (package.policy_snapshot_id, package.policy_snapshot_hash) != (policy.snapshot_id, policy.snapshot_hash):
        _reject("ASSET_PACKAGE_INVALID")
    try:
        descriptor = SourceDescriptorV1(**{key: package.source_descriptor[key] for key in ("provider_id", "source_uri", "license_mode", "allowed_uses", "origin_kind", "attribution")})
        probe = MediaProbeEvidenceV1(**{**{key: package.media_probe_evidence[key] for key in ("fixture_id", "fixture_hash", "source_hash", "duration_ms", "width", "height", "fps_numerator", "fps_denominator", "codec", "has_audio")}, "media_type": MediaType(package.media_probe_evidence["media_type"])})
        fingerprints = FingerprintEvidenceV1(**{**{key: package.fingerprint_evidence[key] for key in ("fixture_id", "fixture_hash", "source_hash", "descriptor_hash", "same_source_key")}, "perceptual_frame_hashes": tuple(package.fingerprint_evidence["perceptual_frame_hashes"]), "local_feature_hashes": tuple(package.fingerprint_evidence["local_feature_hashes"])})
        semantic = SemanticDeclarationV1(**{**package.semantic_declaration, "subjects": tuple(package.semantic_declaration["subjects"]), "actions": tuple(package.semantic_declaration["actions"]), "semantic_tags": tuple(package.semantic_declaration["semantic_tags"]), "avoid_contexts": tuple(package.semantic_declaration["avoid_contexts"]), "domain_roles": tuple(package.semantic_declaration["domain_roles"]), "domain_sensitivity_tags": tuple(package.semantic_declaration["domain_sensitivity_tags"])})
        audio = SourceAudioEligibilityV1(SourceAudioStatus(package.source_audio_eligibility["status"]), tuple(package.source_audio_eligibility["reason_tokens"]), tuple(package.source_audio_eligibility["evidence_ids"]))
        ranges = tuple(SelectedRangeV1(item["start_inclusive"], item["end_exclusive"]) for item in package.selected_ranges)
    except (KeyError, TypeError, ValueError):
        _reject("ASSET_PACKAGE_INVALID")
    registry = ReplayAssetEvidenceRegistry.load(evidence_manifest_path)
    trusted_probe, trusted_fingerprints = registry.resolve(package.source_hash)
    if descriptor.data() != package.source_descriptor or probe.data() != package.media_probe_evidence or fingerprints.data() != package.fingerprint_evidence or semantic.data() != package.semantic_declaration or probe != trusted_probe or fingerprints != trusted_fingerprints or fingerprints.descriptor_hash != descriptor.descriptor_hash or fingerprints.same_source_key != descriptor.same_source_key:
        _reject("ASSET_PACKAGE_INVALID")
    if any(token not in policy.allowed_avoid_context_tokens for token in semantic.data()["avoid_contexts"]) or any(token not in policy.allowed_domain_role_tokens for token in semantic.data()["domain_roles"]) or any(token not in policy.allowed_domain_sensitivity_tokens for token in semantic.data()["domain_sensitivity_tags"]):
        _reject("ASSET_PACKAGE_INVALID")
    input_value = AssetIngestionInputV1(asset_bytes, package.project_id, package.sequence_id, descriptor, semantic, ranges, audio)
    if tuple(item.data(package.source_hash) for item in ranges) != package.selected_ranges or _ranges(input_value, package.source_hash, probe) != package.selected_ranges or audio.data(_snapshot_stub(policy)) != package.source_audio_eligibility or any(token not in policy.source_audio_reason_tokens for token in audio.reason_tokens) or any(value not in {probe.data()["probe_id"], fingerprints.data()["evidence_id"]} for value in audio.evidence_ids):
        _reject("ASSET_PACKAGE_INVALID")
    return package


@dataclass(frozen=True)
class AssetRecordV1:
    asset_id: str
    asset_hash: str
    source_hash: str
    source_byte_length: int
    media_type: MediaType
    media_facts: dict[str, object]
    source_descriptor: dict[str, object]
    fingerprint_evidence: dict[str, object]
    visual_family_id: str
    subjects: tuple[str, ...]
    actions: tuple[str, ...]
    setting: str | None
    mood: str | None
    semantic_tags: tuple[str, ...]
    avoid_contexts: tuple[str, ...]
    domain_roles: tuple[str, ...]
    domain_sensitivity_tags: tuple[str, ...]
    selected_ranges: tuple[dict[str, object], ...]
    source_audio_eligibility: dict[str, object]
    duplicate_of_asset_id: str | None
    duplicate_of_asset_hash: str | None


@dataclass(frozen=True)
class DuplicateDecisionV1:
    decision_id: str
    decision_hash: str
    candidate_package_id: str
    candidate_package_hash: str
    candidate_source_hash: str
    decision_kind: DuplicateKind
    matched_asset_id: str | None
    matched_asset_hash: str | None
    matched_source_hash: str | None
    matched_fingerprint_ids: tuple[str, ...]
    overlapping_selected_ranges: tuple[str, ...]


@dataclass(frozen=True)
class AssetCatalogV1:
    catalog_id: str
    catalog_hash: str
    project_id: str
    policy_snapshot_id: str
    policy_snapshot_hash: str
    records: tuple[AssetRecordV1, ...]
    blocked_decisions: tuple[DuplicateDecisionV1, ...] = ()


@dataclass(frozen=True)
class GenericStockRatioV1:
    ratio_id: str
    ratio_hash: str
    catalog_id: str
    catalog_hash: str
    provider_token_set_hash: str
    status: str
    numerator: int
    denominator: int
    numerator_asset_ids: tuple[str, ...]


@dataclass(frozen=True)
class AssetReuseInstanceV1:
    asset_id: str
    asset_hash: str
    visual_family_id: str
    sequence_id: str
    start_frame: int
    end_exclusive_frame: int
    ordinal: int


@dataclass(frozen=True)
class AssetReuseViolationV1:
    violation_id: str
    violation_hash: str
    kind: str
    visual_family_id: str
    involved_instance_ordinals: tuple[int, ...]
    observed_value: int
    policy_limit: int


@dataclass(frozen=True)
class AssetReuseContextV1:
    catalog_id: str
    catalog_hash: str
    chapter_id: str
    frame_rate: tuple[int, int]
    instances: tuple[AssetReuseInstanceV1, ...]
    context_id: str = field(init=False)
    context_hash: str = field(init=False)

    def __post_init__(self) -> None:
        digest = _hash({"catalog_id": self.catalog_id, "catalog_hash": self.catalog_hash, "chapter_id": self.chapter_id, "frame_rate": list(self.frame_rate), "instances": [item.__dict__ for item in self.instances]})
        object.__setattr__(self, "context_hash", digest)
        object.__setattr__(self, "context_id", "ctx_" + digest[7:27])


@dataclass(frozen=True)
class AssetReusePlanV1:
    status: ReuseStatus
    violations: tuple[AssetReuseViolationV1, ...]
    context_id: str | None = None
    context_hash: str | None = None
    policy_id: str | None = None
    policy_hash: str | None = None
    family_counts: tuple[tuple[str, int], ...] = ()
    generic_stock_ratio_id: str | None = None
    generic_stock_ratio_hash: str | None = None
    plan_id: str = field(init=False)
    plan_hash: str = field(init=False)

    def __post_init__(self) -> None:
        digest = _hash({"status": self.status.value, "context_id": self.context_id, "context_hash": self.context_hash, "policy_id": self.policy_id, "policy_hash": self.policy_hash, "family_counts": [list(item) for item in self.family_counts], "violations": [item.__dict__ for item in self.violations], "generic_stock_ratio_id": self.generic_stock_ratio_id, "generic_stock_ratio_hash": self.generic_stock_ratio_hash})
        object.__setattr__(self, "plan_hash", digest)
        object.__setattr__(self, "plan_id", "plan_" + digest[7:27])


@dataclass(frozen=True)
class CatalogCompilationV1:
    package: AssetIngestionPackageV1
    decision: DuplicateDecisionV1
    catalog: AssetCatalogV1
    generic_stock_ratio: GenericStockRatioV1
    reuse_plan: AssetReusePlanV1
    outcome_kind: str
    mutation: AssetCatalogMutationV1
    receipt: CatalogReceiptV1


@dataclass(frozen=True)
class AssetCatalogMutationV1:
    mutation_id: str
    mutation_hash: str
    input_catalog_id: str
    input_catalog_hash: str
    candidate_package_id: str
    candidate_package_hash: str
    duplicate_decision: DuplicateDecisionV1
    result_kind: str
    accepted_asset_record: AssetRecordV1 | None
    output_catalog_id: str
    output_catalog_hash: str


@dataclass(frozen=True)
class CatalogReceiptV1:
    receipt_id: str
    receipt_hash: str
    status: str
    outcome_kind: str
    reuse_gate_status: str
    error_code: str | None
    dependency_nodes: tuple[tuple[str, str, str], ...]
    dependency_edges: tuple[tuple[str, str, str, str], ...]


@dataclass(frozen=True)
class CatalogFailureV1:
    """Closed failure union: no package, catalog, mutation or other outputs."""

    error_code: str
    receipt: CatalogReceiptV1


def _ranges(input_value: AssetIngestionInputV1, source_hash: str, probe: MediaProbeEvidenceV1) -> tuple[dict[str, object], ...]:
    ranges = tuple(item.data(source_hash) for item in input_value.selected_ranges)
    if probe.media_type in {MediaType.IMAGE, MediaType.DOCUMENT} and ranges:
        _reject("SELECTED_RANGE_INVALID")
    if probe.duration_ms is not None and any(item["end_exclusive"] > probe.duration_ms for item in ranges):
        _reject("SELECTED_RANGE_INVALID")
    if any(ranges[index]["end_exclusive"] > ranges[index + 1]["start_inclusive"] for index in range(len(ranges) - 1)):
        _reject("SELECTED_RANGE_INVALID")
    return ranges


def _catalog_hash(project_id: str, policy: AssetCatalogPolicyV1, records: tuple[AssetRecordV1, ...], blocked: tuple[DuplicateDecisionV1, ...]) -> str:
    return _hash({"project_id": project_id, "policy_snapshot_id": policy.snapshot_id, "policy_snapshot_hash": policy.snapshot_hash, "records": [record.__dict__ for record in records], "blocked_decisions": [decision.__dict__ for decision in blocked]})


def empty_asset_catalog(project_id: str, policy: AssetCatalogPolicyV1) -> AssetCatalogV1:
    if not _token(project_id) or type(policy) is not AssetCatalogPolicyV1:
        _reject("ASSET_CATALOG_INVALID")
    digest = _catalog_hash(project_id, policy, (), ())
    return AssetCatalogV1("cat_" + digest[7:27], digest, project_id, policy.snapshot_id, policy.snapshot_hash, ())


def _validate_catalog(catalog: AssetCatalogV1, policy: AssetCatalogPolicyV1, project_id: str, evidence_registry: ReplayAssetEvidenceRegistry | None = None) -> None:
    if type(catalog) is not AssetCatalogV1 or (catalog.project_id, catalog.policy_snapshot_id, catalog.policy_snapshot_hash) != (project_id, policy.snapshot_id, policy.snapshot_hash):
        _reject("ASSET_CATALOG_INVALID")
    if tuple(sorted(catalog.records, key=lambda item: item.asset_id)) != catalog.records or tuple(sorted(catalog.blocked_decisions, key=lambda item: item.decision_id)) != catalog.blocked_decisions or len({item.asset_id for item in catalog.records}) != len(catalog.records) or len({item.source_hash for item in catalog.records}) != len(catalog.records):
        _reject("ASSET_CATALOG_INVALID")
    for record in catalog.records:
        payload = {key: value for key, value in record.__dict__.items() if key not in {"asset_id", "asset_hash"}}
        if record.asset_hash != _hash(payload) or record.asset_id != "ast_" + record.asset_hash[7:27] or (record.duplicate_of_asset_id, record.duplicate_of_asset_hash) != (None, None):
            _reject("ASSET_CATALOG_INVALID")
        try:
            descriptor = SourceDescriptorV1(**{key: record.source_descriptor[key] for key in ("provider_id", "source_uri", "license_mode", "allowed_uses", "origin_kind", "attribution")})
            evidence = FingerprintEvidenceV1(**{**{key: record.fingerprint_evidence[key] for key in ("fixture_id", "fixture_hash", "source_hash", "descriptor_hash", "same_source_key")}, "perceptual_frame_hashes": tuple(record.fingerprint_evidence["perceptual_frame_hashes"]), "local_feature_hashes": tuple(record.fingerprint_evidence["local_feature_hashes"])})
        except (KeyError, TypeError):
            _reject("ASSET_CATALOG_INVALID")
        if descriptor.data() != record.source_descriptor or evidence.data() != record.fingerprint_evidence or evidence.source_hash != record.source_hash or evidence.descriptor_hash != descriptor.descriptor_hash or evidence.same_source_key != descriptor.same_source_key:
            _reject("ASSET_CATALOG_INVALID")
        if evidence_registry is not None:
            trusted_probe, trusted_fingerprints = evidence_registry.resolve(record.source_hash)
            trusted_media_facts = {key: trusted_probe.data()[key] for key in ("duration_ms", "width", "height", "fps_numerator", "fps_denominator", "codec", "has_audio")}
            if evidence != trusted_fingerprints or record.media_type is not trusted_probe.media_type or record.media_facts != trusted_media_facts:
                _reject("ASSET_CATALOG_INVALID")
        if set(record.media_facts) != {"duration_ms", "width", "height", "fps_numerator", "fps_denominator", "codec", "has_audio"} or type(record.media_facts["has_audio"]) is not bool or any(value is not None and (type(value) is not int or value < 0) for value in (record.media_facts["duration_ms"], record.media_facts["width"], record.media_facts["height"], record.media_facts["fps_numerator"], record.media_facts["fps_denominator"])) or (record.media_facts["codec"] is not None and not _token(record.media_facts["codec"])):
            _reject("ASSET_CATALOG_INVALID")
        if record.media_type is MediaType.VIDEO and (not record.media_facts["duration_ms"] or not record.media_facts["width"] or not record.media_facts["height"] or not record.media_facts["fps_numerator"] or not record.media_facts["fps_denominator"] or math.gcd(record.media_facts["fps_numerator"], record.media_facts["fps_denominator"]) != 1):
            _reject("ASSET_CATALOG_INVALID")
        if record.media_type is not MediaType.VIDEO and (record.media_facts["fps_numerator"] is not None or record.media_facts["fps_denominator"] is not None):
            _reject("ASSET_CATALOG_INVALID")
        expected_family = "fam_" + _hash({"policy": policy.policy_hash, "media_type": record.media_type.value, "perceptual": list(record.fingerprint_evidence["perceptual_frame_hashes"]), "local": list(record.fingerprint_evidence["local_feature_hashes"])})[7:27]
        if record.visual_family_id != expected_family:
            _reject("ASSET_CATALOG_INVALID")
        try:
            ranges = tuple(SelectedRangeV1(item["start_inclusive"], item["end_exclusive"]) for item in record.selected_ranges)
        except (KeyError, TypeError):
            _reject("ASSET_CATALOG_INVALID")
        if record.media_type not in {MediaType.VIDEO, MediaType.AUDIO} and ranges:
            _reject("ASSET_CATALOG_INVALID")
        if tuple(item.data(record.source_hash) for item in ranges) != record.selected_ranges or (record.media_facts["duration_ms"] is not None and any(item.end_exclusive > record.media_facts["duration_ms"] for item in ranges)) or tuple(sorted(ranges, key=lambda item: (item.start_inclusive, item.end_exclusive))) != ranges or any(left.end_exclusive > right.start_inclusive for left, right in zip(ranges, ranges[1:])):
            _reject("ASSET_CATALOG_INVALID")
        if any(value is not None and not _token(value) for value in (record.setting, record.mood)):
            _reject("ASSET_CATALOG_INVALID")
        for values in (record.subjects, record.actions, record.semantic_tags, record.avoid_contexts, record.domain_roles, record.domain_sensitivity_tags):
            _tokens(values)
        if any(token not in policy.allowed_avoid_context_tokens for token in record.avoid_contexts) or any(token not in policy.allowed_domain_role_tokens for token in record.domain_roles) or any(token not in policy.allowed_domain_sensitivity_tokens for token in record.domain_sensitivity_tags):
            _reject("ASSET_CATALOG_INVALID")
        audio = record.source_audio_eligibility
        if set(audio) != {"status", "reason_tokens", "evidence_ids", "policy_snapshot_id", "policy_snapshot_hash"} or audio["status"] not in {item.value for item in SourceAudioStatus} or (audio["policy_snapshot_id"], audio["policy_snapshot_hash"]) != (policy.snapshot_id, policy.snapshot_hash) or any(token not in policy.source_audio_reason_tokens for token in _tokens(audio["reason_tokens"])) or any(item != record.fingerprint_evidence["evidence_id"] for item in _tokens(audio["evidence_ids"])):
            _reject("ASSET_CATALOG_INVALID")
    for decision in catalog.blocked_decisions:
        payload = {"candidate_package_id": decision.candidate_package_id, "candidate_package_hash": decision.candidate_package_hash, "candidate_source_hash": decision.candidate_source_hash, "decision_kind": decision.decision_kind.value, "matched_asset_id": decision.matched_asset_id, "matched_asset_hash": decision.matched_asset_hash, "matched_source_hash": decision.matched_source_hash, "matched_fingerprint_ids": list(decision.matched_fingerprint_ids), "overlapping_selected_ranges": list(decision.overlapping_selected_ranges)}
        if decision.decision_hash != _hash(payload) or decision.decision_id != "dec_" + decision.decision_hash[7:27] or decision.decision_kind is DuplicateKind.DISTINCT:
            _reject("ASSET_CATALOG_INVALID")
        matched = next((record for record in catalog.records if record.asset_id == decision.matched_asset_id), None)
        if matched is None or (decision.matched_asset_hash, decision.matched_source_hash) != (matched.asset_hash, matched.source_hash):
            _reject("ASSET_CATALOG_INVALID")
        if decision.decision_kind is DuplicateKind.EXACT_BYTES and decision.candidate_source_hash != matched.source_hash:
            _reject("ASSET_CATALOG_INVALID")
        if decision.decision_kind is DuplicateKind.SAME_SOURCE and (decision.candidate_source_hash == matched.source_hash or decision.matched_fingerprint_ids or decision.overlapping_selected_ranges):
            _reject("ASSET_CATALOG_INVALID")
        if decision.decision_kind is DuplicateKind.PERCEPTUAL_MATCH and (not decision.matched_fingerprint_ids or not set(decision.matched_fingerprint_ids).issubset(set(matched.fingerprint_evidence["perceptual_frame_hashes"]))):
            _reject("ASSET_CATALOG_INVALID")
        if decision.decision_kind is DuplicateKind.LOCAL_FEATURE_MATCH and (not decision.matched_fingerprint_ids or not set(decision.matched_fingerprint_ids).issubset(set(matched.fingerprint_evidence["local_feature_hashes"]))):
            _reject("ASSET_CATALOG_INVALID")
        if decision.decision_kind is DuplicateKind.SELECTED_RANGE_OVERLAP and (decision.candidate_source_hash != matched.source_hash or not decision.overlapping_selected_ranges):
            _reject("ASSET_CATALOG_INVALID")
    if catalog.catalog_hash != _catalog_hash(project_id, policy, catalog.records, catalog.blocked_decisions) or catalog.catalog_id != "cat_" + catalog.catalog_hash[7:27]:
        _reject("ASSET_CATALOG_INVALID")


def canonical_asset_catalog_json(*, catalog: AssetCatalogV1, policy: AssetCatalogPolicyV1, evidence_manifest_path: Path = TRUSTED_REPLAY_MANIFEST_PATH) -> bytes:
    """Canonical persisted catalog form; serialization is allowed only after verification."""
    _validate_catalog(catalog, policy, catalog.project_id, ReplayAssetEvidenceRegistry.load(evidence_manifest_path))
    return encode_canonical_json_bytes({
        "catalog_id": catalog.catalog_id, "catalog_hash": catalog.catalog_hash,
        "project_id": catalog.project_id, "policy_snapshot_id": catalog.policy_snapshot_id,
        "policy_snapshot_hash": catalog.policy_snapshot_hash,
        "records": [{key: (value.value if isinstance(value, Enum) else list(value) if isinstance(value, tuple) else value) for key, value in record.__dict__.items()} for record in catalog.records],
        "blocked_decisions": [{key: (value.value if isinstance(value, Enum) else list(value) if isinstance(value, tuple) else value) for key, value in decision.__dict__.items()} for decision in catalog.blocked_decisions],
    })


def load_asset_catalog_json(*, payload: bytes, policy: AssetCatalogPolicyV1, evidence_manifest_path: Path = TRUSTED_REPLAY_MANIFEST_PATH) -> AssetCatalogV1:
    """Load only the canonical catalog projection and rederive every nested identity."""
    try:
        raw = json.loads(payload.decode("utf-8"))
        expected = {"catalog_id", "catalog_hash", "project_id", "policy_snapshot_id", "policy_snapshot_hash", "records", "blocked_decisions"}
        if type(raw) is not dict or set(raw) != expected or type(raw["records"]) is not list or type(raw["blocked_decisions"]) is not list:
            _reject("ASSET_CATALOG_INVALID")
        records = tuple(AssetRecordV1(**{**item, "media_type": MediaType(item["media_type"]), "subjects": tuple(item["subjects"]), "actions": tuple(item["actions"]), "semantic_tags": tuple(item["semantic_tags"]), "avoid_contexts": tuple(item["avoid_contexts"]), "domain_roles": tuple(item["domain_roles"]), "domain_sensitivity_tags": tuple(item["domain_sensitivity_tags"]), "selected_ranges": tuple(item["selected_ranges"])} ) for item in raw["records"])
        decisions = tuple(DuplicateDecisionV1(**{**item, "decision_kind": DuplicateKind(item["decision_kind"]), "matched_fingerprint_ids": tuple(item["matched_fingerprint_ids"]), "overlapping_selected_ranges": tuple(item["overlapping_selected_ranges"])} ) for item in raw["blocked_decisions"])
        catalog = AssetCatalogV1(raw["catalog_id"], raw["catalog_hash"], raw["project_id"], raw["policy_snapshot_id"], raw["policy_snapshot_hash"], records, decisions)
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        _reject("ASSET_CATALOG_INVALID")
    registry = ReplayAssetEvidenceRegistry.load(evidence_manifest_path)
    _validate_catalog(catalog, policy, catalog.project_id, registry)
    if canonical_asset_catalog_json(catalog=catalog, policy=policy, evidence_manifest_path=evidence_manifest_path) != payload:
        _reject("ASSET_CATALOG_INVALID")
    return catalog


def verify_catalog_receipt(receipt: CatalogReceiptV1) -> None:
    """Public replay verifier for the terminal artifact lineage receipt."""
    _validate_receipt(receipt)


def canonical_catalog_receipt_json(receipt: CatalogReceiptV1) -> bytes:
    _validate_receipt(receipt)
    return encode_canonical_json_bytes(_json_value(receipt))


def load_catalog_receipt_json(payload: bytes) -> CatalogReceiptV1:
    raw = _canonical_json_load(payload, "RECEIPT_INVALID")
    fields = tuple(CatalogReceiptV1.__dataclass_fields__)
    if type(raw) is not dict or set(raw) != set(fields):
        _reject("RECEIPT_INVALID")
    try:
        receipt = CatalogReceiptV1(**{**raw, "dependency_nodes": tuple(tuple(item) for item in raw["dependency_nodes"]), "dependency_edges": tuple(tuple(item) for item in raw["dependency_edges"])})
    except TypeError:
        _reject("RECEIPT_INVALID")
    _validate_receipt(receipt)
    return receipt


def _decision(candidate: AssetRecordV1, fingerprints: FingerprintEvidenceV1, catalog: AssetCatalogV1, package: AssetIngestionPackageV1) -> DuplicateDecisionV1:
    def build(kind: DuplicateKind, record: AssetRecordV1 | None, fingerprints_ids: tuple[str, ...] = (), ranges: tuple[str, ...] = ()) -> DuplicateDecisionV1:
        payload = {"candidate_package_id": package.package_id, "candidate_package_hash": package.package_hash, "candidate_source_hash": candidate.source_hash, "decision_kind": kind.value, "matched_asset_id": None if record is None else record.asset_id, "matched_asset_hash": None if record is None else record.asset_hash, "matched_source_hash": None if record is None else record.source_hash, "matched_fingerprint_ids": list(fingerprints_ids), "overlapping_selected_ranges": list(ranges)}
        digest = _hash(payload)
        return DuplicateDecisionV1("dec_" + digest[7:27], digest, package.package_id, package.package_hash, candidate.source_hash, kind, payload["matched_asset_id"], payload["matched_asset_hash"], payload["matched_source_hash"], fingerprints_ids, ranges)
    for record in catalog.records:
        ranges = tuple(str(item["range_id"]) for item in candidate.selected_ranges for other in record.selected_ranges if candidate.source_hash == record.source_hash and item["start_inclusive"] < other["end_exclusive"] and other["start_inclusive"] < item["end_exclusive"])
        if ranges:
            return build(DuplicateKind.SELECTED_RANGE_OVERLAP, record, (), ranges)
    for record in catalog.records:
        if record.source_hash == candidate.source_hash:
            return build(DuplicateKind.EXACT_BYTES, record)
    for record in catalog.records:
        stored_key = record.fingerprint_evidence["same_source_key"]
        if stored_key == fingerprints.same_source_key:
            return build(DuplicateKind.SAME_SOURCE, record)
    for record in catalog.records:
        matched = tuple(sorted(set(record.fingerprint_evidence["perceptual_frame_hashes"]).intersection(candidate.fingerprint_evidence["perceptual_frame_hashes"])))
        if matched:
            return build(DuplicateKind.PERCEPTUAL_MATCH, record, matched)
    for record in catalog.records:
        matched = tuple(sorted(set(record.fingerprint_evidence["local_feature_hashes"]).intersection(candidate.fingerprint_evidence["local_feature_hashes"])))
        if matched:
            return build(DuplicateKind.LOCAL_FEATURE_MATCH, record, matched)
    return build(DuplicateKind.DISTINCT, None)


def _candidate_from_package(package: AssetIngestionPackageV1, policy: AssetCatalogPolicyV1) -> tuple[AssetRecordV1, FingerprintEvidenceV1]:
    """Rebuild the candidate identity from a verified package, never mutation JSON."""
    descriptor = package.source_descriptor
    probe = package.media_probe_evidence
    fingerprints_data = package.fingerprint_evidence
    fingerprints = FingerprintEvidenceV1(**{**{key: fingerprints_data[key] for key in ("fixture_id", "fixture_hash", "source_hash", "descriptor_hash", "same_source_key")}, "perceptual_frame_hashes": tuple(fingerprints_data["perceptual_frame_hashes"]), "local_feature_hashes": tuple(fingerprints_data["local_feature_hashes"])})
    semantic = package.semantic_declaration
    media_type = MediaType(probe["media_type"])
    media_facts = {key: probe[key] for key in ("duration_ms", "width", "height", "fps_numerator", "fps_denominator", "codec", "has_audio")}
    family = "fam_" + _hash({"policy": policy.policy_hash, "media_type": media_type.value, "perceptual": list(fingerprints.perceptual_frame_hashes), "local": list(fingerprints.local_feature_hashes)})[7:27]
    record_payload = {"source_hash": package.source_hash, "source_byte_length": package.source_byte_length, "media_type": media_type.value, "media_facts": media_facts, "source_descriptor": descriptor, "fingerprint_evidence": fingerprints_data, "visual_family_id": family, "subjects": semantic["subjects"], "actions": semantic["actions"], "setting": semantic["setting"], "mood": semantic["mood"], "semantic_tags": semantic["semantic_tags"], "avoid_contexts": semantic["avoid_contexts"], "domain_roles": semantic["domain_roles"], "domain_sensitivity_tags": semantic["domain_sensitivity_tags"], "selected_ranges": package.selected_ranges, "source_audio_eligibility": package.source_audio_eligibility, "duplicate_of_asset_id": None, "duplicate_of_asset_hash": None}
    asset_hash = _hash(record_payload)
    record = AssetRecordV1("ast_" + asset_hash[7:27], asset_hash, package.source_hash, package.source_byte_length, media_type, media_facts, descriptor, fingerprints_data, family, tuple(semantic["subjects"]), tuple(semantic["actions"]), semantic["setting"], semantic["mood"], tuple(semantic["semantic_tags"]), tuple(semantic["avoid_contexts"]), tuple(semantic["domain_roles"]), tuple(semantic["domain_sensitivity_tags"]), package.selected_ranges, package.source_audio_eligibility, None, None)
    return record, fingerprints


def _ratio(catalog: AssetCatalogV1, policy: AssetCatalogPolicyV1) -> GenericStockRatioV1:
    ids = tuple(record.asset_id for record in catalog.records if record.source_descriptor["provider_id"] in policy.generic_stock_provider_tokens)
    denominator = len(catalog.records)
    status = "available" if denominator else "unavailable_empty_catalog"
    data = {"catalog_id": catalog.catalog_id, "catalog_hash": catalog.catalog_hash, "provider_token_set_hash": _hash(list(policy.generic_stock_provider_tokens)), "status": status, "numerator": len(ids), "denominator": denominator, "numerator_asset_ids": list(ids)}
    digest = _hash(data)
    return GenericStockRatioV1(
        "ratio_" + digest[7:27], digest, catalog.catalog_id, catalog.catalog_hash,
        str(data["provider_token_set_hash"]), status, len(ids), denominator, ids,
    )


def _reuse(catalog: AssetCatalogV1, policy: AssetCatalogPolicyV1, context: AssetReuseContextV1 | None) -> AssetReusePlanV1:
    if context is None:
        return AssetReusePlanV1(ReuseStatus.NOT_EVALUATED, (), policy_id=policy.policy_id, policy_hash=policy.policy_hash)
    if type(context) is not AssetReuseContextV1 or (context.catalog_id, context.catalog_hash) != (catalog.catalog_id, catalog.catalog_hash) or not _token(context.chapter_id) or type(context.frame_rate) is not tuple or len(context.frame_rate) != 2 or any(type(value) is not int or value <= 0 for value in context.frame_rate) or math.gcd(*context.frame_rate) != 1:
        _reject("REUSE_CONTEXT_INVALID")
    context_payload = {"catalog_id": context.catalog_id, "catalog_hash": context.catalog_hash, "chapter_id": context.chapter_id, "frame_rate": list(context.frame_rate), "instances": [item.__dict__ for item in context.instances]}
    if context.context_hash != _hash(context_payload) or context.context_id != "ctx_" + context.context_hash[7:27]:
        _reject("REUSE_CONTEXT_INVALID")
    records = {record.asset_id: record for record in catalog.records}
    instances = tuple(sorted(context.instances, key=lambda item: (item.ordinal, item.sequence_id, item.start_frame, item.asset_id)))
    if instances != context.instances or len({item.ordinal for item in instances}) != len(instances):
        _reject("REUSE_CONTEXT_INVALID")
    for item in instances:
        record = records.get(item.asset_id)
        if type(item) is not AssetReuseInstanceV1 or record is None or (item.asset_hash, item.visual_family_id) != (record.asset_hash, record.visual_family_id) or not _token(item.sequence_id) or any(type(value) is not int for value in (item.start_frame, item.end_exclusive_frame, item.ordinal)) or item.start_frame < 0 or item.end_exclusive_frame <= item.start_frame:
            _reject("REUSE_CONTEXT_INVALID")
    violations: list[AssetReuseViolationV1] = []
    def violation(kind: str, family: str, ordinals: tuple[int, ...], observed: int, limit: int) -> AssetReuseViolationV1:
        payload = {"kind": kind, "visual_family_id": family, "involved_instance_ordinals": list(ordinals), "observed_value": observed, "policy_limit": limit}
        digest = _hash(payload)
        return AssetReuseViolationV1("rv_" + digest[7:27], digest, kind, family, ordinals, observed, limit)
    families: dict[str, list[AssetReuseInstanceV1]] = {}
    for item in instances: families.setdefault(item.visual_family_id, []).append(item)
    for family, values in families.items():
        if len(values) > policy.chapter_family_budget: violations.append(violation("chapter_family_budget", family, tuple(item.ordinal for item in values), len(values), policy.chapter_family_budget))
        for left, right in zip(values, values[1:]):
            gap = right.start_frame - left.end_exclusive_frame
            if gap < policy.reuse_cooldown_frames: violations.append(violation("cooldown", family, (left.ordinal, right.ordinal), gap, policy.reuse_cooldown_frames))
    counts = tuple(sorted((family, len(values)) for family, values in families.items()))
    return AssetReusePlanV1(ReuseStatus.EVALUATED, tuple(sorted(violations, key=lambda item: item.violation_id)), context.context_id, context.context_hash, policy.policy_id, policy.policy_hash, counts)


def evaluate_asset_reuse(*, catalog: AssetCatalogV1, policy: AssetCatalogPolicyV1, context: AssetReuseContextV1, evidence_manifest_path: Path = TRUSTED_REPLAY_MANIFEST_PATH) -> AssetReusePlanV1:
    """Evaluate an already materialized local catalog without selecting an EDL asset."""
    if type(policy) is not AssetCatalogPolicyV1:
        _reject("ASSET_CATALOG_POLICY_INVALID")
    _validate_catalog(catalog, policy, catalog.project_id, ReplayAssetEvidenceRegistry.load(evidence_manifest_path))
    plan = _reuse(catalog, policy, context)
    ratio = _ratio(catalog, policy)
    return replace(plan, generic_stock_ratio_id=ratio.ratio_id, generic_stock_ratio_hash=ratio.ratio_hash)


def _mutation(input_catalog: AssetCatalogV1, output_catalog: AssetCatalogV1, package: AssetIngestionPackageV1, decision: DuplicateDecisionV1) -> AssetCatalogMutationV1:
    result_kind = "accepted" if decision.decision_kind is DuplicateKind.DISTINCT else "blocked_duplicate"
    accepted = next((record for record in output_catalog.records if record.asset_id not in {old.asset_id for old in input_catalog.records}), None)
    payload = {"input_catalog_id": input_catalog.catalog_id, "input_catalog_hash": input_catalog.catalog_hash, "candidate_package_id": package.package_id, "candidate_package_hash": package.package_hash, "duplicate_decision": decision, "result_kind": result_kind, "accepted_asset_record": accepted, "output_catalog_id": output_catalog.catalog_id, "output_catalog_hash": output_catalog.catalog_hash}
    digest = _hash({**payload, "duplicate_decision": decision.__dict__, "accepted_asset_record": None if accepted is None else accepted.__dict__})
    return AssetCatalogMutationV1("mut_" + digest[7:27], digest, **payload)


def canonical_catalog_mutation_json(mutation: AssetCatalogMutationV1) -> bytes:
    if type(mutation) is not AssetCatalogMutationV1:
        _reject("ASSET_MUTATION_INVALID")
    payload = {key: _json_value(value) for key, value in mutation.__dict__.items() if key not in {"mutation_id", "mutation_hash"}}
    if mutation.mutation_hash != _hash(payload) or mutation.mutation_id != "mut_" + mutation.mutation_hash[7:27]:
        _reject("ASSET_MUTATION_INVALID")
    return encode_canonical_json_bytes(_json_value(mutation))


def load_catalog_mutation_json(*, payload: bytes, package_payload: bytes, asset_bytes: bytes, input_catalog: AssetCatalogV1, output_catalog: AssetCatalogV1, policy: AssetCatalogPolicyV1, evidence_manifest_path: Path = TRUSTED_REPLAY_MANIFEST_PATH) -> AssetCatalogMutationV1:
    raw = _canonical_json_load(payload, "ASSET_MUTATION_INVALID")
    fields = tuple(AssetCatalogMutationV1.__dataclass_fields__)
    if type(raw) is not dict or set(raw) != set(fields):
        _reject("ASSET_MUTATION_INVALID")
    package = load_ingestion_package_json(payload=package_payload, asset_bytes=asset_bytes, policy=policy, evidence_manifest_path=evidence_manifest_path)
    registry = ReplayAssetEvidenceRegistry.load(evidence_manifest_path)
    _validate_catalog(input_catalog, policy, input_catalog.project_id, registry)
    _validate_catalog(output_catalog, policy, output_catalog.project_id, registry)
    try:
        decision_raw = raw["duplicate_decision"]
        decision = DuplicateDecisionV1(**{**decision_raw, "decision_kind": DuplicateKind(decision_raw["decision_kind"]), "matched_fingerprint_ids": tuple(decision_raw["matched_fingerprint_ids"]), "overlapping_selected_ranges": tuple(decision_raw["overlapping_selected_ranges"])})
    except (KeyError, TypeError, ValueError):
        _reject("ASSET_MUTATION_INVALID")
    accepted = next((record for record in output_catalog.records if raw["accepted_asset_record"] is not None and record.asset_id == raw["accepted_asset_record"].get("asset_id")), None)
    if (raw["accepted_asset_record"] is None) != (accepted is None) or (accepted is not None and raw["accepted_asset_record"] != _json_value(accepted)):
        _reject("ASSET_MUTATION_INVALID")
    try:
        mutation = AssetCatalogMutationV1(**{**raw, "duplicate_decision": decision, "accepted_asset_record": accepted})
    except TypeError:
        _reject("ASSET_MUTATION_INVALID")
    if canonical_catalog_mutation_json(mutation) != payload or (mutation.input_catalog_id, mutation.input_catalog_hash, mutation.candidate_package_id, mutation.candidate_package_hash, mutation.output_catalog_id, mutation.output_catalog_hash) != (input_catalog.catalog_id, input_catalog.catalog_hash, package.package_id, package.package_hash, output_catalog.catalog_id, output_catalog.catalog_hash) or mutation.duplicate_decision != decision:
        _reject("ASSET_MUTATION_INVALID")
    candidate, fingerprints = _candidate_from_package(package, policy)
    if decision != _decision(candidate, fingerprints, input_catalog, package):
        _reject("ASSET_MUTATION_INVALID")
    expected = _mutation(input_catalog, output_catalog, package, decision)
    if mutation != expected:
        _reject("ASSET_MUTATION_INVALID")
    return mutation


def _receipt(policy: AssetCatalogPolicyV1, materialization_handle: str, catalog: AssetCatalogV1, package: AssetIngestionPackageV1, decision: DuplicateDecisionV1, mutation: AssetCatalogMutationV1, ratio: GenericStockRatioV1, plan: AssetReusePlanV1, outcome_kind: str) -> CatalogReceiptV1:
    reuse_gate_status = "not_evaluated" if plan.status is ReuseStatus.NOT_EVALUATED else "passed"
    ingress_id = materialization_handle
    result_id = decision.decision_id if mutation.accepted_asset_record is None else mutation.accepted_asset_record.asset_id
    result_hash = decision.decision_hash if mutation.accepted_asset_record is None else mutation.accepted_asset_record.asset_hash
    nodes = (("policy_snapshot", policy.snapshot_id, policy.snapshot_hash), ("materialized_ingestion_input", ingress_id, package.source_hash), ("package", package.package_id, package.package_hash), ("decision", decision.decision_id, decision.decision_hash), ("accepted_or_blocked_result", result_id, result_hash), ("mutation", mutation.mutation_id, mutation.mutation_hash), ("catalog", catalog.catalog_id, catalog.catalog_hash), ("reuse_plan", plan.plan_id, plan.plan_hash), ("generic_stock_ratio", ratio.ratio_id, ratio.ratio_hash), ("receipt", "receipt_self", "sha256:receipt_self"))
    edges = (("policy_snapshot", policy.snapshot_id, "materialized_ingestion_input", ingress_id), ("materialized_ingestion_input", ingress_id, "package", package.package_id), ("package", package.package_id, "decision", decision.decision_id), ("decision", decision.decision_id, "accepted_or_blocked_result", result_id), ("accepted_or_blocked_result", result_id, "mutation", mutation.mutation_id), ("mutation", mutation.mutation_id, "catalog", catalog.catalog_id), ("catalog", catalog.catalog_id, "reuse_plan", plan.plan_id), ("reuse_plan", plan.plan_id, "generic_stock_ratio", ratio.ratio_id), ("generic_stock_ratio", ratio.ratio_id, "receipt", "receipt_self"))
    payload = {"status": "SUCCESS", "outcome_kind": outcome_kind, "reuse_gate_status": reuse_gate_status, "error_code": None, "dependency_nodes": [list(item) for item in nodes], "dependency_edges": [list(item) for item in edges]}
    digest = _hash(payload)
    receipt_id = "rcpt_" + digest[7:27]
    final_nodes = nodes[:-1] + (("receipt", receipt_id, digest),)
    final_edges = edges[:-1] + (("generic_stock_ratio", ratio.ratio_id, "receipt", receipt_id),)
    receipt = CatalogReceiptV1(receipt_id, digest, "SUCCESS", outcome_kind, reuse_gate_status, None, final_nodes, final_edges)
    _validate_receipt(receipt)
    return receipt


def _validate_receipt(receipt: CatalogReceiptV1) -> None:
    """Reject receipt graph drift, including the terminal self-reference."""
    if type(receipt) is not CatalogReceiptV1 or receipt.status not in {"SUCCESS", "FAILURE"}:
        _reject("RECEIPT_INVALID")
    if receipt.status == "FAILURE":
        if receipt.dependency_nodes or receipt.dependency_edges or receipt.error_code is None:
            _reject("RECEIPT_INVALID")
        payload = {"status": receipt.status, "outcome_kind": receipt.outcome_kind, "reuse_gate_status": receipt.reuse_gate_status, "error_code": receipt.error_code, "dependency_nodes": [], "dependency_edges": []}
    else:
        expected_kinds = ("policy_snapshot", "materialized_ingestion_input", "package", "decision", "accepted_or_blocked_result", "mutation", "catalog", "reuse_plan", "generic_stock_ratio", "receipt")
        if tuple(item[0] for item in receipt.dependency_nodes) != expected_kinds or len({(item[0], item[1]) for item in receipt.dependency_nodes}) != len(receipt.dependency_nodes) or any(len(item) != 3 or not _token(item[1]) or not _hash_value(item[2]) for item in receipt.dependency_nodes) or len(receipt.dependency_edges) != len(receipt.dependency_nodes) - 1:
            _reject("RECEIPT_INVALID")
        expected_edges = tuple((receipt.dependency_nodes[index][0], receipt.dependency_nodes[index][1], receipt.dependency_nodes[index + 1][0], receipt.dependency_nodes[index + 1][1]) for index in range(len(receipt.dependency_nodes) - 1))
        if receipt.dependency_edges != expected_edges or len(set(receipt.dependency_edges)) != len(receipt.dependency_edges) or receipt.dependency_nodes[-1] != ("receipt", receipt.receipt_id, receipt.receipt_hash):
            _reject("RECEIPT_INVALID")
        nodes = receipt.dependency_nodes[:-1] + (("receipt", "receipt_self", "sha256:receipt_self"),)
        edges = receipt.dependency_edges[:-1] + (("generic_stock_ratio", receipt.dependency_nodes[-2][1], "receipt", "receipt_self"),)
        payload = {"status": receipt.status, "outcome_kind": receipt.outcome_kind, "reuse_gate_status": receipt.reuse_gate_status, "error_code": receipt.error_code, "dependency_nodes": [list(item) for item in nodes], "dependency_edges": [list(item) for item in edges]}
    if receipt.receipt_hash != _hash(payload) or receipt.receipt_id != "rcpt_" + receipt.receipt_hash[7:27]:
        _reject("RECEIPT_INVALID")


def _compile_asset_catalog(*, input_value: AssetIngestionInputV1, materializations: AssetMaterializationRegistry, materialization_handle: str, evidence_registry: ReplayAssetEvidenceRegistry, policy: AssetCatalogPolicyV1, catalog: AssetCatalogV1, reuse_context: AssetReuseContextV1 | None = None, validate_existing_evidence: bool = False) -> CatalogCompilationV1:
    """Compile one local REPLAY candidate; duplicate/reuse violations never insert it."""
    if type(input_value) is not AssetIngestionInputV1 or type(materializations) is not AssetMaterializationRegistry or type(evidence_registry) is not ReplayAssetEvidenceRegistry or type(policy) is not AssetCatalogPolicyV1:
        _reject("ASSET_INPUT_INVALID")
    if not _token(input_value.project_id) or (input_value.sequence_id is not None and not _token(input_value.sequence_id)):
        _reject("ASSET_INPUT_INVALID")
    _validate_catalog(catalog, policy, input_value.project_id, evidence_registry if validate_existing_evidence else None)
    asset_bytes = materializations.resolve(materialization_handle)
    if asset_bytes != input_value.asset_bytes:
        _reject("MATERIALIZATION_UNAVAILABLE")
    source_hash = _bytes_hash(asset_bytes)
    descriptor = input_value.source_descriptor.data()
    semantic = input_value.semantic_declaration.data()
    probe, fingerprints = evidence_registry.resolve(source_hash)
    if probe.data()["source_hash"] != source_hash or fingerprints.data()["source_hash"] != source_hash or fingerprints.descriptor_hash != input_value.source_descriptor.descriptor_hash or fingerprints.same_source_key != input_value.source_descriptor.same_source_key:
        _reject("UNTRUSTED_REPLAY_EVIDENCE")
    if probe.media_type in {MediaType.IMAGE, MediaType.VIDEO} and not (fingerprints.perceptual_frame_hashes or fingerprints.local_feature_hashes):
        _reject("FINGERPRINT_EVIDENCE_INVALID")
    if probe.media_type in {MediaType.DOCUMENT, MediaType.AUDIO} and (fingerprints.perceptual_frame_hashes or fingerprints.local_feature_hashes):
        _reject("FINGERPRINT_EVIDENCE_INVALID")
    if any(token not in policy.allowed_avoid_context_tokens for token in semantic["avoid_contexts"]) or any(token not in policy.allowed_domain_role_tokens for token in semantic["domain_roles"]) or any(token not in policy.allowed_domain_sensitivity_tokens for token in semantic["domain_sensitivity_tags"]):
        _reject("POLICY_DENIED")
    audio = input_value.source_audio_eligibility.data(_snapshot_stub(policy))
    if any(token not in policy.source_audio_reason_tokens for token in audio["reason_tokens"]) or any(evidence_id != fingerprints.data()["evidence_id"] for evidence_id in audio["evidence_ids"]):
        _reject("POLICY_DENIED")
    ranges = _ranges(input_value, source_hash, probe)
    family = "fam_" + _hash({"policy": policy.policy_hash, "media_type": probe.media_type.value, "perceptual": list(fingerprints.perceptual_frame_hashes), "local": list(fingerprints.local_feature_hashes)})[7:27]
    media_facts = {key: probe.data()[key] for key in ("duration_ms", "width", "height", "fps_numerator", "fps_denominator", "codec", "has_audio")}
    record_payload = {"source_hash": source_hash, "source_byte_length": len(asset_bytes), "media_type": probe.media_type.value, "media_facts": media_facts, "source_descriptor": descriptor, "fingerprint_evidence": fingerprints.data(), "visual_family_id": family, "subjects": semantic["subjects"], "actions": semantic["actions"], "setting": semantic["setting"], "mood": semantic["mood"], "semantic_tags": semantic["semantic_tags"], "avoid_contexts": semantic["avoid_contexts"], "domain_roles": semantic["domain_roles"], "domain_sensitivity_tags": semantic["domain_sensitivity_tags"], "selected_ranges": ranges, "source_audio_eligibility": audio, "duplicate_of_asset_id": None, "duplicate_of_asset_hash": None}
    asset_hash = _hash(record_payload)
    candidate = AssetRecordV1("ast_" + asset_hash[7:27], asset_hash, source_hash, len(asset_bytes), probe.media_type, media_facts, descriptor, fingerprints.data(), family, tuple(semantic["subjects"]), tuple(semantic["actions"]), semantic["setting"], semantic["mood"], tuple(semantic["semantic_tags"]), tuple(semantic["avoid_contexts"]), tuple(semantic["domain_roles"]), tuple(semantic["domain_sensitivity_tags"]), ranges, audio, None, None)
    package_payload = {"schema_version": ASSET_CATALOG_SCHEMA_V1, "project_id": input_value.project_id, "sequence_id": input_value.sequence_id, "policy_snapshot_id": policy.snapshot_id, "policy_snapshot_hash": policy.snapshot_hash, "source_hash": source_hash, "source_byte_length": len(asset_bytes), "source_descriptor": descriptor, "media_probe_evidence": probe.data(), "fingerprint_evidence": fingerprints.data(), "semantic_declaration": semantic, "selected_ranges": list(ranges), "source_audio_eligibility": audio}
    package_hash = _hash(package_payload)
    package = AssetIngestionPackageV1(ASSET_CATALOG_SCHEMA_V1, "pkg_" + package_hash[7:27], package_hash, input_value.project_id, input_value.sequence_id, policy.snapshot_id, policy.snapshot_hash, source_hash, len(asset_bytes), descriptor, probe.data(), fingerprints.data(), semantic, ranges, audio)
    decision = _decision(candidate, fingerprints, catalog, package)
    if decision.decision_kind is not DuplicateKind.DISTINCT:
        blocked = tuple(sorted(catalog.blocked_decisions + (decision,), key=lambda value: value.decision_id))
        digest = _catalog_hash(catalog.project_id, policy, catalog.records, blocked)
        output = AssetCatalogV1("cat_" + digest[7:27], digest, catalog.project_id, policy.snapshot_id, policy.snapshot_hash, catalog.records, blocked)
        ratio = _ratio(output, policy); plan = replace(AssetReusePlanV1(ReuseStatus.NOT_EVALUATED, (), policy_id=policy.policy_id, policy_hash=policy.policy_hash), generic_stock_ratio_id=ratio.ratio_id, generic_stock_ratio_hash=ratio.ratio_hash); mutation = _mutation(catalog, output, package, decision)
        return CatalogCompilationV1(package, decision, output, ratio, plan, "ingestion_only", mutation, _receipt(policy, materialization_handle, output, package, decision, mutation, ratio, plan, "ingestion_only"))
    provisional_records = tuple(sorted(catalog.records + (candidate,), key=lambda value: value.asset_id))
    digest = _catalog_hash(catalog.project_id, policy, provisional_records, catalog.blocked_decisions)
    provisional = AssetCatalogV1("cat_" + digest[7:27], digest, catalog.project_id, policy.snapshot_id, policy.snapshot_hash, provisional_records, catalog.blocked_decisions)
    plan = _reuse(provisional, policy, reuse_context)
    if plan.status is ReuseStatus.EVALUATED and plan.violations:
        _reject("REUSE_DENIED")
    outcome = "reuse_gate_evaluated" if plan.status is ReuseStatus.EVALUATED else "ingestion_only"
    ratio = _ratio(provisional, policy); plan = replace(plan, generic_stock_ratio_id=ratio.ratio_id, generic_stock_ratio_hash=ratio.ratio_hash); mutation = _mutation(catalog, provisional, package, decision)
    return CatalogCompilationV1(package, decision, provisional, ratio, plan, outcome, mutation, _receipt(policy, materialization_handle, provisional, package, decision, mutation, ratio, plan, outcome))


def _failure_receipt(error_code: str) -> CatalogFailureV1:
    mapping = {"MATERIALIZATION_UNAVAILABLE": "materialization_unavailable", "UNTRUSTED_REPLAY_EVIDENCE": "untrusted_replay_evidence", "POLICY_DENIED": "policy_denied", "REUSE_DENIED": "reuse_denied"}
    code = mapping.get(error_code, "invalid_input")
    outcome, gate = ("reuse_gate_evaluated", "denied") if code == "reuse_denied" else ("ingestion_only", "not_evaluated")
    payload = {"status": "FAILURE", "outcome_kind": outcome, "reuse_gate_status": gate, "error_code": code, "dependency_nodes": [], "dependency_edges": []}
    digest = _hash(payload)
    receipt = CatalogReceiptV1("rcpt_" + digest[7:27], digest, "FAILURE", outcome, gate, code, (), ())
    return CatalogFailureV1(code, receipt)


def compile_asset_catalog(*, input_value: AssetIngestionInputV1, policy: AssetCatalogPolicyV1, catalog: AssetCatalogV1, reuse_context: AssetReuseContextV1 | None = None, evidence_manifest_path: Path = TRUSTED_REPLAY_MANIFEST_PATH) -> CatalogCompilationV1 | CatalogFailureV1:
    """Public Phase 8 ingress: evidence can originate only from pinned REPLAY data."""
    try:
        registry = ReplayAssetEvidenceRegistry.load(evidence_manifest_path)
        materializations = AssetMaterializationRegistry()
        materialization_handle = materializations.register(input_value)
        return _compile_asset_catalog(input_value=input_value, materializations=materializations, materialization_handle=materialization_handle, evidence_registry=registry, policy=policy, catalog=catalog, reuse_context=reuse_context, validate_existing_evidence=True)
    except AssetCatalogError as error:
        return _failure_receipt(error.code)


def _snapshot_stub(policy: AssetCatalogPolicyV1) -> DomainPolicySnapshot:
    """Eligibility needs only snapshot identity; compiler already authenticated policy."""
    return DomainPolicySnapshot("3.0.0", policy.snapshot_id, "asset-policy", "0", "asset-policy", "sha256:" + "0" * 64, {}, policy.snapshot_hash, True, "1970-01-01T00:00:00Z", 1)
