# Phase 2 Canonical Emphasis Events Specification Draft

Date: 2026-08-04

Status: Candidate specification drafted and remote closed; acceptance open

## Identity

- Specification:
  `docs/specifications/phase2_canonical_emphasis_events_contract.md`
- Commit: `d4c978eb0df8d11ab033edbd50dc2eca17eab74a`
- Parent: `ac13b9efd58cf544b3b74a62cc6b0578d3bd565f`
- Subject: `docs: draft phase 2 emphasis events contract`
- SHA-256: `5806aa26f798489e475d03b68e451cdbf2c2efd39f450ea7335cb96fc442f3b7`
- UTF-8 byte length: `45380`
- Remote closure: local HEAD, `origin/main`, and live remote
  `refs/heads/main` all equaled the specification commit before this
  documentation synchronization.

## Bounded content

The candidate defines only the canonical semantic emphasis-event artifact. It
binds exact declarative intents to canonical `WordRangeReference` values,
accepted alignment timings, accepted caption groups, and verified Domain Pack
visual-grammar policy. It derives word IDs, caption group, milliseconds, and
confidence without text search or caller-authored timing.

Core owns only a closed domain-neutral intensity scale. Emphasis type names and
versions remain Domain Pack visual-grammar references validated through
`DomainPackRegistry`, `DomainPolicySnapshot`, and a private typed resolved
policy. No service-level domain conditionals or core business-tech enum values
are introduced.

The candidate does not define or authorize planner/provider execution, fuzzy
`text_span` resolution, frames, layout, V5/V6 collision handling, preview,
`AlignmentReport`, filesystem publication, EDL/renderer integration,
implementation, or Phase 2 closure.

## Manual verification evidence

- Exact numbered sections `1..23`: PASS.
- UTF-8 without BOM and `git diff --check`: PASS.
- Four embedded literal golden JSON blocks parsed: PASS.
- All four blocks are compact sorted-key canonical UTF-8 bytes: PASS.
- Event projection/envelope exact lengths and SHA-256 values: PASS.
- Artifact projection/envelope exact lengths and SHA-256 values: PASS.
- `emph_` and `emps_` identities independently recomputed: PASS.
- Root projection embeds the exact event envelope: PASS.
- Exact changed specification boundary before commit: one file.
- Commercial API, provider, network, renderer, and production tests: not used.

These checks prove internal draft consistency only. They are not independent
audit evidence and do not accept the specification.

## Next gate

The next single authoritative task is an independent read-only adversarial
audit of the exact remote-closed file, commit, SHA-256, and byte length. It must
audit dependency/provenance, Domain Pack resolution, word-range and caption
containment, timing/confidence derivation, canonical identity/serialization,
the closed rejection oracle, no-leak/mutation behavior, resource bounds, and
implementation feasibility.

The audit may not edit files, accept the specification, authorize
implementation, assign a Slice number, or close Phase 2.

## Documentation impact matrix

| Path | Impact |
|---|---|
| `docs/specifications/phase2_canonical_emphasis_events_contract.md` | CREATED in the exact remote-closed specification commit. |
| `baseline/phase2_canonical_emphasis_events_specification_draft_report.md` | CREATED by the documentation synchronization. |
| `docs/CURRENT_STATE.md` | UPDATED with candidate identity and audit gate. |
| `docs/NEXT_ACTIONS.md` | UPDATED to the independent read-only audit only. |
| `docs/KNOWN_LIMITATIONS.md` | UPDATED with open audit/acceptance/implementation state. |
| `docs/PHASE_ACCEPTANCE.md` | UPDATED with draft evidence without acceptance. |
| `docs/CHANGELOG.md` | UPDATED with draft remote closure. |
| `docs/MASTER_ROADMAP.md` | REVIEWED; UNCHANGED. |
| Production code, tests, fixtures, schemas, Domain Packs | UNCHANGED. |
| `norm_words_debug.json` | UNTOUCHED. |

```text
SPECIFICATION_STATUS=CANDIDATE_REMOTE_CLOSED
SPECIFICATION_DRAFTED=YES
SPECIFICATION_COMMIT=d4c978eb0df8d11ab033edbd50dc2eca17eab74a
SPECIFICATION_SHA256=5806aa26f798489e475d03b68e451cdbf2c2efd39f450ea7335cb96fc442f3b7
SPECIFICATION_UTF8_BYTES=45380
SPECIFICATION_ACCEPTED=NO
IMPLEMENTATION_AUTHORIZED=NO
INDEPENDENT_SPECIFICATION_AUDIT_REQUIRED=YES
NEXT_ACTION=INDEPENDENT_READ_ONLY_SPECIFICATION_AUDIT
PHASE2_CLOSED=NO
TOTAL_PHASE2_SLICE_COUNT=UNKNOWN
PHASE2_COMPLETION_PERCENTAGE=NOT_STATED
```
