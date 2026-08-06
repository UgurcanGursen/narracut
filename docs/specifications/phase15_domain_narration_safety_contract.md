# Phase 15 Domain / Final Narration Safety Contract

## Purpose

Define one local, fail-closed quality-gate check which proves that a canonical
final narration is evaluated against the immutable selected Domain Pack before
it can receive a passing Phase 15 decision.

## Inputs and exact boundary

`validate_final_narration_safety` accepts only:

- a genuine materialized `NarrationRevision`;
- an immutable `DomainPolicySnapshot`, its expected domain id, pack version,
  snapshot id and snapshot hash;
- a non-empty exact set of expected `(claim_id, claim_hash)` pairs and the
  corresponding genuine `ClaimRecordV1` records;
- the run identity and timestamp used by the existing Phase 15 ledger.

It never renders, speaks, opens media, accesses a provider, calls a queue or
mutates narration, research, planner or domain-pack state.

## Domain-pack compatibility and validation extension

The snapshot must be canonical, immutable and exactly match the expected
domain/pack/snapshot tuple. Its resolved extensions must declare
`final_narration_safety`, and exactly one policy bundle must contain
`safety.final_narration_validation_policy` with core contract version
`FINAL-NARRATION-VALIDATION-POLICY-V1`. A missing, malformed or incompatible
extension is a failed `DOMAIN_VALIDATION_EXTENSION_UNAVAILABLE` check, never a
default pass. This is the pre-render admission signal; downstream callers must
include the check in their required quality-gate set.

## Claim and wording rule

Each expected claim must be canonical and bound to the same project and policy
snapshot. Its status and selected safe-wording tokens must be allowed by both
the research and final-narration policies. Every claim must be referenced by a
spoken canonical narration token, and at least one of its safe wording phrases
must occur in that same narration sentence. A claim reference not supplied in
the expected pair set is rejected.

The final-narration policy also supplies explicit blocked surface phrases. A
case-folded whole-phrase match anywhere in `source_text` fails the check. The
first business-tech policy blocks unsupported declarative legal wording
(`convicted`, `guilty`, `liable`); legal or status language which is not an
allowed claim status therefore cannot be released through this gate.

This is a lexical/provenance guard, not a factual truth, source-retrieval,
semantic-classification or media-rendering assertion.

## Evidence and terminal outcomes

The validator emits one `quality_gate/check_evaluated` observation with the
new closed check id `final_narration_safety`, reference kind
`narration_safety`, and immutable final-narration policy hash.

| Condition | Terminal status | Public code |
|---|---|---|
| Exact compatible snapshot, extension, claims and wording | PASSED | none |
| Snapshot domain/version/id/hash mismatch | FAILED | `DOMAIN_PACK_COMPATIBILITY_MISMATCH` |
| Missing/incompatible validation extension or policy | FAILED | `DOMAIN_VALIDATION_EXTENSION_UNAVAILABLE` |
| Bad/omitted/foreign claim or unapproved status | FAILED | `NARRATION_CLAIM_STATUS_UNSUPPORTED` |
| Trace binding or sentence safe wording missing | FAILED | `NARRATION_SAFETY_BINDING_INVALID` |
| Blocked wording in final text | FAILED | `NARRATION_BLOCKED_WORDING` |

Malformed requests remain fail-closed programmer/input errors and cannot emit
a passing observation.

## Non-goals

No live transport, LLM execution, legal adjudication, source truth scoring,
media decode/classification, audio mixing/remix, renderer/EDL mutation,
Studio/UI, Phase 16 or Phase 17 work is authorized.
