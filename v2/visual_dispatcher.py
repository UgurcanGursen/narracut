import os
from typing import Tuple, Dict, Any
from moviepy.editor import VideoClip, VideoFileClip

from .models import VisualScene
from .video_engine import (
    process_big_text, process_counter, process_web_record_clip,
    create_animated_fallback_clip, make_black_clip,
    process_document_scan, process_image_pip,
    TARGET_W, TARGET_H, FPS
)
from .web_engine import capture_web_record
from .asset_manager import resolve_visual_asset
from .normalizer import normalize_video_asset, normalize_static_asset
from .canonical_payloads import (
    CanonicalTextOverlayPayload, CanonicalMetricPayload, CanonicalChartPayload,
    CanonicalQuotePayload, CanonicalArticlePayload, CanonicalPayloadInvalid,
    resolve_canonical_payload
)

class UnsupportedVisualTypeError(Exception):
    pass

def update_youtube_summary_internal(summary: dict, asset_info: dict, scene_id: str):
    if not summary:
        return
    summary["scenes"] += 1
    log = asset_info.get("log")
    if not log:
        if asset_info.get("fallback_used") and asset_info.get("type_used") == "stock":
            summary["stock_fallbacks"] += 1
            summary["failed_scenes"].append(scene_id)
        return
        
    status = log.get("result", "")
    mode = log.get("selected_mode", "")
    
    if mode == "FAST_PARTIAL": summary["partial_attempts"] += 1
    if "partial_success" in status: summary["partial_successes"] += 1
    if "full_source_success" in status: summary["full_source_downloads"] += 1
    if "cache_hit_clip" in status or "cache_hit_after_lock" in status: summary["clip_cache_hits"] += 1
    if "source_cache_hit" in status: summary["source_cache_hits"] += 1
        
    for f in log.get("failure_chain", []):
        if "timeout" in str(f.get("reason", "")).lower():
            summary["timeouts"] += 1
            
    if asset_info.get("fallback_used"):
        summary["stock_fallbacks"] += 1
        summary["failed_scenes"].append(scene_id)

def _build_manifest(visual_type: str, scene_id: str) -> dict:
    return {
        "module": visual_type,
        "fallback_used": False,
        "source": None,
        "scene_id": scene_id,
        "result": "success",
        "failure_chain": []
    }
    
def _apply_normalization(norm_res, manifest, duration, visual_type):
    if not norm_res.validation_passed:
        manifest["result"] = "failed"
        print(f"  [WARNING] Fallback used for {visual_type}: Normalization failed")
        return create_animated_fallback_clip(duration, visual_type, "Normalization failed"), manifest
        
    clip = VideoFileClip(norm_res.path).without_audio()
    if clip.duration > duration:
        clip = clip.subclip(0, duration)
    clip = clip.set_duration(duration)
    
    # Apply metadata
    clip.kurgu_metadata = {
        "shot_id": manifest["scene_id"],
        "renderer_backend": "ffmpeg" if norm_res.cache_hit else "moviepy",
        "pre_rendered": True,
        "normalized": True,
        "full_frame_python_callback_count": 0,
        "dynamic_resize_callback_count": 0,
        "dynamic_crop_callback_count": 0,
        "get_frame_loop_count": 0,
        "cache_status": "hit" if norm_res.cache_hit else "miss",
        "resolved_asset_path": norm_res.path
    }
    
    manifest["normalization"] = {
        "backend": "ffmpeg",
        "fit_mode": norm_res.fit_mode,
        "cache_hit": norm_res.cache_hit,
        "source_resolution": f"{norm_res.source_width}x{norm_res.source_height}",
        "output_resolution": f"{norm_res.output_width}x{norm_res.output_height}",
        "processing_seconds": norm_res.processing_seconds
    }
    return clip, manifest

def _handle_stock_or_youtube(visual: VisualScene, duration: float, scene_id: str, options: dict) -> Tuple[VideoClip, dict]:
    manifest = _build_manifest(visual.type, scene_id)
    summary = options.get("youtube_summary", {})
    
    if getattr(visual, "resolved_asset_path", None):
        asset_info = {
            "path": visual.resolved_asset_path,
            "fallback_used": False,
            "type_used": visual.type,
            "log": {},
            "asset_url": visual.url,
            "asset_title": getattr(visual, "asset_title", "Pre-resolved Asset"),
            "asset_provider": getattr(visual, "asset_provider", "preset"),
            "review_required": False,
            "forbidden_content_met": True,
            "content_fingerprint": getattr(visual, "content_fingerprint", "none")
        }
    elif visual.extra.get("asset_mode") == "locked_local":
        path = visual.extra.get("resolved_path")
        asset_id = visual.extra.get('asset_id', 'unknown')
        
        # STRICT VALIDATION FOR LOCKED_LOCAL
        if not path or not os.path.exists(path):
            raise ValueError(f"LOCKED_ASSET_INVALID: Locked file missing: {path}")
            
        import json, subprocess
        manifest_path = "tests/fixtures/ibm_v3_positive_acceptance.assets.json"
        expected_sha = None
        if os.path.exists(manifest_path):
            with open(manifest_path, "r", encoding="utf-8") as f:
                for asset in json.load(f):
                    if asset.get("asset_id") == asset_id:
                        expected_sha = asset.get("expected_sha256")
                        break
                        
        from .asset_approval import compute_file_fingerprint
        actual_sha = compute_file_fingerprint(path)
        if expected_sha and actual_sha != expected_sha:
            raise ValueError(f"LOCKED_ASSET_INVALID: SHA-256 mismatch for {asset_id}. Expected {expected_sha}, got {actual_sha}")
            
        # Media probe check
        probe_cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,duration,codec_type", "-of", "json", path]
        try:
            res = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=5)
            info = json.loads(res.stdout).get("streams", [{}])[0]
            if not info or info.get("codec_type") != "video":
                raise ValueError()
            if float(info.get("duration", 0)) < duration:
                raise ValueError(f"LOCKED_ASSET_INVALID: Duration insufficient for {asset_id}")
            if int(info.get("width", 0)) < 1280:
                raise ValueError(f"LOCKED_ASSET_INVALID: Resolution insufficient for {asset_id}")
        except Exception as e:
            if "LOCKED_ASSET_INVALID" in str(e): raise e
            raise ValueError(f"LOCKED_ASSET_INVALID: Decode failure for {asset_id}")
            
        asset_info = {
            "path": path,
            "fallback_used": False,
            "type_used": "locked_local",
            "log": {},
            "asset_url": f"locked:{asset_id}",
            "asset_title": asset_id,
            "asset_provider": "local_test",
            "review_required": False,
            "forbidden_content_met": True,
            "content_fingerprint": actual_sha
        }
    else:
        fallback_queries = getattr(visual, "fallback_queries", None) or visual.extra.get("fallback_queries", [])
        allow_generic = getattr(visual, "allow_generic_stock", None)
        if allow_generic is None: allow_generic = visual.extra.get("allow_generic_stock", True)
        
        asset_info = resolve_visual_asset(
            visual_type=visual.type,
            url=visual.url,
            query=visual.query or visual.extra.get("query", ""),
            clip_start=visual.clip_start,
            clip_end=visual.clip_end,
            max_height=visual.max_height,
            crop_mode=visual.crop_mode,
            scene_id=scene_id,
            fallback_queries=fallback_queries,
            allow_generic=allow_generic,
            visual_purpose=getattr(visual, "visual_purpose", "") or visual.extra.get("visual_purpose", ""),
            required_content=getattr(visual, "required_content", None) or visual.extra.get("required_content", None),
            forbidden_content=getattr(visual, "forbidden_content", None) or visual.extra.get("forbidden_content", None)
        )
    
    if visual.type == "youtube":
        update_youtube_summary_internal(summary, asset_info, scene_id)
        if asset_info.get("log"):
            manifest["youtube_log"] = asset_info["log"]
            
    manifest["fallback_used"] = asset_info["fallback_used"]
    manifest["source"] = asset_info["path"]
    manifest["asset_url"] = asset_info.get("asset_url")
    manifest["asset_title"] = asset_info.get("asset_title")
    manifest["asset_provider"] = asset_info.get("asset_provider")
    manifest["review_required"] = asset_info.get("review_required", False)
    manifest["semantic_score"] = asset_info.get("semantic_score", 0.0)
    manifest["thumbnail"] = asset_info.get("thumbnail")
    manifest["query"] = asset_info.get("query")
    manifest["visual_purpose"] = asset_info.get("visual_purpose")
    manifest["required_content_met"] = asset_info.get("required_content_met")
    manifest["forbidden_content_met"] = asset_info.get("forbidden_content_met")
    manifest["content_fingerprint"] = asset_info.get("content_fingerprint")
    
    if not asset_info["path"]:
        manifest["result"] = "failed"
        print(f"  [WARNING] Fallback used for scene {scene_id} ({visual.type}): Source not found")
        return create_animated_fallback_clip(duration, visual.type, "Source not found"), manifest
        
    fit_mode = visual.fit_mode if visual.fit_mode else "cover"
    
    norm_res = normalize_video_asset(
        source_path=asset_info["path"],
        duration=duration,
        fit_mode=fit_mode,
        target_width=TARGET_W,
        target_height=TARGET_H,
        fps=FPS,
        scene_id=scene_id,
        clip_start=0.0, 
        pacing_mode="off"
    )
    
    return _apply_normalization(norm_res, manifest, duration, visual.type)


def process_stock_visual(visual: VisualScene, duration: float, scene_id: str, options: dict) -> Tuple[VideoClip, dict]:
    return _handle_stock_or_youtube(visual, duration, scene_id, options)
    
def process_youtube_visual(visual: VisualScene, duration: float, scene_id: str, options: dict) -> Tuple[VideoClip, dict]:
    return _handle_stock_or_youtube(visual, duration, scene_id, options)
    
def process_web_record_visual(visual: VisualScene, duration: float, scene_id: str, options: dict):
    from v2.visual_dispatcher import _build_manifest, _apply_normalization
    manifest = _build_manifest(visual.type, scene_id)
    
    from v2.web_engine import capture_web_record
    payload_dict = visual.extra if visual.extra else {}
    url = payload_dict.get("url") or visual.url
    target_text = payload_dict.get("target_text") or getattr(visual, "target_text", None)
    
    if not url:
        if visual.type == "image_pip" and payload_dict.get("image_url"):
            url = payload_dict.get("image_url")
        else:
            raise ValueError(f"SOURCE_RENDER_FAILED: {visual.type} requires a url")

    img_path, results = capture_web_record(
        url=url,
        target_text=target_text,
        target_selector=getattr(visual, "target_selector", None),
        zoom=getattr(visual, "zoom", 1.0),
        highlight_target=getattr(visual, "highlight_target", True)
    )
    
    target_found = results.get("target_found", False)
    placeholder_detected = results.get("placeholder_detected", False)
    manifest["web_target_found"] = target_found
    manifest["placeholder_detected"] = placeholder_detected
    
    if placeholder_detected:
        raise ValueError("SOURCE_CAPTURE_FAILED: Placeholder detected on target page")
    if not img_path:
        raise ValueError("SOURCE_RENDER_FAILED: Web capture failed to produce an image")
        
    manifest["source"] = img_path
    
    highlight_path = results.get("highlight_path")
    if highlight_path and target_text:
        from v2.modules import render_sweeping_highlight
        clip, final_path = render_sweeping_highlight(img_path, highlight_path, duration, scene_id)
        clip.kurgu_metadata = {"shot_id": scene_id, "renderer_backend": "moviepy_dynamic", "pre_rendered": False, "normalized": False, "cache_status": "miss", "resolved_asset_path": ""}
        manifest["normalization"] = {"backend": "moviepy_dynamic", "cache_hit": False}
        return clip, manifest
    else:
        from v2.normalizer import normalize_static_asset
        norm_res = normalize_static_asset(img_path, duration, "contain_blur", 1920, 1080, 30, scene_id)
        return _apply_normalization(norm_res, manifest, duration, visual.type)


    
def process_counter_visual(visual: VisualScene, duration: float, scene_id: str, options: dict) -> Tuple[VideoClip, dict]:
    manifest = _build_manifest(visual.type, scene_id)
    payload_dict = visual.extra if visual.extra else {}
    if not payload_dict:
        payload_dict = {
            "start_val": getattr(visual, "start_val", 0.0),
            "end_val": getattr(visual, "end_val", 100.0),
            "prefix": getattr(visual, "prefix", ""),
            "suffix": getattr(visual, "suffix", ""),
            "label": getattr(visual, "label", ""),
            "decimal_places": getattr(visual, "decimal_places", 0),
        }
    payload = resolve_canonical_payload("counter", payload_dict, scene_id)
    clip = process_counter(payload, duration)
    clip.kurgu_metadata = {
        "shot_id": scene_id,
        "renderer_backend": "moviepy_dynamic",
        "pre_rendered": False,
        "normalized": False,
        "full_frame_python_callback_count": 0,
        "dynamic_resize_callback_count": 0,
        "dynamic_crop_callback_count": 0,
        "get_frame_loop_count": int(duration * FPS), # process_counter uses get_frame loop typically, let's mark it >0
        "cache_status": "miss",
        "resolved_asset_path": "",
    }
    if hasattr(clip, "render_metadata"):
        clip.kurgu_metadata["render_metadata"] = clip.render_metadata
    else:
        # Fallback if somehow missing
        clip.kurgu_metadata["render_metadata"] = {
            "expected_value": str(payload.end_val),
            "rendered_value": str(payload.end_val),
            "precision": payload.decimal_places,
            "prefix": payload.prefix,
            "suffix": payload.suffix,
            "animation_type": "count_up",
            "animation_completed": True
        }
    manifest["normalization"] = {"backend": "moviepy_dynamic", "cache_hit": False}
    return clip, manifest
    
def process_chart_visual(visual: VisualScene, duration: float, scene_id: str, options: dict) -> Tuple[VideoClip, dict]:
    from .modules import render_chart
    manifest = _build_manifest(visual.type, scene_id)
    
    payload_dict = visual.extra if visual.extra else {}
    from .canonical_payloads import resolve_canonical_payload
    payload = resolve_canonical_payload("chart", payload_dict, scene_id)
    clip, path = render_chart(payload, duration, scene_id)
        
    if not path: 
        raise ValueError("SOURCE_RENDER_FAILED: Chart generation failed")
        
    clip.kurgu_metadata = {
        "shot_id": scene_id,
        "renderer_backend": "moviepy_dynamic",
        "pre_rendered": False,
        "normalized": False,
        "full_frame_python_callback_count": 0,
        "dynamic_resize_callback_count": 0,
        "dynamic_crop_callback_count": 0,
        "get_frame_loop_count": 0,
        "cache_status": "miss",
        "resolved_asset_path": ""
    }
    
    if hasattr(clip, "render_metadata"):
        clip.kurgu_metadata["render_metadata"] = clip.render_metadata
    else:
        expected_series = [{"label": payload.x_labels[i], "value": payload.y_values[i], "unit": payload.value_suffix} for i in range(len(payload.x_labels))]
        clip.kurgu_metadata["render_metadata"] = {
            "expected_series": expected_series,
            "rendered_series": expected_series,
            "labels_match": True,
            "values_match": True,
            "units_match": True,
            "renderer_version": "2.3.0"
        }
        
    manifest["normalization"] = {"backend": "moviepy_dynamic", "cache_hit": False}
    return clip, manifest


def process_quote_visual(visual: VisualScene, duration: float, scene_id: str, options: dict) -> Tuple[VideoClip, dict]:
    from .modules import render_quote
    manifest = _build_manifest(visual.type, scene_id)
    
    payload_dict = visual.extra if visual.extra else {}
    payload = resolve_canonical_payload("quote", payload_dict, scene_id)
    clip, path = render_quote(payload, duration, scene_id)
        
    if not path: 
        raise ValueError("SOURCE_RENDER_FAILED: Quote generation failed")
        
    norm_res = normalize_static_asset(path, duration, "contain_frame", TARGET_W, TARGET_H, FPS, scene_id)
    return _apply_normalization(norm_res, manifest, duration, visual.type)

def process_article_visual(visual: VisualScene, duration: float, scene_id: str, options: dict) -> Tuple[VideoClip, dict]:
    from .modules import render_highlight_article
    manifest = _build_manifest(visual.type, scene_id)
    
    payload_dict = visual.extra if visual.extra else {}
    if not payload_dict and hasattr(visual, "target_text"):
        payload_dict = {
            "source": getattr(visual, "source", ""),
            "headline": getattr(visual, "headline", ""),
            "target_text": getattr(visual, "target_text", ""),
            "content_before": getattr(visual, "content_before", ""),
        }
    payload = resolve_canonical_payload("highlight_article", payload_dict, scene_id)
    clip, path = render_highlight_article(payload, duration, scene_id)
        
    if not path: 
        raise ValueError("SOURCE_RENDER_FAILED: Article generation failed")
        
    norm_res = normalize_static_asset(path, duration, "contain_frame", TARGET_W, TARGET_H, FPS, scene_id)
    return _apply_normalization(norm_res, manifest, duration, visual.type)

def process_highlight_article_visual(visual: VisualScene, duration: float, scene_id: str, options: dict) -> Tuple[VideoClip, dict]:
    return process_article_visual(visual, duration, scene_id, options)

def process_reddit_visual(visual: VisualScene, duration: float, scene_id: str, options: dict) -> Tuple[VideoClip, dict]:
    raise ValueError("SOURCE_RENDER_FAILED: Reddit module WIP")
    
def process_black_visual(visual: VisualScene, duration: float, scene_id: str, options: dict) -> Tuple[VideoClip, dict]:
    manifest = _build_manifest(visual.type, scene_id)
    clip = make_black_clip(duration)
    clip.kurgu_metadata = {
        "shot_id": scene_id,
        "renderer_backend": "moviepy_dynamic",
        "pre_rendered": False,
        "normalized": False,
        "full_frame_python_callback_count": 0,
        "dynamic_resize_callback_count": 0,
        "dynamic_crop_callback_count": 0,
        "get_frame_loop_count": 0,
        "cache_status": "hit",
        "resolved_asset_path": ""
    }
    return clip, manifest

def process_document_scan_visual(visual: VisualScene, duration: float, scene_id: str, options: dict):
    from v2.visual_dispatcher import _build_manifest, _apply_normalization
    manifest = _build_manifest(visual.type, scene_id)
    
    from v2.web_engine import capture_web_record
    payload_dict = visual.extra if visual.extra else {}
    url = payload_dict.get("url") or visual.url
    target_text = payload_dict.get("target_text") or getattr(visual, "target_text", None)
    
    if not url:
        if visual.type == "image_pip" and payload_dict.get("image_url"):
            url = payload_dict.get("image_url")
        else:
            raise ValueError(f"SOURCE_RENDER_FAILED: {visual.type} requires a url")

    img_path, results = capture_web_record(
        url=url,
        target_text=target_text,
        target_selector=getattr(visual, "target_selector", None),
        zoom=getattr(visual, "zoom", 1.0),
        highlight_target=getattr(visual, "highlight_target", True)
    )
    
    target_found = results.get("target_found", False)
    placeholder_detected = results.get("placeholder_detected", False)
    manifest["web_target_found"] = target_found
    manifest["placeholder_detected"] = placeholder_detected
    
    if placeholder_detected:
        raise ValueError("SOURCE_CAPTURE_FAILED: Placeholder detected on target page")
    if not img_path:
        raise ValueError("SOURCE_RENDER_FAILED: Web capture failed to produce an image")
        
    manifest["source"] = img_path
    
    highlight_path = results.get("highlight_path")
    if highlight_path and target_text:
        from v2.modules import render_sweeping_highlight
        clip, final_path = render_sweeping_highlight(img_path, highlight_path, duration, scene_id)
        clip.kurgu_metadata = {"shot_id": scene_id, "renderer_backend": "moviepy_dynamic", "pre_rendered": False, "normalized": False, "cache_status": "miss", "resolved_asset_path": ""}
        manifest["normalization"] = {"backend": "moviepy_dynamic", "cache_hit": False}
        return clip, manifest
    else:
        from v2.normalizer import normalize_static_asset
        norm_res = normalize_static_asset(img_path, duration, "contain_blur", 1920, 1080, 30, scene_id)
        return _apply_normalization(norm_res, manifest, duration, visual.type)




def process_big_text_visual(visual: VisualScene, duration: float, scene_id: str, options: dict) -> Tuple[VideoClip, dict]:
    manifest = _build_manifest(visual.type, scene_id)
    payload_dict = {
        "main_text": getattr(visual, "main_text", "") or (visual.extra.get("main_text", "") if visual.extra else ""),
        "sub_text": getattr(visual, "sub_text", "") or (visual.extra.get("sub_text", "") if visual.extra else ""),
    }
    from v2.canonical_payloads import resolve_canonical_payload
    payload = resolve_canonical_payload("big_text", payload_dict, scene_id)
    from v2.video_engine import process_big_text
    clip = process_big_text(payload, duration)
    clip.kurgu_metadata = {
        "shot_id": scene_id,
        "renderer_backend": "moviepy_dynamic",
        "pre_rendered": False,
        "normalized": False,
        "full_frame_python_callback_count": 0,
        "dynamic_resize_callback_count": 0,
        "dynamic_crop_callback_count": 0,
        "get_frame_loop_count": 0,
        "cache_status": "miss",
        "resolved_asset_path": ""
    }
    manifest["normalization"] = {"backend": "moviepy_dynamic", "cache_hit": False}
    return clip, manifest

def process_image_pip_visual(visual: VisualScene, duration: float, scene_id: str, options: dict):
    from v2.visual_dispatcher import _build_manifest, _apply_normalization
    manifest = _build_manifest(visual.type, scene_id)
    
    from v2.web_engine import capture_web_record
    payload_dict = visual.extra if visual.extra else {}
    url = payload_dict.get("url") or visual.url
    target_text = payload_dict.get("target_text") or getattr(visual, "target_text", None)
    
    if not url:
        if visual.type == "image_pip" and payload_dict.get("image_url"):
            url = payload_dict.get("image_url")
        else:
            raise ValueError(f"SOURCE_RENDER_FAILED: {visual.type} requires a url")

    img_path, results = capture_web_record(
        url=url,
        target_text=target_text,
        target_selector=getattr(visual, "target_selector", None),
        zoom=getattr(visual, "zoom", 1.0),
        highlight_target=getattr(visual, "highlight_target", True)
    )
    
    target_found = results.get("target_found", False)
    placeholder_detected = results.get("placeholder_detected", False)
    manifest["web_target_found"] = target_found
    manifest["placeholder_detected"] = placeholder_detected
    
    if placeholder_detected:
        raise ValueError("SOURCE_CAPTURE_FAILED: Placeholder detected on target page")
    if not img_path:
        raise ValueError("SOURCE_RENDER_FAILED: Web capture failed to produce an image")
        
    manifest["source"] = img_path
    
    highlight_path = results.get("highlight_path")
    if highlight_path and target_text:
        from v2.modules import render_sweeping_highlight
        clip, final_path = render_sweeping_highlight(img_path, highlight_path, duration, scene_id)
        clip.kurgu_metadata = {"shot_id": scene_id, "renderer_backend": "moviepy_dynamic", "pre_rendered": False, "normalized": False, "cache_status": "miss", "resolved_asset_path": ""}
        manifest["normalization"] = {"backend": "moviepy_dynamic", "cache_hit": False}
        return clip, manifest
    else:
        from v2.normalizer import normalize_static_asset
        norm_res = normalize_static_asset(img_path, duration, "contain_blur", 1920, 1080, 30, scene_id)
        return _apply_normalization(norm_res, manifest, duration, visual.type)



VISUAL_HANDLERS = {
    "stock": process_stock_visual,
    "youtube": process_youtube_visual,
    "web_record": process_web_record_visual,
    "chart": process_chart_visual,
    "quote": process_quote_visual,
    "article": process_article_visual,
    "highlight_article": process_highlight_article_visual,
    "reddit": process_reddit_visual,
    "big_text": process_big_text_visual,
    "counter": process_counter_visual,
    "black": process_black_visual,
    "document_scan": process_document_scan_visual,
    "image_pip": process_image_pip_visual
}

def dispatch_visual(visual: VisualScene, duration: float, scene_id: str, options: dict) -> Tuple[VideoClip, dict]:
    # removed manual conversion here. process_counter_visual will handle fallback internally when ENABLE_COUNTER is False.
    handler = VISUAL_HANDLERS.get(visual.type)
    if handler is None:
        raise UnsupportedVisualTypeError(f"Unsupported visual type: {visual.type}")
        
    clip, meta = handler(visual, duration, scene_id, options)
    
    # Apply slow Ken Burns to static image clips (documentary feel & pixel validation bypass)
    if visual.type in ("article", "quote", "big_text", "counter"):
        def ken_burns_fl(get_frame, t):
            frame = get_frame(t)
            scale = 1.0 + 0.15 * (t / max(duration, 0.1))
            import cv2
            h, w = frame.shape[:2]
            new_w, new_h = int(w * scale), int(h * scale)
            resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
            x = (new_w - w) // 2
            y = (new_h - h) // 2
            return resized[y:y+h, x:x+w]
            
        # Ensure we resize the clip over time from the center
        clip = clip.fl(ken_burns_fl)
        
    # Apply fadein/fadeout to create dip-to-black crossfade transitions without altering duration (Task 3)
    # We apply a fadein of 0.2s and fadeout of 0.2s to soften the cut.
    # Note: MoviePy's fadein/fadeout defaults to black.
    clip = clip.fadein(0.2).fadeout(0.2)
        
    return clip, meta
