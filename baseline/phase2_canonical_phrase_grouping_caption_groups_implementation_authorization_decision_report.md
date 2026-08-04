# Phase 2 Canonical Phrase Grouping and Caption Groups Implementation Authorization Decision

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
accepted Canonical Phrase Grouping and Caption Groups Contract. It does not
accept an implementation, assign a Slice number, close Phase 2, or authorize
any downstream presentation, renderer, provider, API, queue, or publication
work.

## Authoritative accepted input

```text
SPECIFICATION=docs/specifications/phase2_canonical_phrase_grouping_caption_groups_contract.md
SPECIFICATION_COMMIT=5bd2401544693a9a0bfe9e3e9d398f96b786cb27
SPECIFICATION_SHA256=c0e8925e598bac0414c1c7b96adf256ed0f4072d2196efedf3b90b0961859baf
SPECIFICATION_UTF8_BYTES=43985
SPECIFICATION_ACCEPTANCE_COMMIT=176c950856af77f2bcdc7440fcf59ed7440334cd
SPECIFICATION_ACCEPTANCE_DECISION=ACCEPT
TARGETED_INDEPENDENT_REAUDIT=PASS
CGS_SPEC_AUD_001_STATUS=CLOSED
FINAL_BLOCKER_MAJOR_MINOR_INFO=0/0/0/0
```

The accepted blob, its deterministic error oracle, exact golden bytes, and
public surface are immutable inputs to the implementation task.

## Authorized implementation boundary

Exactly these four paths may change in the implementation commit:

```text
engine/contracts/caption_groups.py
engine/contracts/__init__.py
tests/test_caption_groups.py
tests/test_alignment_request.py
```

The first and third paths are new. `engine/contracts/__init__.py` may receive
only additive imports and the exact public export delta below.
`tests/test_alignment_request.py` may receive only the mechanical update
needed by `test_alignment_request_public_exports_are_exact`; its existing
alignment-request behavior and assertions must not otherwise change.

No documentation, schema, fixture, runtime, UI, provider, renderer, cache,
workspace, or artifact file is part of the implementation commit.

## Exact additive public surface

The implementation must add exactly these 13 public symbols and no others:

```text
CAPTION_GROUP_V1
CAPTION_GROUP_HASH_V1
CAPTION_GROUPS_V1
CAPTION_GROUPS_HASH_V1
PHRASE_GROUPING_POLICY_V1
CaptionGroupWordCountPolicy
CaptionGroupingRejectionReason
CaptionGroup
CaptionGroupsArtifact
CaptionGroupsContractError
compile_caption_groups
load_caption_groups
serialize_caption_groups
```

The existing exact-export oracle must be extended by a named 13-symbol set;
all pre-existing public exports must remain present and no private registry,
materialization helper, canonical-JSON helper, dependency helper, or mutable
builder may leak through `engine.contracts`.

## Import direction and dependency boundary

Permitted imports are the standard library and the accepted repository-owned
contract layers named by section 5 of the specification:

```text
engine.contracts.caption_groups
  -> engine.contracts._canonical_json
  -> engine.contracts.narration
  -> engine.contracts.alignment_result
  -> engine.contracts.issue_codes
```

The module must remain domain-neutral. It may not import providers, network or
filesystem clients, FastAPI/Studio API, UI, renderer, EDL, FFmpeg, Remotion,
legacy `v2` orchestration, or a domain pack. No reverse import from an
upstream contract into `caption_groups` is authorized.

## Required implementation behavior

The code must implement the accepted contract exactly, including:

- exact frozen dataclass models, constants, enum values/order, signatures,
  canonical JSON encodings, hashes, IDs, and `FX-CGS-01` bytes;
- exact-type and genuine-materialization rules for dependencies and outputs;
- current-content, binding, canonical coverage, sentence-run, token-boundary,
  timing, confidence, group, root-identity, and canonical-byte validation;
- deterministic first-failure precedence, the 10 coverage/timing outcomes,
  5 confidence outcomes, and all 45 loader-oracle rows;
- complete contiguous sentence-bounded grouping, with only declared 1-3 word
  exceptions and otherwise 4-9 word groups;
- transactionality and no publication or registry residue after failure;
- a weak registry that releases collected artifacts and retains neither
  dependencies nor caller-owned containers; and
- `O(W + T)` time and `O(W + T + output_bytes)` memory, with no quadratic
  rescans, recursive partition search, blocking I/O, threads, subprocesses,
  network access, or unbounded cache.

The implementation must not create or publish
`timing/caption_groups.json`. Serialization returns bytes only.

## Mandatory focused and adversarial verification

`tests/test_caption_groups.py` must cover every mandatory category in section
21 of the accepted specification. At minimum the gate must demonstrate:

- exact API shape, field/signature order, exports, forbidden exports, enum
  values, and constant values;
- genuine dependency/output enforcement, mutation/copy/proxy/subclass/
  reconstruction rejection, current-content drift, and transactional failure;
- full word/timing coverage, repeated words, empty sentences, punctuation and
  non-spoken tokens, sentence boundaries, and absence of string-search logic;
- sentence lengths 1 through at least 100 plus exhaustive legal partitions
  4 through 24, deterministic boundary ranking, ties, and remainder handling;
- every closed validation outcome and loader-oracle row, multi-fault
  precedence, unknown/missing/type/index ordering, malformed input,
  non-canonical bytes, and closed pointers/codes;
- exact `FX-CGS-01` bytes, hashes, IDs, load/serialize round trips, non-ASCII
  canonical encoding, and determinism across repeated calls;
- private weak-registry collection and stale-callback safety; and
- explicit guards against I/O, provider/API use, threads, subprocesses,
  mutable leaks, and super-linear grouping behavior.

The focused gate must include both new and mechanically affected test modules.
The regression gate must include the accepted Phase 2 upstream contract suites
for temporal raw package, canonical narration, audio artifact, alignment
request, adapter execution, and alignment result. A broader non-provider
repository regression should run when the environment permits. Existing
environment-only collection limitations must be reported rather than hidden.

## Operational and cost policy

This is a pure in-memory deterministic contract task. Commercial LLM and
media APIs remain off. REPLAY-first policy remains in force. No credential,
network, queue, retry, provider execution, database, filesystem publication,
or browser automation is needed or authorized.

## Acceptance boundary after implementation

Implementation completion is not acceptance. After the exact four-path
candidate is tested and remote closed, it requires an independent read-only
implementation audit against the accepted specification. Any blocking finding
must be repaired and targeted re-audited before a separate acceptance decision.

Phase 2 remains open even if this bounded implementation is later accepted.
Emphasis mapping, word-to-frame compilation, confidence/report integration,
V5/V6 preview and collision validation, and Master Roadmap Phase 2 acceptance
remain separate future decisions.

## Documentation impact matrix

| Document | Impact of this decision |
|---|---|
| `docs/MASTER_ROADMAP.md` | None; authoritative roadmap remains unchanged. |
| `docs/CURRENT_STATE.md` | Records authorization and the exact four-path boundary. |
| `docs/NEXT_ACTIONS.md` | Advances the single next task to bounded implementation. |
| `docs/KNOWN_LIMITATIONS.md` | Records that implementation and acceptance remain open. |
| `docs/PHASE_ACCEPTANCE.md` | Records authorization without claiming Phase 2 acceptance. |
| `docs/CHANGELOG.md` | Records this decision and its non-claims. |

## Repository safety

`norm_words_debug.json` was excluded from every repository status/diff check
and was not read, statted, hashed, diffed, modified, deleted, or staged.
