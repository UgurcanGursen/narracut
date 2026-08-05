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
    FullRenderOutcome, ToolchainRuntimeBindingV1, make_remotion_full_producer,
    preflight_full_render_toolchain, run_full_render,
)
from .template_contract import (
    CONTENT_SAFE_AREA_V1, CORE_TEMPLATE_DEFINITIONS, SAFE_AREA_POLICY_V1,
    SUBTITLE_SAFE_AREA_V1, TEMPLATE_RENDER_INPUT_V1, TEMPLATE_RENDER_PLAN_V1,
    TEMPLATE_VERSION_V1, PayloadKind, TemplateContractError,
    TemplateContractRejectionReason, TemplateDefinition, TemplateId,
    TemplateInvocationV1, TemplateKind, TemplatePolicyV1, TemplateRectV1,
    TemplateCompilationInputV1, TemplateRenderInputV1, TemplateRenderPlanV1, TemplateStylePresetV1,
    WordBindingV1, build_template_render_input, compile_template_render_plan,
    compile_template_render_plan_from_canonical,
    core_neutral_style_preset, load_template_render_plan,
    serialize_template_render_input, serialize_template_render_plan,
    style_preset_from_policy_snapshot, template_policy_from_policy_snapshot,
)
from .template_registry import (
    TemplateCandidateV1, TemplateRegistry, TemplateSelectionError,
)
from .template_runner import TemplatePreviewResult, TemplateRunnerError, run_template_replay

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
    "FullRenderOutcome", "ToolchainRuntimeBindingV1", "make_remotion_full_producer",
    "preflight_full_render_toolchain", "run_full_render",
    "CONTENT_SAFE_AREA_V1", "CORE_TEMPLATE_DEFINITIONS", "SAFE_AREA_POLICY_V1",
    "SUBTITLE_SAFE_AREA_V1", "TEMPLATE_RENDER_INPUT_V1", "TEMPLATE_RENDER_PLAN_V1",
    "TEMPLATE_VERSION_V1", "PayloadKind", "TemplateContractError",
    "TemplateContractRejectionReason", "TemplateDefinition", "TemplateId",
    "TemplateInvocationV1", "TemplateKind", "TemplatePolicyV1", "TemplateRectV1",
    "TemplateCompilationInputV1", "TemplateRenderInputV1", "TemplateRenderPlanV1", "TemplateStylePresetV1",
    "WordBindingV1", "build_template_render_input", "compile_template_render_plan",
    "compile_template_render_plan_from_canonical",
    "core_neutral_style_preset", "load_template_render_plan",
    "serialize_template_render_input", "serialize_template_render_plan",
    "style_preset_from_policy_snapshot", "template_policy_from_policy_snapshot",
    "TemplateCandidateV1", "TemplateRegistry", "TemplateSelectionError",
    "TemplatePreviewResult", "TemplateRunnerError", "run_template_replay",
]
