import os
import time
import hashlib
import subprocess
from moviepy.editor import VideoFileClip, concatenate_videoclips
from .config import (
    ENABLE_DYNAMIC_PACING, STATIC_PACING_MODE, STATIC_PACING_MIN_DURATION,
    STATIC_PACING_PUNCH_SCALE, STATIC_PACING_ZOOM_SCALE, 
    STATIC_PACING_SPLIT_RATIO, STATIC_PACING_CACHE_DIR,
    YOUTUBE_PIPELINE_VERSION
)
from .ffprobe_validator import validate_video_file

class PacingMode:
    OFF = "off"
    PUNCH_IN = "punch_in"
    FFMPEG_ZOOM = "ffmpeg_zoom"
    AUTO = "auto"

def resolve_static_pacing_mode(configured_mode: str, duration: float, visual_type: str) -> str:
    if configured_mode != PacingMode.AUTO:
        return configured_mode
        
    if duration < STATIC_PACING_MIN_DURATION:
        return PacingMode.OFF
    if duration <= 8.0:
        return PacingMode.PUNCH_IN
    return PacingMode.FFMPEG_ZOOM

def is_static_source(source_path: str, visual) -> bool:
    if not source_path:
        return False
        
    ext = os.path.splitext(source_path.lower())[1]
    
    if ext in [".png", ".jpg", ".jpeg", ".webp"]:
        return True
        
    if visual.type in ["quote", "article", "highlight_article"]:
        return True
        
    if visual.type == "web_record" and ext in [".png", ".jpg", ".jpeg"]:
        return True
        
    return False

def create_fixed_zoom_crop(source_clip, scale: float, duration: float):
    # Sabit boyutlandirma, lambda (kare bazli) YASAK!
    w, h = source_clip.w, source_clip.h
    new_w, new_h = int(w * scale), int(h * scale)
    
    zoomed = source_clip.resize(newsize=(new_w, new_h))
    
    x_center = new_w / 2
    y_center = new_h / 2
    
    cropped = zoomed.crop(
        x_center=x_center, 
        y_center=y_center, 
        width=w, 
        height=h
    )
    return cropped.set_duration(duration)

def create_punch_in_clip(source_clip, duration: float, scale: float = 1.06, split_ratio: float = 0.5):
    first_duration = duration * split_ratio
    second_duration = duration - first_duration
    
    normal = source_clip.subclip(0, first_duration).set_duration(first_duration)
    zoomed = create_fixed_zoom_crop(source_clip, scale=scale, duration=second_duration)
    
    return concatenate_videoclips([normal, zoomed], method="compose")

def get_or_create_ffmpeg_zoom_clip(source_path: str, duration: float, zoom_scale: float, fps: int = 30) -> str:
    os.makedirs(STATIC_PACING_CACHE_DIR, exist_ok=True)
    
    if not os.path.exists(source_path):
        return None
        
    mod_time = os.path.getmtime(source_path)
    
    hash_str = f"{source_path}_{mod_time}_{duration}_1920x1080_{fps}_{zoom_scale}_{YOUTUBE_PIPELINE_VERSION}"
    hash_hex = hashlib.md5(hash_str.encode('utf-8')).hexdigest()[:8]
    
    out_name = f"{hash_hex}_{duration:.3f}_1920x1080_{fps}fps_zoom{int(zoom_scale*100)}_{YOUTUBE_PIPELINE_VERSION}.mp4"
    out_path = os.path.join(STATIC_PACING_CACHE_DIR, out_name)
    
    if os.path.exists(out_path):
        val = validate_video_file(out_path)
        if val["valid"] and abs(val["duration"] - duration) < 0.5:
            return out_path
        else:
            try: os.remove(out_path)
            except: pass
            
    frame_count = int(duration * fps)
    zoom_step = (zoom_scale - 1.0) / frame_count
    
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", source_path,
        "-vf", f"scale=2200:-1,zoompan=z='min(zoom+{zoom_step:.5f},{zoom_scale})':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frame_count}:s=1920x1080:fps={fps},format=yuv420p",
        "-t", str(duration),
        "-an",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-movflags", "+faststart",
        out_path
    ]
    
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
        
        if os.path.exists(out_path):
            val = validate_video_file(out_path)
            if val["valid"] and abs(val["duration"] - duration) < 0.5:
                return out_path
            try: os.remove(out_path)
            except: pass
    except Exception:
        try: os.remove(out_path)
        except: pass
        
    return None

def apply_pacing_variations(clip, visual, duration: float, source_path: str = None, scene_id: str = ""):
    manifest_log = {
        "eligible": False,
        "mode": "off",
        "cache_hit": False,
        "source_static": False,
        "processing_seconds": 0.0
    }
    
    if not ENABLE_DYNAMIC_PACING:
        return clip, manifest_log
        
    if visual.type in {"stock", "youtube", "chart", "counter", "big_text"}:
        return clip, manifest_log
        
    is_static = is_static_source(source_path, visual)
    manifest_log["source_static"] = is_static
    
    if not is_static:
        return clip, manifest_log
        
    manifest_log["eligible"] = True
    mode = resolve_static_pacing_mode(STATIC_PACING_MODE, duration, visual.type)
    manifest_log["mode"] = mode
    
    if mode == PacingMode.OFF:
        return clip, manifest_log
        
    start_t = time.time()
    print(f"  [PACING][{scene_id}] Static source detected")
    print(f"  [PACING][{scene_id}] Mode → {mode}")
    
    if mode == PacingMode.PUNCH_IN:
        paced_clip = create_punch_in_clip(clip, duration, STATIC_PACING_PUNCH_SCALE, STATIC_PACING_SPLIT_RATIO)
        manifest_log["processing_seconds"] = round(time.time() - start_t, 2)
        return paced_clip, manifest_log
        
    if mode == PacingMode.FFMPEG_ZOOM:
        paced_path = get_or_create_ffmpeg_zoom_clip(source_path, duration, STATIC_PACING_ZOOM_SCALE, fps=30)
        
        if paced_path:
            # Check if it was a cache hit based on creation time vs our start_t
            if os.path.getmtime(paced_path) < start_t:
                manifest_log["cache_hit"] = True
                print(f"  [PACING][{scene_id}] Cache hit")
            else:
                manifest_log["cache_hit"] = False
                
            manifest_log["processing_seconds"] = round(time.time() - start_t, 2)
            new_clip = VideoFileClip(paced_path, audio=False).subclip(0, duration)
            return new_clip, manifest_log
            
        print(f"  [PACING][{scene_id}] FFmpeg failed/timeout, falling back to PUNCH_IN")
        manifest_log["mode"] = "punch_in_fallback"
        paced_clip = create_punch_in_clip(clip, duration, STATIC_PACING_PUNCH_SCALE, STATIC_PACING_SPLIT_RATIO)
        manifest_log["processing_seconds"] = round(time.time() - start_t, 2)
        return paced_clip, manifest_log
        
    return clip, manifest_log
