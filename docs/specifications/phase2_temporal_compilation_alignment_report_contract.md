# Phase 2 Temporal Compilation + Alignment Report Contract

## 1. Status and authority

Status: Candidate specification

Accepted: No

Implementation authorized: No

Phase 2 closed: No

This is the single cohesive specification for the next Phase 2 macro-package
selected by docs/NEXT_ACTIONS.md. It is subordinate to docs/MASTER_ROADMAP.md
and specifies WordToFrameCompiler together with AlignmentReport. It assigns no
Slice number, total Slice count, or Phase 2 completion percentage.

## 2. Bounded purpose

The macro-package consumes only accepted canonical inputs. It provides:

- deterministic word, caption-group, and emphasis-event frame spans derived
  from accepted millisecond boundaries and one explicit rational frame rate;
- exact integer arithmetic and a strict less-than-one-frame boundary-drift
  proof without float, round, a global FPS value, or authored frames;
- an independent confidence report over genuine current narration,
  AlignmentResult, and CaptionGroupsArtifact inputs;
- caller-supplied, fully explicit integer-millionths report policy with no
  defaults or silent fallback;
- distinct AVAILABLE, UNAVAILABLE, and NOT_APPLICABLE report semantics;
- stable identities, canonical bytes, provenance, mutation resistance,
  sanitized errors, and deterministic first-failure precedence; and
- REPLAY-only fixtures and focused/upstream regression gates.

No caller, LLM, UI, provider, loader, or legacy V2 path may supply or override
milliseconds, frame boundaries, confidence observations, finding identities,
metrics, status, or output identities.

## 3. Explicit exclusions

This specification does not authorize CaptionPreviewRenderer, V5/V6 layout or
collision validation, timing-file publication, artifact lifecycle, Remotion,
EDL, FFmpeg integration, providers, paid APIs, UI, queues, retry policy,
additional Domain Packs, Phase 3 work, or any later-phase feature. It does not
change accepted upstream contracts or stable issue-code inventory. It makes no
Phase 2 closure or production-readiness claim.

## 4. Future paths and import boundaries

The exact production and focused-test paths are:

    engine/contracts/word_to_frame.py
    engine/contracts/alignment_report.py
    tests/test_word_to_frame.py
    tests/test_alignment_report.py

Shared integration is additive only:

    engine/contracts/__init__.py
    tests/test_alignment_request.py

Both modules may import only _canonical_json, accepted narration/alignment/
caption/emphasis contract types and serializers, ConfidenceAvailability,
AlignmentTimingSource, and the stable temporal issue-code inventory. Neither
module imports the other. Forbidden imports include V2, provider/runtime
orchestration, filesystem, network, database/cache, UI, renderer, preview,
Remotion, EDL, FFmpeg, subprocess, thread, clock, random, or Phase 3 code.
Compile, load, and serialize perform no I/O.

Narration currently exposes no public canonical serializer. Therefore
alignment_report.py is explicitly permitted to import exactly these four
existing private narration predicates, and no other narration private:

    _has_materialized_narration_document_identity
    _has_materialized_narration_revision_identity
    _is_materialized_narration_document
    _is_materialized_narration_revision

The two has-identity predicates distinguish an exact registered object that
has drifted from a copy/proxy/reconstruction that never owned accepted
identity. The two is-materialized predicates verify current content. This
bounded import does not create a new public upstream API and may not be
re-exported. word_to_frame.py does not import these predicates.

## 5. Exact combined public export delta

word_to_frame.py adds exactly these twelve public symbols:

    WORD_TO_FRAME_V1
    WORD_TO_FRAME_HASH_V1
    WORD_TO_FRAME_POLICY_V1
    TemporalFrameRate
    TemporalFrameSpanKind
    TemporalCompiledFrameSpan
    WordToFrameArtifact
    WordToFrameRejectionReason
    WordToFrameContractError
    compile_word_to_frame
    load_word_to_frame
    serialize_word_to_frame

alignment_report.py adds exactly these sixteen public symbols:

    ALIGNMENT_REPORT_V1
    ALIGNMENT_REPORT_HASH_V1
    ALIGNMENT_REPORT_FINDING_V1
    ALIGNMENT_REPORT_FINDING_HASH_V1
    ALIGNMENT_REPORT_POLICY_V1
    AlignmentReportStatus
    AlignmentFindingSeverity
    AlignmentFindingScope
    AlignmentReportRejectionReason
    AlignmentReportPolicy
    AlignmentReportFinding
    AlignmentReport
    AlignmentReportContractError
    compile_alignment_report
    load_alignment_report
    serialize_alignment_report

No helper, registry, projection, encoder, threshold resolver, frame mapper, or
mutable builder is public. The collision-safe Temporal names are normative;
generic FrameRate or FrameSpan names are forbidden.

## 6. Word-to-frame constants, enums, and models

    WORD_TO_FRAME_V1 = "WORD-TO-FRAME-V1"
    WORD_TO_FRAME_HASH_V1 = "WORD-TO-FRAME-HASH-V1"
    WORD_TO_FRAME_POLICY_V1 = "WORD-TO-FRAME-POLICY-V1"

    class TemporalFrameSpanKind(str, Enum):
        WORD = "WORD"
        CAPTION_GROUP = "CAPTION_GROUP"
        EMPHASIS_EVENT = "EMPHASIS_EVENT"

    class WordToFrameRejectionReason(str, Enum):
        STRUCTURE_INVALID = "STRUCTURE_INVALID"
        UNSUPPORTED_VALUE = "UNSUPPORTED_VALUE"
        DEPENDENCY_CONTENT_DRIFT = "DEPENDENCY_CONTENT_DRIFT"
        DEPENDENCY_BINDING_INVALID = "DEPENDENCY_BINDING_INVALID"
        FRAME_RATE_INVALID = "FRAME_RATE_INVALID"
        SOURCE_RANGE_INVALID = "SOURCE_RANGE_INVALID"
        TIMING_INVALID = "TIMING_INVALID"
        FRAME_MAPPING_INVALID = "FRAME_MAPPING_INVALID"
        NON_CANONICAL_SERIALIZATION = "NON_CANONICAL_SERIALIZATION"
        IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
        CONTENT_DRIFT = "CONTENT_DRIFT"
        NOT_MATERIALIZED = "NOT_MATERIALIZED"

Field order is normative:

    @dataclass(frozen=True)
    class TemporalFrameRate:
        numerator: int
        denominator: int

    @dataclass(frozen=True)
    class TemporalCompiledFrameSpan:
        source_kind: TemporalFrameSpanKind
        source_id: str
        ordinal: int
        start_word_ordinal: int
        end_exclusive_word_ordinal: int
        start_word_id: str
        end_word_id: str
        start_ms: int
        end_ms: int
        start_frame: int
        end_exclusive_frame: int

    @dataclass(frozen=True)
    class WordToFrameArtifact:
        schema_version: str
        hash_scope_version: str
        word_to_frame_id: str
        word_to_frame_hash: str
        project_id: str
        document_id: str
        narration_revision_id: str
        narration_revision_hash: str
        alignment_result_id: str
        alignment_result_hash: str
        caption_groups_id: str
        caption_groups_hash: str
        emphasis_events_id: str
        emphasis_events_hash: str
        confidence_availability: ConfidenceAvailability
        mapping_policy_version: str
        frame_rate: TemporalFrameRate
        word_frames: tuple[TemporalCompiledFrameSpan, ...]
        caption_frames: tuple[TemporalCompiledFrameSpan, ...]
        emphasis_frames: tuple[TemporalCompiledFrameSpan, ...]

All fields are required and non-null. A span contains no text, confidence,
style, path, extension, or arbitrary metadata. Span-level identities are not
added: accepted source_id plus the root hash is the closed identity boundary.

## 7. Word-to-frame exact signatures

    def compile_word_to_frame(
        *,
        alignment_result: AlignmentResult,
        caption_groups: CaptionGroupsArtifact,
        emphasis_events: EmphasisEventsArtifact,
        frame_rate: TemporalFrameRate,
    ) -> WordToFrameArtifact

    def load_word_to_frame(
        source: bytes,
        *,
        alignment_result: AlignmentResult,
        caption_groups: CaptionGroupsArtifact,
        emphasis_events: EmphasisEventsArtifact,
        frame_rate: TemporalFrameRate,
    ) -> WordToFrameArtifact

    def serialize_word_to_frame(
        artifact: WordToFrameArtifact,
    ) -> bytes

The keyword-only order is exact. There is no seconds, frames, ranges, FPS,
mapping callback, default profile, or policy override argument.

## 8. Rational frame-rate and mapping policy

TemporalFrameRate must be its exact dataclass type. Numerator and denominator
must be exact int, not bool, in 1..2**32-1, and gcd must equal one; the compiler
does not silently reduce. The exact rate must satisfy 1 <= numerator /
denominator <= 240 using cross multiplication only. Common fractional rates
including 24000/1001, 30000/1001, and 60000/1001 are valid.

Every output uses the half-open interval [start_frame,end_exclusive_frame).
For scale = 1000 * denominator, the only permitted mapping is:

    start_frame = (start_ms * numerator) // scale
    end_exclusive_frame = (
        end_ms * numerator + scale - 1
    ) // scale

Float, Decimal, Fraction-to-float, round, banker's rounding, epsilon, global
FPS, cumulative-duration scheduling, padding, or minimum-duration repair is
forbidden. Positive upstream duration proves end_exclusive_frame >
start_frame. Every output frame index must be in 0..2**53-1 for exact
JavaScript/Remotion integer transport.

For any mapped boundary, let x = timestamp_ms * numerator. Start uses floor and
end uses ceil, therefore its absolute boundary error numerator is strictly
less than scale. The implementation and tests must prove:

    abs(frame * scale - x) < scale

Adjacent source intervals may share one covered frame because one end is ceil
and the next start is floor; this is deterministic coverage behavior, not
timestamp repair. No per-frame array is produced.

## 9. Word-to-frame derivation and dependency rules

Only genuine, currently registered, exact AlignmentResult,
CaptionGroupsArtifact, and EmphasisEventsArtifact values are accepted.
Preflight invokes their public canonical serializers and rejects copies,
subclasses, proxies, reconstructions, stale objects, or post-materialization
mutation. It then checks, in order:

1. project, document, narration revision ID/hash equality;
2. caption root alignment ID/hash equality;
3. emphasis root alignment and caption ID/hash equality;
4. confidence-availability equality across all three roots;
5. complete word inventory and canonical ordinal/word-ID order;
6. caption partition, source IDs, ranges, endpoints, and timing derivation;
7. emphasis source IDs, ranges, caption binding, endpoints, and timing; and
8. exact frame-rate validity.

One WORD span is emitted per word timing; source_id is word_id and its range is
[ordinal,ordinal+1). One CAPTION_GROUP span and one EMPHASIS_EVENT span is
emitted per accepted source in its accepted ordinal order. Word IDs,
milliseconds, and ranges are copied from the accepted semantic sources, never
searched by string. The artifact owns newly constructed immutable values and
retains no dependency or caller frame-rate object.

## 10. Word-to-frame identity, loader, and error oracle

The root projection is every WordToFrameArtifact field except
word_to_frame_id and word_to_frame_hash. Canonical compact sorted-key UTF-8
bytes are hashed as lowercase SHA-256:

    word_to_frame_hash = sha256(projection_bytes).hexdigest()
    word_to_frame_id = "w2f_" + word_to_frame_hash[:32]

Compile precedence is exact dependency type, current-content genuineness,
cross-binding, source inventory, frame rate, derivation, identity, registry.
Load performs the same preflight before source parsing, then canonical syntax,
root exact keys/types/constants/declarations, frame rate declaration, word
spans, caption spans, emphasis spans, root hash, root ID, full recomputed
envelope equality, source-byte equality, and transactional registry publish.
Unknown key wins before missing key; lower field then lower array index wins.

| Fault | Pointer | Reason | Issue code |
|---|---|---|---|
| alignment/caption/emphasis current-content drift | exact dependency pointer | DEPENDENCY_CONTENT_DRIFT | REPLAY_HASH_MISMATCH |
| root lineage or confidence binding mismatch | exact dependency pointer | DEPENDENCY_BINDING_INVALID | ALIGNMENT_REQUEST_IDENTITY_MISMATCH or ADAPTER_PRECISION_OVERSTATED for confidence |
| invalid, non-reduced, out-of-policy rational | /frame_rate | FRAME_RATE_INVALID | FRAME_RATE_INVALID |
| source ID/range/count mismatch | exact span pointer | SOURCE_RANGE_INVALID | CANONICAL_COVERAGE_BLOCKER |
| ordinal/order mismatch | exact span pointer | SOURCE_RANGE_INVALID | CANONICAL_WORD_ORDER_INVALID |
| source millisecond mismatch | exact span pointer | TIMING_INVALID | ADAPTER_PRECISION_OVERSTATED |
| frame value differs and drift is at least one frame | exact span pointer | FRAME_MAPPING_INVALID | FRAME_BOUNDARY_DRIFT_EXCEEDED |
| frame differs from canonical mapping but drift is below one frame | exact span pointer | FRAME_MAPPING_INVALID | null |
| unsupported schema/hash/policy/kind/confidence literal | containing pointer | UNSUPPORTED_VALUE | UNSUPPORTED_CONTRACT_ENUM |
| source shape/type/unknown/missing key | containing pointer | STRUCTURE_INVALID | null |
| root hash, then ID mismatch | / | IDENTITY_MISMATCH | null |
| invalid/BOM/duplicate/trailing/noncanonical source bytes | / | NON_CANONICAL_SERIALIZATION | null |
| registered output mutation | / | CONTENT_DRIFT | null |
| direct/unregistered serialization | / | NOT_MATERIALIZED | null |

Errors contain only fixed sanitized messages and fixed pointers. Permitted
indexed pointers are /word_frames/N, /caption_frames/N, and
/emphasis_frames/N. Attacker text, paths, IDs, values, or nested exceptions
never enter the message.

## 11. Alignment-report constants and enums

    ALIGNMENT_REPORT_V1 = "ALIGNMENT-REPORT-V1"
    ALIGNMENT_REPORT_HASH_V1 = "ALIGNMENT-REPORT-HASH-V1"
    ALIGNMENT_REPORT_FINDING_V1 = "ALIGNMENT-REPORT-FINDING-V1"
    ALIGNMENT_REPORT_FINDING_HASH_V1 = "ALIGNMENT-REPORT-FINDING-HASH-V1"
    ALIGNMENT_REPORT_POLICY_V1 = "ALIGNMENT-REPORT-POLICY-V1"

    class AlignmentReportStatus(str, Enum):
        PASS = "PASS"
        REVIEW_REQUIRED = "REVIEW_REQUIRED"
        BLOCKED = "BLOCKED"
        CONFIDENCE_UNAVAILABLE = "CONFIDENCE_UNAVAILABLE"
        CONFIDENCE_NOT_APPLICABLE = "CONFIDENCE_NOT_APPLICABLE"

    class AlignmentFindingSeverity(str, Enum):
        WARNING = "WARNING"
        BLOCKER = "BLOCKER"

    class AlignmentFindingScope(str, Enum):
        WORD = "WORD"
        CAPTION_GROUP = "CAPTION_GROUP"
        REPORT = "REPORT"

    class AlignmentReportRejectionReason(str, Enum):
        STRUCTURE_INVALID = "STRUCTURE_INVALID"
        UNSUPPORTED_VALUE = "UNSUPPORTED_VALUE"
        DEPENDENCY_CONTENT_DRIFT = "DEPENDENCY_CONTENT_DRIFT"
        DEPENDENCY_BINDING_INVALID = "DEPENDENCY_BINDING_INVALID"
        POLICY_INVALID = "POLICY_INVALID"
        CONFIDENCE_INVALID = "CONFIDENCE_INVALID"
        FINDING_INVALID = "FINDING_INVALID"
        NON_CANONICAL_SERIALIZATION = "NON_CANONICAL_SERIALIZATION"
        IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
        CONTENT_DRIFT = "CONTENT_DRIFT"
        NOT_MATERIALIZED = "NOT_MATERIALIZED"

Enum values and declaration order are exact and closed. NOT_APPLICABLE is a
status, not a stable issue code; no new issue code is added.

## 12. Alignment-report exact models and signatures

Field order is normative:

    @dataclass(frozen=True)
    class AlignmentReportPolicy:
        policy_version: str
        individual_warning_below_millionths: int
        individual_blocker_below_millionths: int
        caption_group_warning_below_millionths: int
        caption_group_blocker_below_millionths: int
        low_confidence_ratio_warning_at_or_above_millionths: int
        low_confidence_ratio_blocker_at_or_above_millionths: int

    @dataclass(frozen=True)
    class AlignmentReportFinding:
        schema_version: str
        hash_scope_version: str
        alignment_report_finding_id: str
        alignment_report_finding_hash: str
        alignment_result_id: str
        caption_groups_id: str
        alignment_report_policy_snapshot_hash: str
        ordinal: int
        issue_code: str
        severity: AlignmentFindingSeverity
        scope: AlignmentFindingScope
        word_ordinal: int | None
        word_id: str | None
        caption_group_ordinal: int | None
        caption_group_id: str | None
        start_word_ordinal: int | None
        end_exclusive_word_ordinal: int | None
        observed_millionths: int | None
        threshold_millionths: int | None

    @dataclass(frozen=True)
    class AlignmentReport:
        schema_version: str
        hash_scope_version: str
        alignment_report_id: str
        alignment_report_hash: str
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
        alignment_result_id: str
        alignment_result_hash: str
        caption_groups_id: str
        caption_groups_hash: str
        timing_source: AlignmentTimingSource
        confidence_availability: ConfidenceAvailability
        alignment_report_policy: AlignmentReportPolicy
        alignment_report_policy_snapshot_hash: str
        word_count: int
        caption_group_count: int
        evaluated_word_confidence_count: int
        evaluated_caption_group_confidence_count: int
        minimum_word_confidence_millionths: int | None
        minimum_caption_group_confidence_millionths: int | None
        low_confidence_word_count: int
        low_confidence_caption_group_count: int
        low_confidence_word_ratio_millionths: int | None
        warning_finding_count: int
        blocker_finding_count: int
        status: AlignmentReportStatus
        findings: tuple[AlignmentReportFinding, ...]

    def compile_alignment_report(
        *,
        narration_document: CanonicalNarrationDocument,
        narration_revision: NarrationRevision,
        alignment_result: AlignmentResult,
        caption_groups: CaptionGroupsArtifact,
        policy: AlignmentReportPolicy,
    ) -> AlignmentReport

    def load_alignment_report(
        source: bytes,
        *,
        narration_document: CanonicalNarrationDocument,
        narration_revision: NarrationRevision,
        alignment_result: AlignmentResult,
        caption_groups: CaptionGroupsArtifact,
        policy: AlignmentReportPolicy,
    ) -> AlignmentReport

    def serialize_alignment_report(report: AlignmentReport) -> bytes

The keyword-only order is exact. Policy must be present; there is no default,
partial dict, environment policy, or Domain Pack fallback.

## 13. Report dependency and policy validation

Exact genuine current narration document, narration revision, AlignmentResult,
and CaptionGroupsArtifact values are required and validated through accepted
serializers/registries before policy or source bytes. Cross-binding validates
document current revision; project/document/revision ID/hash; alignment
lineage; caption alignment ID/hash; complete word coverage; exact caption
partition; timing; and confidence availability, in that order.

Policy and all seven fields must be exact types; bool, float, stringified
integer, subclass, mapping, or omitted field is invalid. Policy version must
equal ALIGNMENT-REPORT-POLICY-V1. All thresholds are in 0..1_000_000 and:

    0 <= individual_blocker < individual_warning <= 1_000_000
    0 <= caption_group_blocker < caption_group_warning <= 1_000_000
    0 <= ratio_warning < ratio_blocker <= 1_000_000

The compiler reconstructs an owned policy copy. Its snapshot hash is:

    "sha256:" + sha256(canonical exact seven-field policy bytes).hexdigest()

No caller object is retained. Policy validation precedes confidence evaluation.

## 14. Confidence metrics, findings, order, and status

For AVAILABLE, every word and caption group must have exact integer confidence
in 0..1_000_000. A word below blocker threshold emits only
INDIVIDUAL_CONFIDENCE_BLOCKER/BLOCKER; otherwise below warning emits
INDIVIDUAL_CONFIDENCE_WARNING/WARNING. Caption groups use the analogous
SEGMENT_CONFIDENCE_BLOCKER and SEGMENT_CONFIDENCE_WARNING codes. Blocker
suppresses warning for the same target.

low_confidence_word_count counts words strictly below the individual warning
threshold. low_confidence_caption_group_count analogously uses the group
warning threshold. Stored word ratio is floor(low_count * 1_000_000 /
evaluated_word_confidence_count), but warning/blocker gates use exact cross
multiplication:

    low_count * 1_000_000 >= threshold * evaluated_word_confidence_count

This avoids a floor-rounding decision error. Ratio blocker suppresses ratio
warning and uses LOW_CONFIDENCE_RATIO_BLOCKER; otherwise the warning code is
LOW_CONFIDENCE_RATIO_WARNING.

Finding order is exact: word ordinal order, caption-group ordinal order,
aggregate word-ratio finding, then the unavailable singleton. Ordinal is the
final contiguous unsigned-32-bit list index. Finding count may not exceed
word_count + caption_group_count + 1. The only emitted issue codes are the
closed seven-code allowlist INDIVIDUAL_CONFIDENCE_WARNING,
INDIVIDUAL_CONFIDENCE_BLOCKER, SEGMENT_CONFIDENCE_WARNING,
SEGMENT_CONFIDENCE_BLOCKER, LOW_CONFIDENCE_RATIO_WARNING,
LOW_CONFIDENCE_RATIO_BLOCKER, and CONFIDENCE_UNAVAILABLE. Null matrix is
closed:

- WORD: word ordinal/id set; all caption/range target fields null.
- CAPTION_GROUP: group ordinal/id and start/end range set; word fields null.
- REPORT: every word/group/range target field null.
- AVAILABLE findings have observed and selected threshold set.
- UNAVAILABLE singleton has observed and threshold null.

Status derivation first branches on confidence availability. Only for
AVAILABLE is precedence BLOCKED when blocker count is nonzero, otherwise
REVIEW_REQUIRED when warning count is nonzero, otherwise PASS.

For UNAVAILABLE, evaluated counts are zero, minima and ratio are null, low
counts are zero, and exactly one REPORT/WARNING CONFIDENCE_UNAVAILABLE finding
is emitted; status is CONFIDENCE_UNAVAILABLE. For NOT_APPLICABLE, the same
metrics are null/zero but findings and counts are empty/zero; status is
CONFIDENCE_NOT_APPLICABLE. No stable NOT_APPLICABLE issue code may be invented.

## 15. Finding/report identities and report independence

Each finding projection is every finding field except its ID/hash. It binds
alignment_result_id, caption_groups_id, and policy snapshot hash so equivalent
observations from different reports cannot share an identity accidentally:

    finding_hash = sha256(canonical finding projection).hexdigest()
    finding_id = "alrf_" + finding_hash[:32]

The report projection is every root field except alignment_report_id/hash:

    report_hash = sha256(canonical report projection).hexdigest()
    report_id = "alrep_" + report_hash[:32]

AlignmentReport neither imports nor accepts WordToFrameArtifact, frame rate,
frame spans, frame findings, or a private mapping helper. Frame acceptance and
confidence-report acceptance combine only at the macro-package gate.

## 16. Report validation precedence and closed error oracle

Compile precedence is exact dependency types/current content, cross-binding,
policy type/version/ranges/order/hash, confidence state, metrics, findings in
canonical order, finding hash/ID, report hash/ID, registry. Load runs identical
preflight before bytes, then canonical syntax, root exact shape/types/literals/
declarations, owned policy/hash, metrics/status, findings by index and null
matrix, finding hash then ID, report hash then ID, fully recomputed equality,
source-byte equality, transactional publish. Unknown key wins before missing;
lower model field and lower array index win.

| Fault | Pointer | Reason | Issue code |
|---|---|---|---|
| narration/alignment/caption current-content drift | exact dependency pointer | DEPENDENCY_CONTENT_DRIFT | ALIGNMENT_REQUEST_IDENTITY_MISMATCH for narration; REPLAY_HASH_MISMATCH otherwise |
| lineage, timing-source, or root binding mismatch | exact dependency pointer | DEPENDENCY_BINDING_INVALID | ALIGNMENT_REQUEST_IDENTITY_MISMATCH |
| dependency confidence declarations disagree | /caption_groups | CONFIDENCE_INVALID | ADAPTER_PRECISION_OVERSTATED |
| policy type/version/range/order/hash invalid | /policy or /alignment_report_policy | POLICY_INVALID | UNSUPPORTED_CONTRACT_ENUM only for version, otherwise null |
| AVAILABLE missing confidence | exact target pointer | CONFIDENCE_INVALID | CONFIDENCE_REQUIRED_UNAVAILABLE |
| non-null confidence for UNAVAILABLE/NOT_APPLICABLE or invalid bound | exact target pointer | CONFIDENCE_INVALID | ADAPTER_PRECISION_OVERSTATED |
| finding code/severity/scope/null matrix/order/metric differs | /findings/N | FINDING_INVALID | exact expected stable finding code when applicable, otherwise null |
| unsupported schema/hash/timing/confidence/status/finding enum | containing pointer | UNSUPPORTED_VALUE | UNSUPPORTED_CONTRACT_ENUM |
| source/root/finding shape, count, scalar, unknown/missing key | containing pointer | STRUCTURE_INVALID | null |
| finding hash then ID mismatch | /findings/N | IDENTITY_MISMATCH | null |
| report hash then ID mismatch | / | IDENTITY_MISMATCH | null |
| invalid/BOM/duplicate/trailing/noncanonical source bytes | / | NON_CANONICAL_SERIALIZATION | null |
| registered report mutation | / | CONTENT_DRIFT | null |
| direct/unregistered serialization | / | NOT_MATERIALIZED | null |

Errors expose only fixed pointers/reasons/codes and fixed sanitized messages.
No narration text, ID, path, policy value, attacker key/value, or nested
exception is included.

## 17. Canonical wire and mutation rules shared by both modules

Canonical wire is UTF-8 compact JSON with sorted keys, no BOM, duplicate key,
float, negative zero, NaN/infinity, trailing byte/newline, unknown key,
extension, or non-NFC text. Load accepts exact built-in bytes only. Compile and
load publish only after every check; failure publishes no ID/hash/bytes/object.

Each module uses a private weak registry keyed by object identity and stores a
weak reference, immutable canonical envelope bytes, and recursive exact-type
identity signature. Serialize rejects equal-value copies, proxies, subclasses,
unregistered construction, nested replacement, container replacement, and
post-registration mutation. Registry insertion is transactional and handles
identity collision, rollback, stale callback, and garbage collection without
retaining dependencies or caller values.

## 18. Frozen WordToFrame golden FX-W2F-01

FX-W2F-01 uses the accepted FX-EME-01 dependencies and TemporalFrameRate(30,1).
Frame spans are words [3,15), [15,27), [36,51), [51,69); captions [3,27),
[36,69); and emphasis [3,27). The full literal canonical projection bytes are:

    {"alignment_result_hash":"1521f195a591df09edaa968d8f5fa91ed367be1c7190a3f614823d74b3cd36bb","alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","caption_frames":[{"end_exclusive_frame":27,"end_exclusive_word_ordinal":2,"end_ms":900,"end_word_id":"nword_0cc9d55672a3cb4e9199","ordinal":0,"source_id":"cgrp_2bdd1bc0e985d5d45784956cb0818fb9","source_kind":"CAPTION_GROUP","start_frame":3,"start_ms":100,"start_word_id":"nword_5321ba14c2c4b28c31ab","start_word_ordinal":0},{"end_exclusive_frame":69,"end_exclusive_word_ordinal":4,"end_ms":2300,"end_word_id":"nword_d81fe913754f8b49c296","ordinal":1,"source_id":"cgrp_5b9b84abe4eba87d448e56b87ff277d6","source_kind":"CAPTION_GROUP","start_frame":36,"start_ms":1200,"start_word_id":"nword_49e85bb034c88ef36f26","start_word_ordinal":2}],"caption_groups_hash":"12670fe861389bfe8e25f05a126c7ea355c361c2b2848e9b02a216ed83baaec7","caption_groups_id":"cgs_12670fe861389bfe8e25f05a126c7ea3","confidence_availability":"AVAILABLE","document_id":"nardoc_fx34","emphasis_events_hash":"e6286517914a305715e42460d27092370bf304f6715e28a6c483407758a04b7d","emphasis_events_id":"emps_e6286517914a305715e42460d2709237","emphasis_frames":[{"end_exclusive_frame":27,"end_exclusive_word_ordinal":2,"end_ms":900,"end_word_id":"nword_0cc9d55672a3cb4e9199","ordinal":0,"source_id":"emph_3b919932a4e05683fe94c9eae048341b","source_kind":"EMPHASIS_EVENT","start_frame":3,"start_ms":100,"start_word_id":"nword_5321ba14c2c4b28c31ab","start_word_ordinal":0}],"frame_rate":{"denominator":1,"numerator":30},"hash_scope_version":"WORD-TO-FRAME-HASH-V1","mapping_policy_version":"WORD-TO-FRAME-POLICY-V1","narration_revision_hash":"sha256:d60d7ae087efb0e309d4e3f28fedea074d15e11405046249a23b2c7bb42fe0c0","narration_revision_id":"narrev_d60d7ae087efb0e309d4","project_id":"prj_fx34","schema_version":"WORD-TO-FRAME-V1","word_frames":[{"end_exclusive_frame":15,"end_exclusive_word_ordinal":1,"end_ms":500,"end_word_id":"nword_5321ba14c2c4b28c31ab","ordinal":0,"source_id":"nword_5321ba14c2c4b28c31ab","source_kind":"WORD","start_frame":3,"start_ms":100,"start_word_id":"nword_5321ba14c2c4b28c31ab","start_word_ordinal":0},{"end_exclusive_frame":27,"end_exclusive_word_ordinal":2,"end_ms":900,"end_word_id":"nword_0cc9d55672a3cb4e9199","ordinal":1,"source_id":"nword_0cc9d55672a3cb4e9199","source_kind":"WORD","start_frame":15,"start_ms":520,"start_word_id":"nword_0cc9d55672a3cb4e9199","start_word_ordinal":1},{"end_exclusive_frame":51,"end_exclusive_word_ordinal":3,"end_ms":1700,"end_word_id":"nword_49e85bb034c88ef36f26","ordinal":2,"source_id":"nword_49e85bb034c88ef36f26","source_kind":"WORD","start_frame":36,"start_ms":1200,"start_word_id":"nword_49e85bb034c88ef36f26","start_word_ordinal":2},{"end_exclusive_frame":69,"end_exclusive_word_ordinal":4,"end_ms":2300,"end_word_id":"nword_d81fe913754f8b49c296","ordinal":3,"source_id":"nword_d81fe913754f8b49c296","source_kind":"WORD","start_frame":51,"start_ms":1720,"start_word_id":"nword_d81fe913754f8b49c296","start_word_ordinal":3}]}

    projection length=3009
    word_to_frame_hash=285a114d06e92fe5c431ea1e51ebafd9be72476034a7093cc6ad0ca71b090374
    word_to_frame_id=w2f_285a114d06e92fe5c431ea1e51ebafd9
    envelope length=3155
    envelope SHA-256=1727ca57a98fb839e0cc94ada5ef828002fdd0387e5c91fa72be76b08b547a1b

The full literal envelope is exactly the projection above with these two
sorted-key members inserted by canonical encoding:

    "word_to_frame_hash":"285a114d06e92fe5c431ea1e51ebafd9be72476034a7093cc6ad0ca71b090374"
    "word_to_frame_id":"w2f_285a114d06e92fe5c431ea1e51ebafd9"

The focused test must store the complete 3155-byte envelope as one independent
literal bytes constant; deriving it from the projection or production helpers
is forbidden. An additional 30000/1001 fixture must verify non-integer
boundaries, ceil end, half-open positive spans, and the strict integer drift
proof.

## 19. Frozen AlignmentReport golden fixtures

The exact golden policy literal is:

    {"caption_group_blocker_below_millionths":900000,"caption_group_warning_below_millionths":950000,"individual_blocker_below_millionths":900000,"individual_warning_below_millionths":950000,"low_confidence_ratio_blocker_at_or_above_millionths":750000,"low_confidence_ratio_warning_at_or_above_millionths":250000,"policy_version":"ALIGNMENT-REPORT-POLICY-V1"}

    policy bytes length=355
    alignment_report_policy_snapshot_hash=sha256:3d6b49dbfe0490e5bacbfb101dcc107be4dcf0905c1595ef9f7bd66a1ad09957

FX-ALREP-AVAILABLE-01 has four warnings in exact order: word ordinals 2 and 3,
caption-group ordinal 1, and aggregate ratio. Its exact identities are:

    projection length=5610
    report hash=2921b750d2ab27860c634e4aaa4a87613744b8bce536a87770183176e59ba4b3
    report ID=alrep_2921b750d2ab27860c634e4aaa4a8761
    envelope length=5764
    envelope SHA-256=606e62eaa9ffcef384525e8d437f63eb00049e98cc2c58e38adf78d61467b10b
    status=REVIEW_REQUIRED
    warning_finding_count=4
    blocker_finding_count=0

Its finding projection hashes/IDs in order are:

    3fe0abeaeb8d265dcf503bfd3237eaa515d2e2c4b78ad690418e561c8020b81c / alrf_3fe0abeaeb8d265dcf503bfd3237eaa5
    e49d551993edaa3fed3167f580fc38f1e9d52602fd0922060ed368bf7c387765 / alrf_e49d551993edaa3fed3167f580fc38f1
    db4e372581fddbc241fddac4108dd342be4926589bcf0e9164638aeccdeff460 / alrf_db4e372581fddbc241fddac4108dd342
    90219b749491c44b3ebe9e146ed2db3fe87329b83a747442316f12822bf5ad73 / alrf_90219b749491c44b3ebe9e146ed2db3f

FX-ALREP-UNAVAILABLE-01 uses a genuine null-token temporal raw package, a
SUPPORTED REPLAY request, a successful execution carrying UNAVAILABLE
confidence evidence, and newly bound repository timing-origin evidence. The
existing AlignmentResult and CaptionGroups materializers must accept and their
public serializers must serialize the resulting current dependencies. It
freezes:

    run_id=run_alignment_report_UNAVAILABLE
    raw_id=raw_alignment_report_UNAVAILABLE
    timing_origin_evidence fixture_id=FX-ALREP-UNAVAILABLE-TIMING
    timing payload length=1054
    timing payload SHA-256=0e790d84b99d40bd53704673955977f4929c4622dbbd9ea7cb7192b02df81f30
    temporal_raw_package_hash=sha256:6652c8f26f43feaa0286db948724edde455877aadff5a762a791cc2cbee8ab76
    source_alignment_request_id=arq_0273b6a66a126ca2e62d298eec4e555b
    source_alignment_request_hash=0273b6a66a126ca2e62d298eec4e555b1a0e4bc8328066f6b1ec4a5d70a1cdd2
    source_adapter_execution_id=aex_bd897507f95c0fce81bd5530f98a667e
    source_adapter_execution_hash=bd897507f95c0fce81bd5530f98a667ee5cd3c4fab13048e0ec94fb11a0ffd50
    alignment_request_id=arq_221f2b935363a3d8d2558758f51e244e
    alignment_request_hash=221f2b935363a3d8d2558758f51e244e1dc0a01432b72271ba31e2346d70f8ce
    adapter_execution_id=aex_752dfa887cc4a7113694edf6ea0ee9d0
    adapter_execution_hash=752dfa887cc4a7113694edf6ea0ee9d0bad5309d568f8ac64a3b641b4bacf748
    timing_origin_evidence_id=toe_9bbb6108462700a035fbf60c8d7233b7
    timing_origin_evidence_hash=9bbb6108462700a035fbf60c8d7233b720302a46e6b8a8a0389b3dcde71c60de
    alignment_result_id=alr_37fe217ac2c4f77467235bb12536e26a
    alignment_result_hash=37fe217ac2c4f77467235bb12536e26aa783ef4b5d1dea086b8661484b971c5e
    alignment_result envelope length=1758
    alignment_result envelope SHA-256=8d0b46de413920d135533b28356d17f36104acc59134f2c06b515977e6ae422c
    caption_groups_id=cgs_c15e3afcaa73e13ca40d447edfa37f49
    caption_groups_hash=c15e3afcaa73e13ca40d447edfa37f49f58fc997d5999ba8db7f6a87953d0945
    caption_groups envelope length=2298
    caption_groups envelope SHA-256=aa6d5172af5da4333e127a90bff6274603456d596461615b22c607bb85b7c296
    projection length=3105
    report hash=1b52419d9c9e41dbfc7a6f4517d5909e0dd1ad330729b9c83f06a6a2f384acaf
    report ID=alrep_1b52419d9c9e41dbfc7a6f4517d5909e
    envelope length=3259
    envelope SHA-256=64b9facf58d6790596c85c299714ac4f8b7b52c308d1ad532548ec8c369d1c33
    finding hash=a663b34ca488743c2c562f9199f48de3e0363767f2c8d3ac306491d3c521c887
    finding ID=alrf_a663b34ca488743c2c562f9199f48de3
    status=CONFIDENCE_UNAVAILABLE

FX-ALREP-NOT-APPLICABLE-01 uses a genuine null-token temporal raw package, an
UNSUPPORTED REPLAY request, a successful execution carrying NOT_APPLICABLE
confidence evidence, and newly bound repository timing-origin evidence. The
existing AlignmentResult and CaptionGroups materializers and serializers must
accept the chain. It freezes:

    run_id=run_alignment_report_NOT-APPLICABLE
    raw_id=raw_alignment_report_NOT-APPLICABLE
    timing_origin_evidence fixture_id=FX-ALREP-NOT-APPLICABLE-TIMING
    timing payload length=1054
    timing payload SHA-256=0e790d84b99d40bd53704673955977f4929c4622dbbd9ea7cb7192b02df81f30
    temporal_raw_package_hash=sha256:6b2859827c7bede701b4a4d0f90fb45a4727345d8b4ce1fb60247ec6d9f3ea54
    source_alignment_request_id=arq_30588ed71ef21a65b43dc0fd03d0d5d7
    source_alignment_request_hash=30588ed71ef21a65b43dc0fd03d0d5d7ed56b496f8e3239184bc75aad92e7de7
    source_adapter_execution_id=aex_ff4ddc355ebcb3aae967c115e7ba1f7a
    source_adapter_execution_hash=ff4ddc355ebcb3aae967c115e7ba1f7ac00cbf778976b7ed533dc87931199f46
    alignment_request_id=arq_e83198f3b09b4a2d165dacf873ba796c
    alignment_request_hash=e83198f3b09b4a2d165dacf873ba796cd21f691403e71934f98db6dc19e7dee1
    adapter_execution_id=aex_5dd490c52cbc151cfd809e503709772f
    adapter_execution_hash=5dd490c52cbc151cfd809e503709772f08e9d3c613ca6c86ca23a4606e020ba5
    timing_origin_evidence_id=toe_ce6210ed324917ab2d9c8c2514b6b77f
    timing_origin_evidence_hash=ce6210ed324917ab2d9c8c2514b6b77f327a54feab01a765ce063e13092c642b
    alignment_result_id=alr_00c3cd8b81ae25698e01cbd297169182
    alignment_result_hash=00c3cd8b81ae25698e01cbd29716918223e327840cf9af5d3036dbc05b38b16c
    alignment_result envelope length=1761
    alignment_result envelope SHA-256=195589f621d053fd5c88568fa575a678d250780265662b763cf28c8d5a2c3230
    caption_groups_id=cgs_0aabeea64c7fc2733d9e678f6b3704ab
    caption_groups_hash=0aabeea64c7fc2733d9e678f6b3704ab20d95a7cb6a697afff4f15e2b3684322
    caption_groups envelope length=2301
    caption_groups envelope SHA-256=e75771fb46848309ea6b71f45eacc580cf2d50ca250afa582cd98b2819a10f61
    projection length=2313
    report hash=0d777cf83342fc7e399fe98eaa5007329c7960a133c58bf9eb0674e4a55ae470
    report ID=alrep_0d777cf83342fc7e399fe98eaa500732
    envelope length=2467
    envelope SHA-256=b894b07465ba77d1111db6fe84b3e254766480deefb85b7a242a1f05462e27de
    findings=[]
    status=CONFIDENCE_NOT_APPLICABLE

The focused report test must contain complete literal projection and envelope
bytes for all three states. The exact object members are those in sections
12-15; AVAILABLE metrics are word/group counts 4/2, evaluated 4/2, minima
920000/920000, low counts 2/1, ratio 500000, warnings/blockers 4/0.
UNAVAILABLE metrics are evaluated 0/0, minima/ratio null, low counts 0/0,
warnings/blockers 1/0, with exactly the singleton. NOT_APPLICABLE differs by
availability/status and has warnings/blockers 0/0 and no findings. Expected
literal bytes must be authored independently with compact sorted keys and may
not call future production projection, hash, finding, or serializer helpers.

### 19.1 Complete literal bytes required by the golden oracle

The following lines are the complete literal compact sorted-key UTF-8 bytes.
They are normative in addition to the lengths, hashes, IDs, findings, and
metrics above.

FX-W2F-01 complete envelope bytes:

    {"alignment_result_hash":"1521f195a591df09edaa968d8f5fa91ed367be1c7190a3f614823d74b3cd36bb","alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","caption_frames":[{"end_exclusive_frame":27,"end_exclusive_word_ordinal":2,"end_ms":900,"end_word_id":"nword_0cc9d55672a3cb4e9199","ordinal":0,"source_id":"cgrp_2bdd1bc0e985d5d45784956cb0818fb9","source_kind":"CAPTION_GROUP","start_frame":3,"start_ms":100,"start_word_id":"nword_5321ba14c2c4b28c31ab","start_word_ordinal":0},{"end_exclusive_frame":69,"end_exclusive_word_ordinal":4,"end_ms":2300,"end_word_id":"nword_d81fe913754f8b49c296","ordinal":1,"source_id":"cgrp_5b9b84abe4eba87d448e56b87ff277d6","source_kind":"CAPTION_GROUP","start_frame":36,"start_ms":1200,"start_word_id":"nword_49e85bb034c88ef36f26","start_word_ordinal":2}],"caption_groups_hash":"12670fe861389bfe8e25f05a126c7ea355c361c2b2848e9b02a216ed83baaec7","caption_groups_id":"cgs_12670fe861389bfe8e25f05a126c7ea3","confidence_availability":"AVAILABLE","document_id":"nardoc_fx34","emphasis_events_hash":"e6286517914a305715e42460d27092370bf304f6715e28a6c483407758a04b7d","emphasis_events_id":"emps_e6286517914a305715e42460d2709237","emphasis_frames":[{"end_exclusive_frame":27,"end_exclusive_word_ordinal":2,"end_ms":900,"end_word_id":"nword_0cc9d55672a3cb4e9199","ordinal":0,"source_id":"emph_3b919932a4e05683fe94c9eae048341b","source_kind":"EMPHASIS_EVENT","start_frame":3,"start_ms":100,"start_word_id":"nword_5321ba14c2c4b28c31ab","start_word_ordinal":0}],"frame_rate":{"denominator":1,"numerator":30},"hash_scope_version":"WORD-TO-FRAME-HASH-V1","mapping_policy_version":"WORD-TO-FRAME-POLICY-V1","narration_revision_hash":"sha256:d60d7ae087efb0e309d4e3f28fedea074d15e11405046249a23b2c7bb42fe0c0","narration_revision_id":"narrev_d60d7ae087efb0e309d4","project_id":"prj_fx34","schema_version":"WORD-TO-FRAME-V1","word_frames":[{"end_exclusive_frame":15,"end_exclusive_word_ordinal":1,"end_ms":500,"end_word_id":"nword_5321ba14c2c4b28c31ab","ordinal":0,"source_id":"nword_5321ba14c2c4b28c31ab","source_kind":"WORD","start_frame":3,"start_ms":100,"start_word_id":"nword_5321ba14c2c4b28c31ab","start_word_ordinal":0},{"end_exclusive_frame":27,"end_exclusive_word_ordinal":2,"end_ms":900,"end_word_id":"nword_0cc9d55672a3cb4e9199","ordinal":1,"source_id":"nword_0cc9d55672a3cb4e9199","source_kind":"WORD","start_frame":15,"start_ms":520,"start_word_id":"nword_0cc9d55672a3cb4e9199","start_word_ordinal":1},{"end_exclusive_frame":51,"end_exclusive_word_ordinal":3,"end_ms":1700,"end_word_id":"nword_49e85bb034c88ef36f26","ordinal":2,"source_id":"nword_49e85bb034c88ef36f26","source_kind":"WORD","start_frame":36,"start_ms":1200,"start_word_id":"nword_49e85bb034c88ef36f26","start_word_ordinal":2},{"end_exclusive_frame":69,"end_exclusive_word_ordinal":4,"end_ms":2300,"end_word_id":"nword_d81fe913754f8b49c296","ordinal":3,"source_id":"nword_d81fe913754f8b49c296","source_kind":"WORD","start_frame":51,"start_ms":1720,"start_word_id":"nword_d81fe913754f8b49c296","start_word_ordinal":3}],"word_to_frame_hash":"285a114d06e92fe5c431ea1e51ebafd9be72476034a7093cc6ad0ca71b090374","word_to_frame_id":"w2f_285a114d06e92fe5c431ea1e51ebafd9"}

FX-ALREP-AVAILABLE-01 complete projection bytes:

    {"adapter_execution_hash":"0d5a9c0a156e9e3ca7fbffc460b74c261fa0f5f645580e10684d145e526b123b","adapter_execution_id":"aex_0d5a9c0a156e9e3ca7fbffc460b74c26","alignment_report_policy":{"caption_group_blocker_below_millionths":900000,"caption_group_warning_below_millionths":950000,"individual_blocker_below_millionths":900000,"individual_warning_below_millionths":950000,"low_confidence_ratio_blocker_at_or_above_millionths":750000,"low_confidence_ratio_warning_at_or_above_millionths":250000,"policy_version":"ALIGNMENT-REPORT-POLICY-V1"},"alignment_report_policy_snapshot_hash":"sha256:3d6b49dbfe0490e5bacbfb101dcc107be4dcf0905c1595ef9f7bd66a1ad09957","alignment_request_hash":"08487b276310e36fe3163499ffb773a0f06b2d969640d798a1ac360523f01234","alignment_request_id":"arq_08487b276310e36fe3163499ffb773a0","alignment_result_hash":"1521f195a591df09edaa968d8f5fa91ed367be1c7190a3f614823d74b3cd36bb","alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","audio_artifact_hash":"sha256:63d5743b733e34f120180d3a787d78cb0a26119395bbee1aa2e45c257713d968","audio_artifact_id":"aud_63d5743b733e34f12018","blocker_finding_count":0,"caption_group_count":2,"caption_groups_hash":"12670fe861389bfe8e25f05a126c7ea355c361c2b2848e9b02a216ed83baaec7","caption_groups_id":"cgs_12670fe861389bfe8e25f05a126c7ea3","confidence_availability":"AVAILABLE","document_id":"nardoc_fx34","evaluated_caption_group_confidence_count":2,"evaluated_word_confidence_count":4,"findings":[{"alignment_report_finding_hash":"3fe0abeaeb8d265dcf503bfd3237eaa515d2e2c4b78ad690418e561c8020b81c","alignment_report_finding_id":"alrf_3fe0abeaeb8d265dcf503bfd3237eaa5","alignment_report_policy_snapshot_hash":"sha256:3d6b49dbfe0490e5bacbfb101dcc107be4dcf0905c1595ef9f7bd66a1ad09957","alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","caption_group_id":null,"caption_group_ordinal":null,"caption_groups_id":"cgs_12670fe861389bfe8e25f05a126c7ea3","end_exclusive_word_ordinal":null,"hash_scope_version":"ALIGNMENT-REPORT-FINDING-HASH-V1","issue_code":"INDIVIDUAL_CONFIDENCE_WARNING","observed_millionths":940000,"ordinal":0,"schema_version":"ALIGNMENT-REPORT-FINDING-V1","scope":"WORD","severity":"WARNING","start_word_ordinal":null,"threshold_millionths":950000,"word_id":"nword_49e85bb034c88ef36f26","word_ordinal":2},{"alignment_report_finding_hash":"e49d551993edaa3fed3167f580fc38f1e9d52602fd0922060ed368bf7c387765","alignment_report_finding_id":"alrf_e49d551993edaa3fed3167f580fc38f1","alignment_report_policy_snapshot_hash":"sha256:3d6b49dbfe0490e5bacbfb101dcc107be4dcf0905c1595ef9f7bd66a1ad09957","alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","caption_group_id":null,"caption_group_ordinal":null,"caption_groups_id":"cgs_12670fe861389bfe8e25f05a126c7ea3","end_exclusive_word_ordinal":null,"hash_scope_version":"ALIGNMENT-REPORT-FINDING-HASH-V1","issue_code":"INDIVIDUAL_CONFIDENCE_WARNING","observed_millionths":920000,"ordinal":1,"schema_version":"ALIGNMENT-REPORT-FINDING-V1","scope":"WORD","severity":"WARNING","start_word_ordinal":null,"threshold_millionths":950000,"word_id":"nword_d81fe913754f8b49c296","word_ordinal":3},{"alignment_report_finding_hash":"db4e372581fddbc241fddac4108dd342be4926589bcf0e9164638aeccdeff460","alignment_report_finding_id":"alrf_db4e372581fddbc241fddac4108dd342","alignment_report_policy_snapshot_hash":"sha256:3d6b49dbfe0490e5bacbfb101dcc107be4dcf0905c1595ef9f7bd66a1ad09957","alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","caption_group_id":"cgrp_5b9b84abe4eba87d448e56b87ff277d6","caption_group_ordinal":1,"caption_groups_id":"cgs_12670fe861389bfe8e25f05a126c7ea3","end_exclusive_word_ordinal":4,"hash_scope_version":"ALIGNMENT-REPORT-FINDING-HASH-V1","issue_code":"SEGMENT_CONFIDENCE_WARNING","observed_millionths":920000,"ordinal":2,"schema_version":"ALIGNMENT-REPORT-FINDING-V1","scope":"CAPTION_GROUP","severity":"WARNING","start_word_ordinal":2,"threshold_millionths":950000,"word_id":null,"word_ordinal":null},{"alignment_report_finding_hash":"90219b749491c44b3ebe9e146ed2db3fe87329b83a747442316f12822bf5ad73","alignment_report_finding_id":"alrf_90219b749491c44b3ebe9e146ed2db3f","alignment_report_policy_snapshot_hash":"sha256:3d6b49dbfe0490e5bacbfb101dcc107be4dcf0905c1595ef9f7bd66a1ad09957","alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","caption_group_id":null,"caption_group_ordinal":null,"caption_groups_id":"cgs_12670fe861389bfe8e25f05a126c7ea3","end_exclusive_word_ordinal":null,"hash_scope_version":"ALIGNMENT-REPORT-FINDING-HASH-V1","issue_code":"LOW_CONFIDENCE_RATIO_WARNING","observed_millionths":500000,"ordinal":3,"schema_version":"ALIGNMENT-REPORT-FINDING-V1","scope":"REPORT","severity":"WARNING","start_word_ordinal":null,"threshold_millionths":250000,"word_id":null,"word_ordinal":null}],"hash_scope_version":"ALIGNMENT-REPORT-HASH-V1","low_confidence_caption_group_count":1,"low_confidence_word_count":2,"low_confidence_word_ratio_millionths":500000,"minimum_caption_group_confidence_millionths":920000,"minimum_word_confidence_millionths":920000,"narration_revision_hash":"sha256:d60d7ae087efb0e309d4e3f28fedea074d15e11405046249a23b2c7bb42fe0c0","narration_revision_id":"narrev_d60d7ae087efb0e309d4","project_id":"prj_fx34","schema_version":"ALIGNMENT-REPORT-V1","status":"REVIEW_REQUIRED","temporal_raw_package_hash":"sha256:21891739f58b8dfc512de572105c13dc666d42ebeb2e98e02f2d5abd32826a18","timing_origin_evidence_hash":"f140843e7e1f86817c7acc0bdc8eb775021ffd8c5a5a13809d5e33407c34ae03","timing_origin_evidence_id":"toe_f140843e7e1f86817c7acc0bdc8eb775","timing_source":"REPLAY_VERIFIED","warning_finding_count":4,"word_count":4}

FX-ALREP-AVAILABLE-01 complete envelope bytes:

    {"adapter_execution_hash":"0d5a9c0a156e9e3ca7fbffc460b74c261fa0f5f645580e10684d145e526b123b","adapter_execution_id":"aex_0d5a9c0a156e9e3ca7fbffc460b74c26","alignment_report_hash":"2921b750d2ab27860c634e4aaa4a87613744b8bce536a87770183176e59ba4b3","alignment_report_id":"alrep_2921b750d2ab27860c634e4aaa4a8761","alignment_report_policy":{"caption_group_blocker_below_millionths":900000,"caption_group_warning_below_millionths":950000,"individual_blocker_below_millionths":900000,"individual_warning_below_millionths":950000,"low_confidence_ratio_blocker_at_or_above_millionths":750000,"low_confidence_ratio_warning_at_or_above_millionths":250000,"policy_version":"ALIGNMENT-REPORT-POLICY-V1"},"alignment_report_policy_snapshot_hash":"sha256:3d6b49dbfe0490e5bacbfb101dcc107be4dcf0905c1595ef9f7bd66a1ad09957","alignment_request_hash":"08487b276310e36fe3163499ffb773a0f06b2d969640d798a1ac360523f01234","alignment_request_id":"arq_08487b276310e36fe3163499ffb773a0","alignment_result_hash":"1521f195a591df09edaa968d8f5fa91ed367be1c7190a3f614823d74b3cd36bb","alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","audio_artifact_hash":"sha256:63d5743b733e34f120180d3a787d78cb0a26119395bbee1aa2e45c257713d968","audio_artifact_id":"aud_63d5743b733e34f12018","blocker_finding_count":0,"caption_group_count":2,"caption_groups_hash":"12670fe861389bfe8e25f05a126c7ea355c361c2b2848e9b02a216ed83baaec7","caption_groups_id":"cgs_12670fe861389bfe8e25f05a126c7ea3","confidence_availability":"AVAILABLE","document_id":"nardoc_fx34","evaluated_caption_group_confidence_count":2,"evaluated_word_confidence_count":4,"findings":[{"alignment_report_finding_hash":"3fe0abeaeb8d265dcf503bfd3237eaa515d2e2c4b78ad690418e561c8020b81c","alignment_report_finding_id":"alrf_3fe0abeaeb8d265dcf503bfd3237eaa5","alignment_report_policy_snapshot_hash":"sha256:3d6b49dbfe0490e5bacbfb101dcc107be4dcf0905c1595ef9f7bd66a1ad09957","alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","caption_group_id":null,"caption_group_ordinal":null,"caption_groups_id":"cgs_12670fe861389bfe8e25f05a126c7ea3","end_exclusive_word_ordinal":null,"hash_scope_version":"ALIGNMENT-REPORT-FINDING-HASH-V1","issue_code":"INDIVIDUAL_CONFIDENCE_WARNING","observed_millionths":940000,"ordinal":0,"schema_version":"ALIGNMENT-REPORT-FINDING-V1","scope":"WORD","severity":"WARNING","start_word_ordinal":null,"threshold_millionths":950000,"word_id":"nword_49e85bb034c88ef36f26","word_ordinal":2},{"alignment_report_finding_hash":"e49d551993edaa3fed3167f580fc38f1e9d52602fd0922060ed368bf7c387765","alignment_report_finding_id":"alrf_e49d551993edaa3fed3167f580fc38f1","alignment_report_policy_snapshot_hash":"sha256:3d6b49dbfe0490e5bacbfb101dcc107be4dcf0905c1595ef9f7bd66a1ad09957","alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","caption_group_id":null,"caption_group_ordinal":null,"caption_groups_id":"cgs_12670fe861389bfe8e25f05a126c7ea3","end_exclusive_word_ordinal":null,"hash_scope_version":"ALIGNMENT-REPORT-FINDING-HASH-V1","issue_code":"INDIVIDUAL_CONFIDENCE_WARNING","observed_millionths":920000,"ordinal":1,"schema_version":"ALIGNMENT-REPORT-FINDING-V1","scope":"WORD","severity":"WARNING","start_word_ordinal":null,"threshold_millionths":950000,"word_id":"nword_d81fe913754f8b49c296","word_ordinal":3},{"alignment_report_finding_hash":"db4e372581fddbc241fddac4108dd342be4926589bcf0e9164638aeccdeff460","alignment_report_finding_id":"alrf_db4e372581fddbc241fddac4108dd342","alignment_report_policy_snapshot_hash":"sha256:3d6b49dbfe0490e5bacbfb101dcc107be4dcf0905c1595ef9f7bd66a1ad09957","alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","caption_group_id":"cgrp_5b9b84abe4eba87d448e56b87ff277d6","caption_group_ordinal":1,"caption_groups_id":"cgs_12670fe861389bfe8e25f05a126c7ea3","end_exclusive_word_ordinal":4,"hash_scope_version":"ALIGNMENT-REPORT-FINDING-HASH-V1","issue_code":"SEGMENT_CONFIDENCE_WARNING","observed_millionths":920000,"ordinal":2,"schema_version":"ALIGNMENT-REPORT-FINDING-V1","scope":"CAPTION_GROUP","severity":"WARNING","start_word_ordinal":2,"threshold_millionths":950000,"word_id":null,"word_ordinal":null},{"alignment_report_finding_hash":"90219b749491c44b3ebe9e146ed2db3fe87329b83a747442316f12822bf5ad73","alignment_report_finding_id":"alrf_90219b749491c44b3ebe9e146ed2db3f","alignment_report_policy_snapshot_hash":"sha256:3d6b49dbfe0490e5bacbfb101dcc107be4dcf0905c1595ef9f7bd66a1ad09957","alignment_result_id":"alr_1521f195a591df09edaa968d8f5fa91e","caption_group_id":null,"caption_group_ordinal":null,"caption_groups_id":"cgs_12670fe861389bfe8e25f05a126c7ea3","end_exclusive_word_ordinal":null,"hash_scope_version":"ALIGNMENT-REPORT-FINDING-HASH-V1","issue_code":"LOW_CONFIDENCE_RATIO_WARNING","observed_millionths":500000,"ordinal":3,"schema_version":"ALIGNMENT-REPORT-FINDING-V1","scope":"REPORT","severity":"WARNING","start_word_ordinal":null,"threshold_millionths":250000,"word_id":null,"word_ordinal":null}],"hash_scope_version":"ALIGNMENT-REPORT-HASH-V1","low_confidence_caption_group_count":1,"low_confidence_word_count":2,"low_confidence_word_ratio_millionths":500000,"minimum_caption_group_confidence_millionths":920000,"minimum_word_confidence_millionths":920000,"narration_revision_hash":"sha256:d60d7ae087efb0e309d4e3f28fedea074d15e11405046249a23b2c7bb42fe0c0","narration_revision_id":"narrev_d60d7ae087efb0e309d4","project_id":"prj_fx34","schema_version":"ALIGNMENT-REPORT-V1","status":"REVIEW_REQUIRED","temporal_raw_package_hash":"sha256:21891739f58b8dfc512de572105c13dc666d42ebeb2e98e02f2d5abd32826a18","timing_origin_evidence_hash":"f140843e7e1f86817c7acc0bdc8eb775021ffd8c5a5a13809d5e33407c34ae03","timing_origin_evidence_id":"toe_f140843e7e1f86817c7acc0bdc8eb775","timing_source":"REPLAY_VERIFIED","warning_finding_count":4,"word_count":4}

FX-ALREP-UNAVAILABLE-01 complete projection bytes:

    {"adapter_execution_hash":"752dfa887cc4a7113694edf6ea0ee9d0bad5309d568f8ac64a3b641b4bacf748","adapter_execution_id":"aex_752dfa887cc4a7113694edf6ea0ee9d0","alignment_report_policy":{"caption_group_blocker_below_millionths":900000,"caption_group_warning_below_millionths":950000,"individual_blocker_below_millionths":900000,"individual_warning_below_millionths":950000,"low_confidence_ratio_blocker_at_or_above_millionths":750000,"low_confidence_ratio_warning_at_or_above_millionths":250000,"policy_version":"ALIGNMENT-REPORT-POLICY-V1"},"alignment_report_policy_snapshot_hash":"sha256:3d6b49dbfe0490e5bacbfb101dcc107be4dcf0905c1595ef9f7bd66a1ad09957","alignment_request_hash":"221f2b935363a3d8d2558758f51e244e1dc0a01432b72271ba31e2346d70f8ce","alignment_request_id":"arq_221f2b935363a3d8d2558758f51e244e","alignment_result_hash":"37fe217ac2c4f77467235bb12536e26aa783ef4b5d1dea086b8661484b971c5e","alignment_result_id":"alr_37fe217ac2c4f77467235bb12536e26a","audio_artifact_hash":"sha256:63d5743b733e34f120180d3a787d78cb0a26119395bbee1aa2e45c257713d968","audio_artifact_id":"aud_63d5743b733e34f12018","blocker_finding_count":0,"caption_group_count":2,"caption_groups_hash":"c15e3afcaa73e13ca40d447edfa37f49f58fc997d5999ba8db7f6a87953d0945","caption_groups_id":"cgs_c15e3afcaa73e13ca40d447edfa37f49","confidence_availability":"UNAVAILABLE","document_id":"nardoc_fx34","evaluated_caption_group_confidence_count":0,"evaluated_word_confidence_count":0,"findings":[{"alignment_report_finding_hash":"a663b34ca488743c2c562f9199f48de3e0363767f2c8d3ac306491d3c521c887","alignment_report_finding_id":"alrf_a663b34ca488743c2c562f9199f48de3","alignment_report_policy_snapshot_hash":"sha256:3d6b49dbfe0490e5bacbfb101dcc107be4dcf0905c1595ef9f7bd66a1ad09957","alignment_result_id":"alr_37fe217ac2c4f77467235bb12536e26a","caption_group_id":null,"caption_group_ordinal":null,"caption_groups_id":"cgs_c15e3afcaa73e13ca40d447edfa37f49","end_exclusive_word_ordinal":null,"hash_scope_version":"ALIGNMENT-REPORT-FINDING-HASH-V1","issue_code":"CONFIDENCE_UNAVAILABLE","observed_millionths":null,"ordinal":0,"schema_version":"ALIGNMENT-REPORT-FINDING-V1","scope":"REPORT","severity":"WARNING","start_word_ordinal":null,"threshold_millionths":null,"word_id":null,"word_ordinal":null}],"hash_scope_version":"ALIGNMENT-REPORT-HASH-V1","low_confidence_caption_group_count":0,"low_confidence_word_count":0,"low_confidence_word_ratio_millionths":null,"minimum_caption_group_confidence_millionths":null,"minimum_word_confidence_millionths":null,"narration_revision_hash":"sha256:d60d7ae087efb0e309d4e3f28fedea074d15e11405046249a23b2c7bb42fe0c0","narration_revision_id":"narrev_d60d7ae087efb0e309d4","project_id":"prj_fx34","schema_version":"ALIGNMENT-REPORT-V1","status":"CONFIDENCE_UNAVAILABLE","temporal_raw_package_hash":"sha256:6652c8f26f43feaa0286db948724edde455877aadff5a762a791cc2cbee8ab76","timing_origin_evidence_hash":"9bbb6108462700a035fbf60c8d7233b720302a46e6b8a8a0389b3dcde71c60de","timing_origin_evidence_id":"toe_9bbb6108462700a035fbf60c8d7233b7","timing_source":"REPLAY_VERIFIED","warning_finding_count":1,"word_count":4}

FX-ALREP-UNAVAILABLE-01 complete envelope bytes:

    {"adapter_execution_hash":"752dfa887cc4a7113694edf6ea0ee9d0bad5309d568f8ac64a3b641b4bacf748","adapter_execution_id":"aex_752dfa887cc4a7113694edf6ea0ee9d0","alignment_report_hash":"1b52419d9c9e41dbfc7a6f4517d5909e0dd1ad330729b9c83f06a6a2f384acaf","alignment_report_id":"alrep_1b52419d9c9e41dbfc7a6f4517d5909e","alignment_report_policy":{"caption_group_blocker_below_millionths":900000,"caption_group_warning_below_millionths":950000,"individual_blocker_below_millionths":900000,"individual_warning_below_millionths":950000,"low_confidence_ratio_blocker_at_or_above_millionths":750000,"low_confidence_ratio_warning_at_or_above_millionths":250000,"policy_version":"ALIGNMENT-REPORT-POLICY-V1"},"alignment_report_policy_snapshot_hash":"sha256:3d6b49dbfe0490e5bacbfb101dcc107be4dcf0905c1595ef9f7bd66a1ad09957","alignment_request_hash":"221f2b935363a3d8d2558758f51e244e1dc0a01432b72271ba31e2346d70f8ce","alignment_request_id":"arq_221f2b935363a3d8d2558758f51e244e","alignment_result_hash":"37fe217ac2c4f77467235bb12536e26aa783ef4b5d1dea086b8661484b971c5e","alignment_result_id":"alr_37fe217ac2c4f77467235bb12536e26a","audio_artifact_hash":"sha256:63d5743b733e34f120180d3a787d78cb0a26119395bbee1aa2e45c257713d968","audio_artifact_id":"aud_63d5743b733e34f12018","blocker_finding_count":0,"caption_group_count":2,"caption_groups_hash":"c15e3afcaa73e13ca40d447edfa37f49f58fc997d5999ba8db7f6a87953d0945","caption_groups_id":"cgs_c15e3afcaa73e13ca40d447edfa37f49","confidence_availability":"UNAVAILABLE","document_id":"nardoc_fx34","evaluated_caption_group_confidence_count":0,"evaluated_word_confidence_count":0,"findings":[{"alignment_report_finding_hash":"a663b34ca488743c2c562f9199f48de3e0363767f2c8d3ac306491d3c521c887","alignment_report_finding_id":"alrf_a663b34ca488743c2c562f9199f48de3","alignment_report_policy_snapshot_hash":"sha256:3d6b49dbfe0490e5bacbfb101dcc107be4dcf0905c1595ef9f7bd66a1ad09957","alignment_result_id":"alr_37fe217ac2c4f77467235bb12536e26a","caption_group_id":null,"caption_group_ordinal":null,"caption_groups_id":"cgs_c15e3afcaa73e13ca40d447edfa37f49","end_exclusive_word_ordinal":null,"hash_scope_version":"ALIGNMENT-REPORT-FINDING-HASH-V1","issue_code":"CONFIDENCE_UNAVAILABLE","observed_millionths":null,"ordinal":0,"schema_version":"ALIGNMENT-REPORT-FINDING-V1","scope":"REPORT","severity":"WARNING","start_word_ordinal":null,"threshold_millionths":null,"word_id":null,"word_ordinal":null}],"hash_scope_version":"ALIGNMENT-REPORT-HASH-V1","low_confidence_caption_group_count":0,"low_confidence_word_count":0,"low_confidence_word_ratio_millionths":null,"minimum_caption_group_confidence_millionths":null,"minimum_word_confidence_millionths":null,"narration_revision_hash":"sha256:d60d7ae087efb0e309d4e3f28fedea074d15e11405046249a23b2c7bb42fe0c0","narration_revision_id":"narrev_d60d7ae087efb0e309d4","project_id":"prj_fx34","schema_version":"ALIGNMENT-REPORT-V1","status":"CONFIDENCE_UNAVAILABLE","temporal_raw_package_hash":"sha256:6652c8f26f43feaa0286db948724edde455877aadff5a762a791cc2cbee8ab76","timing_origin_evidence_hash":"9bbb6108462700a035fbf60c8d7233b720302a46e6b8a8a0389b3dcde71c60de","timing_origin_evidence_id":"toe_9bbb6108462700a035fbf60c8d7233b7","timing_source":"REPLAY_VERIFIED","warning_finding_count":1,"word_count":4}

FX-ALREP-NOT-APPLICABLE-01 complete projection bytes:

    {"adapter_execution_hash":"5dd490c52cbc151cfd809e503709772f08e9d3c613ca6c86ca23a4606e020ba5","adapter_execution_id":"aex_5dd490c52cbc151cfd809e503709772f","alignment_report_policy":{"caption_group_blocker_below_millionths":900000,"caption_group_warning_below_millionths":950000,"individual_blocker_below_millionths":900000,"individual_warning_below_millionths":950000,"low_confidence_ratio_blocker_at_or_above_millionths":750000,"low_confidence_ratio_warning_at_or_above_millionths":250000,"policy_version":"ALIGNMENT-REPORT-POLICY-V1"},"alignment_report_policy_snapshot_hash":"sha256:3d6b49dbfe0490e5bacbfb101dcc107be4dcf0905c1595ef9f7bd66a1ad09957","alignment_request_hash":"e83198f3b09b4a2d165dacf873ba796cd21f691403e71934f98db6dc19e7dee1","alignment_request_id":"arq_e83198f3b09b4a2d165dacf873ba796c","alignment_result_hash":"00c3cd8b81ae25698e01cbd29716918223e327840cf9af5d3036dbc05b38b16c","alignment_result_id":"alr_00c3cd8b81ae25698e01cbd297169182","audio_artifact_hash":"sha256:63d5743b733e34f120180d3a787d78cb0a26119395bbee1aa2e45c257713d968","audio_artifact_id":"aud_63d5743b733e34f12018","blocker_finding_count":0,"caption_group_count":2,"caption_groups_hash":"0aabeea64c7fc2733d9e678f6b3704ab20d95a7cb6a697afff4f15e2b3684322","caption_groups_id":"cgs_0aabeea64c7fc2733d9e678f6b3704ab","confidence_availability":"NOT_APPLICABLE","document_id":"nardoc_fx34","evaluated_caption_group_confidence_count":0,"evaluated_word_confidence_count":0,"findings":[],"hash_scope_version":"ALIGNMENT-REPORT-HASH-V1","low_confidence_caption_group_count":0,"low_confidence_word_count":0,"low_confidence_word_ratio_millionths":null,"minimum_caption_group_confidence_millionths":null,"minimum_word_confidence_millionths":null,"narration_revision_hash":"sha256:d60d7ae087efb0e309d4e3f28fedea074d15e11405046249a23b2c7bb42fe0c0","narration_revision_id":"narrev_d60d7ae087efb0e309d4","project_id":"prj_fx34","schema_version":"ALIGNMENT-REPORT-V1","status":"CONFIDENCE_NOT_APPLICABLE","temporal_raw_package_hash":"sha256:6b2859827c7bede701b4a4d0f90fb45a4727345d8b4ce1fb60247ec6d9f3ea54","timing_origin_evidence_hash":"ce6210ed324917ab2d9c8c2514b6b77f327a54feab01a765ce063e13092c642b","timing_origin_evidence_id":"toe_ce6210ed324917ab2d9c8c2514b6b77f","timing_source":"REPLAY_VERIFIED","warning_finding_count":0,"word_count":4}

FX-ALREP-NOT-APPLICABLE-01 complete envelope bytes:

    {"adapter_execution_hash":"5dd490c52cbc151cfd809e503709772f08e9d3c613ca6c86ca23a4606e020ba5","adapter_execution_id":"aex_5dd490c52cbc151cfd809e503709772f","alignment_report_hash":"0d777cf83342fc7e399fe98eaa5007329c7960a133c58bf9eb0674e4a55ae470","alignment_report_id":"alrep_0d777cf83342fc7e399fe98eaa500732","alignment_report_policy":{"caption_group_blocker_below_millionths":900000,"caption_group_warning_below_millionths":950000,"individual_blocker_below_millionths":900000,"individual_warning_below_millionths":950000,"low_confidence_ratio_blocker_at_or_above_millionths":750000,"low_confidence_ratio_warning_at_or_above_millionths":250000,"policy_version":"ALIGNMENT-REPORT-POLICY-V1"},"alignment_report_policy_snapshot_hash":"sha256:3d6b49dbfe0490e5bacbfb101dcc107be4dcf0905c1595ef9f7bd66a1ad09957","alignment_request_hash":"e83198f3b09b4a2d165dacf873ba796cd21f691403e71934f98db6dc19e7dee1","alignment_request_id":"arq_e83198f3b09b4a2d165dacf873ba796c","alignment_result_hash":"00c3cd8b81ae25698e01cbd29716918223e327840cf9af5d3036dbc05b38b16c","alignment_result_id":"alr_00c3cd8b81ae25698e01cbd297169182","audio_artifact_hash":"sha256:63d5743b733e34f120180d3a787d78cb0a26119395bbee1aa2e45c257713d968","audio_artifact_id":"aud_63d5743b733e34f12018","blocker_finding_count":0,"caption_group_count":2,"caption_groups_hash":"0aabeea64c7fc2733d9e678f6b3704ab20d95a7cb6a697afff4f15e2b3684322","caption_groups_id":"cgs_0aabeea64c7fc2733d9e678f6b3704ab","confidence_availability":"NOT_APPLICABLE","document_id":"nardoc_fx34","evaluated_caption_group_confidence_count":0,"evaluated_word_confidence_count":0,"findings":[],"hash_scope_version":"ALIGNMENT-REPORT-HASH-V1","low_confidence_caption_group_count":0,"low_confidence_word_count":0,"low_confidence_word_ratio_millionths":null,"minimum_caption_group_confidence_millionths":null,"minimum_word_confidence_millionths":null,"narration_revision_hash":"sha256:d60d7ae087efb0e309d4e3f28fedea074d15e11405046249a23b2c7bb42fe0c0","narration_revision_id":"narrev_d60d7ae087efb0e309d4","project_id":"prj_fx34","schema_version":"ALIGNMENT-REPORT-V1","status":"CONFIDENCE_NOT_APPLICABLE","temporal_raw_package_hash":"sha256:6b2859827c7bede701b4a4d0f90fb45a4727345d8b4ce1fb60247ec6d9f3ea54","timing_origin_evidence_hash":"ce6210ed324917ab2d9c8c2514b6b77f327a54feab01a765ce063e13092c642b","timing_origin_evidence_id":"toe_ce6210ed324917ab2d9c8c2514b6b77f","timing_source":"REPLAY_VERIFIED","warning_finding_count":0,"word_count":4}


## 20. Mandatory focused and regression tests

Word tests must cover exact constants/enums/fields/signatures/exports; all
rate type, gcd, range, uint32, bool, JS-safe, 30 and NTSC cases; floor/ceil and
strict drift proof; word/caption/emphasis coverage and order; genuine/current
dependencies and all bindings; repeated words proving no string search;
literal golden projection/envelope/hash/ID; loader shape/canonicality/
precedence; mutation/copy/proxy/subclass/non-retention/weak-registry behavior;
and static absence of float, round, V2, FPS, per-frame expansion, I/O, and
forbidden imports.

Report tests must cover exact public surface; exact policy presence/types/
bounds/order/hash and no defaults; genuine/current dependencies and binding;
every AVAILABLE warning/blocker boundary including equality; blocker
suppression; exact cross-multiplication ratio gating independent of displayed
floor; finding order/null matrix/upstream-policy identity binding; PASS,
REVIEW_REQUIRED, BLOCKED, UNAVAILABLE, and NOT_APPLICABLE; no invented issue
code; all three full literal golden projection/envelope fixtures; loader
shape/canonicality/precedence; every error-oracle row; mutation and weak
registry safety; and static independence from word_to_frame/frame helpers.

Both suites must include duplicate keys, invalid UTF-8, BOM, noncanonical key
order, trailing newline, float/negative-zero rejection, unknown/missing keys,
hash-before-ID checks, sanitized multi-fault precedence, registry collision/
rollback/stale callback/cleanup, and two independent equivalent compilations.
Run focused tests, the exact upstream narration/alignment/caption/emphasis
regression group, then the broad top-level non-FastAPI regression. Paid APIs,
network, UI, and non-REPLAY execution remain off.

## 21. Complexity, resources, and agent ownership

Word compilation is O(W+C+E+output_bytes) time and memory. Report compilation
is O(W+C+F+output_bytes), where F is finding count. Both pre-index once. No
quadratic scan, string search, recursive narration scan, per-frame allocation,
unbounded cache, blocking I/O, thread, or subprocess is permitted.

Parallel ownership is closed:

- Word agent: word_to_frame.py and test_word_to_frame.py only.
- Report agent: alignment_report.py and test_alignment_report.py only.
- Integration owner: shared __init__.py, exact-export oracle, combined tests,
  git operations, and documentation only after both disjoint branches pass.
- Audit agent: read-only independent audit over the integrated macro-package.

Agents may not concurrently edit shared exports, shared test oracle, this
specification, status documents, or git state. Internal helpers receive no
separate specification, authorization, audit, acceptance, or remote-closure
cycle.

## 22. Acceptance and authorization gates

Before specification acceptance, an independent read-only adversarial audit
must validate every normative field, mapping proof, policy boundary, null
matrix, oracle, literal golden, length/hash/ID, complexity, and exclusion.
Every blocking finding must be repaired and independently re-audited. The
exact specification byte length/SHA and commit must then be recorded and
normally remote closed.

Only an explicit later acceptance/authorization record permits the single
parallel implementation integration described here. After implementation,
one independent integrated audit, one acceptance decision, and one
documentation/remote closure complete this macro-package. Caption preview,
collision validation, file publication, and later Phase 2 work remain outside.

    SPECIFICATION_STATUS=CANDIDATE
    SPECIFICATION_DRAFTED=YES
    SPECIFICATION_ACCEPTED=NO
    IMPLEMENTATION_AUTHORIZED=NO
    NEXT_ACTION=INDEPENDENT_READ_ONLY_SPECIFICATION_AUDIT
    PHASE2_CLOSED=NO
    TOTAL_PHASE2_SLICE_COUNT=UNKNOWN
    PHASE2_COMPLETION_PERCENTAGE=NOT_STATED
