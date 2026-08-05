# Phase 6 Final Acceptance Report

Date: 2026-08-05

## Scope

Phase 6 closes the REPLAY-first Source Acquisition and Evidence Treatment
Engine. It adds no live network acquisition, browser automation, CAPTCHA or
paywall bypass, provider retry/queue, UI, asset catalog, or Phase 7 behavior.

## Acceptance matrix

| Master Roadmap criterion | Evidence | Result |
| --- | --- | --- |
| Challenge screen cannot enter final evidence preview | challenge status rejects preview; capture/treatment binding required | PASS |
| Missing or ambiguous target text cannot invent coordinates | exact text/region validation; text-only fallback has no crop | PASS |
| Three focus events from one document | three verified, distinct capture regions retain three focus events | PASS |
| Paywall/challenge selects deterministic fallback | closed access-status to fallback matrix | PASS |
| Evidence without Playwright | `FeedApiAdapter` REPLAY path and diagnostic SVG test | PASS |
| Domain policy changes ranking without adapter fork | resolved `SourcePriorityPolicy` ranking test | PASS |
| Mandatory primary source can block planner | validated capture gate rejects challenged/text-only primary | PASS |

## Security and lineage

- The capture-plan identity includes a canonical source-package hash covering
  document text, verified region manifest, URL, access status and snapshot
  reference.
- Evidence planner accepts only regions already present in that manifest.
- Challenge/paywall/cookie/authentication states do not carry a renderable
  snapshot and cannot satisfy the mandatory-primary gate.
- Preview requires an exact capture-plan ID/hash binding.

## Verification

| Gate | Result |
| --- | --- |
| Source-engine focused gate | `12 passed` |
| Source-engine + V3 contracts after repair | `97 passed, 1 skipped` |
| Final source-engine + V3 + Phase 5 motion cross-contract gate | `102 passed, 1 skipped` |
| `python -m compileall -q engine/acquisition` | PASS |
| `git diff --check` | PASS |
| Independent final re-audit | PASS; BLOCKER/MAJOR/MINOR `0/0/0` |

## Known boundary

This acceptance proves deterministic, local `REPLAY` treatment only. A future
live transport must separately establish SSRF/redirect/MIME/byte/time limits,
timeouts, provider rate limiting and job retry semantics. Those operational
capabilities are not silently implied by this phase.
