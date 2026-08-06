# Phase 14 Master Repair Integration Contract Audit

Decision: FIX_REQUIRED; implementation is not authorized.

## P14-MRI-001 — FULL adapter has no valid artifact-row ingress

Severity: MAJOR. `FullRenderOutcome` contains terminal receipt/output path but
not the full verified `artifact_rows`. The candidate cannot safely consume rows
from outcome memory, nor recompute them from paths. Existing Phase 4B
`lifecycle_registry` transaction journal is the authoritative committed source.

Required repair: define a trusted transaction-journal loader that locates an
exact committed transaction/receipt, validates its canonical identity and
terminal relation, and yields only its embedded verified artifact rows to the
Phase 14 adapter. Unknown/multiple/incomplete transaction must fail closed.

The pressure and quota-facade boundaries are sound. No implementation
authorization is granted until this ingress repair is independently re-audited.
