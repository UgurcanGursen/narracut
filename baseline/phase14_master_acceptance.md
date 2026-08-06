# Phase 14 Master Acceptance

Decision: ACCEPT / `MASTER_PHASE_CLOSED` for the local, deterministic Phase 14
lifecycle boundary. This is not a Phase 15 validation decision or a claim of a
networked production service.

| Roadmap acceptance criterion | Result | Bounded evidence |
|---|---|---|
| One changed sequence rebuilds only that sequence | PASS | `run_incremental_sequences` consumes canonical dependency snapshots and invokes only `REBUILD` callbacks. |
| Cache cannot return stale output; preview and production are distinct | PASS | content/profile-bound cache tests and the Phase 4 preview lifecycle adapter. |
| Lifecycle entry leaves no unregistered producer artifact | PASS | `run_full_with_lifecycle` admits pressure, executes, then requires committed journal import before terminal success. |
| Protected/reference-aware cleanup has immutable dry-run and restore | PASS | registry, cache lifecycle and cache-plan receipt/restore gates. No permanent delete is implemented. |
| Hard quota/minimum free disk stop a new render | PASS | `storage_pressure_admission` is invoked before preview/FULL lifecycle runner execution. |
| Soft quota is safely managed | PASS (explicit synchronous boundary) | quota manager returns an immutable visible plan and does not invoke the runner until that pressure is resolved; accepted plans may be executed through the receipt-backed facade. No hidden scheduler is claimed. |
| Deduplication saving is measurable | PASS | deterministic logical-versus-physical storage accounting tests. |
| Performance optimization preserves visual/audio output | PASS (local REPLAY evidence) | actual Phase 4 FFmpeg preview/cache reuse plus a local FULL A/V FFmpeg fixture comparing final MP4 and audio-plan/filter/PCM hashes. |

Final regression gate:

```text
python -m pytest tests/test_phase14_closure_repair.py tests/test_phase14_storage_manager.py tests/test_phase14_cache_execution.py tests/test_phase14_cache_lifecycle.py tests/test_phase14_cache.py tests/test_phase14_lifecycle.py tests/test_phase14_renderer_adapter.py tests/test_phase14_performance.py tests/test_phase4b_registry_lifecycle.py tests/test_full_render_lifecycle.py -k "not wraps_one_real" -q -p no:cacheprovider --basetemp C:\tmp\phase14_final_closure_final
48 passed, 1 skipped, 1 deselected in 7.35s

python -m pytest tests/test_phase14_renderer_adapter.py -k "wraps_one_real" -vv -p no:cacheprovider --basetemp C:\tmp\phase14_preview_actual_final_run_tmp
1 passed, 3 deselected in 33.71s
```

Interpretation boundary: the legacy raw Phase 4 renderer primitive remains
backward-compatible by design. Phase 14 admission, committed-journal registry
import and terminal success semantics are enforced by its explicit lifecycle
entrypoints; no legacy primitive is reclassified as a complete lifecycle
operation merely because it can still be called directly.

Excluded: permanent deletion, autonomous worker/scheduler, provider transport,
generic queue/retry, Studio FULL-render HTTP route, and every Phase 15
validation/observability behavior.
