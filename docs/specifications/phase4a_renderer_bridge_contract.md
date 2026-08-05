# Faz 4A — Motion Renderer Bridge Foundation Contract

> Durum: Aday spesifikasyon — uygulama yetkisi değildir
> Kapsam: Kabul edilmiş Faz 3 EDL byte’larından deterministik, fixture-temelli
> sequence preview üreten dar Python → Remotion köprüsü
> Önkoşul: Faz 3 `VIDEO-EDL-V1` ve `AUDIO-EDL-V1` kabul/remote-closure kanıtı
> Hariç: Faz 4B terminal-job cleanup/overwrite tamamlanması; Faz 5 şablon
> kütüphanesi; asset sağlayıcıları, ağ, queue/retry, Studio UI, production asset
> katalogu, source-audio suitability, cache/GC ve final export paketleme

## 1. Amaç ve sınır

Faz 4A, Python’ın motion renderer olmadığını korur: Python yalnız kabul edilmiş
EDL’leri doğrular, immutable typed render-props byte’larını kurar ve yerel
Remotion sürecini adapter üzerinden çağırır. React/Remotion, bu props’ları
tüketerek tek bir sequence için headless REPLAY preview üretir. FFmpeg mux veya
final encode bu makroda yoktur.

Bu çalışma, V2/MoviePy yolunu değiştirmez, kaldırmaz veya ona yeni renderer
bağlamaz. Renderer EDL compiler değildir: V1–V7/A1–A5 event’lerini yeniden
sıralayamaz, süre/cue/boundary hesaplayamaz, overlap çözemez, yeni event veya
varsayılan BGM üretemez. Önceden materialize edilmiş kanonik bytes geçerli
değilse fail-closed olur.

Faz 4A’nın somut ilk render hedefi checked-in REPLAY fixture ile **bir adet
sequence-local preview**dir. Roadmap’teki full render maddesi iptal edilmez veya
başarısız bir `FULL` pseudo-request ile karşılanmış sayılmaz: bu sözleşmede
`mode` yalnız `PREVIEW`dir. Full-sequence/full-film orchestration ile FFmpeg
normalize/mux/final encode, Faz 4B’nin ayrı yetkilendirilmiş sözleşmesinde
gerçekleştirilir. Faz 4A bir `FULL` props, receipt veya output üretmez. Böylece
planlayıcı veya provider varsayımı renderer temeline gizlice eklenmez.

## 2. Uygulama sınırı ve sahiplik

Bu spesifikasyon kabul edilirse izinli üretim yüzeyi en fazla şudur:

```text
engine/rendering/__init__.py
engine/rendering/bridge.py
engine/rendering/fixture_assets.py
engine/rendering/receipt.py
engine/rendering/artifact_hook.py
tests/test_renderer_bridge.py
tests/test_renderer_fixture_assets.py
tests/test_renderer_receipt.py
tests/fixtures/phase4a/...
renderer-remotion/package.json
renderer-remotion/package-lock.json
renderer-remotion/tsconfig.json
renderer-remotion/src/...
renderer-remotion/scripts/...
```

`engine/contracts/edl.py`, `engine/contracts/audio_edl.py` ve kabul edilmiş Faz
2/3 test/fixture’ları değiştirilemez. Yalnız additive public export gerektiği
kanıtlanırsa, ilgili dosya ve exact-export testi ayrı bir authorization kararı
ile eklenir. `studio-ui/` renderer workspace değildir; onun package lock’ı ve
bağımlılık grafiği Faz 4A’da değişmez.

Node workspace kökte izole `renderer-remotion/` olur. Kilitli Node dependency
seti `remotion`, `@remotion/cli`, `react`, `react-dom` ve TypeScript’ten başka
runtime dependency eklemez. Browser’a, ağa, provider SDK’sına veya `.env`
değerine erişim yasaktır. Paket komutları en az `typecheck`, `test` ve
`render:fixture` sağlar; bunlar Node sürümünü receipt’e açıkça yazar.

## 3. Güven zinciri ve ingress

Bridge aşağıdaki exact dependency zincirini alır:

```text
serialize_video_edl(video_edl)
serialize_audio_edl(audio_edl)
  → strict load ile aynı accepted upstream bağlamına yeniden bağlama
  → canonical RenderProps V1 bytes
  → immutable props SHA-256 / render request ID
  → isolated Remotion headless process
  → receipt + registered artifacts
```

Bridge, sadece `VideoEdlArtifact` / `AudioEdlArtifact` exact tipini kabul eder
ve her ikisini kendi serializer’ı ile yeniden materialize eder. Bir upstream
registry hack’i, ad-hoc JSON dict’i, path, URL, provider descriptor veya raw
timeline girdisi kabul edilmez. Loader’lar canonical byte, hash/ID, project,
document, narration revision, sequence ID, WordToFrame ID/hash, video EDL
ID/hash ve duration bindinglerini yeniden kanıtlamalıdır.

`audio_edl.video_edl_id/hash`, video EDL ile; video/audio project-document-
revision-sequence lineage’i birbirleriyle exact eşleşmelidir. Audio duration
sample gridinin video duration frame gridine dönüştürülmesi yeni bir scheduling
otoritesi değildir: bridge yalnız `audio_edl.duration_samples` ile
`sample_at_frame(video_edl.duration_frames)` eşitliğini ve sample clock `48000`
değerini doğrular. Audio boundary decision/PCM evidence renderer tarafından
değiştirilemez; Faz 4A visual preview, A1–A5 için yalnız immutable event/boundary
metadata taşır ve PCM mix/render yapmaz.

### 3.1 Normatif audio-duration doğrulaması

Bu section 3'teki duration cümlesinin exact uygulama kuralıdır ve olası daha
genel ifadelerin önüne geçer:

```text
sample_at_frame(f) = floor(f * 48000 * fps_denominator / fps_numerator)
```

`f`, accepted Video EDL sequence başlangıcına göre yerel, bool olmayan uint32
frame indeksidir. `fps_numerator` ve `fps_denominator` accepted Video EDL local
clock'ından gelir. Float, rounding helper, nominal-FPS dönüşümü, global frame,
saniye veya WordToFrame dışı FPS yasaktır. Bridge yalnız
`audio_edl.duration_samples == sample_at_frame(video_edl.duration_frames)` ve
sample clock `48000` eşitliklerini doğrular; ihlal
`DEPENDENCY_BINDING_INVALID` ile props oluşmadan reddedilir.

## 4. Canonical Render Props V1

Sabitler:

```text
RENDER_PROPS_V1       = "RENDER-PROPS-V1"
RENDER_PROPS_HASH_V1  = "RENDER-PROPS-HASH-V1"
RENDER_RECEIPT_V1     = "RENDER-RECEIPT-V1"
RENDERER_VERSION      = locked Node package version + Python bridge version
```

`RenderProps` JSON UTF-8, BOM’suz, canonical JSON olur. Integer dışı number,
NaN/Infinity, duplicate key, JSON dışı field veya non-NFC string reddedilir.
Kimlik öz-referanslı değildir. `RenderPropsIdentityProjection V1`, aşağıdaki
alanların tamamından **yalnız** `render_props_id`, `render_props_hash` ve
`render_request_id` çıkarıldıktan sonra canonical JSON ile kurulan object’tir.
`render_props_hash = "sha256:" + SHA256(RenderPropsIdentityProjection V1)` ve
`render_props_id = "rprops_" + digest[0:32]` olur. Dolayısıyla loader, identity
alanlarını hash’e beslemeden yeniden hesaplayıp exact eşleşme ister.

`render_request_id` rastgele, sayaç veya wall-clock değeri değildir.
`RenderRequestIdentityProjection V1` tam olarak
`{"schema_version":"RENDER-REQUEST-ID-V1","render_props_hash":...,
"composition_id":...,"renderer_version":...,"fixture_manifest_hash":...}`
canonical object’idir. `render_request_id = "rrq_" +
SHA256(RenderRequestIdentityProjection V1)[0:32]`; listedeki dört değer
props’taki exact değerlerle eşleşir. Aynı accepted inputs aynı request ID’yi,
tek bir input değişimi farklı request ID’yi verir.

```text
schema_version, hash_scope_version, render_props_id, render_props_hash,
render_request_id, mode, renderer_version, project_id, document_id, narration_revision_id,
sequence_id, video_edl_id, video_edl_hash, audio_edl_id, audio_edl_hash,
word_to_frame_id, word_to_frame_hash, fps_numerator, fps_denominator,
duration_frames, duration_samples, width, height, pixel_format,
composition_id, design_system_version, fixture_manifest_id,
fixture_manifest_hash, video_tracks, audio_tracks, audio_boundary_decisions,
asset_bindings
```

`mode` bu Faz 4A contract’ında kapalı `PREVIEW` literalidir; `FULL` inputu
props oluşmadan `MODE_NOT_AUTHORIZED` ile reddedilir. `renderer_version`,
kilitli `renderer-remotion/package-lock.json` dependency graph’ı ve Python
bridge semver’inin önceden tanımlı birleşimidir. `pixel_format` bu makroda
kapalı `rgba` literalidir;
width/height pozitif uint32 ve fixture profile’ında `1280x720`dir. Caller keyfi
FPS, duration, text, source veya asset binding enjekte edemez: bütün event
alanları upstream EDL’den lossless projection olarak gelir.

`video_tracks` V1…V7 sabit sıralı yedi satırdır; her satır tam olarak
`{"track": TimelineTrack, "kind": EdlTrackKind, "priority": uint32,
"events": [VideoEventProjection...]}`dir. `VideoEventProjection`, upstream
`EdlVideoEvent` alanlarının exact/lossless projection’ı olan
`schema_version,hash_scope_version,event_id,event_hash,track,ordinal,intent_id,
editorial_role,start_frame,end_exclusive_frame,start_word_id,end_word_id,payload`
sırası ve adlarıyla object’tir. `payload`, upstream `EdlRenderPayload` alanları
`kind,source,source_artifact_id,source_artifact_hash,source_record_id,
source_record_hash,source_record_ordinal,preview_scene_id,preview_scene_hash,
preview_left_millionths,preview_top_millionths,preview_right_millionths,
preview_bottom_millionths,text,emphasis_type_ref,emphasis_intensity` ile exact
eşleşir. Non-null `source` ise upstream `SourceDescriptor`’ın
`source_ref,source_fps_numerator,source_fps_denominator,source_in_frame,
source_out_exclusive_frame,playback_mode,fit_mode,crop_left_millionths,
crop_top_millionths,crop_right_millionths,crop_bottom_millionths,
opacity_millionths,bound_start_word_id,bound_end_word_id` alanlarını taşır;
bridge bunlardan yeni crop/zoom/highlight geometry hesaplamaz.

`audio_tracks` A1…A5 sabit sıralı beş satırdır ve empty track silinmez. Her
satır tam olarak `{"track": AudioTrackRole, "priority": uint32,
"events": [AudioEventProjection...]}`dir. `AudioEventProjection`, upstream
`EdlAudioEvent`’in 20 alanının exact/lossless projection’ıdır:
`schema_version,hash_scope_version,event_id,event_hash,track,kind,ordinal,
intent_id,source_id,source_media_hash,normalized_pcm_evidence_hash,
start_sample,end_exclusive_sample,source_in_sample,source_out_exclusive_sample,
gain_millibels,cue_start_word_id,cue_end_word_id,cue_start_sample,
cue_end_exclusive_sample`. Kök props aynı zamanda `audio_boundary_decisions`
alanında upstream `AudioBoundaryDecision` listesini
`position,left_event_id,right_event_id,track,policy,transition,left_trim_samples,
right_trim_samples,fade_in_samples,fade_out_samples,overlap_samples,
protected_silence_samples` ad/sırasıyla lossless taşır; renderer bu kararları
yorumlamaz veya değiştirmez.

`asset_bindings` sadece fixture manifestinin allowlist’iyle çözülmüş satırlardır:

```text
event_id, fixture_asset_id, content_sha256, media_type, width, height
```

Her `CALLER_SOURCE` video event’i, `payload.source_artifact_id` ile
`fixture_asset_id` exact eşleşen tam bir satıra bağlanır ve
`payload.source_artifact_hash == content_sha256` olmalıdır. `source_ref`,
yalnız manifestteki aynı `fixture_asset_id`nin opaque referansıdır; path veya
provider mappingi değildir. `KINETIC_EMPHASIS` ve `CAPTION` event’leri dış asset
bağlamaz. Unknown/missing binding, content hash
uyuşmazlığı, duplicate event binding veya path traversal fail-closed’dur. Props
JSON’da mutlak path, kullanıcı home path’i, URL, provider adı veya credential
bulunmaz; Node process dosya konumunu yalnız trusted launch configuration’daki
fixture root’tan alır.

Her `asset_bindings` elemanı tam olarak
`{"event_id": string, "fixture_asset_id": string, "content_sha256":
"sha256:<64-lower-hex>", "media_type": string, "width": uint32,
"height": uint32}`dir; event ID ascending canonical orderdadır. Fixture manifest
root object’i tam olarak `schema_version,fixture_manifest_id,fixture_manifest_hash,
assets` alanlarını taşır. `assets` içindeki her object
`fixture_asset_id,relative_posix_path,content_sha256,media_type,width,height`dir
ve `fixture_manifest_hash/id`, kendi iki identity alanı hariç manifest projection
üzerinden hesaplanır. Resolver yalnız bu exact manifest satırından trusted-root
relative path’i alabilir; props’taki binding hiçbir zaman bir dosya konumu değildir.

### 4.1 Normatif renderer-version temsili

`renderer_version` serbest bir display string değildir. Tam biçimi
`"RRV1|bridge=<BRIDGE_SEMVER>|package_lock_sha256=<64-lower-hex>"` olur.
`BRIDGE_SEMVER`, `engine/rendering/bridge.py` içindeki tek sabit ASCII semverdir.
`package_lock_sha256`, checked-in `renderer-remotion/package-lock.json` ham
byte'larının SHA-256 hex digestidir; `sha256:` öneki yoktur. Python bridge bu iki
değeri launch öncesi hesaplar; props loader biçimi, semver'i ve lock byte hash'ini
exact yeniden hesaplar. `package.json`, Node runtime sürümü, installed
`node_modules`, wall-clock veya lock içindeki dependency-name listesi version
yerine geçemez. Lock dosyası eksik/drift ise `REMOTION_UNAVAILABLE`; format veya
bridge sabiti uyuşmazsa `NON_CANONICAL_PROPS` ile fail-closed olur.

## 5. Composition registry ve design-system temeli

React tarafı `CompositionRegistry` ile yalnız kayıtlı `composition_id` seçer.
Faz 4A’da tek kabul edilen ID `sequence-preview-v1`dir. Registry entry şu
contract’ı tanımlar: props schema version, fixed 1280×720, FPS props’tan,
duration `duration_frames`, root composition ve deterministic layer sırası.
Unknown ID veya version mismatch render öncesi reddedilir.

İlk root composition aşağıdaki sıra ile **en az beş görünür video katmanını**
destekler: base visual (V1), secondary/source visual (V2/V3), evidence/chart
visual (V4), kinetic emphasis (V5), caption (V6), branding/finishing (V7).
Boş EDL track’i görünür sahte katman sayılmaz; fixture bu katmanların beşini
gerçek event ile sağlar. Crop, zoom ve highlight aynı V3 screenshot zaman
aralığında declarative props olarak birlikte uygulanır. V5/V6 cue frame’leri
yalnız event start/end değerlerinden okunur. Chart motion için Faz 4A fixture’ı
V4 structured payload kullanır; Faz 7 chart data engine’i eklenmez.

`DesignTokens V1` immutable ve renderer workspace içinde tek tanımlı olur:
typography/spacing scale, evidence yellow, neutral document/dark quote/chart
palette, easing, transition duration ve caption safe-area. Tasarım tokenları
props hash’inde `design_system_version` olarak bağlanır. Faz 5’te yeni template
veya domain-specific visual grammar eklenmez.

## 6. Fixture Asset Resolver

`FixtureAssetResolver` yalnız checked-in `tests/fixtures/phase4a/` manifestini
ve onun altındaki küçük, lisans/ağ dışı REPLAY assets’lerini okuyabilir. Manifest
canonical JSON olup `fixture_manifest_id`, hash, asset ID, relative POSIX path,
media type, dimensions, byte SHA-256 içerir. Resolver:

- `resolve(event_id)` ile bir binding döndürür; filesystem scan/glob yapmaz;
- `..`, absolute/drive/UNC path, symlink escape, duplicate ID/hash ve unknown
  media type’ı reddeder;
- dosyanın gerçek byte hash’ini render öncesi doğrular;
- cache, download, placeholder veya silent default üretmez;
- asset yoksa receipt’te `ASSET_RESOLUTION_FAILED` ile terminal failure yazar.

İlk fixture SVG/PNG static evidence ve testte oluşturulmuş deterministic audio
metadata kullanabilir. Harici stock/source medya, API veya gerçek source-audio
decoder kullanılamaz.

## 7. Headless invocation, output ve receipt

Python subprocess çağrısı shell string birleştirmez; executable ve argümanlar
array olarak verilir, cwd `renderer-remotion/` olur, timeout explicit olur,
stdin kapalıdır. Environment allowlist’i minimum `PATH`, deterministic locale/
timezone ve renderer’a gerekli sabitlerdir; inherited credential env’leri
props’a veya loglara yazılmaz. Render child output’u bounded capture edilir.

Faz 4A Remotion-only preview çıktısı MP4, WebM, WAV, FFmpeg mux veya decoder
çıktısı değildir. Child, root composition’ı bütün `duration_frames` boyunca
değerlendirir fakat fixture preview artifact’i yalnız sabit örnek kümesindeki
PNG stillerinden oluşur: `0`, `duration_frames//2`, `duration_frames-1`
(duration 1’de duplicate yoktur). Her still `preview/frames/<decimal-frame>.png`
relative POSIX path’inde, exact RGBA 1280×720’dir. Child ayrıca tek canonical
`preview/render-manifest.json` yazar:

```text
schema_version, manifest_id, manifest_hash, render_request_id,
render_props_hash, composition_id, renderer_version, width, height,
fps_numerator, fps_denominator, duration_frames, pixel_format,
frames
```

`frames`, artan `frame_index` sırasındaki exact objects’tir:
`frame_index,relative_path,png_sha256,decoded_rgba_sha256,width,height`.
`manifest_hash`/`manifest_id`, object’in kendisindeki bu iki alan çıkarılarak
canonical JSON’dan sırasıyla `sha256:` + SHA256 ve `rman_` + ilk 32 hex ile
hesaplanır. `relative_path` yalnız yukarıdaki sabit preview root’u altında olur;
manifestte olmayan dosya, manifestteki dosyanın yokluğu, byte hash veya RGBA
hash drift’i failure’dır. Bu plan doğrudan Remotion frame render’ı ile kanıtlanır;
PNG decode yalnız PNG byte’ından RGBA hash doğrulamak içindir ve bir video
encoder/decoder ya da FFmpeg çağrısı değildir.

Her girişim `RenderReceipt` canonical JSON üretir:

```text
schema_version, receipt_id, receipt_hash, render_request_id, status,
failure_code, render_props_id, render_props_hash, video_edl_id, video_edl_hash,
audio_edl_id, audio_edl_hash, composition_id, renderer_version,
node_version, preview_manifest_id, preview_manifest_hash, output_artifact_id,
output_sha256, output_size_bytes, artifact_ids, stdout_sha256, stderr_sha256
```

Receipt kimliği de öz-referanslı değildir. `RenderReceiptIdentityProjection V1`
bu listeden yalnız `receipt_id` ile `receipt_hash` çıkarılmış canonical object’tir.
`receipt_hash = "sha256:" + SHA256(RenderReceiptIdentityProjection V1)` ve
`receipt_id = "rrc_" + digest[0:32]` olur. `output_artifact_id/hash/size`,
başarılı PREVIEW’de sırasıyla preview-manifest `ArtifactRecord` kimliği,
manifest byte SHA-256’sı ve manifest byte length’idir; frame bundle için sahte
tek MP4 kimliği kullanılmaz. `artifact_ids` receipt artifact’inin kendi ID’sini
asla içermez; başarıda sabit sırayla upstream adapter, fixture-manifest adapter,
props, frame ve preview-manifest recordlarını içerir.

`status` yalnız `SUCCEEDED`, `FAILED`, `CANCELLED`dir. `SUCCEEDED` için
`preview_manifest_id/hash` ve output alanları zorunludur; `FAILED/CANCELLED`
için bunlar ve bütün output alanları JSON `null` olur, `failure_code` zorunludur.
Faz 4A cancellation
yalnız parent’ın açık cancellation signal’ını test-double ile almasıdır; queue
ve persistent job worker getirilmez. `SUCCEEDED` için output hash/size ve en az
props + receipt + preview artifact ID’leri vardır; `FAILED/CANCELLED` için
output artifact null, failure code zorunludur. Timeout, non-zero exit, bad
receipt, unavailable binary ve write failure ayrı failure code’lara dönüşür;
başarı maskelenmez.

Determinism kabulü encoded MP4 byte equality iddia etmez; çünkü Faz 4A MP4
üretmez. Aynı locked renderer/fixture/props iki kez çalıştığında:

1. canonical props/receipt identity inputları aynıdır;
2. decoded selected-frame RGBA SHA-256 seti aynıdır;
3. width, height, FPS, duration frame count ve composition ID aynıdır;
4. preview manifest ve her listed PNG’nin byte/RGBA hash’i kendi çalışması
   içinde doğrulanır.

Wall-clock, random, current date, network,
font auto-discovery, locale-dependent text formatting ve nondeterministic CSS
animation yasaktır. Font dosyası checked-in fixture/workspace altında exact
hash ile bağlanır.

## 8. Artifact-registration hook sınırı

Faz 4A, var olan `ArtifactRecord` graph kurallarına uyumlu append-only bir
registration hook kurar. Bu hook accepted EDL kimliklerini doğrudan
`ArtifactRecord.dependency_ids` içine yazmaz; onlar `vedl_`/`aedl_` olup V3
`artifactId` şemasındaki zorunlu `art_` prefix’ini sağlamaz. Bridge önce yalnız
in-memory lineage adapter records üretir ve sonra bütün bağımlılıkları bu valid
`art_*` kimlikleri üzerinden bağlar. Persistence/registry ownership Faz 4B’de
kalır; Faz 4A’daki graph, her attempt’in typed validation inputudur.

Başarılı PREVIEW’nin zorunlu, çevrimsiz adapter topolojisi şöyledir (ok,
`dependency_ids` yönünü gösterir):

```text
art_vedl_<video-edl-digest32>       accepted VideoEdlArtifact bytes
art_aedl_<audio-edl-digest32>       accepted AudioEdlArtifact bytes
art_fixman_<manifest-digest32>      checked-in fixture manifest bytes
  └── art_rprops_<props-digest32>   RenderProps bytes
        ├── art_rframe_<n>_<png-digest32>  each sampled Remotion PNG
        └── art_rmanifest_<digest32>       canonical preview manifest
              └── art_rreceipt_<digest32>  RenderReceipt bytes
```

`art_rprops` depends exactly on `art_vedl`, `art_aedl`, `art_fixman` in that
order. Each frame record depends exactly on `art_rprops`, `art_fixman`; preview
manifest depends on `art_rprops`, followed by sampled frame record IDs in frame
order. Receipt record depends exactly on `art_rprops`, `art_rmanifest`. The
three root adapters have empty dependencies. Thus every `dependency_ids` member
exists in the same validation batch, no record depends on itself, no cycle is
possible, and preview output has both direct and transitive accepted EDL
lineage. A FAILED/CANCELLED attempt emits props plus receipt records only; it
must not emit frame or preview-manifest records.

Every record is an exact existing `ArtifactRecord` schema view, not a parallel
renderer-specific shape: `schema_version="3.0.0"`, valid `art_*` `artifact_id`,
`artifact_type`, upstream `project_id`, upstream `sequence_id`, RFC3339 UTC
`created_at`/`last_accessed_at`, `content_hash`, non-negative `size_bytes`,
`retention_class`, the topology-defined `dependency_ids`, `locked`, `pinned`,
`approved`, `cleanup_candidate`, `producer`, semver `producer_version`, nullable
`job_id`, allowed V3 `status`, and integer `version`. Adapter IDs are derived
from the referenced canonical content digest as shown; their `content_hash`
equals the referenced Video EDL, Audio EDL, fixture manifest, props, PNG,
preview manifest, or receipt byte hash respectively. Phase 4A supplies
`locked=false`, `pinned=false`, `approved=false`, `cleanup_candidate=false`,
`retention_class="review"`, `status="ready"`, `version=1`; it never silently
changes a pre-existing record.

Each props bytes, receipt and successful preview output therefore has stable
ID/content hash/producer version/size/project/sequence/dependency IDs/retention
class. `validate_artifact_graph` is invoked with this complete batch and the
upstream project/sequence allowlists. Graph validation başarısızsa output
başarılı sayılmaz.

Bu hook registry persistence, quota, GC, recovery veya terminal-job orphan
cleanup motoru değildir. Faz 4B; successful/failed/cancelled sonrası cleanup,
overwrite lock/approved korumasının mutating enforcement’ı ve kalıcı lifecycle
işlemlerini tamamlar. Faz 4A hiçbir mevcut locked/approved artifact’i değiştirmez
ve output hedefi mevcut dosyaysa `OUTPUT_TARGET_EXISTS` ile fail-closed olur.

## 9. Fail-closed hata oraklı

En az aşağıdaki kodlar test edilir: `UPSTREAM_NOT_MATERIALIZED`,
`DEPENDENCY_BINDING_INVALID`, `NON_CANONICAL_PROPS`, `UNSUPPORTED_COMPOSITION`,
`ASSET_RESOLUTION_FAILED`, `ASSET_HASH_MISMATCH`, `MODE_NOT_AUTHORIZED`,
`REMOTION_UNAVAILABLE`, `RENDER_TIMEOUT`, `RENDER_EXIT_NONZERO`,
`RECEIPT_INVALID`, `PREVIEW_MANIFEST_INVALID`, `PREVIEW_FRAME_HASH_MISMATCH`,
`ARTIFACT_REGISTRATION_FAILED`, `OUTPUT_TARGET_EXISTS`.

Hata pointer/context’i event veya dependency ID’sini içerir fakat path, token,
raw stderr ya da credential içermez. Hata koşullarının hiçbiri fallback visual,
boş asset, mute audio veya nominal success receipt üretmez.

## 10. Uygulama kabul kanıtı

REPLAY-only test paketi aşağıdakileri kanıtlar:

1. Faz 3 canonical video/audio bytes bağlanır; tamper veya lineage mismatch
   props üretmeden reddedilir.
2. Props loader/serializer byte-identical round trip, hash/ID tamper reddi ve
   stable public surface sağlar.
3. Registry V1–V7/A1–A5’yi sabit sırayla taşır; renderer event schedule veya
   audio boundary değiştiremez.
4. Fixture resolver traversal/missing/hash mismatch için fail-closed olur.
5. Headless fixture preview, canonical Remotion PNG-frame/manifest planıyla 5+
   gerçek video layer, aynı timeline’da crop+zoom+highlight ve V5/V6 word-cued
   text/chart motion üretir; MP4/FFmpeg kabul kanıtı değildir.
6. İki ayrı deterministic run selected-frame hashleri ve receipt input identity
   bakımından aynıdır; no-network gate doğrulanır.
7. Success/failure/cancelled receipt shape ayrıdır ve props/receipt/preview
   records graph validationdan geçer.
8. Existing V2 render path regression testi çalışır; V2 kaynakları değişmez.

Bu kanıtlar Faz 4A’yı kabul ederse, Faz 4B lifecycle/cleanup/overwrite
tamamlanması ile bounded continuation gerekir. Faz 4 ve roadmap’teki tüm final
renderer kabul kriterleri Faz 4A tek başına kapanmış sayılmaz.

## 11. Açık kararlar ve sonraki bounded iş

Bu spec bilinçli olarak Phase 4B için şunları bırakır: gerçek `FULL` render
request ve full-sequence/full-film composition orchestration, true terminal-job
cleanup, approved/locked output overwrite politikasının persistent enforcement’ı,
FFmpeg normalize/mux/final encode, cache/GC, UI progress ve production assets.
Bu nedenle Faz 4 roadmap’inin headless preview **ve full render** maddesi yalnız
Faz 4A ile kabul edilmiş sayılamaz. Faz 4A acceptance sonrası tek sonraki
authoritative task, Phase 4B Render Terminality, Full Render and Artifact
Lifecycle Completion için ayrı spec ve authorization kararıdır.
# Normatif repair addendum — receipt status/DAG

Bu addendum, receipt alanları veya status-DAG konusunda belgedeki daha genel
ifadelerin önüne geçer. `preview_manifest_hash`, `output_sha256`, `stdout_sha256`
ve `stderr_sha256` non-null olduğunda tam olarak `sha256:<64-lower-hex>`
biçimindedir; `preview_manifest_id`/`output_artifact_id` uygun `art_*` ID'sidir.
`output_size_bytes` non-null olduğunda bool olmayan uint64'tür. `artifact_ids`,
tekrarsız `art_*` ID dizisidir, receipt record'un kendi ID'sini hiçbir statüde
içermez. Loader bütün nullability ve digest biçimlerini receipt identity hash'i
hesaplamadan önce doğrular; aksi `RECEIPT_INVALID`tir.

Post-props RenderAttempt, üç accepted ingress adapter (`art_vedl`, `art_aedl`,
`art_fixman`) ve `art_rprops` üretildikten sonra başlar. Canonical props
üretilmeden reddedilen ingress bir RenderAttempt değildir; typed bridge rejection
olarak döner ve receipt/artifact üretmez. Bu ayrım, başarısız receipt'in eksik
veya hayali upstream bağımlılıklarla graph'a yazılmasını önler.

| Receipt status | failure_code | preview/output alanları | artifact_ids exact sıra | receipt DAG |
|---|---|---|---|---|
| `SUCCEEDED` | JSON `null` | `preview_manifest_id/hash`, `output_artifact_id`, `output_sha256`, `output_size_bytes` non-null; output, preview-manifest recordunun exact ID/hash/byte length'idir | `art_vedl`, `art_aedl`, `art_fixman`, `art_rprops`, sampled `art_rframe` IDs frame sırası ile, `art_rmanifest` | receipt -> `art_rprops`, `art_rmanifest`; manifest -> props + frames |
| `FAILED` | zorunlu non-empty closed failure literal | bu beş alanın tamamı JSON `null` | yalnız `art_vedl`, `art_aedl`, `art_fixman`, `art_rprops` | receipt -> yalnız `art_rprops`; frame/manifest record yok |
| `CANCELLED` | zorunlu `CANCELLED_BY_PARENT` | bu beş alanın tamamı JSON `null` | yalnız `art_vedl`, `art_aedl`, `art_fixman`, `art_rprops` | receipt -> yalnız `art_rprops`; frame/manifest record yok |

`SUCCEEDED`te `node_version` non-null, normalized ASCII Node semverdir.
`FAILED`/`CANCELLED`te `node_version`, Node version probe başarılıysa aynı semver,
aksi halde JSON `null` olur; loader null değeri yalnız bu iki status için kabul
eder. Child stdout/stderr capture her post-props attemptte boş olsa bile canonical
byte dizisi olarak bulunur ve ilgili SHA-256 alanları non-null olur; sanitization
sonrası path, credential veya raw stderr receipt'e taşınmaz. Bu iki log digesti
artifact değildir ve `artifact_ids`e girmez. Receipt artifact content hash'i
`receipt_hash` ile exact eşleşir; successful output `output_sha256` ise yalnız
preview-manifest byte hash'idir, receipt hash'i veya frame bundle birleşik hash'i
değildir.
