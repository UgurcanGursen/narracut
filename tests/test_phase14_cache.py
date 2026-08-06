import pytest
from engine.cache import cache_key, storage_usage

def test_cache_key_is_deterministic_and_profile_isolated():
    assert cache_key(profile="preview", inputs={"source":"sha256:x"}) == cache_key(profile="preview", inputs={"source":"sha256:x"})
    assert cache_key(profile="preview", inputs={"source":"sha256:x"}) != cache_key(profile="production", inputs={"source":"sha256:x"})
    with pytest.raises(ValueError): cache_key(profile="other", inputs={})

def test_storage_usage_is_read_only(tmp_path):
    (tmp_path / "a").write_bytes(b"abc")
    assert storage_usage(tmp_path) == {"file_count":1,"bytes":3}
