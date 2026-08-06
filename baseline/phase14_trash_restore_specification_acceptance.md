# Phase 14 Trash/Restore Specification Acceptance

Decision: ACCEPT; bounded implementation authorized.

The candidate consumes only revalidated lifecycle plans, preserves permanent
deletion exclusion, and keeps path authority in the managed project root.
Implementation may add only staging-to-trash and restore with focused tests and
append-only receipts. Cache, quota, provider, queue/retry and FULL render stay
out of scope.
