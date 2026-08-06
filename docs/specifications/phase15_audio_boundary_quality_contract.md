# Phase 15 Audio Boundary Quality Contract

The Phase 15 gate evaluates only a materialized Phase 3 `AudioEdlArtifact` and
an immutable Domain Pack policy. It does not decode new media or remix audio.

The policy declares `audio.audio_boundary_validation_policy` and the
`audio_boundary_quality` validation extension. It fixes maximum trim,
microfade and long-editorial-fade samples plus the maximum number of
non-zero `ZERO_CROSSING_MICROFADE` mitigations. The policy hash is recorded in
the observation.

The validator serializes the supplied artifact to prove its canonical identity,
then derives the mitigation count and extrema from `boundary_decisions`.
Values above fixed per-decision bounds fail as `AUDIO_BOUNDARY_POLICY_VIOLATION`;
a mitigation count above the immutable threshold emits `WARNING` with
`AUDIO_BOUNDARY_REMIX_REQUIRED`. Thus it cannot PASS when the planned
boundary-discontinuity risk exceeds policy. This is a planning/replay quality
signal, not a claim that final mixed PCM was measured.

No mixing, remix execution, renderer, provider, queue, UI, Phase 16 or Phase
17 behavior is authorized.
