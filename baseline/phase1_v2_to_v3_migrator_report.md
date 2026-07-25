# Faz 1 V2ToV3Migrator ve Structured Migration-Loss Report

Tarih: 25 Temmuz 2026
Baslangic revision: `53389d4604127e84719b94c3eff105b61c79cdf1`
Karar: **PASS**

## Gercek V2 contract kaynaklari

Envanter kod yazilmadan once su kaynaklar karsilastirilarak cikarildi:

- `baseline/v2_2_schema_snapshot.json`: `TimelineV2`, `NarrationBlock`,
  `VisualScene`, `BgmConfig` ve `SfxConfig` alan snapshot'i.
- `v2/models.py`: aktif Pydantic modelleri, default'lar ve legacy validator.
- `v2/main.py`: `detect_timeline_format`, JSON okuma, visual unknown-field
  tasiması ve production orchestration'in gercekte okudugu alanlar.
- `tests/test_v2_core.py`: V1/V2 format ve validation davranisi.
- `baseline/fixtures/phase0_offline_full_render.json`: iki block ve dort
  locked-local visual iceren gercek Faz 0 production fixture'i.
- `scripts/verify_phase0_offline_render.py`: fixture'in production
  `v2.main.process_timeline` yolundan gecis kaniti.

Aktif orchestration `version` alanini format seciminden sonra Pydantic modelde
tutmaz; schema snapshot da root `version` tanimlamaz. Gercek Faz 0 fixture'inda
alan bulunur. Migrator bu metadata'yi sessizce kaybetmek yerine NORMALIZED
olarak source version'a baglar.

Visual `extra` acik bir V2 extension kabidir. Incelenmis
`asset_id`, `asset_mode`, `resolved_path`, `expected_sha256` alanlari V3 asset
identity/provenance alanlarina tasinir. Diger `extra` leaf'leri uydurma core
alanina kopyalanmaz; UNSUPPORTED loss kaydi alir. Root, block veya visual
contract disindaki unknown leaf ise `MIGRATION_UNACCOUNTED_SOURCE_FIELD` ile
fail-closed reddedilir.

## Field-by-field migration matrix

Classification degerleri canonical kontrollu listedendir. `WARNING` satirlari
permissive modda raporlanabilir; `ERROR` her iki modda da fail-closed'dur.

| Source pointer / field | Source type ve semantik | Destination | Classification | Donusum | Loss | Kanit/not |
|---|---|---|---|---|---|---|
| `/version` | string/number; orchestration format metadata | `/source_schema_version` | NORMALIZED | text'e normalize | NONE | Faz 0 fixture + `detect_timeline_format` |
| `/blocks` | array; narration block sirasi | story beats + sequences | SPLIT | her block bir beat/sequence | NONE | `TimelineV2.blocks` |
| `/bgm/enabled` | boolean; global BGM enable | report | UNSUPPORTED | kopyalama yok | WARNING | V3 Phase 1 audio asset yok |
| `/bgm/track_id` | string/null; BGM identity | report | UNSUPPORTED | kopyalama yok | WARNING | provenance olmadan asset uydurulmaz |
| `/bgm/gain_db` | number; mix gain | report | UNSUPPORTED | kopyalama yok | WARNING | renderer/audio mix kapsami disi |
| `/bgm/fade_in` | number; fade timing | report | UNSUPPORTED | kopyalama yok | WARNING | timing implementation kapsami disi |
| `/bgm/fade_out` | number; fade timing | report | UNSUPPORTED | kopyalama yok | WARNING | timing implementation kapsami disi |
| `/blocks/*/block_id` | string; stable block ID | beat/sequence IDs | NORMALIZED | `beat_` ve `seq_` namespace | NONE | collision fail-closed |
| `/blocks/*/narration` | string; tam narration metni | sequence/beat narrative goal | NORMALIZED | metni eksiksiz koru | NONE | Phase 1 narration document alani yok |
| `/blocks/*/audio_file` | string/null; local narration audio ref | report | UNSUPPORTED | kopyalama yok | WARNING | content hash/provenance yok |
| `/blocks/*/pause_before` | number; runtime timing | report | DROPPED | acik loss | WARNING | frame/timing Phase 2 kapsami |
| `/blocks/*/pause_after` | number; runtime timing | report | DROPPED | acik loss | WARNING | frame/timing Phase 2 kapsami |
| `/blocks/*/bgm_drop` | boolean; mix automation | report | DROPPED | acik loss | WARNING | audio mix kapsami disi |
| `/blocks/*/sfx_category` | string/null; SFX hint | report | UNSUPPORTED | acik loss | WARNING | asset/provenance yok |
| `/blocks/*/fill_policy` | string; missing visual policy | sequence fallback policy | MERGED | visual policy'lerle birlestir | NONE | fail-closed tercih korunur |
| `/blocks/*/visuals` | array; visual order | assets + edit events | SPLIT | her visual asset/event | NONE | order korunur |
| `.../type` | string; renderer visual type | asset type + event type | NORMALIZED/UNSUPPORTED | bilinen type map; bilinmeyen review placeholder | WARNING if unknown | dispatcher/model inventory |
| `.../offset_start` | number/string; block-relative start | event semantic cue | NORMALIZED/DEFAULTED | explicit offset marker; AUTO order marker | WARNING for AUTO | frame degeri icat edilmez |
| `.../offset_end` | number/string; visual end | next boundary/sequence end | NORMALIZED/DEFAULTED | explicit semantic boundary; AUTO block end | WARNING for AUTO | Phase 1 semantic cue |
| `.../clip_start` | number; source clip trim | report | DROPPED | acik loss | WARNING | renderer timing kapsami disi |
| `.../clip_end` | number; source clip trim | report | DROPPED | acik loss | WARNING | renderer timing kapsami disi |
| `.../query` | string/null; provider search provenance | asset origin URI | NORMALIZED | portable `urn:kurgu:v2-query:` | NONE | secret/path guard uygulanir |
| `.../url` | string/null; source URI | asset origin URI | NORMALIZED | URI korunur | NONE | secret query fail-closed |
| `.../target_text` | string/null; web focus payload | report | UNSUPPORTED | acik loss | WARNING | renderer parameter contract yok |
| `.../target_selector` | string/null; web selector | report | UNSUPPORTED | acik loss | WARNING | browser/render kapsami disi |
| `.../zoom` | number; renderer zoom | report | DROPPED | acik loss | WARNING | renderer kapsami disi |
| `.../scroll_duration` | number; web timing | report | DROPPED | acik loss | WARNING | timing kapsami disi |
| `.../highlight_target` | boolean; web renderer flag | report | DROPPED | acik loss | WARNING | renderer kapsami disi |
| `.../main_text` | string/null; primary text | event `parameters.text` | EXACT/UNSUPPORTED | big_text icin exact | WARNING if not representable | typed core event |
| `.../sub_text` | string/null; secondary text | report | UNSUPPORTED | acik loss | WARNING | ikinci text alani yok |
| `.../background_style` | string; renderer style | report | DROPPED | acik loss | WARNING | renderer token uydurulmaz |
| `.../accent_animation` | string; renderer animation | report | DROPPED | acik loss | WARNING | renderer kapsami disi |
| `.../logo_url` | string/null; logo source | report | UNSUPPORTED | acik loss | WARNING | ayri asset/provenance gerekli |
| `.../start_val` | number/null; counter start | report | UNSUPPORTED | acik loss | WARNING | metric contract yok |
| `.../end_val` | number/null; counter end | report | UNSUPPORTED | acik loss | WARNING | metric contract yok |
| `.../prefix` | string/null; counter text | report | UNSUPPORTED | acik loss | WARNING | renderer payload |
| `.../suffix` | string/null; counter text | report | UNSUPPORTED | acik loss | WARNING | renderer payload |
| `.../label` | string/null; counter label | report | UNSUPPORTED | acik loss | WARNING | renderer payload |
| `.../is_approximate` | boolean; counter qualifier | report | UNSUPPORTED | acik loss | WARNING | claim/metric contract yok |
| `.../max_height` | integer/null; render geometry | report | DROPPED | acik loss | WARNING | renderer kapsami disi |
| `.../crop_mode` | string/null; render geometry | report | DROPPED | acik loss | WARNING | renderer kapsami disi |
| `.../fit_mode` | string/null; render fit | report | DROPPED | acik loss | WARNING | renderer kapsami disi |
| `.../narration_cue_start` | string/null; phrase anchor | event semantic cue | NORMALIZED | phrase korunur | NONE | `semanticCue` |
| `.../narration_cue_end` | string/null; phrase boundary | report/end concept | UNSUPPORTED | acik loss if unused | WARNING | end-event contract yok |
| `.../visual_purpose` | string/null; editorial intent | base-shot purpose | EXACT/UNSUPPORTED | ilk visual exact | WARNING for later visuals | base-shot contract |
| `.../required_content` | array; visual constraint | report | UNSUPPORTED | leaf-by-leaf loss | WARNING | policy uydurulmaz |
| `.../forbidden_content` | array; visual constraint | report | UNSUPPORTED | leaf-by-leaf loss | WARNING | policy uydurulmaz |
| `.../fallback_queries` | array; provider fallback | report | UNSUPPORTED | leaf-by-leaf loss | WARNING | provider runtime kapsami |
| `.../allow_generic_stock` | boolean; fallback rule | sequence fallback policy | MERGED | block/visual policy merge | NONE | explicit review/fail-closed |
| `.../transition_in` | string/null; incoming transition | edit event type | NORMALIZED/UNSUPPORTED | hard_cut -> cut | WARNING if unknown | typed event listesi |
| `.../transition_out` | string/null; outgoing transition | report | DROPPED | acik loss | WARNING | ayri outgoing event yok |
| `.../timing_mode` | string/null; runtime timing mode | report | UNSUPPORTED | acik loss | WARNING | frame/timing kapsami disi |
| `.../trigger_cue` | string/null; phrase anchor | event semantic cue | NORMALIZED | phrase korunur | NONE | `semanticCue` |
| `.../min_duration` | number/null; runtime duration | report | DROPPED | acik loss | WARNING | timing kapsami disi |
| `.../max_duration` | number/null; runtime duration | report | DROPPED | acik loss | WARNING | timing kapsami disi |
| `.../preferred_duration` | number/null; runtime duration | report | DROPPED | acik loss | WARNING | timing kapsami disi |
| `.../subtitle_policy` | string; subtitle renderer | report | DROPPED | acik loss | WARNING | Studio/render kapsami disi |
| `.../fill_policy` | string; visual fallback | sequence fallback policy | MERGED | block policy ile birlestir | NONE | fail-closed |
| `.../asset_locked` | boolean; review/runtime hint | report | UNSUPPORTED | acik loss | WARNING | `extra.asset_mode` authoritative |
| `.../selected_asset_url` | string/null; selected source | asset origin URI | NORMALIZED | URI/portable URN | NONE | secret/path guard |
| `.../sfx_category` | string/null; SFX hint | report | UNSUPPORTED | acik loss | WARNING | audio asset yok |
| `.../sfx/enabled` | boolean; SFX enable | report | UNSUPPORTED | acik loss | WARNING | audio implementation yok |
| `.../sfx/asset_id` | string/null; SFX identity | report | UNSUPPORTED | acik loss | WARNING | provenance/content hash yok |
| `.../sfx/trigger_cue` | string/null; SFX cue | report | UNSUPPORTED | acik loss | WARNING | audio event asset yok |
| `.../sfx/gain_db` | number; SFX mix | report | UNSUPPORTED | acik loss | WARNING | mixer kapsami disi |
| `.../sfx/max_duration` | number/null; SFX duration | report | UNSUPPORTED | acik loss | WARNING | timing kapsami disi |
| `.../extra/asset_id` | string; resolved stable ID | asset/artifact IDs | NORMALIZED | `ast_`/`art_` namespace | NONE | collision fail-closed |
| `.../extra/asset_mode` | string; resolution mode | availability/review | NORMALIZED | locked_local -> local approved | NONE | Faz 0 fixture |
| `.../extra/resolved_path` | string; local provenance | asset origin URI | NORMALIZED | portable URN | NONE | absolute path output'a girmez |
| `.../extra/expected_sha256` | hex string; media hash | asset/artifact content hash | NORMALIZED | `sha256:` prefix | NONE | malformed hash invalid source |
| `.../extra/*` | arbitrary extension leaf | report | UNSUPPORTED | kopyalama yok | WARNING | open V2 extension boundary |
| contract disi root/block/visual leaf | arbitrary | none | INVALID_SOURCE | fail-closed | ERROR | `MIGRATION_UNACCOUNTED_SOURCE_FIELD` |
| secret/token/header benzeri leaf | arbitrary | redacted | DROPPED | deger kopyalanmaz | ERROR | `MIGRATION_SECRET_REDACTED` |

## Public API ve paket

```text
engine/migration/
├── models.py       # options, outcome, mapping/issue typed views, fingerprint
├── v2_to_v3.py     # pure deterministic transformation + coverage
├── reporting.py    # Markdown ve inspection summary
├── io.py           # safe read/atomic output
├── cli.py          # thin command-line adapter
└── __init__.py     # public exports
```

Public yuzey: `V2ToV3Migrator`, `MigrationOptions`, `MigrationOutcome`,
`migrate(...)`, `migrate_file(...)` ve `source_leaf_pointers(...)`.

Core migrate source mapping'i mutate etmez; filesystem/network/wall-clock/random
UUID/global mutable state kullanmaz.

## Deterministik ID ve fingerprint

- Gecerli source ID canonical prefix ile normalize edilir.
- Eksik ID canonical source JSON pointer'dan SHA-256 ile turetilir.
- Collision silent suffix almaz; source pointer listesi, target collection ve
  proposed ID ile `MIGRATION_ID_COLLISION` ERROR uretilir.
- Source/target fingerprint canonical UTF-8 JSON, sorted keys ve compact
  separators uzerinden SHA-256'dir.
- Timestamp gerektiren canonical contract alanlari wall-clock yerine
  `1970-01-01T00:00:00Z` deterministic epoch degerini kullanir.

## Domain mode

- `core_only`: registry gerekmez; `core-generic` profile ve self-consistent
  deterministic embedded snapshot uretilir.
- `domain_pack`: registry, domain ID, version ve profile explicit zorunludur.
  `DomainPackRegistry` ve `DomainPolicyResolver` gercek production
  implementation'i kullanilir.
- Core migrator'da `business-tech` literal'i yoktur. Gercek business-tech ve
  test dummy-domain pack ayni core kodla gecmistir.

Aggregate workspace embedded snapshot'i authoritative tasir. Bu nedenle
`WorkspaceLoader.validate_data(...)` eklendi ve aggregate file load embedded
snapshot'i kullanir; split workspace external snapshot/document davranisi
degismemistir.

## Strict/permissive

- Strict: DROPPED, UNSUPPORTED, AMBIGUOUS veya INVALID_SOURCE varsa FAILED;
  workspace success artifact'i yayinlanmaz.
- Strict, yalniz guvenli DEFAULTED kaydi varsa `SUCCESS_WITH_LOSS` uretebilir.
- Permissive: safe DEFAULTED/DROPPED/UNSUPPORTED warning'lari
  `SUCCESS_WITH_LOSS` olabilir.
- Her iki mod: ERROR, target invalidity, unresolved reference/collision,
  domain configuration/parity, traversal veya secret bulgusunda FAILED.

## Source-field coverage

Production `source_leaf_pointers(...)` algoritmasi sorted object key'leri ve
gercek list index'leriyle JSON leaf pointer toplar. Her leaf tam bir mapping
kaydi alir. Faz 0 demo: `67/67` leaf accounted; duplicate mapping `0`;
unaccounted `0`.

## Canonical migration result

Mevcut `migration_result.schema.json` legacy required alanlari koruyacak sekilde
minimal geriye uyumlu genisletildi. Modern result:

- migration/source/target version ve format,
- mode/resolution mode,
- source/target fingerprint,
- SUCCESS / SUCCESS_WITH_LOSS / FAILED,
- classification/severity counts,
- structured mapping ve issue listeleri,
- deterministic mapping/issue/migration IDs,
- target schema/loader validation sonucu

tasir. Legacy Faz 1 boundary sample'i schema-valid kalmistir.

## Safe IO ve CLI

Sabit output isimleri target directory icinde temporary file + `os.replace`
ile yazilir. Parent traversal reddedilir; dolu output explicit `--overwrite`
olmadan reddedilir; FAILED migration stale/partial workspace birakmaz.

```powershell
python -B -m engine.migration.cli migrate `
  --input samples/migration/v2-to-v3/input_v2.json `
  --output C:\tmp\kurgu-v2-to-v3-demo `
  --mode permissive `
  --resolution-mode core_only
```

Exit code: success/permissive loss `0`, strict policy rejection `2`, failed
migration `3`, usage/configuration `4`.

## Demo

Demo input, Faz 0 fixture ile byte-identical SHA-256'ya sahiptir:
`94b6f02910a5d74aaa19e700768df5906d9e5a79ece700da679668190a552c38`.

Sonuc:

- status: `SUCCESS_WITH_LOSS`
- workspace: 1 chapter, 2 beat, 2 sequence, 4 asset, 4 artifact, 2 track,
  4 event
- source fingerprint:
  `sha256:bf4527509e69d7425a0100437444d4f48948d296edc178f5f33773c041a7aa21`
- target fingerprint:
  `sha256:87dd15461eb9a70f2c8d336fe5f80272521ea1a2a9143981369ee58ed48d4b1f`
- mappings: 69 (67 source leaf + 2 derived root identities)
- warnings: 22
- errors/unaccounted/ambiguous: 0

## Verification

- Yeni migrator suite: `60 passed`
- Birlesik hedefli suite: `147 passed, 1 skipped`
- Full suite: `203 passed, 1 skipped`
- Demo run A/B/expected byte equality: PASS

| Artifact | SHA-256 |
|---|---|
| `workspace.json` | `14085c0dcbd3c2f130be979c062b3f9c133a767d60f3e57f06ec9a14b07546de` |
| `migration_result.json` | `0e637270c6c350a2c97f64976eb5f78d2eb05aca70f65cb3532d8fc84b34a2ef` |
| `migration_report.md` | `5df7477ddadb9cc8db29474bb3f5682cf13d78eeaced0e326102068bae8e9143` |
| `inspection_summary.txt` | `ace77c57f8f1e9579805ce780e58e78aef783b069b0c0a2c2a69b73a67dc7636` |

Degisen Faz 1 Python in-memory compile, tracked JSON parse, 16 schema
`check_schema`/ref resolution, minimal/business-tech/split sample loader,
migration demo loader/result validation, `git diff --check` ve
current/reachable generic secret scan PASS durumundadir.

## V2 mutation ve kalan Faz 1

`main.py`, `v2/`, `requirements.txt`, Faz 0 fixture/evidence ve
`scripts/verify_phase0_offline_render.py` degistirilmedi.

Faz 1 genel durumu OPEN/IN_PROGRESS kalir. Acik kapsam:

- production WorkspaceStore/persistence,
- timing/frame model implementation,
- renderer integration,
- Studio API/UI.

Sonraki tek onerilen gorev: **V3 WorkspaceStore — versioned persistence,
atomic save/load ve migration output revision management.**

## Post-audit security hardening

Independent audit sonrasi URI user-info/sensitive-query no-leak boundary,
FAILED unpublished-target metadata ve BGM/SFX exact allowlist davranislari
harden edildi. Security finding her iki modda
`MIGRATION_SECRET_REDACTED`/ERROR ile FAILED olur; raw URI veya credential
workspace/result/report/summary/CLI output'una tasinmaz. FAILED result target
fingerprint/workspace ID degerlerini null tutar ve insan tarafindan okunabilir
ciktilar workspace'in yayinlanmadigini aciklar.

Migrator output dosyalari tek tek atomic yazilir; dort-artifact seti transaction
degildir. Bu eksik WorkspaceStore staged revision ve active-revision commit
protokolunun zorunlu acceptance kriteridir.

Aggregate layout'ta embedded policy snapshot authoritative,
`policy_snapshot_ref` logical/informational identity'dir; split layout'ta
external document reference semantigi korunur.

Security hardening: PASS. WorkspaceStore entry gate:
PENDING_INDEPENDENT_REAUDIT.

Post-hardening verification: migrator `111 passed`, combined contract/migrator
`198 passed, 1 skipped`, full suite `254 passed, 1 skipped`; demo
A/B/committed expected byte equality PASS.
