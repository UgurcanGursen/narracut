# Faz 4B - Render Terminality, Full Render and Artifact Lifecycle Completion Contract

> Durum: Aday spesifikasyon - kabul veya uygulama yetkisi degildir
> Onkosul: Faz 4A ACCEPTED / CLOSED / REMOTE CLOSED
> Amac: Faz 4A preview temelini degistirmeden gercek `FULL` render,
> FFmpeg normalize/mux/final encode ve kalici artifact terminalitesini tanimlamak

## 1. Sinir ve degismez onkosullar

Bu contract sadece bir accepted Faz 3 Video/Audio EDL ciftinden, accepted Faz 4A
`RenderProps V1` projectionindan ve checked-in REPLAY PCM girdilerinden gercek
sequence-local `FULL` output uretir. Faz 5 template kutuphanesi, provider/source
edinimi, queue/retry, Studio UI progress, cache/GC, production asset catalog,
source-audio suitability, film-level planner veya multi-user worker kapsam disidir.

Faz 3 EDL bytes tek schedule otoritesidir. Faz 4B yeni event, cue, duration,
transition, gain, boundary veya asset uretmez; Python motion/EDL hesaplamaz ve
FFmpeg yeniden schedule etmez. Faz 4A preview API'si, `RenderProps V1` bytes'i,
receipt'i, output semantigi ve `PREVIEW` mode'u degistirilemez. FULL sonucu,
preview basarisizligini maskeleyen pseudo-output olamaz.

## 2. Ayrik FullRenderRequestV1 ingress envelope'u

`FULL` istegi Faz 4A props'unun alanlarini genisletmez veya `mode` degerini
degistirmez. `RenderProps V1.mode` envelope icinde dahi exact `PREVIEW` kalir.
FULL niyeti sadece su kapali envelope ile ifade edilir:

```text
schema_version, full_render_request_id, full_render_request_hash,
render_props, render_props_canonical_sha256, full_render_profile_id,
full_render_profile_hash,
remotion_identity_hash, node_identity_hash, ffmpeg_identity_hash,
ffprobe_identity_hash, output_target_id, pcm_input_manifest,
cancellation_ingress_id
```

`schema_version` exact `FULL-RENDER-REQUEST-V1` literalidir. `render_props`,
Faz 4A loader'inin kabul ettigi complete object'tir; serializer'inin canonical
UTF-8 bytes'i tekrar hesaplanir ve `render_props_canonical_sha256` ile exact
eslesir. Bu alan `sha256:<64-lower-hex>` olur. `render_props.mode != PREVIEW`,
ek/eksik alan, bir 4A identity/hash uyusmazligi veya byte-equivalent olmayan JSON
`FULL_REQUEST_INVALID`tir. Böylece immutable 4A props'a `FULL`, output path,
codec, PCM veya FFmpeg alanlari eklenemez.

`FullRenderRequestIdentityProjection V1`, yukaridaki object'ten yalniz
`full_render_request_id` ve `full_render_request_hash` cikarilarak canonical
JSON ile olusturulur. `full_render_request_hash = "sha256:" + SHA256(projection)`
ve `full_render_request_id = "frq_" + digest[0:32]` olur. ID/hash loader
tarafindan herhangi bir process veya artifact uretilmeden once tekrar hesaplanir.
`output_target_id` `outt_<32-lower-hex>` stable ID'sidir; raw path, URL, codec,
FPS, gain, FFmpeg argument'i, ortam degiskeni veya provider descriptor request'e
giremez.

### 2A. Output-target pre-admission resolution, binding ve hata onceligi

`output_target_id` request identity'sinde olmasi tek basina publish yetkisi
vermez. Orchestrator, `ADMITTED` transitionindan, attempt ID/attempt root,
artifact, registry revision, output reservation, child process veya toolchain
preflight olusturmadan once `artifacts/output-targets.jsonl`in trusted,
append-only snapshotindan exact target head'i read-only resolve eder. Runtime
target bootstrap etmez, eksik target icin kayit eklemez, path tahmin etmez ve
basarili baska bir target'i fallback olarak secmez.

Resolve edilen head'in `output_target_id`, accepted 4A `render_props`un
`project_id` ve `sequence_id` binding'leri ile exact eslesmek zorundadir.
Requestteki target bulunamazsa, target kaydi baska project/sequence'a
bagliysa veya first-publish/replacement icin gerekli initial head ayni trusted
snapshotta kullanilabilir degilse pre-admission sonucu exact
`OUTPUT_TARGET_CONFLICT` olur. Bu cevap attempt, artifact, receipt, cleanup
manifesti/reportu, output reservation, publish veya child process uretmez.

Bu resolution once targeta ait tum `OUTPUT-TARGET-RECORD-V1` satirlarinin
canonical ID/hashlerini ve tek linear chain olusturdugunu dogrular: zincir
yalniz `revision=1` ve iki `previous_* = null` olan tek initial recordla
baslar; her sonraki revision tam bir artar, onceki exact ID/hash'e baglanir ve
immutable target/project/sequence/trusted path alanlarini korur. Hash/ID
drift'i, revision atlamasi, duplicate initial record, fork, birden cok head,
predecessor yoklugu, targetlar arasi linkage veya immutable `locked`/`approved`
degerlerinin revisionlar arasinda degismesi structural corruption'dir ve
pre-admission sonucu exact `ARTIFACT_PERSIST_FAILED` olur. Bu durumda da
attempt/artifact/receipt/process veya registry mutasyonu yapilmaz.

Output-target ailesinde hata onceligi kapali ve deterministiktir. Envelope/4A
props veya request identity gecersizse once `FULL_REQUEST_INVALID`; profile
binding gecersizse ondan sonra `FULL_RENDER_PROFILE_INVALID` verilir. Bu iki
precondition gectikten sonra structural chain corruption
`ARTIFACT_PERSIST_FAILED`, missing/project-sequence binding/initial-head
failure `OUTPUT_TARGET_CONFLICT`, sonra sirasiyla `OUTPUT_LOCKED`,
`OUTPUT_APPROVED` ve `OVERWRITE_POLICY_INVALID` degerlendirilir. Dolayisiyla
structural olarak corrupt bir chain, ayni anda target-missing/binding semptomu
varsa `ARTIFACT_PERSIST_FAILED` ile maskelenmez; bunun disinda listedeki ilk
uyusan kod tek ingress sonucudur. Mevcut kural geregi invalid envelope bu
ailenin hicbiri ve cancellation tarafindan maskelenemez.

`cancellation_ingress_id`, parent'in attempt-local, opaque ve non-secret
signal handle'idir; identity'ye dahildir ama path veya credential degildir.
Sadece trusted orchestration adapter'i bu handle'i kullanabilir. User-controlled
environment variable, signal adi veya child stdout cancellation ingress'i olamaz.

### 2B. Trusted initial target-head provisioning onkosulu

`output-targets.jsonl` ilk-head provisioning'i FULL runtime'in bir parcasi
degildir. `revision=1`, null-current, null-policy initial record, yalniz bu
contract disindaki trusted project/workspace provisioning owner'i tarafindan
yaratilabilir. Bu owner fixture setup veya productta ayri, yetkili project
olusturma akisi olabilir; caller, FULL request, render profile, Remotion,
FFmpeg, recovery veya cleanup yolu bu owner yerine gecemez.

Owner, exact project-root containmentini, project/sequence bindingini ve
`trusted_publish_relative_path` kurallarini record olusmadan once dogrular.
Initial record creation, attempt-local olmayan ayni registry lock altinda
read-chain -> target-absent -> canonical initial-record append+flush sirasi ile
atomiktir. Var olan herhangi bir target head, concurrent winner, partial write,
hash/ID uyusmazligi veya create sonrasi yeniden okunamayan head provisioning
basarisidir; owner bunu in-place repair, ikinci initial record veya fallback
target ile gizleyemez. Bu contracttaki FULL pre-admission, ancak owner'in
durable olarak olusturdugu ve read-only chain validationdan gecen initial/current
head'i kullanir; eksik head'i yaratmaz. Dolayisiyla test fixture'i de ayni
trusted owner contractiyle initial head'i atomik olarak provision eder, render
attempt'iyle degil.

`remotion_identity_hash`, `node_identity_hash`, `ffmpeg_identity_hash` ve
`ffprobe_identity_hash`, secilen checked-in `FullRenderProfileV1` satirinin
respective identity projection'larinin canonical SHA-256 degerleridir. Bunlar
caller tarafindan executable, PATH adi, package yolu, surum veya argv secmek
icin kullanilamaz: loader once profile'i exact `full_render_profile_id` ile
resolve eder, dort profile projection hash'ini tekrar hesaplar ve request ile
exact eslestirir. Eksik/ek alan, profile ile uyusmayan hash veya canonical-byte
drift `FULL_RENDER_PROFILE_INVALID`tir. Resolved profile'in canonical self-hash'i
requestteki exact `full_render_profile_hash` ile eslesmelidir; uyusmazlik
`FULL_RENDER_PROFILE_INVALID`tir. Bu bes binding request identity'sine dahildir;
dolayisiyla ayni props/profile ID'si altinda Node, Remotion, FFmpeg veya FFprobe
toolchain'inin sessiz degisimi yeni request identity'si olmadan kabul edilemez.

`render_props`, Remotion'a yalniz canonical UTF-8 byte olarak
`attempt/remotion/render-props.json` konumunda materialize edilir. Bu dosyanin
SHA-256'si `render_props_canonical_sha256` ile exact eslesir; Remotion CLI'nin
tek props girdisi profile'daki `{RENDER_PROPS_JSON}` complete-path placeholder'i
olur. CLI props'u yeniden serialize edemez, inline JSON alamaz veya baska props
dosyasi okuyamaz. Remotion'un tek video sonucu
`attempt/remotion/video.<profile-container>` olur; bu trusted regular file'in
hash/byte-lengthi renderer-video artifact record'una yazilir ve sonraki
asamalarda `{INPUT_VIDEO}` yalniz bu exact path'e expand edilir. Profile
`remotion_composition_id`, props'taki 4A composition identity ile exact
eslesmezse `FULL_RENDER_PROFILE_INVALID`tir.

## 3. Hash-bound PCM input manifest ve resolver

`pcm_input_manifest` request icinde inline, canonical ve closed object'tir:

```text
schema_version, manifest_id, manifest_hash, sample_rate_hz, channel_layout,
duration_samples, audio_edl_id, audio_edl_hash, entries
```

`schema_version` `FULL-RENDER-PCM-MANIFEST-V1`; sample rate exact `48000`;
channel layout exact `stereo` olur. `manifest_id/hash` kendi iki identity alani
cikarilmis projectiondan sirasiyla `pcmm_` + digest32 ve `sha256:` + SHA256'dur.
`entries`, accepted Audio EDL A1-A5 events'inin track/ordinal sirasindaki
lossless PCM resolver satirlaridir. Her satir tam olarak:

```text
event_id, event_hash, track, ordinal, normalized_pcm_evidence_hash,
pcm_artifact_id, pcm_content_sha256, byte_length, sample_rate_hz,
channel_layout, source_in_sample, source_out_exclusive_sample
```

tasir. Event ID/hash, track, ordinal, PCM evidence hash ve sample araligi Audio
EDL ile exact eslesir. `pcm_artifact_id` kalici registry'de `art_*` kaydidir;
`pcm_content_sha256` dosyanin actual hash'idir. Resolver yalniz registry
recordunun attemptten once sabitlenmis trusted relative storage locationunu
kullanir, dosyanin byte length/hash/sample-rate/channel-layoutini decode/probe
ile dogrular ve manifestte olmayan dosya okumaz. Glob, directory scan, URL,
host path, placeholder, sessiz mute veya yeniden sample scheduling yasaktir.
Eksik/tamper/EDL uyusmazligi `PCM_INPUT_INVALID` ile render process'i baslamadan
reddedilir.

Resolver her entry icin decode/probe sonrasinda byte-identical, lossless
attempt-local PCM materialization uretir:
`attempt/pcm/<track>/<ordinal>-<event_id>.wav`. Path, event'in validated
track/ordinal/event_id alanlarindan olusur; entry sirasi Audio EDL'nin
track/ordinal sirasidir ve isimlendirmede caller path'i kullanilmaz. Her
materialized dosya manifestteki `pcm_content_sha256`, byte length, 48000 Hz ve
stereo degerini yeniden kanitlar. Ardindan bu sirayla her entry'ye sifirdan
baslayan immutable `pcm_input_slot` atanir. Slot `i`, normalize invocation
icinde yalniz `-i attempt/pcm/<track>/<ordinal>-<event_id>.wav` iki-token
ciftiyle ve FFmpeg audio input indeksi `i + 1` ile temsil edilir; input 0
yalniz `{INPUT_VIDEO}`'dur. Concat demuxer, `-f concat`, liste dosyasi,
`ffmpeg-inputs.txt`, tek bir birlesik PCM inputu veya implicit silence
yasaktir. `PCM-MATERIALIZATION-REPORT-V1` ayri artifacti tam olarak
`schema_version,report_id,report_hash,pcm_manifest_id,pcm_manifest_hash,
entries,pcm_input_argv_sha256` alanlarini tasir; her `entries` satiri tam
olarak `pcm_input_slot,ffmpeg_audio_input_index,materialized_pcm_relative_path,
manifest_event_id,manifest_event_hash,materialized_pcm_content_sha256,
byte_length,sample_rate_hz,channel_layout` alanlarini tasir.
`ffmpeg_audio_input_index=pcm_input_slot+1` olur;
`pcm_input_argv_sha256`, slot sirasindaki ASCII NUL-ayrilmis `-i` / relative
path token ciftlerinin hash'idir. Bu report request envelope'unda yeni bir
caller secenegi degil resolver'in process-oncesi deterministic outputudur.
Normalize argv'sindeki `{PCM_INPUT_ARGUMENTS}`, bu kapali token ciftlerinin
tek degisken-slot expansion noktasidir; runtime baska PCM inputu ekleyemez,
cikarmaz veya yeniden siralayamaz. Sira, dosya seti, slot/argv bytes'i veya
herhangi bir PCM hash'i drift ederse `PCM_INPUT_INVALID` olur. Bu kurallar bir
event'i iki kez, farkli sirada ya da implicit silence ile materialize etmeyi
yasaklar.

## 3A. Deterministic AudioRenderPlan ve filter-script artifact'i

PCM resolver basarili olduktan sonra, normalize process'i baslamadan once
orchestrator accepted Audio EDL, PCM manifest ve PCM materialization report'tan
tek bir `AUDIO-RENDER-PLAN-V1` artifact'i derler. Bu caller-configurable bir
envelope veya FFmpeg argumani degildir. Kapali canonical object tam olarak su
alanlari tasir:

```text
schema_version, audio_render_plan_id, audio_render_plan_hash,
audio_edl_id, audio_edl_hash, pcm_manifest_id, pcm_manifest_hash,
pcm_materialization_report_id, pcm_materialization_report_hash,
sample_rate_hz, channel_layout, duration_samples, clips, boundaries, mix
```

`schema_version` exact `AUDIO-RENDER-PLAN-V1` olur. Plan ID/hash, yalniz
`audio_render_plan_id` ve `audio_render_plan_hash` cikarilmis object'in
canonical UTF-8 projection'undan sirasiyla `arp_<digest[0:32]>` ve
`sha256:<64-lower-hex>` olarak hesaplanir. `audio_edl_id/hash`, request PCM
manifestindeki binding ile accepted Audio EDL'nin exact identity'sine; PCM
manifest/report ID/hashleri de resolver'in immutable outputlarina exact
eslesmek zorundadir. `sample_rate_hz=48000`, `channel_layout=stereo` ve
`duration_samples`, Audio EDL'nin degerleriyle exact eslesir. Her fark,
eksik/ek alan, canonical-byte drift veya duplicate plan `PCM_INPUT_INVALID`tir.

`clips`, Audio EDL'nin sabit `A1..A5` track ve event ordinal sirasinda her EDL
event'i icin tam bir satir tasir:

```text
event_id, event_hash, track, ordinal, pcm_input_slot,
ffmpeg_audio_input_index, materialized_pcm_relative_path,
materialized_pcm_content_sha256, source_in_sample,
source_out_exclusive_sample, scheduled_start_sample,
scheduled_end_exclusive_sample, gain_millibels, leading_trim_samples,
trailing_trim_samples, fade_in_samples, fade_out_samples, overlap_samples
```

Event identity, track/ordinal, source araligi, schedule ve gain dogrudan ilgili
Audio EDL event'inden gelir. Materialized path/hash ve
`pcm_input_slot/index`, exact corresponding PCM materialization-report
entry'sinden gelir. `leading_trim_samples`, `trailing_trim_samples`, fade ve
overlap alanlari sadece event'in leading/trailing veya between-events
`AudioBoundaryDecision` satirlarindan hesaplanir; caller degeri, heuristic,
auto-normalize, limiter, ducking, tempo, resample veya implicit gain yoktur.
Mapping kapali ve yonludur: LEADING decision'in `right_trim_samples` degeri
ilk/right event'in `leading_trim_samples` degeridir; TRAILING decision'in
`left_trim_samples` degeri son/left event'in `trailing_trim_samples` degeridir;
BETWEEN_EVENTS decision'inda `left_trim_samples` left event'in trailing,
right_trim_samples` right event'in leading trimidir. Her event kenari icin
uygulanabilir en fazla bir karar bulunur; ayni kenara iki karar veya negatif/
source araligini bosaltan toplam trim `PCM_INPUT_INVALID`tir. Effective PCM
trim araligi `[source_in_sample + leading_trim_samples,
source_out_exclusive_sample - trailing_trim_samples)` olur; effective signal
exact `scheduled_start_sample + leading_trim_samples` konumuna delay edilir.
Bu nedenle trim, EDL eventinin
`[scheduled_start_sample, scheduled_end_exclusive_sample)` schedule alanini
degistirmez; sadece Faz 3 kararinin kenarindaki planli sessiz orani korur.
`gain_millibels`, filter scriptte canonical signed decimal dB
literaline (`<integer-or-decimal-millibels/1000>dB`) bire-bir donusur.

`boundaries`, Audio EDL `boundary_decisions` dizisinin track/position/event
identity sirasindaki lossless projectionidir: `track, position,
left_event_id, right_event_id, policy, transition, left_trim_samples,
right_trim_samples, fade_in_samples, fade_out_samples, overlap_samples,
protected_silence_samples`. Her clip edge'i ve her planned-silence araligi bu
satirlarla bire-bir baglanir. `PRESERVE_SILENCE` sadece EDL'deki exact zero
araligini korur; plan yeni silent clip uretmez. `OVERLAP_CROSSFADE` sadece
EDL'nin mevcut overlap araliginda, belirtilen sample sayisi ile uygulanir.
`mix` kapali olarak `duration_samples`, `sample_rate_hz`, `channel_layout`,
`track_order=[A1,A2,A3,A4,A5]` ve `clip_event_ids` alanlarini tasir; eventlerin
tamamini bir kez ve yalniz bir kez kapsar. Bu plan yeni schedule, boundary,
gain veya source secemez.

Planin tek executable projection'i ayri immutable
`AUDIO-FILTER-SCRIPT-V1` artifact'idir. Bu artifact tam olarak
`schema_version, audio_filter_script_id, audio_filter_script_hash,
audio_render_plan_id, audio_render_plan_hash, filter_script_utf8_sha256,
byte_length` alanlarini tasir. ID/hash kendi iki identity alani cikarilmis
canonical projectiondan `afs_<digest[0:32]>` ve `sha256:<64-lower-hex>` olarak
hesaplanir; script bytes'inin hash'i ve length'i bu record ile exact eslesir.
Filter script UTF-8/LF, NUL'suz, locale-independent ve planin clip/boundary/mix
satirlarindan canonical sirada derlenir. Clip `i` icin tek raw FFmpeg label
`[<ffmpeg_audio_input_index>:a]`, tek pre-boundary label
`[p<i>_pre]`, tek post-boundary label `[p<i>_post]` ve mix'e giden tek label
`[p<i>_mix]` vardir; `i` decimal `pcm_input_slot` degeridir ve label'larda
leading zero, locale veya alternatif isimlendirme yoktur. Raw label exact bir
kez su semantic zincire girer: `aformat=sample_rates=48000:channel_layouts=
stereo,atrim=start_sample=<source_in+leading_trim>:end_sample=<source_out-
trailing_trim>,asetpts=PTS-STARTPTS,adelay=<scheduled_start+leading_trim>S:
all=1,volume=<canonical-dB>[p<i>_pre]`. Faz 3 boundary fade/crossfade
operasyonlari yalniz `[p<i>_pre]` label'larini alip ilgili `[p<i>_post]`
label'larini uretir; boundary yoksa `[p<i>_pre]anull[p<i>_post]` zorunludur.
Stereo mapping explicit ve degismezdir: her raw input yukaridaki `aformat` ile
dogrulanir, `adelay` `all=1` ile iki kanala ayni sample delay'ini uygular ve
hicbir `pan`, mono upmix,
downmix veya channel-layout conversion bulunamaz. Her `[p<i>_post]`, exact
bir kez `anull` ile `[p<i>_mix]` olur; canonical slot sirasi ile `amix`e
girer. Son `amix` sonucu `aformat=sample_rates=48000:channel_layouts=stereo`
ve `atrim=end_sample=<duration_samples>` ile sinirlanir. Her input bir kez
`atrim`, sample tabanli `adelay`, Faz 3 boundary fade/crossfade ve exact dB
gain islemlerinden gecer; son `amix` sonucu exact stereo/48kHz ve
`duration_samples` ile sinirlanir.
Scriptte host dosya yolu, URL, shell syntax, env expansion, `eval`, auto gain,
implicit duration veya plan disi input bulunamaz. Runtime script'i yeniden
hesaplar, plan binding/byte hash/length'i kanitlar ve onu sadece
`attempt/audio/filter-script.ffscript` konumuna yazar. Bu dosya ve plan,
ayri ArtifactRecord'lar olarak registry DAG'ine normalize-audio artifactinden
once baglanir. Drift, missing event, duplicate input veya EDL-boundaryden farkli
filter islemi `PCM_INPUT_INVALID` ile FFmpeg baslamadan reddedilir.

### 3A.1. AudioBoundaryDecision -> FFmpeg graph: kapali derleme tablosu

Asagidaki tablo, `AudioBoundaryDecision` satirinin tek allowed FFmpeg
projectionidir. Bu tablo onceki bolumdeki "boundary fade/crossfade" ifadesini
tamamlar; runtime alternatif filtre, `acrossfade`, `concat`, otomatik curve
veya duration secemez. `acrossfade` ozellikle yasaktir: concat-benzeri bir
zaman ekseni uretir ve Faz 3'un zaten schedule edilmis overlap'ini kaydirir.
`OVERLAP_CROSSFADE`, iki independently scheduled clip uzerindeki iki
`afade` ile elde edilir.

Her clip `i` icin su integerler plan satirindan hesaplanir:

```text
S_i = scheduled_start_sample + leading_trim_samples
E_i = scheduled_end_exclusive_sample - trailing_trim_samples
N_i = E_i - S_i
```

`S_i`, `E_i`, `N_i` decimal ASCII non-negative integerlerdir; `N_i > 0` ve
her uygulanmis fade icin `0 < fade_samples <= N_i` zorunludur. `p<i>_pre`
tam olarak onceki bolumun raw zincirinin outputudur ve bu zincirdeki
`adelay` argumani `S_iS` olur. Bir incoming fade'in canonical ifadesi
`afade=t=in:ss=S_i:ns=F:curve=tri`; bir outgoing fade'in canonical ifadesi
`afade=t=out:ss=E_i-F:ns=F:curve=tri` olur. `ss`, time-second degil sample
sayisidir; `ns` tam sample sayisidir. `tri` tek allowed curve literalidir.
`st`, `d`, floating-point second, locale decimal, `qsin`, `exp`, default
curve veya implicit fade parametresi yasaktir.

| Decision policy | Sol/left event projection | Sag/right event projection | Zorunlu semantic kontrol |
| --- | --- | --- | --- |
| `PRESERVE_SILENCE` | `anull` | `anull` | `transition=NONE`, tum trim/fade/overlap `0`; `protected_silence_samples>0`; EDL'nin exact zero araligi korunur, yeni silence source/filter eklenmez. |
| `HARD_CUT_ZERO_CROSSING` | `anull` | `anull` | `transition=NONE`, tum trim/fade/overlap/protected-silence `0`; iki kaynak kenari Faz 3 tarafindan exact zero crossing olarak kanitlanmistir. |
| `ZERO_CROSSING_MICROFADE` | `afade=t=out:ss=E_left-fade_out_samples:ns=fade_out_samples:curve=tri` yalniz `fade_out_samples>0` ise; aksi `anull` | `afade=t=in:ss=S_right:ns=fade_in_samples:curve=tri` yalniz `fade_in_samples>0` ise; aksi `anull` | `transition=NONE`, `overlap_samples=protected_silence_samples=0`; trimler raw `atrim`de zaten uygulanmistir. |
| `LONG_EDITORIAL_FADE` | `afade=t=out:ss=E_left-fade_out_samples:ns=fade_out_samples:curve=tri` yalniz `fade_out_samples>0` ise; aksi `anull` | `afade=t=in:ss=S_right:ns=fade_in_samples:curve=tri` yalniz `fade_in_samples>0` ise; aksi `anull` | `overlap_samples=protected_silence_samples=0`; only accepted Faz 3 long-fade decision values kullanilir; compiler yeni fade uzunlugu secmez. |
| `OVERLAP_CROSSFADE` | `afade=t=out:ss=E_left-O:ns=O:curve=tri` | `afade=t=in:ss=S_right:ns=O:curve=tri` | `transition=CROSSFADE`, `left_trim_samples=right_trim_samples=protected_silence_samples=0`, `fade_in_samples=fade_out_samples=overlap_samples=O`, `O>=2`, `E_left-S_right=O`; `acrossfade` yasaktir. |

Bir `LEADING` decision yalniz tablonun right projectionini, `TRAILING`
yalniz left projectionini, `BETWEEN_EVENTS` ise iki projectioni uygular.
Bir decision alaninin tablo satiriyla uyusmamasi (ornek: zero-crossing
decisionda overlap, crossfadede farkli fade sayilari, protected silence ile
fade) `PCM_INPUT_INVALID`tir. Fade uygulanmayan her side icin compiler yine
explicit `anull` yazar; filtre secimi veya "identity filter'i atla" davranisi
canonical degildir.

Middle clipin iki siniri icin label/fanout ve yazim sirasi da kapali olarak
asagidadir. Clip `i`nin onceki `BETWEEN_EVENTS` decisioni `B_prev`, sonraki
decisioni `B_next` olsun; `B_prev` bu clipin right-side, `B_next` left-side
projectionidir. `B_prev`/`B_next` yoksa, ya da ilgili side policy tarafindan
identity ise, o stage `anull` olur.

```text
[p<i>_pre]<B_prev right-side expression or anull>[p<i>_left]
[p<i>_left]<B_next left-side expression or anull>[p<i>_right]
[p<i>_right]anull[p<i>_post]
[p<i>_post]anull[p<i>_mix]
```

Her ara label (`p<i>_pre`, `p<i>_left`, `p<i>_right`, `p<i>_post`,
`p<i>_mix`) tam bir producer ve tam bir consumer tasir; split/asplit, bir
label'in iki boundary tarafindan tekrar okunmasi, birden cok `amix` girisi,
veya unlabelled filter output yasaktir. Bu nedenle middle clip iki boundary
fadini sirayla alir fakat iki kez mix edilmez. Global script clipleri
`pcm_input_slot` artan sirasiyla bu dort satirlik bloklarla yazar; bundan
sonra `[p0_mix]...[pN_mix]amix=inputs=N:duration=longest:dropout_transition=0`
yazar ve mevcut final `aformat,atrim=end_sample=<duration_samples>` zincirini
ekler. `N`, `mix.clip_event_ids` uzunluguna exact esit olmali, her label bir
kez bulunmali ve `amix` input sirasi `pcm_input_slot` sirasi olmalidir.

Multi-event acceptance oracle en az bir trackte ard arda uc event (`e0`,
`e1`, `e2`) ve iki farkli `BETWEEN_EVENTS` decision icermelidir: `B01`
`e0/e1`, `B12` `e1/e2`. Oracle, `e1` icin tam olarak yukaridaki dort label
satirini, once `B01`in right-side sonra `B12`nin left-side uygulanmis halde
byte-exact bekler; `e1`in `amix`e yalniz bir `[p<i>_mix]` girisi olur. Oracle
ayrica (1) hem `ZERO_CROSSING_MICROFADE` trim+fade hem
`OVERLAP_CROSSFADE` `O` hesaplarini, (2) `PRESERVE_SILENCE` ve
`HARD_CUT_ZERO_CROSSING` explicit `anull`lerini, (3) `LONG_EDITORIAL_FADE`
`curve=tri`/`ss`/`ns` literalini, (4) filter-script byte hash/length ve
audio-render-plan bindingini, ve (5) `acrossfade`, `asplit`, duplicate label,
float-second fade veya wrong-order mutationlarini fail-closed
`PCM_INPUT_INVALID` olarak kanitlamak zorundadir. Bu oracle olmadan 4B audio
normalization acceptance verilemez.

## 4. Checked-in FullRenderProfileV1 ve toolchain identity

Tek allowed profile kaynagi repository'deki
`renderer-remotion/profiles/full-render-profiles-v1.json` dosyasidir. Bu dosya
canonical JSON'dur; runtime profile uretmez veya environment'tan profile almaz.
4B implementation/admission scope'unda bu catalogla birlikte asagidaki
checked-in provenance fixture'i bulunmak zorundadir:

```text
renderer-remotion/profiles/full-render-profiles-v1.json
tests/fixtures/phase4b/full-render-toolchain-provenance-v1.json
```

Provenance fixture `FULL-RENDER-TOOLCHAIN-PROVENANCE-V1` semasiyla profile
catalog hash'ini, supported platform literalini, Node/Remotion/FFmpeg/FFprobe
identity projection hashlerini, package-lock SHA-256'sini, required local
runtime tree identity'lerini ve fixture'in kendi ID/hash'ini tasir. Profile
catalogu veya fixture runtime tarafindan yazilamaz, indirilemez ya da caller
tarafindan secilemez. Bu iki checked-in belge, profile semantics'in ve kabul
ortaminda kullanilacak toolchain kanitinin tek kaynagidir.

### 4A. Paired runtime ve clean offline REPLAY siniri

Checked-in kaynak dosyalari Node, Remotion veya FFmpeg binary'lerini repository
icine vendoring zorunluluguna sokmaz. Bunun yerine 4B acceptance, yalniz
checked-in provenance fixture ile bire-bir eslesen **paired runtime** uzerinde
calisir. Paired runtime, trusted test/orchestration adapter'ine explicit
`ToolchainRuntimeBindingV1` olarak verilir; request, props, profile, PCM
manifest veya environment'tan turetilmez. Binding tam olarak
`provenance_fixture_id, provenance_fixture_hash, platform, node_root,
remotion_root, ffmpeg_root, ffprobe_root` alanlarini tasir. Dort root yalniz
adapter tarafindan saglanan local absolute paths olabilir; bunlar canonical
request/receipt identity'sine girmez, kalici artifact olarak kaydedilmez ve
child'e argv disinda aktarilmaz. `ToolchainRuntimeBindingV1`deki absolute root,
checked-in repository'nin altina resolve edilmez ve repository-relative
`toolchain_root_relative_posix_path`ten turetilmez. Bu relative deger yalniz
profile/provenance fixture'indeki immutable layout anahtaridir: adapter bu
anahtarin fixture'daki exact degerle eslestigini kanitlar; executable'i ise
yalniz supplied absolute root altinda ilgili `cli_entry_relative_posix_path` /
`executable_relative_posix_path` ile resolve eder. Boylece checked-in layout
provenance'i ile hosta-bagli paired-runtime konumu birbirine karismaz. Adapter
her absolute root'u fixture'daki layout anahtari ve digest/version
projection'lariyla kanitlar;
herhangi bir uyusmazlik, unknown platform veya missing binding
`REMOTION_TOOLCHAIN_UNAVAILABLE` (Node/Remotion) ya da `FFMPEG_UNAVAILABLE`
(FFmpeg/FFprobe) olur.

Bu istisna host discovery degildir: PATH lookup, `where`, glob, package-manager
shim, environment'tan executable secimi ve fallback runtime yasaktir. Bir
clean offline REPLAY, temiz checkout + checked-in profile/provenance/PCM
fixture'lari ve onceden fixture ile eslestirilmis paired runtime ile, hicbir
`npm install`, package download, browser download, URL, DNS, provider veya
network socket kullanmadan calismalidir. Runtime, render ve FFprobe child'lari
allowlisted locale/timezone ile, proxy/registry credentiallari kaldirilmis ve
networku deny eden test sandboxinda baslatilir. Paired runtime yoksa sistem
indirerek veya alternatif toolchain secerek devam etmez; yukaridaki typed
preflight reject'i verir. Acceptance en az bir fresh-worktree offline replay
ve bir network-denial negative oracle'i kanitlamalidir.

Her `FullRenderProfileV1` satiri exact su alanlari tasir:

```text
schema_version, profile_id, profile_hash, remotion_composition_id,
width, height, fps_numerator, fps_denominator, video_codec, pixel_format,
audio_codec, sample_rate_hz, channel_layout, container,
remotion_identity, node_identity, ffmpeg_identity, ffprobe_identity, remotion_render_argv,
ffmpeg_normalize_argv, ffmpeg_mux_encode_argv, ffprobe_argv, stage_timeout_seconds,
probe_expectation
```

`schema_version` `FULL-RENDER-PROFILE-V1`; ID/hash kendi identity alanlari
cikarilmis exact projectiondan hesaplanir. `remotion_identity`, kapali
`toolchain_root_relative_posix_path`, `cli_entry_relative_posix_path`, `cli_entry_sha256`, `normalized_version_line`
ve `version_output_sha256` alanlarini; `node_identity` ise kapali
`toolchain_root_relative_posix_path`, `executable_relative_posix_path`, `executable_sha256`, `normalized_first_version_line` ve `version_output_sha256`
alanlarini tasir. Iki identity'nin hash'i, identity object'inin canonical UTF-8
projection SHA-256 degeridir ve request'teki respective hash ile exact
eslesmelidir. Runtime, absolute binding root altinda resolve edilmis allowlisted
CLI entry'sinin file hash'ini, Remotion `--version` output'unu, Node executable
hash'ini ve Node `--version` output'unu profile'daki beklenen degerlerle process
baslatmadan once aynen kanitlar. PATH'ten baska bir `remotion`/`node` bulmak, host package discovery,
yalniz surum metninin eslesmesi veya lockfile varligi kanit degildir.

`stage_timeout_seconds` profile identity'sinin kapali object'idir; exact olarak
`toolchain_preflight`, `remotion_render`, `ffmpeg_normalize`,
`ffmpeg_mux_encode` ve `ffprobe` anahtarlarini tasir. Her deger canonical JSON
integer'i, `1..3600` araligindadir. Request, environment, CLI, adapter veya
retry bu degerleri override edemez. Bu alan media zamanlamasi degil, yalniz
child-process ust zaman siniridir; props, EDL, PCM manifest, output bytes veya
determinism fingerprint'ine girmez. Ayri bir grace/kill suresi profile'dan
turetilemez: process timeout'unda orchestrator en fazla **5 saniye** graceful
terminate bekler, sonra zorunlu kill ve child-tree reap uygular. Bu sabit,
timeoutun basarili render'a veya publish'e donusmesini engeller.

**Tek profile-oracle'i:** missing/unknown `full_render_profile_id`, catalog
schema/closed-field/profile-ID/profile-hash drift'i, requestteki dort identity
hash'inin profile ile uyusmamasi, profile composition/props clock uyusmazligi,
yasak placeholder/argv veya profile-provenance fixture binding uyusmazligi
tam olarak `FULL_RENDER_PROFILE_INVALID` verir. Bu durumlarda paired runtime
cozulmez ve hicbir process, attempt veya artifact uretilmez. Buna karsilik
gecerli profile/provenance secildikten sonra paired runtime'in yoklugu ya da
actual executable/digest/version kanitinin basarisizligi
`REMOTION_TOOLCHAIN_UNAVAILABLE` veya `FFMPEG_UNAVAILABLE`tir; bu ayrim profile
invalid hatasini runtime availability hatasiyla karistirmayi yasaklar.

`ffmpeg_identity` ve `ffprobe_identity` de kapali olarak kendi
`toolchain_root_relative_posix_path`, `executable_relative_posix_path`,
`executable_sha256`, `normalized_first_version_line` ve `version_output_sha256`
alanlarini tasir. Her `toolchain_root_relative_posix_path` repository layout
anahtaridir: bos, absolute, drive/UNC, `.`/`..`, backslash veya NUL yasaktir;
catalog ve provenance fixture'da exact eslesmelidir. Bu anahtar host dosya
sisteminde repository root'a join edilmez, runtime discovery yapmaz ve paired
runtime'in absolute root'unu secmez. Her CLI/executable relative path kendi
selected **absolute binding root**una gore ayni kapali grameri izler; lexical
join ve handle/realpath sonrasi yeniden containment ile bu root disina resolve
olamaz. Absolute root, ara dizinler, CLI entry ve executable dahil secilen
zincirin hicbir elemani symlink, Windows reparse point veya regular-file
olmayan nesne olamaz. Directory scan, glob, PATH lookup, host package discovery,
package-manager shim (`.cmd`, `.bat`, shell wrapper) veya version metnine gore
alternatif binary secimi yasaktir.
Kanittan herhangi biri basarisizsa hicbir render/artifact/attempt kaydi
uretilmeden `REMOTION_TOOLCHAIN_UNAVAILABLE` typed preflight reject'i doner.

Runtime, resolved exact FFmpeg ve FFprobe regular-file executable'larinin
checked-in binary digest ve respective `-version` output digestini aynen
kanitlayamazsa `FFMPEG_UNAVAILABLE` ile reddeder; yalniz `ffmpeg`/`ffprobe`
PATH adinin bulunmasi yeterli degildir.

Her dort argv alani shell-string degil, kapali ASCII token dizisidir ve
executable tokeni tasimaz. Invoker executable secemez veya argv'den executable
devralamaz: Remotion render/version cagrisi tam olarak verified
`[resolved_node_executable, resolved_remotion_cli_entry, ...profile remotion tokens]`
ile; normalize/mux FFmpeg ve FFprobe cagrilari ise tam olarak sirayla
`[resolved_ffmpeg_executable, ...profile ffmpeg tokens]` ve
`[resolved_ffprobe_executable, ...profile ffprobe tokens]` ile baslatilir.
Bu dort resolved path preflight sonrasinda immutable attempt-local invocation
binding'e yazilir ve child spawn, retry veya recovery bunlardan farkli bir
programi cagirmaz. Shell, `cmd`, `powershell`, `env`, launcher, extension
association veya relative current-working-directory executable resolutioni
kullanilamaz.
Sadece `{RENDER_PROPS_JSON}`, `{INPUT_VIDEO}`, `{PCM_INPUT_ARGUMENTS}`,
`{AUDIO_FILTER_SCRIPT}`,
`{NORMALIZED_AUDIO}`, `{STAGED_OUTPUT}` ve `{PROBE_JSON}` typed
placeholder'lari kullanilir. `{RENDER_PROPS_JSON}` yalniz Remotion argv'sinde,
`{PCM_INPUT_ARGUMENTS}` ve `{AUDIO_FILTER_SCRIPT}` yalniz normalize argv'sinde;
diger placeholder'lar yalniz
anlamli sonraki process asamasinda birer kez bulunabilir. Bir placeholder tek
bir complete trusted path argument'ine expansion olur; yalniz
`{PCM_INPUT_ARGUMENTS}` istisnadir ve resolver raporunun hash-bound, slot
sirasindaki `-i` / complete trusted relative path token ciftlerine expand olur.
Token birlestirme, filter injection, caller argumani, network input, host font discovery veya
implicit codec defaultu yasaktir. `probe_expectation` container, tam video/audio codec,
pixel format, fps rational, stream count, `48000` sample rate, stereo layout ve
duration toleransini kapali olarak tasir. Profile props'un width/height/FPS/
composition ve PCM manifestinin audio clock degerleriyle exact eslesmelidir;
aksi `FULL_RENDER_PROFILE_INVALID`tir.

## 5. Gercek render/probe sirasi

1. Envelope, 4A props, profile, request'teki Node/Remotion identity binding'i,
   output target kaydi ve PCM manifest/resolver tamamen dogrulanir. Node ve
   Remotion preflight'i profile'daki exact executable/CLI hash ve version-output
   digestleriyle process/artifact/attempt kaydindan once tamamlanir; sonucu
   immutable `FULL-RENDER-TOOLCHAIN-PREFLIGHT-V1` projection'i olarak receipt'e
   baglanir.
2. Remotion, profile'daki locked composition'i `{RENDER_PROPS_JSON}` ile exact
   `duration_frames` boyunca attempt sandbox'indaki `{INPUT_VIDEO}` hedefi icin
   render eder.
3. FFmpeg yalniz profile normalize argv'siyle hash-bound PCM inputs ve exact
   `{AUDIO_FILTER_SCRIPT}` artifact'inden normalized audio intermediate'ini
   uretir; EDL'nin sample araliklarini, gainini, boundary kararini veya mix
   kapsamini degistiremez.
4. FFmpeg yalniz profile mux/encode argv'siyle staged final output'u uretir.
5. FFprobe profile argv'siyle staged output'u probe eder; expectation'in her
   alani exact eslesmeden `FINAL_PROBE_INVALID` olur.

Subprocess invocation executable + argv array ile, closed stdin, explicit
timeout, bounded sanitized capture ve minimal allowlisted environment ile
yapilir. Raw stderr, local path veya credential receipt/manifest'e yazilmaz;
yalniz sanitized byte digestleri yazilir. Herhangi bir nonzero/timeout sirayla
typed render failure'a doner; partial video, mute audio veya success fallback'i
yasaktir.

### 5A. Closed child-stage timeout ve nonzero oracle tablosu

Her child, yalniz profile'daki ilgili `stage_timeout_seconds` degeriyle
calisir. `timeout`, deadline'a kadar tamamlanmama; `nonzero`, child'in normal
tamamlanip exit status'unun sifir olmamasidir. Ikisi ayni typed outcome'a
haritalanir. Raw exit status, signal, stderr veya host path receipt, registry,
manifest ya da public hata cevabina yazilmaz; yalniz stage adi, `TIMEOUT` veya
`NONZERO` closed sonuc turu ve sanitized capture digest'i attempt-local cleanup
kanitinda tutulabilir. Tablo disinda stage, timeout veya nonzero kodu yoktur:

| Kapali stage | Timeout budget | `TIMEOUT` veya `NONZERO` typed sonucu | Zero-exit sonrasi zorunlu kontrol | Kontrol basarisizligi |
|---|---:|---|---|---|
| Node version preflight | `toolchain_preflight` | `REMOTION_TOOLCHAIN_UNAVAILABLE` | exact executable + version digest | `REMOTION_TOOLCHAIN_UNAVAILABLE` |
| Remotion CLI version preflight | `toolchain_preflight` | `REMOTION_TOOLCHAIN_UNAVAILABLE` | exact CLI entry + version digest | `REMOTION_TOOLCHAIN_UNAVAILABLE` |
| FFmpeg version preflight | `toolchain_preflight` | `FFMPEG_UNAVAILABLE` | exact executable + version digest | `FFMPEG_UNAVAILABLE` |
| FFprobe version preflight | `toolchain_preflight` | `FFMPEG_UNAVAILABLE` | exact executable + version digest | `FFMPEG_UNAVAILABLE` |
| Remotion full render | `remotion_render` | `REMOTION_FULL_RENDER_FAILED` | regular, nonempty `{INPUT_VIDEO}` ve exact attempt containment | `REMOTION_FULL_RENDER_FAILED` |
| FFmpeg PCM normalize | `ffmpeg_normalize` | `FFMPEG_NORMALIZE_FAILED` | regular, nonempty `{NORMALIZED_AUDIO}` ve canonical PCM expectation | `FFMPEG_NORMALIZE_FAILED` |
| FFmpeg mux/encode | `ffmpeg_mux_encode` | `FFMPEG_MUX_FAILED` | regular, nonempty `{STAGED_OUTPUT}`, exact attempt containment ve pre-probe staged-output hash | `FINAL_ENCODE_FAILED` |
| FFprobe final probe | `ffprobe` | `FINAL_PROBE_INVALID` | closed `probe_expectation`in her alani | `FINAL_PROBE_INVALID` |

`FINAL_ENCODE_FAILED` yalniz mux/encode child'i sifirla ciktiktan sonra staged
outputun olusmamasi, regular/nonempty olmamasi, sandbox disina cikmasi veya
pre-probe hashinin hesaplanamamasi icin kullanilir; bir child nonzero/timeout
kodu degildir. `FFMPEG_MUX_FAILED` ise yalniz ayni mux/encode child'inin
timeout/nonzero sonucudur. Boylece iki kod ayni hata sinifini iki farkli
mekanizma icin paylasmaz. Preflight satirlarinda failure pre-admission reject
oldugu icin attempt, artifact, registry revision veya terminal receipt
uretilmez; diger satirlar admitted lifecycle'i cleanup, receipt ve terminal
status kurallariyla fail-closed tamamlar. Parent cancellation timeout degildir:
yalniz Bolum 6'daki `CANCELLED_BY_PARENT` yolu kullanilir ve bu tablodaki
failure kodlarindan birine cevrilemez.

## 6. Kalici append-only registry ve output target semantics

Registry somut olarak proje rootundaki asagidaki dosyalardan olusur:

```text
artifacts/registry.jsonl
artifacts/output-targets.jsonl
artifacts/transactions/<transaction_id>.json
```

`registry.jsonl` ve `output-targets.jsonl` UTF-8 LF-delimited canonical JSON
record journal'leridir; onceki satir in-place degistirilemez veya silinemez.
Her mutable gorunen durum yeni bir revision record'udur ve onceki record ID/hash
ile baglanir. Tek writer, attempt-local olmayan exact registry lock ile serial
calisir. Bir transaction once `transactions/...` altinda complete canonical
prepare journal olarak write+flush edilir; artifact bytes ve staged output hash
ile dogrulandiktan sonra lock altinda her yeni JSONL satiri append+flush edilir;
en son committed transaction marker'i append edilir. Recovery yalniz complete
journal + append marker kombiniyle idempotent devam eder, scan/heuristic ile
registry uydurmaz.

Her publish transaction journal'i exact base `OUTPUT-TARGET-RECORD-V1`
ID/hash/revision'ini (ilk publish icin current-null head'i), beklenen sonraki
revision'i, old/current artifact+hash ciftini, staged output artifact+hash'ini,
atomic filesystem action'ini ve durable transition marker'larini tasir. Target
head'i lock altinda bu base ile exact eslesmeden transaction devam edemez;
eslesmezse hicbir publish/revision yazmadan `OUTPUT_TARGET_CONFLICT` ile
reddedilir. Bu, stale reservation'in yeni bir target dalini sessizce append
etmesini engeller.

Yalniz `ADMITTED` bir FULL attempt kalici artifact kaydi uretebilir;
pre-admission rejection hicbir attempt, artifact veya registry kaydi uretmez.
Her admitted attempt icin request, props, PCM manifest, cleanup report ve
terminal receipt ayri `ArtifactRecord` olur. Renderer video, normalized audio,
staged output ve probe report ancak ilgili adim basariyla uretildiyse ayri
`ArtifactRecord` olur. Final-output artifacti ve onu target'a baglayan
`OUTPUT-TARGET-RECORD-V1`, success transaction'i tamamlanana kadar yalniz
attempt transaction journal'inin **provisional** kayitlaridir: genel artifact
reader'i, output API'si veya latest-output resolver'i bunlari goremez. Bu iki
provisional kaydin registry/target journal'ine gorunur ve birlikte baglayici
olmasi yalniz exact success marker'i olan immutable `SUCCEEDED` receipt
transaction marker'inin `append+flush`i ile olur. `FAILED` veya `CANCELLED`
attempt final-output artifacti, successful target revision'i ya da success
marker'i append edemez. Publish sonrasi hata/cancellation sebebiyle daha once
durable hale gelmis provisional target revision'i varsa, bunun tek istisnasi
yeni outputu gorunur kilmayan zorunlu compensation revision'idir; bu revision
old current (veya ilk publish rollback'inde null current) durumunu geri getirir
ve success marker'i yerine terminal failure/cancellation kanitina baglanir.
Mevcut Faz 1 semasinin zorunlu stable
artifact ID, content hash, size, producer/version, project/sequence, dependency
IDs, retention, lock/pin/approved, status ve lineage alanlari kullanilir. Batch
graph validation ile ayni transactionda bulunan tum dependency ID'leri
dogrulanmadan success kaydi yazilamaz.

`output_target_id`, `output-targets.jsonl` icindeki project/sequence-bound
logical target kaydini resolve eder; request asla filesystem targeti tasimaz.
Her satir exact `OUTPUT-TARGET-RECORD-V1` object'tir ve baska alan tasimaz:

```text
schema_version, output_target_record_id, output_target_record_hash,
output_target_id, revision, previous_output_target_record_id,
previous_output_target_record_hash, project_id, sequence_id,
trusted_publish_relative_path, current_output_artifact_id,
current_output_content_sha256, replacement_policy, locked, approved
```

`schema_version` exact `OUTPUT-TARGET-RECORD-V1` literalidir. Record ID/hash,
yalniz `output_target_record_id` ve `output_target_record_hash` cikarilmis
canonical projectiondan hesaplanir; ID `outr_<digest[0:32]>`, hash
`sha256:<64-lower-hex>` olur. Ilk revision `revision = 1` ve iki
`previous_*` alanini JSON `null` tasir. Sonraki revision, `revision`i tam bir
arttirir ve onceki satirin exact ID/hash'ini tasir; `output_target_id`,
`project_id`, `sequence_id`, `trusted_publish_relative_path`, `locked` ve
`approved` tum zincir boyunca degismez. FULL publish/replacement ve
compensation revision'i base head'in `locked`/`approved` degerlerini ayni
booleanlarla kopyalamak zorundadir; bu alanlar output writer tarafindan
degistirilebilen policy gecisleri degildir. Bu zincirin kirik, fork'lu, baska
target'a bagli veya bu immutable alanlari degistiren bir revision icermesi
`ARTIFACT_PERSIST_FAILED`dir.

`trusted_publish_relative_path`, yalniz target kaydini olusturan trusted
orchestration tarafindan belirlenen, project root'a gore relative POSIX
path'tir. Bos, absolute, drive/UNC, `.` veya `..` segmentli, backslash'li,
NUL tasiyan ya da project root disina resolve olan deger yasaktir. Runtime bu
tek degeri project root'a resolve eder, containment'i her publish ve restore
oncesinde tekrar kanitlar; caller, profile, props veya child process bu path'i
veremez ya da degistiremez.

Ilk publish edilebilir target revisioninda
`current_output_artifact_id` ve `current_output_content_sha256` ikisi de JSON
`null` olur; bu yol replacement degildir ve `replacement_policy` exact JSON
`null` olur. Replacement hedefinde iki `current_output_*` alani da non-null,
birbirine ait accepted final-output `ArtifactRecord` ID/hash'i olur ve
`replacement_policy` yalniz exact `REPLACE_UNAPPROVED_V1` literalidir.
Karismis null/non-null cift, current artifact/hash uyusmazligi veya baska bir
policy `OVERWRITE_POLICY_INVALID`tir. Basarili ilk publish, current-null
revisiondan yeni outputu current yapan bir sonraki append-only revisionla;
basarili replacement ise eski current ID/hash'i yeni final-output lineage'ina
baglayan bir sonraki revisionla tamamlanir.

`TARGET_REVISION_APPENDED`, atomic filesystem publish'in ve exact output
hash/probe dogrulamasinin ardindan, tek-writer lock altinda resulting
`OUTPUT-TARGET-RECORD-V1` satirinin `append+flush` edilmesidir. Bu event,
yalniz transaction journal'indeki **provisional target head** icin tek
linearization noktasi olur: bir transaction ayni target icin tam bir resulting
revision append edebilir; revision ancak journal'daki exact base head'den
`base.revision + 1` olabilir. `TARGET_REVISION_APPENDED`den once yeni output
nominal/current output degildir. Append edilmis revision da public current
degildir; public current output ancak ayni transactiondaki final-output
artifact kaydi, exact target revision ve immutable `SUCCEEDED` receipt success
marker'inin ucunun de `append+flush` edilip birlikte durable olmasiyla tek
atomik gorunurluk aninda degisir. Bu an, target'in old logical generation'dan
new logical generation'a **tek public linearization noktasi**dir. Bu ana kadar
onceki successful revision public current kalir. Failure/cancellation bu
success marker'ini append edemez ve provisional revision'i publiclestiremez;
gerekirse yalniz compensation revision'i append eder. Bu event ve success
marker'i durable olmadan `SUCCEEDED`, success receipt veya output API response
yazilamaz.

Filesystem publish path'i internal implementation detaildir. Tum reader,
exporter ve Studio adapter'lari output'u yalniz latest successful receipt'e
exact bagli append-only target revisionini resolve ederek, kaydin artifact
ID/hash'i ile path bytes'ini yeniden dogrulayarak gorur; target path'i directory
scan, tahmin edilen path veya staging referansi ile dogrudan okunamaz/serve
edilemez. Dolayisiyla atomic rename ile terminal success arasindaki fiziksel
pencere yeni output'u logical olarak gorunur yapmaz; onceki successful record
current kalir. Staging, restore
staging ve attempt rootlari hicbir reader tarafindan publishable output olarak
gorunmez. Hash/record/path uyusmazligi `ARTIFACT_PERSIST_FAILED`dir ve hicbir
output gorunurlugu vermez.

`locked` ve `approved` boolean'dir. Current target `locked=true` ise `approved`
degerinden bagimsiz olarak mutasyon mutlak `OUTPUT_LOCKED` olur. Ancak
`locked=false` ve `approved=true` ise mutasyon mutlak `OUTPUT_APPROVED` olur.
Yalniz `locked=false`, `approved=false`, non-null current ve exact
`REPLACE_UNAPPROVED_V1` policy allowed replacement olabilir. Target once
reservation altina alinir; staging-to-target publish atomiktir.

## 7. Publish, cleanup ve compensation state machine

Bir admitted attemptin kalici state machine'i kapali olarak sunlardir. Her
terminal yolun immutable receipt'i, cleanup/compensation, `POST_CLEANUP`
manifesti ve cleanup reportu tamamlanmadan once yazilamaz:

```text
ADMITTED -> RENDERED -> AUDIO_NORMALIZED -> MUXED -> PROBED
-> REGISTRY_PREPARED -> PUBLISH_INTENT_RECORDED -> PUBLISHED
-> TARGET_REVISION_APPENDED
-> PRE_CLEANUP_MANIFEST_COMMITTED -> CLEANING -> CLEANED
-> POST_CLEANUP_MANIFEST_COMMITTED -> CLEANUP_REPORT_COMMITTED
-> RECEIPT_COMMITTED -> SUCCEEDED
```

Hata ve cancellation icin exact terminal state siralari asagidadir. Hata
`PUBLISHED`den once olursa ilk satir, `PUBLISHED`den sonra olursa ikinci satir
kullanilir; ikisi de immutable receipt commitinden once biter:

```text
ADMITTED -> ... -> PRE_CLEANUP_MANIFEST_COMMITTED -> COMPENSATING -> CLEANED
-> POST_CLEANUP_MANIFEST_COMMITTED -> CLEANUP_REPORT_COMMITTED
-> RECEIPT_COMMITTED -> FAILED

ADMITTED -> ... -> PUBLISHED -> TARGET_REVISION_APPENDED
-> PRE_CLEANUP_MANIFEST_COMMITTED -> COMPENSATING
-> TARGET_COMPENSATION_REVISION_APPENDED -> CLEANED -> POST_CLEANUP_MANIFEST_COMMITTED
-> CLEANUP_REPORT_COMMITTED -> RECEIPT_COMMITTED -> FAILED

ADMITTED -> ... -> PRE_CLEANUP_MANIFEST_COMMITTED -> COMPENSATING -> CLEANED
-> POST_CLEANUP_MANIFEST_COMMITTED -> CLEANUP_REPORT_COMMITTED
-> RECEIPT_COMMITTED -> CANCELLED

ADMITTED -> ... -> PUBLISHED -> TARGET_REVISION_APPENDED
-> PRE_CLEANUP_MANIFEST_COMMITTED -> COMPENSATING
-> TARGET_COMPENSATION_REVISION_APPENDED -> CLEANED -> POST_CLEANUP_MANIFEST_COMMITTED
-> CLEANUP_REPORT_COMMITTED -> RECEIPT_COMMITTED -> CANCELLED
```

`PUBLISH_INTENT_RECORDED`, eski target identity'sini (ve varsa restore staging
referansini), yeni staged output hash'ini ve transaction ID'yi append-only
journal'a kalici olarak yazar. Atomic publish basarisizsa target degismez.
Publish sonrasi registry veya receipt commitine kadar gorulen hata,
`COMPENSATING` ile onceki targeti atomik restore eder; onceki target yoksa yeni
target only exact attempt output ise kaldirir. Eger
`TARGET_REVISION_APPENDED` coktan durable ise restore/kaldirma tek basina yeterli
degildir: `TARGET_COMPENSATION_REVISION_APPENDED`, bir sonraki append-only
revision olarak old current artifact/hash ciftini tekrar current yapar; ilk
publish rollback'inde ise ikisini de JSON `null` ve policy'yi JSON `null` yapan
sonraki revision append edilir. Bu compensation revision'i exact failed/cancelled
transaction journal'ina ve restore proofuna baglanir; in-place rollback,
satir silme veya old revision'i yeniden yazma yasaktir.

Crash recovery, yalniz durable journal marker'lari ve journal'da adlari/hashleri
verilen exact target/staging dosyalariyla karar verir: (a) publish yoksa staged
output temizlenir, (b) publish var ama `TARGET_REVISION_APPENDED` yoksa old
target restore edilir ve `RECOVERY_COMPENSATION_RECORDED` append marker'i
yazilir, (c) target revision append edilmis ama terminal receipt yoksa old
target restore edilir ve zorunlu `TARGET_COMPENSATION_REVISION_APPENDED` yazilir
ve attempt `FAILED` terminal cleanup yoluna tamamlanir. Recovery directory scan,
mtime, dosya adi tahmini veya 'hangi output daha yeni' heuristigi kullanamaz.
Restore/kaldirma sonucunu cleanup report artifacti ve append-only transaction
recovery record'u tasir. Compensation da kanitlanamazsa `SUCCEEDED` yazilmaz;
recovery tamamlanana kadar target yeni accepted output diye sunulmaz. Basarisiz
compensation/cleanup da actual kalan dosya setini `POST_CLEANUP` manifesti ve
cleanup reportunda kanitlar, ardindan ancak `FAILED` receipt yazabilir.

Her admitted attempt iki state-specific, immutable envanter kaniti tasir:
`FULL-ATTEMPT-MANIFEST-V1` `PRE_CLEANUP` ve `POST_CLEANUP`. Her manifest tam
olarak `schema_version,manifest_id,manifest_hash,attempt_id,cleanup_state,files`
alanlarini tasir. `cleanup_state` sadece bu iki literalden biridir; `files`,
relative POSIX path, artifact ID, byte length, content SHA-256 ve retention
class satirlarindan lexical path sirasiyla olusur. Manifest hash/ID kendi iki
identity alani cikarilmis projectiondan hesaplanir.

`PRE_CLEANUP`, terminal materialization durduktan sonra cleanup baslamadan once
actual attempt rootunun eksiksiz dosya setine exact equality ile baglanir ve
`PRE_CLEANUP_MANIFEST_COMMITTED` durumunda immutable hale gelir. `POST_CLEANUP`,
cleanup/compensation tamamlandiktan sonra actual attempt rootunun kalan dosya
setine ayni exact-equality kuralıyla baglanir ve
`POST_CLEANUP_MANIFEST_COMMITTED` durumunda immutable hale gelir. Kayitsiz ekstra dosya, eksik
satir, symlink escape veya hash drift iki durumda da fail-closed'dur. Bu kural
renderer temp dosyalari dahil attempt rootunda kalan tum dosyalara uygulanir.
`FULL-CLEANUP-REPORT-V1` ayri bir registry artifactidir ve attempt rootunda
degildir; `pre_cleanup_manifest_id/hash`, `post_cleanup_manifest_id/hash`,
silinen/tutulan/compensation ile restore edilen exact artifact ID/hashleri ile
cleanup kararlarini tasir.

Cleanup yalniz `PRE_CLEANUP.files` satirlarindaki attempt-local artifactlere ve
retention kararina gore calisir; `POST_CLEANUP.files`, gercekte kalan satirlar
olmadan yazilamaz. `FULL-CLEANUP-REPORT-V1`, iki immutable manifest yazildiktan
sonra `CLEANUP_REPORT_COMMITTED` durumunda yazilir; immutable terminal receipt
bu rapordan once yazilamaz. Glob, age-based broad delete, baska attempt/project
dosyasi veya locked/pinned artifact silme yasaktir. `CLEANUP_FAILED` bir success
receipt uretmez.

## 8. Cancellation ingress ve process kurallari

Preflight, envelope ve trusted ingress handle'ini artifact/lock/process
olusturmadan validate eder. Bu preflight sonrasinda fakat `ADMITTED` transition
oncesinde gorulen parent cancellation, exact
`CANCELLED_BEFORE_ADMISSION` typed ingress rejection olarak doner. Bu bir
attempt state'i veya terminal receipt degildir: attempt ID, artifact, registry
revision, cleanup manifest/report ya da output reservation uretmez.

Yalniz `ADMITTED` transitionindan sonra trusted `cancellation_ingress_id`
parent cancellation'i `CANCELLED_BY_PARENT` ile `CANCELLED` terminal
lifecycle'ina sokabilir; bu yol zorunlu olarak
`PRE_CLEANUP_MANIFEST_COMMITTED -> COMPENSATING -> CLEANED ->
POST_CLEANUP_MANIFEST_COMMITTED -> CLEANUP_REPORT_COMMITTED ->
RECEIPT_COMMITTED -> CANCELLED` sirasini (publish olduysa ayni siradan once
`PUBLISHED -> TARGET_REVISION_APPENDED -> TARGET_COMPENSATION_REVISION_APPENDED`)
izler. Child veya FFmpeg
stdout'u cancellation isteyemez. Invalid envelope preflight'ta her zaman
`FULL_REQUEST_INVALID`tir; cancellation bunu maskeleyemez.

Orchestrator cancellation'i process baslatmadan hemen once ve her process
siniri oncesi kontrol eder. Process calisiyorsa kapali timeoutlu graceful
terminate, ardindan zorunlu kill uygular; child tree beklenmeden publish'e
gecilemez. Cancellation `TARGET_REVISION_APPENDED` linearization noktasindan
once geldiyse publish yasaktir; fiziksel `PUBLISHED` olmus fakat target revision
append edilmemisse old target restore edilir, ancak compensation revision
uretilmez. Cancellation target revision append edildikten fakat
`RECEIPT_COMMITTED -> SUCCEEDED` tamamlanmadan gelirse zorunlu compensation
revision'iyle `CANCELLED` olur. Success receipt commitinden sonra cancellation
success'i geriye donuk `CANCELLED` yapamaz; parent'a terminal success sonucu
verilir. Bu race receipt ve cleanup reportunda monotonic transition olarak
kayitlidir.

## 9. Receipt, hata oracle'i ve status/DAG

Terminal status kapali set `SUCCEEDED`, `FAILED`, `CANCELLED`dir. `SUCCEEDED`
yalniz final output, successful probe, append-only registry transaction,
published target, immutable PRE/POST cleanup manifestleri ve cleanup reportu
tamamlanip `RECEIPT_COMMITTED` olduktan sonra yazilir. `FAILED` ve `CANCELLED`
de ayni immutable cleanup kanitlari tamamlanip `RECEIPT_COMMITTED` olduktan
sonra yazilir.
`FAILED`/`CANCELLED` final output artifacti veya nominal output identity'si
tasimaz. Receipt canonical JSON'dur; ID/hash kendi identity alanlari cikarilmis
projectiondan hesaplanir ve request/profile/toolchain/target/probe/cleanup
lineage'ini exact baglar. Receipt'in `toolchain_preflight` alani exact
`FULL-RENDER-TOOLCHAIN-PREFLIGHT-V1` object'idir:

```text
schema_version, toolchain_preflight_id, toolchain_preflight_hash,
full_render_profile_id, full_render_profile_hash, remotion_identity_hash,
node_identity_hash, remotion_cli_entry_sha256, remotion_version_output_sha256,
node_executable_sha256, node_version_output_sha256,
ffmpeg_identity_hash, ffmpeg_executable_sha256, ffmpeg_version_output_sha256,
ffprobe_identity_hash, ffprobe_executable_sha256, ffprobe_version_output_sha256
```

ID/hash kendi iki identity alani cikarilmis canonical projectiondan hesaplanir.
Preflight record'un profile/request binding'leri ve observed executable/version
digestleri exact eslesmeden admitted attempt veya terminal receipt yazilamaz.
Preflight, profile'daki kapali relative root/path secimlerinin resolved
containment/no-symlink kanitini da bu digest binding'leriyle birlikte tamamlar;
aksi ilgili toolchain typed preflight reddidir.
Pre-admission `REMOTION_TOOLCHAIN_UNAVAILABLE` response'u receipt/attempt/artifact
olusturmaz; admitted receipt'teki record ise calisan exact Node/Remotion
toolchain'ini denetlenebilir bicimde sabitler.

En az su closed typed kodlar tanimlanir ve negatif test edilir:

```text
FULL_REQUEST_INVALID
PCM_INPUT_INVALID
FULL_RENDER_PROFILE_INVALID
FFMPEG_UNAVAILABLE
REMOTION_TOOLCHAIN_UNAVAILABLE
REMOTION_FULL_RENDER_FAILED
FFMPEG_NORMALIZE_FAILED
FFMPEG_MUX_FAILED
FINAL_ENCODE_FAILED
FINAL_PROBE_INVALID
ARTIFACT_PERSIST_FAILED
OUTPUT_LOCKED
OUTPUT_APPROVED
OVERWRITE_POLICY_INVALID
OUTPUT_TARGET_CONFLICT
ATOMIC_PUBLISH_FAILED
CLEANUP_FAILED
CANCELLED_BEFORE_ADMISSION
CANCELLED_BY_PARENT
```

`SUCCEEDED`de failure code JSON `null`; `FAILED`de `CANCELLED_BY_PARENT` disinda
tam bir closed literal; `CANCELLED`de tam `CANCELLED_BY_PARENT` olur. Her hata
fail-closed'dur: fallback video, mute audio, partial output veya nominal success
receipt yasaktir. `CANCELLED_BEFORE_ADMISSION` yalniz ingress response kodudur;
receiptte, artifact registry'de veya terminal status olarak kullanilamaz.

## 10. Kabul kaniti

REPLAY-only implementation kaniti en az sunlari gosterir:

1. Faz 4A preview byte/identity regression'i degismez; FULL envelope 4A props'u
   mutate edemez.
2. Tamper, stale lineage, raw path/argv ve PCM manifest hash drift'i kendi
   closed oracle'i ile; unknown/profile-hash/identity/argv/provenance drift'i
   `FULL_RENDER_PROFILE_INVALID` ile; Node/Remotion executable veya
   version-identity drift'i ise `REMOTION_TOOLCHAIN_UNAVAILABLE` ile
   process/artifact uretmeden typed red verir.
3. Checked-in profile ile gercek full sequence render, normalized PCM, FFmpeg
   mux/encode ve ffprobe exact expectation kanitlanir; canonical
   `AudioRenderPlan`/filter-scriptin her A1-A5 clip, trim/delay/gain/boundary
   ve mix binding'i Audio EDL ile bire-bir kanitlanir.
4. Iki isolated run, declared deterministic fingerprint setini verir ve
   birbirinin targetini overwrite etmez.
5. Success/failure/admitted-cancellation icin append-only registry revisionlari,
   DAG, receipt, cleanup reportu ile PRE/POST cleanup manifestlerinin kendi
   state-specific exact output equalitysi kanitlanir.
6. Locked/approved target mutasyonsuz reddedilir; allowed replacement atomic
   publish ile eski/yeni lineage ve compensation proofu verir.
   Initial target head, render attempt'inden once trusted provisioning owner
   tarafindan ayni registry lock altinda atomik olusturulur; runtime'in eksik
   targeti bootstrap etmedigi, subsequent/replacement/compensation
   revisionlarinin `locked` ve `approved` booleanlarini korudugu ve drift'in
   `ARTIFACT_PERSIST_FAILED` oldugu negatif/pozitif fixture kaniti ile gosterilir.
7. Pre-admission cancellation attempt/artifact/receipt yaratmadan
   `CANCELLED_BEFORE_ADMISSION` verir; admitted cancellation process/publish
   race'inde partial output ve orphan temp birakmadan `CANCELLED` terminal
   sonucu ve PRE/POST cleanup kaniti verir.
8. V2 regression, clean offline paired-runtime REPLAY ve no-network/no-provider
   gate'i calisir; network-denial altinda hicbir download veya fallback runtime
   secimi olmaz.

## 11. Yetki siniri

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
