# Faz 1 V3 Contract Foundation Report

Tarih: 25 Temmuz 2026

## Recovery ve salvage

- Interrupted recovery manifestindeki ilk 50 Faz 1 dosyasi, salvage baslangicinda
  repository ile path/size/SHA-256 parity verdi.
- Read-only audit karari `SALVAGE_WITH_TARGETED_FIXES` idi; mevcut schema,
  registry, resolver, sample ve invariant yapisi korunarak dar kapsamli
  duzeltmeler uygulandi.

## Contract foundation

- Split document `kind` degeri yuklenen manifest tipiyle fail-closed baglidir.
- Profile/snapshot kimligi, snapshot reference ve domain/pack/profile uyumu
  WorkspaceLoader tarafindan dogrulanir.
- Registry ile calistirilan loader, snapshot'i ayni declarative pack ve profile
  icin DomainPolicyResolver sonucu ile canonical JSON/SHA-256 parity kontrolune
  tabi tutar.
- Event target'lari typed (`target_type`, `target_id`), collection-resolved ve
  event-group compatibility kontrolludur.
- Dataclass'lar canonical schema yerine gecmez: loader yalniz schema-valid
  veriden typed Workspace view uretir; schema version typed view'da korunur.

## Samples ve validation

- Minimal, business-tech ve split-long-form sample'lari canonical loaderdan
  gecmektedir.
- Split-long-form snapshot'i business-tech pack ve split profile icin gercek
  resolver ciktisidir.
- Targeted contract suite: `54 passed, 1 skipped` (Windows symlink yetkisi
  olmayan ortamda acik skip nedeni).

## Sinirlar ve sonraki is

Bu foundation migration, persistence, timing, renderer veya V2 production
refactor icermez. Faz 1 genel olarak OPEN/IN_PROGRESS kalir. Sonraki is:
`V2ToV3Migrator` ve migration-loss reporting implementation.
