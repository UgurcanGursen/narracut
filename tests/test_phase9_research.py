from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from engine.acquisition.source_engine import (
    AccessibleHtmlAdapter, AccessStatus, AcquisitionAdapterId, DOMRegion,
    ReplaySourcePackage, SourceAdapterRegistry, SourceType,
)
from engine.contracts._canonical_json import encode_canonical_json_bytes
from engine.contracts.domain import policy_snapshot_hash
from engine.contracts.models import DomainPolicySnapshot
from engine.research import (
    ApiBackend, BackendMode, ChronologyBuilder, ClaimStore, ContradictionDetector,
    DomainPromptResolver, FactRecordV1, LLMResultImporter, LLMTaskService, LocalModelBackend,
    RepairTaskBuilder, ReplayBackend, SourceCaptureIngress, TaskPackageBuilder,
    TaskStatus, TaskType, claim_research_policy_from_snapshot,
)
from engine.research.gateway import ResearchError, _hash


PACK_ROOT = Path(__file__).resolve().parents[1] / "domain-packs" / "business-tech"


def _snapshot() -> DomainPolicySnapshot:
    research = {
        "source_priority_policy": {"policy_version": "SOURCE-PRIORITY-POLICY-V1", "ranked_source_types": ["regulator_filing", "company_filing", "official_report", "official_press_release", "trusted_reporting", "feed"], "mandatory_primary_source_types": ["regulator_filing"]},
        "claim_research_policy": {"policy_version": "CLAIM-RESEARCH-POLICY-V1", "allowed_claim_types": ["company_statement", "reported_metric", "market_reaction"], "allowed_claim_statuses": ["reported", "attributed", "contested"], "allowed_authority_tokens": ["primary", "official", "reported"], "allowed_contradiction_kinds": ["value_conflict", "status_conflict"], "allowed_date_precisions": ["day", "month", "year"], "allowed_safe_wording_tokens": ["reported", "attributed", "according_to_source"], "allowed_visible_contradiction_wording_tokens": ["sources", "differ"]},
    }
    resolved = {"policy_bundles": [{"ref": "policy.json", "policy": {"research": research}}], "extensions": {}, "enabled_extensions": [], "overrides": {}}
    data = {"schema_version": "3.0.0", "domain_id": "business-tech", "domain_pack_version": "0.1.0", "profile_id": "dpf_business", "manifest_hash": "sha256:4f5a291f1d992d5227410081b7a8b70f6f921d90ae17363372e1fce6140b618e", "resolved_policy": resolved, "immutable": True, "created_at": "2026-08-05T00:00:00Z", "version": 1}
    digest = policy_snapshot_hash(data)
    return DomainPolicySnapshot(**(data | {"snapshot_id": "dps_" + digest[7:27], "canonical_hash": digest}))


def _task(task_type: TaskType):
    policy = claim_research_policy_from_snapshot(_snapshot())
    task = LLMTaskService().create_task(task_type=task_type, project_id="prj_phase9", policy=policy, backend_mode=BackendMode.MANUAL_UI, prompt_template_ref="prompts/research_discovery.md", domain_pack_root=PACK_ROOT, topic="company results")
    return task, policy


def _response(task, result: dict[str, object]) -> bytes:
    return encode_canonical_json_bytes({"schema_version": "PHASE9-LLM-RESPONSE-V1", "task_id": task.task_id, "task_hash": task.task_hash, "task_type": task.task_type.value, "policy_snapshot_id": task.input_manifest["policy_snapshot_id"], "policy_snapshot_hash": task.input_manifest["policy_snapshot_hash"], "result": result})


def _candidate(policy):
    body = {"canonical_url": "https://example.com/filing", "source_type": "company_filing", "source_label": "Example filing", "publication_date": "2026-01-02", "authority_tokens": ["official"], "rationale_tokens": ["results"]}
    digest = _hash(body)
    return {"candidate_id": "cand_" + digest[7:27], "candidate_hash": digest, **body}


def _submit(store: ClaimStore, task, policy):
    store.put_task(task)
    ready = LLMTaskService().revise_task(previous=task, policy=policy, domain_pack_root=PACK_ROOT, topic="company results", status=TaskStatus.PACKAGE_READY, created_at="2026-08-05T00:00:01Z")
    store.put_task(ready)
    submitted = LLMTaskService().revise_task(previous=ready, policy=policy, domain_pack_root=PACK_ROOT, topic="company results", status=TaskStatus.RESPONSE_SUBMITTED, created_at="2026-08-05T00:00:02Z")
    store.put_task(submitted)
    return submitted


def test_manual_package_discovery_capture_extraction_and_claim_lineage(tmp_path: Path) -> None:
    task, policy = _task(TaskType.SOURCE_DISCOVERY)
    package = TaskPackageBuilder().build(task=task, workspace_root=tmp_path, domain_pack_root=PACK_ROOT, topic="company results", scope_tokens=("results",), domain_profile={"profile_id": "dpf_business"}, resolved_policy={"snapshot": policy.policy_snapshot_id})
    assert (package / "response").is_dir() and (package / "input_manifest.json").is_file()
    store = ClaimStore(tmp_path / "claims.sqlite")
    task = _submit(store, task, policy)
    candidate = _candidate(policy)
    candidates = store.put_candidates(task=task, response=_response(task, {"candidates": [candidate]}), policy=policy)
    text = "Revenue fell 10%."
    replay = ReplaySourcePackage("src_fixture", SourceType.COMPANY_FILING, AcquisitionAdapterId.ACCESSIBLE_HTML, "https://example.com/filing", AccessStatus.ACCESSIBLE, "Example filing", "2026-01-02", text, text, None, (DOMRegion("body/p", text, 0, 0, 1_000_000, 1_000_000),))
    source = SourceCaptureIngress().bind(store=store, candidate=candidates[0], package=replay, adapters=SourceAdapterRegistry((AccessibleHtmlAdapter(),)), project_id="prj_phase9", policy=policy)
    extraction, _ = _task(TaskType.SOURCE_EXTRACTION)
    extraction = _submit(store, extraction, policy)
    fact = {"local_id": "loc_fact", "source_id": source.source_id, "source_content_hash": source.content_hash, "source_span": {"start": 0, "end": len(text)}, "text": text, "kind": "reported_metric", "tokens": ["revenue"]}
    facts = store.import_extraction(task=extraction, payload=_response(extraction, {"facts": [fact], "quotes": [], "numbers": [], "uncertainties": []}), policy=policy)
    normalization, _ = _task(TaskType.CLAIM_NORMALIZATION)
    normalization = _submit(store, normalization, policy)
    claim = {"canonical_text": "Revenue fell 10%.", "claim_type": "reported_metric", "status": "reported", "confidence_millionths": 900000, "fact_local_ids": ["loc_fact"], "contradicting_fact_local_ids": [], "time_start": "2026-01-02", "time_end": "2026-01-02", "visual_potential_tokens": ["chart"], "safe_wording_tokens": ["reported"]}
    claims = store.import_claims(task=normalization, payload=_response(normalization, {"claims": [claim]}), policy=policy, facts_by_local_id={"loc_fact": facts[0]})
    assert claims[0].claim_id.startswith("clm_")
    assert ClaimStore.chronology(claims) == claims
    assert ChronologyBuilder().build(store=store, claims=claims, policy=policy)[0].claim_id == claims[0].claim_id
    assert ContradictionDetector().detect(store=store, claims=claims, policy=policy) == ()
    assert store.export_jsonl(tmp_path / "research.jsonl").read_bytes()
    store.close()


def test_response_rejects_unknown_url_span_and_policy_binding(tmp_path: Path) -> None:
    task, policy = _task(TaskType.SOURCE_DISCOVERY)
    store = ClaimStore(tmp_path / "claims.sqlite")
    task = _submit(store, task, policy)
    bad = _candidate(policy) | {"canonical_url": "https://example.com/filing#fragment"}
    with pytest.raises(ResearchError, match="DISCOVERY_RESULT_INVALID|SOURCE_URL_INVALID|SOURCE_URL_NOT_CANONICAL"):
        store.put_candidates(task=task, response=_response(task, {"candidates": [bad]}), policy=policy)
    wrong = _response(task, {"candidates": [_candidate(policy)]}).replace(task.task_hash.encode(), ("sha256:" + "0" * 64).encode())
    with pytest.raises(ResearchError, match="RESPONSE_CANONICAL_INVALID|RESPONSE_BINDING_INVALID"):
        store.put_candidates(task=task, response=wrong, policy=policy)
    store.close()


def test_repair_is_scoped_and_provider_backends_are_unavailable(tmp_path: Path) -> None:
    task, policy = _task(TaskType.SOURCE_DISCOVERY)
    repair, path = RepairTaskBuilder().build(failed_task=task, policy=policy, service=LLMTaskService(), workspace_root=tmp_path, domain_pack_root=PACK_ROOT, topic="company results", scope_tokens=("results",), domain_profile={"profile_id": "dpf_business"}, resolved_policy={"snapshot": policy.policy_snapshot_id}, original_response=b"{}", validation_errors=("source_url_invalid",))
    assert repair.parent_task_id == task.task_id
    assert (path / "response" / "validation_errors.json").is_file()
    with pytest.raises(ResearchError, match="API_BACKEND_UNAVAILABLE"):
        ApiBackend().response_for(task)
    with pytest.raises(ResearchError, match="LOCAL_MODEL_UNAVAILABLE"):
        LocalModelBackend().response_for(task)


def test_replay_rejection_immutable_revision_and_second_pack_prompt(tmp_path: Path) -> None:
    task, policy = _task(TaskType.SOURCE_DISCOVERY)
    replay = LLMTaskService().create_task(task_type=TaskType.SOURCE_DISCOVERY, project_id="prj_phase9", policy=policy, backend_mode=BackendMode.REPLAY, prompt_template_ref="prompts/research_discovery.md", domain_pack_root=PACK_ROOT, topic="company results")
    accepted = _response(replay, {"candidates": []})
    assert ReplayBackend({replay.task_hash: accepted}).response_for(replay) == accepted
    revision = LLMTaskService().revise_task(previous=task, policy=policy, domain_pack_root=PACK_ROOT, topic="company results", status=TaskStatus.REJECTED, created_at="2026-08-05T00:01:00Z", completed_at="2026-08-05T00:01:00Z")
    assert revision.logical_task_id == task.logical_task_id and revision.supersedes_task_id == task.task_id
    store = ClaimStore(tmp_path / "claims.sqlite")
    task = _submit(store, task, policy)
    with pytest.raises(ResearchError):
        LLMResultImporter().import_result(store=store, task=task, payload=b"{}", policy=policy)
    assert store.connection.execute("SELECT accepted FROM phase9_responses").fetchone() == (0,)
    second_pack = tmp_path / "sample-domain" / "prompts"; second_pack.mkdir(parents=True)
    prompt = second_pack / "research.md"; prompt.write_text("generic research output", encoding="utf-8")
    assert DomainPromptResolver().resolve(pack_root=second_pack.parent, prompt_template_ref="prompts/research.md") == "generic research output"
    store.close()


def test_store_rejects_forged_record_and_second_accepted_response(tmp_path: Path) -> None:
    task, policy = _task(TaskType.SOURCE_DISCOVERY)
    store = ClaimStore(tmp_path / "claims.sqlite"); task = _submit(store, task, policy)
    valid = _response(task, {"candidates": []})
    LLMResultImporter().import_result(store=store, task=task, payload=valid, policy=policy)
    changed = _response(task, {"candidates": [_candidate(policy)]})
    with pytest.raises(ResearchError, match="RESPONSE_ALREADY_ACCEPTED"):
        LLMResultImporter().import_result(store=store, task=task, payload=changed, policy=policy)
    task2, _ = _task(TaskType.CLAIM_NORMALIZATION); task2 = _submit(store, task2, policy)
    fake_fact = replace(
        FactRecordV1("fact_aaaaaaaaaaaaaaaaaaaa", "sha256:" + "a" * 64, "prj_phase9", policy.policy_snapshot_id,
                     policy.policy_snapshot_hash, "src_missing", "sha256:" + "b" * 64, task2.task_id,
                     task2.task_hash, "reported_metric", "fake", 0, 4, None, None, None, ("fake",)),
        text="forged",
    )
    with pytest.raises(ResearchError, match="FACT_UNKNOWN"):
        store.import_claims(task=task2, payload=_response(task2, {"claims": [{"canonical_text": "Forged", "claim_type": "reported_metric", "status": "reported", "confidence_millionths": 1, "fact_local_ids": ["loc_fake"], "contradicting_fact_local_ids": [], "time_start": None, "time_end": None, "visual_potential_tokens": ["chart"], "safe_wording_tokens": ["reported"]}]}), policy=policy, facts_by_local_id={"loc_fake": fake_fact})
    store.close()
