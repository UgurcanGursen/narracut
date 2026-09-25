# Phase 17 — verified project state recovery, 2026-09-25

## Outcome and acceptance

The existing project `prj_f01b4d80f4744c619f9b9567f819ba2f` opens again in Studio
at http://127.0.0.1:5173/#studio-video. Its final working video and pending AI
package are available. The active API8007 now uses `.studio-data/studio.sqlite3`
and `.studio-data/phase10-planner.sqlite3` in this repository. A real API process
restart reopens the same project and `READY_FOR_WORKING_RENDER` cycle, stale false.
Recovery acceptance passes. Phase 17 and the separate full live UI cycle remain open.

## Recovery evidence

The preserved September 5 SQLite snapshots were copied using SQLite backup into
new staging databases. The existing chapter proposal/activation was replayed with
its recorded timestamps and reviewer metadata, then compared to the entire saved
activation receipt and chapter overview. This is restoration of a recorded action,
not a new approval. No original database was overwritten or deleted.

Hash-verified exports restore 2 treatments, 7 direction plans, 14 successful
working-edit jobs, 5 AI tasks, 3 AI results and 1 feedback record. Portable task
presentation fields are removed only if the original task hash is reproduced.
Treatment and plan hashes, job input snapshots, result/job hashes, video bytes,
individual scene bytes and feedback version bindings all validate. The current
cycle overview equals `final-cycle-overview.json` from September 7 exactly.

Current job: `ejob_d8afc9ddd8a14f75a0411786c5bb0964`, a 28.433333-second later
section with 2 scenes and 7 shots. The prior 46.5-second opening is retained.
Current video SHA-256:
`95870581cfaa795012b5324a47b945403d7f943b4df7f827761578dacc18c1f8`.

The successful activation is `attempt-3`; earlier staging attempts are retained.
The first stopped on a receipt-check mismatch: the original job receipt hashes
the result overview including `stale=false`, which the recovery verifier now
checks exactly. The second verified the records but Windows refused activation
while a SQLite handle was open. Explicit connection closing resolved this.
Neither failed attempt activated or replaced the production directory.

## Changes and compatibility

- `studio-api/src/kurgu_studio_api/infrastructure/storage.py`: durable default,
  absolute environment override and explicit populated-legacy guard.
- `studio-api/src/kurgu_studio_api/infrastructure/runtime.py`: shared resolver;
  explicit `database_path` remains supported.
- `studio-api/src/kurgu_studio_api/phase17_final_av_render_worker.py`: same location;
  explicit `--database` remains supported. Source/narration workers already use runtime.
- `scripts/start_local_studio.ps1`: repository Python default, storage preflight,
  matching UI proxy target and visible database path in command output.
- `scripts/recover_phase17_editorial_state.py`: bounded offline recovery,
  source preservation, hash checks, overwrite refusal and staged activation.
- `studio-api/tests/test_durable_storage_recovery.py`: persistence across temporary
  directory changes, legacy protection, path checks and tamper/overwrite rejection.
- `.gitignore`: excludes local `.studio-data` databases.
- `docs/STUDIO_DEVAM_REHBERI.md`: exact UI steps and a manual AI handoff message.

Implementation is in the existing local workspace. Its unrelated dirty files
were preserved; this documentation commit does not claim to publish all of that
workspace's implementation history.

## Verification and artifacts

Command: `.venv-studio/Scripts/python.exe -m pytest
studio-api/tests/test_durable_storage_recovery.py
studio-api/tests/test_editorial_cycle_api.py
studio-api/tests/test_editorial_production_api.py -q` with isolated test storage.
Result: **11 passed**. PowerShell launcher parsing and scoped `git diff --check`
pass. No new renderer/UI implementation was added, so no new video render or UI
build was required for this storage recovery.

Real HTTP health, project, editorial cycle, asset catalog and video/ZIP delivery
pass. Catalog reports nine exact media. Downloaded video bytes match the recorded
hash and `ffmpeg -v error -i <delivered-video> -f null -` decodes video and audio
without error. Downloaded ZIP contains 25 CRC-valid entries and the original task
identity. Actual browser project selection, production dossier, ZIP download
event and scene selection pass. Muted full playback reaches 28.454333 seconds
(container duration), ended true, no media error. Unmuted playback paused almost
immediately in this in-app browser; audible playback was not verified. The final
player is reset to the complete section at time zero, unmuted, and left open.

Artifacts under `output/phase17-project-state-recovery-20260925/`:
`attempt-3/originals/`, `attempt-3/recovery-report.json`, `verified-snapshot/`,
`verification.json`, `implementation-file-manifest.json`, `http-delivered-video.mp4`,
`http-delivered-task.zip`, API/UI logs and `documentation-sync.json`.

## Limits and single next task

The treatment ancestor
`sha256:3f5dbd8b9bada5bdfa3ebeca546a6971650215d00cc5cd6b3d1442c706f0a2ca`
is referenced by restored history but was not available in the exported records.
Unexported later historical/canonical records are not claimed recovered. The
known current working state is verified, not a complete September 7 database.
The initial reason the old temporary files became absent is undetermined.

Next: `PHASE17_MANUAL_EDITORIAL_LIVE_UI_ACCEPTANCE`. The owner uses the existing
ZIP with their subscribed AI UI, brings back its JSON, then completes Studio
import/render/version-bound feedback and audible/creative review. The task is a
repair review of the current later section. No full-film or autonomous-editor
quality claim is made. No paid API or automated third-party chat was used.

## DOCUMENTATION_IMPACT_MATRIX

| Document | Impact |
| --- | --- |
| CURRENT_STATE.md | Active durable state and restored workflow |
| CHANGELOG.md | Recovery milestone |
| NEXT_ACTIONS.md | Exactly one next task: live manual editorial cycle acceptance |
| KNOWN_LIMITATIONS.md | Missing history and audible/full-cycle limits |
| PHASE_ACCEPTANCE.md | Recovery acceptance passes; Phase 17 remains open |
| ARCHITECTURE_DECISIONS.md | Durable default, explicit override and legacy guard |
| QUALITY_BENCHMARKS.md | Reviewed, unchanged; no new creative benchmark |
| MASTER_ROADMAP.md | Reviewed, unchanged |
| STUDIO_DEVAM_REHBERI.md | User steps and manual AI prompt |
| baseline/phase17_project_state_recovery_20260925.md | This report |
