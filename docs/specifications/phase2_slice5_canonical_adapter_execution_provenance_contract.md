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

- **Current AlignmentRequest binding:** the required pair
  `alignment_request_id` and `alignment_request_hash`, validated against one
  genuine, materialized current `AlignmentRequest`. These are the root
  `AdapterExecution` binding fields.
- **Source AlignmentRequest dependency:** for `REPLAY` only, one genuine,
  materialized `AlignmentRequest` originally bound to `source_execution`.
  Its identity is carried only by `ReplayEvidence`; it is distinct in role
  and identity from the current replay request.
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
  non-replay source execution and that execution's genuine original request.
  It never asserts that the source request is the current replay request.
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
    source_alignment_request: AlignmentRequest | None = None,
    source_execution: AdapterExecution | None = None,
) -> AdapterExecution

def load_adapter_execution(
    source: bytes,
    *,
    alignment_request: AlignmentRequest,
    source_alignment_request: AlignmentRequest | None = None,
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
When `source_alignment_request` is non-null, both materializers next validate
only its exact `AlignmentRequest` type and genuine materialization. When
`source_execution` is non-null, they then validate only its exact
`AdapterExecution` type and genuine materialization. These Slice-owned
dependency failures use `AdapterExecutionContractError` as specified in
sections 17 and 18. Null values are accepted during pre-input validation;
mode-dependent presence is not decided before root mode parsing.

After root structure and the closed `mode` enum have been parsed,
both `source_alignment_request` and `source_execution` are required for
`REPLAY` and forbidden for `LOCAL`, `FREE_API`, `PAID_API`, and `MANUAL_UI`.
Presence is checked in that exact parameter order. `load_adapter_execution`
applies the same dependency and semantic validation as
`materialize_adapter_execution` before its final exact-byte check.

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
| `source_alignment_request_id` | `str` | required | JSON string | source request binding | exact genuine source request ID; not the current replay request ID | yes | object present | mismatch or role confusion |
| `source_alignment_request_hash` | `str` | required | JSON string | source request binding | exact genuine source request hash; not the current replay request hash | yes | object present | mismatch or role confusion |

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

- The repository `AlignmentRequest` model has no source-request or
  source-execution reference. Its identity projection includes `mode`.
  Therefore Model A, an existing request-carried source binding, is not
  available. This specification selects Model B, an explicit genuine source
  request dependency, as the smallest repository-supported complete replay
  proof.
- Both root `alignment_request_id` and `alignment_request_hash` are required
  and always identify the current genuine request.
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
- For `REPLAY`, `source_alignment_request` is a second genuine exact
  `AlignmentRequest` dependency. It is the request originally bound to
  `source_execution`; it is not stored as a new root field.
- `ReplayEvidence.source_alignment_request_id` and
  `ReplayEvidence.source_alignment_request_hash` must exactly equal the
  source request dependency. The source execution's own request ID/hash must
  also exactly equal that dependency.
- The current `REPLAY` request and source non-`REPLAY` request have distinct
  roles and must have different ID and hash values. Neither source request
  field is compared for equality with the current root request field.
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

- For the current execution, `LOCAL`, `REPLAY`, and `MANUAL_UI` require the
  same current request mode.
- `FREE_API` requires request mode `FREE_API`.
- `PAID_API` also requires request mode `FREE_API`; it is not an
  `AlignmentRequestMode` and cannot appear in an `AlignmentRequest`.
- `PAID_API` does not itself imply authorization approval.
- `PAID_API` retains the request's exact `adapter_id` and `adapter_version`.
  A paid channel, tier, or authorization path may vary, but a different paid
  adapter identity requires a distinct `AlignmentRequest`.
- A different paid adapter requires a distinct `AlignmentRequest`.
- For a `REPLAY` execution, the current request mode is `REPLAY`.
  `source_alignment_request.mode` must not be `REPLAY`.
  `source_execution.mode` must not be `REPLAY` and must satisfy the same
  parity rule against the source request: `LOCAL` and `MANUAL_UI` require the
  identical source request mode; `FREE_API` requires source request mode
  `FREE_API`; `PAID_API` also requires source request mode `FREE_API`.
- Because request mode participates in `AlignmentRequest` identity, current
  replay request identity and source non-replay request identity are required
  to differ. This difference is valid and is not a request-binding failure.
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

`REPLAY` is conditionally valid only when section 11 lineage rules pass with
both a genuine source request and a genuine successful non-replay source
execution. The current replay request and source request identities are
distinct. These rules make both `REPLAY/SUCCEEDED` and `REPLAY/FAILED`
constructible without changing any matrix row.
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

- Materializing `REPLAY` requires the serialized `replay_evidence` object,
  one genuine exact materialized `AlignmentRequest` dependency named
  `source_alignment_request`, and one genuine exact materialized
  `AdapterExecution` dependency named `source_execution`.
- The current root `alignment_request_id` and `alignment_request_hash` remain
  bound only to the current genuine replay request.
- Pre-input validation checks a non-null `source_alignment_request` only for
  exact `AlignmentRequest` type and genuine materialization, then checks a
  non-null `source_execution` only for exact `AdapterExecution` type and
  genuine materialization. It does not decide mode compatibility or required
  presence.
- After the root `mode` is parsed, `REPLAY` requires both dependencies.
  Every non-`REPLAY` mode forbids both dependencies.
- `source_alignment_request.mode` must not be `REPLAY`.
- `source_execution.status` must be `SUCCEEDED`.
- `source_execution.mode` must not be `REPLAY` and must satisfy section 7
  parity against `source_alignment_request`.
- `source_execution.alignment_request_id` and
  `source_execution.alignment_request_hash` must exactly equal
  `source_alignment_request.alignment_request_id` and
  `source_alignment_request.alignment_request_hash`.
- `ReplayEvidence.source_alignment_request_id` and
  `ReplayEvidence.source_alignment_request_hash` must exactly equal that same
  genuine source request dependency.
- Source execution ID/hash in `ReplayEvidence` must exactly match
  `source_execution`.
- Before any lineage comparison, replay scalar syntax is closed:
  `source_adapter_execution_id` is exact built-in `str` matching
  `aex_[0-9a-f]{32}`; `source_adapter_execution_hash` is exact built-in `str`
  matching `[0-9a-f]{64}`; `source_alignment_request_id` is exact built-in
  `str` matching `arq_[0-9a-f]{32}`; and
  `source_alignment_request_hash` is exact built-in `str` matching
  `[0-9a-f]{64}`.
- The source request ID/hash must not equal the current replay request
  ID/hash. Equality is role confusion, not valid replay binding.
- The lineage representation is exactly one direct source object. Lists,
  ancestor arrays, multiple candidates, alternative parents, nested replay
  evidence, and free-form lineage are forbidden.
- `source_adapter_execution_id` must not equal the current supplied
  `adapter_execution_id`; direct self-reference is rejected before hash
  verification.
- A replay source that is itself `REPLAY` is rejected. This prevents a v1
  record from representing cycle-capable replay lineage.
- A source request whose mode is `REPLAY` is also rejected. Together with the
  source execution mode rule and single direct-source schema, this prevents
  cycle-capable replay lineage.
- A missing, extra, ambiguous, copied, reconstructed, role-confused, or
  mismatched dependency rejects publication.
- All replay fields participate in identity.

This section does not execute replay, retrieve cached bytes, orchestrate retry,
look up a request or execution by ID/hash, or define a replay result. Genuine
dependency objects are the complete proof; unverified strings, provider state,
runtime lookup, database lookup, network access, mutable cache lookup, and
future timing artifacts are not accepted as lineage evidence.

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
- `source_alignment_request` and `source_execution` are validation
  dependencies, not retained mutable inputs and not new serialized root
  fields. Their frozen values are copied only into the already-defined
  `ReplayEvidence` scalar identity fields. Mutation, replacement, collection,
  or registry cleanup after successful materialization cannot change the
  execution object, bytes, hash, or ID.
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
- The module may use the existing private exact-type/weak-identity predicate
  from `engine.contracts.alignment` to validate both current and source
  `AlignmentRequest` dependencies. It owns the equivalent private predicate
  for `AdapterExecution`.
- `engine.contracts.alignment` must not import
  `engine.contracts.alignment_execution`. `temporal.py` must not import either
  alignment module. This direction forbids an import cycle.
- A valid terminal `AdapterExecution` envelope is the only publication of
  this Slice. `SUCCEEDED`, `FAILED`, and `BLOCKED` can each publish this
  provenance when valid.
- Publication is atomic: validation and serialization verification complete
  before genuine-instance registration; registration failure leaves no
  genuine object. No other artifact is created or rolled back.
- Source dependency objects are never registered by this materializer,
  modified, published, or looked up by string identity. Their genuine
  registries are read only for validation.

## 17. Deterministic validation order

**Specification decision:** The first failing stage is authoritative.

1. Validate `alignment_request` exact type and genuine materialization. A
   wrong-type or exact-type-but-non-genuine dependency raises `TypeError`
   before `AdapterExecutionContractError` validation. Raw root input is not
   accessed before this check.
2. When `source_alignment_request` is non-null, validate its exact
   `AlignmentRequest` type and genuine materialization. A null value is
   accepted at this stage. A failure uses the exact Slice-owned dependency
   mapping in section 18.
3. When `source_execution` is non-null, validate its exact
   `AdapterExecution` type and genuine materialization. A null value is
   accepted at this stage. A failure uses the exact Slice-owned dependency
   mapping in section 18. Raw root input is not accessed before all three
   dependency preflight stages finish.
4. Parse byte input and validate root mapping type, exact built-in key types,
   duplicate root or nested keys, and the exact root key set. Root key-set
   validation applies unknown-key rejection before missing-required-key
   rejection. It then validates exact built-in root scalar/object/null types
   and evidence-object/null shape. In particular, root `mode` and `status`
   must satisfy `type(value) is str` at this stage. Nested evidence key sets
   and nested scalar types are deferred to their owning stages 12, 13, and
   14. Duplicate-key pointers use the containing-object algorithm in section
   18.
5. Validate root `schema_version` and `hash_scope_version`.
6. Parse closed root enums without coercion, in field order `mode`, then
   `status`. Only exact built-in `str` values reach this stage. An exact
   built-in string absent from the relevant closed enum is an unsupported
   literal; a `str` subclass, arbitrary Enum member, `bytes`, integer,
   boolean, `None`, or any other non-exact-string value has already failed at
   stage 4 and cannot reach enum parsing.
7. Apply dependency presence compatibility using the parsed mode, in exact
   parameter order `source_alignment_request`, then `source_execution`.
   `REPLAY` requires both genuine non-null dependencies; `LOCAL`, `FREE_API`,
   `PAID_API`, and `MANUAL_UI` forbid both.
8. Validate current request binding syntax, then current request ID/hash
   parity against `alignment_request`, in field order ID then hash.
9. Validate current adapter ID, current adapter version, and
   execution-mode/current-request-mode compatibility, in that order.
10. Validate mode/status compatibility.
11. Validate evidence presence/null rules in order paid, replay, confidence.
12. Validate paid-fallback evidence in this exact suborder: mapping and exact
    built-in key-type prerequisites; unknown-key rejection; missing-required-
    key rejection; then known-field scalar validation in this order:
    `schema_version` exact built-in `str` type, then exact literal;
    `authorization_id` exact built-in `str` type, then syntax; `source` exact
    built-in `str` type, then closed enum parsing; `decision` exact built-in
    `str` type, then closed enum parsing; `alignment_request_id` exact
    built-in `str` type, then syntax; `alignment_request_hash` exact built-in
    `str` type, then syntax; request ID then hash binding; decision/status
    invariant.
13. Validate replay in this exact suborder:
    13.1 mapping and exact built-in key-type prerequisites; unknown-key
    rejection; missing-required-key rejection; then the exact replay key set;
    13.2 `ReplayEvidence.schema_version` exact built-in `str` type;
    13.3 `ReplayEvidence.schema_version` exact `REPLAY-EVIDENCE-V1` literal;
    13.4 `source_adapter_execution_id` exact built-in `str` type, then syntax;
    13.5 `source_adapter_execution_hash` exact built-in `str` type, then
    syntax;
    13.6 `source_alignment_request_id` exact built-in `str` type, then syntax;
    13.7 `source_alignment_request_hash` exact built-in `str` type, then
    syntax;
    13.8 source request mode is not `REPLAY`;
    13.9 source execution status is `SUCCEEDED`;
    13.10 source execution mode is not `REPLAY`;
    13.11 source execution mode/source request mode parity;
    13.12 source execution request ID then hash parity against
    `source_alignment_request`;
    13.13 replay-evidence source request ID then hash parity against
    `source_alignment_request`;
    13.14 current/source request role distinction by ID then hash;
    13.15 replay-evidence source execution ID then hash parity against
    `source_execution`;
    13.16 direct self-reference;
    13.17 remaining ambiguity and cycle-capable lineage checks.
14. Validate confidence evidence in this exact suborder:
    14.1 mapping and exact built-in key-type prerequisites; unknown-key
    rejection; missing-required-key rejection; then the exact confidence key
    set;
    14.2 `ConfidenceAvailabilityEvidence.schema_version` exact built-in `str`
    type;
    14.3 exact `CONFIDENCE-AVAILABILITY-EVIDENCE-V1` schema literal;
    14.4 `availability` exact built-in `str` type;
    14.5 closed `ConfidenceAvailability` enum parsing without coercion;
    14.6 capability/status state invariant.
15. Perform the full sensitive-data scan over the supplied logical object
    using the scan and pointer algorithm in section 18.
16. Encode the canonical projection and validate the supplied
    `adapter_execution_hash`.
17. Validate the derived `adapter_execution_id`.
18. For byte input only, validate exact source-byte equality with the canonical
    envelope.
19. Perform immutable construction and canonical envelope encoding
    verification.
20. Register the genuine instance. Registration failure publishes nothing.

The following exact key-set algorithm applies globally to the root mapping and
to every paid, replay, and confidence evidence mapping after any byte-input
duplicate-key rejection:

1. Validate the mapping/root type and require every member name to be an exact
   built-in `str`.
2. Detect unknown keys. If one or more unknown keys exist, reject the
   canonical-JSON-member-order first unknown key even when required keys are
   also missing. Missing-key detection and known-field scalar access do not
   run.
3. Only when no unknown key exists, detect missing required keys. If one or
   more are missing, reject the schema-order first missing key. Known-field
   scalar access does not run.
4. Only an exact key set proceeds to known-field scalar validation.

Canonical JSON member ordering means ascending Unicode code-point order of
exact built-in string keys, exactly the `sorted(keys)` convention used by
`engine.contracts._canonical_json.encode_canonical_json_bytes`. Mapping
insertion order never participates. The selected unknown-key pointer uses JSON
Pointer escaping (`~` becomes `~0`; `/` becomes `~1`) only when the key passes
the section 18 safe-pointer predicate; otherwise it uses the containing-object
pointer.

The canonical required-field orders are the section 5 table orders and are
exactly:

```text
root:
schema_version
hash_scope_version
adapter_execution_id
adapter_execution_hash
alignment_request_id
alignment_request_hash
adapter_id
adapter_version
mode
status
paid_fallback_authorization_evidence
replay_evidence
confidence_availability_evidence

paid:
schema_version
authorization_id
source
decision
alignment_request_id
alignment_request_hash

replay:
schema_version
source_adapter_execution_id
source_adapter_execution_hash
source_alignment_request_id
source_alignment_request_hash

confidence:
schema_version
availability
```

The selected missing-key pointer is the containing mapping pointer plus the
schema-order first missing key, using the same JSON Pointer escaping. Root
fields therefore use `/<field>`; nested fields use
`/paid_fallback_authorization_evidence/<field>`,
`/replay_evidence/<field>`, or
`/confidence_availability_evidence/<field>`.

Raw root input is not accessed before `alignment_request` validation and
validation of every non-null source dependency. Whether either nullable source
dependency is required or forbidden is not decided before current root mode
parsing. If both dependencies violate presence, the
`source_alignment_request` failure wins. A valid `REPLAY` requires both; every
non-`REPLAY` mode forbids both. This order has no mode-before-input dependency.

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

This Slice adds no stable issue code and no rejection reason. Only these
existing issue codes may be non-null:

```text
UNSUPPORTED_CONTRACT_ENUM
ALIGNMENT_REQUEST_IDENTITY_MISMATCH
PAID_FALLBACK_UNAUTHORIZED
REPLAY_INPUT_MISMATCH
REPLAY_HASH_MISMATCH
```

For every `AdapterExecutionContractError` row below, the stable message
category is exactly `Adapter execution rejected: ` followed by that row's
exact reason value. `CONTRACT:<REASON>` in the table denotes that exact
category. Publication result `NONE` means no genuine execution, ID, hash,
canonical bytes, result, report, provenance substitute, or failure artifact.
For the two prerequisite `TypeError` rows, stable category token
`PREREQUISITE:alignment_request` identifies the dependency without making the
exception's sanitized text stable or adding a serialized field.

### 18.1 Pointer and scan algorithms

- Root pointer is `/`. Known-field pointers use `/field` and
  `/evidence_object/field`.
- Dynamic object-key pointers use JSON Pointer escaping: `~` becomes `~0` and
  `/` becomes `~1`.
- A dynamic key is safe to expose only when it is an exact built-in NFC string
  with no surrogate, noncharacter, NUL, C0/C1 control, URI form, absolute-path
  form, drive prefix, or sensitive local name. If unsafe, the containing
  object pointer is used.
- Unknown-key selection and unknown-before-missing precedence use the section
  17 global key-set algorithm. The canonical-JSON-member-order first unknown
  key wins independently of mapping insertion order. The safe-exposure rule
  then selects either its escaped pointer or the containing-object pointer.
- Missing-key selection runs only when no unknown field exists. The section
  17 schema-order first missing required key wins and its exact known-field
  pointer is published.
- Duplicate-key parsing never exposes the duplicated key. The exact pointer is
  `/` for a root duplicate,
  `/paid_fallback_authorization_evidence`,
  `/replay_evidence`, or `/confidence_availability_evidence` for a duplicate
  in that object. This follows the repository parser convention of rejecting
  duplicates before materialization while avoiding key leakage.
- Sensitive scanning is depth-first pre-order. Mapping keys are visited in
  Unicode-code-point order; each key is safety-checked before its value, and
  each value is then recursively scanned. The first failure wins. A sensitive
  scalar uses its exact known-field pointer. An unsafe dynamic key uses the
  containing-object pointer. Arrays and unknown fields have already failed at
  their earlier structure stage.
- Sensitive rejection always uses `STRUCTURE_INVALID`, issue code `None`, and
  a redacted `CONTRACT:STRUCTURE_INVALID` message. The offending key or value
  is never interpolated.

### 18.2 Complete mandatory error oracle

Every rejection required by Sections 5, 10, 11, 12 and 17 has either:

- its own exact oracle row; or
- one explicitly identified generic row whose condition, pointer algorithm,
  reason, and issue-code mapping are sufficient to produce one deterministic
  public failure.

No known nested field falls outside this table.

Materializer/loader stages are the numbered stages in section 17.
Serializer stage `S1` is the exact-type and genuine-materialization preflight
performed before projection or envelope access.

| Condition | Stage | Exception class | Exact pointer | Exact reason | Exact issue code | Message category | Publication |
|---|---:|---|---|---|---|---|---|
| wrong exact type for current `alignment_request` | 1 | `TypeError` | not applicable | not applicable | not applicable | `PREREQUISITE:alignment_request`; exact text non-stable | `NONE` |
| non-genuine current `alignment_request` | 1 | `TypeError` | not applicable | not applicable | not applicable | `PREREQUISITE:alignment_request`; exact text non-stable | `NONE` |
| wrong exact type for non-null `source_alignment_request` | 2 | `AdapterExecutionContractError` | `/source_alignment_request` | `NOT_MATERIALIZED` | `None` | `CONTRACT:NOT_MATERIALIZED` | `NONE` |
| non-genuine non-null `source_alignment_request` | 2 | `AdapterExecutionContractError` | `/source_alignment_request` | `NOT_MATERIALIZED` | `None` | `CONTRACT:NOT_MATERIALIZED` | `NONE` |
| wrong exact type for non-null `source_execution` | 3 | `AdapterExecutionContractError` | `/source_execution` | `NOT_MATERIALIZED` | `None` | `CONTRACT:NOT_MATERIALIZED` | `NONE` |
| non-genuine non-null `source_execution` | 3 | `AdapterExecutionContractError` | `/source_execution` | `NOT_MATERIALIZED` | `None` | `CONTRACT:NOT_MATERIALIZED` | `NONE` |
| byte source is not exact built-in `bytes`, invalid UTF-8, or malformed JSON | 4 | `AdapterExecutionContractError` | `/` | `STRUCTURE_INVALID` | `None` | `CONTRACT:STRUCTURE_INVALID` | `NONE` |
| BOM or otherwise parseable but forbidden byte envelope form | 4 | `AdapterExecutionContractError` | `/` | `NON_CANONICAL_SERIALIZATION` | `None` | `CONTRACT:NON_CANONICAL_SERIALIZATION` | `NONE` |
| duplicate root key | 4 | `AdapterExecutionContractError` | `/` | `STRUCTURE_INVALID` | `None` | `CONTRACT:STRUCTURE_INVALID` | `NONE` |
| duplicate paid-evidence key | 4 | `AdapterExecutionContractError` | `/paid_fallback_authorization_evidence` | `STRUCTURE_INVALID` | `None` | `CONTRACT:STRUCTURE_INVALID` | `NONE` |
| duplicate replay-evidence key | 4 | `AdapterExecutionContractError` | `/replay_evidence` | `STRUCTURE_INVALID` | `None` | `CONTRACT:STRUCTURE_INVALID` | `NONE` |
| duplicate confidence-evidence key | 4 | `AdapterExecutionContractError` | `/confidence_availability_evidence` | `STRUCTURE_INVALID` | `None` | `CONTRACT:STRUCTURE_INVALID` | `NONE` |
| logical root is not a mapping or a root member name is not an exact built-in `str` | 4 | `AdapterExecutionContractError` | `/` | `STRUCTURE_INVALID` | `None` | `CONTRACT:STRUCTURE_INVALID` | `NONE` |
| one or more unknown root fields exist, regardless of simultaneous missing required fields | 4 | `AdapterExecutionContractError` | section 17 canonical-member-order first safe escaped unknown root pointer, otherwise `/` | `STRUCTURE_INVALID` | `None` | `CONTRACT:STRUCTURE_INVALID` | `NONE` |
| no unknown root field exists and one or more required root fields are missing | 4 | `AdapterExecutionContractError` | section 17 schema-order first missing root field pointer | `STRUCTURE_INVALID` | `None` | `CONTRACT:STRUCTURE_INVALID` | `NONE` |
| root `mode` has any wrong exact type, including a `str` subclass, arbitrary Enum, `bytes`, integer, boolean, `None`, or other non-exact-`str` object | 4 | `AdapterExecutionContractError` | `/mode` | `STRUCTURE_INVALID` | `None` | `CONTRACT:STRUCTURE_INVALID` | `NONE` |
| root `status` has any wrong exact type, including a `str` subclass, arbitrary Enum, `bytes`, integer, boolean, `None`, or other non-exact-`str` object | 4 | `AdapterExecutionContractError` | `/status` | `STRUCTURE_INVALID` | `None` | `CONTRACT:STRUCTURE_INVALID` | `NONE` |
| wrong root scalar/object/null type other than the separately listed `mode` and `status` conditions, or any JSON number/boolean/array in such a field | 4 | `AdapterExecutionContractError` | exact known-field pointer | `STRUCTURE_INVALID` | `None` | `CONTRACT:STRUCTURE_INVALID` | `NONE` |
| unsupported `schema_version` | 5 | `AdapterExecutionContractError` | `/schema_version` | `UNSUPPORTED_VALUE` | `None` | `CONTRACT:UNSUPPORTED_VALUE` | `NONE` |
| unsupported `hash_scope_version` | 5 | `AdapterExecutionContractError` | `/hash_scope_version` | `UNSUPPORTED_VALUE` | `None` | `CONTRACT:UNSUPPORTED_VALUE` | `NONE` |
| root `mode` is an exact built-in `str` value unsupported by the closed `AdapterExecutionMode` enum | 6 | `AdapterExecutionContractError` | `/mode` | `UNSUPPORTED_VALUE` | `UNSUPPORTED_CONTRACT_ENUM` | `CONTRACT:UNSUPPORTED_VALUE` | `NONE` |
| root `status` is an exact built-in `str` value unsupported by the closed `AdapterExecutionStatus` enum | 6 | `AdapterExecutionContractError` | `/status` | `UNSUPPORTED_VALUE` | `UNSUPPORTED_CONTRACT_ENUM` | `CONTRACT:UNSUPPORTED_VALUE` | `NONE` |
| `REPLAY` missing `source_alignment_request` | 7 | `AdapterExecutionContractError` | `/source_alignment_request` | `REPLAY_EVIDENCE_INVALID` | `REPLAY_INPUT_MISMATCH` | `CONTRACT:REPLAY_EVIDENCE_INVALID` | `NONE` |
| non-`REPLAY` has `source_alignment_request` | 7 | `AdapterExecutionContractError` | `/source_alignment_request` | `REPLAY_EVIDENCE_INVALID` | `REPLAY_INPUT_MISMATCH` | `CONTRACT:REPLAY_EVIDENCE_INVALID` | `NONE` |
| `REPLAY` missing `source_execution` | 7 | `AdapterExecutionContractError` | `/source_execution` | `REPLAY_EVIDENCE_INVALID` | `REPLAY_INPUT_MISMATCH` | `CONTRACT:REPLAY_EVIDENCE_INVALID` | `NONE` |
| non-`REPLAY` has `source_execution` | 7 | `AdapterExecutionContractError` | `/source_execution` | `REPLAY_EVIDENCE_INVALID` | `REPLAY_INPUT_MISMATCH` | `CONTRACT:REPLAY_EVIDENCE_INVALID` | `NONE` |
| current request ID mismatch | 8 | `AdapterExecutionContractError` | `/alignment_request_id` | `REQUEST_BINDING_INVALID` | `ALIGNMENT_REQUEST_IDENTITY_MISMATCH` | `CONTRACT:REQUEST_BINDING_INVALID` | `NONE` |
| current request hash mismatch | 8 | `AdapterExecutionContractError` | `/alignment_request_hash` | `REQUEST_BINDING_INVALID` | `ALIGNMENT_REQUEST_IDENTITY_MISMATCH` | `CONTRACT:REQUEST_BINDING_INVALID` | `NONE` |
| current adapter ID mismatch | 9 | `AdapterExecutionContractError` | `/adapter_id` | `REQUEST_BINDING_INVALID` | `ALIGNMENT_REQUEST_IDENTITY_MISMATCH` | `CONTRACT:REQUEST_BINDING_INVALID` | `NONE` |
| current adapter version mismatch | 9 | `AdapterExecutionContractError` | `/adapter_version` | `REQUEST_BINDING_INVALID` | `ALIGNMENT_REQUEST_IDENTITY_MISMATCH` | `CONTRACT:REQUEST_BINDING_INVALID` | `NONE` |
| current execution mode/current request mode parity mismatch | 9 | `AdapterExecutionContractError` | `/mode` | `REQUEST_BINDING_INVALID` | `None` | `CONTRACT:REQUEST_BINDING_INVALID` | `NONE` |
| invalid known mode/status pair | 10 | `AdapterExecutionContractError` | `/status` | `MODE_STATUS_INVALID` | `None` | `CONTRACT:MODE_STATUS_INVALID` | `NONE` |
| missing or forbidden paid evidence object | 11 | `AdapterExecutionContractError` | `/paid_fallback_authorization_evidence` | `EVIDENCE_PRESENCE_INVALID` | `PAID_FALLBACK_UNAUTHORIZED` | `CONTRACT:EVIDENCE_PRESENCE_INVALID` | `NONE` |
| missing or forbidden replay evidence object | 11 | `AdapterExecutionContractError` | `/replay_evidence` | `EVIDENCE_PRESENCE_INVALID` | `REPLAY_INPUT_MISMATCH` | `CONTRACT:EVIDENCE_PRESENCE_INVALID` | `NONE` |
| missing or forbidden confidence evidence object | 11 | `AdapterExecutionContractError` | `/confidence_availability_evidence` | `EVIDENCE_PRESENCE_INVALID` | `None` | `CONTRACT:EVIDENCE_PRESENCE_INVALID` | `NONE` |
| a paid-evidence member name is not an exact built-in `str` | 12 | `AdapterExecutionContractError` | `/paid_fallback_authorization_evidence` | `STRUCTURE_INVALID` | `None` | `CONTRACT:STRUCTURE_INVALID` | `NONE` |
| one or more unknown paid-evidence fields exist, regardless of simultaneous missing required fields | 12 | `AdapterExecutionContractError` | section 17 canonical-member-order first safe escaped unknown paid pointer, otherwise `/paid_fallback_authorization_evidence` | `STRUCTURE_INVALID` | `None` | `CONTRACT:STRUCTURE_INVALID` | `NONE` |
| no unknown paid-evidence field exists and one or more required paid fields are missing | 12 | `AdapterExecutionContractError` | section 17 schema-order first missing paid field pointer | `STRUCTURE_INVALID` | `None` | `CONTRACT:STRUCTURE_INVALID` | `NONE` |
| paid `schema_version` wrong exact type | 12 | `AdapterExecutionContractError` | `/paid_fallback_authorization_evidence/schema_version` | `PAID_FALLBACK_AUTHORIZATION_INVALID` | `PAID_FALLBACK_UNAUTHORIZED` | `CONTRACT:PAID_FALLBACK_AUTHORIZATION_INVALID` | `NONE` |
| paid `schema_version` unsupported literal | 12 | `AdapterExecutionContractError` | `/paid_fallback_authorization_evidence/schema_version` | `PAID_FALLBACK_AUTHORIZATION_INVALID` | `PAID_FALLBACK_UNAUTHORIZED` | `CONTRACT:PAID_FALLBACK_AUTHORIZATION_INVALID` | `NONE` |
| paid `authorization_id` wrong exact type or malformed syntax | 12 | `AdapterExecutionContractError` | `/paid_fallback_authorization_evidence/authorization_id` | `PAID_FALLBACK_AUTHORIZATION_INVALID` | `PAID_FALLBACK_UNAUTHORIZED` | `CONTRACT:PAID_FALLBACK_AUTHORIZATION_INVALID` | `NONE` |
| paid `source` wrong exact type or unsupported/coerced value | 12 | `AdapterExecutionContractError` | `/paid_fallback_authorization_evidence/source` | `PAID_FALLBACK_AUTHORIZATION_INVALID` | `PAID_FALLBACK_UNAUTHORIZED` | `CONTRACT:PAID_FALLBACK_AUTHORIZATION_INVALID` | `NONE` |
| paid `decision` wrong exact type or unsupported/coerced value | 12 | `AdapterExecutionContractError` | `/paid_fallback_authorization_evidence/decision` | `PAID_FALLBACK_AUTHORIZATION_INVALID` | `PAID_FALLBACK_UNAUTHORIZED` | `CONTRACT:PAID_FALLBACK_AUTHORIZATION_INVALID` | `NONE` |
| paid `alignment_request_id` wrong exact type, malformed syntax, or current-request mismatch | 12 | `AdapterExecutionContractError` | `/paid_fallback_authorization_evidence/alignment_request_id` | `PAID_FALLBACK_AUTHORIZATION_INVALID` | `PAID_FALLBACK_UNAUTHORIZED` | `CONTRACT:PAID_FALLBACK_AUTHORIZATION_INVALID` | `NONE` |
| paid `alignment_request_hash` wrong exact type, malformed syntax, or current-request mismatch | 12 | `AdapterExecutionContractError` | `/paid_fallback_authorization_evidence/alignment_request_hash` | `PAID_FALLBACK_AUTHORIZATION_INVALID` | `PAID_FALLBACK_UNAUTHORIZED` | `CONTRACT:PAID_FALLBACK_AUTHORIZATION_INVALID` | `NONE` |
| paid decision/status incompatibility after all paid fields validate | 12 | `AdapterExecutionContractError` | `/paid_fallback_authorization_evidence/decision` | `PAID_FALLBACK_AUTHORIZATION_INVALID` | `PAID_FALLBACK_UNAUTHORIZED` | `CONTRACT:PAID_FALLBACK_AUTHORIZATION_INVALID` | `NONE` |
| a replay-evidence member name is not an exact built-in `str` | 13 | `AdapterExecutionContractError` | `/replay_evidence` | `STRUCTURE_INVALID` | `None` | `CONTRACT:STRUCTURE_INVALID` | `NONE` |
| one or more unknown replay-evidence fields exist, regardless of simultaneous missing required fields | 13 | `AdapterExecutionContractError` | section 17 canonical-member-order first safe escaped unknown replay pointer, otherwise `/replay_evidence` | `STRUCTURE_INVALID` | `None` | `CONTRACT:STRUCTURE_INVALID` | `NONE` |
| no unknown replay-evidence field exists and one or more required replay fields are missing | 13 | `AdapterExecutionContractError` | section 17 schema-order first missing replay field pointer | `STRUCTURE_INVALID` | `None` | `CONTRACT:STRUCTURE_INVALID` | `NONE` |
| replay `schema_version` wrong exact type | 13 | `AdapterExecutionContractError` | `/replay_evidence/schema_version` | `REPLAY_EVIDENCE_INVALID` | `REPLAY_INPUT_MISMATCH` | `CONTRACT:REPLAY_EVIDENCE_INVALID` | `NONE` |
| replay `schema_version` unsupported literal | 13 | `AdapterExecutionContractError` | `/replay_evidence/schema_version` | `REPLAY_EVIDENCE_INVALID` | `REPLAY_INPUT_MISMATCH` | `CONTRACT:REPLAY_EVIDENCE_INVALID` | `NONE` |
| replay `source_adapter_execution_id` wrong exact type | 13 | `AdapterExecutionContractError` | `/replay_evidence/source_adapter_execution_id` | `REPLAY_EVIDENCE_INVALID` | `REPLAY_INPUT_MISMATCH` | `CONTRACT:REPLAY_EVIDENCE_INVALID` | `NONE` |
| replay `source_adapter_execution_id` malformed syntax | 13 | `AdapterExecutionContractError` | `/replay_evidence/source_adapter_execution_id` | `REPLAY_EVIDENCE_INVALID` | `REPLAY_INPUT_MISMATCH` | `CONTRACT:REPLAY_EVIDENCE_INVALID` | `NONE` |
| replay `source_adapter_execution_hash` wrong exact type | 13 | `AdapterExecutionContractError` | `/replay_evidence/source_adapter_execution_hash` | `REPLAY_EVIDENCE_INVALID` | `REPLAY_INPUT_MISMATCH` | `CONTRACT:REPLAY_EVIDENCE_INVALID` | `NONE` |
| replay `source_adapter_execution_hash` malformed syntax | 13 | `AdapterExecutionContractError` | `/replay_evidence/source_adapter_execution_hash` | `REPLAY_EVIDENCE_INVALID` | `REPLAY_HASH_MISMATCH` | `CONTRACT:REPLAY_EVIDENCE_INVALID` | `NONE` |
| replay `source_alignment_request_id` wrong exact type | 13 | `AdapterExecutionContractError` | `/replay_evidence/source_alignment_request_id` | `REPLAY_EVIDENCE_INVALID` | `REPLAY_INPUT_MISMATCH` | `CONTRACT:REPLAY_EVIDENCE_INVALID` | `NONE` |
| replay `source_alignment_request_id` malformed syntax | 13 | `AdapterExecutionContractError` | `/replay_evidence/source_alignment_request_id` | `REPLAY_EVIDENCE_INVALID` | `REPLAY_INPUT_MISMATCH` | `CONTRACT:REPLAY_EVIDENCE_INVALID` | `NONE` |
| replay `source_alignment_request_hash` wrong exact type | 13 | `AdapterExecutionContractError` | `/replay_evidence/source_alignment_request_hash` | `REPLAY_EVIDENCE_INVALID` | `REPLAY_INPUT_MISMATCH` | `CONTRACT:REPLAY_EVIDENCE_INVALID` | `NONE` |
| replay `source_alignment_request_hash` malformed syntax | 13 | `AdapterExecutionContractError` | `/replay_evidence/source_alignment_request_hash` | `REPLAY_EVIDENCE_INVALID` | `REPLAY_INPUT_MISMATCH` | `CONTRACT:REPLAY_EVIDENCE_INVALID` | `NONE` |
| source request mode is `REPLAY` | 13 | `AdapterExecutionContractError` | `/source_alignment_request/mode` | `REPLAY_LINEAGE_INVALID` | `REPLAY_INPUT_MISMATCH` | `CONTRACT:REPLAY_LINEAGE_INVALID` | `NONE` |
| source execution status is not `SUCCEEDED` | 13 | `AdapterExecutionContractError` | `/source_execution/status` | `REPLAY_LINEAGE_INVALID` | `REPLAY_INPUT_MISMATCH` | `CONTRACT:REPLAY_LINEAGE_INVALID` | `NONE` |
| source execution mode is `REPLAY` | 13 | `AdapterExecutionContractError` | `/source_execution/mode` | `REPLAY_LINEAGE_INVALID` | `REPLAY_INPUT_MISMATCH` | `CONTRACT:REPLAY_LINEAGE_INVALID` | `NONE` |
| source execution mode/source request mode parity mismatch | 13 | `AdapterExecutionContractError` | `/source_execution/mode` | `REPLAY_EVIDENCE_INVALID` | `REPLAY_INPUT_MISMATCH` | `CONTRACT:REPLAY_EVIDENCE_INVALID` | `NONE` |
| source execution request ID mismatch against source request | 13 | `AdapterExecutionContractError` | `/source_execution/alignment_request_id` | `REPLAY_EVIDENCE_INVALID` | `REPLAY_INPUT_MISMATCH` | `CONTRACT:REPLAY_EVIDENCE_INVALID` | `NONE` |
| source execution request hash mismatch against source request | 13 | `AdapterExecutionContractError` | `/source_execution/alignment_request_hash` | `REPLAY_EVIDENCE_INVALID` | `REPLAY_INPUT_MISMATCH` | `CONTRACT:REPLAY_EVIDENCE_INVALID` | `NONE` |
| replay-evidence source request ID mismatch | 13 | `AdapterExecutionContractError` | `/replay_evidence/source_alignment_request_id` | `REPLAY_EVIDENCE_INVALID` | `REPLAY_INPUT_MISMATCH` | `CONTRACT:REPLAY_EVIDENCE_INVALID` | `NONE` |
| replay-evidence source request hash mismatch | 13 | `AdapterExecutionContractError` | `/replay_evidence/source_alignment_request_hash` | `REPLAY_EVIDENCE_INVALID` | `REPLAY_INPUT_MISMATCH` | `CONTRACT:REPLAY_EVIDENCE_INVALID` | `NONE` |
| source request/current request ID role confusion | 13 | `AdapterExecutionContractError` | `/source_alignment_request/alignment_request_id` | `REPLAY_LINEAGE_INVALID` | `REPLAY_INPUT_MISMATCH` | `CONTRACT:REPLAY_LINEAGE_INVALID` | `NONE` |
| source request/current request hash role confusion | 13 | `AdapterExecutionContractError` | `/source_alignment_request/alignment_request_hash` | `REPLAY_LINEAGE_INVALID` | `REPLAY_INPUT_MISMATCH` | `CONTRACT:REPLAY_LINEAGE_INVALID` | `NONE` |
| replay-evidence source execution ID mismatch | 13 | `AdapterExecutionContractError` | `/replay_evidence/source_adapter_execution_id` | `REPLAY_EVIDENCE_INVALID` | `REPLAY_INPUT_MISMATCH` | `CONTRACT:REPLAY_EVIDENCE_INVALID` | `NONE` |
| replay-evidence source execution hash mismatch | 13 | `AdapterExecutionContractError` | `/replay_evidence/source_adapter_execution_hash` | `REPLAY_EVIDENCE_INVALID` | `REPLAY_HASH_MISMATCH` | `CONTRACT:REPLAY_EVIDENCE_INVALID` | `NONE` |
| direct self-reference | 13 | `AdapterExecutionContractError` | `/replay_evidence/source_adapter_execution_id` | `REPLAY_LINEAGE_INVALID` | `REPLAY_INPUT_MISMATCH` | `CONTRACT:REPLAY_LINEAGE_INVALID` | `NONE` |
| extra parent, ancestor array, multiple-source key, nested replay object, or other ambiguous lineage field | 13 | `AdapterExecutionContractError` | first safe escaped unknown replay pointer, otherwise `/replay_evidence` | `STRUCTURE_INVALID` | `None` | `CONTRACT:STRUCTURE_INVALID` | `NONE` |
| a confidence-evidence member name is not an exact built-in `str` | 14 | `AdapterExecutionContractError` | `/confidence_availability_evidence` | `STRUCTURE_INVALID` | `None` | `CONTRACT:STRUCTURE_INVALID` | `NONE` |
| one or more unknown confidence-evidence fields exist, regardless of simultaneous missing required fields | 14 | `AdapterExecutionContractError` | section 17 canonical-member-order first safe escaped unknown confidence pointer, otherwise `/confidence_availability_evidence` | `STRUCTURE_INVALID` | `None` | `CONTRACT:STRUCTURE_INVALID` | `NONE` |
| no unknown confidence-evidence field exists and one or more required confidence fields are missing | 14 | `AdapterExecutionContractError` | section 17 schema-order first missing confidence field pointer | `STRUCTURE_INVALID` | `None` | `CONTRACT:STRUCTURE_INVALID` | `NONE` |
| confidence `schema_version` wrong exact type | 14 | `AdapterExecutionContractError` | `/confidence_availability_evidence/schema_version` | `CONFIDENCE_AVAILABILITY_INVALID` | `None` | `CONTRACT:CONFIDENCE_AVAILABILITY_INVALID` | `NONE` |
| confidence `schema_version` unsupported literal | 14 | `AdapterExecutionContractError` | `/confidence_availability_evidence/schema_version` | `CONFIDENCE_AVAILABILITY_INVALID` | `None` | `CONTRACT:CONFIDENCE_AVAILABILITY_INVALID` | `NONE` |
| confidence `availability` wrong exact type | 14 | `AdapterExecutionContractError` | `/confidence_availability_evidence/availability` | `CONFIDENCE_AVAILABILITY_INVALID` | `None` | `CONTRACT:CONFIDENCE_AVAILABILITY_INVALID` | `NONE` |
| confidence `availability` unsupported/coerced value | 14 | `AdapterExecutionContractError` | `/confidence_availability_evidence/availability` | `CONFIDENCE_AVAILABILITY_INVALID` | `None` | `CONTRACT:CONFIDENCE_AVAILABILITY_INVALID` | `NONE` |
| confidence availability capability/status incompatibility after schema and enum validation | 14 | `AdapterExecutionContractError` | `/confidence_availability_evidence/availability` | `CONFIDENCE_AVAILABILITY_INVALID` | `None` | `CONTRACT:CONFIDENCE_AVAILABILITY_INVALID` | `NONE` |
| sensitive data in a root known field | 15 | `AdapterExecutionContractError` | exact offending root field pointer | `STRUCTURE_INVALID` | `None` | `CONTRACT:STRUCTURE_INVALID` | `NONE` |
| sensitive data in paid evidence | 15 | `AdapterExecutionContractError` | exact offending paid field pointer | `STRUCTURE_INVALID` | `None` | `CONTRACT:STRUCTURE_INVALID` | `NONE` |
| sensitive data in replay evidence | 15 | `AdapterExecutionContractError` | exact offending replay field pointer | `STRUCTURE_INVALID` | `None` | `CONTRACT:STRUCTURE_INVALID` | `NONE` |
| supplied canonical projection hash mismatch | 16 | `AdapterExecutionContractError` | `/adapter_execution_hash` | `IDENTITY_MISMATCH` | `None` | `CONTRACT:IDENTITY_MISMATCH` | `NONE` |
| supplied derived ID mismatch after hash matches | 17 | `AdapterExecutionContractError` | `/adapter_execution_id` | `IDENTITY_MISMATCH` | `None` | `CONTRACT:IDENTITY_MISMATCH` | `NONE` |
| parsed semantic envelope bytes differ from exact canonical envelope | 18 | `AdapterExecutionContractError` | `/` | `NON_CANONICAL_SERIALIZATION` | `None` | `CONTRACT:NON_CANONICAL_SERIALIZATION` | `NONE` |
| serialize wrong-type or non-genuine execution | `S1` | `AdapterExecutionContractError` | `/` | `NOT_MATERIALIZED` | `None` | `CONTRACT:NOT_MATERIALIZED` | `NONE` |

Malformed `source_adapter_execution_hash` syntax and valid-syntax content
mismatch against the genuine source execution both use
`REPLAY_HASH_MISMATCH`. Its wrong exact type uses
`REPLAY_INPUT_MISMATCH`. All type, literal, and syntax failures for the source
request ID/hash use `REPLAY_INPUT_MISMATCH`; no source-request hash condition
may select `REPLAY_HASH_MISMATCH`.

The `alignment_request` rows intentionally follow the established Slice 4
prerequisite `TypeError` convention. Both source parameters are Slice-owned
dependency boundaries and therefore use `AdapterExecutionContractError`.
Mutation of a frozen public field raises standard frozen-dataclass
`FrozenInstanceError` or `AttributeError`; it is not converted into a contract
error.

Stages 19 and 20 are atomic construction/publication internals, not public
input-rejection paths. They never produce `AdapterExecutionContractError` and
publish no genuine object, ID, hash, or canonical bytes. Registry insertion
exceptions and genuine-verification exceptions propagate unchanged, while a
false genuine-verification result raises exact `RuntimeError` message
`adapter execution provenance registration failed`; cleanup removes only the
exact weak-reference entry inserted by the failing operation.

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
| Paid source alias/coercion | paid `source` is a case variant, `str` subclass, or arbitrary Enum member | `PAID_FALLBACK_AUTHORIZATION_INVALID` | `/paid_fallback_authorization_evidence/source` / `PAID_FALLBACK_UNAUTHORIZED` |
| Confidence alias/coercion | `availability` is a case variant, `str` subclass, or arbitrary Enum member | `CONFIDENCE_AVAILABILITY_INVALID` | `/confidence_availability_evidence/availability` / `None` |
| Wrong-type request dependency | `alignment_request` is a subclass, proxy, or any value that is not exact `AlignmentRequest` type | `TypeError`; rejection reason not applicable | pointer not applicable / issue code not applicable; sanitized message category identifies `alignment_request`, exact text not stable; root input not accessed |
| Non-genuine request dependency | distinct exact `AlignmentRequest` reconstructed, copied, replaced, or otherwise unregistered | `TypeError`; rejection reason not applicable | pointer not applicable / issue code not applicable; sanitized message category identifies `alignment_request`, exact text not stable; root input not accessed |
| Wrong-type source request dependency | non-null `source_alignment_request` is a subclass, proxy, or wrong type | `NOT_MATERIALIZED` | `/source_alignment_request` / `None`; root input not accessed |
| Non-genuine source request dependency | non-null exact `AlignmentRequest` is copied, reconstructed, replaced, or unregistered | `NOT_MATERIALIZED` | `/source_alignment_request` / `None`; root input not accessed |
| Wrong-type source execution dependency | non-null `source_execution` is a subclass, proxy, or wrong type | `NOT_MATERIALIZED` | `/source_execution` / `None`; root input not accessed |
| Non-genuine source execution dependency | non-null exact `AdapterExecution` is copied, reconstructed, replaced, or unregistered | `NOT_MATERIALIZED` | `/source_execution` / `None`; root input not accessed |
| Disallowed pair | `LOCAL/BLOCKED` | `MODE_STATUS_INVALID` | `/status` / `None` |
| Missing request ID | omit `alignment_request_id`, with no unknown root field | `STRUCTURE_INVALID` | `/alignment_request_id` / `None` |
| Missing request hash | omit `alignment_request_hash`, with no unknown root field | `STRUCTURE_INVALID` | `/alignment_request_hash` / `None` |
| Request ID/hash mismatch | use another genuine request's ID or hash | `REQUEST_BINDING_INVALID` | mismatched binding pointer / `ALIGNMENT_REQUEST_IDENTITY_MISMATCH` |
| Paid adapter identity mismatch | approved `PAID_API` input changes `adapter_id` or `adapter_version` from the bound request | `REQUEST_BINDING_INVALID` | mismatched adapter pointer / `ALIGNMENT_REQUEST_IDENTITY_MISMATCH` |
| Current request-mode parity mismatch | current execution `mode` is incompatible with `alignment_request.mode` | `REQUEST_BINDING_INVALID` | `/mode` / `None` |
| Missing paid evidence | `PAID_API/SUCCEEDED` with null evidence | `EVIDENCE_PRESENCE_INVALID` | `/paid_fallback_authorization_evidence` / `PAID_FALLBACK_UNAUTHORIZED` |
| Forbidden paid evidence | `LOCAL/SUCCEEDED` with evidence | `EVIDENCE_PRESENCE_INVALID` | paid pointer / `PAID_FALLBACK_UNAUTHORIZED` |
| Invalid paid evidence | `PAID_API/SUCCEEDED`, decision `DENIED` | `PAID_FALLBACK_AUTHORIZATION_INVALID` | `/paid_fallback_authorization_evidence/decision` / `PAID_FALLBACK_UNAUTHORIZED` |
| Missing replay evidence | `REPLAY/SUCCEEDED` with null evidence | `EVIDENCE_PRESENCE_INVALID` | `/replay_evidence` / `REPLAY_INPUT_MISMATCH` |
| Forbidden replay evidence | `FREE_API/SUCCEEDED` with replay evidence | `EVIDENCE_PRESENCE_INVALID` | `/replay_evidence` / `REPLAY_INPUT_MISMATCH` |
| Missing replay source request dependency | parsed `REPLAY` input with `source_alignment_request=None` | `REPLAY_EVIDENCE_INVALID` | `/source_alignment_request` / `REPLAY_INPUT_MISMATCH` |
| Forbidden replay source request dependency | parsed non-`REPLAY` input with genuine `source_alignment_request` present | `REPLAY_EVIDENCE_INVALID` | `/source_alignment_request` / `REPLAY_INPUT_MISMATCH` |
| Missing replay source dependency | parsed `REPLAY` input with `source_execution=None` | `REPLAY_EVIDENCE_INVALID` | `/source_execution` / `REPLAY_INPUT_MISMATCH` |
| Forbidden replay source dependency | parsed non-`REPLAY` input with genuine `source_execution` present | `REPLAY_EVIDENCE_INVALID` | `/source_execution` / `REPLAY_INPUT_MISMATCH` |
| Failed replay source | genuine `source_execution.status != SUCCEEDED` | `REPLAY_LINEAGE_INVALID` | `/source_execution/status` / `REPLAY_INPUT_MISMATCH` |
| Replay source request is replay-mode | genuine `source_alignment_request.mode == REPLAY` | `REPLAY_LINEAGE_INVALID` | `/source_alignment_request/mode` / `REPLAY_INPUT_MISMATCH` |
| Replay source execution is replay-mode | genuine `source_execution.mode == REPLAY` | `REPLAY_LINEAGE_INVALID` | `/source_execution/mode` / `REPLAY_INPUT_MISMATCH` |
| Source execution/request mode mismatch | source execution mode does not satisfy parity against source request | `REPLAY_EVIDENCE_INVALID` | `/source_execution/mode` / `REPLAY_INPUT_MISMATCH` |
| Source execution request-binding mismatch | source execution request ID/hash differs from source request dependency | `REPLAY_EVIDENCE_INVALID` | first mismatched `/source_execution` binding pointer / `REPLAY_INPUT_MISMATCH` |
| Replay-evidence source-request mismatch | replay evidence request ID/hash differs from source request dependency | `REPLAY_EVIDENCE_INVALID` | first mismatched replay request pointer / `REPLAY_INPUT_MISMATCH` |
| Current/source request role confusion | source request ID or hash equals the current replay request | `REPLAY_LINEAGE_INVALID` | first mismatched `/source_alignment_request` role pointer / `REPLAY_INPUT_MISMATCH` |
| Replay source execution ID mismatch | replay evidence source ID differs from genuine source execution | `REPLAY_EVIDENCE_INVALID` | `/replay_evidence/source_adapter_execution_id` / `REPLAY_INPUT_MISMATCH` |
| Replay source execution hash mismatch | replay evidence source hash differs from genuine source execution | `REPLAY_EVIDENCE_INVALID` | `/replay_evidence/source_adapter_execution_hash` / `REPLAY_HASH_MISMATCH` |
| Replay self-reference | source ID equals supplied current ID | `REPLAY_LINEAGE_INVALID` | `/replay_evidence/source_adapter_execution_id` / `REPLAY_INPUT_MISMATCH` |
| Ambiguous lineage | extra parent array, multiple source key, nested replay object, or other lineage field | `STRUCTURE_INVALID` | section 18 safe unknown pointer or `/replay_evidence` / `None` |
| Missing confidence evidence | `LOCAL/SUCCEEDED` with null evidence | `EVIDENCE_PRESENCE_INVALID` | `/confidence_availability_evidence` / `None` |
| Forbidden confidence evidence | `FREE_API/BLOCKED` with evidence object | `EVIDENCE_PRESENCE_INVALID` | confidence pointer / `None` |
| Invalid confidence state | successful `SUPPORTED` request with `NOT_APPLICABLE` | `CONFIDENCE_AVAILABILITY_INVALID` | `/confidence_availability_evidence/availability` / `None` |
| Duplicate root key | repeat any root key in byte input | `STRUCTURE_INVALID` | `/` / `None` |
| Duplicate nested key | repeat a paid, replay, or confidence evidence key in byte input | `STRUCTURE_INVALID` | exact containing evidence-object pointer / `None` |
| Unknown object field | add root or nested `extra`, with or without a simultaneous missing required field | `STRUCTURE_INVALID` | section 17 canonical-member-order first safe escaped unknown pointer or containing object / `None`; unknown wins before missing |
| Sensitive root value | place a URI, absolute path, control-bearing, or secret material string in a known root field | `STRUCTURE_INVALID` | exact offending root field pointer / `None`; redacted message |
| Sensitive paid value | place sensitive material in a known paid evidence field | `STRUCTURE_INVALID` | exact offending paid field pointer / `None`; redacted message |
| Sensitive replay value | place sensitive material in a known replay evidence field | `STRUCTURE_INVALID` | exact offending replay field pointer / `None`; redacted message |
| Non-canonical serialized input | add whitespace or reorder byte-input keys | `NON_CANONICAL_SERIALIZATION` | `/` / `None` |
| Canonical hash mismatch | replace execution hash with lowercase zero hash | `IDENTITY_MISMATCH` | `/adapter_execution_hash` / `None` |
| Derived identifier mismatch | correct hash plus wrong execution ID | `IDENTITY_MISMATCH` | `/adapter_execution_id` / `None` |

### 20.1 Root scalar and exact-key-set precedence examples

| Example | Exact invalid input | Stage and precedence | Exception class | Exact reason | Exact pointer | Exact issue code | Message category / publication |
|---|---|---|---|---|---|---|---|
| Wrong-type root mode subclass | root `mode=CustomString("LOCAL")` | 4 exact type; before enum parsing | `AdapterExecutionContractError` | `STRUCTURE_INVALID` | `/mode` | `None` | `CONTRACT:STRUCTURE_INVALID` / `NONE` |
| Wrong-type root mode Enum | root `mode=ArbitraryEnum.LOCAL` | 4 exact type; before enum parsing | `AdapterExecutionContractError` | `STRUCTURE_INVALID` | `/mode` | `None` | `CONTRACT:STRUCTURE_INVALID` / `NONE` |
| Unsupported root mode literal | root `mode="UNKNOWN_MODE"` as exact built-in `str` | 6 closed enum; after exact type | `AdapterExecutionContractError` | `UNSUPPORTED_VALUE` | `/mode` | `UNSUPPORTED_CONTRACT_ENUM` | `CONTRACT:UNSUPPORTED_VALUE` / `NONE` |
| Wrong-type root status subclass | root `status=CustomString("SUCCEEDED")` | 4 exact type; before enum parsing | `AdapterExecutionContractError` | `STRUCTURE_INVALID` | `/status` | `None` | `CONTRACT:STRUCTURE_INVALID` / `NONE` |
| Wrong-type root status Enum | root `status=ArbitraryEnum.SUCCEEDED` | 4 exact type; before enum parsing | `AdapterExecutionContractError` | `STRUCTURE_INVALID` | `/status` | `None` | `CONTRACT:STRUCTURE_INVALID` / `NONE` |
| Unsupported root status literal | root `status="UNKNOWN_STATUS"` as exact built-in `str` | 6 closed enum; after exact type | `AdapterExecutionContractError` | `UNSUPPORTED_VALUE` | `/status` | `UNSUPPORTED_CONTRACT_ENUM` | `CONTRACT:UNSUPPORTED_VALUE` / `NONE` |
| Root unknown plus missing | add safe key `aaa_extra` and omit `schema_version` | 4 key set; unknown wins and missing is not evaluated | `AdapterExecutionContractError` | `STRUCTURE_INVALID` | `/aaa_extra` | `None` | `CONTRACT:STRUCTURE_INVALID` / `NONE` |
| Paid unknown plus missing | add paid key `aaa_extra` and omit paid `schema_version` | 12 key set; unknown wins and missing is not evaluated | `AdapterExecutionContractError` | `STRUCTURE_INVALID` | `/paid_fallback_authorization_evidence/aaa_extra` | `None` | `CONTRACT:STRUCTURE_INVALID` / `NONE` |
| Replay unknown plus missing | add replay key `aaa_extra` and omit replay `schema_version` | 13.1 key set; unknown wins and missing is not evaluated | `AdapterExecutionContractError` | `STRUCTURE_INVALID` | `/replay_evidence/aaa_extra` | `None` | `CONTRACT:STRUCTURE_INVALID` / `NONE` |
| Confidence unknown plus missing | add confidence key `aaa_extra` and omit confidence `schema_version` | 14.1 key set; unknown wins and missing is not evaluated | `AdapterExecutionContractError` | `STRUCTURE_INVALID` | `/confidence_availability_evidence/aaa_extra` | `None` | `CONTRACT:STRUCTURE_INVALID` / `NONE` |
| Multiple root unknown keys | add `z_extra` before `a_extra` in one mapping and reverse insertion order in another | 4 key set; canonical member ordering wins independently of insertion order | `AdapterExecutionContractError` | `STRUCTURE_INVALID` | `/a_extra` | `None` | `CONTRACT:STRUCTURE_INVALID` / `NONE` |
| Multiple root missing keys | with no unknown key, omit `schema_version` and `hash_scope_version` | 4 key set; root schema order selects the first missing key | `AdapterExecutionContractError` | `STRUCTURE_INVALID` | `/schema_version` | `None` | `CONTRACT:STRUCTURE_INVALID` / `NONE` |

### 20.2 Nested type, literal, and syntax precedence examples

| Example | Exact invalid input | Stage and precedence | Exception class | Exact reason | Exact pointer | Exact issue code | Message category / publication |
|---|---|---|---|---|---|---|---|
| Wrong-type replay schema | replay `schema_version=1` | 13.2; before schema literal and all lineage checks | `AdapterExecutionContractError` | `REPLAY_EVIDENCE_INVALID` | `/replay_evidence/schema_version` | `REPLAY_INPUT_MISMATCH` | `CONTRACT:REPLAY_EVIDENCE_INVALID` / `NONE` |
| Unsupported replay schema | replay `schema_version="REPLAY-EVIDENCE-V2"` | 13.3; after exact type, before source scalar and lineage checks | `AdapterExecutionContractError` | `REPLAY_EVIDENCE_INVALID` | `/replay_evidence/schema_version` | `REPLAY_INPUT_MISMATCH` | `CONTRACT:REPLAY_EVIDENCE_INVALID` / `NONE` |
| Wrong-type replay source execution ID | replay `source_adapter_execution_id=1` | 13.4 type; before that field's syntax and all later fields | `AdapterExecutionContractError` | `REPLAY_EVIDENCE_INVALID` | `/replay_evidence/source_adapter_execution_id` | `REPLAY_INPUT_MISMATCH` | `CONTRACT:REPLAY_EVIDENCE_INVALID` / `NONE` |
| Malformed replay source execution ID | replay `source_adapter_execution_id="aex_bad"` | 13.4 syntax; after exact type, before source execution hash | `AdapterExecutionContractError` | `REPLAY_EVIDENCE_INVALID` | `/replay_evidence/source_adapter_execution_id` | `REPLAY_INPUT_MISMATCH` | `CONTRACT:REPLAY_EVIDENCE_INVALID` / `NONE` |
| Wrong-type replay source execution hash | replay `source_adapter_execution_hash=1` | 13.5 type; before that field's syntax and all later fields | `AdapterExecutionContractError` | `REPLAY_EVIDENCE_INVALID` | `/replay_evidence/source_adapter_execution_hash` | `REPLAY_INPUT_MISMATCH` | `CONTRACT:REPLAY_EVIDENCE_INVALID` / `NONE` |
| Malformed replay source execution hash | replay `source_adapter_execution_hash="sha256:"` plus 64 lowercase zeros | 13.5 syntax; after exact type, before source request ID | `AdapterExecutionContractError` | `REPLAY_EVIDENCE_INVALID` | `/replay_evidence/source_adapter_execution_hash` | `REPLAY_HASH_MISMATCH` | `CONTRACT:REPLAY_EVIDENCE_INVALID` / `NONE` |
| Wrong-type replay source request ID | replay `source_alignment_request_id=1` | 13.6 type; before that field's syntax and all later fields | `AdapterExecutionContractError` | `REPLAY_EVIDENCE_INVALID` | `/replay_evidence/source_alignment_request_id` | `REPLAY_INPUT_MISMATCH` | `CONTRACT:REPLAY_EVIDENCE_INVALID` / `NONE` |
| Malformed replay source request ID | replay `source_alignment_request_id="arq_bad"` | 13.6 syntax; after exact type, before source request hash | `AdapterExecutionContractError` | `REPLAY_EVIDENCE_INVALID` | `/replay_evidence/source_alignment_request_id` | `REPLAY_INPUT_MISMATCH` | `CONTRACT:REPLAY_EVIDENCE_INVALID` / `NONE` |
| Wrong-type replay source request hash | replay `source_alignment_request_hash=1` | 13.7 type; before that field's syntax and all lineage checks | `AdapterExecutionContractError` | `REPLAY_EVIDENCE_INVALID` | `/replay_evidence/source_alignment_request_hash` | `REPLAY_INPUT_MISMATCH` | `CONTRACT:REPLAY_EVIDENCE_INVALID` / `NONE` |
| Malformed replay source request hash | replay `source_alignment_request_hash="sha256:"` plus 64 lowercase zeros | 13.7 syntax; after exact type, before all lineage checks | `AdapterExecutionContractError` | `REPLAY_EVIDENCE_INVALID` | `/replay_evidence/source_alignment_request_hash` | `REPLAY_INPUT_MISMATCH` | `CONTRACT:REPLAY_EVIDENCE_INVALID` / `NONE` |
| Wrong-type confidence schema | confidence `schema_version=1` | 14.2; before schema literal and availability access | `AdapterExecutionContractError` | `CONFIDENCE_AVAILABILITY_INVALID` | `/confidence_availability_evidence/schema_version` | `None` | `CONTRACT:CONFIDENCE_AVAILABILITY_INVALID` / `NONE` |
| Unsupported confidence schema | confidence `schema_version="CONFIDENCE-AVAILABILITY-EVIDENCE-V2"` | 14.3; after exact type, before availability access | `AdapterExecutionContractError` | `CONFIDENCE_AVAILABILITY_INVALID` | `/confidence_availability_evidence/schema_version` | `None` | `CONTRACT:CONFIDENCE_AVAILABILITY_INVALID` / `NONE` |
| Wrong-type confidence availability | confidence `availability=1` | 14.4; before enum parsing and state invariant | `AdapterExecutionContractError` | `CONFIDENCE_AVAILABILITY_INVALID` | `/confidence_availability_evidence/availability` | `None` | `CONTRACT:CONFIDENCE_AVAILABILITY_INVALID` / `NONE` |
| Unsupported confidence availability | confidence `availability="available"` | 14.5; after exact type, before state invariant | `AdapterExecutionContractError` | `CONFIDENCE_AVAILABILITY_INVALID` | `/confidence_availability_evidence/availability` | `None` | `CONTRACT:CONFIDENCE_AVAILABILITY_INVALID` / `NONE` |
| Confidence capability/status incompatibility | valid `availability="NOT_APPLICABLE"` for a successful request whose capability is `SUPPORTED` | 14.6; after schema and availability validation | `AdapterExecutionContractError` | `CONFIDENCE_AVAILABILITY_INVALID` | `/confidence_availability_evidence/availability` | `None` | `CONTRACT:CONFIDENCE_AVAILABILITY_INVALID` / `NONE` |

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
| Current request dependency substitution | a different, copied, reconstructed, proxy, subclass, or non-genuine current request rejects before root access |
| Source request dependency substitution | a different, copied, reconstructed, proxy, subclass, non-genuine, or replay-mode source request rejects; its provenance cannot transfer to another object |
| Source execution dependency substitution | a different, copied, reconstructed, proxy, subclass, non-genuine, failed, blocked, replay-mode, or mismatched source execution rejects; its provenance cannot transfer to another object |
| Source dependency mutation or collection | dependencies are frozen and retained only for validation; attempted mutation, collection, stale-registry cleanup, or identity reuse cannot change the published execution or make a replacement genuine |
| Canonical bytes mutation attempt | returned `bytes` cannot be mutated; mutable copy changes no object state |
| Returned mapping mutation | any private/test projection copy can be mutated without changing the genuine object |
| Returned sequence mutation | no public sequence is returned; any test-helper copy is caller-owned and cannot change object state |
| Enum substitution | arbitrary Enum, `str` subclass, alias, case variant, or spelling variant is rejected |
| Hash substitution | mismatch rejects before ID verification and publishes nothing |
| Request-binding substitution | different request ID/hash or forged dependency rejects before hashing |
| Replay-lineage substitution | distinct current replay request plus exact genuine non-replay source request/execution pair is required; copied, replay-mode, failed, blocked, mismatched, ambiguous, self-referential, or cycle-capable lineage rejects |

Registry tests shall also cover collection cleanup, stale cleanup replacement
safety, source-dependency provenance non-transfer, insertion failure,
verification false/exception rollback, subclass, proxy, copy, deep copy,
pickle, and reconstructed dataclass rejection.

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
- root `mode` and `status` scalar-oracle tests proving exact built-in `str`
  values reach closed-enum parsing, `str` subclasses and arbitrary Enum
  members reject at stage 4, unsupported exact-string literals reject at
  stage 6, and exact-type failure precedes enum parsing; every case asserts
  exact pointer, reason, issue code, stable message category, publication
  `NONE`, and no sensitive-value leakage;
- exact-key-set tests for the root, paid, replay, and confidence mappings,
  covering wrong mapping/root type, non-exact-string member names, unknown
  only, missing only, simultaneous unknown plus missing, multiple unknown keys
  in different insertion orders, and multiple missing required keys;
- key-set oracle tests proving unknown always precedes missing, the selected
  unknown key follows canonical JSON member ordering independently of mapping
  insertion order, the selected missing key follows that mapping's section 17
  schema order, and known-field scalar validation never runs before the
  key-set winner; every mapping asserts exact pointer, reason
  `STRUCTURE_INVALID`, issue code `None`, message category
  `CONTRACT:STRUCTURE_INVALID`, publication `NONE`, and no sensitive-value
  leakage;
- all 15 mode/status matrix rows;
- every required/forbidden evidence-presence boundary;
- genuine `AlignmentRequest` binding, adapter parity, and request-mode parity;
- approved paid fallback retaining the exact request adapter identity, plus
  rejection of a different paid adapter ID or version;
- paid-fallback source, decision, ID, binding, and forbidden-data tests;
- exact stage-12 paid-evidence oracle tests for schema wrong type and
  unsupported literal; authorization ID wrong type and malformed syntax;
  source wrong type and unsupported/coerced value; decision wrong type and
  unsupported/coerced value; request ID/hash wrong type, malformed syntax,
  and binding mismatch; and decision/status incompatibility;
- valid `REPLAY/SUCCEEDED` and `REPLAY/FAILED` materialization using a genuine
  current `REPLAY` request, a distinct genuine non-`REPLAY` source request,
  and its genuine successful non-`REPLAY` source execution;
- exact tests proving current request ID/hash bind only the current execution,
  source execution request ID/hash bind the source request, replay evidence
  binds that same source request and source execution, and current/source
  request identities are distinct roles;
- exact stage-13 replay-evidence oracle tests in field order for schema wrong
  type and unsupported literal; source execution ID wrong type and malformed
  syntax; source execution hash wrong type and malformed syntax; source
  request ID wrong type and malformed syntax; and source request hash wrong
  type and malformed syntax;
- replay hash-code tests proving malformed or content-mismatched source
  execution hash uses `REPLAY_HASH_MISMATCH`, while its wrong exact type and
  every source-request hash type/syntax failure use
  `REPLAY_INPUT_MISMATCH`;
- replay rejection tests for source status other than `SUCCEEDED`, source
  request mode `REPLAY`, source execution mode `REPLAY`, source
  execution/source request mode mismatch, source request ID mismatch, source
  request hash mismatch, source execution ID mismatch, source execution hash
  mismatch, current/source request role confusion, direct self-reference,
  ambiguous lineage, replay-of-replay, and cycle-capable lineage;
- exact stage-14 confidence-evidence oracle tests for schema wrong type and
  unsupported literal; availability wrong type and unsupported/coerced value;
  and capability/status incompatibility, without numeric confidence;
- multi-fault nested-order tests proving replay scalar type validation
  precedes syntax and lineage comparison, replay schema validation precedes
  every source-lineage check, confidence schema validation precedes
  availability parsing, and availability parsing precedes capability/status
  invariants;
- paired replay tests distinguishing wrong exact type, unsupported literal,
  malformed syntax, valid syntax with dependency mismatch, and valid
  dependency binding with lineage failure;
- pre-input dependency validation tests proving exact order
  `alignment_request`, non-null `source_alignment_request`, non-null
  `source_execution`, and proving every invalid dependency rejects before raw
  root access;
- wrong-type and exact-type-but-non-genuine `alignment_request` preflight
  tests proving exact `TypeError`, non-applicable pointer/reason/issue-code,
  stable category token `PREREQUISITE:alignment_request`, no exact-message
  assertion because message text is non-stable, and raw-input non-access;
- tests proving that `alignment_request` follows the prerequisite `TypeError`
  boundary while invalid/non-genuine `source_alignment_request` and
  `source_execution` use `AdapterExecutionContractError`, their exact
  dependency pointers, reason `NOT_MATERIALIZED`, and issue code `None`;
- mode-dependent source-dependency presence tests proving `REPLAY` requires
  both and every non-`REPLAY` mode forbids both only after mode parsing, with
  `source_alignment_request` presence failure preceding `source_execution`;
- wrong-type, non-genuine, missing, and forbidden tests for each source
  dependency;
- multi-fault ordering where invalid non-null source request wins before an
  invalid non-null source execution and both win before raw input access;
- multi-fault ordering where each source dependency's absence/presence
  compatibility is evaluated only after root mode parsing;
- multi-fault deterministic validation-order tests;
- one exact oracle test for every section 18.2 row, asserting stage precedence,
  exception class, pointer, reason, issue code, stable message category,
  publication `NONE`, and no sensitive-value leakage;
- duplicate root and each nested evidence duplicate containing-object pointer
  test, plus safe/unsafe unknown-key pointer tests;
- depth-first sensitive-scan first-failure tests at root, paid evidence, and
  replay evidence, including exact redacted message behavior;
- failed replay source and current request-mode parity tests asserting their
  distinct exact mappings;
- the complete mutation-resistance matrix, including every added source
  dependency and source-registry provenance non-transfer;
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

This specification defines only immutable execution provenance bound to a
genuine current `AlignmentRequest`, closed execution modes/statuses, evidence
presence, canonical request and adapter binding, paid authorization evidence,
replay lineage verified from explicit genuine source `AlignmentRequest` and
`AdapterExecution` dependencies, confidence availability evidence, immutable
canonical serialization, identity, hashing, publication, errors, golden
oracles, and future mutation-resistant tests. Source dependencies are
validation-only and introduce no runtime, database, network, provider, or
mutable-cache lookup.

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
