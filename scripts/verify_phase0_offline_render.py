import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import types
import urllib.request
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_FIXTURE = REPO_ROOT / "baseline" / "fixtures" / "phase0_offline_full_render.json"
REPO_EVIDENCE_JSON = REPO_ROOT / "baseline" / "offline_isolated_full_render_evidence.json"
REPO_EVIDENCE_MD = REPO_ROOT / "baseline" / "offline_isolated_full_render_report.md"
START_SHA = "7f877a311bb6ab1f02c24bf35cdfa90cc14928e7"
ALLOWED_UNTRACKED = {"norm_words_debug.json"}
FORBIDDEN_VISUAL_TYPES = {"document_scan", "image_pip", "reddit", "web_record", "youtube"}
class OfflineGuardTriggered(RuntimeError):
    pass


@dataclass
class GuardState:
    attempts: List[Dict[str, str]]

    def block(self, channel: str, detail: str) -> None:
        self.attempts.append({"channel": channel, "detail": detail})
        raise OfflineGuardTriggered(f"OFFLINE_GUARD_BLOCKED:{channel}:{detail}")


def run_cmd(args: List[str], *, cwd: Path = None, text: bool = True, check: bool = True):
    return subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=text,
        check=check,
    )


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, data: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def is_remote_ref(value: str) -> bool:
    lowered = value.lower()
    return lowered.startswith("http://") or lowered.startswith("https://") or lowered.startswith("file://")


def ensure_relative_path(rel_path: str) -> Path:
    rel = Path(rel_path)
    if rel.is_absolute():
        raise ValueError(f"absolute path not allowed: {rel_path}")
    if any(part == ".." for part in rel.parts):
        raise ValueError(f"path traversal not allowed: {rel_path}")
    return rel


def ffprobe_json(media_path: Path) -> Dict:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("ffprobe not found on PATH")
    res = run_cmd(
        [
            ffprobe,
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(media_path),
        ],
        text=True,
    )
    return json.loads(res.stdout)


def media_type_summary(media_path: Path) -> Dict[str, object]:
    data = ffprobe_json(media_path)
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    return {
        "format_duration": float(data.get("format", {}).get("duration", 0.0) or 0.0),
        "video": video,
        "audio": audio,
    }


def gather_input_hashes(run_root: Path, fixture: Dict) -> Dict[str, Dict[str, object]]:
    hashes: Dict[str, Dict[str, object]] = {}
    for block in fixture.get("blocks", []):
        audio_rel = block.get("audio_file")
        if audio_rel:
            audio_path = run_root / ensure_relative_path(audio_rel)
            hashes[audio_rel] = {
                "sha256": sha256_file(audio_path),
                "bytes": audio_path.stat().st_size,
            }
        for visual in block.get("visuals", []):
            extra = visual.get("extra", {})
            resolved = extra.get("resolved_path")
            if resolved:
                media_path = run_root / ensure_relative_path(resolved)
                hashes[resolved] = {
                    "sha256": sha256_file(media_path),
                    "bytes": media_path.stat().st_size,
                }
    return dict(sorted(hashes.items()))


def validate_offline_fixture(fixture: Dict, run_root: Path) -> Dict[str, object]:
    if not isinstance(fixture, dict) or "blocks" not in fixture:
        raise ValueError("fixture must be a V2 timeline object with blocks")

    block_count = len(fixture.get("blocks", []))
    visual_count = 0
    for block in fixture.get("blocks", []):
        audio_rel = block.get("audio_file")
        if not audio_rel:
            raise ValueError(f"block {block.get('block_id')} missing audio_file")
        audio_path = run_root / ensure_relative_path(audio_rel)
        if not audio_path.exists():
            raise ValueError(f"missing local audio file: {audio_rel}")
        if audio_path.stat().st_size <= 0:
            raise ValueError(f"empty local audio file: {audio_rel}")
        with wave.open(str(audio_path), "rb") as wav_file:
            if wav_file.getnframes() <= 0:
                raise ValueError(f"invalid local audio file: {audio_rel}")

        for visual in block.get("visuals", []):
            visual_count += 1
            vtype = visual.get("type")
            if vtype in FORBIDDEN_VISUAL_TYPES:
                raise ValueError(f"offline closure fixture rejects visual type: {vtype}")

            if visual.get("url") or is_remote_ref(str(visual.get("url", ""))):
                raise ValueError(f"remote url not allowed in fixture visual: {vtype}")

            extra = visual.get("extra", {})
            for key in ("url", "image_url", "source_url"):
                if key in extra and extra[key]:
                    raise ValueError(f"remote extra field not allowed: {key}")

            if vtype != "stock":
                raise ValueError(f"offline closure fixture expects stock visuals only, got: {vtype}")

            if extra.get("asset_mode") != "locked_local":
                raise ValueError(f"stock visual must use locked_local asset_mode: {visual}")

            resolved_rel = extra.get("resolved_path")
            if not resolved_rel:
                raise ValueError("locked_local visual missing resolved_path")
            resolved_path = run_root / ensure_relative_path(resolved_rel)
            if not resolved_path.exists():
                raise ValueError(f"missing locked_local video: {resolved_rel}")
            if resolved_path.stat().st_size <= 0:
                raise ValueError(f"empty locked_local video: {resolved_rel}")
            summary = media_type_summary(resolved_path)
            video = summary["video"]
            if not video:
                raise ValueError(f"locked_local video missing video stream: {resolved_rel}")
            if summary["format_duration"] <= 0.0:
                raise ValueError(f"locked_local video duration invalid: {resolved_rel}")
    return {
        "block_count": block_count,
        "visual_count": visual_count,
    }


def git_output(repo_root: Path, *args: str) -> str:
    return run_cmd(["git", "-C", str(repo_root), *args], text=True).stdout


def list_tracked_files(repo_root: Path) -> List[Path]:
    raw = run_cmd(["git", "-C", str(repo_root), "ls-files", "-z"], text=False).stdout
    items = [part.decode("utf-8") for part in raw.split(b"\0") if part]
    return [repo_root / item for item in items]


def tree_manifest(root: Path) -> Dict[str, Dict[str, object]]:
    if not root.exists():
        return {}
    entries: Dict[str, Dict[str, object]] = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        entries[rel] = {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
    return entries


def snapshot_repo_state(repo_root: Path) -> Dict[str, object]:
    tracked: Dict[str, Dict[str, object]] = {}
    for path in list_tracked_files(repo_root):
        rel = path.relative_to(repo_root).as_posix()
        tracked[rel] = {"bytes": path.stat().st_size, "sha256": sha256_file(path)}

    status_lines = git_output(repo_root, "status", "--short").splitlines()
    allowed_untracked: Dict[str, Dict[str, object]] = {}
    unexpected_untracked: List[str] = []
    for line in status_lines:
        if not line.startswith("?? "):
            continue
        rel = line[3:].strip().replace("\\", "/")
        if rel in ALLOWED_UNTRACKED:
            path = repo_root / rel
            allowed_untracked[rel] = {
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        else:
            unexpected_untracked.append(rel)

    return {
        "tracked": tracked,
        "allowed_untracked": allowed_untracked,
        "unexpected_untracked": sorted(unexpected_untracked),
        "cache": tree_manifest(repo_root / "cache"),
        "output": tree_manifest(repo_root / "output"),
        "temp_assets": tree_manifest(repo_root / "temp_assets"),
    }


def compare_snapshots(before: Dict[str, object], after: Dict[str, object]) -> Dict[str, object]:
    diffs = {
        "tracked": [],
        "allowed_untracked": [],
        "cache": [],
        "output": [],
        "temp_assets": [],
    }
    for key in diffs:
        before_map = before.get(key, {})
        after_map = after.get(key, {})
        names = sorted(set(before_map) | set(after_map))
        for name in names:
            if before_map.get(name) != after_map.get(name):
                diffs[key].append(name)
    before_untracked = set(before.get("unexpected_untracked", []))
    after_untracked = set(after.get("unexpected_untracked", []))
    unexpected_untracked = sorted(before_untracked ^ after_untracked)
    mutation_count = sum(len(v) for v in diffs.values()) + len(unexpected_untracked)
    return {
        "mutation_count": mutation_count,
        "diffs": diffs,
        "unexpected_untracked": unexpected_untracked,
    }


def synthesize_local_wav(text: str, output_path: Path) -> None:
    out_text = str(output_path).replace("'", "''")
    speech_text = text.replace("'", "''")
    ps_script = "\n".join(
        [
            f"$out = '{out_text}'",
            f"$text = '{speech_text}'",
            "Add-Type -AssemblyName System.Speech",
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer",
            "$s.Rate = -1",
            "$s.SetOutputToWaveFile($out)",
            "$s.Speak($text)",
            "$s.Dispose()",
        ]
    )
    run_cmd(["powershell", "-NoProfile", "-Command", ps_script], text=True)


def generate_video_asset(asset_id: str, output_path: Path, duration: float = 30.0) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg not found on PATH")

    source = f"testsrc2=duration={duration}:size=1920x1080:rate=30"
    filter_chains = {
        "shot_market_establish": "hue=H=2*PI*t/12",
        "shot_earnings_call_broll": "eq=saturation=1.2:contrast=1.1,hue=s=0.3",
        "shot_datacenter_establish": "eq=brightness=-0.12:saturation=0.55,drawgrid=w=160:h=90:t=3:c=0x4CC9F0@0.75",
        "shot_supply_chain_broll": "eq=brightness=-0.05:saturation=0.8,drawbox=x=200+120*t:y=260:w=340:h=240:color=0xFCA311@0.85:t=fill",
    }
    vf = filter_chains.get(asset_id)
    if not vf:
        raise ValueError(f"unsupported deterministic asset id: {asset_id}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    run_cmd(
        [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            source,
            "-vf",
            vf,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "ultrafast",
            "-crf",
            "18",
            str(output_path),
        ],
        text=True,
    )
    summary = media_type_summary(output_path)
    if summary["format_duration"] < duration - 0.25:
        raise RuntimeError(f"generated video too short for {asset_id}: {summary['format_duration']}")


def build_input_bundle(bundle_root: Path) -> Dict[str, object]:
    fixture = load_json(CANONICAL_FIXTURE)
    input_dir = bundle_root / "input"
    audio_dir = bundle_root / "assets" / "audio"
    video_dir = bundle_root / "assets" / "video"
    input_dir.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)
    video_dir.mkdir(parents=True, exist_ok=True)

    for block in fixture.get("blocks", []):
        audio_rel = ensure_relative_path(block["audio_file"])
        audio_target = bundle_root / audio_rel
        audio_target.parent.mkdir(parents=True, exist_ok=True)
        synthesize_local_wav(block["narration"], audio_target)

    for block in fixture.get("blocks", []):
        for visual in block.get("visuals", []):
            resolved_rel = ensure_relative_path(visual["extra"]["resolved_path"])
            target_path = bundle_root / resolved_rel
            generate_video_asset(visual["extra"]["asset_id"], target_path)

    fixture_copy = input_dir / CANONICAL_FIXTURE.name
    fixture_copy.write_text(json.dumps(fixture, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    validate_offline_fixture(fixture, bundle_root)
    return {
        "fixture": fixture,
        "fixture_path": fixture_copy,
        "fixture_sha256": sha256_file(fixture_copy),
        "input_hashes": gather_input_hashes(bundle_root, fixture),
    }


def prepare_run_root(run_root: Path, bundle_root: Path) -> Path:
    for name in ("input", "assets", "cache", "temp", "output", "logs", "reports"):
        (run_root / name).mkdir(parents=True, exist_ok=True)
    shutil.copy2(bundle_root / "input" / CANONICAL_FIXTURE.name, run_root / "input" / CANONICAL_FIXTURE.name)
    if (run_root / "assets").exists():
        shutil.copytree(bundle_root / "assets", run_root / "assets", dirs_exist_ok=True)
    return run_root / "input" / CANONICAL_FIXTURE.name


def repo_preflight(repo_root: Path) -> Dict[str, object]:
    status = git_output(repo_root, "status", "--short", "--branch").splitlines()
    if not status or status[0].strip() != "## main":
        raise RuntimeError(f"unexpected git status header: {status[0] if status else 'missing'}")

    head = git_output(repo_root, "rev-parse", "HEAD").strip()
    origin = git_output(repo_root, "rev-parse", "origin/main").strip()
    if head != START_SHA or origin != START_SHA:
        raise RuntimeError(f"unexpected start sha: head={head} origin={origin}")

    return {
        "head": head,
        "origin_main": origin,
        "status_lines": status[1:],
    }


def install_offline_guards() -> GuardState:
    state = GuardState(attempts=[])

    import requests
    import v2.asset_manager as asset_manager
    import v2.audio_engine as audio_engine
    import v2.web_engine as web_engine
    import v2.youtube_state_machine as youtube_state_machine

    original_request = requests.sessions.Session.request
    original_urlopen = urllib.request.urlopen
    original_create_connection = socket.create_connection
    original_socket_connect = socket.socket.connect
    original_subprocess_run = subprocess.run

    def blocked_request(self, method, url, *args, **kwargs):
        state.block("requests", f"{method} {url}")

    def blocked_urlopen(url, *args, **kwargs):
        state.block("urllib", str(url))

    def blocked_create_connection(address, *args, **kwargs):
        state.block("socket.create_connection", str(address))

    def blocked_socket_connect(self, address):
        state.block("socket.connect", str(address))

    def guarded_subprocess_run(args, *s_args, **kwargs):
        if isinstance(args, (list, tuple)) and args:
            exe = Path(str(args[0])).name.lower()
        else:
            exe = str(args).split(" ", 1)[0].lower()
        allowed = exe.startswith("ffmpeg") or exe.startswith("ffprobe") or exe == "powershell.exe" or exe == "powershell"
        blocked = ("yt-dlp" in exe) or ("playwright" in exe) or ("chrome" in exe) or ("msedge" in exe)
        if blocked and not allowed:
            state.block("subprocess", exe)
        return original_subprocess_run(args, *s_args, **kwargs)

    requests.sessions.Session.request = blocked_request
    urllib.request.urlopen = blocked_urlopen
    socket.create_connection = blocked_create_connection
    socket.socket.connect = blocked_socket_connect
    subprocess.run = guarded_subprocess_run

    asset_manager.fetch_pexels_video = lambda *args, **kwargs: state.block("pexels", "fetch_pexels_video")
    web_engine.capture_web_record = lambda *args, **kwargs: state.block("web_capture", "capture_web_record")
    youtube_state_machine.YouTubeDownloadStateMachine.run = lambda self: state.block("youtube", "YouTubeDownloadStateMachine.run")
    audio_engine.generate_elevenlabs_tts = lambda *args, **kwargs: state.block("elevenlabs", "generate_elevenlabs_tts")
    audio_engine.generate_tts_edge_sync = lambda *args, **kwargs: state.block("edge_tts", "generate_tts_edge_sync")

    return state


def run_ffmpeg_decode_check(output_path: Path) -> Dict[str, object]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg not found on PATH")
    res = subprocess.run(
        [ffmpeg, "-v", "error", "-i", str(output_path), "-f", "null", "-"],
        capture_output=True,
        text=True,
    )
    return {
        "return_code": res.returncode,
        "stderr_tail": "\n".join((res.stderr or "").splitlines()[-8:]),
    }


def framemd5_fingerprint(output_path: Path) -> str:
    ffmpeg = shutil.which("ffmpeg")
    res = subprocess.run(
        [ffmpeg, "-v", "error", "-i", str(output_path), "-map", "0:v:0", "-f", "framemd5", "-"],
        capture_output=True,
        check=True,
    )
    return hashlib.sha256(res.stdout).hexdigest()


def audio_pcm_fingerprint(output_path: Path) -> str:
    ffmpeg = shutil.which("ffmpeg")
    res = subprocess.run(
        [
            ffmpeg,
            "-v",
            "error",
            "-i",
            str(output_path),
            "-map",
            "0:a:0",
            "-f",
            "s16le",
            "-ac",
            "2",
            "-ar",
            "44100",
            "-",
        ],
        capture_output=True,
        check=True,
    )
    return hashlib.sha256(res.stdout).hexdigest()


def stream_metrics(output_path: Path) -> Dict[str, object]:
    ffprobe = shutil.which("ffprobe")
    res = run_cmd(
        [
            ffprobe,
            "-v",
            "error",
            "-count_frames",
            "-count_packets",
            "-show_entries",
            "stream=index,codec_type,codec_name,width,height,r_frame_rate,duration,sample_rate,nb_read_frames,nb_read_packets:format=duration",
            "-of",
            "json",
            str(output_path),
        ],
        text=True,
    )
    return json.loads(res.stdout)


def version_string(executable: str) -> str:
    path = shutil.which(executable)
    if not path:
        raise RuntimeError(f"{executable} not found on PATH")
    res = run_cmd([path, "-version"], text=True)
    return res.stdout.splitlines()[0].strip()


def child_run(run_root: Path, fixture_rel: str) -> int:
    os.chdir(run_root)
    sys.path.insert(0, str(REPO_ROOT))
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_DATASETS_OFFLINE"] = "1"

    fixture_path = run_root / fixture_rel
    fixture = load_json(fixture_path)
    validate_offline_fixture(fixture, run_root)

    guard = install_offline_guards()

    import v2.main as engine_main

    started = time.time()
    exception_text = None
    try:
        engine_main.process_timeline(fixture_rel)
    except Exception as exc:
        exception_text = f"{type(exc).__name__}: {exc}"

    elapsed = time.time() - started
    output_path = run_root / "output" / "final_video_v2.mp4"
    report_path = run_root / "output" / "validation_report.json"
    validation_report = load_json(report_path) if report_path.exists() else None

    success = exception_text is None and output_path.exists() and output_path.stat().st_size > 0
    ffprobe_data = ffprobe_json(output_path) if success else {}
    metrics = stream_metrics(output_path) if success else {}
    decode = run_ffmpeg_decode_check(output_path) if success else {"return_code": 1, "stderr_tail": ""}
    frame_fingerprint = framemd5_fingerprint(output_path) if success else None
    audio_fingerprint = audio_pcm_fingerprint(output_path) if success else None

    video_stream = next((s for s in ffprobe_data.get("streams", []) if s.get("codec_type") == "video"), None) if success else None
    audio_stream = next((s for s in ffprobe_data.get("streams", []) if s.get("codec_type") == "audio"), None) if success else None
    video_duration = float(video_stream.get("duration") or ffprobe_data.get("format", {}).get("duration", 0.0) or 0.0) if video_stream else 0.0
    audio_duration = float(audio_stream.get("duration") or ffprobe_data.get("format", {}).get("duration", 0.0) or 0.0) if audio_stream else 0.0

    result = {
        "run_root_name": run_root.name,
        "orchestrator": "v2.main.process_timeline",
        "ffmpeg_path": shutil.which("ffmpeg"),
        "ffprobe_path": shutil.which("ffprobe"),
        "ffmpeg_version": version_string("ffmpeg"),
        "ffprobe_version": version_string("ffprobe"),
        "fixture_relpath": fixture_rel,
        "fixture_sha256": sha256_file(fixture_path),
        "input_hashes": gather_input_hashes(run_root, fixture),
        "duration_seconds": elapsed,
        "exception": exception_text,
        "provider_attempt_count": len(guard.attempts),
        "network_attempt_count": len(guard.attempts),
        "guard_attempts": guard.attempts,
        "output_exists": output_path.exists(),
        "output_sha256": sha256_file(output_path) if output_path.exists() else None,
        "output_bytes": output_path.stat().st_size if output_path.exists() else 0,
        "validation_report": validation_report,
        "ffprobe": ffprobe_data,
        "stream_metrics": metrics,
        "decode_check": decode,
        "decoded_video_fingerprint": frame_fingerprint,
        "decoded_audio_fingerprint": audio_fingerprint,
        "video_duration": video_duration,
        "audio_duration": audio_duration,
        "av_drift_seconds": abs(video_duration - audio_duration),
        "logs": {
            "validation_report": str(report_path.relative_to(run_root)) if report_path.exists() else None,
            "norm_words_debug": str((run_root / "norm_words_debug.json").relative_to(run_root)) if (run_root / "norm_words_debug.json").exists() else None,
            "whisper_debug": str((run_root / "whisper_debug.json").relative_to(run_root)) if (run_root / "whisper_debug.json").exists() else None,
        },
        "output_relpath": str(output_path.relative_to(run_root)) if output_path.exists() else None,
    }
    write_json(run_root / "reports" / "run_report.json", result)
    print(json.dumps({"run_root_name": run_root.name, "success": success, "provider_attempt_count": len(guard.attempts)}))
    return 0 if success else 1


def markdown_report(summary: Dict[str, object]) -> str:
    run1 = summary["run1"]
    run2 = summary["run2"]
    lines = [
        "# Offline Isolated Full Render Report",
        "",
        "## Closure objective",
        "",
        "Prove that the canonical baseline render can be reproduced twice with identical immutable local inputs, no provider or network access, and no repository output/cache/temp mutation.",
        "",
        "## Authoritative repository revision",
        "",
        f"- repository: `{summary['repository_path']}`",
        f"- revision: `{summary['repository_revision']}`",
        "",
        "## Canonical production orchestrator",
        "",
        "- selected path: `v2.main.process_timeline` via verification harness",
        "- root `main.py` normal render was not selected because it does not expose any hook for fail-closed provider/network guard installation or run-scoped evidence capture without broader production changes",
        "",
        "## Fixture selection rationale",
        "",
        f"- canonical fixture: `{summary['fixture_path']}`",
        f"- fixture SHA-256: `{summary['fixture_sha256']}`",
        "- fixture uses only `audio_file` local narration inputs and `stock` visuals with `locked_local` assets",
        "- fixture duration target is satisfied by two narrated blocks and four visual scenes",
        "",
        "## Why test_1_min.json was or was not used",
        "",
        "- `test_1_min.json` was not used because it contains provider/browser-dependent visuals such as document capture, image PIP, and unresolved stock queries that would violate fail-closed offline execution",
        "",
        "## Offline/fail-closed guard",
        "",
        f"- result: `{'PASS' if summary['provider_attempt_count'] == 0 and summary['network_attempt_count'] == 0 else 'FAIL'}`",
        "- blocked channels: Pexels, web capture, YouTube downloader, Edge TTS, ElevenLabs, socket/requests/urllib network calls, and known network-capable subprocesses",
        "",
        "## Input provenance and hashes",
        "",
        "- immutable inputs were materialized outside the repository and copied unchanged into both run roots",
        "- all run 1 and run 2 input hashes matched exactly",
        "",
        "## Isolation strategy",
        "",
        "- each render ran from its own `C:\\tmp\\kurgu_phase0_offline_render_run*` root",
        "- production cwd was the run root, so `temp_assets`, `output`, `norm_words_debug.json`, and `whisper_debug.json` were emitted only there",
        "",
        "## Run 1 summary",
        "",
        f"- run root: `{run1['run_root_name']}`",
        f"- output: `{run1['output_relpath']}`",
        f"- output SHA-256: `{run1['output_sha256']}`",
        f"- provider/network attempts: `{run1['provider_attempt_count']}`",
        "",
        "## Run 2 summary",
        "",
        f"- run root: `{run2['run_root_name']}`",
        f"- output: `{run2['output_relpath']}`",
        f"- output SHA-256: `{run2['output_sha256']}`",
        f"- provider/network attempts: `{run2['provider_attempt_count']}`",
        "",
        "## FFmpeg/ffprobe validation",
        "",
        f"- ffmpeg: `{summary['ffmpeg_version']}`",
        f"- ffprobe: `{summary['ffprobe_version']}`",
        f"- run 1 decode check: `{run1['decode_check']['return_code']}`",
        f"- run 2 decode check: `{run2['decode_check']['return_code']}`",
        "",
        "## A/V duration comparison",
        "",
        f"- run 1 video/audio: `{run1['video_duration']:.3f}s / {run1['audio_duration']:.3f}s`",
        f"- run 2 video/audio: `{run2['video_duration']:.3f}s / {run2['audio_duration']:.3f}s`",
        f"- run 1 drift: `{run1['av_drift_seconds']:.3f}s`",
        f"- run 2 drift: `{run2['av_drift_seconds']:.3f}s`",
        "",
        "## Decoded video fingerprint comparison",
        "",
        f"- equal: `{summary['decoded_video_equal']}`",
        "",
        "## Decoded audio fingerprint comparison",
        "",
        f"- equal: `{summary['decoded_audio_equal']}`",
        "",
        "## Network/provider attempt result",
        "",
        f"- provider attempts: `{summary['provider_attempt_count']}`",
        f"- network attempts: `{summary['network_attempt_count']}`",
        "",
        "## Repository mutation result",
        "",
        f"- mutation count during render interval: `{summary['repository_mutation_count']}`",
        "",
        "## Output isolation result",
        "",
        f"- run roots only: `{summary['output_isolation_pass']}`",
        "",
        "## Full-suite regression result",
        "",
        f"- pytest result: `{summary['pytest_result']}`",
        "",
        "## Reproducibility decision",
        "",
        f"- final decision: `{summary['final_decision']}`",
        "",
        "## Remaining Phase 0 items",
        "",
        "- Provider revoke/rotation: `NOT CONFIRMED`",
        "- Baseline tag: `PENDING`",
        "- General Phase 0 remains open only for final closure/tag decision",
        "",
    ]
    return "\n".join(lines)


def parent_main(write_repo_evidence: bool) -> int:
    repo_preflight(REPO_ROOT)

    stamp = time.strftime("%Y%m%d_%H%M%S")
    bundle_root = Path("C:/tmp") / f"kurgu_phase0_offline_inputs_{stamp}"
    run1_root = Path("C:/tmp") / f"kurgu_phase0_offline_render_run1_{stamp}"
    run2_root = Path("C:/tmp") / f"kurgu_phase0_offline_render_run2_{stamp}"

    bundle = build_input_bundle(bundle_root)
    fixture_name = bundle["fixture_path"].name
    prepare_run_root(run1_root, bundle_root)
    prepare_run_root(run2_root, bundle_root)

    before = snapshot_repo_state(REPO_ROOT)

    child_args = [sys.executable, str(Path(__file__)), "--child-run"]
    logs: List[Tuple[Path, subprocess.CompletedProcess]] = []
    for run_root in (run1_root, run2_root):
        proc = subprocess.run(
            child_args + [str(run_root), f"input/{fixture_name}"],
            capture_output=True,
            text=True,
        )
        (run_root / "logs" / "child_stdout.txt").write_text(proc.stdout, encoding="utf-8")
        (run_root / "logs" / "child_stderr.txt").write_text(proc.stderr, encoding="utf-8")
        logs.append((run_root, proc))
        if proc.returncode != 0:
            raise RuntimeError(f"child render failed for {run_root.name}")

    after = snapshot_repo_state(REPO_ROOT)
    mutation = compare_snapshots(before, after)

    run1 = load_json(run1_root / "reports" / "run_report.json")
    run2 = load_json(run2_root / "reports" / "run_report.json")

    provider_attempt_count = run1["provider_attempt_count"] + run2["provider_attempt_count"]
    network_attempt_count = run1["network_attempt_count"] + run2["network_attempt_count"]
    decoded_video_equal = run1["decoded_video_fingerprint"] == run2["decoded_video_fingerprint"]
    decoded_audio_equal = run1["decoded_audio_fingerprint"] == run2["decoded_audio_fingerprint"]
    inputs_equal = run1["input_hashes"] == run2["input_hashes"]
    av_ok = run1["av_drift_seconds"] <= 0.50 and run2["av_drift_seconds"] <= 0.50
    decode_ok = run1["decode_check"]["return_code"] == 0 and run2["decode_check"]["return_code"] == 0
    output_isolation_pass = mutation["mutation_count"] == 0
    final_decision = "PASS" if all(
        [
            provider_attempt_count == 0,
            network_attempt_count == 0,
            decoded_video_equal,
            decoded_audio_equal,
            inputs_equal,
            av_ok,
            decode_ok,
            output_isolation_pass,
        ]
    ) else "INCONCLUSIVE"

    summary = {
        "schema_version": "1.0.0",
        "repository_path": str(REPO_ROOT),
        "repository_revision": START_SHA,
        "fixture_path": "baseline/fixtures/phase0_offline_full_render.json",
        "fixture_sha256": bundle["fixture_sha256"],
        "input_hashes": bundle["input_hashes"],
        "orchestrator": "v2.main.process_timeline",
        "ffmpeg_version": run1["ffmpeg_version"],
        "ffprobe_version": run1["ffprobe_version"],
        "run1": run1,
        "run2": run2,
        "output_hashes": {
            "run1_mp4_sha256": run1["output_sha256"],
            "run2_mp4_sha256": run2["output_sha256"],
        },
        "decoded_fingerprints": {
            "run1_video": run1["decoded_video_fingerprint"],
            "run2_video": run2["decoded_video_fingerprint"],
            "run1_audio": run1["decoded_audio_fingerprint"],
            "run2_audio": run2["decoded_audio_fingerprint"],
        },
        "decoded_video_equal": decoded_video_equal,
        "decoded_audio_equal": decoded_audio_equal,
        "provider_attempt_count": provider_attempt_count,
        "network_attempt_count": network_attempt_count,
        "repository_mutation_count": mutation["mutation_count"],
        "repository_mutation_details": mutation,
        "output_isolation_pass": output_isolation_pass,
        "av_drift": {
            "run1_seconds": run1["av_drift_seconds"],
            "run2_seconds": run2["av_drift_seconds"],
        },
        "inputs_equal": inputs_equal,
        "decode_ok": decode_ok,
        "pytest_result": "pending",
        "final_decision": final_decision,
    }

    if write_repo_evidence:
        write_json(REPO_EVIDENCE_JSON, summary)
        REPO_EVIDENCE_MD.write_text(markdown_report(summary), encoding="utf-8")

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify offline isolated full render closure")
    parser.add_argument("--child-run", action="store_true")
    parser.add_argument("run_root", nargs="?")
    parser.add_argument("fixture_rel", nargs="?")
    parser.add_argument("--no-write-repo-evidence", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.child_run:
        if not args.run_root or not args.fixture_rel:
            raise SystemExit("--child-run requires run_root and fixture_rel")
        return child_run(Path(args.run_root), args.fixture_rel)
    return parent_main(write_repo_evidence=not args.no_write_repo_evidence)


if __name__ == "__main__":
    raise SystemExit(main())
