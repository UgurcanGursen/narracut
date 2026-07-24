# Architecture Decisions

## ADR-P0-001 — Public wrapper ile aktif engine ayrımı

Durum: Kabul edildi (Faz 0 baseline kaydı)

`main.py` public thin CLI wrapper/delegation layer'dır. Aktif production
pipeline `v2/main.py`, ana orchestration sembolü
`v2.main.process_timeline`'dır. `legacy` sözcüğü “silinmiş/deprecated” değil,
aktif baseline, parity referansı ve kontrollü migration kaynağı anlamındadır.

Kanıt:

- Import: `main.py:5-7`
- CLI delegation: `main.py:40-52`
- Orchestrator: `v2/main.py:96`
- JSON load/format: `v2/main.py:111-114`
- Legacy validation: `v2/main.py:163-193`
- Editorial delegation: `v2/main.py:116-158`

Karar: Faz 0'da wrapper/delegation yapısı değiştirilmez.

## ADR-P0-002 — Validation sırası kodun gerçek davranışıyla belgelenir

Durum: Kabul edildi

Kullanıcı beyanındaki “validation sonrasında delegation” ifadesi kavramsal
akış olarak korunur, fakat implementasyon ayrımı açık yazılır:

- `--validate-only`: root `run_validation`; render/delegation yok.
- Normal V1/V2 render: root doğrudan `process_timeline`; load ve validation
  engine içinde.
- Editorial render: `process_timeline` formatı algılar ve
  `process_editorial_timeline` yoluna delege eder.

Bu nüans mimariyi kendiliğinden değiştirme gerekçesi değildir.

## ADR-P0-003 — Dirty baseline tag'lenmez

Durum: Geçici karar / blocker

Görev başlangıcında kullanıcı değişiklikleri bulunduğundan HEAD'e tag eklemek
mevcut runtime dosyalarının gerçek içeriğini temsil etmeyecekti. Bu nedenle
`stage3-development-baseline` tag'i oluşturulmadı. Revision, dirty file listesi
ve önemli dosya SHA-256 değerleri manifest'e yazıldı.

## ADR-P0-004 — Hedef mimariye kontrollü migration

Durum: Roadmap ile bağlayıcı

```text
v2/ active engine
→ adapter boundary
→ verified replacement modules
→ parity validation
→ controlled migration
```

Toplu taşıma, rename veya renderer rewrite Faz 0 kapsamında yapılmaz.

## Roadmap ADR'leri

`docs/MASTER_ROADMAP.md` içindeki ADR-001–ADR-015 bağlayıcıdır. Bu dosya onları
yeniden tanımlamaz; yalnızca mevcut baseline'a ilişkin kararları kaydeder.

