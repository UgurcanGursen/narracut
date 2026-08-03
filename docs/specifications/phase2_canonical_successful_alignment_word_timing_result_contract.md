# Phase 2 Canonical Successful Alignment Word-Timing Result Contract

## 1. Status and authority

```text
Status: Candidate specification
Accepted: No
Implementation authorized: No
Phase 2 closed: No
```

Authority is limited to:

- `baseline/phase2_post_slice5_scope_report.md`;
- `baseline/phase2_next_bounded_candidate_specification_path_decision_report.md`;
- the closed Slice 1-5 contracts and their accepted implementations.

This candidate owns a domain-agnostic core contract. It does not change any
closed upstream contract. Later acceptance and a separate implementation
authorization decision are mandatory.

## 2. Bounded purpose

This contract defines one immutable, successful alignment result whose
canonical word timings are derived from a genuine temporal raw package and
bound to genuine closed Slice 1-5 objects. It defines:

- deterministic raw alignment-token to canonical narration `word_id` mapping;
- integer millisecond `WordTiming` values;
- confidence availability and fixed-point confidence values;
- complete coverage, ordering, bounds, and non-overlap invariants;
- canonical bytes, SHA-256 identity, derived ID, provenance, and atomic
  publication.

It is the canonical word-timing projection underpinning a future
`timing/word_timeline.json`. It is not that future file-layout contract.

## 3. Explicit exclusions

This candidate does not define provider or runtime execution, retries, queues,
network or paid-provider behavior, `FAILED` or `BLOCKED` result publication,
a failure artifact, `AlignmentReport`, quality/publication thresholds,
caption or phrase grouping, emphasis mapping, word-to-frame compilation,
`CaptionPreviewRenderer`, V5/V6 collision validation, Phase 3, UI, database,
or renderer behavior.

An LLM or a person MUST NOT generate, estimate, repair, or default any
millisecond value. No string-search, fuzzy-search, positional guess, silent
coercion, silent default, or silent repair is permitted.

## 4. Terminology and dependency roles

- **Raw package:** a genuine exact `CanonicalRawPackage` produced by the
  Slice 1 materializer.
- **Narration document and revision:** a genuine exact
  `CanonicalNarrationDocument` and `NarrationRevision` pair produced together
  by Slice 2. `NarrationRevision.canonical_words` is the only canonical word
  inventory.
- **Audio artifact:** a genuine exact `AudioArtifact` produced by Slice 3.
  Its `DecodedAudioMetadata.duration_us_numerator` and
  `duration_us_denominator` define the exact audio duration.
- **Alignment request:** a genuine exact `AlignmentRequest` produced by
  Slice 4 and bound to the raw package, narration revision, and audio artifact.
- **Adapter execution:** a genuine exact `AdapterExecution` produced by Slice
  5 and bound to the request.
- **Observation token:** one closed token object inside the raw package profile
  defined in section 8. It is validation input, not a public result model.
- **Spoken observation token:** an observation whose exact `kind` is
  `SPOKEN`.
- **Canonical word:** one `CanonicalWord`, in increasing `ordinal` order.
- **Published result:** a genuine exact `AlignmentResult` registered only
  after every validation and byte verification succeeds.

## 5. Ownership and future paths

Only a future separately authorized implementation may use these paths:

```text
engine/contracts/alignment_result.py
tests/test_alignment_result.py
engine/contracts/__init__.py
```

`alignment_result.py` owns the contract. The test file owns focused tests.
`__init__.py` only exports the public symbols. No existing upstream module may
import `alignment_result.py`; it imports the closed upstream modules.

## 6. Exact public symbol delta

The future public export delta is exactly:

```text
ALIGNMENT_RESULT_V1
ALIGNMENT_RESULT_HASH_V1
ALIGNMENT_TOKEN_OBSERVATION_V1
AlignmentTimingSource
AlignmentResultRejectionReason
WordTiming
AlignmentResult
AlignmentResultContractError
materialize_alignment_result
load_alignment_result
serialize_alignment_result
```

No other public symbol is authorized. The existing public
`ConfidenceAvailability` and `TokenKind` declarations are reused and are not
redeclared.

## 7. Constants, enums, and closed values

```python
ALIGNMENT_RESULT_V1 = "ALIGNMENT-RESULT-V1"
ALIGNMENT_RESULT_HASH_V1 = "ALIGNMENT-RESULT-HASH-V1"
ALIGNMENT_TOKEN_OBSERVATION_V1 = "ALIGNMENT-TOKEN-OBSERVATION-V1"

class AlignmentTimingSource(str, Enum):
    ADAPTER_MEASURED = "ADAPTER_MEASURED"
    REPLAY_VERIFIED = "REPLAY_VERIFIED"

class AlignmentResultRejectionReason(str, Enum):
    STRUCTURE_INVALID = "STRUCTURE_INVALID"
    UNSUPPORTED_VALUE = "UNSUPPORTED_VALUE"
    DEPENDENCY_BINDING_INVALID = "DEPENDENCY_BINDING_INVALID"
    EXECUTION_NOT_SUCCESSFUL = "EXECUTION_NOT_SUCCESSFUL"
    RAW_OBSERVATION_INVALID = "RAW_OBSERVATION_INVALID"
    TIMESTAMP_SOURCE_FORBIDDEN = "TIMESTAMP_SOURCE_FORBIDDEN"
    TRANSCRIPT_DIVERGENCE = "TRANSCRIPT_DIVERGENCE"
    MAPPING_AMBIGUOUS = "MAPPING_AMBIGUOUS"
    TIMING_INVALID = "TIMING_INVALID"
    CONFIDENCE_INVALID = "CONFIDENCE_INVALID"
    SENSITIVE_DATA = "SENSITIVE_DATA"
    NON_CANONICAL_SERIALIZATION = "NON_CANONICAL_SERIALIZATION"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    NOT_MATERIALIZED = "NOT_MATERIALIZED"
```

These declarations are alias-free and closed. Values must be exact built-in
strings; case variants, spelling variants, arbitrary Enums, and `str`
subclasses are rejected without coercion.

## 8. Closed raw observation profile

The raw package MUST have exact media type:

```text
application/vnd.kurgu.alignment-token-observation+json
```

Its already-canonicalized `payload` MUST be an exact mapping with members:

```text
schema_version: str
narration_revision_id: str
narration_revision_hash: str
normalization_profile_hash: str
timestamp_source: str
tokens: array
```

`schema_version` MUST equal `ALIGNMENT-TOKEN-OBSERVATION-V1`. Revision ID,
revision hash, and normalization profile hash MUST exactly equal the genuine
`NarrationRevision` values. `timestamp_source` MUST parse as
`AlignmentTimingSource`.

Every token mapping has this exact field set and order in the logical model:

```text
index: int
kind: str
normalized_alignment_text: str | null
start_ms: int | null
end_ms: int | null
confidence_millionths: int | null
```

`index` is an exact non-boolean integer in `[0, 2**32 - 1]`; indices are
strictly increasing and unique. `kind` is exactly one existing `TokenKind`
value.

For `SPOKEN`, normalized text is an exact, non-empty, NFC built-in string with
no surrogate, Unicode noncharacter, C0, C1, or DEL code point. `start_ms` and
`end_ms` are exact non-boolean integers. Confidence follows section 11.

For `PUNCTUATION` and `NON_SPOKEN`, normalized text, start, end, and confidence
MUST all be null. Those tokens preserve raw order but are ineligible for
mapping and never appear in the result. Canonical punctuation and non-spoken
text are likewise absent because only `NarrationRevision.canonical_words` is
eligible. Unknown token fields or kinds are rejected.

No provider payload, provider response object, credential, authorization,
URI, path, raw exception, or provider metadata may be copied into the result.

## 9. Exact immutable models

Field order is normative.

```python
@dataclass(frozen=True)
class WordTiming:
    word_id: str
    start_ms: int
    end_ms: int
    confidence_millionths: int | None
    source_token_indices: tuple[int, ...]

@dataclass(frozen=True)
class AlignmentResult:
    schema_version: str
    hash_scope_version: str
    alignment_result_id: str
    alignment_result_hash: str
    project_id: str
    document_id: str
    temporal_raw_package_hash: str
    narration_revision_id: str
    narration_revision_hash: str
    audio_artifact_id: str
    audio_artifact_hash: str
    alignment_request_id: str
    alignment_request_hash: str
    adapter_execution_id: str
    adapter_execution_hash: str
    timing_source: AlignmentTimingSource
    confidence_availability: ConfidenceAvailability
    word_timings: tuple[WordTiming, ...]
```

All fields are required and non-null except `confidence_millionths` under the
rules below. No extensions exist. In particular, `text`, `normalized_text`,
caption IDs, phrase IDs, emphasis, frames, issue sets, provider data, runtime
state, report data, failure data, paths, URIs, and authorization material are
forbidden result fields.

The exact logical materializer signatures are:

```python
def materialize_alignment_result(
    value: Mapping[str, Any],
    *,
    temporal_raw_package: CanonicalRawPackage,
    narration_document: CanonicalNarrationDocument,
    narration_revision: NarrationRevision,
    audio_artifact: AudioArtifact,
    alignment_request: AlignmentRequest,
    adapter_execution: AdapterExecution,
) -> AlignmentResult

def load_alignment_result(
    source: bytes,
    *,
    temporal_raw_package: CanonicalRawPackage,
    narration_document: CanonicalNarrationDocument,
    narration_revision: NarrationRevision,
    audio_artifact: AudioArtifact,
    alignment_request: AlignmentRequest,
    adapter_execution: AdapterExecution,
) -> AlignmentResult

def serialize_alignment_result(result: AlignmentResult) -> bytes
```

## 10. Genuine prerequisite and success binding

Dependencies are checked before reading `value` or `source`, in the parameter
order shown above. Each dependency MUST have exact runtime type and genuine
weak-registry provenance from its own materializer. A copy, deep copy,
reconstruction, `dataclasses.replace`, pickle result, proxy, subclass,
lookalike, wrong type, or collected/stale object is not genuine.

The following equalities are mandatory:

- document `project_id`, `document_id`, and `current_revision_id` bind exactly
  to the revision;
- revision project/document bind exactly to the audio artifact and request;
- audio revision ID/hash bind exactly to the revision;
- request raw hash, revision ID/hash, and audio ID/hash bind exactly to the
  supplied genuine dependencies;
- execution request ID/hash bind exactly to the supplied request;
- every corresponding result identity field equals the genuine dependency;
- raw payload revision ID/hash and normalization profile hash equal the
  revision.

Intrinsic binding checks and their first-failure pointers are exactly:

| Order | Equality | Pointer |
|---:|---|---|
| 1 | document project equals revision project | `/narration_document/project_id` |
| 2 | document ID equals revision document ID | `/narration_document/document_id` |
| 3 | document current revision equals revision ID | `/narration_document/current_revision_id` |
| 4 | audio project equals revision project | `/audio_artifact/project_id` |
| 5 | audio document equals revision document | `/audio_artifact/document_id` |
| 6 | audio revision ID equals revision ID | `/audio_artifact/narration_revision_id` |
| 7 | audio revision hash equals revision hash | `/audio_artifact/narration_revision_hash` |
| 8 | request project equals revision project | `/alignment_request/project_id` |
| 9 | request document equals revision document | `/alignment_request/document_id` |
| 10 | request raw hash equals raw package hash | `/alignment_request/temporal_raw_package_hash` |
| 11 | request revision ID equals revision ID | `/alignment_request/narration_revision_id` |
| 12 | request revision hash equals revision hash | `/alignment_request/narration_revision_hash` |
| 13 | request audio ID equals audio ID | `/alignment_request/audio_artifact_id` |
| 14 | request audio hash equals audio hash | `/alignment_request/audio_artifact_hash` |
| 15 | execution request ID equals request ID | `/adapter_execution/alignment_request_id` |
| 16 | execution request hash equals request hash | `/adapter_execution/alignment_request_hash` |

`adapter_execution.status` MUST be exact `SUCCEEDED`. `FAILED` and `BLOCKED`
cannot publish an `AlignmentResult` and produce no result ID, result hash, or
canonical result bytes.

All five genuine Slice 5 modes may publish only when status is `SUCCEEDED`.
`LOCAL`, `FREE_API`, `PAID_API`, and `MANUAL_UI` require
`ADAPTER_MEASURED`; `REPLAY` requires `REPLAY_VERIFIED`. For `MANUAL_UI`, the
mode describes human-mediated transport only: `ADAPTER_MEASURED` attests that
the imported integers were emitted by an audio aligner, not authored,
estimated, or repaired by the person or an LLM. Any other pairing or source
claim is forbidden. The result does not retain replay source objects; their
validity is already part of the genuine Slice 5 execution.

## 11. Confidence model

The root `confidence_availability` MUST equal
`adapter_execution.confidence_availability_evidence.availability`. A
successful execution always has that evidence under Slice 5.

- `AVAILABLE`: every spoken observation has an exact non-boolean integer
  `confidence_millionths` in `[0, 1_000_000]`. A word consuming multiple raw
  tokens receives the minimum consumed value.
- `UNAVAILABLE`: every spoken observation and every `WordTiming` confidence is
  null.
- `NOT_APPLICABLE`: every spoken observation and every `WordTiming` confidence
  is null; this is valid only where the genuine request capability has
  `confidence_output == "UNSUPPORTED"` as already enforced by Slice 5.

No float, decimal string, percentage string, boolean, default, interpolation,
or quality threshold is permitted. This contract records confidence; it does
not decide whether confidence is good enough to publish a later product.

## 12. Deterministic token-to-word mapping

The canonical side is the complete tuple `narration_revision.canonical_words`
sorted by the already-required contiguous `ordinal` values. The raw side is
the subsequence of `SPOKEN` observations in increasing token `index` order.
Both sequences MUST be non-empty.

The comparison key is the exact `normalized_alignment_text` string. The
contract performs no additional normalization. The raw payload's exact
`normalization_profile_hash` proves which existing narration profile produced
its normalized strings. Spoken-form overrides are therefore already reflected
in the canonical word string and are not reinterpreted here.

Supported mapping is an order-preserving partition of the complete spoken raw
sequence into one non-empty contiguous token group per canonical word. For a
word and candidate raw group, the edge exists iff concatenating the raw
normalized strings with the empty string exactly equals the canonical word's
normalized string. Every raw spoken token is consumed exactly once; no token
may be skipped, reused, reordered, or searched by position elsewhere.

The implementation MUST run dynamic programming over `(word_position,
raw_position)`, enumerate candidate group ends in increasing raw position, and
count complete supported paths with saturation at two:

- exactly one complete path: use it;
- more than one complete path: reject `DIVERGENCE_AMBIGUOUS`;
- no complete path: run the diagnostic below, then reject
  `TRANSCRIPT_DIVERGENCE` if it does not apply.

One canonical word to multiple raw tokens is supported by the same rule.
Its timing is first token `start_ms` through last token `end_ms`, its confidence
is the group minimum when available, and `source_token_indices` is the exact
non-empty tuple of consumed indices.

Many canonical words to one raw token is unsupported because the token has no
genuine per-word boundary. After no supported path, a second dynamic program
uses the same exact keys but additionally allows one raw key to equal the empty
separator concatenation of two or more consecutive canonical keys. If any
complete cover requires such an edge, reject `ADAPTER_PRECISION_OVERSTATED`.
No interval subdivision is allowed. Other zero-path cases reject
`TRANSCRIPT_DIVERGENCE`.

The computed output has exactly one `WordTiming` per canonical word, in
canonical ordinal order, with exact `word_id`. Duplicate or missing word IDs,
extra timings, reordered timings, unconsumed spoken tokens, and empty source
token tuples are forbidden. The caller-declared `word_timings` MUST equal the
computed tuple field by field; it is never an independent timing source.

## 13. Timing invariants

For every spoken observation and every published timing:

- integers are exact built-in `int`, never `bool`, subclass, float, string, or
  coerced value;
- `0 <= start_ms < end_ms`;
- exact audio bound is
  `end_ms * 1000 * duration_us_denominator <= duration_us_numerator`;
- spoken observations are ordered by index and satisfy
  `previous.end_ms <= current.start_ms`;
- published words satisfy the same non-overlap inequality;
- equality at a boundary is allowed;
- gaps before, between, or after words are allowed, are not filled, and have
  no maximum in this bounded contract;
- internal gaps among multiple tokens mapped to one word remain inside that
  word's first-start/last-end interval and are not repaired;
- zero duration, reversal, negative time, audio overflow, and overlap are
  rejected before mapping publication.

Manual and LLM-authored timestamps are forbidden. Only the raw observation
bound through the genuine request and successful execution is a timing source.

## 14. Canonical projection and envelope

The hash projection contains every `AlignmentResult` field except
`alignment_result_id` and `alignment_result_hash`. The envelope contains all
fields. `WordTiming` contains all five fields. Explicit null confidence is
retained. Arrays preserve semantic order; object members are emitted in
ascending Unicode code-point order of their exact NFC names by
`encode_canonical_json_bytes`.

Canonical encoding is UTF-8 without BOM or trailing newline, with no
insignificant whitespace. Object keys are unique. Quote and backslash use
`\"` and `\\`; U+0000-U+001F would use lowercase `\u00xx`, but controls are
rejected before publication. Strings are exact NFC. Surrogates and Unicode
noncharacters are forbidden. Integers use minimal base-10 syntax; `-0`, plus
signs, leading zeroes, fractions, exponents, NaN, and infinities are forbidden.
Booleans are not integers. Unknown fields are rejected at every level.

`load_alignment_result` accepts exact built-in `bytes`, rejects BOM,
non-UTF-8, duplicate keys, forbidden numeric syntax, and non-canonical bytes,
and then uses the same logical materialization path. After full semantic and
identity validation, source bytes MUST exactly equal the newly encoded
canonical envelope.

## 15. Identity and hash rules

```text
alignment_result_hash = lowercase_hex(
    SHA256(exact canonical hash-projection bytes)
)

alignment_result_id = "alr_" + alignment_result_hash[0:32]
```

The hash is exactly 64 lowercase hexadecimal characters with no `sha256:`
prefix. The ID is exactly 36 characters. Hash mismatch is checked before ID
mismatch. Envelope SHA-256 is verification evidence only and is not the
result identity. No upstream hash is recomputed from an ID string; genuine
objects and their stored canonical identities are required.

## 16. Error contract

```python
class AlignmentResultContractError(ValueError):
    pointer: str
    reason: AlignmentResultRejectionReason
    issue_code: str | None

    def __init__(
        self,
        pointer: str,
        reason: AlignmentResultRejectionReason,
        issue_code: str | None = None,
    ) -> None: ...
```

Its constructor accepts only an exact built-in sanitized JSON Pointer, an
exact enum member, and either null or one existing canonical member of
`STABLE_ISSUE_CODES`. Its exact public message is:

```text
Alignment result rejected: <REASON_VALUE>
```

The message and pointer never include offending values, narration text,
normalized token text, provider data, credentials, authorization material,
paths, URIs, hashes supplied by an attacker, or raw exception text. A contract
error is not serialized, has no identity, and carries no canonical bytes.

Wrong-type or non-genuine dependencies raise sanitized `TypeError` before
input access. Internal construction, encoding verification, or registry
failures propagate as sanitized `RuntimeError`; they publish nothing and are
not converted to result artifacts.

No stable issue-code inventory delta is introduced. Exact existing codes used
by this contract are:

| Condition | Existing issue code |
|---|---|
| unsupported enum literal | `UNSUPPORTED_CONTRACT_ENUM` |
| request/dependency identity mismatch | `ALIGNMENT_REQUEST_IDENTITY_MISMATCH` |
| failed or blocked execution | `ADAPTER_FAILURE` |
| manual/LLM or incompatible timing source | `LLM_TIMESTAMP_SOURCE_FORBIDDEN` |
| zero supported transcript mapping | `TRANSCRIPT_DIVERGENCE` |
| multiple supported mappings | `DIVERGENCE_AMBIGUOUS` |
| many canonical words would require one raw interval | `ADAPTER_PRECISION_OVERSTATED` |
| incomplete/duplicate word coverage | `CANONICAL_COVERAGE_BLOCKER` |
| canonical word order violation | `CANONICAL_WORD_ORDER_INVALID` |
| missing required confidence | `CONFIDENCE_REQUIRED_UNAVAILABLE` |
| confidence supplied when unavailable/not applicable or outside its range | `ADAPTER_PRECISION_OVERSTATED` |
| negative or audio-overflow timestamp | `TIMESTAMP_OUT_OF_BOUNDS` |
| reversed timestamp/order | `TIMESTAMP_NON_MONOTONIC` |
| equal start and end | `ZERO_DURATION_WORD` |
| temporal overlap | `TIMESTAMP_OVERLAP` |

Structure, canonical-byte, result hash/ID, and internal publication failures
use `issue_code=None`; no inaccurate alias is invented.

## 17. Deterministic validation and first-failure precedence

The first failing stage is authoritative. Within a field list, the listed
order is authoritative. Within unknown keys, the lexicographically first safe
key wins; an unsafe key selects its containing-object pointer.

1. Preflight the six genuine dependencies in function-parameter order without
   touching logical input.
2. For loader input only, validate exact `bytes`, BOM, strict UTF-8, JSON
   syntax, duplicate keys, and forbidden numeric syntax.
3. Require root mapping and exact root key set. Unknown beats missing; missing
   follows `AlignmentResult` field order.
4. Validate exact root scalar/container types in model field order.
5. Validate result schema and hash-scope literals, then timing-source and
   confidence enums.
6. Validate intrinsic genuine document/revision/audio/request/execution
   bindings in section 10 order.
7. Validate all declared result dependency identity fields in model order.
8. Validate successful execution status.
9. Parse the genuine raw canonical package envelope; require its exact media
   type and payload mapping.
10. Validate raw payload key set and fields in section 8 order.
11. Validate raw revision/profile bindings, then timing-source/mode pairing.
12. Validate token array presence and non-empty structure.
13. Validate each token in array order: exact key set, index, kind, normalized
    text presence/value, timestamp presence/type/range, confidence
    presence/type/range.
14. Validate strict token-index order, then spoken timestamp order,
    non-overlap, and exact audio bounds.
15. Validate canonical word inventory: non-empty, unique word IDs, contiguous
    zero-based ordinal order, and non-empty exact normalized strings.
16. Run the supported mapping path count; ambiguous wins before zero-path
    diagnostic. If zero, run the many-to-one precision diagnostic, then
    divergence.
17. Compute the complete expected `WordTiming` tuple.
18. Validate declared `word_timings` array shape and each object key/type.
19. Compare declared word count; then ID multiset coverage; then ID order;
    then start, end, confidence, and source indices against the computed tuple,
    in that exact order.
20. Scan the closed result envelope for forbidden/sensitive values and cycles;
    only the defined safe identity strings, enums, integers, nulls, and arrays
    can survive.
21. Encode the hash projection and compute SHA-256.
22. Check declared hash, then derived ID.
23. Encode the full envelope; for loader input, compare exact source bytes.
24. Construct frozen objects and independently re-encode the object envelope;
    mismatch is an internal failure.
25. Register atomically, verify genuineness, and return.

No later stage may mask an earlier failure. No stage publishes a partial
object, failure object, identity, hash, or canonical bytes.

## 18. Complete bounded error oracle

`Publication` is `NONE` for every row.

| Invalid class | Stage | Exception | Pointer | Reason | Issue code |
|---|---:|---|---|---|---|
| wrong-type/non-genuine dependency | 1 | `TypeError` | n/a | n/a | n/a |
| source not exact bytes | 2 | `AlignmentResultContractError` | `/` | `STRUCTURE_INVALID` | `None` |
| BOM or non-canonical source encoding | 2/23 | `AlignmentResultContractError` | `/` | `NON_CANONICAL_SERIALIZATION` | `None` |
| invalid UTF-8/JSON, duplicate key, float, exponent, or `-0` | 2 | `AlignmentResultContractError` | containing object or `/` | `STRUCTURE_INVALID` | `None` |
| root not mapping, unknown/missing field, wrong field type | 3/4 | `AlignmentResultContractError` | exact selected pointer | `STRUCTURE_INVALID` | `None` |
| unsupported schema/hash-scope literal | 5 | `AlignmentResultContractError` | exact field | `UNSUPPORTED_VALUE` | `UNSUPPORTED_CONTRACT_ENUM` |
| unsupported timing/confidence enum | 5 | `AlignmentResultContractError` | exact field | `UNSUPPORTED_VALUE` | `UNSUPPORTED_CONTRACT_ENUM` |
| genuine dependencies disagree | 6 | `AlignmentResultContractError` | dependency-role pointer | `DEPENDENCY_BINDING_INVALID` | `ALIGNMENT_REQUEST_IDENTITY_MISMATCH` |
| declared result dependency identity disagrees | 7 | `AlignmentResultContractError` | exact root field | `DEPENDENCY_BINDING_INVALID` | `ALIGNMENT_REQUEST_IDENTITY_MISMATCH` |
| execution `FAILED` or `BLOCKED` | 8 | `AlignmentResultContractError` | `/adapter_execution/status` | `EXECUTION_NOT_SUCCESSFUL` | `ADAPTER_FAILURE` |
| raw media type differs from the exact profile media type | 9 | `AlignmentResultContractError` | `/raw_package/media_type` | `RAW_OBSERVATION_INVALID` | `None` |
| raw payload is not a mapping | 9 | `AlignmentResultContractError` | `/raw_package/payload` | `RAW_OBSERVATION_INVALID` | `None` |
| raw payload has an unknown key | 10 | `AlignmentResultContractError` | lexicographically first safe `/raw_package/payload/<key>`, otherwise `/raw_package/payload` | `RAW_OBSERVATION_INVALID` | `None` |
| raw payload has no unknown key and is missing a required key | 10 | `AlignmentResultContractError` | first missing field in section 8 payload order | `RAW_OBSERVATION_INVALID` | `None` |
| raw payload field has the wrong exact type | 10 | `AlignmentResultContractError` | exact payload field | `RAW_OBSERVATION_INVALID` | `None` |
| raw payload schema is an unsupported exact string | 10 | `AlignmentResultContractError` | `/raw_package/payload/schema_version` | `UNSUPPORTED_VALUE` | `UNSUPPORTED_CONTRACT_ENUM` |
| raw revision/profile binding mismatch | 11 | `AlignmentResultContractError` | exact payload field | `DEPENDENCY_BINDING_INVALID` | `ALIGNMENT_REQUEST_IDENTITY_MISMATCH` |
| timing-source/mode mismatch | 11 | `AlignmentResultContractError` | `/raw_package/payload/timestamp_source` | `TIMESTAMP_SOURCE_FORBIDDEN` | `LLM_TIMESTAMP_SOURCE_FORBIDDEN` |
| tokens has the wrong exact type | 10 | `AlignmentResultContractError` | `/raw_package/payload/tokens` | `RAW_OBSERVATION_INVALID` | `None` |
| tokens array is empty | 12 | `AlignmentResultContractError` | `/raw_package/payload/tokens` | `RAW_OBSERVATION_INVALID` | `None` |
| token key set is invalid | 13 | `AlignmentResultContractError` | exact selected token pointer | `RAW_OBSERVATION_INVALID` | `None` |
| token kind has wrong exact type | 13 | `AlignmentResultContractError` | exact token kind pointer | `RAW_OBSERVATION_INVALID` | `None` |
| token kind is an unsupported exact string | 13 | `AlignmentResultContractError` | exact token kind pointer | `UNSUPPORTED_VALUE` | `UNSUPPORTED_CONTRACT_ENUM` |
| spoken normalized text invalid; non-spoken presence rule fails | 13 | `AlignmentResultContractError` | exact token field | `RAW_OBSERVATION_INVALID` | `None` |
| confidence required but null | 13 | `AlignmentResultContractError` | token confidence pointer | `CONFIDENCE_INVALID` | `CONFIDENCE_REQUIRED_UNAVAILABLE` |
| confidence forbidden or outside `[0,1000000]` | 13 | `AlignmentResultContractError` | token confidence pointer | `CONFIDENCE_INVALID` | `ADAPTER_PRECISION_OVERSTATED` |
| negative/start or end beyond audio | 13/14 | `AlignmentResultContractError` | exact time pointer | `TIMING_INVALID` | `TIMESTAMP_OUT_OF_BOUNDS` |
| start equals end | 13 | `AlignmentResultContractError` | token end pointer | `TIMING_INVALID` | `ZERO_DURATION_WORD` |
| start exceeds end or token time order reverses | 13/14 | `AlignmentResultContractError` | exact time pointer | `TIMING_INVALID` | `TIMESTAMP_NON_MONOTONIC` |
| spoken intervals overlap | 14 | `AlignmentResultContractError` | later token start pointer | `TIMING_INVALID` | `TIMESTAMP_OVERLAP` |
| canonical words empty/duplicate/missing | 15 | `AlignmentResultContractError` | `/narration_revision/canonical_words` | `TRANSCRIPT_DIVERGENCE` | `CANONICAL_COVERAGE_BLOCKER` |
| canonical ordinal/order invalid | 15 | `AlignmentResultContractError` | exact canonical word pointer | `TRANSCRIPT_DIVERGENCE` | `CANONICAL_WORD_ORDER_INVALID` |
| more than one complete supported mapping | 16 | `AlignmentResultContractError` | `/raw_package/payload/tokens` | `MAPPING_AMBIGUOUS` | `DIVERGENCE_AMBIGUOUS` |
| only a many-canonical-to-one-token cover exists | 16 | `AlignmentResultContractError` | `/raw_package/payload/tokens` | `TRANSCRIPT_DIVERGENCE` | `ADAPTER_PRECISION_OVERSTATED` |
| no complete mapping exists | 16 | `AlignmentResultContractError` | `/raw_package/payload/tokens` | `TRANSCRIPT_DIVERGENCE` | `TRANSCRIPT_DIVERGENCE` |
| declared timing count differs from canonical word count | 18 | `AlignmentResultContractError` | `/word_timings` | `TRANSCRIPT_DIVERGENCE` | `CANONICAL_COVERAGE_BLOCKER` |
| declared word ID multiset has a duplicate, missing ID, or foreign ID | 19 | `AlignmentResultContractError` | first duplicate/foreign `/word_timings/<index>/word_id`, otherwise `/word_timings` | `TRANSCRIPT_DIVERGENCE` | `CANONICAL_COVERAGE_BLOCKER` |
| declared IDs are the complete set but are reordered | 19 | `AlignmentResultContractError` | first reordered `/word_timings/<index>/word_id` | `TRANSCRIPT_DIVERGENCE` | `CANONICAL_WORD_ORDER_INVALID` |
| declared start or end differs from computed evidence | 19 | `AlignmentResultContractError` | first differing time field | `TIMING_INVALID` | `ADAPTER_PRECISION_OVERSTATED` |
| declared confidence differs from computed evidence | 19 | `AlignmentResultContractError` | first differing confidence field | `CONFIDENCE_INVALID` | `ADAPTER_PRECISION_OVERSTATED` |
| declared source indices differ from the computed group | 19 | `AlignmentResultContractError` | first differing source-indices field | `TIMING_INVALID` | `ADAPTER_PRECISION_OVERSTATED` |
| sensitive/unsafe value or cycle | 20 | `AlignmentResultContractError` | safe containing pointer | `SENSITIVE_DATA` | `None` |
| result hash mismatch | 22 | `AlignmentResultContractError` | `/alignment_result_hash` | `IDENTITY_MISMATCH` | `None` |
| result ID mismatch after correct hash | 22 | `AlignmentResultContractError` | `/alignment_result_id` | `IDENTITY_MISMATCH` | `None` |
| loader bytes are semantically valid but not canonical | 23 | `AlignmentResultContractError` | `/` | `NON_CANONICAL_SERIALIZATION` | `None` |
| serialize receives non-genuine/copy/proxy/subclass | preflight | `AlignmentResultContractError` | `/` | `NOT_MATERIALIZED` | `None` |
| construction/registry insertion/verification fails | 24/25 | `RuntimeError` or original internal exception | n/a | n/a | n/a |

For declared count failure, `/word_timings` is selected. For the first
declared member mismatch, array order then `WordTiming` field order selects the
pointer. Duplicate source indices, a non-increasing tuple, or a source index
outside that word's computed group uses the source-indices pointer and
`ADAPTER_PRECISION_OVERSTATED`.

## 19. Security and no-leak invariants

- The result serializes only closed dependency identities, timing-source and
  confidence enums, word IDs, integer timings/confidence, and token indices.
- It never serializes raw normalized strings, provider token text, provider
  payload, model/endpoint/SDK data, credentials, cookies, API tokens,
  authorization evidence, URI/path data, exception text, or runtime objects.
- Exact-key validation prevents hidden extension channels.
- Error messages are category-only; pointers use only static safe field names
  and decimal array indices.
- Input mappings are not retained. Raw package bytes are read only after all
  six dependencies are proven genuine.
- No filesystem, database, network, environment, credential store, clock,
  random source, locale, or provider call participates in validation,
  serialization, hash, or publication.

Narration text is resolved later through the bound revision; it is deliberately
not duplicated in this result.

## 20. Immutability, genuine registry, and atomic publication

`WordTiming` and `AlignmentResult` are exact frozen dataclasses. All incoming
sequences become tuples; no caller mapping/list is retained. Canonical bytes,
if privately cached, are immutable bytes and are never accepted as provenance
for another object.

The implementation owns a private weak registry keyed by `id(result)` whose
value is a `weakref.ref` to the exact object. Genuineness requires exact
`AlignmentResult` type, a present registry entry, and `entry() is result`.
The weakref cleanup callback deletes the key only when the current registry
value is the callback's own weakref. Collection of an old object therefore
cannot remove a replacement entry after identity reuse.

Publication is transactional:

1. complete validation, hash/ID checks, construction, and canonical
   re-encoding happen before registration;
2. insert one weakref entry;
3. verify exact genuineness;
4. if insertion or verification raises or verification is false, delete only
   the just-inserted owned entry, preserve any unrelated/replacement entry,
   publish nothing, and propagate a sanitized internal failure;
5. return only after verification succeeds.

Copy, deep copy, pickle reconstruction, `dataclasses.replace`, direct
constructor use, `object.__new__`, subclassing, proxying, field cloning, and
mapping/envelope reconstruction do not transfer or mint provenance.
Serialization rejects all such objects. Dependency collection after successful
publication cannot alter result values or bytes; dependencies are validation
inputs and are not mutable retained state.

## 21. Golden fixture `FX-ALR-01`

This fixture is independently reproducible from existing genuine fixture
construction rules.

1. Materialize the existing FX-34 narration (`Alpha beta. Gamma delta.`) with
   `materialize_canonical_narration`. Its revision identity is:

```text
narrev_d60d7ae087efb0e309d4
sha256:d60d7ae087efb0e309d4e3f28fedea074d15e11405046249a23b2c7bb42fe0c0
normalization profile hash:
sha256:fda29f7bd8d0cc018489dcb0a7163b8130022e3bfd5e8a0cb88918c2723bb862
```

Its canonical words in order are:

```text
nword_5321ba14c2c4b28c31ab alpha
nword_0cc9d55672a3cb4e9199 beta
nword_49e85bb034c88ef36f26 gamma
nword_d81fe913754f8b49c296 delta
```

2. Generate the existing deterministic PCM WAVE fixture form with sample rate
   8000, one channel, 32000 frames, signed little-endian S16, and frame sample
   `((frame * 257 + 12345) % 65536) - 32768`. The exact file length is 64044
   bytes and media hash is:

```text
sha256:913d5cfe5fb72e8586b42cee742d3bea4da16d3e97fb158835d4cd060ae3bd72
```

Materialize it with the FX-34 revision binding. The exact audio identities and
duration are:

```text
aud_63d5743b733e34f12018
sha256:63d5743b733e34f120180d3a787d78cb0a26119395bbee1aa2e45c257713d968
duration_us_numerator=4000000
duration_us_denominator=1
```

3. The exact canonical raw payload bytes are the following single line:

```json
{"narration_revision_hash":"sha256:d60d7ae087efb0e309d4e3f28fedea074d15e11405046249a23b2c7bb42fe0c0","narration_revision_id":"narrev_d60d7ae087efb0e309d4","normalization_profile_hash":"sha256:fda29f7bd8d0cc018489dcb0a7163b8130022e3bfd5e8a0cb88918c2723bb862","schema_version":"ALIGNMENT-TOKEN-OBSERVATION-V1","timestamp_source":"ADAPTER_MEASURED","tokens":[{"confidence_millionths":980000,"end_ms":500,"index":0,"kind":"SPOKEN","normalized_alignment_text":"alpha","start_ms":100},{"confidence_millionths":960000,"end_ms":900,"index":1,"kind":"SPOKEN","normalized_alignment_text":"beta","start_ms":520},{"confidence_millionths":null,"end_ms":null,"index":2,"kind":"NON_SPOKEN","normalized_alignment_text":null,"start_ms":null},{"confidence_millionths":940000,"end_ms":1700,"index":3,"kind":"SPOKEN","normalized_alignment_text":"gamma","start_ms":1200},{"confidence_millionths":920000,"end_ms":2300,"index":4,"kind":"SPOKEN","normalized_alignment_text":"delta","start_ms":1720},{"confidence_millionths":null,"end_ms":null,"index":5,"kind":"NON_SPOKEN","normalized_alignment_text":null,"start_ms":null}]}
```

```text
payload byte length=1100
payload SHA-256=3b0400702d5472413b9428b1c852401c591f0bed71ac16978a377e7ef2775c37
raw package canonical hash=sha256:57c6fd734242b7adb82de8f32f67fea350c78d50071acca1c3e4cac95b5e2a4d
raw package canonical byte length=1397
```

4. Materialize a LOCAL request with adapter ID
`adapter_alignment_fx01`, version `1.0.0`, confidence `SUPPORTED`, network
`FORBIDDEN`, license `LOCAL`, and canonical transcript reference. Then
materialize a LOCAL/SUCCEEDED execution with confidence `AVAILABLE`:

```text
alignment request ID=arq_5a457891dd4d800258a702662852cbaa
alignment request hash=5a457891dd4d800258a702662852cbaa762ab41394f9922089bb6208badf12f9
alignment request envelope length=1197
adapter execution ID=aex_d34f77353dc56cb1b8390365e96a2733
adapter execution hash=d34f77353dc56cb1b8390365e96a2733b27f14f99eacb107bc1a24ba9e96d56d
adapter execution envelope length=684
```

5. The exact result hash-projection bytes are:

```json
{"adapter_execution_hash":"d34f77353dc56cb1b8390365e96a2733b27f14f99eacb107bc1a24ba9e96d56d","adapter_execution_id":"aex_d34f77353dc56cb1b8390365e96a2733","alignment_request_hash":"5a457891dd4d800258a702662852cbaa762ab41394f9922089bb6208badf12f9","alignment_request_id":"arq_5a457891dd4d800258a702662852cbaa","audio_artifact_hash":"sha256:63d5743b733e34f120180d3a787d78cb0a26119395bbee1aa2e45c257713d968","audio_artifact_id":"aud_63d5743b733e34f12018","confidence_availability":"AVAILABLE","document_id":"nardoc_fx34","hash_scope_version":"ALIGNMENT-RESULT-HASH-V1","narration_revision_hash":"sha256:d60d7ae087efb0e309d4e3f28fedea074d15e11405046249a23b2c7bb42fe0c0","narration_revision_id":"narrev_d60d7ae087efb0e309d4","project_id":"prj_fx34","schema_version":"ALIGNMENT-RESULT-V1","temporal_raw_package_hash":"sha256:57c6fd734242b7adb82de8f32f67fea350c78d50071acca1c3e4cac95b5e2a4d","timing_source":"ADAPTER_MEASURED","word_timings":[{"confidence_millionths":980000,"end_ms":500,"source_token_indices":[0],"start_ms":100,"word_id":"nword_5321ba14c2c4b28c31ab"},{"confidence_millionths":960000,"end_ms":900,"source_token_indices":[1],"start_ms":520,"word_id":"nword_0cc9d55672a3cb4e9199"},{"confidence_millionths":940000,"end_ms":1700,"source_token_indices":[3],"start_ms":1200,"word_id":"nword_49e85bb034c88ef36f26"},{"confidence_millionths":920000,"end_ms":2300,"source_token_indices":[4],"start_ms":1720,"word_id":"nword_d81fe913754f8b49c296"}]}
```

```text
projection byte length=1449
projection SHA-256=cb0b9bc7c59f7fd636278a75a281fcdd9703335108766cebdb2e8553e306a338
alignment_result_id=alr_cb0b9bc7c59f7fd636278a75a281fcdd
```

6. The exact canonical envelope bytes are:

```json
{"adapter_execution_hash":"d34f77353dc56cb1b8390365e96a2733b27f14f99eacb107bc1a24ba9e96d56d","adapter_execution_id":"aex_d34f77353dc56cb1b8390365e96a2733","alignment_request_hash":"5a457891dd4d800258a702662852cbaa762ab41394f9922089bb6208badf12f9","alignment_request_id":"arq_5a457891dd4d800258a702662852cbaa","alignment_result_hash":"cb0b9bc7c59f7fd636278a75a281fcdd9703335108766cebdb2e8553e306a338","alignment_result_id":"alr_cb0b9bc7c59f7fd636278a75a281fcdd","audio_artifact_hash":"sha256:63d5743b733e34f120180d3a787d78cb0a26119395bbee1aa2e45c257713d968","audio_artifact_id":"aud_63d5743b733e34f12018","confidence_availability":"AVAILABLE","document_id":"nardoc_fx34","hash_scope_version":"ALIGNMENT-RESULT-HASH-V1","narration_revision_hash":"sha256:d60d7ae087efb0e309d4e3f28fedea074d15e11405046249a23b2c7bb42fe0c0","narration_revision_id":"narrev_d60d7ae087efb0e309d4","project_id":"prj_fx34","schema_version":"ALIGNMENT-RESULT-V1","temporal_raw_package_hash":"sha256:57c6fd734242b7adb82de8f32f67fea350c78d50071acca1c3e4cac95b5e2a4d","timing_source":"ADAPTER_MEASURED","word_timings":[{"confidence_millionths":980000,"end_ms":500,"source_token_indices":[0],"start_ms":100,"word_id":"nword_5321ba14c2c4b28c31ab"},{"confidence_millionths":960000,"end_ms":900,"source_token_indices":[1],"start_ms":520,"word_id":"nword_0cc9d55672a3cb4e9199"},{"confidence_millionths":940000,"end_ms":1700,"source_token_indices":[3],"start_ms":1200,"word_id":"nword_49e85bb034c88ef36f26"},{"confidence_millionths":920000,"end_ms":2300,"source_token_indices":[4],"start_ms":1720,"word_id":"nword_d81fe913754f8b49c296"}]}
```

```text
envelope byte length=1601
envelope SHA-256=2555507a358fc0c1dfcde0ff73ba4a70f17fea0b339d45438e86350f8d35a0cb
```

The projection and envelope were independently encoded with the repository
canonical encoder and with a separate UTF-8, sorted-key, compact JSON encoder;
both methods produced byte-identical values, lengths, and SHA-256 digests.

## 22. Mandatory future test matrix

The focused future test module MUST cover:

- exact constants, enum inheritance/member order/values/no aliases, dataclass
  fields/order/types, function signatures, exports, and forbidden exports;
- genuine FX-34 narration, deterministic 4-second audio, raw package, request,
  and execution construction for `FX-ALR-01`;
- exact golden projection/envelope bytes, lengths, hash, ID, envelope SHA-256,
  two independent materializations, and load/serialize equality;
- each error-oracle row, exact stage, pointer, reason, issue code, safe message,
  publication `NONE`, and no sensitive leakage;
- multi-fault tests proving dependency preflight, unknown-before-missing,
  type-before-enum, dependency-before-execution, raw shape-before-mapping,
  timing-before-mapping, ambiguity-before zero-path diagnostic, semantic
  validation before identity, and hash-before-ID precedence;
- exact built-in type resistance for every string and integer, including bool,
  subclasses, arbitrary Enums, floats, decimal strings, and coercible objects;
- duplicate JSON keys at root and nested timing objects, BOM, invalid UTF-8,
  forbidden number syntax, Unicode/NFC/control boundaries, whitespace and
  member-order non-canonical bytes;
- every genuine dependency role with wrong type, copy, deep copy, pickle,
  replace, reconstruction, proxy, subclass, role swap, distinct genuine
  mismatch, stale registry, and collection cases;
- `SUCCEEDED` for LOCAL/REPLAY/FREE_API/PAID_API/MANUAL_UI, rejection of every
  FAILED/BLOCKED execution, MANUAL_UI transport versus timing-origin
  separation, and timing-source mode parity;
- AVAILABLE/UNAVAILABLE/NOT_APPLICABLE confidence presence, bounds `0` and
  `1000000`, out-of-range values, group-min aggregation, and capability parity;
- punctuation and non-spoken exclusion, one-to-one, one canonical to multiple
  raw tokens, forbidden many canonical to one raw token, no mapping, ambiguous
  mapping, exact-case mismatch, no fuzzy/search fallback, skipped/extra/reused
  tokens, and complete coverage;
- timing boundaries at zero and exact audio end, one millisecond duration,
  equality adjacency, arbitrary allowed gaps, negative, zero, reversed,
  overlap, audio overflow, non-monotonic indices, duplicate indices, duplicate
  word IDs, missing/extra/reordered words, and wrong source-token tuples;
- result field mutation, nested tuple mutation attempts, source input mutation,
  private projection-copy mutation, bytes-copy mutation, direct construction,
  object reconstruction, and serialize-not-genuine rejection;
- weak-registry collection cleanup, stale replacement safety, insertion
  exception rollback, verification false/exception rollback, unrelated-entry
  preservation, and no strong dependency retention;
- static import direction and proof that production has no filesystem,
  database, network, provider, clock, random, UI, frame, caption, emphasis, or
  Phase 3 dependency.

Every golden oracle is a literal test constant. Tests MUST NOT derive the
expected hash or ID by calling the production projection helper under test.

## 23. Backward compatibility and non-claims

This is an additive candidate. It does not change TRP-RAW-V1 canonicalization,
the narration hierarchy or word IDs, AudioArtifact identity/security,
AlignmentRequest, AdapterExecution, stable issue-code inventory, existing
exports, or any accepted Slice 1-5 byte/hash oracle. The raw observation
profile is a consumer profile inside the existing opaque TRP payload boundary;
it does not broaden Slice 1 validation.

This document does not claim that the candidate is accepted, implementation is
authorized, code or tests exist, the timing file is written, quality gates
pass, another Slice number exists, a total Phase 2 Slice count is known, a
completion percentage exists, or Phase 2 is closed.

## 24. Specification acceptance and future authorization gates

Before acceptance, all of the following are required:

1. manual end-to-end normative review;
2. independent read-only audit of fields, bindings, mapping, timing,
   confidence, serialization, identity, error precedence, security, registry,
   golden bytes, and test completeness;
3. bounded corrections for every material finding;
4. independent golden byte/hash recomputation;
5. exact file SHA-256 and byte-length verification;
6. a bodyless specification commit and normal remote closure;
7. consistent documentation synchronization recording acceptance only after
   those gates pass.

Acceptance permits only a separate implementation-authorization decision.
Implementation remains forbidden until that decision explicitly verifies
bounded paths, public delta, tests, regression boundary, and commit scope.

```text
SPECIFICATION_STATUS=CANDIDATE
SPECIFICATION_ACCEPTED=NO
IMPLEMENTATION_AUTHORIZED=NO
PHASE2_CLOSED=NO
NEXT_REQUIRED_GATE=INDEPENDENT_READ_ONLY_AUDIT
```
