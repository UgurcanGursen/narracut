# Phase 17 resume audit — 2026-09-25

## Finding

The Studio services from 2026-09-07 were no longer listening. We started the
same local API on 8007 and UI on 5173; both returned HTTP 200, but the known
project `prj_f01b4d80f4744c619f9b9567f819ba2f` did not load. The project
list returned `items: []`, and the editorial-cycle request returned 404
`PROJECT_NOT_FOUND`. The runtime uses the OS temporary directory for its
SQLite files. The current temporary Studio database has zero project rows.
The exact reason earlier rows disappeared was not established. The resumed
servers were stopped after diagnosis.

A 2026-09-05 backup at
`output/phase17-chapter-revision-studio-20260905/before-studio.sqlite3`
contains the exact project ID, one project, 29 tasks, 20 responses and seven
source records. Its paired `before-phase10-planner.sqlite3` has 16 planner
records and older production metadata. A binary search of SQLite and WAL
files in `output/` found the exact project ID only in those two backup files.
The 2026-09-07 editorial task ZIP (26,971,059 bytes), latest section MP4
(13,928,179 bytes), AI result JSON files and cycle overview are still present.
The earlier 46.5-second opening video also remains in output.

These are recovery inputs, not a verified complete database backup. Do not
silently activate the older snapshot as if it includes 2026-09-07 edits.
No code or production records were changed in this audit.

## Next task and acceptance

`PHASE17_PROJECT_STATE_RECOVERY`: make immutable working copies of the current
and 2026-09-05 databases; move the active database location to durable local
storage; reconcile later task, result, direction and job artifacts with their
recorded IDs, hashes and lineage; show exactly what remains missing. Acceptance
requires the saved project and current editorial cycle to load through both API
and Studio, with no invented approvals. Then run the separate live UI task
(download, import, render, version-bound feedback), followed by owner review.
Phase 17 remains OPEN.

## Verification

Read the roadmap, current state, next actions, limitations and Phase 17
acceptance in required order. Inspected Git status and prior remote-closed
sync. Checked local ports and files. Started API and UI with the repository
Python/Vite; checked health, project list and project endpoint. Queried SQLite
in read-only mode and searched output SQLite/WAL files for the project ID.
Stopped the services started for this audit. All observations above are direct;
recovery and creative acceptance were not tested.

## DOCUMENTATION_IMPACT_MATRIX

| File | Impact |
| --- | --- |
| docs/CURRENT_STATE.md | Records the current missing-project blocker |
| docs/CHANGELOG.md | Records the bounded resume audit |
| docs/NEXT_ACTIONS.md | Sets exactly one recovery task before live acceptance |
| docs/KNOWN_LIMITATIONS.md | Marks project state and durable storage unresolved |
| docs/PHASE_ACCEPTANCE.md | Keeps Phase 17 and live UI acceptance open |
| docs/baseline/phase17_resume_audit_20260925.md | Evidence and recovery scope |
| docs/QUALITY_BENCHMARKS.md | Reviewed, unchanged; no new quality result |
| docs/ARCHITECTURE_DECISIONS.md | Reviewed, unchanged; durable location is not yet selected |
| docs/MASTER_ROADMAP.md | Reviewed, unchanged; no roadmap change |
