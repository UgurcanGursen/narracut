from __future__ import annotations

import copy
import dataclasses
import gc
import hashlib
import json
import pickle
import weakref
from dataclasses import FrozenInstanceError, replace
from enum import Enum

import pytest

import engine.contracts as contracts
import engine.contracts.alignment_execution as execution_contracts
from engine.contracts import (
    ADAPTER_EXECUTION_HASH_V1,
    ADAPTER_EXECUTION_V1,
    CONFIDENCE_AVAILABILITY_EVIDENCE_V1,
    PAID_FALLBACK_AUTHORIZATION_EVIDENCE_V1,
    REPLAY_EVIDENCE_V1,
    AdapterExecution,
    AdapterExecutionContractError,
    AdapterExecutionMode,
    AdapterExecutionRejectionReason,
    AdapterExecutionStatus,
    ConfidenceAvailability,
    ConfidenceAvailabilityEvidence,
    PaidFallbackAuthorizationDecision,
    PaidFallbackAuthorizationEvidence,
    PaidFallbackAuthorizationSource,
    ReplayEvidence,
    load_adapter_execution,
    materialize_adapter_execution,
    serialize_adapter_execution,
)
from tests.test_alignment_request import (
    FX_ARQ_01_ENVELOPE_BYTES,
    FX_ARQ_01_HASH,
    FX_ARQ_01_ID,
    _fixture_identity_digest,
    _materialize as materialize_request,
    _raw_request,
)


FX_AEX_01_PROJECTION_BYTES = (
    b'{"adapter_id":"adapter_fxarq","adapter_version":"1.0.0",'
    b'"alignment_request_hash":"bfd2a97af22b1f105c2ebe9356ce2fe684b0add89be14fea09e6b21cfbe54e51",'
    b'"alignment_request_id":"arq_bfd2a97af22b1f105c2ebe9356ce2fe6",'
    b'"confidence_availability_evidence":{"availability":"AVAILABLE",'
    b'"schema_version":"CONFIDENCE-AVAILABILITY-EVIDENCE-V1"},'
    b'"hash_scope_version":"ADAPTER-EXECUTION-HASH-V1","mode":"LOCAL",'
    b'"paid_fallback_authorization_evidence":null,"replay_evidence":null,'
    b'"schema_version":"ADAPTER-EXECUTION-V1","status":"SUCCEEDED"}'
)
FX_AEX_01_HASH = "183e432fedb7c26e2339909ed805cd49eddfafd47eb217ed3e393c5cb6462aa7"
FX_AEX_01_ID = "aex_183e432fedb7c26e2339909ed805cd49"
FX_AEX_01_ENVELOPE_SHA256 = "f874ae7027af4eb1e251bdced9933d11da112d3d56c403f1a32b4627512d4c58"

SLICE5_PUBLIC_EXPORTS = frozenset({
    "ADAPTER_EXECUTION_V1", "ADAPTER_EXECUTION_HASH_V1",
    "PAID_FALLBACK_AUTHORIZATION_EVIDENCE_V1", "REPLAY_EVIDENCE_V1",
    "CONFIDENCE_AVAILABILITY_EVIDENCE_V1", "AdapterExecutionMode",
    "AdapterExecutionStatus", "PaidFallbackAuthorizationSource",
    "PaidFallbackAuthorizationDecision", "ConfidenceAvailability",
    "PaidFallbackAuthorizationEvidence", "ReplayEvidence",
    "ConfidenceAvailabilityEvidence", "AdapterExecution",
    "AdapterExecutionRejectionReason", "AdapterExecutionContractError",
    "materialize_adapter_execution", "load_adapter_execution",
    "serialize_adapter_execution",
})


class CustomString(str):
    pass


class ArbitraryEnum(Enum):
    LOCAL = "LOCAL"


def _canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()


def _rehash(value: dict) -> dict:
    projection = {key: copy.deepcopy(item) for key, item in value.items()
                  if key not in {"adapter_execution_id", "adapter_execution_hash"}}
    digest = hashlib.sha256(_canonical(projection)).hexdigest()
    value["adapter_execution_hash"] = digest
    value["adapter_execution_id"] = "aex_" + digest[:32]
    return value


def _request(mode: str = "LOCAL", *, confidence: str = "SUPPORTED"):
    transcript = None if mode == "FREE_API" else ...
    raw, dependencies = _raw_request(mode=mode, transcript_reference=transcript)
    if confidence != "SUPPORTED":
        raw["adapter_capability"]["confidence_output"] = confidence
        digest = _fixture_identity_digest(raw)
        raw["alignment_request_hash"] = digest
        raw["alignment_request_id"] = "arq_" + digest[:32]
    return materialize_request(raw, dependencies=dependencies)


def _raw_execution(request=None, *, mode="LOCAL", status="SUCCEEDED",
                   paid=None, replay=None, confidence=...):
    request = request or _request("FREE_API" if mode == "PAID_API" else mode)
    if confidence is ...:
        confidence = None if status == "BLOCKED" else {
            "schema_version": CONFIDENCE_AVAILABILITY_EVIDENCE_V1,
            "availability": "NOT_APPLICABLE" if status == "FAILED" else (
                "AVAILABLE" if request.adapter_capability.confidence_output == "SUPPORTED"
                else "NOT_APPLICABLE"
            ),
        }
    if paid is None and mode == "PAID_API":
        paid = {
            "schema_version": PAID_FALLBACK_AUTHORIZATION_EVIDENCE_V1,
            "authorization_id": "pfa_test_001",
            "source": "USER_EXPLICIT",
            "decision": "DENIED" if status == "BLOCKED" else "APPROVED",
            "alignment_request_id": request.alignment_request_id,
            "alignment_request_hash": request.alignment_request_hash,
        }
    value = {
        "schema_version": ADAPTER_EXECUTION_V1,
        "hash_scope_version": ADAPTER_EXECUTION_HASH_V1,
        "adapter_execution_id": "aex_" + "0" * 32,
        "adapter_execution_hash": "0" * 64,
        "alignment_request_id": request.alignment_request_id,
        "alignment_request_hash": request.alignment_request_hash,
        "adapter_id": request.adapter_capability.adapter_id,
        "adapter_version": request.adapter_capability.adapter_version,
        "mode": mode,
        "status": status,
        "paid_fallback_authorization_evidence": paid,
        "replay_evidence": replay,
        "confidence_availability_evidence": confidence,
    }
    return _rehash(value), request


def _materialize(value=None, request=None, **kwargs):
    if value is None:
        value, request = _raw_execution(request)
    return materialize_adapter_execution(value, alignment_request=request, **kwargs)


def _replay_case(*, status="SUCCEEDED"):
    source_request = _request("LOCAL")
    source_raw, _ = _raw_execution(source_request)
    source_execution = _materialize(source_raw, source_request)
    current_request = _request("REPLAY")
    replay = {
        "schema_version": REPLAY_EVIDENCE_V1,
        "source_adapter_execution_id": source_execution.adapter_execution_id,
        "source_adapter_execution_hash": source_execution.adapter_execution_hash,
        "source_alignment_request_id": source_request.alignment_request_id,
        "source_alignment_request_hash": source_request.alignment_request_hash,
    }
    value, _ = _raw_execution(current_request, mode="REPLAY", status=status, replay=replay)
    return value, current_request, source_request, source_execution


def _assert_error(exc, reason, pointer, issue=None):
    error = exc.value
    assert type(error) is AdapterExecutionContractError
    assert error.reason is reason
    assert error.pointer == pointer
    assert error.issue_code == issue
    assert str(error) == f"Adapter execution rejected: {reason.value}"
    assert not hasattr(error, "adapter_execution_id")
    assert not hasattr(error, "adapter_execution_hash")
    assert not hasattr(error, "canonical_bytes")


def test_golden_projection_envelope_identity_and_loader() -> None:
    value, request = _raw_execution()
    assert _canonical({key: item for key, item in value.items()
                       if key not in {"adapter_execution_id", "adapter_execution_hash"}}) == FX_AEX_01_PROJECTION_BYTES
    assert len(FX_AEX_01_PROJECTION_BYTES) == 521
    assert hashlib.sha256(FX_AEX_01_PROJECTION_BYTES).hexdigest() == FX_AEX_01_HASH
    assert value["adapter_execution_hash"] == FX_AEX_01_HASH
    assert value["adapter_execution_id"] == FX_AEX_01_ID
    execution = _materialize(value, request)
    envelope = serialize_adapter_execution(execution)
    assert len(envelope) == 675
    assert hashlib.sha256(envelope).hexdigest() == FX_AEX_01_ENVELOPE_SHA256
    loaded = load_adapter_execution(envelope, alignment_request=request)
    assert loaded == execution and loaded is not execution
    assert serialize_adapter_execution(loaded) == envelope


def test_public_constants_enums_models_and_exports_are_exact() -> None:
    assert ADAPTER_EXECUTION_V1 == "ADAPTER-EXECUTION-V1"
    assert ADAPTER_EXECUTION_HASH_V1 == "ADAPTER-EXECUTION-HASH-V1"
    expectations = {
        AdapterExecutionMode: ["LOCAL", "REPLAY", "FREE_API", "PAID_API", "MANUAL_UI"],
        AdapterExecutionStatus: ["SUCCEEDED", "FAILED", "BLOCKED"],
        PaidFallbackAuthorizationSource: ["USER_EXPLICIT"],
        PaidFallbackAuthorizationDecision: ["APPROVED", "DENIED"],
        ConfidenceAvailability: ["AVAILABLE", "UNAVAILABLE", "NOT_APPLICABLE"],
    }
    for enum_type, values in expectations.items():
        assert issubclass(enum_type, str) and issubclass(enum_type, Enum)
        assert [member.name for member in enum_type] == values
        assert [member.value for member in enum_type] == values
        assert len(enum_type.__members__) == len(values)
    assert set(contracts.__all__) >= SLICE5_PUBLIC_EXPORTS
    for name in SLICE5_PUBLIC_EXPORTS:
        assert getattr(contracts, name) is getattr(execution_contracts, name)


@pytest.mark.parametrize("mode,status,valid", [
    (mode, status, not (status == "BLOCKED" and mode in {"LOCAL", "REPLAY"}))
    for mode in ("LOCAL", "REPLAY", "FREE_API", "PAID_API", "MANUAL_UI")
    for status in ("SUCCEEDED", "FAILED", "BLOCKED")
])
def test_all_fifteen_mode_status_rows(mode, status, valid) -> None:
    if mode == "REPLAY":
        value, request, source_request, source_execution = _replay_case(status=status)
        kwargs = {"source_alignment_request": source_request, "source_execution": source_execution}
    else:
        request = _request("FREE_API" if mode == "PAID_API" else mode)
        value, _ = _raw_execution(request, mode=mode, status=status)
        kwargs = {}
    if valid:
        assert _materialize(value, request, **kwargs).status.value == status
    else:
        with pytest.raises(AdapterExecutionContractError) as exc:
            _materialize(value, request, **kwargs)
        _assert_error(exc, AdapterExecutionRejectionReason.MODE_STATUS_INVALID, "/status")


@pytest.mark.parametrize("field,mode,issue", [
    ("paid_fallback_authorization_evidence", "LOCAL", "PAID_FALLBACK_UNAUTHORIZED"),
    ("replay_evidence", "FREE_API", "REPLAY_INPUT_MISMATCH"),
    ("confidence_availability_evidence", "LOCAL", None),
])
def test_required_and_forbidden_evidence_presence(field, mode, issue) -> None:
    request_mode = "FREE_API" if mode == "FREE_API" else mode
    request = _request(request_mode)
    value, _ = _raw_execution(request, mode=mode)
    if field == "paid_fallback_authorization_evidence":
        value[field] = {"unexpected": "object"}
    elif field == "replay_evidence":
        value[field] = {"unexpected": "object"}
    else:
        value[field] = None
    with pytest.raises(AdapterExecutionContractError) as exc:
        _materialize(value, request)
    _assert_error(exc, AdapterExecutionRejectionReason.EVIDENCE_PRESENCE_INVALID,
                  f"/{field}", issue)


def test_paid_authorization_approval_denial_binding_and_adapter_parity() -> None:
    request = _request("FREE_API")
    for status, decision in (("SUCCEEDED", "APPROVED"), ("FAILED", "APPROVED"), ("BLOCKED", "DENIED")):
        value, _ = _raw_execution(request, mode="PAID_API", status=status)
        assert value["paid_fallback_authorization_evidence"]["decision"] == decision
        assert _materialize(value, request).status.value == status
    value, _ = _raw_execution(request, mode="PAID_API")
    value["paid_fallback_authorization_evidence"]["decision"] = "DENIED"
    _rehash(value)
    with pytest.raises(AdapterExecutionContractError) as exc:
        _materialize(value, request)
    _assert_error(exc, AdapterExecutionRejectionReason.PAID_FALLBACK_AUTHORIZATION_INVALID,
                  "/paid_fallback_authorization_evidence/decision", "PAID_FALLBACK_UNAUTHORIZED")
    value, _ = _raw_execution(request, mode="PAID_API")
    value["adapter_id"] = "other_adapter"
    _rehash(value)
    with pytest.raises(AdapterExecutionContractError) as exc:
        _materialize(value, request)
    _assert_error(exc, AdapterExecutionRejectionReason.REQUEST_BINDING_INVALID,
                  "/adapter_id", "ALIGNMENT_REQUEST_IDENTITY_MISMATCH")


def test_replay_success_failed_and_exact_lineage_bindings() -> None:
    for status in ("SUCCEEDED", "FAILED"):
        value, request, source_request, source_execution = _replay_case(status=status)
        execution = _materialize(value, request, source_alignment_request=source_request,
                                 source_execution=source_execution)
        assert execution.alignment_request_id == request.alignment_request_id
        assert execution.replay_evidence.source_alignment_request_id == source_request.alignment_request_id
        assert execution.replay_evidence.source_adapter_execution_id == source_execution.adapter_execution_id


@pytest.mark.parametrize("field,replacement,pointer,issue", [
    ("source_adapter_execution_id", "aex_" + "f" * 32,
     "/replay_evidence/source_adapter_execution_id", "REPLAY_INPUT_MISMATCH"),
    ("source_adapter_execution_hash", "f" * 64,
     "/replay_evidence/source_adapter_execution_hash", "REPLAY_HASH_MISMATCH"),
    ("source_alignment_request_id", "arq_" + "f" * 32,
     "/replay_evidence/source_alignment_request_id", "REPLAY_INPUT_MISMATCH"),
    ("source_alignment_request_hash", "f" * 64,
     "/replay_evidence/source_alignment_request_hash", "REPLAY_INPUT_MISMATCH"),
])
def test_replay_dependency_mismatch_oracle(field, replacement, pointer, issue) -> None:
    value, request, source_request, source_execution = _replay_case()
    value["replay_evidence"][field] = replacement
    _rehash(value)
    with pytest.raises(AdapterExecutionContractError) as exc:
        _materialize(value, request, source_alignment_request=source_request,
                     source_execution=source_execution)
    _assert_error(exc, AdapterExecutionRejectionReason.REPLAY_EVIDENCE_INVALID,
                  pointer, issue)


@pytest.mark.parametrize("availability,confidence,status,valid", [
    ("AVAILABLE", "SUPPORTED", "SUCCEEDED", True),
    ("UNAVAILABLE", "SUPPORTED", "SUCCEEDED", True),
    ("NOT_APPLICABLE", "SUPPORTED", "SUCCEEDED", False),
    ("NOT_APPLICABLE", "UNSUPPORTED", "SUCCEEDED", True),
    ("AVAILABLE", "UNSUPPORTED", "SUCCEEDED", False),
    ("NOT_APPLICABLE", "SUPPORTED", "FAILED", True),
    ("AVAILABLE", "SUPPORTED", "FAILED", False),
])
def test_confidence_capability_and_status_boundaries(availability, confidence, status, valid) -> None:
    request = _request("LOCAL", confidence=confidence)
    value, _ = _raw_execution(request, status=status)
    value["confidence_availability_evidence"]["availability"] = availability
    _rehash(value)
    if valid:
        assert _materialize(value, request).confidence_availability_evidence.availability.value == availability
    else:
        with pytest.raises(AdapterExecutionContractError) as exc:
            _materialize(value, request)
        _assert_error(exc, AdapterExecutionRejectionReason.CONFIDENCE_AVAILABILITY_INVALID,
                      "/confidence_availability_evidence/availability")


@pytest.mark.parametrize("field,bad,reason,issue", [
    ("mode", CustomString("LOCAL"), AdapterExecutionRejectionReason.STRUCTURE_INVALID, None),
    ("mode", ArbitraryEnum.LOCAL, AdapterExecutionRejectionReason.STRUCTURE_INVALID, None),
    ("mode", "local", AdapterExecutionRejectionReason.UNSUPPORTED_VALUE, "UNSUPPORTED_CONTRACT_ENUM"),
    ("status", CustomString("SUCCEEDED"), AdapterExecutionRejectionReason.STRUCTURE_INVALID, None),
    ("status", ArbitraryEnum.LOCAL, AdapterExecutionRejectionReason.STRUCTURE_INVALID, None),
    ("status", "UNKNOWN_STATUS", AdapterExecutionRejectionReason.UNSUPPORTED_VALUE, "UNSUPPORTED_CONTRACT_ENUM"),
])
def test_root_exact_scalar_and_enum_precedence(field, bad, reason, issue) -> None:
    value, request = _raw_execution()
    value[field] = bad
    with pytest.raises(AdapterExecutionContractError) as exc:
        _materialize(value, request)
    _assert_error(exc, reason, f"/{field}", issue)


@pytest.mark.parametrize("container,base,first_required", [
    (None, "/", "schema_version"),
    ("paid_fallback_authorization_evidence", "/paid_fallback_authorization_evidence", "schema_version"),
    ("replay_evidence", "/replay_evidence", "schema_version"),
    ("confidence_availability_evidence", "/confidence_availability_evidence", "schema_version"),
])
def test_unknown_before_missing_and_canonical_unknown_order(container, base, first_required) -> None:
    if container == "paid_fallback_authorization_evidence":
        request = _request("FREE_API")
        value, _ = _raw_execution(request, mode="PAID_API")
    elif container == "replay_evidence":
        value, request, source_request, source_execution = _replay_case()
    else:
        value, request = _raw_execution()
    target = value if container is None else value[container]
    del target[first_required]
    target["z_extra"] = "safe"
    target["a_extra"] = "safe"
    kwargs = ({"source_alignment_request": source_request, "source_execution": source_execution}
              if container == "replay_evidence" else {})
    with pytest.raises(AdapterExecutionContractError) as exc:
        _materialize(value, request, **kwargs)
    expected = "/a_extra" if base == "/" else base + "/a_extra"
    _assert_error(exc, AdapterExecutionRejectionReason.STRUCTURE_INVALID, expected)


def test_schema_order_first_missing_key_is_deterministic() -> None:
    value, request = _raw_execution()
    del value["schema_version"]
    del value["hash_scope_version"]
    with pytest.raises(AdapterExecutionContractError) as exc:
        _materialize(value, request)
    _assert_error(exc, AdapterExecutionRejectionReason.STRUCTURE_INVALID, "/schema_version")


@pytest.mark.parametrize("mutator,pointer", [
    (lambda raw: raw.replace(b'"schema_version":"ADAPTER-EXECUTION-V1"',
                             b'"schema_version":"ADAPTER-EXECUTION-V1","schema_version":"ADAPTER-EXECUTION-V1"'), "/"),
    (lambda raw: raw.replace(b'"availability":"AVAILABLE"',
                             b'"availability":"AVAILABLE","availability":"AVAILABLE"'),
     "/confidence_availability_evidence"),
])
def test_duplicate_keys_use_containing_object_pointer(mutator, pointer) -> None:
    value, request = _raw_execution()
    with pytest.raises(AdapterExecutionContractError) as exc:
        load_adapter_execution(mutator(_canonical(value)), alignment_request=request)
    _assert_error(exc, AdapterExecutionRejectionReason.STRUCTURE_INVALID, pointer)


@pytest.mark.parametrize("transform,reason", [
    (lambda raw: b"\xef\xbb\xbf" + raw, AdapterExecutionRejectionReason.NON_CANONICAL_SERIALIZATION),
    (lambda raw: b" " + raw, AdapterExecutionRejectionReason.NON_CANONICAL_SERIALIZATION),
    (lambda raw: raw + b"\n", AdapterExecutionRejectionReason.NON_CANONICAL_SERIALIZATION),
    (lambda raw: raw[:-1], AdapterExecutionRejectionReason.STRUCTURE_INVALID),
    (lambda raw: raw.replace(b'"status":"SUCCEEDED"', b'"status":1'), AdapterExecutionRejectionReason.STRUCTURE_INVALID),
])
def test_loader_canonical_and_malformed_byte_boundaries(transform, reason) -> None:
    value, request = _raw_execution()
    with pytest.raises(AdapterExecutionContractError) as exc:
        load_adapter_execution(transform(_canonical(value)), alignment_request=request)
    _assert_error(exc, reason, "/" if reason is AdapterExecutionRejectionReason.NON_CANONICAL_SERIALIZATION
                  else ("/status" if b'"status":1' in transform(_canonical(value)) else "/"))


def test_hash_precedes_id_and_noncanonical_check() -> None:
    value, request = _raw_execution()
    value["adapter_execution_hash"] = "0" * 64
    value["adapter_execution_id"] = "aex_" + "f" * 32
    with pytest.raises(AdapterExecutionContractError) as exc:
        _materialize(value, request)
    _assert_error(exc, AdapterExecutionRejectionReason.IDENTITY_MISMATCH,
                  "/adapter_execution_hash")
    _rehash(value)
    value["adapter_execution_id"] = "aex_" + "f" * 32
    with pytest.raises(AdapterExecutionContractError) as exc:
        _materialize(value, request)
    _assert_error(exc, AdapterExecutionRejectionReason.IDENTITY_MISMATCH,
                  "/adapter_execution_id")


def test_dependency_preflight_order_and_raw_non_access() -> None:
    class ExplodingMapping(dict):
        def keys(self):
            raise AssertionError("raw input accessed")

    raw = ExplodingMapping()
    with pytest.raises(TypeError) as exc:
        materialize_adapter_execution(raw, alignment_request=object())
    assert "alignment_request" in str(exc.value)
    request = _request()
    with pytest.raises(AdapterExecutionContractError) as exc:
        materialize_adapter_execution(raw, alignment_request=request,
                                      source_alignment_request=object(),
                                      source_execution=object())
    _assert_error(exc, AdapterExecutionRejectionReason.NOT_MATERIALIZED,
                  "/source_alignment_request")
    with pytest.raises(AdapterExecutionContractError) as exc:
        materialize_adapter_execution(raw, alignment_request=request,
                                      source_execution=object())
    _assert_error(exc, AdapterExecutionRejectionReason.NOT_MATERIALIZED,
                  "/source_execution")


def test_source_dependency_presence_is_after_mode_parsing_and_ordered() -> None:
    request = _request("REPLAY")
    value, _ = _raw_execution(request, mode="REPLAY", replay={})
    value["mode"] = "UNKNOWN"
    with pytest.raises(AdapterExecutionContractError) as exc:
        _materialize(value, request)
    _assert_error(exc, AdapterExecutionRejectionReason.UNSUPPORTED_VALUE,
                  "/mode", "UNSUPPORTED_CONTRACT_ENUM")
    value["mode"] = "REPLAY"
    with pytest.raises(AdapterExecutionContractError) as exc:
        _materialize(value, request)
    _assert_error(exc, AdapterExecutionRejectionReason.REPLAY_EVIDENCE_INVALID,
                  "/source_alignment_request", "REPLAY_INPUT_MISMATCH")


@pytest.mark.parametrize("container,field,bad,reason,pointer,issue", [
    ("paid", "schema_version", 1, AdapterExecutionRejectionReason.PAID_FALLBACK_AUTHORIZATION_INVALID,
     "/paid_fallback_authorization_evidence/schema_version", "PAID_FALLBACK_UNAUTHORIZED"),
    ("paid", "authorization_id", "bad", AdapterExecutionRejectionReason.PAID_FALLBACK_AUTHORIZATION_INVALID,
     "/paid_fallback_authorization_evidence/authorization_id", "PAID_FALLBACK_UNAUTHORIZED"),
    ("paid", "source", "user_explicit", AdapterExecutionRejectionReason.PAID_FALLBACK_AUTHORIZATION_INVALID,
     "/paid_fallback_authorization_evidence/source", "PAID_FALLBACK_UNAUTHORIZED"),
    ("replay", "schema_version", 1, AdapterExecutionRejectionReason.REPLAY_EVIDENCE_INVALID,
     "/replay_evidence/schema_version", "REPLAY_INPUT_MISMATCH"),
    ("replay", "source_adapter_execution_id", "aex_bad", AdapterExecutionRejectionReason.REPLAY_EVIDENCE_INVALID,
     "/replay_evidence/source_adapter_execution_id", "REPLAY_INPUT_MISMATCH"),
    ("replay", "source_adapter_execution_hash", "sha256:" + "0" * 64, AdapterExecutionRejectionReason.REPLAY_EVIDENCE_INVALID,
     "/replay_evidence/source_adapter_execution_hash", "REPLAY_HASH_MISMATCH"),
    ("replay", "source_alignment_request_hash", "sha256:" + "0" * 64, AdapterExecutionRejectionReason.REPLAY_EVIDENCE_INVALID,
     "/replay_evidence/source_alignment_request_hash", "REPLAY_INPUT_MISMATCH"),
    ("confidence", "schema_version", 1, AdapterExecutionRejectionReason.CONFIDENCE_AVAILABILITY_INVALID,
     "/confidence_availability_evidence/schema_version", None),
    ("confidence", "availability", "available", AdapterExecutionRejectionReason.CONFIDENCE_AVAILABILITY_INVALID,
     "/confidence_availability_evidence/availability", None),
])
def test_nested_exact_type_literal_and_syntax_oracles(container, field, bad, reason, pointer, issue) -> None:
    if container == "paid":
        request = _request("FREE_API")
        value, _ = _raw_execution(request, mode="PAID_API")
        target = value["paid_fallback_authorization_evidence"]
        kwargs = {}
    elif container == "replay":
        value, request, source_request, source_execution = _replay_case()
        target = value["replay_evidence"]
        kwargs = {"source_alignment_request": source_request, "source_execution": source_execution}
    else:
        value, request = _raw_execution()
        target = value["confidence_availability_evidence"]
        kwargs = {}
    target[field] = bad
    with pytest.raises(AdapterExecutionContractError) as exc:
        _materialize(value, request, **kwargs)
    _assert_error(exc, reason, pointer, issue)


def test_sensitive_scan_redacts_and_uses_exact_pointer() -> None:
    value, request = _raw_execution()
    value["adapter_version"] = "https://secret.example/token"
    request.adapter_capability  # keep genuine request alive
    # Binding is earlier than the sensitive scan; use a matching genuine request field
    object.__setattr__(request.adapter_capability, "adapter_version", value["adapter_version"])
    try:
        with pytest.raises(AdapterExecutionContractError) as exc:
            _materialize(value, request)
        _assert_error(exc, AdapterExecutionRejectionReason.STRUCTURE_INVALID,
                      "/adapter_version")
        assert "secret.example" not in str(exc.value)
    finally:
        object.__setattr__(request.adapter_capability, "adapter_version", "1.0.0")


def test_models_input_and_serialized_bytes_are_immutable() -> None:
    value, request = _raw_execution()
    nested = value["confidence_availability_evidence"]
    execution = _materialize(value, request)
    original = serialize_adapter_execution(execution)
    value["adapter_id"] = "changed"
    nested["availability"] = "UNAVAILABLE"
    assert serialize_adapter_execution(execution) == original
    with pytest.raises((FrozenInstanceError, AttributeError)):
        execution.status = AdapterExecutionStatus.FAILED
    mutable = bytearray(original)
    mutable[0] = 0
    assert serialize_adapter_execution(execution) == original


@pytest.mark.parametrize("factory", [copy.copy, copy.deepcopy, pickle.loads])
def test_copy_deepcopy_pickle_and_reconstruction_do_not_mint_provenance(factory) -> None:
    execution = _materialize()
    clone = factory(pickle.dumps(execution)) if factory is pickle.loads else factory(execution)
    with pytest.raises(AdapterExecutionContractError) as exc:
        serialize_adapter_execution(clone)
    _assert_error(exc, AdapterExecutionRejectionReason.NOT_MATERIALIZED, "/")
    reconstructed = replace(execution)
    with pytest.raises(AdapterExecutionContractError):
        serialize_adapter_execution(reconstructed)


def test_subclass_proxy_and_direct_constructor_are_not_genuine() -> None:
    execution = _materialize()

    class ExecutionSubclass(AdapterExecution):
        pass

    clone = object.__new__(ExecutionSubclass)
    for field in dataclasses.fields(execution):
        object.__setattr__(clone, field.name, getattr(execution, field.name))
    for forged in (clone, AdapterExecution(**{field.name: getattr(execution, field.name)
                                                for field in dataclasses.fields(execution)})):
        with pytest.raises(AdapterExecutionContractError) as exc:
            serialize_adapter_execution(forged)
        _assert_error(exc, AdapterExecutionRejectionReason.NOT_MATERIALIZED, "/")


def test_registry_collection_cleanup_and_registration_rollback(monkeypatch) -> None:
    execution = _materialize()
    identity = id(execution)
    reference = weakref.ref(execution)
    del execution
    for _ in range(5):
        gc.collect()
        if reference() is None:
            break
    assert reference() is None
    assert identity not in execution_contracts._MATERIALIZED_ADAPTER_EXECUTIONS

    monkeypatch.setattr(execution_contracts, "_is_materialized_adapter_execution", lambda value: False)
    value, request = _raw_execution()
    before = dict(execution_contracts._MATERIALIZED_ADAPTER_EXECUTIONS)
    with pytest.raises(RuntimeError, match="^adapter execution provenance registration failed$"):
        _materialize(value, request)
    assert execution_contracts._MATERIALIZED_ADAPTER_EXECUTIONS == before


def test_alignment_request_golden_and_stable_issue_inventory_regressions() -> None:
    request = _request()
    from engine.contracts import serialize_alignment_request
    assert request.alignment_request_id == FX_ARQ_01_ID
    assert request.alignment_request_hash == FX_ARQ_01_HASH
    assert serialize_alignment_request(request) == FX_ARQ_01_ENVELOPE_BYTES
    assert {
        "UNSUPPORTED_CONTRACT_ENUM", "ALIGNMENT_REQUEST_IDENTITY_MISMATCH",
        "PAID_FALLBACK_UNAUTHORIZED", "REPLAY_INPUT_MISMATCH", "REPLAY_HASH_MISMATCH",
    } <= execution_contracts.STABLE_ISSUE_CODE_SET
