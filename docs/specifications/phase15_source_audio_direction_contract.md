# Phase 15 Source Audio Direction Validator Contract

Status: candidate contract for independent audit; not implementation authority.

## Phase and bounded objective

This is Phase 15 validation/observability work. It attaches already accepted
Phase 8 asset metadata and Phase 11 source-audio direction evidence to the
canonical Phase 15 quality ledger. It answers a narrow question only:

> Does the accepted source-speech direction remain policy-safe, including the
> existing contamination decision and BGM/narration conflict direction?

It is not an audio mixer, a media classifier, a waveform/pixel validator, an
audio-boundary analyser, a renderer or an EDL mutator.

## Exact inputs

The public validator will accept only:

- one exact immutable `DomainPolicySnapshot` and expected snapshot ID/hash;
- one or more exact Phase 8 `AssetRecordV1` values, with unique `(asset_id,
  asset_hash)` pairs;
- one exact Phase 11 `AudioDirectionPlanV1`;
- `run_id`, UTC timestamp and first ordinal.

It will derive `AudioDirectorPolicyV1` only with
`audio_director_policy_from_snapshot(snapshot)`. It will reject a plan whose
project/snapshot/policy identity differs from that derivation. It will
materialize `plan.data()` and `canonical_audio_direction_json(plan)` before
emitting evidence; mutable look-alikes, forged ID/hash pairs and incomplete
directions therefore do not create a PASS observation.

Each analysis must map to exactly one supplied Phase 8 asset. The validator
will re-run the existing `AudioDirectorService.analyze` using the stored mode,
speech-presence, contamination, noise, intelligibility and duration values.
The recomputed analysis must have the same canonical ID/hash as the plan row.
This deliberately reuses the existing Phase 11 policy and its existing
contamination/intelligibility decisions; it introduces no threshold value.

## Required outcomes

The implementation will add only these Phase 15 ledger extensions:

- evidence-reference kind: `source_audio_direction`;
- quality check ID: `source_audio_safety`;
- a reference made from the canonical Phase 11 plan ID and hash-bound
  canonical plan bytes;
- exactly one ordered `quality_gate/check_evaluated` observation for the
  request, using the derived audio-director policy hash.

For every direction containing `source_speech_in` or `source_speech_out`, the
existing pair requirement must hold and at least one referenced recomputed
analysis must be a source-speech mode. Those analyses must have the existing
`narration_conflict_policy == "pause"` and
`bgm_conflict_policy in {"hard_duck", "mute"}` conditions. No source-speech
direction may be accepted for an ineligible/no-rights/no-audio asset, an
embedded-music/ambience/unusable/disabled mode, or a recomputation rejected by
the existing contamination/intelligibility policy.

A structurally invalid or unverifiable input is rejected before observation
creation with a closed public error code. A structurally valid plan that
cannot preserve the source-speech safety condition yields a `FAILED`
`source_audio_safety` observation with a closed, non-secret public code.
A caller without a complete canonical plan is `NOT_READY`, never PASS. A plan
with no source-speech direction is PASS only for this narrow policy-direction
check; it does not assert a final PCM output was analysed.

## Required tests

- canonical eligible clean-speech plan produces an ordered ledger row and a
  PASS decision;
- forged snapshot/policy/asset/analysis bindings fail closed;
- Phase 8 ineligible or non-`rights_confirmed` source material cannot PASS;
- a manually forged clean-speech analysis that violates the existing
  contamination or intelligibility decision cannot PASS after recomputation;
- embedded music cannot be paired with source-speech events;
- a source-speech direction without pause + hard-duck/mute cannot PASS;
- missing plan produces `NOT_READY`; exact non-speech plan remains a narrow
  PASS;
- canonical JSONL and `evaluate_quality_gate` reject an unknown reference kind
  or check ID.

## Explicit exclusions and acceptance boundary

No live source/asset/timing transport, rate-limit/retry/queue worker, provider
call, browser automation, media decode/classification, mix/remix, FFmpeg,
renderer, EDL mutation, Studio/UI, Phase 16 benchmark or Phase 17 packaging
work is authorized. The validator does not close audio-boundary,
domain-final-narration, extension-readiness or host-wide orphan-artifact rows.
Phase 15 Master acceptance remains open.
