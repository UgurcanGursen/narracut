# Phase 13 Master-Criterion Integration Decision

Date: 2026-08-06

## Scope

This is a read-only reconciliation of the accepted Phase 13 Studio foundation
against the remaining Master Roadmap criteria. It does not authorize renderer,
cache/GC, transport, provider, queue/retry or UI implementation work.

## Evidence

| Concern | Existing canonical evidence | Decision |
|---|---|---|
| Project reopen and Manual LLM workflow | Phase 13 foundation at `cc32a61` | SATISFIED at the local Studio boundary |
| Hash-bound review and immutable approval | Phase 13 foundation at `cc32a61` | SATISFIED at the read-only review boundary |
| Deterministic sequence preview engine | Phase 4A `run_headless_preview` and Phase 4 final acceptance | Engine evidence exists, but no Studio handoff |
| Full-render terminal receipt/lifecycle | Phase 4B `run_full_render` and `8bac18b` evidence | Terminal engine evidence exists, but no Studio job/read model |
| Live job progress/failure view | No durable render-job event or Studio endpoint | NOT SATISFIED |
| Storage, quota and GC view | Deferred Delivery Ledger `DDL-08`, owned by Phase 14 | UNAVAILABLE; not a Phase 13 implementation responsibility |

## Findings

1. Phase 4 is not missing. It has a bounded REPLAY preview path and a
   deterministic FULL-render terminal path. The prior Phase 13 wording was
   imprecise: the missing item is a **project-bound, API-safe Studio handoff**,
   not the renderer itself.
2. `run_headless_preview` requires caller-owned temporary/output paths and
   returns one terminal `PreviewRun`; its artifact batch is in-memory. It is
   not safe for React to invoke or to expose as arbitrary filesystem output.
3. `run_full_render` returns a terminal `FullRenderOutcome`. Its internal
   attempt journal and terminal receipt do not provide an API-level job state,
   ordered event stream or reconnectable progress read model.
4. Phase 14 remains the sole owner of durable cross-run cache, dependency-aware
   cleanup, quota, storage accounting and GC. A Phase 13 SQLite control-plane
   record must not impersonate that lifecycle registry.

## Decision

`PHASE13_MASTER_PHASE_CLOSED=NO`.

The next bounded task is to write and independently accept a **Phase 13
Renderer Control-Plane Integration Contract**. That contract may authorize a
thin FastAPI/application-port adapter only after acceptance. It must define:

- a hash-bound, project/sequence-scoped preview request and terminal receipt
  view over existing Phase 4 capabilities;
- a safe preview-manifest/media delivery contract with no filesystem path or
  arbitrary artifact lookup exposed to React;
- durable, ordered render-job state/events suitable for polling and SSE
  reconnection, including explicit failure and cancellation states;
- exact ownership: Phase 13 consumes those read models; it does not rewrite
  EDLs, schedule media, implement a renderer, or own Phase 14 storage/GC;
- explicit `UNAVAILABLE_OWNER_PHASE14` states for storage/GC until Phase 14
  provides canonical evidence.

The contract must not introduce provider calls, browser automation, a general
queue/retry worker, cache/GC, direct UI filesystem access, or a fake preview,
progress percentage or storage total. After its implementation is accepted,
Phase 13 still requires a Phase 14 handoff before a Master closure claim can
be made.

## Documentation impact matrix

| Document | Impact |
|---|---|
| `docs/MASTER_ROADMAP.md` | None; scope and phase ownership are unchanged |
| `docs/CURRENT_STATE.md` | Records the precise Phase 4 handoff gap |
| `docs/NEXT_ACTIONS.md` | Advances the sole task to the read-only contract specification |
| `docs/KNOWN_LIMITATIONS.md` | Corrects stale Phase 4B history and retains Phase 13/14 limits |
| `docs/PHASE_ACCEPTANCE.md` | Records the integration decision and open closure condition |
| `docs/CHANGELOG.md` | Records the reconciliation outcome |
| `docs/ARCHITECTURE_DECISIONS.md` | None; no architectural decision changed |
| `docs/QUALITY_BENCHMARKS.md` | None; no benchmark claim is made |
