# Faz 1 Contract Integrity Hardening Report

Tarih: 25 Temmuz 2026
Baslangic revision: `dd0e3c0f9e5a740839cc27c6672c6a705e863113`
Karar: **PASS**

## Audit bulgulari ve kapanis

Post-commit bagimsiz audit'in migrator oncesi bildirdigi blocker'lar hedefli
olarak kapatildi:

- Domain-pack snapshot parity kontrolu registry olmadan basarili sayilmiyor.
- Event'in kendi `track_ref` degeri event grubunun audio/video routing kuraliyla
  dogrulaniyor.
- Base shot yalniz mevcut bir video track'e baglanabiliyor.
- Chapter, beat ve sequence kimlik/membership zinciri aggregate ve split
  workspace'lerde fail-closed dogrulaniyor.
- Public raw mapping factory'leri typed dataclass API'sinden kaldirildi; loader
  schema-valid veri icin private construction yolunu kullaniyor.
- Stable ID indexleri duplicate degeri overwrite etmeden structured hata
  uretiyor.

## Registry-required loader karari

`workspace.schema.json` domain resolution contract'ina zorunlu
`resolution_mode` eklendi:

- `core_only`: yalniz `core-generic` / `0.0.0`; registry gerektirmez.
- `domain_pack`: registry ve resolver zorunludur; yoklugunda
  `DOMAIN_REGISTRY_REQUIRED` uretilir.

Registry saglandiginda pack lookup, profile/pack identity, deterministic policy
resolution, canonical snapshot hash ve snapshot parity birlikte dogrulanir.
Yeniden hashlenmis fakat pack policy'sinden sapmis snapshot registry yoklugunu
bypass edemez.

## Routing ve hierarchy

- `audio_events` yalniz audio track kullanir.
- `edit_events`, `overlay_events` ve `text_emphasis_events` yalniz video track
  kullanir.
- Namespaced domain event'leri ayni core-safe routing kontrolunden gecer.
- Uyumsuzluk `EVENT_TRACK_TYPE_MISMATCH`; base-shot uyumsuzlugu
  `BASE_SHOT_TRACK_TYPE_MISMATCH` kodunu, tam JSON pointer ve kaynak dosyayla
  raporlar.
- Missing chapter/beat, chapter-beat uyumsuzlugu ve chapter membership
  celiskileri canonical story iliskileri uzerinden dogrulanir.
- Beat'in sequence membership'i de iki yonlu kontrol edilir.

## Typed-view ve duplicate identity siniri

Schema-invalid mapping'lerden nesne ureten public `from_dict` factory'leri
private `_from_validated_dict` yollarina donusturuldu. `Workspace.from_dict`
acikca hata vermeye devam eder; public typed view yalniz
`WorkspaceLoader.load()` schema validation'i tamamlandiktan sonra uretilir.
Critical alanlar ve `schema_version` typed view'da korunur.

Loader; chapter, beat, sequence, asset, artifact, track ve sequence kapsamindaki
event ID duplicate'lerini ilk ve ikinci pointer'i koruyarak reddeder.

## Dogrulama kaniti

- Hedefli suite: `70 passed, 1 skipped`
- Tek full-suite kosusu: `128 passed, 1 skipped`
- Faz 1 in-memory Python compile: PASS (`7` dosya)
- Tracked JSON parse: PASS (`85` dosya)
- Draft 2020-12 schema check / ref resolution: PASS (`16` schema, `154` ref)
- Public loader sample gate: minimal, business-tech, split-long-form PASS
- Domain-pack sample registry olmadan: `DOMAIN_REGISTRY_REQUIRED`
- Current/reachable secret scan: `0` / `0`
- `git diff --check`: PASS
- `main.py`, `v2/`, `requirements.txt`: mutation yok

Windows symlink yetkisi olmayan ortam icin mevcut tek explicit skip korunur.
Full video render calistirilmadi.

## Faz ve kalan teknik borc

- Faz 0: CLOSED
- Faz 1 contract foundation: PASS
- Contract integrity hardening: PASS
- Faz 1 geneli: OPEN / IN_PROGRESS
- Migrator entry gate: READY

`engine/contracts/workspace.py` modul boyutu LOW/non-blocking teknik borc olarak
kalir. Bu gorevde genis refactor yapilmadi; yeni kontroller private helper'lara
ayrildi.
