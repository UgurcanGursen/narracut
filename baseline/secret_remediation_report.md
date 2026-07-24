# Faz 0.1 — Pexels Secret Remediation Report

Değerlendirme tarihi: 24 Temmuz 2026  
Branch/revision: `main` / `c90009cd07da637607d456188deb3407570bef05`  
Implementation sonucu: **ACCEPTED**  
Faz 0 sonucu: **BLOCKED / NOT CLOSED**

Bu görevde provider API çağrısı, ağ çağrısı, full render, Git history rewrite,
commit, tag veya push yapılmadı. Görev öncesi kullanıcı değişiklikleri
korundu.

## Original risk classification

Tracked `v2/asset_manager.py`, canonical config'i bypass eden non-empty literal
Pexels fallback içeriyordu. Değer yüksek entropili ve credential biçimliydi;
placeholder/test işareti yoktu. Güvenli sınıflandırma: **compromised secret**.

Değer bu rapora, test çıktısına, loga veya başka bir artifact'e alınmamıştır.
Değişiklik özeti: `[REDACTED literal removed]`.

## Provider revoke/rotation status: not-confirmed

Kullanıcı provider tarafında revoke/rotate işlemini yapacağını veya yapmış
olabileceğini bildirdi; tamamlandığı bu görev içinde kesin olarak teyit
edilmedi. Credential validity isteği gönderilmedi.

## Changed code symbols

- `v2.config.get_pexels_api_key`
- `v2.config.PEXELS_API_KEY`
- `v2.asset_manager` canonical config import'u
- `v2.asset_manager.fetch_pexels_video`

`fetch_pexels_video` dönüş şekli değiştirilmedi. Exception logu raw exception
mesajı yerine yalnızca exception sınıf adını yazar; böylece provider header
veya credential içeren hata metninin loga taşınması engellenir.

## New configuration contract

```text
process environment
→ PEXELS_API_KEY
→ v2.config.get_pexels_api_key()
→ v2.config.PEXELS_API_KEY
→ v2.asset_manager.fetch_pexels_video()
```

- Tek credential kaynağı process environment'tır.
- Missing environment değeri empty string olur.
- `asset_manager.py` environment değişkenini ayrı fallback ile okumaz.
- `.env`, `.env.local` ve `.env.*.local` Git tarafından ignore edilir.
- `.env.example`, yalnızca boş `PEXELS_API_KEY=` bildirimi içerir.

## Missing-key behavior

Credential boşsa:

1. Pexels HTTP search/download çağrısı yapılmaz.
2. `assets/videos/*.mp4` içinde local dosya varsa canonical metadata dict döner:
   `path`, local `url`, `title`, `provider=local`,
   `review_required=True`.
3. Local dosya yoksa `None` döner.
4. `resolve_visual_asset` mevcut dict sözleşmesini tüketmeye devam eder ve
   `asset_provider`, `review_required`, `content_fingerprint` provenance
   alanlarını korur.

String-path eski sözleşmesine dönülmemiştir.

## Test results

| Komut | Sonuç |
|---|---|
| `python -m pytest -q tests/test_pexels_secret_remediation.py` | **5 passed** |
| Pexels/asset-manager hedefli test grubu | **5 passed, 1 known stale failure** |
| `python -m pytest -q` | **34 passed, 2 known failed** |
| `python -m py_compile v2/config.py v2/asset_manager.py tests/test_pexels_secret_remediation.py` | **passed** |

Bilinen failure'lar:

- `test_numeric_equivalent`: kapsam dışı production bug; değiştirilmedi.
- `test_pexels_key_missing_fallback`: eski string-path beklentisi; canonical
  metadata dict döndüğü için başarısız. Test bu görevde yeniden tasarlanmadı.

Yeni testler şunları kanıtlar:

- environment değeri canonical config accessor'dan okunur,
- environment yoksa default boştur,
- missing key durumunda HTTP çağrısı yoktur,
- local metadata/provenance dict sözleşmesi korunur,
- request failure logunda credential marker'ı bulunmaz.

## Current-tree secret scan

Historical değer Git history'den process belleğine alınarak, değeri çıktıya
yazmadan current tracked ve non-ignored untracked dosyalar ile ilgili Python
compiled dosyalarında exact-match taraması yapıldı.

- Taranan yol: 129
- Exact eşleşme: **0**
- Eşleşen dosya: **0**
- Non-empty Pexels environment fallback source pattern'i: **0**

`.git` object database bu current-tree sonucuna dahil değildir; history
exposure aşağıda ayrı raporlanır.

## Git-history exposure status

- Taranan commit: 1
- Historical değeri içeren commit: 1
- Git history değiştirilmedi.
- BFG, filter-repo, rebase, reset veya force-push kullanılmadı.

Current source güvenlidir; historical commit güvenli değildir.

## Remote exposure assessment

- Remote mevcut: `origin`
- Remote taşıma şekli: HTTPS
- Host: GitHub
- Remote URL userinfo/credential içeriyor görünmüyor.
- Aktif branch: `main`
- Upstream: `origin/main`
- Local `origin/main` remote-tracking ref'i HEAD ile aynı committe.

Ağ üzerinden fetch yapılmadığı için provider remote'un anlık durumu yeniden
doğrulanmadı. Bununla birlikte remote-tracking ref'in historical committe
olması, secret bulunan commit'in remote'a çıkmış olma ihtimalini **yüksek**
yapar.

## Remaining history-remediation decision

Faz 0.1B dört seçeneği karşılaştırmış ve mevcut tek-commit dirty repo için
**harici sanitized staging repository'de yeni root history** yaklaşımını
önermiştir. Plan:

- original repo'ya dokunmadan full-tree ve ayrı `.git` backup,
- secret-safe diff patch ve SHA-256 manifestleri,
- candidate allowlist ve source/staging parity,
- current/history exact secret scan,
- yeni tek root commit,
- old remote SHA'ya karşı kontrollü `--force-with-lease`,
- remote post-verification ve rollback

adımlarını içerir.

Plan `baseline/git_history_remediation_plan.md` içindedir ve henüz
uygulanmamıştır. Provider revocation **NOT CONFIRMED** kalır. Commit ve remote
mutation ayrı kullanıcı onayı gerektirir.

## Remaining Phase 0 blockers

- Provider revoke/rotation teyidi.
- Hazırlanan history/remote remediation planının açık onayla uygulanması.
- Numeric equivalence production bug'ı.
- Stale Pexels string-path testinin canonical dict contract'a uyarlanması.
- System FFmpeg + ffprobe preflight.
- Fail-closed offline/cache-only ve isolated full-render reproduction.
- Kullanıcı diff'ini koruyan güvenli baseline commit/branch/tag.

Faz 1 implementation başlamamalıdır.

## Faz 0.1C local history replacement update

- Original secret-bearing `.git` değiştirilmeden full repository backup ve
  recovery artifacts üretildi.
- Fresh sibling source candidate historical exact-value taramasında
  0 eşleşme / 0 dosya verdi.
- Non-empty Pexels fallback pattern, genel secret pattern ve local env dosyası
  taramaları da sıfırdır.
- Sanitized candidate'ın source ile SHA-256 parity farkı yoktur.
- Secret-remediation testleri isolated temp root ile 5 passed sonucunu verdi.
- Fresh local single-root Git history oluşturuldu; authoritative new SHA
  recovery artifact/final handoff'ta kaydedilir.
- Remote push yapılmadı. `origin/main` exposure'ı exact old-SHA
  `--force-with-lease` onayı verilene kadar sürer.
- Provider revoke/rotation **NOT CONFIRMED** kalır.

Bu işlem current/reachable sanitized history riskini azaltır; provider-side
revocation yerine geçmez. Original ve backup `.git` artifact'leri hassas ve
offline tutulmalıdır.

## Faz 0.1C remote replacement sonucu

- Pre-push live `origin/main` expected old SHA ile eşleşti.
- Approved sanitized root exact `--force-with-lease` ile başarıyla gönderildi.
- Post-push live `origin/main` approved new SHA ile eşleşti.
- Fresh remote clone current tree ve reachable history exact-value taraması:
  0 eşleşme.
- Non-empty Pexels literal, generic secret ve local env dosyası: 0.
- Fresh clone eski commit object'ini içermiyor; `git fsck` temiz.

Bu sonuç yalnız reachable remote `main` zinciri ve fresh clone için
sanitization kanıtıdır. Provider revoke/rotation **NOT CONFIRMED** kalır ve
hosting cache/replica, fork veya eski clone'ların fiziksel silindiğini
kanıtlamaz. Original repo ve backup `.git` remote'a gönderilmemeli, bulutla
paylaşılmamalı veya public archive yapılmamalıdır.
