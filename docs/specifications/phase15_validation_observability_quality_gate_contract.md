# Phase 15 — Validation, Observability and Quality-Gate Contract

## 1. Purpose and ownership

This contract defines the first Phase 15 boundary: a deterministic local run
evidence ledger and a fail-closed quality-gate decision. It is the shared
validation surface for accepted REPLAY and MANUAL_UI paths. It does not enable
network/provider transport, a worker, a retry loop, a Studio route, or Phase
16 reference benchmarking.

The contract owns the truthfulness of a run decision. Individual phases retain
ownership of their domain validation, renderer behavior, artifact lifecycle,
policy resolution and media operations.

## 2. Canonical evidence model

Every run has one caller-supplied, non-empty `run_id`, one declared execution
mode (`REPLAY`, `MANUAL_UI`, or `DISABLED`) and append-only canonical JSONL
observations. An observation has these required fields:

```json
{
  "schema_version": "PHASE15-RUN-OBSERVATION-V1",
  "run_id": "run_example",
  "ordinal": 1,
  "timestamp_utc": "2026-08-06T00:00:00Z",
  "category": "render",
  "event": "attempt_finished",
  "status": "succeeded",
  "provenance": {
    "producer": "phase4_preview",
    "input_hashes": ["sha256:..."],
    "artifact_ids": ["artifact_example"]
  }
}
```

`ordinal` starts at one and increments without gaps. `category`, `event` and
`status` are closed tokens. Input hashes and artifact IDs are sorted,
duplicate-free typed values. Observations cannot contain URLs with query
credentials, credentials, cookies, authorization headers, tokens, local
absolute paths, raw media, user prompt bodies, or unbounded stderr/stdout.
The writer rejects invalid input rather than silently redacting an ambiguous
payload; an explicit safe summary may be supplied by the caller.

`transport` observations may describe only the selected mode and a terminal
decision. For an enabled future live transport, the normalized observation
must expose: selected mode, attempt ordinal, timeout outcome, byte/MIME
outcome, redirect/SSRF outcome, retry-budget decision, rate-limit decision,
fallback decision and root failure code. In this package no live transport is
implemented; `API`/provider/browser modes are unsupported and must be reported
as `unsupported`, never simulated as success.

## 3. Terminal evidence and gate decision

The gate accepts only canonical bytes emitted by the observation writer plus
typed evidence references. It returns a canonical `QualityGateDecisionV1`:

```text
PASS | WARNING | FAIL | NOT_READY
```

`PASS` requires every declared required check to have an observed terminal
`passed` result and a non-empty provenance reference. `WARNING` requires the
same evidence plus an explicit warning code; a warning never converts missing,
unsupported, skipped, mocked, pending, unknown or not-implemented work into a
pass. `FAIL` is returned for a failed check, malformed evidence, identity
drift, an orphan artifact, or a root-cause failure observation. `NOT_READY` is
returned when a required check lacks terminal evidence or is unsupported.

The caller supplies the immutable required-check set. Threshold values are
declared in that set with a policy identifier/hash. The gate does not mutate,
infer or relax a threshold to obtain a pass. A decision lists all checked,
missing, failed and warning codes in stable order, with the observation ordinal
and hash that justified each result.

The first bounded required checks are:

| Check | Required evidence | Failure outcome |
|---|---|---|
| `render_path` | Phase 4 render receipt and terminal status | `RENDER_EVIDENCE_MISSING` |
| `artifact_lifecycle` | Phase 14 registry/receipt reference | `ARTIFACT_EVIDENCE_MISSING` |
| `storage_pressure` | Phase 14 admission or explicit non-applicability | `STORAGE_EVIDENCE_MISSING` |
| `domain_contract` | resolved Domain Pack/core contract snapshot | `DOMAIN_CONTRACT_EVIDENCE_MISSING` |
| `failure_provenance` | terminal failure code when any operation fails | `FAILURE_PROVENANCE_MISSING` |

No quality decision claims pixel, audio, semantic, source, claim or transport
validation unless that exact check is declared and has its own evidence.

## 4. Metric projection

The ledger may deterministically project only observed values: run elapsed
time, per-sequence render timing, cache hit/miss, artifact/storage values,
orphan count, dedup savings, failure-code counts and selected transport
outcomes. Missing data stays missing; zero is not a default. Metric keys are
closed and values are derived from referenced observations only.

## 5. Failure precedence

Input/canonical-byte validation precedes run identity, ordinal continuity,
policy validation, evidence-reference validation and quality-check evaluation.
The first failed phase emits one stable public code and no unsafe payload. A
terminal failure cannot later be overwritten by a `PASS` observation.

## 6. Explicit exclusions

- actual provider, source, asset or timing transport;
- retry execution, rate-limit waiting or queue/worker scheduling;
- browser automation or access-control bypass;
- media decode, pixel/audio/semantic-analysis implementation;
- permanent deletion, storage mutation or a new lifecycle policy;
- Studio/FastAPI endpoints and React UI;
- Phase 16 benchmark thresholds and Phase 17 product-gate conclusions.

## 7. Bounded acceptance

1. Same ordered safe input emits byte-identical JSONL, metric projection and
   gate decision.
2. Missing, unsupported, mocked, pending, unknown or not-implemented required
   evidence cannot return `PASS` or `WARNING`.
3. A failure decision exposes a stable root cause and evidence pointer without
   leaking sensitive/path/raw-content data.
4. Tampered observation bytes, ordinal gaps, cross-run references, duplicate
   IDs/hashes and terminal-status contradictions fail closed.
5. Existing Phase 4/14 REPLAY evidence can enter the gate without changing
   renderer or lifecycle semantics.
