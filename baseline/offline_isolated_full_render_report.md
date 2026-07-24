# Offline Isolated Full Render Report

## Closure objective

Prove that the canonical baseline render can be reproduced twice with identical immutable local inputs, no provider or network access, and no repository output/cache/temp mutation.

## Authoritative repository revision

- repository: `C:\Users\user\Documents\Kurgu_V3_Clean_sanitized_freesound_20260724_224147304`
- revision: `7f877a311bb6ab1f02c24bf35cdfa90cc14928e7`

## Canonical production orchestrator

- selected path: `v2.main.process_timeline` via verification harness
- root `main.py` normal render was not selected because it does not expose any hook for fail-closed provider/network guard installation or run-scoped evidence capture without broader production changes

## Fixture selection rationale

- canonical fixture: `baseline/fixtures/phase0_offline_full_render.json`
- fixture SHA-256: `46163fe535ab0b931540a1cc6864a78a2a8858def0d24ce92175739b14a9d8e0`
- fixture uses only `audio_file` local narration inputs and `stock` visuals with `locked_local` assets
- fixture duration target is satisfied by two narrated blocks and four visual scenes

## Why test_1_min.json was or was not used

- `test_1_min.json` was not used because it contains provider/browser-dependent visuals such as document capture, image PIP, and unresolved stock queries that would violate fail-closed offline execution

## Offline/fail-closed guard

- result: `PASS`
- blocked channels: Pexels, web capture, YouTube downloader, Edge TTS, ElevenLabs, socket/requests/urllib network calls, and known network-capable subprocesses

## Input provenance and hashes

- immutable inputs were materialized outside the repository and copied unchanged into both run roots
- all run 1 and run 2 input hashes matched exactly

## Isolation strategy

- each render ran from its own `C:\tmp\kurgu_phase0_offline_render_run*` root
- production cwd was the run root, so `temp_assets`, `output`, `norm_words_debug.json`, and `whisper_debug.json` were emitted only there

## Run 1 summary

- run root: `kurgu_phase0_offline_render_run1_20260724_235505`
- output: `output\final_video_v2.mp4`
- output SHA-256: `5dce729f2200b3f22a8be303350b11648776ffcbecf6a1d40606ddefd8bd0a03`
- provider/network attempts: `0`

## Run 2 summary

- run root: `kurgu_phase0_offline_render_run2_20260724_235505`
- output: `output\final_video_v2.mp4`
- output SHA-256: `5dce729f2200b3f22a8be303350b11648776ffcbecf6a1d40606ddefd8bd0a03`
- provider/network attempts: `0`

## FFmpeg/ffprobe validation

- ffmpeg: `ffmpeg version 8.1.2-full_build-www.gyan.dev Copyright (c) 2000-2026 the FFmpeg developers`
- ffprobe: `ffprobe version 8.1.2-full_build-www.gyan.dev Copyright (c) 2007-2026 the FFmpeg developers`
- run 1 decode check: `0`
- run 2 decode check: `0`

## A/V duration comparison

- run 1 video/audio: `35.633s / 35.630s`
- run 2 video/audio: `35.633s / 35.630s`
- run 1 drift: `0.003s`
- run 2 drift: `0.003s`

## Decoded video fingerprint comparison

- equal: `True`

## Decoded audio fingerprint comparison

- equal: `True`

## Network/provider attempt result

- provider attempts: `0`
- network attempts: `0`

## Repository mutation result

- mutation count during render interval: `0`

## Output isolation result

- run roots only: `True`

## Full-suite regression result

- pytest result: `56 passed`

## Reproducibility decision

- final decision: `PASS`

## Remaining Phase 0 items

- Provider revoke/rotation: `NOT CONFIRMED`
- Baseline tag: `PENDING`
- General Phase 0 remains open only for final closure/tag decision
