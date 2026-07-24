# Known Limitations

Son guncelleme: 24 Temmuz 2026

## Faz 0 blocker'lari

1. Provider revoke/rotation durumu **NOT CONFIRMED** olarak kalir. History replacement bu durumu tek basina kapatmaz.
2. Accepted paired FFmpeg/ffprobe runtime dogrulansa da practical `drawtext` invocation halen Fontconfig nedeniyle blockerdir.
3. Full offline isolated render reproduction bu gorevde henuz calistirilmamistir.
4. Remote `main` replacement henuz yapilmamistir; live SHA check, exact lease push ve fresh-clone verification beklemektedir.
5. `stage3-development-baseline` tag'i yoktur.

## Security sinirlari

- Current tree prepared sibling icinde secret-remediated durumdadir.
- Eski source repo, backup'lar ve onceki clone'lar secret-bearing Git metadata tasiyabilir.
- Bu eski repository'ler remote'a push edilmemeli, bulutla paylasilmamali ve yeni authoritative development icin kullanilmamalidir.

## Runtime ve reproduction sinirlari

- Koku CLI icin explicit offline/cache-only/skip-download modu yoktur.
- Legacy output override yoktur.
- Edge TTS, YouTube, web capture ve benzeri yollar ag bagimliligi tasir.
- `v2/audio_engine_debug.py` ve `v2/audio_engine_debug2.py` bilinen debug debt olarak disarida tutulur.
