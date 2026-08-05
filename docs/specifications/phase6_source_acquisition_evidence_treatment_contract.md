# Faz 6 — Source Acquisition ve Evidence Treatment Contract

Durum: Uygulama sözleşmesi

Bu sözleşme, Faz 6'nın sınırlarını belirler. Acquisition katmanı bir anti-bot
veya paywall aşma sistemi değildir. Varsayılan çalışma biçimi `REPLAY`dir:
adapter'lar yalnızca önceden yakalanmış, hash'i verilmiş source package'larını
işler. Canlı ağ istemcisi, kuyruk/retry altyapısı, browser extension ve Studio
UI bu fazın dışında kalır.

## Core ve domain sınırı

Core, adapter kimliklerini, erişim durumlarını, hash/lineage'i, target-region
doğrulamasını ve deterministic fallback kararını taşır. Source type sırası ve
planner'a geçmek için zorunlu primary source koşulu yalnız seçili Domain Pack'in
resolved policy snapshot'ından `SourcePriorityPolicy` ile gelir. Core'da
domain adına göre dallanma yoktur; policy yoksa ranking/gate fail-closed olur.

## Güvenli acquisition girişleri

- URL yalnız canonical HTTP(S) kaynak tanımlayıcısıdır; bu fazda ağ isteği
  yapılmaz.
- Source package, adapter, source type, erişim statüsü, source label, tarih,
  exact document text ve hash'lenmiş snapshot referansını birlikte taşır.
- Canlı ingress eklendiğinde SSRF/private-address, redirect, MIME, byte-size,
  timeout ve TLS denetimleri adapter dışındaki bir transport sınırında zorunlu
  uygulanacaktır. Bu gelecekteki çalışma, Faz 6'nın `REPLAY` kabulünü zayıflatmaz.
- Cloudflare/DataDome, CAPTCHA, yetkisiz paywall ve fingerprint bypass asla
  denenmez. Bu sinyaller capture değil fallback üretir.

## Statü ve fallback matrisi

| Access status | Deterministic fallback |
| --- | --- |
| `accessible`, `text_found` | `NO_FALLBACK` |
| `snapshot_available` | `SNAPSHOT_EVIDENCE` |
| `challenge_detected`, `paywall_detected`, `cookie_wall_detected`, `authentication_required`, `manual_capture_required` | `MANUAL_CAPTURE_PACKAGE` |
| `text_not_found` | `TEXT_ONLY_EVIDENCE` |
| `unavailable` | `BLOCK_PLANNER` |

Challenge, paywall ve benzeri statülerde snapshot/render input'u kabul edilmez;
dolayısıyla challenge ekranı final preview'a giremez. `target_text` document
içinde tam ve tekil eşleşmiyorsa adapter koordinat üretmez; `text_not_found`
fallback'ine geçer. Tahmin edilmiş selector, crop veya coordinate yasaktır.

## Evidence ve lineage

`SourceCapturePlan` source URL'si, adapter, status, fallback, package hash'i,
target DOM path'i, region/scroll/highlight event'leri, source label ve tarihini
taşır. Snapshot kullanılıyorsa hash zorunludur. Planın stable ID'si ve hash'i
tüm bu projection üzerinden üretilir. Source preview yalnız capture planından
üretilir; host dosya yolu veya ham challenge HTML'i taşımadığı için renderer'a
erişim bypass'ı sunmaz.

`EvidenceTreatmentPlanner`, direct veya snapshot kanıt için sağlanan bölgeler
üzerinden `full_page`, `headline`, `target_paragraph`, `sentence_highlight` ve
`number_callout` focus event'leri oluşturur. Aynı belgede en az üç farklı
region, üç ayrı focus event olarak korunur. Text-only veya manual fallback,
koordinat içermeyen source-label/date evidence card üretir.

## Kabul oracle'ları

1. challenge paketinin preview üretimi reddedilir;
2. missing/ambiguous target text coordinate üretemez;
3. tek document için üç farklı doğrulanmış region üç focus event üretir;
4. paywall/challenge sadece loglanmaz, status-to-fallback matrisi ile sonuçlanır;
5. `FeedApiAdapter` browser/Playwright olmadan evidence üretir;
6. iki policy snapshot farklı source ranking üretirken adapter sınıfları aynı kalır;
7. mandatory primary source türü bulunmadığında planner gate `BLOCKED` döner.
