# Phase 14 Master Repair Scope Reconciliation

Decision: candidate integration contract required before implementation.

## FULL artifact registry bridge

`run_full_render` already emits verified terminal artifact rows. A Phase 14
adapter may convert only these rows into registry records after the full render
transaction succeeds. It must require a resolved lifecycle policy mapping for
every `kind`; no hidden `temporary`/`review` default is allowed. The mapping
supplies retention class, lock/pin/approval state and producer version. Final
output mapping must be `final` and protected. Failed/cancelled terminal rows
remain registered with their explicit policy mapping; no cache reuse is added.

## Disk pressure guard

A trusted local `StoragePressurePolicyV1` supplies storage scope, hard byte
limit and minimum free bytes. Admission calculates managed usage and
`shutil.disk_usage(managed_root).free`; a cache miss/FULL render is rejected
before attempt creation if either projected hard usage or minimum-free boundary
would be violated. Existing cache hits remain integrity-only reuse. Missing or
invalid trusted root/policy is fail-closed.

## Explicit local quota facade

`StorageQuotaManagerV1` is an explicit synchronous local facade with
`analyze`, `plan` and `execute` operations. It consumes the accepted cache
planner/executor only when the caller supplies the trusted scope/policy and a
previously visible immutable plan. It returns typed dry-run/receipt state. It
does not scan arbitrary paths, schedule work, auto-run cleanup, expose HTTP or
perform permanent deletion.

## Exclusions

No renderer rewrite, output route, provider/queue, background worker, generic
retry, permanent deletion or Phase 15 behavior is authorized.
