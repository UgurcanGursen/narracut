# Phase 2 Post-Caption-Groups Scope Reconciliation Report

Date: 2026-08-04

## Decision scope

This is a bounded, read-only reconciliation of the accepted Caption Groups
implementation against the Master Roadmap Phase 2 pipeline, deliverables, and
acceptance criteria. It does not modify production code, tests, the accepted
Caption Groups specification, or `docs/MASTER_ROADMAP.md`.

Authoritative repository:

```text
C:\Users\user\Documents\Kurgu_V3_Clean_sanitized_freesound_20260724_224147304
```

Decision base:

```text
HEAD=9c92e29280bcda46bf4a927e98ac641dad1cbabe
origin/main=9c92e29280bcda46bf4a927e98ac641dad1cbabe
CAPTION_GROUPS_IMPLEMENTATION_ACCEPTED=YES
CAPTION_GROUPS_IMPLEMENTATION_REMOTE_CLOSED=YES
```

## Evidence reviewed

- Master Roadmap Phase 2 pipeline, six deliverables, and six acceptance
  criteria.
- Accepted canonical contracts in `engine/contracts/` for temporal raw input,
  narration, audio, alignment request, adapter execution, alignment result,
  and caption groups.
- Focused contract tests and the accepted implementation/audit evidence chain.
- Existing Phase 1 `text_emphasis_events` envelope/schema placeholders.
- Legacy frame conversion in `v2/editorial_engine.py`.
- Repository search for canonical emphasis, frame compiler, caption preview,
  collision validation, and alignment-report implementations.

Schema placeholders, empty fixture arrays, legacy behavior, and documentation
text are not treated as canonical Phase 2 completion evidence.

## Master deliverable matrix

| Deliverable | Status | Repository evidence | Remaining boundary |
|---|---|---|---|
| `timing/word_timeline.json` | PARTIALLY_SATISFIED | Accepted `AlignmentResult` and immutable `WordTiming` values cover every canonical narration word for the allowlisted REPLAY success path | No canonical filesystem publication/lifecycle at the roadmap path; other runtime producers remain unavailable |
| `timing/caption_groups.json` | PARTIALLY_SATISFIED | Accepted `CaptionGroupsArtifact` provides deterministic phrase groups, word ranges, derived timing, confidence, identity, and canonical bytes | No canonical filesystem publication/lifecycle at the roadmap path |
| `timing/emphasis_events.json` | NOT_SATISFIED | Phase 1 has only generic `text_emphasis_events` envelopes and empty migration defaults | No canonical Phase 2 emphasis event model, word-range binding, timing derivation, identity, or artifact |
| `WordToFrameCompiler` | NOT_SATISFIED | `v2/editorial_engine.py` contains legacy `int(entry["start"] * 30)` conversion | No canonical compiler, rational frame-rate/rounding policy, end-frame semantics, or one-frame acceptance oracle |
| `CaptionPreviewRenderer` | NOT_SATISFIED | No canonical implementation or accepted focused evidence found | Caption/emphasis frame inputs and V5/V6 collision policy are prerequisites |
| `AlignmentReport` | NOT_SATISFIED | Confidence values and availability exist in accepted alignment/group artifacts | No explicit report artifact, thresholds, issue projection, or low-confidence reporting boundary |

The first two rows are canonical semantic contract progress, not a claim that
the roadmap-named files have been published.

## Master acceptance matrix

| Master criterion | Status | Exact reasoning |
|---|---|---|
| Every narration word has start/end timing | PARTIALLY_SATISFIED | Accepted REPLAY `AlignmentResult` enforces full canonical-word timing coverage, but roadmap artifact publication and broader trusted producer execution are absent |
| Cues bind to word-ID ranges instead of string search | PARTIALLY_SATISFIED | `WordRangeReference`, `resolve_word_range`, `WordRangeConsumer.EMPHASIS`, and caption group word ranges exist; canonical emphasis/cue integration is still missing |
| Kinetic text differs from narration by at most one frame | NOT_SATISFIED | No accepted `WordToFrameCompiler`, normative rounding policy, or drift test exists |
| V5 and V6 do not occlude each other | NOT_SATISFIED | No accepted preview renderer, layout contract, or collision validator exists |
| Low confidence is explicitly reported | PARTIALLY_SATISFIED | Confidence availability and per-word/per-group values exist, but no `AlignmentReport` or explicit low-confidence classification/report exists |
| LLM does not generate manual seconds | PARTIALLY_SATISFIED | Accepted timing contracts derive timing from allowlisted alignment evidence and reject caller-authored timing; the downstream emphasis pipeline has not yet bound semantic intent to word IDs and derived times |

## Remaining dependency order

```text
accepted AlignmentResult
-> accepted CaptionGroupsArtifact
-> canonical emphasis events
-> word-to-frame compilation
-> caption/emphasis preview and V5/V6 collision validation
```

`AlignmentReport` is also still required, but selecting it now would not
advance the next missing pipeline edge from phrase grouping to emphasis
mapping. Filesystem artifact publication remains a separate lifecycle concern
and must not be silently folded into a semantic contract.

## Candidate comparison

| Candidate | Dependency readiness | Roadmap contribution | Boundedness | Decision |
|---|---|---|---|---|
| Canonical Emphasis Events Contract | Ready: narration word ranges, alignment timing, and caption groups are accepted | Completes the next missing `phrase grouping -> emphasis mapping` edge and advances `timing/emphasis_events.json` semantics | Cohesive if limited to semantic intent, word-ID ranges, derived timing, canonical identity, and validation | SELECTED |
| WordToFrameCompiler Contract | Missing canonical emphasis inputs | Advances frame accuracy but would either ignore V5 semantics or create a second later integration pass | Premature | DEFERRED |
| AlignmentReport Contract | Alignment/group confidence exists | Advances explicit low-confidence reporting | Independently bounded, but not the next pipeline edge | DEFERRED |
| CaptionPreviewRenderer Contract | Frame compilation and collision policy absent | Advances V5/V6 preview acceptance | Dependencies not ready | DEFERRED |
| Timing artifact publication/lifecycle | Semantic timeline/group bytes exist | Would materialize roadmap file paths | Cross-cutting artifact lifecycle decision; must not be mixed into emphasis semantics | DEFERRED |

## Selected next bounded candidate

Title: **Canonical Emphasis Events Contract**

Exact future specification path:

```text
docs/specifications/phase2_canonical_emphasis_events_contract.md
```

The specification should decide, without implementing:

- domain-neutral immutable emphasis intent/event models;
- exact binding to canonical `word_id` half-open ranges;
- deterministic timing derived only from accepted `AlignmentResult` words;
- caption-group relationship rules where applicable;
- emphasis type/intensity vocabulary ownership and Domain Pack boundary;
- canonical serialization, versioning, hash scope, stable identity, and
  dependency provenance;
- deterministic validation/error precedence, atomic non-publication, no-leak,
  and mutation/forgery resistance;
- exact golden bytes and acceptance fixture matrix.

The specification must explicitly exclude:

- fuzzy/string-search resolution of LLM text spans inside the canonical
  boundary;
- LLM/provider execution, paid API calls, or browser automation;
- caller-, LLM-, or manually-authored seconds/frames;
- word-to-frame compilation, frame-rate policy, preview rendering, V5/V6
  layout/collision validation, `AlignmentReport`, and filesystem publication;
- Phase 3 EDL or renderer integration.

If an external planner still emits a `text_span`, a later adapter boundary
must resolve that intent to an exact canonical word range before an emphasis
event can be published. The canonical artifact itself must never use string
search as its identity or timing mechanism.

## Explicit non-claims

- No new Slice number is assigned.
- The total official Phase 2 Slice count remains unknown.
- No Phase 2 completion percentage is stated.
- The selected specification is not drafted or accepted by this report.
- No implementation is authorized or started.
- No roadmap file artifact is declared published.
- Phase 2 acceptance evaluation and closure are not allowed.
- `docs/MASTER_ROADMAP.md` is unchanged.

## Documentation impact matrix

| Path or area | Decision |
|---|---|
| `baseline/phase2_post_caption_groups_scope_reconciliation_report.md` | CREATED |
| `docs/CURRENT_STATE.md` | UPDATED |
| `docs/NEXT_ACTIONS.md` | UPDATED |
| `docs/KNOWN_LIMITATIONS.md` | UPDATED |
| `docs/PHASE_ACCEPTANCE.md` | UPDATED |
| `docs/CHANGELOG.md` | UPDATED |
| `docs/MASTER_ROADMAP.md` | REVIEWED_NO_CHANGE |
| `docs/specifications/phase2_canonical_emphasis_events_contract.md` | SELECTED_FUTURE_PATH; NOT_CREATED |
| Production code and tests | REVIEWED_NO_CHANGE |
| `norm_words_debug.json` | UNTOUCHED |

## Reconciliation decision

```text
POST_CAPTION_GROUPS_SCOPE_RECONCILIATION_STATUS=PASS
CAPTION_GROUPS_IMPLEMENTATION_ACCEPTED=YES
CAPTION_GROUPS_IMPLEMENTATION_REMOTE_CLOSED=YES
MASTER_PHASE2_DELIVERABLES_COMPLETE=NO
MASTER_PHASE2_ACCEPTANCE_CRITERIA_COMPLETE=NO
PHASE2_SCOPE_DECISION=MORE_BOUNDED_PHASE2_WORK_REQUIRED
NEXT_BOUNDED_CANDIDATE_TITLE=Canonical Emphasis Events Contract
SPECIFICATION_REQUIRED=YES
SELECTED_SPECIFICATION_PATH=docs/specifications/phase2_canonical_emphasis_events_contract.md
SPECIFICATION_PATH_DECISION=CLOSED
SPECIFICATION_DRAFTED=NO
SPECIFICATION_ACCEPTED=NO
IMPLEMENTATION_AUTHORIZED=NO
NEXT_ACTION=SPECIFICATION_DRAFTING
NEXT_IMPLEMENTATION_ALLOWED=NO
PHASE2_ACCEPTANCE_DECISION_ALLOWED=NO
PHASE2_CLOSED=NO
TOTAL_PHASE2_SLICE_COUNT=UNKNOWN
PHASE2_COMPLETION_PERCENTAGE=NOT_STATED
```
