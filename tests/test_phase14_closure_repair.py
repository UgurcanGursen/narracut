import pytest
import shutil
import subprocess
from pathlib import Path
from engine.incremental import plan_incremental_sequences, run_incremental_sequences, sequence_dependency_snapshot
from engine.performance import benchmark_full_av_hash_preserving
from engine.storage_manager import StoragePressurePolicy, StorageQuotaManager, run_with_soft_quota_admission
from engine.rendering.full_render import normalize_mux_probe
from tests.test_phase14_cache_execution import _entry, _payload, _policy


def test_one_changed_sequence_rebuilds_only_that_sequence():
    before=sequence_dependency_snapshot(project_id="p",sequence_input_hashes={"seq_a":"sha256:"+"a"*64,"seq_b":"sha256:"+"b"*64})
    after=sequence_dependency_snapshot(project_id="p",sequence_input_hashes={"seq_a":"sha256:"+"a"*64,"seq_b":"sha256:"+"c"*64})
    assert plan_incremental_sequences(previous=before,current=after)==({"sequence_id":"seq_a","action":"REUSE"},{"sequence_id":"seq_b","action":"REBUILD"})
    called=[]
    result=run_incremental_sequences(previous=before,current=after,rebuilders={"seq_b":lambda:called.append("seq_b")})
    assert called==["seq_b"] and result[0]["action"]=="REUSE" and result[1]["result"] is None


def test_soft_quota_requires_visible_non_mutating_plan(tmp_path):
    item=_payload(b"data"); entry=_entry(item); manager=StorageQuotaManager()
    result=manager.assess_render_admission(managed_root=tmp_path,pressure_policy=StoragePressurePolicy("cache",10**9,0),estimated_bytes=0,policy=_policy(),payloads=(item,),entries=(entry,),retained_artifact_ids=frozenset())
    assert result["status"]=="SOFT_QUOTA_PLAN_REQUIRED" and not list(tmp_path.rglob(".trash"))
    assert run_with_soft_quota_admission(manager=manager,managed_root=tmp_path,pressure_policy=StoragePressurePolicy("cache",10**9,0),estimated_bytes=0,policy=_policy(),payloads=(item,),entries=(entry,),retained_artifact_ids=frozenset(),runner=lambda:pytest.fail("render"))["status"]=="SOFT_QUOTA_PLAN_REQUIRED"


def test_full_av_benchmark_rejects_audio_drift():
    def good(): return {"final_output_bytes":b"mp4","audio_plan_hash":"sha256:"+"a"*64,"filter_script_hash":"sha256:"+"b"*64,"pcm_manifest_hash":"sha256:"+"c"*64}
    assert benchmark_full_av_hash_preserving(baseline=good,candidate=good)["quality_preserved"]
    with pytest.raises(ValueError,match="HASH_CHANGED"):
        benchmark_full_av_hash_preserving(baseline=good,candidate=lambda:{**good(),"audio_plan_hash":"sha256:"+"d"*64})


def test_full_av_benchmark_uses_local_ffmpeg_fixture(tmp_path):
    ffmpeg=Path(shutil.which("ffmpeg") or ""); ffprobe=Path(shutil.which("ffprobe") or "")
    if not ffmpeg.is_file() or not ffprobe.is_file(): pytest.skip("FFmpeg fixture runtime unavailable")
    video=tmp_path/"video.mp4"; pcm=tmp_path/"pcm.wav"
    for command in (([str(ffmpeg),"-y","-f","lavfi","-i","color=c=black:s=64x64:r=30","-t","0.1","-an","-c:v","libx264","-pix_fmt","yuv420p",str(video)]),([str(ffmpeg),"-y","-f","lavfi","-i","anullsrc=r=48000:cl=stereo","-t","0.1","-c:a","pcm_f32le",str(pcm)])):
        assert subprocess.run(command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False).returncode==0
    def producer(index=[0]):
        index[0]+=1; output=tmp_path/f"full-{index[0]}.mp4"; normalize_mux_probe(video_path=video,pcm_paths=[pcm],staged_output=output,ffmpeg=ffmpeg,ffprobe=ffprobe)
        return {"final_output_bytes":output.read_bytes(),"audio_plan_hash":"sha256:"+"a"*64,"filter_script_hash":"sha256:"+"b"*64,"pcm_manifest_hash":"sha256:"+"c"*64}
    assert benchmark_full_av_hash_preserving(baseline=producer,candidate=producer)["quality_preserved"]
