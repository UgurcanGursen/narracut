# Phase 13 Renderer Control-Plane Integration Contract

Status: candidate specification; read-only design only, no implementation authorization

## 1. Objective

This contract closes the interface gap identified by
`baseline/phase13_master_criterion_integration_decision_report.md`: the
accepted Phase 4 REPLAY renderer has terminal preview/FULL evidence, while the
HTTP-only Studio cannot safely request a project-bound sequence preview, learn
its state, reconnect to progress, or retrieve verified preview evidence.

The first integration is deliberately **PREVIEW-only and REPLAY-only**. It
turns accepted Phase 12/Phase 3 render inputs into a controlled Phase 4A
preview invocation through an application port. It neither changes renderer
semantics nor makes the Studio an artifact, media or filesystem owner.

## 2. Ownership and non-goals

| Concern | Owner | This contract permits |
|---|---|---|
| Phase 3 schedule, sample timing and EDL bytes | Phase 3 | Read-only identity verification only |
| Phase 12 executable-plan and review lock | Phase 12 / Phase 13 review | Read-only prerequisite verification only |
| RenderProps and REPLAY preview execution | Phase 4 | Invocation through a narrow trusted port |
| Job state, ordered safe events and Studio DTOs | Phase 13 | Local control-plane persistence and read models |
| Cache, retention, quota, registry, cleanup and GC | Phase 14 | Explicit unavailable state only |
| Transport, rate limits, retry and provider/media acquisition | Phase 15 | Nothing |

This contract does not authorize a renderer rewrite, EDL compilation or
mutation, FFmpeg work, FULL render start endpoint, source/asset opening,
provider call, browser automation, generic queue/retry worker, direct UI
filesystem access, artifact registry, storage accounting, TTL policy or GC.

## 3. Trusted prerequisites and fail-closed admission

`POST /api/v1/projects/{project_id}/sequences/{sequence_id}/preview-renders`
has no caller-supplied path, source URL, props, EDL bytes, hash or render mode.
The application service resolves all of the following through trusted ports:

1. the opened Studio project and its exact domain-pack/policy snapshot;
2. the current immutable review snapshot for that project;
3. an executable sequence belonging to that snapshot and its exact Phase 12
   executable-plan hash and Phase 3 video/audio EDL bundle hashes;
4. a trusted, REPLAY-only `RenderInputSnapshotV1`, including canonical EDL
   bytes, `RenderProps`, fixture root and the Phase 4 preview composition;
5. a review decision that is not superseded and whose sequence has not been
   changed after the bound plan/bundle hashes were reviewed.

The Studio SQLite repository is not a substitute for item 4. It may persist
the resulting identity, job and safe receipt view, but it cannot manufacture
EDL bytes, fixture bindings, a project root or an asset path. Missing or
forged prerequisites fail before job admission with one deterministic public
code: `RENDER_INPUT_UNAVAILABLE`, `REVIEW_BINDING_INVALID`,
`SEQUENCE_NOT_REVIEWABLE`, `PREVIEW_MODE_UNAVAILABLE` or
`RENDER_REQUEST_CONFLICT`.

The application derives `preview_request_id` and `preview_request_hash` from
the project, sequence, domain-policy snapshot, executable-plan hash, EDL-bundle
hash, RenderProps hash and `PREVIEW_REPLAY_V1` mode. A duplicate active request
returns its existing job view; it never starts a second process. A user may
explicitly request a new attempt only after a terminal result. There is no
automatic retry, fallback mode or silent conversion to FULL.

`preview_request_id` identifies immutable requested inputs; it is not a job
identity. Each admitted or pre-admission-rejected attempt receives a new opaque
`preview_job_id` and an atomically allocated positive `attempt_ordinal` within
that request. The job stores the exact parent request ID/hash and ordinal.
There may be at most one non-terminal job for a request hash. A terminal job
never accepts a new event, receipt or delivery descriptor, and a new attempt
cannot reuse its job ID, ordinal, receipt hash or delivery ID. This preserves
the lineage of two explicit attempts with identical render inputs.

## 4. Control-plane state and event log

The Phase 13 repository stores a local, append-only control-plane event log.
It is not the Phase 14 artifact registry. A job contains its `preview_job_id`,
parent request ID/hash, attempt ordinal, stable IDs, canonical hashes, mode,
timestamps, terminal public code and opaque delivery references; it never stores
a local path, raw stderr, provider secret or media bytes.

```text
REQUESTED -> ADMITTED -> RUNNING -> SUCCEEDED
                         |          |
                         +--------> FAILED
                         +--------> CANCELLED

REQUESTED -> REJECTED_PRE_ADMISSION
```

- Events have a per-job monotonically increasing integer `ordinal`, immutable
  `event_id`, UTC timestamp, state and closed safe payload. Duplicate or
  out-of-order ordinals are repository corruption, not a client recovery path.
- `REJECTED_PRE_ADMISSION` creates no Phase 4 process or preview evidence.
- `FAILED` and `CANCELLED` carry a closed public failure code and never expose
  subprocess output, signal, exception text or a host path.
- `SUCCEEDED` binds the exact Phase 4 receipt hash, preview-manifest hash and
  delivery descriptor. A result without all three is not successful.
- `GET /preview-renders/{job_id}` returns the latest safe view. `GET
  /preview-renders/{job_id}/events?after=<ordinal>` returns a finite ordered
  replay. `GET /preview-renders/{job_id}/events/stream?after=<ordinal>` is an
  SSE projection of the same persisted event sequence; reconnection cannot
  invent progress or skip a persisted event.

Progress is stage/state based in the first integration. The UI must not infer
an invented percentage from elapsed time. `ADMITTED`, `RUNNING` and terminal
states are the only supported progress claims until a later owner provides
canonical numeric progress.

## 5. Safe preview delivery

On success, the execution adapter validates Phase 4's canonical preview
manifest and creates a `PreviewDeliveryDescriptorV1` containing only
`delivery_id`, job/request IDs, attempt ordinal, project/sequence IDs, manifest
ID/hash, selected-frame identity list and an opaque delivery expiry. The
descriptor has no filesystem path, URL supplied by a renderer, artifact-store
key or media byte payload.

The only delivery endpoints are:

```text
GET /api/v1/projects/{project_id}/preview-renders/{job_id}/manifest
GET /api/v1/projects/{project_id}/preview-renders/{job_id}/frames/{frame_index}
```

They validate project/job/descriptor/manifest/frame binding before reading a
trusted adapter-owned preview delivery location. A request for an unlisted
frame, expired descriptor, wrong project, forged job ID or unavailable backing
evidence returns a typed error; it does not scan directories, guess filenames
or fall back to another preview. The browser may receive only the verified
manifest JSON and declared PNG frame bytes with fixed media types.

This is a short-lived attempt delivery seam, not durable artifact retention.
The trusted execution adapter alone owns its single-use output root and may
withdraw the delivery capability only after terminal delivery handling; that
attempt-local cleanup may not scan, classify, retain, pin or reclaim any other
artifact. It reports `PREVIEW_DELIVERY_UNAVAILABLE` after withdrawal or a
restart with no verified backing evidence. This is not a Phase 14 retention,
quota or GC policy. Phase 14 alone can later replace it with durable
artifact/media ownership, retention and restoration semantics.

## 6. Storage and FULL-render read states

Every Phase 13 response that would otherwise imply storage, quota, GC,
reclaimable bytes, cache hit or durable artifact restoration returns the typed
state `UNAVAILABLE_OWNER_PHASE14`. It must not return zero, an empty list or a
SQLite database size as a storage/GC value.

Phase 4B FULL render receipts may be exposed in a future read-only contract,
but this contract exposes no FULL-render start, cancel, replacement or media
endpoint. It also does not equate a terminal Phase 4 receipt with durable
cross-run storage evidence.

## 7. API and UI boundary

FastAPI route functions map DTOs to the application service only. The service
uses `StudioRenderInputResolverPort`, `PreviewExecutionPort`,
`RenderJobRepositoryPort` and `PreviewDeliveryPort`; React knows only the
generated OpenAPI client. Neither FastAPI nor React imports `engine.rendering`
directly, reads a project directory, stores media blobs, invokes a subprocess
or accepts a renderer path from a request. Direct UI filesystem access is
forbidden.

The UI permits one explicit action, **Render preview**, from an eligible
sequence review. It polls or subscribes to the job state, displays only the
safe event/failure vocabulary, and renders only server-declared frames. It
shows the Phase 14 storage/GC state as unavailable rather than displaying a
fake total.

## 8. Future implementation acceptance gates

Implementation may be authorized only after independent specification
acceptance. Its focused evidence must prove all of the following:

1. A canonical two-sequence Phase 12/Phase 3 REPLAY fixture starts a preview
   through the Studio API and binds the terminal receipt/manifest to the exact
   requested sequence and policy snapshot.
2. Forged, stale, cross-project, changed-review, unavailable-input and
   duplicate-active requests fail closed before the renderer process starts.
   Two explicit terminal attempts for identical inputs receive distinct job IDs
   and ordinals and cannot read or append one another's events or deliveries.
3. Persisted event ordinals replay identically after a fresh FastAPI app;
   SSE reconnection resumes after an explicit ordinal without duplicate state.
4. Success provides only manifest-declared frame bytes; path traversal, guessed
   frame names, cross-project access and expired delivery are rejected.
5. Failure/cancellation exposes deterministic safe codes and no raw stderr,
   absolute path, secret, media source or false progress percentage.
6. Storage/GC remains `UNAVAILABLE_OWNER_PHASE14`; no cache, cleanup or quota
   behavior is claimed.
7. OpenAPI is regenerated, generated TypeScript is byte-current, React stays
   HTTP-only, and Phase 4/12 regression evidence remains green.

## 9. Closure effect

This candidate authorizes no code. Even after a later accepted implementation,
Phase 13 cannot claim `MASTER_PHASE_CLOSED` until the Phase 14-owned durable
storage/GC read model is handed off and demonstrated. `PRODUCT_GATE_CLOSED`
remains a Phase 17 decision.
