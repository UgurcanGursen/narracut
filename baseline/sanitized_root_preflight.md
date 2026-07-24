# Faz 0.1C — Sanitized Root Preflight

Değerlendirme tarihi: 24 Temmuz 2026  
Durum: **LOCAL SANITIZED ROOT READY; REMOTE PUSH NOT PERFORMED**

## Scope and safety boundary

Bu çalışma original dirty repository üzerinde history rewrite, checkout, reset,
clean, stash, branch değişikliği, commit, tag veya dosya silme yapmadı. Original
repo `main` branch'i ve `c90009cd07da637607d456188deb3407570bef05` HEAD'i
korundu. Altı kullanıcı dosyasındaki 1061 ekleme / 478 silme aynen kaldı.

Provider revoke/rotation durumu **NOT CONFIRMED**'dır. History sanitization,
provider-side credential iptalinin yerine geçmez.

## Paths and recovery artifacts

- Authoritative backup root:
  `C:\Users\user\Documents\Kurgu_V3_Clean_backup_20260724_163134`
- Full repository snapshot:
  `C:\Users\user\Documents\Kurgu_V3_Clean_backup_20260724_163134\repository`
- Recovery artifacts:
  `C:\Users\user\Documents\Kurgu_V3_Clean_backup_20260724_163134\recovery`
- Sanitized sibling repository:
  `C:\Users\user\Documents\Kurgu_V3_Clean_sanitized_20260724_163134`
- Earlier incomplete backup attempt:
  `C:\Users\user\Documents\Kurgu_V3_Clean_backup_20260724_163006`

İlk backup denemesi generated `.pytest_cache` ACL hatası nedeniyle kabul
edilmedi ve silinmedi. Authoritative backup, yalnızca erişilemeyen generated
`.pytest_cache` içeriğini hariç tutarak 608 dosya ve 4,891,937,629 byte source
parity'si sağladı. `.git`, current working tree, kullanıcı değişiklikleri,
docs/baseline ve generated/output içeriği backup'ta korundu. Backup içindeki
eski `.git` secret-bearing history taşıdığı için hassas ve offline tutulmalıdır.

Recovery paketi status, safe tracked diff, empty staged diff, untracked
manifest, tracked/critical SHA-256 manifestleri, old HEAD/branch, redacted
remote durumu ve rollback talimatlarını içerir. `tracked_diff.patch`,
historical credential'ı removed line olarak yeniden üretmemek için
`v2/asset_manager.py` dosyasını bilerek içermez; sanitized current dosya full
backup ve critical hash manifestinde korunur.

## Candidate tracking decision

Sanitized root candidate'ı `git ls-files -co --exclude-standard` tabanlıdır.

Commit kapsamına alınan önemli fixture'lar:

- `timeline.json`
- `test_1_min.json`
- `ibm_v3_native.json`
- `tests/fixtures/` ve `tests/assets/` altındaki tracked acceptance verileri

Commit kapsamı dışında bırakılanlar:

- `norm_words_debug.json` — generated, untracked, ignore edilmemiş debug çıktısı
- `whisper_debug.json` — generated, untracked, ignore edilmemiş debug çıktısı
- `.git`
- ignored `cache/`, `output/`, `temp_assets/`
- `__pycache__`, `.pytest_cache`
- local `.env`, `.env.local`, `.env.*.local`

İlk candidate 104 dosyaydı; bu preflight raporu ve final Faz 0.1C belge
güncellemeleri sync edildiğinde final candidate manifesti yeniden üretilecektir.

## Secret and parity gates

Commit öncesi sibling taramasında:

- historical credential exact match: 0 eşleşme / 0 dosya
- non-empty Pexels literal fallback pattern: 0 eşleşme / 0 dosya
- genel private-key/token/key-assignment pattern'leri: 0 eşleşme / 0 dosya
- local secret/env dosyası: 0
- source/sibling candidate SHA-256 farkı: 0
- altı protected kullanıcı dosyasında SHA-256 farkı: 0
- unexpected extra veya missing candidate: 0
- staged forbidden generated/cache/output/env yolu: 0

Secret değer hiçbir loga, rapora, patch'e veya yanıta yazılmadı. Exact-value
scan için değer yalnızca secured old Git snapshot'tan process belleğine
alınmıştır.

## Compile and test gates

Sibling repo üzerinde ağsız çalıştırılan kontroller:

| Kontrol | Sonuç |
|---|---|
| `python -m json.tool baseline/baseline_manifest.json` | PASS |
| Hedef production/test `python -m py_compile` | PASS |
| `python -m compileall -q .` | KNOWN FAIL: yalnız `v2/audio_engine_debug.py` ve `v2/audio_engine_debug2.py` |
| `python -m pytest -q tests/test_pexels_secret_remediation.py --basetemp <isolated>` | PASS: 5 passed |
| İki bilinen testin hedefli çalışması | EXPECTED FAIL: 2 failed |
| `python -m pytest -q --basetemp <isolated>` | BASELINE: 34 passed, 2 failed |

İlk pytest denemesinde user temp root ACL hatası oluştu; bu production/test
contract sonucu değildir. Erişilebilir, ayrı `C:\tmp` basetemp ile tekrar
çalıştırıldığında yalnız bilinen iki failure kaldı:

- `tests/test_adversarial_alignment.py::test_numeric_equivalent`
- `tests/test_v2_core.py::TestV2Core::test_pexels_key_missing_fallback`

Faz 0.1C bu iki testi veya production davranışını değiştirmez.

## Local root and remote lease boundary

Sibling fresh Git repository'si `main` branch'inde sıfır committen
başlatılmıştır. Sanitized root commit mesajı:

`chore: establish sanitized Kurgu Engine baseline`

Bu rapor root commitin parçasıdır; commit SHA'sı commit içeriğine
self-reference olarak yazılamaz. Authoritative SHA commit sonrasında recovery
paketindeki `sanitized_root_commit.txt` ve final handoff'ta kaydedilir.

Expected old remote SHA:
`c90009cd07da637607d456188deb3407570bef05`

Onay verilirse kullanılacak tek remote mutation biçimi:

```text
git push --force-with-lease=refs/heads/main:c90009cd07da637607d456188deb3407570bef05 origin main:main
```

Bu komut bu görevde kullanıcıya gösterilmeden/ayrı açık onay alınmadan
çalıştırılmaz. Plain `--force` kullanılmaz. Push öncesinde live
`refs/heads/main` SHA yeniden doğrulanmalı; expected SHA farklıysa işlem
durmalıdır.

## Rollback

Push öncesi rollback: sibling repo terk edilir; original dirty repo ve
authoritative backup değişmeden kullanılmaya devam eder.

Push sonrası tercih edilen düzeltme: secret-bearing old root'u geri taşımak
yerine backup'tan corrected sanitized root üretip mevcut remote sanitized SHA'ya
karşı yeni exact `--force-with-lease` uygulamaktır. Eski root'u remote'a geri
yüklemek historical credential'ı yeniden yayımlar ve provider revocation
teyitsizken önerilmez.

## Post-push update

- Push approval: açıkça verildi.
- Pre-push live remote SHA: expected old SHA ile eşleşti.
- Exact `--force-with-lease`: başarılı.
- Post-push remote SHA: approved sanitized root ile eşleşti.
- Fresh remote clone:
  `C:\Users\user\Documents\Kurgu_V3_Clean_postpush_verify_20260724_170436`.
- Clone/history/secret/parity/parse/compile/test doğrulamaları geçti; full
  pytest yalnız bilinen iki failure ile 34 passed sonucunu korudu.
- Post-push docs henüz commit veya push edilmedi.

## Remaining gates

- Provider revoke/rotation teyidi
- Faz 0'ın diğer mevcut blocker'ları: iki test, system FFmpeg/ffprobe ve
  fail-closed offline isolated full-render kanıtı
- Post-push docs için ayrı takip commit/push onayı

Faz 1 implementation başlatılmamıştır.
