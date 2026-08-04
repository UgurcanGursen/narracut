# Faz 3B — 48 kHz Audio Sample Grid ve Boundary Planı Sözleşmesi

> Durum: Aday spesifikasyon — uygulama yetkisi değildir
> Kapsam: Faz 3B ses-zamanlama ve boundary-planı
> Önkoşul: Kabul edilmiş Faz 3A `VIDEO-EDL-V1` ve Faz 2 zamanlama
> sözleşmeleri
> Hariç: medya sağlayıcısı/ağ, asset katalogu, source-audio güvenlik kararı,
> Remotion, FFmpeg mux/encode, kalıcı artifact lifecycle ve Faz 11 mix
> direction

## 1. Amaç ve sınır

Bu paket, bir sequence’in A1–A5 ses kararlarını video EDL’den **ayrı**, 48,000
Hz sample grid üzerinde deterministik bir plan artifact’ine derler. Video
frame-grid hiçbir zaman ses zamanı için yuvarlama otoritesi değildir. Buna
karşılık plan, aynı sequence-local süreye ve video EDL kimliğine sıkı
bağlanarak A/V ilişkisinin ölçülebilir kalmasını sağlar.

Bu sözleşme ses decode etmez, DSP uygulamaz, dosya indirmez, process/thread
başlatmaz, FFmpeg/Remotion çağırmaz ve çıktı medyası üretmez. `AudioArtifact`
yalnız A1 narration için kabul edilmiş upstream kimlik/metadata kanıtıdır;
A2–A5 gerçek asset çözümü Faz 8, source-speech suitability/contamination kararı
Faz 11’dedir. Bu nedenle bütün kabul kanıtı küçük, checked-in PCM REPLAY
fixture’larıyla yürür; hiçbir ticari API veya production medya gerekmez.

Bu paket, Faz 3A `VideoEdlArtifact` byte’larını değiştirmez, video event
zamanını yeniden hesaplamaz ve `TimelineTrack` enum’una yeni değer eklemez.
Faz 4 yalnız kabul edilmiş video ve audio plan byte’larını tüketebilir; ses
event’ini yeniden sıralayamaz veya boundary politikasını yorumlayıp değiştiremez.

## 2. Sabitler, public yüzey ve model sırası

Uygulama dosyası yalnız `engine/contracts/audio_edl.py` olacaktır. Onun ve
`engine/contracts.__init__` public export kümesi tam olarak aşağıdakidir:

```text
AUDIO_EDL_V1
AUDIO_EDL_HASH_V1
AUDIO_SAMPLE_CLOCK_V1
INTERNAL_AUDIO_SAMPLE_RATE_HZ
INTERNAL_AUDIO_CHANNEL_COUNT
InternalPcmFormat
AudioTrackRole
AudioEventKind
AudioBoundaryPolicy
AudioTransitionKind
AudioBoundaryPosition
AudioCueWordRange
AudioCueSampleRange
ReplayPcmSource
ReplayPcmEvidence
AudioPlacementIntent
AudioBoundaryIntent
AudioPlannedSilence
AudioBoundaryDecision
EdlAudioEvent
AudioEdlTrack
AudioEdlArtifact
AudioEdlRejectionReason
AudioEdlContractError
compile_audio_edl
plan_audio_boundaries
load_audio_edl
serialize_audio_edl
```

Literal değerler sırasıyla `AUDIO-EDL-V1`, `AUDIO-EDL-HASH-V1`,
`AUDIO-SAMPLE-CLOCK-48KHZ-V1`, `48000`, `2` olur. Internal PCM yalnız
`PCM_F32LE` veya `PCM_S24LE` olabilir; ikisi de interleaved stereo 48 kHz’tir.
Ara pipeline’da MP3/AAC, tekrar lossy encode veya concatenate yasaktır.

Enumlar kapalı ve aşağıdaki sıra/değerle serialize edilir:

```text
AudioTrackRole: A1="A1", A2="A2", A3="A3", A4="A4", A5="A5"
AudioEventKind: NARRATION, BGM, SFX, SOURCE_SPEECH, AMBIENCE
AudioBoundaryPolicy: ZERO_CROSSING_MICROFADE, OVERLAP_CROSSFADE,
                     PRESERVE_SILENCE, HARD_CUT_ZERO_CROSSING,
                     LONG_EDITORIAL_FADE
AudioTransitionKind: NONE, FADE_IN, FADE_OUT, CROSSFADE
AudioBoundaryPosition: LEADING, BETWEEN_EVENTS, TRAILING
```

Yukarıdaki enum adları değerlerinin kendisidir: `InternalPcmFormat.PCM_F32LE`
`"PCM_F32LE"`, `InternalPcmFormat.PCM_S24LE` `"PCM_S24LE"` olur; aynı
biçimde her `AudioEventKind`, `AudioBoundaryPolicy`, `AudioTransitionKind` ve
`AudioBoundaryPosition` üyesi yukarıdaki büyük-harf literalinin aynı string
değeriyle serialize edilir. `Enum.auto()`, display adı, ordinal veya
case-normalisation kabul edilmez.

`AudioTrackRole` yalnız A1–A5’den oluşur ve Faz 3A’daki `TimelineTrack` ile
aynı string değerini taşır. A1 sırası narration, A2 BGM, A3 SFX, A4 source
speech, A5 ambience’tir; başka “master” veya gizli track yoktur. `AudioEventKind`
ile track eşleşmesi birebirdir. Böylece A4 payload’ı A2’ye veya A1 payload’ı
A3’e sessizce taşınamaz.

`AudioEdlTrack.priority`, Faz 3A ile aynı medya-kendi-içinde sabit registry
önceliğidir: A1=10, A2=20, A3=30, A4=40, A5=50. Bu değer ses gain/mix kararı
değil, debug ve canonical ordering anahtarıdır.

Dataclass alan sıraları değişmez:

```text
AudioCueWordRange(project_id, document_id, narration_revision_id,
                  start_word_id, end_word_id)
AudioCueSampleRange(project_id, document_id, narration_revision_id,
                    start_word_id, end_word_id, start_sample,
                    end_exclusive_sample)
ReplayPcmSource(source_id, source_media_hash,
                normalized_pcm_evidence_hash, pcm_format,
                source_sample_rate_hz, source_channel_count,
                source_sample_frames, normalized_sample_frames,
                encoder_delay_samples, encoder_padding_samples)
ReplayPcmEvidence(source_id, normalized_pcm_evidence_hash, pcm_format,
                  sample_rate_hz, channel_count, sample_frames,
                  interleaved_samples)
AudioPlacementIntent(intent_id, track: AudioTrackRole, kind: AudioEventKind,
                     cue: AudioCueWordRange, source: ReplayPcmSource, source_in_sample,
                     source_out_exclusive_sample, gain_millibels,
                     ordinal)
AudioBoundaryIntent(boundary_intent_id, track: AudioTrackRole, ordinal,
                    position: AudioBoundaryPosition,
                    left_intent_id: str | None, right_intent_id: str | None,
                    left_transition: AudioTransitionKind,
                    right_transition: AudioTransitionKind,
                    requested_crossfade_samples)
AudioPlannedSilence(silence_id, track: AudioTrackRole, ordinal,
                    left_intent_id: str | None, right_intent_id: str | None,
                    start_sample, end_exclusive_sample)
AudioBoundaryDecision(position: AudioBoundaryPosition,
                      left_event_id: str | None, right_event_id: str | None,
                      track: AudioTrackRole,
                      policy: AudioBoundaryPolicy,
                      transition: AudioTransitionKind,
                      left_trim_samples, right_trim_samples,
                      fade_in_samples, fade_out_samples,
                      overlap_samples, protected_silence_samples)
EdlAudioEvent(schema_version, hash_scope_version, event_id, event_hash,
              track: AudioTrackRole, kind: AudioEventKind, ordinal, intent_id,
              source_id, source_media_hash, normalized_pcm_evidence_hash,
              start_sample, end_exclusive_sample, source_in_sample,
              source_out_exclusive_sample, gain_millibels,
              cue_start_word_id, cue_end_word_id, cue_start_sample,
              cue_end_exclusive_sample)
AudioEdlTrack(track: AudioTrackRole, priority, events)
AudioEdlArtifact(schema_version, hash_scope_version, audio_edl_id,
                 audio_edl_hash, video_edl_id, video_edl_hash,
                 word_to_frame_id, word_to_frame_hash,
                 narration_audio_id, narration_audio_hash,
                 narration_audio_media_byte_hash,
                 project_id, document_id, narration_revision_id,
                 narration_revision_hash, sequence_id,
                 sample_clock_version, sample_rate_hz, channel_count,
                 internal_pcm_format, sources, pcm_evidence,
                 duration_samples, tracks,
                 boundary_intents, planned_silences, boundary_decisions)
```

Her string NFC olmalı; kimlikler ASCII stable ID (1–128 byte), hash’ler
`sha256:` + 64 küçük hex olmalı, sayısal alanlar bool olmayan uint32 (sample
sayacı/ordinal) veya signed int32 (millibel) olmalıdır. Gain [-96,000, 24,000]
millibel aralığındadır. `ReplayPcmSource` kaynak medya provenance'ını ve ayrı
normalized PCM evidence hash'ini taşır; bunlar path, URL veya provider
descriptor değildir. `source_in/out` delay/padding tazmininden sonraki
effective normalized kaynak aralığına uygulanır; `in < out` zorunludur.

`source_media_hash`, kaynak medya byte'larının provenance hash'idir;
`normalized_pcm_evidence_hash` ise checked-in, 48 kHz stereo normalized PCM
kanıt byte'larının ayrı hash'idir. Bu iki alan aynı semantik alana ait
değildir, birbirinin yerine geçemez ve ikisinin de `sha256:` biçimi vardır.
`source_sample_*` ham kaynak metadata'sını, `normalized_sample_frames` ise
normalizasyon öncesi delay/padding dâhil 48 kHz PCM frame sayısını ifade eder.
`source_in/out`, delay/padding çıkarılmış effective normalized PCM
koordinatlarıdır: `0 <= in < out <= normalized_sample_frames - delay -
padding`. Bir placement'in output süresi tam olarak `out - in` sample'dır;
time-stretch, gizli resample veya belirsiz kaynak-süre eşlemesi yoktur.

**Artifact-içi immutable source/evidence snapshot (normatif).** Başarılı
`AudioEdlArtifact`, compile girdisindeki doğrulanmış `sources` ve
`pcm_evidence` tuple'larını root alanları olarak, aynı kanonik sırayla ve
tam dataclass projection ile taşır; bunlar yalnız derleme-sırası yardımcı
girdileri değildir. Her ikisi de artifact identity projection'ına, artifact
hash'ine ve canonical JSON'a dahildir. `EdlAudioEvent.source_id` ile başlayan
tek çözüm zinciri aşağıdaki artifact-içi snapshot'tır:

```text
event.source_id
  -> artifact.sources[source_id]
       (source_media_hash, normalized_pcm_evidence_hash, pcm_format,
        source_sample_rate_hz, source_channel_count, source_sample_frames,
        normalized_sample_frames, encoder_delay_samples, encoder_padding_samples)
  -> artifact.pcm_evidence[source_id]
       (normalized_pcm_evidence_hash, pcm_format, sample_rate_hz,
        channel_count, sample_frames, interleaved_samples)
```

Bu zincir, Bölüm 2'deki `d + a + (t - e)` fiziksel PCM koordinatını,
delay/padding tazminini, formatı ve frame sınırını artifact byte'larından
tek başına yeniden kurmaya yeterlidir. Faz 4 resolver'ı yalnız bu snapshot
ve event alanlarıyla çözüm yapar; dış registry'den source/evidence alanı
tamamlayamaz, ID/hash'e göre farklı bir kayıt seçemez, delay/padding'i
varsayamaz veya event'i yeniden zamanlayamaz. Gerçek Faz 4 PCM okuyucusu
ayrı bir implementation sorumluluğu olsa da, resolver snapshot'taki evidence
hash, format, frame sayısı ve canonical PCM bytes ile exact uyuşmayan medya
kullanırsa fail-closed olmalıdır. Snapshot'taki path/URL/provider descriptor
yoktur. Bu norm, Faz 4 renderer/mux implementasyonu değildir.

**Timeline→PCM koordinat kuralı (normatif).** `ReplayPcmEvidence` içindeki
PCM frame koordinatı fiziksel, delay/padding dâhil koordinattır; timeline ve
`source_in_sample` ise effective koordinatlardır. Bir `EdlAudioEvent` için
`e = event.start_sample`, `a = event.source_in_sample`, `b =
event.source_out_exclusive_sample`, `d = source.encoder_delay_samples` ve
`t` eventin timeline sample koordinatı olsun. Yalnız
`e <= t < event.end_exclusive_sample` iken:

```text
pcm_frame(event, t) = d + a + (t - e)
0 <= a < b <= source.normalized_sample_frames - d - source.encoder_padding_samples
0 <= pcm_frame(event, t) < evidence.sample_frames
event.end_exclusive_sample - e = b - a
```

Bu formül tek PCM lookup yoludur. `source_in_sample`a delay'i ikinci kez
eklemek, padding'i kaynak başına kaydırmak, eventin timeline başlangıcını
ihmal etmek veya `normalized_sample_frames`ı effective uzunluk saymak
yasaktır. Bir trim `n` olduğunda outgoing tarafın korunmuş PCM aralığı
`[d+a, d+b-n)`, incoming tarafın korunmuş aralığı `[d+a+n, d+b)` olur; bu
aralıklar boş olursa karar geçersizdir. `n=0` aralığı değiştirmez. Bu
hesaplardan herhangi birinde uint32 taşması, source/evidence sınırı dışına
çıkış veya event/source süre eşitsizliği `PCM_EVIDENCE_INVALID` ile ilgili
`/intents/<uint32>` pointer'ında fail-closed olur; planner clamp, wrap veya
sessiz trim uygulamaz.

## 3. Grid ve A/V dönüşüm kuralı

Sequence-local video frame `f` için sample başlangıcı aşağı yönlü rasyonel
dönüşümdür:

```text
sample_at_frame(f) = floor(f * 48000 * fps_denominator / fps_numerator)
```

Bu fonksiyonun `fps_numerator` ve `fps_denominator` girdileri **yalnız**
materialized `video_edl` içindeki sequence-local frame clock'tan alınır;
caller, `WordToFrameArtifact` veya global bir zaman çizelgesi ayrı bir FPS
veremez. `word_to_frame`in frame-rate kesri, `video_edl`in kesri ve onun
sequence ID/bounds'u exact eşleşmelidir. `f`, video EDL sequence başlangıcına
göre yerel, bool olmayan uint32 frame indeksidir; global frame, saniye veya
float timestamp önce yerel frame'e dönüştürülerek kullanılamaz. Bu kontrol
`sample_at_frame` çağrısından önce yapılır ve aksi durum
`DEPENDENCY_BINDING_INVALID` ile `/video_edl` pointer'ında fail-closed olur.
Dolayısıyla `duration_samples`, yalnız
`sample_at_frame(video_edl.duration_frames)` değeridir; helper veya loader
farklı bir süre hesaplayamaz ya da kabul edemez.

**Boundary intent input (normatif).** `AudioPlacementIntent` yalnız bir event
yerleşimini anlatır; bir event'in sol ve sağ sınırındaki transition kararını
taşımaz. Her nonempty track için compiler'ın üreteceği her `LEADING`,
`BETWEEN_EVENTS` ve `TRAILING` boundary'e tam olarak bir immutable
`AudioBoundaryIntent` caller tarafından verilmelidir. Bu tuple, bir eventin
sol sınırında `FADE_IN`, sağ sınırında `FADE_OUT` istemesini iki ayrı canonical
row ile ifade eder; event-level mutable/ambiguous transition state yoktur.

`AudioBoundaryIntent.ordinal` bool olmayan uint32 olup tuple index'ine eşit
olmalıdır. ID ASCII stable `abint_` kimliğidir. `position` ve null ID matrix'i
tamdır: `LEADING=(null, right_intent_id)`,
`BETWEEN_EVENTS=(left_intent_id, right_intent_id)`,
`TRAILING=(left_intent_id, null)`. Non-null intent ID, aynı trackte materialize
edilen intent'e exact bağlanır; between row'unda iki intent canonical track
stream'inde doğrudan komşu olmalıdır. Her nonempty-track boundary key'i
`(track, position, left_intent_id_or_empty, right_intent_id_or_empty)` için
tam bir row bulunur; extra, duplicate veya missing row
`BOUNDARY_POLICY_INVALID` ile ilgili `/boundary_intents/<uint32>` pointer'ında
fail-closed olur.

Allowed two-sided transition matrix'i kapalıdır:

```text
LEADING:  left=NONE, right=NONE | FADE_IN
TRAILING: left=NONE | FADE_OUT, right=NONE
BETWEEN:  (NONE, NONE) | (CROSSFADE, CROSSFADE) | (FADE_OUT, FADE_IN)
```

Yukarıdaki her durumda `requested_crossfade_samples` bool olmayan uint32'dir;
yalnız `(CROSSFADE, CROSSFADE)` için sıfırdan büyük, tüm diğer kombinasyonlarda
tam sıfırdır. Bu alan renderer tavsiyesi değil, tek bir between-boundary'nin
overlap kabulü için tek yetkili sample sayısıdır. `FADE_IN` ve `FADE_OUT`
başka bir boundary'e taşınamaz; compiler transition'ı eventten, renderer'dan
veya komşu row'dan türetemez ya da sessizce dönüştüremez.
`AudioPlannedSilence.silence_id` stable ASCII `sil_` kimliğidir. Sessizlik,
track-local komşuluğunu `left_intent_id`/`right_intent_id` ile açıkça bağlar:
iki ID de null olamaz; null olmayan ID aynı trackteki bir niyete exact
eşleşmelidir. Bu binding, sessizliğin rastgele bir gap'ten çıkarılmasını
veya başka sequence'in event'ine bağlanmasını engeller.

`planned_silences` caller tuple'ı canonical, strict ve yeniden sıralanamazdır.
Her row'un bool olmayan uint32 `ordinal` değeri kendi tuple index'ine tam eşit
olur; row'lar şu strict artan anahtarla yazılır: `(track.priority,
start_sample, end_exclusive_sample, left_intent_id_or_empty,
right_intent_id_or_empty, silence_id)`. `track.priority` Bölüm 2'deki
A1..A5 sabitidir; null binding'in anahtar karşılığı boş ASCII stringdir.
Compiler bu tuple'ı sort, deduplicate veya normalize etmez. İlk ordinal veya
strict-order ihlâli, ihlâlli row'un `/planned_silences/<uint32>` pointer'ında
`ORDERING_INVALID` ile fail-closed olur. Aynı canonical key zaten birden çok
row ile yazılamaz; ayrıca aynı boundary key Bölüm 5'teki ayrı uniqueness
kuralıyla yasaktır. Böylece planned-silence sırası hem helper inputunun hem
artifact snapshot'ının tek anlamlı parçasıdır.

Video EDL’den gelen `duration_frames` için `duration_samples` tam olarak
`sample_at_frame(duration_frames)` olur. Bir cue’nun start/end WordToFrame
frame değerleri bu fonksiyonla sample sınırına çevrilir. Böylece video event
başlangıcıyla eşleşmesi gereken A1 narration veya cue-bound SFX’in grid hatası
bir video frame’inden küçüktür; implementasyon acceptance testinde mutlak farkı
`< ceil(48000 * fps_denominator / fps_numerator)` sample olarak hesaplayıp
kanıtlar. Milisaniye float’ı, `round`, zamana bağlı clock ve per-frame sample
array yasaktır.

`AudioCueWordRange` caller'ın verdiği tek cue girdisidir ve sample koordinatı
taşımaz. Derleyici `AudioCueSampleRange`'i yalnız materialized `WordToFrame`
artifact'indeki word ID'lerinden türetir; caller sample koordinatına güvenmez.
Bu derivation'ın start/end değerleri `sample_at_frame` ile hesaplanır ve event
payload'ına yeniden yazılır. Metin arama ve tekrar eden kelimeye göre eşleme
yapılamaz. Faz 3A EDL’nin sequence
başlangıç/bitiş word kimlikleri, FPS ve project/document/revision lineage’i
tam eşleşmek zorundadır. A1’in her intent cue’su narration aralığındadır; A2,
A3, A4 ve A5 cue’su opsiyonel değildir: sıralama için her event yine görünür
bir sequence-local cue ile bağlıdır. Bu, sessiz bir “sonsuz BGM” default’unu
engeller.

Cue bir **anchor**dur; tüm ses olayının cue sample aralığıyla zorunlu olarak
aynı uzunlukta olması istenmez. Derleyici her intent için
`start_sample = cue_start_sample` ve
`end_exclusive_sample = start_sample + (source_out_exclusive_sample -
source_in_sample)` üretir. Bu nedenle A2–A5 cue'su olay başlangıcını
deterministik olarak video gridine bağlar, fakat BGM/SFX/source speech/ambience
örneğini yapay olarak cue sonuna kesmez. Yalnız A1 `NARRATION` için event
aralığı exact `AudioCueSampleRange` olmalıdır ve effective source uzunluğu
cue uzunluğuna eşit değilse `CUE_RESOLUTION_INVALID` ile fail-closed olunur.
Her türde A/V kabul ölçüsü event başlangıcı ile cue/video frame başlangıcı
arasındaki farktır; bu fark sıfırdır ve genel sınır olarak bir video
frame'inin sample sayısından küçüktür. Olay sonunun cue sonuyla eşitliği
A2–A5 için bir A/V kriteri değildir.

**Zorunlu sequence-bound aşaması (normatif).** Cue ve effective source span'i
türetilir türetilmez, **her** intent için candidate event aralığı önce

```text
0 <= start_sample < end_exclusive_sample <= duration_samples
```

ile doğrulanır. `duration_samples` bu bölümün başında tanımlanan, materialized
video EDL'den türetilmiş tek sequence-local üst sınırdır; track sonu, son
intent, planned silence veya caller değeri ikame edilemez. Candidate event,
bu kontrol geçmeden canonical ordering anahtarına alınamaz, track listesine
append edilemez, same-track collision/crossfade veya A1/A4 speech collision
kontrolüne giremez ve boundary helper'a verilemez. Negatif start, boş/ters
aralık, uint32 overflow ya da sequence sonunu aşan `end_exclusive_sample`,
ilk ilgili `/intents/<uint32>` pointer'ında `SEQUENCE_BOUNDS_INVALID` ile
fail-closed olur. Compiler clamp, truncate, wrap, track-local süre türetme
veya sonraki collision hatasını tercih etmez.

## 4. Normalizasyon ve kaynak kabulü

`ReplayPcmSource` yalnız fixture/test sınırında normalize edilmiş PCM'nin
metadata/provenance kaydını temsil eder. `ReplayPcmEvidence`, aynı kayda bağlı
değişmez checked-in PCM kanıtını temsil eder; `interleaved_samples` tuple'dır,
`sample_frames * channel_count` uzunluğundadır ve evidence hash'i canonical
PCM byte gösteriminden yeniden hesaplanır. Canonical PCM byte'ı **yalnız**
şudur: `PCM_F32LE` için her scaların runtime type'ı tam `float` olmalı (bool,
int, Decimal veya platform-specific numeric subtype kabul edilmez), sonlu
IEEE-754 binary32 sayısı olmalı, `-0.0`, NaN ve ±infinity reddedilmeli ve scalar `struct.pack("<f",
x)` ile little-endian dört byte olarak yazılmalıdır. Kabul, yalnız pack'in
başarılı olmasına dayanmaz: `packed = struct.pack("<f", x)` sonrasında
`unpacked = struct.unpack("<f", packed)[0]` hesaplanır; `unpacked` sonlu,
pozitif/negatif sıfır olmayan olmalı ve IEEE numeric equality ile
`unpacked == x` exact doğru olmalıdır. Böylece binary64 caller değerinin
binary32'ye yuvarlanması, overflow, NaN canonicalization, signed-zero drift
ve platforma bağlı float text dönüşümü kabul edilmez. Hash/fixture oracle'ı
aynı pack→unpack→exact-equality kuralını uygulanmadan hiçbir F32 scalarını
canonical bytes'a yazamaz. `PCM_S24LE` için her
scalar bool olmayan `[-8388608, 8388607]` aralığında tamsayı olmalı ve signed
two's-complement değerinin low-order üç byte'ı little-endian yazılmalıdır.
Stereo sample frame'leri input tuple'daki sol/sağ sırasıyla ardışık yazılır;
container header, platform endian'ı, float text temsili veya runtime
normalisation hash'e girmez. `normalized_pcm_evidence_hash` tam olarak bu
byte dizisinin `sha256:` hash'idir. Derleyici production medya decode
etmez: her source için exact bir immutable evidence gerekir; eksik, farklı
source ID'li veya hash'i uyuşmayan evidence fail-closed olur. Derleyici
aşağıdaki kararı artifact’e taşır:

### 4.1 Fixture-only WAV container binding (normatif)

`tests/fixtures/phase3/audio_edl_pcm/*.wav` dosyaları yalnız REPLAY fixture
kanıtıdır; WAV path'i, WAV container byte hash'i ve RIFF metadata'sı hiçbir
zaman `ReplayPcmEvidence`, `AudioEdlArtifact`, canonical JSON veya artifact
identity projection'ına girmez. Buna karşılık
`tests/fixtures/phase3/audio_edl_replay_v1.json`, canonical compile input'tan
ayrı **test-only** `fixture_pcm_bindings` array'ini taşır. Bu array source ID
ile strict artan canonical sırada olmalı ve her row tam olarak aşağıdaki
anahtarlara sahip olmalıdır:

```text
source_id
relative_wav_path
wav_file_byte_hash
normalized_pcm_evidence_hash
pcm_format
sample_rate_hz
channel_count
sample_frames
```

`relative_wav_path`, JSON fixture köküne göre yalnız
`audio_edl_pcm/<ascii-file-name>.wav` biçiminde relatif POSIX path'tir;
absolute path, `\\`, `..`, `.` segmenti, URL, symlink resolution veya glob
yasaktır. `wav_file_byte_hash`, checked-in WAV container'ın **tam dosya
byte** dizisinin `sha256:` hash'idir. Bu hash yalnız fixture dosyasının yanlış
değiştirilmesini yakalar; `source_media_hash` değildir ve canonical audio EDL
kimliğine girmez.

Her binding, aynı `source_id`li bir `ReplayPcmEvidence` ile birebir eşleşmeli;
format, 48 kHz, iki kanal, frame sayısı ve
`normalized_pcm_evidence_hash` exact aynı olmalıdır. Test-only WAV reader
yalnız aşağıdaki dar container profilini kabul eder:

```text
RIFF little-endian + WAVE
exactly one fmt chunk and one data chunk; no trailing bytes or extra chunks
PCM_S24LE: format tag 1, bits_per_sample 24, block_align 6, byte_rate 288000
PCM_F32LE: format tag 3, bits_per_sample 32, block_align 8, byte_rate 384000
channels 2, sample_rate_hz 48000, data_size == sample_frames * block_align
```

Reader `data` chunk byte'larını dönüştürmeden `ReplayPcmEvidence`'ın Bölüm
4'te tanımlı canonical PCM byte gösterimiyle byte-for-byte karşılaştırır.
Dolayısıyla `sha256(data_chunk_bytes)` exact
`normalized_pcm_evidence_hash` olmalı; evidence'in `interleaved_samples`
değerlerinden yeniden üretilen canonical PCM byte'ı da aynı data chunk'a exact
eşleşmelidir. RIFF/WAV parser implicit decode, resample, channel map,
normalization, float text conversion, NaN canonicalization veya padding
varsayımı yapmaz. Bir container hash'i, path'i, fmt/data metadata'sı veya
data/canonical-evidence byte'ı uyuşmazsa test fixture geçersizdir; compiler
bu test-only binding'i runtime input olarak kabul etmez ve artifact'e serialize
etmez.

Bu ayrım zorunludur: `wav_file_byte_hash` checked-in container provenance'ını,
`normalized_pcm_evidence_hash` ise audio planının fiziksel PCM kanıtını bağlar.
İlki ikincinin yerine kullanılamaz; WAV header byte'ları evidence hash'ine
katılamaz.

1. Kaynak kimliği, `source_media_hash` ve `normalized_pcm_evidence_hash` exact
   olmalı; aynı `source_id` farklı medya veya evidence hash'i ile tekrar
   kullanılamaz. Media hash ile evidence hash'ini eşit saymak veya biri yokken
   diğerini ikame etmek yasaktır.
2. Runtime input yalnız 48 kHz/stereo normalized PCM evidence olabilir. Farklı
   kaynak formatının resample/channel-map işlemi Faz 3B uygulama sınırının
   dışındaki fixture-authoring adımıdır; compiler ve boundary helper gerçek
   asset, WAVE container veya codec decode desteği iddia etmez.
3. Encoder delay ve tail padding nonnegative explicit sample sayılarıdır.
   Tazmin sonrası kullanılabilir aralık boşsa `ENCODER_COMPENSATION_INVALID`
   ile fail-closed olunur. Sıfır değer varsayılan değildir; fixture bunu açıkça
   yazar.
4. A1 source, supplied genuine `AudioArtifact` ile exact
   project/document/narration revision/hash ve decoded sample metadata
   bakımından bağlanır: `ReplayPcmSource.source_id/source_media_hash`
   sırasıyla audio artifact ID/media-byte-hash’e eşit olmalıdır; normalized PCM
   evidence hash'i AudioArtifact media hash'i değildir. Diğer
   track’ler source-audio güvenli veya lisanslı
   sayılmaz; yalnız REPLAY ses planı olarak işaretlenir.

A1 için yukarıdaki binding ayrıca ham metadata'da da exacttır:

```text
A1 ReplayPcmSource.source_id                 == narration_audio.audio_artifact_id
A1 ReplayPcmSource.source_media_hash         == narration_audio.media_byte_hash
A1 ReplayPcmSource.source_sample_rate_hz     == narration_audio.decoded_metadata.sample_rate_hz
A1 ReplayPcmSource.source_channel_count      == narration_audio.decoded_metadata.channel_count
A1 ReplayPcmSource.source_sample_frames       == narration_audio.decoded_metadata.sample_frame_count
```

Bu beş eşitlik A1 `NARRATION` intenti olmayan ya da birden çok olan artifact
ile birlikte de geçerlidir: nonempty A1 track tam olarak bir narration source
registry kaydına bağlanır ve her A1 intent aynı exact registry kaydını taşır.
`ReplayPcmSource`un 48 kHz/stereo normalized metadata'sı, mevcut
`AudioArtifact.decoded_metadata` yerine geçmez; normalize edilen evidence
farklı formatta bir fixture-authoring sonucu olabilir. Her A1 raw metadata,
ID veya media hash farkı `DEPENDENCY_BINDING_INVALID` ile `/narration_audio`
pointer'ında fail-closed olur; compiler declared/decoded değerleri kırparak,
resample ederek veya default atayarak eşitlemez.

Normalizasyon yalnız fixture üretiminde doğrulanır; Faz 3B runtime'ında
`AudioFormatNormalizer`, production decode veya I/O yoktur. Public saf helper
`plan_audio_boundaries(*, tracks: tuple[AudioEdlTrack, ...],
intents: tuple[AudioPlacementIntent, ...],
boundary_intents: tuple[AudioBoundaryIntent, ...],
planned_silences: tuple[AudioPlannedSilence, ...],
pcm_evidence: tuple[ReplayPcmEvidence, ...],
duration_samples: int) -> tuple[AudioBoundaryDecision,
...]` yalnız immutable tuple'ları okur. `intents`, eventlerin `intent_id`
alanlarıyla one-to-one exact bağlanır; `boundary_intents` tüm generated
boundary key'leriyle one-to-one exact bağlanır ve two-sided transition ile
`requested_crossfade_samples` değerlerini helper'a taşıyan tek otoritedir.
Helper bu bilgiyi eventten, mutable globalden, başka boundary row'undan veya
renderer varsayımından türetemez. Helper karar tuple'ını
döndürür; disk, network, subprocess, global cache, buffer mutation ve codec
çağrısı yapmaz. `compile_audio_edl` bu helper'ı çağırır ve onun sonucu olmayan
boundary kaydını kabul etmez.

`duration_samples`, bool olmayan uint32 ve root artifactteki tam değer olmak
zorundadır; helper bunu track sonundan, son eventten veya silence aralığından
türetmez. Derleyici helper'a yalnız
`sample_at_frame(video_edl.duration_frames)` değerini verir. Böylece LEADING ve
TRAILING terminal kararları ile `AudioPlannedSilence`ın `0`/`duration_samples`
uç sınırları helper tarafından bağımsız olarak doğrulanabilir. Eksik, farklı
veya türetilmiş süre `BOUNDARY_POLICY_INVALID` ile `/boundary_decisions/<uint32>`
pointer'ında fail-closed olur.

`sources` ve `pcm_evidence` iki ayrı, tekil kimlik alanıdır; compiler bunları
birbirinin yerine geçirmez. Her ikisinde de `source_id` global olarak tam bir
kez bulunur: aynı `source_id` ile iki kayıt (byte-byte aynı olsalar bile), aynı
source'a iki evidence veya bir evidence'in iki source tarafından paylaşılması
yasaktır. Her intent'in source'u, `sources` içinde tam bir kayda ve onunla aynı
`source_id` taşıyan tam bir evidence kaydına bağlanmalıdır; orphan
`intent.source`, registry'deki aynı `source_id`li `ReplayPcmSource` ile tüm
dataclass alanlarında field-wise exact eşit olmalıdır; yalnız `source_id`,
media hash veya evidence hash eşitliği yeterli değildir. Compiler, intent
içindeki kısmi/forged source'u registry kaydıyla birleştiremez, registry
alanlarını sessizce dolduramaz veya intent kaydını tercih edemez. Bu equality,
canonical dataclass projection üzerinden doğrulanır ve fark
`DEPENDENCY_BINDING_INVALID` ile ilgili `/intents/<uint32>` pointer'ında
fail-closed olur. Orphan source/evidence ve kullanılmayan source kaydı da yasaktır. Bu kontrol input
sırasını değiştirmeden iki map ve tek intent geçişiyle `O(S + I)` yapılır.

Artifact snapshot'ı için iki input tuple da ayrıca canonical olarak
`source_id` strict ASCII artan sırada verilmelidir ve aynı tuple index'inde
aynı `source_id`yi taşımalıdır. Compiler onları sort etmez, deduplicate etmez
veya birini diğerinin sırasına göre yeniden kurmaz; ilk sıra/indeks ihlâli
`/sources/<uint32>` ya da `/pcm_evidence/<uint32>` pointer'ında
`ORDERING_INVALID` ile fail-closed olur. Başarılı derleme bu exact sıra ile
root `sources`/`pcm_evidence` snapshot'ını serialize eder. Böylece aynı
semantik kayıtların farklı caller sırası farklı canonical byte üretmesine
izin verilmez ve Faz 4 resolver index eşlemesi yalnız convenience olarak
kullanılsa bile kimlik otoritesi `source_id` olur.

Bağlı source/evidence üçlüsünün metadata'sı exact olmalıdır:

```text
source.normalized_pcm_evidence_hash == evidence.normalized_pcm_evidence_hash
source.pcm_format                    == evidence.pcm_format == internal_pcm_format
evidence.sample_rate_hz              == INTERNAL_AUDIO_SAMPLE_RATE_HZ
evidence.channel_count               == INTERNAL_AUDIO_CHANNEL_COUNT
source.normalized_sample_frames      == evidence.sample_frames
len(evidence.interleaved_samples)    == evidence.sample_frames * evidence.channel_count
```

`source.source_sample_rate_hz` ve `source.source_channel_count` yalnız ham
provenance metadata'sıdır, bool olmayan pozitif uint32 olmalıdır ve normalized
evidence formatı yerine kullanılamaz. `source.source_sample_frames` pozitif
uint32, delay/padding bool olmayan uint32; effective interval kuralı ile
birlikte source/evidence sayacı overflow veya çifte tazmin bırakmaz. Her
yukarıdaki eşitsizlik, eksik/extra source-evidence eşlemesi veya herhangi bir
duplicate `PCM_EVIDENCE_INVALID` ile ilgili ilk `/sources/<uint32>` ya da
`/pcm_evidence/<uint32>` pointer'ında fail-closed olur; compiler duplicate'i
“ilk kazanan” diye seçmez.

## 5. Boundary planner ve çakışma kuralları

Her track event stream’i compiler tarafından türetilen
`(start_sample, end_exclusive_sample, intent_id)` sırasındadır; caller yalnız
word-ID cue ve effective source aralığını verir. Aynı track için half-open aralıklar
doğrudan üst üste gelemez; tek istisna aşağıdaki yetkili crossfade algoritmasıdır.
Trackler arası
eşzamanlı çalışma serbesttir: örneğin A1 narration + A2 BGM + A3 impact SFX +
A5 ambience eşzamanlı olabilir. A1 ve A4 aynı sample’da konuşma taşıyamaz;
çakışma `SPEECH_COLLISION` ile fail-closed olur. Faz 11’in source-speech/BGM
uygunluk politikası burada taklit edilmez.

Caller `intents` tuple'ı global canonical input order'da verilir; compiler
**hiçbir zaman sort etmez veya ordinal yeniden yazmaz**. Her `ordinal` bool
olmayan uint32 olmalı, tuple index'ine eşit olmalı ve dolayısıyla tam olarak
`0..len(intents)-1` benzersiz/contiguous serisini oluşturmalıdır. Cue ve
effective source span'i derive edilip Bölüm 3 zorunlu sequence-bound aşaması
geçtikten sonra her row'un global anahtarı

```text
(track.priority, start_sample, end_exclusive_sample, intent_id)
```

olur; input'taki her anahtar bir öncekinden strict ASCII/number tuple order'a
göre büyük olmalıdır. Aynı anahtar, aynı `intent_id` veya ters sıralanmış row
kabul edilmez. Bu tek sol→sağ geçiş, source/evidence ve word map'leri
kurulduktan sonra `O(I)` zamanda yapılır; track event listeleri bu validated
order'dan append ile elde edilir, sort veya quadratic yeniden sıralama yoktur.
Ordinal'in index'e eşit olmaması, duplicate/gap, duplicate `intent_id` veya
global anahtarın previous key'den strict büyük olmaması ilk ihlâl eden
`/intents/<uint32>` pointer'ında `ORDERING_INVALID` ile fail-closed olur.
Cue/source derivation'ı yapılamıyorsa bu sıralama kontrolünden önce
`CUE_RESOLUTION_INVALID`, türetilen event sequence sınırı dışındaysa ondan da
önce `SEQUENCE_BOUNDS_INVALID` kazanır. Bu öncelik, hostile caller sırasının
geçersiz cue'yu veya sequence sonunu aşan event'i maskelemesini önler.

Crossfade kararı yalnız aynı trackteki ardışık iki intent'i exact bağlayan tek
bir `BETWEEN_EVENTS AudioBoundaryIntent` için şu koşulların **tamamı**
sağlandığında üretilir: `left_transition == right_transition == CROSSFADE`,
`requested_crossfade_samples > 0`, iki event non-speech, sağ eventin türetilmiş
başlangıcı tam olarak `left.end_exclusive_sample - requested_crossfade_samples`,
sağ eventin sonu sol eventin sonundan büyük ve overlap herhangi bir planned
silence ile kesişmez. Bu koşullardan biri sağlanmazsa her positive same-track overlap
`TRACK_COLLISION` olur; planner overlap'i küçültmez, kaydırmaz, oluşturmaz veya
fallback policy seçmez. Kabul edilen overlap sayısı kararın
`overlap_samples`, `fade_in_samples` ve `fade_out_samples` alanlarına aynen
yazılır. Başka boundary row'u veya event-level alan crossfade yetkisi veremez.
Böylece caller'ın cue-anchor'ları ile canonical event zamanları tek anlamlı
kalır.

`AudioPlannedSilence` explicit, half-open ve track-local bir modeldir; sessizlik
varsayılan gap'ten çıkarılamaz. Her silence ID benzersizdir, range sequence
sınırları içindedir, event veya crossfade ile kesişemez ve `PRESERVE_SILENCE`
kararıyla tam bir kez korunur. En az bir intent binding'i non-null olmak
zorundadır. Her silence için canonical boundary key tam olarak
`(track, position, left_intent_id_or_empty, right_intent_id_or_empty)`dir;
`position`, yalnız right binding için `LEADING`, yalnız left binding için
`TRAILING`, iki binding için `BETWEEN_EVENTS` olur. Bir terminal veya iki-event
boundary key'i en fazla bir planned silence'a ait olabilir. İkinci silence
aynı key'i tanımlarsa (range veya `silence_id` farklı olsa bile) compiler ve
loader sonraki row'un `/planned_silences/<uint32>` pointer'ında
`BOUNDARY_POLICY_INVALID` ile fail-closed olur; “ilk kazanan”, birleştirme,
implicit sessizlik veya ikinci bir preserve kararı yoktur. `left_intent_id` null değilse bağlı eventin sonu
silence başlangıcını aşamaz; `right_intent_id` null değilse bağlı eventin
başlangıcı silence sonundan önce olamaz. İki binding de mevcutsa intent'ler
track sırasındaki doğrudan komşulardır. Karardaki event ID'leri bu bound
intent'lerin türetilmiş event ID'lerine exact eşleşmelidir. A1 planned
silence'ın narration TTS word aralığıyla kesişmesi yasaktır. Yalnız sağ
binding'i olan silence terminal `LEADING` kararıdır ve `start_sample == 0`
olmalıdır; yalnız sol binding'i olan silence terminal `TRAILING` kararıdır ve
`end_exclusive_sample == duration_samples` olmalıdır. Bu terminal silence'lar
da ilgili tek bağlı event ile `PRESERVE_SILENCE` olarak tam bir kez serialize
edilir; implicit terminal gap sessizlik değildir.

**Exact planned-silence adjacency geometry (normative).** Yukarıdaki
“aşamaz” ilişkisi toleranslı bir bağ değildir ve bu alt bölüm onu daraltır.
Sol binding varsa bağlı eventin `end_exclusive_sample` değeri tam olarak
`silence.start_sample` olmalıdır; sağ binding varsa bağlı eventin
`start_sample` değeri tam olarak `silence.end_exclusive_sample` olmalıdır.
İki binding varsa intent'ler aynı track stream'inde direct-adjacent olmalı ve
iki eşitlik de sağlanmalıdır. Böylece daha geniş/ikinci bir unowned gap,
overlap veya yalnızca “aşmama” planned silence olarak kabul edilemez. Yalnız
sağ bindingli `LEADING` satırda ayrıca `silence.start_sample == 0`; yalnız sol
bindingli `TRAILING` satırda ayrıca
`silence.end_exclusive_sample == duration_samples` olmalıdır. Bu exact
eşitliklerden, terminal uç kuralından veya direct-adjacency kuralından
herhangi biri ihlâl edilirse compiler ve loader ilk ihlâlli silence row'un
`/planned_silences/<uint32>` pointer'ında exact
`BOUNDARY_POLICY_INVALID` ile fail-closed olur. Clamp, gap'i silence'a
genişletme/daraltma veya başka policy'ye düşme yasaktır.

Her `AudioPlannedSilence` canonical boundary key'i için exact bir matching
`AudioBoundaryIntent` bulunmalı ve onun two-sided transition'ı `(NONE,NONE)`
olmalıdır; PRESERVE_SILENCE ile crossfade/long-fade/hard-cut/microfade intent'i
aynı boundary'de birlikte bulunamaz. Bu matching row, silence varlığını
override etmez: Section 5.1 priority'sinde preserve satırı kazanır ve onun
field matrix'i karar artifact'ine yazılır. Missing/forged/non-NONE row ilgili
`/boundary_intents/<uint32>` `BOUNDARY_POLICY_INVALID` ile fail-closed olur.

`PRESERVE_SILENCE` metadata-only bir gap kabulü değildir: sessizliğe komşu
olan her bound event, fiziksel PCM kenarında **iki kanalda da exact `0`**
olmak zorundadır. Sol binding varsa outgoing kenar frame'i
`x[d + b - 1] == 0`; sağ binding varsa incoming kenar frame'i
`x[d + a] == 0` olmalıdır; `a`, `b` ve `d` bölüm 2'deki aynı event/source
koordinatlarıdır. Equality IEEE PCM sample equality'dir: sign-change,
interior zero-crossing, trim, fade, gain, epsilon veya renderer-sonrası
telafi edge-zero yerine geçmez. Terminal planned silence tek komşusu için,
between-events planned silence iki komşusu için bu kuralı sağlar. Bir bound
kenar exact zero değilse ilgili silence row'un
`/planned_silences/<uint32>` pointer'ında `BOUNDARY_POLICY_INVALID` ile
fail-closed olunur; silence korunmuş sayılmaz ve başka bir boundary policy'ye
fallback yapılmaz.

Artifact sabit sırayla A1–A5'in **tamamını** `AudioEdlTrack` olarak taşır;
boş track `events=()` ile geçerlidir ve onun için boundary kararı üretilmez.
En az bir event taşıyan her track için her komşu pair ile sequence başlangıç ve
sonu için tam bir `AudioBoundaryDecision` üretilir. Terminal kararlar JSON'da açıkça
serialize edilir: `LEADING` için `left_event_id: null` ve ilk event ID'si;
`TRAILING` için son event ID'si ve `right_event_id: null`; `BETWEEN_EVENTS`
için iki ID de non-null olur. Başka null kombinasyonu, event-less terminal
kararı veya nonempty track terminal kararının atlanması `BOUNDARY_POLICY_INVALID`
olur.
`boundary_intents`, compiler'ın önce materialize ettiği bu aynı complete
boundary setinin caller-owned, immutable karşılığıdır. Tuple global canonical
sırası `(track priority, boundary_anchor_sample, position_rank,
left_intent_id_or_empty, right_intent_id_or_empty, boundary_intent_id)`dir;
önceki anahtardan strict büyük olmalı, ordinal index'e eşit olmalı ve compiler
sort/deduplicate etmemelidir. `boundary_anchor_sample` ve `position_rank`,
hemen aşağıdaki `AudioBoundaryDecision` tanımıyla aynıdır. Böylece bir eventin
trailing transition'ı ile sonraki eventin leading transition'ı bağımsız iki
terminal/between row'da ifade edilir; herhangi bir eventin tek transition
alanının iki sınırı sessizce yönetmesi mümkün değildir. Missing/extra,
non-adjacent, wrong-track, duplicate key/ID veya noncanonical sıra, boundary
kararı seçilmeden `/boundary_intents/<uint32>` + `ORDERING_INVALID` (sıra/ID)
ya da `BOUNDARY_POLICY_INVALID` (shape/binding/matrix) ile fail-closed olur.
`AudioBoundaryDecision` JSON nesnesi tam olarak dataclass alan sırasındaki
12 anahtara sahip olur; hiçbiri eksik veya ek olamaz. Sadece
`left_event_id`/`right_event_id` null olabilir ve null kombinasyonu position
ile tam eşleşir: `LEADING=(null, event_id)`,
`BETWEEN_EVENTS=(event_id, event_id)`, `TRAILING=(event_id, null)`.
Tüm sayısal alanlar JSON number olup null, bool veya string olamaz.
Kararların global sırası `(track priority, boundary_anchor_sample, position_rank,
left_event_id_or_empty, right_event_id_or_empty)`dir; `position_rank`
`LEADING=0`, `BETWEEN_EVENTS=1`, `TRAILING=2` olur. Anchor leading'de sağ
event start'ı, between'de sol event end'i, trailing'de sol event end'idir.
Karar aşağıdakilerden birini açıkça seçer:

- `PRESERVE_SILENCE`: explicit `AudioPlannedSilence` aralığını korur;
  `protected_silence_samples > 0`, overlap ve crossfade sıfırdır. Crossfade
  bu aralığı örtemez.
- `ZERO_CROSSING_MICROFADE`: en yakın geçerli zero crossing, sağ/sol sınırdan
  en fazla 240 sample (5 ms) aranır; bulunmazsa tam kayıtlı microfade uygulanır.
  TTS kelime start/end sample’ını trimleyemez.
- `HARD_CUT_ZERO_CROSSING`: yalnız SFX/ambience için, explicit zero crossing
  bulunursa fade olmadan kullanılabilir; narration/source speech için yasaktır.
- `OVERLAP_CROSSFADE`: aynı trackte komşu, non-speech eventler arasında
  yalnız yukarıdaki crossfade algoritmasıyla gerçekleşir.
  `overlap_samples == fade_in_samples == fade_out_samples > 0` olmalı,
  output range sequence dışına taşmamalı ve protected silence’a girmemelidir.
- `LONG_EDITORIAL_FADE`: BGM/ambience için explicit uzun fade; gain/easing
  yorumu Faz 4/11’e bırakılmaz, karar sample sayısını taşır. Uygulama
  penceresi ve gain formülü aşağıda sabittir.

`AudioTransitionKind.NONE`, declarative long fade veya crossfade uygulanmadığını
belirtir; total matriste izin verilen `ZERO_CROSSING_MICROFADE`,
`PRESERVE_SILENCE`, `HARD_CUT_ZERO_CROSSING` ve iki-event `LONG_EDITORIAL_FADE`
satırlarında kullanılır. Matris dışında bir `NONE` kombinasyonu yoktur.
Boundary uygulaması click/pop yok iddiasını ses
örneklerinde test eder: pair birleşiminde mutlak sample farkı fixture’ın sabit
eşik üstündeyse test başarısız olur; “warning ile kabul” yoktur. `ZeroCrossingDetector`
yalnız PCM array üzerinde bounded lineer pencere tarar. `MicroFadePlanner` ve
`CrossfadeCollisionResolver` yalnız karar üretir; ses buffer’ını mutate etmez.

### 5.1 Tam karar matrisi ve PCM oracle (normatif)

Bu alt bölümdeki sabitler implementation tarafından değiştirilemez:
`ZERO_CROSSING_SEARCH_SAMPLES = 240`, `MICROFADE_SAMPLES = 240`,
`LONG_EDITORIAL_FADE_SAMPLES = 24000` ve
`MAX_SEAM_CHANNEL_DELTA = 1/64`. Bütün sayılar 48 kHz sample sayısıdır;
dolayısıyla microfade 5 ms, long editorial fade 500 ms'tir. Bir long fade
isteği bu sayıdan daha kısa uygulanamaz; event içinde yeterli sample yoksa
`BOUNDARY_POLICY_INVALID` ile fail-closed olunur. Compiler bu sabitleri
payload'dan, environment'tan veya renderer ayarından almaz.

`AudioBoundaryDecision` için total karar tablosu aşağıdaki gibidir. Tabloda
“sıfır” `left_trim_samples`, `right_trim_samples`, `fade_in_samples`,
`fade_out_samples`, `overlap_samples` ve `protected_silence_samples` alanlarının
tam olarak `0` olmasını; “N” ise ilgili policy'nin literal sample sayısını
anlatır. Tabloda yazmayan her position/policy/transition kombinasyonu,
herhangi bir pozitif alan veya başka bir null-ID bileşimi
`BOUNDARY_POLICY_INVALID` olur.

Bir satırın önkoşulu birden fazlasıyla uyumlu görünürse tablo yorumlanmaz;
helper aşağıdaki **sabit öncelik sırası** ile ilk geçerli sınıfı seçer:

```text
terminal explicit planned silence
→ between-events explicit planned silence
→ accepted overlap crossfade
→ accepted two-sided long editorial fade
→ accepted HARD_CUT_ZERO_CROSSING
→ ZERO_CROSSING_MICROFADE fallback
```

Leading/trailing long fade bu sırada kendi terminal non-silence satırında,
terminal microfade ise son fallback'te değerlendirilir. Özellikle aynı A3/A5
temasında ilgili boundary row `(NONE,NONE)` ise, hard-cut uygunluğu generic microfade
fallback'inden **önce** ve tek kez değerlendirilir. Hard-cutın koşulları
sağlanmıyorsa helper hard-cut metadata'sı yazamaz; yalnız o zaman generic
`ZERO_CROSSING_MICROFADE` fallback'i normal crossing/trim/microfade kuralları
ile uygulanır. Helper adayları yeniden sıralamaz, bir policy'yi diğerine
dönüştürmez ve bir event tarafında hem hard-cut hem trim/fade kararı üretmez.

| Konum ve önkoşul | Tek geçerli policy / transition | Zorunlu alanlar | Yasak durum |
|---|---|---|---|
| `LEADING`, terminal planned silence yok; ilk event A1/A3/A4 veya A5/A2'de `NONE` | `ZERO_CROSSING_MICROFADE` / `NONE` | yalnız `right_trim_samples` 0..240 **veya** `fade_in_samples=240`; diğerleri sıfır | `left_event_id` non-null, overlap, long fade |
| `LEADING`, ilk event A2/A5 ve boundary row `left=NONE,right=FADE_IN` | `LONG_EDITORIAL_FADE` / `FADE_IN` | `fade_in_samples=24000`; diğerleri sıfır | A1/A3/A4, short fade, trim/overlap |
| `LEADING`, explicit terminal planned silence yalnız sağ intent'e bağlı | `PRESERVE_SILENCE` / `NONE` | `protected_silence_samples = silence.end - silence.start > 0`; right bound eventin iki kanal incoming physical edge'i exact `0`; diğerleri sıfır; `left_event_id=null`, `right_event_id` bound event | silence `start_sample != 0`, edge-zero yok, fade/trim/overlap veya farklı bound event |
| `TRAILING`, terminal planned silence yok; son event A1/A3/A4 veya A5/A2'de `NONE` | `ZERO_CROSSING_MICROFADE` / `NONE` | yalnız `left_trim_samples` 0..240 **veya** `fade_out_samples=240`; diğerleri sıfır | `right_event_id` non-null, overlap, long fade |
| `TRAILING`, son event A2/A5 ve boundary row `left=FADE_OUT,right=NONE` | `LONG_EDITORIAL_FADE` / `FADE_OUT` | `fade_out_samples=24000`; diğerleri sıfır | A1/A3/A4, short fade, trim/overlap |
| `TRAILING`, explicit terminal planned silence yalnız sol intent'e bağlı | `PRESERVE_SILENCE` / `NONE` | `protected_silence_samples = silence.end - silence.start > 0`; left bound eventin iki kanal outgoing physical edge'i exact `0`; diğerleri sıfır; `left_event_id` bound event, `right_event_id=null` | silence `end_exclusive_sample != duration_samples`, edge-zero yok, fade/trim/overlap veya farklı bound event |
| `BETWEEN_EVENTS`, explicit planned silence iki komşuyu bağlar | `PRESERVE_SILENCE` / `NONE` | `protected_silence_samples = silence.end - silence.start > 0`; iki bound eventin de ilgili iki-kanal physical edge'i exact `0`; diğerleri sıfır | edge-zero yok, herhangi fade, trim, overlap veya silence'ı örten event |
| `BETWEEN_EVENTS`, boundary row `(CROSSFADE,CROSSFADE)` ile kabul edilen aynı-track non-speech crossfade | `OVERLAP_CROSSFADE` / `CROSSFADE` | `overlap_samples = fade_in_samples = fade_out_samples = requested_crossfade_samples > 0`; trim ve protected silence sıfır | speech, planned silence veya başka overlap |
| `BETWEEN_EVENTS`, A2/A5 solda ve sağda boundary row `(FADE_OUT,FADE_IN)`, pozitif overlap yok, silence yok | `LONG_EDITORIAL_FADE` / `NONE` | `fade_out_samples=fade_in_samples=24000`; trim, overlap ve protected silence sıfır; iki fade kendi event aralıklarında kalır | tek taraflı long fade, A1/A3/A4, crossfade veya event sınırı dışına taşma |
| `BETWEEN_EVENTS`, iki taraf A3/A5, her temas eden tarafta exact crossing var ve boundary row `(NONE,NONE)` | `HARD_CUT_ZERO_CROSSING` / `NONE` | tüm sayısal alanlar sıfır | A1/A2/A4, crossing yokken hard cut, trim veya fade |
| `BETWEEN_EVENTS`, yukarıdaki satırlardan hiçbiri | `ZERO_CROSSING_MICROFADE` / `NONE` | her taraf için 0..240 trim **veya** ilgili 240-sample microfade; overlap/protected silence sıfır | `HARD_CUT_ZERO_CROSSING` dışında pozitif overlap; belirsiz fallback |

Bir `BETWEEN_EVENTS` long-fade satırında ilgili `AudioBoundaryIntent` iki-sided
transition'ı tam olarak `(FADE_OUT, FADE_IN)` olmalıdır; yalnız bir tarafın
fade istemesi veya aynı boundary'nin `(CROSSFADE, CROSSFADE)` istemesi bu satıra
düşmez. `FADE_IN` yalnız leading ya da bu two-sided long-fade satırında,
`FADE_OUT` yalnız trailing ya da bu two-sided long-fade satırında geçerlidir.
Bunun dışında `FADE_IN`/`FADE_OUT`, short fade'e dönüşmez ve fail-closed olur.

Long editorial fade için `N = LONG_EDITORIAL_FADE_SAMPLES = 24000` ve iki
kanal için de aynı exact lineer gain uygulanır. `FADE_IN` right event'in ilk
`N` frame'inde, local `i = 0..N-1` için `gain_in(i) = i/(N-1)`; `FADE_OUT`
left event'in son `N` frame'inde kronolojik local `i = 0..N-1` için
`gain_out(i) = 1 - i/(N-1)` olur. Leading yalnız `gain_in`, trailing yalnız
`gain_out`, between-events long fade ise non-overlapping iki kendi penceresini
aynı anda uygular; iki pencere birbirine crossfade olarak karışmaz ve output
event aralığı dışına yazmaz. Her ilgili event span'i en az `N` sample olmak
zorundadır; aksi `BOUNDARY_POLICY_INVALID` olur. Çarpılmayan frame'lerin gain'i
tam `1`'dir; protected silence'ın gain'i veya sample'ı değişmez. Bu formül
renderer, encoder veya platform easing'ine devredilemez.

Zero crossing bir stereo PCM **frame sınırıdır**. Bir event içi timeline
sınırı `p` yalnız `event.start_sample < p < event.end_exclusive_sample`
olduğunda incelenebilir; iki fiziksel PCM frame'i sırasıyla
`q_left = pcm_frame(event, p - 1)` ve `q_right = pcm_frame(event, p)`dir.
Sınır ancak ve ancak her kanal için aşağıdaki predicate doğruysa geçerlidir:

```text
(x[q_left] == 0) or (x[q_right] == 0)
or (x[q_left] < 0 < x[q_right]) or (x[q_left] > 0 > x[q_right])
```

Her `x[q]`, ilgili `ReplayPcmEvidence.interleaved_samples`daki
stereo frame'dir; `q` bu bölümün Timeline→PCM formülüyle hesaplanır. Event
dışındaki timeline veya PCM frame'i hiç okunamaz.

Outgoing tarafta interior aday aralığı
`[max(event.start_sample + 1, event.end_exclusive_sample - 240),
event.end_exclusive_sample - 1]`, incoming tarafta ise
`[event.start_sample + 1, min(event.end_exclusive_sample - 1,
event.start_sample + 240)]` olur. Buna ek olarak trim sıfır yalnız gerçek
event kenarındaki PCM frame sıfırsa kabul edilir: outgoing için
`x[d + b - 1] == 0`, incoming için `x[d + a] == 0`; bunlar sign-change
testi değil explicit edge-zero testidir ve başka bir source frame'ine taşmaz.
İç adayda outgoing trim `event.end_exclusive_sample - p`, incoming trim
`p - event.start_sample`dir. En küçük trim uzaklığı seçilir; eşitlikte daha
küçük mutlak `p`, sonra `event_id` ASCII sırası seçilir. A1 narration
trimlenemez: A1 tarafında yalnız yukarıdaki explicit edge-zero ile zero trim
kabul edilir, aksi hâlde 240-sample microfade kullanılır. A2/A3/A4/A5 için
crossing bulunursa ilgili trim kayda yazılır; bulunmazsa ilgili 240-sample
microfade zorunludur. Hard-cut satırında iki temas eden taraf için de yukarıdaki
explicit zero-trim edge-zero testi sağlanmalıdır; interior crossing trim
gerektirdiği için hard-cutı yetkilendirmez. Hard cut seçildikten sonra trim
veya fade yoktur.
Microfade, `i=0..239` için lineer `i/239` gain-in ve `1-i/239` gain-out'tur;
crossfade de istenen `N` uzunluğunda lineer `i/(N-1)` / `1-i/(N-1)`
penceresini kullanır. `N=1` crossfade isteği geçersizdir
(`BOUNDARY_POLICY_INVALID`); `N >= 2` gerekir.

Click/pop acceptance oracle'ı salt “uygulama dinlemesi” değildir. Checked-in
sentetik PCM fixture'larında oracle'a katılan eventlerin gain'i tam `0`
millibel olmalı ve policy uygulanmadan önceki her komşu frame için her
kanaldaki mutlak fark `<= 1/64` olmalıdır. Test, yukarıdaki literal lineer
pencerelerle kararı immutable input'tan yeni bir referans tuple'a uygular;
her policy seam'i için seam öncesi/sonrasındaki tüm ardışık output frame
çiftlerinde hem sol hem sağ kanal için `abs(a-b) <= 1/64` olduğunu doğrular.
Hard cut bu oracle'ı ancak seçilen exact crossing'te geçebilir. Bu eşiğin
tek bir kanal veya tek bir frame için bile aşılması test failure'dır; warning,
epsilon genişletmesi, RMS/ortalama istisnası veya renderer-sonrası telafi
yoktur. Oracle output'u fixture testinin geçici belleğinde tutulur; compiler
ve planner PCM buffer mutate etmez veya dosya yazmaz.

Long-fade oracle'ı bu genel seam oracle'ın ayrı ve zorunlu parçasıdır:
referans tuple, yukarıdaki `i/(N-1)` ve `1-i/(N-1)` rasyonel lineer gain'leri
her kanal ve her pencere frame'ine uygular; leading/trailing/between-events
olmak üzere her geçerli long-fade satırını kapsar. Test, karar alanlarının tam
`N` olduğunu, ilk fade-in/son fade-out output frame'inin tam sıfır, son
fade-in/ilk fade-out gain'inin tam bir olduğunu, pencere dışının
değişmediğini ve penceredeki ardışık gain farkının tam `1/(N-1)` olduğunu
doğrular. Ardından generated output'ta boundary etrafındaki tüm komşu stereo
frame çiftlerine aynı `MAX_SEAM_CHANNEL_DELTA` kuralı uygulanır. Renderer
sonrası farklı easing, long fade'i sadece metadata kabul etmek veya bu oracle'ı
atlamak acceptance failure'dır.

## 6. Deterministik derleme, kimlik ve serializasyon

İmza:

```text
compile_audio_edl(*, video_edl: VideoEdlArtifact,
                  word_to_frame: WordToFrameArtifact,
                  narration_audio: AudioArtifact,
                  intents: tuple[AudioPlacementIntent, ...],
                  boundary_intents: tuple[AudioBoundaryIntent, ...],
                  sources: tuple[ReplayPcmSource, ...],
                  pcm_evidence: tuple[ReplayPcmEvidence, ...],
                  planned_silences: tuple[AudioPlannedSilence, ...],
                  internal_pcm_format: InternalPcmFormat) -> AudioEdlArtifact
```

Root artifact, doğrudan materialized dependency çiftlerini de taşır:
`word_to_frame_id/hash`, `narration_audio_id/hash` ve
`narration_audio_media_byte_hash`. Bu alanlar sırasıyla supplied
`WordToFrameArtifact.word_to_frame_id/hash` ile
`AudioArtifact.audio_artifact_id/hash/media_byte_hash` değerlerine exact
eşleşir. `video_edl_id/hash` için de aynı exact eşleşme uygulanır. Root'taki
project/document/narration revision ID+hash, üç dependency'nin ortak lineage'i
ile eşleşmelidir; hiçbir ID veya hash nested event/source alanından çıkarılamaz
ya da ikame edilemez. Böylece root JSON tek başına hangi kabul edilmiş video,
word-grid ve narration-audio kanıtının tüketildiğini gösterir.

Root, bunlara ek olarak Bölüm 2'de tanımlanan immutable `sources`,
`pcm_evidence`, `boundary_intents` ve `planned_silences` snapshot'larını taşır;
ayrıca yalnız bu immutable girdilerden türetilmiş `boundary_decisions`
projection'ını taşır. Loader ve Faz 4 resolver bu dört input snapshot'ını
compile çağrısındaki yan argümanların kopyası saymaz:
artifact'in tanımlayıcı girdileridir. `load_audio_edl` supplied
`sources`/`pcm_evidence`/`boundary_intents`/`planned_silences` değerlerinin
her birini embedded snapshot ile dataclass-fieldwise exact karşılaştırır;
ek, eksik, farklı sıralı, farklı delay/padding/format/frame sayılı veya aynı
ID/hash'li ama farklı PCM scalar içeren kayıt `DEPENDENCY_CONTENT_DRIFT` ile
ilgili `/sources/<uint32>` ya da `/pcm_evidence/<uint32>` pointer'ında
fail-closed olur. Embedded snapshot eksik ya da event'in source_id'sini
çözemiyorsa `STRUCTURE_INVALID` ile `/` pointer'ında fail-closed olur.
`planned_silences` için ek/eksik/field drift veya canonical sıra/ordinal drift
ilgili `/planned_silences/<uint32>` pointer'ında `DEPENDENCY_CONTENT_DRIFT`
ile fail-closed olur; shape/order ihlâli expected artifact türetilmeden önce
bulunursa aynı pointer'da `ORDERING_INVALID` kazanır. Embedded
`boundary_decisions` caller inputu değildir: loader onu validated embedded
input snapshot'larından `plan_audio_boundaries` ile yeniden üretir ve
fieldwise exact karşılaştırır. Bir kararın eklenmesi, çıkarılması, sırasının
değişmesi veya herhangi bir policy/transition/trim/fade/overlap/protected-
silence alanının drift'i ilgili `/boundary_decisions/<uint32>` pointer'ında
`DEPENDENCY_CONTENT_DRIFT` ile fail-closed olur.

Derleyici önce gerçek materialized dependency’leri ve immutable
source/evidence/boundary-intent/planned-silence snapshot’ını serialize eder;
content drift, lineage, video FPS, sequence
ID/bounds ve A1 metadata binding’ini kontrol eder. Sonra source/evidence
map'ini bir kez indeksler, word map'ini bir kez indeksler, caller sırasını
doğrular, cue sample aralıklarını WordToFrame'den türetir, **her intent için
sequence bound'unu ordering/collision'dan önce** ve `end - start == source_out
- source_in` eşitliğini doğrular; yalnız sonra her trackte tek geçişle saf
boundary key setini materialize eder, `boundary_intents` complete-set
shape/binding/order kontrolünü yapar ve yalnız sonra saf boundary helper
kararlarını çıkarır. Helper ağaç/yinelenen arama yapmaz; validated canonical
boundary row'larını yalnız bir kez lineer geçer.
Per-sample output buffer, per-frame allocation, quadratic pair scan, media I/O
veya history cache yoktur. Karmaşıklık
`O(W + I + S + B)` zaman/bellektir (`W` word lookup, `I` intent, `S` source,
`B` boundary); zero-crossing taraması event başına sabit 240 sample pencere ile
sınırlandırılır.

Event kimliği canonical projection’ın SHA-256’sından `aevt_` + ilk 32 hex;
artifact kimliği `aedl_` + ilk 32 hex olur. Event projection, source
snapshot'tan yalnız `source_id`, `source_media_hash` ve
`normalized_pcm_evidence_hash`yi tekrar etmez; event'in diğer temporal alanları
ile birlikte artifact-içi snapshot'a bağlanır. Artifact projection, root
`sources`, `pcm_evidence`, `boundary_intents`, `planned_silences` ve
`boundary_decisions` tuple'larının tam canonical projection'ını içerir;
dolayısıyla source media hash'i, evidence hash'i, PCM scalar/format/frame,
delay/padding veya sıradaki tek-bit drift; boundary ID/position/intent
binding/two-sided transition/crossfade drift'i; planned-silence
ordinal/binding/range drift'i veya derived karar policy/transition/field
drift'i dahi hem artifact hash/ID'sini hem load sonucunu değiştirir. Projection
yalnız kendi türetilmiş `event_id`/
`event_hash` veya `audio_edl_id`/`audio_edl_hash` alanını çıkarır; dependency,
event ve embedded snapshot alanı çıkarılamaz.
JSON sorted-key, compact UTF-8 canonical formdur; tüm enumlar
string değeriyle, tuple’lar array olarak yazılır. Successful compile/load exact
immutable object + bytes’ı weak-reference registry’ye alır. Serializasyon
yalnız canlı registry artifact’i kabul eder; drift `CONTENT_DRIFT`, kayıt dışı
nesne `NOT_MATERIALIZED` olur. Fallback serialization yasaktır.

`load_audio_edl(source: bytes, *, video_edl, word_to_frame, narration_audio,
intents, boundary_intents, sources, pcm_evidence, planned_silences,
internal_pcm_format)`
expected artifact’i bağımsız türetir.
Doğrulama önceliği: exact bytes type; UTF-8/BOM/duplicate-key/grammar/canonical
lexical form; root/nested exact shape; literal/enum; dependency serialization
ve binding; embedded source/evidence/boundary-intent snapshot exact binding;
cue/source
türetimi ve **her event sequence bound**; intent ordering; complete
boundary-intent shape/binding/order; track/speech collision ve boundary
kuralları; event identity; root identity; independently derived exact
byte equality. Bu sırada ilk hata
kazanır.

`AudioEdlContractError(pointer, reason, issue_code=None)` `ValueError`’dır ve
metni tam olarak `Audio EDL rejected: <REASON>` olur. Nedenler tam olarak:

```text
STRUCTURE_INVALID, UNSUPPORTED_VALUE, DEPENDENCY_CONTENT_DRIFT,
DEPENDENCY_BINDING_INVALID, CUE_RESOLUTION_INVALID,
ENCODER_COMPENSATION_INVALID, PCM_EVIDENCE_INVALID, TRACK_COLLISION, SPEECH_COLLISION,
SEQUENCE_BOUNDS_INVALID, ORDERING_INVALID, BOUNDARY_POLICY_INVALID, NON_CANONICAL_SERIALIZATION, IDENTITY_MISMATCH,
CONTENT_DRIFT, NOT_MATERIALIZED
```

Pointer seti `/`, `/video_edl`, `/word_to_frame`, `/narration_audio`,
`/sources/<uint32>`, `/pcm_evidence/<uint32>`, `/intents/<uint32>`,
`/boundary_intents/<uint32>`, `/planned_silences/<uint32>`,
`/tracks/<uint32>/events/<uint32>` ve
`/boundary_decisions/<uint32>` ile sınırlıdır. Hata mesajında hostile input,
path veya PCM bytes yer almaz.

## 7. Gerekli REPLAY fixture ve test kanıtı

Uygulama aşağıdaki yeni dosya sınırıyla kalır:

```text
engine/contracts/audio_edl.py
engine/contracts/__init__.py                 # yalnız public re-export
tests/fixtures/phase3/audio_edl_replay_v1.json
tests/fixtures/phase3/audio_edl_pcm/*.wav    # küçük, lisanssız sentetik PCM
tests/test_audio_edl.py
tests/test_audio_edl_replay.py
```

Fixture, Faz 3A compact gerçek chain’ini tüketir ve A1–A5’in her birinde en az
bir event taşır. A1 planned silence, A2 crossfade, A3 zero-crossing hard cut,
A4 explicit speech collision rejection örneği, A5 microfade içerir. Ayrıca
encoder delay/padding sıfır olmayan ayrı küçük kaynak ve 30/1 ile 30000/1001
video-grid örnekleri bulunur. Fixture PCM’leri sentetik, kısa, checked-in
olmalı; production audio, provider credential, URL veya gerçek kaynak konuşması
içermez.

Focused testler şunları kanıtlar:

1. exact public yüzey, literal/enum/dataclass alan sırası, canonical golden ve
   hash/ID yeniden hesaplaması; root video/word-to-frame/narration-audio
   ID+hash+media-byte-hash provenance binding'i;
2. 48 kHz stereo internal format, rational video-frame→sample dönüşümü ve
   A/V farkı bir frame altında; A1 exact cue-span eşitliği ile A2–A5 cue anchor
   başlangıç kuralının (olay sonu cue sonundan farklı olabilir) ayrı oracles;
3. fixed A1–A5 registry, track/kind eşleşmesi, cross-track layering,
   boş-track serializasyonu, same-track collision ve A1/A4 speech collision
   rejection;
4. delay/padding compensation, source-media hash ile normalized-PCM-evidence
   hash ayrımı, immutable checked-in PCM evidence binding'i, WordToFrame'den
   türetilen word-ID cue mapping, TTS word sınırının kesilmemesi ve explicit
   planned silence preservation ve PRESERVE_SILENCE için her bound eventin
   iki-kanal exact physical edge-zero oracle'ı;
5. each boundary policy/transition null-or-zero matrix, requested crossfade
   sample sayısı/eşitliği, canonical immutable `AudioBoundaryIntent` complete-set
   binding'i, terminal ve between boundary'lerin independent two-sided transition
   input'u ve tek yetkili overlap algoritması, serializable leading /
   between-events / trailing terminal boundary kayıtları, zero-crossing bounded
   search, microfade/crossfade decision, planned-silence ID/komşu-intent/event
   binding'i, terminal/two-event canonical boundary-key uniqueness (ikinci
   silence row'u `/planned_silences/<uint32>` + `BOUNDARY_POLICY_INVALID`),
   PCM discontinuity/click-pop oracle;
6. dependency/content drift, source-media veya PCM-evidence hash mismatch,
   boundary-intent ID/ordinal/order/position/adjacency/transition/crossfade
   drift veya missing/extra row; planned-silence ID/ordinal/strict tuple
   sırası/binding/range drift'i ile derived boundary-decision
   policy/transition/field/order/missing/extra row drift'i,
   loader precedence, duplicate
   keys/noncanonical bytes, identity mismatch, weak registry cleanup ve iki
   bağımsız compile’ın byte/hash eşitliği;
7. static import guard: `subprocess`, `ffmpeg`, `remotion`, network client,
   provider, filesystem write ve Faz 4/Faz 8/Faz 11 modülleri yasaktır.
8. `sample_at_frame` yalnız materialized `video_edl` local clock'ını kullanır:
   aynı nominal süreli fakat farklı FPS, non-local/global frame ve
   `word_to_frame` FPS/sequence mismatch'i `/video_edl`
   `DEPENDENCY_BINDING_INVALID` ile reddedilir; iki kabul edilen FPS örneğinde
   `duration_samples == sample_at_frame(video_edl.duration_frames)` exacttır.
9. `plan_audio_boundaries`e geçirilen `duration_samples` olmadan terminal
   karar üretilemez; forged track-sonu süresi, farklı helper süresi, leading ve
   trailing terminal silence sınırı ile root duration uyuşmazlığı fail-closed
   olur. Compile/load aynı helper inputuyla byte-byte aynı terminal kararları
   üretir.
10. registrydeki source ile yalnız `source_id`/hash'i aynı olan fakat raw
    metadata, delay/padding veya normalized frame sayısı farklı bir
    `intent.source` `/intents/<uint32>` `DEPENDENCY_BINDING_INVALID` ile
    reddedilir; compiler registry değerleriyle sessiz replacement yapmaz.
11. A1 için audio artifact ID/media hash ile birlikte decoded raw sample-rate,
    channel-count ve sample-frame-count binding'i test edilir. Her bir alan
    bağımsız olarak forged edildiğinde `/narration_audio`
    `DEPENDENCY_BINDING_INVALID` alınır; normalized PCM evidence formatı ile
    upstream decoded metadata'nın farklı olabildiği kabul fixture'ı ayrıca
   kanıtlanır.
12. leading, trailing ve between-events `PRESERVE_SILENCE` örneklerinin her
    bound event tarafında iki kanalda exact `0` edge PCM frame'i taşıdığı;
    yalnız bir kanal, sign-change, interior crossing, epsilon veya gain ile
    ikamenin `/planned_silences/<uint32>` `BOUNDARY_POLICY_INVALID` verdiği
    negatif testlerle kanıtlanır. Aynı terminal/two-event boundary key'ine
    ikinci silence eklenmesi de sonraki silence row'unda aynı hata/pointer ile
    fail-closed olur.
    Leading, trailing ve between-events için ayrı negatif geometri oracle'ı,
    ilgili bound event kenarını silence sınırından bir sample bile uzaklaştırır;
    between-events örneği ayrıca direct-adjacent olmayan intent binding'i
    kullanır. Her varyant exact `/planned_silences/<uint32>` pointer'ında
    exact `BOUNDARY_POLICY_INVALID` reason'ını vermelidir; unowned-gap veya
    terminal-uç ihlâli başka bir pointer/reason'a dönüşemez.
13. her başarılı artifact'in root `sources`, `pcm_evidence`,
    `boundary_intents` ve `planned_silences` snapshot'ı fixture girdisiyle
    field-wise exacttır; `boundary_decisions` aynı embedded immutable girdiler
    ile helper tarafından yeniden türetildiğinde field-wise exacttır. Canonical
    artifact JSON'dan tek
    başına `event -> source -> evidence` çözümü, `d+a+(t-e)` physical PCM
    frame'i ve format/frame sınırı yeniden hesaplanır. Embedded PCM scalar,
    format, sample-frame, source-media/evidence hash, delay veya padding'in
    her biri tek başına drift edildiğinde artifact hash/ID değişir; eski bytes
    `load_audio_edl` tarafından ilgili snapshot pointer'ında fail-closed olur.
    Aynı `source_id`/hash taşıyan ama farklı raw metadata, delay/padding,
    frame sayısı veya PCM scalar içeren supplied source/evidence, embedded
    snapshot yerine kabul edilmez. Planned-silence veya boundary-decision
    projection'ındaki tek alan/sıra drift'i artifact hash/ID'yi değiştirir;
    preserved eski bytes `load_audio_edl` tarafından ilgili pointer'da
    `DEPENDENCY_CONTENT_DRIFT` ile fail-closed olur.
14. sequence-bound negative oracles, aynı intentte ordering/collision'a uygun
    görünse bile `end_exclusive_sample > duration_samples`, overflow, boş/ters
    veya negative candidate aralığı için `/intents/<uint32>`
    `SEQUENCE_BOUNDS_INVALID` verir. Test spy/oracle'ı bu eventin canonical
    ordering anahtarına, track/crossfade/speech collision geçişine veya
    `plan_audio_boundaries` çağrısına hiç ulaşmadığını kanıtlar; loader aynı
    önceliği preserved bytes için uygular.
15. `PCM_F32LE` canonicalizer pack→unpack→finite/exact-equality kuralını
    bağımsız uygular: exact binary32 değer geçer; binary64'e özgü yuvarlanacak
    değer, overflow, `-0.0`, NaN ve ±infinity `PCM_EVIDENCE_INVALID` ile
    fail-closed olur. WAV data bytes ile `ReplayPcmEvidence` scalar tuple'ı
    aynı kural altında byte-for-byte eşleşir.
16. Bir eventin leading ve trailing boundary'lerinin farklı transition
    semantics taşıdığı fixture (ör. leading `FADE_IN`, trailing `FADE_OUT`) ve
    iki komşu event için `(FADE_OUT,FADE_IN)` ile `(CROSSFADE,CROSSFADE)`
    ayrı oracles ile kanıtlanır. Event-level transition alanı, missing/extra
    boundary row, swapped left/right side, terminal null matrix, non-adjacent
    binding, duplicate key/ID, noncanonical boundary tuple order ve sadece
    bir tarafın fade/crossfade istemesi `/boundary_intents/<uint32>`
    `BOUNDARY_POLICY_INVALID` veya `ORDERING_INVALID` ile fail-closed olur.

Faz 3 acceptance öncesinde Faz 3A focused suite + bu iki suite + Faz 2 temporal,
preview ve collision upstream suite’leri + top-level non-FastAPI broad regression
çalışmalıdır. Bağımsız adversarial audit; floating-point drift, off-by-one
half-open boundary, overlap’ın silence’ı kapatması, source hash substitution,
A1/A4 collision, PRESERVE_SILENCE physical edge-zero/duplicate-boundary-key
rejection, malformed canonical JSON ve click/pop oracle’ını özellikle
incelemelidir.

## 8. Faz sınırı ve sonraki adım

Bu belge implementation yetkisi veya Faz 3 closure değildir. Ses planı,
Faz 4 renderer/mux’unu başlatmaz; gerçek source-audio selection/ducking/loudness
policy’si Faz 11’dedir. Faz 3 ancak Faz 3A video EDL ve bu Faz 3B audio planı
birlikte kabul edilmiş, REPLAY E2E kanıtı üretilmiş ve ana acceptance belgeleri
güncellenmişse kapanabilir.

```text
SPECIFICATION_STATUS=CANDIDATE
SPECIFICATION_DRAFTED=YES
SPECIFICATION_ACCEPTED=NO
IMPLEMENTATION_AUTHORIZED=NO
PHASE3B_CLOSED=NO
NEXT_ACTION=INDEPENDENT_READ_ONLY_SPECIFICATION_AUDIT
```
