# Known Limitations

Son guncelleme: 24 Temmuz 2026

## Faz 0 blocker'lari

1. Provider revoke/rotation durumu **NOT CONFIRMED** olarak kalir.
2. Varsayilan Fontconfig font discovery bu Windows ortaminda calismaz; `drawtext` yalniz explicit `fontfile` ile dogrulanmistir.
3. `stage3-development-baseline` tag'i yoktur.

## Security sinirlari

- Reachable `origin/main` history sanitized root ile remediated durumdadir.
- Bu yine de hosting cache/replica retention, eski clone/fork veya local sensitive repository'lerde fiziksel yokluk kaniti degildir.
- Eski source repo, backup'lar ve onceki clone'lar secret-bearing Git metadata tasiyabilir; remote'a push edilmemeli, bulutla paylasilmamali ve yeni authoritative development icin kullanilmamalidir.

## Runtime ve reproduction sinirlari

- Koku CLI icin explicit offline/cache-only/skip-download modu yoktur.
- Legacy output override yoktur.
- Edge TTS, YouTube, web capture ve benzeri yollar ag bagimliligi tasir.
- Closure fixture render'i `phase0_block_01` icin `159.5 WPM` warning'i ile `success_with_warnings` dondurur; decoded fingerprint, A/V drift ve output validity gate'leri yine de PASS durumundadir.
- `v2/audio_engine_debug.py` ve `v2/audio_engine_debug2.py` bilinen debug debt olarak disarida tutulur.
