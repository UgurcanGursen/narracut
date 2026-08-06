# Phase 13 Studio, Manual LLM and Review Contract

Status: accepted implementation scope; Phase 13 implementation authorized

## Objective and ownership

Phase 13 turns the accepted local `REPLAY`/`MANUAL_UI` contracts into a
human-operated Studio product boundary. It owns the API-mediated project,
manual-task, review and approval experience. The UI remains an HTTP client;
the FastAPI layer remains a thin orchestration adapter; the Python engine and
the canonical artifacts remain the only domain decision owners.

This contract closes Deferred Delivery Ledger row `DDL-06`: a user can work
with a task package, import a result, see validation, create a repair and make
an approval decision without managing repository paths, stable IDs or raw
JSON files. It does not close the final production-product gate.

## Existing baseline and required correction

The Phase 1 Studio shell has only three project read/create endpoints and an
`InMemoryProjectRepository`. Its declared `process_lifetime` persistence is
correct for that shell but cannot satisfy Phase 13's create-and-reopen
criterion. Phase 13 must replace that runtime choice through an application
port with a local SQLite-backed Studio state repository. It must not pretend
that the in-memory store can reopen a project after API restart.

The SQLite store is a local control-plane record, not the Phase 14 artifact
lifecycle or the Phase 17 crash-recovery proof. It persists only immutable
references, UI workflow state, validation summaries and approval lineage. It
does not own arbitrary media bytes, cache cleanup, renderer output ownership
or a distributed job queue.

## Frozen implementation boundary

The implementation package is limited to these four API/UI capabilities and
their OpenAPI-generated client contracts:

1. **Project dashboard and reopen.** Create/list/open a project through the
   public API; display the resolved domain-pack version and policy-snapshot
   identity. Unsupported domain/version/profile combinations remain explicit
   errors. Domain migration is not performed; an impact-preview record and an
   explicit user confirmation are prerequisites for any later migration.
2. **Manual LLM inbox.** List and inspect Phase 9/10 `REPLAY` or `MANUAL_UI`
   task packages, copy a prompt, download only an API-produced context package,
   paste or upload a result, receive canonical validation, and create a
   task-bound repair. Opening a web AI is an explicit user action using a
   documented external link; no browser automation, cookies, credentials or
   provider API is introduced.
3. **Read-only editorial review.** Present accepted source/claim, planner,
   approved asset/range/crop, template capability, optional visualization,
   audio-direction, executable-plan and Phase 3 video/audio EDL references
   for a sequence. The API returns safe typed view models, never a repository
   path, source URL credential, Python object or media file handle.
4. **Versioned review decisions.** A review action creates an immutable,
   hash-bound decision record. Asset/crop/template/emphasis/source-audio or
   replan requests create a replacement request for the owning contract; they
   do not mutate an approved Phase 8, 10, 11, 12 or Phase 3 artifact in place.
   An approved sequence records the reviewed executable-plan and EDL bundle
   hashes and becomes locked until an explicit replacement decision. The first
   UI version supports a bounded asset-change/replan path in one or two user
   actions; it does not rebuild EDLs, schedule frames/samples or bypass Phase
   12.

The expected implementation seams are additive application ports/services,
SQLite infrastructure adapters, FastAPI DTO/routes, generated OpenAPI and
TypeScript client, plus focused React screens and tests. Direct imports from
React into `engine/`, `domain-packs/`, project folders or SQLite are forbidden.
FastAPI route functions may map DTOs and invoke application services only;
policy resolution, task validation, EDL compilation and artifact validation
stay behind their existing canonical owners.

## Lifecycle and fail-closed rules

```text
task created -> pending -> waiting for user -> submitted
  -> valid -> approved
  -> repair_required -> replacement task -> submitted

review opened -> replacement requested | approved-and-locked
```

- Every task/result/repair and review/approval record carries project ID,
  active domain pack version, policy snapshot ID, stable ID, canonical content
  hash, producer/version and predecessor reference where applicable.
- Cross-project, cross-domain-policy, stale-version, forged-hash, missing
  prerequisite and already-locked mutation attempts fail with a typed API
  error. There is no silent default task mode, default domain, default asset,
  default crop, default template or implicit unlock.
- Task payloads and uploaded results are size- and schema-bounded before
  persistence. Validation errors are persisted as safe structured summaries;
  raw provider responses, local filesystem paths and secrets are not echoed to
  the UI.
- The UI can display `unavailable` status for a capability owned by a later
  phase. It must not show a fake preview, render progress, storage total or
  task success when no canonical backing artifact exists.

## Explicit non-goals and phase boundaries

- No paid LLM call, browser-driven web-UI automation, source/asset transport,
  queue/retry worker, live URL/media opening, or provider credential handling.
- No renderer invocation, preview rendering, FFmpeg work, EDL schedule rewrite
  or PCM/audio mix. Phase 12 and Phase 3 artifacts are presented, not edited.
- No Phase 14 artifact registry/cache/GC/recovery implementation and no Phase
  15 operational transport/limit/failure implementation. Their future views
  may be typed read-only unavailable states only.
- No authentication, multi-user collaboration, billing, Spring Boot or
  internet-facing deployment.

## Acceptance gates for the authorized implementation

1. A project created with `business-tech@0.1.0` survives an API restart and is
   reopened by its stable ID through the UI. The resolved pack/version and
   policy snapshot are visible; an unsupported domain is rejected rather than
   silently treated as business-tech.
2. A `MANUAL_UI` task completes package download/copy, result submit,
   validation, repair and approval using only the Studio API. A user is never
   required to edit repository JSON, stable IDs or paths.
3. A rejected/stale/cross-project/cross-policy/forged task or review reference
   cannot enter the approved state; all errors have deterministic API codes.
4. A review screen reads a Phase 12 two-sequence executable plan and its
   hash-bound Phase 3 video/audio EDL bundle. An approval locks the exact
   reviewed hashes; a requested change creates a replacement request and does
   not mutate the accepted artifact.
5. OpenAPI is regenerated from FastAPI and the committed TypeScript client is
   byte-current. HTTP-only boundary, backend route/service thinness, SQLite
   restart/reopen behavior and focused UI workflow tests pass.
6. Manual/replay fixtures prove the workflow without a provider API, browser
   automation, renderer bypass or direct filesystem access.

Phase 13 may be marked `MASTER_PHASE_CLOSED` only after these gates and every
Phase 13 Master Roadmap criterion with an available owner is demonstrated.
Phase 14/15-backed operational render, storage and transport views remain
explicitly unavailable until their owners provide canonical evidence.
