# Phase 2 Canonical Emphasis Events Implementation Authorization Decision

Date: 2026-08-04

## Decision

```text
IMPLEMENTATION_AUTHORIZATION_DECISION=AUTHORIZE
IMPLEMENTATION_AUTHORIZED=YES
IMPLEMENTATION_STATUS=NOT_STARTED
IMPLEMENTATION_ACCEPTANCE=OPEN
NEXT_ACTION=BOUNDED_IMPLEMENTATION
NEXT_IMPLEMENTATION_ALLOWED=YES
PHASE2_CLOSED=NO
TOTAL_PHASE2_SLICE_COUNT=UNKNOWN
PHASE2_COMPLETION_PERCENTAGE=NOT_STATED
```

This decision authorizes one minimal, reversible implementation of the
accepted Canonical Emphasis Events Contract. It does not accept an
implementation, assign a Slice number, publish an artifact file, authorize
downstream frame/preview/report work, or close Phase 2.

## Authoritative accepted input

```text
SPECIFICATION=docs/specifications/phase2_canonical_emphasis_events_contract.md
SPECIFICATION_COMMIT=d4c978eb0df8d11ab033edbd50dc2eca17eab74a
SPECIFICATION_SHA256=5806aa26f798489e475d03b68e451cdbf2c2efd39f450ea7335cb96fc442f3b7
SPECIFICATION_UTF8_BYTES=45380
SPECIFICATION_ACCEPTANCE_COMMIT=a2b273efdaa7a48b5afb85ebe27af7873eb20b92
SPECIFICATION_ACCEPTANCE_DECISION=ACCEPT
INDEPENDENT_SPECIFICATION_AUDIT=PASS
FINAL_BLOCKER_MAJOR_MINOR_INFO=0/0/0/0
```

The accepted bytes, exact public surface, closed rejection oracle, four golden
JSON blocks, Domain Pack boundary, and mandatory test matrix are immutable
inputs to implementation.

## Authorized implementation boundary

Exactly these four paths may change in the implementation commit:

```text
engine/contracts/emphasis_events.py
engine/contracts/__init__.py
tests/test_emphasis_events.py
tests/test_alignment_request.py
```

The first and third paths are new. `engine/contracts/__init__.py` may receive
only additive imports and the exact public export delta below.
`tests/test_alignment_request.py` may receive only a named mechanical export
set and its inclusion in the existing exact-export oracle. Existing request,
execution, result, and caption assertions must not otherwise change.

No specification, documentation, schema, fixture, Domain Pack, runtime, UI,
provider, renderer, workspace, or artifact file is part of the implementation
commit. The existing committed `business-tech` manifest and policy snapshot
are read-only test dependencies; no new visual grammar value is authorized.

## Exact additive public surface

The implementation must add exactly these 15 symbols and no others:

```text
EMPHASIS_EVENT_V1
EMPHASIS_EVENT_HASH_V1
EMPHASIS_EVENTS_V1
EMPHASIS_EVENTS_HASH_V1
EMPHASIS_MAPPING_POLICY_V1
EmphasisIntensity
EmphasisEventsRejectionReason
EmphasisTypeRef
EmphasisIntent
EmphasisEvent
EmphasisEventsArtifact
EmphasisEventsContractError
compile_emphasis_events
load_emphasis_events
serialize_emphasis_events
```

No private registry, policy resolver, projection/hash helper, range helper,
text resolver, mutable builder, or Domain Pack internal may leak through
`engine.contracts`.

## Import and dependency boundary

Only standard library and these accepted repository contract layers may be
imported:

```text
engine.contracts._canonical_json
engine.contracts.narration
engine.contracts.alignment_result
engine.contracts.caption_groups
engine.contracts.alignment_execution
engine.contracts.domain
engine.contracts.models
engine.contracts.temporal
```

The module must remain domain-neutral. A private immutable typed resolved
emphasis policy is required; raw policy mapping traversal may not be scattered
through validation. `DomainPackRegistry.get` may be used only against an
already discovered in-memory registry. The module must never call `discover`,
read policy files, retain registry/snapshot/dependency objects, or branch on a
domain ID.

Provider/runtime orchestration, filesystem, network, database/cache, FastAPI,
UI, renderer, EDL, FFmpeg, Remotion, frame compiler, preview/report, V2,
thread, subprocess, clock, and random imports are forbidden.

## Required behavior

Implementation must exactly realize the accepted contract, including:

- exact constants, enum order/values, frozen dataclass field order/types, and
  keyword-only signatures;
- genuine/current narration, alignment, and caption dependency validation;
- full DomainPolicySnapshot reconstruction/hash/ID/immutable checks and exact
  registry manifest/visual-grammar parity;
- exact tuple-only intents, word-range revision/bounds/sentence checks,
  canonical ordering, duplicate/overlap rejection, and at most 10,000 events;
- exact one-caption-group containment with no string/text-span search;
- word IDs, time, and confidence derived only from accepted word timings;
- all section 18/18.1 precedence, pointer, reason, and issue-code outcomes;
- exact FX-EME-01 event/root projection and envelope bytes, hashes, and IDs;
- canonical non-object root classification, strict loader recompilation, and
  canonical byte equality;
- transactional weak-registry publication, mutation/copy/proxy/subclass/
  reconstruction rejection, stale-callback safety, and no mutable retention;
- sanitized no-leak errors and no partial output on any failure; and
- `O(W + G + P + I + output_bytes)` time/memory without hidden rescans or I/O.

Serialization returns bytes only. It must not create
`timing/emphasis_events.json`.

## Mandatory verification gates

`tests/test_emphasis_events.py` must cover every category in specification
section 20, not only golden happy paths. At minimum it must prove:

- exact API/export shape and forbidden exports;
- genuine dependency/current-content/binding order and every mutation/forgery
  path;
- snapshot/registry/manifest/visual-grammar parity, duplicate and unknown
  types, event-types non-fallback, and no domain conditional;
- empty, adjacent, duplicate, overlapping, cross-sentence and cross-caption
  intents, repeated narration words, and absence of string search;
- AVAILABLE/UNAVAILABLE/NOT_APPLICABLE confidence and subset-minimum behavior;
- every closed loader/oracle row and multi-fault precedence;
- four literal FX-EME-01 golden blocks plus an empty-artifact golden;
- registry rollback/collision/cleanup/non-retention and no-leak behavior; and
- static no-I/O/provider/frame/layout/preview/report import boundaries and
  linear-resource behavior.

Required gates after implementation:

1. focused: `tests/test_emphasis_events.py` plus mechanically affected
   `tests/test_alignment_request.py`;
2. upstream: temporal raw, canonical narration, audio artifact, alignment
   request, adapter execution, alignment result, caption groups, and emphasis
   events suites together;
3. broad: the same top-level non-FastAPI repository gate used by accepted
   caption-groups work;
4. full collection attempt when environment permits, with missing FastAPI or
   other environment-only stops reported honestly rather than hidden.

Tests use REPLAY fixtures and the existing committed business-tech skeleton.
No commercial API, provider, network, browser, credential, or media operation
is permitted.

## Rollback and acceptance boundary

Rollback scope is exactly the four authorized paths: remove the new module and
focused tests, remove only the 15 additive imports/exports, and remove only the
mechanical export-oracle set. No upstream or Domain Pack rollback is required.

Implementation completion is not acceptance. The exact tested candidate must
be normally committed/pushed, then independently audited read-only against the
accepted specification. Blocking findings require bounded repair and targeted
re-audit before a separate implementation acceptance decision.

Phase 2 remains open after this bounded authorization and after any later
Emphasis Events acceptance. Word-to-frame compilation, AlignmentReport,
artifact publication, CaptionPreviewRenderer, and V5/V6 collision evidence
remain separate roadmap work.

## Documentation impact matrix

| Path | Impact |
|---|---|
| `baseline/phase2_canonical_emphasis_events_implementation_authorization_decision_report.md` | CREATED. |
| `docs/CURRENT_STATE.md` | UPDATED. |
| `docs/NEXT_ACTIONS.md` | UPDATED. |
| `docs/KNOWN_LIMITATIONS.md` | UPDATED. |
| `docs/PHASE_ACCEPTANCE.md` | UPDATED. |
| `docs/CHANGELOG.md` | UPDATED. |
| Accepted specification and Master Roadmap | UNCHANGED. |
| Production/tests/Domain Packs | REVIEWED; UNCHANGED by this decision. |
| `norm_words_debug.json` | UNTOUCHED. |

## Repository safety

`norm_words_debug.json` was excluded from every repository status/diff check
and was not read, statted, hashed, diffed, modified, deleted, or staged.
