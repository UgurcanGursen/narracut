# Phase 17 — Active V2 opening review rendered, 2026-09-06

Result: **11-SECOND_EDITORIAL_REVIEW_RENDERED**. Phase 17 remains open.

## Delivered artifact

`output/phase17-opening-review-20260906/opening-11s-review-v3.mp4`

- 1920 × 1080, H.264/AAC, 30 fps, exactly 330 video frames / 11.000 seconds.
- Stereo 48 kHz audio, measured -16.29 LUFS and -1.49 dBTP.
- SHA-256: `f93445215bac0ee3f9ce99d8be533534aa49c4c1431a410235bd7ac87060c481`.
- Size: 3,139,923 bytes. Complete FFmpeg decode passes.
- Local viewing page includes playback, three scene seek buttons, source,
  MP4 download and return-to-Studio link:
  `http://127.0.0.1:5173/reviews/chap_e8aa8b74e3b3b9e46fd8/f93445215bac/index.html`.

## Scope and lineage

User authorized producing the previously proposed 11-second opening. The local
producer reopened active chapter `chap_e8aa8b74e3b3b9e46fd8` and all three beat
IDs/hashes through Studio, then read the canonical chapter's exact policy,
claim and evidence references. It checked the catalog-bound source crop and
original DOE PDF byte hashes before staging render inputs. No planner,
Director, canonical timing, review approval or product-publication row was
fabricated or modified. Chapters 2 and 3 and the 39-second plan remain unchanged.

The new Remotion entry renders a parameterized source-reading review. Topic
wording and document labels are input data; the renderer has no domain switch
or embedded DOE-specific behavior. The existing production renderer entry and
render path remain unchanged. This does not close the canonical sequence /
Director / timing / EDL / final-product pipeline for the revised chapter.

## Editorial and audio decisions

- Scene 1, 0–3 s: “What about the other fifteen days?” Source's remaining-day
  phrase is highlighted. The illustrative/constrained-location qualifier is visible.
- Scene 2, 3–7.5 s: “D O E's example: constrained grids, around three hundred
  fifty days.” Source scope and `(say) 350 days` are highlighted.
- Scene 3, 7.5–11 s: “Those remaining fifteen days need another solution.”
  Source's backup/storage possibility and its constraints remain visible.
- One actual source paragraph is reused intentionally; it is not counted as
  three unique assets. No literal day-350 outage/calendar is shown.
- Local Kokoro `am_fenrir`, speed 1.10; no commercial API call, generated stock
  imagery, or new provider connection. The first longer second sentence was
  5,312 ms and rejected. The shorter take is 4,330.667 ms; rejected take retained.
- Local pinned WhisperX aligned all 24 spoken tokens. Actual WAV durations plus
  start offsets fit the 3,000 / 4,500 / 3,500 ms budgets.
- The initial mux had 100 ms of normalization tail and about 43 ms constant
  audio displacement. Final audio is bounded to exactly 11 seconds and applies
  the measured 43 ms compensation. FFT cross-correlation against each exact
  source WAV measures final start errors of 0.333 / 0 / 0 ms.

## Validation

Commands run from the authoritative workspace with existing local runtimes:

| Command/check | Result |
| --- | --- |
| `.venv-kokoro/Scripts/python.exe -B .../produce_audio.py` | Three final WAVs fit; failed longer take retained |
| `.venv-studio/Scripts/python.exe -B .../align_audio.py` | Three local WhisperX runs succeeded; 24 tokens |
| `.venv-studio/Scripts/python.exe -B .../build_review.py` | Active chapter, source/catalog hashes and word coverage pass |
| Remotion CLI `render src/chapter-review-entry.tsx chapter-source-review-v1 ... --props ... --codec h264 --pixel-format yuv420p --crf 17 --concurrency 2` | Actual 330-frame render completed |
| `.venv-studio/Scripts/python.exe -B .../finalize_review.py` | Final v3 duration, decode, audio and loudness checks pass |
| `.venv-kokoro/Scripts/python.exe -B .../verify_audio_sync.py` | All three actual rendered voice offsets pass |
| `npm run typecheck` in `renderer-remotion` | PASS |
| CUA browser playback | duration/currentTime=11, ended=true, readyState=4, error=null, 1920×1080 |
| Visual frame inspection | Contact sheet and full-resolution source/number/caption frame inspected; no crop/title/caption overlap |
| One independent final input audit | PASS: active lineage, source meaning, media bytes, durations and honest draft status |

The initial failed duration/sync checks were repaired before final delivery.
No broad repository test suite was run: the existing production engine was
not modified. Playback completion and media measurements are not a claim of
human listening or professional creative acceptance.

## Changed files and supporting artifacts

- New `renderer-remotion/src/chapter-review.tsx` and `chapter-review-entry.tsx`.
- New local production/evidence directory `output/phase17-opening-review-20260906/`:
  production, alignment, build, finalization, audio-sync and viewing-page scripts;
  active chapter snapshot; scripts/WAVs/alignment receipts; source-bound manifest;
  render props; raw and retained intermediate MP4s; final v3 MP4; FFprobe/loudness/
  sync receipts; source-reading frames/contact sheets; review HTML and URL.
- Exact inputs staged under `renderer-remotion/public/phase17-opening-review-20260906/`.
- Local static viewing bundle under `studio-ui/public/reviews/chap_e8aa8b74e3b3b9e46fd8/f93445215bac/`.
- Five authoritative status documents updated, plus this acceptance record.

Generated media and local implementation remain local. The separate documentation
branch records this outcome without bulk-staging the pre-existing dirty tree.

## Remaining limits and single next task

This is **EDITORIAL_REVIEW_DRAFT**, not canonical final-video publication.
`human_timing_approval=false`, `canonical_publication=false`. WhisperX assigned
0.505 confidence to the acronym token `E's`; human listening/timing review is
still required before canonical approval. No old timing approval was reused.
The remaining 28 seconds of the 39-second project have not been rendered.

Single next task: `PHASE17_V2_OPENING_CREATIVE_AND_TIMING_REVIEW` — inspect the
delivered opening, collect actual feedback and timing approval, then apply any
bounded corrections before promoting the revised chapter through production.

## DOCUMENTATION_IMPACT_MATRIX

| Document | Impact |
| --- | --- |
| CURRENT_STATE.md | Updated: actual 11-second draft video and measured result |
| CHANGELOG.md | Updated: production run, quality corrections and final artifact |
| NEXT_ACTIONS.md | Updated: one next task, opening creative/timing review |
| KNOWN_LIMITATIONS.md | Updated: canonical pipeline and remaining 28 seconds open |
| PHASE_ACCEPTANCE.md | Updated: review MP4 passes local media gates; Phase 17 open |
| QUALITY_BENCHMARKS.md | Reviewed, unchanged: no human creative-quality acceptance |
| ARCHITECTURE_DECISIONS.md | Reviewed, unchanged: preview does not alter production architecture |
| MASTER_ROADMAP.md | Reviewed, unchanged: original multi-domain core / pack model retained |
