# Phase 2 Temporal Compilation + Alignment Report Implementation Acceptance

Decision date: 2026-08-04

## Decision

The bounded **Temporal Compilation + Alignment Report** macro-package is
**ACCEPTED / CLOSED / REMOTE-CLOSURE READY**. This decision accepts only the
`WordToFrame` and `AlignmentReport` canonical contract implementations. It
does not close Phase 2.

## Identity

- Specification/authorization commit:
  `6458c9dad8d3e3173ef54783e220f4c5009577a4`.
- Specification:
  `docs/specifications/phase2_temporal_compilation_alignment_report_contract.md`.
- Specification: `68310` UTF-8 bytes; SHA-256
  `129a2565ed2a3912ca751bb4b32b41cabac0e80379f2bc18f0c074bfbd62852d`.
- Audited implementation commit:
  `8eafe6e012d71bbca67f9902d8fe55fcad252973`.
- Pre-documentation parity:
  `HEAD == origin/main == 8eafe6e012d71bbca67f9902d8fe55fcad252973`.

## Accepted boundary

```text
engine/contracts/word_to_frame.py
engine/contracts/alignment_report.py
engine/contracts/__init__.py
tests/test_word_to_frame.py
tests/test_alignment_report.py
tests/test_alignment_request.py
```

## Independent audit

- Final verdict: `PASS`.
- Findings: `BLOCKER=0 / MAJOR=0 / MINOR=0`.
- Focused WordToFrame + AlignmentReport: `253 passed`.
- Exact public-export oracle: `1 passed`.
- Upstream temporal/narration/alignment/caption/emphasis: `1840 passed`.
- Broad top-level non-FastAPI: `2204 passed, 1 skipped`.
- Full FastAPI collection is not claimed because optional `fastapi` is absent;
  only `tests/test_control_plane_openapi_foundation.py` was excluded.
- `py_compile`, `git diff --check`, protected-excluded clean status, and
  local/remote parity: `PASS`.

## Accepted behavior

- Exact rational integer frame-rate validation and half-open
  floor-start/ceil-end compilation satisfy the accepted one-frame drift rule.
- Word, caption-group, and emphasis spans join through stable IDs and complete
  dependency inventories; string search and caller-authored time are rejected.
- Alignment confidence is emitted as AVAILABLE, CONFIDENCE_UNAVAILABLE, or
  CONFIDENCE_NOT_APPLICABLE, with PASS/REVIEW_REQUIRED/BLOCKED where applicable.
- Canonical bytes, IDs, hashes, lineage, strict loader precedence, mutation
  resistance, registry rollback/weak cleanup, and non-retention are verified.
- All WordToFrame and three AlignmentReport state goldens match the accepted
  specification under independent parse/hash/identity checks.
- Provider, network, filesystem publication, UI, renderer, EDL, database,
  queue/retry, paid API, and Phase 3 work are out of scope.

## Remaining Phase 2 boundary

- `CaptionPreviewRenderer` and deterministic V5/V6 collision validation;
- atomic lifecycle/publication of the named timing artifacts; and
- final Phase 2 end-to-end acceptance reconciliation.

## Documentation impact matrix

| Document | Impact |
|---|---|
| `docs/MASTER_ROADMAP.md` | None; authoritative scope is unchanged |
| `docs/CURRENT_STATE.md` | Records accepted macro-package and remaining boundary |
| `docs/NEXT_ACTIONS.md` | Advances the sole next task to preview/collision |
| `docs/KNOWN_LIMITATIONS.md` | Removes superseded compiler/report gaps and preserves open publication/runtime limits |
| `docs/PHASE_ACCEPTANCE.md` | Records audit, test evidence, and criterion reconciliation |
| `docs/CHANGELOG.md` | Records implementation acceptance and next macro-package |

```text
TEMPORAL_COMPILATION_ALIGNMENT_REPORT_IMPLEMENTATION_ACCEPTED=YES
TEMPORAL_COMPILATION_ALIGNMENT_REPORT_IMPLEMENTATION_STATUS=CLOSED
TEMPORAL_COMPILATION_ALIGNMENT_REPORT_FINAL_AUDIT=PASS
NEXT_MACRO_PACKAGE=Caption Preview + V5/V6 Collision Validation
PHASE2_CLOSED=NO
TOTAL_PHASE2_SLICE_COUNT=UNKNOWN
PHASE2_COMPLETION_PERCENTAGE=NOT_STATED
```
