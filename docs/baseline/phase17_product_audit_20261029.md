# Kurgu Studio — ürün ve klasör değerlendirmesi, 29 Ekim 2026

Rol: teknik ürün sorumlusu ve mimari denetçi. Aktif faz: 17, açık.
Kapsam: kayıtlı hedef, mevcut kod/veri, Git durumu, Belgeler altındaki ilişkili
klasörler, hedefli doğrulama ve arşivli temizlik hazırlığı. Yeni özellik yok.

## Sonuç

Çalışan bir mühendislik prototipi var. Günlük kullanım için kabul edilmiş bir
ürün düzeyine henüz ulaşmadı. Ürünleşme riski somut: deneyler, eski kopyalar,
uzun kabul notları ve sürüm kontrolüne alınmamış temel özellikler birikmiş.
Uygulamayı yeniden yazmak için kanıt yok; mevcut sürümü tek bir tekrarlanabilir
ürün tabanına toplamak öncelikli.

## Gerçekte ne çalışıyor?

React/Vite arayüz, FastAPI, kalıcı SQLite kayıtları, domain pack yapısı, AI görev
paketi, sonuç aktarımı, Remotion/FFmpeg üretimi ve sahneye bağlı geri bildirim
kodları mevcut. Aktif veritabanında business-tech 0.3.2 alanında tek gerçek
proje var: Why AI Data Centers Are Running Out of Power. 14 üretim, 7 kurgu planı,
2 treatment ve 9 AI döngü kaydı duruyor. Son üretim 7 Eylül tarihli 28,4 saniyelik
bir devam bölümü; 46,5 saniyelik açılış da korunmuş. Yeni tam video kabulü yok.

29 Ekim'de 11 hedefli depolama/kurtarma ve editoryal API testi geçti. UI
`npm run build` (TypeScript dahil) geçti. Bunlar sınırlı teknik doğrulamalardır;
profesyonel kurgu, izleyici tutma veya tam üretim döngüsü başarısını kanıtlamaz.
Bu turda servisler kapalı bulundu; canlı ekran kabulü veya yeni render yapılmadı.
Kalıcı `.studio-data` veritabanları yerinde ve salt okunur sorgularla doğrulandı.

## Ürünleşmeyi engelleyenler

1. Temiz kopyadan aynı uygulamayı kurma kanıtı yok. Ana çalışma dalının son
   commit'i `4f686d4`, 7 Ağustos tarihli. Denetim öncesi 68 tracked değişiklik ve
   22.006 untracked dosya var. Büyük bölümü geçici test dosyaları; ancak
   `editorial_cycle.py`, `infrastructure/storage.py` ve `EditorialCyclePanel.tsx`
   gibi kritik ürün dosyaları da untracked. Tüm çalışma kaybolmuş değil;
   temiz bir Git kopyasının güncel Studio'yu içerdiği söylenemez.
2. Gerçek manuel AI sonucu → içe aktar → render → sürüme bağlı değerlendirme
   döngüsünün bütün canlı kabulü hâlâ açık. Önceki görevde bu adım kullanıcıya
   devredildi; bitmiş bir ürün kabulü yerine geçmiyor.
3. Yaratıcı kalite kapısı eksik. Sayısal ses senkronu ve başarılı MP4, anlatılan
   konuyla doğru görüntünün seçildiğini veya iyi bir YouTube açılışı olduğunu
   kanıtlamıyor. Tek proje ve kısa parçalar genellenmiş editör kalitesi sağlamaz.
4. Arayüzde hâlâ Yakında/Snapshot gerekli alanları var. Sunucu durumu metni
   statik; ana sayfadaki aria-current da sabit. Genel bakışın eski hazır/araştırma
   durumları son editoryal çalışma ile kullanıcı açısından tutarlı olmayabilir.
5. `CURRENT_STATE.md` 3.399, `NEXT_ACTIONS.md` 769 satırdı. Eski checkpoint'ler
   tarihsel olarak doğru olsa da bugünkü durumun okunmasını zorlaştırıyor.
   Bu görevde kısa güncel özet ve kök README giriş noktası eklendi.
6. İş akışı servisinde yaklaşık 2.437, araştırma UI bileşeninde 2.362 dolu satır
   var. Bu tek başına hata değildir; değişikliklerin dar kapsamlı ve doğrulanabilir
   tutulmasını daha önemli hâle getirir.

## Belgeler klasörü envanteri

İlişkili 32 klasörün ilk ölçümü toplam 40,90 GiB. Aktif çalışma 20,15 GiB;
10,22 GiB `output`, 2,11 GiB WhisperX ortamı, 1,53 GiB renderer alanıdır.
420 `.pytest*` klasörü yaklaşık 2,95 GiB tutuyor. Boyutlar arşiv oluşturulmadan
önce ölçülmüştür; yeniden boyut taraması yapılmadı.

| Klasör | GiB | Karar |
| --- | ---: | --- |
| Kurgu | 4.929 | Farklı/önemli içerik veya geçmiş; koru |
| kurgu_pytest_ALIGNMENT_REQUEST_TESTS_066e700408374c53860150efbebafdc7 | 0.000 | Arşivlendi; silme engellendi |
| kurgu_pytest_ALIGNMENT_REQUEST_TESTS_b096712e34c04094a53f6f09578ecfad | 0.000 | Arşivlendi; silme engellendi |
| kurgu_pytest_ALIGNMENT_REQUEST_TESTS_d1cdcd8726fc482d807b336ceb34fd62 | 0.000 | Arşivlendi; silme engellendi |
| kurgu_pytest_ALIGNMENT_REQUEST_TESTS_e1616f19c7f24e75997e07d2a9bcb831 | 0.000 | Arşivlendi; silme engellendi |
| kurgu_pytest_NARRATION_TESTS_d0a086cadbf04873b8e202d1ca0d22ca | 0.000 | Arşivlendi; silme engellendi |
| kurgu_pytest_PREREQUISITE_AND_AUDIO_TESTS_0c413153134b4fb3b055cc40ea84b303 | 0.000 | Arşivlendi; silme engellendi |
| kurgu_pytest_PREREQUISITE_AND_AUDIO_TESTS_33ac3a6209a54d1582e2567043019f46 | 0.000 | Arşivlendi; silme engellendi |
| kurgu_pytest_PREREQUISITE_AND_AUDIO_TESTS_462bd758013a4f1487e579fe378148f9 | 0.000 | Arşivlendi; silme engellendi |
| kurgu_pytest_PREREQUISITE_AND_AUDIO_TESTS_593548d536ed4effac151b3c2c8a3e6d | 0.000 | Arşivlendi; silme engellendi |
| kurgu_pytest_REGRESSION_TESTS_f0f17dd936be42eba962fca8dd7e65f3 | 0.000 | Arşivlendi; silme engellendi |
| kurgu_pytest_TEMPORAL_TESTS_864152a6737d4835a747210d34261acb | 0.000 | Arşivlendi; silme engellendi |
| kurgu_pytest_V3_CONTRACT_TESTS_19929e90a81c478c935967e4c0ca08cf | 0.000 | Arşivlendi; silme engellendi |
| kurgu_pytest_V3_CONTRACT_TESTS_50a95aa03636414d88e5eda8072545d0 | 0.000 | Arşivlendi; silme engellendi |
| kurgu_pytest_V3_CONTRACT_TESTS_67a1d79d83b84360ba2fbf4c8020f929 | 0.000 | Arşivlendi; silme engellendi |
| kurgu_pytest_V3_CONTRACT_TESTS_8ccc2d02becb43a5bb254fdf3bf5889f | 0.000 | Arşivlendi; silme engellendi |
| Kurgu_Test_Temp | 0.000 | Arşivlendi; silme engellendi |
| Kurgu_V3_Clean | 4.556 | Farklı/önemli içerik veya geçmiş; koru |
| Kurgu_V3_Clean_backup_20260724_163006 | 4.556 | Farklı/önemli içerik veya geçmiş; koru |
| Kurgu_V3_Clean_backup_20260724_163134 | 4.556 | Farklı/önemli içerik veya geçmiş; koru |
| Kurgu_V3_Clean_freesound_final_verify_20260724_231200000 | 0.001 | Arşivlendi; silme engellendi |
| Kurgu_V3_Clean_freesound_postpush_verify_20260724_225900000 | 2.130 | Farklı/önemli içerik veya geçmiş; koru |
| Kurgu_V3_Clean_freesound_postpush_verify_20260724_230300000 | 0.001 | Arşivlendi; silme engellendi |
| Kurgu_V3_Clean_phase0_final_verify_20260725_0001 | 0.002 | Farklı/önemli içerik veya geçmiş; koru |
| Kurgu_V3_Clean_phase0_final_verify_20260725_0002 | 0.002 | Arşivlendi; silme engellendi |
| Kurgu_V3_Clean_phase3b_clean_verify_20260805 | 0.001 | Farklı/önemli içerik veya geçmiş; koru |
| Kurgu_V3_Clean_postpush_verify_20260724_170436 | 0.001 | Arşivlendi; silme engellendi |
| Kurgu_V3_Clean_sanitized_20260724_163134 | 0.002 | Farklı/önemli içerik veya geçmiş; koru |
| Kurgu_V3_Clean_sanitized_freesound_20260724_224147304 | 20.154 | Aktif çalışma; koru |
| Kurgu_V3_Clean_sanitized_verify_20260724_163134 | 0.001 | Arşivlendi; silme engellendi |
| Kurgu_V3_Clean_sanitized_verify_final_20260724_163134 | 0.001 | Arşivlendi; silme engellendi |
| Kurgu_V3_Clean_sanitized_verify_noconvert_20260724_163134 | 0.001 | Arşivlendi; silme engellendi |

Eski ana kopyaların yalnız seçilmiş kaynak/doküman uzantıları karşılaştırıldı;
medya içerikleri veya her kod satırı semantik olarak incelenmiş sayılmamalı.
Kurgu içinde aktif projede olmayan 51 kaynak/doküman yolu ve aynı yolda farklı
13 dosya; Kurgu_V3_Clean içinde farklı 20 dosya bulundu. İki eski yedek de
aktif klasörle tamamen aynı değil. Bunları topluca silmek doğrulanmış bir
tekilleştirme işlemi olmaz. Ayrıntı: `source-comparison.json`.

## Temizlik sonucu

420 aktif-klasör test dizini ve 26 kardeş test/doğrulama dizini seçildi.
Toplam 446 dizin, 17.837 dosya, yaklaşık 2,956 GiB için geri açılabilir
`cleanup-archive.zip` oluşturuldu (yaklaşık 1,421 GiB). Arşiv CRC kontrolü,
arşivdeki her dosyanın SHA-256'sı ve kaynak dosyaların SHA-256'sı doğrulandı.
Boş dizin adları ve tüm yollar planda korunuyor.

**Silinen dosya/klasör: 0. Açılan alan: 0.** Otomatik onay incelemesi toplu
recursive silmeyi `blocked by policy` ile reddetti. İçi tamamen boş klasörlerle
sınırlı, recursive olmayan güvenli deneme de aynı şekilde reddedildi. Daha fazla
silme yolu denenmedi. Arşiv diske yaklaşık 1,421 GiB eklemiştir; silme gerçekleşmiş
ve alan açılmış gibi raporlanamaz. İnceleme için somut liste `cleanup-plan.json`,
sonuç `cleanup-result.json`. Veritabanları, son video ve seçili kritik kaynak
hash'leri temizlik hazırlığından sonra değişmedi.

## Sonraki tek görev

`PHASE17_REPRODUCIBLE_PRODUCT_BASELINE`: mevcut uygulama kaynaklarını ve gerekli
bağımlılık/sözleşmeleri geçici deneylerden ayıran incelenebilir bir dosya manifesti
hazırla; kaynakları seçerek sürüm kontrolüne al; temiz ve yalıtılmış bir checkout'ta
kurulum, UI build, API ve kısa fixture üretimini doğrula. `git add .` kullanma.
Ürün verisi ve sırları Git'e koyma. Bu taban geçtikten sonra manuel AI döngüsünün
canlı kabulünü tamamla. Roadmap veya domain kapsamı değişikliği gerekmiyor.

Bu görevin kabulü: güncel durum ve tüm ilişkili klasörlerin sınıflandırılması,
ölçülmüş kontroller, doğrulanmış temizlik arşivi, silme sınırının dürüst kaydı,
tek sonraki görev ve dokümantasyon eşitlemesi. Faz 17 kapanmıyor.

## Kanıtlar ve DOCUMENTATION_IMPACT_MATRIX

Komutlar: `git status --porcelain -uall`, `git log`, `git worktree list`,
kardeş repo durumları; güvenli `os.walk` envanteri ve seçilmiş dosya hash'leri;
SQLite salt okunur sorgular; 11 hedefli pytest testi; `npm run build`.
Temizlik silme komutları yürütme öncesinde engellendi. Testler izole veriyle
çalıştırıldı. İnceleme kanıtları `output/project-audit-20261029` altında.

| Belge/dosya | Etki |
| --- | --- |
| README.md | Ana giriş, gerçek ürün durumu ve mevcut açma komutu |
| CURRENT_STATE.md | Kısa güncel denetim sonucu |
| CHANGELOG.md | Envanter/arşiv ve silmenin engellendiği kaydı |
| NEXT_ACTIONS.md | Tek sonraki görev: tekrarlanabilir ürün tabanı |
| KNOWN_LIMITATIONS.md | Ürün, sürüm kontrolü ve temizlik sınırları |
| PHASE_ACCEPTANCE.md | Denetim kabulü; faz ve ürün kabulü açık |
| QUALITY_BENCHMARKS.md | Bugünkü teknik kontroller; yaratıcı kalite kabulü yok |
| ARCHITECTURE_DECISIONS.md | İncelendi, yeni mimari karar yok |
| MASTER_ROADMAP.md | İncelendi, değiştirilmedi |
| baseline/phase17_product_audit_20261029.md | Bu değerlendirme |

Uygulama kodu bu görevde değiştirilmedi. Yeni arşiv, envanter, hash, Git ve veri
kayıtları üretilmiştir; eski yedekler ve uygulama verisi korunmuştur.
