# Quality Benchmarks

> Phase 14 note (2026-08-06): local REPLAY lifecycle evidence is not a Phase
> 16 reference-quality threshold. The FFmpeg fixture preserves final MP4 bytes
> plus audio-plan/filter/PCM hashes across two producers; see
> `baseline/phase14_master_acceptance.md`.

Son güncelleme: 6 Ağustos 2026

## Mevcut kanıtlar

| Kanıt | Sonuç |
|---|---|
| `python -m pytest -q` | 29 passed, 2 failed |
| `main.py --validate-only test_1_min.json` | valid |
| `main.py --validate-only timeline.json` | valid, 3 warning |
| `output/validation_report.json` | `failed_quality_check` |
| truthful acceptance run | `acceptance_status=failed` |

Son legacy video `output/final_video_v2.mp4` için raporlanan süre 134.8 s;
rapor video/audio farkını 140.98 s / 134.80 s olarak kaydediyor. Üç TTS WPM
uyarısı var: 166.2, 157.3, 225.0.

Truthful acceptance run'ında pacing ve asset alt durumları valid; technical,
editorial, alignment ve pixel alt durumları invalid. Bu artifact başarılı
benchmark olarak sınıflandırılmamıştır.

## Faz 0 benchmark politikası

- Mevcut MP4, fixture, config ve raporlar silinmez veya overwrite edilmez.
- Başarısız rapor başarılı baseline sayılmaz.
- Faz 0'da yeni kalite threshold'u veya renderer davranışı eklenmez.
- Hash'ler `baseline/baseline_manifest.json` içinde tutulur.

## Henüz kanıtlanmayan

- Aynı input ile başarılı, ağdan bağımsız, tekrar üretilebilir full render.
- System `ffprobe` ile black-screen analizi.
- `stage3-development-baseline` tag'ine bağlı salt-okunur artifact paketi.
- Roadmap Faz 16 referans benchmark metrikleri; bunlar Faz 0 kapsamı dışıdır.
