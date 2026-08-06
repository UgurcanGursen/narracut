# Phase 15 Scope Reconciliation

Decision: the first Phase 15 implementation package is the local
`RunEvidenceLedger + QualityGateDecision` contract at
`docs/specifications/phase15_validation_observability_quality_gate_contract.md`.

## Why this package first

The roadmap requires validation to report truthfully and makes missing or
not-implemented work non-valid. Existing phase evidence is distributed across
render receipts, registry/cache records and individual validation artifacts;
there is no shared canonical decision boundary that can say precisely which
evidence was observed, missing or unsupported. Adding a live transport first
would violate the Phase 17 ownership of operational source/asset/timing modes.

## In scope

- canonical append-only run observations and safe provenance summaries;
- deterministic evidence/metric projection;
- a fail-closed decision for declared checks and bounded Phase 4/14 evidence;
- explicit unsupported-mode transport observations, without transport calls;
- tests for identity, continuity, redaction/no-leak, missing evidence and
  decision precedence.

## Out of scope

- provider/source/asset/timing transport, retry execution, queue, rate-limit
  waiting or browser automation;
- new renderer, media analysis, lifecycle mutation, permanent delete, Studio
  API/UI, Phase 16 metrics or Phase 17 packaging;
- reopening accepted Phase 0–14 implementation.

## Acceptance dependency map

```text
Phase 4 receipt + Phase 14 lifecycle evidence + Domain Pack snapshot
    -> Phase 15 canonical observation ledger
    -> declared quality checks
    -> PASS/WARNING/FAIL/NOT_READY decision
```

The proposed contract deliberately does not declare a quality check for an
unimplemented validator. Therefore it cannot turn an absent pixel, audio,
source, semantic or transport validator into a passing result.

Next task: independently audit this candidate contract for roadmap coverage,
scope discipline, failure precedence and backward-compatible integration
before any implementation is authorized.
