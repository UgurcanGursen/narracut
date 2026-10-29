# Kurgu Studio

Business-tech faceless YouTube videoları için yerel kurgu uygulaması.
Hedef; araştırma, senaryo, kaynaklar ve sesi bir araya getirerek sahne bazında
incelenebilen ve düzeltilebilen bir video üretmek. İlk kullanım biçimi,
abone olunan AI araçlarıyla manuel görev dosyası alışverişidir.

**29 Ekim 2026 durumu:** çalışan bir mühendislik prototipi. Tek bir gerçek
projenin kayıtları, 46,5 saniyelik açılış ve 28,4 saniyelik devam bölümü var.
Tam video, bağımsız uçtan uca kullanım ve profesyonel ilk kurgu kalitesi henüz
kabul edilmiş değil. Aktif faz: **17 — açık**.

## Nereden başlanır?

- Güncel durum: [docs/CURRENT_STATE.md](docs/CURRENT_STATE.md)
- Tek sonraki görev: [docs/NEXT_ACTIONS.md](docs/NEXT_ACTIONS.md)
- Ürün ve klasör değerlendirmesi: [29 Ekim incelemesi](docs/baseline/phase17_product_audit_20261029.md)
- Mevcut ekranların kullanımı: [Studio devam rehberi](docs/STUDIO_DEVAM_REHBERI.md)
- Bağlayıcı ürün hedefi: [Master roadmap](docs/MASTER_ROADMAP.md)

## Mevcut kurulumu açma

Proje klasöründe PowerShell:

```powershell
.\scripts\start_local_studio.ps1 -ApiPort 8007
```

Arayüz: http://127.0.0.1:5173/#studio-video

Bu komut mevcut `.venv-studio` Python ortamını ve kurulu UI bağımlılıklarını
kullanır. Temiz bilgisayarda eksiksiz yeniden kurulum henüz doğrulanmadı;
sonraki görevin kabul koşullarından biri budur.

## Hangi klasör ne için?

| Klasör | İşlev |
| --- | --- |
| `studio-ui`, `studio-api` | Kullanıcı arayüzü ve yerel API |
| `engine`, `renderer-remotion`, `domain-packs`, `shared-schemas` | Kurgu motoru, görüntü üretimi ve sözleşmeler |
| `.studio-data` | Aktif proje veritabanları; yerel yedeğe dahil edilmeli |
| `output`, `assets`, `cache` | Üretilmiş videolar, kaynaklar ve yeniden kullanılan çalışma verileri |
| `docs` | Durum, kararlar ve kabul kayıtları |
| `.codex-tmp` | Yönetilen dokümantasyon worktree'si de içerir; sıradan önbellek değildir |

Aktif çalışma bu README'nin bulunduğu klasördür. Belgeler altındaki eski
`Kurgu*` kopyalarının bir kısmı farklı kaynaklar içerir. Temizlik kaydı ve geri
açılabilir arşiv `output/project-audit-20261029` altında tutulur.
