from engine.performance import benchmark_hash_preserving


def test_benchmark_requires_exact_output_hash_and_reports_timing():
    receipt = benchmark_hash_preserving(baseline=lambda: b"same", candidate=lambda: b"same")
    assert receipt["quality_preserved"] and receipt["baseline_hash"] == receipt["candidate_hash"]
