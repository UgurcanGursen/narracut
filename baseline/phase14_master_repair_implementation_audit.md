# Phase 14 Master Repair Implementation Audit

Decision: FIX_REQUIRED; Phase 14 remains open.

## P14-MRI-IMP-001 — Pressure admission is a utility, not renderer admission

Severity: MAJOR. `storage_pressure_admission` is tested directly, but neither
the preview lifecycle adapter nor `run_full_render` invokes it. Hard/minimum
free pressure therefore cannot prove a render attempt is blocked before process
or attempt-directory creation.

Required repair: add a narrow, optional trusted pressure policy/root adapter at
both existing renderer admission seams. Missing policy for the new lifecycle
entry point must fail closed; legacy Phase 4 calls remain unchanged until they
explicitly opt into the Phase 14 adapter.

## P14-MRI-IMP-002 — FULL registry import is callable but not terminally bound

Severity: MAJOR. The journal bridge correctly validates a committed transaction,
but no terminal orchestration seam calls it. A FULL render can still finish
without a Phase 14 registry import.

Required repair: introduce one explicit `finalize_full_lifecycle` adapter that
requires a committed transaction ID, registry path and complete trusted policy;
tests must invoke it immediately after a real/replay terminal full transaction
and prove missing policy blocks final lifecycle completion.

No permanent deletion, worker, provider, queue, Studio/FULL route or Phase 15
implementation is authorized.
