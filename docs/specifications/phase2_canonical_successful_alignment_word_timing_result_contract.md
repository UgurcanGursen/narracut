# Phase 2 Canonical Successful Alignment Word-Timing Result Contract

## 1. Status, authority, and repair state

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

This revision repairs independent-audit findings F1-F5. It remains a candidate
pending targeted independent read-only re-audit. It does not accept the
specification, authorize implementation, assign a Slice number, or close
Phase 2.

## 2. Bounded purpose

This contract defines one immutable successful alignment result and one
repository-owned timing-origin evidence boundary. In this bounded revision,
publication is intentionally limited to an exact allowlisted `REPLAY` fixture.
It defines:

- deterministic raw alignment-token to canonical narration `word_id` mapping;
- integer millisecond `WordTiming` values;
- confidence availability and fixed-point confidence values;
- complete coverage, ordering, bounds, and non-overlap invariants;
- canonical bytes, SHA-256 identities, derived IDs, immutable provenance, and
  atomic publication.

It underpins a future `timing/word_timeline.json`; it is not that future file
layout contract.

## 3. Explicit exclusions

This candidate does not define provider/runtime execution, retries, queues,
network or paid-provider behavior, `FAILED` or `BLOCKED` result publication,
a failure artifact, `AlignmentReport`, quality thresholds, caption or phrase
grouping, emphasis mapping, word-to-frame compilation,
`CaptionPreviewRenderer`, V5/V6 collision validation, Phase 3, UI, database,
or renderer behavior.

An LLM or person MUST NOT generate, estimate, repair, or default a millisecond
value. No string search, fuzzy search, positional guess, silent coercion,
silent default, silent repair, mode downgrade, or fallback is permitted.

## 4. Terminology and trust boundary

- **Raw package:** an exact genuine `CanonicalRawPackage` from Slice 1.
- **Narration pair:** an exact genuine `CanonicalNarrationDocument` and
  `NarrationRevision` pair produced together by Slice 2.
- **Audio artifact:** an exact genuine `AudioArtifact` from Slice 3.
- **Alignment request:** an exact genuine `AlignmentRequest` from Slice 4.
- **Adapter execution:** an exact genuine `AdapterExecution` from Slice 5.
- **Timing-origin evidence:** an exact genuine `TimingOriginEvidence` loaded
  only from canonical bytes whose complete identity is in the closed
  repository allowlist in section 9.
- **Observation token:** one closed token object in section 8. It is input,
  not a public result model.
- **Canonical word:** one `CanonicalWord` in increasing ordinal order.
- **Published result:** an exact genuine `AlignmentResult` returned only after
  all validation, recomputation, snapshot, and registry checks succeed.

Slice 1 and Slice 5 genuineness proves only passage through their public
materializers. It does not prove timing origin. `TimingOriginEvidence` is the
additional bounded trust boundary. It claims repository allowlist membership,
not provider authenticity or cryptographic authorship.

## 5. Future paths and import direction

Only a future separately authorized implementation may change:

```text
engine/contracts/alignment_result.py
engine/contracts/__init__.py
tests/test_alignment_result.py
```

`alignment_result.py` owns all new declarations. `__init__.py` only exports
the exact public delta. Existing upstream modules MUST NOT import
`alignment_result.py`; it imports the closed upstream modules.

## 6. Exact public symbol delta

```text
ALIGNMENT_RESULT_V1
ALIGNMENT_RESULT_HASH_V1
ALIGNMENT_TOKEN_OBSERVATION_V1
TIMING_ORIGIN_EVIDENCE_V1
TIMING_ORIGIN_EVIDENCE_HASH_V1
AlignmentTimingSource
AlignmentResultRejectionReason
TimingOriginEvidence
WordTiming
AlignmentResult
AlignmentResultContractError
load_repository_timing_origin_evidence
materialize_alignment_result
load_alignment_result
serialize_alignment_result
```

No other public symbol is authorized. Existing `ConfidenceAvailability` and
`TokenKind` declarations are reused and not redeclared.

## 7. Constants, enums, and closed values

```python
ALIGNMENT_RESULT_V1 = "ALIGNMENT-RESULT-V1"
ALIGNMENT_RESULT_HASH_V1 = "ALIGNMENT-RESULT-HASH-V1"
ALIGNMENT_TOKEN_OBSERVATION_V1 = "ALIGNMENT-TOKEN-OBSERVATION-V1"
TIMING_ORIGIN_EVIDENCE_V1 = "TIMING-ORIGIN-EVIDENCE-V1"
TIMING_ORIGIN_EVIDENCE_HASH_V1 = "TIMING-ORIGIN-EVIDENCE-HASH-V1"

class AlignmentTimingSource(str, Enum):
    REPLAY_VERIFIED = "REPLAY_VERIFIED"

class AlignmentResultRejectionReason(str, Enum):
    STRUCTURE_INVALID = "STRUCTURE_INVALID"
    UNSUPPORTED_VALUE = "UNSUPPORTED_VALUE"
    DEPENDENCY_BINDING_INVALID = "DEPENDENCY_BINDING_INVALID"
    DEPENDENCY_CONTENT_DRIFT = "DEPENDENCY_CONTENT_DRIFT"
    EXECUTION_NOT_SUCCESSFUL = "EXECUTION_NOT_SUCCESSFUL"
    TIMING_ORIGIN_EVIDENCE_INVALID = "TIMING_ORIGIN_EVIDENCE_INVALID"
    RAW_OBSERVATION_INVALID = "RAW_OBSERVATION_INVALID"
    TIMESTAMP_SOURCE_FORBIDDEN = "TIMESTAMP_SOURCE_FORBIDDEN"
    TRANSCRIPT_DIVERGENCE = "TRANSCRIPT_DIVERGENCE"
    TIMING_INVALID = "TIMING_INVALID"
    CONFIDENCE_INVALID = "CONFIDENCE_INVALID"
    SENSITIVE_DATA = "SENSITIVE_DATA"
    NON_CANONICAL_SERIALIZATION = "NON_CANONICAL_SERIALIZATION"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    CONTENT_DRIFT = "CONTENT_DRIFT"
    NOT_MATERIALIZED = "NOT_MATERIALIZED"
```

Declarations are alias-free and closed. Enum inputs are exact built-in
strings; case variants, spelling variants, arbitrary `Enum` values, and
`str` subclasses are rejected without coercion. `ADAPTER_MEASURED` is not a
value of `AlignmentTimingSource` and cannot authorize publication.

## 8. Closed raw observation profile

The raw package media type MUST be exactly:

```text
application/vnd.kurgu.alignment-token-observation+json
```

The canonical `payload` is an exact built-in `dict` with exactly these keys:

```text
schema_version
narration_revision_id
narration_revision_hash
normalization_profile_hash
tokens
```

`timestamp_source` is forbidden. Its former string assertion is not timing
origin evidence. `schema_version` equals
`ALIGNMENT-TOKEN-OBSERVATION-V1`. Revision ID/hash and profile hash equal the
recomputed genuine revision values.

At the logical boundary `tokens` MUST be an exact built-in `list`. At the JSON
loader boundary a JSON array becomes that exact list. Tuple, arbitrary
`Sequence`, iterator, string, bytes, subclass, or coercible object is rejected.
Every token MUST be an exact built-in `dict` with exact built-in `str` keys and
exactly these fields:

```text
index
kind
normalized_alignment_text
start_ms
end_ms
confidence_millionths
```

`index` is exact built-in non-boolean `int` in `[0, 2**32 - 1]`; indices are
strictly increasing and unique. `kind` is one exact existing `TokenKind`
value.

For `SPOKEN`, normalized text is an exact non-empty NFC built-in string with
no surrogate, Unicode noncharacter, C0, C1, or DEL code point. Start/end are
exact non-boolean integers. Confidence follows section 14.

For `PUNCTUATION` and `NON_SPOKEN`, normalized text, start, end, and confidence
are all null. These tokens preserve raw order but are ineligible for mapping
and never appear in the result.

## 9. Timing-origin evidence model and producer

Field order is normative:

```python
@dataclass(frozen=True)
class TimingOriginEvidence:
    schema_version: str
    hash_scope_version: str
    timing_origin_evidence_id: str
    timing_origin_evidence_hash: str
    fixture_id: str
    temporal_raw_package_hash: str
    timing_payload_byte_hash: str
    narration_document_snapshot_hash: str
    narration_revision_id: str
    narration_revision_hash: str
    audio_artifact_id: str
    audio_artifact_hash: str
    alignment_request_id: str
    alignment_request_hash: str
    adapter_execution_id: str
    adapter_execution_hash: str
```

The hash projection contains every field except evidence ID/hash. Canonical
projection SHA-256 is 64 lowercase hexadecimal characters without a prefix:

```text
timing_origin_evidence_hash = lowercase_hex(SHA256(projection_bytes))
timing_origin_evidence_id = "toe_" + timing_origin_evidence_hash[0:32]
```

The only constructor boundary is:

```python
def load_repository_timing_origin_evidence(source: bytes) -> TimingOriginEvidence
```

There is no public logical materializer. `source` MUST be exact built-in
`bytes`. The loader performs strict UTF-8/JSON/canonical validation, exact
root-field validation, projection hash then ID verification, and finally
requires this exact tuple in the private immutable allowlist:

```text
(
  fixture_id="FX-ALR-01",
  timing_origin_evidence_hash=
    "f140843e7e1f86817c7acc0bdc8eb775021ffd8c5a5a13809d5e33407c34ae03",
  canonical_envelope_sha256=
    "11ba9218006576fc87f0bcac1bf7cbe808dcdfc78a3fa3f957e97918960628a9",
  canonical_envelope_byte_length=1206,
  canonical_timing_payload_sha256=
    "86497808c046ec4334395f23eaef5a8e9976780af61a2ec7278ade6137d0b0ad",
  canonical_timing_payload_byte_length=1062,
)
```

Allowlist comparison uses all six values. The allowlist entry also owns the
exact immutable canonical timing payload bytes printed in section 20; those
bytes are not caller input and their digest and length MUST equal the last two
tuple members. Only after all comparisons succeed is the frozen object
constructed and registered. Direct construction, a copied object, or
canonical bytes absent from this exact allowlist is not trusted. The private
evidence registry stores `(weakref, exact canonical evidence envelope bytes,
exact canonical timing payload bytes)` and verifies object identity and both
immutable byte snapshots. No public API accepts replacement timing payload
bytes.

This bounded producer accepts only repository-owned committed fixture bytes.
It makes no provider-authenticity claim. Adding another fixture or a trusted
runtime producer requires a later accepted specification change; it cannot be
done by configuration, environment, caller input, or silent allowlist growth.

## 10. Result models and signatures

Field order is normative:

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
    timing_origin_evidence_id: str
    timing_origin_evidence_hash: str
    timing_source: AlignmentTimingSource
    confidence_availability: ConfidenceAvailability
    word_timings: tuple[WordTiming, ...]
```

All fields are required and non-null except `confidence_millionths`. No
extensions exist. Result text, normalized text, captions, phrases, emphasis,
frames, issue sets, provider/runtime/report/failure data, paths, URIs, and
authorization material are forbidden.

```python
def materialize_alignment_result(
    value: dict[str, Any],
    *,
    temporal_raw_package: CanonicalRawPackage,
    narration_document: CanonicalNarrationDocument,
    narration_revision: NarrationRevision,
    audio_artifact: AudioArtifact,
    alignment_request: AlignmentRequest,
    adapter_execution: AdapterExecution,
    timing_origin_evidence: TimingOriginEvidence,
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
    timing_origin_evidence: TimingOriginEvidence,
) -> AlignmentResult

def serialize_alignment_result(result: AlignmentResult) -> bytes
```

Logical root and every nested object MUST be exact built-in `dict`; every
logical array MUST be exact built-in `list`. Arbitrary `Mapping`, tuple,
`Sequence`, iterator, subclass, string, bytes, and coercible containers are
rejected. Successful construction converts only validated lists to tuples and
never retains caller containers.

## 11. Exact dependency integrity preflight

Before reading logical `value` or loader `source`, preflight checks these seven
parameters in signature order. Wrong runtime type or absent genuine registry
entry raises sanitized `TypeError`. For every genuine object, current content
is then independently reserialized and its identity recomputed; registry
membership alone is insufficient.

1. **Raw package:** read the actual `canonical_bytes` and `canonical_hash`
   fields; require `canonical_bytes` to be exact built-in envelope bytes,
   strict canonical parse and byte-identical re-encoding; recompute the
   `sha256:` envelope hash and compare it to `canonical_hash`. Retrieve timing
   payload bytes exclusively from the genuine
   evidence registry snapshot, require exact built-in bytes, strict canonical
   parse and byte-identical re-encoding, and recompute `sha256:` payload hash.
   Canonically encode the raw envelope's `payload` member and require it to be
   byte-identical to that private payload snapshot. The raw envelope
   `payload_byte_hash`, evidence
   `timing_payload_byte_hash`, allowlist payload digest/length, and recomputed
   payload digest/length MUST all agree. No payload absent from the private
   snapshot is accepted and no caller-supplied payload source exists.
2. **Narration document:** encode exactly `schema_version`, `project_id`,
   `document_id`, `current_revision_id`, `language`, `locale`, `title`, and
   thawed `extensions`; compute prefixed SHA-256 and compare to evidence
   `narration_document_snapshot_hash`.
3. **Narration revision:** reconstruct the accepted Slice 2 revision hash
   projection from the actual fields `schema_version`, `hash_scope_version`,
   `project_id`, `document_id`, `parent_revision_id`, `source_byte_hash`,
   `source_text`, `normalization_profile`, `text_tokens` without extensions,
   `canonical_words`, `sections` without extensions, and `lineage_manifest`.
   Recompute prefixed revision hash and `narrev_` ID. Compare stored values and
   evidence. Revision/document extensions remain outside revision identity as
   required by Slice 2.
4. **Audio artifact:** reconstruct the accepted Slice 3 projection from
   `schema_version`, `hash_scope_version`, project/document/revision identity
   fields, `media_byte_hash`, `logical_input`, and `decoded_metadata`;
   `extensions` are excluded. Recompute prefixed hash and `aud_` ID and
   compare stored values and evidence.
5. **Alignment request:** reconstruct the accepted Slice 4 projection from
   every field except request ID/hash; recompute bare hash and `arq_` ID and
   compare stored values and evidence.
6. **Adapter execution:** reconstruct the accepted Slice 5 projection from
   every field except execution ID/hash; recompute bare hash and `aex_` ID and
   compare stored values and evidence.
7. **Timing-origin evidence:** re-encode every field, compare to its registry
   evidence byte snapshot, recompute projection hash then ID, recompute
   envelope digest and length, re-hash and remeasure its private timing payload
   snapshot, and repeat exact six-value allowlist membership.

The first content drift uses the parameter-order pointer:

| Dependency | Fixed pointer | Reason | Existing stable issue code |
|---|---|---|---|
| raw package | `/temporal_raw_package` | `DEPENDENCY_CONTENT_DRIFT` | `REPLAY_HASH_MISMATCH` |
| narration document | `/narration_document` | `DEPENDENCY_CONTENT_DRIFT` | `ALIGNMENT_REQUEST_IDENTITY_MISMATCH` |
| narration revision | `/narration_revision` | `DEPENDENCY_CONTENT_DRIFT` | `ALIGNMENT_REQUEST_IDENTITY_MISMATCH` |
| audio artifact | `/audio_artifact` | `DEPENDENCY_CONTENT_DRIFT` | `ALIGNMENT_REQUEST_IDENTITY_MISMATCH` |
| alignment request | `/alignment_request` | `DEPENDENCY_CONTENT_DRIFT` | `ALIGNMENT_REQUEST_IDENTITY_MISMATCH` |
| adapter execution | `/adapter_execution` | `DEPENDENCY_CONTENT_DRIFT` | `REPLAY_HASH_MISMATCH` |
| timing evidence | `/timing_origin_evidence` | `TIMING_ORIGIN_EVIDENCE_INVALID` | `REPLAY_HASH_MISMATCH` |

No mapping, status, payload, result identity, or canonical result bytes are
computed before this preflight succeeds. Snapshots are immutable local values;
no cached mutable projection or caller alias is trusted.

## 12. Binding and success-only publication

After integrity preflight, exact equalities are checked in this order:

| Order | Equality | Fixed pointer |
|---:|---|---|
| 1 | document project equals revision project | `/narration_document/project_id` |
| 2 | document ID equals revision document ID | `/narration_document/document_id` |
| 3 | current revision equals revision ID | `/narration_document/current_revision_id` |
| 4 | audio project/document/revision ID/hash equal revision | `/audio_artifact` |
| 5 | request project/document/raw/revision/audio identities equal dependencies | `/alignment_request` |
| 6 | execution request ID/hash equal request | `/adapter_execution` |
| 7 | evidence raw/payload/document/revision/audio/request/execution fields equal snapshots | `/timing_origin_evidence` |
| 8 | declared result dependency/evidence identities equal dependencies | `/` |

Rows 4-8 use their fixed containing pointer; attacker values never appear in
a pointer. Binding failure reason is `DEPENDENCY_BINDING_INVALID` and issue
code is `ALIGNMENT_REQUEST_IDENTITY_MISMATCH`, except row 7 uses
`REPLAY_INPUT_MISMATCH`.

`adapter_execution.status` MUST be exact `SUCCEEDED`, and mode MUST be exact
`REPLAY`. `FAILED` and `BLOCKED` publish nothing. `LOCAL`, `FREE_API`,
`PAID_API`, and `MANUAL_UI` successful executions are deterministically
rejected at `/adapter_execution/mode` with
`TIMESTAMP_SOURCE_FORBIDDEN` / `LLM_TIMESTAMP_SOURCE_FORBIDDEN`. No mode is
downgraded or translated to `REPLAY`.

The request mode and capability mode MUST also be `REPLAY`. Execution replay
evidence remains subject to the recomputed Slice 5 identity. Root
`timing_source` MUST be `REPLAY_VERIFIED`; it is derived from the allowlisted
evidence and not from raw payload text.

## 13. Deterministic token-to-word mapping and uniqueness

The canonical side is the complete non-empty
`narration_revision.canonical_words` tuple in contiguous ordinal order. The
raw side is the non-empty `SPOKEN` subsequence in increasing token-index order.
The comparison key is exact `normalized_alignment_text`; no additional
normalization occurs.

Every canonical word has an exact non-empty built-in NFC `word_id` and
`normalized_alignment_text`, with the same forbidden-code-point rules as a
spoken raw key. Its `ordinal` is an exact non-boolean integer, starts at zero,
and increases by one. These checks precede mapping and make every canonical
and raw comparison key non-empty.

Supported mapping is an order-preserving partition of the complete spoken raw
sequence into one non-empty contiguous group per canonical word. An edge
exists iff concatenating the raw keys with the empty separator exactly equals
the canonical word key. Every spoken token is consumed exactly once.

The mapping is unique whenever it exists. Proof: each raw key is non-empty, so
the concatenated code-point length strictly increases as a candidate group end
advances. For a fixed canonical key, at most one candidate end can have equal
length and exact value. Induction over canonical words therefore gives at
most one complete partition. No ambiguity-counting branch exists and this
contract never emits `DIVERGENCE_AMBIGUOUS`.

The implementation walks words and candidate group ends in increasing order.
Exactly one cover is used. If no cover exists, a diagnostic dynamic program
additionally allows one raw key to equal two or more consecutive canonical
keys. If a complete cover requiring such an edge exists, reject
`ADAPTER_PRECISION_OVERSTATED`; otherwise reject `TRANSCRIPT_DIVERGENCE`.
No interval subdivision is allowed.

Repeated words remain unique by consumed prefix. Punctuation/non-spoken tokens
are excluded before mapping. Missing, extra, case-different, Unicode-different,
skipped, reordered, or incompatible split/merge keys produce one of the two
zero-cover outcomes. No text-search fallback exists.

One canonical word may consume multiple raw tokens. Its timing is the first
token start through last token end, confidence is the minimum consumed value
when available, and `source_token_indices` is the exact consumed-index tuple.
The output has exactly one `WordTiming` per canonical word in ordinal order.
Caller-declared `word_timings` MUST equal this computed tuple field by field.

## 14. Timing and confidence invariants

For every spoken observation and published timing:

- integers are exact built-in `int`, never boolean, subclass, float, string,
  or coerced value;
- `0 <= start_ms < end_ms`;
- exact audio bound is
  `end_ms * 1000 * duration_us_denominator <= duration_us_numerator`;
- token order satisfies `previous.end_ms <= current.start_ms`;
- published word order satisfies the same inequality;
- equality adjacency is allowed;
- gaps before, between, and after words are allowed and are not filled;
- internal gaps in a multi-token word remain inside first-start/last-end;
- negative, zero-duration, reversed, overflow, and overlap inputs fail before
  mapping publication.

Root confidence equals successful execution confidence evidence:

- `AVAILABLE`: every spoken confidence is exact integer `[0, 1_000_000]`;
  grouped word confidence is the minimum.
- `UNAVAILABLE`: all spoken and result confidence values are null.
- `NOT_APPLICABLE`: all are null and request capability confidence output is
  exact `UNSUPPORTED`.

No float, percentage, decimal string, default, interpolation, threshold, or
manual/LLM timestamp is permitted.

## 15. Canonical serialization and identity

Result hash projection contains every result field except result ID/hash.
Evidence hash projection follows section 9. Full envelopes contain all fields.
`WordTiming` contains all five fields and explicit null confidence is retained.

`encode_canonical_json_bytes` rules apply: UTF-8, no BOM/trailing newline or
insignificant whitespace, unique keys, object keys in ascending Unicode
code-point order, semantic array order, exact NFC strings, minimal base-10
integers, and no float, exponent, NaN, infinity, negative zero, surrogate,
noncharacter, C0, C1, or DEL value.

```text
alignment_result_hash = lowercase_hex(SHA256(result_projection_bytes))
alignment_result_id = "alr_" + alignment_result_hash[0:32]
```

The hash is checked before ID. Envelope SHA-256 is verification evidence only.
`load_alignment_result` accepts exact bytes, performs strict parsing, runs the
same dependency and logical materialization path, then requires source bytes
to equal the newly encoded envelope exactly.

## 16. Result mutation resistance and publication registry

The private result registry is keyed by `id(result)` and stores:

```text
(weakref.ref(exact_result), exact_canonical_envelope_bytes)
```

Genuineness requires exact type, present entry, live identical object, and a
byte snapshot. The cleanup callback removes an entry only if it still owns the
same weakref. Registration is transactional: construct and verify first,
insert one entry, verify identity and snapshot, roll back only the owned entry
on false/exception, and return only after success.

`serialize_alignment_result` does not trust frozen-dataclass syntax. It:

1. requires exact genuine object and registry snapshot;
2. validates every current field and nested tuple without coercion;
3. rebuilds projection, recomputes hash then ID;
4. rebuilds the canonical envelope;
5. requires exact equality with the registry snapshot;
6. returns a bytes copy only after all checks pass.

Any mutation, including `object.__setattr__`, coherent mutation of data plus
hash/ID, nested replacement, or private-cache alteration, rejects at `/` with
`CONTENT_DRIFT`, `issue_code=None`, and emits no bytes. Copy, deep copy,
pickle, `dataclasses.replace`, direct construction, `object.__new__`, subclass,
proxy, reconstruction, and field cloning do not transfer provenance.

## 17. Closed container, key, pointer, and no-leak rules

- Logical objects are exact built-in dicts; arrays are exact built-in lists.
- JSON objects/arrays parse to exact dict/list only after duplicate-key and
  number-syntax checks.
- Every key is exact built-in NFC `str`. Nonconforming or unknown key text is
  never appended to a pointer or message.
- Unknown root key pointer is `/`.
- Unknown raw payload key pointer is `/raw_package/payload`.
- Unknown token key pointer is `/raw_package/payload/tokens/<index>`.
- Unknown `WordTiming` key pointer is `/word_timings/<index>`.
- Unknown evidence key pointer is `/timing_origin_evidence`.
- Missing or invalid known fields use the fixed containing-object pointer:
  `/` for the result root, `/timing_origin_evidence` for evidence,
  `/raw_package/payload` for payload, and the implementation-generated indexed
  token/timing object pointer for array members. Field order still determines
  first failure, but no field or key text is copied into the pointer.
- Decimal array indices are implementation-generated and are the only dynamic
  pointer segments.

Messages are exactly `Alignment result rejected: <REASON_VALUE>`. They never
include offending values, dynamic keys, narration/token/provider text,
credentials, authorization material, URI/path data, attacker hashes, or raw
exceptions. Result/evidence serialization contains only defined identities,
enums, integers, nulls, and arrays. No filesystem, network, database,
environment, credential store, clock, random, provider, or locale operation
participates.

## 18. Error contract and stable issue codes

```python
class AlignmentResultContractError(ValueError):
    pointer: str
    reason: AlignmentResultRejectionReason
    issue_code: str | None
```

Constructor inputs are exact sanitized built-in pointer, exact enum member,
and null or one exact canonical `STABLE_ISSUE_CODES` member. The error has no
identity, bytes, or serialized artifact. Wrong/non-genuine dependencies raise
sanitized `TypeError`. Internal construction/registry failures raise sanitized
`RuntimeError`. Publication is `NONE` for every failure.

Existing stable codes used are exactly:

```text
ADAPTER_FAILURE
ADAPTER_PRECISION_OVERSTATED
ALIGNMENT_REQUEST_IDENTITY_MISMATCH
CANONICAL_COVERAGE_BLOCKER
CANONICAL_WORD_ORDER_INVALID
CONFIDENCE_REQUIRED_UNAVAILABLE
LLM_TIMESTAMP_SOURCE_FORBIDDEN
REPLAY_HASH_MISMATCH
REPLAY_INPUT_MISMATCH
TIMESTAMP_NON_MONOTONIC
TIMESTAMP_OUT_OF_BOUNDS
TIMESTAMP_OVERLAP
TRANSCRIPT_DIVERGENCE
UNSUPPORTED_CONTRACT_ENUM
ZERO_DURATION_WORD
```

No inventory delta or alias is introduced.

## 19. Deterministic validation precedence and oracle

First failing stage is authoritative:

1. seven dependency type/genuineness checks in signature order;
2. seven content-integrity recomputations in section 11 order;
3. loader bytes/UTF-8/JSON/canonical syntax when applicable;
4. exact root dict/key set, unknown before missing;
5. root field types, schema/hash-scope/confidence literals;
6. section 12 intrinsic bindings;
7. execution status, then exact REPLAY mode/source;
8. raw envelope/media/payload shape;
9. raw payload fields and token list/items in array order;
10. token index/time/confidence ordering and audio bounds;
11. canonical word inventory;
12. unique supported mapping, then many-to-one diagnostic;
13. computed timing tuple;
14. declared timing list/items and field comparison;
15. sensitive-value/cycle scan;
16. result projection hash, then ID;
17. full envelope and loader source-byte equality;
18. construction, re-encoding, atomic registration, snapshot verification.

Exact oracle:

| Condition | Stage | Fixed pointer | Reason | Issue code |
|---|---:|---|---|---|
| evidence source type is not exact built-in bytes | evidence loader | `/timing_origin_evidence` | `STRUCTURE_INVALID` | `None` |
| evidence source is invalid UTF-8 | evidence loader | `/timing_origin_evidence` | `STRUCTURE_INVALID` | `None` |
| evidence source is malformed JSON | evidence loader | `/timing_origin_evidence` | `STRUCTURE_INVALID` | `None` |
| evidence source has a duplicate key | evidence loader | `/timing_origin_evidence` | `STRUCTURE_INVALID` | `None` |
| evidence root is not an exact dict | evidence loader | `/timing_origin_evidence` | `STRUCTURE_INVALID` | `None` |
| evidence root has an unknown key | evidence loader | `/timing_origin_evidence` | `STRUCTURE_INVALID` | `None` |
| evidence root is missing a known key | evidence loader | `/timing_origin_evidence` | `STRUCTURE_INVALID` | `None` |
| evidence root has a wrong field type | evidence loader | `/timing_origin_evidence` | `STRUCTURE_INVALID` | `None` |
| evidence source is not byte-identical canonical JSON | evidence loader | `/timing_origin_evidence` | `NON_CANONICAL_SERIALIZATION` | `None` |
| evidence schema version is unsupported | evidence loader | `/timing_origin_evidence` | `UNSUPPORTED_VALUE` | `UNSUPPORTED_CONTRACT_ENUM` |
| evidence hash-scope version is unsupported | evidence loader | `/timing_origin_evidence` | `UNSUPPORTED_VALUE` | `UNSUPPORTED_CONTRACT_ENUM` |
| evidence projection hash mismatches | evidence loader | `/timing_origin_evidence/timing_origin_evidence_hash` | `IDENTITY_MISMATCH` | `REPLAY_HASH_MISMATCH` |
| evidence ID mismatches | evidence loader | `/timing_origin_evidence/timing_origin_evidence_id` | `IDENTITY_MISMATCH` | `REPLAY_HASH_MISMATCH` |
| evidence is not the exact six-value allowlist member | evidence loader | `/timing_origin_evidence` | `TIMING_ORIGIN_EVIDENCE_INVALID` | `REPLAY_INPUT_MISMATCH` |
| raw package canonical content drifts | 2 | `/temporal_raw_package` | `DEPENDENCY_CONTENT_DRIFT` | `REPLAY_HASH_MISMATCH` |
| raw package stored hash differs from recomputation | 2 | `/temporal_raw_package` | `DEPENDENCY_CONTENT_DRIFT` | `REPLAY_HASH_MISMATCH` |
| narration document content drifts | 2 | `/narration_document` | `DEPENDENCY_CONTENT_DRIFT` | `ALIGNMENT_REQUEST_IDENTITY_MISMATCH` |
| narration revision projection content drifts | 2 | `/narration_revision` | `DEPENDENCY_CONTENT_DRIFT` | `ALIGNMENT_REQUEST_IDENTITY_MISMATCH` |
| narration revision stored hash differs from recomputation | 2 | `/narration_revision` | `DEPENDENCY_CONTENT_DRIFT` | `ALIGNMENT_REQUEST_IDENTITY_MISMATCH` |
| narration revision stored ID differs from recomputation | 2 | `/narration_revision` | `DEPENDENCY_CONTENT_DRIFT` | `ALIGNMENT_REQUEST_IDENTITY_MISMATCH` |
| audio artifact projection content drifts | 2 | `/audio_artifact` | `DEPENDENCY_CONTENT_DRIFT` | `ALIGNMENT_REQUEST_IDENTITY_MISMATCH` |
| audio artifact stored hash differs from recomputation | 2 | `/audio_artifact` | `DEPENDENCY_CONTENT_DRIFT` | `ALIGNMENT_REQUEST_IDENTITY_MISMATCH` |
| audio artifact stored ID differs from recomputation | 2 | `/audio_artifact` | `DEPENDENCY_CONTENT_DRIFT` | `ALIGNMENT_REQUEST_IDENTITY_MISMATCH` |
| alignment request projection content drifts | 2 | `/alignment_request` | `DEPENDENCY_CONTENT_DRIFT` | `ALIGNMENT_REQUEST_IDENTITY_MISMATCH` |
| alignment request stored hash differs from recomputation | 2 | `/alignment_request` | `DEPENDENCY_CONTENT_DRIFT` | `ALIGNMENT_REQUEST_IDENTITY_MISMATCH` |
| alignment request stored ID differs from recomputation | 2 | `/alignment_request` | `DEPENDENCY_CONTENT_DRIFT` | `ALIGNMENT_REQUEST_IDENTITY_MISMATCH` |
| adapter execution projection content drifts | 2 | `/adapter_execution` | `DEPENDENCY_CONTENT_DRIFT` | `REPLAY_HASH_MISMATCH` |
| adapter execution stored hash differs from recomputation | 2 | `/adapter_execution` | `DEPENDENCY_CONTENT_DRIFT` | `REPLAY_HASH_MISMATCH` |
| adapter execution stored ID differs from recomputation | 2 | `/adapter_execution` | `DEPENDENCY_CONTENT_DRIFT` | `REPLAY_HASH_MISMATCH` |
| timing evidence projection content drifts | 2 | `/timing_origin_evidence` | `TIMING_ORIGIN_EVIDENCE_INVALID` | `REPLAY_HASH_MISMATCH` |
| timing evidence stored hash differs from recomputation | 2 | `/timing_origin_evidence` | `TIMING_ORIGIN_EVIDENCE_INVALID` | `REPLAY_HASH_MISMATCH` |
| timing evidence stored ID differs from recomputation | 2 | `/timing_origin_evidence` | `TIMING_ORIGIN_EVIDENCE_INVALID` | `REPLAY_HASH_MISMATCH` |
| timing evidence envelope differs from its registry snapshot | 2 | `/timing_origin_evidence` | `TIMING_ORIGIN_EVIDENCE_INVALID` | `REPLAY_HASH_MISMATCH` |
| timing payload differs from its registry snapshot | 2 | `/timing_origin_evidence` | `TIMING_ORIGIN_EVIDENCE_INVALID` | `REPLAY_HASH_MISMATCH` |
| result source type is not exact built-in bytes | 3 | `/` | `STRUCTURE_INVALID` | `None` |
| result source is invalid UTF-8 | 3 | `/` | `STRUCTURE_INVALID` | `None` |
| result source is malformed JSON | 3 | `/` | `STRUCTURE_INVALID` | `None` |
| result source has a duplicate key | 3 | `/` | `STRUCTURE_INVALID` | `None` |
| result source is not byte-identical canonical JSON | 3 | `/` | `NON_CANONICAL_SERIALIZATION` | `None` |
| result root is not an exact dict | 4 | `/` | `STRUCTURE_INVALID` | `None` |
| result root has an unknown key | 4 | `/` | `STRUCTURE_INVALID` | `None` |
| result root is missing a known key | 4 | `/` | `STRUCTURE_INVALID` | `None` |
| result root has a wrong field type | 5 | `/` | `STRUCTURE_INVALID` | `None` |
| result schema version is unsupported | 5 | `/` | `UNSUPPORTED_VALUE` | `UNSUPPORTED_CONTRACT_ENUM` |
| result hash-scope version is unsupported | 5 | `/` | `UNSUPPORTED_VALUE` | `UNSUPPORTED_CONTRACT_ENUM` |
| result confidence availability is unsupported | 5 | `/` | `UNSUPPORTED_VALUE` | `UNSUPPORTED_CONTRACT_ENUM` |
| document project differs from revision project | 6 | `/narration_document/project_id` | `DEPENDENCY_BINDING_INVALID` | `ALIGNMENT_REQUEST_IDENTITY_MISMATCH` |
| document ID differs from revision document ID | 6 | `/narration_document/document_id` | `DEPENDENCY_BINDING_INVALID` | `ALIGNMENT_REQUEST_IDENTITY_MISMATCH` |
| current revision differs from revision ID | 6 | `/narration_document/current_revision_id` | `DEPENDENCY_BINDING_INVALID` | `ALIGNMENT_REQUEST_IDENTITY_MISMATCH` |
| audio binding differs from revision | 6 | `/audio_artifact` | `DEPENDENCY_BINDING_INVALID` | `ALIGNMENT_REQUEST_IDENTITY_MISMATCH` |
| request binding differs from its dependencies | 6 | `/alignment_request` | `DEPENDENCY_BINDING_INVALID` | `ALIGNMENT_REQUEST_IDENTITY_MISMATCH` |
| execution binding differs from request | 6 | `/adapter_execution` | `DEPENDENCY_BINDING_INVALID` | `ALIGNMENT_REQUEST_IDENTITY_MISMATCH` |
| evidence binding differs from dependency snapshots | 6 | `/timing_origin_evidence` | `DEPENDENCY_BINDING_INVALID` | `REPLAY_INPUT_MISMATCH` |
| declared result binding differs from its dependencies | 6 | `/` | `DEPENDENCY_BINDING_INVALID` | `ALIGNMENT_REQUEST_IDENTITY_MISMATCH` |
| execution status is FAILED | 7 | `/adapter_execution/status` | `EXECUTION_NOT_SUCCESSFUL` | `ADAPTER_FAILURE` |
| execution status is BLOCKED | 7 | `/adapter_execution/status` | `EXECUTION_NOT_SUCCESSFUL` | `ADAPTER_FAILURE` |
| execution mode is not REPLAY | 7 | `/adapter_execution/mode` | `TIMESTAMP_SOURCE_FORBIDDEN` | `LLM_TIMESTAMP_SOURCE_FORBIDDEN` |
| request mode is not REPLAY | 7 | `/alignment_request/mode` | `TIMESTAMP_SOURCE_FORBIDDEN` | `LLM_TIMESTAMP_SOURCE_FORBIDDEN` |
| capability mode is not REPLAY | 7 | `/alignment_request/adapter_capability/mode` | `TIMESTAMP_SOURCE_FORBIDDEN` | `LLM_TIMESTAMP_SOURCE_FORBIDDEN` |
| result timing source is not REPLAY_VERIFIED | 7 | `/timing_source` | `TIMESTAMP_SOURCE_FORBIDDEN` | `LLM_TIMESTAMP_SOURCE_FORBIDDEN` |
| raw envelope media type is not the exact observation media type | 8 | `/raw_package` | `RAW_OBSERVATION_INVALID` | `None` |
| private timing payload snapshot is not valid canonical JSON | 8 | `/raw_package/payload` | `RAW_OBSERVATION_INVALID` | `None` |
| raw payload has an unknown key | 9 | `/raw_package/payload` | `RAW_OBSERVATION_INVALID` | `None` |
| raw payload is missing a known field | 9 | `/raw_package/payload` | `RAW_OBSERVATION_INVALID` | `None` |
| raw payload has a wrong field type | 9 | `/raw_package/payload` | `RAW_OBSERVATION_INVALID` | `None` |
| token container is not an exact list | 9 | `/raw_package/payload/tokens` | `RAW_OBSERVATION_INVALID` | `None` |
| token list is empty | 9 | `/raw_package/payload/tokens` | `RAW_OBSERVATION_INVALID` | `None` |
| token item has an unknown key | 9 | `/raw_package/payload/tokens/<index>` | `RAW_OBSERVATION_INVALID` | `None` |
| token item is missing a known field | 9 | `/raw_package/payload/tokens/<index>` | `RAW_OBSERVATION_INVALID` | `None` |
| token item has a wrong field type | 9 | `/raw_package/payload/tokens/<index>` | `RAW_OBSERVATION_INVALID` | `None` |
| token kind is unsupported | 9 | `/raw_package/payload/tokens/<index>` | `RAW_OBSERVATION_INVALID` | `None` |
| required token confidence is null | 9 | `/raw_package/payload/tokens/<index>` | `CONFIDENCE_INVALID` | `CONFIDENCE_REQUIRED_UNAVAILABLE` |
| forbidden token confidence is non-null | 9 | `/raw_package/payload/tokens/<index>` | `CONFIDENCE_INVALID` | `ADAPTER_PRECISION_OVERSTATED` |
| token confidence is outside its closed range | 9 | `/raw_package/payload/tokens/<index>` | `CONFIDENCE_INVALID` | `ADAPTER_PRECISION_OVERSTATED` |
| token timestamp is negative | 10 | `/raw_package/payload/tokens/<index>` | `TIMING_INVALID` | `TIMESTAMP_OUT_OF_BOUNDS` |
| token timestamp exceeds the closed maximum | 10 | `/raw_package/payload/tokens/<index>` | `TIMING_INVALID` | `TIMESTAMP_OUT_OF_BOUNDS` |
| spoken token start equals end | 10 | `/raw_package/payload/tokens/<index>` | `TIMING_INVALID` | `ZERO_DURATION_WORD` |
| spoken token start exceeds end | 10 | `/raw_package/payload/tokens/<index>` | `TIMING_INVALID` | `TIMESTAMP_NON_MONOTONIC` |
| spoken token order is non-monotonic | 10 | `/raw_package/payload/tokens/<index>` | `TIMING_INVALID` | `TIMESTAMP_NON_MONOTONIC` |
| spoken token interval overlaps the previous spoken interval | 10 | `/raw_package/payload/tokens/<index>` | `TIMING_INVALID` | `TIMESTAMP_OVERLAP` |
| canonical word inventory is empty | 11 | `/narration_revision/canonical_words` | `TRANSCRIPT_DIVERGENCE` | `CANONICAL_COVERAGE_BLOCKER` |
| canonical word inventory has a duplicate word ID | 11 | `/narration_revision/canonical_words` | `TRANSCRIPT_DIVERGENCE` | `CANONICAL_COVERAGE_BLOCKER` |
| canonical word inventory has an invalid required field | 11 | `/narration_revision/canonical_words` | `TRANSCRIPT_DIVERGENCE` | `CANONICAL_COVERAGE_BLOCKER` |
| canonical word order is invalid | 11 | `/narration_revision/canonical_words` | `TRANSCRIPT_DIVERGENCE` | `CANONICAL_WORD_ORDER_INVALID` |
| only a forbidden many-canonical-to-one cover exists | 12 | `/raw_package/payload/tokens` | `TRANSCRIPT_DIVERGENCE` | `ADAPTER_PRECISION_OVERSTATED` |
| no complete supported cover exists | 12 | `/raw_package/payload/tokens` | `TRANSCRIPT_DIVERGENCE` | `TRANSCRIPT_DIVERGENCE` |
| timing container is not an exact list | 14 | `/word_timings` | `TRANSCRIPT_DIVERGENCE` | `CANONICAL_COVERAGE_BLOCKER` |
| timing item count differs from canonical word count | 14 | `/word_timings` | `TRANSCRIPT_DIVERGENCE` | `CANONICAL_COVERAGE_BLOCKER` |
| timing item has an unknown key | 14 | `/word_timings/<index>` | `STRUCTURE_INVALID` | `None` |
| timing item is missing a known field | 14 | `/word_timings/<index>` | `STRUCTURE_INVALID` | `None` |
| timing item has a wrong field type | 14 | `/word_timings/<index>` | `STRUCTURE_INVALID` | `None` |
| timing item repeats an earlier word ID | 14 | `/word_timings/<index>` | `TRANSCRIPT_DIVERGENCE` | `CANONICAL_COVERAGE_BLOCKER` |
| timing item contains a foreign word ID | 14 | `/word_timings/<index>` | `TRANSCRIPT_DIVERGENCE` | `CANONICAL_COVERAGE_BLOCKER` |
| a canonical word ID is missing after item scan | 14 | `/word_timings` | `TRANSCRIPT_DIVERGENCE` | `CANONICAL_COVERAGE_BLOCKER` |
| complete timing IDs are reordered | 14 | `/word_timings/<index>` | `TRANSCRIPT_DIVERGENCE` | `CANONICAL_WORD_ORDER_INVALID` |
| declared start differs from computed start | 14 | `/word_timings/<index>` | `TIMING_INVALID` | `ADAPTER_PRECISION_OVERSTATED` |
| declared end differs from computed end | 14 | `/word_timings/<index>` | `TIMING_INVALID` | `ADAPTER_PRECISION_OVERSTATED` |
| declared confidence differs from computed confidence | 14 | `/word_timings/<index>` | `CONFIDENCE_INVALID` | `ADAPTER_PRECISION_OVERSTATED` |
| declared source indices differ from computed indices | 14 | `/word_timings/<index>` | `TIMING_INVALID` | `ADAPTER_PRECISION_OVERSTATED` |
| a forbidden sensitive value is present | 15 | `/` | `SENSITIVE_DATA` | `None` |
| a logical input cycle is present | 15 | `/` | `SENSITIVE_DATA` | `None` |
| result projection hash mismatches | 16 | `/alignment_result_hash` | `IDENTITY_MISMATCH` | `None` |
| result ID mismatches | 16 | `/alignment_result_id` | `IDENTITY_MISMATCH` | `None` |
| serializer input is not a genuine result | serialize | `/` | `NOT_MATERIALIZED` | `None` |
| genuine serializer input differs from its registry snapshot | serialize | `/` | `CONTENT_DRIFT` | `None` |

For indexed rows, the lowest array index wins. For token known fields, field
order is `index`, `kind`, `normalized_alignment_text`, `start_ms`, `end_ms`,
`confidence_millionths`. For timing fields, `WordTiming` model order wins.
Multi-fault input never masks an earlier stage.

## 20. Golden fixture `FX-ALR-01`

All values needed for clean-room reproduction follow.

1. Materialize existing FX-34 narration from exact source
`Alpha beta. Gamma delta.`. Required identities:

```text
project_id=prj_fx34
document_id=nardoc_fx34
narration_revision_id=narrev_d60d7ae087efb0e309d4
narration_revision_hash=sha256:d60d7ae087efb0e309d4e3f28fedea074d15e11405046249a23b2c7bb42fe0c0
normalization_profile_hash=sha256:fda29f7bd8d0cc018489dcb0a7163b8130022e3bfd5e8a0cb88918c2723bb862
narration_document_snapshot_hash=sha256:7b3111ff00144fff30daa73fc3024868f0f0a7107b722e25ccf6107e9307143b
```

Canonical words are:

```text
nword_5321ba14c2c4b28c31ab alpha
nword_0cc9d55672a3cb4e9199 beta
nword_49e85bb034c88ef36f26 gamma
nword_d81fe913754f8b49c296 delta
```

2. Generate PCM WAVE: 8000 Hz, one channel, 32000 frames, little-endian S16,
sample `((frame * 257 + 12345) % 65536) - 32768`.

```text
file length=64044
media hash=sha256:913d5cfe5fb72e8586b42cee742d3bea4da16d3e97fb158835d4cd060ae3bd72
audio ID=aud_63d5743b733e34f12018
audio hash=sha256:63d5743b733e34f120180d3a787d78cb0a26119395bbee1aa2e45c257713d968
duration_us_numerator=4000000
duration_us_denominator=1
```

3. Exact raw root inputs:

```text
schema_version=TRP-RAW-V1
run_id=run_alignment_result_fx01
raw_id=raw_alignment_result_fx01
media_type=application/vnd.kurgu.alignment-token-observation+json
issue_codes=[]
```

Exact payload bytes:

```json
{"narration_revision_hash":"sha256:d60d7ae087efb0e309d4e3f28fedea074d15e11405046249a23b2c7bb42fe0c0","narration_revision_id":"narrev_d60d7ae087efb0e309d4","normalization_profile_hash":"sha256:fda29f7bd8d0cc018489dcb0a7163b8130022e3bfd5e8a0cb88918c2723bb862","schema_version":"ALIGNMENT-TOKEN-OBSERVATION-V1","tokens":[{"confidence_millionths":980000,"end_ms":500,"index":0,"kind":"SPOKEN","normalized_alignment_text":"alpha","start_ms":100},{"confidence_millionths":960000,"end_ms":900,"index":1,"kind":"SPOKEN","normalized_alignment_text":"beta","start_ms":520},{"confidence_millionths":null,"end_ms":null,"index":2,"kind":"NON_SPOKEN","normalized_alignment_text":null,"start_ms":null},{"confidence_millionths":940000,"end_ms":1700,"index":3,"kind":"SPOKEN","normalized_alignment_text":"gamma","start_ms":1200},{"confidence_millionths":920000,"end_ms":2300,"index":4,"kind":"SPOKEN","normalized_alignment_text":"delta","start_ms":1720},{"confidence_millionths":null,"end_ms":null,"index":5,"kind":"NON_SPOKEN","normalized_alignment_text":null,"start_ms":null}]}
```

```text
payload length=1062
payload SHA-256=86497808c046ec4334395f23eaef5a8e9976780af61a2ec7278ade6137d0b0ad
raw canonical length=1359
raw canonical hash=sha256:21891739f58b8dfc512de572105c13dc666d42ebeb2e98e02f2d5abd32826a18
```

4. Build a source LOCAL request and execution, then a current REPLAY request
and execution. Both capabilities use adapter `adapter_alignment_fx01`, version
`1.0.0`, English, `audio/wav`, confidence `SUPPORTED`, network `FORBIDDEN`,
and canonical transcript reference. LOCAL license is `LOCAL`; REPLAY license
is `REPLAY`. All statuses are `SUCCEEDED` and confidence is `AVAILABLE`.

```text
source LOCAL request ID=arq_0e915d69f6fc1f49dc9f3f00f05afd93
source LOCAL request hash=0e915d69f6fc1f49dc9f3f00f05afd93e5bdbc660e5178610485165710dea57a
source LOCAL request envelope length=1197
source LOCAL request envelope SHA-256=de821f628dcef33ebdc38f179b7b22c5803d4f1a8a02b31d20608f2b06f4bf04
source LOCAL execution ID=aex_cb5681908af17ff36bd5aadb84feda79
source LOCAL execution hash=cb5681908af17ff36bd5aadb84feda79cb07411fbc54a964ba0e553cb5a95a21
source LOCAL execution envelope length=684
source LOCAL execution envelope SHA-256=ed591f632b90af4b1781322f7c0546fdb24223b8ddddf1e6c5513cee27c41922
REPLAY request ID=arq_08487b276310e36fe3163499ffb773a0
REPLAY request hash=08487b276310e36fe3163499ffb773a0f06b2d969640d798a1ac360523f01234
REPLAY request envelope length=1200
REPLAY request envelope SHA-256=db2c1ce2c0f01e4b949411da6edbc39e9523ba7cd1e71528c17766c11e1862d2
REPLAY execution ID=aex_0d5a9c0a156e9e3ca7fbffc460b74c26
REPLAY execution hash=0d5a9c0a156e9e3ca7fbffc460b74c261fa0f5f645580e10684d145e526b123b
REPLAY execution envelope length=1056
REPLAY execution envelope SHA-256=27389e31161c15d6e79442c97c5661d46c2f7d1d5b065d82a773b4c5910046e1
```

Exact source LOCAL request envelope:

```json
{"adapter_capability":{"adapter_id":"adapter_alignment_fx01","adapter_version":"1.0.0","confidence_output":"SUPPORTED","language_tag":"en","license_class":"LOCAL","media_type":"audio/wav","mode":"LOCAL","network_access":"FORBIDDEN","schema_version":"ADAPTER-CAPABILITY-V1"},"alignment_request_hash":"0e915d69f6fc1f49dc9f3f00f05afd93e5bdbc660e5178610485165710dea57a","alignment_request_id":"arq_0e915d69f6fc1f49dc9f3f00f05afd93","audio_artifact_hash":"sha256:63d5743b733e34f120180d3a787d78cb0a26119395bbee1aa2e45c257713d968","audio_artifact_id":"aud_63d5743b733e34f12018","document_id":"nardoc_fx34","hash_scope_version":"ALIGNMENT-REQUEST-HASH-V1","mode":"LOCAL","narration_revision_hash":"sha256:d60d7ae087efb0e309d4e3f28fedea074d15e11405046249a23b2c7bb42fe0c0","narration_revision_id":"narrev_d60d7ae087efb0e309d4","project_id":"prj_fx34","schema_version":"ALIGNMENT-REQUEST-V1","temporal_raw_package_hash":"sha256:21891739f58b8dfc512de572105c13dc666d42ebeb2e98e02f2d5abd32826a18","transcript_reference":{"narration_revision_hash":"sha256:d60d7ae087efb0e309d4e3f28fedea074d15e11405046249a23b2c7bb42fe0c0","narration_revision_id":"narrev_d60d7ae087efb0e309d4","text_scope":"CANONICAL_NARRATION"}}
```

Exact source LOCAL execution envelope:

```json
{"adapter_execution_hash":"cb5681908af17ff36bd5aadb84feda79cb07411fbc54a964ba0e553cb5a95a21","adapter_execution_id":"aex_cb5681908af17ff36bd5aadb84feda79","adapter_id":"adapter_alignment_fx01","adapter_version":"1.0.0","alignment_request_hash":"0e915d69f6fc1f49dc9f3f00f05afd93e5bdbc660e5178610485165710dea57a","alignment_request_id":"arq_0e915d69f6fc1f49dc9f3f00f05afd93","confidence_availability_evidence":{"availability":"AVAILABLE","schema_version":"CONFIDENCE-AVAILABILITY-EVIDENCE-V1"},"hash_scope_version":"ADAPTER-EXECUTION-HASH-V1","mode":"LOCAL","paid_fallback_authorization_evidence":null,"replay_evidence":null,"schema_version":"ADAPTER-EXECUTION-V1","status":"SUCCEEDED"}
```

Exact REPLAY request envelope:

```json
{"adapter_capability":{"adapter_id":"adapter_alignment_fx01","adapter_version":"1.0.0","confidence_output":"SUPPORTED","language_tag":"en","license_class":"REPLAY","media_type":"audio/wav","mode":"REPLAY","network_access":"FORBIDDEN","schema_version":"ADAPTER-CAPABILITY-V1"},"alignment_request_hash":"08487b276310e36fe3163499ffb773a0f06b2d969640d798a1ac360523f01234","alignment_request_id":"arq_08487b276310e36fe3163499ffb773a0","audio_artifact_hash":"sha256:63d5743b733e34f120180d3a787d78cb0a26119395bbee1aa2e45c257713d968","audio_artifact_id":"aud_63d5743b733e34f12018","document_id":"nardoc_fx34","hash_scope_version":"ALIGNMENT-REQUEST-HASH-V1","mode":"REPLAY","narration_revision_hash":"sha256:d60d7ae087efb0e309d4e3f28fedea074d15e11405046249a23b2c7bb42fe0c0","narration_revision_id":"narrev_d60d7ae087efb0e309d4","project_id":"prj_fx34","schema_version":"ALIGNMENT-REQUEST-V1","temporal_raw_package_hash":"sha256:21891739f58b8dfc512de572105c13dc666d42ebeb2e98e02f2d5abd32826a18","transcript_reference":{"narration_revision_hash":"sha256:d60d7ae087efb0e309d4e3f28fedea074d15e11405046249a23b2c7bb42fe0c0","narration_revision_id":"narrev_d60d7ae087efb0e309d4","text_scope":"CANONICAL_NARRATION"}}
```

Exact REPLAY execution envelope:

```json
{"adapter_execution_hash":"0d5a9c0a156e9e3ca7fbffc460b74c261fa0f5f645580e10684d145e526b123b","adapter_execution_id":"aex_0d5a9c0a156e9e3ca7fbffc460b74c26","adapter_id":"adapter_alignment_fx01","adapter_version":"1.0.0","alignment_request_hash":"08487b276310e36fe3163499ffb773a0f06b2d969640d798a1ac360523f01234","alignment_request_id":"arq_08487b276310e36fe3163499ffb773a0","confidence_availability_evidence":{"availability":"AVAILABLE","schema_version":"CONFIDENCE-AVAILABILITY-EVIDENCE-V1"},"hash_scope_version":"ADAPTER-EXECUTION-HASH-V1","mode":"REPLAY","paid_fallback_authorization_evidence":null,"replay_evidence":{"schema_version":"REPLAY-EVIDENCE-V1","source_adapter_execution_hash":"cb5681908af17ff36bd5aadb84feda79cb07411fbc54a964ba0e553cb5a95a21","source_adapter_execution_id":"aex_cb5681908af17ff36bd5aadb84feda79","source_alignment_request_hash":"0e915d69f6fc1f49dc9f3f00f05afd93e5bdbc660e5178610485165710dea57a","source_alignment_request_id":"arq_0e915d69f6fc1f49dc9f3f00f05afd93"},"schema_version":"ADAPTER-EXECUTION-V1","status":"SUCCEEDED"}
```

5. Exact timing-origin evidence canonical envelope bytes:

```json
{"adapter_execution_hash":"0d5a9c0a156e9e3ca7fbffc460b74c261fa0f5f645580e10684d145e526b123b","adapter_execution_id":"aex_0d5a9c0a156e9e3ca7fbffc460b74c26","alignment_request_hash":"08487b276310e36fe3163499ffb773a0f06b2d969640d798a1ac360523f01234","alignment_request_id":"arq_08487b276310e36fe3163499ffb773a0","audio_artifact_hash":"sha256:63d5743b733e34f120180d3a787d78cb0a26119395bbee1aa2e45c257713d968","audio_artifact_id":"aud_63d5743b733e34f12018","fixture_id":"FX-ALR-01","hash_scope_version":"TIMING-ORIGIN-EVIDENCE-HASH-V1","narration_document_snapshot_hash":"sha256:7b3111ff00144fff30daa73fc3024868f0f0a7107b722e25ccf6107e9307143b","narration_revision_hash":"sha256:d60d7ae087efb0e309d4e3f28fedea074d15e11405046249a23b2c7bb42fe0c0","narration_revision_id":"narrev_d60d7ae087efb0e309d4","schema_version":"TIMING-ORIGIN-EVIDENCE-V1","temporal_raw_package_hash":"sha256:21891739f58b8dfc512de572105c13dc666d42ebeb2e98e02f2d5abd32826a18","timing_origin_evidence_hash":"f140843e7e1f86817c7acc0bdc8eb775021ffd8c5a5a13809d5e33407c34ae03","timing_origin_evidence_id":"toe_f140843e7e1f86817c7acc0bdc8eb775","timing_payload_byte_hash":"sha256:86497808c046ec4334395f23eaef5a8e9976780af61a2ec7278ade6137d0b0ad"}
```

```text
evidence length=1206
evidence projection hash=f140843e7e1f86817c7acc0bdc8eb775021ffd8c5a5a13809d5e33407c34ae03
evidence ID=toe_f140843e7e1f86817c7acc0bdc8eb775
evidence envelope SHA-256=11ba9218006576fc87f0bcac1bf7cbe808dcdfc78a3fa3f957e97918960628a9
```

6. Exact result projection bytes:

```json
{"adapter_execution_hash":"0d5a9c0a156e9e3ca7fbffc460b74c261fa0f5f645580e10684d145e526b123b","adapter_execution_id":"aex_0d5a9c0a156e9e3ca7fbffc460b74c26","alignment_request_hash":"08487b276310e36fe3163499ffb773a0f06b2d969640d798a1ac360523f01234","alignment_request_id":"arq_08487b276310e36fe3163499ffb773a0","audio_artifact_hash":"sha256:63d5743b733e34f120180d3a787d78cb0a26119395bbee1aa2e45c257713d968","audio_artifact_id":"aud_63d5743b733e34f12018","confidence_availability":"AVAILABLE","document_id":"nardoc_fx34","hash_scope_version":"ALIGNMENT-RESULT-HASH-V1","narration_revision_hash":"sha256:d60d7ae087efb0e309d4e3f28fedea074d15e11405046249a23b2c7bb42fe0c0","narration_revision_id":"narrev_d60d7ae087efb0e309d4","project_id":"prj_fx34","schema_version":"ALIGNMENT-RESULT-V1","temporal_raw_package_hash":"sha256:21891739f58b8dfc512de572105c13dc666d42ebeb2e98e02f2d5abd32826a18","timing_origin_evidence_hash":"f140843e7e1f86817c7acc0bdc8eb775021ffd8c5a5a13809d5e33407c34ae03","timing_origin_evidence_id":"toe_f140843e7e1f86817c7acc0bdc8eb775","timing_source":"REPLAY_VERIFIED","word_timings":[{"confidence_millionths":980000,"end_ms":500,"source_token_indices":[0],"start_ms":100,"word_id":"nword_5321ba14c2c4b28c31ab"},{"confidence_millionths":960000,"end_ms":900,"source_token_indices":[1],"start_ms":520,"word_id":"nword_0cc9d55672a3cb4e9199"},{"confidence_millionths":940000,"end_ms":1700,"source_token_indices":[3],"start_ms":1200,"word_id":"nword_49e85bb034c88ef36f26"},{"confidence_millionths":920000,"end_ms":2300,"source_token_indices":[4],"start_ms":1720,"word_id":"nword_d81fe913754f8b49c296"}]}
```

```text
projection length=1612
projection SHA-256=1521f195a591df09edaa968d8f5fa91ed367be1c7190a3f614823d74b3cd36bb
alignment_result_id=alr_1521f195a591df09edaa968d8f5fa91e
```

7. Exact result envelope bytes:

```json
{"adapter_execution_hash":"0d5a9c0a156e9e3ca7fbffc460b74c261fa0f5f645580e10684d145e526b123b","adapter_execution_id":"aex_0d5a9c0a156e9e3ca7fbffc460b74c26","alignment_request_hash":"08487b276310e36fe3163499ffb773a0f06b2d969640d798a1ac360523f01234","alignment_request_id":"arq_08487b276310e36fe3163499ffb773a0","alignment_result_hash":"1521f195a591df09edaa968d8f5fa91ed367be1c7190a3f614823d74b3cd36bb","alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","audio_artifact_hash":"sha256:63d5743b733e34f120180d3a787d78cb0a26119395bbee1aa2e45c257713d968","audio_artifact_id":"aud_63d5743b733e34f12018","confidence_availability":"AVAILABLE","document_id":"nardoc_fx34","hash_scope_version":"ALIGNMENT-RESULT-HASH-V1","narration_revision_hash":"sha256:d60d7ae087efb0e309d4e3f28fedea074d15e11405046249a23b2c7bb42fe0c0","narration_revision_id":"narrev_d60d7ae087efb0e309d4","project_id":"prj_fx34","schema_version":"ALIGNMENT-RESULT-V1","temporal_raw_package_hash":"sha256:21891739f58b8dfc512de572105c13dc666d42ebeb2e98e02f2d5abd32826a18","timing_origin_evidence_hash":"f140843e7e1f86817c7acc0bdc8eb775021ffd8c5a5a13809d5e33407c34ae03","timing_origin_evidence_id":"toe_f140843e7e1f86817c7acc0bdc8eb775","timing_source":"REPLAY_VERIFIED","word_timings":[{"confidence_millionths":980000,"end_ms":500,"source_token_indices":[0],"start_ms":100,"word_id":"nword_5321ba14c2c4b28c31ab"},{"confidence_millionths":960000,"end_ms":900,"source_token_indices":[1],"start_ms":520,"word_id":"nword_0cc9d55672a3cb4e9199"},{"confidence_millionths":940000,"end_ms":1700,"source_token_indices":[3],"start_ms":1200,"word_id":"nword_49e85bb034c88ef36f26"},{"confidence_millionths":920000,"end_ms":2300,"source_token_indices":[4],"start_ms":1720,"word_id":"nword_d81fe913754f8b49c296"}]}
```

```text
envelope length=1764
envelope SHA-256=c2bab562863094ae6c1d29964a86316641dfc22cc5aa2d68dcc7542d9e4aef99
```

Repository canonical encoding and an independent compact sorted-key UTF-8
encoder MUST produce byte-identical payload, evidence, projection, and
envelope values.

## 21. Mandatory future tests

The focused module MUST cover:

- exact constants, enums, dataclass fields/order/types, signatures, exports,
  and forbidden exports;
- exact evidence allowlist membership, canonical bytes, hash/ID, direct
  construction/copy/proxy rejection, and no runtime allowlist extension;
- the complete FX-ALR-01 construction including exact run/raw IDs, source
  LOCAL lineage, REPLAY lineage, all bytes, lengths, hashes, and IDs;
- caller-authored arbitrary valid milliseconds through genuine Slice 1-5
  public materializers rejected because evidence raw/payload/execution binding
  does not match;
- rejection of LOCAL/FREE_API/PAID_API/MANUAL_UI publication, every
  FAILED/BLOCKED state, mode downgrade, and former `ADAPTER_MEASURED` input;
- mutation via `object.__setattr__` for every dependency and evidence;
  recomputation must reject the first drift pointer before logical input;
- result ordinary/coherent mutation, nested replacement, copy/deepcopy,
  pickle/replace/direct/new/subclass/proxy and serializer snapshot checks;
- exact one-to-one and one-word-to-many-token mapping, repeated words,
  punctuation/non-spoken exclusion, many-words-to-one rejection, missing,
  extra, case/Unicode mismatch, reorder, and proof-oriented exhaustive small
  search showing complete path count never exceeds one;
- confidence modes/bounds/group minimum and every timing boundary;
- exact logical dict/list acceptance and rejection of tuple, arbitrary
  Mapping/Sequence, subclasses, strings, bytes, iterators, and coercion;
- duplicate/unknown/missing keys at every object level, fixed pointers,
  attacker-key no-leak, multi-fault precedence, and every oracle row;
- strict loader syntax, canonical round trips, hash-before-ID, two independent
  result materializations, registry rollback/stale cleanup, and no mutable
  alias retention;
- static import direction and absence of filesystem, database, network,
  provider, clock, random, UI, frame, caption, emphasis, or Phase 3 imports.

Golden expected constants MUST be literal and not derived through production
projection helpers under test.

## 22. Backward compatibility and non-claims

This additive candidate does not change TRP-RAW-V1, narration identities,
AudioArtifact, AlignmentRequest, AdapterExecution, stable issue inventory, or
accepted Slice 1-5 bytes/hashes. Its raw profile is a consumer profile inside
the opaque Slice 1 payload boundary.

The candidate does not claim general provider timing support. Only exact
allowlisted repository replay evidence can publish. No implementation, test,
timing file, quality gate, new Slice number, total Slice count, completion
percentage, or Phase 2 closure is claimed.

## 23. Acceptance and future authorization gates

Before acceptance:

1. targeted independent read-only re-audit must close F1-F5;
2. golden bytes/hashes/lengths/IDs must be independently recomputed;
3. exact file SHA-256 and byte length must be verified;
4. this correction commit must be normally remote closed;
5. a later documentation task may record acceptance only after those gates.

Acceptance permits only a separate implementation-authorization decision.
That later decision must verify exact paths, public delta, tests, regression
boundary, and commit scope.

```text
SPECIFICATION_STATUS=CANDIDATE
SPECIFICATION_ACCEPTED=NO
IMPLEMENTATION_AUTHORIZED=NO
PHASE2_CLOSED=NO
INDEPENDENT_AUDIT_FINDINGS_F1_F5=REPAIRED_PENDING_TARGETED_REAUDIT
NEXT_REQUIRED_GATE=TARGETED_INDEPENDENT_READ_ONLY_REAUDIT
```
