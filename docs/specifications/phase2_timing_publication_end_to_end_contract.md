# Phase 2 Timing Publication + End-to-End Closure Contract

Status: candidate specification

## 1. Authority, intent, and exclusions

This is the final bounded Phase 2 macro selected by `docs/NEXT_ACTIONS.md`.
It is subordinate to `docs/MASTER_ROADMAP.md`; it does not change that roadmap.
It atomically creates exactly these already-authorized roadmap files from
genuine, materialized Phase 2 artifacts:

```text
timing/word_timeline.json   = serialize_alignment_result(AlignmentResult)
timing/caption_groups.json  = serialize_caption_groups(CaptionGroupsArtifact)
timing/emphasis_events.json = serialize_emphasis_events(EmphasisEventsArtifact)
```

`WordToFrameArtifact` is a mandatory lineage proof, not a fourth published
file. `AlignmentReport`, `CaptionPreviewArtifact`, and `V5V6CollisionReport`
are acceptance-only evidence: the publisher neither receives nor interprets
them. No fallback, merge, overwrite, repair, partial publication, durable
crash recovery, WorkspaceStore/schema/ArtifactRecord change, provider,
network, queue/retry, UI, EDL, renderer, Remotion, FFmpeg, V2, database, or
Phase 3/4 behavior is authorized. Phase 14 owns durable staged-revision and
commit-pointer lifecycle design.

## 2. Exact implementation boundary and imports

The only production files that may change are:

```text
engine/contracts/timing_publication.py
engine/contracts/__init__.py                         # additive root exports only
```

The only test/evidence files that may change or be added are:

```text
tests/test_timing_publication.py
tests/test_phase2_timing_publication_end_to_end.py
tests/test_alignment_request.py                       # mechanical exact-export oracle only
tests/fixtures/phase2/timing_publication_replay_v1.json
```

The fixture is immutable UTF-8 source evidence consumed only by
`tests/test_phase2_timing_publication_end_to_end.py`; it is not a runtime project artifact. No accepted upstream contract,
fixture, test, or production module may be edited. The publisher imports only
`pathlib`, `os`, `stat`, `hashlib`, `dataclasses`, the repository canonical JSON
encoder, and public types/serializers from `alignment_result`, `caption_groups`,
`emphasis_events`, and `word_to_frame`. It imports no private helper from any
contract and no forbidden subsystem named in section 1. Focused import tests
enforce this boundary.

## 3. Exact public surface and models

`engine/contracts/timing_publication.py` exports exactly:

```text
TIMING_PUBLICATION_V1
TIMING_PUBLICATION_HASH_V1
TimingPublicationRejectionReason
TimingPublicationContractError
PublishedTimingFile
TimingPublicationReceipt
publish_timing_artifacts
serialize_timing_publication_receipt
```

Constants are exactly `"TIMING-PUBLICATION-V1"` and
`"TIMING-PUBLICATION-HASH-V1"`. `PublishedTimingFile` declaration order is:

```text
relative_path: str
sha256: str
byte_length: int
```

`TimingPublicationReceipt` declaration order is exactly:

```text
schema_version, hash_scope_version, timing_publication_id,
timing_publication_hash, project_id, document_id, narration_revision_id,
narration_revision_hash, alignment_result_id, alignment_result_hash,
caption_groups_id, caption_groups_hash, emphasis_events_id,
emphasis_events_hash, word_to_frame_id, word_to_frame_hash, files
```

Both models are frozen dataclasses. `files` is an exact `tuple` of exactly
three `PublishedTimingFile` values, in this order and with these exact
forward-slash paths:

```text
timing/word_timeline.json
timing/caption_groups.json
timing/emphasis_events.json
```

`sha256` is 64 lowercase hexadecimal characters without a prefix and
`byte_length` is a non-bool non-negative `int`. Every other receipt string is
an exact, non-empty `str`; no extra model fields, mapping subclasses, or
coercions are accepted. The receipt envelope has every declared field. Its
identity projection is that envelope excluding only
`timing_publication_id` and `timing_publication_hash`; canonical JSON is the
repository UTF-8 sorted-key/no-whitespace encoder. The SHA-256 of that
projection is the receipt hash and the ID is `tpub_` plus its first 32 lowercase
hex characters. `serialize_timing_publication_receipt` returns only the
registered canonical bytes for the exact returned receipt object; it does not
reconstruct or accept a caller-built receipt.

## 4. Invocation, materialization, and lineage matrix

The only signature is:

```text
publish_timing_artifacts(*, alignment_result: AlignmentResult,
                         caption_groups: CaptionGroupsArtifact,
                         emphasis_events: EmphasisEventsArtifact,
                         word_to_frame: WordToFrameArtifact,
                         project_root: pathlib.Path) -> TimingPublicationReceipt
```

`project_root` must be an exact absolute `pathlib.Path`, with no `.` or `..`
component; another type raises `TypeError` before any serializer or filesystem
operation. Before any filesystem inspection, serializers run in this fixed
order: alignment result, caption groups, emphasis events, word-to-frame. A
serializer failure, non-exact object, unregistered object, mutation, proxy, or
subclass is `TimingPublicationContractError` with that input's pointer and
`DEPENDENCY_CONTENT_DRIFT`. The returned bytes are retained as the only three
payloads and are never reserialized after writes begin.

After all four serializers succeed, binding checks run in the following exact
row and field order. The left value is authoritative; the first unequal field
ends the call with `DEPENDENCY_BINDING_INVALID` at the right-hand input pointer.

| Row | Authoritative input | Compared input | Exact fields, in order |
|---|---|---|---|
| 1 | alignment result | caption groups | `project_id`, `document_id`, `narration_revision_id`, `narration_revision_hash`, `alignment_result_id`, `alignment_result_hash` |
| 2 | alignment result | emphasis events | `project_id`, `document_id`, `narration_revision_id`, `narration_revision_hash`, `alignment_result_id`, `alignment_result_hash` |
| 3 | caption groups | emphasis events | `caption_groups_id`, `caption_groups_hash` |
| 4 | alignment result | word-to-frame | `project_id`, `document_id`, `narration_revision_id`, `narration_revision_hash`, `alignment_result_id`, `alignment_result_hash` |
| 5 | caption groups | word-to-frame | `caption_groups_id`, `caption_groups_hash` |
| 6 | emphasis events | word-to-frame | `emphasis_events_id`, `emphasis_events_hash` |

Rows and fields are a deterministic precedence rule, not merely documentation.
No data is written until every row succeeds. Receipt lineage is copied from the
same authoritative values: project/document/revision from alignment result;
then each artifact's ID/hash. A returned receipt is registered only after the
post-promotion verification in section 6 succeeds.

## 5. Error oracle

`TimingPublicationRejectionReason` has exactly:

```text
STRUCTURE_INVALID, DEPENDENCY_CONTENT_DRIFT, DEPENDENCY_BINDING_INVALID,
PATH_INVALID, TARGET_EXISTS, WRITE_FAILED, VERIFY_FAILED, PROMOTION_FAILED,
IDENTITY_MISMATCH, NOT_MATERIALIZED
```

`TimingPublicationContractError(pointer, reason, issue_code=None)` is a
`ValueError`; its message is exactly `Timing publication rejected: <REASON>`.
`issue_code` is always `None` in this macro. Its only legal pointers are `/`,
`/alignment_result`, `/caption_groups`, `/emphasis_events`, `/word_to_frame`,
`/project_root`, `/timing`, and `/timing/word_timeline.json`,
`/timing/caption_groups.json`, `/timing/emphasis_events.json`. Error messages,
pointers, receipt values, and test diagnostics must never include a host path,
payload bytes, OS exception text, or a directory listing.

For `publish_timing_artifacts`, precedence is: signature/type; four
serializers in section 4; matrix rows/fields in section 4; project-root and
reparse preflight; target/staging absence; staging create; writes in published
file order; each immediate reread/digest verification in that same order;
pre-promotion reparse/absence recheck; promotion; post-promotion verification;
receipt registration. Project-root lexical/containment/non-directory/reparse
failures are `PATH_INVALID` at `/project_root`; a target or owned staging path
that exists and is not a reparse point is `TARGET_EXISTS` at `/timing`.
Existing reparse points take precedence as `PATH_INVALID`. A write/open/fsync
failure is `WRITE_FAILED` at that file pointer; a reread, byte-length, or hash
mismatch is `VERIFY_FAILED` there; a no-replace rename or post-promotion
verification failure is `PROMOTION_FAILED` at `/timing`. Receipt serialization
uses exact registered-object/materialization checks first (`NOT_MATERIALIZED`),
then exact nested/root shape (`STRUCTURE_INVALID`), then identity/hash
(`IDENTITY_MISMATCH`); it never emits filesystem reasons.

## 6. Filesystem transaction and Windows reparse rule

The target is exactly `project_root / "timing"`. Preflight requires that root
exists as a real directory and that `project_root`, its direct parent, any
existing target, and any existing staging path are neither a symlink nor a
Windows reparse point (including junctions). Reparse detection uses `lstat`
and, where exposed, the Windows reparse attribute; `Path.is_symlink()` alone
is insufficient. The resolved target parent must be the validated root, so no
lexical traversal or escape can be accepted.

The deterministic owned staging sibling is exactly
`project_root / (".timing-publication-" + timing_publication_id + ".staging")`.
It is created exclusively only after the receipt identity has been calculated
from validated inputs and the target/staging were confirmed absent. Each of the
three retained canonical byte payloads is exclusively created in staging,
written, flushed, `fsync`ed, reread, and SHA-256/length checked before the
next file. No target is created before all three checks pass.

Immediately before promotion, parent, target, and staging are checked again
with the same no-reparse rule; target must still be absent. Promotion uses a
single `os.rename(staging, target)` equivalent that fails if the target exists.
On Windows the implementation must not use `os.replace`, `Path.replace`,
`MoveFileEx` with `MOVEFILE_REPLACE_EXISTING`, or any overwrite-capable move.
If a race creates target or a reparse point, no replacement is attempted and
the call fails according to section 5. After rename, the exact three target
files are reread and independently byte/hash/length checked; target itself
and its direct parent are checked again for reparse status before returning.

Before promotion, every failure removes only the publisher's exact owned flat
staging directory: it unlinks only the three named regular, non-reparse files
then `rmdir`s that exact non-reparse directory. It never recursively deletes,
follows a link/reparse point, or removes a target. If a hostile replacement or
reparse is observed during cleanup, it is left untouched as non-owned and the
original stable failure is raised. Promotion/post-promotion failures use the
same safe staging cleanup where staging still exists. No receipt is returned
or registered on any failure; no target may be published on pre-promotion
failure. This is an atomic no-replacement success boundary, not a power-loss
durability claim.

## 7. Required test and REPLAY evidence

`tests/test_timing_publication.py` proves exact exports/signature/models,
receipt canonical golden and repeatability across independent roots, all six
matrix rows including first-field precedence, all four materialization failures
before I/O, traversal/root/symlink/junction/existing-target/existing-staging
rejection, exclusive-write/verify/promotion fault injection, no-replace race,
safe cleanup, and no output/receipt on every failing branch.

`tests/test_phase2_timing_publication_end_to_end.py` is the sole consumer of
`tests/fixtures/phase2/timing_publication_replay_v1.json`. It creates one
versioned, real REPLAY chain with at least 96 words, multiple caption groups,
and non-overlapping emphasis spans:

```text
AlignmentResult -> CaptionGroups -> EmphasisEvents -> WordToFrame
-> AlignmentReport -> CaptionPreview -> V5/V6CollisionReport -> publication
```

The 96-word minimum is the bounded high-cardinality acceptance gate for this
Phase 2 contract: tests must assert the source word count and that no per-frame
collection is materialized. It proves published byte equality, no per-frame expansion, clean collision,
and explicit low-confidence `REVIEW_REQUIRED` evidence. A REVIEW_REQUIRED
report and a separately constructed collision BLOCKER are asserted as visible
acceptance evidence and are never labelled a clean Phase 2 acceptance result.
The fixture/test use no monkeypatch of contract semantics, network, provider,
V2, Remotion, FFmpeg, UI, or filesystem operation outside temporary test
project roots.

## 8. Phase 2 closure gate

Phase 2 may be marked CLOSED only after this exact implementation has an
independent audit with zero open blocker/major/minor findings, focused and broad
non-FastAPI regression gates pass, and the final acceptance record maps all
six Master Roadmap deliverables and all six Phase 2 acceptance criteria to
concrete evidence. Otherwise Phase 2 remains open.
