# Faz 0.1B — Git History Remediation Plan

Hazırlanma tarihi: 24 Temmuz 2026  
Aktif branch: `main`  
Current HEAD: `c90009cd07da637607d456188deb3407570bef05`  
Plan durumu: **PREPARED / NOT EXECUTED**  
Provider revoke/rotation: **NOT CONFIRMED**

Bu belge yalnızca uygulanabilir operasyon planıdır. History rewrite, branch
oluşturma/değiştirme, commit, tag, push, force-push, reset, stash, clean,
checkout veya dosya silme yapılmamıştır. Historical credential bu belgeye
alınmamıştır.

## Current repository state

| Alan | Doğrulanmış durum |
|---|---|
| Branch | `main` |
| Upstream | `origin/main` |
| HEAD | `c90009cd07da637607d456188deb3407570bef05` |
| Toplam commit | 1 |
| Historical credential içeren commit | 1 |
| Local `origin/main` | HEAD ile aynı SHA |
| HEAD, `origin/main` tarafından erişilebilir | Evet |
| Remote | `origin`, HTTPS, GitHub |
| Remote URL userinfo | Yok |
| Tag | 0 |
| Working tree | Dirty |
| Tracked dosya | 83 |
| Non-ignored untracked dosya | 22; bu plan eklendikten sonra 23 |
| Current-tree historical credential scan | 0 eşleşme / 0 dosya |

Remote'un anlık server durumu ağla yeniden okunmadı. Local remote-tracking ref
aynı historical commit'i gösterdiği için remote exposure olasılığı yüksektir.

### Faz 0 / Faz 0.1 dosya ayrımı

Kullanıcı tarafından sağlanan governance/roadmap girdileri:

- `AGENTS.md`
- `docs/MASTER_ROADMAP.md`
- `docs/prompts/CODEX_PHASE_00_BOOTSTRAP.md`

Faz 0 proje hafızası:

- `docs/ARCHITECTURE_DECISIONS.md`
- `docs/CHANGELOG.md`
- `docs/CURRENT_STATE.md`
- `docs/DOMAIN_PACKS.md`
- `docs/KNOWN_LIMITATIONS.md`
- `docs/NEXT_ACTIONS.md`
- `docs/PHASE_ACCEPTANCE.md`
- `docs/QUALITY_BENCHMARKS.md`
- `baseline/baseline_manifest.json`
- `baseline/dependency_graph.md`
- `baseline/domain_assumption_inventory.md`
- `baseline/phase0_closure_assessment.md`
- `baseline/target_directory_map.md`
- `baseline/v2_2_schema_snapshot.json`

Faz 0.1 secret remediation:

- `.gitignore`
- `.env.example`
- `v2/config.py`
- `v2/asset_manager.py`
- `tests/test_pexels_secret_remediation.py`
- `baseline/secret_remediation_report.md`
- Faz 0 hafıza dosyalarındaki ilgili güncellemeler

Faz 0.1B:

- `baseline/git_history_remediation_plan.md`
- Zorunlu docs ve baseline manifest güncellemeleri

## User changes that must be preserved

Bu altı tracked dosya görev öncesi kullanıcı değişikliğidir ve remediation
işlemi bunları byte-parity/hash manifestiyle korumalıdır:

| Dosya | Eklenen satır | Silinen satır |
|---|---:|---:|
| `test_1_min.json` | 196 | 188 |
| `v2/main.py` | 64 | 52 |
| `v2/modules.py` | 233 | 80 |
| `v2/video_engine.py` | 278 | 1 |
| `v2/visual_dispatcher.py` | 183 | 55 |
| `v2/web_engine.py` | 107 | 102 |
| **Toplam** | **1061** | **478** |

Koruma yalnızca bu altı dosyayla sınırlı değildir. Faz 0/Faz 0.1 untracked
artifact'leri, `.gitignore`, `.env.example`, `v2/config.py`,
`v2/asset_manager.py` ve secret-remediation testi de sanitized root candidate
içinde açıkça envanterlenmelidir.

## Current exposure status

- Current working tree'de historical credential exact-match sonucu sıfırdır.
- Git history'deki tek commit historical credential'ı içerir.
- `origin/main` local remote-tracking ref'i aynı commit'i gösterir.
- Provider revoke/rotation tamamlanmamıştır veya teyit edilememektedir:
  **NOT CONFIRMED**.
- Eski secret compromised kabul edilmelidir.
- History rewrite yapılmamıştır; local `.git` object database ve muhtemel
  remote halen exposure kapsamındadır.

## Evaluated remediation options

| Seçenek | Kullanıcı değişikliği kayıp riski | Rollback | Remote etkisi | Force-push | Tek commit için uygunluk | Öneri |
|---|---|---|---|---|---|---|
| A. `git-filter-repo` ile rewrite | Orta/yüksek: dirty ve untracked içerik önce ayrı snapshot'a taşınmalı; yanlış path/replacement mevcut kullanıcı diff'ini dışarıda bırakabilir | Harici `.git` ve full-tree backup ile mümkün | Mevcut commit SHA değişir; bütün klonlar etkilenir | Evet | Teknik olarak uygun fakat bir commit için gereksiz karmaşık | Hayır |
| B. Sanitized orphan branch/new root | Orta: aynı dirty repo içinde orphan checkout risklidir; staging kopyada daha güvenli | Harici backup ile kolay | `main` yeni root'a taşınır; eski ref/reflog temizliği gerekir | Evet | Uygun | İkinci tercih |
| C. Yeni temiz Git history'yi harici staging repo'da başlatma | Düşük: original repo ve dirty tree hiç değiştirilmez; allowlist/hash parity ile kopyalanır | En kolay: push öncesi original repo tamamen sağlam kalır | Remote `main` yeni root SHA'ya kontrollü taşınır | Evet | Tek commit history için en sade ve denetlenebilir yol | **Önerilen** |
| D. Revoke sonrası history'yi bırakma | Working tree kayıp riski yok | Gereksiz | Remote exposure kalıcı olur | Hayır | Ancak credential kesin revoke edilmiş ve risk kabul edilmişse | Hayır; revoke teyitsiz |

## Recommended option

**Seçenek C: original dirty repo'ya dokunmadan, repository dışında sanitized
bir staging repository oluşturup tek yeni root commit üretmek.**

Gerekçeler:

1. Original `.git`, working tree ve kullanıcı diff'i operasyon boyunca
   değişmez.
2. Yeni repo eski object, reflog veya secret-bearing ref içermez.
3. Tek commitli history için `filter-repo` yerine daha az hareketli parça vardır.
4. File allowlist ve SHA-256 parity push öncesinde kesin doğrulanabilir.
5. Push öncesi rollback, staging klasörünü terk edip original repo ile devam
   etmek kadar basittir.
6. Remote güncellemesi expected old SHA'lı `--force-with-lease` ile
   sınırlandırılabilir.

Provider revocation teyitsiz olduğu için bu yaklaşım exposure'ı azaltır fakat
provider-side güvenlik açığını tek başına kapatmaz.

## Exact proposed operation sequence

Aşağıdaki komutlar **bu görevde çalıştırılmamıştır**. `<SECURE_BACKUP_BASE>` ve
`<SANITIZED_STAGING_BASE>` kullanıcı tarafından repository dışındaki gerçek,
erişimi kısıtlı absolute path'lerle değiştirilmelidir.

### 0. Exclusive execution window ve preflight

```powershell
$SourceRepo = (Resolve-Path 'C:\Users\user\Documents\Kurgu_V3_Clean').Path
$BackupBase = '<SECURE_BACKUP_BASE>'
$StagingBase = '<SANITIZED_STAGING_BASE>'
$Stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$BackupRoot = Join-Path $BackupBase "Kurgu-history-remediation-$Stamp"
$StagingRepo = Join-Path $StagingBase "Kurgu-sanitized-$Stamp"

$OldHead = git -C $SourceRepo rev-parse HEAD
$OldRemoteTrackingHead = git -C $SourceRepo rev-parse refs/remotes/origin/main
if ($OldHead -ne 'c90009cd07da637607d456188deb3407570bef05') {
    throw 'HEAD changed; regenerate and reapprove the plan.'
}
if ($OldHead -ne $OldRemoteTrackingHead) {
    throw 'Local origin/main changed; stop and reassess.'
}
if (Test-Path -LiteralPath $BackupRoot) { throw 'Backup target already exists.' }
if (Test-Path -LiteralPath $StagingRepo) { throw 'Staging target already exists.' }
```

Execution sırasında başka kullanıcı/agent repo dosyalarını değiştirmemelidir.
Preflight sonrası status ve manifest yeniden alınır; bu rapordaki sayılarla
uyuşmazsa işlem durur.

### 1. Repository dışı yedekler

```powershell
New-Item -ItemType Directory -Path $BackupRoot | Out-Null
New-Item -ItemType Directory -Path $StagingRepo | Out-Null

robocopy $SourceRepo (Join-Path $BackupRoot 'full-worktree') /E /XJ /XD (Join-Path $SourceRepo '.git')
if ($LASTEXITCODE -gt 7) { throw 'Full worktree backup failed.' }

robocopy (Join-Path $SourceRepo '.git') (Join-Path $BackupRoot 'git-metadata') /E /XJ
if ($LASTEXITCODE -gt 7) { throw 'Git metadata backup failed.' }

$OldHead | Set-Content -LiteralPath (Join-Path $BackupRoot 'HEAD.sha') -Encoding ascii
git -C $SourceRepo status --porcelain=v2 |
    Set-Content -LiteralPath (Join-Path $BackupRoot 'status.porcelain-v2.txt') -Encoding utf8
```

Raw `git diff` içinde removed historical literal bulunabileceği için
`v2/asset_manager.py` patch'ten bilerek çıkarılır. Current sanitized dosya full
worktree backup ve SHA manifestinde korunur.

```powershell
git -C $SourceRepo diff --binary -- . ':(exclude)v2/asset_manager.py' |
    Set-Content -LiteralPath (Join-Path $BackupRoot 'working-tree-safe.patch') -Encoding utf8
git -C $SourceRepo diff --cached --binary -- . ':(exclude)v2/asset_manager.py' |
    Set-Content -LiteralPath (Join-Path $BackupRoot 'index-safe.patch') -Encoding utf8
git -C $SourceRepo ls-files --others --exclude-standard |
    Set-Content -LiteralPath (Join-Path $BackupRoot 'untracked-paths.txt') -Encoding utf8
```

Tracked ve untracked SHA-256 manifestleri:

```powershell
$Tracked = @(git -C $SourceRepo ls-files)
$Untracked = @(git -C $SourceRepo ls-files --others --exclude-standard)

$Tracked | ForEach-Object {
    $Path = Join-Path $SourceRepo $_
    if (Test-Path -LiteralPath $Path -PathType Leaf) {
        $Hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
        [pscustomobject]@{ path = $_; sha256 = $Hash }
    }
} | ConvertTo-Json -Depth 3 |
    Set-Content -LiteralPath (Join-Path $BackupRoot 'tracked-sha256.json') -Encoding utf8

$Untracked | ForEach-Object {
    $Path = Join-Path $SourceRepo $_
    if (Test-Path -LiteralPath $Path -PathType Leaf) {
        $Hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
        [pscustomobject]@{ path = $_; sha256 = $Hash }
    }
} | ConvertTo-Json -Depth 3 |
    Set-Content -LiteralPath (Join-Path $BackupRoot 'untracked-sha256.json') -Encoding utf8
```

Backup klasörü şifreli/offline storage'a alınmalı; `.git` yedeği compromised
historical credential içerdiği için normal bulut senkronizasyonuna
konulmamalıdır.

### 2. Sanitized candidate allowlist ve staging copy

Fresh root'a yalnızca tracked veya non-ignored untracked source/artifact
dosyaları alınır. Generated debug JSON'lar açıkça çıkarılır.

```powershell
$ExcludedCandidatePaths = @(
    'norm_words_debug.json',
    'whisper_debug.json'
)

$CandidatePaths = @(
    git -C $SourceRepo ls-files -co --exclude-standard
) | Sort-Object -Unique | Where-Object {
    $_ -notin $ExcludedCandidatePaths
}

foreach ($RelativePath in $CandidatePaths) {
    $SourcePath = Join-Path $SourceRepo $RelativePath
    if (-not (Test-Path -LiteralPath $SourcePath -PathType Leaf)) { continue }
    $TargetPath = Join-Path $StagingRepo $RelativePath
    $TargetParent = Split-Path -Parent $TargetPath
    New-Item -ItemType Directory -Force -Path $TargetParent | Out-Null
    Copy-Item -LiteralPath $SourcePath -Destination $TargetPath
}
```

Bu allowlist `.git`, ignored `.env` dosyaları, `cache/`, `output/` ve
`temp_assets/` içeriğini staging repo'ya taşımaz.

### 3. Source/staging hash parity

```powershell
$SourceParity = foreach ($RelativePath in $CandidatePaths) {
    $Path = Join-Path $SourceRepo $RelativePath
    [pscustomobject]@{
        path = $RelativePath
        sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
    }
}
$StagingParity = foreach ($RelativePath in $CandidatePaths) {
    $Path = Join-Path $StagingRepo $RelativePath
    [pscustomobject]@{
        path = $RelativePath
        sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
    }
}
$ParityDiff = Compare-Object $SourceParity $StagingParity -Property path, sha256
if ($ParityDiff) { $ParityDiff; throw 'Source/staging parity failed.' }
```

Özellikle altı kullanıcı dosyası için ayrıca explicit SHA kontrolü yapılır.

### 4. Fresh Git initialization; commit öncesi doğrulama

```powershell
git -C $StagingRepo init -b main
git -C $StagingRepo add -A
git -C $StagingRepo status --short
Push-Location $StagingRepo
try {
    python -m pytest -q
}
finally {
    Pop-Location
}
```

Beklenen pytest baseline'ı mevcut durumda 34 passed ve iki bilinen failure'dır;
yeni failure oluşursa durulur.

Historical credential, secured old Git backup'tan yalnızca process belleğine
alınır; hiçbir dosyaya veya console'a yazılmaz. Candidate files exact-match
scan sonucu sıfır değilse commit oluşturulmaz.

```powershell
$OldGitDir = Join-Path $BackupRoot 'git-metadata'
$OldAssetSource = git --git-dir=$OldGitDir show "$OldHead`:v2/asset_manager.py"
$CredentialMatch = [regex]::Match(
    ($OldAssetSource -join "`n"),
    'os\.environ\.get\("PEXELS_API_KEY",\s*"([^"]+)"\)'
)
if (-not $CredentialMatch.Success) {
    throw 'Historical credential could not be identified without output.'
}
$HistoricalCredential = $CredentialMatch.Groups[1].Value

$CandidateSecretMatches = 0
foreach ($RelativePath in $CandidatePaths) {
    $Path = Join-Path $StagingRepo $RelativePath
    try {
        $Content = [System.IO.File]::ReadAllText($Path)
        $CandidateSecretMatches += [regex]::Matches(
            $Content,
            [regex]::Escape($HistoricalCredential)
        ).Count
    }
    catch {
        # Binary/non-text files are handled by the post-commit object scan.
    }
}
Write-Output "candidate_secret_matches=$CandidateSecretMatches"
if ($CandidateSecretMatches -ne 0) {
    throw 'Historical credential remains in staging.'
}
```

### 5. Kullanıcı onaylı sanitized root commit

Yalnızca parity, secret scan ve test kontrolleri kabul edilirse:

```powershell
git -C $StagingRepo commit -m 'Establish sanitized repository baseline'
$NewHead = git -C $StagingRepo rev-parse HEAD
if ((git -C $StagingRepo rev-list --count HEAD) -ne '1') {
    throw 'Sanitized history must contain exactly one root commit.'
}
```

Commit mesajı herhangi bir credential veya secret fingerprint'i içermez.

### 6. Commit/history doğrulama

```powershell
git -C $StagingRepo fsck --full --no-reflogs --unreachable
git -C $StagingRepo status --porcelain=v2
git -C $StagingRepo rev-list --count --all
git -C $StagingRepo show --stat --oneline --decorate HEAD
```

Current tree ve yeni root committe historical exact-value eşleşmesi sıfır
olmalıdır. Fresh `.git` içinde eski commit, ref, reflog veya unreachable object
olmamalıdır. `git fsck` çıktısı beklenmeyen object gösterirse işlem durur.

Reachable history exact-value scan'i içeriği yazdırmadan:

```powershell
$HistorySecretMatches = 0
foreach ($Commit in (git -C $StagingRepo rev-list --all)) {
    foreach ($RelativePath in (git -C $StagingRepo ls-tree -r --name-only $Commit)) {
        $Blob = git -C $StagingRepo show "$Commit`:$RelativePath" 2>$null
        if ($LASTEXITCODE -eq 0) {
            $HistorySecretMatches += [regex]::Matches(
                ($Blob -join "`n"),
                [regex]::Escape($HistoricalCredential)
            ).Count
        }
    }
}
Write-Output "history_secret_matches=$HistorySecretMatches"
if ($HistorySecretMatches -ne 0) {
    throw 'Historical credential remains in reachable history.'
}
```

### 7. Remote lease preflight ve kontrollü update

```powershell
$OriginUrl = git -C $SourceRepo config --get remote.origin.url
git -C $StagingRepo remote add origin $OriginUrl

$RemoteLine = git -C $StagingRepo ls-remote --heads origin refs/heads/main
$RemoteHead = ($RemoteLine -split '\s+')[0]
if ($RemoteHead -ne $OldHead) {
    throw 'Remote main changed; force-push is forbidden until plan is regenerated.'
}

git -C $StagingRepo push `
    --force-with-lease=refs/heads/main:$OldHead `
    origin main:main
```

Bu adım ağ ve destructive remote mutation içerir; ayrı, açık kullanıcı onayı
gerektirir. Plain `--force` kullanılmaz.

### 8. Remote post-verification

```powershell
$VerifiedRemoteLine = git -C $StagingRepo ls-remote --heads origin refs/heads/main
$VerifiedRemoteHead = ($VerifiedRemoteLine -split '\s+')[0]
if ($VerifiedRemoteHead -ne $NewHead) {
    throw 'Remote verification failed.'
}
git -C $StagingRepo fetch origin main
git -C $StagingRepo branch --set-upstream-to=origin/main main
git -C $StagingRepo status --short --branch
```

GitHub branch protection, Actions, deploy keys ve collaborators ayrıca
kontrol edilmelidir. Diğer klonlar eski history'yi merge etmemeli; fresh clone
veya hard realignment için koordinasyon gerekir.

## Backup and rollback plan

### Push öncesi rollback

- Original repo hiç değişmediği için staging işleminden vazgeçilir.
- Original dirty tree ve `.git` kullanılmaya devam edilir.
- Backup manifestleri parity incelemesi için saklanır.
- Staging veya backup silme bu plandan ayrı açık onay gerektirir.

### Push sonrası güvenli düzeltme

Sanitized root'ta hata bulunursa tercih edilen rollback, secret-bearing old
commit'i geri push etmek değildir:

1. Original full-worktree backup'tan yeni corrected sanitized staging üret.
2. Hash parity ve secret/history scan'i tekrar çalıştır.
3. Yeni corrected root'u mevcut sanitized remote SHA'ya karşı
   `--force-with-lease` ile güncelle.

### Acil eski-remote rollback

Eski HEAD'i remote'a geri taşımak historical credential'ı yeniden yayınlar.
Provider revoke teyitsizken bu güvenlik açısından önerilmez. Yalnızca incident
owner açıkça onaylar ve erişim sürekliliği daha yüksek öncelik kabul edilirse,
secured original repo kullanılarak current remote SHA'ya karşı
`--force-with-lease` uygulanabilir. Plain force kullanılmaz.

Local rollback kaynağı:

- repository dışı `full-worktree` backup,
- ayrı `git-metadata` backup,
- recorded `HEAD.sha`,
- safe tracked diff patch,
- tracked/untracked SHA-256 manifestleri,
- original repo klasörü.

## Generated-file tracking policy

| Yol | Mevcut durum | Sanitized commit politikası | Backup politikası |
|---|---|---|---|
| `cache/` | 30 dosya / 37,868,989 byte; ignored, tracked değil | Commit'e girmez | Gerekirse full filesystem backup'ta tutulur |
| `output/` | 56 dosya / 216,836,994 byte; ignored, tracked değil | Commit'e girmez | Baseline kanıtı olarak offline backup'ta tutulabilir |
| `temp_assets/` | 58 dosya / 37,242,885 byte; ignored, tracked değil | Commit'e girmez | Reproducibility ihtiyacına göre offline backup |
| `norm_words_debug.json` | 48 byte; untracked ve ignore değil | Candidate allowlist'ten çıkarılır | Full backup'ta tutulabilir |
| `whisper_debug.json` | 7,029 byte; untracked ve ignore değil | Candidate allowlist'ten çıkarılır | Full backup'ta tutulabilir |
| Local `.env` ailesi | Mevcut local dosya yok; ignore kuralları var | Asla commit'e girmez | Gerekiyorsa ayrı encrypted secret storage |
| `.env.example` | Empty-only örnek | Commit'e girer | Normal source backup |

Bu görev `.gitignore` kapsamını genişletmez ve hiçbir generated dosyayı silmez.
Debug JSON ignore kararı ayrı, açık bir maintenance değişikliği olmalıdır.

## Post-rewrite verification checklist

- [ ] Original repo ve backup hashleri değişmemiş.
- [ ] Candidate file listesi kullanıcı tarafından onaylanmış.
- [ ] Altı protected kullanıcı dosyasının source/staging SHA-256 parity'si tam.
- [ ] Tüm candidate dosyalarının source/staging parity'si tam.
- [ ] Current staging tree historical secret exact scan: 0.
- [ ] Yeni Git history commit sayısı: 1.
- [ ] Bütün reachable commitlerde historical secret exact scan: 0.
- [ ] Fresh `.git` object/ref/reflog scan: eski commit yok.
- [ ] `git fsck --full --no-reflogs --unreachable`: beklenmeyen object yok.
- [ ] `git status`: commit öncesi yalnızca beklenen staged dosyalar; commit
      sonrası clean.
- [ ] Pytest sonucu mevcut bilinen baseline'dan kötü değil.
- [ ] `docs/` ve `baseline/` file/hash integrity tam.
- [ ] Generated/cache/output/env dosyaları staged değil.
- [ ] Remote pre-push SHA tam olarak recorded old HEAD.
- [ ] Push yalnızca exact `--force-with-lease` ile yapılmış.
- [ ] Remote `main` post-push SHA yeni sanitized HEAD ile aynı.
- [ ] GitHub branch protection/CI sonucu doğrulanmış.
- [ ] Collaborator'lara fresh-clone/realignment talimatı iletilmiş.
- [ ] Provider revoke/rotation durumu hâlâ ayrı blocker olarak görünür.

## User confirmations required

Execution başlamadan önce şu onayların tamamı gerekir:

1. Provider revoke/rotation durumunun **NOT CONFIRMED** kalmasının yarattığı
   aktif riskin kabulü.
2. Seçenek C'nin ve yeni tek-root history'nin onayı.
3. Sanitized root'a girecek candidate file listesinin onayı.
4. `norm_words_debug.json`, `whisper_debug.json`, cache/output/temp ve local
   `.env` ailesinin commit dışında kalmasının onayı.
5. Repository dışı secure backup ve staging absolute path'lerinin verilmesi.
6. Backup'ın şifreleme/erişim/retention sahibinin belirlenmesi.
7. GitHub branch protection ve force-push yetkisinin hazır olması.
8. Collaborator/CI/deploy koordinasyon penceresinin onayı.
9. Sanitized root commit oluşturmak için ayrı onay.
10. Recorded remote SHA'ya karşı `--force-with-lease` push için ayrı son onay.
11. Eski history backup'ının ne zaman ve kim tarafından imha edileceği kararı.

Talepteki “provider revocation user-confirmed” acceptance maddesi, açık
`NOT CONFIRMED` talimatıyla çelişir ve bu görevde karşılanmış sayılmaz.

## Remaining Phase 0 blockers

- Provider revoke/rotation teyidi.
- Bu planın kullanıcı tarafından onaylanması ve ayrı görevde uygulanması.
- Remote sanitized history doğrulaması ve collaborator koordinasyonu.
- Numeric equivalence production bug'ı.
- Stale Pexels string-path testinin canonical dict contract'a uyarlanması.
- System FFmpeg + ffprobe preflight.
- Fail-closed offline/cache-only isolated full-render reproduction.
- Başarılı kanıtlardan sonra güvenli baseline tag.

Faz 1 implementation başlamamalıdır.
