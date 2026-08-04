# Phase 2 Canonical Phrase Grouping and Caption Groups Specification Path Decision

Date: 2026-08-04

Status: Closed scope and specification-path decision; remote closure recorded
by this documentation synchronization

## Authority and evidence base

- Repository authority at decision time:
  `13f5ddb0d13df6cd4d036847a9abaa32ef6d2992`.
- `docs/MASTER_ROADMAP.md` Phase 2 pipeline places phrase grouping after
  canonical word alignment and before emphasis mapping and word-to-frame
  compilation.
- The roadmap names `timing/caption_groups.json` as a Phase 2 deliverable and
  describes readable subtitles as phrase-based, with 4-9 words preferred.
- The Canonical Successful Alignment Word-Timing Result implementation is
  accepted and remote closed at
  `87eb330922a5a1295de861544b44859ddd001911`.
- No canonical phrase-grouping contract or accepted
  `timing/caption_groups.json` producer exists at this decision point.

## Decision

Selected bounded candidate title:

```text
Canonical Phrase Grouping and Caption Groups Contract
```

Selected future specification path:

```text
docs/specifications/phase2_canonical_phrase_grouping_caption_groups_contract.md
```

The selected path did not exist when this decision was made. The descriptive,
non-numbered filename follows the repository convention already used for the
post-Slice-5 bounded alignment-result contract without inventing a total Phase
2 Slice decomposition.

## Bounded future specification scope

The future specification may define only:

- exact binding to a genuine canonical narration revision and an accepted
  canonical successful alignment result;
- deterministic, order-preserving, complete and contiguous partitioning of
  canonical word timings into caption groups;
- caption-group word ranges, time-bound derivation, stable identity, and
  confidence propagation;
- deterministic sentence and punctuation boundary handling;
- the exact meaning of the roadmap's 4-9-word preference, including bounded
  exceptions and deterministic precedence;
- canonical display-text derivation without string-search timing recovery;
- canonical JSON serialization, content hashing, validation precedence,
  mutation resistance, and secret/no-leak rules; and
- the repository artifact semantics for `timing/caption_groups.json`.

## Explicitly out of scope

This decision does not authorize or specify:

- implementation, tests, acceptance, or implementation authorization;
- emphasis mapping or `timing/emphasis_events.json`;
- word-to-frame compilation or frame-number fields;
- line wrapping, safe-area layout, V5/V6 collision handling, preview rendering,
  or the CaptionPreviewRenderer;
- failure artifacts, `AlignmentReport`, provider/runtime execution, network,
  retry, queue, API, payment, database, cache, Studio API, or UI behavior;
- Phase 3 rendering work or Phase 2 closure.

## Readiness and next gate

The accepted canonical narration and alignment-result contracts provide the
required upstream semantic inputs. No blocker prevents bounded specification
drafting. Exact fields, partition invariants, preference/exception precedence,
identity rules, and validation/error taxonomy must be resolved in the draft;
they are not decided by this path-selection report.

The next single authoritative task is drafting the candidate specification at
the selected path. Drafting does not accept the specification and does not
authorize implementation.

## Documentation impact matrix

| Path | Impact |
|---|---|
| `docs/CURRENT_STATE.md` | Records the closed path decision and the drafting-only next gate. |
| `docs/NEXT_ACTIONS.md` | Sets one authoritative specification-drafting task. |
| `docs/KNOWN_LIMITATIONS.md` | Records that the contract and artifact producer remain missing. |
| `docs/PHASE_ACCEPTANCE.md` | Adds path-decision evidence without closing Phase 2. |
| `docs/CHANGELOG.md` | Records the bounded decision and scope boundary. |
| `docs/MASTER_ROADMAP.md` | Reviewed as authority; unchanged. |
| Production, tests, fixtures, schemas, specifications | Unchanged by this decision and documentation synchronization. |

```text
PHASE2_SCOPE_DECISION=MORE_BOUNDED_PHASE2_WORK_REQUIRED
BOUNDED_CANDIDATE_TITLE=Canonical Phrase Grouping and Caption Groups Contract
SELECTED_SPECIFICATION_PATH=docs/specifications/phase2_canonical_phrase_grouping_caption_groups_contract.md
SPECIFICATION_PATH_DECISION=CLOSED
SPECIFICATION_DRAFTED=NO
SPECIFICATION_ACCEPTED=NO
IMPLEMENTATION_AUTHORIZED=NO
NEXT_ACTION=SPECIFICATION_DRAFTING
PHASE2_CLOSED=NO
TOTAL_PHASE2_SLICE_COUNT=UNKNOWN
PHASE2_COMPLETION_PERCENTAGE=NOT_STATED
```
