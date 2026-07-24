"""
download_assets.py
==================
Freesound.org API kullanarak ses efektleri ve arka plan müziği indirir.
İndirilen dosyalar assets/ klasör hiyerarşisine kaydedilir.

Kullanım:
    1. FREESOUND_API_KEY değişkenine kendi API anahtarınızı girin.
    2. python download_assets.py

Ücretsiz API anahtarı almak için:
    https://freesound.org/apiv2/apply/
    (Kayıt olduktan sonra "API Credentials" sayfasından token alın.)

NOT: Pixabay'nin /api/audio/ endpoint'i standart API anahtarlarına
     403 Forbidden verdiği için bu script Freesound.org API'sini kullanır.
"""

import os
import time
import requests
from v2.config import get_freesound_api_key

# ─────────────────────────────────────────────
#  AYARLAR
# ─────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Freesound API uç noktası
FREESOUND_SEARCH_URL = "https://freesound.org/apiv2/search/text/"

# İstekler arası bekleme süresi (saniye) — API rate-limit koruması
SLEEP_BETWEEN_DOWNLOADS = 1.0

# Her kategori:
#   "folder"         : assets/ altındaki göreli klasör yolu
#   "query"          : Freesound'da aranacak birincil sorgu
#   "fallback_query" : Sonuç yetersizse denenen yedek sorgu
#   "filter"         : Freesound Solr filtresi (sadece type:mp3 yeterli)
#   "prefix"         : kaydedilecek dosya adı öneki  (boom_1.mp3, …)
#   "limit"          : kaç dosya indirileceği
CATEGORIES = [
    {
        "folder":         "assets/sfx/booms",
        "query":          "cinematic bass boom impact",
        "fallback_query": "boom impact explosion",
        "filter":         "type:mp3",
        "prefix":         "boom",
        "limit":          5,
    },
    {
        "folder":         "assets/sfx/whooshes",
        "query":          "cinematic whoosh transition",
        "fallback_query": "whoosh swish air",
        "filter":         "type:mp3",
        "prefix":         "whoosh",
        "limit":          5,
    },
    {
        "folder":         "assets/sfx/typing",
        "query":          "mechanical keyboard typing",
        "fallback_query": "keyboard typing click",
        "filter":         "type:mp3",
        "prefix":         "typing",
        "limit":          5,
    },
    {
        "folder":         "assets/sfx/glitch",
        "query":          "glitch digital",
        "fallback_query": "glitch",
        "filter":         "type:mp3",
        "prefix":         "glitch",
        "limit":          5,
    },
    {
        "folder":         "assets/sfx/paper",
        "query":          "paper rustle shuffle",
        "fallback_query": "paper",
        "filter":         "type:mp3",
        "prefix":         "paper",
        "limit":          5,
    },
    {
        "folder":         "assets/bgm/tension",
        "query":          "dark tension documentary ambient",
        "fallback_query": "dark ambient tension",
        "filter":         "type:mp3",
        "prefix":         "tension",
        "limit":          3,
    },
]


# ─────────────────────────────────────────────
#  YARDIMCI FONKSİYONLAR
# ─────────────────────────────────────────────

def create_directories():
    """Tüm kategori klasörlerini oluşturur (zaten varsa atlar)."""
    print("\n📁  Klasör hiyerarşisi oluşturuluyor...\n")
    for cat in CATEGORIES:
        dir_path = os.path.join(BASE_DIR, cat["folder"])
        os.makedirs(dir_path, exist_ok=True)
        print(f"   ✔  {cat['folder']}")
    print()


def fetch_audio_results(query: str, filter_str: str, limit: int) -> list:
    """
    Freesound Text Search API'sine istek atar ve ses listesini döndürür.

    :param query:       Arama sorgusu
    :param filter_str:  Solr filtresi (örn: "type:mp3")
    :param limit:       İstenecek maksimum sonuç sayısı
    :return:            API'den gelen sonuç listesi
    """
    # Freesound per_page min:3 max:150; daha fazla aday çekerek limit kadar seçiyoruz
    page_size = min(max(limit * 2, 6), 50)
    api_key = get_freesound_api_key()

    if not api_key:
        print("   Freesound key unavailable.")
        return []

    params = {
        "token":     api_key,
        "query":     query,
        "filter":    filter_str,
        "sort":      "downloads_desc",   # en çok indirilenler önce
        "fields":    "id,name,previews,download,duration",
        "page_size": page_size,
    }

    try:
        response = requests.get(FREESOUND_SEARCH_URL, params=params, timeout=15)
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        print("   ❌  Bağlantı hatası: İnternet bağlantınızı kontrol edin.")
        return []
    except requests.exceptions.Timeout:
        print("   ❌  Zaman aşımı: Freesound API yanıt vermedi.")
        return []
    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "?"
        if status == 401:
            print("   ❌  HTTP 401 — Geçersiz API anahtarı. Anahtarınızı kontrol edin.")
        elif status == 429:
            print("   ❌  HTTP 429 — API rate limit aşıldı. Biraz bekleyin.")
        else:
            print(f"   ❌  HTTP {status} hatası: {exc}")
        return []
    except requests.exceptions.RequestException as exc:
        print(f"   ❌  İstek hatası: {exc}")
        return []

    try:
        data = response.json()
    except ValueError:
        print("   ❌  API'den geçersiz JSON yanıtı alındı.")
        return []

    results = data.get("results", [])
    if not results:
        print("   ⚠️   Bu sorgu için sonuç bulunamadı.")
        return []

    return results[:limit]


def get_preview_url(hit: dict) -> str | None:
    """
    Bir Freesound sonucundan en kaliteli indirilebilir preview URL'sini seçer.
    Freesound preview'ları ücretsiz ve lisans gerektirmez.

    :param hit: API sonuç nesnesi
    :return:    MP3 preview URL'si veya None
    """
    previews = hit.get("previews", {})
    # Kalite öncelik sırası
    for quality in ("preview-hq-mp3", "preview-lq-mp3"):
        url = previews.get(quality)
        if url:
            return url
    return None


def download_file(url: str, dest_path: str) -> bool:
    """
    Verilen URL'deki dosyayı `dest_path`'e indirir.
    Freesound preview'ları için token header'ı eklenir.

    :return: Başarılı ise True, aksi halde False
    """
    api_key = get_freesound_api_key()
    if not api_key:
        print("      Freesound key unavailable.")
        return False

    headers = {"Authorization": f"Token {api_key}"}

    try:
        with requests.get(url, headers=headers, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        return True
    except requests.exceptions.HTTPError as exc:
        print(f"      ❌  İndirme HTTP hatası: {exc}")
        return False
    except requests.exceptions.ConnectionError:
        print("      ❌  İndirme sırasında bağlantı kesildi.")
        return False
    except requests.exceptions.Timeout:
        print("      ❌  İndirme zaman aşımı.")
        return False
    except requests.exceptions.RequestException as exc:
        print(f"      ❌  İndirme hatası: {exc}")
        return False
    except OSError as exc:
        print(f"      ❌  Dosya yazma hatası: {exc}")
        return False


def process_category(cat: dict):
    """Tek bir kategori için arama ve indirme işlemini yürütür."""
    folder         = cat["folder"]
    query          = cat["query"]
    fallback_query = cat.get("fallback_query", "")
    filter_s       = cat["filter"]
    prefix         = cat["prefix"]
    limit          = cat["limit"]
    dir_path       = os.path.join(BASE_DIR, folder)
    cat_label      = os.path.basename(folder)   # örn: "booms", "tension"

    print(f"{'─' * 60}")
    print(f"🔍  [{cat_label.upper()}] kategorisi aranıyor...")
    print(f"    Sorgu      : \"{query}\"")
    print(f"    Filtre     : {filter_s}")
    print(f"    Hedef      : {folder}")
    print(f"    Limit      : {limit} dosya\n")

    hits = fetch_audio_results(query, filter_s, limit)

    # Sonuç yetersizse yedek sorguyu dene
    if len(hits) < limit and fallback_query and fallback_query != query:
        eksik = limit - len(hits)
        print(f"   🔄  Yeterli sonuç yok ({len(hits)}/{limit}), yedek sorgu deneniyor: \"{fallback_query}\"")
        extra = fetch_audio_results(fallback_query, filter_s, limit)
        # Zaten indirilen ID'leri tekrar ekleme
        mevcut_ids = {h["id"] for h in hits}
        for h in extra:
            if h["id"] not in mevcut_ids and len(hits) < limit:
                hits.append(h)
                mevcut_ids.add(h["id"])
        print(f"   ✔   Yedek sorgu sonrası toplam: {len(hits)} ses\n")

    if not hits:
        print(f"   ⚠️   {cat_label} için hiç sonuç alınamadı, atlanıyor.\n")
        return

    downloaded = 0
    for idx, hit in enumerate(hits, start=1):
        sound_name = hit.get("name", f"ses_{idx}")
        duration   = hit.get("duration", 0)
        preview_url = get_preview_url(hit)

        if not preview_url:
            print(f"   ⚠️   {idx}. sonuç için preview URL'si yok, atlanıyor.")
            continue

        filename  = f"{prefix}_{idx}.mp3"
        dest_path = os.path.join(dir_path, filename)

        print(f"   ⬇️   {cat_label} kategorisi için {idx}. ses indiriliyor...")
        print(f"        İsim   : {sound_name[:55]}")
        print(f"        Süre   : {duration:.1f}s")
        print(f"        Hedef  : {filename}")

        success = download_file(preview_url, dest_path)

        if success:
            size_kb = os.path.getsize(dest_path) / 1024
            print(f"        ✅  İndirildi — {size_kb:.1f} KB")
            downloaded += 1
        else:
            # Yarım kalan dosyayı temizle
            if os.path.exists(dest_path):
                try:
                    os.remove(dest_path)
                except OSError:
                    pass

        if idx < len(hits):
            time.sleep(SLEEP_BETWEEN_DOWNLOADS)

    print(f"\n   📊  {cat_label}: {downloaded}/{len(hits)} dosya başarıyla indirildi.\n")


def print_summary():
    """İndirme tamamlandığında klasör içeriklerini özetler."""
    print(f"\n{'═' * 60}")
    print("📂  İNDİRME ÖZETİ")
    print(f"{'═' * 60}")

    total_files = 0
    total_bytes = 0

    for cat in CATEGORIES:
        dir_path  = os.path.join(BASE_DIR, cat["folder"])
        cat_label = os.path.basename(dir_path)

        if not os.path.isdir(dir_path):
            print(f"  {cat_label:20s}  →  klasör bulunamadı")
            continue

        mp3_files = [f for f in os.listdir(dir_path) if f.endswith(".mp3")]
        size_kb   = sum(
            os.path.getsize(os.path.join(dir_path, f)) for f in mp3_files
        ) / 1024
        total_files += len(mp3_files)
        total_bytes += size_kb * 1024

        print(f"  {cat_label:20s}  →  {len(mp3_files):2d} dosya  ({size_kb:7.1f} KB)")

    print(f"{'─' * 60}")
    print(f"  {'TOPLAM':20s}  →  {total_files:2d} dosya  ({total_bytes / 1024:7.1f} KB)")
    print(f"{'═' * 60}\n")


# ─────────────────────────────────────────────
#  ANA AKIŞ
# ─────────────────────────────────────────────

def main():
    print("╔══════════════════════════════════════════════════════════╗")
    print("║    Freesound Ses Varlığı İndirici — download_assets.py   ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print("   API : freesound.org  |  Anahtar almak için:")
    print("         https://freesound.org/apiv2/apply/\n")

    # API anahtarı kontrolü
    if not get_freesound_api_key():
        print("⛔  HATA: Freesound key unavailable.")
        print("   Lütfen FREESOUND_API_KEY environment değişkenini ayarlayın.")
        print("   Ücretsiz anahtar: https://freesound.org/apiv2/apply/\n")
        return

    # 1. Klasörleri oluştur
    create_directories()

    # 2. Her kategori için ara ve indir
    for cat in CATEGORIES:
        process_category(cat)
        time.sleep(SLEEP_BETWEEN_DOWNLOADS)

    # 3. Özeti yazdır
    print_summary()
    print("✅  Tüm işlemler tamamlandı.")


if __name__ == "__main__":
    main()
