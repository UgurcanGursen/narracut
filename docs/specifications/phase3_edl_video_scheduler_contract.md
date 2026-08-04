# Phase 3A EDL and Video Scheduler Contract

## 1. Status, authority, and bounded purpose

Status: Candidate specification

Accepted: No

Implementation authorized: No

Phase 3 closed: No

This document is subordinate to `docs/MASTER_ROADMAP.md`.  It is the first,
bounded implementation package of Phase 3: convert already accepted temporal
artifacts and a declarative video edit request into a deterministic,
frame-accurate multi-track **video** EDL plus a reviewable timeline-debug
artifact.  It neither changes Phase 2 nor treats an accepted timing artifact
as a renderer input format.

The package closes only the video-half foundation of the Master Roadmap's
`TimelineCompiler`, `FrameGridScheduler`, `CollisionDetector`,
`SequenceDurationCalculator`, `EDLVisualizer`, and `TimelineDebugExport`
deliverables.  Phase 3 remains open until the separately bounded audio
sample-grid and boundary-planning package is accepted.

## 2. Explicit exclusions

This contract does not authorize 48 kHz sample planning, PCM inspection or
normalisation, encoder-delay handling, fades/crossfades, zero-crossing search,
audio collision resolution, audio mixing, FFmpeg, Remotion, Node, rendering,
media decoding, source acquisition, asset-catalog lookup, provider execution,
network, database, queue/retry service, UI, filesystem publication, artifact
lifecycle, cache, clock/random use, threads, subprocesses, V2 changes, or
Domain Pack changes.

It does not infer a source duration, validate a media file, choose a crop,
create a transition, interpolate motion, repair collisions, search narration
text, normalize strings, or accept caller-authored timeline milliseconds or
timeline frame coordinates.  A source descriptor is an opaque, typed future
asset binding; it is not proof that source media exists.  Audio tracks are
present only as fixed empty registry entries in this package.

## 3. Paths, ownership, and import boundary

The exact new production paths are:

```text
engine/contracts/edl.py
engine/contracts/timeline_debug.py
```

The exact focused test paths are:

```text
tests/test_edl.py
tests/test_timeline_debug.py
```

Only the integration owner may make additive exports in
`engine/contracts/__init__.py` and update the exact-export oracle in
`tests/test_alignment_request.py`.  `edl.py` may import the canonical JSON
encoder and the public APIs of `caption_groups`, `emphasis_events`,
`word_to_frame`, `caption_preview`, and `v5_v6_collision`.  `timeline_debug.py`
may import only canonical JSON and public EDL APIs.  Neither module may import
V2, renderer, media, audio, provider, filesystem, or private contract helpers.
All compile/load/serialize/debug functions are pure in-memory operations.

## 4. Fixed clocks, intervals, and registry

All timeline ranges are exact half-open integer frame intervals
`[start_frame, end_exclusive_frame)`.  `bool` is never an integer.  The
immutable video clock is:

```text
clock_version = "VIDEO-FRAME-CLOCK-V1"
fps_numerator  = positive uint32
fps_denominator = positive uint32
gcd(fps_numerator, fps_denominator) = 1
```

The Phase 3A REPLAY baseline uses `30/1`; `30000/1001` must also be covered by
tests. The supplied reduced EDL rate must equal the supplied genuine
`WordToFrameArtifact.frame_rate` numerator and denominator exactly; rate
conversion is rejected, never rounded. The word-to-frame compiler's source
millisecond rational mapping remains the sole timing provenance. The EDL and
debug artifacts deliberately contain no milliseconds, so a second ms/frame
formula cannot drift from that accepted mapping. The scheduler obtains event
boundaries exclusively from genuine `WordToFrameArtifact` rows and does not
accept a numeric timeline time input.

The entire registry is emitted in this exact track order, including empty
tracks:

| Track | Kind | z / mix priority | Phase 3A role |
|---|---:|---:|---|
| V1 | VIDEO | 10 | Base footage |
| V2 | VIDEO | 20 | Secondary B-roll / inserts |
| V3 | VIDEO | 30 | Source evidence |
| V4 | VIDEO | 40 | Charts / diagrams / UI callouts |
| V5 | VIDEO | 50 | Kinetic emphasis / quote / metric overlays, compiler-owned |
| V6 | VIDEO | 60 | Readable subtitles, compiler-owned |
| V7 | VIDEO | 70 | Branding / finishing reservation |
| A1 | AUDIO | 10 | narration reservation |
| A2 | AUDIO | 20 | Background music reservation |
| A3 | AUDIO | 30 | Editorial sound effects reservation |
| A4 | AUDIO | 40 | Source speech reservation |
| A5 | AUDIO | 50 | Natural ambience reservation |

The A-track ordering is metadata only and every A track has zero events in a
valid Phase 3A EDL.  The fixed registry is core, domain-neutral, and may not
be altered by a Domain Pack or request.

Within every V track, events are in increasing `(start_frame,
end_exclusive_frame,event_id)` order and positive temporal overlap is rejected.
Touching boundaries are valid.  Between V tracks, stacking is determined only
by the table.  Cross-track overlap is allowed except that V5/V6 require the
accepted collision report to have zero findings; the scheduler neither
rechecks geometry nor silently moves either event.  V7 does not implement a
transition in this package; it merely carries an independently word-cued
event.  No automatic priority-based dropping occurs.

## 5. Public surface, models, and canonical identity

`edl.py` exports exactly:

```text
VIDEO_EDL_V1
VIDEO_EDL_HASH_V1
VIDEO_CLOCK_V1
TimelineTrack
EdlTrackKind
EdlPayloadKind
SourcePlaybackMode
SourceFitMode
CueWordRange
SourceDescriptor
VideoEditIntent
EdlRenderPayload
EdlVideoEvent
EdlTrack
VideoEdlArtifact
VideoEdlRejectionReason
VideoEdlContractError
compile_video_edl
load_video_edl
serialize_video_edl
```

`timeline_debug.py` exports exactly:

```text
TIMELINE_DEBUG_V1
TIMELINE_DEBUG_HASH_V1
TimelineDebugEntry
TimelineDebugArtifact
TimelineDebugRejectionReason
TimelineDebugContractError
compile_timeline_debug
load_timeline_debug
serialize_timeline_debug
```

All listed records are frozen dataclasses and their declaration order is
normative.  Their complete field order is:

```text
CueWordRange(project_id, document_id, narration_revision_id,
             start_word_id, end_word_id)
SourceDescriptor(source_ref, source_fps_numerator, source_fps_denominator,
                 source_in_frame, source_out_exclusive_frame, playback_mode,
                 fit_mode, crop_left_millionths, crop_top_millionths,
                 crop_right_millionths, crop_bottom_millionths,
                 opacity_millionths, bound_start_word_id, bound_end_word_id)
VideoEditIntent(intent_id, track: TimelineTrack, cue, source, editorial_role, ordinal)
EdlRenderPayload(kind, source, source_artifact_id, source_artifact_hash,
                 source_record_id, source_record_hash, source_record_ordinal, preview_scene_id,
                 preview_scene_hash, preview_left_millionths,
                 preview_top_millionths, preview_right_millionths,
                 preview_bottom_millionths, text, emphasis_type_ref,
                 emphasis_intensity)
EdlVideoEvent(schema_version, hash_scope_version, event_id, event_hash,
              track: TimelineTrack, ordinal, intent_id, editorial_role,
              start_frame, end_exclusive_frame, start_word_id, end_word_id,
              payload)
EdlTrack(track: TimelineTrack, kind, priority, events)
VideoEdlArtifact(schema_version, hash_scope_version, video_edl_id,
                 video_edl_hash, project_id, document_id,
                 narration_revision_id, narration_revision_hash,
                 sequence_id, sequence_start_word_id, sequence_end_word_id,
                 sequence_start_frame, sequence_content_end_exclusive_frame,
                 trailing_silence_frames, sequence_end_exclusive_frame,
                 word_to_frame_id, word_to_frame_hash,
                 caption_preview_id, caption_preview_hash,
                 v5_v6_collision_report_id, v5_v6_collision_report_hash,
                 clock_version, fps_numerator, fps_denominator,
                 duration_frames, tracks)
TimelineDebugEntry(ordinal, event_id, track: TimelineTrack, priority, start_frame,
                   end_exclusive_frame, start_word_id, end_word_id,
                   intent_id)
TimelineDebugArtifact(schema_version, hash_scope_version,
                      timeline_debug_id, timeline_debug_hash,
                      video_edl_id, video_edl_hash, clock_version,
                      fps_numerator, fps_denominator, duration_frames,
                      entries)
```

`TimelineTrack` is the sole unified canonical string enum with exactly `V1`
through `V7`, then `A1` through `A5`, in registry order. `VideoEditIntent`,
`EdlVideoEvent`, `EdlTrack`, and `TimelineDebugEntry` use exactly this type and
serialize its string value. The compiler additionally permits caller/video
events only on V1–V7, while A1–A5 appear only as required empty `EdlTrack`
entries in Phase 3A. Thus every EDL and debug track has one closed type and
canonical serialization cannot coerce between separate enums. `EdlTrackKind`
is exactly `VIDEO` and `AUDIO`; `EdlPayloadKind` is exactly `CALLER_SOURCE`,
`KINETIC_EMPHASIS`, and `CAPTION`; `SourcePlaybackMode` is exactly `HOLD`,
`LOOP`, and `FIT`; `SourceFitMode` is exactly `CONTAIN`,
`COVER`, or `STRETCH`.  `editorial_role` is an opaque nonempty NFC string of
at most 128 Unicode scalar values; the core never selects or interprets it.
`source_ref` and `intent_id` are nonempty ASCII stable identifiers, maximum
128 bytes. Source FPS is reduced positive uint32 rational; source in/out
values are nonnegative uint32 source-local frame coordinates with `in < out`;
they are not timeline coordinates. At a timeline frame offset `d`, `HOLD`
maps to `min(source_out-1, source_in + floor(d * source_fps_n * edl_fps_d /
(source_fps_d * edl_fps_n)))`; `LOOP` uses the same increment modulo the
source span; `FIT` maps `floor(d * source_span / event_duration)`. This is a
deterministic playback mapping declaration only: Phase 3A does not open the
source, verify its FPS, or decode a frame. Phase 8 must bind `source_ref` to a
catalog AssetRecord and Phase 4 must reject an unavailable/incompatible source
before render; neither phase may change these EDL bytes.
`bound_start_word_id` and `bound_end_word_id` are inclusive stable word IDs.
For every caller event they must exactly equal `VideoEditIntent.cue`'s start/end
IDs; this is the sole source-to-timeline semantic binding in Phase 3A. It
prevents a source descriptor approved for one cue from being silently attached
to another. A source descriptor has no such relation to V5/V6 because those
payloads have null source and are bound to their temporal artifacts instead.
Crop and opacity are non-bool integers in `[0, 1_000_000]`; crop is a positive
half-open normalized rectangle and opacity is positive.  There are no defaults.

There is deliberately no duplicate `EdlVideoEvent.source` field: the sole
event source is `EdlVideoEvent.payload.source`. This removes a null/equality
ambiguity from canonical projection. The payload null matrix is normative.
`CALLER_SOURCE` has exactly its supplied
`SourceDescriptor`, its `intent_id` as `source_record_id`, a null
`source_record_hash`, a nonnegative caller ordinal, and every
preview/text/emphasis field null. `KINETIC_EMPHASIS` has source null; its source
artifact ID/hash are the exact EmphasisEvents artifact; record ID/hash/ordinal
are the exact `EmphasisEvent.emphasis_event_id`, `emphasis_event_hash`, and
ordinal; preview identity and rectangle exactly reproduce its V5 PreviewScene;
text exactly reproduces that scene's semantic proxy label; and intensity exactly
reproduces the event. `emphasis_type_ref` is either null or the exact frozen
upstream `EmphasisTypeRef` type, never a string or mapping. For KINETIC it is
non-null and its canonical projection is exactly the sorted-key nested object
`{"domain_id":...,"name":...,"version":...}` copied byte-for-byte by scalar
value from the matched event; it has no independent ID/hash, and is bound by
the matched event ID/hash and enclosing EmphasisEvents artifact ID/hash.
`CAPTION` has source null; its source artifact ID/hash are the exact
CaptionGroups artifact; record ID/hash/ordinal are the exact CaptionGroup
ID/hash/ordinal;
preview identity/rectangle exactly reproduce its V6 PreviewScene; text exactly
reproduces byte-for-byte `display_text`; and emphasis fields are null. Thus a
Phase 4 renderer receives typed text, geometry, timing, track, and provenance
without searching an upstream artifact or recalculating a cue.

Every schema/hash literal is exactly the exported V1 constant.  Projection
omits only the record's identity/hash pair.  SHA-256 of sorted-key, compact
UTF-8 canonical JSON gives the hash; IDs are respectively `vevt_`, `vedl_`,
`tdbg_` plus the first 32 lowercase hash hex characters.  Serialization is the
complete envelope, uses canonical JSON, and contains all declared fields.
The EDL contains a fixed 12-element `tracks` tuple in registry order.

## 6. Inputs and deterministic compilation

The exact signature is:

```text
compile_video_edl(*, intents: tuple[VideoEditIntent, ...],
                  sequence_id: str, sequence_start_word_id: str,
                  sequence_end_word_id: str,
                  caption_groups: CaptionGroupsArtifact,
                  emphasis_events: EmphasisEventsArtifact,
                  word_to_frame: WordToFrameArtifact,
                  caption_preview: CaptionPreviewArtifact,
                  v5_v6_collision_report: V5V6CollisionReport,
                  fps_numerator: int, fps_denominator: int) -> VideoEdlArtifact
```

It first serializes every dependency and rejects an unmaterialized, mutated,
or content-drift dependency.  It then requires exact shared
project/document/narration-revision identities and hashes across all inputs;
the preview must bind the supplied caption/emphasis/frame artifacts; the
report must bind the supplied preview; and `finding_count == blocker_count ==
0`.  A nonzero collision report is a fail-closed `V5_V6_COLLISION_BLOCKED`,
not a warning or repair request. `sequence_id` is a nonempty ASCII stable ID,
maximum 128 bytes. Its inclusive start/end word IDs are resolved in the same
indexed word map and must be ordered. Their exact upstream global frames become
`sequence_start_frame` and `sequence_content_end_exclusive_frame`. Every EDL
event frame is sequence-local: subtract `sequence_start_frame` from its
resolved upstream frame. Every event cue must lie fully inside the sequence.
`duration_frames` and `sequence_end_exclusive_frame` are equal to the
sequence-local content end. `trailing_silence_frames` is canonically zero in
Phase 3A. This is an explicit limitation, not dropped data: accepted Phase 2
artifacts do not supply a trusted sequence-tail silence boundary. A future
audio/sequence-boundary contract must add such provenance before nonzero
trailing silence can be represented; Phase 3A has no caller field that could
silently invent it.

For caller intents, only V1/V2/V3/V4/V7 are legal. Caller `ordinal` is one
global namespace: tuple order is strictly increasing contiguous uint32 values
beginning at zero, `intent_id` is unique, and it must not begin `emphasis:` or
`caption:`. Per-track `EdlVideoEvent.ordinal` is a separate namespace and is
contiguous from zero after all generated/caller events are placed in canonical
temporal order. V5 comes solely from every
accepted `EmphasisEvent` using its exact word-ID bounds, source ID, source
ordinal, and word-to-frame span.  V6 comes solely from every accepted
`CaptionGroup` by the same rule.  Caller input cannot insert, suppress,
relocate, or edit V5/V6.  Every cue must name its inclusive start and end word
IDs from the supplied word-to-frame artifact; resolution finds those stable IDs
once in an indexed mapping and produces start frame of start word and exclusive
end frame of end word.  Repeated text is irrelevant and no string lookup is
allowed.
Generated `intent_id` values are exactly `emphasis:<event_id>` and
`caption:<group_id>`. Generated V5 `editorial_role` is exactly the literal
`"kinetic_emphasis"`; generated V6 `editorial_role` is exactly the literal
`"readable_subtitle"`. These literals are compiler constants, not Domain Pack
labels, caller data, or a renderer inference. Their payload provenance is
described in section 5.

Before event generation, preview scenes are checked as a complete ordered
binding, not merely by aggregate artifact identity. For each emphasis ordinal
`i`, preview scene `i` must be V5 with the exact event source ID, exact
word-to-frame half-open span, and the expected combined scene ordinal `i`.
For each caption ordinal `j`, scene `len(emphasis_events)+j` must be V6 with
the exact group source ID, exact word-to-frame half-open span, and that exact
combined ordinal. Its policy rectangle and label must also match the payload
null matrix. Any mismatch is `DEPENDENCY_BINDING_INVALID`; the compiler never
substitutes a visually similar scene.

The compiler rejects duplicate intent IDs, noncontiguous/incorrect caller
ordinals, a source/cue mismatch, a V5/V6 caller intent, unknown track, any
unresolved word ID, inverted cue, empty event range, same-track overlap, or
unbound dependency.  It builds no per-frame array.  It derives
the fixed sequence-local duration described above (including an empty sequence
whose start/end cue resolves to a positive span), emits fixed tracks, then
creates event and root identities from their
canonical projections.  Equivalent input objects always produce byte-identical
EDL bytes.

## 7. Load, errors, and materialization

```text
load_video_edl(source: bytes, *, intents: tuple[VideoEditIntent, ...],
               sequence_id: str, sequence_start_word_id: str,
               sequence_end_word_id: str,
               caption_groups: CaptionGroupsArtifact,
               emphasis_events: EmphasisEventsArtifact,
               word_to_frame: WordToFrameArtifact,
               caption_preview: CaptionPreviewArtifact,
               v5_v6_collision_report: V5V6CollisionReport,
               fps_numerator: int, fps_denominator: int) -> VideoEdlArtifact
serialize_video_edl(artifact: VideoEdlArtifact) -> bytes
```

The loader derives the expected result but validates the supplied envelope in
this exact precedence; the first matching row wins even for a multi-fault
payload.

| Order | Validation | Rejection |
|---:|---|---|
| 1 | exact `bytes` input | `TypeError` |
| 2 | UTF-8 / BOM / duplicate key / JSON grammar / canonical lexical form | `NON_CANONICAL_SERIALIZATION` at `/` |
| 3 | root, nested record, and fixed-12-track exact key/type shape | `STRUCTURE_INVALID` at closest pointer |
| 4 | schema/hash literals and enum values | `UNSUPPORTED_VALUE` at closest pointer |
| 5 | supplied dependency serialization and complete lineage/rate/preview-scene binding | `DEPENDENCY_CONTENT_DRIFT` or `DEPENDENCY_BINDING_INVALID` |
| 6 | sequence ID/bounds, cue resolution, source playback/crop/null matrix, ordinal namespaces, local frame values, and track order/overlap | `CUE_RESOLUTION_INVALID` or `TRACK_COLLISION` |
| 7 | collision report zero-findings prerequisite | `V5_V6_COLLISION_BLOCKED` |
| 8 | each event identity/hash | `IDENTITY_MISMATCH` at its event pointer |
| 9 | root identity/hash | `IDENTITY_MISMATCH` at `/` |
| 10 | complete canonical bytes equal independently derived expected envelope | `NON_CANONICAL_SERIALIZATION` at `/` |

It never trusts supplied event timing, track priority, source descriptor, or
identity. BOM, malformed UTF-8, floats, JSON constants, noncanonical number
spellings, trailing whitespace, and noncanonical key order always terminate at
row 2. This table is also the required test oracle.

`VideoEdlContractError(pointer, reason, issue_code=None)` is `ValueError` and
its exact text is `Video EDL rejected: <REASON>`; hostile source text is never
rendered in the message.  Reasons are exactly `STRUCTURE_INVALID`,
`UNSUPPORTED_VALUE`, `DEPENDENCY_CONTENT_DRIFT`, `DEPENDENCY_BINDING_INVALID`,
`CUE_RESOLUTION_INVALID`, `TRACK_COLLISION`, `V5_V6_COLLISION_BLOCKED`,
`NON_CANONICAL_SERIALIZATION`, `IDENTITY_MISMATCH`, `CONTENT_DRIFT`, and
`NOT_MATERIALIZED`.  Pointers are `/`, `/intents`, `/word_to_frame`,
`/caption_preview`, `/v5_v6_collision_report`, `/tracks`, or
`/tracks/<uint32>/events/<uint32>`.

Successful compile/load places the exact immutable object and bytes in a
weak-reference registry.  Serialization requires exact live registered type,
detects recursive identity/content drift, and returns registered bytes.  There
is no fallback serialization, mutable builder, or unbounded cache.

## 8. Timeline-debug artifact

`compile_timeline_debug(*, video_edl: VideoEdlArtifact) -> TimelineDebugArtifact`
first serializes the genuine EDL.  It emits one entry per video event in
global `(start_frame, end_exclusive_frame, priority, event_id)` order.  The
entry is a readable provenance index, not a second scheduler: it repeats exact
event values and no derived milliseconds.  It contains no audio entry in this
package.  Its `duration_frames`, clock, and EDL identity must match exactly.

`load_timeline_debug(source: bytes, *, video_edl: VideoEdlArtifact) ->
TimelineDebugArtifact` and `serialize_timeline_debug(artifact)` use the same
strict parser, expected-output comparison, weak registry, and this exact
precedence: bytes type; canonical lexical JSON; root/entry shape; literals and
enums; genuine EDL serialization and identity binding; entry order and exact
event projection; entry identities; root identity; expected-envelope byte
equality. The corresponding reasons are respectively `TypeError`,
`NON_CANONICAL_SERIALIZATION`, `STRUCTURE_INVALID`, `UNSUPPORTED_VALUE`,
`DEPENDENCY_CONTENT_DRIFT`/`DEPENDENCY_BINDING_INVALID`, `ENTRY_INVALID`,
`IDENTITY_MISMATCH`, `IDENTITY_MISMATCH`, and
`NON_CANONICAL_SERIALIZATION`. `TimelineDebugContractError` text is exactly
`Timeline debug rejected: <REASON>`.  Its reasons are exactly
`STRUCTURE_INVALID`, `UNSUPPORTED_VALUE`, `DEPENDENCY_CONTENT_DRIFT`,
`DEPENDENCY_BINDING_INVALID`, `ENTRY_INVALID`,
`NON_CANONICAL_SERIALIZATION`, `IDENTITY_MISMATCH`, `CONTENT_DRIFT`, and
`NOT_MATERIALIZED`; pointers are `/`, `/video_edl`, `/entries`, or
`/entries/<uint32>`.

## 9. Complexity and resource ceiling

Compilation is `O(W + C + E + I + O)` time and memory, where W/C/E are the
accepted word/caption/emphasis rows, I caller intents, and O emitted video
events.  It indexes word IDs and merges ordered streams once; validation of
same-track non-overlap is a single pass per track.  Debug compilation is
`O(O)` after EDL validation.  Sorting an untrusted event list is forbidden;
canonical source ordering must be supplied or rejected.  No per-frame
allocation, quadratic pair scan, font/media allocation, I/O, process, thread,
or retained historical artifact is permitted.

## 10. Mandatory acceptance tests

Focused tests must prove exact public exports, constants, models, field order,
signatures, canonical literal goldens, identity recomputation, 30/1 and
30000/1001 exact WordToFrame-rate equality, half-open boundary behavior,
sequence-local bounds and explicit zero trailing-silence limitation,
word-ID-only resolution, repeated-word non-search, caller/generated ordinal
namespace separation, source `HOLD`/`LOOP`/`FIT` playback formulas, V5/V6
compiler ownership and complete payload null matrix, preview scene
source/span/combined-ordinal equality, exact structured `EmphasisTypeRef`
projection/type binding, generated editorial-role literals, unified
`TimelineTrack` use in request/event/EDL/debug serialization, all 12 Master
registry tracks in order,
all empty A tracks, z priorities, same-track overlap rejection, allowed
cross-track layering, zero-finding collision prerequisite, dependency drift
and mutation, every loader-precedence row, weak registry cleanup, and two
equivalent independent compilations.

The fixture set must include a compact real REPLAY chain containing V1 through
V7 plus V5/V6, and a high-cardinality chain with at least 10,000 words, 2,000
caption groups, 1,000 emphasis events, and 5,000 caller intents.  The latter
must assert event count, canonical byte/hash equality across two runs, no
per-frame materialization by static/observable guard, and a documented
linear-work bound; it must not use production media.  Tests must statically
reject imports for every excluded subsystem.

Before acceptance, run the two focused suites, exact Phase 2 temporal,
preview, and collision upstream suites, and the broad top-level non-FastAPI
regression.  Commercial APIs remain disabled.  A later independent adversarial
audit must pass before implementation acceptance.

## 11. Phase boundary and follow-up

This candidate does not authorize implementation until a separate acceptance
and authorization record exists.  Phase 3B will add the 48 kHz audio sample
clock and boundary planner while preserving this EDL's video identities and
fixed registry.  Phase 4 may consume only accepted EDL bytes and must not
re-schedule cues, calculate video timing, or reinterpret track priority.

```text
SPECIFICATION_STATUS=CANDIDATE
SPECIFICATION_DRAFTED=YES
SPECIFICATION_ACCEPTED=NO
IMPLEMENTATION_AUTHORIZED=NO
NEXT_ACTION=INDEPENDENT_READ_ONLY_SPECIFICATION_AUDIT
PHASE3_CLOSED=NO
```
