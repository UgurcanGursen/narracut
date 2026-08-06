"""Small, deterministic Phase 14 replay performance evidence helper."""
from __future__ import annotations

import hashlib
from collections.abc import Callable
from time import perf_counter_ns


def benchmark_hash_preserving(*, baseline: Callable[[], bytes], candidate: Callable[[], bytes]) -> dict[str, object]:
    started = perf_counter_ns(); baseline_bytes = baseline(); baseline_ms = (perf_counter_ns() - started) // 1_000_000
    started = perf_counter_ns(); candidate_bytes = candidate(); candidate_ms = (perf_counter_ns() - started) // 1_000_000
    if type(baseline_bytes) is not bytes or type(candidate_bytes) is not bytes:
        raise ValueError("PERFORMANCE_OUTPUT_INVALID")
    baseline_hash = "sha256:" + hashlib.sha256(baseline_bytes).hexdigest()
    candidate_hash = "sha256:" + hashlib.sha256(candidate_bytes).hexdigest()
    if baseline_hash != candidate_hash:
        raise ValueError("PERFORMANCE_OUTPUT_HASH_CHANGED")
    return {"baseline_hash": baseline_hash, "candidate_hash": candidate_hash,
            "baseline_ms": baseline_ms, "candidate_ms": candidate_ms,
            "quality_preserved": True, "improved": candidate_ms <= baseline_ms}
