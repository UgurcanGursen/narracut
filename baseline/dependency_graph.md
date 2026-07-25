# Baseline Dependency Graph

Tarih: 24 Temmuz 2026

## Faz 1 V3 contract boundary

```text
schema/v3/ + SchemaCatalog
        -> WorkspaceLoader
        -> DomainPackRegistry + DomainPolicyResolver
        -> typed read-only Workspace view
```

Split workspaces manifest kind/content, profile/snapshot reference and resolver
parity kontrollerinden fail-closed olarak gecer. Bu boundary V2 production
pipeline'ina import veya runtime side effect eklemez.

Domain resolution artik explicit `core_only` veya `domain_pack` modundadir.
Domain-pack yolu registry + resolver parity olmadan fail-closed olur. Loader
devaminda duplicate stable-ID, chapter-beat-sequence membership, event
track-routing ve base-shot video-track integrity kapilarindan gecer:

```text
WorkspaceLoader
  -> SchemaCatalog
  -> core_only | DomainPackRegistry + DomainPolicyResolver
  -> duplicate identity gate
  -> story hierarchy gate
  -> event/base-shot track routing gate
  -> private schema-validated typed Workspace view
```

Public artifact/retention validation boundary:

```text
raw Artifact Mapping[]
  -> caller-provided SchemaCatalog
  -> artifact.schema.json
  -> private typed construction
  -> artifact graph invariants

raw Retention Mapping
  -> caller-provided SchemaCatalog
  -> retention_policy.schema.json
  -> private typed construction
  -> retention invariants
```

Raw Mapping ile public validator cagrilari catalog dependency'si olmadan
calismaz. WorkspaceLoader kendi catalog instance'ini artifact graph validator'a
aktarir.

## Entrypoint ve delegation

```text
main.py
├─ v2.main.detect_timeline_format
├─ v2.models.convert_v1_to_v2
├─ v2.models.TimelineV2
├─ v2.models.TimelineValidator
└─ v2.main.process_timeline
```

### Root CLI dalları

```text
python main.py --validate-only <input>
→ main.run_validation
→ json.load
→ v2.main.detect_timeline_format
→ v2.models conversion/model parse
→ TimelineValidator.validate
→ report stdout
→ STOP (render delegation yok)
```

```text
python main.py <input>
→ v2.main.process_timeline
```

Kök normal dal `run_validation()` çağırmaz (`main.py:40-52`). Legacy validation
engine içinde gerçekleşir (`v2/main.py:163-193`).

## Selected closure path (Faz 0 offline reproducibility)

- Preferred root path `python main.py <input>` gercekte `v2.main.process_timeline`
  delegation'ina iner.
- Faz 0 closure kaniti icin secilen canonical symbol
  `v2.main.process_timeline` olmustur.
- Root CLI dogrudan secilmemistir; cunku fail-closed provider/network guard
  kurulumu, repo-disina run-scoped output izolasyonu ve evidence capture hook'u
  icin mevcut CLI yuzeyi ek production degisikligi sunmaz.
- `scripts/verify_phase0_offline_render.py` yalniz fixture materialization,
  isolated run root kurulumu, guard, production symbol invocation ve output
  validation islerini yapar; renderer/normalizer/encode davranisini mock etmez.

## `v2.main.process_timeline`

```text
process_timeline (v2/main.py:96)
├─ init_dirs
│  ├─ temp_assets/
│  ├─ temp_assets/tts/
│  ├─ temp_assets/v2_cache/
│  └─ output/
├─ json.load + detect_timeline_format
├─ v3_editorial?
│  ├─ acceptance asset manifest SHA-256 preflight
│  ├─ editorial_engine.set_isolated_paths
│  └─ editorial_engine.process_editorial_timeline
└─ V1/V2 legacy path
   ├─ models.convert_v1_to_v2 / TimelineV2
   ├─ models.TimelineValidator.validate
   ├─ asset_manager.init_grouping
   ├─ audio_engine.resolve_audio_for_block
   ├─ audio_engine.mix_master_audio
   ├─ audio_engine.align_narration_once
   ├─ audio_engine.find_cue_time
   ├─ visual_dispatcher.dispatch_visual
   │  ├─ asset_manager.resolve_visual_asset
   │  │  └─ youtube_state_machine / Pexels / local assets
   │  ├─ web_engine.capture_web_record
   │  ├─ modules.render_chart/render_quote/render_highlight_article
   │  ├─ video_engine visual handlers/subtitles/fallbacks
   │  └─ normalizer video/static normalization
   ├─ pacing.apply_pacing_variations
   ├─ MoviePy concatenate/composite/write (bundled imageio FFmpeg kullanılabilir)
   ├─ audio_engine.apply_bgm_ducking/normalize_lufs/SFX
   ├─ external ffprobe blackdetect (literal PATH command; warning fallback)
   └─ output/validation_report.json
```

## Active downstream module graph

| Modül | Önemli bağımlılıklar / rol |
|---|---|
| `v2/models.py` | V1/V2/editorial Pydantic modelleri ve validator'lar |
| `v2/audio_engine.py` | Edge/ElevenLabs TTS, alignment, timing, mix, LUFS |
| `v2/asset_manager.py` | local/Pexels/YouTube asset resolution, cache |
| `v2/youtube_state_machine.py` | metadata/source/clip cache ve download state |
| `v2/visual_dispatcher.py` | 13 visual type handler registry |
| `v2/video_engine.py` | text/counter/web/document/PIP/subtitle/transition |
| `v2/modules.py` | chart, quote, article/highlight render |
| `v2/web_engine.py` | HTML/browser capture |
| `v2/normalizer.py` | FFmpeg normalize; `cache/normalized` |
| `v2/pacing.py` | dynamic visual pacing; `cache/paced` |
| `v2/editorial_engine.py` | `beats` input için aktif alternate pipeline |
| `v2/completion_gate.py` | editorial acceptance closure |
| `v2/observability.py` | run/phase timing |
| `v2/pixel_validator.py` | rendered pixel validation |

## Media toolchain boundary (Faz 0.4A)

- MoviePy reader/writer çağrıları bundled `imageio-ffmpeg` executable'ını
  kullanabilir.
- `normalizer`, `ffprobe_validator`, `pacing`, `asset_manager`,
  `youtube_downloader`, `visual_dispatcher`, `pixel_validator`, `main` ve
  `editorial_engine` içinde active literal `ffmpeg`/`ffprobe` subprocess
  çağrıları vardır; mevcut codebase bunlar için config/resolver override sunmaz.
- System PATH'te her iki binary de yoktur; bundled package ffprobe sağlamaz.
  Full dependency matrix ve Faz 0.4B planı:
  `baseline/ffmpeg_ffprobe_toolchain_audit.md`.

Dispatcher tablosu (`v2/visual_dispatcher.py:547-560`):
`stock`, `youtube`, `web_record`, `chart`, `quote`, `article`,
`highlight_article`, `reddit`, `big_text`, `counter`, `black`,
`document_scan`, `image_pip`.

## Input, output, cache ve temp

### Inputs

- V1 list: `timeline.json`
- V2 blocks: `test_1_min.json`
- Faz 0 closure fixture: `baseline/fixtures/phase0_offline_full_render.json`
- Editorial beats: `ibm_v3_native.json`
- Acceptance/negative fixtures: `tests/fixtures/*.json`
- Acceptance asset manifest:
  `tests/fixtures/ibm_v3_positive_acceptance.assets.json`

### Legacy outputs

- `output/final_video_v2.mp4`
- `output/final_audio.wav`
- `output/final_audio_lufs.wav`
- `output/validation_report.json`

### Editorial outputs

`output/truthful_acceptance_closure/<run_id>/` altında final MP4, validation,
alignment, coverage, schedule, pacing, asset, source, pixel, performance,
render-path, phase timing, fixture matrix ve completion status raporları.

### Cache/temp

- `cache/pexels_*.mp4` ve fingerprints
- `cache/normalized/*.mp4`
- `cache/transitions/*.mp4`
- `temp_assets/tts/*.wav`
- `temp_assets/master_speech.wav`
- `temp_assets/bgm_ducked.wav`
- visual render ara MP4/PNG/meta dosyaları
- editorial run için `temp_assets/<run_id>/`

## Error davranışı

- Unknown format: `detect_timeline_format` `ValueError` yükseltir.
- Legacy invalid timeline: `ValueError("Timeline JSON validation failed.")`.
- Root normal CLI exception'ı yakalamaz; `v2.main` CLI yakalar ve exit 1 yapar.
- Root `--validate-only` invalid/missing sonuçlarında non-zero exit açıkça
  uygulanmaz.
- Unsupported visual type: `UnsupportedVisualTypeError`.
- `ffprobe` yokluğu blackdetect aşamasında warning ile yakalanır; kalite
  kontrolü fiilen eksik kalabilir.

## Diğer çalıştırılabilir yollar

- `python -m v2.main ...`
- `python run_verification.py`
- `python tests/run_verification.py`
- `python download_assets.py`
- `python -m v2.completion_gate ...`

Verification script'leri full render ve output yazımı yapar; Faz 0'da ağ ve
mevcut output overwrite riski nedeniyle çalıştırılmadı.

## Faz 1 V2ToV3Migrator graph

```text
V2 JSON Mapping
-> V2ToV3Migrator.migrate
   -> canonical source fingerprint
   -> deterministic source leaf pointer inventory
   -> stable ID normalization/derivation + collision gate
   -> core_only profile/snapshot
      or DomainPackRegistry + DomainPolicyResolver
   -> aggregate canonical V3 workspace construction
   -> WorkspaceLoader.validate_data
   -> canonical migration_result.schema.json validation
-> MigrationOutcome
```

```text
python -B -m engine.migration.cli migrate
-> safe input JSON read
-> explicit strict|permissive + core_only|domain_pack options
-> public V2ToV3Migrator
-> public WorkspaceLoader candidate validation
-> target-directory temporary files + atomic replace
   |-- workspace.json (yalniz basarili migration)
   |-- migration_result.json
   |-- migration_report.md
   `-- inspection_summary.txt
```

`engine/migration` V2 production modullerini import etmez ve renderer,
filesystem, network, wall-clock veya random UUID kullanmaz. V2 field inventory
`baseline/v2_2_schema_snapshot.json`, `v2/models.py`, `v2/main.py`, V2 testleri
ve Faz 0 production fixture'ina dayanir.

## Faz 1 migrator security boundary

```text
untrusted V2 source leaf
-> engine.migration.security.inspect_source_value
   |-- field-name credential family
   |-- URI user-info
   |-- sensitive query/fragment key
   |-- malformed credential-like URI
   `-- control character
-> safe reference: normal origin/URN mapping
   or secret finding:
      MIGRATION_SECRET_REDACTED / ERROR
      -> FAILED
      -> target fingerprint/workspace ID null
      -> no workspace.json
```

`write_outcome` her dosya icin atomic replace kullanir, fakat workspace/result/
report/summary seti transaction degildir. WorkspaceStore staged revision,
artifact hash verification, revision manifest, durability, commit marker veya
active-revision switch, crash recovery, previous-valid-revision preservation ve
partial staging cleanup saglamadan production persistence kabul edilmez.
