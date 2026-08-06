"""Phase 14 lifecycle adapter for an already-authorized Phase 4 renderer.

This module deliberately does not start a worker or reinterpret a render
request.  It is a narrow admission/cache/registry boundary around a caller
that already owns a Phase 4 invocation.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from engine.cache import cache_get, cache_key, cache_put, render_admission, storage_usage
from engine.lifecycle import (
    append_registry_records,
    import_verified_artifact_rows,
)
from engine.cache_lifecycle import cache_write_lifecycle_metadata

from .preview_runner import PreviewRun
from .receipt import RenderStatus


@dataclass(frozen=True)
class CachedPreviewOutcome:
    """A verified preview-manifest result, never a substitute ``PreviewRun``."""

    disposition: str
    cache_key: str
    preview_manifest_bytes: bytes
    output_sha256: str


def run_phase4_preview_cached(
    *,
    cache_root: Path,
    managed_storage_root: Path,
    registry_path: Path,
    profile: str,
    inputs: dict,
    estimated_bytes: int,
    hard_limit_bytes: int,
    lifecycle_timestamp_utc: str,
    runner: Callable[[], PreviewRun],
) -> CachedPreviewOutcome:
    """Admit one preview, or return an integrity-checked exact cache hit.

    Only a successful Phase 4 ``PreviewRun`` can populate the cache.  Failed
    and cancelled attempts intentionally leave no cache entry; their terminal
    renderer evidence remains the renderer's own responsibility.
    """
    key = cache_key(profile=profile, inputs=inputs)
    hit = cache_get(cache_root, key)
    if hit is not None:
        return CachedPreviewOutcome(
            disposition="CACHE_HIT",
            cache_key=key,
            preview_manifest_bytes=hit.payload,
            output_sha256=hit.payload_hash,
        )
    if render_admission(
        used_bytes=storage_usage(managed_storage_root)["bytes"],
        estimated_bytes=estimated_bytes,
        hard_limit_bytes=hard_limit_bytes,
    ) != "ADMITTED":
        raise ValueError("RENDER_BLOCKED_HARD_QUOTA")

    rendered = runner()
    if type(rendered) is not PreviewRun:
        raise ValueError("RENDER_OUTPUT_INVALID")
    if (
        rendered.receipt.status is not RenderStatus.SUCCEEDED
        or type(rendered.preview_manifest_bytes) is not bytes
        or rendered.receipt.output_sha256 != "sha256:" + __import__("hashlib").sha256(rendered.preview_manifest_bytes).hexdigest()
    ):
        raise ValueError("RENDER_OUTPUT_NOT_CACHEABLE")

    # Phase 4 has already built and validated this DAG.  Phase 14 translates
    # it into the durable, path-free registry before exposing a cache result.
    records = import_verified_artifact_rows(
        tuple(record.__dict__ for record in rendered.artifacts.records)
    )
    append_registry_records(registry_path=registry_path, records=records)
    lifecycle = cache_write_lifecycle_metadata(
        storage_scope_id="phase14_preview_cache", cache_key=key, profile=profile,
        payload_hash=rendered.receipt.output_sha256,
        payload_size_bytes=len(rendered.preview_manifest_bytes),
        producer_version="phase4a-renderer", timestamp_utc=lifecycle_timestamp_utc,
    )
    entry = cache_put(cache_root, key, rendered.preview_manifest_bytes, lifecycle=lifecycle)
    return CachedPreviewOutcome(
        disposition="RENDERED",
        cache_key=key,
        preview_manifest_bytes=entry.payload,
        output_sha256=entry.payload_hash,
    )
