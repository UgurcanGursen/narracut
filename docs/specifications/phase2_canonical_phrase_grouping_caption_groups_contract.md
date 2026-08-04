# Phase 2 Canonical Phrase Grouping and Caption Groups Contract

## 1. Status and authority

Status: Candidate specification

Accepted: No

Implementation authorized: No

Phase 2 closed: No

This document is the bounded candidate selected by
`baseline/phase2_canonical_phrase_grouping_caption_groups_specification_path_decision_report.md`.
It is subordinate to `docs/MASTER_ROADMAP.md` and defines only the canonical
phrase-grouping artifact represented by `timing/caption_groups.json`.

The official total Phase 2 Slice count remains unknown. This document assigns
no Slice number and states no completion percentage.

## 2. Bounded purpose

The contract deterministically converts one genuine current canonical
narration revision and one genuine accepted successful `AlignmentResult` into
an immutable caption-group artifact. It provides:

- a complete, contiguous, order-preserving partition of every canonical word;
- sentence-bounded phrase groups;
- explicit enforcement of the roadmap's preferred 4-9-word range;
- a visible, closed exception for sentences containing only 1-3 words;
- canonical word-ID ranges and exact word-ID membership;
- group timing and confidence derived only from accepted word timings;
- deterministic display text derived only from canonical narration tokens;
- stable group and artifact identities; and
- canonical bytes suitable for the future repository artifact
  `timing/caption_groups.json`.

No caller, LLM, provider, UI, or renderer may supply group boundaries,
milliseconds, confidence, display text, identity, or fallback values.

## 3. Explicit exclusions

This contract does not define or authorize:

- production implementation or tests;
- specification acceptance or implementation authorization;
- `timing/emphasis_events.json` or emphasis policy;
- word-to-frame compilation, `start_frame`, or `end_frame`;
- caption line wrapping, font metrics, safe-area placement, V5/V6 collision
  handling, preview rendering, or `CaptionPreviewRenderer`;
- `AlignmentReport`, thresholds, quality decisions, failure artifacts, or
  manual correction workflows;
- provider execution, TTS, forced alignment, network, API, retry, queue,
  payment, database, cache, filesystem publication, Studio API, or UI behavior;
- Phase 3 rendering, EDL integration, or Phase 2 closure.

The contract produces semantic caption groups, not presentation layout.

## 4. Terminology and invariants

**Canonical word** means an exact `CanonicalWord` in
`NarrationRevision.canonical_words`.

**Accepted word timing** means the corresponding exact `WordTiming` in a
genuine materialized `AlignmentResult` whose current canonical bytes and
identity still validate.

**Sentence word run** means the maximal contiguous canonical-word subsequence
sharing one genuine narration `sentence_id`.

**Caption group** means one non-empty half-open canonical-word range entirely
inside one sentence word run.

**Complete partition** means:

1. the first group starts at canonical word ordinal zero;
2. each group's exclusive end equals the next group's start;
3. the final exclusive end equals the canonical word count;
4. every canonical word appears in exactly one `word_ids` tuple; and
5. group and word order are never changed.

No gap, overlap, duplication, omission, reorder, cross-revision reference, or
cross-sentence group is valid.

## 5. Future paths and import direction

Candidate future implementation paths are descriptive, not authorized:

```text
engine/contracts/caption_groups.py
tests/test_caption_groups.py
engine/contracts/__init__.py   # mechanical additive export only
```

Permitted import direction is:

```text
engine.contracts.caption_groups
  -> engine.contracts._canonical_json
  -> engine.contracts.narration
  -> engine.contracts.alignment_result
  -> engine.contracts.alignment_execution  # ConfidenceAvailability type only
  -> engine.contracts.temporal             # stable issue inventory only
```

Forbidden imports include provider/runtime orchestration, filesystem writers,
network clients, database/cache, clocks, random generators, UI, renderer,
frame compiler, emphasis, Phase 3, and V2 modules. The contract performs no
I/O. A later artifact-lifecycle component may atomically publish the bytes to
`timing/caption_groups.json`; that publication is outside this scope.

## 6. Exact future public symbol delta

If separately authorized, the additive public surface is exactly:

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

No punctuation ranking sets, registry, hashing helper, token-selection helper,
dependency helper, or mutable builder is public.

## 7. Closed constants and enums

```python
CAPTION_GROUP_V1 = "CAPTION-GROUP-V1"
CAPTION_GROUP_HASH_V1 = "CAPTION-GROUP-HASH-V1"
CAPTION_GROUPS_V1 = "CAPTION-GROUPS-V1"
CAPTION_GROUPS_HASH_V1 = "CAPTION-GROUPS-HASH-V1"
PHRASE_GROUPING_POLICY_V1 = "PHRASE-GROUPING-POLICY-V1"

class CaptionGroupWordCountPolicy(str, Enum):
    PREFERRED_4_TO_9 = "PREFERRED_4_TO_9"
    SHORT_SENTENCE_1_TO_3 = "SHORT_SENTENCE_1_TO_3"

class CaptionGroupingRejectionReason(str, Enum):
    STRUCTURE_INVALID = "STRUCTURE_INVALID"
    UNSUPPORTED_VALUE = "UNSUPPORTED_VALUE"
    DEPENDENCY_CONTENT_DRIFT = "DEPENDENCY_CONTENT_DRIFT"
    DEPENDENCY_BINDING_INVALID = "DEPENDENCY_BINDING_INVALID"
    CANONICAL_COVERAGE_INVALID = "CANONICAL_COVERAGE_INVALID"
    GROUPING_POLICY_INVALID = "GROUPING_POLICY_INVALID"
    DISPLAY_TEXT_INVALID = "DISPLAY_TEXT_INVALID"
    TIMING_INVALID = "TIMING_INVALID"
    CONFIDENCE_INVALID = "CONFIDENCE_INVALID"
    NON_CANONICAL_SERIALIZATION = "NON_CANONICAL_SERIALIZATION"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    CONTENT_DRIFT = "CONTENT_DRIFT"
    NOT_MATERIALIZED = "NOT_MATERIALIZED"
```

Values are exact and closed. No aliases, case folding, coercion, extension
values, or unknown-enum fallback exists.

The policy's private exact boundary-token sets are:

```text
HARD_BREAK_TOKEN_TEXTS = (".", "!", "?", "…", "...", "?!", "!?", ";", ":", "—", "–")
SOFT_BREAK_TOKEN_TEXTS = (",")
TARGET_WORD_COUNT = 6
MIN_PREFERRED_WORD_COUNT = 4
MAX_PREFERRED_WORD_COUNT = 9
```

Tuple order is not a ranking. Membership is exact built-in string equality.
No locale, regex punctuation category, model judgment, or runtime configuration
may extend these sets.

## 8. Exact data models and signatures

Field order is normative:

```python
@dataclass(frozen=True)
class CaptionGroup:
    schema_version: str
    hash_scope_version: str
    caption_group_id: str
    caption_group_hash: str
    narration_revision_id: str
    alignment_result_id: str
    grouping_policy_version: str
    ordinal: int
    sentence_id: str
    start_word_ordinal: int
    end_exclusive_word_ordinal: int
    start_word_id: str
    end_word_id: str
    word_ids: tuple[str, ...]
    word_count_policy: CaptionGroupWordCountPolicy
    display_text: str
    start_ms: int
    end_ms: int
    confidence_millionths: int | None

@dataclass(frozen=True)
class CaptionGroupsArtifact:
    schema_version: str
    hash_scope_version: str
    caption_groups_id: str
    caption_groups_hash: str
    project_id: str
    document_id: str
    narration_revision_id: str
    narration_revision_hash: str
    alignment_result_id: str
    alignment_result_hash: str
    grouping_policy_version: str
    confidence_availability: ConfidenceAvailability
    caption_groups: tuple[CaptionGroup, ...]
```

All fields are required. Only `confidence_millionths` may be null. There are no
extensions. Frames, layout, coordinates, style, provider data, source-token
indices, paths, URIs, authorization evidence, issue arrays, and arbitrary
metadata are forbidden.

```python
def compile_caption_groups(
    *,
    narration_document: CanonicalNarrationDocument,
    narration_revision: NarrationRevision,
    alignment_result: AlignmentResult,
) -> CaptionGroupsArtifact

def load_caption_groups(
    source: bytes,
    *,
    narration_document: CanonicalNarrationDocument,
    narration_revision: NarrationRevision,
    alignment_result: AlignmentResult,
) -> CaptionGroupsArtifact

def serialize_caption_groups(
    artifact: CaptionGroupsArtifact,
) -> bytes
```

There is deliberately no public function accepting caller-declared boundaries
or a logical caption-group mapping. `compile_caption_groups` is the sole
producer. `load_caption_groups` accepts bytes only to verify and recover the
same deterministic artifact for the exact dependencies.

## 9. Dependency integrity preflight

Both compile and load perform the same dependency preflight before grouping or
reading loader bytes. First failure wins.

### 9.1 Exact type and provenance

Check parameters in signature order:

1. `narration_document` is the exact genuine materialized
   `CanonicalNarrationDocument`;
2. `narration_revision` is the exact genuine materialized
   `NarrationRevision`; and
3. `alignment_result` is the exact genuine materialized `AlignmentResult`.

Wrong type, subclass, proxy, copy, reconstructed dataclass, absent live
registry entry, or non-identical weak-reference owner raises sanitized
`TypeError`. No bytes are emitted.

### 9.2 Current-content reconstruction

Registry membership alone is insufficient.

1. Rebuild the exact canonical narration-document projection from current
   fields.
2. Rebuild the accepted narration-revision hash projection from current fields;
   recompute the prefixed revision hash and `narrev_` ID and compare both.
3. Invoke the accepted alignment-result serializer semantics to validate exact
   current result type, owned provenance, nested tuple fields, projection hash,
   ID, and byte equality with its immutable registry snapshot. Save a bytes
   copy and parse it strictly for subsequent comparisons.

Document drift rejects at `/narration_document`; revision drift at
`/narration_revision`; result drift at `/alignment_result`. The reason is
`DEPENDENCY_CONTENT_DRIFT`. The issue code is
`ALIGNMENT_REQUEST_IDENTITY_MISMATCH` for narration dependencies and
`REPLAY_HASH_MISMATCH` for the accepted result snapshot. No downstream
artifact is registered on failure.

The implementation may use existing private, same-package provenance helpers,
but it may not weaken or bypass any accepted upstream genuineness check.

## 10. Intrinsic dependency binding

After preflight, require in this exact order:

| Order | Equality | Pointer |
|---:|---|---|
| 1 | document project equals revision project | `/narration_document` |
| 2 | document ID equals revision document ID | `/narration_document` |
| 3 | document current revision equals revision ID | `/narration_document` |
| 4 | result project equals revision project | `/alignment_result` |
| 5 | result document equals revision document | `/alignment_result` |
| 6 | result revision ID equals revision ID | `/alignment_result` |
| 7 | result revision hash equals recomputed revision hash | `/alignment_result` |

Failure reason is `DEPENDENCY_BINDING_INVALID`; issue code is
`ALIGNMENT_REQUEST_IDENTITY_MISMATCH`. No identity is computed before all
bindings pass.

## 11. Canonical coverage and timing join

The genuine revision inventory must satisfy the accepted canonical narration
rules again from current content:

- `canonical_words` is a non-empty exact tuple of exact `CanonicalWord`;
- ordinals are exact non-boolean integers `0..N-1`;
- word IDs and token IDs are unique exact NFC stable IDs;
- each word binds to one exact `SPOKEN` text token with matching token ID,
  ordinal, text order, hierarchy IDs, display text, and source range;
- sentence hierarchy order is deterministic; words for a sentence form one
  contiguous run; and
- concatenating non-empty sentence word runs in hierarchy order yields every
  canonical word exactly once.

The genuine alignment result must contain exactly `N` timings. Timing index
`i` must have the word ID of canonical ordinal `i`. Every timing remains exact
integer/non-boolean, satisfies `0 <= start_ms < end_ms`, and the sequence
satisfies `previous.end_ms <= current.start_ms`.

Coverage, ID, order, or sentence-run failure rejects before grouping with
`CANONICAL_COVERAGE_INVALID`. Applicable issue codes are
`CANONICAL_COVERAGE_BLOCKER`, `CANONICAL_WORD_ORDER_INVALID`, or
`TRANSCRIPT_DIVERGENCE`. Timing failure uses `TIMING_INVALID` with
`ZERO_DURATION_WORD`, `TIMESTAMP_NON_MONOTONIC`, or `TIMESTAMP_OVERLAP`.

No string search, fuzzy matching, token re-alignment, omitted-word fallback,
or fabricated timing is permitted.

## 12. Deterministic phrase-grouping policy

Process sentence word runs in hierarchy order. Empty sentences produce no
group. Global caption-group ordinals start at zero and increase by one.

### 12.1 Short-sentence exception

If a complete sentence word run contains 1-3 words, emit exactly one group for
the complete run and set:

```text
word_count_policy=SHORT_SENTENCE_1_TO_3
```

This is the only below-four exception. It is explicit data, not a silent
fallback. It may not be combined with an adjacent sentence.

### 12.2 Preferred-range grouping

If a sentence contains at least four words, every emitted group must contain
4-9 words and must set:

```text
word_count_policy=PREFERRED_4_TO_9
```

At each unconsumed sentence position:

1. If the remaining word count is 4-9, consume all remaining words.
2. Otherwise enumerate candidate sizes `4, 5, 6, 7, 8, 9` whose remainder is
   either zero or at least four.
3. For each candidate, inspect only punctuation tokens after its last word and
   before the next word in the same sentence. Boundary rank is `0` if any token
   display text is in `HARD_BREAK_TOKEN_TEXTS`, else `1` if any is in
   `SOFT_BREAK_TOKEN_TEXTS`, else `2`.
4. Choose the unique minimum tuple:

```text
(boundary_rank, abs(candidate_size - 6), -candidate_size)
```

5. Emit that group and continue from its exclusive end.

Candidate sizes are unique, so the tuple gives a unique winner. The remainder
guard proves a 1-3-word tail cannot occur. Every sentence length of at least
four is representable by sizes 4-9; therefore there is no merge-across-sentence
fallback and no ungrouped tail.

Punctuation influences only a choice among valid 4-9-word boundaries. It never
changes word order, sentence ownership, timing, or coverage.

## 13. Exact display-text derivation

Display text is derived after boundaries and cannot affect grouping.

For each group, define its sentence-local text-token interval:

- lower bound is the sentence's first token text order for the first group in
  that sentence; otherwise it is the first group word's text order;
- upper bound is the next group's first word text order, or one past the
  sentence's final token text order for the final group.

Within that interval:

1. retain exact `SPOKEN` and `PUNCTUATION` tokens in increasing text order;
2. exclude every `NON_SPOKEN` token and never copy its display text;
3. require retained spoken-token IDs to equal the group's word token IDs in
   exact order;
4. start with the first retained token's exact `display_text`;
5. between adjacent retained tokens, inspect the canonical source slice from
   the previous `source_end` to the next `source_start`; append one ASCII space
   iff that slice contains at least one of U+0009, U+000A, U+000D, or U+0020,
   then append the next token's `display_text`;
6. append no source character other than that single derived separator; and
7. require the final string to be non-empty built-in NFC text without
   surrogate, noncharacter, C0, C1, or DEL code points.

Punctuation between two groups attaches to the preceding group. Leading
punctuation at sentence start attaches to its first group; trailing punctuation
attaches to its final group. Authorized canonical narration display text may
legitimately resemble a URI or path and is not silently removed. Errors never
echo that text. Source text, normalized alignment text, non-spoken instructions,
trace references, and extensions are not serialized.

Failure reason is `DISPLAY_TEXT_INVALID`; issue code is
`CANONICAL_COVERAGE_BLOCKER` when token coverage is wrong, otherwise null.

## 14. Derived word ranges, timing, and confidence

For a group covering half-open ordinals `[start, end)`:

```text
start_word_ordinal = start
end_exclusive_word_ordinal = end
start_word_id = canonical_words[start].word_id
end_word_id = canonical_words[end - 1].word_id
word_ids = canonical_words[start:end].word_id in exact order
start_ms = word_timings[start].start_ms
end_ms = word_timings[end - 1].end_ms
```

`start_ms` and `end_ms` include natural gaps between words but are never padded,
rounded, interpolated, frame-converted, or rewritten.

Confidence derives from the exact root availability:

- `AVAILABLE`: every covered word confidence must be an exact integer in
  `[0, 1_000_000]`; group confidence is their minimum.
- `UNAVAILABLE`: every covered word confidence and group confidence is null.
- `NOT_APPLICABLE`: every covered word confidence and group confidence is
  null.

Mixed null/non-null confidence, floats, booleans, strings, percentages,
averages, defaults, and thresholds are forbidden. Failure reason is
`CONFIDENCE_INVALID`, using `CONFIDENCE_REQUIRED_UNAVAILABLE` or
`ADAPTER_PRECISION_OVERSTATED` as applicable.

## 15. Group identity

Each group projection contains every `CaptionGroup` field except
`caption_group_id` and `caption_group_hash`. Dependency IDs and policy version
are intentionally repeated so a group identity cannot be transplanted across
revision, alignment result, or policy.

```text
caption_group_hash = lowercase_hex(SHA256(canonical_group_projection_bytes))
caption_group_id = "cgrp_" + caption_group_hash[0:32]
```

Hash is checked before ID. Group ordinal and all derived display/timing/
confidence fields participate in identity. Two textually identical phrases at
different positions therefore have distinct identities.

## 16. Artifact identity and canonical serialization

The artifact projection contains every `CaptionGroupsArtifact` field except
`caption_groups_id` and `caption_groups_hash`, including complete group
envelopes in ordinal order.

```text
caption_groups_hash = lowercase_hex(SHA256(canonical_artifact_projection_bytes))
caption_groups_id = "cgs_" + caption_groups_hash[0:32]
```

`encode_canonical_json_bytes` rules apply: UTF-8, no BOM, no trailing newline
or insignificant whitespace, unique keys, keys sorted by Unicode code point,
semantic array order, exact minimal base-10 integers, and no floats, exponent,
NaN, infinity, or negative zero. Strings are exact NFC and use the accepted
forbidden-code-point rules.

Logical objects parsed by the loader are exact built-in `dict`; arrays are
exact built-in `list`. Subclasses, arbitrary mappings/sequences, tuples,
iterators, and coercible values are rejected. Construction converts validated
lists to tuples and retains no caller container.

`load_caption_groups` first completes dependency preflight, then strictly
parses source bytes with duplicate-key, UTF-8, number, key, and container
checks. It derives the expected artifact independently from dependencies and
requires every declared field, group projection hash/ID, root projection
hash/ID, and final source byte to equal the deterministic result. A canonical
but different grouping cannot load.

## 17. Mutation resistance and publication registry

The private artifact registry is keyed by `id(artifact)` and stores:

```text
(weakref.ref(exact_artifact), exact_canonical_envelope_bytes)
```

Registration is transactional and collision-safe. It occurs only after full
derivation, identity, canonical-byte, and current-dependency validation. A
cleanup callback removes only the entry still owned by its exact weakref.

`serialize_caption_groups` requires exact type, live identical owner, exact
registry snapshot, valid current nested tuples/enums/scalars, recomputed group
hashes/IDs, recomputed root hash/ID, and byte equality with the stored snapshot.
Any drift rejects at `/` with `CONTENT_DRIFT` and emits nothing.

Copy, deep copy, pickle, `dataclasses.replace`, direct construction,
`object.__new__`, subclass, proxy, reconstruction, and field cloning never
transfer provenance. `object.__setattr__` cannot create publishable bytes.

## 18. Error contract, pointers, and no-leak behavior

```python
class CaptionGroupsContractError(ValueError):
    pointer: str
    reason: CaptionGroupingRejectionReason
    issue_code: str | None
```

Messages are exactly:

```text
Caption groups rejected: <REASON_VALUE>
```

Allowed pointers are closed:

```text
/
/narration_document
/narration_revision
/alignment_result
/caption_groups
/caption_groups/<decimal-index>
```

Decimal indices are implementation-generated. Unknown or attacker-authored key
text never appears in a pointer or message. Missing/unknown fields use the
containing-object pointer. Errors never contain canonical narration text,
display text, non-spoken text, provider data, hashes supplied by an attacker,
paths, URIs, credentials, environment values, raw exceptions, or repr output.

Wrong/non-genuine dependencies raise sanitized `TypeError`. Internal
construction/registry failure raises sanitized `RuntimeError`. Contract errors
carry no identity, bytes, or failure artifact. Publication is `NONE` for every
failure.

Only existing stable issue codes are used:

```text
ADAPTER_PRECISION_OVERSTATED
ALIGNMENT_REQUEST_IDENTITY_MISMATCH
CANONICAL_COVERAGE_BLOCKER
CANONICAL_WORD_ORDER_INVALID
CONFIDENCE_REQUIRED_UNAVAILABLE
REPLAY_HASH_MISMATCH
TIMESTAMP_NON_MONOTONIC
TIMESTAMP_OVERLAP
TRANSCRIPT_DIVERGENCE
UNSUPPORTED_CONTRACT_ENUM
WORD_RANGE_OUT_OF_BOUNDS
WORD_RANGE_REVERSED
WORD_RANGE_REVISION_MISMATCH
ZERO_DURATION_WORD
```

No stable issue inventory delta is introduced.

## 19. Deterministic validation precedence

First failure is authoritative:

1. dependency exact type/genuineness in signature order;
2. document, revision, then alignment-result current-content integrity;
3. loader bytes/UTF-8/JSON/canonical syntax, when loading;
4. dependency bindings in section 10 order;
5. narration word, hierarchy, sentence-run, and token coverage;
6. alignment-result word-ID coverage, time order, then confidence mode;
7. deterministic boundaries sentence by sentence;
8. display-token coverage and display-text derivation group by group;
9. derived range, timing, confidence, and word-count-policy fields;
10. group projection hash then group ID in ordinal order;
11. root fields, confidence literal, and exact group list;
12. root projection hash then root ID;
13. full canonical envelope and loader source-byte equality;
14. transactional registry publication.

Within a parsed object, unknown keys win before missing keys; field-order type
checks then follow the model order in section 8. Within arrays, lower index
wins. A loader source with multiple faults never masks an earlier dependency
or stage failure.

### 19.1 Minimum rejection oracle

| Fault | Pointer | Reason | Issue code |
|---|---|---|---|
| narration dependency drift | `/narration_revision` | `DEPENDENCY_CONTENT_DRIFT` | `ALIGNMENT_REQUEST_IDENTITY_MISMATCH` |
| alignment-result snapshot drift | `/alignment_result` | `DEPENDENCY_CONTENT_DRIFT` | `REPLAY_HASH_MISMATCH` |
| project/document/revision mismatch | `/alignment_result` | `DEPENDENCY_BINDING_INVALID` | `ALIGNMENT_REQUEST_IDENTITY_MISMATCH` |
| missing/extra/reordered word timing | `/alignment_result` | `CANONICAL_COVERAGE_INVALID` | `CANONICAL_COVERAGE_BLOCKER` |
| overlapping word timing | `/alignment_result` | `TIMING_INVALID` | `TIMESTAMP_OVERLAP` |
| unsupported root/group enum | containing object | `UNSUPPORTED_VALUE` | `UNSUPPORTED_CONTRACT_ENUM` |
| range gap/overlap/reversal | `/caption_groups/<index>` | `CANONICAL_COVERAGE_INVALID` | `WORD_RANGE_REVERSED` or `WORD_RANGE_OUT_OF_BOUNDS` |
| group crosses sentence | `/caption_groups/<index>` | `GROUPING_POLICY_INVALID` | `CANONICAL_COVERAGE_BLOCKER` |
| preferred group outside 4-9 | `/caption_groups/<index>` | `GROUPING_POLICY_INVALID` | `WORD_RANGE_OUT_OF_BOUNDS` |
| undeclared short exception | `/caption_groups/<index>` | `GROUPING_POLICY_INVALID` | `CANONICAL_COVERAGE_BLOCKER` |
| display text differs | `/caption_groups/<index>` | `DISPLAY_TEXT_INVALID` | null |
| timing differs from endpoints | `/caption_groups/<index>` | `TIMING_INVALID` | `TIMESTAMP_NON_MONOTONIC` |
| confidence differs from minimum/null mode | `/caption_groups/<index>` | `CONFIDENCE_INVALID` | `ADAPTER_PRECISION_OVERSTATED` |
| group hash mismatch | `/caption_groups/<index>` | `IDENTITY_MISMATCH` | null |
| root hash or ID mismatch | `/` | `IDENTITY_MISMATCH` | null |
| canonical parsed content differs from derivation | first containing object | reason for first differing field | applicable code |
| non-canonical but logically equal bytes | `/` | `NON_CANONICAL_SERIALIZATION` | null |
| serialized genuine object mutated | `/` | `CONTENT_DRIFT` | null |
| direct/unregistered object serialized | `/` | `NOT_MATERIALIZED` | null |

## 20. Golden fixture `FX-CGS-01`

The golden fixture consumes the exact genuine FX-ALR-01 dependencies from the
accepted alignment-result contract. Canonical source is
`Alpha beta. Gamma delta.`. The four canonical words and timings are unchanged.

Sentence identities are:

```text
nsen_626e5f802472c1d68a83  words [0,2)
nsen_154597301f10fae98161  words [2,4)
```

Both sentences contain two words, so each emits one explicit
`SHORT_SENTENCE_1_TO_3` group. Exact group evidence is:

```text
group 0 projection length=650
group 0 hash=2bdd1bc0e985d5d45784956cb0818fb9c4333d0dea5adf907edb4cebf9e9b8fb
group 0 ID=cgrp_2bdd1bc0e985d5d45784956cb0818fb9
group 0 envelope length=797
group 0 envelope SHA-256=22e4b1a9d645a81366aa58cd26e7e10de215912926d3f3d4d78663d88c375ee4

group 1 projection length=653
group 1 hash=5b9b84abe4eba87d448e56b87ff277d6b7739a7dcef152c3098d0f289be1f613
group 1 ID=cgrp_5b9b84abe4eba87d448e56b87ff277d6
group 1 envelope length=800
group 1 envelope SHA-256=465cb62737661567909dbf918870888ba37647d57e03771dbad39282f9855808
```

Exact artifact projection bytes:

```json
{"alignment_result_hash":"1521f195a591df09edaa968d8f5fa91ed367be1c7190a3f614823d74b3cd36bb","alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","caption_groups":[{"alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","caption_group_hash":"2bdd1bc0e985d5d45784956cb0818fb9c4333d0dea5adf907edb4cebf9e9b8fb","caption_group_id":"cgrp_2bdd1bc0e985d5d45784956cb0818fb9","confidence_millionths":960000,"display_text":"Alpha beta.","end_exclusive_word_ordinal":2,"end_ms":900,"end_word_id":"nword_0cc9d55672a3cb4e9199","grouping_policy_version":"PHRASE-GROUPING-POLICY-V1","hash_scope_version":"CAPTION-GROUP-HASH-V1","narration_revision_id":"narrev_d60d7ae087efb0e309d4","ordinal":0,"schema_version":"CAPTION-GROUP-V1","sentence_id":"nsen_626e5f802472c1d68a83","start_ms":100,"start_word_id":"nword_5321ba14c2c4b28c31ab","start_word_ordinal":0,"word_count_policy":"SHORT_SENTENCE_1_TO_3","word_ids":["nword_5321ba14c2c4b28c31ab","nword_0cc9d55672a3cb4e9199"]},{"alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","caption_group_hash":"5b9b84abe4eba87d448e56b87ff277d6b7739a7dcef152c3098d0f289be1f613","caption_group_id":"cgrp_5b9b84abe4eba87d448e56b87ff277d6","confidence_millionths":920000,"display_text":"Gamma delta.","end_exclusive_word_ordinal":4,"end_ms":2300,"end_word_id":"nword_d81fe913754f8b49c296","grouping_policy_version":"PHRASE-GROUPING-POLICY-V1","hash_scope_version":"CAPTION-GROUP-HASH-V1","narration_revision_id":"narrev_d60d7ae087efb0e309d4","ordinal":1,"schema_version":"CAPTION-GROUP-V1","sentence_id":"nsen_154597301f10fae98161","start_ms":1200,"start_word_id":"nword_49e85bb034c88ef36f26","start_word_ordinal":2,"word_count_policy":"SHORT_SENTENCE_1_TO_3","word_ids":["nword_49e85bb034c88ef36f26","nword_d81fe913754f8b49c296"]}],"confidence_availability":"AVAILABLE","document_id":"nardoc_fx34","grouping_policy_version":"PHRASE-GROUPING-POLICY-V1","hash_scope_version":"CAPTION-GROUPS-HASH-V1","narration_revision_hash":"sha256:d60d7ae087efb0e309d4e3f28fedea074d15e11405046249a23b2c7bb42fe0c0","narration_revision_id":"narrev_d60d7ae087efb0e309d4","project_id":"prj_fx34","schema_version":"CAPTION-GROUPS-V1"}
```

```text
artifact projection length=2152
artifact hash=12670fe861389bfe8e25f05a126c7ea355c361c2b2848e9b02a216ed83baaec7
artifact ID=cgs_12670fe861389bfe8e25f05a126c7ea3
```

Exact artifact envelope bytes:

```json
{"alignment_result_hash":"1521f195a591df09edaa968d8f5fa91ed367be1c7190a3f614823d74b3cd36bb","alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","caption_groups":[{"alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","caption_group_hash":"2bdd1bc0e985d5d45784956cb0818fb9c4333d0dea5adf907edb4cebf9e9b8fb","caption_group_id":"cgrp_2bdd1bc0e985d5d45784956cb0818fb9","confidence_millionths":960000,"display_text":"Alpha beta.","end_exclusive_word_ordinal":2,"end_ms":900,"end_word_id":"nword_0cc9d55672a3cb4e9199","grouping_policy_version":"PHRASE-GROUPING-POLICY-V1","hash_scope_version":"CAPTION-GROUP-HASH-V1","narration_revision_id":"narrev_d60d7ae087efb0e309d4","ordinal":0,"schema_version":"CAPTION-GROUP-V1","sentence_id":"nsen_626e5f802472c1d68a83","start_ms":100,"start_word_id":"nword_5321ba14c2c4b28c31ab","start_word_ordinal":0,"word_count_policy":"SHORT_SENTENCE_1_TO_3","word_ids":["nword_5321ba14c2c4b28c31ab","nword_0cc9d55672a3cb4e9199"]},{"alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","caption_group_hash":"5b9b84abe4eba87d448e56b87ff277d6b7739a7dcef152c3098d0f289be1f613","caption_group_id":"cgrp_5b9b84abe4eba87d448e56b87ff277d6","confidence_millionths":920000,"display_text":"Gamma delta.","end_exclusive_word_ordinal":4,"end_ms":2300,"end_word_id":"nword_d81fe913754f8b49c296","grouping_policy_version":"PHRASE-GROUPING-POLICY-V1","hash_scope_version":"CAPTION-GROUP-HASH-V1","narration_revision_id":"narrev_d60d7ae087efb0e309d4","ordinal":1,"schema_version":"CAPTION-GROUP-V1","sentence_id":"nsen_154597301f10fae98161","start_ms":1200,"start_word_id":"nword_49e85bb034c88ef36f26","start_word_ordinal":2,"word_count_policy":"SHORT_SENTENCE_1_TO_3","word_ids":["nword_49e85bb034c88ef36f26","nword_d81fe913754f8b49c296"]}],"caption_groups_hash":"12670fe861389bfe8e25f05a126c7ea355c361c2b2848e9b02a216ed83baaec7","caption_groups_id":"cgs_12670fe861389bfe8e25f05a126c7ea3","confidence_availability":"AVAILABLE","document_id":"nardoc_fx34","grouping_policy_version":"PHRASE-GROUPING-POLICY-V1","hash_scope_version":"CAPTION-GROUPS-HASH-V1","narration_revision_hash":"sha256:d60d7ae087efb0e309d4e3f28fedea074d15e11405046249a23b2c7bb42fe0c0","narration_revision_id":"narrev_d60d7ae087efb0e309d4","project_id":"prj_fx34","schema_version":"CAPTION-GROUPS-V1"}
```

```text
artifact envelope length=2300
artifact envelope SHA-256=fec81a32ef81b7ac4fb785b059d1f713edb90ea91197f72cd8a22992941da942
```

Repository encoding and an independent compact sorted-key UTF-8 encoder must
produce byte-identical group projections, group envelopes, artifact projection,
and artifact envelope.

## 21. Mandatory future tests

The focused module must cover:

- exact constants, enum order/values, dataclass field order/types, signatures,
  public exports, and forbidden exports;
- genuine dependency requirements, current-content drift for every dependency,
  binding order, mutation through `object.__setattr__`, copy/proxy/subclass/
  reconstruction rejection, and no publication on any failure;
- complete canonical word/timing coverage, repeated words, sentence-run order,
  empty hierarchy sentences, punctuation/non-spoken handling, and no string
  search;
- every sentence length from 1 through at least 100, proving complete coverage,
  only the declared 1-3 exception, all other sizes 4-9, no cross-sentence group,
  and deterministic output;
- exact boundary ranking for every hard/soft/no-mark value, multiple marks,
  closing punctuation tokens, target-distance ties, and larger-size tie break;
- property/exhaustive tests showing greedy remainder safety and unique
  partition for the closed policy;
- display derivation with leading/trailing punctuation, punctuation ownership,
  whitespace/no-whitespace gaps, excluded non-spoken tokens, Unicode NFC,
  attacker text, and no error-message text leak;
- AVAILABLE/UNAVAILABLE/NOT_APPLICABLE confidence, minimum propagation, null
  rules, integer bounds, and bool/float/string rejection;
- FX-CGS-01 literal bytes, lengths, hashes, IDs, independent hash calculation,
  strict loader round trip, and two independent equivalent compilations;
- duplicate/unknown/missing keys, container subclasses, number syntax, invalid
  UTF-8, BOM, trailing bytes/newline, field-order and array-index precedence;
- group/root hash-before-ID, canonical-but-different boundary rejection,
  mutated serialized artifact rejection, registry rollback/collision/stale-ID/
  cleanup behavior, and no mutable alias retention; and
- static import direction plus absence of provider, filesystem, database,
  network, clock, random, frame, layout, preview, emphasis, renderer, UI, V2,
  and Phase 3 imports.

Golden expected constants must be literal and must not be derived through the
production projection helpers under test.

## 22. Performance and resource bounds

Implementation must pre-index hierarchy words, tokens, and boundary ranks in
one pass. Candidate evaluation is at most six constant-time choices per group.
Required complexity is:

```text
time: O(W + T)
memory: O(W + T + output_bytes)
```

where `W` is canonical word count and `T` is narration text-token count. It
must not perform quadratic rescans, recursive partition search, regex
backtracking over full narration, unbounded caches, threads, subprocesses, or
blocking I/O. The private weak registry must release entries when artifacts are
collected and must never retain dependencies or caller containers.

## 23. Backward compatibility and non-claims

This candidate is additive. It does not change accepted narration,
AudioArtifact, AlignmentRequest, AdapterExecution, TimingOriginEvidence,
AlignmentResult, WordTiming, canonical JSON, stable issue codes, or their
golden bytes and identities.

The artifact consumes exact accepted upstream objects and introduces no domain
pack conditionals. Phrase grouping remains domain-neutral core behavior;
domain-specific narrative or visual grammar does not enter this contract.

This candidate does not claim a production implementation, persisted
`timing/caption_groups.json`, layout-ready captions, renderer readiness,
production readiness, Phase 2 acceptance, or Phase 2 closure.

## 24. Acceptance and future authorization gates

Before specification acceptance:

1. manual structural and exact-golden verification must pass;
2. an independent read-only audit must report all findings by severity;
3. every blocking finding must be repaired and independently re-audited;
4. the final file SHA-256 and UTF-8 byte length must be recorded;
5. the exact candidate commit must be normally pushed and remote closed; and
6. authoritative status documents must be synchronized in a separate bounded
   documentation task.

Acceptance, if later recorded, permits only a separate implementation-
authorization decision. It does not itself authorize code or tests.

```text
SPECIFICATION_STATUS=CANDIDATE
SPECIFICATION_DRAFTED=YES
SPECIFICATION_ACCEPTED=NO
IMPLEMENTATION_AUTHORIZED=NO
PHASE2_CLOSED=NO
TOTAL_PHASE2_SLICE_COUNT=UNKNOWN
PHASE2_COMPLETION_PERCENTAGE=NOT_STATED
NEXT_REQUIRED_GATE=MANUAL_VERIFICATION_AND_INDEPENDENT_READ_ONLY_AUDIT
```
