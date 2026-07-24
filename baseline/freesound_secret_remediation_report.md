# Freesound Secret Remediation Report

## Discovery summary

Freesound current-tree remediation was accepted before S2. The authoritative
source repo for this task is
`C:\Users\user\Documents\Kurgu_V3_Clean_sanitized_20260724_163134`, and S2
preflight confirmed the accepted working-tree delta set before building a new
sanitized sibling.

## Credential classification

The historical Freesound value is treated as a real secret and is never
printed in this report. Exact-value checks were derived in memory only for
absence verification.

## Current-tree remediation

Current working-tree remediation is preserved in the prepared sibling
`C:\Users\user\Documents\Kurgu_V3_Clean_sanitized_freesound_20260724_224147304`.
The sibling was created from current working-tree files only, with `.git`,
`norm_words_debug.json`, local env files and generated/cache/temp content
excluded.

## Canonical FREESOUND_API_KEY contract

- `.env.example` exposes only an empty `FREESOUND_API_KEY=` placeholder
- `v2/config.py` provides the canonical environment accessor
- `download_assets.py` consumes the canonical accessor rather than a hard-coded key

## Missing-key fail-closed behavior

Missing-key behavior is expected to fail closed. The remediation contract does
not allow a non-empty fallback key inside production code.

## HTTP suppression without key

The regression suite preserves the no-secret contract and safe missing-key
behavior.

## Regression tests

Accepted targeted remediation coverage remains:

- `tests/test_freesound_secret_remediation.py`
- `tests/test_pexels_secret_remediation.py`

Root-commit pre-push test execution for this sibling is still pending at this
report stage.

## Current-tree secret scan

Prepared sibling pre-init scan result:

- non-empty `FREESOUND_API_KEY` assignment: 0
- hard-coded Freesound credential-like literal: 0
- historical exact Freesound occurrence: 0
- non-empty Pexels fallback: 0
- historical exact Pexels occurrence: 0
- verified generic secret: 0
- local `.env` or secret file: 0
- binary/archive file: 0
- `.git` metadata: 0

## Pre-replacement reachable-history exposure

The source authoritative repo still carries reachable historical Freesound
exposure before replacement. This is why S2 creates a new parentless sanitized
root rather than rewriting the source working tree directly.

## S2 replacement plan

- source snapshot artifacts recorded under `C:\tmp\kurgu_freesound_s2_recovery_20260724_224056280`
- parentless sanitized sibling prepared at `C:\Users\user\Documents\Kurgu_V3_Clean_sanitized_freesound_20260724_224147304`
- remote replacement pending live SHA verification and exact `--force-with-lease`
- post-push verification must use fresh clones
- rollback must never reconnect the old secret-bearing chain to remote `main`

## Provider revoke/rotation status

Provider revoke/rotation remains **NOT CONFIRMED**.

## Remaining Phase 0 blockers

- Current tree remediated
- Sanitized-root replacement prepared
- Remote replacement pending verification
- Provider revoke/rotation NOT CONFIRMED
- Drawtext gate BLOCKED
- General Phase 0 OPEN
