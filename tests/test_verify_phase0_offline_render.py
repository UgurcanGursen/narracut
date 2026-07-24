import importlib.util
import json
import tempfile
import wave
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "verify_phase0_offline_render.py"
SPEC = importlib.util.spec_from_file_location("verify_phase0_offline_render", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def write_wav(path: Path, seconds: float = 0.25) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = 16000
    frame_count = int(sample_rate * seconds)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"\x00\x00" * frame_count)


def make_fixture(audio_rel="assets/audio/a.wav", video_rel="assets/video/v.mp4", *, url=None):
    visual = {
        "type": "stock",
        "offset_start": 0.0,
        "offset_end": "AUTO",
        "allow_generic_stock": False,
        "fit_mode": "cover",
        "extra": {
            "asset_mode": "locked_local",
            "asset_id": "v",
            "resolved_path": video_rel,
        },
    }
    if url:
        visual["url"] = url
    return {
        "version": "2.2",
        "blocks": [
            {
                "block_id": "b1",
                "narration": "local narration",
                "audio_file": audio_rel,
                "visuals": [visual],
            }
        ],
    }


def test_rejects_remote_url_fixture():
    with tempfile.TemporaryDirectory() as tmp_dir:
        run_root = Path(tmp_dir)
        write_wav(run_root / "assets/audio/a.wav")
        (run_root / "assets/video/v.mp4").parent.mkdir(parents=True, exist_ok=True)
        (run_root / "assets/video/v.mp4").write_bytes(b"not-a-real-video")
        fixture = make_fixture(url="https://example.com/video")
        try:
            MODULE.validate_offline_fixture(fixture, run_root)
        except ValueError as exc:
            assert "remote url" in str(exc)
        else:
            raise AssertionError("expected remote fixture rejection")


def test_rejects_missing_local_audio():
    with tempfile.TemporaryDirectory() as tmp_dir:
        run_root = Path(tmp_dir)
        (run_root / "assets/video/v.mp4").parent.mkdir(parents=True, exist_ok=True)
        (run_root / "assets/video/v.mp4").write_bytes(b"not-a-real-video")
        fixture = make_fixture()
        try:
            MODULE.validate_offline_fixture(fixture, run_root)
        except ValueError as exc:
            assert "missing local audio file" in str(exc)
        else:
            raise AssertionError("expected missing audio rejection")


def test_rejects_path_escape():
    try:
        MODULE.ensure_relative_path("../escape.wav")
    except ValueError as exc:
        assert "path traversal" in str(exc)
    else:
        raise AssertionError("expected path traversal rejection")


def test_rejects_missing_local_video():
    with tempfile.TemporaryDirectory() as tmp_dir:
        run_root = Path(tmp_dir)
        write_wav(run_root / "assets/audio/a.wav")
        fixture = make_fixture()
        try:
            MODULE.validate_offline_fixture(fixture, run_root)
        except ValueError as exc:
            assert "missing locked_local video" in str(exc)
        else:
            raise AssertionError("expected missing video rejection")


def test_accepts_local_fixture_with_stubbed_media_probe():
    with tempfile.TemporaryDirectory() as tmp_dir:
        run_root = Path(tmp_dir)
        write_wav(run_root / "assets/audio/a.wav")
        video_path = run_root / "assets/video/v.mp4"
        video_path.parent.mkdir(parents=True, exist_ok=True)
        video_path.write_bytes(b"stub")
        original = MODULE.media_type_summary
        MODULE.media_type_summary = lambda _path: {
            "format_duration": 10.0,
            "video": {"codec_type": "video", "width": 1920, "height": 1080},
            "audio": None,
        }
        try:
            summary = MODULE.validate_offline_fixture(make_fixture(), run_root)
        finally:
            MODULE.media_type_summary = original
        assert summary["block_count"] == 1
        assert summary["visual_count"] == 1


def test_guard_blocks_known_provider_subprocess():
    state = MODULE.GuardState(attempts=[])
    try:
        state.block("subprocess", "yt-dlp")
    except MODULE.OfflineGuardTriggered:
        pass
    else:
        raise AssertionError("expected guard to raise")
    assert state.attempts == [{"channel": "subprocess", "detail": "yt-dlp"}]


def test_write_json_is_parseable():
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir) / "evidence.json"
        payload = {"schema_version": "1.0.0", "final_decision": "PASS"}
        MODULE.write_json(path, payload)
        assert json.loads(path.read_text(encoding="utf-8")) == payload
