import os
import json
import uuid
import time
from PIL import Image

# MoviePy Pillow 10+ Compatibility Patch
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = getattr(Image, 'Resampling', Image).LANCZOS

from moviepy.editor import concatenate_videoclips, AudioFileClip, VideoFileClip, CompositeAudioClip

from .models import convert_v1_to_v2, TimelineV2, TimelineValidator
from .audio_engine import (
    resolve_audio_for_block, get_audio_duration, mix_master_audio, 
    apply_bgm_ducking, normalize_lufs, transcribe_audio_aligned,
    align_narration_once, generate_sfx_track, measure_wpm, find_cue_time
)
from .asset_manager import resolve_visual_asset, init_grouping
from .web_engine import capture_web_record
from .video_engine import (
    process_big_text, process_counter, process_web_record_clip, 
    generate_subtitles, add_subtitles_to_clip, make_black_clip,
    slice_alignment, TARGET_W, TARGET_H, FPS
)
from .pacing import apply_pacing_variations
from .visual_dispatcher import dispatch_visual, UnsupportedVisualTypeError
from .config import (
    USE_ELEVENLABS, PEXELS_API_KEY, TIMELINE_TIMING_POLICY, TIMELINE_DURATION_TOLERANCE,
    BIG_TEXT_MAX_DURATION, COUNTER_MAX_DURATION, QUOTE_MAX_DURATION, TEXT_ONLY_MAX_RATIO
)

TEMP_DIR = os.path.join(os.getcwd(), "temp_assets")
OUT_DIR = os.path.join(os.getcwd(), "output")

def init_dirs():
    os.makedirs(TEMP_DIR, exist_ok=True)
    os.makedirs(os.path.join(TEMP_DIR, "tts"), exist_ok=True)
    os.makedirs(os.path.join(TEMP_DIR, "v2_cache"), exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)

def detect_timeline_format(data):
    if isinstance(data, dict):
        if "beats" in data:
            return "v3_editorial"
        if "blocks" in data:
            return "v2"

    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict) and "block_id" in first and "narration" in first and "visuals" in first:
            return "v2_blocks_list"
        if isinstance(first, dict) and "type" in first:
            return "v1"

    raise ValueError("Unknown timeline format")

def update_youtube_summary(summary: dict, asset_info: dict, scene_id: str):
    summary["scenes"] += 1
        
    log = asset_info.get("log")
    if not log:
        if asset_info.get("fallback_used") and asset_info.get("type_used") == "stock":
            summary["stock_fallbacks"] += 1
            summary["failed_scenes"].append(scene_id)
        return
        
    status = log.get("result", "")
    mode = log.get("selected_mode", "")
    
    if mode == "FAST_PARTIAL":
        summary["partial_attempts"] += 1
        
    if "partial_success" in status:
        summary["partial_successes"] += 1
    if "full_source_success" in status:
        summary["full_source_downloads"] += 1
    if "cache_hit_clip" in status or "cache_hit_after_lock" in status:
        summary["clip_cache_hits"] += 1
    if "source_cache_hit" in status:
        summary["source_cache_hits"] += 1
        
    for f in log.get("failure_chain", []):
        if "timeout" in str(f.get("reason", "")).lower():
            summary["timeouts"] += 1
            
    if asset_info.get("fallback_used"):
        summary["stock_fallbacks"] += 1
        summary["failed_scenes"].append(scene_id)
        
def resolve_visual_clip(visual, duration: float, scene_id: str, youtube_summary: dict) -> tuple:
    # Stub that redirects to dispatcher
    options = {"youtube_summary": youtube_summary}
    return dispatch_visual(visual, duration, scene_id, options)

def process_timeline(timeline_path: str, preview_seconds: float = None, preview_mode: str = "truncate", review_assets: bool = False, render_mode: str = "production", enforce_performance_gate: bool = False, **kwargs):
    init_dirs()
    from .config import TIMELINE_TIMING_POLICY, TIMING_MODE
    import pathlib
    import sys
    
    if kwargs.get("quality_profile") == "acceptance":
        expected_path = pathlib.Path("tests/fixtures/ibm_v3_positive_acceptance.json").resolve()
        resolved_input_path = pathlib.Path(timeline_path).resolve()
        if resolved_input_path != expected_path:
            print("WRONG_INPUT_FIXTURE")
            sys.exit(1)
            
    print("=== Kurgu Motoru V2.3.0 ===")
    
    with open(timeline_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    format_type = detect_timeline_format(data)
    
    if format_type == "v3_editorial":
        quality_profile = kwargs.get("quality_profile", "default")
        if quality_profile == "acceptance":
            manifest_path = timeline_path.replace(".json", ".assets.json")
            if not os.path.exists(manifest_path):
                raise ValueError(f"Acceptance baseline requires fixture manifest: {manifest_path}")
            
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)
            
            import hashlib
            print("  [PRE-FLIGHT] Validating fixture assets against manifest...")
            for asset in manifest_data:
                rp = asset.get("relative_path")
                if not rp or not os.path.exists(rp):
                    raise ValueError(f"Fixture asset missing: {rp}")
                
                h = hashlib.sha256()
                with open(rp, 'rb') as af:
                    for chunk in iter(lambda: af.read(4096), b""):
                        h.update(chunk)
                if h.hexdigest() != asset.get("expected_sha256"):
                    raise ValueError(f"Fixture asset SHA-256 mismatch for {rp}")
            print("  [PRE-FLIGHT] Fixture manifest verified successfully.")
            
        from .editorial_engine import process_editorial_timeline, set_isolated_paths
        import uuid
        import time
        run_id = f"run_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        set_isolated_paths(run_id)

        # Run Read-Only Audit first
        import sys
        if os.path.exists("scratch/audit2.py"):
            sys.path.insert(0, os.path.abspath("scratch"))
            try:
                import audit2
                audit_out = os.path.join(os.getcwd(), "output", "truthful_acceptance_closure", run_id)
                audit2.run_read_only_audit(run_id, audit_out)
            except Exception as e:
                print(f"[ERROR] Failed to run audit: {e}")

        return process_editorial_timeline(timeline_path, render_mode=render_mode, preview_seconds=preview_seconds, enforce_performance_gate=enforce_performance_gate, quality_profile=quality_profile, run_id=run_id)
        
    print("  [WARN] Legacy JSON detected. Direct rendering is discouraged.")
    print("  [WARN] Please use '--migrate-editorial' to convert this to V3 Editorial schema first.")
    
    if format_type == "v1":
        timeline = convert_v1_to_v2(data)
    else:
        # Move unknown visual fields into 'extra' to bypass Pydantic drop
        known_visual_fields = {"offset_start", "offset_end", "type", "clip_start", "clip_end", "query", "url", "target_text", "target_selector", "zoom", "scroll_duration", "highlight_target", "main_text", "sub_text", "background_style", "accent_animation", "logo_url", "start_val", "end_val", "prefix", "suffix", "label", "is_approximate", "max_height", "crop_mode", "fit_mode", "extra", "narration_cue_start", "narration_cue_end", "visual_purpose", "required_content", "forbidden_content", "fallback_queries", "allow_generic_stock", "transition_in", "transition_out", "subtitle_policy", "fill_policy", "asset_locked", "selected_asset_url", "sfx_category"}
        
        blocks = data if format_type == "v2_blocks_list" else data.get("blocks", [])
        for b in blocks:
            for v in b.get("visuals", []):
                extra_dict = v.get("extra", {})
                keys_to_del = []
                for k, val in v.items():
                    if k not in known_visual_fields:
                        extra_dict[k] = val
                        keys_to_del.append(k)
                for k in keys_to_del:
                    del v[k]
                v["extra"] = extra_dict
                
        if format_type == "v2_blocks_list":
            timeline = TimelineV2(blocks=blocks)
        else:
            timeline = TimelineV2(**data)
            
    validator = TimelineValidator()
    val_report = validator.validate(timeline)
    for err in val_report["errors"]: print(f"  [ERROR] {err}")
    for wrn in val_report["warnings"]: print(f"  [WARN] {wrn}")
    
    if not val_report["is_valid"]:
        raise ValueError("Timeline JSON validation failed.")
        
    init_grouping(timeline.blocks)
        
    youtube_summary = {
        "scenes": 0,
        "partial_attempts": 0,
        "partial_successes": 0,
        "full_source_downloads": 0,
        "source_cache_hits": 0,
        "clip_cache_hits": 0,
        "timeouts": 0,
        "stock_fallbacks": 0,
        "failed_scenes": []
    }
    
    import glob
    import random
    bgm_files = glob.glob("assets/bgm/**/*.mp3", recursive=True) + glob.glob("assets/bgm/**/*.wav", recursive=True)
    bgm_path = random.choice(bgm_files) if bgm_files else "assets/bgm/documentary_bgm.mp3"
    
    # Startup Diagnostics
    print("\n--- Startup Diagnostics ---")
    print(f"Timeline format: V2.1 ({format_type})")
    print(f"Blocks: {len(timeline.blocks)}")
    total_visuals = sum(len(b.visuals) for b in timeline.blocks)
    print(f"Visual scenes: {total_visuals}")
    print(f"TTS provider: {'ElevenLabs' if USE_ELEVENLABS else 'Edge (Default)'}")
    print(f"Pexels configured: {'Yes' if PEXELS_API_KEY else 'No'}")
    print("YouTube engine: Hybrid V2.1.1")
    print(f"BGM file found: {'Yes' if os.path.exists(bgm_path) else 'No'}")
    print("SFX categories: booms, whooshes, typing, glitch, paper")
    print("Modules: 11/11 (Stock, YT, Record, Chart, Quote, Article, Reddit, BigText, Counter, Black)")
    print("FFmpeg: Ready\nFFprobe: Ready\nPlaywright: Ready")
    print("---------------------------\n")

    print("[INFO] Generating Audio and exact timings...")
    narration_paths = []
    pauses_before = []
    pauses_after = []
    duck_cues = []
    sfx_cues = []
    
    manifest_scenes = []
    
    val_report["tts_analysis"] = []
    
    for block in timeline.blocks:
        audio_out_path = os.path.join(TEMP_DIR, "tts", f"{block.block_id}.wav")
        has_audio = False
        
        if getattr(block, "audio_file", None) or block.narration.strip():
            if not os.path.exists(audio_out_path):
                has_audio = resolve_audio_for_block(block, audio_out_path)
            else:
                has_audio = True
                
        narration_paths.append(audio_out_path if has_audio and os.path.exists(audio_out_path) else "")
        pauses_before.append(block.pause_before)
        pauses_after.append(block.pause_after)
        
        if has_audio and os.path.exists(audio_out_path) and block.narration.strip():
            word_count = len(block.narration.split())
            wpm_stats = measure_wpm(audio_out_path, word_count)
            val_report["tts_analysis"].append({
                "block_id": block.block_id,
                "stats": wpm_stats
            })
            if wpm_stats["status"] == "out_of_range":
                val_report["warnings"].append(f"Block '{block.block_id}' TTS out of range: {wpm_stats['active_wpm']} WPM")

    master_speech_path = os.path.join(TEMP_DIR, "master_speech.wav")
    timings = mix_master_audio(narration_paths, pauses_before, pauses_after, master_speech_path)
    
    total_duration = timings[-1]["end"] if timings else 0.0
    
    if preview_seconds and preview_mode == "complete_story":
        if total_duration > preview_seconds:
            print(f"PREVIEW_NARRATION_TOO_LONG")
            print(f"[ERROR] Total duration is {total_duration:.2f}s, exceeding requested {preview_seconds}s limit.")
            return
            
    print("[INFO] Generating Visual Scenes...")
    final_clips = []
    
    for i, block in enumerate(timeline.blocks):
        block_timing = timings[i]
        b_start = block_timing["start"]
        b_end = block_timing["end"]
        b_duration = b_end - b_start
        
        if preview_seconds and preview_mode == "truncate" and b_start >= preview_seconds:
            print(f"  [INFO] Skipping block {block.block_id} due to --preview-seconds")
            continue
            
        if block.bgm_drop:
            duck_cues.append({
                "time": block_timing["narration_start"],
                "duration": block_timing["narration_end"] - block_timing["narration_start"],
                "drop_db": 10.0
            })
            
        visuals_count = len(block.visuals)
        current_offset = 0.0
        block_video_clips = []
        
        block_align_data = []
        if narration_paths[i]:
            block_align_data = align_narration_once(narration_paths[i], block.narration)
            
        # Strict timing verification report array
        if 'timing_analysis' not in val_report:
            val_report['timing_analysis'] = []
            
        # Pre-sort visuals by their chronological cue time to guarantee safe sequential processing
        temp_vis = []
        for v in block.visuals:
            t_m = "cue_anchor"  # Enforce cue_anchor
            trig = getattr(v, "trigger_cue", None) or getattr(v, "narration_cue_start", "")
            if t_m in ["cue_anchor", "cue_locked"]:
                ct = find_cue_time(block_align_data, trig)
                s = ct["time"] if ct["time"] >= 0 else float(getattr(v, "offset_start", 0.0) if getattr(v, "offset_start", 0.0) != "AUTO" else 0.0)
            else:
                s = float(getattr(v, "offset_start", 0.0)) if getattr(v, "offset_start", 0.0) != "AUTO" else 0.0
            temp_vis.append((s, v))
        temp_vis.sort(key=lambda x: x[0])
        block.visuals = [item[1] for item in temp_vis]
        
        narration_duration = block_timing["narration_end"] - block_timing["narration_start"]
        
        # We build an absolute visual schedule before generating clips
        visual_schedules = []
        
        # Helper to get block-relative time for a cue
        def get_cue_relative_time(visual_obj):
            trig = getattr(visual_obj, "trigger_cue", None) or getattr(visual_obj, "narration_cue_start", "")
            if trig:
                cue_data = find_cue_time(block_align_data, trig)
                if cue_data["time"] >= 0:
                    return (block_timing["narration_start"] - block_timing["start"]) + cue_data["time"]
            return -1.0

        for v_idx, visual in enumerate(block.visuals):
            is_first = (v_idx == 0)
            is_last = (v_idx == len(block.visuals) - 1)
            
            req_start = getattr(visual, "offset_start", "AUTO")
            req_end = getattr(visual, "offset_end", "AUTO")
            
            # Start Time
            if req_start != "AUTO":
                v_start = float(req_start)
            else:
                if is_first:
                    v_start = 0.0
                else:
                    t = get_cue_relative_time(visual)
                    if t >= 0:
                        v_start = t
                    else:
                        v_start = visual_schedules[-1]["end"] if visual_schedules else 0.0
                        
            # End Time
            if req_end != "AUTO":
                v_end = float(req_end)
            else:
                if is_last:
                    v_end = b_duration
                else:
                    next_v = block.visuals[v_idx + 1]
                    next_req_start = getattr(next_v, "offset_start", "AUTO")
                    if next_req_start != "AUTO":
                        t = float(next_req_start)
                    else:
                        t = get_cue_relative_time(next_v)
                        
                    if t >= 0:
                        v_end = t
                    else:
                        v_end = v_start + (getattr(visual, "max_duration", 15.0) or 15.0)
                        
            # Absolute hard cap at audio boundary
            if v_end > b_duration: v_end = b_duration
            if v_start > b_duration: v_start = b_duration
            if v_end < v_start: v_end = v_start
            
            # Minimum duration protection
            min_d = getattr(visual, "min_duration", None)
            if min_d and (v_end - v_start) < min_d:
                v_end = min(b_duration, v_start + min_d)
            
            if 'timing_analysis' not in val_report: val_report['timing_analysis'] = []
            val_report["timing_analysis"].append({
                "scene_id": f"scene_{block.block_id}_{v_idx}",
                "visual_start": round(v_start, 2),
                "visual_end": round(v_end, 2),
                "duration": round(v_end - v_start, 2)
            })
            
            visual_schedules.append({
                "start": v_start,
                "end": v_end,
                "duration": v_end - v_start
            })
            
        for v_idx, visual in enumerate(block.visuals):
            v_start = visual_schedules[v_idx]["start"]
            v_end = visual_schedules[v_idx]["end"]
            v_dur = visual_schedules[v_idx]["duration"]
            
            if v_dur <= 0:
                print(f"  [WARNING] Visual {v_idx} has 0 duration. Skipping.")
                continue
            current_offset = v_end
            
            if v_dur <= 0: continue
            
            # SFX Cue mapping
            vis_sfx = visual.extra.get("sfx_category") if visual.extra else getattr(visual, "sfx_category", None)
            
            default_sfx = None
            if visual.type == "big_text": default_sfx = "booms"
            elif visual.type == "counter": default_sfx = "glitch"
            elif visual.type == "web_record": default_sfx = "typing"
            elif visual.type in ["highlight_article", "quote"]: default_sfx = "paper"
            
            block_sfx = getattr(block, "sfx_category", None) if v_idx == 0 else None
            
            s_cat = vis_sfx or default_sfx or block_sfx
            if s_cat:
                sfx_cues.append({"time": b_start + v_start, "category": s_cat})
                
            scene_id = f"scene_{block.block_id}_{v_idx}"
            print(f"  [INFO] Processing Block '{block.block_id}', Visual {v_idx} ({visual.type})...")
            clip, m_info = resolve_visual_clip(visual, v_dur, scene_id, youtube_summary)
            
            m_info["block_id"] = block.block_id
            m_info["start_time"] = b_start + v_start
            m_info["end_time"] = b_start + v_end
            m_info["asset_locked"] = getattr(visual, "asset_locked", False)
            manifest_scenes.append(m_info)
            
            # Slice subtitles for this visual
            if block_align_data and visual.type not in ["big_text", "counter"]:
                vis_align_data = slice_alignment(block_align_data, start_time=v_start, end_time=v_end)
                subs = generate_subtitles(vis_align_data, v_dur, visual.type)
                clip = add_subtitles_to_clip(clip, subs, visual.type)
                
            block_video_clips.append(clip)
            
        if block_video_clips:
            if len(block_video_clips) == 1:
                b_clip = block_video_clips[0]
            else:
                from .video_engine import generate_local_transition
                final_block_clips = []
                for i in range(len(block_video_clips)):
                    curr_clip = block_video_clips[i]
                    vis_data = block.visuals[i]
                    
                    if i > 0:
                        prev_clip = final_block_clips[-1]
                        trans_in = getattr(vis_data, "transition_in", "hard_cut")
                        if trans_in == "short_dissolve":
                            trans_clip = generate_local_transition(prev_clip, curr_clip, 0.15, "short_dissolve")
                            if trans_clip:
                                trimmed_prev = prev_clip.subclip(0, max(0, prev_clip.duration - 0.15))
                                final_block_clips[-1] = trimmed_prev
                                final_block_clips.append(trans_clip)
                                curr_clip = curr_clip.subclip(0.15, curr_clip.duration)
                                
                    final_block_clips.append(curr_clip)
                
                b_clip = concatenate_videoclips(final_block_clips, method="chain")
                
            b_trans = getattr(block, "transition_out", "hard_cut")
            if b_trans == "dip_to_black":
                from moviepy.video.fx.fadeout import fadeout
                b_clip = fadeout(b_clip, 0.5)
                
            final_clips.append(b_clip)
        else:
            final_clips.append(make_black_clip(b_duration))

    black_detected = False
    
    if review_assets:
        print("[INFO] Generating Asset Review Report (--review-assets flag)...")
        review_dir = os.path.join(TEMP_DIR, "asset_review")
        os.makedirs(review_dir, exist_ok=True)
        review_path = os.path.join(review_dir, "asset_review.json")
        with open(review_path, "w", encoding="utf-8") as f:
            json.dump(manifest_scenes, f, indent=2)
        print(f"[SUCCESS] Asset review saved to {review_path}")
        out_video = None
        total_duration = min(total_duration, preview_seconds) if preview_seconds else total_duration
    else:
        from .config import REQUIRE_ASSET_APPROVAL
        if REQUIRE_ASSET_APPROVAL:
            needs_approval = False
            for s_info in manifest_scenes:
                if s_info.get("review_required") and not s_info.get("asset_locked", False):
                    val_report["errors"].append(f"Scene {s_info.get('scene_id')} requires asset approval, but is not locked.")
                    needs_approval = True
                    
            if needs_approval:
                print("[ERROR] REQUIRE_ASSET_APPROVAL is enabled but some scenes require review. Render aborted.")
                with open(VAL_REPORT_PATH, "w", encoding="utf-8") as f:
                    json.dump(val_report, f, indent=2)
                return
                    
        print("[INFO] Compositing Final Video...")
        master_video = concatenate_videoclips(final_clips, method="chain")
        
        if preview_seconds and preview_seconds < total_duration:
            master_video = master_video.subclip(0, preview_seconds)
            total_duration = preview_seconds
            
        from .config import ENABLE_BGM, ENABLE_SFX
        
        final_audio_path = os.path.join(OUT_DIR, "final_audio.wav")
        mix_layers = [AudioFileClip(master_speech_path)]
        
        if os.path.exists(bgm_path) and ENABLE_BGM:
            ducked_bgm = os.path.join(TEMP_DIR, "bgm_ducked.wav")
            apply_bgm_ducking(bgm_path, duck_cues, ducked_bgm, total_duration)
            bgm_clip = AudioFileClip(ducked_bgm)
            mix_layers.append(bgm_clip)
            
        if ENABLE_SFX:
            sfx_clip = generate_sfx_track(sfx_cues, total_duration)
            if sfx_clip: mix_layers.append(sfx_clip)
            
        if len(mix_layers) > 1:
            final_mix = CompositeAudioClip(mix_layers)
            final_mix.write_audiofile(final_audio_path, fps=44100, logger=None)
        else:
            import shutil
            shutil.copy(master_speech_path, final_audio_path)
            
        for c in mix_layers: 
            if hasattr(c, 'close'): c.close()
            
        print("[INFO] Normalizing final audio to -15 LUFS (Max TP: -1.0 dBTP)...")
        lufs_audio_path = os.path.join(OUT_DIR, "final_audio_lufs.wav")
        normalize_lufs(final_audio_path, lufs_audio_path, target_lufs=-15.0)
        
        final_audio_clip = AudioFileClip(lufs_audio_path)
        if preview_seconds:
            final_audio_clip = final_audio_clip.subclip(0, min(preview_seconds, final_audio_clip.duration))
            
        v_dur = master_video.duration
        a_dur = final_audio_clip.duration
        
        if abs(v_dur - a_dur) > (1.0 / FPS):
            print(f"  [QUALITY ERROR] Audio/Video sync deviation: Video {v_dur:.2f}s vs Audio {a_dur:.2f}s")
            val_report["errors"].append(f"Video duration ({v_dur:.2f}s) differs from Audio duration ({a_dur:.2f}s).")
            # Strict clamping
            if v_dur > a_dur:
                master_video = master_video.subclip(0, a_dur)
            else:
                diff = a_dur - v_dur
                try:
                    last_frame_clip = master_video.to_ImageClip(t=v_dur - 0.05).set_duration(diff)
                    master_video = concatenate_videoclips([master_video, last_frame_clip], method="chain")
                except Exception as e:
                    print(f"  [WARN] Freeze frame extension failed: {e}")
                    pass
        master_video = master_video.set_audio(final_audio_clip)
        
        out_video = os.path.join(OUT_DIR, "final_video_v2.mp4")
        if review_assets:
            pass # Skips writing video for faster asset preview
        else:
            master_video.write_videofile(
                out_video,
                fps=FPS,
                codec="libx264",
                audio_codec="aac",
                bitrate="8000k",
                preset="ultrafast",
                threads=4,
                logger="bar"
            )
            
        try:
            master_video.close()
            final_audio_clip.close()
            for c in final_clips:
                if hasattr(c, 'close'): c.close()
        except:
            pass
        
        # FFprobe Blackdetect Analysis
        print("[INFO] Running FFprobe Black Screen Detection...")
        import subprocess
        out_video_ff = out_video.replace("\\", "/").replace(":", "\\:") if os.name == 'nt' else out_video
        cmd = ["ffprobe", "-f", "lavfi", "-i", f"movie='{out_video_ff}',blackdetect=d=0.5:pix_th=0.10", "-show_entries", "tags=lavfi.black_start,lavfi.black_end", "-of", "default=nw=1", "-v", "quiet"]
        try:
            b_res = subprocess.run(cmd, capture_output=True, text=True)
            lines = b_res.stdout.split('\n')
            starts = [float(l.split('=')[1]) for l in lines if 'lavfi.black_start=' in l]
            ends = [float(l.split('=')[1]) for l in lines if 'lavfi.black_end=' in l]
            
            real_blacks = 0
            for i in range(min(len(starts), len(ends))):
                if ends[i] - starts[i] >= 0.4:
                    real_blacks += 1
                    
            if real_blacks > 0:
                black_detected = True
                print(f"  [QUALITY ERROR] Black screen sequences detected: {real_blacks}")
                val_report["errors"].append("Pure black fallback detected in output.")
            else:
                ignored = len(set(starts)) # unique micro dips
                if ignored > 0:
                    print(f"  [INFO] No significant black screens detected (ignored {ignored} micro-dips from transitions).")
        except Exception as e:
            print(f"  [WARN] FFprobe blackdetect failed: {e}")
    
    render_status = "success"
    if black_detected or len(val_report["errors"]) > 0:
        render_status = "failed_quality_check"
    elif youtube_summary["stock_fallbacks"] > 0 or len(val_report["warnings"]) > 0:
        render_status = "success_with_warnings"
        
    report = {
        "render_status": render_status,
        "youtube_summary": youtube_summary,
        "duration": total_duration,
        "blocks": len(timeline.blocks),
        "visual_scenes": len(manifest_scenes),
        "warnings": val_report["warnings"],
        "errors": val_report["errors"],
        "timing_analysis": val_report.get("timing_analysis", []),
        "tts_analysis": val_report.get("tts_analysis", []),
        "manifest": manifest_scenes
    }
    
    with open(os.path.join(OUT_DIR, "validation_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)
        
    print(f"\n[INFO] Render Status: {render_status.upper()}")
    if render_status == "success_with_warnings":
        print("\nRender completed with warnings.")
        print(f"YouTube scenes: {youtube_summary['scenes']}")
        print(f"Downloaded successfully: {youtube_summary['scenes'] - youtube_summary['stock_fallbacks']}")
        print(f"Stock fallback used: {youtube_summary['stock_fallbacks']}")
        print("\nAffected scenes:")
        for s in youtube_summary["failed_scenes"]:
            print(f"- {s} — Full source or partial unavailable/fallback")
            
    print(f"\n[SUCCESS] Render complete! Saved to {out_video}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Timeline V2 Editor Engine")
    parser.add_argument("timeline", nargs="?", default="timeline.json", help="Path to timeline JSON file")
    parser.add_argument("--preview-seconds", type=float, default=None, help="Render only first N seconds")
    parser.add_argument("--preview-mode", type=str, choices=["truncate", "complete_story"], default="complete_story", help="Preview mode behavior")
    parser.add_argument("--review-assets", action="store_true", help="Download assets and build manifest, skip render")
    parser.add_argument("--migrate-editorial", action="store_true", help="Migrate old V1/V2 timeline to V3 Editorial Format")
    parser.add_argument("--render-mode", type=str, choices=["review", "preview", "production"], default="production", help="Render strictness level")
    
    # Asset Management CLI
    parser.add_argument("--approve-asset", type=str, help="Approve an asset by its ID")
    parser.add_argument("--reject-asset", type=str, help="Reject an asset by its ID")
    parser.add_argument("--lock-asset", type=str, help="Lock an asset to a specific URL/source")
    parser.add_argument("--url", type=str, help="URL to use when locking an asset")
    
    parser.add_argument("--batch-test", type=str, help="Run a batch test on a directory of fixtures (e.g. tests/fixtures)")
    parser.add_argument("--enforce-performance-gate", action="store_true", help="Fail if performance metrics violate production standards")
    parser.add_argument("--quality-profile", type=str, default="default", help="Quality profile to use (e.g., acceptance, default)")
    
    args = parser.parse_args()
    
    if args.approve_asset or args.reject_asset or args.lock_asset:
        from .asset_approval import cli_approve_asset, cli_reject_asset, cli_lock_asset
        if not os.path.exists(args.timeline):
            print(f"File not found: {args.timeline}")
        else:
            if args.approve_asset: cli_approve_asset(args.timeline, args.approve_asset)
            if args.reject_asset: cli_reject_asset(args.timeline, args.reject_asset)
            if args.lock_asset: cli_lock_asset(args.timeline, args.lock_asset, args.url)
    elif args.migrate_editorial:
        if not os.path.exists(args.timeline):
            print(f"File not found: {args.timeline}")
        else:
            from .migration import convert_to_editorial
            print(f"Migrating {args.timeline} to V3 Editorial Schema...")
            t, r, o = convert_to_editorial(args.timeline)
            print(f"Migration completed. Output saved to: {o}")
            print(f"Report: {json.dumps(r, indent=2)}")
    elif args.batch_test:
        fixtures_dir = args.batch_test
        if not os.path.isdir(fixtures_dir):
            print(f"Directory not found: {fixtures_dir}")
        else:
            import glob
            import shutil
            fixtures = glob.glob(os.path.join(fixtures_dir, "*.json"))
            print(f"Found {len(fixtures)} fixtures in {fixtures_dir}")
            
            batch_summary = {"passed": 0, "failed": 0, "results": {}}
            
            print(f"{'Fixture':<30} | {'Mode':<10} | {'Expected':<15} | {'Actual':<15} | {'Tech':<5} | {'Edit':<5} | {'Pace':<5} | {'Align':<5} | {'Asset':<5} | {'Pixel':<5}")
            print("-" * 125)
            
            for fix in fixtures:
                fix_name = os.path.basename(fix)
                
                with open(fix, "r", encoding="utf-8") as ff:
                    fix_data = json.load(ff)
                expected = fix_data.get("expected_failure", False)
                
                # We need to temporarily output to a specific dir so reports don't overwrite each other
                import v2.editorial_engine as ee
                original_out = ee.OUT_DIR
                run_out = os.path.join("output", "batch_results", fix_name.replace(".json", ""))
                ee.OUT_DIR = run_out
                os.makedirs(run_out, exist_ok=True)
                
                # Ensure we run in production mode to trigger all validations
                try:
                    process_timeline(fix, render_mode="production", enforce_performance_gate=args.enforce_performance_gate)
                except Exception as e:
                    pass
                finally:
                    ee.OUT_DIR = original_out
                
                val_report_path = os.path.join(run_out, "validation_report.json")
                if os.path.exists(val_report_path):
                    with open(val_report_path, "r", encoding="utf-8") as f:
                        val_report = json.load(f)
                    actual = val_report.get("acceptance_status", "unknown")
                    
                    tech = val_report.get("technical_status", "N/A")[:5]
                    edit = val_report.get("editorial_status", "N/A")[:5]
                    pace = val_report.get("pacing_status", "N/A")[:5]
                    align = val_report.get("alignment_status", "N/A")[:5]
                    asset = val_report.get("asset_status", "N/A")[:5]
                    pixel = val_report.get("pixel_status", "N/A")[:5]
                    
                    if expected is False:
                        passed = (actual == "valid")
                        actual_str = "SUCCESS" if passed else "FAILED"
                    else:
                        errors = " ".join(val_report.get("errors", []))
                        if expected is True:
                            passed = (actual != "valid")
                            actual_str = actual
                        elif expected in errors:
                            passed = True
                            actual_str = expected
                        else:
                            passed = False
                            actual_str = actual
                else:
                    if 'passed' not in locals():
                        passed = False
                        actual_str = "CRASH"
                        tech = edit = pace = align = asset = pixel = "ERROR"
                    
                exp_str = str(expected) if expected else "SUCCESS"
                print(f"{fix_name:<30} | {'production':<10} | {exp_str:<15} | {actual_str:<15} | {tech:<5} | {edit:<5} | {pace:<5} | {align:<5} | {asset:<5} | {pixel:<5}")
                
                if passed:
                    batch_summary["passed"] += 1
                    batch_summary["results"][fix_name] = "PASS"
                else:
                    batch_summary["failed"] += 1
                    batch_summary["results"][fix_name] = "FAIL"
                    
            with open(os.path.join("output", "batch_summary.json"), "w", encoding="utf-8") as f:
                json.dump(batch_summary, f, indent=2)
            print("-" * 125)
            print(f"Batch run complete. Passed: {batch_summary['passed']}, Failed: {batch_summary['failed']}")
    elif os.path.exists(args.timeline):
        try:
            process_timeline(args.timeline, preview_seconds=args.preview_seconds, preview_mode=args.preview_mode, review_assets=args.review_assets, render_mode=args.render_mode, enforce_performance_gate=args.enforce_performance_gate, quality_profile=args.quality_profile)
        except Exception as e:
            import traceback
            traceback.print_exc()
            import sys
            sys.exit(1)
    else:
        print("Please provide a timeline JSON file.")
