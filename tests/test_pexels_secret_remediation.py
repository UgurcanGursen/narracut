from unittest.mock import patch

from v2 import asset_manager, config


def test_config_reads_pexels_key_from_environment(monkeypatch):
    marker = "unit-test-config-value"
    monkeypatch.setenv("PEXELS_API_KEY", marker)

    assert config.get_pexels_api_key() == marker


def test_config_has_empty_default_without_environment(monkeypatch):
    monkeypatch.delenv("PEXELS_API_KEY", raising=False)

    assert config.get_pexels_api_key() == ""


def test_missing_key_skips_http_and_returns_none_without_local_assets():
    with (
        patch.object(asset_manager, "PEXELS_API_KEY", ""),
        patch.object(asset_manager.requests, "get") as mock_get,
        patch.object(asset_manager.os.path, "isdir", return_value=False),
    ):
        result = asset_manager.fetch_pexels_video("test query")

    assert result is None
    mock_get.assert_not_called()


def test_missing_key_preserves_local_metadata_contract(tmp_path):
    local_asset = tmp_path / "local-stock.mp4"
    local_asset.write_bytes(b"local-test-asset")

    with (
        patch.object(asset_manager, "PEXELS_API_KEY", ""),
        patch.object(asset_manager.requests, "get") as mock_get,
        patch.object(asset_manager.os.path, "isdir", return_value=True),
        patch.object(
            asset_manager.glob,
            "glob",
            return_value=[str(local_asset)],
        ),
    ):
        result = asset_manager.resolve_visual_asset(
            "stock",
            query="test query",
            scene_id="secret-remediation-test",
        )

    mock_get.assert_not_called()
    assert result["path"] == str(local_asset)
    assert result["type_used"] == "stock"
    assert result["asset_provider"] == "local"
    assert result["review_required"] is True
    assert result["content_fingerprint"]


def test_request_failure_does_not_log_credential(capsys):
    marker = "unit-test-log-marker"

    with (
        patch.object(asset_manager, "PEXELS_API_KEY", marker),
        patch.object(
            asset_manager.requests,
            "get",
            side_effect=RuntimeError(marker),
        ),
    ):
        result = asset_manager.fetch_pexels_video(
            "test query",
            allow_generic=False,
        )

    captured = capsys.readouterr()
    assert result is None
    assert marker not in captured.out
    assert marker not in captured.err
