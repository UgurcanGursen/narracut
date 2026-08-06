"""Pinned local faster-whisper worker for ``engine.local_timing``.

This executable deliberately accepts only the P17 local request file and a
local model directory. ``local_files_only`` prevents a model-cache miss from
silently becoming a network download.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.contracts._canonical_json import encode_canonical_json_bytes
from engine.local_timing import LOCAL_TIMING_OUTPUT_V1, LOCAL_TIMING_REQUEST_V1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("request")
    parser.add_argument("output")
    args = parser.parse_args()
    request_path, output_path, model_dir = Path(args.request), Path(args.output), Path(args.model_dir)
    try:
        request = json.loads(request_path.read_text(encoding="utf-8"))
        if encode_canonical_json_bytes(request) != request_path.read_bytes():
            return 2
        if type(request) is not dict or set(request) != {"schema_version", "audio_file_name", "audio_sha256", "words"} or request["schema_version"] != LOCAL_TIMING_REQUEST_V1 or request["audio_file_name"] != "input.wav" or type(request["words"]) is not list or not request["words"]:
            return 2
        audio = request_path.parent / request["audio_file_name"]
        if not audio.is_file() or "sha256:" + hashlib.sha256(audio.read_bytes()).hexdigest() != request["audio_sha256"]:
            return 2
        expected = []
        for item in request["words"]:
            if type(item) is not dict or set(item) != {"word_id", "text"} or not all(type(item[key]) is str and item[key] for key in item):
                return 2
            expected.append(item)
        from faster_whisper import WhisperModel
        model = WhisperModel(str(model_dir), device="cpu", compute_type="int8", local_files_only=True)
        segments, _ = model.transcribe(str(audio), word_timestamps=True, vad_filter=True)
        observed = [word for segment in segments for word in (segment.words or ())]
        if len(observed) != len(expected) or any(_norm(item["text"]) != _norm(word.word) for item, word in zip(expected, observed, strict=True)):
            return 3
        words = [{"word_id": item["word_id"], "start_ms": round(word.start * 1000), "end_ms": round(word.end * 1000), "confidence_millionths": round(word.probability * 1_000_000)} for item, word in zip(expected, observed, strict=True)]
        output_path.write_bytes(encode_canonical_json_bytes({"schema_version": LOCAL_TIMING_OUTPUT_V1, "words": words}))
        return 0
    except Exception:
        return 1


def _norm(value: str) -> str:
    return re.sub(r"[^\\w]+", "", value, flags=re.UNICODE).casefold()


if __name__ == "__main__":
    raise SystemExit(main())
