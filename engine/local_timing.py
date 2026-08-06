"""Bounded, local-only process boundary for a real word-timing producer.

The executable is deliberately supplied by local configuration.  This module
never downloads a model, calls an API, or falls back to REPLAY.  Its wire
format is intentionally small so a pinned WhisperX wrapper can be introduced
without putting provider-specific code in the canonical timing contracts.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Callable

from engine.contracts._canonical_json import encode_canonical_json_bytes


LOCAL_TIMING_REQUEST_V1 = "P17-LOCAL-TIMING-REQUEST-V1"
LOCAL_TIMING_OUTPUT_V1 = "P17-LOCAL-TIMING-OUTPUT-V1"


@dataclass(frozen=True)
class LocalTimingLimits:
    timeout_seconds: float = 120.0
    max_input_bytes: int = 512 * 1024 * 1024
    max_output_bytes: int = 16 * 1024 * 1024

    def __post_init__(self) -> None:
        if (
            type(self.timeout_seconds) not in {int, float}
            or self.timeout_seconds <= 0
            or type(self.max_input_bytes) is not int
            or self.max_input_bytes <= 0
            or type(self.max_output_bytes) is not int
            or self.max_output_bytes <= 0
        ):
            raise ValueError("LOCAL_TIMING_LIMITS_INVALID")


@dataclass(frozen=True)
class LocalTimingResult:
    status: str
    failure_code: str | None
    request_hash: str
    audio_hash: str
    output_hash: str | None
    words: tuple[dict[str, object], ...]


class LocalTimingAdapter:
    """Runs one configured local tool at a time with an explicit failure result."""

    _run_lock = Lock()

    def __init__(self, *, command: tuple[str, ...], limits: LocalTimingLimits = LocalTimingLimits()) -> None:
        if not command or any(type(item) is not str or not item for item in command):
            raise ValueError("LOCAL_TIMING_COMMAND_INVALID")
        self._command = command
        self._limits = limits

    def run(
        self,
        *,
        audio_file: Path,
        words: tuple[tuple[str, str], ...],
        work_dir: Path,
        cancelled: Callable[[], bool] | None = None,
    ) -> LocalTimingResult:
        if not isinstance(audio_file, Path) or not audio_file.is_file() or not words or any(type(word_id) is not str or not word_id or type(text) is not str or not text for word_id, text in words):
            raise ValueError("LOCAL_TIMING_INPUT_INVALID")
        if not isinstance(work_dir, Path):
            raise ValueError("LOCAL_TIMING_WORKDIR_INVALID")
        size = audio_file.stat().st_size
        audio_hash = _hash_file(audio_file)
        request = {"schema_version": LOCAL_TIMING_REQUEST_V1, "audio_file_name": "input.wav", "audio_sha256": audio_hash, "words": [{"word_id": word_id, "text": text} for word_id, text in words]}
        request_hash = "sha256:" + hashlib.sha256(encode_canonical_json_bytes(request)).hexdigest()
        if size > self._limits.max_input_bytes:
            return LocalTimingResult("FAILED", "INPUT_TOO_LARGE", request_hash, audio_hash, None, ())
        work_dir.mkdir(parents=True, exist_ok=True)
        request_file = work_dir / "local_timing_request.json"
        output_file = work_dir / "local_timing_output.json"
        shutil.copyfile(audio_file, work_dir / "input.wav")
        request_file.write_bytes(encode_canonical_json_bytes(request))
        if output_file.exists():
            output_file.unlink()
        if cancelled is not None and cancelled():
            return LocalTimingResult("CANCELLED", "CANCELLED", request_hash, audio_hash, None, ())
        with self._run_lock:
            return self._execute(request_file, output_file, request_hash, audio_hash, tuple(word_id for word_id, _ in words), cancelled)

    def _execute(self, request_file: Path, output_file: Path, request_hash: str, audio_hash: str, word_ids: tuple[str, ...], cancelled: Callable[[], bool] | None) -> LocalTimingResult:
        try:
            process = subprocess.Popen(
                (*self._command, str(request_file), str(output_file)),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=False,
            )
        except OSError:
            return LocalTimingResult("FAILED", "TOOL_UNAVAILABLE", request_hash, audio_hash, None, ())
        started = time.monotonic()
        while process.poll() is None:
            if cancelled is not None and cancelled():
                _stop(process)
                return LocalTimingResult("CANCELLED", "CANCELLED", request_hash, audio_hash, None, ())
            if time.monotonic() - started > self._limits.timeout_seconds:
                _stop(process)
                return LocalTimingResult("FAILED", "TIMEOUT", request_hash, audio_hash, None, ())
            time.sleep(0.02)
        if process.returncode != 0:
            return LocalTimingResult("FAILED", "TOOL_FAILED", request_hash, audio_hash, None, ())
        try:
            if not output_file.is_file() or output_file.stat().st_size > self._limits.max_output_bytes:
                return LocalTimingResult("FAILED", "OUTPUT_INVALID", request_hash, audio_hash, None, ())
            raw = output_file.read_bytes()
            output_hash = "sha256:" + hashlib.sha256(raw).hexdigest()
            value = json.loads(raw.decode("utf-8"))
            if encode_canonical_json_bytes(value) != raw:
                return LocalTimingResult("FAILED", "OUTPUT_NON_CANONICAL", request_hash, audio_hash, output_hash, ())
            words = _validate_output(value, word_ids)
            return LocalTimingResult("SUCCEEDED", None, request_hash, audio_hash, output_hash, words)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
            return LocalTimingResult("FAILED", "OUTPUT_INVALID", request_hash, audio_hash, None, ())


def _validate_output(value: object, word_ids: tuple[str, ...]) -> tuple[dict[str, object], ...]:
    if type(value) is not dict or set(value) != {"schema_version", "words"} or value["schema_version"] != LOCAL_TIMING_OUTPUT_V1 or type(value["words"]) is not list or len(value["words"]) != len(word_ids):
        raise ValueError("LOCAL_TIMING_OUTPUT_INVALID")
    previous_end = -1
    parsed: list[dict[str, object]] = []
    for expected, item in zip(word_ids, value["words"], strict=True):
        if type(item) is not dict or set(item) not in ({"word_id", "start_ms", "end_ms"}, {"word_id", "start_ms", "end_ms", "confidence_millionths"}) or item.get("word_id") != expected or type(item.get("start_ms")) is not int or type(item.get("end_ms")) is not int or item["start_ms"] < previous_end or item["end_ms"] <= item["start_ms"]:
            raise ValueError("LOCAL_TIMING_OUTPUT_INVALID")
        confidence = item.get("confidence_millionths")
        if confidence is not None and (type(confidence) is not int or not 0 <= confidence <= 1_000_000):
            raise ValueError("LOCAL_TIMING_OUTPUT_INVALID")
        previous_end = item["end_ms"]
        parsed.append(dict(item))
    return tuple(parsed)


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _stop(process: subprocess.Popen[bytes]) -> None:
    process.terminate()
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=2)
