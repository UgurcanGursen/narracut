"""Phase 4B checked-in profile/provenance fixture admission tests.

These are deliberately filesystem-only.  They prove the REPLAY catalog can be
selected from canonical checked-in bytes without PATH, package-manager, URL or
network discovery.  Runtime preflight and child execution belong to the full
render adapter, not to this fixture boundary.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "renderer-remotion" / "profiles" / "full-render-profiles-v1.json"
PROVENANCE_PATH = ROOT / "tests" / "fixtures" / "phase4b" / "full-render-toolchain-provenance-v1.json"
LOCK_PATH = ROOT / "renderer-remotion" / "package-lock.json"
_HASH_PREFIX = "sha256:"


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha(value: object) -> str:
    return _HASH_PREFIX + hashlib.sha256(_canonical(value)).hexdigest()


def _load_canonical(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    parsed = json.loads(raw)
    # Repository text files end with one LF; the JSON payload itself has no
    # non-canonical whitespace or key ordering drift.
    assert raw in {_canonical(parsed), _canonical(parsed) + b"\n"}, f"{path.name} must be canonical JSON bytes"
    return parsed


def _profile_hash(profile: dict[str, object]) -> str:
    return _sha({key: value for key, value in profile.items() if key not in {"profile_id", "profile_hash"}})


def test_replay_catalog_is_canonical_closed_and_profile_self_identifying() -> None:
    catalog = _load_canonical(CATALOG_PATH)
    assert set(catalog) == {"profiles", "schema_version"}
    assert catalog["schema_version"] == "FULL-RENDER-PROFILE-CATALOG-V1"
    profiles = catalog["profiles"]
    assert isinstance(profiles, list) and len(profiles) == 1
    profile = profiles[0]
    assert isinstance(profile, dict)
    assert set(profile) == {
        "schema_version", "profile_id", "profile_hash", "remotion_composition_id",
        "width", "height", "fps_numerator", "fps_denominator", "video_codec",
        "pixel_format", "audio_codec", "sample_rate_hz", "channel_layout", "container",
        "remotion_identity", "node_identity", "ffmpeg_identity", "ffprobe_identity",
        "remotion_render_argv", "ffmpeg_normalize_argv", "ffmpeg_mux_encode_argv",
        "ffprobe_argv", "stage_timeout_seconds", "probe_expectation",
    }
    assert profile["schema_version"] == "FULL-RENDER-PROFILE-V1"
    assert profile["profile_id"] == "frp_phase4b_replay_win32_x64"
    assert profile["profile_hash"] == _profile_hash(profile)
    assert (profile["width"], profile["height"], profile["fps_numerator"], profile["fps_denominator"]) == (1280, 720, 30, 1)
    assert (profile["sample_rate_hz"], profile["channel_layout"], profile["container"]) == (48000, "stereo", "mp4")


def test_profile_toolchain_identities_are_closed_hash_bound_and_do_not_encode_host_roots() -> None:
    profile = _load_canonical(CATALOG_PATH)["profiles"][0]
    assert isinstance(profile, dict)
    expected = {
        "node_identity": {"executable_relative_posix_path", "executable_sha256", "normalized_first_version_line", "toolchain_root_relative_posix_path", "version_output_sha256"},
        "remotion_identity": {"cli_entry_relative_posix_path", "cli_entry_sha256", "normalized_version_line", "toolchain_root_relative_posix_path", "version_output_sha256"},
        "ffmpeg_identity": {"executable_relative_posix_path", "executable_sha256", "normalized_first_version_line", "toolchain_root_relative_posix_path", "version_output_sha256"},
        "ffprobe_identity": {"executable_relative_posix_path", "executable_sha256", "normalized_first_version_line", "toolchain_root_relative_posix_path", "version_output_sha256"},
    }
    for key, fields in expected.items():
        identity = profile[key]
        assert isinstance(identity, dict) and set(identity) == fields
        root = identity["toolchain_root_relative_posix_path"]
        executable = identity.get("executable_relative_posix_path", identity.get("cli_entry_relative_posix_path"))
        line = identity.get("normalized_first_version_line", identity.get("normalized_version_line"))
        assert isinstance(root, str) and root and "/" not in root and "\\" not in root and ":" not in root
        assert isinstance(executable, str) and executable and "/" not in executable and "\\" not in executable and ":" not in executable
        assert isinstance(line, str) and line and "\n" not in line
        assert identity["version_output_sha256"] == _HASH_PREFIX + hashlib.sha256(line.encode("utf-8")).hexdigest()
        digest_key = "cli_entry_sha256" if key == "remotion_identity" else "executable_sha256"
        assert isinstance(identity[digest_key], str) and len(identity[digest_key]) == 71 and identity[digest_key].startswith(_HASH_PREFIX)


def test_provenance_fixture_binds_catalog_lock_and_every_identity_without_network_selection() -> None:
    catalog = _load_canonical(CATALOG_PATH)
    profile = catalog["profiles"][0]
    assert isinstance(profile, dict)
    provenance = _load_canonical(PROVENANCE_PATH)
    assert set(provenance) == {
        "schema_version", "provenance_fixture_id", "provenance_fixture_hash", "profile_catalog_sha256",
        "package_lock_sha256", "supported_platform", "runtime_trees",
    }
    assert provenance["schema_version"] == "FULL-RENDER-TOOLCHAIN-PROVENANCE-V1"
    assert provenance["provenance_fixture_id"] == "frtprov_phase4b_replay_win32_x64"
    assert provenance["profile_catalog_sha256"] == _HASH_PREFIX + hashlib.sha256(_canonical(catalog)).hexdigest()
    assert provenance["package_lock_sha256"] == _HASH_PREFIX + hashlib.sha256(LOCK_PATH.read_bytes()).hexdigest()
    assert provenance["provenance_fixture_hash"] == _sha({key: value for key, value in provenance.items() if key not in {"provenance_fixture_id", "provenance_fixture_hash"}})
    rows = provenance["runtime_trees"]
    assert isinstance(rows, list) and [row["kind"] for row in rows] == ["node", "remotion", "ffmpeg", "ffprobe"]
    for row, identity_key in zip(rows, ("node_identity", "remotion_identity", "ffmpeg_identity", "ffprobe_identity"), strict=True):
        assert set(row) == {"kind", "toolchain_root_relative_posix_path", "identity_hash"}
        assert row["toolchain_root_relative_posix_path"] == profile[identity_key]["toolchain_root_relative_posix_path"]
        assert row["identity_hash"] == _sha(profile[identity_key])
    # The immutable REPLAY evidence names only relative layout keys and contains
    # no discovery or fetch channel; a later adapter must receive paired roots explicitly.
    text = CATALOG_PATH.read_text(encoding="utf-8") + PROVENANCE_PATH.read_text(encoding="utf-8")
    forbidden = ("http://", "https://", "npm", "npx", "PATH", "where", "registry", "download", "\\\\", "C:\\")
    assert not any(value in text for value in forbidden)
