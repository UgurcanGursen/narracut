import hashlib
import pytest
from engine.cache_lifecycle import CacheEntryRecord, CachePayloadObject, RetentionPolicySnapshot, cache_write_lifecycle_metadata, load_cache_write_lifecycle_metadata, plan_soft_quota, resolve_payload_object, storage_report, validate_soft_quota_plan


def payload(data=b"same"):
    digest = "sha256:" + hashlib.sha256(data).hexdigest()
    values = {"payload_object_id":"", "storage_scope_id":"global_cache", "payload_hash":digest, "payload_size_bytes":len(data), "created_at":"2026-08-01T00:00:00Z", "status":"ready"}
    values["payload_object_id"] = "cpo_" + hashlib.sha256(__import__("engine.contracts._canonical_json", fromlist=["encode_canonical_json_bytes"]).encode_canonical_json_bytes({key:value for key, value in values.items() if key != "payload_object_id"})).hexdigest()[:32]
    return CachePayloadObject.materialize(values)


def entry(item, identifier, *, retained=()):
    values = {"cache_entry_id":"", "storage_scope_id":"global_cache", "cache_key":"sha256:" + identifier * 64, "profile":"preview", "payload_object_id":item.payload_object_id, "producer_input_hash":"sha256:" + identifier * 64, "producer_version":"1", "created_at":"2026-08-01T00:00:00Z", "last_accessed_at":"2026-08-01T00:00:00Z", "registry_artifact_ids":retained, "status":"ready"}
    values["cache_entry_id"] = "cen_" + hashlib.sha256(__import__("engine.contracts._canonical_json", fromlist=["encode_canonical_json_bytes"]).encode_canonical_json_bytes({key:(tuple(retained) if key == "registry_artifact_ids" else value) for key, value in values.items() if key != "cache_entry_id"})).hexdigest()[:32]
    return CacheEntryRecord.materialize(values)


def policy(): return RetentionPolicySnapshot("sha256:" + "f" * 64, "global_cache", 0, 100, 0, "2026-08-02T00:00:00Z")


def test_report_and_plan_retire_all_references_before_one_payload():
    item = payload(); entries = (entry(item, "a"), entry(item, "b"))
    assert storage_report(payloads=(item,), entries=entries) == {"logical_bytes":8, "physical_bytes":4, "dedup_saved_bytes":4}
    plan = plan_soft_quota(payloads=(item,), entries=entries, policy=policy(), retained_artifact_ids=frozenset())
    assert [row["kind"] for row in plan["rows"]] == ["RETIRE_CACHE_ENTRY", "RETIRE_CACHE_ENTRY", "TRASH_CACHE_PAYLOAD"] and plan["status"] == "PLANNED"


def test_retained_reference_and_bad_scope_fail_closed():
    item = payload(); kept = entry(item, "a", retained=("art_final",))
    assert plan_soft_quota(payloads=(item,), entries=(kept,), policy=policy(), retained_artifact_ids=frozenset({"art_final"}))["rows"] == []
    with pytest.raises(ValueError, match="SCOPE"):
        plan_soft_quota(payloads=(item,), entries=(kept,), policy=RetentionPolicySnapshot("sha256:" + "f" * 64, "other", 0, 1, 0, "2026-08-02T00:00:00Z"), retained_artifact_ids=frozenset())


def test_orphan_payload_is_direct_reclaim_candidate():
    item = payload()
    plan = plan_soft_quota(payloads=(item,), entries=(), policy=policy(), retained_artifact_ids=frozenset())
    assert [row["kind"] for row in plan["rows"]] == ["TRASH_CACHE_PAYLOAD"]


def test_resolver_accepts_only_verified_fanout_object(tmp_path):
    data=b"same"; digest="sha256:"+hashlib.sha256(data).hexdigest(); path=tmp_path/"sha256"/digest[7:9]/digest[9:]; path.parent.mkdir(parents=True); path.write_bytes(data)
    assert resolve_payload_object(managed_root=tmp_path, payload_hash=digest) == path
    path.unlink()
    try:
        path.symlink_to(tmp_path / "elsewhere")
    except OSError:
        pytest.skip("symlink fixture privilege unavailable")
    with pytest.raises(ValueError, match="RESOLUTION"):
        resolve_payload_object(managed_root=tmp_path, payload_hash=digest)


def test_plan_rejects_registry_or_policy_drift():
    item = payload(); entries = (entry(item, "a"),); planned = plan_soft_quota(payloads=(item,), entries=entries, policy=policy(), retained_artifact_ids=frozenset())
    validate_soft_quota_plan(plan=planned, payloads=(item,), entries=entries, policy=policy())
    with pytest.raises(ValueError, match="STALE"):
        validate_soft_quota_plan(plan=planned, payloads=(item,), entries=entries, policy=RetentionPolicySnapshot("sha256:" + "e" * 64, "global_cache", 0, 100, 0, "2026-08-02T00:00:00Z"))


def test_cache_write_metadata_is_path_free_and_reopenable():
    metadata = cache_write_lifecycle_metadata(storage_scope_id="global_cache", cache_key="sha256:" + "a" * 64, profile="preview", payload_hash="sha256:" + "b" * 64, payload_size_bytes=3, producer_version="v1", timestamp_utc="2026-08-01T00:00:00Z")
    entry, payload = load_cache_write_lifecycle_metadata(metadata)
    assert entry.payload_object_id == payload.payload_object_id
