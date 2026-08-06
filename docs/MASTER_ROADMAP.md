# Kurgu Engine — Nihai Master Geliştirme Yol Haritası

> **Belge sürümü:** 2.3
> **Tarih:** 24 Temmuz 2026
> **Durum:** Mimari ana plan — geliştirme boyunca tek referans belge
> **Ürün tanımı:** Araştırılmış bir hikâyeyi, doğrulanmış iddiaları, kaynak kanıtlarını, görsel argümanları, hareketli kompozisyonları ve kontrollü ses tasarımını kullanarak editoryal belgesele dönüştüren yarı otonom kurgu sistemi.
>
> **2.3 revizyonu:** v2.2 kararları korunarak çekirdek mimari `multi-domain-ready core + domain-specific intelligence packs` modeline geçirildi. Business/Technology ilk production domain’i olarak seçildi; True Crime/Legal, History/Geopolitics ve Science gibi alanların çekirdeği çatallamadan sonradan eklenebilmesi için Domain Pack Registry, ortak extension contract, domain-aware research/planner/visual/validation politikaları ve pack-specific benchmark kapıları tanımlandı. İlk geliştirmede yalnızca `business-tech` paketi uygulanacak; diğer domain’ler önceden hard-code edilmeyecek.

---

# 0. Bu Belgenin Amacı

Bu roadmap, Kurgu Engine’in mevcut:

```text
JSON al
→ TTS üret
→ her narration parçasına bir görsel koy
→ görselleri arka arkaya birleştir
→ altyazı ve BGM ekle
→ MP4 üret
```

yaklaşımından çıkıp şu yapıya geçmesini planlar:

```text
Konu + domain seçimi
→ aktif Domain Pack ve policy snapshot
→ Kurgu Engine LLM görev paketi
→ web erişimli yapay zekâ arayüzünde araştırma
→ yapılandırılmış sonucun içe aktarılması ve doğrulanması
→ doğrulanmış source registry ve claim graph
→ global hikâye mimarisi
→ chapter ve beat planı
→ sequence bazlı editoryal plan
→ semantik asset acquisition
→ multi-track EDL
→ kelime seviyesinde zamanlama
→ katmanlı motion composition
→ kontrollü audio direction
→ continuity ve pacing
→ sequence bazlı review
→ incremental render
→ artifact lifecycle ve storage garbage collection
→ final paket
```

Bu dosya, projenin **tek ana geliştirme planıdır**. Yeni bir özellik, mimari değişiklik veya faz sırası bu belge güncellenmeden uygulanmamalıdır.

---

# 1. Mevcut Durum ve Temel Sorun

Kurgu Engine bugün aşağıdaki temel işleri yapabiliyor:

- JSON tabanlı senaryo okuma
- TTS üretme
- Kelime hizalama ve cue eşleştirme
- Temel timeline oluşturma
- Stock, source, chart, metric ve text görselleri üretme
- Videoları birleştirme
- Altyazı ve ses miksleme
- FFmpeg ile final encode
- Temel validation ve observability

Ancak mevcut modelin temel birimi `visual` olduğu için çıktı çoğunlukla:

- Tek katmanlı
- Tam ekran kartlardan oluşan
- Uzun süre aynı görüntüyü gösteren
- Aynı B-roll ailesini farklı anlamlarda tekrar kullanan
- Kaynak sayfalarını yalnızca screenshot olarak gösteren
- Grafikleri bağımsız slayt gibi sunan
- Görsel argüman kuramayan
- Narration ile görsel hareket arasında zayıf bağ kuran
- Kaynak sesini ve BGM’i bilinçli yönetmeyen

bir video olmaktadır.

Hedef sistemin temel birimi `EditorialSequence` olacaktır:

```text
Narrative claim
→ editorial role
→ evidence / mechanism / example / consequence
→ base shot
→ edit events
→ overlay events
→ text emphasis events
→ audio events
→ continuity state
→ sequence render
```

---

# 2. Nihai Ürün Vizyonu

Kurgu Engine nihai durumda:

1. Kullanıcıdan yalnızca bir konu veya kısa research brief alacak.
2. Konuyu güvenilir kaynaklardan araştıracak.
3. Kaynakları tek tek işleyecek ve kalıcı bir claim store oluşturacak.
4. Başlıktaki varsayımı otomatik olarak doğru kabul etmeyecek.
5. Global hikâye mimarisi oluşturacak.
6. Hikâyeyi chapter, beat ve sequence seviyelerine bölecek.
7. Her sequence için editoryal görevi belirleyecek.
8. Kaynak, grafik, UI, B-roll, quote ve text arasında doğru görsel stratejiyi seçecek.
9. Asset’leri provenance, lisans modu, semantik açıklama ve visual family bilgileriyle kataloglayacak.
10. Frame-accurate, multi-track EDL üretecek.
11. Kelime seviyesindeki alignment verisini kinetic text ve cue tabanlı motion için kullanacak.
12. Remotion tabanlı katmanlı motion composition üretecek.
13. Kaynak konuşması, narration ve BGM arasında çakışma yaratmadan audio direction uygulayacak.
14. Video boyunca görsel çeşitlilik, hareket yönü, template tekrarları ve tempo yönetimi yapacak.
15. Kullanıcının yalnızca sorunlu sequence’leri değiştirebildiği review arayüzü sunacak.
16. Yalnızca değişen sequence’leri yeniden render edecek.
17. 10–20 dakikalık belgeselleri tek dev LLM çağrısı olmadan, hiyerarşik biçimde derleyecek.
18. Geliştirme ve ilk gerçek videolarda ticari LLM API çağrısı olmadan `REPLAY` ve `MANUAL_UI` modlarıyla çalışabilecek.
19. Kullanıcıdan manuel internet araştırması istemeyecek; web erişimli yapay zekâ arayüzü araştırmayı yapacak, kullanıcı yalnızca hazır görev paketini taşıyıp sonucu içe aktaracak.
20. React + TypeScript tabanlı Studio UI üzerinden proje, araştırma görevleri, sequence preview, render, storage ve review süreçlerini görünür biçimde yönetecek.
21. İlk backend olarak ince bir FastAPI Studio API kullanacak; Spring Boot ancak gerçek multi-user/SaaS/enterprise ihtiyaçları ortaya çıkarsa yeniden değerlendirilecek.
22. Tek bir multi-domain-ready core kullanacak; research, claim taxonomy, entity roles, narrative grammar, visual grammar, safety ve validation davranışlarını seçilen Domain Pack üzerinden çözecek.
23. İlk production domain’i `business-tech` olacak; yeni domain eklemek core’u fork etmek veya mevcut project schema’yı yeniden yazmak gerektirmeyecek.

Nihai kalite hedefi:

- Logically Answered benzeri kaynak yoğunluğu
- MagnatesMedia benzeri dramatik yapı
- Tam ekran stock montajı yerine katmanlı editoryal kompozisyon
- Belge, haber, keynote, podcast, UI, grafik, quote card ve B-roll arasında kontrollü çeşitlilik
- İddia ile görsel arasında açık semantik ilişki
- Konuşma, motion ve ses tasarımı arasında frame seviyesinde senkron
- Aynı kalite yaklaşımının farklı konularda tekrar edilebilir olması
- Business/Technology alanında derinleşen ilk house style; yeni alanlarda ayrı domain intelligence kullanılması
- True Crime/Legal gibi hassas alanların aynı renderer’ı kullanırken farklı claim, wording, source ve safety kurallarıyla çalışabilmesi

---

# 3. Bağlayıcı Mimari Kararlar

Aşağıdaki kararlar bu roadmap’in değişmez başlangıç noktalarıdır.

## ADR-001 — Python orkestratördür, motion renderer değildir

Python şu işleri yönetir:

- Research orchestration
- Claim store
- Story planning
- TTS ve alignment
- Asset acquisition
- Timeline compilation
- Cache
- Validation
- FFmpeg mux/encode
- Packaging

Gelişmiş motion composition:

```text
Remotion + React
```

üzerinde çalışır.

Final normalize, audio mux ve encode:

```text
FFmpeg
```

ile yapılır.

## ADR-002 — Temel birim `visual` değil `EditorialSequence` olacaktır

Bir sequence:

- Tek bir editoryal amaca sahiptir.
- Bir veya daha fazla claim’e bağlıdır.
- Bir base shot içerir.
- Birden fazla edit event barındırır.
- Birden fazla video ve audio track kullanabilir.
- Kendi içinde giriş, gelişme ve payoff taşıyabilir.
- Bağımsız preview ve render edilebilir.

## ADR-003 — Asset türü ile editoryal görev ayrılacaktır

Örnek:

```text
Asset type: article screenshot
Editorial role: prove_claim
Composition: article_focus_scan
Edit event: highlight_target_sentence
```

`article`, `stock`, `chart` veya `video` tek başına kurgu kararını tanımlamaz.

## ADR-004 — Word-level timing, motion renderer’dan önce kurulacaktır

Kinetic typography ve narration’a bağlı motion için:

```text
TTS
→ forced word alignment
→ word timeline
→ phrase groups
→ emphasis spans
→ frame mapping
→ Remotion events
```

zinciri zorunludur.

LLM hiçbir zaman milisaniye veya frame zamanı uydurmaz.

## ADR-005 — 10–20 dakikalık film tek promptta planlanmayacaktır

Tek çağrıda bütün narration, claim graph, asset planı ve EDL üretmek yasaktır.

Planlama:

```text
source
→ claim
→ outline
→ chapter
→ beat
→ sequence
→ deterministic compile
```

şeklinde parçalanır.

## ADR-006 — Playwright tek source edinme yöntemi değildir

Source Engine bir anti-bot aşma sistemi olmayacaktır.

Playwright yalnızca erişilebilir sayfalar için kullanılan adapter’lardan biridir.

## ADR-007 — Source audio opt-in olacaktır

Her haber veya röportaj klibinin sesi kullanılmaz.

Source audio ancak:

- konuşma yeterince temizse,
- gömülü müzik contamination seviyesi kabul edilebilirse,
- narration ile çakışmıyorsa,
- BGM policy doğru uygulanabiliyorsa

kullanılır.

## ADR-008 — Validation kalite yerine geçmeyecektir

Validation:

- gerçek hatayı yakalar,
- eksik alanı başarı saymaz,
- threshold’u çıktıya göre değiştirmez,
- kötü videoyu raporlarla iyi göstermeye çalışmaz.

## ADR-009 — Artifact lifecycle, render üretiminden önce tanımlanacaktır

Renderer, cache veya source engine hiçbir ara dosyayı kayıtsız üretemez.

Her artifact:

- stable artifact ID,
- content hash,
- producer version,
- retention class,
- dependency IDs,
- lock/pin durumu,
- created/last-accessed zamanı,
- boyut,
- project/sequence ilişkisi

taşır.

Garbage collection yalnızca dependency graph tarafından referans verilmeyen, kilitlenmemiş ve retention policy gereği silinebilir artifact’lere uygulanır. Salt dosya yaşıyla kör silme yapılmaz.

## ADR-010 — Video frame-accurate, audio sample-accurate derlenecektir

Video event’leri frame grid üzerinde; audio event’leri ise ortak sample grid üzerinde derlenir.

Varsayılan iç audio formatı:

```text
48 kHz
PCM / float32 veya PCM 24-bit
stereo
sample-based timebase
```

Her audio boundary, içerik türüne göre:

- zero-crossing,
- micro fade,
- overlap crossfade,
- planlanmış sessizlik,
- uzun editoryal fade

politikalarından biriyle işlenir. Ara pipeline’da MP3/AAC concat yapılmaz; kayıplı encode yalnızca final export aşamasında uygulanır.

## ADR-011 — LLM kullanımı backend soyutlaması üzerinden yürütülecektir

Pipeline doğrudan belirli bir ticari LLM API’sine bağlanmayacaktır. Bütün zekâ görevleri ortak `LLMTask` ve `LLMResult` sözleşmelerinden geçer.

Desteklenen backend modları:

```text
REPLAY     — önceden onaylanmış fixture/çıktı kullanılır; LLM çağrısı yoktur
MANUAL_UI  — görev paketi kullanıcı tarafından ChatGPT/Claude/Gemini arayüzünde çalıştırılır
LOCAL_MODEL — düşük riskli görevler yerel modelle yürütülür
API        — ileride ticari API ile otomatik çalıştırılır
```

Varsayılan geliştirme politikası:

```text
renderer / EDL / audio / cache testleri → REPLAY
ilk yeni araştırma ve planlama görevleri → MANUAL_UI
basit sınıflandırma/etiketleme → deterministic code veya LOCAL_MODEL
commercial API → varsayılan kapalı
```

Backend değişimi project schema, task formatı veya onaylanmış artifact’leri bozamaz.

## ADR-012 — Kullanıcı manuel araştırmacı olmayacaktır

Kullanıcı yalnızca:

- konuyu ve hedef süre/dili girer,
- Kurgu Engine’in ürettiği görev paketini web erişimli yapay zekâ arayüzüne verir,
- dönen yapılandırılmış sonucu içe aktarır,
- yalnızca kritik çelişki ve kalite uyarılarını onaylar.

Kaynak keşfi, kaynak okuma, fact extraction, claim normalization, chronology ve görsel araştırma yapay zekâ tarafından yapılır. Kurgu Engine ise URL, schema, stable ID, claim/source ilişkisi, erişilebilirlik ve lineage kontrollerini deterministik olarak uygular.

Kullanıcıdan SEC, Reuters, şirket raporu veya benzeri kaynakları elle okuyup tabloya aktarması beklenmez.

## ADR-013 — İlk ürün stack’i React + TypeScript + ince FastAPI Studio API olacaktır

Başlangıç mimarisi:

```text
React + TypeScript Studio UI
        ↓ REST + SSE/WebSocket
Thin FastAPI Studio API
        ↓
Python Kurgu Engine + Remotion + FFmpeg
```

Kurallar:

- React yalnızca HTTP/API sözleşmesini bilir; dosya sistemine veya Python fonksiyonlarına doğrudan erişmez.
- FastAPI endpoint’leri ince orchestration katmanıdır; medya ve domain mantığı controller içine gömülmez.
- OpenAPI ve ortak JSON Schema; Python modelleri, TypeScript tipleri ve gelecekte gerekirse Java DTO’ları için kaynak sözleşmedir.
- İlk local sürümde SQLite yeterlidir; ürün gerektirirse PostgreSQL ve gerçek job queue eklenir.
- Spring Boot başlangıç mimarisine eklenmez.

## ADR-014 — Spring Boot teknoloji hedefi değil, product-gate kararıdır

Spring Boot yalnızca aşağıdaki ihtiyaçların birkaçı gerçek kullanımda ortaya çıkarsa değerlendirilir:

- birden fazla kullanıcı ve ekip,
- multi-tenant proje izolasyonu,
- abonelik/faturalama,
- kurumsal SSO ve gelişmiş roller,
- dağıtık worker havuzu,
- yoğun job orchestration/retry,
- ayrıntılı audit ve kurumsal control-plane ihtiyacı.

Bu durumda React aynı API sözleşmesini kullanmaya devam eder; Spring Boot control-plane eklenebilir, Python medya motoru yeniden yazılmaz. Sırf “ileride ürün olur” varsayımıyla erken Spring Boot veya mikroservis mimarisi kurulmaz.

## ADR-015 — Çekirdek multi-domain-ready, intelligence domain-specific olacaktır

Kurgu Engine tek bir genel amaçlı prompt ile her konuda aynı davranışı göstermeye çalışmayacaktır. Sistem iki katmana ayrılır:

```text
Domain-agnostic Core
+
Selected Domain Pack
```

Çekirdek şu yetenekleri ortak sağlar:

- project/workspace ve stable ID yönetimi,
- Manual LLM Gateway ve backend abstraction,
- source/claim/evidence persistence,
- chronology, chapter, beat ve sequence altyapısı,
- asset catalog, multi-track EDL, renderer ve audio engine,
- review UI, artifact lifecycle, validation orchestration ve export.

Domain Pack şu intelligence katmanlarını sağlar:

- research policy ve source priority,
- claim taxonomy ve legal/epistemic status’ler,
- entity role taxonomy,
- narrative patterns ve beat extensions,
- visual grammar ve template preference/bans,
- audio/tone guidance,
- safety, ethics ve wording policy,
- domain-specific validation rules,
- task prompt templates ve benchmark fixtures.

İlk pack:

```text
business-tech
```

Planlanan fakat ilk release kapsamında uygulanmayacak pack örnekleri:

```text
true-crime-legal
history-geopolitics
science-explainer
```

Core içinde `EarningsClaim`, `MurderSuspect`, `RevenueChart` gibi domain’e kilitli sınıflar oluşturulmaz. Ortak modeller `Claim`, `PersonEntity`, `EvidenceDocument`, `DataVisualization`, `DomainRole` gibi genel kalır; domain anlamı seçili pack tarafından genişletilir.

Yeni domain eklemek için core fork edilemez, mevcut domain davranışı `if domain == ...` bloklarıyla her servise dağıtılamaz. Bütün domain farklılıkları versioned extension contract üzerinden yüklenir.

---

# 4. Global Tasarım İlkeleri

## 4.1. Source-first visual strategy

Tercih sırası:

1. Resmî belge veya birincil kaynak
2. Gerçek ürün/UI görüntüsü
3. Haber, keynote, podcast veya röportaj klibi
4. Özel grafik, diyagram veya explain visual
5. Şirket, kişi, ürün veya lokasyon görüntüsü
6. Operasyonel B-roll
7. Generic stock yalnızca bağlayıcı olarak

## 4.2. Her hareketin editoryal amacı olmalıdır

Yasak davranışlar:

- Random zoom
- Random pan
- Her kesmede dissolve
- Sırf ekran boş kalmasın diye hareket
- Aynı template’i sürekli tekrar etmek
- Her kelimeyi karaoke gibi animasyonla göstermek

## 4.3. LLM önerir, deterministic code derler

LLM:

- Hikâye yapısı önerir
- Claim’leri normalize eder
- Narration yazar
- Editorial role belirler
- Asset brief üretir
- Edit-event niyeti üretir

Deterministik kod:

- ID üretir
- Dosyaları birleştirir
- Schema doğrular
- Frame hesaplar
- Collision çözer
- Hash ve dependency kontrolü yapar
- Final EDL’yi derler

## 4.4. Long-form proje bir dosya değil workspace’tir

10–20 dakikalık bir proje tek dev JSON olarak tutulmaz.

Önerilen yapı:

```text
projects/<project_id>/
  project.json
  project_state.json
  domain/
    active_profile.json
    pack_snapshot/
    policy_resolution.json
  research/
    sources/
      source_001.json
      source_002.json
    source_index.json
    claims.jsonl
    claim_graph.json
    chronology.json
  story/
    global_outline.json
    chapters/
      chapter_01.json
      chapter_02.json
    beats/
      beat_001.json
  sequences/
    seq_001.json
    seq_002.json
  assets/
    catalog.jsonl
    candidates/
    approved/
  timing/
    narration.wav
    word_timeline.json
    caption_groups.json
    emphasis_events.json
  edl/
    compiled_edl.json
    timeline_debug.json
  renders/
    sequences/
    preview/
    final/
  artifacts/
    registry.jsonl
    manifests/
  .trash/
  reports/
  logs/
```

## 4.5. Proje durumu LLM context’i değildir

Kalıcı durum:

- SQLite veya PostgreSQL
- JSONL artifact’leri
- Stable IDs
- Content hashes
- Dependency graph
- Versioned records

ile tutulur.

LLM’ye her çağrıda yalnızca ilgili context gönderilir.

## 4.6. Sıfır-API geliştirme birinci sınıf çalışma modudur

Uygulama API anahtarı olmadan açılabilmeli ve aşağıdaki süreçleri tamamlayabilmelidir:

- onaylanmış fixture’larla bütün renderer testleri,
- Manual LLM Gateway üzerinden yeni research/story/sequence görevleri,
- local TTS/alignment/render,
- sonuç doğrulama, review ve export.

API entegrasyonu sonradan takılan ayrı bir backend adapter’ıdır; ürünün temel akışına gömülü zorunluluk değildir.

## 4.7. Yapay zekâ web arayüzleri otomatik sürülmeyecektir

Kurgu Engine:

- ChatGPT/Claude/Gemini web sayfasını Playwright ile otomatik kontrol etmez,
- login/CAPTCHA/rate-limit mekanizmalarını aşmaz,
- arayüz DOM’undan programatik çıktı kazımaz.

Uygulama yalnızca kullanıcı kontrollü kolaylıklar sunar:

```text
Promptu kopyala
Görev paketini indir
İlgili yapay zekâ arayüzünü aç
Yanıtı yapıştır veya JSON yükle
Doğrula ve kabul et
```

## 4.7.1. Optional automation and capability execution policy

> Automation is optional; guidance, validation, reproducibility and cost
> control are mandatory.

Bu future binding product ilkesidir; Faz 1 CLOSED durumundadir ve bu karar Faz
1 runtime enum'u veya schema'si degildir. Her capability destekledigi modlari
bir capability matrix ile ilan
eder: `LOCAL`, `MANUAL_UI`, `FREE_API`, `PAID_API`, `REPLAY`, `DISABLED`.
Unsupported mode fail-closed olur; her capability tum modlari desteklemek
zorunda degildir. Mevcut LLM-specific `LOCAL_MODEL`, `API`, `MANUAL_UI`,
`REPLAY` terimleri bu dokumantasyon karariyla degismez.

`MANUAL_UI`; providerdan bagimsiz task package, copyable prompt, expected
schema/output, quality/safety rules ve technical asset requirements sunar.
Kullanici kendi browser membership'iyle islemi yapar, sonucu geri yukler ve
uygulama schema, integrity, source/claim, media ve cost/license metadata
sinirlarini dogrular. Browser account automation, session-cookie alma veya web
UI scraping yasaktir.

Gelecekte provider execution global/project/capability budget, estimated and
actual/retry cost, explicit expensive-operation approval, local-asset-first
selection, provider failure/fallback lineage ve replay/cache korumasi
saglamalidir. Pahali image/video generation sessizce calismaz.

### Future acceptance mapping

| Phase | Binding direction |
|---|---|
| Faz 2 | Local-first alignment; paid fallback only by explicit preference; confidence, repair and replay evidence |
| Faz 6 | Free adapters, manual premium search tasks and user-uploaded licensed assets |
| Faz 8 | Manual image/video/document/audio ingestion as first-class assets with local catalog and duplicate checks |
| Faz 9-10 | `MANUAL_UI` and `PAID_API` produce equivalent contracts; prompt packages and import validation remain first-class |
| Faz 11 | Local/free/manual/premium/optional-generative audio choices; local mix is default |
| Faz 13 | Mode selection, task copy/import, scoped repair, approval, estimated cost and license/source review |
| Faz 15 | Provider, mode, cost, latency, retry, failure, quality, manual intervention and output-validation observability |

## 4.7.2. Independent Editorial Critic Pipeline

Future script acceptance flow is:

```text
Research Bundle -> Narrative Contract -> Planner -> Writer
-> Independent Critic Pipeline -> Scoped Repair Plan -> Writer Repair
-> Independent Verification -> Human Approval -> Scene Planning
```

This is a binding target, not a Faz 1 implementation. Writer cannot approve
its own output. An independent Critic produces structured issues rather than a
full rewrite; each issue carries ID, type, severity, location, evidence,
viewer/editorial risk, minimum repair, protected claims/content and blocker
status. Scoped repair preserves unaffected sections and claims, then receives
independent verification and human approval.

Evidence/Factual, Narrative Continuity, Retention and Pacing, and Visual
Feasibility are distinct critic roles. Retention is a risk estimate calibrated
later with post-publication audience-retention data, not a promise of video
success. Future scene-planning gates are `FACTUAL_GATE`, `CONTINUITY_GATE`,
`RETENTION_RISK_GATE`, `VISUAL_FEASIBILITY_GATE` and `HUMAN_APPROVAL_GATE`.

Critic work maps to Faz 9 (grounding input), Faz 10 (narrative contract,
writer, structured report, repair and verification), Faz 12 (continuity and
pacing), Faz 15 (quality gates and issue lifecycle), and Faz 16 (benchmark
and retention calibration). YouTube Analytics integration is future API or
manual CSV-import scope, not a Faz 1 or Faz 10 completion claim.

## 4.8. Studio UI aşamalı geliştirilecektir

```text
UI-A — Developer Console: proje, job, log, preview, artifact ve storage
UI-B — Manual LLM Gateway: pending task, prompt package, import, validate, repair
UI-C — Production Review Studio: research/claim/story/sequence/audio/final review
```

İlk UI yalnızca güzel dashboard değildir; çalışan pipeline’ın kontrol yüzeyidir.

## 4.9. Domain Pack extension contract

Domain Pack bir prompt klasörü değil, versioned ürün bileşenidir. Önerilen repo yapısı:

```text
domain-packs/
  business-tech/
    domain.yaml
    research_policy.yaml
    source_priority.yaml
    claim_taxonomy.yaml
    entity_roles.yaml
    narrative_patterns.yaml
    visual_grammar.yaml
    audio_policy.yaml
    safety_policy.yaml
    validation_rules.yaml
    template_preferences.yaml
    prompts/
      research_discovery.md
      source_extraction.md
      claim_normalization.md
      story_architecture.md
      chapter_planning.md
      sequence_planning.md
    fixtures/
    benchmarks/
  true-crime-legal/
    README.md                 # ilk release’te yalnızca contract örneği; implementation yok
```

Her pack manifest’i en az şu bilgileri taşır:

```text
domain_id
display_name
version
core_contract_version
supported_project_types
claim_taxonomy_version
source_policy_version
prompt_bundle_version
validation_bundle_version
template_capability_requirements
```

Proje oluşturulurken `domain_id` ve `domain_pack_version` sabitlenir. Pack sonradan güncellense bile mevcut proje sessizce yeni davranışa geçirilmez; explicit migration veya yeni project version gerekir.

### İlk pack: Business/Technology

İlk kalite optimizasyonu yalnızca şu alanlarda yapılır:

```text
şirket yükselişi/çöküşü
teknoloji ürünleri ve platformlar
AI, yazılım ve altyapı mekanizmaları
finansal sonuçlar ve stratejik kararlar
kurumsal dava ve düzenleyici olaylar
```

### Gelecekteki True Crime/Legal pack ilkeleri

Bu pack eklendiğinde en az şu ayrımlar zorunlu olur:

```text
established_fact
allegation
prosecution_claim
defense_claim
witness_statement
forensic_finding
charged
convicted
acquitted
dismissed
appealed
unknown
```

`charged` olan yaşayan bir kişi narration’da `murderer` veya kesin fail olarak yazılamaz. Devam eden dava, mağdur hassasiyeti, grafik şiddet ve kişisel veri kuralları pack validation’ı tarafından uygulanır. Bu kurallar business-tech prompt’una eklenen birkaç satırla taklit edilmez.

---

# 5. Kalıcı Proje Hafızası

Repo kökünde:

```text
docs/
  MASTER_ROADMAP.md
  CURRENT_STATE.md
  ARCHITECTURE_DECISIONS.md
  KNOWN_LIMITATIONS.md
  QUALITY_BENCHMARKS.md
  PHASE_ACCEPTANCE.md
  CHANGELOG.md
  NEXT_ACTIONS.md
  DOMAIN_PACKS.md
```

bulunacaktır.

## `CURRENT_STATE.md`

Her geliştirme sonunda güncellenir:

- Çalışan özellikler
- Kısmen çalışan özellikler
- Çalışmayan özellikler
- Son başarılı run
- Son benchmark sonucu
- Aktif branch
- Aktif faz
- Sıradaki görev

## `KNOWN_LIMITATIONS.md`

Bilinen eksikler gizlenmez:

- Real external source capture kapsama oranı
- Bot-protected kaynaklar
- Template eksikleri
- Semantic asset selection sorunları
- Source audio contamination desteği
- Planner’ın desteklemediği beat türleri

## `NEXT_ACTIONS.md`

Aynı anda en fazla 5 aktif görev içerir.

Yeni görev, mevcut görev kapatılmadan veya backlog’a taşınmadan eklenmez.

---

# 6. Hedef Sistem Bileşenleri

```text
React + TypeScript Studio UI
FastAPI Studio API
OpenAPI / Shared Schema Registry
Project Workspace Manager
Domain Pack Registry
Domain Policy Resolver
Domain Prompt Bundle Registry
Domain Validation Extension Registry
LLM Backend Adapter Registry
Manual LLM Gateway
LLM Task Package Builder
LLM Result Importer and Validator
Replay Fixture Store
Research Source Adapter Registry
Research Extractor
Claim Store and Claim Graph
Chronology Builder
Global Story Architect
Chapter Planner
Beat Planner
Sequence Planner
Visual Director
Asset Acquisition Engine
Asset Catalog and Semantic Index
Source Acquisition Engine
Evidence Treatment Engine
Temporal Annotation Engine
Audio Sample Grid and Boundary Engine
Multi-track Timeline Compiler
Motion Template Renderer
Chart and Metric Engine
Audio Director
Continuity and Pacing Director
Validation Engine
Production Review UI
Render Queue and Cache
Artifact Registry and Storage Garbage Collector
Packaging and Export
```


## 6.1. İlk çalışma zamanı mimarisi

```text
Browser
  └── React + TypeScript + Vite
          ├── Project Dashboard
          ├── Manual LLM Tasks
          ├── Research/Claim/Story views
          ├── Sequence Preview and Review
          ├── Render Progress
          └── Storage/GC Console
                    ↓ REST + SSE
              Thin FastAPI Studio API
                    ├── project/domain/task/job/artifact endpoints
                    ├── schema + domain pack validation
                    ├── prompt package export/import
                    ├── Domain Pack Registry and policy resolution
                    └── engine service orchestration
                              ↓
                    Python Kurgu Engine
                       ├── research artifact processing
                       ├── TTS/alignment
                       ├── asset/source acquisition
                       ├── timeline/audio compilation
                       ├── FFmpeg
                       └── Remotion render process
```

İlk sürüm local çalışır:

```text
UI: localhost
FastAPI: localhost
Database: SQLite
Progress: SSE
Execution: local worker/process
```

React build’i ileride tek paket veya Docker Compose içinde sunulabilir. Bu karar Spring Boot gerektirmez.

---

# 7. Multi-track Mimari

## Video track’leri

```text
V1 — Base footage
V2 — Secondary B-roll / inserts
V3 — Source evidence
V4 — Charts / diagrams / UI callouts
V5 — Kinetic emphasis / quote / metric overlays
V6 — Readable subtitles
V7 — Branding / finishing
```

## Audio track’leri

```text
A1 — Narration
A2 — Background music
A3 — Editorial sound effects
A4 — Source speech
A5 — Natural ambience
```

Source speech ile ambience ayrı tutulur; source klibinin ham sesi tek kanal olarak kör biçimde mikslenmez.

---

# 8. Ana Domain Nesneleri

```text
Project
ProjectState
DomainPackManifest
DomainProfile
DomainPolicySnapshot
DomainRole
EntityRole
ClaimTaxonomy
SourcePriorityPolicy
NarrativePattern
VisualGrammar
SafetyPolicy
DomainValidationRule
ResearchSource
SourceSnapshot
FactExtraction
Claim
EvidenceItem
ChronologyEvent
GlobalOutline
ChapterBrief
NarrativeBeat
EditorialSequence
BaseShot
EditEvent
OverlayEvent
TextEmphasisEvent
AudioEvent
AssetBrief
AssetCandidate
AssetRecord
SourceCapturePlan
WordTiming
CaptionGroup
ContinuityState
ValidationResult
LLMTask
LLMTaskPackage
LLMResult
LLMBackendConfig
LLMRepairTask
ApiContractVersion
ArtifactRecord
RetentionPolicy
StorageQuota
RenderArtifact
```

---

# FAZLAR

---

# Faz 0 — Baseline Dondurma ve Proje Hafızası

## Amaç

Mevcut sistemi kaybetmeden kontrollü biçimde yeni mimariye geçmek.

## Yapılacaklar

- Mevcut çalışan kod `stage3-development-baseline` etiketiyle dondurulur.
- Son çalışan fixture, MP4, config ve raporlar salt-okunur referans olarak saklanır.
- V2.2 schema snapshot alınır.
- Mevcut pipeline dependency graph çıkarılır.
- Kod; production, experimental, deprecated ve duplicate olarak sınıflandırılır.
- Cache ve fixture kaynakları kayıt altına alınır.
- Repo hafıza dosyaları oluşturulur.
- Mevcut kod içindeki business/technology’ye özel varsayımlar envanterlenir; core adayı, business-tech pack adayı veya legacy debt olarak sınıflandırılır.
- İlk aşamada dosyalar topluca taşınmaz; hedef directory map yalnızca belgelenir.

## Teslimatlar

```text
docs/CURRENT_STATE.md
docs/KNOWN_LIMITATIONS.md
docs/ARCHITECTURE_DECISIONS.md
baseline/baseline_manifest.json
baseline/v2_2_schema_snapshot.json
baseline/dependency_graph.md
baseline/domain_assumption_inventory.md
baseline/target_directory_map.md
```

## Kabul kriterleri

- Mevcut baseline aynı input ile tekrar üretilebilir.
- Kullanılan fixture, asset, config ve cache yolları kayıtlıdır.
- Yeni geliştirme branch’i baseline’dan ayrıdır.
- “Şu an ne çalışıyor?” sorusunun tek belgede cevabı vardır.
- Core’a gömülü domain-specific sabitler ve promptlar listelenmiştir.
- Faz 0 sırasında geniş klasör taşıma veya renderer rewrite yapılmamıştır.

## Bu fazda yapılmayacaklar

- Yeni motion template
- Yeni provider
- Performance optimization
- V2.2’yi kırmak

---

# Faz 1 — Editorial Domain Model ve V3 Workspace Schema

## Amaç

`blocks + visuals` modelinden long-form, sequence bazlı proje modeline geçmek.

## Yapılacaklar

Bu fazda domain/workspace sözleşmesine ek olarak ilk ürün kontrol sınırı kurulur:

- `studio-api/` altında ince FastAPI uygulama iskeleti
- `studio-ui/` altında React + TypeScript + Vite shell
- `shared-schemas/` altında canonical JSON Schema’lar
- FastAPI OpenAPI çıktısından generated TypeScript client
- Proje oluşturma, durum okuma ve artifact listeleme için ilk endpoint’ler
- React’in yalnızca HTTP üzerinden çalıştığını doğrulayan sınır testleri

Domain extension contract önce tanımlanır:

```text
DomainPackManifest
DomainProfile
DomainPolicySnapshot
DomainRole extension
Claim taxonomy extension
Entity role extension
Narrative pattern extension
Visual grammar extension
Safety/validation extension
Prompt bundle extension
```

Core schema yalnızca `domain_id`, `domain_pack_version` ve extension payload referanslarını bilir. Core servisler pack dosyasının içeriğini doğrudan hard-code etmez; `DomainPolicyResolver` üzerinden typed policy alır.

V3 workspace schema tanımlanır:

```json
{
  "project": {},
  "domain": {},
  "research": {},
  "story": {},
  "sequences": [],
  "assets": [],
  "timing": {},
  "tracks": {},
  "render_profile": {}
}
```

Her `EditorialSequence`:

```text
sequence_id
chapter_id
beat_id
narrative_goal
editorial_role
claim_ids
start_cue
end_cue
base_shot
edit_events
overlay_events
text_emphasis_events
audio_events
continuity_constraints
fallback_policy
status
version
```

alanlarını taşır.

## Edit event türleri

```text
cut
crop_to_target
push_in
pull_out
pan
highlight_wipe
text_reveal
metric_count
chart_draw
source_focus
split_screen
picture_in_picture
blur_background
vignette
callout
logo_reveal
chapter_reset
```

## Artifact manifest sözleşmesi

Her renderer, downloader, source adapter ve audio pipeline çıktısı `ArtifactRecord` üretir.

```text
artifact_id
artifact_type
project_id
sequence_id
created_at
last_accessed_at
content_hash
size_bytes
retention_class
dependency_ids
locked
pinned
approved
producer
producer_version
job_id
status
```

Retention sınıfları:

```text
ephemeral
temporary
cache
review
approved
final
provenance
baseline
pinned
```

`approved`, `final`, `provenance`, `baseline` ve `pinned` artifact’ler salt TTL nedeniyle silinemez.

## V2.2 uyumluluğu

- V2.2 input desteği korunur.
- `V2ToV3Migrator` oluşturulur.
- V2.2 içerik basit sequence’lere çevrilir.
- Kayıp veya bilinmeyen alan silent default ile doldurulmaz.

## Teslimatlar

```text
schema/v3/
  project.schema.json
  chapter.schema.json
  beat.schema.json
  sequence.schema.json
  asset.schema.json
  artifact.schema.json
  retention_policy.schema.json
  domain_pack.schema.json
  domain_profile.schema.json
  domain_policy_snapshot.schema.json
domain-packs/business-tech/manifest + policy skeleton
domain-packs/true-crime-legal/README.md contract example only
DomainPackRegistry
DomainPolicyResolver
V2ToV3Migrator
domain models
schema validator
sample workspaces
studio-api/ FastAPI skeleton
studio-ui/ React + TypeScript shell
shared-schemas/
openapi.json
generated TypeScript API client
```

## Kabul kriterleri

- Bir narration span içinde birden fazla edit event tanımlanabilir.
- Bir sequence birden fazla video ve audio track kullanabilir.
- Asset type ile editorial role ayrıdır.
- V2.2 migration kayıpları açıkça raporlanır.
- 20 dakikalık proje tek dosyaya zorlanmaz.
- Artifact dependency ve retention bilgisi schema seviyesinde zorunludur.
- Kayıtsız orphan render dosyası üretilemez.
- React UI proje verisine yalnızca Studio API üzerinden erişir.
- FastAPI endpoint’leri domain/engine servislerini çağıran ince adapter olarak kalır.
- OpenAPI sözleşmesinden TypeScript client üretilebilir.
- Spring Boot veya ikinci bir control-plane bu fazın kapsamına girmez.
- Core domain modellerinde business-tech’e özel sınıf veya zorunlu alan yoktur.
- `business-tech` pack’i core contract üzerinden yüklenir.
- Yeni bir dummy domain manifest’i eklenerek core kod değiştirilmeden schema validation yapılabilir.
- `true-crime-legal` bu fazda tam uygulanmaz; yalnızca extension contract’ın yeterliliğini doğrulayan örnek manifest/README bulunur.

---

# Faz 2 — Temporal Annotation ve Word-Level Alignment Contract

## Amaç

Motion, kinetic typography, subtitle ve audio event’leri için güvenilir kelime zaman çizelgesi oluşturmak.

## Pipeline

```text
Narration text
→ TTS
→ audio normalization
→ forced word alignment
→ token-to-original-word mapping
→ phrase grouping
→ emphasis mapping
→ word-to-frame compilation
```

## WordTiming modeli

```json
{
  "word_id": "word_0042",
  "text": "expensive",
  "normalized_text": "expensive",
  "start_ms": 12480,
  "end_ms": 13060,
  "confidence": 0.97,
  "caption_group_id": "caption_008",
  "start_frame": 374,
  "end_frame": 392
}
```

## İki ayrı text sistemi

### V5 — Kinetic emphasis

Yalnızca editoryal olarak önemli:

- Anahtar kelime
- Rakam
- Karşıtlık
- Reveal
- Sonuç

span’lerinde kullanılır.

### V6 — Readable subtitles

- Phrase bazlıdır.
- 4–9 kelimelik gruplar tercih edilir.
- Safe area içinde kalır.
- Motion overlay ile çakışmaz.
- Erişilebilirlik ve okunabilirlik önceliklidir.

## Emphasis planner davranışı

LLM yalnızca:

```json
{
  "text_span": "ninety-nine percent",
  "emphasis_type": "numeric_reveal",
  "intensity": "strong"
}
```

üretir.

Gerçek zamanlar alignment motorundan gelir.

## Teslimatlar

```text
timing/word_timeline.json
timing/caption_groups.json
timing/emphasis_events.json
WordToFrameCompiler
CaptionPreviewRenderer
AlignmentReport
```

## Kabul kriterleri

- Narration’daki her kelimenin start/end zamanı vardır.
- Cue’lar string araması yerine word ID aralıklarına bağlanabilir.
- Kinetic text narration ile en fazla 1 frame sapma gösterir.
- V5 ve V6 aynı ekranda birbirini kapatmaz.
- Düşük confidence açıkça raporlanır.
- LLM tarafından manuel saniye üretilmez.

---

# Faz 3 — Multi-track EDL ve Timeline Compiler

## Amaç

V3 sequence’lerini frame-accurate, multi-track edit decision list’e dönüştürmek.

## Yapılacaklar

- Frame-grid scheduler
- Millisecond-to-frame conversion
- Track collision rules
- Layer priority
- Sequence boundaries
- Cue-to-word mapping
- Edit-event interpolation
- Audio/video sync
- Video frame grid ve audio sample grid ayrımı
- 48 kHz sample-time compilation
- Audio format normalization
- Encoder delay/padding compensation
- Zero-crossing search
- Micro-fade ve overlap-crossfade planning
- Planned-silence preservation
- Audio boundary collision resolution
- Transition hesaplama
- Nested composition
- Sequence pre-render
- Deterministic merge

## EDL örneği

```json
{
  "fps": 30,
  "audio_sample_rate": 48000,
  "tracks": {
    "V1": [],
    "V2": [],
    "V3": [],
    "V4": [],
    "V5": [],
    "V6": [],
    "V7": [],
    "A1": [],
    "A2": [],
    "A3": [],
    "A4": [],
    "A5": []
  }
}
```

## Teslimatlar

```text
TimelineCompiler
FrameGridScheduler
AudioSampleGrid
AudioFormatNormalizer
AudioBoundaryResolver
ZeroCrossingDetector
MicroFadePlanner
CrossfadeCollisionResolver
EncoderDelayCompensator
CollisionDetector
SequenceDurationCalculator
EDLVisualizer
TimelineDebugExport
```

## Kabul kriterleri

- Aynı anda base shot, source overlay, kinetic word, subtitle ve audio event çalışabilir.
- Track çakışmaları deterministik çözülür.
- A/V sync bir frame’in altındadır.
- Timeline debug hangi event’in hangi frame’de çalıştığını gösterir.
- Word timing ile motion event aynı frame-grid’i kullanır.
- Audio event’ler 48 kHz sample grid üzerinde deterministik derlenir.
- Uç uca PCM birleştirmelerinde boundary click/pop oluşmaz.
- Planlanmış narration sessizliği crossfade tarafından kapatılmaz.
- TTS kelime başlangıcı ve sonu fade ile kesilmez.
- Audio türüne uygun boundary policy metadata’da görünürdür.

---

# Faz 4 — Motion Renderer Temeli

## Amaç

Statik full-screen görseller yerine deklaratif, katmanlı composition üretmek.

## Teknoloji

```text
Python → render props JSON
Remotion + React → sequence render
FFmpeg → normalize, mux, final encode
```

## Yapılacaklar

- Python–Remotion bridge
- Typed JSON props
- Composition registry
- Shared design system
- Deterministic rendering
- Headless rendering
- Sequence preview
- Full render orchestration
- Renderer metadata
- Artifact registry entegrasyonu
- Successful / failed / cancelled artifact ayrımı
- Ephemeral frame ve temp-file cleanup hook’ları
- Job sonunda orphan temp cleanup
- Error propagation

## Design system

```text
Typography scale
Spacing scale
Color tokens
Evidence yellow
Neutral document palette
Dark quote-card palette
Chart palette
Motion easing library
Transition durations
Caption safe areas
```

## Kabul kriterleri

- Tek sequence içinde 5+ katman render edilir.
- Screenshot üzerinde crop + zoom + highlight aynı timeline’da çalışır.
- Text ve chart motion word cue’larına bağlanır.
- Aynı input aynı output’u üretir.
- Sequence bağımsız preview edilebilir.
- Renderer’ın ürettiği her ara ve final dosya Artifact Registry’ye kaydedilir.
- Başarılı veya iptal edilmiş job sonunda kayıtsız temp dosyası kalmaz.
- Renderer lock’lu/approved artifact’i overwrite edemez.

---

# Faz 5 — Core Motion Template Library

## Amaç

Tutarlı görsel dil üreten reusable composition kütüphanesi oluşturmak.

## Template seti

1. `cold_open_source_montage`
2. `chapter_title`
3. `article_focus_scan`
4. `headline_to_paragraph_zoom`
5. `highlight_wipe`
6. `expert_quote_card`
7. `metric_reveal`
8. `metric_comparison`
9. `animated_line_chart`
10. `animated_bar_chart`
11. `process_diagram`
12. `agent_loop_diagram`
13. `equation_morph`
14. `product_ui_focus`
15. `terminal_demo`
16. `split_screen_comparison`
17. `icon_multiplication`
18. `timeline_progression`
19. `news_clip_context`
20. `final_thesis_card`
21. `kinetic_keyword`
22. `numeric_punch`
23. `quote_word_highlight`
24. `caption_phrase`

## Her template’in parametreleri

```text
duration
layout
source asset
target region
entry animation
exit animation
camera motion
emphasis spans
word timings
color theme
caption
source label
safe areas
```

## Core template ve domain preset ayrımı

Core template’ler domain bağımsız composition capability’leridir. `agent_loop_diagram`, `product_ui_focus` ve `terminal_demo` gibi business-tech ağırlıklı template’ler ilk pack’in capability bundle’ında tutulabilir; core registry bunları yalnızca capability ID olarak bilir. Domain Pack:

- tercih edilen template’leri,
- yasak veya düşük öncelikli template’leri,
- renk/tipografi/tone preset’lerini,
- gerekli template capability’lerini

belirtir. Yeni domain için renderer fork edilmez.

## Kalite kuralları

- Random effect yoktur.
- Easing ailesi tutarlıdır.
- Motion okunabilirliği bozmaz.
- Subtitle safe area korunur.
- Kinetic text yalnızca gerekli span’lerde kullanılır.
- Aynı template art arda sınırsız kullanılmaz.

## Kabul kriterleri

- En az 15 template production kalitesinde çalışır.
- Word-timed kinetic template’ler frame-accurate çalışır.
- Aynı template farklı asset ve verilerle kullanılabilir.
- Template seçiminde editorial role kullanılabilir.
- Template registry domain pack preference/bans uygulayabilir.
- Business-tech preset’i kaldırıldığında core template’ler yine parse ve render edilebilir.

---

# Faz 6 — Source Acquisition ve Evidence Treatment Engine

## Amaç

Kaynak edinmeyi yalnızca headless browser scraping olarak görmeden, erişim durumuna göre güvenli ve gerçekçi bir acquisition ladder oluşturmak.

Kaynak öncelikleri global sabit değildir. Seçili Domain Pack, source type ranking ve zorunlu source sınıflarını `SourcePriorityPolicy` üzerinden sağlar. Acquisition adapter’ları ortak kalır.

Örnek:

```text
business-tech: regulator/SEC → investor relations → official report → trusted press
true-crime-legal: court record → indictment/judgment → police/prosecutor statement → trusted reporting
```

## Source Acquisition Ladder

### Seviye 1 — Birincil, doğrudan erişilebilir kaynaklar

- SEC ve eşdeğer resmî kayıtlar
- Şirket investor relations
- Resmî PDF raporlar
- Basın açıklamaları
- Mahkeme belgeleri
- Düzenleyici kurum sayfaları
- Resmî sunumlar

### Seviye 2 — Erişilebilir HTML

Playwright adapter:

- DOM text search
- Headline detection
- Paragraph detection
- Date/source extraction
- Scroll plan
- Crop region calculation
- Screenshot veya short recording

### Seviye 3 — Feed ve API

- RSS
- Resmî API
- Haber sağlayıcı API
- SEC/EDGAR veri akışları
- Structured press release feeds

Bu kaynaklarda, doğrulanmış metin kendi branded evidence card template’imizle gösterilebilir.

### Seviye 4 — Kullanıcı destekli capture

Review UI veya browser extension:

```text
Kullanıcı sayfayı normal tarayıcıda açar
→ hedef paragrafı seçer
→ URL + DOM + screenshot + timestamp alınır
→ source package oluşturulur
```

### Seviye 5 — Screenshot olmadan source treatment

Görsel erişim yok ama bilgi doğrulanmışsa:

- Publisher adı
- Tarih
- Doğrulanmış kısa paraphrase
- Headline veya document label

ile evidence card oluşturulur.

## Bot ve paywall politikası

Sistem:

- Cloudflare/DataDome challenge aşmaya çalışmaz.
- CAPTCHA çözmez.
- Gizli browser fingerprint bypass uygulamaz.
- Yetkisiz paywall erişimi denemez.

Yalnızca durumu tespit eder ve uygun fallback’e geçer.

## Source statüleri

```text
accessible
challenge_detected
paywall_detected
cookie_wall_detected
authentication_required
manual_capture_required
text_found
text_not_found
snapshot_available
unavailable
```

## Evidence treatment

```text
full-page establish
→ headline crop
→ target paragraph focus
→ sentence highlight
→ number callout
→ source label and date
```

## SourceCapturePlan

```text
source_id
acquisition_adapter
url
access_status
target_text
target_dom_path
crop_regions
scroll_events
highlight_events
source_label
publication_date
fallback_mode
```

## Teslimatlar

```text
SourceAdapterRegistry
OfficialPdfAdapter
AccessibleHtmlAdapter
FeedApiAdapter
ManualCapturePackage
ChallengeDetector
EvidenceTreatmentPlanner
DOMRegionExtractor
SourcePreviewRenderer
```

## Kabul kriterleri

- Challenge ekranı final videoya giremez.
- Target text bulunmazsa koordinat uydurulmaz.
- Aynı belge içinde üç farklı focus event üretilebilir.
- Paywall/challenge durumu yalnızca loglanmaz; deterministic fallback seçilir.
- Playwright olmadan da source evidence üretilebilir.
- Source ranking seçili domain policy’sine göre değişebilir; adapter kodu domain için fork edilmez.
- Bir domain’in zorunlu primary-source şartı karşılanmazsa planner’a geçiş engellenebilir.

---

# Faz 7 — Data Visualization ve Metric Engine

## Amaç

Grafik ve metrikleri ayrı slayt olmaktan çıkarıp narration’ın görsel argümanına dönüştürmek.

## Yapılacaklar

- Declarative chart specification
- Line, bar, area, stacked, comparison, waterfall ve timeline chart
- Axis reveal
- Label reveal
- Line draw
- Bar grow
- Value callout
- Before/after transition
- Series focus
- Source caption
- Unit/currency validation
- Domain-neutral timeline, map, relationship graph ve evidence-chain specifications
- Metric count-up/count-down
- Equation morph
- Word-cued animation

## Chart metadata

```text
expected series
rendered series
unit
period
currency
source claim IDs
source references
animation stages
```

## Kabul kriterleri

- Chart animation narration fiiline bağlanabilir.
- Rendered values metadata ile doğrulanabilir.
- Aynı chart içinde farklı zamanlarda farklı noktalar vurgulanabilir.
- Metric ve chart bağımsız slide gibi görünmez.
- Business revenue chart ile legal movement timeline aynı declarative visualization core’unu kullanabilir.
- Domain Pack desteklenmeyen veya etik açıdan sakıncalı visualization türlerini engelleyebilir.

---

# Faz 8 — Asset Ingestion, Catalog ve Semantic Index

## Amaç

Asset seçimini dosya adı veya keyword eşleşmesinden çıkarıp provenance ve semantik bilgiye dayalı sisteme dönüştürmek.

## Asset kaynakları

Aşağıdaki liste ilk `business-tech` pack için başlangıç kaynaklarıdır; core asset catalog yalnızca provider, provenance ve semantic metadata’yı bilir.

- Resmî şirket görselleri
- Wikimedia Commons
- Pexels / Pixabay
- Haber ve keynote klipleri
- Podcast klipleri
- Ürün ekran kayıtları
- Şirket, kişi ve lokasyon görüntüleri
- Kullanıcı local library

## AssetRecord alanları

```text
asset_id
provider
source_url
license_mode
allowed_uses
media_type
duration
resolution
fps
codec
visual_family_id
subjects
actions
setting
mood
semantic_tags
avoid_contexts
domain_roles
domain_sensitivity_tags
source_hash
multi-frame perceptual fingerprints
selected ranges
source audio eligibility
```

## Semantic AssetBrief

```json
{
  "editorial_role": "show_operational_consequence",
  "subject": "developers using AI coding tools",
  "action": "reviewing generated code",
  "setting": "software engineering workspace",
  "avoid": [
    "generic server rooms",
    "abstract binary",
    "people typing without visible code"
  ],
  "preferred_asset_type": "screen_recording_or_real_broll"
}
```

## Duplicate ve visual-family sistemi

- Multi-frame pHash
- ORB/local feature similarity
- Same-source detection
- Selected-range detection
- Visual family ID
- Reuse cooldown
- Chapter-level family budget

## Kabul kriterleri

- Aynı server-room ailesi ilgisiz kavramlarda tekrar seçilemez.
- `avoid` alanları uygulanır.
- Her asset’in semantik açıklaması ve visual family ID’si vardır.
- Generic stock fallback oranı ölçülür.
- Source audio eligibility asset catalog’a yazılır.
- AssetBrief seçili Domain Pack’in visual grammar ve avoid-context kurallarını taşır.
- Core catalog `server_room`, `crime_scene` gibi kategorileri zorunlu enum olarak hard-code etmez.

---

# Faz 9 — Manual LLM Gateway, Research Engine ve Persistent Claim Store

## Amaç

Kullanıcıya manuel araştırma yaptırmadan; web erişimli yapay zekâ arayüzünü araştırmacı olarak kullanan, API maliyeti gerektirmeyen, kaynak bazlı ve doğrulanabilir bir pipeline kurmak.

## Kullanıcı deneyimi

Kullanıcı konu ile birlikte domain seçer veya sistemden öneri alır:

```text
Domain: Business & Technology
Project type: Company collapse
```

Domain selection confidence düşükse kullanıcı onayı olmadan research başlamaz.

Kullanıcı yalnızca konuyu girer:

```text
IBM Hisseleri Neden Sert Düştü?
```

Kurgu Engine şu akışı yönetir:

```text
research discovery task hazırla
→ prompt/context/schema paketini kullanıcıya sun
→ kullanıcı paketi web erişimli ChatGPT/Claude/Gemini arayüzünde çalıştırır
→ JSON sonucu uygulamaya yapıştırır veya yükler
→ URL/schema/source-lineage doğrulanır
→ geçerli sonuç persistent store’a kaydedilir
→ sıradaki research task otomatik açılır
```

Kullanıcı kaynak aramaz, SEC belgesi okumaz, rakam tablosu hazırlamaz ve chronology yazmaz.

## Faz 9A — LLM Task Gateway ve backend sözleşmesi

Her LLM işi:

```text
task_id
task_type
project_id
input_manifest
prompt_template
context_artifacts
expected_output_schema
backend_mode
status
attempt
parent_task_id
created_at
completed_at
```

taşır.

Backend modları:

```text
REPLAY
MANUAL_UI
LOCAL_MODEL
API
```

İlk production-like çalışma modu `MANUAL_UI` olacaktır.

## Manual task paketi

```text
llm_tasks/<task_id>/
  README.md
  prompt.md
  input_manifest.json
  topic_or_scope.json
  domain_profile.json
  resolved_domain_policies.json
  relevant_sources.json
  relevant_claims.json
  expected_output.schema.json
  response/
```

Studio UI butonları:

```text
Promptu Kopyala
Görev Paketini İndir
ChatGPT / Claude / Gemini Arayüzünü Aç
Yanıtı Yapıştır
JSON Yükle
Doğrula
Kabul Et
Repair Görevi Oluştur
```

## Faz 9B — Research discovery ve source candidate generation

Web erişimli yapay zekâ, seçili Domain Pack’in research prompt bundle ve source policy’siyle:

```text
Topic
→ başlık varsayımını test et
→ araştırma soruları üret
→ source discovery yap
→ candidate sources döndür
→ source authority ve source type öner
```

Kurgu Engine deterministik olarak:

- URL biçimini ve erişilebilirliği kontrol eder.
- Publisher/domain eşleşmesini kontrol eder.
- Duplicate kaynakları birleştirir.
- Seçili domain policy’sine göre resmî/birincil kaynakları önceliklendirir.
- Paywall/challenge/manual capture durumunu kaydeder.
- Uydurma veya erişilemeyen URL’yi onaylanmış kaynak yapmaz.

## Faz 9C — Source-by-source extraction

Her LLM görevi tek kaynak veya küçük kaynak grubu işler.

Çıktı:

```text
source metadata
facts
source spans
numbers and units
quotes and speakers
dates
people and organizations
uncertainties
contradictions
visual opportunities
```

Model kaynakta olmayan bilgi ekleyemez. Doğrudan alıntı source span’e bağlanır.

## Faz 9D — Claim normalization

Aynı iddialar birleştirilir:

```text
claim_id
canonical claim text
claim type
domain claim status
confidence
supporting sources
contradicting sources
numbers
time period
visual potential
```

Stable claim ID’yi LLM değil `ClaimService` verir.

## Faz 9E — Contradiction ve chronology

- Kaynak çelişkileri görünür hâle getirilir.
- Olaylar tarih sırasına yerleştirilir.
- Şirket iddiası, üçüncü taraf yorumu ve doğrulanmış gerçek ayrılır.
- Davalar, iddialar, kararlar ve sonuçlar aynı statüde gösterilmez.
- Claim wording ve status geçişleri seçili Domain Pack’in taxonomy/safety kurallarıyla doğrulanır.
- Güvenli wording önerileri üretilir; örneğin kaynaklar yüzde konusunda farklıysa yaklaşık ifade önerilir.

## Persistent store

```text
SQLite başlangıçta
PostgreSQL ihtiyaç halinde
+ JSONL export
+ stable IDs
+ content hashes
+ source versions
+ LLM task lineage
```

## Repair döngüsü

Geçersiz sonuçta uygulama bütün görevi baştan yazdırmaz:

```text
original_response.json
validation_errors.json
repair_prompt.md
expected_output.schema.json
```

paketi üretir. Repair prompt yalnızca belirli hataları düzeltir.

## Teslimatlar

```text
LLMBackend protocol
ReplayBackend
ManualUIBackend
LocalModelBackend interface
ApiBackend interface
LLMTaskService
TaskPackageBuilder
LLMResultImporter
LLMResultValidator
RepairTaskBuilder
SourceDiscoveryService
SourceRanker
SourceExtractor
ClaimNormalizer
ClaimStore
ContradictionDetector
ChronologyBuilder
DomainAwareResearchPolicyResolver
DomainClaimTaxonomyValidator
research/*.jsonl
```

## Kabul kriterleri

- API anahtarı olmadan yeni bir topic için research süreci tamamlanabilir.
- Kullanıcı internet araştırmasını elle yapmaz; yalnızca görev paketini arayüze taşır ve sonucu içe aktarır.
- Her kritik finansal iddia güvenilir kanıtla bağlıdır.
- Alıntılar source span ile eşleşir.
- Çelişkili kaynaklar görünürdür.
- Research tekrar başlatıldığında bütün geçmişi prompta yapıştırmak gerekmez.
- Tek LLM çağrısı bütün belgeseli araştırmaz.
- Uydurma URL veya var olmayan claim ID kabul edilmez.
- Onaylanmış research çıktısı `REPLAY` fixture olarak tekrar kullanılabilir.
- Ticari AI web arayüzü otomatik browser botuyla sürülmez.
- Research task package aktif domain profile ve policy snapshot’ını içerir.
- Business-tech promptları core gateway içine gömülü değildir; pack bundle’dan yüklenir.
- Farklı bir örnek domain manifest’i ile research task schema’sı core kod değiştirmeden üretilebilir.

---

# Faz 10 — Hierarchical Story, Narrative ve Editorial Planner

## Amaç

10–20 dakikalık belgeseli tek prompt yerine hiyerarşik ve sequence bazlı olarak planlamak; bütün planner görevlerini aynı LLM Gateway üzerinden `REPLAY`, `MANUAL_UI`, `LOCAL_MODEL` veya ileride `API` modunda çalıştırmak.

Planner’ın beat seçimi, narration wording’i, evidence standardı, visual grammar ve safety kuralları aktif Domain Pack’ten çözülür. Core planner yalnızca hierarchical orchestration, context slicing ve deterministic assembly yapar.

## Faz 10A — Global story architecture

Yalnızca kompakt üst plan oluşturulur:

```text
hook
central question
chapters
major reveals
counterarguments
payoff
final question
```

Bu aşamada frame veya asset URL üretilmez.

## Faz 10B — Chapter briefs

Her chapter:

```text
chapter goal
entry state
exit state
claim IDs
required evidence
main reveal
counterpoint
visual opportunities
continuity handoff
estimated duration
```

alanlarını taşır.

## Faz 10C — Narrative beat planning

Core beat türleri:

```text
hook
context
promise
rise
reveal
contradiction
mechanism
example
consequence
counterargument
payoff
chapter_reset
final_question
reconstruct_timeline
compare_accounts
introduce_entity
```

Domain Pack ek beat subtype veya constraint tanımlayabilir; core enum’u çatallanmaz.

Her beat yaklaşık 20–60 saniyelik anlatı amacıdır.

## Faz 10D — Sequence planning

Her LLM çağrısı yalnızca bir veya birkaç sequence üretir.

Önerilen çağrı sınırı:

```text
30–90 saniye narration
3–8 claim
5–15 asset brief
10–30 edit event
```

## Planner görev yürütme politikası

- Geliştirme testlerinde onaylanmış planner çıktıları `REPLAY` olarak kullanılır.
- İlk gerçek videolarda global outline, chapter, beat ve sequence planları `MANUAL_UI` görev paketleriyle çalıştırılır.
- API backend’i bu fazın acceptance kriteri değildir.
- Her sonuç schema, claim ID, cue ve template capability bakımından içe aktarılırken doğrulanır.
- Geçersiz sonuç için dar kapsamlı repair task üretilir.

## Sequence planner context’i

LLM’ye yalnızca:

- İlgili chapter brief
- İlgili claim’ler
- İlgili evidence item’lar
- Son iki sequence’in continuity state’i
- Kullanılmaması gereken asset aileleri
- Mevcut template capability listesi
- Aktif domain profile, narrative patterns, visual grammar ve safety policy

verilir.

## Faz 10E — Local validation

Her sequence ayrı doğrulanır:

- Claim coverage
- Cue validity
- Duration
- Visual role coverage
- Asset brief quality
- Edit-event density
- Continuity constraints

## Faz 10F — Deterministic assembly

LLM final project JSON’u birleştirmez.

Compiler:

- Sequence dosyalarını sıralar.
- Stable ID ve dependency kontrolü yapar.
- Global EDL’ye derler.
- Cross-sequence collision ve continuity kontrolü yapar.

## Planner output

```text
narration span
claim IDs
editorial role
preferred composition
asset brief
edit event plan
text emphasis plan
audio direction
continuity constraints
```

## Kabul kriterleri

- Tek prompt bütün filmi üretmez.
- Bir sequence bozulduğunda yalnızca o sequence yeniden planlanabilir.
- Her narration span için “neden bu görsel?” cevabı vardır.
- Planner generic stock’u varsayılan olarak seçmez.
- Belge → grafik → quote gibi kanıt zincirleri kurabilir.
- Sequence başına birden fazla edit event üretir.
- Planner API anahtarı olmadan `MANUAL_UI` modunda tamamlanabilir.
- Aynı task paketi farklı LLM arayüzlerinde çalıştırılabilir.
- Backend değişimi sequence schema veya project state’i değiştirmez.
- Domain pack değişimi explicit migration olmadan mevcut project state’ini sessizce değiştirmez.
- Aynı core planner `business-tech` ve contract-only dummy pack ile task package üretebilir.
- True Crime/Legal eklendiğinde allegation/conviction gibi statüler planner wording’ini deterministik olarak sınırlar.
- Onaylanmış planner sonucu `REPLAY` olarak renderer geliştirmesinde tekrar kullanılabilir.

---

# Faz 11 — Audio Director ve Source Audio Eligibility

## Amaç

Videonun sesini narration + tek BGM olmaktan çıkarırken source audio ve BGM çatışmasını engellemek.

## Audio bus önceliği

```text
1. Narration
2. Source speech
3. Editorial SFX
4. Natural ambience
5. Background music
```

## Source audio sınıfları

```text
clean_speech
speech_with_ambience
embedded_music
ambience_only
unusable
disabled
```

## SourceAudioAnalysis

```text
speech_presence_score
music_contamination_score
noise_score
speech_intelligibility_score
source_audio_mode
recommended_duration
bgm_conflict_policy
narration_conflict_policy
```

## Kullanım politikası

### `clean_speech`

- Narration durur.
- BGM hard-duck veya mute olur.
- 2–6 saniyelik source konuşma kullanılır.
- Source audio fade-out sonrası narration geri gelir.

### `speech_with_ambience`

- Kısa gerçeklik dokunuşu olarak kullanılabilir.
- BGM ağır biçimde duck edilir.
- Source speech ile narrator aynı anda konuşmaz.

### `embedded_music`

Varsayılan:

```text
source_audio_allowed = false
```

Görüntü sessiz kullanılabilir.

Konuşma:

- narrator paraphrase,
- quote card,
- transcript overlay

ile aktarılır.

### `ambience_only`

- Çok düşük seviyede ve kısa kullanılabilir.
- Narration intelligibility’yi etkilemez.

## Müzik ayrıştırma politikası

AI vocal/music separation:

- MVP acceptance için zorunlu değildir.
- Varsayılan otomatik çözüm değildir.
- Artifact veya müzik kalıntısı varsa çıktı reddedilir.
- İleride opsiyonel enhancement olarak eklenebilir.

## Diğer Audio Director görevleri

- Chapter-based music segmentation
- Music intensity curve
- Narration ducking
- Reveal drop
- Impact/riser
- Paper/typing/UI click SFX
- Ambience layers
- Loudness normalization
- PCM-first intermediate audio pipeline
- Audio-type-specific boundary profiles
- Zero-crossing ve micro-pop prevention
- Transition-safe fades

## Audio boundary policy

Her `AudioEvent` video frame’ine ek olarak sample zamanlarını taşır:

```text
start_ms
end_ms
start_sample
end_sample
fade_in_ms
fade_out_ms
crossfade_ms
fade_curve
boundary_policy
fade_profile
```

`boundary_policy`:

```text
none
zero_crossing
micro_fade
overlap_crossfade
planned_silence
long_editorial_fade
```

`fade_profile`:

```text
narration
source_speech
ambience
bgm
impact
ui_sfx
```

Varsayılan başlangıç profilleri:

| Ses tipi | Fade-in | Fade-out / Crossfade | Not |
|---|---:|---:|---|
| Narration parçası | 5–10 ms | 8–15 ms | Kelime onset’i korunur |
| Source speech | 10–20 ms | 15–30 ms | Editoryal girişte 80–200 ms uygulanabilir |
| Ambience | 200–800 ms | 300–1000 ms | Oda değişimi hissi engellenir |
| BGM | 500–1500 ms | 500–1500 ms | Chapter geçişi 1–3 sn olabilir |
| Impact | 0–3 ms | 10–30 ms | Attack öldürülmez |
| UI click | 0–1 ms | 2–8 ms | Çok kısa SFX korunur |

İki narration parçası arasında planlanmış pause varsa overlap crossfade uygulanmaz. Kesim noktası uygun olduğunda ±2–5 ms içinde zero-crossing aranır; uygun nokta yoksa micro-fade kullanılır.

## Micro-pop detection

Boundary çevresinde:

```text
sample amplitude discontinuity
derivative spike
true-peak spike
DC offset discontinuity
```

ölçülür. Eşik aşılırsa boundary yeniden işlenir veya validation warning oluşur.

## AudioEvent türleri

```text
music_start
music_change
music_drop
music_resume
impact
riser
paper
keyboard
ui_click
source_speech_in
source_speech_out
ambience_in
ambience_out
```

## Kabul kriterleri

- Narration ve source speech üst üste konuşmaz.
- Embedded source music ile Kurgu Engine BGM’i çakışmaz.
- Her chapter’ın müzikal durumu vardır.
- Source audio yalnızca eligibility kontrolünü geçen kliplerde kullanılır.
- Her kesmeye SFX eklenmez.
- Final loudness tutarlıdır.
- Audio timeline 48 kHz sample grid üzerinde derlenir.
- Uç uca ses birleşimlerinde duyulur micro-pop/click bulunmaz.
- Fade/crossfade profilleri audio türüne göre seçilir.
- Planlanmış sessizlikler crossfade tarafından kapatılmaz.
- Ara audio artifact’leri PCM tabanlıdır; MP3/AAC yalnızca final export’ta kullanılır.
- Impact ve consonant attack’ları boundary treatment sırasında kaybolmaz.

---

# Faz 12 — Continuity ve Pacing Director

## Amaç

Video boyunca görsel çeşitlilik, motion grammar, template dağılımı, renk dengesi ve ritmi yönetmek.

## Takip edilen state

```text
last visual family
last composition template
last color palette
last source type
last camera direction
last transition
last focus position
last chart type
last quote card
last stock category
last audio intensity
last kinetic text pattern
```

## Continuity kuralları

- Üç benzer article treatment üst üste gelmez.
- Aynı visual family cooldown süresinden önce tekrar kullanılamaz.
- Aynı template art arda maksimum iki kez kullanılabilir.
- Hareket yönleri sürekli aynı olmaz.
- Yoğun evidence bölümünden sonra visual reset uygulanır.
- Chapter kartları attention reset olarak kullanılır.
- V5 kinetic emphasis sürekli görünmez.

Continuity ve pacing default’ları Domain Pack tarafından override edilebilir. Business-tech hızlı evidence/metric ritmi kullanabilirken future true-crime/legal pack daha kontrollü timeline, belge okuma ve mağdur hassasiyeti temposu kullanabilir.

## Pacing modeli

```text
Hook: hızlı ve yüksek edit-event yoğunluğu
Evidence: orta, okunabilir source focus
Mechanism: açıklayıcı, aşamalı motion
Example: daha somut ve değişken
Payoff: yavaşlatılmış vurgu
Chapter reset: kısa nefes
```

## Ölçümler

```text
base shots per minute
edit events per minute
source focus duration
static duration
composition diversity
visual family reuse
kinetic emphasis density
chapter tempo curve
```

## Faz 12A - Executable Editorial Integration

Faz 12, Faz 10 planner'inin assembly request olarak kalan çıktısını doğrudan
renderer'a göndermez. Deterministik bir integration compiler; onaylı
asset/range/crop adaylarını, Faz 5 template capability'lerini, Faz 7
visualization referanslarını ve Faz 11 audio direction'ını policy snapshot
altında immutable executable editorial plan'a bağlar. Bu plan mevcut Faz 3
compiler tarafından multi-track final EDL'ye derlenir.

Bu katman source URL, frame koordinatı veya renderer props'u uydurmaz; eksik
provenance, capability, asset, policy veya continuity girdisi fail-closed olur.
Planner-asset-EDL akışının sahibi Faz 12'dir; Faz 10'un bounded acceptance'i
bu çalışmayı sessizce tamamlanmış saymaz.

## Kabul kriterleri

- Planner, asset catalog, template capability, visualization ve audio
  direction girdileriyle iki aynı replay'de byte-identical executable plan ve
  final EDL üretilir.
- Eksik/onaysız asset, range, crop, capability, policy veya continuity
  referansı executable plan ya da EDL'ye dönüşemez.

- Video boyunca visual family tekrarları raporlanır.
- Edit-event density chapter’a göre değişir.
- Uzun source sahnelerinde iç motion vardır.
- Aynı server-room görüntüsü ilgisiz kavramlarda kullanılmaz.
- Ortalama shot süresi tek başına kalite ölçütü değildir.
- Pacing kuralları aktif domain profile’dan gelir ve project metadata’da sürümlenir.

---

# Faz 13 — Studio UI, Manual LLM Gateway ve Human-in-the-loop Review

## Amaç

Kurgu Engine’i terminal/script koleksiyonundan çıkarıp; araştırma görevlerini, proje durumunu, render’ı ve sequence review’ı tek ürün arayüzünden yönetmek.

Bu faz tek seferde en sona bırakılmaz; üç seviyede gelişir.

## Faz 13A — Developer Console

**Başlangıç zamanı:** Faz 1 ile birlikte temel shell; Faz 4’e kadar çalışır hâle gelir.

Ekranlar:

```text
Project Dashboard
Project Create/Open
Domain and Project Type Selection
Active Domain Pack / Policy Version
Pipeline Stage Status
Job Progress
Logs
Sequence Preview
Artifact List
Storage Usage
Validation Summary
```

Amaç estetik değil, motorun görünür ve kontrol edilebilir olmasıdır.

## Faz 13B — Manual LLM Gateway UI

**Başlangıç zamanı:** Faz 9 ile birlikte.

LLM Tasks ekranı:

```text
pending / waiting / valid / repair_required / approved
research discovery
source extraction
claim normalization
story architecture
chapter planning
sequence planning
repair task
```

Bir görevde:

```text
Promptu Kopyala
Context Paketini İndir
Web AI Arayüzünü Aç
Yanıtı Yapıştır
JSON Yükle
Validation Sonucunu Gör
Kabul Et
Repair Task Oluştur
```

Kullanıcı dosya adı, stable ID veya klasör yönetmek zorunda kalmaz.

## Faz 13C — Production Review Studio

**Başlangıç zamanı:** Faz 12 sonrası.

Ana bölümler:

```text
Overview
Domain Profile
Research
Sources
Claims
Story
Script
Sequences
Assets
Timeline
Audio
Review
Exports
Logs
Storage
```

## Sequence review ekranı

```text
Narration
Claims
Evidence
Editorial role
Selected template
Selected asset
Source crop preview
Word timing preview
Kinetic emphasis preview
Audio eligibility
Multi-track timeline preview
Alternative assets
Validation warnings
```

## Kullanıcı aksiyonları

- Asset değiştir
- Crop/highlight değiştir
- Template değiştir
- Quote veya chart verisini kontrol et
- Kinetic emphasis azalt/artır
- Source audio’yu kapat
- Sequence’i yeniden planla
- Preview render et
- Sequence’i onayla ve hash ile kilitle

## Teknoloji

```text
Frontend: React + TypeScript + Vite
Data: TanStack Query
Local UI state: Zustand veya eşdeğeri
Styling/components: Tailwind + erişilebilir component library
Progress: SSE; gerçek çift yönlü ihtiyaç oluşursa WebSocket
Backend: thin FastAPI Studio API
Database: SQLite başlangıçta
```

Timeline ve waveform için özel React bileşenleri kullanılabilir; ilk sürümde tam NLE/Premiere klonu yapılmaz.

## Render davranışı

- Yalnızca değişen sequence yeniden render edilir.
- Onaylanan sequence hash ile kilitlenir.
- Full video her küçük değişiklikte yeniden render edilmez.
- Job progress ve failure nedeni UI’da canlı görünür.

## Teslimatlar

```text
studio-ui/
studio-api/
Project Dashboard
LLM Task Inbox
Task Detail / Import / Validation
Research and Claim views
Story/Chapter view
Sequence Review view
Render Progress view
Storage/GC view
Generated TypeScript API client
```

## Kabul kriterleri

- Proje UI’dan oluşturulup tekrar açılabilir.
- API anahtarı olmadan Manual LLM task oluşturma/import/repair akışı tamamlanabilir.
- Kullanıcı araştırmayı elle yapmaz ve bütün JSON’u manuel düzenlemek zorunda kalmaz.
- Problemli sequence 1–2 işlemle değiştirilebilir.
- Sequence preview hızlı üretilir.
- Onaylanan sequence istemeden yeniden planlanmaz.
- React dosya sistemine veya engine fonksiyonuna doğrudan erişmez.
- UI ile backend arasındaki sözleşme OpenAPI üzerinden test edilir.
- Spring Boot bu fazın gereksinimi değildir.
- Proje oluştururken domain seçilebilir; seçili pack/version ve policy snapshot görüntülenebilir.
- UI desteklenmeyen domain’i “business-tech gibi” sessizce çalıştırmaz.
- Domain migration kullanıcı onayı ve impact preview olmadan uygulanmaz.

---

# Faz 14 — Render Cache, Artifact Lifecycle, Storage Garbage Collection ve Performance Architecture

## Amaç

Kalite mimarisi oturduktan sonra incremental render maliyetini ve disk tüketimini kontrol etmek; onaylı veya final artifact’leri riske atmadan yeniden üretilebilir ara çıktıları otomatik yönetmek.

## Artifact Registry

Her artifact merkezi registry’ye yazılır:

```json
{
  "artifact_id": "artifact_seq_004_preview_v7",
  "artifact_type": "sequence_preview",
  "project_id": "project_ibm",
  "sequence_id": "seq_004",
  "created_at": "2026-07-24T10:30:00+03:00",
  "last_accessed_at": "2026-07-24T11:10:00+03:00",
  "content_hash": "sha256:...",
  "size_bytes": 428103992,
  "retention_class": "temporary",
  "dependency_ids": [],
  "locked": false,
  "pinned": false,
  "approved": false,
  "producer": "motion_renderer",
  "producer_version": "0.4.2",
  "job_id": "job_...",
  "status": "complete"
}
```

## Retention sınıfları ve varsayılan politika

| Sınıf | Örnek | Varsayılan saklama |
|---|---|---|
| `ephemeral` | frame, temp PCM, concat list | Başarılı job sonrası hemen veya 1–6 saat |
| `temporary` | başarısız/yarım render, kilitlenmemiş preview | 24–72 saat |
| `cache` | normalized asset, chart, alignment, sequence cache | 7–30 gün + LRU |
| `review` | kullanıcı incelemesine sunulan preview | 7–14 gün; review bekliyorsa korunur |
| `approved` | onaylanmış sequence render | Otomatik TTL uygulanmaz |
| `final` | final MP4, subtitle ve export paketi | Otomatik silinmez |
| `provenance` | source snapshot, lisans, source manifest | Proje/final var oldukça korunur |
| `baseline` | benchmark/baseline artifact | GC dokunamaz |
| `pinned` | manuel sabitlenen artifact | GC dokunamaz |

Retention süreleri config ile değiştirilebilir; silent default veya runtime’da keyfî eşik değiştirme yapılamaz.

## Dependency-aware mark-and-sweep

### Mark

Aşağıdaki artifact’ler ve tüm dependency zincirleri korunur:

```text
aktif project version
aktif render job
approved sequence
final export
provenance
baseline
pinned artifact
review bekleyen artifact
```

### Sweep

Yalnızca:

```text
referanssız
kilitlenmemiş
TTL süresi geçmiş
aktif job tarafından kullanılmayan
retention policy gereği silinebilir
```

artifact’ler temizlenir.

GC salt klasör modification time’a göre silme yapmaz.

## İki aşamalı silme

```text
workspace artifact
→ .trash/
→ grace period (24–72 saat)
→ permanent delete
```

Trash içeriği kullanıcı veya CLI tarafından grace period içinde geri yüklenebilir.

## Storage quota ve disk pressure

Örnek başlangıç politikası:

```text
Project soft quota: 25 GB
Project hard quota: 50 GB
Global cache soft quota: 100 GB
Global cache hard quota: 200 GB
Minimum free disk: %15 veya 30 GB
```

Soft quota aşımında temizleme sırası:

1. Süresi geçmiş `ephemeral`
2. Failed/cancelled job artifact’leri
3. Eski kilitlenmemiş preview’lar
4. LRU sequence render cache
5. LRU chart/audio/alignment cache
6. Yeniden indirilebilir normalized asset cache

Hard quota veya minimum free disk sınırı aşılırsa yeni production render başlamaz. Cleanup dry-run sonucu ve kullanıcıya önerilen işlem gösterilir.

## Content-addressable storage ve deduplication

Yeniden üretilebilir ortak asset/cache verisi hash tabanlı tutulur:

```text
cache/sha256/ab/cd/<full_hash>
```

Aynı fiziksel dosya farklı sequence/workspace’lerde kopyalanmaz. Uygun platformda hardlink/reflink; aksi durumda ortak object store referansı kullanılır.

## Cache katmanları

```text
source capture cache
normalized asset cache
motion template cache
sequence render cache
chart render cache
audio cache
alignment cache
subtitle cache
final composition cache
```

## Cache key bileşenleri

```text
source SHA-256
selected range
crop parameters
template version
renderer version
quality profile
text payload
data payload
audio hash
word timeline hash
```

## Performance işleri

- Sequence-level parallel rendering
- FFmpeg `filter_complex` composition
- Python per-frame callback’lerinden kaçınma
- Hardware encode profiles
- Render queue
- Incremental rebuild
- Preview/production profiles
- Render dependency graph
- Job-scoped temp directory
- Atomic artifact promotion: temp → complete

## CLI ve operasyonlar

```text
kurgu storage status
kurgu storage analyze <project_id>
kurgu storage clean --dry-run
kurgu storage clean --project <project_id>
kurgu storage clean --expired
kurgu storage pin <artifact_id>
kurgu storage unpin <artifact_id>
kurgu storage restore <artifact_id>
```

`--dry-run` şunları gösterir:

```text
artifact count
toplam reclaimable bytes
silme nedeni
retention class
dependency status
trash destination
```

## Teslimatlar

```text
ArtifactRegistry
ArtifactManifestWriter
RetentionPolicyEngine
DependencyMarker
GarbageCollector
TrashManager
StorageQuotaManager
DiskPressureGuard
ContentAddressableStore
StorageUsageReporter
CacheManager
IncrementalBuildPlanner
```

## Kabul kriterleri

- Tek sequence değişince yalnızca ilgili sequence render edilir.
- Cache stale output üretmez.
- Preview ve production ayrıdır.
- Renderer/artifact producer kayıtsız dosya bırakamaz.
- Approved, final, provenance, baseline ve pinned artifact’ler TTL nedeniyle silinmez.
- Her destructive cleanup çalıştırılmadan önce immutable deletion-plan/dry-run manifest’i üretilir.
- Dependency graph tarafından kullanılan artifact silinemez.
- Hatalı cleanup, grace period içinde restore edilebilir.
- Soft quota otomatik ve güvenli biçimde yönetilir.
- Hard quota altında disk tükenmeden render durdurulur.
- Deduplication tasarrufu ölçülür.
- Performance optimizasyonu görsel veya ses kalitesini düşürmez.

---

# Faz 15 — Validation, Observability ve Quality Gates

## Amaç

Sistemin başarısını dürüstçe ölçmek; validation’ı ürünün yerine koymamak.

## Validation katmanları

```text
Research validation
Claim/evidence validation
Source accessibility validation
Asset provenance validation
Semantic visual validation
Timeline validation
Word timing validation
Render-path validation
Pixel validation
Audio/pacing validation
Audio boundary and micro-pop validation
Source audio contamination validation
Storage/artifact lifecycle validation
Continuity validation
Artifact integrity
Package integrity
```

## Kalite metrikleri

```text
source evidence density
stock fallback ratio
visual family reuse
edit events per minute
composition diversity
chapter pacing
static interval duration
semantic mismatch count
unverified claim count
source-to-claim coverage
kinetic text density
source audio rejection rate
manual capture requirement rate
workspace size bytes
cache size bytes
orphan artifact count
expired artifact count
deduplication savings bytes
gc reclaimed bytes
audio boundary discontinuity count
micro-pop warning count
```

## Observability

- Run-scoped context
- Canonical phase registry
- JSONL logs
- FFmpeg progress
- Per-sequence render timing
- LLM call lineage
- Cache hit/miss
- Failure provenance
- Enabled source/asset/timing transport attempts, timeout, retry-budget,
  rate-limit and fallback decisions
- Source adapter decisions
- Artifact creation/deletion lineage
- Storage quota and disk-pressure events
- Audio boundary treatment decisions

## Kabul kriterleri

- Missing veya not-implemented rapor valid sayılamaz.
- Enabled live source, asset or timing transport uses an explicit mode policy;
  timeout, byte/MIME, redirect/SSRF, retry-budget, rate-limit and fallback
  outcomes are observable and testable. Unsupported modes fail closed.
- Threshold çıktı geçsin diye değiştirilemez.
- Validation gerçek video ve artifact’lerle çelişemez.
- Failure code gerçek kök nedene işaret eder.
- Bir source capture başarısız olduğunda challenge ekranı başarı sayılamaz.
- Source audio contamination tespit edilirse BGM ile mikslenmez.
- Domain Pack version/core contract uyumsuzluğu render’dan önce bloklanır.
- Domain-specific blocked wording veya unsupported legal status final narration’a geçemez.
- Validation extension’ı olmayan yeni domain production-ready sayılamaz.
- Registry dışında kalan orphan artifact görünür ve başarısız kalite durumu üretir.
- GC korunan dependency’yi silerse test başarısız olur.
- Audio boundary discontinuity eşiği aşılırsa warning veya otomatik remix uygulanır.

---

# Faz 16 — Reference Benchmark System

## Amaç

Kaliteyi soyut yorumlarla değil, sabit referanslarla karşılaştırmak.

## Referans seti

İlk `business-tech` pack için en az üç video:

1. Kaynak yoğun iş/teknoloji belgeseli
2. Şirket çöküşü belgeseli
3. Grafik ve UI yoğun açıklayıcı video

## Çıkarılacak metrikler

```text
chapter structure
base-shot density
edit-event density
source density
source treatment distribution
template distribution
stock ratio
chart ratio
quote-card ratio
kinetic text density
average static duration
audio transition patterns
source audio usage patterns
```

Her yeni Domain Pack ayrıca kendi en az üç kısa benchmark fixture’ını ve bir 3–5 dakikalık pilotunu sağlamadan production-ready kabul edilmez. Domain’ler birbirine yalnızca genel composition metrikleriyle değil, kendi safety/source/narrative kriterleriyle de ölçülür.

## Internal benchmark projeleri

```text
IBM — 3–4 dakika
WeWork — 6–8 dakika
Token Cost — 90 saniyelik referans segment
Long-form benchmark — 12–15 dakika
```

## Kabul kriterleri

- Benchmark karşılaştırması otomatik raporlanır.
- Sistem kendi önceki sürümüyle kıyaslanır.
- “Daha iyi görünüyor” yerine ölçülebilir farklar sunulur.
- Referans videonun marka kimliği kopyalanmaz; editoryal teknikler ölçülür.
- Business-tech kalitesi başka domain’e otomatik başarı olarak yazılmaz.
- Yeni pack kendi domain benchmark kapısını geçmeden UI’da production etiketi alamaz.

---

# Faz 17 — Production Packaging, Dağıtım ve Ürünleşme Kapısı

## Amaç

React + FastAPI + Python + Remotion mimarisini tek makinede çalışan geliştirme aracından sürdürülebilir local/beta ürüne dönüştürmek; Spring Boot veya daha ağır control-plane ihtiyacını yalnızca gerçek kullanım verisiyle değerlendirmek.

## İlk production stack’i

```text
React + TypeScript
FastAPI Studio API
Python engine workers
Remotion renderer
FFmpeg
SQLite local / PostgreSQL beta ihtiyacında
SSE progress
Docker Compose veya paketlenmiş local launcher
```

FastAPI kullanılması ürünleşmeye engel değildir. Spring Boot zorunlu production bileşeni değildir.

## Yapılacaklar

- Project workspace manager
- Selected source/asset transport operationalization without access-control
  bypass, with Phase 15 safety and observability evidence
- Selected trusted non-REPLAY timing producer for end-to-end projects
- Kalıcı job queue ve retry policy ihtiyaca göre
- Provider credentials ve secret management
- Asset/object storage politikası
- Project versioning
- Export presets
- Failure recovery
- LLM backend seçimi ve kullanım/maliyet raporu
- User roles yalnızca multi-user sürümde
- Review/approval flow
- Manual source capture extension
- Local launcher / Docker Compose
- Backup, project archive ve restore
- Health checks ve structured logs

## Spring Boot Decision Gate

Aşağıdaki ürün sinyalleri ölçülür:

```text
tek kullanıcı mı, çok kullanıcı mı?
aynı anda kaç aktif proje/render var?
billing/abonelik gerekiyor mu?
multi-tenant izolasyon gerekiyor mu?
kurumsal SSO/audit gerekiyor mu?
dağıtık worker orchestration FastAPI yapısını zorluyor mu?
```

Karar seçenekleri:

### A — FastAPI ile devam

Local ürün, tek kullanıcı veya küçük beta için ihtiyaçları karşılıyorsa mimari değiştirilmez.

### B — Spring Boot control-plane ekle

Gerçek ihtiyaç oluşursa:

```text
React
  → Spring Boot control-plane
      → Python worker API / queue
```

Spring tarafına proje/kullanıcı/billing/audit/orchestration taşınabilir. Python medya motoru ve Remotion yeniden yazılmaz.

### C — Parçalı geçiş

Yalnızca auth, billing ve multi-user project management Spring’e taşınır; medya ve render servisleri FastAPI/Python’da kalır.

## Çıktılar

```text
YouTube 16:9
Short preview
Subtitle SRT/VTT
Thumbnail source pack
Source manifest
License report
Chapter metadata
Description draft
Project archive
Local installer/launcher veya Docker Compose package
```

## Kabul kriterleri

- Proje tekrar açılıp düzenlenebilir.
- Render yarıda kalınca baştan başlamaz.
- Source ve license bilgileri export edilir.
- Kullanıcı bütün aşamaları UI’dan takip edebilir.
- LLM provider/backend değişimi proje verisini bozmaz.
- Ürün `MANUAL_UI` ile API maliyeti olmadan çalışabilir.
- React/FastAPI çözümü en az iki 10–15 dakikalık gerçek belgeselde baştan sona denenmiştir.
- Spring Boot kararı varsayımla değil ölçülen ürün ihtiyacıyla verilir.
- Spring eklenmese de production beta dağıtımı mümkündür.
- `docs/ROADMAP_SCOPE_RECONCILIATION.md` Deferred Delivery Ledger has no open
  row; two end-to-end projects exercise the selected supported source, asset
  and timing modes.

---

# 9. Fazlar Arası Bağımlılık

```text
Faz 0 — Baseline ve hafıza
  ↓
Faz 1 — V3 domain/workspace
  ↓
Faz 2 — Word timing ve temporal annotation
  ↓
Faz 3 — Multi-track EDL
  ↓
Faz 4 — Motion renderer
  ↓
Faz 5 — Core templates
  ├──────────────┐
  ↓              │
Faz 6 — Source acquisition/evidence
  ↓              │
Faz 7 — Charts/metrics
  ↓              │
Faz 8 — Asset catalog/semantic index
  ↓              │
Faz 9 — Manual LLM Gateway + research/claim store
  ↓              │
Faz 10 — Hierarchical planner ◀────┘
  ↓
Faz 11 — Audio director
  ↓
Faz 12 — Continuity/pacing
  ↓
Faz 13 — Studio UI + Manual LLM Gateway + Review
  ↓
Faz 14 — Cache/artifact lifecycle/GC/performance
  ↓
Faz 15 — Validation/observability
  ↓
Faz 16 — Benchmarks
  ↓
Faz 17 — Packaging + product gate
```

## Bağımlılık notları

- Faz 2 tamamlanmadan kinetic text production kapsamına alınmaz.
- Faz 6, Playwright’ın her kaynağı açacağı varsayımı üzerine kurulmaz.
- Faz 9 ve Faz 10 tek-prompt yaklaşımı kullanamaz.
- Faz 1 Domain Pack contract tamamlanmadan research/planner içine business-specific promptlar gömülemez.
- İlk production pack `business-tech`tir; diğer domain’ler milestone’ları geciktirecek biçimde paralel uygulanmaz.
- Faz 10, Faz 5 template capability listesi ve Faz 8 semantic catalog olmadan production karar veremez.
- Faz 12, planner asset brief'lerini approved asset/range/crop, template,
  visualization ve audio kararlarıyla executable editorial plan'a bağlamadan
  final EDL üretemez.
- Faz 11 source audio kullanımı Faz 8 asset metadata’sına bağlıdır.
- Faz 3 sample-accurate audio contract’ı olmadan Faz 11 production mix kapsamına geçemez.
- Faz 4’ten itibaren her artifact Faz 1 manifest sözleşmesine uymalıdır.
- Faz 14 kalite mimarisi oturmadan başlatılmaz; ancak artifact metadata Faz 1’de, kayıt hook’ları Faz 4’te kurulmalıdır.
- Faz 15 her faz boyunca gelişir; final gate en son sabitlenir.
- Faz 13A UI shell Faz 1’den itibaren paralel ilerler; Faz 13B Manual LLM ekranları Faz 9 ile, Faz 13C review studio Faz 12 sonrasında tamamlanır.
- Geliştirme ve ilk videolarda LLM backend varsayılanı `REPLAY` veya `MANUAL_UI`’dır; API zorunlu değildir.
- Spring Boot, Faz 17 product-gate kararı verilmeden mimariye eklenmez.

---

# 10. Ana Milestone’lar

## Milestone A — Structured Editing Foundation

Kapsam:

```text
Faz 0–4
```

Sonuç:

- V3 workspace schema
- Word timeline
- Multi-track EDL
- Remotion renderer
- Katmanlı sequence render
- Sample-accurate audio boundary foundation
- Artifact manifest foundation
- Thin FastAPI Studio API ve React UI shell

## Milestone B — Editorial Composition System

Kapsam:

```text
Faz 5–7
```

Sonuç:

- Motion template library
- Source acquisition ladder
- Evidence treatment
- Animated chart/metric engine

## Milestone C — Intelligent Research and Visual Planning

Kapsam:

```text
Faz 8–10
```

Sonuç:

- Semantic asset catalog
- Persistent claim graph
- Chapter/beat/sequence planner
- Tek prompt yerine hierarchical compilation
- Manual LLM Gateway ve API’siz research/planning
- Domain Pack Registry ve production-ready `business-tech` intelligence bundle

## Milestone D — Finished Documentary Experience

Kapsam:

```text
Faz 11–13
```

Sonuç:

- Source-audio-safe audio direction
- Continuity/pacing
- Studio UI, Manual LLM task inbox ve sequence review

## Milestone E — Scalable Production Engine

Kapsam:

```text
Faz 14–17
```

Sonuç:

- Incremental rendering
- Artifact lifecycle, quota ve garbage collection
- Truthful validation
- Reference benchmarking
- React/FastAPI production packaging
- Spring Boot decision gate

---

# 11. Global Kabul Kriterleri

Uygulama nihai hedefe ulaşmış sayılmadan önce aşağıdaki koşullar karşılanmalıdır.

## Domain mimarisi

- Core schema ve servisler business-tech’e özel zorunlu sınıflara bağlı değildir.
- Her proje domain ID, pack version ve resolved policy snapshot taşır.
- Research, planner, visual selection ve validation aktif Domain Pack üzerinden policy çözer.
- İlk production pack `business-tech`tir.
- Contract-only ikinci domain manifest’i core değişmeden yüklenebilir.
- Yeni domain eklenmesi mevcut pack ve projelerde regression oluşturmaz.
- Domain-specific safety/claim taxonomy olmadan hassas bir domain production-ready işaretlenemez.

## Araştırma

- Kritik iddialar güvenilir kaynaklarla bağlıdır.
- Uydurma URL, alıntı veya rakam yoktur.
- Claim store kalıcıdır.
- Çelişkiler görünürdür.
- Tek LLM çağrısı bütün projeyi araştırmaz.
- Kullanıcı kaynakları elle araştırmak zorunda değildir.
- Web erişimli yapay zekâ research discovery, extraction ve chronology görevlerini tamamlar.
- API anahtarı olmadan Manual LLM Gateway üzerinden research tamamlanabilir.
- Uydurma URL ve kaynağa bağlanmayan claim kabul edilmez.

## Hikâye ve planner

- Global outline, chapter, beat ve sequence katmanları ayrıdır.
- Her narration span için editorial role vardır.
- Her sequence birden fazla edit event taşıyabilir.
- Sequence lokal olarak yeniden planlanabilir.
- Deterministic compiler final EDL’yi üretir.
- Planner backend’i `REPLAY`, `MANUAL_UI`, `LOCAL_MODEL` veya `API` olarak değiştirilebilir.
- Onaylanmış LLM sonuçları fixture olarak yeniden kullanılabilir.

## Görsel kalite

- Kaynak ekranlarında crop, focus ve highlight vardır.
- Bot challenge ekranları final videoya girmez.
- Grafikler aşamalı animation taşır.
- Quote ve chapter kartları tutarlı tasarım diline sahiptir.
- Aynı visual family ilgisiz bağlamlarda tekrar edilmez.
- Generic stock ana içerik değildir.

## Text ve zamanlama

- Her narration kelimesinin word timing verisi vardır.
- Kinetic emphasis frame-accurate çalışır.
- Readable subtitles ve emphasis overlays çakışmaz.
- Her kelime gereksiz yere animasyonlu değildir.

## Ses

- Chapter bazlı müzik yönetimi vardır.
- Narration ve source speech çakışmaz.
- Embedded source music, Kurgu Engine BGM’i ile üst üste bindirilmez.
- Reveal anlarında kontrollü audio event kullanılır.
- Final loudness tutarlıdır.
- Audio timeline 48 kHz sample grid üzerinde sample-accurate derlenir.
- Uç uca ses birleşimlerinde duyulur micro-pop/click bulunmaz.
- Fade/crossfade profilleri audio türüne göre seçilir.
- Planlanmış narration sessizlikleri korunur.
- Ara audio pipeline PCM kullanır; kayıplı encode yalnızca final export’ta yapılır.

## Kullanılabilirlik ve ürün arayüzü

- React + TypeScript Studio UI proje yaşam döngüsünü görünür biçimde yönetir.
- Thin FastAPI Studio API bütün dosya sistemi/engine erişiminin sınırıdır.
- Manual LLM task paketi UI’dan kopyalanabilir/indirilebilir ve sonuç yapıştırılabilir/yüklenebilir.
- Problemli sequence tek başına yeniden render edilebilir.
- Kullanıcı alternatif asset, crop, template ve audio policy seçebilir.
- Proje durumu kalıcıdır.
- Long-form proje tek JSON dosyasına bağlı değildir.

## Güvenilirlik

- Eski cache yeni run olarak paketlenemez.
- Validation gerçek artifact’i kontrol eder.
- Eksik rapor valid olamaz.
- Source acquisition fallback kararları görünürdür.
- LLM çağrı lineage’ı kayıtlıdır.
- API kullanımı kapalıyken pipeline sessizce ticari çağrı yapamaz.
- React backend’i atlayarak workspace dosyalarını değiştiremez.
- OpenAPI ve shared schema sürümü project metadata’da kayıtlıdır.
- Her artifact registry’de retention ve dependency bilgisiyle kayıtlıdır.
- Approved/final/provenance artifact’leri otomatik GC tarafından silinemez.
- Workspace ve global cache kotaları izlenir.
- Disk pressure production render başlamadan tespit edilir.
- Cleanup iki aşamalı ve geri alınabilirdir.

---

# 12. Kesinlikle Yapılmaması Gerekenler

- V2.2’ye rastgele visual type eklemeye devam etmek
- Her sahneye zoom koyarak slayt problemini çözmeye çalışmak
- Transition sayısını kalite sanmak
- Stock provider sayısını erken artırmak
- Threshold’u çıktı geçsin diye değiştirmek
- Aynı renderer’a patch üstüne patch eklemek
- Promptu uzatarak mimari problemi çözmeye çalışmak
- 20 dakikalık projeyi tek promptta üretmek
- Bütün proje state’ini her LLM çağrısında göndermek
- Playwright’ı bot koruması aşma motoruna çevirmek
- Challenge veya paywall ekranını source evidence saymak
- Kaynak videonun ham sesini doğrudan BGM üstüne bindirmek
- Ara audio dosyalarını MP3/AAC olarak tekrar tekrar encode ve concat etmek
- Tüm ses türlerine kör biçimde aynı fade süresini uygulamak
- Impact SFX attack’ını uzun fade-in ile yok etmek
- GC’yi yalnızca dosya yaşına göre çalıştırmak
- Approved, final veya provenance artifact’lerini TTL ile silmek
- Render klasörünü dependency kontrolü olmadan topluca temizlemek
- Disk tamamen dolana kadar production render başlatmak
- Her kelimeyi karaoke altyazısı gibi animasyonla göstermek
- Kötü videoyu daha hızlı render etmeye odaklanmak
- Full otomasyonu ilk günden zorunlu yapmak
- Human review ihtiyacını başarısızlık saymak
- Kullanıcıya “araştırmayı kendin yap ve kaynakları hazırla” demek
- ChatGPT/Claude/Gemini web arayüzünü gizli API gibi Playwright ile otomatik sürmek
- LLM API anahtarını geliştirme için zorunlu yapmak
- React’i doğrudan workspace klasörüne veya Python fonksiyonlarına bağlamak
- Spring Boot’u gerçek ürün ihtiyacı oluşmadan sırf gelecekte lazım olabilir diye eklemek
- İlk günden mikroservis, Kafka veya Kubernetes kurmak
- Tek bir dev “her konuda uzman” prompt oluşturmak
- Business-tech claim/entity sınıflarını core schema’ya gömmek
- Her servise dağıtılmış `if domain == ...` blokları yazmak
- İlk business-tech kalite kapısı geçmeden true-crime/history/science pack’lerini tam geliştirmek
- True Crime/Legal’i yalnızca business promptuna birkaç talimat ekleyerek desteklenmiş saymak
- Domain Pack migration’ını mevcut projelere sessizce uygulamak

---

# 13. Değişiklik Yönetimi

Her faz için ayrı branch:

```text
phase/00-baseline-memory
phase/01-v3-workspace-domain-contract
phase/02-word-timing
phase/03-multitrack-edl
phase/04-motion-renderer
phase/05-template-library
phase/06-source-acquisition
phase/07-data-visualization
phase/08-semantic-assets
phase/09-manual-llm-research-claim-store
phase/10-hierarchical-planner
phase/11-audio-director
phase/12-continuity
phase/13-studio-ui-manual-llm-review
phase/14-artifact-lifecycle-gc
phase/15-validation
phase/16-benchmark
phase/17-packaging-product-gate
```

Her faz kapanırken:

1. `CURRENT_STATE.md` güncellenir.
2. `KNOWN_LIMITATIONS.md` güncellenir.
3. `PHASE_ACCEPTANCE.md` sonuçları eklenir.
4. Örnek artifact saklanır.
5. Sonraki fazın giriş koşulları kontrol edilir.
6. ADR gerekiyorsa eklenir.
7. Tag oluşturulur.

Örnek tag’ler:

```text
v3.0-workspace-domain-contract
v3.1-word-timeline
v3.2-multitrack-edl
v3.2.1-audio-sample-grid
v3.3-motion-renderer-alpha
v3.4-editorial-templates
v3.5-source-acquisition
v3.6-hierarchical-planner-beta
v3.7-artifact-lifecycle-gc
```

---

# 14. Görev Seçim Kuralı

Yeni görev başlamadan önce:

1. Hangi faza ait?
2. Fazın kabul kriterine doğrudan katkı sağlıyor mu?
3. Mevcut blocker’ı çözüyor mu?
4. Başka fazın sorumluluğunu erken mi getiriyor?
5. Hangi artifact üretilecek?
6. Nasıl test edilecek?
7. Hangi mevcut artifact veya schema değişecek?
8. Geriye dönük uyumluluk etkisi nedir?
9. Bu görev core’a mı yoksa aktif Domain Pack’e mi aittir?
10. Yeni bir domain-specific davranış ekliyorsa extension contract kullanıyor mu?

Net cevap yoksa görev backlog’a alınır.

---

# 15. Geliştirme Disiplini

## Bir faz açıkken

- Başka fazın büyük feature’ı eklenmez.
- Acceptance criteria değiştirilmez.
- Bilinen eksik başarı gibi raporlanmaz.
- Preview ve benchmark saklanır.

## LLM görevleri ve maliyet disiplini

- Yeni ticari API çağrısı varsayılan olarak kapalıdır.
- Renderer, audio, cache ve UI geliştirmesi `REPLAY` fixture’larıyla test edilir.
- Yeni research/planner çıktısı gerektiğinde önce `MANUAL_UI` task paketi kullanılır.
- Her task ve result content hash, backend mode, model bilgisi (kullanıcı sağladıysa) ve lineage ile kaydedilir.
- API backend’i eklendiğinde proje bazlı harcama limiti ve dry-run zorunludur.
- İlk geliştirme yalnızca `business-tech` pack’ini production düzeyine taşır.
- Yeni domain fikirleri backlog’a alınır; core extension contract eksiği ortaya çıkarıyorsa yalnızca contract iyileştirilir, yeni pack tamamlanmaz.
- Prompt template’leri gateway/core klasörüne değil ilgili `domain-packs/<id>/prompts/` altına yazılır.

Her coding-agent görevi:

```text
faz numarası
amaç
kapsam içi dosyalar
kapsam dışı işler
zorunlu artifact’ler
testler
acceptance criteria
```

ile başlar.

## Faz kapatma

Bir faz yalnızca:

- Kod yazıldığı için değil,
- artifact üretildiği,
- acceptance criteria geçtiği,
- dokümantasyon güncellendiği

zaman kapanır.

Her bounded implementation ayrıca `FOUNDATION_ACCEPTED` olarak kaydedilir.
Bir fazın `MASTER_PHASE_CLOSED` olması için kendi roadmap kriterleri ile
`docs/ROADMAP_SCOPE_RECONCILIATION.md` içindeki kendisine ait Deferred
Delivery Ledger satırlarının kanıtla kapanması zorunludur.
`PRODUCT_GATE_CLOSED` yalnızca Faz 17'de ledger tamamen boşken verilebilir.

---

# 16. Nihai Başarı Tanımı

Kurgu Engine başarılı sayılacaktır, eğer:

- Kullanıcı yalnızca konu verebildiğinde,
- Kullanıcı kaynak araştırmasını elle yapmak zorunda kalmadığında,
- Web erişimli yapay zekâ görev paketleriyle araştırma ve planlama yapabildiğinde,
- Sistem API anahtarı olmadan `MANUAL_UI` ve `REPLAY` modlarında çalışabildiğinde,
- React + TypeScript Studio UI bütün süreci FastAPI sınırı üzerinden yönetebildiğinde,
- Sistem güvenilir research yapabildiğinde,
- Claim ve evidence ilişkisini kalıcı olarak tutabildiğinde,
- Long-form projeyi tek prompt yerine hiyerarşik biçimde derleyebildiğinde,
- Narration’ı chapter, beat ve sequence’lere bölebildiğinde,
- Word-level timing ile motion ve kinetic text’i senkronlayabildiğinde,
- Multi-track EDL oluşturabildiğinde,
- Belge, UI, B-roll, grafik, quote ve text’i katmanlı kullanabildiğinde,
- Bot-protected kaynaklarda güvenli fallback uygulayabildiğinde,
- Source konuşmasını BGM ile çakıştırmadan kullanabildiğinde,
- Aynı görsel ailesini yanlış bağlamlarda tekrar etmediğinde,
- Görsel ve ses ritmini chapter boyunca yönetebildiğinde,
- Kullanıcı yalnızca sorunlu sequence’leri düzelterek final videoya ulaşabildiğinde,
- Ortaya çıkan video basit bir slayt veya stock montage gibi görünmediğinde,
- Spring Boot eklenmeden de ilk production beta ve gerçek YouTube videosu üretilebildiğinde,
- Business/Technology pack’iyle yayınlanabilir kalite kanıtlandığında,
- Aynı core’a ikinci bir domain pack eklemek renderer, workspace veya Manual LLM Gateway’i yeniden yazmayı gerektirmediğinde.

---

# Son Not

Bu proje bir “video dosyalarını birleştirme aracı” değildir.

Doğru ürün tanımı:

> **Kullanıcıdan konu, yaratıcı yön ve domain seçimi alan; multi-domain-ready core üzerinde seçili Domain Pack’in araştırma, claim, narrative, visual ve safety intelligence’ını kullanan; web erişimli yapay zekâ görevleriyle planlama yapan ve kaynak/kanıt/grafik/hareket/ses kararlarını sequence bazlı belgesele derleyen, API’siz veya API destekli çalışabilen görsel üretim stüdyosu.**

Her teknik karar bu tanıma hizmet etmelidir.
