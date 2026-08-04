# Phase 2 Canonical Phrase Grouping and Caption Groups Specification Acceptance Decision

Date: 2026-08-04

Decision: ACCEPT

Status: Specification accepted by this documentation closure; implementation
authorization remains closed

## Accepted identity

- Specification:
  `docs/specifications/phase2_canonical_phrase_grouping_caption_groups_contract.md`
- Corrected specification commit:
  `5bd2401544693a9a0bfe9e3e9d398f96b786cb27`
- SHA-256:
  `c0e8925e598bac0414c1c7b96adf256ed0f4072d2196efedf3b90b0961859baf`
- UTF-8 byte length: `43985`
- Documentation/audit repository HEAD before this decision:
  `e9dfd769a3df640f4821a31ec91886674afff7c2`

The specification's embedded `Accepted: No` and `Implementation authorized:
No` lines are immutable candidate-snapshot metadata. This external decision is
the authoritative acceptance record; it does not rewrite the accepted blob.

## Gate evidence

- Initial independent audit: `FIX_REQUIRED` with findings
  BLOCKER/MAJOR/MINOR/INFO `0/1/0/0`.
- Finding `CGS-SPEC-AUD-001`: repaired in the corrected specification.
- Targeted independent re-audit: `PASS`.
- Targeted findings: BLOCKER/MAJOR/MINOR/INFO `0/0/0/0`.
- `CGS_SPEC_AUD_001_STATUS=CLOSED`.
- `NEW_BLOCKING_FINDING_COUNT=0`.
- `SPECIFICATION_ACCEPTANCE_READY=YES`.
- Corrected blob/commit/SHA/length/encoding identity: PASS.
- Section 11 fixed outcomes: `10`; section 14 confidence outcomes: `5`;
  section 19.1 closed loader-oracle rows: `45`.
- Grouping probes: sentence lengths `1..1000` PASS; exhaustive legal
  partitions `4..24` PASS.
- FX-CGS-01 group/root projections, envelopes, hashes, IDs, and lengths: PASS.
- Stable issue inventory, closed pointers, multi-fault precedence, upstream
  model compatibility, bounded scope, and no-leak rules: PASS.
- Protected `norm_words_debug.json`: untouched.

## Accepted scope

Acceptance covers only the immutable semantic caption-group contract:

- genuine narration and AlignmentResult dependency binding;
- deterministic sentence-bounded complete word partitioning;
- explicit short-sentence exception and otherwise mandatory 4-9-word groups;
- punctuation boundary ranking and display-text derivation;
- word ranges, timing, confidence, canonical identities/bytes;
- loader, mutation resistance, errors, no-leak, and resource bounds; and
- the future semantic artifact `timing/caption_groups.json`.

Acceptance does not cover implementation, tests, artifact publication,
emphasis, frames, layout/collision, preview, renderer, provider/API/queue,
database/cache/UI, Phase 3, production readiness, or Phase 2 closure.

## Decision boundary and next gate

The specification is accepted. Implementation remains not authorized and not
started. The next single authoritative task is a separate read-only
implementation-authorization decision that must reconcile exact production and
test paths, additive exports, regression boundary, REPLAY/no-commercial-API
policy, and mandatory tests. It may authorize only the bounded contract if all
prerequisites are ready.

## Documentation impact matrix

| Path | Impact |
|---|---|
| `docs/CURRENT_STATE.md` | Records accepted corrected identity and next authorization decision. |
| `docs/NEXT_ACTIONS.md` | Sets one read-only implementation-authorization decision. |
| `docs/KNOWN_LIMITATIONS.md` | Removes audit/acceptance as open; keeps implementation/downstream gaps. |
| `docs/PHASE_ACCEPTANCE.md` | Records accepted specification without Phase 2 closure. |
| `docs/CHANGELOG.md` | Records PASS re-audit and ACCEPT decision. |
| `docs/MASTER_ROADMAP.md` | Reviewed; unchanged. |
| Production, tests, fixtures, schemas | Unchanged. |

```text
CAPTION_GROUPS_SPECIFICATION_TARGETED_REAUDIT=PASS
CGS_SPEC_AUD_001_STATUS=CLOSED
SPECIFICATION_ACCEPTANCE_DECISION=ACCEPT
SPECIFICATION_ACCEPTED=YES
IMPLEMENTATION_AUTHORIZED=NO
IMPLEMENTATION_STATUS=NOT_STARTED
NEXT_ACTION=IMPLEMENTATION_AUTHORIZATION_DECISION
PHASE2_CLOSED=NO
TOTAL_PHASE2_SLICE_COUNT=UNKNOWN
PHASE2_COMPLETION_PERCENTAGE=NOT_STATED
```
