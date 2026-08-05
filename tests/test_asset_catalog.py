from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import engine.acquisition.asset_catalog as asset_catalog_module

from engine.acquisition import (
    AssetBriefV1, AssetCatalogError, AssetIngestionInputV1, AssetMaterializationRegistry,
    AssetReuseContextV1, AssetReuseInstanceV1,
    FingerprintEvidenceV1, MediaProbeEvidenceV1, MediaType,
    ReplayAssetEvidenceRegistry, SemanticDeclarationV1, SourceAudioEligibilityV1,
    SourceAudioStatus, SourceDescriptorV1, SelectedRangeV1, asset_catalog_policy_from_snapshot,
    compile_asset_catalog, empty_asset_catalog,
    canonical_asset_catalog_json, load_asset_catalog_json, verify_catalog_receipt,
    canonical_catalog_mutation_json, canonical_catalog_receipt_json, canonical_ingestion_package_json,
    load_catalog_mutation_json, load_catalog_receipt_json, load_ingestion_package_json,
    evaluate_asset_reuse,
)
from engine.contracts.domain import policy_snapshot_hash
from engine.contracts.models import DomainPolicySnapshot


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = REPO_ROOT / "tests" / "fixtures" / "phase8_replay_evidence_manifest.json"


def _hash(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _snapshot() -> DomainPolicySnapshot:
    raw_policy = {
        "policy_version": "ASSET-CATALOG-POLICY-V1",
        "allowed_asset_brief_roles": ["show_operational_consequence"],
        "allowed_preferred_type_tokens": ["real_broll"],
        "allowed_avoid_context_tokens": ["generic_server_room"],
        "allowed_domain_role_tokens": ["company"],
        "allowed_domain_sensitivity_tokens": ["attribution_required"],
        "source_audio_reason_tokens": ["rights_confirmed", "no_source_audio"],
        "generic_stock_provider_tokens": ["pexels"],
        "reuse_cooldown_frames": 30,
        "chapter_family_budget": 2,
    }
    resolved = {"policy_bundles": [{"ref": "policy.json", "policy": {"visual": {"asset_catalog_policy": raw_policy}}}], "extensions": {}, "enabled_extensions": [], "overrides": {}}
    data = {"schema_version": "3.0.0", "domain_id": "business-tech", "domain_pack_version": "0.1.0", "profile_id": "profile_business", "manifest_hash": "sha256:" + "a" * 64, "resolved_policy": resolved, "immutable": True, "created_at": "2026-08-05T00:00:00Z", "version": 1}
    digest = policy_snapshot_hash(data)
    return DomainPolicySnapshot(**(data | {"snapshot_id": "dps_" + digest[7:27], "canonical_hash": digest}))


def _input(value: bytes, *, uri: str = "urn:fixture:one", provider: str = "pexels", avoid: tuple[str, ...] = ("generic_server_room",), ranges: tuple[SelectedRangeV1, ...] = ()) -> AssetIngestionInputV1:
    return AssetIngestionInputV1(
        value, "prj_asset", None,
        SourceDescriptorV1(provider, uri, "editorial", ("video",), "local_replay"),
        SemanticDeclarationV1(("company",), ("operating",), "workspace", "analytical", ("broll",), avoid, ("company",), ("attribution_required",)),
        ranges, SourceAudioEligibilityV1(SourceAudioStatus.NOT_APPLICABLE, ("no_source_audio",), ()),
    )


def _register(registry: ReplayAssetEvidenceRegistry, value: bytes, descriptor: SourceDescriptorV1, *, visual: str = "a", media_type: MediaType = MediaType.IMAGE, use_local: bool = False) -> None:
    source_hash = _hash(value)
    duration = 1_000 if media_type is MediaType.VIDEO else None
    probe_facts = {"source_hash": source_hash, "media_type": media_type.value, "duration_ms": duration, "width": 100, "height": 100, "fps_numerator": 30 if media_type is MediaType.VIDEO else None, "fps_denominator": 1 if media_type is MediaType.VIDEO else None, "codec": "png", "has_audio": False}
    probe = MediaProbeEvidenceV1("probe_fixture", asset_catalog_module._hash(probe_facts), source_hash, media_type, duration, 100, 100, 30 if media_type is MediaType.VIDEO else None, 1 if media_type is MediaType.VIDEO else None, "png", False)
    frames = (_hash(("frame-" + visual).encode()),) if media_type in {MediaType.IMAGE, MediaType.VIDEO} and not use_local else ()
    local = (_hash(("local-" + visual).encode()),) if media_type in {MediaType.IMAGE, MediaType.VIDEO} and use_local else ()
    fingerprint_facts = {"source_hash": source_hash, "descriptor_hash": descriptor.descriptor_hash, "perceptual_frame_hashes": list(frames), "local_feature_hashes": list(local), "same_source_key": descriptor.same_source_key}
    fingerprint = FingerprintEvidenceV1("fingerprint_fixture", asset_catalog_module._hash(fingerprint_facts), source_hash, descriptor.descriptor_hash, frames, local, descriptor.same_source_key)
    # Test-only in-memory fixture harness; production can populate only via
    # the pinned manifest loader.
    registry._probes[probe.source_hash] = probe
    registry._fingerprints[fingerprint.source_hash] = fingerprint


def _compile(value: bytes, *, catalog=None, uri="urn:fixture:one", provider="pexels", avoid=("generic_server_room",), visual="a", ranges=(), media_type=MediaType.IMAGE, use_local=False):
    policy = asset_catalog_policy_from_snapshot(_snapshot())
    current = empty_asset_catalog("prj_asset", policy) if catalog is None else catalog
    input_value = _input(value, uri=uri, provider=provider, avoid=avoid, ranges=ranges)
    materializations = AssetMaterializationRegistry(); handle = materializations.register(input_value)
    evidence = ReplayAssetEvidenceRegistry(); _register(evidence, value, input_value.source_descriptor, visual=visual, media_type=media_type, use_local=use_local)
    try:
        return asset_catalog_module._compile_asset_catalog(input_value=input_value, materializations=materializations, materialization_handle=handle, evidence_registry=evidence, policy=policy, catalog=current)
    except AssetCatalogError as error:
        return asset_catalog_module._failure_receipt(error.code)


def test_catalog_record_has_byte_provenance_semantics_family_and_generic_stock_ratio() -> None:
    result = _compile(b"image-bytes")
    record = result.catalog.records[0]
    assert record.source_hash == _hash(b"image-bytes")
    assert record.visual_family_id.startswith("fam_")
    assert record.avoid_contexts == ("generic_server_room",)
    assert result.generic_stock_ratio.status == "available"
    assert (result.generic_stock_ratio.numerator, result.generic_stock_ratio.denominator) == (1, 1)
    assert result.outcome_kind == "ingestion_only"
    assert result.mutation.result_kind == "accepted"
    assert result.receipt.status == "SUCCESS"
    assert {"policy_snapshot", "package", "decision", "mutation", "catalog", "reuse_plan", "generic_stock_ratio"}.issubset({node[0] for node in result.receipt.dependency_nodes})
    assert result.receipt.dependency_nodes[-1][0] == "receipt"
    assert result.receipt.dependency_edges[-1][2] == "receipt"


def test_public_contract_models_have_only_the_declared_phase8_fields() -> None:
    assert tuple(asset_catalog_module.AssetRecordV1.__dataclass_fields__) == (
        "asset_id", "asset_hash", "source_hash", "source_byte_length", "media_type", "media_facts", "source_descriptor", "fingerprint_evidence", "visual_family_id", "subjects", "actions", "setting", "mood", "semantic_tags", "avoid_contexts", "domain_roles", "domain_sensitivity_tags", "selected_ranges", "source_audio_eligibility", "duplicate_of_asset_id", "duplicate_of_asset_hash",
    )
    assert tuple(asset_catalog_module.AssetCatalogMutationV1.__dataclass_fields__) == (
        "mutation_id", "mutation_hash", "input_catalog_id", "input_catalog_hash", "candidate_package_id", "candidate_package_hash", "duplicate_decision", "result_kind", "accepted_asset_record", "output_catalog_id", "output_catalog_hash",
    )
    assert tuple(asset_catalog_module.AssetReuseContextV1.__dataclass_fields__) == (
        "catalog_id", "catalog_hash", "chapter_id", "frame_rate", "instances", "context_id", "context_hash",
    )


def test_catalog_and_terminal_receipt_replay_verifiers_reject_mutation() -> None:
    policy = asset_catalog_policy_from_snapshot(_snapshot())
    result = compile_asset_catalog(input_value=_input(b"phase8-fixture-image", uri="urn:fixture:image"), policy=policy, catalog=empty_asset_catalog("prj_asset", policy))
    canonical = canonical_asset_catalog_json(catalog=result.catalog, policy=policy)
    assert load_asset_catalog_json(payload=canonical, policy=policy) == result.catalog
    tampered = json.loads(canonical)
    tampered["records"][0]["source_hash"] = _hash(b"forged")
    with pytest.raises(AssetCatalogError, match="ASSET_CATALOG_INVALID"):
        load_asset_catalog_json(payload=json.dumps(tampered, separators=(",", ":")).encode(), policy=policy)
    verify_catalog_receipt(result.receipt)
    mutated = asset_catalog_module.CatalogReceiptV1(
        result.receipt.receipt_id, result.receipt.receipt_hash, result.receipt.status,
        result.receipt.outcome_kind, result.receipt.reuse_gate_status, result.receipt.error_code,
        result.receipt.dependency_nodes[:-1] + (("receipt", result.receipt.receipt_id, _hash(b"forged")),), result.receipt.dependency_edges,
    )
    with pytest.raises(AssetCatalogError, match="RECEIPT_INVALID"):
        verify_catalog_receipt(mutated)


def test_package_mutation_and_receipt_canonical_replay_rejects_drift() -> None:
    policy = asset_catalog_policy_from_snapshot(_snapshot())
    input_value = _input(b"phase8-fixture-image", uri="urn:fixture:image")
    initial = empty_asset_catalog("prj_asset", policy)
    result = compile_asset_catalog(input_value=input_value, policy=policy, catalog=initial)
    package_json = canonical_ingestion_package_json(result.package)
    assert load_ingestion_package_json(payload=package_json, asset_bytes=input_value.asset_bytes, policy=policy) == result.package
    mutation_json = canonical_catalog_mutation_json(result.mutation)
    assert load_catalog_mutation_json(payload=mutation_json, package_payload=package_json, asset_bytes=input_value.asset_bytes, input_catalog=initial, output_catalog=result.catalog, policy=policy) == result.mutation
    receipt_json = canonical_catalog_receipt_json(result.receipt)
    assert load_catalog_receipt_json(receipt_json) == result.receipt
    tampered = json.loads(package_json)
    tampered["source_byte_length"] += 1
    with pytest.raises(AssetCatalogError, match="ASSET_PACKAGE_INVALID"):
        load_ingestion_package_json(payload=json.dumps(tampered, separators=(",", ":")).encode(), asset_bytes=input_value.asset_bytes, policy=policy)


def test_video_probe_requires_reduced_fps_rational() -> None:
    with pytest.raises(AssetCatalogError, match="MEDIA_PROBE_INVALID"):
        MediaProbeEvidenceV1("probe_fps", "sha256:" + "0" * 64, _hash(b"video"), MediaType.VIDEO, 1_000, 100, 100, 60, 2, "h264", False).data()


def test_exact_bytes_and_same_source_are_explicitly_blocked_not_inserted() -> None:
    first = _compile(b"first")
    same_bytes = _compile(b"first", catalog=first.catalog)
    assert same_bytes.decision.decision_kind.value == "exact_bytes"
    assert len(same_bytes.catalog.records) == 1
    same_origin = _compile(b"reencoded", catalog=first.catalog)
    assert same_origin.decision.decision_kind.value == "same_source"
    assert len(same_origin.catalog.records) == 1


def test_policy_and_trusted_fixture_fail_closed() -> None:
    denied = _compile(b"bytes", avoid=("not_allowed",))
    assert denied.error_code == "policy_denied" and denied.receipt.status == "FAILURE"
    policy = asset_catalog_policy_from_snapshot(_snapshot())
    input_value = _input(b"bytes")
    untrusted = compile_asset_catalog(input_value=input_value, policy=policy, catalog=empty_asset_catalog("prj_asset", policy))
    assert untrusted.error_code == "untrusted_replay_evidence" and untrusted.receipt.dependency_nodes == ()


def test_replay_evidence_manifest_is_hash_authenticated_and_tamper_rejected(tmp_path: Path) -> None:
    loaded = ReplayAssetEvidenceRegistry.load(MANIFEST)
    probe, fingerprints = loaded.resolve("sha256:4731777bc9dff2f7e6a75bcd5a9bf59e6ca8c9826cad6f1ba5dbb5a458d66a5d")
    assert (probe.fixture_id, fingerprints.fixture_id) == ("probe_image", "fingerprint_image")
    tampered = json.loads(MANIFEST.read_text(encoding="utf-8"))
    tampered["entries"][0]["probe"]["width"] = 101
    path = tmp_path / "tampered_manifest.json"; path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(AssetCatalogError, match="REPLAY_EVIDENCE_MANIFEST_INVALID"):
        ReplayAssetEvidenceRegistry.load(path)


@pytest.mark.parametrize(("value", "uri", "media_type"), [
    (b"phase8-fixture-image", "urn:fixture:image", MediaType.IMAGE),
    (b"phase8-fixture-video", "urn:fixture:video", MediaType.VIDEO),
    (b"phase8-fixture-document", "urn:fixture:document", MediaType.DOCUMENT),
    (b"phase8-fixture-audio", "urn:fixture:audio", MediaType.AUDIO),
])
def test_public_compiler_uses_only_hash_authenticated_pinned_manifest(value: bytes, uri: str, media_type: MediaType) -> None:
    policy = asset_catalog_policy_from_snapshot(_snapshot())
    input_value = _input(value, uri=uri)
    result = compile_asset_catalog(input_value=input_value, policy=policy, catalog=empty_asset_catalog("prj_asset", policy))
    assert result.receipt.status == "SUCCESS"
    assert result.catalog.records[0].media_type is media_type


def test_perceptual_family_is_not_split_by_semantic_declaration() -> None:
    first = _compile(b"first", visual="same")
    second = _compile(b"second", catalog=first.catalog, uri="urn:fixture:two", visual="same")
    assert second.decision.decision_kind.value == "perceptual_match"
    assert len(second.catalog.records) == 1


def test_local_feature_duplicate_is_explicit() -> None:
    first = _compile(b"first", visual="same", use_local=True)
    second = _compile(b"second", catalog=first.catalog, uri="urn:fixture:two", visual="same", use_local=True)
    assert second.decision.decision_kind.value == "local_feature_match"


def test_selected_range_duplicate_precedes_exact_bytes() -> None:
    first = _compile(b"video", ranges=(SelectedRangeV1(0, 500),), media_type=MediaType.VIDEO)
    overlapping = _compile(b"video", catalog=first.catalog, ranges=(SelectedRangeV1(400, 900),), media_type=MediaType.VIDEO)
    assert overlapping.decision.decision_kind.value == "selected_range_overlap"
    assert len(overlapping.catalog.records) == 1


@pytest.mark.parametrize("media_type", [MediaType.DOCUMENT, MediaType.AUDIO])
def test_document_and_audio_require_explicit_empty_fingerprints(media_type: MediaType) -> None:
    result = _compile(b"nonvisual", media_type=media_type)
    assert result.catalog.records[0].media_type is media_type


def test_reuse_context_must_bind_to_exact_catalog_record() -> None:
    policy = asset_catalog_policy_from_snapshot(_snapshot())
    result = compile_asset_catalog(input_value=_input(b"phase8-fixture-image", uri="urn:fixture:image"), policy=policy, catalog=empty_asset_catalog("prj_asset", policy))
    record = result.catalog.records[0]
    context = AssetReuseContextV1(result.catalog.catalog_id, result.catalog.catalog_hash, "chapter_one", (30, 1), (
        AssetReuseInstanceV1(record.asset_id, record.asset_hash, record.visual_family_id, "seq_one", 0, 30, 0),
    ))
    plan = evaluate_asset_reuse(catalog=result.catalog, policy=policy, context=context)
    assert plan.status.value == "evaluated"
    wrong = AssetReuseContextV1("cat_wrong", result.catalog.catalog_hash, "chapter_one", (30, 1), context.instances)
    with pytest.raises(AssetCatalogError, match="REUSE_CONTEXT_INVALID"):
        evaluate_asset_reuse(catalog=result.catalog, policy=policy, context=wrong)


def test_reuse_violations_are_closed_hash_bound_records() -> None:
    policy = asset_catalog_policy_from_snapshot(_snapshot())
    result = compile_asset_catalog(input_value=_input(b"phase8-fixture-image", uri="urn:fixture:image"), policy=policy, catalog=empty_asset_catalog("prj_asset", policy))
    record = result.catalog.records[0]
    context = AssetReuseContextV1(result.catalog.catalog_id, result.catalog.catalog_hash, "chapter_one", (30, 1), (
        AssetReuseInstanceV1(record.asset_id, record.asset_hash, record.visual_family_id, "seq_one", 0, 30, 0),
        AssetReuseInstanceV1(record.asset_id, record.asset_hash, record.visual_family_id, "seq_two", 31, 60, 1),
        AssetReuseInstanceV1(record.asset_id, record.asset_hash, record.visual_family_id, "seq_three", 61, 90, 2),
    ))
    plan = evaluate_asset_reuse(catalog=result.catalog, policy=policy, context=context)
    assert {item.kind for item in plan.violations} == {"cooldown", "chapter_family_budget"}
    assert all(item.violation_id == "rv_" + item.violation_hash[7:27] for item in plan.violations)


def test_asset_brief_carries_the_resolved_domain_visual_policy_and_fails_closed() -> None:
    policy = asset_catalog_policy_from_snapshot(_snapshot())
    brief = AssetBriefV1("show_operational_consequence", "developers", "reviewing", "workspace", ("generic_server_room",), ("real_broll",), policy.snapshot_id, policy.snapshot_hash, policy.policy_hash)
    assert brief.data(policy)["brief_id"].startswith("brief_")
    denied = AssetBriefV1("unknown_role", "developers", "reviewing", "workspace", (), (), policy.snapshot_id, policy.snapshot_hash, policy.policy_hash)
    with pytest.raises(AssetCatalogError, match="ASSET_BRIEF_INVALID"):
        denied.data(policy)
