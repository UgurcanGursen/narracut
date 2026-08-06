# Phase 12 Continuity and Executable Editorial Integration Contract

Status: accepted and closed bounded implementation scope

## Boundary

Phase 12 is a local `REPLAY`/`MANUAL_UI`-first deterministic integration
compiler. It is the only owner of the bridge from accepted Phase 10 planning
artifacts to executable editorial decisions. It consumes immutable Phase 10
sequence plans, accepted Phase 8 catalog records and selected ranges, Phase 5
template capabilities, optional Phase 7 visualization artifacts and Phase 11
audio-direction plans under one immutable Domain Policy Snapshot.

It emits an immutable `ExecutableEditorialPlanV1`, explicit continuity/pacing
receipts and Phase 3 compilation inputs. It delegates frame/sample scheduling
to the existing Phase 3 compiler. It never opens media, guesses timestamps,
uses source URLs, renders, mixes, calls a provider, changes a planner result,
or mutates a catalog.

## Policy and continuity

`EditorialIntegrationPolicyV1` resolves only from the active immutable Domain
Policy Snapshot. It declares the maximum consecutive template/family reuse,
the permitted pacing roles and whether an execution row may be asset-only,
visualization-only or both. Core code contains no domain-name condition and no
implicit template, asset, crop, music or pacing default.

For every ordered sequence the compiler records a `ContinuityStateV1` before
and after the decision. It fail-closes when a selected visual family or
template exceeds the policy's consecutive-reuse limit, a required reset is
missing, an approved asset/range/crop reference is absent, or a planner
capability pair cannot be resolved to the active template capability.
Every sequence provides an explicit Phase 11 chapter-audio-direction ID/hash
pair; Phase 12 never guesses a chapter mapping from a beat or sequence name.

## Immutable artifacts

```text
ApprovedAssetSelectionV1
  selection_id/hash, planner_asset_brief_id/hash,
  phase8 asset_id/hash, selected range, crop, approval provenance

TemplateCapabilityV1
  cap_id/hash, Phase 5 template definition/version and policy binding

ContinuityStateV1
  state_id/hash, ordered sequence position, prior/current visual family,
  template, visualization kind and audio intensity

ExecutableSequenceV1
  execution_id/hash, Phase 10 sequence-plan pair, approved asset selection,
  template capability, optional Phase 7 visualization and Phase 11 audio
  direction references, incoming/outgoing continuity-state pairs

ExecutableEditorialPlanV1
  plan_id/hash, Phase 10 assembly-request pair, policy snapshot pair,
  ordered executable sequences and explicit Phase 3 compilation handoff

FinalEdlBundleV1
  bundle_id/hash, executable-plan pair, ordered per-sequence Phase 3
  video-EDL and hash-bound audio-EDL pairs
```

Every ID/hash pair is recomputed from canonical JSON. All cross-phase inputs
must have the same project and policy snapshot. A source asset is represented
only by the approved Phase 8 record/range/crop decision; no URL or renderer
props are synthesized in this layer.

## Phase 3 handoff

The executable plan may create `VideoEditIntent` inputs only from an approved
asset selection plus an explicit caller-supplied word cue and source playback
descriptor. Phase 12 calls the existing Phase 3 video compiler; it does not
reschedule, serialize by hand, or reinterpret its result. A Phase 3 audio EDL
remains dependent on explicit PCM/timing inputs: Phase 11's direction is a
policy decision, not an invented audio timestamp. The final bundle therefore
accepts only Phase 3-produced video/audio artifacts, requires every audio EDL
to bind its paired video EDL, and records ordered hashes without rewriting
either artifact.

## Acceptance gates

1. Business-tech and contract-only dummy Domain Packs resolve the same core
   plan structure without a domain-name branch.
2. Missing or forged planner, policy, capability, asset, range, crop,
   approval, visualization, audio-direction or continuity reference fails
   closed before a Phase 3 compiler call.
3. Consecutive visual-family/template reuse and invalid pacing-role transitions
   are reported as deterministic continuity failures; every accepted sequence
   has explicit incoming and outgoing state.
4. A two-sequence identical replay produces byte-identical executable-plan and
   final-bundle bytes; every Phase 3 video/audio EDL pair remains unchanged.
5. No provider call, transport, queue/retry, media-open, renderer invocation,
   UI mutation or silent fallback belongs to the accepted Phase 12 boundary.
