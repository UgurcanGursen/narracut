import hashlib
import json
import pytest
from engine.contracts._canonical_json import encode_canonical_json_bytes
from engine.lifecycle import load_registry
from engine.storage_manager import (StoragePressurePolicy, StorageQuotaManager,
    register_committed_full_artifacts, storage_pressure_admission)


def test_pressure_admission_checks_projected_bytes(tmp_path):
    (tmp_path / "used").write_bytes(b"xx")
    assert storage_pressure_admission(managed_root=tmp_path, policy=StoragePressurePolicy("scope", 2, 0), estimated_bytes=1) == "BLOCKED_HARD_QUOTA"


def test_committed_full_journal_imports_only_explicit_policy_rows(tmp_path):
    transaction_id="txn_demo"; receipt_hash="sha256:"+"a"*64
    row={"artifact_id":"art_final_1","kind":"final_output","content_sha256":"sha256:"+"b"*64,"byte_length":3,"project_id":"prj_demo","sequence_id":"seq_demo","producer":"phase4b"}
    journal={"schema_version":"FULL-RENDER-TRANSACTION-V1","transaction_id":transaction_id,"artifact_rows":[row],"receipt":{"receipt_hash":receipt_hash}}
    path=tmp_path/"artifacts"/"transactions"/f"{transaction_id}.json"; path.parent.mkdir(parents=True); path.write_bytes(encode_canonical_json_bytes(journal))
    registry=tmp_path/"artifacts"/"registry.jsonl"; registry.write_bytes(encode_canonical_json_bytes({"schema_version":"FULL-RENDER-REGISTRY-ROW-V1","transaction_id":transaction_id,"marker":"COMMITTED","receipt_hash":receipt_hash})+b"\n")
    target=tmp_path/"phase14-registry.jsonl"
    policy={"final_output":{"retention_class":"final","locked":False,"pinned":False,"approved":False,"producer_version":"1"}}
    register_committed_full_artifacts(project_root=tmp_path,transaction_id=transaction_id,registry_path=target,policy_by_kind=policy)
    assert load_registry(registry_path=target)[0].retention_class=="final"
    with pytest.raises(ValueError,match="POLICY"):
        register_committed_full_artifacts(project_root=tmp_path,transaction_id=transaction_id,registry_path=tmp_path/"bad.jsonl",policy_by_kind={})
