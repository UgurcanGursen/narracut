# Phase 14 REPLAY Performance Acceptance

Decision: ACCEPT (bounded benchmark); Phase 14 Master remains OPEN.

The fixed Phase 4 REPLAY fixture runs once through the existing renderer and
then through the integrity-checked Phase 14 cache-hit path. The benchmark
requires byte-identical preview-manifest SHA-256 values before it can report
timing. The cache-hit measurement was no slower than the initial render.

Evidence: `tests/test_phase14_renderer_adapter.py`,
`engine/performance.py`; actual gate: `1 passed, 2 deselected in 31.96s`.

This proves only the bounded preview/cache optimization preserves the verified
manifest. It does not claim FULL-render audio quality, a generic SLO, provider
performance, worker queue behavior or Phase 15 observability.
