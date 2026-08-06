from __future__ import annotations

import hashlib
import json
import re
from dataclasses import replace
from pathlib import Path

from engine.contracts import (
    DomainPackRegistry, DomainPolicyResolver, NORMALIZATION_PROFILE_HASH_V1,
    SchemaCatalog, materialize_canonical_narration, normalization_profile_hash,
)
from engine.contracts._canonical_json import encode_canonical_json_bytes
from engine.contracts.domain import policy_snapshot_hash
from engine.research.store import ClaimRecordV1, _claim_projection
from engine.validation.final_narration_safety import validate_final_narration_safety
from engine.validation.run_evidence import evaluate_quality_gate, serialize_jsonl
from tests.test_canonical_narration import _initial_lineage_manifest


ROOT = Path(__file__).resolve().parents[1]
RUN = "run_final_narration"
STAMP = "2026-08-06T00:00:00Z"


def _snapshot():
    catalog = SchemaCatalog(ROOT / "shared-schemas" / "v3")
    registry = DomainPackRegistry([ROOT / "domain-packs"], catalog)
    registry.discover()
    profile = json.loads((ROOT / "samples" / "v3" / "business-tech" / "workspace.json").read_text(encoding="utf-8"))["domain"]["profile"]
    return DomainPolicyResolver(catalog).resolve(registry.get("business-tech", "0.1.0"), profile)[0]


def _claim(snapshot, *, status="reported", wording=("reported",)):
    raw = {
        "project_id": "prj_safety", "policy_snapshot_id": snapshot.snapshot_id,
        "policy_snapshot_hash": snapshot.canonical_hash, "task_id": "task_safety",
        "task_hash": "sha256:" + "a" * 64, "canonical_text": "Revenue fell.",
        "claim_type": "reported_metric", "status": status, "confidence_millionths": 900000,
        "fact_ids": ("fact_safety",), "contradicting_fact_ids": (), "time_start": None,
        "time_end": None, "visual_potential_tokens": ("chart",),
        "safe_wording_tokens": wording,
    }
    provisional = ClaimRecordV1("", "", **raw)
    digest = "sha256:" + hashlib.sha256(encode_canonical_json_bytes(_claim_projection(provisional))).hexdigest()
    return ClaimRecordV1("clm_" + digest[7:27], digest, **raw)


def _narration(claim: ClaimRecordV1, source="Reported revenue fell."):
    profile = {
        "hash_scope_version": NORMALIZATION_PROFILE_HASH_V1, "language": "en", "locale": "en-US",
        "profile_id": "nprof_safety", "profile_version": "1.0.0", "tokenization_rule_version": "safety-v1",
        "number_policy_id": "num_none_v1", "pronunciation_policy_id": "pron_none_v1", "lexical_alias_policy_id": "alias_none_v1",
    }
    profile["profile_hash"] = normalization_profile_hash(profile)
    tokens = []
    words = []
    ordinal = 0
    for order, match in enumerate(re.finditer(r"[A-Za-z]+|[.]", source)):
        value = match.group(0)
        spoken = value != "."
        tokens.append({"kind": "SPOKEN" if spoken else "PUNCTUATION", "display_text": value,
            "normalized_alignment_text": value.casefold() if spoken else None, "text_order": order,
            "canonical_word_ordinal": ordinal if spoken else None, "source_start": match.start(), "source_end": match.end(),
            "section_order": 0, "paragraph_order": 0, "sentence_order": 0,
            "trace_refs": [claim.claim_id] if spoken else [], "extensions": {}})
        if spoken:
            words.append({"text_order": order, "canonical_word_ordinal": ordinal})
            ordinal += 1
    value = {"schema_version": "NARRATION-REVISION-V1", "project_id": "prj_safety", "document_id": "nardoc_safety",
        "language": "en", "locale": "en-US", "parent_revision_id": None, "normalization_profile": profile,
        "sections": [{"order": 0, "source_start": 0, "source_end": len(source), "paragraphs": [{"order": 0,
            "source_start": 0, "source_end": len(source), "sentences": [{"order": 0, "source_start": 0,
            "source_end": len(source), "segmentation_rule_version": "safety-sentence-v1", "extensions": {}}], "extensions": {}}], "extensions": {}}],
        "text_tokens": tokens, "canonical_words": words, "document_extensions": {}, "revision_extensions": {}}
    source_bytes = source.encode("utf-8")
    value["lineage_manifest"] = _initial_lineage_manifest(value, source_bytes)
    return materialize_canonical_narration(source_bytes, value).revision


def _validate(snapshot, revision, claim, **overrides):
    values = {"run_id": RUN, "timestamp_utc": STAMP, "narration_revision": revision,
        "claims": (claim,), "expected_claim_pairs": ((claim.claim_id, claim.claim_hash),), "domain_snapshot": snapshot,
        "expected_domain_id": "business-tech", "expected_domain_pack_version": "0.1.0",
        "expected_policy_snapshot_id": snapshot.snapshot_id, "expected_policy_snapshot_hash": snapshot.canonical_hash}
    values.update(overrides)
    return validate_final_narration_safety(**values)


def test_compatible_domain_claim_and_sentence_safe_wording_pass():
    snapshot = _snapshot(); claim = _claim(snapshot); observation = _validate(snapshot, _narration(claim), claim)
    assert observation.status == "PASSED"
    assert evaluate_quality_gate(source=serialize_jsonl((observation,)), required_checks={"final_narration_safety": observation.policy_hash}).decision == "PASS"


def test_domain_version_mismatch_and_missing_validation_extension_fail_closed():
    snapshot = _snapshot(); claim = _claim(snapshot); revision = _narration(claim)
    mismatch = _validate(snapshot, revision, claim, expected_domain_pack_version="0.1.1")
    assert (mismatch.status, mismatch.public_code) == ("FAILED", "DOMAIN_PACK_COMPATIBILITY_MISMATCH")
    resolved = json.loads(json.dumps(snapshot.resolved_policy))
    resolved["extensions"]["validation_rules"] = [row for row in resolved["extensions"]["validation_rules"] if row["name"] != "final_narration_safety"]
    altered = replace(snapshot, resolved_policy=resolved)
    altered = replace(altered, canonical_hash=policy_snapshot_hash({name: getattr(altered, name) for name in altered.__dataclass_fields__}))
    claim = _claim(altered); revision = _narration(claim)
    missing = _validate(altered, revision, claim)
    assert (missing.status, missing.public_code) == ("FAILED", "DOMAIN_VALIDATION_EXTENSION_UNAVAILABLE")


def test_unsupported_legal_status_and_blocked_wording_cannot_pass():
    snapshot = _snapshot(); legal_claim = _claim(snapshot, status="convicted")
    unsupported = _validate(snapshot, _narration(legal_claim), legal_claim)
    assert (unsupported.status, unsupported.public_code) == ("FAILED", "NARRATION_CLAIM_STATUS_UNSUPPORTED")
    claim = _claim(snapshot)
    blocked = _validate(snapshot, _narration(claim, "Reported guilty revenue."), claim)
    assert (blocked.status, blocked.public_code) == ("FAILED", "NARRATION_BLOCKED_WORDING")


def test_omitted_claim_trace_or_sentence_safe_wording_cannot_pass():
    snapshot = _snapshot(); claim = _claim(snapshot)
    no_wording = _narration(claim, "Revenue fell.")
    observation = _validate(snapshot, no_wording, claim)
    assert (observation.status, observation.public_code) == ("FAILED", "NARRATION_SAFETY_BINDING_INVALID")
