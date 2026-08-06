"""Phase 15 planned audio-boundary risk gate; never decodes or mixes media."""
from __future__ import annotations
import hashlib
from dataclasses import dataclass
from engine.contracts._canonical_json import encode_canonical_json_bytes
from engine.contracts.domain import policy_snapshot_hash
from engine.contracts.models import DomainPolicySnapshot
from engine.contracts.audio_edl import AudioBoundaryPolicy, AudioEdlArtifact, serialize_audio_edl
from engine.validation.run_evidence import EvidenceReference, RunObservation, build_observation

def _hash(value: object) -> str: return "sha256:" + hashlib.sha256(encode_canonical_json_bytes(value)).hexdigest()
def _fail(code: str) -> None: raise ValueError(code)

@dataclass(frozen=True)
class AudioBoundaryValidationPolicyV1:
    policy_hash: str; max_trim_samples: int; max_microfade_samples: int; max_long_editorial_fade_samples: int; max_microfade_boundary_count: int

def audio_boundary_policy_from_snapshot(snapshot: DomainPolicySnapshot) -> AudioBoundaryValidationPolicyV1:
    data={name:getattr(snapshot,name) for name in snapshot.__dataclass_fields__}
    if type(snapshot) is not DomainPolicySnapshot or not snapshot.immutable or snapshot.canonical_hash != policy_snapshot_hash(data): _fail("AUDIO_BOUNDARY_POLICY_UNAVAILABLE")
    resolved=snapshot.resolved_policy; rules=resolved.get("extensions",{}).get("validation_rules") if type(resolved) is dict else None
    bundles=resolved.get("policy_bundles") if type(resolved) is dict else None
    matches=[row["policy"]["audio"]["audio_boundary_validation_policy"] for row in bundles or () if type(row) is dict and type(row.get("policy")) is dict and type(row["policy"].get("audio")) is dict and "audio_boundary_validation_policy" in row["policy"]["audio"]]
    fields={"policy_version","required_validation_rule","max_trim_samples","max_microfade_samples","max_long_editorial_fade_samples","max_microfade_boundary_count"}
    if type(rules) is not list or sum(type(x) is dict and x.get("name")=="audio_boundary_quality" for x in rules)!=1 or len(matches)!=1 or type(matches[0]) is not dict or set(matches[0])!=fields or matches[0].get("policy_version")!="AUDIO-BOUNDARY-VALIDATION-POLICY-V1" or matches[0].get("required_validation_rule")!="audio_boundary_quality": _fail("AUDIO_BOUNDARY_POLICY_UNAVAILABLE")
    raw=matches[0]; values=tuple(raw[x] for x in ("max_trim_samples","max_microfade_samples","max_long_editorial_fade_samples","max_microfade_boundary_count"))
    if any(type(x) is not int or x<0 for x in values): _fail("AUDIO_BOUNDARY_POLICY_UNAVAILABLE")
    return AudioBoundaryValidationPolicyV1(_hash({"snapshot_hash":snapshot.canonical_hash,**raw}),*values)

def validate_audio_boundary_quality(*, run_id:str, timestamp_utc:str, audio_edl:AudioEdlArtifact, domain_snapshot:DomainPolicySnapshot, expected_policy_snapshot_id:str, expected_policy_snapshot_hash:str, first_ordinal:int=1)->RunObservation:
    if type(audio_edl) is not AudioEdlArtifact or type(run_id) is not str or not run_id or type(timestamp_utc) is not str or type(first_ordinal) is not int or first_ordinal<1: _fail("AUDIO_BOUNDARY_REQUEST_INVALID")
    try: serialize_audio_edl(audio_edl)
    except Exception as exc: raise ValueError("AUDIO_BOUNDARY_EDL_INVALID") from exc
    if (domain_snapshot.snapshot_id,domain_snapshot.canonical_hash)!=(expected_policy_snapshot_id,expected_policy_snapshot_hash): _fail("AUDIO_BOUNDARY_POLICY_MISMATCH")
    policy=audio_boundary_policy_from_snapshot(domain_snapshot)
    refhash=_hash({"audio_edl_id":audio_edl.audio_edl_id,"audio_edl_hash":audio_edl.audio_edl_hash,"policy_hash":policy.policy_hash})
    reference=EvidenceReference("PHASE15-EVIDENCE-REFERENCE-V1","audio_boundary","boundary_"+refhash[7:39],refhash,run_id)
    decisions=audio_edl.boundary_decisions
    invalid=any(max(row.left_trim_samples,row.right_trim_samples)>policy.max_trim_samples or max(row.fade_in_samples,row.fade_out_samples)> (policy.max_long_editorial_fade_samples if row.policy is AudioBoundaryPolicy.LONG_EDITORIAL_FADE else policy.max_microfade_samples) for row in decisions)
    risky=sum(row.policy is AudioBoundaryPolicy.ZERO_CROSSING_MICROFADE and any((row.left_trim_samples,row.right_trim_samples,row.fade_in_samples,row.fade_out_samples)) for row in decisions)
    status,code=("FAILED","AUDIO_BOUNDARY_POLICY_VIOLATION") if invalid else (("WARNING","AUDIO_BOUNDARY_REMIX_REQUIRED") if risky>policy.max_microfade_boundary_count else ("PASSED",None))
    return build_observation(run_id=run_id,ordinal=first_ordinal,timestamp_utc=timestamp_utc,category="quality_gate",event="check_evaluated",status=status,producer="phase15",evidence_references=(reference,),check_id="audio_boundary_quality",policy_hash=policy.policy_hash,public_code=code)
