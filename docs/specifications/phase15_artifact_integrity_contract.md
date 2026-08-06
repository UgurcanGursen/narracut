# Phase 15 Artifact Integrity Validator Contract

Status: candidate contract for independent audit; not implementation authority.

## Bounded objective

Attach truthful Phase 14 registry/deletion-plan evidence to the Phase 15
ledger. The validator proves only that a declared output is registry-bound and
that the provided non-destructive deletion plan exactly preserves declared
protected roots and their transitive dependencies.

## Exact inputs and behavior

- exact `ArtifactRegistryRecord` tuple, one project ID, expected output ID and
  content hash, deletion policy hash, protected root IDs, and one plan mapping;
- validate the registry with `registry_snapshot` and reject cross-project,
  missing/cyclic or identity-drift records;
- require the expected output record with exact project/content identity;
- recompute `plan_deletion(records, policy_hash, plan["as_of"], root_ids)` and
  require exact equality with the supplied plan; this proves plan identity,
  snapshot, protected closure and candidate set together;
- emit a hash-bound `artifact_integrity` evidence reference and exactly one
  `artifact_integrity` quality check using the deletion policy hash.

An expected output outside the registry, an input/project mismatch, a forged or
stale plan, or a candidate that would include a protected dependency is a
non-passing closed public result. Structurally unsafe inputs are rejected
before an observation is emitted. The validator never opens arbitrary paths,
deletes files, executes a plan, changes retention, or claims host-wide orphan
discovery.

## Required tests

- a registry-bound output plus canonical deletion plan passes;
- missing/wrong output and cross-project dependency cannot pass;
- forged/stale plan cannot pass;
- a root's transitive dependency cannot appear in candidates;
- unknown evidence/check tokens remain fail closed;
- no filesystem read/write/delete helper is imported by the validator.

## Exclusions

No arbitrary filesystem scan, permanent deletion, trash execution, worker,
transport, media decode, renderer/EDL mutation, Studio/UI, Phase 16 or Phase
17 behavior is authorized. Domain/final-narration and audio-boundary rows
remain open, as does Phase 15 Master acceptance.
