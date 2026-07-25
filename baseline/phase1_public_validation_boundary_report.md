# Faz 1 Public Validation Boundary Report

Tarih: 25 Temmuz 2026
Baslangic revision: `071343951d284f8251ab4cebb549e1d9746d9dcc`
Karar: **PASS**

## Audit bulgusu

Post-hardening audit, exported `validate_artifact_graph(...)` ve
`validate_retention_policy(...)` fonksiyonlarinin raw Mapping girdilerini
SchemaCatalog dogrulamasi olmadan private typed construction yoluna
gecirebildigini kanitladi. Bu nedenle schema-invalid artifact ve retention
mapping'leri semantic validator tarafindan yanlislikla valid kabul
edilebiliyordu.

## Public API karari

Mevcut Mapping kullanan cagrilari korumak icin guvenli raw-mapping yaklasimi
secildi:

- Raw Mapping input icin caller'in explicit `catalog=SchemaCatalog(...)`
  dependency'si zorunludur.
- Catalog verilmezse silent fallback yerine acik `TypeError` uretilir.
- `ArtifactRecord` ve `RetentionPolicy` typed inputlari schema-valid typed view
  olarak kabul edilir.
- Import-time schema scan, global mutable catalog, gizli path tahmini veya yeni
  dependency eklenmedi.

Bu imza degisikliginin backward-compatibility etkisi aciktir: raw Mapping ile
public validator cagiran caller artik catalog vermek zorundadir. WorkspaceLoader
kendi mevcut catalog dependency'sini artifact graph validator'a aktarir.

## Raw Mapping validation akisi

Artifact:

```text
raw Mapping collection
-> her item artifact.schema.json
-> tum schema issue'larini artifact index pointer'i ile dondur
-> schema issue yoksa private ArtifactRecord construction
-> dependency/reference/cleanup semantic invariant'lari
```

Retention:

```text
raw Mapping
-> retention_policy.schema.json
-> schema issue varsa aynen dondur
-> schema-valid ise private RetentionPolicy construction
-> retention class / TTL / cleanup semantic invariant'lari
```

Schema validation basarisizsa private construction ve semantic validation
calismaz. Schema sonrasindaki beklenmedik construction hatasi
`CONTRACT_CONSTRUCTION_ERROR` olarak acikca gorunur.

## Structured issue davranisi

SchemaCatalog'un mevcut `SCHEMA_*` kodlari, source file, message ve JSON pointer
bilgisi korunur. Artifact collection issue pointer'lari
`/artifacts/<index>/...` ile gercek graph konumuna prefix edilir. Retention
pointer'lari canonical policy root'una gore korunur.

## Semantic invariant regression

Schema-valid girdilerde su semantic kontroller korunmustur:

- duplicate artifact ID
- missing/self dependency
- dependency cycle
- orphan artifact/output
- protected cleanup
- protected retention class TTL/cleanup kurallari
- tum retention class'larinin kapsanmasi

Schema-invalid artifact/retention inputlarinin semantic success veya
yaniltici birincil semantic error uretmedigi focused testlerle dogrulandi.

## Resolver parity focused regression

Business-tech snapshot resolved-policy payload'i degistirildi, production
`policy_snapshot_hash` helper'i ile yeniden hashlenip deterministic snapshot ID
yenilendi ve external/embedded snapshot birlikte yazildi. Gercek
DomainPackRegistry ile public WorkspaceLoader sonucu
`POLICY_SNAPSHOT_RESOLUTION_MISMATCH` verdi; self-hash tutarli olmasi pack
resolver parity kontrolunu bypass etmedi.

## Dogrulama

- Hedefli V3 suite: `85 passed, 1 skipped`
- Tek full-suite kosusu: `143 passed, 1 skipped`
- Minimal, business-tech ve split-long-form public loader: PASS
- Faz 1 in-memory compile: PASS
- Tracked JSON parse: PASS
- 16 schema check_schema ve tum `$ref` resolution: PASS
- Current/reachable generic secret scan: `0` / `0`
- `main.py`, `v2/`, `requirements.txt`, Faz 0 evidence: mutation yok
- Full video render: calistirilmadi

## Faz durumu

- Faz 0: CLOSED
- Faz 1 contract foundation: PASS
- Contract integrity hardening: PASS
- Public validation boundary: PASS
- Faz 1 geneli: OPEN / IN_PROGRESS
- Migrator entry gate: READY

`engine/contracts/workspace.py` modul boyutu LOW/non-blocking teknik borc olarak
kalir.
