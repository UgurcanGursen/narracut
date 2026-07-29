# Known Limitations

Son guncelleme: 29 Temmuz 2026

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

- Faz 1 CLOSED durumundadir. V3 contract foundation, contract integrity,
  public validation boundary, V2ToV3Migrator, migration-loss reporting,
  migrator URI security, thin project API, generated client/UI shell ve
  post-audit test hardening kanitlanmistir.
- API project catalog process-lifetime in-memory'dir; restart sonrasi project
  state kaybolur. WorkspaceStore, SQLite, durable persistence, upload, render
  orchestration/progress, authentication, billing ve full review UI yoktur.
- Studio UI thin control-plane shell'dir; temporal alignment, end-user video
  production flow, automated provider execution veya Critic pipeline
  implementation claim etmez.
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

## Faz 2 status note

- Slice 1-4 repository evidence reconciliation completed.
- Post-Slice-4 scope reconciliation is no longer a blocker; the scope report is
  remote closed at `f89e10156a940016deef4e94b6aef8863837dbf6`.
- Remote-closed scope report path:
  `baseline/phase2_post_slice4_scope_report.md`.
- Remote-closed scope report SHA-256:
  `aefaacf8e19e94c1f1f31615550d6e76c2d1184cb290ce34c12264df4cc3703f`.
- `TERRASCOPE-001` is CLOSED by targeted Terra re-audit.
- Slice 4 is remote closed at
  `d32e66585d660bc3e37a1896dbb7df050a8bc849`.
- Phase 2 overall closure is not established.
- The total official Phase 2 Slice count is not reconciled.
- No Phase 2 completion percentage is claimed.
- Accepted/committed Slice 5 specification does not exist yet.
- Slice 5 implementation remains blocked.
- The next bounded candidate is `PHASE2-SLICE-5-CANDIDATE` - Canonical Adapter
  Execution Provenance Contract, but only a specification task is authorized.
- Scope report evidence gaps remain: `EVIDENCE_PATH_NOT_FOUND`,
  `TEST_RESULT_NOT_RECONCILED`, and `NOT_PROVEN_BY_REPOSITORY`.
- Slice 1-3 standalone scope/audit/closure evidence and test-result
  reconciliation gaps remain, so broader closure must not be claimed.
- Downstream canonical timing deliverables are not proven complete.

## Environment and test limitations

- Legacy full Python collection, committed manifestlerde olmayan `pyloudnorm`
  nedeniyle `v2.audio_engine` import zincirindeki uc collection'da durur.
- Starlette/HTTPX TestClient deprecation warning'i non-blockingdir.
- Windows symlink skip kabul edilmistir; `.pytest_cache` ve
  `shared-schemas/.pytest_cache` permission warning'leri pre-existingdir.
- `v2/audio_engine_debug.py` ve `v2/audio_engine_debug2.py` bilinen
  syntax/indentation debug debt'idir; MoviePy SyntaxWarning'leri applicable
  ortamlarda gorulebilir.

## Operations and repository safety

- Provider credential revoke/rotation NOT CONFIRMED olarak kalir.
- `C:\Users\user\Documents\Kurgu_V3_Clean`,
  `C:\Users\user\Documents\Kurgu_V3_Clean_backup_20260724_163134`,
  `C:\Users\user\Documents\Kurgu_V3_Clean_sanitized_20260724_163134` ve
  onceki verification/sanitized clone'lar unsafe history tasiyabilir; asla
  authoritative development, push, sharing veya public archive icin
  kullanilmaz. Tek authoritative repository bu dokumanda kayitli sanitized
  Freesound repository'dir.
