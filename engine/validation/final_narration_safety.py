"""Phase 15 domain-bound final-narration safety gate; no rendering or media I/O."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from engine.contracts._canonical_json import encode_canonical_json_bytes
from engine.contracts.domain import policy_snapshot_hash
from engine.contracts.models import DomainPolicySnapshot
from engine.contracts.narration import NarrationRevision, _is_materialized_narration_revision
from engine.research.gateway import ClaimResearchPolicyV1, claim_research_policy_from_snapshot
from engine.research.store import ClaimRecordV1, _claim_projection
from engine.validation.run_evidence import EvidenceReference, RunObservation, build_observation


FINAL_NARRATION_VALIDATION_POLICY_V1 = "FINAL-NARRATION-VALIDATION-POLICY-V1"


def _fail(code: str) -> None:
    raise ValueError(code)


def _hash(value: object) -> str:
    return "sha256:" + hashlib.sha256(encode_canonical_json_bytes(value)).hexdigest()


def _hash_ok(value: object) -> bool:
    return type(value) is str and re.fullmatch(r"sha256:[0-9a-f]{64}", value) is not None


def _pairs(value: object) -> tuple[tuple[str, str], ...]:
    if type(value) is not tuple or not value:
        _fail("NARRATION_CLAIM_PAIRS_INVALID")
    pairs = tuple(value)
    if (any(type(item) is not tuple or len(item) != 2 or type(item[0]) is not str
            or not item[0].startswith("clm_") or not _hash_ok(item[1]) for item in pairs)
            or len(set(pairs)) != len(pairs) or tuple(sorted(pairs)) != pairs):
        _fail("NARRATION_CLAIM_PAIRS_INVALID")
    return pairs


def _tokens(value: object) -> tuple[str, ...]:
    if (type(value) not in {list, tuple} or not value or any(type(item) is not str
            or not re.fullmatch(r"[a-z][a-z0-9_]*", item) for item in value)
            or len(set(value)) != len(value)):
        _fail("DOMAIN_VALIDATION_EXTENSION_UNAVAILABLE")
    return tuple(value)


@dataclass(frozen=True)
class FinalNarrationValidationPolicyV1:
    policy_snapshot_id: str
    policy_snapshot_hash: str
    policy_hash: str
    allowed_claim_statuses: tuple[str, ...]
    allowed_safe_wording_tokens: tuple[str, ...]
    blocked_wording_tokens: tuple[str, ...]


def final_narration_policy_from_snapshot(snapshot: DomainPolicySnapshot) -> FinalNarrationValidationPolicyV1:
    """Resolve the one declared final-narration extension or fail closed."""
    if type(snapshot) is not DomainPolicySnapshot or not snapshot.immutable:
        _fail("DOMAIN_VALIDATION_EXTENSION_UNAVAILABLE")
    snapshot_data = {name: getattr(snapshot, name) for name in snapshot.__dataclass_fields__}
    if snapshot.canonical_hash != policy_snapshot_hash(snapshot_data):
        _fail("DOMAIN_VALIDATION_EXTENSION_UNAVAILABLE")
    resolved = snapshot.resolved_policy
    if type(resolved) is not dict or type(resolved.get("extensions")) is not dict:
        _fail("DOMAIN_VALIDATION_EXTENSION_UNAVAILABLE")
    rules = resolved["extensions"].get("validation_rules")
    if type(rules) is not list or sum(type(row) is dict and row.get("name") == "final_narration_safety" for row in rules) != 1:
        _fail("DOMAIN_VALIDATION_EXTENSION_UNAVAILABLE")
    matches: list[object] = []
    bundles = resolved.get("policy_bundles")
    if type(bundles) is list:
        for bundle in bundles:
            raw_policy = bundle.get("policy") if type(bundle) is dict else None
            safety = raw_policy.get("safety") if type(raw_policy) is dict else None
            if type(safety) is dict and "final_narration_validation_policy" in safety:
                matches.append(safety["final_narration_validation_policy"])
    required = {"policy_version", "required_validation_rule", "allowed_claim_statuses", "allowed_safe_wording_tokens", "blocked_wording_tokens"}
    if (len(matches) != 1 or type(matches[0]) is not dict or set(matches[0]) != required
            or matches[0].get("policy_version") != FINAL_NARRATION_VALIDATION_POLICY_V1
            or matches[0].get("required_validation_rule") != "final_narration_safety"):
        _fail("DOMAIN_VALIDATION_EXTENSION_UNAVAILABLE")
    raw = matches[0]
    policy = FinalNarrationValidationPolicyV1(
        snapshot.snapshot_id, snapshot.canonical_hash,
        _hash({"snapshot_hash": snapshot.canonical_hash, **raw}),
        _tokens(raw["allowed_claim_statuses"]), _tokens(raw["allowed_safe_wording_tokens"]),
        _tokens(raw["blocked_wording_tokens"]),
    )
    try:
        research = claim_research_policy_from_snapshot(snapshot)
    except Exception as exc:
        raise ValueError("DOMAIN_VALIDATION_EXTENSION_UNAVAILABLE") from exc
    if (not set(policy.allowed_claim_statuses).issubset(research.allowed_claim_statuses)
            or not set(policy.allowed_safe_wording_tokens).issubset(research.allowed_safe_wording_tokens)):
        _fail("DOMAIN_VALIDATION_EXTENSION_UNAVAILABLE")
    return policy


def final_narration_safety_reference(*, run_id: str, revision: NarrationRevision,
                                     claim_pairs: tuple[tuple[str, str], ...],
                                     policy_hash: str) -> EvidenceReference:
    if not _is_materialized_narration_revision(revision) or not _hash_ok(policy_hash):
        _fail("NARRATION_SAFETY_REFERENCE_INVALID")
    digest = _hash({"revision_id": revision.revision_id, "revision_hash": revision.revision_hash,
                    "claim_pairs": [list(item) for item in claim_pairs], "policy_hash": policy_hash})
    return EvidenceReference("PHASE15-EVIDENCE-REFERENCE-V1", "narration_safety",
                             "narration_" + digest[7:39], digest, run_id)


def _sentence_texts(revision: NarrationRevision) -> dict[str, str]:
    spans: dict[str, list[int]] = {}
    for token in revision.text_tokens:
        if token.kind.value == "SPOKEN":
            span = spans.setdefault(token.sentence_id, [token.source_start, token.source_end])
            span[0] = min(span[0], token.source_start)
            span[1] = max(span[1], token.source_end)
    return {key: revision.source_text[start:end].casefold() for key, (start, end) in spans.items()}


def _phrase_present(text: str, phrase: str) -> bool:
    return re.search(r"(?<!\\w)" + re.escape(phrase.replace("_", " ")) + r"(?!\\w)", text.casefold()) is not None


def _validate_claims(*, claims: object, pairs: tuple[tuple[str, str], ...], project_id: str,
                     research: ClaimResearchPolicyV1, policy: FinalNarrationValidationPolicyV1,
                     revision: NarrationRevision) -> str | None:
    if type(claims) is not tuple or len(claims) != len(pairs) or any(type(item) is not ClaimRecordV1 for item in claims):
        _fail("NARRATION_CLAIMS_INVALID")
    rows = {(item.claim_id, item.claim_hash): item for item in claims}
    if len(rows) != len(claims) or tuple(sorted(rows)) != pairs:
        return "NARRATION_CLAIM_STATUS_UNSUPPORTED"
    texts = _sentence_texts(revision)
    expected_ids = {pair[0] for pair in pairs}
    trace_sentences: dict[str, set[str]] = {}
    for token in revision.text_tokens:
        for reference in token.trace_refs:
            if reference.startswith("clm_"):
                if reference not in expected_ids:
                    return "NARRATION_SAFETY_BINDING_INVALID"
                trace_sentences.setdefault(reference, set()).add(token.sentence_id)
    for pair in pairs:
        claim = rows[pair]
        if (claim.claim_hash != _hash(_claim_projection(claim))
                or claim.claim_id != "clm_" + claim.claim_hash[7:27]
                or claim.project_id != project_id
                or (claim.policy_snapshot_id, claim.policy_snapshot_hash) != (research.policy_snapshot_id, research.policy_snapshot_hash)
                or claim.status not in policy.allowed_claim_statuses or not claim.safe_wording_tokens
                or not set(claim.safe_wording_tokens).issubset(policy.allowed_safe_wording_tokens)):
            return "NARRATION_CLAIM_STATUS_UNSUPPORTED"
        sentences = trace_sentences.get(claim.claim_id, set())
        if not sentences or not any(any(_phrase_present(texts[sentence], wording) for wording in claim.safe_wording_tokens) for sentence in sentences):
            return "NARRATION_SAFETY_BINDING_INVALID"
    return None


def validate_final_narration_safety(*, run_id: str, timestamp_utc: str,
                                    narration_revision: NarrationRevision,
                                    claims: tuple[ClaimRecordV1, ...],
                                    expected_claim_pairs: tuple[tuple[str, str], ...],
                                    domain_snapshot: DomainPolicySnapshot,
                                    expected_domain_id: str,
                                    expected_domain_pack_version: str,
                                    expected_policy_snapshot_id: str,
                                    expected_policy_snapshot_hash: str,
                                    first_ordinal: int = 1) -> RunObservation:
    """Emit one immutable domain/claim/text safety check; never changes narration."""
    if (type(run_id) is not str or not run_id or type(timestamp_utc) is not str or type(first_ordinal) is not int or first_ordinal < 1
            or type(expected_domain_id) is not str or not expected_domain_id or type(expected_domain_pack_version) is not str or not expected_domain_pack_version
            or type(domain_snapshot) is not DomainPolicySnapshot or not _is_materialized_narration_revision(narration_revision)):
        _fail("NARRATION_SAFETY_REQUEST_INVALID")
    pairs = _pairs(expected_claim_pairs)
    compatible = (domain_snapshot.domain_id, domain_snapshot.domain_pack_version, domain_snapshot.snapshot_id, domain_snapshot.canonical_hash) == (
        expected_domain_id, expected_domain_pack_version, expected_policy_snapshot_id, expected_policy_snapshot_hash)
    if not compatible:
        policy_hash, code = domain_snapshot.canonical_hash, "DOMAIN_PACK_COMPATIBILITY_MISMATCH"
    else:
        try:
            policy = final_narration_policy_from_snapshot(domain_snapshot)
            policy_hash = policy.policy_hash
            if any(_phrase_present(narration_revision.source_text, item) for item in policy.blocked_wording_tokens):
                code = "NARRATION_BLOCKED_WORDING"
            else:
                code = _validate_claims(claims=claims, pairs=pairs, project_id=narration_revision.project_id,
                    research=claim_research_policy_from_snapshot(domain_snapshot), policy=policy, revision=narration_revision)
        except ValueError as exc:
            if str(exc) != "DOMAIN_VALIDATION_EXTENSION_UNAVAILABLE":
                raise
            policy_hash, code = domain_snapshot.canonical_hash, "DOMAIN_VALIDATION_EXTENSION_UNAVAILABLE"
    reference = final_narration_safety_reference(run_id=run_id, revision=narration_revision,
        claim_pairs=pairs, policy_hash=policy_hash)
    return build_observation(run_id=run_id, ordinal=first_ordinal, timestamp_utc=timestamp_utc,
        category="quality_gate", event="check_evaluated", status="PASSED" if code is None else "FAILED",
        producer="phase15", evidence_references=(reference,), check_id="final_narration_safety",
        policy_hash=policy_hash, public_code=code)
