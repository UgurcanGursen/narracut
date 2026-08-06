# Phase 17 Local/Beta Scope Reconciliation

Date: 2026-08-06

## Existing evidence inventory

| Roadmap area | Existing boundary | Missing product-gate capability |
|---|---|---|
| Local persistence | `SQLiteProjectRepository` persists project, task, review and preview-job metadata with WAL | workspace revisions, artifact files, crash-reopen verification and backup/restore |
| UI/API workflow | React Studio, FastAPI routes, review flow and preview-event endpoint exist | full-stage status, final render/export controls and recovery UX |
| Render jobs | persisted preview-job state and a REPLAY executor exist | durable worker queue, retry policy, restart resumption and final-render work |
| Source/assets/timing | Phase 6/8 are REPLAY/manual packages; Phase 2 trusted successful publisher is REPLAY only | selected real local source/asset transport and non-REPLAY trusted timing producer |
| Lifecycle | Phase 14 has registry/cache plan/restore primitives | project archive/restore tied to workspace revisions |
| Operations | FastAPI health/toolchain tests exist | local launcher or Compose, structured logs, backup policy and health package |

## Authorized implementation order

1. **P17-A Workspace and recovery.** Add a local workspace revision store and
   durable job journal. It must have atomic active-revision publication,
   restart recovery and a visible terminal failure state. No provider execution.
2. **P17-B Local import and export.** Add user-selected local source/asset
   import with hashes, provenance/license fields and export of source/license,
   SRT/VTT, metadata and archive manifests. No access-control bypass or remote
   acquisition.
3. **P17-C Worker lifecycle.** Add bounded local retry/resume around supported
   jobs, stage events and structured logs; preserve `REPLAY` and `MANUAL_UI`
   cost-free modes.
4. **P17-D Local package.** Add health checks, a repeatable launcher and backup/
   restore tests. Docker Compose is optional only if it materially improves the
   local single-user package.
5. **P17-E Product-gate evidence.** Select lawful sources, a trusted non-REPLAY
   timing path and three benchmark references, then execute two real 10–15
   minute business-tech projects. This needs concrete source/provider choices
   and cannot be fabricated from fixtures.

## Decisions

- Continue with FastAPI for the local/beta package. The repository has no
  measured multi-user, billing, SSO, multi-tenant or distributed-worker signal
  that would justify Spring Boot.
- Commercial LLM API, provider credentials, automated browser use and paid
  source acquisition remain disabled. `MANUAL_UI` and `REPLAY` remain supported.
- The first implementation slice is P17-A only. It must not silently convert
  existing SQLite metadata or existing artifact/cache directories.

## Product-gate status

The Phase 17 product gate is **OPEN**. This plan authorizes only P17-A design
and implementation preparation; it does not claim production readiness.
