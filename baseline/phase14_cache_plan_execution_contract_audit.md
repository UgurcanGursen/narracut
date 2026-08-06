# Phase 14 Cache Plan Execution Contract Audit

Decision: FIX_REQUIRED; implementation is not authorized.

## P14-CPE-001 — Receipt and per-event append are not an atomic state unit

Severity: MAJOR.

The candidate requires one receipt followed by ordered retirement events, yet
an I/O failure after a receipt or part of its events is durable leaves an
append-only ledger with an ambiguous partial effective state. Filesystem
rollback cannot remove already fsync'd lines without violating the same
append-only rule.

Required repair: define one canonical, fsync'd batch transaction record that
contains the receipt projection and every transition. The effective-state
reader admits a transaction only when its one record is complete and
hash-valid. Any staging/temporary publication must be invisible to readers.
Restore needs the same one-record transition batch. The receipt ID/hash must
be derivable from that batch so no cross-file atomicity is assumed.

Other candidate boundaries (preflight, root/content validation, reference-first
rows, rollback of moved bytes and permanent-delete exclusion) are sound. The
sole next task is this contract repair and targeted re-audit.
