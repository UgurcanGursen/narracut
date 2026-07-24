# Codex İlk Görev Promptu — Faz 0 Baseline ve Proje Hafızası

Repo kökündeki `AGENTS.md` ile `docs/MASTER_ROADMAP.md` dosyalarını baştan sona oku ve bunları bağlayıcı kabul et.

## Aktif görev

Yalnızca **Faz 0 — Baseline Dondurma ve Proje Hafızası** görevini uygula.

Bu görevde yeni renderer, V3 schema, FastAPI, React UI, Domain Pack implementation, source acquisition, planner veya yeni görsel özellik geliştirme. Mevcut kodu geniş çaplı refactor etme ve klasörleri topluca taşıma.


## Kullanıcı tarafından doğrulanmış mevcut runtime mimarisi

Aşağıdaki bilgiler mevcut sistem hakkında kullanıcı tarafından doğrulanmıştır.

Bunları başlangıç gerçeği olarak kabul et; yine de kodu inceleyerek doğrula. Kodda bir çelişki görürsen mimariyi kendiliğinden değiştirme. Çelişkiyi dosya, sembol ve çağrı zinciri referanslarıyla raporla.

### Public entrypoint

Repository kökündeki:

```text
main.py
```

dosyası sistemin ana kurgu motoru değildir.

Kök `main.py` yalnızca:

- terminalden verilen kullanıcı komutlarını ve argümanları alır,
- input/timeline dosyasını belirler,
- mevcutsa `timeline.json` veya ilgili timeline input’u için validation akışını çalıştırır,
- gerçek video üretim işini `v2/main.py` içindeki `process_timeline` fonksiyonuna devreder.

Kök `main.py` şu anda:

```text
thin CLI wrapper
public entrypoint
delegation layer
```

olarak değerlendirilmelidir.

### Canonical mevcut engine

Sistemin mevcut gerçek kalbi ve aktif production pipeline implementasyonu:

```text
v2/main.py
```

dosyasıdır.

Ana orchestration fonksiyonu:

```text
v2.main.process_timeline
```

olarak doğrulanmalıdır.

`v2/main.py` Faz 0 kapsamında:

```text
ACTIVE LEGACY PRODUCTION ENGINE
```

olarak sınıflandırılmalıdır.

Buradaki `legacy` ifadesi:

- kullanılmayan,
- terk edilmiş,
- güvenle silinebilir,
- önemsiz eski kod

anlamına gelmez.

Şu anlamlara gelir:

- mevcut çalışan ana motordur,
- yeni mimarinin migration kaynağıdır,
- baseline ve davranış referansıdır,
- yeni core doğrulanana kadar korunmalıdır,
- Faz 0 sırasında taşınmamalı, yeniden adlandırılmamalı veya parçalanmamalıdır.

### Doğrulanacak çağrı zinciri

Faz 0 kapsamında özellikle şu akışı koddan doğrula:

```text
root/main.py
→ CLI / input argument parsing
→ timeline loading
→ timeline validation
→ v2.main.process_timeline
→ downstream pipeline modules
→ generated artifacts / reports / final output
```

Bu zincirde:

- import edilen gerçek modülleri,
- çağrılan önemli fonksiyonları,
- input ve output dosyalarını,
- error/validation davranışını,
- cache ve temp kullanımını

dosya ve fonksiyon referanslarıyla belgele.

Aşağıdaki dosyalarda wrapper ile gerçek engine ayrımını açıkça göster:

```text
docs/CURRENT_STATE.md
docs/ARCHITECTURE_DECISIONS.md
baseline/baseline_manifest.json
baseline/dependency_graph.md
```

Faz 0 sırasında kök `main.py` ile `v2/main.py` arasındaki delegation yapısını değiştirme.

## Mevcut repo hakkında başlangıç bilgisi

Repo kökünde şu yapı görülüyor:

```text
assets/
cache/
output/
temp_assets/
templates/
tests/
v2/
.gitignore
download_assets.py
ibm_v3_native.json
main.py
norm_words_debug.json
requirements.txt
run_verification.py
test_1_min.json
timeline.json
whisper_debug.json
```

Bu listeyi kesin veya eksiksiz kabul etme; gerçek repository’yi kendin incele.


## Çalışmaya başlamadan önce yazacağın kısa plan

Herhangi bir dosya oluşturmadan veya değiştirmeden önce kısa biçimde şunları yaz:

1. Anladığın aktif faz
2. Kök `main.py` ile `v2/main.py` arasındaki mevcut ilişki
3. Kapsam içi işler
4. Kapsam dışı işler
5. Kullanacağın acceptance kriterleri
6. İnceleyeceğin temel dosya ve komutlar

Bu ön açıklama kısa olmalı; uzun bir tasarım belgesine dönüşmemelidir.

## Yapılacaklar

1. Git durumunu ve repository ağacını incele. Mevcut dosyaları silme veya değiştirmeden önce çalışma ağacındaki kullanıcı değişikliklerini tespit et.
2. Gerçek entrypoint’leri ve delegation zincirini doğrula. Özellikle:
   - public CLI entrypoint’in kök `main.py` olup olmadığını,
   - canonical engine entrypoint’in `v2/main.py` olup olmadığını,
   - ana orchestration fonksiyonunun `v2.main.process_timeline` olup olmadığını,
   - wrapper → validation → `process_timeline` çağrı zincirini,
   - `process_timeline` tarafından kullanılan önemli downstream modülleri,
   - üretilen output, report, cache ve temp artifact’lerini

   dosya ve sembol referanslarıyla belgele.

   Kök `main.py`yi ana motor, `v2/main.py`yi ise önemsiz veya silinebilir eski kod olarak sınıflandırma.
3. Mevcut çalıştırma ve test komutlarını koddan/README’den keşfet. Komut uydurma.
4. Güvenli ve makul ise mevcut testleri ve en kısa mevcut fixture/verification akışını çalıştır. Uzun veya maliyetli render gerekiyorsa önce nedenini raporla; ticari LLM API çağrısı yapma.
5. Mevcut baseline’ı değiştirmeden aşağıdaki proje hafıza dosyalarını oluştur veya gerçek bulgularla güncelle. `CURRENT_STATE.md` ve `ARCHITECTURE_DECISIONS.md` içinde kök wrapper ile aktif `v2` engine ayrımını açıkça kaydet:

```text
docs/CURRENT_STATE.md
docs/KNOWN_LIMITATIONS.md
docs/ARCHITECTURE_DECISIONS.md
docs/QUALITY_BENCHMARKS.md
docs/PHASE_ACCEPTANCE.md
docs/CHANGELOG.md
docs/NEXT_ACTIONS.md
docs/DOMAIN_PACKS.md
```

6. Aşağıdaki baseline artifact’lerini oluştur:

```text
baseline/baseline_manifest.json
baseline/v2_2_schema_snapshot.json       # gerçek bir V2.2 schema/input bulunabiliyorsa
baseline/dependency_graph.md
baseline/domain_assumption_inventory.md
baseline/target_directory_map.md
```

7. `baseline_manifest.json` içine en az şunları kaydet:

```text
repository revision veya mevcut git durumu
aktif branch ve working tree durumu
Python/runtime ve platform bilgisi
public CLI entrypoint
canonical engine entrypoint
main orchestration function
verified delegation chain
keşfedilen diğer entrypoint’ler
çalıştırılan komutlar
önemli fixture/input dosyaları
mevcut output ve report türleri
hash alınması makul olan baseline dosyalarının SHA-256 değerleri
test/verification sonuçları
bilinen environment bağımlılıkları
external binary/tool bağımlılıkları
network/API requirement durumu
```

Kodla doğrulandığı ölçüde manifest’te şu sınıflandırma açıkça yer alsın:

```json
{
  "public_cli_entrypoint": "main.py",
  "canonical_engine_entrypoint": "v2/main.py",
  "main_orchestration_function": "v2.main.process_timeline",
  "engine_classification": "active_legacy_production_engine"
}
```

Kod bu bilgilerle çelişirse sahte biçimde yazma; `verification_status` ve çelişki açıklaması ekle.

8. `domain_assumption_inventory.md` içinde mevcut kodu tarayarak bulduğun varsayımları şu üç gruba ayır:

```text
CORE CANDIDATE
BUSINESS-TECH PACK CANDIDATE
ACTIVE LEGACY PRODUCTION ENGINE
LEGACY / TECHNICAL DEBT
```

Örnek inceleme alanları:

- IBM, şirket, gelir, hisse, yatırımcı gibi hard-coded terimler
- business-specific visual veya chart türleri
- prompt metinleri
- asset arama sorguları
- validation kuralları
- JSON alanları ve enum’lar

`ACTIVE LEGACY PRODUCTION ENGINE` grubunda özellikle:

```text
root/main.py delegation path
v2/main.py
v2.main.process_timeline
aktif runtime için zorunlu downstream modüller
```

belgelenmelidir.

Bu grup “sil” anlamına gelmez. Aktif baseline, migration kaynağı ve parity referansı anlamına gelir.

Bir dosyayı yalnızca `v2/` altında bulunduğu için technical debt olarak işaretleme.

Bu görevde bunları taşımaya veya düzeltmeye çalışma; yalnızca dosya, sembol ve mümkünse satır referanslarıyla envanterle.

9. `target_directory_map.md` içinde roadmap’e uygun hedef yapıyı öner; fakat mevcut dosyaları henüz taşıma. En az şu sınırları göster:

```text
docs/
shared-schemas/
domain-packs/business-tech/
studio-api/
studio-ui/
engine veya mevcut Python core sınırı
motion-renderer/
baseline/
projects/
```

Mevcut `v2/` motorunun hedef yapıya geçişini tek seferlik taşıma olarak değil, kontrollü migration olarak göster:

```text
v2/ active engine
→ adapter boundary
→ verified replacement modules
→ parity validation
→ controlled migration
```

`v2/` klasörünü doğrudan silinecek veya topluca taşınacak klasör gibi gösterme.

10. `NEXT_ACTIONS.md` içinde aynı anda en fazla beş iş bırak ve yalnızca bir tanesini “next recommended task” olarak işaretle. Faz 1’e geçiş için eksik acceptance varsa açıkça belirt.

## Kesinlikle yapılmayacaklar

- Kök `main.py` ile `v2/main.py` arasındaki delegation yapısını değiştirme.
- `v2/main.py`yi taşıma, yeniden adlandırma, parçalama veya silme.
- `process_timeline` fonksiyonunun davranışını değiştirme.
- `v2/` klasörünü yalnızca isminden dolayı deprecated kabul etme.
- Mevcut `assets/`, `cache/`, `output/` veya `temp_assets/` klasörlerini temizleme.
- Yeni domain pack’i tam uygulama.
- Business-tech özel kodu şimdiden yeniden tasarlama.
- Spring Boot, mikroservis, Kafka, Redis veya cloud altyapısı ekleme.
- Ticari LLM/TTS/asset API’sine çağrı yapma.
- Başarısız test veya eksik artifact’i başarılı gösterme.
- Kullanıcının mevcut değişikliklerini overwrite etme.

## Acceptance kriterleri

Görev ancak şu koşullarda tamamlanmış sayılır:

- Kök `main.py`nin thin wrapper/public entrypoint olduğu koddan doğrulanmış veya çelişki açıkça raporlanmıştır.
- `v2/main.py`nin aktif legacy production engine olduğu koddan doğrulanmış veya çelişki açıkça raporlanmıştır.
- `v2.main.process_timeline` ana orchestration fonksiyonu olarak doğrulanmış veya çelişki açıkça raporlanmıştır.
- Wrapper → validation → `process_timeline` delegation zinciri belgelenmiştir.
- Mevcut çalışan durum ve entrypoint’ler belgelenmiştir.
- En az bir gerçek test/verification sonucu veya neden çalıştırılamadığına dair kanıt vardır.
- Baseline manifest ve dependency graph gerçek repository’ye dayanır.
- Domain-specific varsayımlar dosya ve sembol referanslarıyla envanterlenmiştir.
- `v2/main.py` silinebilir/deprecated kod olarak yanlış sınıflandırılmamıştır.
- Hiçbir production/fixture/output dosyası silinmemiştir.
- Geniş refactor veya faz dışı feature yapılmamıştır.
- `CURRENT_STATE.md`, `KNOWN_LIMITATIONS.md`, `PHASE_ACCEPTANCE.md`, `CHANGELOG.md` ve `NEXT_ACTIONS.md` günceldir.

## Görev sonu yanıt biçimi

Yanıtını şu sırayla ver:

1. Faz 0 sonucu
2. Doğrulanan runtime zinciri
   - public CLI entrypoint
   - canonical engine
   - orchestration function
   - delegation flow
3. Değiştirilen/oluşturulan dosyalar
4. Çalıştırılan komutlar ve sonuçları
5. Baseline hakkında önemli bulgular
6. Domain assumption inventory özeti
7. Blocker ve doğrulanamayan noktalar
8. Faz 1 readiness durumu
9. Sonraki tek önerilen görev

Sonraki görev önerisini tek bir görevle sınırla. Faz 0 acceptance tamamlanmadıysa Faz 1 implementation önermeden önce eksik baseline işini öner.
