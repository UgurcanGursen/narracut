# Known Limitations

Son guncelleme: 4 Agustos 2026

## Known limitations ve follow-up'lar

1. Provider revoke/rotation durumu **NOT CONFIRMED** olarak ayri security follow-up olarak kalir.
2. Varsayilan Fontconfig font discovery bu Windows ortaminda calismaz; `drawtext` yalniz explicit `fontfile` ile dogrulanmistir.

## Security sinirlari

- Reachable `origin/main` history sanitized root ile remediated durumdadir.
- Bu yine de hosting cache/replica retention, eski clone/fork veya local sensitive repository'lerde fiziksel yokluk kaniti degildir.
- Eski source repo, backup'lar ve onceki clone'lar secret-bearing Git metadata tasiyabilir; remote'a push edilmemeli, bulutla paylasilmamali ve yeni authoritative development icin kullanilmamalidir.

## Runtime ve reproduction sinirlari

- Koku CLI icin explicit offline/cache-only/skip-download modu yoktur.
- Legacy output override yoktur.
- Edge TTS, YouTube, web capture ve benzeri yollar ag bagimliligi tasir.
- Closure fixture render'i `phase0_block_01` icin `159.5 WPM` warning'i ile `success_with_warnings` dondurur; decoded fingerprint, A/V drift ve output validity gate'leri yine de PASS durumundadir.
- `v2/audio_engine_debug.py` ve `v2/audio_engine_debug2.py` bilinen debug debt olarak disarida tutulur.

## Faz 0 status note

- Bu limitation ve security follow-up'lar Faz 0'i tekrar OPEN yapan teknik blocker olarak siniflandirilmaz.

## Faz 1 status note

- Faz 1 CLOSED durumundadir. V3 contract foundation, contract integrity,
  public validation boundary, V2ToV3Migrator, migration-loss reporting,
  migrator URI security, thin project API, generated client/UI shell ve
  post-audit test hardening kanitlanmistir.
- API project catalog process-lifetime in-memory'dir; restart sonrasi project
  state kaybolur. WorkspaceStore, SQLite, durable persistence, upload, render
  orchestration/progress, authentication, billing ve full review UI yoktur.
- Studio UI thin control-plane shell'dir; temporal alignment, end-user video
  production flow, automated provider execution veya Critic pipeline
  implementation claim etmez.
- V2 audio file, BGM/SFX, pause, frame-duration, subtitle ve renderer-specific
  visual ayarlari Phase 1 canonical workspace'te birebir temsil edilmez.
  Migrator bunlari structured loss olarak raporlar; strict mod yayinlamaz.
- Descriptor fingerprint, source media hash'i bulunmadiginda yalniz
  deterministic review placeholder'idir; media-byte hash'i oldugu iddia
  edilmez ve manual verification gerekir.
- Aggregate migration outputta embedded policy snapshot authoritative'dir;
  `policy_snapshot_ref` logical/informational identity'dir. Split workspace'te
  ayni alan gercek external document reference olmaya devam eder.
- Migrator her output dosyasini tek basina atomic replace ile yazar; dort
  artifact seti transaction degildir ve write/process failure sonrasi
  mixed-generation set kalabilir. Production persistence icin guvenilir
  sayilmaz.
- WorkspaceStore staged revision directory, tum artifact hash dogrulamasi,
  revision manifest, file close/fsync, commit marker veya atomic active
  revision pointer, crash recovery, mixed-generation engeli, onceki valid
  revision'i koruma ve partial staging cleanup saglamalidir.
- Faz 1 production persistence, timing/frame, renderer integration ve Studio
  API/UI kapsamlarini henuz tamamlamaz.
- `engine/contracts/workspace.py` modul boyutu LOW/non-blocking teknik borctur;
  yeni integrity kontrolleri private helper'lara ayrilmis, genis bolme/refactor
  ertelenmistir.

## Faz 2 status note

- Slice 1-4 repository evidence reconciliation completed.
- Post-Slice-4 scope reconciliation is no longer a blocker; the scope report is
  remote closed at `f89e10156a940016deef4e94b6aef8863837dbf6`.
- Remote-closed scope report path:
  `baseline/phase2_post_slice4_scope_report.md`.
- Remote-closed scope report SHA-256:
  `aefaacf8e19e94c1f1f31615550d6e76c2d1184cb290ce34c12264df4cc3703f`.
- `TERRASCOPE-001` is CLOSED by targeted Terra re-audit.
- Slice 4 is remote closed at
  `d32e66585d660bc3e37a1896dbb7df050a8bc849`.
- The bounded Slice 5 specification-path decision is remote closed.
- Decision report path:
  `baseline/phase2_slice5_specification_path_decision_report.md`.
- Decision report commit:
  `d61500d861762bb6215e0f3041c144e25ea10752`.
- Decision report SHA-256:
  `cab27022625b6edd19562070ff35950a57eb591b10e58b1cd9621eb028295049`.
- Selected Slice 5 specification path:
  `docs/specifications/phase2_slice5_canonical_adapter_execution_provenance_contract.md`.
- The corrected Slice 5 candidate specification commit is remote closed at
  `e262b9d0ce60c01f2e88519b2c0e58d7a9417ea6`.
- Corrected specification SHA-256:
  `e6de8c1cdf52498a8e5c657962e48fc9915f58065621c8cb586c0c213ab7d71f`.
- Corrected specification UTF-8 byte length: `104240`.
- Independent corrected-specification re-audit: PASS with 0 BLOCKER /
  0 MAJOR / 0 MINOR findings.
- The corrected specification is accepted by the external decision record
  `baseline/phase2_slice5_specification_acceptance_decision_report.md`.
- The immutable specification file retains its historical `Accepted: No`
  metadata and remains byte-for-byte unchanged.
- Slice 5 bounded implementation authorization is granted by
  `baseline/phase2_slice5_implementation_authorization_decision_report.md`.
- The public-export compatibility repair is authorized by
  `baseline/phase2_slice5_implementation_scope_correction_report.md`.
- Scope correction: `AUTHORIZED`.
- The corrected implementation boundary is exactly
  `engine/contracts/alignment_execution.py`,
  `tests/test_alignment_execution.py`, `engine/contracts/__init__.py`, and
  `tests/test_alignment_request.py`.
- The bounded AdapterExecution implementation is accepted and remote closed.
- Implementation commit:
  `9cdf8de75ab1d51fd39e0dba303fd5bb06f553a4`.
- Audit-repair commit:
  `8120cb8907eb539b3d724749eba1cd084b8ddf84`.
- Original implementation audit: `FIX_REQUIRED`.
- `S5-IMPL-AUD-001`: BLOCKER -> CLOSED.
- `S5-IMPL-AUD-002`: MAJOR -> CLOSED.
- Targeted re-audit: PASS with 0 BLOCKER / 0 MAJOR / 0 MINOR / 0 INFO.
- Final test evidence: focused `129 passed`; regression `249 passed, 1
  skipped`; combined `378 passed, 1 skipped`; targeted repair `18 passed`;
  independent pointer probes `13 passed`.
- Slice 5 is CLOSED / REMOTE CLOSED after the implementation acceptance
  documentation commit is pushed.
- No runtime or provider execution is claimed.
- No canonical timing result, failure artifact, or `AlignmentReport` is
  defined by the Slice 5 specification.
- No renderer integration, production readiness, database/cache behavior,
  retry/queue orchestration, or paid-provider invocation is claimed.
- Phase 2 overall closure is not established.
- The total official Phase 2 Slice count is not reconciled.
- No Phase 2 completion percentage is claimed.
- Post-Slice-5 scope reconciliation is complete. Its report is
  `baseline/phase2_post_slice5_scope_report.md`.
- The Slice 1-3 historical focused-test evidence gap is closed by the bounded
  read-only closure reconciliation: Slice 1 `47 passed`, Slice 2 `150 passed`,
  and Slice 3 `84 passed`, for `281 passed` total.
- The focused tests ran with cache provider disabled and repository-external
  task-specific basetemp paths under `C:\tmp`; pre/post Git status parity,
  commit ancestry, and public export verification passed.
- Slice 1, Slice 2, and Slice 3 are CLOSED. Their former unreconciled
  classification and evidence blocker no longer apply.
- The corrected Slice 5 specification itself has zero open audit findings.
- Downstream canonical timing deliverables are not proven complete.
- Slice 5 acceptance proves only its bounded immutable AdapterExecution
  provenance contract. It does not prove provider execution, runtime timing
  correctness, downstream result artifacts, renderer behavior, performance,
  or production readiness.
- The reconciliation decision is
  `MORE_BOUNDED_PHASE2_WORK_REQUIRED`; no Master Phase 2 deliverable is proven
  complete by Slice 1-5 alone.
- The selected bounded candidate is Canonical Successful Alignment
  Word-Timing Result Contract.
- Its specification-path decision is CLOSED and recorded in
  `baseline/phase2_next_bounded_candidate_specification_path_decision_report.md`.
- The exact selected future specification path is
  `docs/specifications/phase2_canonical_successful_alignment_word_timing_result_contract.md`.
- The specification is accepted and its exact four-path bounded
  implementation is authorized by
  `baseline/phase2_canonical_successful_alignment_word_timing_result_contract_acceptance_and_implementation_authorization_report.md`.
- The accepted bounded implementation is remote closed at
  `87eb330922a5a1295de861544b44859ddd001911` and recorded by
  `baseline/phase2_canonical_successful_alignment_word_timing_result_implementation_acceptance_report.md`.
- Independent implementation audit: PASS; P0/P1/P2 findings: `0/0/0`;
  focused deterministic gate: `471 passed`.
- The first test collection attempt lacked the repository `PYTHONPATH`; the
  rerun with an explicit repository-root `PYTHONPATH` passed. This is an
  environment-only note, not a product regression or FastAPI blocker.
- Successful result publication is limited to the exact repository-owned
  allowlisted `REPLAY` timing evidence. `MANUAL_UI`, `FREE_API`, and `PAID_API`
  successful publication require a separately specified trusted runtime
  producer and are deterministically rejected without silent downgrade.
- Remaining Phase 2 gaps include phrase/caption grouping, complete
  confidence/report integration, emphasis mapping, word-to-frame compilation,
  and V5/V6 preview/collision validation. The accepted implementation covers
  only the bounded canonical successful alignment result contract.
- The phrase-grouping scope and specification path are selected in
  `baseline/phase2_canonical_phrase_grouping_caption_groups_specification_path_decision_report.md`,
  and the candidate specification is drafted and remote closed. The initial
  audit returned `FIX_REQUIRED` with one MAJOR error-oracle ambiguity. A bounded
  repair is remote closed, targeted re-audit passed, and the corrected
  specification is accepted. The exact four-path bounded implementation and
  its two-path audit repair are accepted and remote closed at
  `8b77c4d5bbd6f176d11a92f6a491a707e7b47ac6`; no filesystem artifact
  publication is implemented.

```text
PHASE2_SLICE5_CORRECTED_SPECIFICATION_REMOTE_CLOSED=YES
PHASE2_SLICE5_SPECIFICATION_ACCEPTED=YES
SLICE1_3_EVIDENCE_BLOCK=CLEARED
SLICE5_IMPLEMENTATION_AUTHORIZED=YES
SLICE5_IMPLEMENTATION_ALLOWED=YES
IMPLEMENTATION_START_ALLOWED=YES
SLICE5_IMPLEMENTATION_STATUS=CLOSED
SLICE5_IMPLEMENTATION_ACCEPTANCE=ACCEPT
SLICE5_IMPLEMENTATION_ACCEPTED=YES
SLICE5_STATUS=CLOSED
SLICE5_REMOTE_CLOSED=YES
PHASE2_CLOSED=NO
POST_SLICE5_SCOPE_RECONCILIATION_STATUS=CLOSED
NEXT_SLICE_IMPLEMENTATION_ALLOWED=NO
```

```text
PHASE2_SCOPE_DECISION=MORE_BOUNDED_PHASE2_WORK_REQUIRED
COMPLETED_BOUNDED_CANDIDATE_TITLE=Canonical Successful Alignment Word-Timing Result Contract
ALIGNMENT_RESULT_IMPLEMENTATION_ACCEPTED=YES
BOUNDED_CANDIDATE_TITLE=Canonical Phrase Grouping and Caption Groups Contract
SELECTED_SPECIFICATION_PATH=docs/specifications/phase2_canonical_phrase_grouping_caption_groups_contract.md
SPECIFICATION_PATH_DECISION=CLOSED
SPECIFICATION_DRAFTED=YES
ORIGINAL_SPECIFICATION_AUDIT=FIX_REQUIRED
TARGETED_SPECIFICATION_REAUDIT=PASS
CGS_SPEC_AUD_001_STATUS=CLOSED
SPECIFICATION_ACCEPTED=YES
IMPLEMENTATION_AUTHORIZATION_DECISION=AUTHORIZE
IMPLEMENTATION_AUTHORIZED=YES
IMPLEMENTATION_STATUS=CLOSED
IMPLEMENTATION_ACCEPTANCE=ACCEPT
IMPLEMENTATION_ACCEPTED=YES
IMPLEMENTATION_REMOTE_CLOSED=YES
TARGETED_IMPLEMENTATION_REAUDIT=PASS
NEXT_ACTION=POST_CAPTION_GROUPS_SCOPE_RECONCILIATION
NEXT_IMPLEMENTATION_ALLOWED=NO
PHASE2_CLOSED=NO
TOTAL_PHASE2_SLICE_COUNT=UNKNOWN
PHASE2_COMPLETION_PERCENTAGE=NOT_STATED
```

## Environment and test limitations

## Post-caption-groups Phase 2 limitations

- The read-only reconciliation is PASS, but none of the six Master Roadmap
  deliverables is claimed fully complete at its named runtime/publication
  boundary.
- Accepted `AlignmentResult` and `CaptionGroupsArtifact` provide canonical
  semantic bytes and stable identities; `timing/word_timeline.json` and
  `timing/caption_groups.json` filesystem publication/lifecycle are not
  implemented.
- Phase 1 generic `text_emphasis_events` envelopes and empty fixture values do
  not satisfy the canonical Phase 2 `timing/emphasis_events.json` deliverable.
- `WordToFrameCompiler`, `CaptionPreviewRenderer`, V5/V6 collision validation,
  and `AlignmentReport` remain absent as accepted canonical implementations.
- Low-confidence data is representable but not yet explicitly classified and
  emitted through an accepted report boundary.
- The Canonical Emphasis Events candidate is drafted and remote closed, but it
  has not received independent read-only audit or specification acceptance.
  Its Domain Pack policy, intent/range, canonical oracle, mutation/no-leak, and
  implementation-feasibility decisions remain unaccepted until that audit.
- No emphasis implementation or downstream frame/preview/report work is
  authorized.

```text
POST_CAPTION_GROUPS_SCOPE_RECONCILIATION_STATUS=PASS
PHASE2_SCOPE_DECISION=MORE_BOUNDED_PHASE2_WORK_REQUIRED
NEXT_BOUNDED_CANDIDATE_TITLE=Canonical Emphasis Events Contract
SELECTED_SPECIFICATION_PATH=docs/specifications/phase2_canonical_emphasis_events_contract.md
SPECIFICATION_DRAFTED=YES
SPECIFICATION_STATUS=CANDIDATE_REMOTE_CLOSED
SPECIFICATION_ACCEPTED=NO
INDEPENDENT_SPECIFICATION_AUDIT_REQUIRED=YES
IMPLEMENTATION_AUTHORIZED=NO
PHASE2_CLOSED=NO
```

- The caption-groups full repository collection attempt stops in two
  FastAPI-dependent test areas because the active Python environment does not
  contain `fastapi`. The top-level non-FastAPI gate passes with
  `1855 passed, 1 skipped`; no full-suite pass is claimed.
- Legacy full Python collection, committed manifestlerde olmayan `pyloudnorm`
  nedeniyle `v2.audio_engine` import zincirindeki uc collection'da durur.
- Starlette/HTTPX TestClient deprecation warning'i non-blockingdir.
- Windows symlink skip kabul edilmistir; `.pytest_cache` ve
  `shared-schemas/.pytest_cache` permission warning'leri pre-existingdir.
- `v2/audio_engine_debug.py` ve `v2/audio_engine_debug2.py` bilinen
  syntax/indentation debug debt'idir; MoviePy SyntaxWarning'leri applicable
  ortamlarda gorulebilir.

## Operations and repository safety

- Provider credential revoke/rotation NOT CONFIRMED olarak kalir.
- `C:\Users\user\Documents\Kurgu_V3_Clean`,
  `C:\Users\user\Documents\Kurgu_V3_Clean_backup_20260724_163134`,
  `C:\Users\user\Documents\Kurgu_V3_Clean_sanitized_20260724_163134` ve
  onceki verification/sanitized clone'lar unsafe history tasiyabilir; asla
  authoritative development, push, sharing veya public archive icin
  kullanilmaz. Tek authoritative repository bu dokumanda kayitli sanitized
  Freesound repository'dir.
