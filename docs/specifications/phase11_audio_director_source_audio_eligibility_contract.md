# Phase 11 Audio Director and Source Audio Eligibility Contract

Status: accepted and closed bounded implementation scope

## Boundary

Phase 11 is a local `REPLAY`/`MANUAL_UI`-first planning layer. It consumes
accepted Phase 8 source-audio eligibility metadata and produces immutable,
Domain-Pack-bound audio-direction artifacts. It does not open media, classify
audio with a provider, mix PCM, invoke FFmpeg, create an EDL, select an asset,
or automate a browser.

Phase 3 remains the owner of 48 kHz sample-grid/boundary compilation. Phase 12
will bind a Phase 11 plan with approved visual decisions and use the Phase 3
compiler to produce the final EDL.

## Policy

`AudioDirectorPolicyV1` resolves only from the active immutable Domain Policy
Snapshot. It declares the allowed source-audio modes, music intensities, event
types, speech modes and the 2-6 second source-speech duration range. Core code
contains no domain-name branch or silent default.

## Immutable artifacts

```text
SourceAudioAnalysisV1
  analysis_id/hash, asset_id/hash, source_audio_mode,
  speech_presence_bps, music_contamination_bps, noise_bps,
  speech_intelligibility_bps, recommended_duration_ms,
  policy_snapshot_id/hash

ChapterAudioDirectionV1
  chapter_brief_id/hash, music_intensity, event_type_tokens,
  source_analysis_id/hash pairs

AudioDirectionPlanV1
  plan_id/hash, project_id, policy_snapshot_id/hash,
  sample_rate_hz=48000, intermediate_format=pcm,
  ordered chapter directions
```

Only a Phase 8 `eligible` audio asset with `rights_confirmed` provenance can
produce `clean_speech` or `speech_with_ambience`. Both require narration
`pause` and BGM `hard_duck` or `mute`; thus source speech cannot overlap
narration or un-ducked BGM. `embedded_music`, `unusable` and `disabled` cannot
produce a source-speech directive. `ambience_only` can never be source speech.

The contract does not invent timestamps. Its 48 kHz/PCM declarations are a
typed handoff to Phase 3 and Phase 12, not a replacement sample compiler.

## Acceptance gates

1. Business-tech and contract-only dummy Domain Packs resolve the same core
   artifact structure without a domain-name branch.
2. Policy/asset/provenance mismatch, non-eligible speech, narration overlap,
   un-ducked BGM, invalid duration and unsupported event type fail closed.
3. Every planned chapter has one music state; no chapter plan has only source
   speech or implicit music behavior.
4. Two identical replays serialize byte-identically with a 48 kHz PCM handoff.
5. The plan contains no EDL, renderer input, provider call, live transport or
   concrete asset-selection decision.
