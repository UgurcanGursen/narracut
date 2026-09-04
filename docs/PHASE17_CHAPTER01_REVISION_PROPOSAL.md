# Faz 17 — ilk chapter sürüm 2 plan düzenlemesi

Tarih: 2026-09-04
Sonuç: `PROPOSAL_VALIDATED / STUDIO_ACTIVATION_NOT_IMPLEMENTED`.

Kullanıcı mevcut 11 saniyelik ilk chapter içinde yeniden düzenlemeyi onayladı.
Plan 3 + 4,5 + 3,5 saniye olarak yazıldı. 13 ve 15 saniyelik sonraki chapter'lar
değişmedi; toplam 39 saniye korunuyor. Bu, ürün veya Faz 17 kapanışı değildir.

## Yapılan iş

- Exact canlı kayıtlar salt-okunur SQLite bağlantılarıyla alındı.
- Mevcut `ChapterBriefV1` ve `NarrativeBeatV1` constructor'larıyla bir chapter
  ve üç beat, proposed/version=2 olarak oluşturuldu. Claim/fact, parent ve
  supersedes kimlik/hash bağlantıları korundu. Yeni class veya core domain kuralı yok.
- Kesin 350. gün kesintisi yerine DOE'nun kısıtlı bölgeler için verdiği örnek
  ve kalan günlerde çözüm ihtiyacı anlatılıyor. Anlatım 25 sözcük, sayılar yazıyla.
- Renderer planından desteklenmeyen takvim/ortak nesne vaadi kaldırıldı;
  kaynak okuma dizisinin görsel kalitesi henüz kabul edilmedi.
- Eski canlı planner kayıtları değişmedi. Eski ses/timing silinmedi veya yeni
  metne taşınmadı. Studio etkin planı henüz eski kayıtlardır.

## Değiştirilen/üretilen dosyalar

`output/phase17-data-center-power-chapter-01-revision-v2/`:
`prepare_revision.py`, `test_revision.py`, `PLAN.md`, `chapter-brief-v2.json`,
`narrative-beats-v2.json`, `editorial-plan-v2.json`, `source-context.json`,
`unchanged-chapters.json`, `superseded-parent-records.json`, `verification.json`.
Engine, Studio API ve renderer üretim kodu bu görevde değiştirilmedi.

## Komutlar ve kontroller

`PYTHONPATH=.;studio-api/src` ile `.venv-studio/Scripts/python.exe`:

- `.../prepare_revision.py`: başarılı; iki çalıştırma aynı proposal kimliklerini
  verdi. Önceki ilk denemede canonical JSON float alanını reddetti; WPM gösterimi
  decimal string olarak düzeltildi. İlk iki yazılmış proposed artifact değişmedi.
- `.../test_revision.py -v`: **6/6 geçti**. Mevcut Phase10 identity, exact
  supersedes/parent, süre korunumu, planlanan sözlü metin hızı/qualification,
  sahte accepted değişikliğinin reddi ve manifest hash'leri kontrol edildi.
- Kaynak crop görsel olarak incelendi; yeni video/still render yapılmadı.
- Bu testler timing, audio, UI entegrasyonu veya yaratıcı kalite testi değildir.

## Tek sonraki görev

`PHASE17_BUSINESS_TECH_V032_CHAPTER_REVISION_ACTIVATION`:
Studio'da onay sonrası chapter revizyonunu sürümlü ve atomik biçimde etkinleştir;
aynı işlemde eski downstream'in yeni dala taşınmasını engelle. Hata/rollback,
duplicate, stale-parent, başka proje ve eski timing reuse negatif testleri gerekir.
Mevcut kabul edilmiş bir kaydın status/hash alanını doğrudan değiştirme.
Bu geçiş tamamlanmadan yeni ses veya render başlatılmamalı.

## DOCUMENTATION_IMPACT_MATRIX

| Belge | Etki |
|---|---|
| CURRENT_STATE | 11 saniyelik V2 öneri hazır; canlı plan değişmedi |
| NEXT_ACTIONS | Tek uygulanabilir adım chapter revision activation |
| KNOWN_LIMITATIONS | Canonical aktivasyon ve görsel/audio kabulü açık |
| PHASE_ACCEPTANCE | 6 proposal kontrolü geçti; ürün acceptance değil |
| CHANGELOG | Plan düzenlemesi ve artifact kaydı |
| QUALITY_BENCHMARKS | Değişmedi; yeni yaratıcı kalite iddiası yok |
| ARCHITECTURE_DECISIONS | Değişmedi; yeni mimari uygulanmadı |
| MASTER_ROADMAP | Değişmedi; toplam süre ve aktif faz aynı |
