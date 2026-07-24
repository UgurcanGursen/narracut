import os
import time
import json
import socket
import datetime
from typing import Dict, Any

from .config import (
    YOUTUBE_METADATA_TIMEOUT, YOUTUBE_PARTIAL_TIMEOUT, 
    YOUTUBE_FULL_SOURCE_TIMEOUT, YOUTUBE_LOCAL_TRIM_TIMEOUT, 
    YOUTUBE_LOCK_TIMEOUT
)
from .cache_manager import (
    get_metadata_path, get_source_path, get_clip_path, 
    check_failure_status, record_failure, CACHE_BASE, CORRUPT_DIR
)
from .process_utils import get_current_pid, is_process_alive
from .ffprobe_validator import validate_and_move_if_corrupt
from .youtube_downloader import (
    DownloadMode, fetch_metadata, download_fast_partial, 
    download_full_source, slice_local_video
)

class DownloadState:
    CACHE_CLIP_CHECK = "CACHE_CLIP_CHECK"
    SOURCE_CACHE_CHECK = "SOURCE_CACHE_CHECK"
    METADATA_FETCH = "METADATA_FETCH"
    MODE_SELECTION = "MODE_SELECTION"
    FAST_PARTIAL = "FAST_PARTIAL"
    PARTIAL_VALIDATION = "PARTIAL_VALIDATION"
    FULL_SOURCE = "FULL_SOURCE"
    SOURCE_VALIDATION = "SOURCE_VALIDATION"
    LOCAL_TRIM = "LOCAL_TRIM"
    CLIP_VALIDATION = "CLIP_VALIDATION"
    FALLBACK = "FALLBACK"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class YouTubeDownloadStateMachine:
    def __init__(self, video_id: str, url: str, clip_start: float, duration: float, 
                 max_height: int = 480, crop_mode: str = "none", request_count: int = 1):
        self.video_id = video_id
        self.url = url
        self.clip_start = clip_start
        self.duration = duration
        self.clip_end = clip_start + duration
        self.max_height = max_height
        self.crop_mode = crop_mode
        self.request_count = request_count
        
        self.state = DownloadState.CACHE_CLIP_CHECK
        self.mode = DownloadMode.AUTO
        
        self.clip_path = get_clip_path(video_id, clip_start, self.clip_end, max_height=max_height, crop_mode=crop_mode)
        self.source_path = get_source_path(video_id, max_height=max_height)
        
        self.partial_path = get_clip_path(video_id, clip_start, self.clip_end, max_height=max_height, crop_mode="rough")
        
        self.failure_chain = []
        self.final_result = None
        self.log_events = []
        
        self.lock_file = os.path.join(CACHE_BASE, f"{video_id}.lockmeta")
        self._my_lock = False

    def log_transition(self, to_state: str, reason: str = ""):
        evt = {
            "video_id": self.video_id,
            "from_state": self.state,
            "to_state": to_state,
            "reason": reason,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        self.log_events.append(evt)
        self.state = to_state

    def run(self) -> Dict[str, Any]:
        try:
            if not self.acquire_lock_with_stale_check():
                self.log_transition(DownloadState.FAILED, "lock_timeout")
                return self._finalize("lock_timeout_failed")

            while self.state not in [DownloadState.COMPLETE, DownloadState.FAILED, DownloadState.FALLBACK, DownloadState.CANCELLED]:
                if self.state == DownloadState.CACHE_CLIP_CHECK:
                    self._handle_cache_clip_check()
                elif self.state == DownloadState.SOURCE_CACHE_CHECK:
                    self._handle_source_cache_check()
                elif self.state == DownloadState.METADATA_FETCH:
                    self._handle_metadata_fetch()
                elif self.state == DownloadState.MODE_SELECTION:
                    self._handle_mode_selection()
                elif self.state == DownloadState.FAST_PARTIAL:
                    self._handle_fast_partial()
                elif self.state == DownloadState.PARTIAL_VALIDATION:
                    self._handle_partial_validation()
                elif self.state == DownloadState.FULL_SOURCE:
                    self._handle_full_source()
                elif self.state == DownloadState.SOURCE_VALIDATION:
                    self._handle_source_validation()
                elif self.state == DownloadState.LOCAL_TRIM:
                    self._handle_local_trim()
                elif self.state == DownloadState.CLIP_VALIDATION:
                    self._handle_clip_validation()
                
            return self._finalize("success" if self.state == DownloadState.COMPLETE else self.state.lower())
            
        except Exception as e:
            self.failure_chain.append({"stage": self.state, "reason": str(e)})
            self.log_transition(DownloadState.FAILED, "unhandled_exception")
            return self._finalize("exception")
        finally:
            self.release_lock()

    def _finalize(self, status: str) -> Dict[str, Any]:
        return {
            "video_id": self.video_id,
            "requested_url": self.url,
            "requested_range": [self.clip_start, self.clip_end],
            "selected_mode": self.mode.value,
            "result": status,
            "path": self.clip_path if status == "success" else None,
            "failure_chain": self.failure_chain,
            "transitions": self.log_events
        }

    def acquire_lock_with_stale_check(self) -> bool:
        start_wait = time.time()
        hostname = socket.gethostname()
        pid = get_current_pid()
        
        while time.time() - start_wait < YOUTUBE_LOCK_TIMEOUT:
            if not os.path.exists(self.lock_file):
                # Try to acquire
                meta = {
                    "pid": pid,
                    "hostname": hostname,
                    "created_at": time.time(),
                    "video_id": self.video_id,
                    "target_file": self.source_path
                }
                try:
                    with open(self.lock_file, "w") as f:
                        json.dump(meta, f)
                    self._my_lock = True
                    return True
                except Exception:
                    pass
            else:
                # Check stale
                try:
                    with open(self.lock_file, "r") as f:
                        meta = json.load(f)
                    
                    lock_age = time.time() - meta.get("created_at", 0)
                    lock_pid = meta.get("pid", 0)
                    lock_host = meta.get("hostname", "")
                    
                    if lock_host == hostname:
                        if not is_process_alive(lock_pid):
                            # Stale lock on same machine!
                            try: os.remove(self.lock_file)
                            except: pass
                            continue
                            
                    if lock_age > YOUTUBE_LOCK_TIMEOUT:
                        try: os.remove(self.lock_file)
                        except: pass
                        continue
                        
                except Exception:
                    # Corrupted lock
                    try: os.remove(self.lock_file)
                    except: pass
                    continue
                    
            time.sleep(2.0)
        return False

    def release_lock(self):
        if self._my_lock and os.path.exists(self.lock_file):
            try: os.remove(self.lock_file)
            except: pass
            self._my_lock = False

    def _handle_cache_clip_check(self):
        if os.path.exists(self.clip_path):
            val = validate_and_move_if_corrupt(self.clip_path, self.duration, CORRUPT_DIR)
            if val["valid"]:
                self.log_transition(DownloadState.COMPLETE, "clip_cache_hit")
                return
            else:
                self.failure_chain.append({"stage": "cache_clip_check", "reason": f"corrupt: {val['reason']}"})
        self.log_transition(DownloadState.SOURCE_CACHE_CHECK, "clip_cache_miss")

    def _handle_source_cache_check(self):
        if os.path.exists(self.source_path):
            val = validate_and_move_if_corrupt(self.source_path, expected_duration=None, corrupt_dir=CORRUPT_DIR)
            if val["valid"]:
                self.log_transition(DownloadState.LOCAL_TRIM, "source_cache_hit")
                return
            else:
                self.failure_chain.append({"stage": "source_cache_check", "reason": f"corrupt: {val['reason']}"})
        self.log_transition(DownloadState.MODE_SELECTION, "source_cache_miss")

    def _handle_metadata_fetch(self):
        # We can fetch metadata here if needed. But for FAST_PARTIAL vs FULL_SOURCE,
        # we can decide purely based on failure cache, request_count and clip_start.
        self.log_transition(DownloadState.MODE_SELECTION, "skipped_metadata")

    def _handle_mode_selection(self):
        fail_status = check_failure_status(self.video_id, "FAST_PARTIAL")
        
        if fail_status["active"]:
            if fail_status["permanent"]:
                self.failure_chain.append({"stage": "mode_selection", "reason": "permanent_failure_cached"})
                self.log_transition(DownloadState.FALLBACK, "permanent_fail")
                return
            else:
                self.mode = DownloadMode.FULL_SOURCE
                self.log_transition(DownloadState.FULL_SOURCE, "active_partial_failure")
                return
                
        if self.request_count >= 2:
            self.mode = DownloadMode.FULL_SOURCE
            self.log_transition(DownloadState.FULL_SOURCE, "clip_count_>=_2")
            return
            
        if self.clip_start > 120.0:
            self.mode = DownloadMode.FULL_SOURCE
            self.log_transition(DownloadState.FULL_SOURCE, "late_start_time")
            return
            
        self.mode = DownloadMode.FAST_PARTIAL
        self.log_transition(DownloadState.FAST_PARTIAL, "conditions_met")

    def _handle_fast_partial(self):
        res = download_fast_partial(self.url, self.clip_start, self.clip_end, self.partial_path, timeout=YOUTUBE_PARTIAL_TIMEOUT)
        if res["success"]:
            self.log_transition(DownloadState.PARTIAL_VALIDATION, "partial_downloaded")
        else:
            reason = res.get("reason", "unknown")
            record_failure(self.video_id, "FAST_PARTIAL", reason)
            self.failure_chain.append({"stage": "fast_partial", "reason": reason})
            self.mode = DownloadMode.FULL_SOURCE
            self.log_transition(DownloadState.FULL_SOURCE, "partial_failed")

    def _handle_partial_validation(self):
        val = validate_and_move_if_corrupt(self.partial_path, expected_duration=None, corrupt_dir=CORRUPT_DIR)
        if val["valid"]:
            self.log_transition(DownloadState.LOCAL_TRIM, "partial_valid")
        else:
            self.failure_chain.append({"stage": "partial_validation", "reason": f"invalid: {val['reason']}"})
            self.mode = DownloadMode.FULL_SOURCE
            self.log_transition(DownloadState.FULL_SOURCE, "partial_invalid")

    def _handle_full_source(self):
        res = download_full_source(self.url, self.source_path, timeout=YOUTUBE_FULL_SOURCE_TIMEOUT)
        if res["success"]:
            self.log_transition(DownloadState.SOURCE_VALIDATION, "full_source_downloaded")
        else:
            reason = res.get("reason", "unknown")
            record_failure(self.video_id, "FULL_SOURCE", reason)
            self.failure_chain.append({"stage": "full_source", "reason": reason})
            self.log_transition(DownloadState.FALLBACK, "full_source_failed")

    def _handle_source_validation(self):
        val = validate_and_move_if_corrupt(self.source_path, expected_duration=None, corrupt_dir=CORRUPT_DIR)
        if val["valid"]:
            self.log_transition(DownloadState.LOCAL_TRIM, "source_valid")
        else:
            self.failure_chain.append({"stage": "source_validation", "reason": f"invalid: {val['reason']}"})
            self.log_transition(DownloadState.FALLBACK, "source_invalid")

    def _handle_local_trim(self):
        src = self.partial_path if self.mode == DownloadMode.FAST_PARTIAL else self.source_path
        start_offset = 0 if self.mode == DownloadMode.FAST_PARTIAL else self.clip_start
        # If fast partial, we downloaded max(0, clip_start-3) to clip_end+3
        if self.mode == DownloadMode.FAST_PARTIAL:
            start_offset = self.clip_start - max(0.0, self.clip_start - 3.0)
            
        res = slice_local_video(src, start_offset, self.duration, self.clip_path, timeout=YOUTUBE_LOCAL_TRIM_TIMEOUT)
        if res["success"]:
            self.log_transition(DownloadState.CLIP_VALIDATION, "trim_success")
        else:
            self.failure_chain.append({"stage": "local_trim", "reason": res.get("reason", "unknown")})
            if self.mode == DownloadMode.FAST_PARTIAL:
                self.mode = DownloadMode.FULL_SOURCE
                self.log_transition(DownloadState.FULL_SOURCE, "trim_failed_try_full")
            else:
                self.log_transition(DownloadState.FALLBACK, "trim_failed")

    def _handle_clip_validation(self):
        val = validate_and_move_if_corrupt(self.clip_path, self.duration, CORRUPT_DIR)
        if val["valid"]:
            self.log_transition(DownloadState.COMPLETE, "clip_valid")
        else:
            self.failure_chain.append({"stage": "clip_validation", "reason": f"invalid: {val['reason']}"})
            if self.mode == DownloadMode.FAST_PARTIAL:
                self.mode = DownloadMode.FULL_SOURCE
                self.log_transition(DownloadState.FULL_SOURCE, "clip_invalid_try_full")
            else:
                self.log_transition(DownloadState.FALLBACK, "clip_invalid")
