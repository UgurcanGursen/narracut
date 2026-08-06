import pytest
from engine.incremental import plan_incremental_sequences, sequence_dependency_snapshot
from engine.performance import benchmark_full_av_hash_preserving
from engine.storage_manager import StoragePressurePolicy, StorageQuotaManager
from tests.test_phase14_cache_execution import _entry, _payload, _policy


def test_one_changed_sequence_rebuilds_only_that_sequence():
    before=sequence_dependency_snapshot(project_id="p",sequence_input_hashes={"seq_a":"sha256:"+"a"*64,"seq_b":"sha256:"+"b"*64})
    after=sequence_dependency_snapshot(project_id="p",sequence_input_hashes={"seq_a":"sha256:"+"a"*64,"seq_b":"sha256:"+"c"*64})
    assert plan_incremental_sequences(previous=before,current=after)==({"sequence_id":"seq_a","action":"REUSE"},{"sequence_id":"seq_b","action":"REBUILD"})


def test_soft_quota_requires_visible_non_mutating_plan(tmp_path):
    item=_payload(b"data"); entry=_entry(item); manager=StorageQuotaManager()
    result=manager.assess_render_admission(managed_root=tmp_path,pressure_policy=StoragePressurePolicy("cache",10**9,0),estimated_bytes=0,policy=_policy(),payloads=(item,),entries=(entry,),retained_artifact_ids=frozenset())
    assert result["status"]=="SOFT_QUOTA_PLAN_REQUIRED" and not list(tmp_path.rglob(".trash"))


def test_full_av_benchmark_rejects_audio_drift():
    def good(): return {"final_output_bytes":b"mp4","audio_plan_hash":"sha256:"+"a"*64,"filter_script_hash":"sha256:"+"b"*64,"pcm_manifest_hash":"sha256:"+"c"*64}
    assert benchmark_full_av_hash_preserving(baseline=good,candidate=good)["quality_preserved"]
    with pytest.raises(ValueError,match="HASH_CHANGED"):
        benchmark_full_av_hash_preserving(baseline=good,candidate=lambda:{**good(),"audio_plan_hash":"sha256:"+"d"*64})
