"""Small, deterministic Phase 14 replay performance evidence helper."""
from __future__ import annotations

import hashlib
from collections.abc import Callable
from time import perf_counter_ns
from typing import Mapping


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


def benchmark_full_av_hash_preserving(*, baseline: Callable[[], Mapping[str, object]], candidate: Callable[[], Mapping[str, object]]) -> dict[str, object]:
    def run(producer: Callable[[], Mapping[str, object]]) -> tuple[Mapping[str, object], int]:
        started = perf_counter_ns(); evidence = producer(); elapsed = (perf_counter_ns() - started) // 1_000_000
        if type(evidence) is not dict or type(evidence.get("final_output_bytes")) is not bytes: raise ValueError("FULL_AV_EVIDENCE_INVALID")
        required = {"audio_plan_hash", "filter_script_hash", "pcm_manifest_hash"}
        if any(not isinstance(evidence.get(key), str) or not evidence[key].startswith("sha256:") for key in required): raise ValueError("FULL_AV_EVIDENCE_INVALID")
        return evidence, elapsed
    first, first_ms = run(baseline); second, second_ms = run(candidate)
    first_projection = {"final_output_hash": "sha256:" + hashlib.sha256(first["final_output_bytes"]).hexdigest(), **{key: first[key] for key in ("audio_plan_hash", "filter_script_hash", "pcm_manifest_hash")}}
    second_projection = {"final_output_hash": "sha256:" + hashlib.sha256(second["final_output_bytes"]).hexdigest(), **{key: second[key] for key in ("audio_plan_hash", "filter_script_hash", "pcm_manifest_hash")}}
    if first_projection != second_projection: raise ValueError("FULL_AV_OUTPUT_HASH_CHANGED")
    return {"baseline": first_projection, "candidate": second_projection, "baseline_ms": first_ms, "candidate_ms": second_ms, "quality_preserved": True, "improved": second_ms <= first_ms}
