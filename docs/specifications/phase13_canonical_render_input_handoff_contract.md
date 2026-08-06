# Phase 13 Canonical Render-Input Handoff Contract

Status: accepted specification; implementation authorization remains separate

## Objective

This contract supplies the missing trusted `RenderInputSnapshotV1` prerequisite
for the accepted Phase 13 renderer control-plane contract. It carries one
accepted Phase 12 executable sequence and its Phase 3 video/audio EDL material
into a server-validated, REPLAY-only Studio resolver. It is a handoff record,
not a renderer, artifact registry, media store or Phase 14 lifecycle service.

## Ownership and input source

Only a trusted Phase 12/Phase 3 handoff adapter may construct a package. React
never uploads EDL bytes, RenderProps, fixture paths or a package body. The
Studio preview endpoint receives only project and executable-sequence identity,
then resolves an already accepted package through an application port.

The adapter must load canonical Phase 3 bytes with their existing loaders,
verify exact EDL ID/hash pairs against the Phase 12 `FinalEdlBundleV1`, build
Phase 4 `RenderProps` with the checked-in trusted REPLAY fixture resolver, and
verify project, sequence, domain-pack version and policy-snapshot identity.
Any missing/mismatched/corrupt input rejects the handoff with a deterministic
safe code before persistence; it may not guess a fixture, path, asset or mode.

## Immutable package

`RenderInputSnapshotV1` contains exactly these identity-bearing groups:

```text
snapshot_id/hash, project_id, executable_sequence_id/hash,
domain_pack_version, policy_snapshot_id/hash,
executable_plan_id/hash, final_edl_bundle_id/hash,
video_edl_id/hash/canonical_bytes, audio_edl_id/hash/canonical_bytes,
render_props_id/hash/canonical_bytes,
fixture_manifest_id/hash, mode=PREVIEW_REPLAY_V1, created_at, producer/version
```

Canonical byte fields are persisted as opaque BLOBs only after loader and hash
verification. API read models expose IDs/hashes and safe availability state,
never package bytes, fixture roots, project paths or media locations. Snapshot
ID/hash are calculated over the complete canonical identity projection; a
snapshot is append-only and cannot be replaced in place.

At most one active snapshot may bind a project/executable-sequence/policy
snapshot/plan-hash/bundle-hash tuple. A replacement requires a distinct
upstream Phase 12 bundle and creates a new snapshot; stale review or changed
policy fails closed. The Phase 13 SQLite database records metadata and verified
bytes, not renderer output, cache, retention class, quota or GC state.

## Resolver boundary

`StudioRenderInputResolverPort.resolve(project_id, sequence_id, review_snapshot)`
returns either the exact verified `RenderInputSnapshotV1` or a typed unavailable
result. It is the only component allowed to hand canonical bytes, `RenderProps`
and trusted fixture binding to `PreviewExecutionPort`. Neither route functions,
React, the review store nor caller request data can bypass it.

## Acceptance gates

1. A two-sequence REPLAY Phase 12/3 fixture produces two distinct snapshots;
   each reloads byte-identically after a fresh API app.
2. Forged EDL bytes/hashes, wrong project/sequence/policy, noncanonical props,
   caller path, changed plan/bundle and fixture drift fail before persistence.
3. The preview control plane receives only resolver output; no endpoint accepts
   EDL bytes, fixture path, RenderProps or mode.
4. Snapshot metadata never impersonates Phase 14 storage/GC; that view remains
   `UNAVAILABLE_OWNER_PHASE14`.

## Non-goals

No render invocation, preview media delivery, FULL render, provider/browser
automation, source/asset transport, queue/retry, cache/GC, lifecycle recovery,
direct filesystem UI access or Phase 14 implementation is authorized.
