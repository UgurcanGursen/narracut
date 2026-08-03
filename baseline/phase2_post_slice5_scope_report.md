# Phase 2 Post-Slice-5 Scope Reconciliation Report

Date: 2026-08-03

## Repository identity and method

- Authoritative repository:
  `C:\Users\user\Documents\Kurgu_V3_Clean_sanitized_freesound_20260724_224147304`
- Branch: `main`
- Reconciliation base HEAD, `origin/main`, and live `refs/heads/main`:
  `31e6193f26aa724a5f8f23efc8a6b9d1c90038d8`.
- Tracked worktree and staging area were clean.
- The only untracked status entry was `norm_words_debug.json`; only its Git
  status name was observed.
- Required governance documents were reviewed in the prescribed order.
- Repository-wide discovery covered `engine/`, `tests/`, `shared-schemas/`,
  `v2/`, `templates/`, `studio-api/`, and `studio-ui/`.
- No tests, provider/runtime/API calls, implementation, or specification
  drafting were performed by the reconciliation. Git remote access was used
  only for repository identity and closure verification.

## Authority and Phase 2 objective

`docs/MASTER_ROADMAP.md` defines Phase 2 as the Temporal Annotation and
Word-Level Alignment Contract. Its objective is a reliable word timeline for
motion, kinetic typography, subtitles, and audio events. Its pipeline is:

```text
Narration text
-> TTS
-> audio normalization
-> forced word alignment
-> token-to-original-word mapping
-> phrase grouping
-> emphasis mapping
-> word-to-frame compilation
```

The Master Roadmap deliverables are `timing/word_timeline.json`,
`timing/caption_groups.json`, `timing/emphasis_events.json`,
`WordToFrameCompiler`, `CaptionPreviewRenderer`, and `AlignmentReport`.

## Completed Slice capability matrix

| Work item | Owned contract or artifact | Proven capability | Explicitly not proven | Commit and test evidence | Master contribution |
|---|---|---|---|---|---|
| Slice 1 - Temporal Raw Package | `TRP-RAW-V1` canonical raw package | Exact raw payload bytes/hash and closed issue-code inventory | Alignment result, word timing, report, grouping, or frame compilation | `9247f7feca1ce40030a6ccc68d3e8c2775c969bc`, `e0edbc751a271de561412e53acf84ae870aba97c`; `47 passed` | Prerequisite only |
| Slice 2 - Canonical Narration | Narration revision, canonical words, stable word IDs, `WordRangeReference` | Canonical narration hierarchy, word identity, lineage, and range resolution | Word timing and migration of runtime text cues to canonical ranges | `d00cea0dfbe965c81cdbcb311855184bf6a5cd68`, `dba75ae2bcb81228df59e2d0d5e398fd171b4438`, `fa63e8d4a741ca2c1a91b7dd04fe73e024a14d48`; `150 passed` | Prerequisite; partial cue-binding foundation |
| Slice 3 - Canonical AudioArtifact | Immutable canonical audio artifact | Secure canonical audio identity and decoded metadata | Alignment execution, timing, or report | `1373c4aee0374c19c1bafed122b2c4d12b5a6855`, `8e8cd2670b9d38586fdbcdcd6d63833b082143ee`, `477668b09dc000a16429bd7738bb4c21953f41fb`; `84 passed` | Prerequisite only |
| Slice 4 - Canonical AlignmentRequest | Immutable pre-execution request | Binding of raw package, narration revision, audio artifact, mode, capability, and optional transcript | Adapter execution, alignment result, timing, or report | `2af9778de57f692f698a356f330b3bf3ede11106`, `d32e66585d660bc3e37a1896dbb7df050a8bc849`; CLOSED / REMOTE CLOSED | Prerequisite only |
| Slice 5 - Canonical AdapterExecution Provenance | Immutable terminal execution provenance | Closed mode/status/evidence rules, request binding, canonical identity, and publication safety | Provider execution, canonical result, WordTiming, failure artifact, or AlignmentReport | `9cdf8de75ab1d51fd39e0dba303fd5bb06f553a4`, `8120cb8907eb539b3d724749eba1cd084b8ddf84`; focused `129 passed`, regression `249 passed, 1 skipped`, targeted re-audit PASS | Prerequisite only |

Slice 1-5 are CLOSED. Slice 4 and Slice 5 are REMOTE CLOSED. No concrete
contradictory repository evidence was found.

## Repository artifact classification

- `CANONICAL_PHASE2_IMPLEMENTATION`: the closed Slice 1-5 contracts under
  `engine/contracts/`.
- `SCHEMA_ONLY`: Phase 1 `timing_manifest`, `timing_ref`, and
  `text_emphasis_events` surfaces under `shared-schemas/v3/`; the workspace
  explicitly labels the timing boundary `semantic_references_only`.
- `LEGACY_ONLY`: float-second Whisper word dictionaries and text-cue matching
  in `v2/audio_engine.py`, ad hoc `alignment_report.json` and
  `int(seconds * 30)` conversion in `v2/editorial_engine.py`, and subtitle
  slicing in `v2/video_engine.py`.
- `TEST_ONLY`: legacy alignment helpers and fixtures do not establish a
  canonical Phase 2 result contract.
- `DOCUMENTATION_ONLY`: roadmap declarations and Slice 5 non-claims.
- `MISSING`: canonical successful alignment result, WordTiming timeline,
  canonical AlignmentReport, phrase/caption grouping, emphasis mapping,
  word-to-frame compiler, and caption preview/collision validation.

Legacy behavior, schema placeholders, fixtures, and documentation text are
not canonical Phase 2 completion evidence.

## Master deliverable matrix

| Deliverable | Repository classification | Exact evidence | Canonical implementation | Tested | Acceptance proven | Blocking dependency |
|---|---|---|---|---|---|---|
| `timing/word_timeline.json` | MISSING | Roadmap declaration; only legacy float dictionaries in `v2/audio_engine.py` | NO | NO | NO | Canonical successful alignment and narration-word timing result |
| `timing/caption_groups.json` | MISSING | No canonical implementation found | NO | NO | NO | Canonical word timeline and phrase grouping |
| `timing/emphasis_events.json` | SCHEMA_ONLY / PARTIAL | `shared-schemas/v3/sequence.schema.json`, `engine/contracts/models.py` | NO | PARTIAL schema coverage only | NO | Canonical word timeline, word ranges, and emphasis mapping |
| `WordToFrameCompiler` | MISSING | Legacy conversion only in `v2/editorial_engine.py` | NO | NO | NO | Canonical word timeline and normative frame policy |
| `CaptionPreviewRenderer` | MISSING | No canonical implementation found | NO | NO | NO | Caption groups, emphasis timing, and frame compilation |
| `AlignmentReport` | LEGACY_ONLY | Ad hoc report in `v2/editorial_engine.py` | NO | PARTIAL legacy coverage only | NO | Canonical result, failure, and confidence boundaries |

## Master acceptance matrix

| Master criterion | Status | Repository evidence |
|---|---|---|
| Every narration word has start/end timing | NOT_SATISFIED | `CanonicalWord` has no timing and no canonical result/timeline exists |
| Cues bind to word-ID ranges instead of string search | PARTIALLY_SATISFIED | `WordRangeReference` exists, but shared semantic cues and legacy runtime still use semantic/text references |
| Kinetic text differs from narration by at most one frame | NOT_SATISFIED | No canonical frame compiler, rounding policy, or tolerance test |
| V5 kinetic emphasis and V6 readable subtitles do not occlude | NOT_SATISFIED | No canonical preview or collision validator |
| Low confidence is explicitly reported | PARTIALLY_SATISFIED | Stable issue codes and Slice 5 confidence-availability evidence exist, but no canonical timing/report representation exists |
| LLM does not generate manual seconds | PARTIALLY_SATISFIED | Closed request/provenance contracts do not publish timing, but no canonical result source-enforcement boundary exists |

## Current gaps

| Capability | Status |
|---|---|
| Canonical successful alignment/timing result | MISSING |
| Canonical WordTiming model | MISSING |
| Deterministic alignment-token to narration-word-ID mapping | LEGACY_ONLY / CANONICAL_MISSING |
| Timing coverage, ordering, bounds, and non-overlap invariants | ISSUE_INVENTORY_ONLY / IMPLEMENTATION_MISSING |
| Low-confidence result and report representation | PARTIAL |
| Failure artifact and report boundary | MISSING |
| Phrase/caption grouping | MISSING |
| Emphasis mapping | SCHEMA_ONLY / IMPLEMENTATION_MISSING |
| Millisecond-to-frame compilation | LEGACY_ONLY / CANONICAL_MISSING |
| Runtime cue-to-word-range binding | PARTIAL |
| V5/V6 preview and collision validation | MISSING |

These gaps are not one implementation item. They remain ordered by the Master
Roadmap pipeline and require separate bounded decisions.

## Candidate comparison

| Candidate | Dependency order | Readiness and boundedness | Roadmap contribution | Coupling risk | Decision |
|---|---|---|---|---|---|
| Canonical successful alignment/timing result boundary | Earliest publishable boundary after closed Slice 1-5 | Dependencies ready; one immutable success artifact | Establishes trusted input for `word_timeline.json` and every-word timing | Moderate and cohesive when timing entries and mapping are owned together | SELECTED |
| Standalone WordTiming/timeline boundary | Requires successful execution/result provenance | Data model is bounded but unattached timings would be unsafe | Direct deliverable contribution | High risk of duplicating result identity and provenance | Fold only the necessary timing projection into the selected result contract |
| Alignment failure/report boundary | Can follow execution provenance but does not publish successful timing | Independently specifiable | Advances diagnostics and report deliverable | Coupling success and failure/report would broaden the next task | DEFERRED |
| Standalone token-to-original-word mapping boundary | Consumes raw tokens and canonical words but still needs a publication artifact | Algorithmically bounded | Advances the next pipeline step | A separate public artifact would add identity and lifecycle boundaries without completing a deliverable | Keep as deterministic behavior inside the selected success result contract |

## Selected next bounded candidate

Title: **Canonical Successful Alignment Word-Timing Result Contract**

The candidate is the earliest missing canonical boundary between forced
alignment execution evidence and token-to-original-word timing projection. It
depends directly on the closed Slice 1-5 contracts and materially advances the
canonical `timing/word_timeline.json` deliverable and the every-word timing,
low-confidence reporting, and no-manual-seconds criteria.

Proposed ownership:

- Domain-agnostic immutable successful alignment result.
- Canonical narration-word timing projection.
- Proposed new production module: `engine/contracts/alignment_result.py`.
- Existing public export boundary: `engine/contracts/__init__.py`.
- Proposed focused test module: `tests/test_alignment_result.py`.

Proposed in-scope behavior:

- Bind successful-result provenance to genuine Slice 1-5 dependencies.
- Deterministically map alignment tokens to canonical narration `word_id`
  values.
- Represent canonical millisecond word timings and confidence.
- Enforce specification-defined coverage, ordering, bounds, and non-overlap.
- Provide immutable canonical serialization, versioned hash scope, derived
  identity, and atomic publication/non-publication.
- Reject manual or LLM-authored timing sources at the canonical boundary.

Proposed out-of-scope behavior:

- Provider, network, API, paid-provider, or alignment runtime execution.
- Failure artifact and `AlignmentReport`.
- Phrase/caption grouping and emphasis mapping.
- Frame compilation, caption preview, and V5/V6 collision validation.
- Phase 3 EDL, renderer integration, Studio API, and UI.

Required future specification decisions include exact models, fields, enums,
presence/nullability, timing source rules, validation and error precedence,
canonical bytes, identity/hash scopes, provenance bindings, issue-code usage,
failure/non-publication rules, security/no-leak behavior, golden fixtures, and
mutation-resistance tests. No such decisions are invented by this report.

Expected bounded failure model:

- `FAILED` or `BLOCKED` execution cannot publish a success result.
- Validation, dependency, mapping, timing, identity, or publication failure is
  fail-closed and publishes no result identity, hash, bytes, or artifact.
- No silent fallback or default timing is permitted.
- Canonical operational failure artifacts and `AlignmentReport` remain later
  bounded work.

Security/no-leak boundary:

- No provider payload, credential, authorization secret, filesystem path,
  URI, raw exception value, or manual/LLM timestamp may leak through the
  artifact or error surface.
- Genuine exact dependencies and immutable publication must prevent forged,
  copied, subclassed, stale, or replacement provenance.

Required future acceptance evidence:

- Accepted normative specification and independent read-only audit.
- Exact golden projection/envelope bytes, hashes, and derived identity.
- Complete deterministic token-to-word mapping and every-word accounting.
- Timing bounds, monotonicity, overlap, zero-duration, coverage, confidence,
  and timing-source rejection fixtures.
- Forgery, mutation, registry cleanup, rollback, no-leak, and duplicate/unknown
  issue-code tests.
- Focused tests and Slice 1-5 regression evidence.

## Explicit non-claims

- No new Slice number is assigned.
- The total official Phase 2 Slice count remains unknown.
- No Phase 2 completion percentage is stated.
- The selected candidate specification is not drafted or accepted.
- The selected candidate implementation is not authorized or started.
- No Master Phase 2 deliverable is declared complete by this report.
- Phase 2 acceptance evaluation is not yet allowed.
- Phase 2 is not closed.

## Documentation impact matrix

| Path or area | Decision |
|---|---|
| `baseline/phase2_post_slice5_scope_report.md` | CREATED |
| `baseline/phase2_next_bounded_candidate_specification_path_decision_report.md` | CREATED |
| `docs/CURRENT_STATE.md` | UPDATED |
| `docs/NEXT_ACTIONS.md` | UPDATED |
| `docs/KNOWN_LIMITATIONS.md` | UPDATED |
| `docs/PHASE_ACCEPTANCE.md` | UPDATED |
| `docs/CHANGELOG.md` | UPDATED |
| `docs/MASTER_ROADMAP.md` | REVIEWED_NO_CHANGE |
| `docs/ARCHITECTURE_DECISIONS.md` | REVIEWED_NO_CHANGE |
| `docs/QUALITY_BENCHMARKS.md` | REVIEWED_NO_CHANGE |
| `docs/DOMAIN_PACKS.md` | REVIEWED_NO_CHANGE |
| `docs/specifications/` | REVIEWED_NO_CHANGE; selected future file absent |
| Production and tests | REVIEWED_NO_CHANGE |

## Reconciliation decision

```text
PHASE2_POST_SLICE5_SCOPE_RECONCILIATION_STATUS=PASS
SLICE1_STATUS=CLOSED
SLICE2_STATUS=CLOSED
SLICE3_STATUS=CLOSED
SLICE4_STATUS=CLOSED_REMOTE_CLOSED
SLICE5_STATUS=CLOSED_REMOTE_CLOSED
SLICE1_5_EVIDENCE_CHAIN=PASS
MASTER_PHASE2_DELIVERABLES_COMPLETE=NO
MASTER_PHASE2_ACCEPTANCE_CRITERIA_COMPLETE=NO
PHASE2_SCOPE_DECISION=MORE_BOUNDED_PHASE2_WORK_REQUIRED
NEXT_BOUNDED_CANDIDATE_TITLE=Canonical Successful Alignment Word-Timing Result Contract
SPECIFICATION_REQUIRED=YES
SPECIFICATION_PATH_DECISION_REQUIRED_AT_RECONCILIATION=YES
SELECTED_SPECIFICATION_PATH=docs/specifications/phase2_canonical_successful_alignment_word_timing_result_contract.md
SPECIFICATION_PATH_DECISION=CLOSED
SPECIFICATION_DRAFTED=NO
SPECIFICATION_ACCEPTED=NO
SELECTED_CANDIDATE_IMPLEMENTATION_AUTHORIZED=NO
NEXT_IMPLEMENTATION_ALLOWED=NO
PHASE2_ACCEPTANCE_DECISION_ALLOWED=NO
PHASE2_CLOSED=NO
TOTAL_PHASE2_SLICE_COUNT=UNKNOWN
PHASE2_COMPLETION_PERCENTAGE=NOT_STATED
```
