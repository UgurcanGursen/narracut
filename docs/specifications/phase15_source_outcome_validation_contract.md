# Phase 15 Source Outcome Validation Contract

## Scope

This package validates existing Phase 6 `SourceCapturePlan` outcomes and
attaches them to the Phase 15 ledger. It performs no URL request, browser
automation, retry/backoff, rate-limit waiting or fallback acquisition.

## Canonical outcome rules

The adapter receives only a validated `SourceCapturePlan`, its existing typed
Phase 6 `SourcePriorityPolicy`, a selected execution mode (`REPLAY`,
`MANUAL_UI` or `DISABLED`) and the resolved policy snapshot ID/hash. It requires
the policy's snapshot ID/hash to equal that resolved identity, then
recomputes/validates the plan identity through the Phase 6 boundary. It emits
one `transport/mode_declared` observation and exactly one
`quality_gate/check_evaluated` observation with `check_id: source_outcome`.

| Capture outcome | Ledger result |
|---|---|
| `accessible`/`text_found` + `NO_FALLBACK` | `PASSED` |
| `snapshot_available` + `SNAPSHOT_EVIDENCE` | `PASSED` with snapshot evidence |
| challenge/paywall/cookie/auth/manual-capture status + `MANUAL_CAPTURE_PACKAGE` | `NOT_READY`, `MANUAL_CAPTURE_REQUIRED`; never `PASSED` |
| `text_not_found` + `TEXT_ONLY_EVIDENCE` | `WARNING`, `TEXT_ONLY_EVIDENCE` |
| `unavailable` + `BLOCK_PLANNER` | `FAILED`, `SOURCE_UNAVAILABLE` |
| unsupported live/API/browser mode | `UNSUPPORTED`; never a successful capture |

An inconsistent status/fallback pair, policy identity drift, challenge with a
snapshot/render claim, raw URL/path/credential field, or a missing snapshot
reference is a fail-closed stable error. The adapter preserves Phase 6’s
fallback matrix; it cannot reinterpret a challenge page as source success.

The closed public errors are `SOURCE_OUTCOME_REQUEST_INVALID`,
`SOURCE_OUTCOME_PLAN_INVALID`, `SOURCE_OUTCOME_POLICY_MISMATCH`,
`SOURCE_OUTCOME_FALLBACK_INVALID`, `SOURCE_OUTCOME_SNAPSHOT_MISSING`,
`SOURCE_OUTCOME_CHALLENGE_FORBIDDEN` and `SOURCE_OUTCOME_MODE_UNSUPPORTED`.
Their observation references carry only the plan ID/hash, policy snapshot
ID/hash and safe status/fallback tokens; no URL or source text is recorded.

## Required future-live outcome shape

No live transport is enabled here. If one is enabled in its Phase 17 owner, its
normalized outcome must provide mode, attempt ordinal, timeout, byte/MIME,
redirect/SSRF, retry-budget, rate-limit, fallback and root failure results to
this validator. Omission is `NOT_READY`, not `PASSED`.

## Exclusions

No network, provider, queue/worker, media decode, Studio/UI, Phase 16 or Phase
17 behavior is implemented. Bounded acceptance needs deterministic matrix
tests, unsupported-mode tests and proof that challenge does not pass.
