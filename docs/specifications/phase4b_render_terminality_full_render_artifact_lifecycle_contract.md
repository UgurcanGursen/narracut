# Faz 4B - Render Terminality, Full Render and Artifact Lifecycle Completion Contract

> Durum: Aday spesifikasyon - kabul veya uygulama yetkisi degildir
> Onkosul: Faz 4A ACCEPTED / CLOSED / REMOTE CLOSED
> Amac: Faz 4A preview temelini degistirmeden gercek `FULL` render terminalitesi,
> FFmpeg normalize/mux/final encode ve persistent artifact lifecycle kapanisini
> tanimlamak

## 1. Sinir ve non-goals

Bu contract Faz 4A `PREVIEW` behaviorunu korur ve yalniz onun accepted typed
props/receipt/lineage modelini genisletir. Faz 5 template kutuphanesi, Faz 8
provider/source acquisition, queue/retry, Studio UI progress, cache/GC policy,
production asset catalog, source-audio suitability veya multi-user worker
orchestration bu kapsamda yoktur.

`FULL`, preview'un basarisizligini maskeleyen pseudo request degildir: tek
sequence veya acikca tanimli film render planinin tum frame araligini ve kabul
edilmis A1-A5 PCM-boundary metadata'sini gercekten tuketir. Faz 4B yeni EDL,
asset, cue, duration, transition veya audio boundary uretemez; Faz 3 accepted
bytes tek scheduling otoritesi olmaya devam eder.

## 2. Ingress ve FULL request kimligi

`FullRenderRequest V1`, accepted RenderProps V1 ile baslar ve yalniz su ek
alanlari tasir: closed `mode="FULL"`, `output_profile_id`, canonical
`output_target_id`, `full_render_request_id` ve `full_render_request_hash`.
Kimlik projection'i kendi ID/hash alanlarini cikartir; hash
`sha256:<64-lower-hex>`, ID `frq_<digest32>` olur. Output profile yalniz
checked-in allowlistten secilir; caller codec, bitrate, resolution, FPS, path,
FFmpeg argumani veya audio gain enjekte edemez.

Request, Faz 4A RenderProps lineage'i, project/document/narration/sequence
kimlikleri, video/audio EDL hashleri, renderer version ve FFmpeg toolchain
identity'sini exact baglar. Tamper, stale dependency, noncanonical JSON,
unknown profile veya `PREVIEW` props'tan FULL'a sessiz donusum fail-closed olur.

## 3. Gercek full render ve FFmpeg siniri

Remotion, kabul edilmis composition'i `duration_frames` boyunca frame-accurate
render eder. Python motion/EDL hesaplamaz. FFmpeg yalniz pinned/probed toolchain
ile su sirada calisir:

1. Renderer video streamini profile kurallarina gore normalize eder.
2. Accepted A1-A5 PCM/boundary metadata'sindan audio mix girdi manifestini
   dogrular; PCM'i yeniden schedule etmez.
3. Video ve audioyu mux eder, final encode eder ve output'u probe eder.

Codec/container/sample rate/channel layout/pixel format closed profile tarafindan
belirlenir. Probe, codec/container/duration/fps/sample-clock ve stream sayisini
profile ile exact eslestirmeden success yazamaz. FFmpeg stderr, path veya
credential receipt'e tasinmaz; yalniz sanitize edilmis digest ve typed failure
code kalir. Network, provider, shell-string invocation ve implicit host font
discovery yasaktir.

## 4. Persistent artifact lifecycle ve terminality

Her FULL attempt, Faz 1 `ArtifactRecord` semasina append-only kalici kayitlar
yazar. Request, props, renderer video intermediate'i, normalized audio
intermediate'i, final output, probe reportu ve receipt ayri artifact olur;
content hash, size, producer/version, project/sequence, dependency IDs,
retention, status, lock/pin/approved alanlari zorunludur. Dependency graph
batch halinde validate edilir; kayit basarisizsa render SUCCESS olamaz.

Attempt terminal statuleri closed set `SUCCEEDED`, `FAILED`, `CANCELLED`dir.
Terminal receipt, status/failure nullability, output artifact identity/hash/size,
toolchain identity ve sanitize stdout/stderr digestlerini canonical JSON olarak
tasir. `SUCCEEDED` yalniz final output + probe + registry kayitlari tam oldugunda
verilir. `FAILED`/`CANCELLED` final artifact uretemez; mevcut approved output'u
asla success gibi gosteremez.

## 5. Output hedefi, overwrite ve cleanup

Output target, artifact registry'nin persistent kaydiyla resolve edilir; raw
filesystem path public request alani degildir. Hedef mevcutsa:

- `locked=true` veya `approved=true` ise overwrite mutlak yasaktir.
- Unlocked/unapproved hedefte overwrite ancak explicit canonical replacement
  policy ve yeni artifact lineage'i ile mumkundur.
- Atomic staging-to-target publish kullanilir; yarim dosya hedefi degistiremez.

Her attempt kendine ait sandbox rootunda calisir. Success, failure veya explicit
cancellation sonrasinda ephemeral frame/temp/intermediate dosyalari, registry'de
kalmasi gerekmeyen retention sinifina gore deterministic cleanup planindan
gecer. Cleanup sadece attempt root icindeki exact manifestte kayitli dosyalara
uygulanir; glob, age-based broad delete, baska attempt/project dosyasi silme ve
locked/pinned artifact silme yasaktir. Cleanup sonucunun kendisi canonical
terminal receipt/probe alaninda veya bagli cleanup report artifactinde kayitli
olur. Orphan tespiti manifest+registry lineage ile yapilir; cache/GC motoru bu
fazda getirilmez.

## 6. Fail-closed failure oracle

En az su typed kodlar tanimlanir ve test edilir: `FULL_MODE_NOT_AUTHORIZED`,
`FULL_REQUEST_INVALID`, `FFMPEG_UNAVAILABLE`, `FFMPEG_NORMALIZE_FAILED`,
`FFMPEG_MUX_FAILED`, `FINAL_ENCODE_FAILED`, `FINAL_PROBE_INVALID`,
`ARTIFACT_PERSIST_FAILED`, `OUTPUT_LOCKED`, `OUTPUT_APPROVED`,
`OVERWRITE_POLICY_INVALID`, `ATOMIC_PUBLISH_FAILED`, `CLEANUP_FAILED`,
`CANCELLED_BY_PARENT`. Hicbiri fallback video, mute audio, partial output veya
nominal success receipt uretemez.

## 7. Kabul kaniti

REPLAY-only test paketi su kanitlari saglar:

1. Faz 4A preview regression'i byte/identity davranisini korur.
2. FULL request accepted Phase 3/4A lineage olmadan props/attempt uretmeden
   reddedilir; runtime EDL/audio schedule degistiremez.
3. Gercek full sequence render + FFmpeg mux/encode uretir; probe closed output
   profile'i, A/V durationini ve 48 kHz audioyu dogrular.
4. Iki isolated run ayni accepted inputlarda declared deterministic fingerprint
   setini verir; test hedefleri birbirini overwrite etmez.
5. Success, failure ve cancellation ayri receipt/DAG/registry kayitlari ile
   kanitlanir; terminal cleanup kayitsiz attempt-local temp birakmaz.
6. Locked/approved target overwrite denemesi mutasyon olmadan typed hata verir;
   allowed replacement atomic publish ve eski/yeni lineage kaniti uretir.
7. V2 yolunun regression testi ve no-network/no-provider gate calisir.

## 8. Uygulama yetkisi ve sonraki karar

Bu belge adaydir. Bagimsiz read-only audit, ayri acceptance karari ve acik
implementation authorization olmadan kod, package degisikligi, migration veya
artifact mutasyonu yapilamaz. Faz 4 yalniz bu bounded implementation kabul,
remote closure ve Master Roadmap kriter uzlasimindan sonra kapanabilir.

```text
PHASE4B_SPECIFICATION_STATUS=CANDIDATE
PHASE4B_SPECIFICATION_ACCEPTED=NO
PHASE4B_IMPLEMENTATION_AUTHORIZED=NO
PHASE4_CLOSED=NO
```
