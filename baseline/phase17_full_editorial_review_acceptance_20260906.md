# Phase 17 — Full 39-second editorial review, 2026-09-06

## Scope and authorization

The user accepted the proposal to replace the slide-like 11-second fragment
with a coherent first cut of the complete three-chapter, 39-second story.
Phase 17 remains SCOPE_RECONCILIATION. This bounded artifact task covers
manual editorial selection, local narration, real footage, evidence inserts,
explanatory graphics, audio mixing and a review page. It does not implement
automatic asset selection/Director intelligence, canonical sequence/EDL
publication, new domain packs, commercial APIs or public YouTube publication.
The roadmap and existing production renderer path are unchanged.

## Result and bounded acceptance

`EDITORIAL_REVIEW_DRAFT_RENDERED`, not phase completion or production approval.

- Final: `output/phase17-full-review-20260906/full-39s-editorial-review.mp4`.
- SHA-256: `2d34e8582b1f7d92ca1a82cf0ba5c86f1f3cf7f7136fbc82ec8c15471acc5fbf`.
- 18,005,557 bytes; 1920×1080, 30 fps, 1170 frames, exactly 39 seconds.
- 3 current chapters, 10 current beats, 16 contiguous editorial shots.
- 17.5 seconds of actual illustrative footage; 5.7 seconds of source inserts;
  15.8 seconds of explanatory graphics. Selection and cuts were agent-directed.
- Ten source WAV placements independently measured in decoded output: maximum
  start error 0 ms at 24 kHz measurement resolution, within one frame.
- Stereo 48 kHz AAC; integrated loudness −16.11 LUFS, true peak −1.38 dBTP.
- Full FFmpeg decode passes. No commercial API calls.
- Independent input/source audit found one caption boundary error in beat 4;
  `[5,4]` became `[4,5]`, then the picture was rendered again. No other blockers.
- Final contact sheet and first-pass full-size frame inspection show readable
  figures and captions, source qualification and clean layout. These checks
  do not establish audience retention or human listening approval.

The DOE 350/15 split is explicitly illustrative, limited to constrained
locations and non-chronological. Backup/storage are possibilities, subject to
constraints. The 300–1000 MW or larger / 1–3-year figures retain DOE scope.
EIA original captured article text supports US gas generation growth of 7.3%
versus 1.7% over 2025–2027, and modeled 2027 ERCOT wholesale prices about
$37/MWh above baseline. None are described as actual outcomes or household bills.

## Changed files and artifacts

- `renderer-remotion/src/editorial-cut-review.tsx` and
  `renderer-remotion/src/editorial-cut-review-entry.tsx`: independent generic
  review composition. All topic wording, figures and sources arrive in props.
  The production entry point and core/domain architecture are untouched.
- `output/phase17-full-review-20260906/`: current chapter and catalog snapshots,
  canonical chapter records, scripts, exact audio, alignment receipts, selected
  footage derivatives, render props/manifest, mixed audio, first/final pictures,
  final MP4, frame images, contact sheet, checks and page builder.
  First/second audio takes and first picture are retained as history.
- `renderer-remotion/public/phase17-full-review-20260906/`: hashed render inputs.
- `studio-ui/public/reviews/full-39s/2d34e8582b1f/`: local review bundle with
  video, chapter/shot seeking, per-shot local notes and JSON revision-note export.
  Notes do not trigger generation. The page does not invent canonical review approval.
- This report and scoped updates to CURRENT_STATE, NEXT_ACTIONS, CHANGELOG,
  KNOWN_LIMITATIONS and PHASE_ACCEPTANCE.

Review URL:
`http://127.0.0.1:5173/reviews/full-39s/2d34e8582b1f/index.html`.

## Commands and verification evidence

- `npm run typecheck` in `renderer-remotion`: PASS.
- Local Kokoro `produce_audio.py`, bounded revisions and final reuse/hash
  verification: all 10 narration files fit their beats. Overlong first takes
  were retained and replaced; final narration receipts match exact text/audio.
- `align_audio.py`: seven new WhisperX jobs return 0; first three reuse their
  exact measured alignment. No external timing service or model download.
- `prepare_cut.py`: current chapter identity, catalog byte hashes, contiguous
  schedule, caption coverage and complete WAV fit checks PASS.
- Remotion CLI `render src/editorial-cut-review-entry.tsx editorial-cut-review-v1`
  with `render-props.json`, H.264/yuv420p/CRF17/concurrency2: first visual-QA
  render and one targeted caption-fix render both return 0.
- `mix_audio.py`: deterministic original non-diegetic tone bed, quiet pulse/cut
  accents, ducking and exact narration sample placements; no stock music.
- `finalize_cut.py`: constant gain and latency-compensated limiter, AAC mux,
  ffprobe frame/duration checks, full decode, loudness scan and WAV correlation
  PASS. `render-receipt.json`, `ffprobe.json`, `loudness-final.json` and
  `audio-sync-verification.json` contain exact evidence.
- `make_review_page.py`: local bundle generated; browser QA stored separately
  in `browser-playback.json`. Playback completion is not human listening approval.
- One independent final input audit by `revision_review`; no repeated audit
  after the isolated, verified caption-group repair.

## Limits and next task

This is a manually directed first cut, not a working automatic research-to-video
pipeline. Actual shot replacement from the main Studio interface remains open.
Review-page notes are local feedback, not canonical workflow events. Some
footage is from a 480p original and retains source-video visual limitations;
the Portugal transmission footage is illustrative and explicitly labeled.
Full attribution and CC BY links appear on the review page; original footage
audio is muted. Local synthesized accompaniment is a simple draft sound bed.
Automatic alignment is not a human timing approval; the reused DOE acronym
token has 0.505 confidence. Narrative appeal and voice quality still need the
user's actual viewing/listening judgment. Phase 17 remains open.

**Single recommended next task:** `PHASE17_FULL_CUT_CREATIVE_REVIEW_AND_ONE_REVISION`:
review the delivered complete cut and apply one bounded revision to named shots
based on the user's actual response. Do not infer approval from playback.

## DOCUMENTATION_IMPACT_MATRIX

| Document | Impact | Action |
|---|---|---|
| CURRENT_STATE.md | Complete 39-second draft now exists | Scoped checkpoint |
| NEXT_ACTIONS.md | User expanded opening review into a full first cut | Exactly one current next task |
| CHANGELOG.md | New cut, local review page and validation evidence | Scoped checkpoint |
| KNOWN_LIMITATIONS.md | Remaining 28 seconds no longer unrendered; automatic production still absent | Superseding checkpoint, preserve history |
| PHASE_ACCEPTANCE.md | Bounded artifact evidence only | Record results; Phase 17 stays open |
| QUALITY_BENCHMARKS.md | No new general quality threshold or audience result | Reviewed; unchanged |
| ARCHITECTURE_DECISIONS.md | Separate review entry, no core architecture change | Reviewed; unchanged |
| MASTER_ROADMAP.md | User authorized artifact production, no roadmap change | Reviewed; unchanged |

Documentation is reconciled in a separate clean bounded doc worktree. Only the
five scoped documents and this report are committed/pushed; accumulated local
implementation and media are not bulk staged. Remote proof is recorded under
`output/phase17-full-review-20260906/documentation-sync.json` after verification.
