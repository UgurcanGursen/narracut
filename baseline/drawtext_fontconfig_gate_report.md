# Drawtext / Fontconfig Gate Report

## Environment and binary identity

- Authoritative repository: `C:\Users\user\Documents\Kurgu_V3_Clean_sanitized_freesound_20260724_224147304`
- Checked on: 24 Temmuz 2026
- `ffmpeg`: `C:\Users\user\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin\ffmpeg.EXE`
- `ffprobe`: `C:\Users\user\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin\ffprobe.EXE`
- Paired runtime identity: PASS
- Relevant FFmpeg config flags observed in runtime preflight: `--enable-fontconfig`, `--enable-libfreetype`, `--enable-libfribidi`, `--enable-libharfbuzz`

## Original drawtext failure

- Synthetic default-font command was reproduced in isolated temp root `C:\tmp\kurgu_drawtext_gate_wo7qoxcx`
- Return code: `3221225477`
- Output file: not created
- Failure point: filter initialization after lavfi input opened
- Key classification signal: `Fontconfig error: Cannot load default config file: File not found`

## Fontconfig failure classification

- Failure is not `drawtext filter missing`
- Failure is not `ffmpeg` / `ffprobe` binary resolution
- Failure is default Fontconfig discovery on this Windows environment
- Classification: environment limitation affecting implicit font selection only

## Verified Windows font

- Selected font path: `C:\WINDOWS\Fonts\segoeui.ttf`
- Selection order used: `segoeui.ttf`, `arial.ttf`, `calibri.ttf`, then first readable `.ttf` / `.otf`
- File state: exists, regular file, non-zero size, readable

## Explicit fontfile command strategy

- Command style: subprocess argument list, not shell filter string expansion
- Synthetic source: `color=c=black:s=320x180:d=2`
- Deterministic filter: `drawtext=fontfile='C\\:/WINDOWS/Fonts/segoeui.ttf':text='Kurgu Engine':x=20:y=60:fontsize=28:fontcolor=white`
- Windows drive-letter handling: colon escaped as `C\\:`

## Explicit fontfile result

- Return code: `0`
- Output file created: yes
- Output size: `4392` bytes
- `ffprobe` JSON parse: PASS
- Video stream present: yes
- Codec: `h264`
- Width x height: `320x180`
- Duration: `2.0` seconds
- Capability decision: `DRAWTEXT_OPERATIONAL_WITH_EXPLICIT_FONTFILE`

## Output verification

- Plain no-text control render also succeeded
- First-frame SHA-256 hashes between plain and explicit-font outputs differed
- Classification: text was actually rendered; success is not a false positive container write

## Production drawtext call-site inventory

- `v2/asset_manager.py` stock fallback branch: `ACTIVE_BASELINE_RUNTIME (fallback-only)`
- `v2/main.process_timeline`: `NOT_DRAWTEXT_USAGE`
- `v2/editorial_engine.py`: `NOT_DRAWTEXT_USAGE` for text overlays; PIL image composition is used
- `v2/video_engine.py`: `NOT_DRAWTEXT_USAGE` for subtitles, counters, big text, and fallback cards; PIL + MoviePy are used
- `v2/modules.py`: `NOT_DRAWTEXT_USAGE`
- No other active production `drawtext` call-site was found in the authoritative repository

## Baseline fixture reachability

- `test_1_min.json` includes stock scenes, so the `v2.asset_manager.py` fallback branch is reachable if stock acquisition returns no asset
- Normal text overlays and subtitles in the baseline path are not `drawtext`-backed
- `v2.main.process_timeline` does not directly call `drawtext`
- Baseline classification: current baseline path does not depend on default Fontconfig font discovery for its ordinary text rendering path

## Editorial-path reachability

- Editorial path text overlays are PIL-generated and then composed into video
- No active editorial `drawtext` dependency was verified

## Faz 0 blocker decision

- Filter capability decision: `DRAWTEXT_OPERATIONAL_WITH_EXPLICIT_FONTFILE`
- Phase 0 blocker decision: `NOT_A_BASELINE_BLOCKER`
- Reasoning:
- explicit `fontfile` render passed on the accepted paired runtime
- the observed failure is limited to default Fontconfig discovery
- baseline/runtime text overlays are rendered by Python/PIL/MoviePy, not by `drawtext`
- the only production `drawtext` call-site is a stock local-fallback generator, not the ordinary subtitle/card pipeline

## Long-term product consideration

- If the stock fallback generator remains in production, it should eventually pass an explicit font path or package a deterministic font contract
- This is a hardening task, not evidence that the current Phase 0 baseline is blocked

## Remaining Phase 0 blockers

- Provider revoke/rotation: `NOT CONFIRMED`
- Offline isolated full render: `OPEN`
- Baseline tag: `NOT CREATED`
- General Phase 0: `OPEN`
