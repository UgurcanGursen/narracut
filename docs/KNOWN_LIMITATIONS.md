# Known Limitations

Son guncelleme: 25 Temmuz 2026

## Known limitations ve follow-up'lar

1. Provider revoke/rotation durumu **NOT CONFIRMED** olarak ayri security follow-up olarak kalir.
2. Varsayilan Fontconfig font discovery bu Windows ortaminda calismaz; `drawtext` yalniz explicit `fontfile` ile dogrulanmistir.

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

## Faz 0 status note

- Bu limitation ve security follow-up'lar Faz 0'i tekrar OPEN yapan teknik blocker olarak siniflandirilmaz.

## Faz 1 status note

- V3 contract foundation, contract integrity hardening ve public validation
  boundary PASS durumundadir. V2ToV3Migrator ve structured migration-loss
  reporting, migrator security hardening ve secondary provenance URI hardening
  PASS'tir; WorkspaceStore entry gate PENDING_INDEPENDENT_REAUDIT
  durumundadir.
- V2 audio file, BGM/SFX, pause, frame-duration, subtitle ve renderer-specific
  visual ayarlari Phase 1 canonical workspace'te birebir temsil edilmez.
  Migrator bunlari structured loss olarak raporlar; strict mod yayinlamaz.
- Descriptor fingerprint, source media hash'i bulunmadiginda yalniz
  deterministic review placeholder'idir; media-byte hash'i oldugu iddia
  edilmez ve manual verification gerekir.
- Aggregate migration outputta embedded policy snapshot authoritative'dir;
  `policy_snapshot_ref` logical/informational identity'dir. Split workspace'te
  ayni alan gercek external document reference olmaya devam eder.
- Migrator her output dosyasini tek basina atomic replace ile yazar; dort
  artifact seti transaction degildir ve write/process failure sonrasi
  mixed-generation set kalabilir. Production persistence icin guvenilir
  sayilmaz.
- WorkspaceStore staged revision directory, tum artifact hash dogrulamasi,
  revision manifest, file close/fsync, commit marker veya atomic active
  revision pointer, crash recovery, mixed-generation engeli, onceki valid
  revision'i koruma ve partial staging cleanup saglamalidir.
- Faz 1 production persistence, timing/frame, renderer integration ve Studio
  API/UI kapsamlarini henuz tamamlamaz.
- `engine/contracts/workspace.py` modul boyutu LOW/non-blocking teknik borctur;
  yeni integrity kontrolleri private helper'lara ayrilmis, genis bolme/refactor
  ertelenmistir.
