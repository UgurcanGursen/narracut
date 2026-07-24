# Changelog

## 2026-07-24 - Faz 0.4B-S2 Freesound history replacement verified

### Verified

- Parentless sanitized root commit `49d57a5f05366df7779af277a36f949c74984f55` olusturuldu
- Live `origin/main` exact `--force-with-lease` ile eski SHA `1ba85a7e33dca034503f7b09878deb10689e3080` uzerinden degistirildi
- Fresh post-push clone `C:\Users\user\Documents\Kurgu_V3_Clean_freesound_postpush_verify_20260724_230300000` ile root history, blob parity, secret absence ve `49 passed` full suite dogrulandi
- Freesound current-tree remediation: PASS
- Freesound reachable main history remediation: PASS
- Remote replacement verification: PASS

### Still open

- Provider revoke/rotation: **NOT CONFIRMED**
- Drawtext operational gate: PASS with explicit fontfile / default Fontconfig known limitation
- Offline isolated full render: OPEN
- General Phase 0: OPEN

## 2026-07-24 - Faz 0 drawtext / Fontconfig operational gate closure

- Accepted paired `ffmpeg` / `ffprobe` runtime revalidated on the authoritative sanitized repository
- Default `drawtext` invocation reproduced the expected Fontconfig config-file failure
- Verified Windows font `C:\WINDOWS\Fonts\segoeui.ttf` used with escaped `fontfile=` strategy
- Explicit-font `drawtext` render passed with real frame-hash difference and valid `ffprobe` metadata
- Production inventory confirmed ordinary subtitles and text overlays use PIL/MoviePy rather than `drawtext`
- Only verified production `drawtext` call-site is the stock local-fallback generator in `v2.asset_manager.py`
- Drawtext capability decision: `DRAWTEXT_OPERATIONAL_WITH_EXPLICIT_FONTFILE`
- Faz 0 blocker decision: `NOT_A_BASELINE_BLOCKER`

## 2026-07-24 - Faz 0.4B existing paired runtime verification

- Existing paired runtime accepted
- drawtext practical invocation initially appeared blocked by Fontconfig before explicit-font verification

## 2026-07-24 - Faz 0.1B through Faz 0.4A recap

- Freesound current-tree remediation accepted
- Existing paired runtime verified
- Baseline tag not created
