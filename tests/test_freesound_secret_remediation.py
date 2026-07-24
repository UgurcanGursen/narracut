from importlib import import_module, reload
from unittest.mock import Mock, patch

from v2 import config


def _load_download_assets():
    module = import_module("download_assets")
    return reload(module)


def test_config_reads_freesound_key_from_environment(monkeypatch):
    marker = "unit-test-key"
    monkeypatch.setenv("FREESOUND_API_KEY", f"  {marker}  ")

    assert config.get_freesound_api_key() == marker


def test_config_has_empty_freesound_default_without_environment(monkeypatch):
    monkeypatch.delenv("FREESOUND_API_KEY", raising=False)

    assert config.get_freesound_api_key() == ""


def test_missing_key_skips_freesound_http(monkeypatch):
    monkeypatch.delenv("FREESOUND_API_KEY", raising=False)
    module = _load_download_assets()

    with patch.object(module.requests, "get") as mock_get:
        result = module.fetch_audio_results("test query", "type:mp3", 3)

    assert result == []
    mock_get.assert_not_called()


def test_present_key_uses_environment_value_for_search_request(monkeypatch):
    marker = "unit-test-key"
    monkeypatch.setenv("FREESOUND_API_KEY", marker)
    module = _load_download_assets()
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "results": [
            {
                "id": 1,
                "name": "whoosh",
                "previews": {"preview-hq-mp3": "https://example.test/preview.mp3"},
                "download": "https://example.test/download",
                "duration": 1.25,
            }
        ]
    }

    with patch.object(module.requests, "get", return_value=response) as mock_get:
        result = module.fetch_audio_results("test query", "type:mp3", 1)

    assert result == response.json.return_value["results"]
    _, kwargs = mock_get.call_args
    assert kwargs["params"]["token"] == marker


def test_import_is_safe_without_key(monkeypatch):
    monkeypatch.delenv("FREESOUND_API_KEY", raising=False)

    with patch("requests.get") as mock_get:
        module = _load_download_assets()

    assert module.get_freesound_api_key() == ""
    mock_get.assert_not_called()


def test_download_uses_environment_value_for_authorization_header(monkeypatch, tmp_path):
    marker = "unit-test-key"
    monkeypatch.setenv("FREESOUND_API_KEY", marker)
    module = _load_download_assets()
    dest_path = tmp_path / "preview.mp3"

    response = Mock()
    response.raise_for_status.return_value = None
    response.iter_content.return_value = [b"abc", b"def"]
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)

    with patch.object(module.requests, "get", return_value=response) as mock_get:
        result = module.download_file("https://example.test/preview.mp3", str(dest_path))

    assert result is True
    assert dest_path.read_bytes() == b"abcdef"
    _, kwargs = mock_get.call_args
    assert kwargs["headers"]["Authorization"] == f"Token {marker}"


def test_static_freesound_secret_regression():
    with open("download_assets.py", "r", encoding="utf-8") as handle:
        download_assets_source = handle.read()

    with open(".env.example", "r", encoding="utf-8") as handle:
        env_example = handle.read()

    assert 'FREESOUND_API_KEY = "' not in download_assets_source
    assert 'FREESOUND_API_KEY="' not in download_assets_source
    assert "FREESOUND_API_KEY=\n" in env_example or "FREESOUND_API_KEY=\r\n" in env_example
