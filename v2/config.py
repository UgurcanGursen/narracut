import os


def get_pexels_api_key() -> str:
    """Read the optional Pexels credential from the process environment."""
    return os.environ.get("PEXELS_API_KEY", "").strip()


def get_freesound_api_key() -> str:
    """Read the optional Freesound credential from the process environment."""
    return os.environ.get("FREESOUND_API_KEY", "").strip()


def _get_float_env(key: str, default: float) -> float:
    val = os.environ.get(key)
    if val is None:
        return default
    try:
        fval = float(val)
        if fval <= 0:
            raise ValueError(f"{key} must be positive.")
        return fval
    except ValueError as e:
        raise ValueError(f"Config error for {key}: {str(e)}")

def _get_int_env(key: str, default: int) -> int:
    val = os.environ.get(key)
    if val is None:
        return default
    try:
        ival = int(val)
        if ival <= 0:
            raise ValueError(f"{key} must be positive.")
        return ival
    except ValueError as e:
        raise ValueError(f"Config error for {key}: {str(e)}")

YOUTUBE_METADATA_TIMEOUT = _get_float_env("YOUTUBE_METADATA_TIMEOUT", 20.0)
YOUTUBE_PARTIAL_TIMEOUT = _get_float_env("YOUTUBE_PARTIAL_TIMEOUT", 45.0)
YOUTUBE_FULL_SOURCE_TIMEOUT = _get_float_env("YOUTUBE_FULL_SOURCE_TIMEOUT", 900.0)
YOUTUBE_LOCAL_TRIM_TIMEOUT = _get_float_env("YOUTUBE_LOCAL_TRIM_TIMEOUT", 60.0)
YOUTUBE_LOCK_TIMEOUT = _get_float_env("YOUTUBE_LOCK_TIMEOUT", 1200.0)

YOUTUBE_DEFAULT_MAX_HEIGHT = _get_int_env("YOUTUBE_DEFAULT_MAX_HEIGHT", 480)
YOUTUBE_ZOOMED_MAX_HEIGHT = _get_int_env("YOUTUBE_ZOOMED_MAX_HEIGHT", 720)
YOUTUBE_PIPELINE_VERSION = os.environ.get("YOUTUBE_PIPELINE_VERSION", "2.1.1")

USE_ELEVENLABS = os.environ.get("USE_ELEVENLABS", "false").lower() == "true"
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "")
ELEVENLABS_MODEL = os.environ.get("ELEVENLABS_MODEL", "eleven_multilingual_v2")
PEXELS_API_KEY = get_pexels_api_key()

ENABLE_DYNAMIC_PACING = os.environ.get("ENABLE_DYNAMIC_PACING", "true").lower() == "true"
STATIC_PACING_MODE = os.environ.get("STATIC_PACING_MODE", "auto")
STATIC_PACING_MIN_DURATION = float(os.environ.get("STATIC_PACING_MIN_DURATION", "4.0"))
STATIC_PACING_PUNCH_SCALE = float(os.environ.get("STATIC_PACING_PUNCH_SCALE", "1.06"))
STATIC_PACING_ZOOM_SCALE = float(os.environ.get("STATIC_PACING_ZOOM_SCALE", "1.08"))
STATIC_PACING_SPLIT_RATIO = float(os.environ.get("STATIC_PACING_SPLIT_RATIO", "0.50"))
STATIC_PACING_CACHE_DIR = os.environ.get("STATIC_PACING_CACHE_DIR", "cache/paced")

VIDEO_NORMALIZATION_BACKEND = os.environ.get("VIDEO_NORMALIZATION_BACKEND", "ffmpeg")
VIDEO_NORMALIZATION_CACHE_DIR = os.environ.get("VIDEO_NORMALIZATION_CACHE_DIR", "cache/normalized")
VIDEO_NORMALIZATION_TIMEOUT = _get_float_env("VIDEO_NORMALIZATION_TIMEOUT", 180.0)
VIDEO_NORMALIZATION_PIPELINE_VERSION = os.environ.get("VIDEO_NORMALIZATION_PIPELINE_VERSION", "2.1.3")
VIDEO_NORMALIZATION_PRESET = os.environ.get("VIDEO_NORMALIZATION_PRESET", "veryfast")
VIDEO_NORMALIZATION_CRF = os.environ.get("VIDEO_NORMALIZATION_CRF", "20")

TIMELINE_TIMING_POLICY = os.environ.get("TIMELINE_TIMING_POLICY", "strict")
TIMELINE_DURATION_TOLERANCE = float(os.environ.get("TIMELINE_DURATION_TOLERANCE", "0.25"))
TTS_TARGET_WPM = int(os.environ.get("TTS_TARGET_WPM", "140"))
TTS_WPM_TOLERANCE = int(os.environ.get("TTS_WPM_TOLERANCE", "7"))
EDGE_TTS_RATE = os.environ.get("EDGE_TTS_RATE", "-5%")
GRAPHICS_RENDERER_VERSION = os.environ.get("GRAPHICS_RENDERER_VERSION", "2.2.0")
CACHE_SCHEMA_VERSION = os.environ.get("CACHE_SCHEMA_VERSION", "2.2.0")
ASSET_CANDIDATE_COUNT = int(os.environ.get("ASSET_CANDIDATE_COUNT", "5"))
BIG_TEXT_MAX_DURATION = float(os.environ.get("BIG_TEXT_MAX_DURATION", "4.5"))
COUNTER_MAX_DURATION = float(os.environ.get("COUNTER_MAX_DURATION", "5.5"))
QUOTE_MAX_DURATION = float(os.environ.get("QUOTE_MAX_DURATION", "6.5"))
TEXT_ONLY_MAX_RATIO = float(os.environ.get("TEXT_ONLY_MAX_RATIO", "0.20"))

# V2.3 Editorial & Debug Configs
EDITORIAL_DEBUG_MODE = os.environ.get("EDITORIAL_DEBUG_MODE", "false").lower() == "true"
ENABLE_BGM = os.environ.get("ENABLE_BGM", "false").lower() == "true"
ENABLE_SFX = os.environ.get("ENABLE_SFX", "false").lower() == "true"
ENABLE_COUNTER = os.environ.get("ENABLE_COUNTER", "false").lower() == "true"
ENABLE_AUTOMATIC_TRANSITIONS = os.environ.get("ENABLE_AUTOMATIC_TRANSITIONS", "true").lower() == "true"
ENABLE_AUTOMATIC_STOCK_FALLBACK = os.environ.get("ENABLE_AUTOMATIC_STOCK_FALLBACK", "true").lower() == "true"

TIMING_MODE = os.environ.get("TIMING_MODE", "cue_anchor")
REQUIRE_ASSET_APPROVAL = os.environ.get("REQUIRE_ASSET_APPROVAL", "false").lower() == "true"
STOCK_SEMANTIC_MIN_SCORE = float(os.environ.get("STOCK_SEMANTIC_MIN_SCORE", "0.30"))
