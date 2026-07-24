# Faz 0.3 — Pexels Stale Test Contract Alignment Report

Tarih: 24 Temmuz 2026
Authoritative revision: `d84680b4778ba18e8e182ce7049c3a450dd906b1`

## Reproduced failure

Değişiklik öncesi kalan tek failure:
`tests/test_v2_core.py::TestV2Core::test_pexels_key_missing_fallback`

Eski beklenti:

```text
fetch_pexels_video("test") -> "assets/videos/test.mp4"
```

Gerçek canonical production davranışı:

```text
fetch_pexels_video("test") -> {
  "path": "assets/videos/test.mp4",
  "url": "local:test.mp4",
  "title": "test.mp4",
  "provider": "local",
  "review_required": true
}
```

Local fallback yoksa dönüş `None` olur.

## Verified production chain

```text
v2.config.get_pexels_api_key()
→ v2.config.PEXELS_API_KEY
→ v2.asset_manager.fetch_pexels_video()
→ v2.asset_manager.resolve_visual_asset()
```

- Missing key: HTTP çağrısı yapılmaz.
- Local fallback: canonical metadata dict döner.
- No fallback: `None` döner.
- `resolve_visual_asset`, dict sözleşmesini `asset_provider`,
  `review_required` ve `content_fingerprint` alanlarına taşır.

## Test change

Yalnız `tests/test_v2_core.py` güncellendi.

- Eski string-path assertion kaldırıldı.
- Local fallback için `path`, `url`, `title`, `provider` ve
  `review_required` doğrulandı.
- `requests.get` patched kalarak missing-key HTTP no-call davranışı kontrol
  edildi.
- Local fallback yokken `None` dalı korunarak doğrulandı.

Production kodu değiştirilmedi.

## Verification

| Komut | Sonuç |
|---|---|
| `python -m pytest -q tests/test_v2_core.py::TestV2Core::test_pexels_key_missing_fallback tests/test_pexels_secret_remediation.py --basetemp C:\tmp\kurgu_phase03_targeted_20260724` | `6 passed` |
| `python -m pytest -q --basetemp C:\tmp\kurgu_phase03_full_20260724` | `42 passed` |
| `python -m py_compile tests/test_v2_core.py` | PASS |

## Remaining Faz 0 blockers

- Provider revoke/rotation teyidi
- System `ffmpeg` / `ffprobe` preflight
- Isolated, fail-closed offline full-render reproduction
