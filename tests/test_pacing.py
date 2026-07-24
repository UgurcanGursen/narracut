import os
import pytest
from unittest.mock import patch, MagicMock
import subprocess
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from v2.pacing import (
    apply_pacing_variations, PacingMode, is_static_source,
    get_or_create_ffmpeg_zoom_clip
)
from v2.models import VisualScene

class TestPacing:
    
    def test_dynamic_sources_ignored(self):
        clip = MagicMock()
        # 1. Stock video
        visual = VisualScene(type="stock")
        _, m = apply_pacing_variations(clip, visual, 6.0, "video.mp4")
        assert m["eligible"] == False
        
        # 2. YouTube video
        visual = VisualScene(type="youtube")
        _, m = apply_pacing_variations(clip, visual, 6.0, "video.mp4")
        assert m["eligible"] == False

        # 3,4,5. Big text, counter, chart
        for t in ["big_text", "counter", "chart"]:
            visual = VisualScene(type=t)
            _, m = apply_pacing_variations(clip, visual, 6.0, "video.mp4")
            assert m["eligible"] == False

    def test_short_quote_off(self):
        # 6. Dört saniyeden kısa quote -> OFF
        clip = MagicMock()
        visual = VisualScene(type="quote")
        _, m = apply_pacing_variations(clip, visual, 3.5, "quote.png")
        assert m["eligible"] == True
        assert m["mode"] == PacingMode.OFF

    @patch('v2.pacing.create_punch_in_clip')
    def test_medium_quote_punch_in(self, mock_punch):
        # 7. 6 saniyelik quote -> PUNCH_IN
        clip = MagicMock()
        mock_punch.return_value = clip
        visual = VisualScene(type="quote")
        _, m = apply_pacing_variations(clip, visual, 6.0, "quote.png")
        assert m["eligible"] == True
        assert m["mode"] == PacingMode.PUNCH_IN
        mock_punch.assert_called_once()

    @patch('v2.pacing.get_or_create_ffmpeg_zoom_clip')
    @patch('v2.pacing.VideoFileClip')
    def test_long_article_ffmpeg_zoom(self, mock_vf, mock_get_ff):
        # 8. 10 saniyelik article -> FFMPEG_ZOOM
        clip = MagicMock()
        mock_get_ff.return_value = "cached.mp4"
        mock_vf.return_value.subclip.return_value = clip
        
        visual = VisualScene(type="article")
        
        with patch('os.path.getmtime', return_value=0):
            _, m = apply_pacing_variations(clip, visual, 10.0, "article.png")
            
        assert m["eligible"] == True
        assert m["mode"] == PacingMode.FFMPEG_ZOOM
        assert m["cache_hit"] == True
        mock_get_ff.assert_called_once()

    @patch('v2.pacing.get_or_create_ffmpeg_zoom_clip')
    @patch('v2.pacing.create_punch_in_clip')
    def test_ffmpeg_failure_fallback(self, mock_punch, mock_get_ff):
        # 9. FFmpeg başarısız -> PUNCH_IN fallback
        clip = MagicMock()
        mock_get_ff.return_value = None # Failed
        mock_punch.return_value = clip
        
        visual = VisualScene(type="article")
        _, m = apply_pacing_variations(clip, visual, 10.0, "article.png")
        
        assert m["mode"] == "punch_in_fallback"
        mock_punch.assert_called_once()

    def test_no_lambda_resize_in_codebase(self):
        # 14. Kod tabanında resize(lambda) kalmadığı doğrulanır
        result = subprocess.run(
            ['findstr', '/S', '/C:"resize(lambda"', 'c:\\Users\\user\\Documents\\Kurgu\\v2\\*.py'],
            capture_output=True, text=True
        )
        assert "resize(lambda" not in result.stdout

    @patch('v2.pacing.subprocess.run')
    @patch('v2.pacing.validate_video_file')
    @patch('os.path.exists')
    @patch('os.path.getmtime')
    def test_ffmpeg_zoom_cache_logic(self, mock_mtime, mock_exists, mock_val, mock_run):
        # 10 & 11. Aynı FFmpeg zoom ikinci kez -> cache hit, bozuk -> yeniden oluşturulur
        mock_mtime.return_value = 12345
        
        def exists_side_effect(path):
            if "article.png" in path: return True
            if ".mp4" in path: return True # pretend cached file exists
            return False
            
        mock_exists.side_effect = exists_side_effect
        
        # Test 11: Corrupt cache (duration mismatch)
        mock_val.return_value = {"valid": True, "duration": 2.0} # Target is 10
        get_or_create_ffmpeg_zoom_clip("article.png", 10.0, 1.08)
        assert mock_run.called
        
        mock_run.reset_mock()
        
        # Test 10: Perfect cache hit
        mock_val.return_value = {"valid": True, "duration": 10.0}
        res2 = get_or_create_ffmpeg_zoom_clip("article.png", 10.0, 1.08)
        assert mock_run.called == False
        assert res2 is not None
