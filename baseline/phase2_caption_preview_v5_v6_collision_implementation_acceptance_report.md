# Phase 2 Caption Preview + V5/V6 Collision Implementation Acceptance

Date: 2026-08-04

## Decision

**ACCEPT.** The bounded Caption Preview + V5/V6 Collision Validation
macro-package is implemented and remote closed at implementation commit
`218c4bd277867b29d6812715311993a500e19d33`.

## Implemented boundary

- `engine/contracts/caption_preview.py`
- `engine/contracts/v5_v6_collision.py`
- additive public exports in `engine/contracts/__init__.py`
- exact export assertion in `tests/test_alignment_request.py`
- focused REPLAY tests in `tests/test_caption_preview.py` and
  `tests/test_v5_v6_collision.py`

The implementation consumes only accepted Caption Groups, Emphasis Events,
and WordToFrame artifacts. It emits sparse canonical preview geometry and a
deterministic fail-closed V5/V6 collision report. It does not publish timing
files, render production captions, introduce Remotion/EDL/UI/providers, or
close Phase 2.

## Acceptance evidence

- Current specification:
  `docs/specifications/phase2_caption_preview_v5_v6_collision_contract.md`.
- Final independent re-audit: **ACCEPT**, BLOCKER/MAJOR/MINOR `0/0/0`.
- Focused/export gate: `66 passed`.
- Broad non-FastAPI upstream regression: `2237 passed, 1 skipped`.
- `py_compile` and `git diff --check`: PASS.
- Public fixtures verify fixed byte/SHA/identity goldens, independent compact
  canonical JSON reconstruction, loader precedence, weak-registry collection,
  half-open geometry, and V5-to-V6 collision ordering.

## Document impact matrix

| Document | Impact |
|---|---|
| `docs/MASTER_ROADMAP.md` | No change; Phase 2 remains open. |
| `docs/CURRENT_STATE.md` | Records accepted macro and the next macro. |
| `docs/NEXT_ACTIONS.md` | Advances to timing publication and Phase 2 end-to-end closure. |
| `docs/KNOWN_LIMITATIONS.md` | Records remaining publication/integration boundary. |
| `docs/PHASE_ACCEPTANCE.md` | Marks only this macro accepted; not Phase 2. |
| `docs/CHANGELOG.md` | Records implementation acceptance. |

## Remaining boundary

The next and only recommended macro-package is canonical timing-file
publication plus an end-to-end Phase 2 acceptance reconciliation. It must
consume the accepted contracts, introduce no provider/UI/renderer scope, and
include the high-cardinality authoritative fixture noted by the preview
contract.
