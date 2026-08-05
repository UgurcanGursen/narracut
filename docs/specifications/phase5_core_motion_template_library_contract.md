# Faz 5 — Core Motion Template Library Contract

> Durum: Aday ve dondurulmuş spesifikasyon — uygulama yetkisi değildir
> Amaç: Faz 4 render yüzeyinde tekrar kullanılabilir, domain-bağımsız on beş
> motion composition capability’sini typed registry üzerinden seçip render etmek
> Önkoşul: Faz 2, Faz 3 ve Faz 4 kabul edilmiş EDL, word-to-frame ve renderer
> sözleşmeleri
> Hariç: Yeni source/provider edinimi, chart veri üretimi, asset catalog, planner,
> sequence'ler arası continuity/pacing optimizasyonu, Studio UI, cache/GC,
> queue/retry ve Faz 6+

## 1. Karar ve sınır

Faz 5, Phase 4’ün schedule veya artifact lifecycle otoritesini değiştirmez.
`VideoEdlArtifact`, `AudioEdlArtifact`, accepted `RenderProps` ve FULL render
receipt’leri yeniden derlenemez; template katmanı yalnız doğrulanmış bir
composition planını Remotion katmanlarına projekte eder. Yeni event, asset,
frame, audio boundary, crop veya default narration üretmek yasaktır.

Bu ilk bounded pakette aşağıdaki **15 core capability** uygulanır. İsimler
roadmap’teki template setinin kapalı alt kümesidir ve core registry’de stable
capability ID’lerdir:

```text
cold_open_source_montage       chapter_title
article_focus_scan             headline_to_paragraph_zoom
highlight_wipe                 expert_quote_card
metric_reveal                  metric_comparison
process_diagram                split_screen_comparison
timeline_progression           news_clip_context
final_thesis_card              kinetic_keyword
caption_phrase
```

`agent_loop_diagram`, `product_ui_focus` ve `terminal_demo` core’a eklenmez;
ileride business-tech capability bundle’ında ayrı ele alınır. `animated_*_chart`
ve diğer data-visualization üretimi Faz 7’nin otoritesidir. Bu ayrım, “en az 15
template” kabul kriterini karşılar fakat core’a business-tech veya chart-engine
semantiği sızdırmaz.

Her capability aynı, sabit easing family’sini ve safe-area kurallarını kullanır;
random effect, wall-clock, `Math.random`, network, provider çağrısı ve host
font discovery yasaktır. Faz 5 plan doğrulayıcısı, aynı `template_id`nin bir
sequence-local ordered invocation listesinde üç kez ardışık kullanılmasını
fail-closed reddeder. Faz 12; bunun üstüne sequence'ler arası cooldown,
çeşitlilik ve pacing optimizasyonunu ekler.

## 2. Sahiplik ve izinli değişiklik yüzeyi

Uygulama tek bounded pakette en fazla aşağıdaki ek/additive yüzeyi sahiplenir:

```text
engine/rendering/template_contract.py
engine/rendering/template_registry.py
engine/rendering/template_runner.py
engine/rendering/__init__.py                 (additive exports only)
renderer-remotion/src/templates/...
renderer-remotion/src/TemplateComposition.tsx
renderer-remotion/src/template-contract.ts
renderer-remotion/src/template-schema.ts
renderer-remotion/src/index.tsx              (additive composition registration only)
renderer-remotion/scripts/render-template-fixture.mjs
renderer-remotion/public/phase5-fonts/NotoSans-Variable.ttf
renderer-remotion/public/phase5-fonts/OFL.txt
tests/test_motion_templates.py
tests/fixtures/phase5/...
domain-packs/business-tech/policies/skeleton.json
```

Faz 2/3 canonical contractleri, Faz 4 bridge/full-render lifecycle modülleri,
`studio-ui/`, provider adapter’ları ve mevcut package-lock değişmez. Bir Node
dependency, browser API veya external media dosyası eklenmez. Render-time
network/host font discovery yerine yalnız yukarıdaki iki checked-in dosyadan
oluşan, SIL Open Font License ile paketlenmiş sabit Noto Sans variable font
kullanılabilir; lisans dosyası fontla birlikte kalır. Başka font paketi ya da
font asset eklenmez.
Gerekirse Phase 4 fixture asset manifestindeki halihazırda trusted SVG’ler
read-only tüketilir; yeni asset edinilmez. Her test `REPLAY` fixture kullanır.
Faz 4 `RenderProps`una alan eklemek, onun hash/request/receipt semantiğini
değiştirmek veya `sequence-preview-v1` girişini gevşetmek kesinlikle yasaktır.

## 3. Typed core contract

Python ve TypeScript aynı kapalı vocabulary’yi taşır. Serbest string template,
ad-hoc props veya renderer içinde `if domain == ...` yasaktır.

```text
TemplateId = 15 capability ID’sinden biri
EditorialRole = nonempty normalized core role string
TemplateKind = SOURCE | TEXT | METRIC | DIAGRAM | COMPARISON | KINETIC
```

Her `TemplateDefinition` tam olarak şu immutable alanları bildirir:

```text
template_id
template_version                 # bu paket için "1.0.0"
kind
supported_editorial_roles        # boş olmayan, sıralı ve tekrarsız core role listesi
requires_source_asset            # bool
supports_target_region           # bool
supports_caption                 # bool
supports_source_label            # bool
supports_word_binding            # bool
safe_area_policy                 # "SAFE-AREA-V1"
payload_kind
```

Registry’deki 15 tanım sabit sıralı `template_id` düzeniyle döner. Bir template
yalnız tanımının desteklediği inputları kabul eder; örneğin source zorunlu bir
template source binding olmadan, `caption_phrase` ise geçerli word binding
olmadan compile edilmez. `metric_*` template’leri yalnız caller’ın already
materialized label/value payload’ını gösterir; hesaplama, sayı yuvarlama veya
chart dataset üretmez. `process_diagram` generic node/edge labels kullanır;
business entity türü bilmez.

`SAFE-AREA-V1` canonical millionths geometry’si sabittir: `content =
[64_000, 56_000, 936_000, 746_000]`, `subtitle =
[64_000, 772_000, 936_000, 936_000]`. `target_region`, source/template content
bounds ve herhangi bir text/layout bounds kendi atanmış rectangle’ı dışına
çıkamaz. Bu değerler bütün 15 definition tarafından aynı `safe_area_policy`
ile taşınır; component’in CSS ile yeni bir safe area uydurması yasaktır.

On beş immutable definition aşağıdaki tablodur. Role listeleri sıralı kapalı
vocabulary’dir; `payload_kind` da closed discriminated union tag’idir.

| template_id | kind | roles | source | target | caption | source label | word | payload_kind |
|---|---|---|---:|---:|---:|---:|---:|---|
| cold_open_source_montage | SOURCE | introduce,context | yes | no | no | yes | no | SOURCE_TEXT |
| chapter_title | TEXT | chapter,introduce | no | no | yes | no | no | TITLE_BODY |
| article_focus_scan | SOURCE | prove_claim,context | yes | yes | no | yes | no | SOURCE_TEXT |
| headline_to_paragraph_zoom | SOURCE | prove_claim,context | yes | yes | no | yes | no | SOURCE_TEXT |
| highlight_wipe | SOURCE | prove_claim,emphasize | yes | yes | no | yes | no | SOURCE_TEXT |
| expert_quote_card | TEXT | quote,context | no | no | yes | yes | no | QUOTE |
| metric_reveal | METRIC | quantify,prove_claim | no | no | yes | yes | no | METRIC_SINGLE |
| metric_comparison | METRIC | compare,quantify | no | no | yes | yes | no | METRIC_PAIR |
| process_diagram | DIAGRAM | explain_mechanism,context | no | no | yes | no | no | DIAGRAM |
| split_screen_comparison | COMPARISON | compare,context | yes | no | yes | yes | no | COMPARISON |
| timeline_progression | DIAGRAM | chronology,context | no | no | yes | no | no | TIMELINE |
| news_clip_context | SOURCE | context,prove_claim | yes | no | yes | yes | no | SOURCE_TEXT |
| final_thesis_card | TEXT | conclude,emphasize | no | no | yes | no | no | TITLE_BODY |
| kinetic_keyword | KINETIC | emphasize | no | no | yes | no | yes | KINETIC |
| caption_phrase | KINETIC | caption | no | no | yes | no | yes | KINETIC |

`TemplateInvocationV1` bu tipli, sequence-local plan satırıdır:

```text
template_id, template_version, editorial_role,
start_frame, end_exclusive_frame,
layout, source_event_id | null, target_region | null,
entry_animation, exit_animation, camera_motion,
caption | null, source_label | null, style_preset_id,
payload,
word_binding | null, safe_area_policy
```

`payload` exact `payload_kind` tarafından belirlenen kapalı union’dır:

```text
SOURCE_TEXT   = { headline, body }
TITLE_BODY    = { title, body }
QUOTE         = { quote, attribution }
METRIC_SINGLE = { label, value, qualifier }
METRIC_PAIR   = { left_label, left_value, right_label, right_value, qualifier }
DIAGRAM       = { nodes: [{node_id,label}], edges: [{from_node_id,to_node_id}] }
TIMELINE      = { points: [{point_id,label,ordinal}] }
COMPARISON    = { left_label, right_label, conclusion }
KINETIC       = { display_text }
```

Tüm stringler nonempty NFC’dir. `DIAGRAM` node ID’leri lexical sıralı/unique,
edge’leri source/target node inventory’sinde; `TIMELINE` ordinal’leri 1’den
başlayan contiguous integer’dır. Metric değerleri sadece already-materialized
display stringidir; sayısal hesaplama, rounding veya dataset üretimi yapılmaz.
`KINETIC.display_text` word IDs ile arama/eşleme için kullanılmaz; text araması
runtime’da yasaktır.

`start_frame`/`end_exclusive_frame`, accepted Phase 3 video event aralığı içinde
pozitif duration ile kalır. `source_event_id`, yalnız accepted `RenderProps`
içindeki existing source event’e bağlanır; path, URL veya yeni asset taşımaz.
`target_region` millionths coordinate dörtgenidir ve `[0, 1_000_000]` içinde,
strict left < right/top < bottom olur. Text alanları nonempty NFC string olup
renderer bunları arama, LLM üretimi veya localization işlemine sokmaz.

`TemplateRenderPlanV1`, exact `RenderProps.render_request_id`,
`render_props_hash`, `word_to_frame_id/hash`, ordered invocation listesi,
resolved style preset identity’si ve
plan identity’sini taşır. Identity projection yalnız `template_plan_id` ve
`template_plan_hash` hariç canonical JSON’dur; hash `sha256:` + SHA-256,
ID `tmplplan_` + digest ilk 32 hex’tir. Aynı verified props + invocation +
resolved policy + style preset aynı plan byte’ını üretir. Plan loaded edilmeden veya render’a
gönderilmeden önce identity ve tüm cross-reference’lar yeniden doğrulanır.

Faz 4 girişini değiştirmeden Node’a taşıma için Faz 5’in kendi kapalı zarfı
`TemplateRenderInputV1`dir:

```text
schema_version = "TEMPLATE-RENDER-INPUT-V1"
render_props                 # exact verified RENDER-PROPS-V1 object
template_render_plan         # exact verified TEMPLATE-RENDER-PLAN-V1 object
word_to_frame_artifact       # exact canonical WORD-TO-FRAME-V1 object
template_input_id
template_input_hash
```

Python `template_runner` ve Node `template-schema` bu zarfın tek ingress
otoritesidir. Python compiler'ın ingress’i `TemplateCompilationInputV1`dir:
exact verified RenderProps, exact canonical WordToFrameArtifact, optional
accepted DomainPolicySnapshot ve typed invocation draft’ları taşır. Compiler
önce `load_word_to_frame` ile artifact’in canonical bytes/identity/lineage’ını,
sonra RenderProps’taki `word_to_frame_id/hash`, narration revision ve FPS ile
eşitliğini doğrular; yalnız ardından plan üretir. Node zarf parser’ı embedded
WordToFrame object’in canonical JSON/identity’sini yeniden doğrular ve her
kinetic binding’in word-ID uçları ile start/end frame’inin artifact’teki exact
word span’larıyla eşit olduğunu kanıtlar. İkisi de önce embedded RenderProps’un
mevcut Faz 4 canonical parser’ını, sonra plan ve zarf identity’sini doğrular;
zarfın canonical hash’i
yalnız kendi ID/hash alanları hariç canonical JSON’dur. Yeni composition ID
`template-composition-v1` yalnız bu zarfı tüketir. Zarf, Faz 4 render request,
FULL producer, output target, artifact registry veya receipt’i değiştirmez;
bu pakette yalnız bağımsız REPLAY preview/render gate’i için kullanılır.

## 4. Word/frame bağlama

`kinetic_keyword` ve `caption_phrase` için `word_binding` zorunludur; diğer
template’lerde yalnız explicit destek verilmişse vardır. Binding serbest
milisaniye, text-search veya substring değildir:

```text
narration_revision_id
word_to_frame_id
word_to_frame_hash
start_word_id
end_word_id
start_frame
end_exclusive_frame
```

Compiler, input WordToFrame artifact’ını canonical loader ile doğrular ve her
iki word ID’nin aynı narration revision’a ait olduğunu kanıtlar. Binding frame
uçları accepted WordToFrame mapping’den exact gelir; caller frame veya seconds
veremez. `start_frame < end_exclusive_frame` zorunludur. Kinetic component
yalnız bu inclusive word-ID range’i ve bu frame aralığını kullanır; karaoke
varsayılanı, tüm narration’a yayılma veya runtime metin eşleme yoktur.

Kabul testinde farklı FPS içeren iki REPLAY fixture’ı için seçilmiş word/frame
uçları component props’unda exact korunur; bir frame drift, unknown word,
revision/hash uyuşmazlığı veya manual-second ingress fail-closed olur.

## 5. Editorial-role seçimi, domain policy ve style preset

`TemplateStylePresetV1` her invocation’ın immutable görsel bağlamıdır:

```text
preset_id
color_theme_id
typography_id
font_asset_hash
tone_id
preset_hash
policy_snapshot_id | null
policy_snapshot_hash | null
```

`core-neutral-v1`, pack yokken kullanılan açık core preset’tir; boş, implicit
veya host-font default’u değildir. Her Faz 5 preset’i paketlenmiş
`phase5-noto-sans-v1` typography ID’sini kullanır; `font_asset_hash`, checked-in
font byte’ının `sha256:bfb7bb691513f12e734dc346c03a03f784912432d7e3fa8e56efcf906fe86b3d`
değeridir ve plan identity’sine dahildir; renderer generic fallback font
tanımlamaz. Business-tech preset’i yalnız accepted
DomainPolicySnapshot içindeki manifestle kayıtlı policy bundle’ların
`policy.visual.template_policy` alanından extract edilir. Extractor başka ham
snapshot alanı, dosya yolu veya caller JSON’u okumaz. Bu alan tam olarak
`preferred_template_ids`, `banned_template_ids`, `required_template_ids` ve
`style_preset` taşır. `style_preset`; fixed `preset_id`, `color_theme_id`,
`typography_id`, `font_asset_hash` ve `tone_id` bildirir. Unknown/duplicate ID, preference/ban
çelişkisi, eksik alan veya snapshot identity drift’i typed policy-invalid
hatasıdır. Preset hash’i ve snapshot binding’i `TemplateRenderPlanV1` identity
projection’ına dahildir; renderer preset’i değiştiremez.

`TemplateRegistry.select(...)` planı değil, compiler öncesi closed
`TemplateCandidateV1` listesi üzerinde çalışan deterministik policy resolver’dır.
Candidate tam olarak `{template_id, editorial_role}` taşır; payload veya serbest
renderer props taşımaz. Her invocation, select sonucunda seçilen tek template ID
ile compile edilir; loaded `TemplateRenderPlanV1` tekrar selection yapmaz.
Girdi requested `editorial_role`, candidate listesi ve optional resolved Domain
Policy Snapshot’tır. Çıktı ya tek `TemplateDefinition` ya da typed
`TemplateSelectionError` olur.

Seçim sırası kesindir:

1. Candidate’lerden requested editorial role’u desteklemeyenleri çıkar.
2. Snapshot yoksa kalan core tanımları `template_id` lexical sırası ile değerlendir.
3. Snapshot varsa yalnız yukarıda tanımlanan canonical bundle extractor’ın
   `visual.template_policy` içindeki `preferred_template_ids`,
   `banned_template_ids` ve `required_template_ids` alanları okunur.
4. Ban uygulanır; gerekli ID banlandıysa fail-closed olur. Requested role’u
   destekleyen required ID varsa candidate listesinde bulunması zorunludur ve
   seçim yalnız bu required candidate’lar arasında yapılır. Required ID role’u
   desteklemiyorsa o role için seçim kısıtlamaz; registry varlığını yine doğrular.
5. Kalan preferred candidate varsa declared preference sırası, yoksa lexical
   core sırası kullanılır.

Policy yalnız seçim ve resolved style preset bağlama yapar; `TemplateDefinition`,
easing, timing, source binding veya safe area’yı değiştiremez. `business-tech` profile kaldırıldığında ya da
snapshot verilmediğinde Step 2 çalışır: 15 core plan parse edilir ve fixture
render’ı başarıyla tamamlanır. Core registry domain pack discovery çağırmaz;
snapshot caller tarafından already resolved typed değer olarak verilir.

Bu pakette business-tech’in zaten manifest tarafından referans verilen
`policies/skeleton.json` bundle’ına yalnız typed `visual.template_policy`
eklenir. Manifest extension veya core modeline business-specific role eklenmez.

## 6. Render projection ve güvenlik

`TemplateComposition` yalnız verified `TemplateRenderInputV1` alır. Kompozisyon,
zarf içindeki template invocation’unun event
aralığını, source event ID’sini veya word binding’ini değiştiremez. Component
props’ları closed TypeScript discriminated union olur; unknown template/field
Node tarafında render öncesi reddedilir.

Safe areas `SAFE-AREA-V1` ile frame dimensions’dan deterministik hesaplanır.
Caption ve kinetic text subtitle-safe rectangle’ı ihlal edemez. `target_region`
safe area dışında ise component clip/taşıma yapmaz; Python compiler hata verir.
Source template’leri only existing `asset_bindings` içindeki matching event’i
kullanır. Template sonucu Faz 4 output register/publish semantiğini değiştirmez;
FULL preview/full-render çağrısındaki output registry ve receipt hala Faz 4’ün
tek sahibidir.

## 7. Deterministic REPLAY fixture ve kabul kanıtı

`tests/fixtures/phase5/` iki minimal canonical REPLAY planı içerir:

- `core_no_pack`: all 15 invocation, accepted Phase 4 props lineage ve iki
  word-timed invocation; domain snapshot yoktur.
- `business_tech_policy`: aynı core inputs’in birkaç uygun editorial-role
  candidate’i, preference/banned policy örneği ve expected chosen ID’leri.

Fixture’lar canonical JSON, stable identity/hash ve checked-in local SVG/text
payload’ları kullanır; network, clock, random seed, provider ve host font
kullanmaz. Her template için en az iki farklı legal invocation varyantı
fixture/test data’da bulunur: farklı source event veya farklı text/metric/role
payload’ı. Bu, aynı capability’nin tek hard-coded sahne olmadığını kanıtlar.

Her template için en az iki legal varyant canonical compiler üzerinden
doğrulanır; birincil varyantın başlangıç frame’i için deterministic RGBA
SHA-256 golden değeri fixture’da tutulur. Kinetic template’lerin başlangıç,
orta ve bitiş frame’leri de ayrı golden setinde tutulur. Python tarafı ayrıca resolved
safe-area rectangle ve text/layout bounds’larını assertion ile doğrular;
caption/kinetic bounds subtitle-safe area dışına çıkarsa fail-closed olur.
Bu kontroller visual golden ile birlikte motion’ın görünür ve tekrar üretilebilir
olduğunu kanıtlar; yalnız non-empty frame yeterli kabul edilmez. On beş
template’in seçilmiş karelerinden üretilen deterministic contact sheet tek
manuel visual-review artifact’idir ve Faz 5 acceptance raporunda açıkça PASS
olarak kaydedilmeden "production-quality" claim’i yapılamaz.

Tek bounded implementation paketinin test kapıları şunlardır:

1. Registry exactly 15 core ID, version, closed typed schema ve deterministic
   ordering sunar; her template iki legal REPLAY varyantında compile edilir.
   Birincil varyantların 15 başlangıç frame’i ile kinetic template’lerin
   start/mid/end frame’leri visual golden, safe-area ve layout-bounds
   kapılarını geçer. Non-empty frame tek başına yeterli kabul edilmez.
2. Her template’in iki legal payload/asset varyantı parse + render edilir;
   source/word gereksinimlerinin eksikliği typed fail-closed hata verir.
3. `kinetic_keyword` ve `caption_phrase` WordToFrame-derived exact frame
   boundary ile render edilir; manual seconds/text-search/revision drift reddedilir.
4. Editorial role selection policy yokken deterministic core fallback, policy
   varken preference/bans ve required capability kurallarını uygular.
5. business-tech policy fixture kaldırıldığında `core_no_pack` fixture’ı 15
   template için parse + render edilir.
6. Üç ardışık aynı template ID içeren sequence-local plan typed fail-closed
   reddedilir; iki ardışık kullanım legal kalır.
7. Python contract tests, TypeScript typecheck/unit tests ve yalnız bir gerçek
   bounded Remotion REPLAY render gate’i geçer. Faz 4 FULL lifecycle gate’i
   gereksiz tekrar çalıştırılmaz.

## 8. Açıkça sonraki fazlara bırakılanlar

Faz 5, template capability’yi üretir ama template seçiminin long-form dağılım
optimizasyonunu yapmaz (Faz 12), source semantic uygunluğunu hesaplamaz (Faz 8),
chart data/animation engine’i kurmaz (Faz 7), domain-specific template bundle’ı
uygulamaz ve planner’a yeni LLM promptu eklemez (Faz 9/10). Bu maddeler için
fake default, silent fallback veya roadmap dışı implementation eklenmez.
