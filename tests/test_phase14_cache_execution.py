import hashlib
import pytest
from engine.cache_execution import execute_cache_plan, load_cache_transactions, restore_cache_transaction
from engine.cache_lifecycle import CacheEntryRecord, CachePayloadObject, RetentionPolicySnapshot, plan_soft_quota
from engine.contracts._canonical_json import encode_canonical_json_bytes


def _payload(data):
    digest="sha256:"+hashlib.sha256(data).hexdigest(); body={"storage_scope_id":"cache", "payload_hash":digest,"payload_size_bytes":len(data),"created_at":"2026-08-01T00:00:00Z","status":"ready"}; ident="cpo_"+hashlib.sha256(encode_canonical_json_bytes(body)).hexdigest()[:32]
    return CachePayloadObject.materialize({"payload_object_id":ident, **body})


def _entry(item):
    body={"storage_scope_id":"cache","cache_key":"sha256:"+"a"*64,"profile":"preview","payload_object_id":item.payload_object_id,"producer_input_hash":"sha256:"+"a"*64,"producer_version":"v1","created_at":"2026-08-01T00:00:00Z","last_accessed_at":"2026-08-01T00:00:00Z","registry_artifact_ids":(),"status":"ready"}; ident="cen_"+hashlib.sha256(encode_canonical_json_bytes(body)).hexdigest()[:32]
    return CacheEntryRecord.materialize({"cache_entry_id":ident, **body})


def _policy(): return RetentionPolicySnapshot("sha256:"+"f"*64,"cache",0,100,0,"2026-08-02T00:00:00Z")


def test_plan_moves_payload_as_one_receipted_transaction_and_restores(tmp_path):
    raw=b"payload"; item=_payload(raw); entry=_entry(item); path=tmp_path/"sha256"/item.payload_hash[7:9]/item.payload_hash[9:]; path.parent.mkdir(parents=True); path.write_bytes(raw)
    plan=plan_soft_quota(payloads=(item,),entries=(entry,),policy=_policy(),retained_artifact_ids=frozenset())
    retired=execute_cache_plan(managed_root=tmp_path,plan=plan,payloads=(item,),entries=(entry,),policy=_policy(),timestamp_utc="2026-08-02T00:00:00Z")
    assert not path.exists() and len(load_cache_transactions(managed_root=tmp_path)) == 1
    restored=restore_cache_transaction(managed_root=tmp_path,transaction=retired,timestamp_utc="2026-08-02T00:01:00Z")
    assert path.read_bytes()==raw and restored["kind"]=="restored" and len(load_cache_transactions(managed_root=tmp_path))==2


def test_failed_transaction_publication_rolls_payload_back(tmp_path, monkeypatch):
    raw=b"payload"; item=_payload(raw); entry=_entry(item); path=tmp_path/"sha256"/item.payload_hash[7:9]/item.payload_hash[9:]; path.parent.mkdir(parents=True); path.write_bytes(raw)
    plan=plan_soft_quota(payloads=(item,),entries=(entry,),policy=_policy(),retained_artifact_ids=frozenset())
    monkeypatch.setattr("engine.cache_execution._append_transaction", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("disk")))
    with pytest.raises(OSError):
        execute_cache_plan(managed_root=tmp_path,plan=plan,payloads=(item,),entries=(entry,),policy=_policy(),timestamp_utc="2026-08-02T00:00:00Z")
    assert path.read_bytes()==raw and load_cache_transactions(managed_root=tmp_path)==()
