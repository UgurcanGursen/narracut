"""Canonical, local Phase 15 run evidence and fail-closed quality decisions."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Mapping

from engine.contracts._canonical_json import encode_canonical_json_bytes
from engine.lifecycle import ArtifactRegistryRecord, registry_snapshot
from engine.rendering.receipt import load_render_receipt


OBSERVATION_V1 = "PHASE15-RUN-OBSERVATION-V1"
REFERENCE_V1 = "PHASE15-EVIDENCE-REFERENCE-V1"
DECISION_V1 = "PHASE15-QUALITY-GATE-DECISION-V1"
_HASH = re.compile(r"^sha256:[0-9a-f]{64}$")
_RUN = re.compile(r"^[a-z][a-z0-9_]{2,80}$")
_TOKEN = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
_UTC = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
_UNSAFE = re.compile(r"(?i)(authorization|cookie|api[_-]?key|token|secret|credential|password)")

_EVENTS: dict[tuple[str, str], frozenset[str]] = {
    ("render", "attempt_finished"): frozenset({"SUCCEEDED", "FAILED", "CANCELLED"}),
    ("artifact", "registry_verified"): frozenset({"SUCCEEDED", "FAILED"}),
    ("storage", "admission_decided"): frozenset({"ADMITTED", "BLOCKED", "NOT_APPLICABLE"}),
    ("domain", "contract_resolved"): frozenset({"SUCCEEDED", "FAILED"}),
    ("transport", "mode_declared"): frozenset({"REPLAY", "MANUAL_UI", "DISABLED", "UNSUPPORTED"}),
    ("quality_gate", "check_evaluated"): frozenset({"PASSED", "WARNING", "FAILED", "NOT_READY", "UNSUPPORTED"}),
}
_CHECKS = frozenset({"render_path", "artifact_lifecycle", "storage_pressure", "domain_contract", "source_outcome", "failure_provenance"})
_KIND_BY_CATEGORY = {"render": "render_receipt", "artifact": "artifact_registry", "storage": "storage_admission", "domain": "domain_snapshot"}
_KIND_BY_CHECK = {**_KIND_BY_CATEGORY, "render_path": "render_receipt", "artifact_lifecycle": "artifact_registry", "storage_pressure": "storage_admission", "domain_contract": "domain_snapshot", "source_outcome": "source_capture", "failure_provenance": "failure_code"}
_METRICS = frozenset({"run_elapsed_ms", "sequence_render_ms", "cache_hit_count", "cache_miss_count", "artifact_count", "workspace_size_bytes", "cache_size_bytes", "orphan_artifact_count", "dedup_saved_bytes", "failure_count", "transport_outcome_count"})


def _fail(code: str) -> None:
    raise ValueError(code)


def _sha(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _valid_hash(value: object) -> bool:
    return type(value) is str and _HASH.fullmatch(value) is not None


def _safe_text(value: object) -> bool:
    if type(value) is not str or len(value) > 160 or _UNSAFE.search(value) is not None:
        return False
    return not value.startswith(("/", "\\", "~/", "~\\")) and re.match(r"^[A-Za-z]:[\\/]", value) is None


def _strict_json(source: bytes, code: str) -> dict[str, Any]:
    if type(source) is not bytes or source.startswith(b"\xef\xbb\xbf"):
        _fail(code)
    try:
        value = json.loads(source)
    except (UnicodeDecodeError, json.JSONDecodeError):
        _fail(code)
    if type(value) is not dict or encode_canonical_json_bytes(value) != source:
        _fail(code)
    return value


@dataclass(frozen=True)
class EvidenceReference:
    schema_version: str
    kind: str
    reference_id: str
    reference_hash: str
    run_id: str

    def data(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class RunObservation:
    schema_version: str
    run_id: str
    ordinal: int
    timestamp_utc: str
    category: str
    event: str
    status: str
    provenance: dict[str, object]
    evidence_references: tuple[EvidenceReference, ...]
    metrics: dict[str, int]
    check_id: str | None
    policy_hash: str | None
    public_code: str | None

    def data(self) -> dict[str, object]:
        return {"schema_version": self.schema_version, "run_id": self.run_id,
                "ordinal": self.ordinal, "timestamp_utc": self.timestamp_utc,
                "category": self.category, "event": self.event, "status": self.status,
                "provenance": self.provenance,
                "evidence_references": [item.data() for item in self.evidence_references],
                "metrics": self.metrics, "check_id": self.check_id,
                "policy_hash": self.policy_hash, "public_code": self.public_code}


@dataclass(frozen=True)
class QualityGateDecision:
    schema_version: str
    run_id: str
    decision: str
    primary_code: str | None
    observations_hash: str
    checked: tuple[str, ...]
    missing: tuple[str, ...]
    failed: tuple[str, ...]
    warnings: tuple[str, ...]

    def data(self) -> dict[str, object]:
        return {"schema_version": self.schema_version, "run_id": self.run_id,
                "decision": self.decision, "primary_code": self.primary_code,
                "observations_hash": self.observations_hash, "checked": list(self.checked),
                "missing": list(self.missing), "failed": list(self.failed),
                "warnings": list(self.warnings)}


def _reference(value: Mapping[str, object], *, run_id: str) -> EvidenceReference:
    if set(value) != {"schema_version", "kind", "reference_id", "reference_hash", "run_id"}:
        _fail("EVIDENCE_REFERENCE_FIELDS_INVALID")
    item = EvidenceReference(**value)  # type: ignore[arg-type]
    if (item.schema_version != REFERENCE_V1 or item.kind not in {"render_receipt", "artifact_registry", "storage_admission", "domain_snapshot", "source_capture", "failure_code"}
            or not _safe_text(item.reference_id) or not _valid_hash(item.reference_hash)
            or item.run_id != run_id):
        _fail("EVIDENCE_REFERENCE_INVALID")
    return item


def render_receipt_reference(*, run_id: str, source: bytes) -> EvidenceReference:
    if not _RUN.fullmatch(run_id): _fail("RUN_ID_INVALID")
    receipt = load_render_receipt(source)
    return EvidenceReference(REFERENCE_V1, "render_receipt", receipt.receipt_id, receipt.receipt_hash, run_id)


def artifact_registry_reference(*, run_id: str, records: tuple[ArtifactRegistryRecord, ...]) -> EvidenceReference:
    if not _RUN.fullmatch(run_id): _fail("RUN_ID_INVALID")
    return EvidenceReference(REFERENCE_V1, "artifact_registry", "registry_snapshot", registry_snapshot(records), run_id)


def storage_admission_reference(*, run_id: str, storage_scope_id: str, policy_hash: str, status: str) -> EvidenceReference:
    if not _RUN.fullmatch(run_id) or not _TOKEN.fullmatch(storage_scope_id) or not _valid_hash(policy_hash) or status not in {"ADMITTED", "BLOCKED_HARD_QUOTA", "BLOCKED_MIN_FREE_DISK", "NOT_APPLICABLE"}:
        _fail("STORAGE_ADMISSION_REFERENCE_INVALID")
    raw = encode_canonical_json_bytes({"storage_scope_id": storage_scope_id, "policy_hash": policy_hash, "status": status})
    return EvidenceReference(REFERENCE_V1, "storage_admission", "storage_" + _sha(raw)[7:39], _sha(raw), run_id)


def domain_snapshot_reference(*, run_id: str, snapshot_id: str, snapshot_hash: str) -> EvidenceReference:
    if not _RUN.fullmatch(run_id) or not _safe_text(snapshot_id) or not _valid_hash(snapshot_hash):
        _fail("DOMAIN_SNAPSHOT_REFERENCE_INVALID")
    return EvidenceReference(REFERENCE_V1, "domain_snapshot", snapshot_id, snapshot_hash, run_id)


def failure_code_reference(*, run_id: str, code: str) -> EvidenceReference:
    if not _RUN.fullmatch(run_id) or not _TOKEN.fullmatch(code): _fail("FAILURE_CODE_REFERENCE_INVALID")
    raw = encode_canonical_json_bytes({"failure_code": code})
    return EvidenceReference(REFERENCE_V1, "failure_code", code, _sha(raw), run_id)


def build_observation(*, run_id: str, ordinal: int, timestamp_utc: str, category: str, event: str,
                      status: str, producer: str, input_hashes: tuple[str, ...] = (),
                      artifact_ids: tuple[str, ...] = (), evidence_references: tuple[EvidenceReference, ...] = (),
                      metrics: Mapping[str, int] | None = None, check_id: str | None = None,
                      policy_hash: str | None = None, public_code: str | None = None) -> RunObservation:
    if not _RUN.fullmatch(run_id) or type(ordinal) is not int or ordinal < 1 or not _UTC.fullmatch(timestamp_utc):
        _fail("OBSERVATION_IDENTITY_INVALID")
    allowed = _EVENTS.get((category, event))
    if allowed is None or status not in allowed or not _safe_text(producer): _fail("OBSERVATION_TRANSITION_INVALID")
    if tuple(sorted(input_hashes)) != input_hashes or len(set(input_hashes)) != len(input_hashes) or any(not _valid_hash(item) for item in input_hashes): _fail("OBSERVATION_PROVENANCE_INVALID")
    if tuple(sorted(artifact_ids)) != artifact_ids or len(set(artifact_ids)) != len(artifact_ids) or any(not _safe_text(item) for item in artifact_ids): _fail("OBSERVATION_PROVENANCE_INVALID")
    try:
        refs = tuple(_reference(item.data() if type(item) is EvidenceReference else item, run_id=run_id) for item in evidence_references)
    except (AttributeError, TypeError):
        _fail("EVIDENCE_REFERENCE_FIELDS_INVALID")
    if tuple(sorted((item.kind, item.reference_id) for item in refs)) != tuple((item.kind, item.reference_id) for item in refs) or len({(item.kind, item.reference_id) for item in refs}) != len(refs): _fail("EVIDENCE_REFERENCE_ORDER_INVALID")
    values = dict(metrics or {})
    if set(values) - _METRICS or any(type(value) is not int or value < 0 for value in values.values()): _fail("OBSERVATION_METRIC_INVALID")
    expected_kind = _KIND_BY_CATEGORY.get(category)
    if expected_kind and expected_kind not in {item.kind for item in refs}: _fail("EVIDENCE_REFERENCE_MISSING")
    if category == "quality_gate":
        if check_id not in _CHECKS or not _valid_hash(policy_hash) or (status != "PASSED" and not _TOKEN.fullmatch(public_code or "")):
            _fail("QUALITY_CHECK_INVALID")
        if _KIND_BY_CHECK[check_id] not in {item.kind for item in refs}: _fail("EVIDENCE_REFERENCE_MISSING")
    elif any(value is not None for value in (check_id, policy_hash)):
        _fail("OBSERVATION_FIELDS_INVALID")
    elif status in {"FAILED", "CANCELLED"}:
        if not _TOKEN.fullmatch(public_code or ""): _fail("FAILURE_PROVENANCE_MISSING")
    elif public_code is not None:
        _fail("OBSERVATION_FIELDS_INVALID")
    return RunObservation(OBSERVATION_V1, run_id, ordinal, timestamp_utc, category, event, status,
                          {"producer": producer, "input_hashes": list(input_hashes), "artifact_ids": list(artifact_ids)},
                          refs, {key: values[key] for key in sorted(values)}, check_id, policy_hash, public_code)


def serialize_observation(value: RunObservation) -> bytes:
    if type(value) is not RunObservation: _fail("OBSERVATION_INVALID")
    rebuilt = build_observation(run_id=value.run_id, ordinal=value.ordinal, timestamp_utc=value.timestamp_utc,
        category=value.category, event=value.event, status=value.status, producer=value.provenance.get("producer", ""),
        input_hashes=tuple(value.provenance.get("input_hashes", ())), artifact_ids=tuple(value.provenance.get("artifact_ids", ())),
        evidence_references=value.evidence_references, metrics=value.metrics, check_id=value.check_id,
        policy_hash=value.policy_hash, public_code=value.public_code)
    if rebuilt != value: _fail("OBSERVATION_INVALID")
    return encode_canonical_json_bytes(value.data())


def load_observation(source: bytes) -> RunObservation:
    raw = _strict_json(source, "OBSERVATION_BYTES_INVALID")
    required = {"schema_version", "run_id", "ordinal", "timestamp_utc", "category", "event", "status", "provenance", "evidence_references", "metrics", "check_id", "policy_hash", "public_code"}
    if set(raw) != required or raw.get("schema_version") != OBSERVATION_V1 or type(raw["provenance"]) is not dict or set(raw["provenance"]) != {"producer", "input_hashes", "artifact_ids"} or type(raw["evidence_references"]) is not list or type(raw["metrics"]) is not dict:
        _fail("OBSERVATION_FIELDS_INVALID")
    try:
        result = build_observation(run_id=raw["run_id"], ordinal=raw["ordinal"], timestamp_utc=raw["timestamp_utc"], category=raw["category"], event=raw["event"], status=raw["status"], producer=raw["provenance"]["producer"], input_hashes=tuple(raw["provenance"]["input_hashes"]), artifact_ids=tuple(raw["provenance"]["artifact_ids"]), evidence_references=tuple(EvidenceReference(**item) for item in raw["evidence_references"]), metrics=raw["metrics"], check_id=raw["check_id"], policy_hash=raw["policy_hash"], public_code=raw["public_code"])
    except (TypeError, KeyError): _fail("OBSERVATION_FIELDS_INVALID")
    if serialize_observation(result) != source: _fail("OBSERVATION_BYTES_INVALID")
    return result


def serialize_jsonl(observations: tuple[RunObservation, ...]) -> bytes:
    if not observations: _fail("OBSERVATION_LOG_EMPTY")
    run_ids = {item.run_id for item in observations}
    if len(run_ids) != 1 or tuple(item.ordinal for item in observations) != tuple(range(1, len(observations) + 1)):
        _fail("OBSERVATION_LOG_CONTINUITY_INVALID")
    return b"\n".join(serialize_observation(item) for item in observations) + b"\n"


def load_jsonl(source: bytes) -> tuple[RunObservation, ...]:
    if type(source) is not bytes or not source.endswith(b"\n") or not source.strip(): _fail("OBSERVATION_LOG_BYTES_INVALID")
    rows = tuple(load_observation(line) for line in source.splitlines())
    if serialize_jsonl(rows) != source: _fail("OBSERVATION_LOG_BYTES_INVALID")
    return rows


def project_metrics(source: bytes) -> dict[str, tuple[int, ...]]:
    rows = load_jsonl(source); result: dict[str, list[int]] = {}
    for row in rows:
        for key, value in row.metrics.items(): result.setdefault(key, []).append(value)
    return {key: tuple(result[key]) for key in sorted(result)}


def evaluate_quality_gate(*, source: bytes, required_checks: Mapping[str, str]) -> QualityGateDecision:
    rows = load_jsonl(source); run_id = rows[0].run_id
    if set(required_checks) - _CHECKS or not required_checks or any(not _valid_hash(value) for value in required_checks.values()): _fail("QUALITY_GATE_POLICY_INVALID")
    producer_failures = tuple(row for row in rows if row.status in {"FAILED", "CANCELLED"} and row.category != "quality_gate")
    checks = [row for row in rows if row.category == "quality_gate"]
    by_check = {row.check_id: row for row in checks}
    if len(by_check) != len(checks): _fail("QUALITY_CHECK_DUPLICATE")
    missing = tuple(sorted(check for check in required_checks if check not in by_check or by_check[check].status in {"NOT_READY", "UNSUPPORTED"}))
    failed = tuple(sorted(check for check in required_checks if check in by_check and by_check[check].status == "FAILED"))
    warnings = tuple(sorted(check for check in required_checks if check in by_check and by_check[check].status == "WARNING"))
    mismatch = tuple(sorted(check for check, row in by_check.items() if check not in required_checks or row.policy_hash != required_checks.get(check)))
    failure_row = by_check.get("failure_provenance")
    producer_codes = tuple(row.public_code for row in producer_failures)
    failure_ref_ids = {ref.reference_id for ref in failure_row.evidence_references if ref.kind == "failure_code"} if failure_row else set()
    if producer_failures and (failure_row is None or failure_row.status != "PASSED" or not set(producer_codes) <= failure_ref_ids):
        return QualityGateDecision(DECISION_V1, run_id, "FAIL", "FAILURE_PROVENANCE_MISSING", _sha(source), tuple(sorted(required_checks)), missing, failed, warnings)
    if mismatch: return QualityGateDecision(DECISION_V1, run_id, "FAIL", "QUALITY_POLICY_MISMATCH", _sha(source), tuple(sorted(required_checks)), missing, failed, warnings)
    if producer_failures: return QualityGateDecision(DECISION_V1, run_id, "FAIL", producer_codes[0], _sha(source), tuple(sorted(required_checks)), missing, failed, warnings)
    if failed: return QualityGateDecision(DECISION_V1, run_id, "FAIL", by_check[failed[0]].public_code, _sha(source), tuple(sorted(required_checks)), missing, failed, warnings)
    if missing: return QualityGateDecision(DECISION_V1, run_id, "NOT_READY", by_check[missing[0]].public_code if missing[0] in by_check else "QUALITY_EVIDENCE_MISSING", _sha(source), tuple(sorted(required_checks)), missing, failed, warnings)
    if warnings: return QualityGateDecision(DECISION_V1, run_id, "WARNING", by_check[warnings[0]].public_code, _sha(source), tuple(sorted(required_checks)), missing, failed, warnings)
    return QualityGateDecision(DECISION_V1, run_id, "PASS", None, _sha(source), tuple(sorted(required_checks)), (), (), ())


def serialize_quality_gate_decision(value: QualityGateDecision) -> bytes:
    _validate_quality_decision(value)
    return encode_canonical_json_bytes(value.data())


def _validate_quality_decision(value: QualityGateDecision) -> None:
    groups = (value.checked, value.missing, value.failed, value.warnings)
    if (type(value) is not QualityGateDecision or value.schema_version != DECISION_V1 or not _RUN.fullmatch(value.run_id)
            or value.decision not in {"PASS", "WARNING", "FAIL", "NOT_READY"} or not _valid_hash(value.observations_hash)
            or any(type(group) is not tuple or any(type(item) is not str for item in group)
                   or tuple(sorted(group)) != group or len(set(group)) != len(group)
                   or any(item not in _CHECKS for item in group) for group in groups)
            or set(value.missing) - set(value.checked) or set(value.failed) - set(value.checked)
            or set(value.warnings) - set(value.checked)):
        _fail("QUALITY_DECISION_INVALID")
    if value.decision == "PASS":
        if value.primary_code is not None or any(groups[1:]): _fail("QUALITY_DECISION_INVALID")
    elif type(value.primary_code) is not str or not _TOKEN.fullmatch(value.primary_code):
        _fail("QUALITY_DECISION_INVALID")


def load_quality_gate_decision(source: bytes) -> QualityGateDecision:
    raw = _strict_json(source, "QUALITY_DECISION_BYTES_INVALID")
    required = {"schema_version", "run_id", "decision", "primary_code", "observations_hash", "checked", "missing", "failed", "warnings"}
    if set(raw) != required or raw.get("schema_version") != DECISION_V1 or any(type(raw[key]) is not list for key in ("checked", "missing", "failed", "warnings")):
        _fail("QUALITY_DECISION_FIELDS_INVALID")
    try:
        result = QualityGateDecision(raw["schema_version"], raw["run_id"], raw["decision"], raw["primary_code"], raw["observations_hash"], tuple(raw["checked"]), tuple(raw["missing"]), tuple(raw["failed"]), tuple(raw["warnings"]))
    except (TypeError, KeyError): _fail("QUALITY_DECISION_FIELDS_INVALID")
    _validate_quality_decision(result)
    if serialize_quality_gate_decision(result) != source: _fail("QUALITY_DECISION_BYTES_INVALID")
    return result
