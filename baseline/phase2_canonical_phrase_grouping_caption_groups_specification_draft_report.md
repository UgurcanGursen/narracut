# Phase 2 Canonical Phrase Grouping and Caption Groups Specification Draft

Date: 2026-08-04

Status: Candidate specification drafted and remote closed; acceptance open

## Identity

- Specification:
  `docs/specifications/phase2_canonical_phrase_grouping_caption_groups_contract.md`
- Commit: `171078ca1c50a43ac9a395fe135e6bc044079b28`
- Parent: `13b6e318d77bc794e3a4bab3e4807d3517917c3d`
- Subject: `docs: draft phase 2 caption groups contract`
- SHA-256: `d379e02e84883a08da66fd6289ca973d0f49a89f007bf68a524c7981dc7cbd46`
- UTF-8 byte length: `35784`
- Remote closure: local HEAD, `origin/main`, and live remote
  `refs/heads/main` all equal the specification commit.

## Bounded content

The candidate defines only deterministic phrase grouping and the semantic
`timing/caption_groups.json` contract. It binds genuine canonical narration to
an accepted genuine AlignmentResult, partitions all words contiguously within
sentences, enforces 4-9-word groups, exposes only the explicit 1-3-word
short-sentence exception, derives display text/timing/confidence, and defines
canonical identity, serialization, validation, mutation, no-leak, and resource
bounds.

It does not define or authorize emphasis, frames, layout, safe-area/collision,
preview, renderer, AlignmentReport/failure artifacts, provider/API/queue,
database/cache/UI, Phase 3, implementation, or Phase 2 closure.

## Manual verification evidence

- Exact numbered sections `1..24`: PASS.
- UTF-8/BOM and `git diff --check`: PASS.
- Both embedded golden JSON blocks parsed: PASS.
- Group projection hashes and `cgrp_` IDs independently recomputed: PASS.
- Artifact projection/envelope lengths, hashes, and `cgs_` ID independently
  recomputed: PASS.
- Deterministic remainder/property probe for sentence lengths `1..1000`: PASS;
  lengths 1-3 use only the declared exception, all other groups are 4-9 words,
  and coverage is complete.
- Changed specification boundary: exactly one file.
- Commercial API, provider, network, renderer, and production tests: not used.

These checks prove internal draft consistency only. They are not independent
audit evidence and do not accept the specification.

## Next gate

The next single authoritative task is an independent read-only adversarial
audit of the exact remote-closed file/commit/SHA. The audit must report findings
by severity and decide only whether repair is required before acceptance
consideration. It may not edit files, accept the specification, authorize
implementation, or close Phase 2.

## Documentation impact matrix

| Path | Impact |
|---|---|
| `docs/CURRENT_STATE.md` | Records the remote-closed candidate and manual evidence. |
| `docs/NEXT_ACTIONS.md` | Sets the independent read-only audit as the sole next task. |
| `docs/KNOWN_LIMITATIONS.md` | Records that audit, acceptance, and implementation remain open. |
| `docs/PHASE_ACCEPTANCE.md` | Adds candidate draft evidence without acceptance. |
| `docs/CHANGELOG.md` | Records draft remote closure and exact identity. |
| `docs/MASTER_ROADMAP.md` | Reviewed; unchanged. |
| Production, tests, fixtures, schemas | Unchanged. |

```text
SPECIFICATION_STATUS=CANDIDATE_REMOTE_CLOSED
SPECIFICATION_DRAFTED=YES
SPECIFICATION_SHA256=d379e02e84883a08da66fd6289ca973d0f49a89f007bf68a524c7981dc7cbd46
SPECIFICATION_UTF8_BYTES=35784
SPECIFICATION_ACCEPTED=NO
IMPLEMENTATION_AUTHORIZED=NO
INDEPENDENT_SPECIFICATION_AUDIT_REQUIRED=YES
NEXT_ACTION=INDEPENDENT_READ_ONLY_SPECIFICATION_AUDIT
PHASE2_CLOSED=NO
TOTAL_PHASE2_SLICE_COUNT=UNKNOWN
PHASE2_COMPLETION_PERCENTAGE=NOT_STATED
```
