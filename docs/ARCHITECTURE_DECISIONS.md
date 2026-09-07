# Architecture Decisions

## Latest checkpoint — 2026-09-07, manual editorial cycle

Phase **17 SCOPE_RECONCILIATION remains OPEN**. The owner authorized the bounded
manual workflow following the opening assessment. Portable task bundles now
carry actual media/source previews and a rendered-cut snapshot; returned AI files
persist outline, per-shot needs and declared reviews before existing production.
Missing material and unresolved/stale review gate rendering; atomic import and
job admission preserve task/plan lineage. Scene feedback is version-bound.
The immutable canonical catalog is adapted; supplementary working media remain
unapproved. No paid calls, new domains or canonical promotion.

Actual opening `ejob_296f3b4deb0745cc9abdc5a3d7f3e2ff`: 46.5s, 5 scenes, 13 shots. Final later section
`ejob_d8afc9ddd8a14f75a0411786c5bb0964`: 28.433333s, 2 scenes, 7 shots. Its selected-scene repair preserves
the first scene's exact video hash. Measured mux maximum offset 0.0ms. 42 engine,
17 API and 44 UI cases pass; build, client and renderer checks pass.

**Live cycle acceptance is pending.** Automatic approval review rejected the new
API startup as `blocked by policy`; the old API8006 remains selected. Actual
browser playback passes; the new workflow displays an explicit old-API warning
and blocks production. In-process API/render success is not a full live UI pass,
creative approval, full film, or autonomous professional editing.
Report and DOCUMENTATION_IMPACT_MATRIX: `baseline/phase17_manual_editorial_cycle_acceptance_20260907.md`.
Sync evidence: `output/phase17-manual-editorial-cycle-20260907/documentation-sync.json`.

## Latest checkpoint — 2026-09-07, documentary opening repair

The prior 87.866667-second vector edit remains technically verified but was
**creatively rejected by the owner**. A new project-owned **OPENING_EXCERPT**
now renders the first **46.5 seconds** in 1080p/30fps, with five narration
sections and 13 media/document shots. It is not the complete video.
Job `ejob_9fd4a1421b884fd2840474da074f70ca`. Actual agreement, archival photo, illustrative footage,
source paragraph, local narration and original underscore have exact lineage.

The opening's script and new Microsoft source are unapproved working inputs;
accepted chapter allocations/claim IDs are unchanged. Source-byte quote
verification and documentary-specific AI repair instructions were added after
the independent audit. 25 backend/mux and 15 API tests, 10 UI tests, build,
renderer typecheck, generated client and HTTP boundary pass. Decoded mux offset:
maximum **0.0 ms**. Technical success is not creative approval.

Manual editorial authoring, limited footage, canonical promotion and full-video
production remain open. No paid APIs, no other domains, no full-pilot benchmark
claim. Phase **17 SCOPE_RECONCILIATION stays OPEN**. Current Studio API: **8006**.
Full artifact, commands, file inventory and DOCUMENTATION_IMPACT_MATRIX:
`baseline/phase17_documentary_opening_acceptance_20260907.md`. Documentation sync evidence:
`output/phase17-opening-20260907/documentation-sync.json`.

## ADR-P17-WORKING-EDIT — Measured previews retain accepted ancestry

Status: Implemented for unapproved Studio working edits, 2026-09-07.

Joint treatment narration has a different duration from the earlier accepted
39-second chapter allocation. The Studio production worker records immutable
treatment/direction snapshots and measured voice durations in project-owned
working-edit jobs. Generic vector motion is executed through Remotion; normalized
PCM is muxed against exact video frame counts. Input/code/model hashes determine
scene reuse. No accepted chapter, EDL or approval ledger is rewritten.

The tradeoff is explicit: this enables real video review before canonical duration
migration, but it is not canonical activation or completion of the existing
snapshot export path. Working edits carry `human_approved=false` and
`canonical_publication=false`. Promotion requires its own migration/acceptance
scope. Existing render paths remain available. Creative/business-tech decisions
remain in the manual direction and domain-pack prompt, not domain-specific core
classes or conditional branches.

Evidence: `baseline/phase17_studio_working_edit_acceptance_20260907.md`.

## Previous checkpoints (historical)

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
