# Known Limitations

Son guncelleme: 6 Agustos 2026

## Roadmap reconciliation status note

- Phase 0-10 closures are accepted foundation evidence, not an assertion that
  the end-to-end product gate has passed. The authoritative owner, acceptance
  evidence and remaining status of every deferred product obligation are in
  `docs/ROADMAP_SCOPE_RECONCILIATION.md`.
- No later phase may declare `MASTER_PHASE_CLOSED` while one of its Deferred
  Delivery Ledger rows is open. `PRODUCT_GATE_CLOSED` remains a Phase 17-only
  decision.

## Faz 15 status note

- Faz 15 baslatildi; ilk paket yalniz canonical run evidence ve fail-closed
  quality-gate siniridir. Canli source/asset/timing transport Faz 17 sahipligi
  altinda kalir; Faz 15 bunu ancak etkinlestirildiginde dogrular.
- Pixel, semantic, claim/source ve transport validatorleri bu ilk pakette
  uygulanmis sayilmaz. Source-audio icin yalniz Phase 8/11 policy-direction
  attachment vardir; PCM mix, media classification, boundary-discontinuity ve
  micro-pop kaniti yoksa yeni gate bunlari PASS olarak raporlayamaz.
- Artifact-integrity gate'i canonical Phase 14 registry/output/deletion-plan
  tutarliligini fail-closed dogrular; host dosya sistemi taramasi veya fiziksel
  silme/trash isleminin basarili olduguna dair yeni bir iddia uretmez.
- Final-narration gate'i domain policy, claim provenance ve acik lexical
  blok-listesi icin fail-closed admission saglar; hukuki/faktuel semantic
  adjudication veya claim-source truth validation iddia etmez.

## Faz 13 status note

- Phase 13 is FOUNDATION_ACCEPTED as a local SQLite/OpenAPI Studio control
  plane. It proves project reopen, MANUAL_UI task handoff/import/repair/
  approval and immutable Phase 12/Phase 3 review decisions; it does not make
  a provider call or automate a web AI interface.
- `MASTER_PHASE_CLOSED` is intentionally open. The local implementation has a
  verified two-sequence Phase 12/3-to-Phase-4 REPLAY preview handoff, but Phase
  14 has not supplied durable storage or GC read models; the UI must report
  unavailable rather than invent those values.
- Preview delivery is intentionally attempt-local memory. It is unavailable
  after application restart and is not an artifact store, cache, retention
  mechanism, quota calculation or restoration claim.
- The Studio endpoint accepts no path, source URL, props, EDL bytes or render
  mode. Only a trusted resolver can supply a persisted snapshot; normal
  runtime projects without one fail closed as `RENDER_INPUT_UNAVAILABLE`.
- Canonical snapshot identity/EDL/RenderProps validation is performed before
  SQLite write, and actual two-sequence Phase 4 Studio execution has bounded
  acceptance evidence. Delivery rejects undeclared frames and the UI consumes
  declared evidence through generated HTTP calls; durable ownership remains
  Phase 14. Do not present the local preview seam as durable lifecycle work.
- The preview endpoint executes the bounded REPLAY runner synchronously. Its
  persisted event history is safe to replay after completion, but it is not a
  restart-safe worker or an in-render live-progress system. A fake percentage,
  background thread or queue without artifact/recovery ownership is forbidden;
  Phase 14 owns the required lifecycle handoff and preview performance/SLO
  measurement.

## Faz 14 status note

- Faz 14, local deterministic lifecycle sınırı için `MASTER_PHASE_CLOSED`tır:
  durable registry/reopen, immutable deletion planı, plan-scoped trash/restore,
  content-addressable cache, protected/reference-aware quota planı,
  hard/min-free admission, dedup muhasebesi ve hash-korumalı A/V REPLAY kanıtı
  vardır. Ayrıntılı kabul kanıtı `baseline/phase14_master_acceptance.md`dir.
- Bu bir networked operasyon servisi değildir. Permanent deletion, otomatik
  worker/scheduler, provider/source transport, generic queue/retry, Studio
  FULL-render route ve restart-safe dağıtık operasyonlar sonraki kapsamların
  sahibidir; bunlar mevcut Faz 14 kapanışından çıkarılamaz.
- Soft-quota sınırında sistem görünür immutable cleanup planı üretir ve plan
  çözülmeden render runner’ını çağırmaz. Gizli/aralıklarla çalışan cleanup
  worker’ı yoktur; receipt-backed execution açıkça çağrılan sınırdır.

## Faz 12 status note

- Phase 12 is CLOSED only as a local executable-editorial-plan and Phase 3
  handoff boundary. It does not make a final production render, create missing
  PCM/timing inputs, run a Studio UI, persist multi-user review state, open
  media or operate provider transports.
- Phase 11 audio direction remains an explicit policy mapping, not an audio
  event schedule. A complete audio EDL still requires explicit Phase 3 PCM and
  timing inputs; Phase 12 does not invent them.
- The unrelated historical `tests/test_edl.py` compact golden hash currently
  differs from its committed expectation despite no Phase 12 change to the
  Phase 3 module. The Phase 12 explicit-handoff test passes; investigate that
  legacy Phase 3 golden separately rather than silently changing it here.

## Faz 11 status note

- Phase 11 is CLOSED only as a local, policy-bound audio-direction planning
  boundary. It does not open or classify media, perform vocal/music
  separation, mix/normalize PCM, invoke FFmpeg, create an EDL, select an
  asset, or call a provider.
- Phase 3 remains the owner of sample-accurate 48 kHz compilation; Phase 12
  must bind approved visual decisions and Phase 11 direction into an
  executable editorial plan before the final EDL can exist. Live transport,
  queues/retries and Studio review remain later-phase work.

## Faz 10 status note

- Phase 10 is CLOSED as a local REPLAY/MANUAL_UI-first planning boundary. It
  emits immutable planner artifacts and a deterministic assembly request; it
  does not produce an EDL, renderer input, concrete asset selection, frame
  assignment or final Workspace.
- Provider API execution, browser automation, paid LLM calls, durable queues,
  retries, multi-user planner persistence and Studio UI remain explicitly out
  of scope. A V3/EDL translation requires a separately audited compatibility
  contract.

## Faz 9 status note

- Phase 9 is CLOSED as a local REPLAY/MANUAL_UI research boundary. It does not
  call commercial LLM APIs, automate a web UI, crawl live URLs, or provide the
  Studio UI; `LOCAL_MODEL` and `API` remain typed unavailable interfaces.
- SQLite/JSONL proves immutable local research lineage, not a multi-user
  PostgreSQL service, distributed queue/retry system, or production network
  transport. Those remain later operational work.

## Faz 7 status note

- Phase 7 is CLOSED. It proves exact, evidence-bound declarative visualization
  REPLAY rendering and an isolated Remotion selected-frame receipt; it does not
  introduce live data ingest, financial conversions, geocoding, asset catalog,
  UI review, job queues or automatic injection into Phase 4 preview.
- The active environment lacks optional `fastapi`; all-Python collection cannot
  collect its API suites. The Phase 7 focused/V3 and Node renderer gates pass.

## Faz 6 status note

- Phase 6 is CLOSED. Its `REPLAY` acquisition adapters and evidence treatment
  prove deterministic, content-addressed capture handling; they do not open
  live URLs or establish a production web transport.
- Production network safety (SSRF/private-address and redirect controls, MIME
  and byte limits, timeouts, TLS), provider rate limits, persistent jobs and
  retry/queue behavior remain explicitly out of scope for a later operational
  phase.
- Manual capture is a content-addressed local package, not a browser extension
  or Review UI implementation. Phase 6 does not create a semantic asset
  catalog, data visualization, or final video renderer integration.

## Faz 5 status note

- Phase 5 is CLOSED. Its template library proves local REPLAY rendering and
  reusable visual capabilities, not source acquisition, provider media
  retries/rate limits, semantic asset selection, chart-data animation or
  long-form template-distribution optimization.
- The pinned Noto Sans font is an intentionally bounded renderer asset. It
  prevents host-font drift but does not establish a general typography or
  localization system.

## Faz 4 status note

- Phase 4 is CLOSED. Its REPLAY-only full-render proof does not establish
  provider media ingestion, distributed queue/retry, cache/GC or production
  multi-user operation; those remain later-phase work.

- Phase 3 is closed at video `fbee3b7ae1f1d6b607fa913f4cb4ff8ba3bbfc9f` and
  audio `3ae26f8a3f958a9e470a02b7a6afa0c05efe82a9`. Its proof is deterministic
  REPLAY compilation; it does not establish arbitrary provider media's
  perceptual join quality.
- Phase 4A preview evidence remains at `d3f99d0c766924cc6ee7d07e80a6ea53a27e806f`.
  Phase 4B FULL render, terminal receipt, cleanup and overwrite evidence is
  accepted at `8bac18b386b38c03f5dc0f3f84dd10a5732ce891`; neither creates the
  Studio control-plane handoff or Phase 14 cache/GC capability.
- Queue/retry, rate-limit handling, provider/source acquisition, Studio job
  progress, production asset catalog and Phase 11 audio-direction policy remain
  outside the accepted Phase 4 renderer boundary.

The historical Phase 3A limitation section below is superseded and retained as
the pre-audio acceptance record.

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

- Faz 2 is CLOSED. The accepted timing publisher provides bounded no-replace
  three-file publication, not Faz 14 crash-durable artifact lifecycle.
- Faz 3 EDL, scheduler and audio sample-grid work; Faz 4 renderer work; and
  provider/UI/queue/retry production capabilities remain outside this closure.

## Faz 3A status note

- Video-frame-grid EDL and timeline-debug contracts are accepted at
  `fbee3b7ae1f1d6b607fa913f4cb4ff8ba3bbfc9f`; this is not a Phase 3 closure.
- A1–A5 remain intentionally empty in the accepted Video EDL. There is no
  accepted 48 kHz AudioSampleGrid, PCM normalization, encoder delay/padding
  compensation, zero-crossing/fade/crossfade planning, boundary collision
  resolution, planned-silence protection, or click/pop proof yet.
- Phase 3A does not render assets or media. Remotion, FFmpeg final mux,
  artifact registration, terminal-job temp cleanup and overwrite protection
  remain explicitly Phase 4 work.

- Caption Preview + V5/V6 Collision Validation is accepted and remote closed
  at `218c4bd277867b29d6812715311993a500e19d33`; it is a sparse canonical
  preview/collision contract, not a production caption renderer.
- Canonical named timing-file publication, its atomic artifact lifecycle, and
  final Phase 2 end-to-end reconciliation remain open. The preview contract
  deliberately defers its high-cardinality authoritative fixture to that
  closure macro.
- No Remotion/EDL render, provider execution, queue/retry service, UI, or
  production media output is established by this acceptance.

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
- The Canonical Emphasis Events candidate is drafted, independently audited
  with `PASS` and zero findings, and externally accepted. The accepted
  specification remains unimplemented.
- The exact four-path Emphasis Events implementation is authorized but not yet
  implemented, tested, independently audited, or accepted. Downstream frame,
  preview, report, publication, and Domain Pack edits are not authorized.

```text
POST_CAPTION_GROUPS_SCOPE_RECONCILIATION_STATUS=PASS
PHASE2_SCOPE_DECISION=MORE_BOUNDED_PHASE2_WORK_REQUIRED
NEXT_BOUNDED_CANDIDATE_TITLE=Canonical Emphasis Events Contract
SELECTED_SPECIFICATION_PATH=docs/specifications/phase2_canonical_emphasis_events_contract.md
SPECIFICATION_DRAFTED=YES
SPECIFICATION_STATUS=CANDIDATE_REMOTE_CLOSED
SPECIFICATION_ACCEPTANCE_DECISION=ACCEPT
SPECIFICATION_ACCEPTED=YES
INDEPENDENT_SPECIFICATION_AUDIT=PASS
IMPLEMENTATION_AUTHORIZATION_DECISION=AUTHORIZE
IMPLEMENTATION_AUTHORIZED=YES
IMPLEMENTATION_STATUS=NOT_STARTED
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

## Phase 8 limitations (accepted boundary)

- Phase 8 accepts only pinned local REPLAY evidence; it does not acquire from
  providers, open URLs, decode arbitrary production media, or automate a
  browser.
- Asset catalog replay is intentionally fail-closed: unknown media bytes or
  evidence not present in the checked-in manifest are rejected.
- Asset reuse analysis validates supplied context only; it does not select an
  EDL asset or create a replacement. Provider queues, retries, UI, durable
  persistence, and production operations are later-phase work.

## Operations and repository safety

- Provider credential revoke/rotation NOT CONFIRMED olarak kalir.
- `C:\Users\user\Documents\Kurgu_V3_Clean`,
  `C:\Users\user\Documents\Kurgu_V3_Clean_backup_20260724_163134`,
  `C:\Users\user\Documents\Kurgu_V3_Clean_sanitized_20260724_163134` ve
  onceki verification/sanitized clone'lar unsafe history tasiyabilir; asla
  authoritative development, push, sharing veya public archive icin
  kullanilmaz. Tek authoritative repository bu dokumanda kayitli sanitized
  Freesound repository'dir.

## Post-Emphasis Events Phase 2 limitations — 2026-08-04

- Canonical Emphasis Events implementation is accepted and remote closed at
  `9bfdceed69b3fd769d02b6a9130f62235fbd630e`; earlier statements that it is
  unimplemented or unaudited are superseded by this section.
- Canonical semantic serializers exist for word timing, caption groups, and
  emphasis events, but atomic workspace publication/lifecycle for
  `timing/word_timeline.json`, `timing/caption_groups.json`, and
  `timing/emphasis_events.json` remains absent.
- `WordToFrameCompiler` remains absent; the at-most-one-frame drift criterion
  is not yet accepted.
- `AlignmentReport` remains absent; low-confidence data exists but is not yet
  emitted through an accepted canonical report boundary.
- `CaptionPreviewRenderer` and deterministic V5/V6 collision validation remain
  absent.
- The optional FastAPI dependency is not installed in the active environment;
  the definitive non-FastAPI gate is `1951 passed, 1 skipped`, not a claimed
  full collection pass.
- Phase 2 remains open. No Slice total or completion percentage is asserted.

```text
EMPHASIS_EVENTS_IMPLEMENTATION_ACCEPTED=YES
EMPHASIS_EVENTS_IMPLEMENTATION_REMOTE_CLOSED=YES
NEXT_MACRO_PACKAGE=Temporal Compilation + Alignment Report
PHASE2_CLOSED=NO
```

## Post-Temporal Compilation + Alignment Report limitations — 2026-08-04

- The accepted implementation at
  `8eafe6e012d71bbca67f9902d8fe55fcad252973` supersedes earlier statements
  that `WordToFrameCompiler` and `AlignmentReport` are absent.
- Exact rational word/caption/emphasis frame compilation and explicit
  confidence-report states are accepted canonical contracts.
- Atomic workspace publication/lifecycle for `timing/word_timeline.json`,
  `timing/caption_groups.json`, and `timing/emphasis_events.json` remains
  absent.
- `CaptionPreviewRenderer` and deterministic V5/V6 collision validation remain
  absent; therefore the preview/collision acceptance criteria are not closed.
- Optional `fastapi` is absent in the active environment. The definitive broad
  gate is `2204 passed, 1 skipped` with only
  `tests/test_control_plane_openapi_foundation.py` excluded; a full FastAPI
  collection is not claimed.
- Provider execution, queue/retry orchestration, renderer/EDL publication,
  durable persistence, UI, and production readiness are not established by
  this bounded acceptance.
- Phase 2 remains open. No Slice total or completion percentage is asserted.

```text
TEMPORAL_COMPILATION_ALIGNMENT_REPORT_IMPLEMENTATION_ACCEPTED=YES
NEXT_MACRO_PACKAGE=Caption Preview + V5/V6 Collision Validation
PHASE2_CLOSED=NO
```
