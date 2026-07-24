# Known Limitations

Son guncelleme: 24 Temmuz 2026

## Faz 0 blocker'lari

1. Provider revoke/rotation durumu **NOT CONFIRMED** olarak kalir.
2. Accepted paired FFmpeg/ffprobe runtime dogrulansa da practical `drawtext` invocation halen Fontconfig nedeniyle blockerdir.
3. Full offline isolated render reproduction halen aciktir.
4. `stage3-development-baseline` tag'i yoktur.

## Security sinirlari

- Reachable `origin/main` history sanitized root ile remediated durumdadir.
- Bu yine de hosting cache/replica retention, eski clone/fork veya local sensitive repository'lerde fiziksel yokluk kaniti degildir.
- Eski source repo, backup'lar ve onceki clone'lar secret-bearing Git metadata tasiyabilir; remote'a push edilmemeli, bulutla paylasilmamali ve yeni authoritative development icin kullanilmamalidir.

## Runtime ve reproduction sinirlari

- Koku CLI icin explicit offline/cache-only/skip-download modu yoktur.
- Legacy output override yoktur.
- Edge TTS, YouTube, web capture ve benzeri yollar ag bagimliligi tasir.
- `v2/audio_engine_debug.py` ve `v2/audio_engine_debug2.py` bilinen debug debt olarak disarida tutulur.
