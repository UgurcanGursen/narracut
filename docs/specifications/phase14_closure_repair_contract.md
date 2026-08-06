# Phase 14 Closure Repair Contract

Status: candidate; audit and implementation authorization are separate.

## Incremental sequence contract

`SequenceDependencySnapshotV1` is canonical JSON containing project ID and an
ordered map of sequence ID to verified input hash. IDs are unique and stable;
hashes are SHA-256. `plan_incremental_sequences(previous, current)` rejects
project drift/invalid input and emits every current sequence in stable order:
`REUSE` only if its exact prior hash matches, otherwise `REBUILD`. Removed
sequences are explicit `ORPHANED` decisions, never reused. No EDL scheduler or
renderer mutation is allowed.

## Soft quota admission contract

`StorageQuotaManager.assess_render_admission` first calls trusted pressure
admission. Hard/min-free failure returns its fail-closed status. If pressure
admits but logical/physical storage exceeds the policy soft limit, it returns
`SOFT_QUOTA_PLAN_REQUIRED` plus only an immutable `CACHE-SOFT-QUOTA-PLAN-V1`.
It never executes the plan. `INSUFFICIENT_ELIGIBLE_RECLAIM` remains visible.
Otherwise it returns `ADMITTED`. The caller owns displaying or explicitly
executing the plan.

## FULL A/V replay performance contract

`benchmark_full_av_hash_preserving` receives two local REPLAY producers. Each
returns canonical `FullAvEvidenceV1` with final output bytes/hash and immutable
audio-plan, filter-script and PCM-manifest hashes. The benchmark measures both
wall durations and rejects any hash/evidence difference before reporting an
improvement. It makes no codec/hardware/SLO claim.

## Required verification

Multi-sequence fixture proves one changed sequence gets exactly one rebuild;
soft quota emits dry-run/no mutation; hard/min-free preempts soft quota; FULL
A/V benchmark accepts exact evidence and rejects video/audio drift.

Permanent deletion, worker, provider/queue, Studio/FULL route and Phase 15 are
excluded.
