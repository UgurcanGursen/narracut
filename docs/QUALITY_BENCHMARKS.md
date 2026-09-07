# Quality Benchmarks

## Latest checkpoint — 2026-09-07, actual Studio working edit

The saved business-tech project now renders a measured 87.866667-second,
six-scene, 1080p/30fps working edit with local speech, word alignment and 23
executed visual cues. Final job `ejob_625336760cc24f69b3d91f59bb044dca`. UI review and selected-scene
production work; the final revision changes only scene 2 and preserves the other
five scene video hashes. Speech/alignment are reused for visual-only changes.

Actual-output QA caught and repaired cumulative AAC/concat timing displacement.
Final decoded full-cut and single-scene PCM comparison maximum offset is
0.0 ms across 36 comparisons. This is mux accuracy,
not human listening or semantic approval. 31 backend/mux and 40 UI tests pass;
build, renderer typecheck, generated client and HTTP boundary pass.

This is an unapproved working edit with independent measured duration and exact
accepted chapter ancestry. Old canonical 39-second allocations are unchanged.
Automatic creative planning/footage selection, sound design and canonical
promotion remain outstanding. The current manual direction was agent-authored;
one result does not establish reliable professional first-pass quality.
Phase 17 SCOPE_RECONCILIATION remains OPEN. No commercial API calls.

Current UI: `http://127.0.0.1:5173/#studio-video`; final API: localhost **8003**,
selected through ignored `studio-ui/.env.local`. Existing servers were preserved
after automatic approval review blocked a restart command.

Acceptance, commands, file inventory and DOCUMENTATION_IMPACT_MATRIX: `baseline/phase17_studio_working_edit_acceptance_20260907.md`.

## Previous checkpoints (historical)

## Latest checkpoint — 2026-09-06, joint narration/visual treatment

The owner rejected the 39-second cut's creative quality and narration/visual
relevance. Mechanical timing/playback PASS does not mean creative acceptance.
The earlier video remains an unaccepted editorial draft.

The actual business-tech 0.3.2 project now has a persistent Studio joint planning
workbench: six scenes, ten current beats, 21 word-cued visual events, estimated
83–109 seconds. The agent authored this plan; MANUAL_UI task download/import is
available for the owner's external AI tools. No commercial API calls.
Latest treatment: `etreat_33231dd0a14a464bbd02eb20`.
UI: `http://127.0.0.1:5173/#editorial-treatment`.

Evidence/parent checks, cue ordering, cross-scene object state continuity,
immutable revisions, stale/concurrent edit rejection and actual UI save/reopen
pass. Twenty backend tests, targeted UI tests, production build and client/boundary
checks pass. This is PREPRODUCTION_DRAFT only: no new audio/video, measured timing,
canonical activation or creative approval. The old canonical 39-second allocation
remains; migration and treatment-to-Director/renderer execution are still required.
Phase 17 SCOPE_RECONCILIATION stays OPEN.

Acceptance, file inventory and DOCUMENTATION_IMPACT_MATRIX: `baseline/phase17_joint_editorial_treatment_acceptance_20260906.md`.

## Previous checkpoints (historical)

> Phase 14 note (2026-08-06): local REPLAY lifecycle evidence is not a Phase
> 16 reference-quality threshold. The FFmpeg fixture preserves final MP4 bytes
> plus audio-plan/filter/PCM hashes across two producers; see
> `baseline/phase14_master_acceptance.md`.

Son güncelleme: 6 Ağustos 2026

## Mevcut kanıtlar

| Kanıt | Sonuç |
|---|---|
| `python -m pytest -q` | 29 passed, 2 failed |
| `main.py --validate-only test_1_min.json` | valid |
| `main.py --validate-only timeline.json` | valid, 3 warning |
| `output/validation_report.json` | `failed_quality_check` |
| truthful acceptance run | `acceptance_status=failed` |

Son legacy video `output/final_video_v2.mp4` için raporlanan süre 134.8 s;
rapor video/audio farkını 140.98 s / 134.80 s olarak kaydediyor. Üç TTS WPM
uyarısı var: 166.2, 157.3, 225.0.

Truthful acceptance run'ında pacing ve asset alt durumları valid; technical,
editorial, alignment ve pixel alt durumları invalid. Bu artifact başarılı
benchmark olarak sınıflandırılmamıştır.

## Faz 0 benchmark politikası

- Mevcut MP4, fixture, config ve raporlar silinmez veya overwrite edilmez.
- Başarısız rapor başarılı baseline sayılmaz.
- Faz 0'da yeni kalite threshold'u veya renderer davranışı eklenmez.
- Hash'ler `baseline/baseline_manifest.json` içinde tutulur.

## Henüz kanıtlanmayan

- Aynı input ile başarılı, ağdan bağımsız, tekrar üretilebilir full render.
- System `ffprobe` ile black-screen analizi.
- `stage3-development-baseline` tag'ine bağlı salt-okunur artifact paketi.
- Roadmap Faz 16 referans benchmark metrikleri; bunlar Faz 0 kapsamı dışıdır.
