import os
import time
import subprocess
import hashlib
import json
from dataclasses import dataclass
from typing import Optional

from .config import (
    VIDEO_NORMALIZATION_CACHE_DIR,
    VIDEO_NORMALIZATION_TIMEOUT,
    VIDEO_NORMALIZATION_PIPELINE_VERSION,
    VIDEO_NORMALIZATION_PRESET,
    VIDEO_NORMALIZATION_CRF
)

@dataclass
class NormalizedAssetResult:
    path: str
    cache_hit: bool
    fit_mode: str
    processing_seconds: float
    source_width: int
    source_height: int
    output_width: int
    output_height: int
    validation_passed: bool

def _get_file_hash(filepath: str) -> str:
    mtime = os.path.getmtime(filepath)
    raw = f"{filepath}_{mtime}"
    return hashlib.md5(raw.encode('utf-8')).hexdigest()[:8]

def _get_cache_path(fingerprint: str, start: float, duration: float, fit_mode: str, w: int, h: int, fps: int) -> str:
    os.makedirs(VIDEO_NORMALIZATION_CACHE_DIR, exist_ok=True)
    filename = f"{fingerprint}_{start:.3f}_{duration:.3f}_{fit_mode}_{w}x{h}_{fps}_crf{VIDEO_NORMALIZATION_CRF}_v{VIDEO_NORMALIZATION_PIPELINE_VERSION}.mp4"
    return os.path.join(VIDEO_NORMALIZATION_CACHE_DIR, filename)

def _validate_asset(filepath: str, expected_w: int, expected_h: int, expected_fps: int) -> bool:
    if not os.path.exists(filepath):
        return False
    try:
        cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,r_frame_rate,pix_fmt:format=duration",
            "-of", "json", filepath
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        data = json.loads(result.stdout)
        streams = data.get("streams", [])
        if not streams:
            return False
            
        stream = streams[0]
        w = int(stream.get("width", 0))
        h = int(stream.get("height", 0))
        pix_fmt = stream.get("pix_fmt", "")
        
        format_info = data.get("format", {})
        actual_duration = float(format_info.get("duration", 0.0))
        
        if w != expected_w or h != expected_h or pix_fmt != "yuv420p":
            return False
            
        # Optional: check if duration is reasonably close (e.g., within 1.0s difference for static loops or edge cases)
        # We don't enforce strict duration since validation is mostly for integrity. But > 0 is essential.
        if actual_duration < 0.1:
            return False
            
        return True
    except Exception:
        return False

def _get_source_info(filepath: str) -> tuple:
    try:
        cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "json", filepath
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        data = json.loads(result.stdout)
        streams = data.get("streams", [])
        if streams:
            return int(streams[0].get("width", 0)), int(streams[0].get("height", 0))
    except Exception:
        pass
    return 0, 0

def normalize_video_asset(
    source_path: str,
    duration: float,
    fit_mode: str,
    target_width: int,
    target_height: int,
    fps: int,
    scene_id: str,
    clip_start: float = 0.0,
    pacing_mode: str = "off"
) -> NormalizedAssetResult:
    start_time = time.time()
    
    sw, sh = _get_source_info(source_path)
    fingerprint = _get_file_hash(source_path)
    
    cache_fit = f"{fit_mode}_{pacing_mode}"
    out_path = _get_cache_path(fingerprint, clip_start, duration, cache_fit, target_width, target_height, fps)
    
    if _validate_asset(out_path, target_width, target_height, fps):
        print(f"[NORMALIZE][{scene_id}] Cache hit for {out_path}")
        return NormalizedAssetResult(
            path=out_path, cache_hit=True, fit_mode=fit_mode,
            processing_seconds=time.time() - start_time,
            source_width=sw, source_height=sh, output_width=target_width, output_height=target_height,
            validation_passed=True
        )
        
    print(f"[NORMALIZE][{scene_id}] Cache miss. Source: {sw}x{sh}. Fit: {fit_mode}. Started FFmpeg...")
    
    vf_filters = []
    
    if fit_mode == "cover":
        vf_filters.append(f"scale={target_width}:{target_height}:force_original_aspect_ratio=increase")
        vf_filters.append(f"crop={target_width}:{target_height}")
    elif fit_mode == "contain_blur":
        pass 
    elif fit_mode == "contain_frame":
        vf_filters.append(f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease")
        vf_filters.append(f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:black")
    elif fit_mode == "none":
        vf_filters.append(f"scale={target_width}:{target_height}")
    else:
        vf_filters.append(f"scale={target_width}:{target_height}:force_original_aspect_ratio=increase")
        vf_filters.append(f"crop={target_width}:{target_height}")
        
    cmd = ["ffmpeg", "-y"]
    
    if clip_start > 0:
        cmd.extend(["-ss", str(clip_start)])
    cmd.extend(["-t", str(duration)])
    cmd.extend(["-i", source_path])
    
    if fit_mode == "contain_blur":
        fc = (
            f"[0:v]scale={target_width}:{target_height}:force_original_aspect_ratio=increase,"
            f"crop={target_width}:{target_height},boxblur=15:1,"
            f"colorchannelmixer=r=0.4:g=0.4:b=0.4[bg];"
            f"[0:v]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2"
        )
        cmd.extend(["-filter_complex", fc])
    else:
        cmd.extend(["-vf", ",".join(vf_filters)])
        
    cmd.extend([
        "-r", str(fps),
        "-c:v", "libx264",
        "-preset", VIDEO_NORMALIZATION_PRESET,
        "-crf", VIDEO_NORMALIZATION_CRF,
        "-pix_fmt", "yuv420p",
        "-an",
        "-movflags", "+faststart",
        out_path
    ])
    
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=VIDEO_NORMALIZATION_TIMEOUT)
    except BaseException as e:
        if os.path.exists(out_path):
            try: os.remove(out_path)
            except: pass
        print(f"[NORMALIZE][{scene_id}] FFmpeg failed or interrupted: {e}")
        return NormalizedAssetResult(
            path="", cache_hit=False, fit_mode=fit_mode, processing_seconds=0.0,
            source_width=sw, source_height=sh, output_width=0, output_height=0, validation_passed=False
        )
        
    proc_time = time.time() - start_time
    is_valid = _validate_asset(out_path, target_width, target_height, fps)
    
    if not is_valid and os.path.exists(out_path):
        os.remove(out_path) 
        
    print(f"[NORMALIZE][{scene_id}] Completed in {proc_time:.2f}s. Validation: {is_valid}")
    
    return NormalizedAssetResult(
        path=out_path if is_valid else "", cache_hit=False, fit_mode=fit_mode,
        processing_seconds=proc_time, source_width=sw, source_height=sh,
        output_width=target_width, output_height=target_height, validation_passed=is_valid
    )

def normalize_static_asset(
    image_path: str,
    duration: float,
    fit_mode: str,
    target_width: int,
    target_height: int,
    fps: int,
    scene_id: str,
    pacing_mode: str = "off"
) -> NormalizedAssetResult:
    start_time = time.time()
    sw, sh = _get_source_info(image_path)
    fingerprint = _get_file_hash(image_path)
    
    cache_fit = f"static_{fit_mode}_{pacing_mode}"
    out_path = _get_cache_path(fingerprint, 0.0, duration, cache_fit, target_width, target_height, fps)
    
    if _validate_asset(out_path, target_width, target_height, fps):
        print(f"[NORMALIZE][{scene_id}] Cache hit for static asset {out_path}")
        return NormalizedAssetResult(
            path=out_path, cache_hit=True, fit_mode=fit_mode,
            processing_seconds=time.time() - start_time,
            source_width=sw, source_height=sh, output_width=target_width, output_height=target_height,
            validation_passed=True
        )
        
    print(f"[NORMALIZE][{scene_id}] Cache miss (static). Source: {sw}x{sh}. Started FFmpeg...")
    
    cmd = ["ffmpeg", "-y", "-loop", "1", "-t", str(duration), "-i", image_path]
    
    vf_filters = []
    if fit_mode == "cover":
        vf_filters.append(f"scale={target_width}:{target_height}:force_original_aspect_ratio=increase")
        vf_filters.append(f"crop={target_width}:{target_height}")
    elif fit_mode == "contain_frame":
        vf_filters.append(f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease")
        vf_filters.append(f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:black")
    else:
        vf_filters.append(f"scale={target_width}:{target_height}:force_original_aspect_ratio=increase")
        vf_filters.append(f"crop={target_width}:{target_height}")
        
    if pacing_mode == "fade_in":
        vf_filters.append("fade=t=in:st=0:d=0.2")
    elif pacing_mode == "wipe_right":
        # simple horizontal wipe opening over 0.8s
        # ffmpeg crop filter supports evaluating 't' (time in seconds)
        # Note: crop filter takes out_w:out_h:x:y
        # To wipe right, we want width to grow from 0 to in_w over 0.8s.
        vf_filters.append("crop='in_w*min(t/0.8,1)':in_h:0:0")
        # Then pad back to original width so it doesn't change video resolution dynamically
        vf_filters.append(f"pad={target_width}:{target_height}:0:0:black")
    elif pacing_mode == "zoom_in":
        # Slow zoom in, up to 1.15x
        vf_filters.append(f"zoompan=z='min(zoom+0.0015,1.15)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={target_width}x{target_height}")
    elif pacing_mode == "scroll_down":
        # A slow pan downwards
        vf_filters.append(f"zoompan=z='1.15':d=1:x='iw/2-(iw/zoom/2)':y='min(y+1,ih-ih/zoom)':s={target_width}x{target_height}")
        
    cmd.extend(["-vf", ",".join(vf_filters)])
    cmd.extend([
        "-r", str(fps), "-c:v", "libx264", "-preset", VIDEO_NORMALIZATION_PRESET,
        "-crf", VIDEO_NORMALIZATION_CRF, "-pix_fmt", "yuv420p", "-an",
        "-movflags", "+faststart", out_path
    ])
    
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=VIDEO_NORMALIZATION_TIMEOUT)
    except BaseException as e:
        if os.path.exists(out_path):
            try: os.remove(out_path)
            except: pass
        print(f"[NORMALIZE][{scene_id}] Static FFmpeg failed or interrupted: {e}")
        return NormalizedAssetResult(
            path="", cache_hit=False, fit_mode=fit_mode, processing_seconds=0.0,
            source_width=sw, source_height=sh, output_width=0, output_height=0, validation_passed=False
        )
        
    proc_time = time.time() - start_time
    is_valid = _validate_asset(out_path, target_width, target_height, fps)
    
    if not is_valid and os.path.exists(out_path):
        os.remove(out_path)
        
    print(f"[NORMALIZE][{scene_id}] Static completed in {proc_time:.2f}s. Validation: {is_valid}")
    
    return NormalizedAssetResult(
        path=out_path if is_valid else "", cache_hit=False, fit_mode=fit_mode,
        processing_seconds=proc_time, source_width=sw, source_height=sh,
        output_width=target_width, output_height=target_height, validation_passed=is_valid
    )
