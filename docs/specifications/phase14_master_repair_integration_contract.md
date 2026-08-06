# Phase 14 Master Repair Integration Contract

Status: candidate; audit and implementation authorization are separate.

## 1. FULL artifact registry adapter

`register_full_render_artifacts` consumes only a successful or terminal
`FullRenderOutcome` and its existing verified `artifact_rows`. It receives a
trusted, complete `FullArtifactLifecyclePolicyV1` keyed by row `kind`; each
entry declares retention class, locked, pinned, approved, producer version and
terminal eligibility. Missing/unknown kind or a final row without `final`
retention fails before registry append. The adapter transforms rows without
paths/URIs into `ArtifactRegistryRecord` and idempotently persists the full
dependency-valid batch. It never changes `run_full_render`, output publishing,
renderer toolchain, route or receipt semantics.

## 2. Trusted storage pressure admission

`StoragePressurePolicyV1` contains `storage_scope_id`, hard byte limit and
minimum free bytes. `storage_pressure_admission(managed_root, policy,
estimated_bytes)` measures managed bytes and trusted local free bytes via
`shutil.disk_usage`. It returns `ADMITTED`, `BLOCKED_HARD_QUOTA` or
`BLOCKED_MIN_FREE_DISK`; invalid root/policy/measurement is fail-closed. A
cache miss or FULL render invokes it before attempt-directory/process creation.
An integrity-valid cache hit does not need a new render admission.

## 3. Explicit local quota manager

`StorageQuotaManagerV1` exposes only synchronous, caller-invoked methods:

```text
analyze(scope, policy, payloads, entries) -> usage + dedup + pressure
plan(scope, policy, payloads, entries, retained_ids) -> immutable dry-run
execute(scope, policy, plan, payloads, entries, timestamp) -> transaction
```

`execute` delegates solely to the accepted cache-plan executor after revalidating
the exact immutable plan. It neither discovers arbitrary files nor schedules,
retries, loops or automatically cleans any data. A quota/pressure result must
remain visible to the caller; there is no silent cleanup/default.

## 4. Required evidence

Tests must prove: full row policy mapping rejects missing/final drift; complete
FULL row batch reopens in registry; hard-quota/minimum-free admission fails
before producer invocation; cache hit bypasses only render admission; quota
facade dry-run has no mutation and execute/restore preserves receipt lineage.

## 5. Exclusions

Permanent deletion, background worker, provider, generic queue/retry, Studio
or FULL HTTP route, renderer rewrite and Phase 15 validation are excluded.
