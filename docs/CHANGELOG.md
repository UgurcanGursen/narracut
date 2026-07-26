# Changelog

## 2026-07-26 - Faz 1 closure documentation and product operating model

- Faz 1, V3 contract/migrator/control-plane teslimatlari ve independent mini
  re-audit `PASS_WITH_FINDINGS` kanitiyla CLOSED olarak kaydedildi
- Optional automation capability execution ve Independent Editorial Critic
  Pipeline future binding kararlar olarak kaydedildi; runtime implementation
  eklenmedi
- Faz 2'nin tek giris gorevi Temporal Annotation and Word-Level Alignment
  Contract read-only specification and acceptance design olarak kesinlestirildi
- WorkspaceStore ve durable persistence Faz 14-17 future scope'unda tutuldu

## 2026-07-25 - Faz 1 secondary provenance URI security fix

- Primary target secimi ile source security acceptance birbirinden ayrildi
- Exact visual/extra URI-provenance field inventory'si `_account_remaining`
  yoluna deterministic URI context sagliyor
- Scheme-less, username-only, whitespace-obfuscated ve percent-encoded
  user-info URI context'inde fail-closed yapildi
- Dort affected field x strict/permissive gercek migrator+CLI no-leak matrix'i
  eklendi
- Narration email/colon ve guvenli secondary URI/local-path false-positive
  regression testleri eklendi
- Migrator suite: `126 passed`
- Combined suite: `213 passed, 1 skipped`
- Full suite: `269 passed, 1 skipped`
- Demo A/B/committed expected dort artifact byte equality: PASS
- 16 schema/159 ref, demo result/WorkspaceLoader ve
  minimal/business-tech/split-long-form loader kalite kapilari: PASS
- Secondary provenance URI hardening: PASS
- WorkspaceStore entry gate: PENDING_INDEPENDENT_REAUDIT

## 2026-07-25 - Faz 1 migrator security hardening

- URI user-info, sensitive query/fragment, signed-URL ve control-character
  kaynaklari standard-library security boundary ile fail-closed yapildi
- Raw secret'in workspace, result, mapping, report, summary ve CLI output'una
  tasinmamasi regression testleriyle sabitlendi
- FAILED migration target fingerprint/workspace ID alanlari null ve raporlar
  `not published` semantigine getirildi
- BGM/SFX bilinen alanlari aktif V2 modelinden exact allowlist olarak alindi;
  unknown/nested unknown alanlar iki modda da fail-closed yapildi
- Migrator suite: `111 passed`
- Birlesik contract/migrator suite: `198 passed, 1 skipped`
- Full suite: `254 passed, 1 skipped`
- Demo A/B/committed expected byte equality: PASS
- Multi-file output setinin transaction olmadigi ve WorkspaceStore zorunlu
  transaction acceptance kriterleri belgelendi
- Migrator security hardening: PASS
- WorkspaceStore entry gate: PENDING_INDEPENDENT_REAUDIT

## 2026-07-25 - Faz 1 V2ToV3Migrator

- Gercek V2 `TimelineV2`/production fixture contract'i field-by-field
  migration matrix ile envanterlendi
- Pure deterministic `engine.migration` paketi, strict/permissive policy,
  source-leaf coverage ve collision handling eklendi
- Canonical `migration_result.schema.json` legacy boundary korunarak structured
  mapping/loss, counts, fingerprint ve validation alanlariyla genisletildi
- Core-only ve gercek registry/resolver domain-pack migration modlari eklendi
- Safe atomic output IO ve thin CLI eklendi
- Faz 0 fixture'iyle byte-identical demo input ve incelenebilir dort expected
  artifact eklendi
- Yeni migrator suite: `60 passed`
- Hedefli suite: `147 passed, 1 skipped`
- Full suite: `203 passed, 1 skipped`
- V2ToV3Migrator: PASS; structured migration-loss reporting: PASS
- Faz 1 geneli OPEN/IN_PROGRESS; WorkspaceStore entry gate READY

## 2026-07-25 - Faz 1 public validation boundary

- Public artifact ve retention raw Mapping inputlari icin explicit SchemaCatalog dependency zorunlu oldu
- Schema-invalid input private construction ve semantic validation'dan once fail-closed durduruluyor
- Schema issue code/source/message ve JSON pointer bilgisi korunuyor
- WorkspaceLoader artifact graph cagrisi mevcut catalog dependency'sini aktariyor
- Rehashed forged snapshot'in gercek registry resolver parity kontrolunde reddi focused testle sabitlendi
- Hedefli suite: `85 passed, 1 skipped`
- Full suite: `143 passed, 1 skipped`
- Public validation boundary: PASS; migrator entry gate: READY

## 2026-07-25 - Faz 1 V3 contract integrity hardening

- Explicit `core_only` / `domain_pack` resolution mode contract'i eklendi
- Domain-pack workspace registry olmadan `DOMAIN_REGISTRY_REQUIRED` ile kapatildi
- Event ve base-shot track type routing fail-closed dogrulamasi eklendi
- Aggregate/split chapter-beat-sequence membership integrity eklendi
- Public raw dataclass mapping factory'leri private construction sinirina alindi
- Chapter, beat, sequence, asset, artifact, track ve event duplicate ID kontrolu eklendi
- Hedefli suite: `70 passed, 1 skipped`
- Full suite: `128 passed, 1 skipped`
- Contract integrity hardening: PASS; migrator entry gate: READY

## 2026-07-25 - Faz 1 V3 contract foundation

- Interrupted V3 contract calismasi recovery parity ile korunarak salvage edildi
- Split manifest kind/content binding, profile/snapshot integrity ve resolver parity eklendi
- Typed event target resolution ve event-group compatibility eklendi
- Split snapshot gercek business-tech resolver ciktisiyla yenilendi
- Faz 1 contract foundation: PASS; Faz 1 geneli OPEN/IN_PROGRESS

## 2026-07-25 - Faz 1 JSON Schema validator dependency provisioning

- `jsonschema[format]==4.26.0` canonical dependency olarak `requirements.txt`'ye eklendi
- Aktif Python ortaminda `python -m pip install "jsonschema[format]==4.26.0"` PASS
- `python -m pip check` PASS
- `Draft202012Validator.check_schema` ve `FormatChecker` runtime dogrulamasi PASS
- Yeni smoke test `tests/test_jsonschema_dependency.py` eklendi
- Hedefli test: `2 passed`
- Full suite: `58 passed`
- Faz 1 contract-foundation blocker: READY_TO_RESUME
- Faz 0 status: CLOSED

## 2026-07-25 - Faz 0 final baseline closure

- Final preflight temiz dogrulandi: branch `main`, local/remote HEAD `d1cac1ef27ad1c3977c62aed7a9de3691dc81223`, local/remote `stage3-development-baseline` yok, parentless sanitized root zinciri korundu
- Existing Phase 0 evidence artifacts birbirleriyle tutarli dogrulandi
- Final quality gate tekrarlandi: `56 passed`, JSON parse PASS, `git diff --check` PASS, `git fsck --full` clean, current/reachable Freesound/Pexels/generic secret scan `0`
- Final closure report `baseline/phase0_final_closure_report.md` eklendi
- Faz 0 technical acceptance: PASS
- Faz 0 management closure: PASS
- Faz 0 status: CLOSED
- Provider revoke/rotation: **NOT CONFIRMED** ve ayri security follow-up olarak korundu
- Siradaki ana faz: `Faz 1 - Editorial Domain Model ve V3 Workspace Schema`

## 2026-07-24 - Faz 0 offline isolated full-render closure

- Canonical closure fixture `baseline/fixtures/phase0_offline_full_render.json` eklendi
- Verification harness `scripts/verify_phase0_offline_render.py` ile gercek `v2.main.process_timeline` orchestration'i iki izole run root'ta calistirildi
- Root `main.py` yerine harness kullanimi, fail-closed guard ve run-scoped evidence capture hook'u gerektirdigi icin belgelendi
- Her iki run icin provider/network attempt sayisi `0`, repository mutation sayisi `0` ve output isolation PASS olarak dogrulandi
- Final MP4'ler `h264` video + `aac` audio ile gecerli, decode PASS, A/V drift `0.003s`
- Run 1 ve Run 2 decoded video fingerprint'leri eslesti
- Run 1 ve Run 2 decoded audio fingerprint'leri eslesti
- Full regression suite `56 passed`
- Offline isolated full render: PASS
- Fail-closed provider/network gate: PASS
- Two-run decoded-content reproducibility: PASS
- Faz 0 technical acceptance gates: PASS
- Provider revoke/rotation: **NOT CONFIRMED**
- Baseline tag: PENDING
- General Phase 0: OPEN pending final closure/tag decision

## 2026-07-24 - Faz 0.4B-S2 Freesound history replacement verified

### Verified

- Parentless sanitized root commit `49d57a5f05366df7779af277a36f949c74984f55` olusturuldu
- Live `origin/main` exact `--force-with-lease` ile eski SHA `1ba85a7e33dca034503f7b09878deb10689e3080` uzerinden degistirildi
- Fresh post-push clone `C:\Users\user\Documents\Kurgu_V3_Clean_freesound_postpush_verify_20260724_230300000` ile root history, blob parity, secret absence ve `49 passed` full suite dogrulandi
- Freesound current-tree remediation: PASS
- Freesound reachable main history remediation: PASS
- Remote replacement verification: PASS

### Still open

- Provider revoke/rotation: **NOT CONFIRMED**
- Drawtext operational gate: PASS with explicit fontfile / default Fontconfig known limitation
- Offline isolated full render: OPEN
- General Phase 0: OPEN

## 2026-07-24 - Faz 0 drawtext / Fontconfig operational gate closure

- Accepted paired `ffmpeg` / `ffprobe` runtime revalidated on the authoritative sanitized repository
- Default `drawtext` invocation reproduced the expected Fontconfig config-file failure
- Verified Windows font `C:\WINDOWS\Fonts\segoeui.ttf` used with escaped `fontfile=` strategy
- Explicit-font `drawtext` render passed with real frame-hash difference and valid `ffprobe` metadata
- Production inventory confirmed ordinary subtitles and text overlays use PIL/MoviePy rather than `drawtext`
- Only verified production `drawtext` call-site is the stock local-fallback generator in `v2.asset_manager.py`
- Drawtext capability decision: `DRAWTEXT_OPERATIONAL_WITH_EXPLICIT_FONTFILE`
- Faz 0 blocker decision: `NOT_A_BASELINE_BLOCKER`

## 2026-07-24 - Faz 0.4B existing paired runtime verification

- Existing paired runtime accepted
- drawtext practical invocation initially appeared blocked by Fontconfig before explicit-font verification

## 2026-07-24 - Faz 0.1B through Faz 0.4A recap

- Freesound current-tree remediation accepted
- Existing paired runtime verified
- Baseline tag not created
