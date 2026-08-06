# Phase 14 Durable Artifact Registry and Lifecycle Planning Contract

Status: candidate specification; implementation authorization is separate

## 1. Purpose and boundary

This contract introduces the durable, local control-plane records needed to
plan lifecycle work. It does not delete, move, restore, cache, render or start
a worker. Phase 4 remains the producer of verified render evidence; Phase 13
remains an HTTP-only consumer; Phase 15 owns provider transport/retry policy.

## 2. Canonical registry record

Each artifact has a canonical immutable `ArtifactRegistryRecordV1` containing:

```text
artifact_id, artifact_hash, project_id, sequence_id?, job_id?
artifact_type, content_hash, size_bytes, created_at, last_accessed_at
retention_class, dependency_ids, locked, pinned, approved
producer, producer_version, status, registry_record_id, registry_record_hash
```

`artifact_hash` is the SHA-256 of verified bytes. Registry identity is the
canonical JSON projection excluding only its own ID/hash. A record never stores
an absolute path, file URI, provider URI, secret, raw stderr or caller-supplied
ownership declaration. Existing `ArtifactRecord` values may enter only through
a verified adapter that recomputes identity and validates the full dependency
graph.

## 3. Retention and roots

The allowed classes are exactly the existing `engine.contracts.artifacts`
classes. `approved`, `final`, `provenance`, `baseline`, `pinned`, and any
locked record are protected roots. Active project revision, active job and
review-pending roots are explicit registry references, not inferred from file
timestamps. Dependencies are marked transitively. Missing dependency, cycle,
cross-project edge or contradictory protected/cleanup state fails closed.

## 4. Immutable dry-run deletion plan

`LifecycleDeletionPlanV1` is planning evidence, not permission to mutate. It
contains a plan ID/hash, policy snapshot ID/hash, as-of timestamp, registry
snapshot hash, protected root IDs, ordered candidate rows, total reclaimable
bytes, and a logical `.trash` destination token for every candidate. Each row
states the exact policy reason and dependency decision. A plan with a protected,
marked, locked, pinned or approved candidate is invalid.

The plan is invalid if its registry/policy/as-of binding changes. There is no
implicit recomputation at execution time and no age-only scan.

## 5. Future mutation gate

A later, separately authorized package may consume an accepted plan only after
revalidating the current registry snapshot and every candidate. It must use
two-stage promotion to a project-scoped trash area, write an append-only
receipt, support grace-period restore, and expose no destructive CLI/API before
a dry-run plan is visible. Permanent deletion, cache eviction and quota-driven
admission remain separate future decisions.

## 6. Atomic registry semantics

Registry append and manifest publication use a single local writer, durable
write/flush, and an explicit commit marker. A partial/uncommitted transaction
is unavailable to readers and requires recovery classification, never silent
cleanup. Content bytes are promoted from job-scoped staging only after their
hash, byte length, producer and dependency bindings validate.

## 7. Required verification

1. Deterministic serialize/reopen with identical IDs/hashes.
2. Forged byte/hash, duplicate identity, unknown dependency, cycle,
   cross-project dependency and path/URI leakage fail before registry append.
3. Protected roots and their transitive dependencies never appear in a plan.
4. Dry-run plan is byte-identical for fixed inputs and becomes invalid after a
   registry or policy mutation.
5. Phase 4 import is verified; Phase 13 receives truthful unavailable state
   until a later safe read API exists.

## 8. Exclusions

No provider, browser automation, generic queue/retry, FULL-render route,
media acquisition, cache eviction, quota enforcement, filesystem deletion,
trash move, restore or performance claim is authorized by this contract.
