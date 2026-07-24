import os
import json
import time
import subprocess
from enum import Enum

from .process_utils import run_process_with_timeout

class DownloadMode(Enum):
    AUTO = "AUTO"
    FAST_PARTIAL = "FAST_PARTIAL"
    FULL_SOURCE = "FULL_SOURCE"

def should_retry(reason: str) -> bool:
    """Checks if the error is temporary."""
    reason = reason.lower()
    if "timeout" in reason:
        return True
    if "http error 429" in reason or "http error 5" in reason:
        return True
    return False

def _retry_runner(cmd: list, timeout: float, max_retries: int = 2) -> dict:
    """Runs a command with exponential backoff for temporary errors."""
    delays = [2, 5]
    
    for attempt in range(max_retries + 1):
        res = run_process_with_timeout(cmd, timeout)
        
        if res["success"]:
            return res
            
        if not should_retry(res["reason"]):
            # Fatal error, do not retry
            break
            
        if attempt < max_retries:
            time.sleep(delays[attempt])
            
    return res

def fetch_metadata(url: str, output_path: str, timeout: float = 20.0) -> dict:
    """Fetches video metadata and saves to cache."""
    cmd = [
        "yt-dlp",
        "--dump-single-json",
        "--no-playlist",
        url
    ]
    
    res = _retry_runner(cmd, timeout)
    if res["success"]:
        # Command success but we didn't capture stdout in run_process_with_timeout to avoid complexity.
        # Let's run it directly for metadata with subprocess since it's just a quick JSON dump.
        pass
        
    # Re-run natively with subprocess to capture stdout for metadata
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        if proc.returncode == 0:
            data = json.loads(proc.stdout.decode("utf-8"))
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f)
            return {"success": True, "data": data}
            
        else:
            stderr = proc.stderr.decode("utf-8").lower()
            return {"success": False, "reason": stderr}
            
    except subprocess.TimeoutExpired:
        return {"success": False, "reason": "timeout"}
    except Exception as e:
        return {"success": False, "reason": str(e)}

def download_fast_partial(url: str, start: float, end: float, out_path: str, timeout: float = 45.0) -> dict:
    """
    Downloads only the required section using --download-sections.
    """
    # Clean partials
    for ext in [".part", ".ytdl"]:
        if os.path.exists(out_path + ext):
            try: os.remove(out_path + ext)
            except: pass
            
    # As requested: download_start = max(0, clip_start - 3)
    d_start = max(0.0, start - 3.0)
    d_end = end + 3.0
    
    cmd = [
        "yt-dlp",
        "--no-playlist",
        "--download-sections", f"*{d_start}-{d_end}",
        "-f", "bestvideo[height<=480][ext=mp4]/best[height<=480][ext=mp4]/bestvideo[height<=480]",
        "-o", out_path,
        url
    ]
    
    start_t = time.time()
    res = _retry_runner(cmd, timeout)
    elapsed = time.time() - start_t
    
    if not res["success"] or not os.path.exists(out_path):
        # Cleanup
        if os.path.exists(out_path):
            try: os.remove(out_path)
            except: pass
        return {"success": False, "reason": res["reason"], "elapsed": elapsed}
        
    return {"success": True, "elapsed": elapsed}

def download_full_source(url: str, out_path: str, timeout: float = 300.0) -> dict:
    """
    Downloads the full video (video only, max 480p).
    """
    cmd = [
        "yt-dlp",
        "--no-playlist",
        "-f", "bestvideo[height<=480][ext=mp4]/best[height<=480][ext=mp4]/bestvideo[height<=480]",
        "-o", out_path,
        url
    ]
    
    start_t = time.time()
    res = _retry_runner(cmd, timeout)
    elapsed = time.time() - start_t
    
    if not res["success"] or not os.path.exists(out_path):
        return {"success": False, "reason": res["reason"], "elapsed": elapsed}
        
    return {"success": True, "elapsed": elapsed}

def slice_local_video(source_path: str, start: float, duration: float, out_path: str, timeout: float = 60.0) -> dict:
    """
    Uses ffmpeg to extract and re-encode exactly the required section.
    """
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start),
        "-i", source_path,
        "-t", str(duration),
        "-an",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        out_path
    ]
    
    start_t = time.time()
    res = run_process_with_timeout(cmd, timeout)
    elapsed = time.time() - start_t
    
    if not res["success"] or not os.path.exists(out_path):
        return {"success": False, "reason": res["reason"], "elapsed": elapsed}
        
    return {"success": True, "elapsed": elapsed}
