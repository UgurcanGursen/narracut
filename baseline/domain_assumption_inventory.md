# Domain Assumption Inventory

Tarih: 24 Temmuz 2026

Sınıflandırma konumun adına göre değil, runtime rolüne göre yapılmıştır.
`ACTIVE LEGACY PRODUCTION ENGINE` “sil” anlamına gelmez.

## CORE CANDIDATE

| Varsayım/yetenek | Referans | Gerekçe |
|---|---|---|
| Timeline model/validation | `v2/models.py:20-219` | Domain bağımsız block/visual sözleşmesi adayı |
| Audio resolve/alignment/mix | `v2/audio_engine.py`; `v2/main.py:229-265` | Ortak medya altyapısı |
| Visual dispatch registry | `v2/visual_dispatcher.py:547-569` | Visual capability boundary adayı |
| Asset resolution/cache | `v2/asset_manager.py:177-245` | Provider/domain ayrımı sonrası core adapter adayı |
| Video normalize/pacing | `v2/normalizer.py`, `v2/pacing.py` | Domain bağımsız medya işleme |
| Output/report orchestration | `v2/main.py:504-645` | Core artifact/export adayı |
| Editorial observability/gates | `v2/observability.py`, `v2/completion_gate.py` | Domain extension destekli core validation adayı |

## BUSINESS-TECH PACK CANDIDATE

| Bulgu | Referans | Not |
|---|---|---|
| IBM acceptance fixture'ına hard-coded quality path | `v2/main.py:102-107` | Quality profile davranışı tek IBM fixture'ına bağlı |
| IBM asset manifest hard-code | `v2/visual_dispatcher.py:123` | Pack benchmark/fixture bundle'a taşınma adayı |
| IBM test asset taraması | `v2/editorial_engine.py:1332` | Business-tech benchmark içeriği |
| Generic technology/data-center fallback query | `v2/asset_manager.py:63` | Domain visual grammar/fallback policy adayı |
| Business/financial mock article | `tests/fixtures/mock_business.html:4,66-87` | Pack fixture adayı |
| IBM revenue/share/earnings narratives | `ibm_v3_native.json`; `tests/fixtures/ibm_v3_*.json` | Pack fixture/benchmark verisi |
| Business cue adversarial examples | `run_verification.py:85-88`; `tests/test_audio.py:10-41` | Domain benchmark metni; cue algorithm core kalabilir |
| Revenue/chart/source-note payload'ları | `tests/fixtures/ibm_v3_positive_acceptance.json:87-160` | Business-tech data visualization fixture |
| `stock` varsayılan/fallback yoğunluğu | `v2/models.py:123`; `v2/asset_manager.py:224-237` | Domain pack visual policy tarafından sınırlandırılmalı |

## ACTIVE LEGACY PRODUCTION ENGINE

| Bileşen | Referans | Runtime rolü |
|---|---|---|
| Root delegation path | `main.py:5-7`, `main.py:40-52` | Public CLI/import ve aktif engine çağrısı |
| Root validation-only path | `main.py:15-38`, `main.py:42-47` | Ayrı non-render validation CLI |
| Canonical orchestrator | `v2/main.py:96-645` | Legacy V1/V2 active production pipeline |
| Editorial branch | `v2/main.py:116-158` | Beats input'u active editorial engine'e delege eder |
| Model validator | `v2/models.py:101-219` | Legacy input contract ve validation |
| Downstream media modules | `v2/audio_engine.py`, `v2/asset_manager.py`, `v2/visual_dispatcher.py`, `v2/video_engine.py`, `v2/modules.py`, `v2/web_engine.py`, `v2/normalizer.py`, `v2/pacing.py` | Aktif render için zorunlu |
| Alternate editorial engine | `v2/editorial_engine.py:80-1592` | Mevcut `beats`/acceptance pipeline |

Bu bileşenler yeni core doğrulanana kadar korunmalı ve parity referansı olarak
kullanılmalıdır.

## LEGACY / TECHNICAL DEBT

| Bulgu | Referans | Risk |
|---|---|---|
| Parse etmeyen debug kopyaları | `v2/audio_engine_debug.py:393`, `v2/audio_engine_debug2.py:401` | Kaynak ağacı gürültüsü; aktif import değil |
| Kod içine gömülü non-empty provider credential | `v2/asset_manager.py:12` | Secret yönetimi ve istenmeyen ağ çağrısı riski |
| Gerçek probe olmadan “Ready” diagnostics | `v2/main.py:214-227` | Yanıltıcı environment raporu |
| Undefined görünen `VAL_REPORT_PATH` | `v2/main.py:498-501` | Asset approval failure dalında NameError riski |
| Serbest-string visual type + ayrı handler table | `v2/models.py:22`; `v2/visual_dispatcher.py:547-560` | Schema/implementation drift |
| Unknown alanları `extra` içine taşıma | `v2/main.py:166-185` | Silent contract drift/migration kaybı |
| Geniş `except: pass` blokları | `v2/main.py:578-584`; diğer media yolları | Failure visibility kaybı |
| Root validate-only exit semantics | `main.py:35-38`, `main.py:44-47` | CI için güvenilir exit code yok |
| Test/implementation dönüş tipi drift'i | `v2/asset_manager.py:34-159`; `tests/test_v2_core.py:127-136` | 1 başarısız test |
| Numeric normalization regression | `v2/audio_engine.py` `find_cue_time`; `tests/test_adversarial_alignment.py:48-55` | 1 başarısız test |

## JSON alanları ve enum benzeri varsayımlar

- V2 `VisualScene.type` string; desteklenen gerçek tipler dispatcher table'da.
- V2 varsayılanları: `allow_generic_stock=true`, `timing_mode=cue_locked`,
  `fill_policy=error`, `subtitle_policy=hide_tool_subtitles`.
- Editorial modeller `visual_type`, `visual_purpose`, cue/duration ve payload
  alanları kullanır (`v2/models.py:222-263`).
- Bu görevde hiçbir alan, prompt, query veya validation kuralı taşınmadı.

