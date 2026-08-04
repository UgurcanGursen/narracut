# Phase 2 Canonical Emphasis Events Contract

## 1. Status and authority

Status: Candidate specification

Accepted: No

Implementation authorized: No

Phase 2 closed: No

This document is the bounded candidate selected by
`baseline/phase2_post_caption_groups_scope_reconciliation_report.md`. It is
subordinate to `docs/MASTER_ROADMAP.md` and defines only the canonical semantic
emphasis-event artifact represented by future
`timing/emphasis_events.json` bytes.

The official total Phase 2 Slice count remains unknown. This document assigns
no Slice number and states no completion percentage.

## 2. Bounded purpose

The contract deterministically compiles exact declarative emphasis intents
against one genuine current canonical narration revision, one genuine accepted
successful `AlignmentResult`, one genuine accepted `CaptionGroupsArtifact`,
and one validated resolved Domain Pack policy snapshot. It provides:

- non-empty half-open canonical word-ID ranges, never string search;
- domain-owned, versioned emphasis-type references without core domain
  conditionals;
- a closed domain-neutral intensity scale;
- exact containment in one accepted caption group;
- deterministic timing and confidence derived only from accepted word timings;
- stable event and artifact identities;
- immutable canonical bytes suitable for later publication as
  `timing/emphasis_events.json`; and
- fail-closed dependency, policy, validation, mutation, and no-leak behavior.

An intent may choose only a semantic word range, a resolved Domain Pack visual
grammar reference, and intensity. No intent, caller, LLM, provider, UI, or
loader may supply milliseconds, frames, display text, confidence, caption
group identity, output identity, or fallback values.

## 3. Explicit exclusions

This contract does not define or authorize:

- production implementation or tests;
- specification acceptance or implementation authorization;
- LLM/provider execution, prompt templates, browser automation, paid API calls,
  retries, queues, or planner orchestration;
- fuzzy, substring, regex, normalized-text, or first-match resolution of an
  LLM `text_span`;
- caller-, LLM-, UI-, or manually-authored seconds, milliseconds, frames,
  confidence, or caption-group selection;
- a planner artifact, planner authorship attestation, or manual-review task
  package;
- word-to-frame compilation, frame-rate or rounding policy, `start_frame`,
  `end_frame`, or one-frame drift acceptance;
- typography style, animation preset, font, layout, coordinates, safe area,
  V5/V6 collision handling, preview rendering, or `CaptionPreviewRenderer`;
- `AlignmentReport`, confidence thresholds, failure artifacts, or correction
  workflows;
- filesystem publication, artifact lifecycle, workspace persistence, Studio
  API, database/cache, Phase 3 EDL, renderer integration, or Phase 2 closure.

If an external planner emits `text_span`, an outside adapter must resolve it to
one exact, unambiguous `WordRangeReference` before this boundary. Ambiguous or
unresolved text produces no canonical intent or artifact. This contract never
receives or stores `text_span`.

## 4. Terminology and core invariants

**Intent** means an untrusted declarative `EmphasisIntent` containing exactly
one word range, one typed visual-grammar reference, and one intensity.

**Emphasis type reference** means a three-part `(domain_id, name, version)`
reference that exactly matches one entry in the resolved Domain Pack
`visual_grammars` inventory. Core does not interpret the name.

**Accepted word range** means a non-empty `WordRangeReference` resolved with
`WordRangeConsumer.EMPHASIS` against the exact current narration revision.

**Containing caption group** means the unique accepted caption group whose
half-open word interval fully contains the intent interval.

**Emphasis event** means the immutable derived output for one accepted intent.

The artifact invariants are:

1. intents are in strict canonical range order;
2. ranges are non-empty, unique, and non-overlapping; adjacency is allowed;
3. every range remains within one narration sentence and one caption group;
4. each output event maps one-to-one to the intent at the same ordinal;
5. word IDs, caption group, time, and confidence are derived, never supplied;
6. no text or source offsets are copied into the artifact;
7. an empty intent tuple is valid and yields an empty event tuple; and
8. every failure publishes no event, root identity, hash, or canonical bytes.

## 5. Future paths and import direction

Candidate future implementation paths are descriptive, not authorized:

```text
engine/contracts/emphasis_events.py
tests/test_emphasis_events.py
engine/contracts/__init__.py   # mechanical additive export only
tests/test_alignment_request.py # mechanical exact-export oracle only
```

Permitted import direction is:

```text
engine.contracts.emphasis_events
  -> engine.contracts._canonical_json
  -> engine.contracts.narration
  -> engine.contracts.alignment_result
  -> engine.contracts.caption_groups
  -> engine.contracts.alignment_execution  # ConfidenceAvailability only
  -> engine.contracts.domain               # registry/hash helpers only
  -> engine.contracts.models               # DomainPolicySnapshot only
  -> engine.contracts.temporal             # stable issue inventory only
```

Forbidden imports include provider/runtime orchestration, filesystem writers,
network clients, database/cache, clocks, random generators, subprocesses,
threads, UI, renderer, frame compiler, preview/layout, Phase 3, and V2 modules.
The contract performs no I/O. A caller may prepare a discovered registry before
entry; the compile/load functions never call `discover`, read a bundle, or
retain the registry.

## 6. Exact future public symbol delta

If separately authorized, the additive public surface is exactly:

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

No policy extractor, registry, hashing helper, range helper, mutable builder,
text resolver, or private projection function is public.

## 7. Closed constants and enums

```python
EMPHASIS_EVENT_V1 = "EMPHASIS-EVENT-V1"
EMPHASIS_EVENT_HASH_V1 = "EMPHASIS-EVENT-HASH-V1"
EMPHASIS_EVENTS_V1 = "EMPHASIS-EVENTS-V1"
EMPHASIS_EVENTS_HASH_V1 = "EMPHASIS-EVENTS-HASH-V1"
EMPHASIS_MAPPING_POLICY_V1 = "EMPHASIS-MAPPING-POLICY-V1"

class EmphasisIntensity(str, Enum):
    SUBTLE = "SUBTLE"
    MEDIUM = "MEDIUM"
    STRONG = "STRONG"

class EmphasisEventsRejectionReason(str, Enum):
    STRUCTURE_INVALID = "STRUCTURE_INVALID"
    UNSUPPORTED_VALUE = "UNSUPPORTED_VALUE"
    DEPENDENCY_CONTENT_DRIFT = "DEPENDENCY_CONTENT_DRIFT"
    DEPENDENCY_BINDING_INVALID = "DEPENDENCY_BINDING_INVALID"
    POLICY_INVALID = "POLICY_INVALID"
    INTENT_INVALID = "INTENT_INVALID"
    WORD_RANGE_INVALID = "WORD_RANGE_INVALID"
    ORDERING_INVALID = "ORDERING_INVALID"
    OVERLAP_INVALID = "OVERLAP_INVALID"
    CAPTION_GROUP_BINDING_INVALID = "CAPTION_GROUP_BINDING_INVALID"
    TIMING_INVALID = "TIMING_INVALID"
    CONFIDENCE_INVALID = "CONFIDENCE_INVALID"
    NON_CANONICAL_SERIALIZATION = "NON_CANONICAL_SERIALIZATION"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    CONTENT_DRIFT = "CONTENT_DRIFT"
    NOT_MATERIALIZED = "NOT_MATERIALIZED"
```

Values and declaration order are exact and closed. There are no aliases,
case-folding, coercion, unknown-value fallback, or core/domain-specific
extension enums. `EmphasisIntensity` is a transport magnitude only; its visual
meaning remains Domain Pack/renderer policy outside this contract.

Private hard bounds are normative:

```text
MAX_EMPHASIS_EVENTS = 10_000
MAX_TYPE_NAME_CODE_POINTS = 128
```

The effective event maximum is the smaller of `10_000` and canonical word
count because event ranges cannot overlap.

## 8. Exact data models and signatures

Field order is normative:

```python
@dataclass(frozen=True)
class EmphasisTypeRef:
    domain_id: str
    name: str
    version: str

@dataclass(frozen=True)
class EmphasisIntent:
    word_range: WordRangeReference
    emphasis_type_ref: EmphasisTypeRef
    intensity: EmphasisIntensity

@dataclass(frozen=True)
class EmphasisEvent:
    schema_version: str
    hash_scope_version: str
    emphasis_event_id: str
    emphasis_event_hash: str
    narration_revision_id: str
    alignment_result_id: str
    caption_groups_id: str
    policy_snapshot_id: str
    policy_snapshot_hash: str
    mapping_policy_version: str
    ordinal: int
    caption_group_id: str
    start_word_ordinal: int
    end_exclusive_word_ordinal: int
    start_word_id: str
    end_word_id: str
    word_ids: tuple[str, ...]
    emphasis_type_ref: EmphasisTypeRef
    intensity: EmphasisIntensity
    start_ms: int
    end_ms: int
    confidence_millionths: int | None

@dataclass(frozen=True)
class EmphasisEventsArtifact:
    schema_version: str
    hash_scope_version: str
    emphasis_events_id: str
    emphasis_events_hash: str
    project_id: str
    document_id: str
    narration_revision_id: str
    narration_revision_hash: str
    alignment_result_id: str
    alignment_result_hash: str
    caption_groups_id: str
    caption_groups_hash: str
    mapping_policy_version: str
    domain_id: str
    domain_pack_version: str
    policy_snapshot_id: str
    policy_snapshot_hash: str
    confidence_availability: ConfidenceAvailability
    emphasis_events: tuple[EmphasisEvent, ...]
```

All fields are required. Only event `confidence_millionths` may be null. There
are no extensions. Text, normalized text, source offsets, sentence text,
display text, authored times/frames, style/layout, provider metadata, prompts,
paths, URIs, authorization data, issue arrays, and arbitrary metadata are
forbidden.

```python
def compile_emphasis_events(
    *,
    narration_document: CanonicalNarrationDocument,
    narration_revision: NarrationRevision,
    alignment_result: AlignmentResult,
    caption_groups: CaptionGroupsArtifact,
    domain_policy_snapshot: DomainPolicySnapshot,
    domain_pack_registry: DomainPackRegistry,
    intents: tuple[EmphasisIntent, ...],
) -> EmphasisEventsArtifact

def load_emphasis_events(
    source: bytes,
    *,
    narration_document: CanonicalNarrationDocument,
    narration_revision: NarrationRevision,
    alignment_result: AlignmentResult,
    caption_groups: CaptionGroupsArtifact,
    domain_policy_snapshot: DomainPolicySnapshot,
    domain_pack_registry: DomainPackRegistry,
    intents: tuple[EmphasisIntent, ...],
) -> EmphasisEventsArtifact

def serialize_emphasis_events(
    artifact: EmphasisEventsArtifact,
) -> bytes
```

The keyword-only order is exact. There is no public overload accepting JSON
intents, `text_span`, milliseconds, frames, a logical output mapping, or a
default policy. `intents` must be exact built-in `tuple`; list, sequence,
iterator, generator, or tuple subclass is rejected. Inputs are validated and
copied into immutable output values; caller containers are never retained.

## 9. Dependency integrity preflight

### 9.1 Exact types and current-content genuineness

Preflight requires exact built-in contract types, not `isinstance` acceptance,
in signature order:

1. `CanonicalNarrationDocument`;
2. `NarrationRevision`;
3. `AlignmentResult`;
4. `CaptionGroupsArtifact`;
5. `DomainPolicySnapshot`;
6. `DomainPackRegistry`;
7. exact `tuple` intents and exact nested intent/ref/range/enum types.

Subclass, proxy, dataclass copy, reconstruction, pickle copy, stale instance,
replacement object, or an object made equal by field assignment is not a
genuine accepted narration/alignment/caption dependency. Existing private
registries and canonical serializers must confirm current-content identity for
the first four dependencies before intent inspection.

The policy snapshot has no accepted private materialization registry in the
current Phase 1 model, so this contract does not invent one. Instead it
reconstructs every snapshot field into exact built-in JSON containers,
recomputes `policy_snapshot_hash`, requires exact `canonical_hash`, derives
`snapshot_id = "dps_" + hash_hex[0:20]`, requires `immutable is True`, and
verifies manifest and visual-grammar parity through the exact discovered
registry entry. This is content/provenance verification, not an authorship or
signature claim.

Nested mutation through `object.__setattr__`, mutable mappings/lists, enum
replacement, or dependency replacement after prior success must be detected.
Preflight retains no dependency, registry, snapshot, or intent reference.

### 9.2 Exact cross-binding order

After current-content checks, binding is validated in this exact order:

1. document current revision equals revision ID;
2. document project/document IDs equal revision values;
3. alignment result project/document/revision IDs and revision hash match;
4. caption artifact project/document/revision IDs and revision hash match;
5. caption artifact alignment result ID/hash match;
6. alignment and caption confidence availability match;
7. snapshot domain/version identifies one registry pack;
8. snapshot manifest hash matches that exact pack raw manifest;
9. snapshot resolved `extensions` exactly matches pack manifest extensions;
10. all four root dependencies are current and mutually consistent.

No identifier is normalized or compared case-insensitively. Any mismatch
fails before policy extraction, intent validation, output construction, or
publication.

## 10. Domain Pack policy boundary

Core owns no emphasis-type vocabulary. It reads only this exact path from the
verified snapshot:

```text
resolved_policy/extensions/visual_grammars
```

Implementation must resolve this mapping once into a private immutable typed
`_ResolvedEmphasisPolicy` containing snapshot identity, domain/version, and an
exact tuple/frozen lookup of permitted `EmphasisTypeRef` values. Downstream
validation consumes only that typed value. Repeated raw mapping traversal or
domain behavior distributed through service-level conditionals is forbidden.
The resolver is private because it is specific to this artifact boundary; it
does not replace or broaden the existing repository `DomainPolicyResolver`.

The snapshot `resolved_policy` must be an exact built-in dict with exactly:

```text
policy_bundles
extensions
enabled_extensions
overrides
```

`extensions` must be an exact dict satisfying the existing manifest extension
shape. `visual_grammars` must be an exact list. Each entry is an exact dict
with exactly `name`, `version`, `description`; name and version are NFC safe
strings, and duplicate `(name, version)` pairs reject the snapshot. The
registry manifest and snapshot extension documents must be canonical-logically
equal; description participates in parity but is never copied to output.

An `EmphasisTypeRef` is accepted only when:

- `domain_id` exactly equals snapshot `domain_id`;
- `name` matches `^[a-z][a-z0-9_]*$`, is no more than 128 code points, and is
  NFC;
- `version` is the exact manifest semver string; and
- exactly one verified `visual_grammars` entry has the same name and version.

Core performs no `if domain == ...`, no name ranking, no semantic aliasing,
and no fallback to `event_types`. A type present only in `event_types` is not a
V5 visual grammar and is rejected. Missing pack, missing policy, empty visual
grammar inventory, unknown type, duplicate type, or drift fails closed.

The existing `business-tech` skeleton is the only production target, but this
contract does not add new pack values. `earnings_sting@0.1.0` is used only by
the exact golden because it is already present in the accepted skeleton. New
production V5 vocabularies require a separate Domain Pack policy change and
acceptance; they never require a core conditional.

## 11. Intent validation and canonical order

Each `EmphasisIntent` is validated in tuple index order:

1. exact dataclass/type fields;
2. exact `WordRangeReference` and `narration_revision_id` equality;
3. unsigned 32-bit ordinal types (`bool` is invalid);
4. start less than exclusive end;
5. endpoints within canonical word count;
6. `resolve_word_range(..., consumer=WordRangeConsumer.EMPHASIS)` success;
7. all selected words share one `sentence_id`;
8. exact `EmphasisTypeRef` structural and policy validation;
9. exact `EmphasisIntensity` enum.

The tuple itself must contain at most 10,000 entries. Intents must already be
strictly ordered by:

```text
(start_ordinal, end_exclusive_ordinal,
 emphasis_type_ref.domain_id, emphasis_type_ref.name,
 emphasis_type_ref.version, intensity.value)
```

The compiler does not silently reorder. After structural order is proven,
each later start must be greater than or equal to the preceding exclusive end.
Equality is valid adjacency. A lower start is overlap. Exact duplicate intent
content is both non-increasing and overlapping and is rejected as overlap.

No semantic importance judgment occurs here. An upstream planner/reviewer is
responsible for choosing sparse editorial ranges. This artifact proves the
range is canonical and policy-addressable, not that the editorial choice is
good.

## 12. Caption-group containment and mapping

Caption groups are pre-indexed by start/end ordinal. For each intent, exactly
one group must satisfy:

```text
group.start_word_ordinal <= intent.start_ordinal
and
intent.end_exclusive_ordinal <= group.end_exclusive_word_ordinal
```

Zero matches rejects. More than one match indicates a drifted/invalid caption
partition and rejects during dependency preflight. An event cannot cross a
caption boundary even when both groups share one sentence. The derived
`caption_group_id` is copied from the unique match; callers never supply it.

The event range derives exactly:

```text
start_word_ordinal = intent.word_range.start_ordinal
end_exclusive_word_ordinal = intent.word_range.end_exclusive_ordinal
word_ids = canonical word IDs in that half-open range
start_word_id = word_ids[0]
end_word_id = word_ids[-1]
```

No string comparison, token search, display-text comparison, source-offset
search, or sentence-text scan participates in mapping.

## 13. Derived timing and confidence

Alignment timings are pre-indexed by exact `word_id`. The accepted alignment
result and caption artifact must each already prove complete word coverage.
For each event:

```text
start_ms = timing(start_word_id).start_ms
end_ms = timing(end_word_id).end_ms
```

All selected timings must be positive-duration, monotonic, non-overlapping,
within audio bounds, and in canonical word order. Derived event duration must
be positive. No padding, lead/lag, animation preroll, rounding, snapping,
frame conversion, or default is applied.

Confidence follows the alignment result declaration:

- `AVAILABLE`: every selected word confidence is an exact integer in
  `[0, 1_000_000]`; event confidence is the exact minimum.
- `UNAVAILABLE`: every selected word and event confidence is null.
- `NOT_APPLICABLE`: every selected word and event confidence is null.

Caption group confidence is independently recomputed as the minimum across the
whole containing group and must match its accepted declaration. An event
subset may legitimately have a higher confidence than its group. The event
must never copy group confidence as a shortcut.

This contract carries confidence evidence but defines no low-confidence
threshold or report. `AlignmentReport` remains separate work.

## 14. Event construction and identity

One event is constructed per intent in identical ordinal order. Every field is
derived from validated dependencies, snapshot, or exact intent semantics.

The event projection contains every `EmphasisEvent` field except
`emphasis_event_id` and `emphasis_event_hash`. The nested type reference is
serialized as an exact object with `domain_id`, `name`, and `version`.

```text
emphasis_event_hash = lowercase_hex(SHA256(canonical_event_projection_bytes))
emphasis_event_id = "emph_" + emphasis_event_hash[0:32]
```

Hash is checked before ID. Ordinal, word membership, caption group, policy
snapshot, type, intensity, timing, and confidence all participate. Identical
words at a different revision position, type version, policy snapshot, or
intensity produce a different event identity.

## 15. Artifact identity and canonical serialization

The artifact projection contains every `EmphasisEventsArtifact` field except
`emphasis_events_id` and `emphasis_events_hash`, including complete event
envelopes in ordinal order.

```text
emphasis_events_hash = lowercase_hex(SHA256(canonical_artifact_projection_bytes))
emphasis_events_id = "emps_" + emphasis_events_hash[0:32]
```

`encode_canonical_json_bytes` rules apply: UTF-8, no BOM, no trailing newline
or whitespace, unique keys, keys sorted by Unicode code point, semantic array
order, exact minimal base-10 integers, and no floats, exponent, NaN, infinity,
or negative zero. Strings are exact NFC and obey accepted forbidden-code-point
rules.

Parsed objects are exact built-in `dict`; arrays are exact built-in `list`.
Subclasses, arbitrary mappings/sequences, tuples, iterators, and coercible
values reject. Construction converts validated lists to tuples and retains no
caller container.

`load_emphasis_events` first completes dependency and intent preflight, then
strictly parses source bytes and independently compiles the expected artifact.
It requires every field, event projection hash/ID, root projection hash/ID,
and final source byte to equal the deterministic result. A canonical but
different event set cannot load.

A loader `source` that is not exact built-in `bytes` raises sanitized
`TypeError`. BOM, invalid UTF-8, invalid/trailing JSON, duplicate keys,
forbidden number syntax, or logically equal non-canonical bytes reject at `/`
with `NON_CANONICAL_SERIALIZATION` and null issue code.

## 16. Mutation resistance and publication registry

Compilation/loading returns frozen dataclasses with tuples and exact immutable
enum/ref/range values. No mutable alias from snapshot, registry, intents,
parsed JSON, or dependency is retained.

A private weak-reference registry records only:

- object identity;
- canonical envelope bytes;
- root ID and hash; and
- weak-reference cleanup callback identity.

It stores no dependency, policy snapshot, registry, intent, text, parsed
mapping, or caller container. Registration is transactional and final. A live
identity collision never overwrites an entry. Partial construction or callback
setup failure rolls back all tentative state. Stale callbacks cannot remove a
newer entry reusing an object ID.

`serialize_emphasis_events` accepts only the exact registered instance,
revalidates its entire current projection, nested refs/enums/tuples, hashes and
IDs, and compares newly encoded bytes with registered bytes. Direct
construction, copy, subclass, proxy, pickle/reconstruction, equal-but-distinct
object, or any `object.__setattr__` mutation rejects. Collected artifacts leave
no live registry entry.

## 17. Error contract, pointers, and no-leak behavior

```python
class EmphasisEventsContractError(ValueError):
    reason: EmphasisEventsRejectionReason
    pointer: str
    issue_code: str | None
```

Messages are fixed sanitized English literals selected only by closed reason.
Compile intent faults use `/intents/<index>`; loader event faults use
`/emphasis_events/<index>`. Dependency and root pointers are fixed literals.
Unknown or attacker-authored key/type text never appears in pointer or message.

Errors never contain narration/display/source text, a planner `text_span`,
visual-grammar description, unknown attacker type name, provider payload,
policy bundle content, hashes supplied by an attacker, paths, URIs,
credentials, environment values, raw exceptions, repr output, or filesystem
details. Registry/domain errors are caught and replaced by contract literals.

Wrong exact dependency/input types raise sanitized `TypeError`. Internal
construction/registry failure raises sanitized `RuntimeError`. Contract errors
carry no output identity, bytes, partial event, or failure artifact.

Only existing stable issue codes are used:

```text
ADAPTER_PRECISION_OVERSTATED
ALIGNMENT_REQUEST_IDENTITY_MISMATCH
CANONICAL_COVERAGE_BLOCKER
CANONICAL_WORD_ORDER_INVALID
CONFIDENCE_REQUIRED_UNAVAILABLE
REPLAY_HASH_MISMATCH
TIMESTAMP_NON_MONOTONIC
TIMESTAMP_OUT_OF_BOUNDS
TIMESTAMP_OVERLAP
UNSUPPORTED_CONTRACT_ENUM
WORD_RANGE_OUT_OF_BOUNDS
WORD_RANGE_REVERSED
WORD_RANGE_REVISION_MISMATCH
ZERO_DURATION_WORD
```

Policy-specific faults use null issue code because no existing stable temporal
code accurately represents Domain Pack policy failure. No stable issue
inventory delta is introduced by this candidate.

## 18. Deterministic validation precedence

First failure is authoritative:

1. exact dependency/input types in signature order;
2. narration document, revision, alignment result, and caption artifact
   current-content integrity;
3. policy snapshot exact reconstruction, hash/ID/immutable checks;
4. registry pack existence, manifest hash, and extension parity;
5. cross-dependency binding in section 9.2 order;
6. alignment word coverage/timing/confidence, then caption partition/current
   derived values;
7. intent tuple count and per-intent structure in index order;
8. word-range revision, ordinal types, non-empty/bounds/resolution, sentence;
9. type-ref structure then resolved visual-grammar membership;
10. intensity;
11. canonical intent order, duplicate/overlap;
12. caption-group containment;
13. derived word IDs, timing, and confidence;
14. loader bytes/UTF-8/JSON/canonical syntax, when loading;
15. loader root exact keys/types/constants/dependency/policy declarations;
16. loader event list and each event in ordinal order;
17. event projection hash then event ID in ordinal order;
18. root projection hash then root ID;
19. full canonical envelope/source-byte equality; and
20. transactional registry publication.

Within parsed objects, unknown keys win before missing keys, then model field
order. Within arrays, lower index wins. Dependency or intent failure is never
masked by malformed loader bytes because preflight intentionally precedes
source parsing.

### 18.1 Closed rejection oracle

| Fault | Pointer | Reason | Issue code |
|---|---|---|---|
| narration dependency drift | `/narration_revision` | `DEPENDENCY_CONTENT_DRIFT` | `ALIGNMENT_REQUEST_IDENTITY_MISMATCH` |
| alignment result drift | `/alignment_result` | `DEPENDENCY_CONTENT_DRIFT` | `REPLAY_HASH_MISMATCH` |
| caption artifact drift | `/caption_groups` | `DEPENDENCY_CONTENT_DRIFT` | `REPLAY_HASH_MISMATCH` |
| policy snapshot hash or derived ID mismatch | `/domain_policy_snapshot` | `DEPENDENCY_CONTENT_DRIFT` | null |
| policy snapshot is not immutable | `/domain_policy_snapshot` | `POLICY_INVALID` | null |
| registry pack missing or manifest hash differs | `/domain_policy_snapshot` | `POLICY_INVALID` | null |
| snapshot extensions differ from registry manifest | `/domain_policy_snapshot` | `POLICY_INVALID` | null |
| document/revision/result/caption binding mismatch | fixed failing dependency pointer | `DEPENDENCY_BINDING_INVALID` | `ALIGNMENT_REQUEST_IDENTITY_MISMATCH` |
| alignment/caption confidence availability differs | `/caption_groups` | `CONFIDENCE_INVALID` | `ADAPTER_PRECISION_OVERSTATED` |
| alignment word coverage/timing inventory invalid | `/alignment_result` | `DEPENDENCY_CONTENT_DRIFT` | `CANONICAL_COVERAGE_BLOCKER` |
| caption partition/group derived value invalid | `/caption_groups` | `DEPENDENCY_CONTENT_DRIFT` | `CANONICAL_COVERAGE_BLOCKER` |
| intents is not exact tuple or exceeds limit | `/intents` | `STRUCTURE_INVALID` | null |
| intent/ref/range is not its exact type | `/intents/<index>` | `STRUCTURE_INVALID` | null |
| range revision differs | `/intents/<index>` | `WORD_RANGE_INVALID` | `WORD_RANGE_REVISION_MISMATCH` |
| start exceeds exclusive end | `/intents/<index>` | `WORD_RANGE_INVALID` | `WORD_RANGE_REVERSED` |
| range empty or endpoint outside revision | `/intents/<index>` | `WORD_RANGE_INVALID` | `WORD_RANGE_OUT_OF_BOUNDS` |
| range spans more than one sentence | `/intents/<index>` | `WORD_RANGE_INVALID` | `CANONICAL_COVERAGE_BLOCKER` |
| type-ref string/shape/domain syntax invalid | `/intents/<index>` | `STRUCTURE_INVALID` | null |
| type-ref domain differs from snapshot | `/intents/<index>` | `POLICY_INVALID` | null |
| type absent/duplicated in resolved visual grammars | `/intents/<index>` | `POLICY_INVALID` | null |
| intensity is not exact closed enum | `/intents/<index>` | `UNSUPPORTED_VALUE` | `UNSUPPORTED_CONTRACT_ENUM` |
| tuple is not in canonical sort order without overlap | `/intents/<index>` | `ORDERING_INVALID` | `CANONICAL_WORD_ORDER_INVALID` |
| duplicate or overlapping range | `/intents/<index>` | `OVERLAP_INVALID` | `CANONICAL_COVERAGE_BLOCKER` |
| range has zero or multiple containing caption groups | `/intents/<index>` | `CAPTION_GROUP_BINDING_INVALID` | `CANONICAL_COVERAGE_BLOCKER` |
| derived selected timing is zero/out-of-bounds/overlapping | `/intents/<index>` | `TIMING_INVALID` | exact applicable timestamp/zero-duration code |
| AVAILABLE selected confidence is missing | `/intents/<index>` | `CONFIDENCE_INVALID` | `CONFIDENCE_REQUIRED_UNAVAILABLE` |
| derived confidence otherwise invalid | `/intents/<index>` | `CONFIDENCE_INVALID` | `ADAPTER_PRECISION_OVERSTATED` |
| loader root is not exact dict, has unknown/missing keys, or wrong field container/scalar type | `/` | `STRUCTURE_INVALID` | null |
| loader event list is not exact list | `/emphasis_events` | `STRUCTURE_INVALID` | null |
| loader event/type-ref is not exact dict, has unknown/missing keys, or wrong field type | `/emphasis_events/<index>` | `STRUCTURE_INVALID` | null |
| unsupported root/event schema/hash/mapping/confidence/intensity literal | fixed root/event pointer | `UNSUPPORTED_VALUE` | `UNSUPPORTED_CONTRACT_ENUM` |
| loaded dependency/policy declaration differs | fixed root/event pointer | `DEPENDENCY_BINDING_INVALID` | `ALIGNMENT_REQUEST_IDENTITY_MISMATCH` or null for policy |
| loaded event count differs from intent count | `/emphasis_events` | `INTENT_INVALID` | `CANONICAL_COVERAGE_BLOCKER` |
| loaded ordinal differs from list index | `/emphasis_events/<index>` | `ORDERING_INVALID` | `CANONICAL_WORD_ORDER_INVALID` |
| loaded range/type/intensity differs from corresponding intent | `/emphasis_events/<index>` | `INTENT_INVALID` | null |
| loaded caption group or word IDs differ from derivation | `/emphasis_events/<index>` | `CAPTION_GROUP_BINDING_INVALID` | `CANONICAL_COVERAGE_BLOCKER` |
| loaded start/end time differs from derivation | `/emphasis_events/<index>` | `TIMING_INVALID` | `TIMESTAMP_NON_MONOTONIC` |
| loaded confidence null while AVAILABLE minimum is non-null | `/emphasis_events/<index>` | `CONFIDENCE_INVALID` | `CONFIDENCE_REQUIRED_UNAVAILABLE` |
| loaded confidence has any other inequality | `/emphasis_events/<index>` | `CONFIDENCE_INVALID` | `ADAPTER_PRECISION_OVERSTATED` |
| event hash mismatch | `/emphasis_events/<index>` | `IDENTITY_MISMATCH` | null |
| event ID mismatch after hash passed | `/emphasis_events/<index>` | `IDENTITY_MISMATCH` | null |
| root hash mismatch | `/` | `IDENTITY_MISMATCH` | null |
| root ID mismatch after hash passed | `/` | `IDENTITY_MISMATCH` | null |
| invalid/BOM/trailing/duplicate/non-canonical source bytes | `/` | `NON_CANONICAL_SERIALIZATION` | null |
| registered object mutated | `/` | `CONTENT_DRIFT` | null |
| direct/unregistered object serialized | `/` | `NOT_MATERIALIZED` | null |

For the timing row, issue selection is closed: zero duration ->
`ZERO_DURATION_WORD`; before audio start/after audio end ->
`TIMESTAMP_OUT_OF_BOUNDS`; overlap -> `TIMESTAMP_OVERLAP`; otherwise order or
derived endpoint mismatch -> `TIMESTAMP_NON_MONOTONIC`, in that order.

For the unsupported-literal row, the pointer is `/` for a root literal and
`/emphasis_events/<index>` for an event/type/intensity literal. For dependency
declaration mismatch the lowest field in model order wins. No implementer may
choose an alternate pointer/reason/code.

## 19. Golden fixture `FX-EME-01`

The golden consumes exact FX-CGS-01 narration/alignment/caption dependencies
and the committed `business-tech` policy snapshot:

```text
project_id=prj_fx34
document_id=nardoc_fx34
narration_revision_id=narrev_d60d7ae087efb0e309d4
alignment_result_id=alr_1521f195a591df09edaa968d8f5fa91e
caption_groups_id=cgs_12670fe861389bfe8e25f05a126c7ea3
policy_snapshot_id=dps_d18e9981c3f4bcca8e3f
policy_snapshot_hash=sha256:d18e9981c3f4bcca8e3f5a8f62c838d0e0ecbd14e6cd229e2702c08e2a3f3f2c
```

The single intent is literal:

```text
word range=[0,2)
emphasis type=business-tech / earnings_sting / 0.1.0
intensity=STRONG
```

It maps to caption group
`cgrp_2bdd1bc0e985d5d45784956cb0818fb9`, word IDs
`nword_5321ba14c2c4b28c31ab` through
`nword_0cc9d55672a3cb4e9199`, time `[100,900]` ms, and confidence
`960000`.

Exact event projection bytes:

```json
{"alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","caption_group_id":"cgrp_2bdd1bc0e985d5d45784956cb0818fb9","caption_groups_id":"cgs_12670fe861389bfe8e25f05a126c7ea3","confidence_millionths":960000,"emphasis_type_ref":{"domain_id":"business-tech","name":"earnings_sting","version":"0.1.0"},"end_exclusive_word_ordinal":2,"end_ms":900,"end_word_id":"nword_0cc9d55672a3cb4e9199","hash_scope_version":"EMPHASIS-EVENT-HASH-V1","intensity":"STRONG","mapping_policy_version":"EMPHASIS-MAPPING-POLICY-V1","narration_revision_id":"narrev_d60d7ae087efb0e309d4","ordinal":0,"policy_snapshot_hash":"sha256:d18e9981c3f4bcca8e3f5a8f62c838d0e0ecbd14e6cd229e2702c08e2a3f3f2c","policy_snapshot_id":"dps_d18e9981c3f4bcca8e3f","schema_version":"EMPHASIS-EVENT-V1","start_ms":100,"start_word_id":"nword_5321ba14c2c4b28c31ab","start_word_ordinal":0,"word_ids":["nword_5321ba14c2c4b28c31ab","nword_0cc9d55672a3cb4e9199"]}
```

```text
event projection length=913
event hash=3b919932a4e05683fe94c9eae048341b705259b7dcacfb8d552f9ca6531437d5
event ID=emph_3b919932a4e05683fe94c9eae048341b
event envelope length=1062
event envelope SHA-256=3fa29852cb8dd7c22c10d69f5afd9123bddac3431ff8f2f27230bfc22e71d8e9
```

Exact event envelope bytes:

```json
{"alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","caption_group_id":"cgrp_2bdd1bc0e985d5d45784956cb0818fb9","caption_groups_id":"cgs_12670fe861389bfe8e25f05a126c7ea3","confidence_millionths":960000,"emphasis_event_hash":"3b919932a4e05683fe94c9eae048341b705259b7dcacfb8d552f9ca6531437d5","emphasis_event_id":"emph_3b919932a4e05683fe94c9eae048341b","emphasis_type_ref":{"domain_id":"business-tech","name":"earnings_sting","version":"0.1.0"},"end_exclusive_word_ordinal":2,"end_ms":900,"end_word_id":"nword_0cc9d55672a3cb4e9199","hash_scope_version":"EMPHASIS-EVENT-HASH-V1","intensity":"STRONG","mapping_policy_version":"EMPHASIS-MAPPING-POLICY-V1","narration_revision_id":"narrev_d60d7ae087efb0e309d4","ordinal":0,"policy_snapshot_hash":"sha256:d18e9981c3f4bcca8e3f5a8f62c838d0e0ecbd14e6cd229e2702c08e2a3f3f2c","policy_snapshot_id":"dps_d18e9981c3f4bcca8e3f","schema_version":"EMPHASIS-EVENT-V1","start_ms":100,"start_word_id":"nword_5321ba14c2c4b28c31ab","start_word_ordinal":0,"word_ids":["nword_5321ba14c2c4b28c31ab","nword_0cc9d55672a3cb4e9199"]}
```

Exact artifact projection bytes:

```json
{"alignment_result_hash":"1521f195a591df09edaa968d8f5fa91ed367be1c7190a3f614823d74b3cd36bb","alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","caption_groups_hash":"12670fe861389bfe8e25f05a126c7ea355c361c2b2848e9b02a216ed83baaec7","caption_groups_id":"cgs_12670fe861389bfe8e25f05a126c7ea3","confidence_availability":"AVAILABLE","document_id":"nardoc_fx34","domain_id":"business-tech","domain_pack_version":"0.1.0","emphasis_events":[{"alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","caption_group_id":"cgrp_2bdd1bc0e985d5d45784956cb0818fb9","caption_groups_id":"cgs_12670fe861389bfe8e25f05a126c7ea3","confidence_millionths":960000,"emphasis_event_hash":"3b919932a4e05683fe94c9eae048341b705259b7dcacfb8d552f9ca6531437d5","emphasis_event_id":"emph_3b919932a4e05683fe94c9eae048341b","emphasis_type_ref":{"domain_id":"business-tech","name":"earnings_sting","version":"0.1.0"},"end_exclusive_word_ordinal":2,"end_ms":900,"end_word_id":"nword_0cc9d55672a3cb4e9199","hash_scope_version":"EMPHASIS-EVENT-HASH-V1","intensity":"STRONG","mapping_policy_version":"EMPHASIS-MAPPING-POLICY-V1","narration_revision_id":"narrev_d60d7ae087efb0e309d4","ordinal":0,"policy_snapshot_hash":"sha256:d18e9981c3f4bcca8e3f5a8f62c838d0e0ecbd14e6cd229e2702c08e2a3f3f2c","policy_snapshot_id":"dps_d18e9981c3f4bcca8e3f","schema_version":"EMPHASIS-EVENT-V1","start_ms":100,"start_word_id":"nword_5321ba14c2c4b28c31ab","start_word_ordinal":0,"word_ids":["nword_5321ba14c2c4b28c31ab","nword_0cc9d55672a3cb4e9199"]}],"hash_scope_version":"EMPHASIS-EVENTS-HASH-V1","mapping_policy_version":"EMPHASIS-MAPPING-POLICY-V1","narration_revision_hash":"sha256:d60d7ae087efb0e309d4e3f28fedea074d15e11405046249a23b2c7bb42fe0c0","narration_revision_id":"narrev_d60d7ae087efb0e309d4","policy_snapshot_hash":"sha256:d18e9981c3f4bcca8e3f5a8f62c838d0e0ecbd14e6cd229e2702c08e2a3f3f2c","policy_snapshot_id":"dps_d18e9981c3f4bcca8e3f","project_id":"prj_fx34","schema_version":"EMPHASIS-EVENTS-V1"}
```

```text
artifact projection length=1970
artifact hash=e6286517914a305715e42460d27092370bf304f6715e28a6c483407758a04b7d
artifact ID=emps_e6286517914a305715e42460d2709237
artifact envelope length=2121
artifact envelope SHA-256=008e79e10b989f54377af498c269eca00df09b426b4d8a0ec86441e55a13111c
```

Exact artifact envelope bytes:

```json
{"alignment_result_hash":"1521f195a591df09edaa968d8f5fa91ed367be1c7190a3f614823d74b3cd36bb","alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","caption_groups_hash":"12670fe861389bfe8e25f05a126c7ea355c361c2b2848e9b02a216ed83baaec7","caption_groups_id":"cgs_12670fe861389bfe8e25f05a126c7ea3","confidence_availability":"AVAILABLE","document_id":"nardoc_fx34","domain_id":"business-tech","domain_pack_version":"0.1.0","emphasis_events":[{"alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","caption_group_id":"cgrp_2bdd1bc0e985d5d45784956cb0818fb9","caption_groups_id":"cgs_12670fe861389bfe8e25f05a126c7ea3","confidence_millionths":960000,"emphasis_event_hash":"3b919932a4e05683fe94c9eae048341b705259b7dcacfb8d552f9ca6531437d5","emphasis_event_id":"emph_3b919932a4e05683fe94c9eae048341b","emphasis_type_ref":{"domain_id":"business-tech","name":"earnings_sting","version":"0.1.0"},"end_exclusive_word_ordinal":2,"end_ms":900,"end_word_id":"nword_0cc9d55672a3cb4e9199","hash_scope_version":"EMPHASIS-EVENT-HASH-V1","intensity":"STRONG","mapping_policy_version":"EMPHASIS-MAPPING-POLICY-V1","narration_revision_id":"narrev_d60d7ae087efb0e309d4","ordinal":0,"policy_snapshot_hash":"sha256:d18e9981c3f4bcca8e3f5a8f62c838d0e0ecbd14e6cd229e2702c08e2a3f3f2c","policy_snapshot_id":"dps_d18e9981c3f4bcca8e3f","schema_version":"EMPHASIS-EVENT-V1","start_ms":100,"start_word_id":"nword_5321ba14c2c4b28c31ab","start_word_ordinal":0,"word_ids":["nword_5321ba14c2c4b28c31ab","nword_0cc9d55672a3cb4e9199"]}],"emphasis_events_hash":"e6286517914a305715e42460d27092370bf304f6715e28a6c483407758a04b7d","emphasis_events_id":"emps_e6286517914a305715e42460d2709237","hash_scope_version":"EMPHASIS-EVENTS-HASH-V1","mapping_policy_version":"EMPHASIS-MAPPING-POLICY-V1","narration_revision_hash":"sha256:d60d7ae087efb0e309d4e3f28fedea074d15e11405046249a23b2c7bb42fe0c0","narration_revision_id":"narrev_d60d7ae087efb0e309d4","policy_snapshot_hash":"sha256:d18e9981c3f4bcca8e3f5a8f62c838d0e0ecbd14e6cd229e2702c08e2a3f3f2c","policy_snapshot_id":"dps_d18e9981c3f4bcca8e3f","project_id":"prj_fx34","schema_version":"EMPHASIS-EVENTS-V1"}
```

Future tests must hold these full literal envelope bytes independently; they
may not generate expected envelopes through production helpers.

Repository encoding and an independent compact sorted-key UTF-8 encoder must
reproduce every length, hash, and ID above.

## 20. Mandatory future tests

The focused module must cover:

- exact constants, enum order/values, dataclass field order/types, signatures,
  public export delta, and forbidden exports;
- exact genuine narration/alignment/caption dependency requirements, every
  current-content drift path, cross-binding order, copy/proxy/subclass/
  reconstruction rejection, and no publication on failure;
- policy snapshot full reconstruction, canonical hash/ID/immutable checks,
  registry missing/stale/duplicate pack, manifest hash drift, extension parity,
  duplicate visual grammars, type name/version/domain checks, `event_types`
  non-fallback, and no domain conditional;
- exact tuple-only intent input, empty tuple, 10,000 bound, exact types, bool/
  float/string ordinal rejection, range revision/bounds/non-empty/sentence,
  canonical ordering, duplicate, overlap, and adjacency;
- repeated narration words proving no string search, ambiguous external span
  non-entry, no text field, and exact `WordRangeConsumer.EMPHASIS` resolution;
- zero/multiple containing group, cross-group range, multiple non-overlapping
  events in one group, adjacent groups, and exact derived caption group/word IDs;
- AVAILABLE/UNAVAILABLE/NOT_APPLICABLE confidence, subset minimum distinct
  from group minimum, integer bounds, null rules, and no group-confidence copy;
- exact timing endpoint derivation, audio bounds, zero duration, overlap,
  monotonicity, and static absence of seconds/frames/padding/rounding;
- FX-EME-01 literal event/artifact projection and envelope bytes, lengths,
  hashes, IDs, independent hash calculation, loader round trip, and two
  independent equivalent compilations;
- empty-artifact literal golden in addition to FX-EME-01;
- duplicate/unknown/missing keys, non-object canonical JSON roots, container
  subclasses, number syntax, invalid UTF-8, BOM, trailing bytes/newline,
  key-order and array-index precedence;
- every section 18.1 oracle row and multi-fault first-failure precedence with
  one exact pointer/reason/code outcome;
- event/root hash-before-ID, canonical-but-different intent/event rejection,
  mutated serialization, registry rollback/collision/stale callback/cleanup,
  dependency and caller-container non-retention, and no text/policy/path leak;
  and
- static import direction and absence of provider, filesystem discovery/read,
  network, database, cache, clock, random, thread, subprocess, frame, layout,
  preview, report, renderer, UI, V2, and Phase 3 imports.

Golden constants must be literal and must not be derived through production
projection or serialization helpers under test.

## 21. Performance and resource bounds

Implementation pre-indexes canonical words, word timings, and caption groups
once, and extracts the visual-grammar inventory once. Required complexity is:

```text
time: O(W + G + P + I + output_bytes)
memory: O(W + G + P + I + output_bytes)
```

where `W` is canonical words, `G` caption groups, `P` visual grammar entries,
and `I` intents. No per-intent full word/group/policy scan, quadratic overlap
check, regex over narration, recursive search, unbounded cache, blocking I/O,
thread, or subprocess is allowed. Registry lookup is in-memory and bounded.
The private weak registry releases entries when artifacts are collected.

## 22. Backward compatibility and non-claims

This candidate is additive. It changes no accepted narration, AudioArtifact,
AlignmentRequest, AdapterExecution, TimingOriginEvidence, AlignmentResult,
WordTiming, CaptionGroup, CaptionGroupsArtifact, Domain Pack schema, policy
snapshot, canonical JSON, stable issue code, golden byte, or identity.

Existing Phase 1 `text_emphasis_events` envelopes are not migrated, aliased,
or accepted as this artifact. Legacy `v2` seconds/frame behavior is not used.

The contract is multi-domain-ready core plus Domain Pack-owned visual grammar.
It adds no `business-tech` Python branch and does not implement other domain
packs. It does not claim planner trust, visual quality, persisted
`timing/emphasis_events.json`, frame accuracy, collision safety, renderer
readiness, production readiness, Phase 2 acceptance, or Phase 2 closure.

## 23. Acceptance and future authorization gates

Before specification acceptance:

1. manual structural, policy, and exact-golden verification must pass;
2. an independent read-only adversarial audit must report all findings by
   severity;
3. every blocking finding must be repaired and independently re-audited;
4. final SHA-256 and UTF-8 byte length must be recorded;
5. the exact candidate commit must be normally pushed and remote closed; and
6. authoritative status documents must be synchronized in a separate bounded
   documentation task.

Acceptance, if later recorded, permits only a separate read-only
implementation-authorization decision. It does not itself authorize code,
tests, Domain Pack edits, or artifact publication.

```text
SPECIFICATION_STATUS=CANDIDATE
SPECIFICATION_DRAFTED=YES
SPECIFICATION_ACCEPTED=NO
IMPLEMENTATION_AUTHORIZED=NO
NEXT_ACTION=INDEPENDENT_READ_ONLY_SPECIFICATION_AUDIT
PHASE2_CLOSED=NO
TOTAL_PHASE2_SLICE_COUNT=UNKNOWN
PHASE2_COMPLETION_PERCENTAGE=NOT_STATED
```
