import os
import time
import pytest
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from v2.process_utils import run_process_with_timeout, is_process_alive
from v2.ffprobe_validator import validate_and_move_if_corrupt
from v2.youtube_state_machine import YouTubeDownloadStateMachine, DownloadState, DownloadMode
from v2.cache_manager import classify_error

class TestYouTubeStateMachine:
    def test_process_timeout_kills_tree(self):
        cmd = ["ping", "-n", "10", "127.0.0.1"]
        start = time.time()
        res = run_process_with_timeout(cmd, timeout=1.0)
        elapsed = time.time() - start
        
        assert res["success"] == False
        assert res["reason"] == "timeout"
        assert elapsed < 5.0 
        
    def test_error_classification(self):
        assert classify_error("network timeout")[0] == "timeout"
        assert classify_error("http error 429")[0] == "http_429"
        assert classify_error("http error 502")[0] == "http_5xx"
        assert classify_error("private video is unavailable")[0] == "permanent_unavailable"
        assert classify_error("region restricted")[0] == "region_restricted"

    @patch('v2.youtube_state_machine.download_fast_partial')
    @patch('v2.youtube_state_machine.slice_local_video')
    @patch('v2.youtube_state_machine.validate_and_move_if_corrupt')
    @patch('v2.youtube_state_machine.check_failure_status')
    @patch('os.path.exists')
    def test_state_machine_fast_partial(self, mock_exists, mock_fail, mock_val, mock_slice, mock_partial):
        # Mocks
        mock_exists.return_value = False # No cache, no lock
        mock_fail.return_value = {"active": False}
        mock_partial.return_value = {"success": True}
        mock_slice.return_value = {"success": True}
        mock_val.return_value = {"valid": True, "reason": "ok"}
        
        machine = YouTubeDownloadStateMachine("test1", "http://x", 10.0, 5.0)
        res = machine.run()
        
        assert res["result"] == "success"
        assert res["selected_mode"] == "FAST_PARTIAL"
        assert "FAST_PARTIAL" in [t["from_state"] for t in res["transitions"]]
        
    @patch('v2.youtube_state_machine.check_failure_status')
    @patch('os.path.exists')
    def test_state_machine_forces_full_source_if_count_gte_2(self, mock_exists, mock_fail):
        mock_exists.return_value = False
        mock_fail.return_value = {"active": False}
        
        machine = YouTubeDownloadStateMachine("test2", "http://x", 10.0, 5.0, request_count=2)
        # We don't want it to actually download, so we just run until mode selection
        machine.state = DownloadState.MODE_SELECTION
        machine._handle_mode_selection()
        
        assert machine.mode == DownloadMode.FULL_SOURCE

    @patch('v2.youtube_state_machine.validate_and_move_if_corrupt')
    @patch('os.path.exists')
    def test_cache_hit_skips_download(self, mock_exists, mock_val):
        # Clip exists in cache
        def mock_exists_side_effect(path):
            if path.endswith(".lockmeta"): return False
            if "clips" in path: return True
            return False
        mock_exists.side_effect = mock_exists_side_effect
        mock_val.return_value = {"valid": True, "reason": "ok"}
        
        machine = YouTubeDownloadStateMachine("test3", "http://x", 10.0, 5.0)
        res = machine.run()
        
        assert res["result"] == "success"
        # Should transition straight from CACHE_CLIP_CHECK to COMPLETE
        assert len(res["transitions"]) > 0
        assert res["transitions"][0]["to_state"] == "COMPLETE"
        
    @patch('v2.youtube_state_machine.validate_and_move_if_corrupt')
    @patch('os.path.exists')
    def test_corrupt_cache_moves_forward(self, mock_exists, mock_val):
        def mock_exists_side_effect(path):
            if path.endswith(".lockmeta"): return False
            if "clips" in path: return True
            return False
        mock_exists.side_effect = mock_exists_side_effect
        # Simulated corrupt
        mock_val.return_value = {"valid": False, "reason": "invalid_resolution", "moved_to_corrupt": True}
        
        machine = YouTubeDownloadStateMachine("test4", "http://x", 10.0, 5.0)
        # Just run the check
        machine._handle_cache_clip_check()
        assert machine.state == DownloadState.SOURCE_CACHE_CHECK
