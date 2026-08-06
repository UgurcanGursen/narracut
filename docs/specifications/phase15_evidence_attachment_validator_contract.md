# Phase 15 Evidence Attachment Validator Contract

## Purpose

This bounded validator transforms already accepted canonical evidence into the
first four `quality_gate/check_evaluated` observations of the local Phase 15
ledger. It validates cross-evidence identity before attaching an observation;
it neither creates nor mutates renderer, registry, storage or Domain Pack data.

## Inputs and validation order

The adapter receives only typed values or canonical bytes supplied by trusted
callers. It does not accept a filesystem path, URL, raw media payload or a
caller-selected parser.

1. Validate request tokens (`run_id`, `project_id`, policy hash and timestamp).
2. Load canonical Phase 4 `RenderProps` and `RenderReceipt`; require matching
   request/props/EDL IDs and hashes, and derive `project_id` from `RenderProps`.
3. Materialize the supplied Phase 14 registry rows and require one project
   match, a valid graph snapshot and receipt output artifact membership when a
   render succeeded.
4. Validate the supplied Phase 14 `StoragePressurePolicy` identity, scope and
   terminal admission outcome. The adapter records an existing outcome; it
   never reads disk or calls the render runner.
5. Validate the supplied immutable `DomainPolicySnapshot` data using the
   existing Domain Pack snapshot schema/loader and require its snapshot ID/hash
   to match the request policy binding.
6. Emit only after all relevant evidence validations pass; otherwise emit no
   success observation and return one stable attachment failure code.

## Attachments

| Check | PASS condition | Evidence reference |
|---|---|---|
| `render_path` | Phase 4 receipt/props identity is valid and terminal status is `SUCCEEDED` | `render_receipt` |
| `artifact_lifecycle` | registry graph is valid, project matches and successful output artifact is registered | `artifact_registry` |
| `storage_pressure` | admission outcome is `ADMITTED` or explicit `NOT_APPLICABLE` with policy/scope binding | `storage_admission` |
| `domain_contract` | resolved Domain Pack snapshot is canonical and request policy binding matches | `domain_snapshot` |

If an input represents a terminal producer failure, the adapter emits the
matching producer observation plus exact `failure_provenance` evidence, then
the ledger reducer decides `FAIL`; it never emits an unrelated passing check.

## Stable failures

`ATTACHMENT_REQUEST_INVALID`, `RENDER_EVIDENCE_INVALID`,
`RENDER_EVIDENCE_PROJECT_MISMATCH`, `ARTIFACT_EVIDENCE_INVALID`,
`ARTIFACT_OUTPUT_UNREGISTERED`, `STORAGE_EVIDENCE_INVALID`,
`DOMAIN_CONTRACT_EVIDENCE_INVALID` and `DOMAIN_CONTRACT_MISMATCH` are the only
public failures. A parser/policy error maps to its owning stable attachment
code without exposing paths or raw payloads.

## Exclusions and acceptance

No source/asset/timing transport, retry, rate-limit wait, queue/worker, media
decode, pixel/audio/semantic checking, threshold creation, storage mutation,
Studio/UI, Phase 16 or Phase 17 behavior is included. Tests must prove valid
attachments, each mismatch/failure code, no output on failed validation and
that a successful render with an absent registry artifact cannot pass.
