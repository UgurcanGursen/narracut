# Phase 2 Slice 5 Candidate Specification

ID: `PHASE2-SLICE-5-CANDIDATE`

Title: Canonical Adapter Execution Provenance Contract

```text
Status: Candidate specification
Accepted: No
Implementation authorized: No
Phase 2 closed: No
```

Drafting this document does not accept this specification and does not
authorize implementation.

## 1. Status and authority

This candidate is bounded by:

- scope authority:
  `baseline/phase2_post_slice4_scope_report.md`, commit
  `f89e10156a940016deef4e94b6aef8863837dbf6`, SHA-256
  `aefaacf8e19e94c1f1f31615550d6e76c2d1184cb290ce34c12264df4cc3703f`;
- path authority:
  `baseline/phase2_slice5_specification_path_decision_report.md`, commit
  `d61500d861762bb6215e0f3041c144e25ea10752`, SHA-256
  `cab27022625b6edd19562070ff35950a57eb591b10e58b1cd9621eb028295049`;
- documentation synchronization closure commit:
  `d27cd83ae2f8501a19dd232a3516af5cdfed6d9d`;
- dependency documents: `docs/MASTER_ROADMAP.md`,
  `docs/PHASE_ACCEPTANCE.md`, `docs/CURRENT_STATE.md`,
  `docs/NEXT_ACTIONS.md`, `docs/KNOWN_LIMITATIONS.md`,
  `docs/ARCHITECTURE_DECISIONS.md`, and `docs/DOMAIN_PACKS.md`.

The required Phase 2 work-item dependencies are:

- Slice 1 - Temporal Raw Package;
- Slice 2 - Canonical Narration;
- Slice 3 - Canonical AudioArtifact;
- Slice 4 - Canonical AlignmentRequest Contract.

This dependency list does not establish the total Phase 2 Slice count.

Every new normative choice below is a **Specification decision**. It is a
bounded candidate decision justified by the existing canonical contract
patterns; it is not presented as a previously accepted historical fact.

## 2. Purpose

**Specification decision:** This contract represents one immutable,
terminal adapter execution provenance snapshot bound to one genuine
`AlignmentRequest`. It records which execution mode was selected, the terminal
execution classification, and the exact authorization, replay, and confidence
availability evidence permitted by that mode and status.

`PAID_API` identifies a paid-fallback path under evaluation for a `FREE_API`
request. It does not itself imply authorization approval; its authorization
evidence determines whether execution proceeded or remained `BLOCKED`.

It is not an alignment result, word timing collection, failure artifact,
runtime execution record, provider response payload, billing record, or mutable
orchestration state. `SUCCEEDED` does not publish timings. `FAILED` does not
publish a failure artifact. `BLOCKED` records that execution did not start.

## 3. Terminology

- **AlignmentRequest binding:** the required pair
  `alignment_request_id` and `alignment_request_hash`, validated against one
  genuine, materialized `AlignmentRequest`.
- **Adapter execution:** the bounded semantic event classified by this
  provenance snapshot. Provider invocation mechanics are outside this
  specification.
- **Execution provenance:** the immutable `AdapterExecution` envelope and its
  identity-participating evidence.
- **Execution mode:** one exact member of `AdapterExecutionMode`.
- **Execution status:** one exact terminal member of
  `AdapterExecutionStatus`.
- **Paid-fallback authorization evidence:** the closed decision evidence that
  determines whether a `PAID_API` path for the bound request was approved and
  proceeded or was denied and remained `BLOCKED`.
- **Replay evidence:** a single direct binding to one genuine, successful,
  non-replay source execution for the same request.
- **Confidence-availability evidence:** a declaration of availability only;
  it carries no score, word list, provider payload, or quality classification.
- **Canonical projection:** the identity-bearing JSON object excluding
  `adapter_execution_id` and `adapter_execution_hash`.
- **Canonical envelope:** the canonical projection plus the verified derived
  identifier and hash.
- **Derived identifier:** `aex_` followed by the first 32 lowercase
  hexadecimal characters of the projection SHA-256.
- **Publication boundary:** the point after complete validation, identity
  verification, immutable construction, canonical serialization verification,
  and genuine-instance registration.

## 4. Contract ownership and future paths

**Specification decision:** The contract is domain-agnostic core
infrastructure. A Domain Pack may select policy before request creation but
must not alter these fields, enum domains, identity rules, or validation
semantics.

Future implementation paths are:

```text
engine/contracts/alignment_execution.py
tests/test_alignment_execution.py
engine/contracts/__init__.py
```

The first path owns the contract. The second is the focused test module. The
third is only the publication boundary. This specification task creates or
changes none of those paths.

## 5. Exact public data model

### 5.1 Public constants and symbols

**Specification decision:** The future module shall define and publish exactly
this Slice-owned public symbol delta:

```text
ADAPTER_EXECUTION_V1
ADAPTER_EXECUTION_HASH_V1
PAID_FALLBACK_AUTHORIZATION_EVIDENCE_V1
REPLAY_EVIDENCE_V1
CONFIDENCE_AVAILABILITY_EVIDENCE_V1
AdapterExecutionMode
AdapterExecutionStatus
PaidFallbackAuthorizationSource
PaidFallbackAuthorizationDecision
ConfidenceAvailability
PaidFallbackAuthorizationEvidence
ReplayEvidence
ConfidenceAvailabilityEvidence
AdapterExecution
AdapterExecutionRejectionReason
AdapterExecutionContractError
materialize_adapter_execution
load_adapter_execution
serialize_adapter_execution
```

Constant values are:

```text
ADAPTER_EXECUTION_V1=ADAPTER-EXECUTION-V1
ADAPTER_EXECUTION_HASH_V1=ADAPTER-EXECUTION-HASH-V1
PAID_FALLBACK_AUTHORIZATION_EVIDENCE_V1=PAID-FALLBACK-AUTHORIZATION-EVIDENCE-V1
REPLAY_EVIDENCE_V1=REPLAY-EVIDENCE-V1
CONFIDENCE_AVAILABILITY_EVIDENCE_V1=CONFIDENCE-AVAILABILITY-EVIDENCE-V1
```

All public enum declarations and member/value mappings are exactly:

```python
class AdapterExecutionMode(str, Enum):
    LOCAL = "LOCAL"
    REPLAY = "REPLAY"
    FREE_API = "FREE_API"
    PAID_API = "PAID_API"
    MANUAL_UI = "MANUAL_UI"


class AdapterExecutionStatus(str, Enum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class PaidFallbackAuthorizationSource(str, Enum):
    USER_EXPLICIT = "USER_EXPLICIT"


class PaidFallbackAuthorizationDecision(str, Enum):
    APPROVED = "APPROVED"
    DENIED = "DENIED"


class ConfidenceAvailability(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class AdapterExecutionRejectionReason(str, Enum):
    STRUCTURE_INVALID = "STRUCTURE_INVALID"
    UNSUPPORTED_VALUE = "UNSUPPORTED_VALUE"
    REQUEST_BINDING_INVALID = "REQUEST_BINDING_INVALID"
    MODE_STATUS_INVALID = "MODE_STATUS_INVALID"
    EVIDENCE_PRESENCE_INVALID = "EVIDENCE_PRESENCE_INVALID"
    PAID_FALLBACK_AUTHORIZATION_INVALID = "PAID_FALLBACK_AUTHORIZATION_INVALID"
    REPLAY_EVIDENCE_INVALID = "REPLAY_EVIDENCE_INVALID"
    REPLAY_LINEAGE_INVALID = "REPLAY_LINEAGE_INVALID"
    CONFIDENCE_AVAILABILITY_INVALID = "CONFIDENCE_AVAILABILITY_INVALID"
    NON_CANONICAL_SERIALIZATION = "NON_CANONICAL_SERIALIZATION"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    NOT_MATERIALIZED = "NOT_MATERIALIZED"
```

Each declaration is public, closed, string-valued, and alias-free. Unknown
members, case folding, arbitrary Enum coercion, and arbitrary `str`-subclass
coercion are forbidden. Canonical serialization uses the exact `.value`
shown above.

All value objects and the root model shall be exact, frozen dataclasses.

The public function signatures are exactly:

```python
def materialize_adapter_execution(
    value: Mapping[str, Any],
    *,
    alignment_request: AlignmentRequest,
    source_execution: AdapterExecution | None = None,
) -> AdapterExecution

def load_adapter_execution(
    source: bytes,
    *,
    alignment_request: AlignmentRequest,
    source_execution: AdapterExecution | None = None,
) -> AdapterExecution

def serialize_adapter_execution(
    execution: AdapterExecution,
) -> bytes
```

Before root input access, both public materializers validate
`alignment_request` as an exact genuine materialized `AlignmentRequest`.
Wrong-type and exact-type-but-non-genuine values raise `TypeError` under the
established prerequisite dependency convention. The exception class is
normative. The sanitized message category identifies `alignment_request`, but
exact message text is not a stable contract. These failures occur before
`AdapterExecutionContractError` validation and carry no pointer, rejection
reason, or issue code.
When `source_execution` is non-null, they also validate only its exact type and
genuine materialization at that pre-input stage. A null `source_execution` is
not rejected and mode-dependent presence is not decided before root mode
parsing.

After root structure and the closed `mode` enum have been parsed,
`source_execution` is required for `REPLAY` and forbidden for `LOCAL`,
`FREE_API`, `PAID_API`, and `MANUAL_UI`. `load_adapter_execution` applies the
same dependency and semantic validation as `materialize_adapter_execution`
before its final exact-byte check.

### 5.2 `AdapterExecution`

| Field name | Exact type | Required or optional | Canonical representation | Semantic meaning | Allowed values and constraints | Identity/hash participation | Presence condition | Invalid states |
|---|---|---|---|---|---|---|---|---|
| `schema_version` | `str` | required | JSON string | root schema | exact `ADAPTER-EXECUTION-V1` | yes | always | any other value/type |
| `hash_scope_version` | `str` | required | JSON string | identity scope | exact `ADAPTER-EXECUTION-HASH-V1` | yes | always | any other value/type |
| `adapter_execution_id` | `str` | required | JSON string | derived identity | exact derived value | no | envelope only | syntax or digest mismatch |
| `adapter_execution_hash` | `str` | required | JSON string | projection SHA-256 | 64 lowercase hex, no `sha256:` prefix | no | envelope only | syntax or digest mismatch |
| `alignment_request_id` | `str` | required | JSON string | request identity | exact bound request ID | yes | always | absent, malformed, or parity mismatch |
| `alignment_request_hash` | `str` | required | JSON string | request content identity | exact bound request hash; 64 lowercase hex | yes | always | absent, malformed, or parity mismatch |
| `adapter_id` | `str` | required | JSON string | selected adapter identity | exact equality with request capability | yes | always | mismatch or unsafe string |
| `adapter_version` | `str` | required | JSON string | selected adapter version | exact equality with request capability | yes | always | mismatch or unsafe string |
| `mode` | `AdapterExecutionMode` | required | enum `.value` string | effective execution mode | closed domain in section 7 | yes | always | unknown/coerced value |
| `status` | `AdapterExecutionStatus` | required | enum `.value` string | terminal classification | closed domain in section 8 | yes | always | unknown/coerced value |
| `paid_fallback_authorization_evidence` | `PaidFallbackAuthorizationEvidence \| None` | conditional | object or JSON `null` | paid fallback decision | section 10 | yes | key always present; object only where matrix requires | missing object, forbidden object, or non-null invalid object |
| `replay_evidence` | `ReplayEvidence \| None` | conditional | object or JSON `null` | direct replay source | section 11 | yes | key always present; object only for `REPLAY` | missing object, forbidden object, ambiguity, or invalid lineage |
| `confidence_availability_evidence` | `ConfidenceAvailabilityEvidence \| None` | conditional | object or JSON `null` | confidence availability only | section 12 | yes | key always present; object for `SUCCEEDED`/`FAILED`, null for `BLOCKED` | missing required object, forbidden object, or invalid state |

### 5.3 `PaidFallbackAuthorizationEvidence`

| Field name | Exact type | Required or optional | Canonical representation | Semantic meaning | Allowed values and constraints | Identity/hash participation | Presence condition | Invalid states |
|---|---|---|---|---|---|---|---|---|
| `schema_version` | `str` | required | JSON string | evidence schema | exact `PAID-FALLBACK-AUTHORIZATION-EVIDENCE-V1` | yes, through root | object present | other value/type |
| `authorization_id` | `str` | required | JSON string | authorization identity | exact built-in NFC string matching `pfa_[a-z0-9][a-z0-9_-]{2,63}` | yes | object present | malformed, URI, path, or secret-bearing value |
| `source` | `PaidFallbackAuthorizationSource` | required | enum `.value` string | authority source | exact closed value | yes | object present | unknown/free-form source |
| `decision` | `PaidFallbackAuthorizationDecision` | required | enum `.value` string | authorization decision | exact closed value | yes | object present | unknown/coerced decision |
| `alignment_request_id` | `str` | required | JSON string | authorization binding | exact current request ID | yes | object present | mismatch |
| `alignment_request_hash` | `str` | required | JSON string | authorization binding | exact current request hash | yes | object present | mismatch |

### 5.4 `ReplayEvidence`

| Field name | Exact type | Required or optional | Canonical representation | Semantic meaning | Allowed values and constraints | Identity/hash participation | Presence condition | Invalid states |
|---|---|---|---|---|---|---|---|---|
| `schema_version` | `str` | required | JSON string | evidence schema | exact `REPLAY-EVIDENCE-V1` | yes, through root | `REPLAY` only | other value/type |
| `source_adapter_execution_id` | `str` | required | JSON string | direct source execution | exact genuine source ID | yes | object present | self-reference, mismatch, or malformed |
| `source_adapter_execution_hash` | `str` | required | JSON string | direct source content identity | exact genuine source hash | yes | object present | mismatch or malformed |
| `source_alignment_request_id` | `str` | required | JSON string | source request binding | exact current and source request ID | yes | object present | mismatch |
| `source_alignment_request_hash` | `str` | required | JSON string | source request binding | exact current and source request hash | yes | object present | mismatch |

### 5.5 `ConfidenceAvailabilityEvidence`

| Field name | Exact type | Required or optional | Canonical representation | Semantic meaning | Allowed values and constraints | Identity/hash participation | Presence condition | Invalid states |
|---|---|---|---|---|---|---|---|---|
| `schema_version` | `str` | required | JSON string | evidence schema | exact `CONFIDENCE-AVAILABILITY-EVIDENCE-V1` | yes, through root | evidence present | other value/type |
| `availability` | `ConfidenceAvailability` | required | enum `.value` string | availability, not quality | exact closed value | yes | evidence present | unknown state or state incompatible with request/status |

No model in this Slice carries provider response, timing result, exception
payload, billing data, timestamps, mutable progress, retry count, cost, or
payment state.

## 6. AlignmentRequest binding

**Specification decision:**

- Both `alignment_request_id` and `alignment_request_hash` are required.
- Materialization requires a genuine exact `AlignmentRequest` produced by
  `materialize_alignment_request`; reconstruction, subclass, proxy, copied
  lookalike, or unregistered instance is rejected before raw input access.
- A wrong-type `alignment_request` and an exact `AlignmentRequest` that is not
  genuinely materialized each raise `TypeError` before root input access.
  Exception class and the sanitized `alignment_request` message category are
  normative; exact message text is not a stable contract.
- The two stored values must exactly equal the genuine request values.
- The request payload is referenced, never embedded.
- Both binding fields participate in execution identity.
- `adapter_id` and `adapter_version` must exactly equal
  `alignment_request.adapter_capability.adapter_id` and
  `alignment_request.adapter_capability.adapter_version`.
- A `PAID_API` execution remains bound to that exact adapter identity. It may
  represent only a paid channel, tier, or authorization path of the same
  adapter.
- A different paid `adapter_id` or `adapter_version` requires a distinct
  `AlignmentRequest` bound to that adapter and cannot be represented as a
  `PAID_API` execution of the original request.
- Execution mode must satisfy section 7 request-mode parity.
- Any mismatch rejects the entire execution before identity generation and
  publishes no execution artifact.

## 7. Closed execution-mode domain

**Specification decision:**

`AdapterExecutionMode` is the exact public `str, Enum` declaration in section
5.1. Its member names and `.value` strings are normative.

| Enum member | Exact serialized value | Meaning | Allowed statuses | Required evidence | Forbidden evidence | Paid-fallback relevance | Replay relevance |
|---|---|---|---|---|---|---|---|
| `LOCAL` | `LOCAL` | local adapter execution | `SUCCEEDED`, `FAILED` | confidence | paid, replay | none | none |
| `REPLAY` | `REPLAY` | deterministic use of one prior successful source execution | `SUCCEEDED`, `FAILED` | replay, confidence | paid | none | direct source required |
| `FREE_API` | `FREE_API` | free network adapter execution | `SUCCEEDED`, `FAILED`, `BLOCKED` | confidence unless blocked | paid, replay | may precede a separate paid fallback record | none |
| `PAID_API` | `PAID_API` | paid-fallback execution path evaluated for a `FREE_API` request; authorization evidence determines approval or denial | `SUCCEEDED`, `FAILED`, `BLOCKED` | paid; confidence unless blocked | replay | mandatory decision evidence | none |
| `MANUAL_UI` | `MANUAL_UI` | user-mediated import execution classification | `SUCCEEDED`, `FAILED`, `BLOCKED` | confidence unless blocked | paid, replay | none | none |

Request-mode parity is exact:

- `LOCAL`, `REPLAY`, and `MANUAL_UI` require the same request mode.
- `FREE_API` requires request mode `FREE_API`.
- `PAID_API` also requires request mode `FREE_API`; it is not an
  `AlignmentRequestMode` and cannot appear in an `AlignmentRequest`.
- `PAID_API` does not itself imply authorization approval.
- `PAID_API` retains the request's exact `adapter_id` and `adapter_version`.
  A paid channel, tier, or authorization path may vary, but a different paid
  adapter identity requires a distinct `AlignmentRequest`.
- A different paid adapter requires a distinct `AlignmentRequest`.
- No provider brand, model, SDK, or endpoint is part of this enum.

Unknown values, aliases, case variants, arbitrary `str` subclasses, and other
Enum types are rejected without coercion.

## 8. Closed execution-status domain

**Specification decision:**

`AdapterExecutionStatus` is the exact public `str, Enum` declaration in
section 5.1. Its member names and `.value` strings are normative.

| Enum member | Exact serialized value | Meaning | Classification | Allowed modes | Required/forbidden evidence | Invalid combinations |
|---|---|---|---|---|---|---|
| `SUCCEEDED` | `SUCCEEDED` | adapter work completed and may have produced a downstream candidate | terminal | all modes | confidence required; mode-specific evidence per matrix | never means timings/result were published |
| `FAILED` | `FAILED` | adapter work started but did not complete successfully | terminal | all modes | confidence required and `NOT_APPLICABLE`; mode-specific evidence per matrix | never creates a failure artifact |
| `BLOCKED` | `BLOCKED` | adapter work did not start because an execution precondition or authorization denied it | terminal | `FREE_API`, `PAID_API`, `MANUAL_UI` | confidence forbidden; mode-specific evidence per matrix | invalid for `LOCAL` and `REPLAY` |

There are no non-terminal values. No transition API, retry state, mutable
lifecycle, or ordering between snapshots is defined.

## 9. Mode x status evidence matrix

**Specification decision:** `OPTIONAL` is not used.

| Mode | Status | Classification | Paid-fallback authorization | Replay evidence | Confidence-availability evidence |
|---|---|---|---|---|---|
| `LOCAL` | `SUCCEEDED` | VALID | FORBIDDEN | FORBIDDEN | REQUIRED |
| `LOCAL` | `FAILED` | VALID | FORBIDDEN | FORBIDDEN | REQUIRED |
| `LOCAL` | `BLOCKED` | INVALID | FORBIDDEN | FORBIDDEN | FORBIDDEN |
| `REPLAY` | `SUCCEEDED` | CONDITIONALLY VALID | FORBIDDEN | REQUIRED | REQUIRED |
| `REPLAY` | `FAILED` | CONDITIONALLY VALID | FORBIDDEN | REQUIRED | REQUIRED |
| `REPLAY` | `BLOCKED` | INVALID | FORBIDDEN | FORBIDDEN | FORBIDDEN |
| `FREE_API` | `SUCCEEDED` | VALID | FORBIDDEN | FORBIDDEN | REQUIRED |
| `FREE_API` | `FAILED` | VALID | FORBIDDEN | FORBIDDEN | REQUIRED |
| `FREE_API` | `BLOCKED` | VALID | FORBIDDEN | FORBIDDEN | FORBIDDEN |
| `PAID_API` | `SUCCEEDED` | CONDITIONALLY VALID | REQUIRED | FORBIDDEN | REQUIRED |
| `PAID_API` | `FAILED` | CONDITIONALLY VALID | REQUIRED | FORBIDDEN | REQUIRED |
| `PAID_API` | `BLOCKED` | CONDITIONALLY VALID | REQUIRED | FORBIDDEN | FORBIDDEN |
| `MANUAL_UI` | `SUCCEEDED` | VALID | FORBIDDEN | FORBIDDEN | REQUIRED |
| `MANUAL_UI` | `FAILED` | VALID | FORBIDDEN | FORBIDDEN | REQUIRED |
| `MANUAL_UI` | `BLOCKED` | VALID | FORBIDDEN | FORBIDDEN | FORBIDDEN |

`REPLAY` is conditionally valid only when section 11 lineage rules pass.
`PAID_API` is conditionally valid only when section 10 rules pass.
For `PAID_API`, `SUCCEEDED` and `FAILED` require `APPROVED`;
`BLOCKED` requires `DENIED`.

## 10. Paid-fallback authorization evidence

**Specification decision:**

`PaidFallbackAuthorizationSource` and
`PaidFallbackAuthorizationDecision` are the exact public `str, Enum`
declarations in section 5.1. Their member names and `.value` strings are
normative.

```text
PaidFallbackAuthorizationSource.USER_EXPLICIT = "USER_EXPLICIT"

PaidFallbackAuthorizationDecision.APPROVED = "APPROVED"
PaidFallbackAuthorizationDecision.DENIED = "DENIED"
```

The source domain is closed. Unknown, free-form, provider, URI, policy-name, or
credential-derived source values are forbidden.

- `PAID_API` identifies the paid-fallback execution path being evaluated; the
  mode alone is not an approval decision.
- Evidence existence: required only for `PAID_API`.
- Evidence identity: `authorization_id` identifies the immutable external
  decision and participates in the execution hash. It is not a secret,
  credential, receipt, or payment identifier.
- Evidence source: only `USER_EXPLICIT`.
- Evidence decision: `APPROVED` or `DENIED`.
- Evidence binding: both request identity fields must exactly match the
  current genuine request.
- `SUCCEEDED` and `FAILED` require `APPROVED`.
- `BLOCKED` requires `DENIED`.
- `DENIED` with any non-`BLOCKED` status is invalid.
- `APPROVED` with `BLOCKED` is invalid because this Slice defines no other
  paid-block reason.

Provider execution, billing, estimated or actual cost, payment result,
credential material, authorization token, URL, and provider response are
forbidden fields.

## 11. Replay evidence

**Specification decision:**

- Materializing `REPLAY` requires both the serialized `replay_evidence` object
  and a genuine exact materialized `AdapterExecution` dependency named
  `source_execution`.
- Pre-input validation checks a non-null `source_execution` only for exact
  type and genuine materialization. It does not decide mode compatibility.
- After the root `mode` is parsed, `REPLAY` requires a non-null
  `source_execution`; every non-`REPLAY` mode forbids it.
- The source must have status `SUCCEEDED`.
- The source mode must not be `REPLAY`.
- Source execution ID/hash must exactly match the dependency.
- Source request ID/hash must exactly match both the source execution and the
  current genuine request.
- The lineage representation is exactly one direct source object. Lists,
  ancestor arrays, multiple candidates, alternative parents, nested replay
  evidence, and free-form lineage are forbidden.
- `source_adapter_execution_id` must not equal the current supplied
  `adapter_execution_id`; direct self-reference is rejected before hash
  verification.
- A replay source that is itself `REPLAY` is rejected. This prevents a v1
  record from representing cycle-capable replay lineage.
- A missing, extra, ambiguous, copied, reconstructed, or mismatched source
  rejects publication.
- All replay fields participate in identity.

This section does not execute replay, retrieve cached bytes, orchestrate retry,
or define a replay result.

## 12. Confidence-availability evidence

**Specification decision:**

`ConfidenceAvailability` is the exact public `str, Enum` declaration in
section 5.1. Its member names and `.value` strings are normative.

```text
ConfidenceAvailability.AVAILABLE = "AVAILABLE"
ConfidenceAvailability.UNAVAILABLE = "UNAVAILABLE"
ConfidenceAvailability.NOT_APPLICABLE = "NOT_APPLICABLE"
```

- `AVAILABLE` means confidence data was available to a successful adapter
  execution. It says nothing about score or quality.
- `UNAVAILABLE` means the successful adapter execution declared confidence
  support through its bound request capability, but confidence data was not
  available.
- `NOT_APPLICABLE` means confidence cannot apply to this provenance snapshot
  because the adapter capability is `UNSUPPORTED` or status is `FAILED`.
- For `SUCCEEDED` plus request capability `SUPPORTED`, only `AVAILABLE` or
  `UNAVAILABLE` is valid.
- For `SUCCEEDED` plus request capability `UNSUPPORTED`, only
  `NOT_APPLICABLE` is valid.
- For `FAILED`, only `NOT_APPLICABLE` is valid.
- For `BLOCKED`, the evidence field must be JSON `null`; an evidence object is
  forbidden because no execution occurred.

Numeric confidence, word-level confidence, provider confidence payload,
threshold, warning/blocker quality classification, and score aggregation are
forbidden.

## 13. Immutability contract

**Specification decision:**

- Root and evidence objects are exact frozen dataclasses; public subclass
  instances are never genuine.
- All constructor mappings are parsed into exact scalar/enum/frozen-object
  fields. Caller mappings are never retained.
- No valid v1 field stores a mutable mapping or sequence.
- Mutation of source mappings or any rejected nested sequence after
  construction cannot affect an object or its bytes.
- Mutation attempts on public fields fail through frozen-dataclass behavior.
- Enum members and evidence objects are immutable.
- A canonical byte cache, if used, is private and stores only immutable
  `bytes`; callers receive immutable bytes.
- Private projection/envelope mappings are fresh values or recursively
  read-only. Mutating a returned or test-visible copy cannot affect the
  genuine object.
- Copy, deep copy, pickle reconstruction, `dataclasses.replace`, direct
  constructor use, `object.__new__`, subclassing, proxying, and field cloning
  do not mint materialization provenance.
- Genuine-instance registration uses exact type plus weak identity. Failed
  registration publishes nothing and cleanup cannot delete a replacement
  entry installed under the same identity key.

## 14. Canonical serialization

**Specification decision:** Serialization uses the repository
`engine.contracts._canonical_json.encode_canonical_json_bytes` behavior.

- Encoding: UTF-8, without BOM.
- Object keys: exact built-in strings, sorted by Unicode code point.
- Enum values: exact serialized strings.
- Booleans: lowercase JSON `true`/`false`; no valid v1 field uses a boolean.
- Null policy: the three evidence keys always exist. Forbidden/absent
  conditional evidence is JSON `null`; no field is omitted.
- Optional-field omission: forbidden. Every root key and every key of a
  present evidence object is required.
- Arrays: no valid v1 field is an array. Any array in a defined field is
  rejected; unknown array fields are rejected as unknown.
- Unicode: exact built-in strings, valid Unicode, NFC, no surrogate,
  noncharacter, NUL, C0/C1 control, path, URI, or sensitive material.
- Whitespace: no insignificant whitespace and no trailing newline.
- Numbers: all JSON numbers, including integers, floats, negative zero,
  non-finite values, and booleans substituted for numbers, are forbidden
  because v1 has no numeric field.
- String escaping: quote and backslash use `\"` and `\\`; U+0000-U+001F
  would use lowercase `\u00xx`, but such controls are rejected by this
  contract before publication.
- Duplicate keys: `load_adapter_execution` rejects them before
  materialization or hashing.
- Unknown fields: rejected at root and every evidence-object level.
- `load_adapter_execution` accepts only exact canonical envelope bytes. A
  semantically equivalent envelope with alternate key order, whitespace,
  escape spelling, decomposed Unicode, BOM, or trailing newline is rejected as
  non-canonical.

## 15. Canonical identity and hashing

**Specification decision:**

- Projection: every root field except `adapter_execution_id` and
  `adapter_execution_hash`, including explicit evidence `null` values.
- Projection bytes: section 14 canonical UTF-8 bytes.
- Hash algorithm: SHA-256.
- `adapter_execution_hash`: lowercase 64-character hex digest of projection
  bytes, without a `sha256:` prefix.
- `adapter_execution_id`: `aex_` plus the first 32 digest characters.
- Envelope: projection fields plus the verified ID and hash.
- Every semantic field participates in identity. There is no non-identity
  metadata in v1.
- Runtime result, provider payload, timing, billing, latency, timestamp, retry,
  and mutable orchestration data cannot participate because they are forbidden.
- Hash mismatch is rejected before derived-ID mismatch.
- Derived-ID mismatch is rejected after the hash matches.
- Rejection publishes no ID, hash, canonical bytes, execution object, result,
  report, provenance substitute, or failure artifact.

## 16. Publication boundary

**Specification decision:**

- Public module: `engine.contracts.alignment_execution`.
- Consumer import path: `engine.contracts`.
- `engine/contracts/__init__.py` shall import and add exactly the section 5.1
  symbol delta to `__all__`; existing exports remain unchanged.
- Parsing, canonical projection/envelope helpers, sensitive scanners,
  genuine-instance registry, and registration predicates remain private.
- `engine.contracts.alignment_execution` may import
  `engine.contracts.alignment`, `engine.contracts.temporal`, and the private
  canonical JSON encoder.
- `engine.contracts.alignment` must not import
  `engine.contracts.alignment_execution`. `temporal.py` must not import either
  alignment module. This direction forbids an import cycle.
- A valid terminal `AdapterExecution` envelope is the only publication of
  this Slice. `SUCCEEDED`, `FAILED`, and `BLOCKED` can each publish this
  provenance when valid.
- Publication is atomic: validation and serialization verification complete
  before genuine-instance registration; registration failure leaves no
  genuine object. No other artifact is created or rolled back.

## 17. Deterministic validation order

**Specification decision:** The first failing stage is authoritative.

1. Validate `alignment_request` exact type and genuine materialization. A
   wrong-type or exact-type-but-non-genuine dependency raises `TypeError`
   before `AdapterExecutionContractError` validation. Raw root input is not
   accessed before this check.
2. When `source_execution` is non-null, validate its exact type and genuine
   materialization. A null value is accepted at this stage. Required or
   forbidden presence is not decided before mode parsing, and raw root input
   is not accessed before validation of any non-null dependency.
3. Root input type, exact key set, missing fields, unknown fields, duplicate
   keys for byte input, and exact built-in scalar/object/null types.
4. Validate root `schema_version` and `hash_scope_version`.
5. Parse closed root enums without coercion, in field order `mode`, then
   `status`.
6. Apply `source_execution` presence compatibility using the parsed mode:
   `REPLAY` requires a genuine non-null dependency; `LOCAL`, `FREE_API`,
   `PAID_API`, and `MANUAL_UI` forbid a present dependency.
7. Validate request binding syntax, then request ID/hash parity against the
   genuine request.
8. Validate adapter ID/version parity and execution-mode/request-mode
   compatibility.
9. Validate mode/status compatibility.
10. Validate evidence presence/null rules in order paid, replay, confidence.
11. Validate paid-fallback nested structure and enums, authorization binding,
    and
    decision/status invariants.
12. Validate replay nested structure, source identity/hash parity, request parity,
    direct self-reference, ambiguity, and cycle-capable lineage checks.
13. Validate confidence nested structure and enum, then capability/status
    state invariants.
14. Perform the full sensitive-data scan over the supplied logical object.
15. Encode the canonical projection and validate the supplied
    `adapter_execution_hash`.
16. Validate the derived `adapter_execution_id`.
17. For byte input only, validate exact source-byte equality with the canonical
    envelope.
18. Perform immutable construction, canonical envelope encoding verification,
    and
    genuine-instance registration.

Within a key-set failure, the lexicographically first unknown pointer wins;
otherwise missing-required-field rejection uses the containing object pointer.

Raw root input is not accessed before `alignment_request` validation and
validation of any non-null `source_execution` dependency. Whether
`source_execution` is required or forbidden is not decided before mode
parsing. `REPLAY` requires a genuine non-null `source_execution`. Every
non-`REPLAY` mode forbids `source_execution`. This deterministic validation
order is implementable and has no mode-before-input dependency.

## 18. Error contract

**Specification decision:**

```text
class AdapterExecutionContractError(ValueError)
```

It carries only:

```text
pointer: str
reason: AdapterExecutionRejectionReason
issue_code: str | None
```

`pointer` is a sanitized exact built-in string. `reason` is an exact member:

`AdapterExecutionRejectionReason` is the exact public `str, Enum` declaration
in section 5.1. Every listed member has the identical uppercase string as its
exact `.value`; no other member or alias exists.

Stable message categories are the exact reason value prefixed by
`Adapter execution rejected: `. Raw values, paths, URIs, credentials, provider
payloads, and source exception text are never interpolated.

This Slice adds no stable issue code. `issue_code`, when non-null, must be an
exact existing inventory member:

| Rejection | Exact issue code |
|---|---|
| unknown mode/status/evidence enum | `UNSUPPORTED_CONTRACT_ENUM` |
| request ID/hash parity failure | `ALIGNMENT_REQUEST_IDENTITY_MISMATCH` |
| missing, forbidden, malformed, mismatched, or denied-in-nonblocked paid evidence | `PAID_FALLBACK_UNAUTHORIZED` |
| replay request/source ID mismatch or ambiguous lineage | `REPLAY_INPUT_MISMATCH` |
| replay source execution hash mismatch | `REPLAY_HASH_MISMATCH` |
| all other contract-shape, state, canonical-byte, identity, and materialization rejections | `None` |

Unknown object fields are `STRUCTURE_INVALID`. Invalid known mode/status pairs
are `MODE_STATUS_INVALID`. Invalid evidence presence is
`EVIDENCE_PRESENCE_INVALID`. Hash mismatch points to
`/adapter_execution_hash`; derived-ID mismatch points to
`/adapter_execution_id`. Replay self-reference and replay-of-replay use
`REPLAY_LINEAGE_INVALID`.

Unknown fields and non-canonical serialized bytes publish nothing. Mutation of
a frozen public field raises standard frozen-dataclass `FrozenInstanceError`
or `AttributeError`; it is not converted into a serialized contract error.
Serialization of a non-genuine object raises `NOT_MATERIALIZED`.

`alignment_request` prerequisite dependency failures are exact:

| Condition | Exception class | Pointer | Reason | Issue code | Message stability |
|---|---|---|---|---|---|
| invalid exact type for `alignment_request` | `TypeError` | not applicable | not applicable | not applicable | sanitized category identifies `alignment_request`; exact text is not stable |
| exact `AlignmentRequest` type but not a genuine materialized instance | `TypeError` | not applicable | not applicable | not applicable | sanitized category identifies `alignment_request`; exact text is not stable |

These failures occur before `AdapterExecutionContractError` validation and
before root input access. They intentionally follow the established
prerequisite contract convention and do not carry pointer,
`AdapterExecutionRejectionReason`, or issue-code fields.

Slice-owned `source_execution` dependency-parameter failures are exact:

| Condition | Pointer | Reason | Issue code |
|---|---|---|---|
| invalid exact type for non-null `source_execution` | `/source_execution` | `NOT_MATERIALIZED` | `None` |
| non-null `source_execution` is not a genuine materialized instance | `/source_execution` | `NOT_MATERIALIZED` | `None` |
| parsed `REPLAY` mode with `source_execution=None` | `/source_execution` | `REPLAY_EVIDENCE_INVALID` | `REPLAY_INPUT_MISMATCH` |
| parsed non-`REPLAY` mode with present `source_execution` | `/source_execution` | `REPLAY_EVIDENCE_INVALID` | `REPLAY_INPUT_MISMATCH` |

The first two rows are pre-input failures. The last two rows are evaluated
only after mode parsing. They reuse existing rejection reasons and stable issue
codes; no new hierarchy or issue code is introduced.

The difference between the two dependency boundaries is intentional:
`alignment_request` follows the established prerequisite contract convention,
while `source_execution` is a Slice-owned dependency boundary specified by
this candidate and therefore uses `AdapterExecutionContractError`.

## 19. Golden canonical oracle

**Specification decision:** `FX-AEX-01` is the required time-independent
golden example.

Projection-source semantic values:

```text
schema_version=ADAPTER-EXECUTION-V1
hash_scope_version=ADAPTER-EXECUTION-HASH-V1
alignment_request_id=arq_bfd2a97af22b1f105c2ebe9356ce2fe6
alignment_request_hash=bfd2a97af22b1f105c2ebe9356ce2fe684b0add89be14fea09e6b21cfbe54e51
adapter_id=adapter_fxarq
adapter_version=1.0.0
mode=LOCAL
status=SUCCEEDED
paid_fallback_authorization_evidence=null
replay_evidence=null
confidence_availability_evidence=object
confidence_availability_evidence.schema_version=CONFIDENCE-AVAILABILITY-EVIDENCE-V1
confidence_availability_evidence.availability=AVAILABLE
```

Complete materialization envelope values:

```text
schema_version=ADAPTER-EXECUTION-V1
hash_scope_version=ADAPTER-EXECUTION-HASH-V1
adapter_execution_id=aex_183e432fedb7c26e2339909ed805cd49
adapter_execution_hash=183e432fedb7c26e2339909ed805cd49eddfafd47eb217ed3e393c5cb6462aa7
alignment_request_id=arq_bfd2a97af22b1f105c2ebe9356ce2fe6
alignment_request_hash=bfd2a97af22b1f105c2ebe9356ce2fe684b0add89be14fea09e6b21cfbe54e51
adapter_id=adapter_fxarq
adapter_version=1.0.0
mode=LOCAL
status=SUCCEEDED
paid_fallback_authorization_evidence=null
replay_evidence=null
confidence_availability_evidence=object
confidence_availability_evidence.schema_version=CONFIDENCE-AVAILABILITY-EVIDENCE-V1
confidence_availability_evidence.availability=AVAILABLE
```

The derived ID and hash are excluded from the canonical projection but are
required supplied fields of the canonical envelope accepted by
`materialize_adapter_execution` and `load_adapter_execution`.

Canonical projection text:

```json
{"adapter_id":"adapter_fxarq","adapter_version":"1.0.0","alignment_request_hash":"bfd2a97af22b1f105c2ebe9356ce2fe684b0add89be14fea09e6b21cfbe54e51","alignment_request_id":"arq_bfd2a97af22b1f105c2ebe9356ce2fe6","confidence_availability_evidence":{"availability":"AVAILABLE","schema_version":"CONFIDENCE-AVAILABILITY-EVIDENCE-V1"},"hash_scope_version":"ADAPTER-EXECUTION-HASH-V1","mode":"LOCAL","paid_fallback_authorization_evidence":null,"replay_evidence":null,"schema_version":"ADAPTER-EXECUTION-V1","status":"SUCCEEDED"}
```

```text
Canonical projection UTF-8 byte length:
521

Canonical projection SHA-256:
183e432fedb7c26e2339909ed805cd49eddfafd47eb217ed3e393c5cb6462aa7

Derived identifier:
aex_183e432fedb7c26e2339909ed805cd49
```

Canonical envelope text:

```json
{"adapter_execution_hash":"183e432fedb7c26e2339909ed805cd49eddfafd47eb217ed3e393c5cb6462aa7","adapter_execution_id":"aex_183e432fedb7c26e2339909ed805cd49","adapter_id":"adapter_fxarq","adapter_version":"1.0.0","alignment_request_hash":"bfd2a97af22b1f105c2ebe9356ce2fe684b0add89be14fea09e6b21cfbe54e51","alignment_request_id":"arq_bfd2a97af22b1f105c2ebe9356ce2fe6","confidence_availability_evidence":{"availability":"AVAILABLE","schema_version":"CONFIDENCE-AVAILABILITY-EVIDENCE-V1"},"hash_scope_version":"ADAPTER-EXECUTION-HASH-V1","mode":"LOCAL","paid_fallback_authorization_evidence":null,"replay_evidence":null,"schema_version":"ADAPTER-EXECUTION-V1","status":"SUCCEEDED"}
```

```text
Canonical envelope UTF-8 byte length:
675

Canonical envelope SHA-256:
f874ae7027af4eb1e251bdced9933d11da112d3d56c403f1a32b4627512d4c58
```

## 20. Normative invalid examples

| Example | Invalid input | Expected exception/reason | Expected pointer / issue code |
|---|---|---|---|
| Unknown mode | `mode="LOCAL_API"` | `UNSUPPORTED_VALUE` | `/mode` / `UNSUPPORTED_CONTRACT_ENUM` |
| Unknown status | `status="COMPLETE"` | `UNSUPPORTED_VALUE` | `/status` / `UNSUPPORTED_CONTRACT_ENUM` |
| Root enum alias/coercion | `mode=CustomString("LOCAL")` or an arbitrary Enum member | `UNSUPPORTED_VALUE` | `/mode` / `UNSUPPORTED_CONTRACT_ENUM` |
| Paid source alias/coercion | paid `source` is a case variant, `str` subclass, or arbitrary Enum member | `PAID_FALLBACK_AUTHORIZATION_INVALID` | `/paid_fallback_authorization_evidence/source` / `PAID_FALLBACK_UNAUTHORIZED` |
| Confidence alias/coercion | `availability` is a case variant, `str` subclass, or arbitrary Enum member | `CONFIDENCE_AVAILABILITY_INVALID` | `/confidence_availability_evidence/availability` / `None` |
| Wrong-type request dependency | `alignment_request` is a subclass, proxy, or any value that is not exact `AlignmentRequest` type | `TypeError`; rejection reason not applicable | pointer not applicable / issue code not applicable; sanitized message category identifies `alignment_request`, exact text not stable; root input not accessed |
| Non-genuine request dependency | distinct exact `AlignmentRequest` reconstructed, copied, replaced, or otherwise unregistered | `TypeError`; rejection reason not applicable | pointer not applicable / issue code not applicable; sanitized message category identifies `alignment_request`, exact text not stable; root input not accessed |
| Disallowed pair | `LOCAL/BLOCKED` | `MODE_STATUS_INVALID` | `/status` / `None` |
| Missing request ID | omit `alignment_request_id` | `STRUCTURE_INVALID` | `/` / `None` |
| Missing request hash | omit `alignment_request_hash` | `STRUCTURE_INVALID` | `/` / `None` |
| Request ID/hash mismatch | use another genuine request's ID or hash | `REQUEST_BINDING_INVALID` | mismatched binding pointer / `ALIGNMENT_REQUEST_IDENTITY_MISMATCH` |
| Paid adapter identity mismatch | approved `PAID_API` input changes `adapter_id` or `adapter_version` from the bound request | `REQUEST_BINDING_INVALID` | mismatched adapter pointer / `ALIGNMENT_REQUEST_IDENTITY_MISMATCH` |
| Missing paid evidence | `PAID_API/SUCCEEDED` with null evidence | `EVIDENCE_PRESENCE_INVALID` | `/paid_fallback_authorization_evidence` / `PAID_FALLBACK_UNAUTHORIZED` |
| Forbidden paid evidence | `LOCAL/SUCCEEDED` with evidence | `EVIDENCE_PRESENCE_INVALID` | paid pointer / `PAID_FALLBACK_UNAUTHORIZED` |
| Invalid paid evidence | `PAID_API/SUCCEEDED`, decision `DENIED` | `PAID_FALLBACK_AUTHORIZATION_INVALID` | `/paid_fallback_authorization_evidence/decision` / `PAID_FALLBACK_UNAUTHORIZED` |
| Missing replay evidence | `REPLAY/SUCCEEDED` with null evidence | `EVIDENCE_PRESENCE_INVALID` | `/replay_evidence` / `REPLAY_INPUT_MISMATCH` |
| Forbidden replay evidence | `FREE_API/SUCCEEDED` with replay evidence | `EVIDENCE_PRESENCE_INVALID` | `/replay_evidence` / `REPLAY_INPUT_MISMATCH` |
| Missing replay source dependency | parsed `REPLAY` input with `source_execution=None` | `REPLAY_EVIDENCE_INVALID` | `/source_execution` / `REPLAY_INPUT_MISMATCH` |
| Forbidden replay source dependency | parsed non-`REPLAY` input with genuine `source_execution` present | `REPLAY_EVIDENCE_INVALID` | `/source_execution` / `REPLAY_INPUT_MISMATCH` |
| Non-genuine replay source dependency | non-null copied, reconstructed, proxied, subclassed, or wrong-type `source_execution` | `NOT_MATERIALIZED` | `/source_execution` / `None` |
| Replay self-reference | source ID equals supplied current ID | `REPLAY_LINEAGE_INVALID` | `/replay_evidence/source_adapter_execution_id` / `REPLAY_INPUT_MISMATCH` |
| Ambiguous/cycle-capable lineage | extra parent array, multiple source keys, or source mode `REPLAY` | `REPLAY_LINEAGE_INVALID` | `/replay_evidence` / `REPLAY_INPUT_MISMATCH` |
| Missing confidence evidence | `LOCAL/SUCCEEDED` with null evidence | `EVIDENCE_PRESENCE_INVALID` | `/confidence_availability_evidence` / `None` |
| Forbidden confidence evidence | `FREE_API/BLOCKED` with evidence object | `EVIDENCE_PRESENCE_INVALID` | confidence pointer / `None` |
| Invalid confidence state | successful `SUPPORTED` request with `NOT_APPLICABLE` | `CONFIDENCE_AVAILABILITY_INVALID` | `/confidence_availability_evidence/availability` / `None` |
| Unknown object field | add root or nested `extra` | `STRUCTURE_INVALID` | lexicographically first unknown pointer / `None` |
| Non-canonical serialized input | add whitespace or reorder byte-input keys | `NON_CANONICAL_SERIALIZATION` | `/` / `None` |
| Canonical hash mismatch | replace execution hash with lowercase zero hash | `IDENTITY_MISMATCH` | `/adapter_execution_hash` / `None` |
| Derived identifier mismatch | correct hash plus wrong execution ID | `IDENTITY_MISMATCH` | `/adapter_execution_id` / `None` |

Every rejection produces no genuine `AdapterExecution`.

## 21. Mutation-resistance matrix

| Mutation class | Required future test and expected behavior |
|---|---|
| Top-level constructor argument mutation | mutate source mapping after materialization; object, bytes, hash, and ID remain unchanged |
| Nested mapping mutation | mutate a paid/replay/confidence input mapping; frozen evidence and envelope remain unchanged |
| Nested sequence mutation | inject a list into any defined or unknown field; materialization rejects it, and later list mutation cannot create a genuine object |
| Paid-fallback evidence mutation | frozen-field assignment fails; source mapping mutation has no effect |
| Replay evidence mutation | frozen-field assignment fails; source substitution requires rematerialization and rehash |
| Confidence evidence mutation | frozen-field assignment fails; enum substitution is rejected |
| Source input mutation after construction | all canonical outputs remain byte-identical |
| Canonical bytes mutation attempt | returned `bytes` cannot be mutated; mutable copy changes no object state |
| Returned mapping mutation | any private/test projection copy can be mutated without changing the genuine object |
| Returned sequence mutation | no public sequence is returned; any test-helper copy is caller-owned and cannot change object state |
| Enum substitution | arbitrary Enum, `str` subclass, alias, case variant, or spelling variant is rejected |
| Hash substitution | mismatch rejects before ID verification and publishes nothing |
| Request-binding substitution | different request ID/hash or forged dependency rejects before hashing |
| Replay-lineage substitution | different, copied, replay-mode, failed, ambiguous, or self-referential source rejects |

Registry tests shall also cover collection cleanup, stale cleanup replacement
safety, insertion failure, verification false/exception rollback, subclass,
proxy, copy, deep copy, pickle, and reconstructed dataclass rejection.

## 22. Future test plan

The focused future path is:

```text
tests/test_alignment_execution.py
```

It shall contain:

- golden contract tests for exact projection/envelope text, bytes, lengths,
  hashes, and derived ID;
- canonical serialization tests for UTF-8, ordering, nulls, whitespace,
  Unicode, duplicate keys, unknown fields, and non-canonical byte rejection;
- canonical projection and envelope SHA-256 tests;
- derived-ID syntax, truncation, mismatch, and hash-first precedence tests;
- exact public `str, Enum` inheritance, declaration identity, member names,
  serialized `.value` strings, no-alias, no-unknown-member, no-case-folding,
  no-arbitrary-Enum-coercion, no-`str`-subclass-coercion, and public import
  identity tests;
- all 15 mode/status matrix rows;
- every required/forbidden evidence-presence boundary;
- genuine `AlignmentRequest` binding, adapter parity, and request-mode parity;
- approved paid fallback retaining the exact request adapter identity, plus
  rejection of a different paid adapter ID or version;
- paid-fallback source, decision, ID, binding, and forbidden-data tests;
- replay source identity/hash/request parity, self-reference, ambiguity, and
  replay-of-replay rejection tests;
- confidence availability/capability/status tests without numeric confidence;
- pre-input dependency validation tests proving that invalid
  `alignment_request` and any invalid non-null `source_execution` reject
  before raw root access;
- wrong-type and exact-type-but-non-genuine `alignment_request` preflight
  tests proving exact `TypeError`, non-applicable pointer/reason/issue-code,
  a sanitized message category identifying `alignment_request`, no
  exact-message assertion because message text is non-stable, and raw-input
  non-access;
- tests proving that `alignment_request` follows the prerequisite `TypeError`
  boundary while invalid/non-genuine `source_execution` uses
  `AdapterExecutionContractError` with pointer `/source_execution`, reason
  `NOT_MATERIALIZED`, and issue code `None`;
- mode-dependent `source_execution` presence tests proving `REPLAY` requires
  it and every non-`REPLAY` mode forbids it only after mode parsing;
- multi-fault ordering where an invalid non-null `source_execution` wins
  before raw input access;
- multi-fault ordering where `source_execution` absence/presence compatibility
  is evaluated only after root mode parsing;
- multi-fault deterministic validation-order tests;
- exact error type, reason, pointer, message-category, issue-code, and
  no-leak tests;
- the complete mutation-resistance matrix;
- public import and exact `__all__` delta tests;
- regressions against Slice 4 `AlignmentRequest`, its golden oracle, genuine
  provenance registry, and existing stable issue inventory.

Existing prerequisite tests, including `tests/test_alignment_request.py` and
`tests/test_temporal_raw_package.py`, shall not be changed merely to satisfy
this candidate drafting task. No test code is authorized by this document.

## 23. Specification acceptance gates

The required future sequence is:

1. Manual specification verification.
2. Independent Terra read-only audit.
3. Bounded corrections, if required.
4. Specification commit.
5. Exact-SHA commit verification.
6. Remote push verification.
7. Documentation synchronization.
8. Separate implementation authorization.

Implementation cannot begin until the specification is accepted, remote
closed, and documentation-synchronized. Acceptance of this specification,
when it occurs, will not itself authorize implementation.

## 24. Explicit in-scope and out-of-scope boundary

This specification defines only immutable execution provenance bound to
`AlignmentRequest`, closed execution modes/statuses, evidence presence,
canonical request and adapter binding, paid authorization evidence, replay
lineage evidence, confidence availability evidence, immutable canonical
serialization, identity, hashing, publication, errors, golden oracles, and
future mutation-resistant tests.

It does not define or implement provider execution, alignment runtime
execution, external API calls, canonical word timing result, word timing
success artifact, failure artifact, `AlignmentReport`, transcript divergence,
quality or publication gates for timing, correction application, replay
execution, retry orchestration, paid provider invocation, provider selection,
phrase grouping, emphasis mapping, frame compilation, caption preview,
Phase 3 EDL or frame compilation, UI behavior, database persistence, queueing,
network protocol, operational monitoring, billing calculation, payment
result, or mutable execution lifecycle.

## 25. Explicit non-claims

Slice 5 is not implemented.

This candidate specification is not yet accepted.

No runtime alignment execution exists because of this specification.

No canonical word timing result is defined by this specification.

No failure artifact or AlignmentReport is defined by this specification.

Implementation is not authorized.

Phase 2 is not closed.

The total Phase 2 Slice count is not established here.
