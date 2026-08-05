"""Phase 4A deterministic, REPLAY-only renderer adapter boundary."""

from .bridge import (
    BRIDGE_SEMVER, RENDER_PROPS_HASH_V1, RENDER_PROPS_V1, RenderBridgeError,
    RenderFailureCode, RenderMode, RenderProps, build_render_props,
    load_render_props, serialize_render_props,
)
from .fixture_assets import FixtureAssetResolver, FixtureAssetResolverError
from .receipt import RenderReceipt, RenderStatus, build_render_receipt, load_render_receipt, serialize_render_receipt
from .visual_directives import VisualDirective
from .preview_runner import PreviewRun, run_headless_preview
from .full_render import (
    FULL_REQUEST_V1, TARGET_RECORD_V1, FullRenderError, OutputTargetHead,
    atomic_publish, build_full_render_request, normalize_mux_probe,
    provision_output_target, resolve_output_target,
)
from .full_orchestrator import (
    FullRenderOutcome, RemotionFullRuntime, make_remotion_full_producer,
    run_full_render,
)

__all__ = [
    "BRIDGE_SEMVER", "RENDER_PROPS_HASH_V1", "RENDER_PROPS_V1",
    "RenderBridgeError", "RenderFailureCode", "RenderMode", "RenderProps",
    "FixtureAssetResolver", "FixtureAssetResolverError", "RenderReceipt",
    "RenderStatus", "build_render_props", "load_render_props",
    "serialize_render_props", "build_render_receipt", "load_render_receipt",
    "serialize_render_receipt", "VisualDirective",
    "PreviewRun", "run_headless_preview",
    "FULL_REQUEST_V1", "TARGET_RECORD_V1", "FullRenderError", "OutputTargetHead",
    "atomic_publish", "build_full_render_request", "normalize_mux_probe",
    "provision_output_target", "resolve_output_target",
    "FullRenderOutcome", "RemotionFullRuntime", "make_remotion_full_producer", "run_full_render",
]
