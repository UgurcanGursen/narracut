# Kurgu Engine — Codex Çalışma Kuralları

Bu dosyanın kapsamı repo kökü ve bütün alt klasörlerdir.

## 1. Tek kaynak belgeler

Her görevden önce şu dosyaları sırayla oku:

1. `docs/MASTER_ROADMAP.md`
2. `docs/CURRENT_STATE.md`
3. `docs/NEXT_ACTIONS.md`
4. `docs/KNOWN_LIMITATIONS.md`
5. İlgili fazın `docs/PHASE_ACCEPTANCE.md` bölümü

`docs/MASTER_ROADMAP.md` mimari hedeflerin tek ana kaynağıdır. Kullanıcı açıkça istemedikçe roadmap’i değiştirme.

## 2. Faz disiplini

- Aynı anda yalnızca aktif fazın görevlerini uygula.
- Sonraki fazlardan büyük özellikleri erken ekleme.
- Her görevin başında faz numarasını, amacı, kapsam içi/kapsam dışı işleri ve acceptance kriterlerini kısa biçimde yaz.
- Görev active phase’e doğrudan katkı sağlamıyorsa kodlama; bulguyu backlog veya `NEXT_ACTIONS.md` içine öneri olarak yaz.
- Faz kabul kriterleri geçmeden fazı tamamlanmış sayma.

## 3. Multi-domain mimari

Bağlayıcı ürün modeli:

```text
multi-domain-ready core
+
domain-specific intelligence pack
```

- Core; workspace, stable ID, LLM Gateway, source/claim persistence, chronology, story hierarchy, asset catalog, EDL, renderer, audio, review, artifact lifecycle ve export sağlar.
- Research policy, source priority, claim taxonomy, entity roles, narrative grammar, visual grammar, safety, validation ve promptlar Domain Pack içindedir.
- İlk ve tek production hedefi şimdilik `business-tech` pack’idir.
- `true-crime-legal`, `history-geopolitics` veya `science-explainer` pack’lerini kullanıcı açıkça görevlendirmeden geliştirme.
- Core içine `EarningsClaim`, `MurderSuspect`, `RevenueChart` gibi domain’e kilitli sınıflar ekleme.
- Domain davranışını servislere dağılmış `if domain == ...` bloklarıyla uygulama. `DomainPackRegistry` ve typed policy resolver kullan.
- Prompt template’lerini core/gateway içine gömme; `domain-packs/<domain_id>/prompts/` altında tut.
- Domain pack sürümü ve resolved policy snapshot proje metadata’sında kalıcı olmalıdır.

## 4. Mevcut baseline’ı koru

Mevcut repo; `main.py`, `v2/`, `templates/`, `assets/`, `cache/`, `output/`, `temp_assets/` ve mevcut test/fixture’ları içerir.

- Faz 0 kabul edilmeden toplu klasör taşıma veya büyük yeniden adlandırma yapma.
- Mevcut çalışan render yolunu sessizce kaldırma.
- `assets/`, `cache/`, `output/` veya fixture dosyalarını kullanıcı açıkça istemeden silme.
- Eski davranışı değiştiriyorsan migration ve geriye dönük uyumluluk etkisini açıkça belgeleyerek test et.
- Başarısız veya eksik özelliği çalışanmış gibi raporlama.

## 5. LLM maliyet politikası

- Ticari LLM API çağrıları varsayılan olarak kapalıdır.
- Renderer, timeline, audio, cache ve UI testlerinde `REPLAY` fixture kullan.
- Yeni research/planner zekâsı gerektiğinde önce `MANUAL_UI` task package üret.
- Kullanıcı açıkça onaylamadan API anahtarı, ücretli provider veya otomatik web-UI sürme ekleme.
- ChatGPT/Claude/Gemini web arayüzlerini Playwright ile gizli API gibi otomatik kullanma.

## 6. UI ve backend sınırı

İlk stack:

```text
React + TypeScript + Vite
→ thin FastAPI Studio API
→ Python Kurgu Engine + Remotion + FFmpeg
```

- React dosya sistemine veya Python fonksiyonlarına doğrudan erişmez.
- FastAPI endpoint’leri ince adapter/orchestration katmanı olarak kalır.
- Canonical sözleşmeler `shared-schemas/` ve OpenAPI üzerinden yönetilir.
- Spring Boot başlangıç kapsamına girmez; yalnızca roadmap’teki product gate koşulları oluşursa değerlendirilir.

## 7. Kod ve doğrulama standardı

- Önce mevcut kodu ve test komutlarını keşfet; isim veya davranış uydurma.
- Mümkün olan en küçük, geri alınabilir değişikliği yap.
- Silent fallback veya silent default kullanma; hata ve migration kaybını görünür kıl.
- Stable ID, content hash, provenance ve artifact lineage kurallarını koru.
- Değişiklikten sonra ilgili testleri, lint/type-check komutlarını ve mümkünse kısa fixture render’ını çalıştır.
- Çalıştıramadığın kontrolü açıkça belirt; geçmediği hâlde başarılı deme.

## 8. Görev sonu zorunlu rapor

Her görev sonunda şunları yaz:

- Değiştirilen dosyalar
- Uygulanan faz ve acceptance kriterleri
- Çalıştırılan komutlar ve sonuçları
- Üretilen artifact’ler
- Bilinen eksikler veya blocker’lar
- Sonraki tek önerilen görev

Faz kapanıyorsa `CURRENT_STATE.md`, `KNOWN_LIMITATIONS.md`, `PHASE_ACCEPTANCE.md`, `CHANGELOG.md` ve `NEXT_ACTIONS.md` dosyalarını güncelle.
