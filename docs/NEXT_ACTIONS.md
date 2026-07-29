# Next Actions

Aktif faz: Faz 0 CLOSED. Faz 1 CLOSED. Faz 2 IN_PROGRESS.

## NEXT RECOMMENDED TASK - Prepare the bounded candidate specification for PHASE2-SLICE-5-CANDIDATE

This is the single authoritative next task.

Task title:

```text
Canonical Adapter Execution Provenance Contract
```

Exact specification path:

```text
docs/specifications/phase2_slice5_canonical_adapter_execution_provenance_contract.md
```

Task constraints:

- specification-only
- may start only after this documentation synchronization is committed,
  manually exact-SHA verified, pushed, and remote closed on `main`
- bound to the accepted post-Slice-4 scope report in-scope/out-of-scope
  boundary
- no production implementation
- no production or test file modification
- the specification is not accepted by being drafted
- no Phase 2 closure claim

Scope basis:

```text
baseline/phase2_post_slice4_scope_report.md
```

Dependency boundary:

- Slice 1 - Temporal Raw Package
- Slice 2 - Canonical Narration
- Slice 3 - Canonical AudioArtifact
- Slice 4 - Canonical AlignmentRequest Contract

This dependency boundary is not the total Phase 2 Slice count.

The specification must preserve the selected candidate boundary:

- immutable adapter execution provenance bound to AlignmentRequest
- closed mode/status and evidence-presence rules
- canonical identity, hashing, serialization, and publication boundary
- paid-fallback authorization evidence
- replay evidence
- confidence-availability evidence
- golden and mutation-resistance contract tests

The specification must keep these areas out of scope:

- provider or alignment runtime execution
- canonical word timing result
- failure artifact
- AlignmentReport
- transcript divergence handling
- quality gates and corrections
- replay execution
- phrase grouping
- emphasis mapping
- frame compilation
- caption preview
- Phase 3 EDL or frame compilation

Implementation remains blocked until the specification has its own independent
audit and acceptance gate. This task does not close Phase 2.

## Deferred, not current work

- WorkspaceStore, SQLite, durable persistence, project recovery and packaging
  remain Phase 14-17 responsibilities.
- Provider automation and the Independent Editorial Critic Pipeline remain
  future binding decisions.
- Provider revoke/rotation remains a separate security/operations follow-up.
