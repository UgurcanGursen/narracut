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

__all__ = [
    "BRIDGE_SEMVER", "RENDER_PROPS_HASH_V1", "RENDER_PROPS_V1",
    "RenderBridgeError", "RenderFailureCode", "RenderMode", "RenderProps",
    "FixtureAssetResolver", "FixtureAssetResolverError", "RenderReceipt",
    "RenderStatus", "build_render_props", "load_render_props",
    "serialize_render_props", "build_render_receipt", "load_render_receipt",
    "serialize_render_receipt", "VisualDirective",
    "PreviewRun", "run_headless_preview",
]
