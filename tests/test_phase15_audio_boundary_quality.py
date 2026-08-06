from __future__ import annotations
import json
from dataclasses import replace
from pathlib import Path
from engine.contracts import DomainPackRegistry, DomainPolicyResolver, SchemaCatalog
from engine.contracts.domain import policy_snapshot_hash
from engine.contracts.audio_edl import compile_audio_edl
from engine.contracts.word_to_frame import TemporalFrameRate
from engine.validation.audio_boundary_quality import validate_audio_boundary_quality
from engine.validation.run_evidence import evaluate_quality_gate, serialize_jsonl
from tests.test_audio_edl_replay import _all_track_kwargs
ROOT=Path(__file__).resolve().parents[1]
def _snapshot():
 c=SchemaCatalog(ROOT/"shared-schemas"/"v3"); r=DomainPackRegistry([ROOT/"domain-packs"],c); r.discover(); p=json.loads((ROOT/"samples"/"v3"/"business-tech"/"workspace.json").read_text())["domain"]["profile"]; return DomainPolicyResolver(c).resolve(r.get("business-tech","0.1.0"),p)[0]
def _audio(): return compile_audio_edl(**_all_track_kwargs(rate=TemporalFrameRate(30,1)))
def _check(snapshot,audio): return validate_audio_boundary_quality(run_id="run_audio_boundary",timestamp_utc="2026-08-06T00:00:00Z",audio_edl=audio,domain_snapshot=snapshot,expected_policy_snapshot_id=snapshot.snapshot_id,expected_policy_snapshot_hash=snapshot.canonical_hash)
def test_replay_boundary_decisions_are_policy_bound_and_pass_at_declared_threshold():
 o=_check(_snapshot(),_audio()); assert o.status=="PASSED"; assert evaluate_quality_gate(source=serialize_jsonl((o,)),required_checks={"audio_boundary_quality":o.policy_hash}).decision=="PASS"
def test_lowered_immutable_threshold_requires_visible_remix_warning():
 s=_snapshot(); resolved=json.loads(json.dumps(s.resolved_policy)); resolved["policy_bundles"][0]["policy"]["audio"]["audio_boundary_validation_policy"]["max_microfade_boundary_count"]=4
 s=replace(s,resolved_policy=resolved); s=replace(s,canonical_hash=policy_snapshot_hash({n:getattr(s,n) for n in s.__dataclass_fields__}))
 o=_check(s,_audio()); assert (o.status,o.public_code)==("WARNING","AUDIO_BOUNDARY_REMIX_REQUIRED")
