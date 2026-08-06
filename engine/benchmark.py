"""Phase 16 deterministic editorial-composition benchmark reducer."""
from __future__ import annotations
import hashlib
from dataclasses import dataclass
from typing import Any
from engine.contracts._canonical_json import encode_canonical_json_bytes
from engine.contracts.domain import policy_snapshot_hash
from engine.contracts.models import DomainPolicySnapshot
from engine.contracts.edl import VideoEdlArtifact, serialize_video_edl
from engine.contracts.audio_edl import AudioEdlArtifact, serialize_audio_edl
from engine.editorial_integration import ExecutableEditorialPlanV1, canonical_executable_editorial_plan_json

BENCHMARK_V1="PHASE16-BENCHMARK-V1"
def _hash(v:object)->str:return "sha256:"+hashlib.sha256(encode_canonical_json_bytes(v)).hexdigest()
def _fail(c:str)->None:raise ValueError(c)
@dataclass(frozen=True)
class BenchmarkReportV1:
    report_id:str; report_hash:str; project_id:str; domain_id:str; domain_pack_version:str; policy_snapshot_id:str; policy_snapshot_hash:str; executable_plan_id:str; executable_plan_hash:str; metrics:dict[str,Any]
    def data(self)->dict[str,Any]:return {"schema_version":BENCHMARK_V1,**self.__dict__}
def canonical_benchmark_json(value:BenchmarkReportV1)->bytes:
    if type(value)is not BenchmarkReportV1:_fail("BENCHMARK_REPORT_INVALID")
    return encode_canonical_json_bytes(value.data())
def compile_benchmark(*,snapshot:DomainPolicySnapshot,plan:ExecutableEditorialPlanV1,videos:tuple[VideoEdlArtifact,...],audios:tuple[AudioEdlArtifact,...])->BenchmarkReportV1:
    if type(snapshot)is not DomainPolicySnapshot or not snapshot.immutable or snapshot.canonical_hash!=policy_snapshot_hash({n:getattr(snapshot,n) for n in snapshot.__dataclass_fields__}):_fail("BENCHMARK_DOMAIN_MISMATCH")
    if type(plan)is not ExecutableEditorialPlanV1 or type(videos)is not tuple or type(audios)is not tuple:_fail("BENCHMARK_INPUT_UNAVAILABLE")
    try: canonical_executable_editorial_plan_json(plan); [serialize_video_edl(v) for v in videos]; [serialize_audio_edl(a) for a in audios]
    except Exception as exc:raise ValueError("BENCHMARK_INPUT_UNAVAILABLE") from exc
    p=plan.data(); rows=p["sequences"]
    if len(rows)!=len(videos) or len(rows)!=len(audios) or any(v.sequence_id!=r["executable_sequence_id"] or a.sequence_id!=r["executable_sequence_id"] for r,v,a in zip(rows,videos,audios,strict=True)):_fail("BENCHMARK_INPUT_UNAVAILABLE")
    video_events=[event for v in videos for track in v.tracks for event in track.events]; audio_events=[event for a in audios for track in a.tracks for event in track.events]
    duration=sum(v.duration_frames*1000*v.fps_denominator//v.fps_numerator for v in videos)
    templates:dict[str,int]={}; modes:dict[str,int]={}; tracks:dict[str,int]={}; boundaries:dict[str,int]={}
    for r in rows: templates[str(r["template_capability_id_hash"][0])]=templates.get(str(r["template_capability_id_hash"][0]),0)+1; modes[str(r["execution_mode"])]=modes.get(str(r["execution_mode"]),0)+1
    for a in audios:
        for t in a.tracks: tracks[t.track.value]=tracks.get(t.track.value,0)+len(t.events)
        for d in a.boundary_decisions: boundaries[d.policy.value]=boundaries.get(d.policy.value,0)+1
    metrics={"sequence_count":len(rows),"duration_ms":duration,"video_edit_event_count":len(video_events),"video_edit_events_per_minute":0 if not duration else len(video_events)*60000//duration,"audio_event_count":len(audio_events),"template_distribution":dict(sorted(templates.items())),"execution_mode_distribution":dict(sorted(modes.items())),"audio_track_distribution":dict(sorted(tracks.items())),"audio_boundary_distribution":dict(sorted(boundaries.items())),"source_treatment_distribution":"UNAVAILABLE","stock_ratio":"UNAVAILABLE","chart_ratio":"UNAVAILABLE","quote_card_ratio":"UNAVAILABLE","kinetic_text_density":"UNAVAILABLE","actual_source_audio_usage":"UNAVAILABLE"}
    body={"project_id":p["project_id"],"domain_id":snapshot.domain_id,"domain_pack_version":snapshot.domain_pack_version,"policy_snapshot_id":snapshot.snapshot_id,"policy_snapshot_hash":snapshot.canonical_hash,"executable_plan_id":p["executable_editorial_plan_id"],"executable_plan_hash":p["executable_editorial_plan_hash"],"metrics":metrics}; h=_hash(body); return BenchmarkReportV1("bmr_"+h[7:27],h,**body)
