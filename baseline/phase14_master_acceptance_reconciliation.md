# Phase 14 Master Acceptance Reconciliation

Decision: FIX_REQUIRED; Phase 14 is not closed.

| Master criterion | Evidence | Result |
|---|---|---|
| Changed cache key does not reuse stale output; preview/production separated | `engine/cache.py`, preview adapter tests | PASS (bounded cache path) |
| Phase 4 preview output is registered and cache/provenance bound | lifecycle adapter + actual REPLAY tests | PASS (preview) |
| Artifact producer leaves no unregistered files | `full_orchestrator.py` emits local artifact rows but has no Phase 14 registry import | OPEN / MAJOR |
| Protected/reference-aware dry-run, trash, restore and soft quota | lifecycle/cache execution tests | PASS (bounded local plan path) |
| Hard quota and minimum-free-disk prevent render start | hard-byte quota preview adapter exists; no trusted free-disk guard | OPEN / MAJOR |
| Safe soft-quota operational management | explicit transaction executor exists; no trusted quota manager admission/analyze loop | OPEN / MAJOR |
| Dedup savings | deterministic logical/physical arithmetic | PASS (fixture accounting) |
| Performance preserves output | actual fixed REPLAY manifest-hash cache benchmark | PASS (bounded preview) |

Required bounded repair scope:

1. bridge existing Phase 4 FULL artifact rows into the durable registry without
   changing renderer semantics or exposing a new route;
2. add trusted storage-pressure measurement (hard quota plus minimum free
   bytes) and fail-closed renderer admission for preview/FULL adapters; and
3. add an explicit local quota-manager analyze/plan/execute facade that invokes
   only accepted plans, never a worker or automatic background loop.

Permanent deletion, provider/queue, Studio/FULL API route and Phase 15 remain
out of scope. Reconcile these three repair items before implementation
authorization.
