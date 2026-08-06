from __future__ import annotations

import sys
import subprocess
from pathlib import Path

from engine.contracts._canonical_json import encode_canonical_json_bytes
from engine.local_timing import LOCAL_TIMING_OUTPUT_V1, LocalTimingAdapter, LocalTimingLimits


def _tool(tmp_path: Path, body: str) -> tuple[str, ...]:
    script = tmp_path / "tool.py"
    script.write_text(body, encoding="utf-8")
    return (sys.executable, str(script))


def test_local_timing_runs_a_canonical_local_tool_and_binds_words(tmp_path: Path) -> None:
    command = _tool(tmp_path, "import pathlib, sys\npathlib.Path(sys.argv[2]).write_bytes(b'{\\\"schema_version\\\":\\\"P17-LOCAL-TIMING-OUTPUT-V1\\\",\\\"words\\\":[{\\\"end_ms\\\":100,\\\"start_ms\\\":0,\\\"word_id\\\":\\\"word_1\\\"},{\\\"end_ms\\\":220,\\\"start_ms\\\":100,\\\"word_id\\\":\\\"word_2\\\"}]}')\n")
    audio = tmp_path / "narration.wav"
    audio.write_bytes(b"local-audio")
    result = LocalTimingAdapter(command=command).run(audio_file=audio, words=(("word_1", "Hello"), ("word_2", "world")), work_dir=tmp_path / "run")
    assert result.status == "SUCCEEDED"
    assert result.failure_code is None
    assert [item["word_id"] for item in result.words] == ["word_1", "word_2"]
    assert result.output_hash is not None


def test_local_timing_rejects_noncanonical_or_mismatched_output(tmp_path: Path) -> None:
    payload = {"schema_version": LOCAL_TIMING_OUTPUT_V1, "words": [{"word_id": "other", "start_ms": 0, "end_ms": 100}]}
    command = _tool(tmp_path, "import pathlib, sys\npathlib.Path(sys.argv[2]).write_bytes(" + repr(encode_canonical_json_bytes(payload)) + ")\n")
    audio = tmp_path / "narration.wav"
    audio.write_bytes(b"local-audio")
    result = LocalTimingAdapter(command=command).run(audio_file=audio, words=(("word_1", "Hello"),), work_dir=tmp_path / "run")
    assert (result.status, result.failure_code, result.words) == ("FAILED", "OUTPUT_INVALID", ())


def test_local_timing_has_explicit_timeout_and_cancellation(tmp_path: Path) -> None:
    command = _tool(tmp_path, "import time\ntime.sleep(10)\n")
    audio = tmp_path / "narration.wav"
    audio.write_bytes(b"local-audio")
    adapter = LocalTimingAdapter(command=command, limits=LocalTimingLimits(timeout_seconds=0.05))
    timed_out = adapter.run(audio_file=audio, words=(("word_1", "Hello"),), work_dir=tmp_path / "timeout")
    cancelled = adapter.run(audio_file=audio, words=(("word_1", "Hello"),), work_dir=tmp_path / "cancel", cancelled=lambda: True)
    assert (timed_out.status, timed_out.failure_code) == ("FAILED", "TIMEOUT")
    assert (cancelled.status, cancelled.failure_code) == ("CANCELLED", "CANCELLED")


def test_faster_whisper_worker_fails_before_model_load_for_invalid_request(tmp_path: Path) -> None:
    project = Path(__file__).resolve().parents[1]
    request = tmp_path / "request.json"
    output = tmp_path / "output.json"
    request.write_text("{}", encoding="utf-8")
    completed = subprocess.run((sys.executable, str(project / "tools" / "local_timing_faster_whisper.py"), "--model-dir", str(tmp_path / "missing-model"), str(request), str(output)), cwd=project, check=False)
    assert completed.returncode == 2
    assert not output.exists()
