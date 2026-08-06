# Phase 13 Preview Implementation Authorization

Decision: **AUTHORIZE one bounded implementation package.**

Authorized additions only:

- `RenderInputSnapshotV1`, render-job/event/delivery application models and
  ports; SQLite tables for immutable handoff metadata and ordered job events.
- A trusted REPLAY handoff adapter using existing Phase 3 loaders, Phase 4
  `RenderProps` and `run_headless_preview`; no renderer rewrite.
- Thin FastAPI/OpenAPI preview request, job/event, manifest/frame and typed
  Phase 14-unavailable read endpoints; generated TypeScript client and a React
  preview/job panel.
- Focused Studio, Phase 4 and Phase 12 regression tests.

Excluded: FULL render start, providers, browser automation, queue/retry,
source/asset transport, cache/GC, quota, lifecycle recovery and Phase 14 code.
