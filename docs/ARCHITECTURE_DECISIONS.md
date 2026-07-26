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

## ADR-P1-005 - Optional Automation and Capability Execution Modes

Durum: Kabul edildi; future binding architecture decision. Faz 1'de runtime,
schema veya enum olarak uygulanmamistir.

> Automation is optional; guidance, validation, reproducibility and cost
> control are mandatory.

Her gelecekteki capability, destekledigi execution modlarini acik bir capability
matrix ile ilan etmelidir: `LOCAL`, `MANUAL_UI`, `FREE_API`, `PAID_API`,
`REPLAY`, `DISABLED`. Bir capability'nin her modu desteklemesi gerekmez;
unsupported mode fail-closed olur. Bu cross-capability taxonomy, mevcut
LLM-specific `LOCAL_MODEL`, `API`, `MANUAL_UI`, `REPLAY` adlarini bu kararla
degistirmez; aradaki migration sonraki bir tasarim gorevidir.

`MANUAL_UI`, providerdan bagimsiz task package, kopyalanabilir prompt, beklenen
format/schema, quality/safety kurallari ve teknik asset gereksinimleri uretir.
Kullanici kendi browser hesabinda islemi yapar ve sonucu text, JSON veya dosya
olarak geri yukler. Uygulama schema, referential integrity, source/claim,
technical media ve cost/license metadata sinirlarini dogrular; bounded repair
task uretebilir. Consumer browser hesabini otomatik surmek, cookie almak veya
browser scraping yapmak `MANUAL_UI` degildir.

Provider execution gelecekte global/project/capability budget, estimate ve
actual/retry cost, explicit expensive-operation approval, provider
failure/fallback lineage ve replay/cache korumasini desteklemelidir. Local
asset, paid generationdan once degerlendirilir; pahali image/video generation
sessizce calismaz.

## ADR-P1-006 - Independent Editorial Critic Pipeline

Durum: Kabul edildi; future binding editorial decision. Faz 1'de Critic code,
schema veya provider integration uygulanmamistir.

Future script acceptance flow:

```text
Research Bundle
-> Narrative Contract
-> Planner
-> Writer
-> Independent Critic Pipeline
-> Scoped Repair Plan
-> Writer Repair
-> Independent Verification
-> Human Approval
-> Scene Planning
```

Writer kendi ciktisini tek basina onaylamaz. Critic mumkunse farkli model veya
providerla, degilse temiz ve bagimsiz context ile calisir; tum senaryoyu yeniden
yazmak yerine structured issue report uretir. Her issue en az `issue_id`,
`critic_type`, `severity`, location, evidence, viewer/editorial risk, minimum
repair, protected claims/content ve blocker status tasir. Repair yalniz ilgili
scope'u degistirir; etkilenmeyen claim ve bolumler korunur. Repair sonrasinda
independent verification ve nihai insan onayi zorunludur.

Critic tipleri: Evidence/Factual, Narrative Continuity, Retention and Pacing,
ve Visual Feasibility. Scene planning oncesinde future gates
`FACTUAL_GATE`, `CONTINUITY_GATE`, `RETENTION_RISK_GATE`,
`VISUAL_FEASIBILITY_GATE`, `HUMAN_APPROVAL_GATE` olarak desteklenir. Retention
degerlendirmesi risk tahminidir; video basarisini veya viral olmayi garanti
etmez ve yayin sonrasi audience-retention verisiyle kalibre edilir.

Evidence/Factual Critic; unsupported veya source ile celisen claim, farkli
para/tarih/isim, fact gibi sunulan yorum, research bundle disi ayrinti ve
claim/source strength uyumsuzlugunu inceler. Narrative Continuity Critic;
kronoloji, neden-sonuc, tanitilmayan kisi/kurum, setup-payoff, merkezi soru,
tekrar ve series-level editorial memory'yi inceler. Retention and Pacing
Critic; hook, merkezi soru, exposition, bilgi/momentum, stakes, payoff,
isim-rakam yogunlugu ve transition risklerini channel/domain profile'a gore
degerlendirir; katı bir "her N saniyede twist" kuralı uygulamaz. Visual
Feasibility Critic; soyut anlatim, asset bulunabilirligi, generic visual
tekrari, uygun document/chart/map treatment'i ve generated reconstruction'in
gercek olay sanilmasi riskini scene planning oncesi gorunur kilar.
