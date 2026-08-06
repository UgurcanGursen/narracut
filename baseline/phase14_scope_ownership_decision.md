# Phase 14 Scope and Ownership Decision

Date: 2026-08-06
Decision: **AUTHORIZE bounded specification work only**

## Objective

Start Phase 14 by making durable artifact ownership explicit without treating
the Phase 4 in-memory graph or its narrow full-render journal as a production
artifact lifecycle service.

## Repository evidence

- `engine/rendering/artifact_hook.py` validates an in-memory Phase 4 artifact
  graph but persists no registry.
- `engine/rendering/lifecycle_registry.py` is an intentionally narrow,
  full-render transaction journal and explicitly defers recovery/GC.
- `engine/contracts/artifacts.py` already supplies typed lineage and protected
  retention invariants, but no persistent registry, mark/sweep plan, trash or
  quota implementation exists.
- Phase 13 preview delivery is attempt-local and correctly becomes unavailable
  after restart; it must not be relabelled as storage.

## Selected first bounded package

**Durable Artifact Registry and Non-destructive Lifecycle Planning Contract**

The specification must define immutable registry/manifests, canonical
dependency roots, retention-policy resolution, atomic promotion boundaries and
an immutable dry-run deletion plan. It must require a distinct later approval
before any mutation-capable trash/restore/GC implementation.

## Explicit exclusions

- No file deletion, trash move, restore, GC execution or quota enforcement.
- No cache population/eviction, content-addressable store, hardlink/reflink or
  incremental renderer cache.
- No FULL-render endpoint, provider transport, generic queue/retry worker or
  browser automation.
- No mutation of accepted Phase 3/4 contracts or existing artifact history.

## Acceptance requirements for the later specification

1. Registry never accepts an absolute path, URI, provider secret or caller
   supplied ownership claim.
2. Every registry row is content-hash, producer, project/sequence/job and
   dependency bound; protected retention classes cannot become candidates.
3. The dry-run plan is immutable, hash-identified, dependency-aware and names
   a recovery/trash destination without mutating it.
4. Existing Phase 4 receipt/journal evidence remains importable only through a
   verified adapter; it is never silently upgraded.
5. Phase 13 can read truthful unavailable/storage state only after a later
   implementation provides a safe read model.

## Next decision

Draft and independently accept
`docs/specifications/phase14_durable_artifact_registry_lifecycle_planning_contract.md`.
No Phase 14 implementation is authorized by this scope decision.

## Documentation impact matrix

| Document | Impact |
|---|---|
| `docs/MASTER_ROADMAP.md` | None; scope follows existing Phase 14 ownership. |
| `docs/CURRENT_STATE.md` | Records Phase 14 planning start. |
| `docs/NEXT_ACTIONS.md` | Sets the sole specification task. |
| `docs/KNOWN_LIMITATIONS.md` | Records that no cleanup/cache implementation exists. |
| `docs/PHASE_ACCEPTANCE.md` | No change; no acceptance gate passed. |
| `docs/CHANGELOG.md` | Records the scope decision. |
| `docs/QUALITY_BENCHMARKS.md` | None; no performance result. |
| `docs/ARCHITECTURE_DECISIONS.md` | None; no ADR change. |
