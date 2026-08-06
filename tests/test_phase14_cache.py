import pytest
from engine.cache import cache_get, cache_key, cache_put, incremental_action, quota_status, storage_usage

def test_cache_key_is_deterministic_and_profile_isolated():
    assert cache_key(profile="preview", inputs={"source":"sha256:x"}) == cache_key(profile="preview", inputs={"source":"sha256:x"})
    assert cache_key(profile="preview", inputs={"source":"sha256:x"}) != cache_key(profile="production", inputs={"source":"sha256:x"})
    with pytest.raises(ValueError): cache_key(profile="other", inputs={})

def test_storage_usage_is_read_only(tmp_path):
    (tmp_path / "a").write_bytes(b"abc")
    assert storage_usage(tmp_path) == {"file_count":1,"bytes":3}

def test_cache_store_round_trip(tmp_path):
    key = cache_key(profile="preview", inputs={"x":1})
    cache_put(tmp_path, key, b"cached")
    assert cache_get(tmp_path, key) == b"cached"

def test_quota_status_is_read_only_and_validated():
    assert quota_status(used_bytes=5, soft_limit_bytes=10, hard_limit_bytes=20) == "OK"
    assert quota_status(used_bytes=10, soft_limit_bytes=10, hard_limit_bytes=20) == "SOFT_LIMIT"
    assert quota_status(used_bytes=20, soft_limit_bytes=10, hard_limit_bytes=20) == "HARD_LIMIT"

def test_incremental_action_never_reuses_changed_key():
    key = cache_key(profile="preview", inputs={"x":1})
    assert incremental_action(previous_key=key, current_key=key) == "REUSE"
    assert incremental_action(previous_key=key, current_key=cache_key(profile="preview", inputs={"x":2})) == "REBUILD"
