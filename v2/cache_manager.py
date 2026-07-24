import os
import json
import datetime
from .config import YOUTUBE_PIPELINE_VERSION

CACHE_BASE = os.path.join(os.getcwd(), "cache")
META_DIR = os.path.join(CACHE_BASE, "metadata")
SOURCES_DIR = os.path.join(CACHE_BASE, "sources")
CLIPS_DIR = os.path.join(CACHE_BASE, "clips")
FAILURES_DIR = os.path.join(CACHE_BASE, "failures")
CORRUPT_DIR = os.path.join(CACHE_BASE, "corrupt")

def init_cache_dirs():
    for d in [CACHE_BASE, META_DIR, SOURCES_DIR, CLIPS_DIR, FAILURES_DIR, CORRUPT_DIR]:
        os.makedirs(d, exist_ok=True)

def get_metadata_path(video_id: str) -> str:
    return os.path.join(META_DIR, f"{video_id}.json")

def get_source_path(video_id: str, max_height: int = 480, ext: str = "mp4") -> str:
    # Format: VIDEO_ID_480p_mp4_v2.1.1.mp4
    return os.path.join(SOURCES_DIR, f"{video_id}_{max_height}p_{ext}_v{YOUTUBE_PIPELINE_VERSION}.{ext}")

def get_clip_path(video_id: str, clip_start: float, clip_end: float, max_height: int = 480, ext: str = "mp4", crop_mode: str = "none") -> str:
    # Format: VIDEO_ID_20.000_28.000_480p_mp4_none_v2.1.1.mp4
    s = f"{clip_start:.3f}"
    e = f"{clip_end:.3f}"
    filename = f"{video_id}_{s}_{e}_{max_height}p_{ext}_{crop_mode}_v{YOUTUBE_PIPELINE_VERSION}.{ext}"
    return os.path.join(CLIPS_DIR, filename)

def classify_error(reason: str) -> tuple:
    """Returns (error_type, retry_after_days, retry_after_minutes)."""
    r = reason.lower()
    if "timeout" in r or "network error" in r:
        return ("timeout", 7, 0)
    elif "http error 429" in r:
        return ("http_429", 0, 30)
    elif "http error 5" in r:
        return ("http_5xx", 0, 60)
    elif any(k in r for k in ["private video", "members-only", "removed", "unavailable"]):
        return ("permanent_unavailable", 9999, 0)
    elif "region" in r:
        return ("region_restricted", 9999, 0)
    elif "requested format" in r:
        return ("format_unavailable", 0, 0) # Immediately handled or permanently failed
    return ("unknown", 1, 0)

def record_failure(video_id: str, mode: str, reason: str):
    error_type, days, mins = classify_error(reason)
    
    now = datetime.datetime.now(datetime.timezone.utc)
    if days == 9999:
        retry_after = None # Permanent
    else:
        retry_after = now + datetime.timedelta(days=days, minutes=mins)
        
    data = {
        "video_id": video_id,
        "mode": mode,
        "error_type": error_type,
        "reason": reason,
        "failed_at": now.isoformat(),
        "retry_after": retry_after.isoformat() if retry_after else None
    }
    
    fp = os.path.join(FAILURES_DIR, f"{video_id}.json")
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def check_failure_status(video_id: str, mode: str) -> dict:
    """
    Returns {"active": bool, "type": str, "reason": str, "permanent": bool}
    """
    fp = os.path.join(FAILURES_DIR, f"{video_id}.json")
    if not os.path.exists(fp):
        return {"active": False}
        
    try:
        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        if data.get("mode") == mode:
            retry_after_str = data.get("retry_after")
            if retry_after_str is None:
                return {"active": True, "type": data.get("error_type"), "reason": data.get("reason"), "permanent": True}
                
            retry_after = datetime.datetime.fromisoformat(retry_after_str)
            now = datetime.datetime.now(datetime.timezone.utc)
            if now < retry_after:
                return {"active": True, "type": data.get("error_type"), "reason": data.get("reason"), "permanent": False}
    except Exception:
        pass
        
    return {"active": False}

init_cache_dirs()
