# Changelog

## 2026-07-25 - Faz 1 JSON Schema validator dependency provisioning

- `jsonschema[format]==4.26.0` canonical dependency olarak `requirements.txt`'ye eklendi
- Aktif Python ortaminda `python -m pip install "jsonschema[format]==4.26.0"` PASS
- `python -m pip check` PASS
- `Draft202012Validator.check_schema` ve `FormatChecker` runtime dogrulamasi PASS
- Yeni smoke test `tests/test_jsonschema_dependency.py` eklendi
- Hedefli test: `2 passed`
- Full suite: `58 passed`
- Faz 1 contract-foundation blocker: READY_TO_RESUME
- Faz 0 status: CLOSED

## 2026-07-25 - Faz 0 final baseline closure

- Final preflight temiz dogrulandi: branch `main`, local/remote HEAD `d1cac1ef27ad1c3977c62aed7a9de3691dc81223`, local/remote `stage3-development-baseline` yok, parentless sanitized root zinciri korundu
- Existing Phase 0 evidence artifacts birbirleriyle tutarli dogrulandi
- Final quality gate tekrarlandi: `56 passed`, JSON parse PASS, `git diff --check` PASS, `git fsck --full` clean, current/reachable Freesound/Pexels/generic secret scan `0`
- Final closure report `baseline/phase0_final_closure_report.md` eklendi
- Faz 0 technical acceptance: PASS
- Faz 0 management closure: PASS
- Faz 0 status: CLOSED
- Provider revoke/rotation: **NOT CONFIRMED** ve ayri security follow-up olarak korundu
- Siradaki ana faz: `Faz 1 - Editorial Domain Model ve V3 Workspace Schema`

## 2026-07-24 - Faz 0 offline isolated full-render closure

- Canonical closure fixture `baseline/fixtures/phase0_offline_full_render.json` eklendi
- Verification harness `scripts/verify_phase0_offline_render.py` ile gercek `v2.main.process_timeline` orchestration'i iki izole run root'ta calistirildi
- Root `main.py` yerine harness kullanimi, fail-closed guard ve run-scoped evidence capture hook'u gerektirdigi icin belgelendi
- Her iki run icin provider/network attempt sayisi `0`, repository mutation sayisi `0` ve output isolation PASS olarak dogrulandi
- Final MP4'ler `h264` video + `aac` audio ile gecerli, decode PASS, A/V drift `0.003s`
- Run 1 ve Run 2 decoded video fingerprint'leri eslesti
- Run 1 ve Run 2 decoded audio fingerprint'leri eslesti
- Full regression suite `56 passed`
- Offline isolated full render: PASS
- Fail-closed provider/network gate: PASS
- Two-run decoded-content reproducibility: PASS
- Faz 0 technical acceptance gates: PASS
- Provider revoke/rotation: **NOT CONFIRMED**
- Baseline tag: PENDING
- General Phase 0: OPEN pending final closure/tag decision

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
