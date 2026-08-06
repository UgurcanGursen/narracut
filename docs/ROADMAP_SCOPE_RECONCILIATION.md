# Yol Haritası Kapsam Uzlaştırması

Tarih: 2026-08-06

## Karar

Kabul edilen Faz 0-10 uygulamaları geçerli, sınırlı foundation kanıtları
olarak korunur. Sınırlı bir kabul, MASTER_ROADMAP'in öngördüğü uçtan uca ürün
entegrasyonlarının tamamlandığı anlamına gelmez. Bu karar hiçbir kabul edilmiş
artifact'i yeniden açmaz; ertelenen her ürün yükümlülüğüne bir sahip faz ve
test edilebilir kapanış koşulu atar.

## Kapanış sözlüğü

`FOUNDATION_ACCEPTED`, sınırlı sözleşmenin, uygulamanın ve kanıtının kabul
edildiğini belirtir. `MASTER_PHASE_CLOSED` ayrıca o faza ait tüm MASTER_ROADMAP
kriterlerinin ve o fazın sahip olduğu Deferred Delivery Ledger satırlarının
geçmesini gerektirir. `PRODUCT_GATE_CLOSED`, ancak Faz 17'de ledger açık satır
taşımıyorken ve nihai ürün kapıları geçiyorken verilebilir.

Tarihsel `CLOSED` kayıtları kendi kanıt anlamlarını korur; sessizce
`PRODUCT_GATE_CLOSED` iddiasına dönüşmez.

## Ertelenen teslimat defteri

| ID | Foundation kaynağı | Ertelenen yükümlülük | Sahip faz | Kapanış kanıtı |
|---|---|---|---|---|
| DDL-01 | Faz 1 | Dayanıklı proje workspace'i, yeniden açma ve recovery | Faz 17 | Uçtan uca proje için restart/reopen ve yarım job recovery kanıtı |
| DDL-02 | Faz 2 | Gerçek proje için güvenilir non-REPLAY timing üreticisi | Faz 17 | Seçili local veya provider üreticinin provenance, hata yönetimi ve uçtan uca timing artifact'i |
| DDL-03 | Faz 6 | Browser-bot veya erişim kontrolü bypass'ı olmadan operasyonel source transport | Faz 17, Faz 15 doğrulaması | Açık mod politikası ile timeout, byte/MIME, redirect/SSRF, retry bütçesi ve fallback kanıtı |
| DDL-04 | Faz 7 | Chart/metric artifact'lerinin seçilmiş çalıştırılabilir görsel kararına dönüşmesi | Faz 12 | Chart referansı, capability ve cue'nun deterministic executable-plan ve EDL entegrasyonunda korunması |
| DDL-05 | Faz 8 | Planner asset brief'lerinin onaylı asset/range/crop adaylarına çözülmesi | Faz 12 | Provenance, family/cooldown kuralları ve fail-closed missing-asset testleriyle policy-bound seçim |
| DDL-06 | Faz 9 | Manual task lifecycle'ın dosya/JSON yönetimi olmadan kullanılabilmesi | Faz 13 | Kalıcı proje durumuna karşı UI package, import, validation, repair ve approval akışı |
| DDL-07 | Faz 10 | Planner çıktısının somut, typed, render edilebilir multi-track EDL olması | Faz 12 | Deterministic executable plan ile mevcut Faz 3 compiler'ın iki replay'de aynı onaylı EDL'yi üretmesi |
| DDL-08 | Faz 4/14 sınırı | Cross-run artifact registry, cache ve lifecycle'ın dayanıklı olması | Faz 14 | Kalıcı dependency-aware artifact lifecycle, recovery ve cleanup kanıtı |
| DDL-09 | Faz 6/8/9 operasyonları | Gerçek source/asset/timing modunun tamamlanmış belgeselde kanıtlanması | Faz 17 | İki 10-15 dakikalık business-tech projesinin seçili modları kullanması ve provenance/license kayıtlarını export etmesi |

Hiçbir satır açık roadmap güncellemesi, kabul kanıtı ve documentation
reconciliation olmadan taşınamaz, çoğaltılamaz veya kapatılamaz.

## Zorunlu entegrasyon yolu

1. Faz 11, onaylı planner ve katalog girdilerinden policy-bound audio direction
   üretir; final EDL derlemez.
2. Faz 12, execution integration'ın sahibidir: planner artifact'leri, onaylı
   asset seçimleri, Faz 5 capability'leri, Faz 7 visualizasyonları ve Faz 11
   audio direction immutable executable editorial plan'a dönüşür; ardından
   mevcut Faz 3 compiler final EDL'yi üretir.
3. Faz 13, kalıcı proje sınırı üzerinden task/review/approval operasyonlarını
   sunar.
4. Faz 14, artifact, cache ve recovery davranışını dayanıklı hale getirir.
5. Faz 15, etkin operasyonel transport'ları doğrular; retry, limit, failure ve
   fallback kararlarını raporlar.
6. Faz 16, entegre çıktıyı referans benchmark'larla ölçer.
7. Faz 17, seçili gerçek çalışma modlarını iki uçtan uca belgeselde kanıtlar
   ve tüm ledger satırlarını kapatır.

## Koruma kuralları

- `MANUAL_UI` ve `REPLAY` birinci sınıf çalışma modları olarak kalır.
- Ticari LLM API, LLM web UI browser otomasyonu veya listelenen her source
  provider'ın desteklenmesi ürün kapanışı için zorunlu değildir.
- Etkinleştirilen her live transport açıkça seçilmeli, operasyonel güvenlik ve
  observability kapılarını geçmelidir; desteklenmeyen modlar fail-closed olur.
- Faz 12 bir entegrasyon sahibidir; Faz 3, Faz 4, Domain Pack, provenance veya
  review sözleşmelerini bypass etme izni değildir.
