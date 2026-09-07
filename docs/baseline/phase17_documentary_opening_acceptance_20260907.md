# Phase 17 — documentary opening repair

Date: 2026-09-07. Phase **17 SCOPE_RECONCILIATION, OPEN**.

The owner rejected the prior 87.866667-second vector-only edit as a presentation,
not a convincing YouTube video. Its earlier technical PASS does not override
that creative rejection. The new deliverable is explicitly an **OPENING_EXCERPT**:
the first **46.5 seconds**, not the complete video or a middle chapter.

## Actual artifact

Project: `prj_f01b4d80f4744c619f9b9567f819ba2f`.
Job: `ejob_9fd4a1421b884fd2840474da074f70ca`.
Parent treatment: `sha256:c8d0ba970aa12560e318c523047de0369e704ae0166e4d49fc10aa41f4e6232e`.
Direction: `sha256:7a2a92cf22ba93ff83f7e805215b7bc5029f2593043ad912c769d5e97a3f1769`.
Video hash: `sha256:00bdd59779b46a424d6f88fece74c47c9c3da0bbf77539fd86981fa52077b13f`.
Path: `output/studio-editorial-production/prj_f01b4d80f4744c619f9b9567f819ba2f/ejob_9fd4a1421b884fd2840474da074f70ca/video.mp4`.
Format: 1920×1080, 30fps, 1395 frames.
Five narration sections, 13 word-cued shots.
Current UI: `http://127.0.0.1:5173/#studio-video`; API localhost **8006** through
ignored `studio-ui/.env.local`. Earlier workers were preserved.

The opening uses the September 20, 2024 Microsoft/Constellation agreement as a
concrete entry point, then distinguishes contracted energy from delivery to a
new data center. The DOE one-to-three-year figure is explicitly requested
service, not guaranteed connection time. It ends on the delivery question.

Media include an NRC archival Three Mile Island site photo, real transmission
maintenance, selected facility footage, and an actual DOE report paragraph.
The camera choices, cut cues, text, inference and source limitations are stored
in the project-owned direction. An early cut lingered on the same photo and
showed talking tour participants; the repair shortened the history and switched
the later facility shots to physical rack details. Detailed license links and
modifications are in `output/phase17-opening-20260907/credits.md`.

The narration is local Kokoro with local WhisperX word alignment. A quiet,
original procedural score has cue accents and a deliberate drop under the
qualification. An initial bed around -51 LUFS was too low; the final score is
-34.57 LUFS. Final mix is
-17.12 LUFS,
-0.96 dBTP. It is not captured site sound.

## Scope and acceptance

In scope: repairing the actual current project's opening; traceable mixed
media direction; local voice/score/mux; Studio review and scene targeting;
schema-correct manual AI repair; visible failure and stale state.
Out of scope: complete long-form video, other domain packs, paid APIs,
automatic professional editing on unseen topics, canonical publication.

| Criterion | Result |
|---|---|
| Opening identified as partial in plan, job and player | PASS |
| Source/asset paths and content hashes verified before execution | PASS |
| Verbatim quote checked against captured HTML/text bytes | PASS |
| Ordered actual word cues; video range exhaustion rejected | PASS |
| 13 rendered shots matched to measured cues | PASS |
| Final full MP4 decodes; video duration/frame count match | PASS |
| Decoded voice/scene/full-mix comparison | PASS: maximum 0.0 ms mux offset |
| New working scene IDs do not overwrite parent scene IDs | PASS |
| AI repair package supplies documentary schema and pack instructions | PASS |
| Captured quote forgery and inherited parent variants rejected | PASS |
| Existing motion production and mux regressions | PASS |
| Owner creative/listening approval, audience retention | NOT CLAIMED |
| Full pilot house-style/preflight acceptance | NOT CLAIMED; this is a short working excerpt |

The independent final audit found two issues: a submitted quote list could
falsely self-certify an invented quote; the AI repair package still contained
legacy vector-only instructions. Both were repaired together and regression
tested. Current quoted material was accurate even before the gate fix.
No second independent audit or invented human approval is reported.

## Checks run

- `.venv-studio/Scripts/python.exe -m pytest tests/test_editorial_production.py tests/test_editorial_production_mux.py tests/test_documentary_direction.py -q --basetemp=output/phase17-opening-20260907/tests-backend-02`: **25 passed**.
- API production, treatment and OpenAPI contract tests with `studio-api/src` on sys.path: **15 passed**. One existing Starlette/httpx deprecation warning.
- Production/treatment UI tests: **10 passed**.
- `npm run build`, renderer `npm exec tsc -- --noEmit`, `npm run check:client`, `npm run verify:http-boundary`: **PASS**.
- Focused final mux/quote tests after score gain repair: **10 passed** (subset, not additional unique tests).
- `output/phase17-opening-20260907/verify_opening.py`: **TECHNICAL_PASS**, source hashes, all shot frames, PCM correlation, full decode, loudness and contact sheet.
- An initial pytest invocation hit a Windows permission error in the shared system temp folder; the owned repository-local basetemp rerun passed. No test failure is concealed as a pass.

Implementation files:
- `engine/planner/editorial_production.py`
- `engine/planner/documentary_direction.py`
- `engine/planner/documentary_score.py`
- `shared-schemas/editorial-documentary-direction-v1.schema.json`
- `domain-packs/business-tech-v0.3.2/prompts/editorial_documentary_direction.md`
- `renderer-remotion/src/editorial-documentary.tsx`
- `renderer-remotion/src/editorial-motion.tsx`
- `studio-ui/src/api/studioApi.ts`
- `studio-ui/src/components/EditorialProductionPanel.tsx`
- `studio-ui/src/components/EditorialProductionPanel.test.tsx`
- `studio-ui/src/components/EditorialTreatmentPanel.tsx`
- `tests/test_documentary_direction.py`

Artifacts: final MP4, immutable job inputs and scene receipts, score WAV/receipt,
`opening-direction.json`, captured source files, `credits.md`,
`final-verification.json`, `final-contact-sheet.jpg`, per-shot frames,
`implementation-file-manifest.json`, this report and `documentation-sync.json`.

## Remaining limitations

This is agent-authored MANUAL_UI direction executed by Studio. The engine does
not autonomously discover good stories, source footage, or judge viewer
interest. Its excerpt gate is schema/source/timing admission, not a replacement
for the existing canonical director preflight or full-pilot house-style gate.
The new Microsoft material is a captured, unapproved working source, not an
accepted claim injected into the old DOE chapter. Canonical 39-second allocations
and earlier claim IDs remain unchanged. Canonical promotion/export remains open.

The media library is still narrow: one archival plant photograph, a short
transmission clip and 480p facility footage. Some crops and explanatory footage
repeat. This has stronger factual and visual specificity than the rejected
vector edit, but no claim of parity with the reference channels is justified.
The original underscore is simple; music, delivery and long-form rhythm still
need creative listening assessment. New domain packs and commercial APIs remain
out of scope. No retention or channel-growth prediction is reported.

Next single task: `PHASE17_OPENING_CREATIVE_ACCEPTANCE_AND_REPAIR` — assess the
delivered opening as an opening, record owner feedback, and repair recurring
creative weaknesses as a whole before extending the sequence.

## DOCUMENTATION_IMPACT_MATRIX

| Document | Impact | Reason |
|---|---|---|
| CURRENT_STATE.md | Updated | Real opening job, scope, duration and current API port. |
| CHANGELOG.md | Updated | Media-backed working direction, original score, quote gate and repair package. |
| NEXT_ACTIONS.md | Updated | Exactly one opening creative acceptance/repair task. |
| KNOWN_LIMITATIONS.md | Updated | Unapproved new sources, limited media, manual direction, no audience evidence. |
| PHASE_ACCEPTANCE.md | Updated | Bounded technical result; Phase 17 remains OPEN. |
| QUALITY_BENCHMARKS.md | Updated | Actual shots, measured PCM/cues; no full-pilot benchmark claim. |
| ARCHITECTURE_DECISIONS.md | Updated | Separate working excerpt with exact parent ancestry; no canonical promotion. |
| MASTER_ROADMAP.md | Reviewed, unchanged | Core plus business-tech pack unchanged; no roadmap authorization. |
