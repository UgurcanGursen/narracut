# Phase 2 Caption Preview + V5/V6 Collision Contract

## 1. Status, authority, and bounded intent

Status: Candidate specification

Accepted: No

Implementation authorized: No

Phase 2 closed: No

This is the single Phase 2 macro-package selected by `docs/NEXT_ACTIONS.md`.
It is subordinate to `docs/MASTER_ROADMAP.md`.  It defines a deterministic,
in-memory, reviewable sparse scene geometry artifact and an independent V5/V6
collision report.  It assigns no Slice number, total Slice count, or Phase 2
completion percentage.

The only accepted inputs are `CaptionGroupsArtifact`, `EmphasisEventsArtifact`,
and `WordToFrameArtifact`.  The package proves a limited but important Phase 2
property: every generated V5/V6 scene has canonical frame provenance and any
positive-area, positive-duration cross-track occlusion or safe-area breach is
reported deterministically.  It does not promise a rendered visual result.

## 2. Explicit exclusions

This contract does not authorize narration input, word/string search, text
normalization, caller-authored milliseconds or frames, font lookup, glyph
shaping, font metrics, rasterization, PNG/video output, Remotion, EDL, FFmpeg,
V2, UI, filesystem publication, network, database/cache, provider execution,
threads, clock/random use, scheduling, collision repair, same-track collision
rules, artifact lifecycle, timing publication, domain-pack changes, or Phase 3
work.  It does not change an accepted upstream contract or stable issue-code
inventory.

The diagnostic SVG is an in-memory UTF-8 `str`; it is neither a renderer nor a
file artifact.  It draws semantic rectangles and labels only.  It must never
be treated as a font, text, or pixel-layout oracle.

## 3. Paths, ownership, and import boundary

The exact new production paths are:

    engine/contracts/caption_preview.py
    engine/contracts/v5_v6_collision.py

The exact focused paths are:

    tests/test_caption_preview.py
    tests/test_v5_v6_collision.py

Only the integration owner may add the exports in
`engine/contracts/__init__.py` and the mechanical exact-export assertion in
`tests/test_alignment_request.py`.  `caption_preview.py` may import canonical
JSON, `CaptionGroupsArtifact`/`serialize_caption_groups`,
`EmphasisEventsArtifact`/`serialize_emphasis_events`, and
`WordToFrameArtifact`/`serialize_word_to_frame`.  `v5_v6_collision.py` may
import canonical JSON and the public caption-preview types/serializer only.
Neither module imports private helpers from another contract.  All forbidden
imports in section 2 are enforced by focused import tests.  Compile, load,
serialize, and SVG generation perform no I/O.

## 4. Exact public export delta

`caption_preview.py` exports exactly these fourteen symbols:

    CAPTION_PREVIEW_V1
    CAPTION_PREVIEW_HASH_V1
    CAPTION_PREVIEW_POLICY_V1
    PreviewTrack
    PreviewRect
    CaptionPreviewLayoutPolicy
    PreviewScene
    CaptionPreviewArtifact
    CaptionPreviewRejectionReason
    CaptionPreviewContractError
    compile_caption_preview
    load_caption_preview
    serialize_caption_preview
    render_caption_preview_diagnostic_svg

`v5_v6_collision.py` exports exactly these fourteen symbols:

    V5_V6_COLLISION_REPORT_V1
    V5_V6_COLLISION_REPORT_HASH_V1
    V5_V6_COLLISION_FINDING_V1
    V5_V6_COLLISION_FINDING_HASH_V1
    V5V6CollisionFindingKind
    V5V6CollisionSeverity
    V5V6CollisionRejectionReason
    V5V6CollisionFinding
    V5V6CollisionReport
    V5V6CollisionContractError
    compile_v5_v6_collision_report
    load_v5_v6_collision_report
    serialize_v5_v6_collision_report
    render_v5_v6_collision_diagnostic_svg

No mutable builder, geometry helper, registry, projection,
intersection routine, or parser is public.

## 5. Canonical coordinate, interval, and policy rules

Coordinates use an exact normalized canvas of `1_000_000` units on each axis.
A rectangle is half-open `[left,right) x [top,bottom)`.  A scene time range is
half-open `[start_frame,end_exclusive_frame)`.  All coordinates and frames are
exact Python `int`, never `bool`, non-negative, and no coordinate may exceed
`1_000_000`.  Every rectangle must satisfy `left < right` and `top < bottom`.
Every range must satisfy `start_frame < end_exclusive_frame`.

Every call provides one exact immutable `CaptionPreviewLayoutPolicy`; there
are no defaults, global configuration, or implicit fallback. Its
`policy_version` is exactly `CAPTION-PREVIEW-POLICY-V1`, and its canonical
projection hash is SHA-256 canonical JSON, stored as `sha256:<64 lowercase
hex>` in `layout_policy_snapshot_hash`. The policy object is copied as an
owned immutable nested value into the artifact. The baseline REPLAY policy
uses this safe rectangle:

    left=50_000, top=50_000, right=950_000, bottom=950_000

Its V5 geometry is `left=80_000, top=80_000, right=920_000, bottom=260_000`.
Its V6 geometry is `left=80_000, top=760_000, right=920_000, bottom=920_000`.
These are semantic proxy locations, not typography measurements.  They are
deliberately separated so the accepted compiler golden is PASS; loaders and
reports still validate hostile/tampered/constructed collision candidates.

Positive overlap means, exactly:

    max(left_a,left_b) < min(right_a,right_b)
    and max(top_a,top_b) < min(bottom_a,bottom_b)
    and max(start_a,start_b) < min(end_a,end_b)

Equal edges, corner touching, temporal adjacency, or zero area/duration are
not collisions.  Safe-area violation means a scene rectangle is not fully
contained by the fixed safe rectangle; boundary equality is allowed.

## 6. Caption-preview constants, enums, and field order

    CAPTION_PREVIEW_V1 = "CAPTION-PREVIEW-V1"
    CAPTION_PREVIEW_HASH_V1 = "CAPTION-PREVIEW-HASH-V1"
    CAPTION_PREVIEW_POLICY_V1 = "CAPTION-PREVIEW-POLICY-V1"

    class PreviewTrack(str, Enum):
        V5 = "V5"
        V6 = "V6"

    class CaptionPreviewRejectionReason(str, Enum):
        STRUCTURE_INVALID = "STRUCTURE_INVALID"
        UNSUPPORTED_VALUE = "UNSUPPORTED_VALUE"
        DEPENDENCY_CONTENT_DRIFT = "DEPENDENCY_CONTENT_DRIFT"
        DEPENDENCY_BINDING_INVALID = "DEPENDENCY_BINDING_INVALID"
        FRAME_BINDING_INVALID = "FRAME_BINDING_INVALID"
        GEOMETRY_INVALID = "GEOMETRY_INVALID"
        NON_CANONICAL_SERIALIZATION = "NON_CANONICAL_SERIALIZATION"
        IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
        CONTENT_DRIFT = "CONTENT_DRIFT"
        NOT_MATERIALIZED = "NOT_MATERIALIZED"

Field declaration order is normative:

    @dataclass(frozen=True)
    class PreviewRect:
        left: int
        top: int
        right: int
        bottom: int

    @dataclass(frozen=True)
    class CaptionPreviewLayoutPolicy:
        policy_version: str
        safe_rect: PreviewRect
        v5_rect: PreviewRect
        v6_rect: PreviewRect

    @dataclass(frozen=True)
    class PreviewScene:
        schema_version: str
        hash_scope_version: str
        preview_scene_id: str
        preview_scene_hash: str
        track: PreviewTrack
        ordinal: int
        source_id: str
        start_frame: int
        end_exclusive_frame: int
        rect: PreviewRect
        semantic_proxy_label: str

    @dataclass(frozen=True)
    class CaptionPreviewArtifact:
        schema_version: str
        hash_scope_version: str
        caption_preview_id: str
        caption_preview_hash: str
        project_id: str
        document_id: str
        narration_revision_id: str
        narration_revision_hash: str
        caption_groups_id: str
        caption_groups_hash: str
        emphasis_events_id: str
        emphasis_events_hash: str
        word_to_frame_id: str
        word_to_frame_hash: str
        layout_policy: CaptionPreviewLayoutPolicy
        layout_policy_snapshot_hash: str
        canvas_units: int
        safe_rect: PreviewRect
        scenes: tuple[PreviewScene, ...]

`CaptionPreviewContractError(pointer, reason, issue_code=None)` is a
`ValueError`.  `pointer` is one of `/`, `/caption_groups`, `/emphasis_events`,
`/word_to_frame`, `/scenes`, `/safe_rect`, or `/scenes/<uint32>`.  An optional
issue code must already be in the stable temporal inventory.  The error string
is exactly `Caption preview rejected: <REASON>` and includes no hostile data.

## 7. Preview derivation and signatures

The exact signatures are:

    compile_caption_preview(*, caption_groups: CaptionGroupsArtifact,
                            emphasis_events: EmphasisEventsArtifact,
                            word_to_frame: WordToFrameArtifact,
                            layout_policy: CaptionPreviewLayoutPolicy) -> CaptionPreviewArtifact
    load_caption_preview(source: bytes, *, caption_groups: CaptionGroupsArtifact,
                         emphasis_events: EmphasisEventsArtifact,
                         word_to_frame: WordToFrameArtifact,
                         layout_policy: CaptionPreviewLayoutPolicy) -> CaptionPreviewArtifact
    serialize_caption_preview(artifact: CaptionPreviewArtifact) -> bytes
    render_caption_preview_diagnostic_svg(artifact: CaptionPreviewArtifact) -> str

Dependencies must be exact, genuine, current materialized artifacts.  First,
serialize each dependency; a failure is mapped to
`DEPENDENCY_CONTENT_DRIFT` at its dependency pointer.  Then require shared
project/document/revision identifiers and matching group/event frame source
IDs, source ordinals, word boundaries, ms values, and half-open frame values.
Any discrepancy is `DEPENDENCY_BINDING_INVALID` or `FRAME_BINDING_INVALID`;
there is no repair or fallback.

Emit scenes in this exact order: all V5 emphasis-frame scenes by their source
ordinal, then all V6 caption-frame scenes by their source ordinal.  Scene
ordinal is contiguous over the combined array beginning at zero.  V5 source is
the matching `EmphasisEvent`; its label is exactly
`"[EMPHASIS:" + intensity.value + "]"`.  This is an explicit semantic proxy;
no event word, narration text, display text, or inferred string may enter V5.
V6 source is the matching `CaptionGroup`; its label is exactly that group's
`display_text`, byte-for-byte.  The compiler never receives narration.

Each scene has `schema_version="CAPTION-PREVIEW-V1"`,
`hash_scope_version="CAPTION-PREVIEW-HASH-V1"`, and its layout-policy track
rectangle. Policy validation precedes dependency inspection: exact type, exact
fields, exact version, non-bool normalized integer rectangles, and all
rectangles valid within the normalized canvas. Track rectangles are not
required to be inside `safe_rect`: that is the report's intentional,
materializable `SAFE_AREA_VIOLATION` condition. A failure is
`GEOMETRY_INVALID` at `/layout_policy` with no fallback.
The scene projection omits its two identity fields; SHA-256 of its canonical
JSON is `preview_scene_hash`, and ID is `pscn_` plus its first 32 hex chars.
The artifact projection omits its two identity fields; its SHA-256 is
`caption_preview_hash`, and ID is `cprev_` plus its first 32 hex chars.
Canonical JSON is the repository encoder's UTF-8, sorted-key, no-whitespace
encoding.  Root serialization contains every declared field; nested rectangle
keys are `left`, `top`, `right`, `bottom`.

## 8. Preview load, serialization, and registry behavior

`load_caption_preview` independently derives expected output from its supplied
exact policy before accepting source semantics. It rejects exact non-bytes with `TypeError`; BOM, duplicate
keys, floats, non-canonical integer spellings, constants, malformed UTF-8, or
non-canonical bytes cause `NON_CANONICAL_SERIALIZATION`.  Exact key/type shape
precedes enum/literal validation; root dependency declarations precede scenes;
scene semantics precede scene identities; root identity precedes byte equality.
The error precedence is deterministic and specified by that order.

The loader accepts only bytes equal to the expected canonical envelope; it
does not trust supplied geometry, label, frames, provenance, IDs, or hashes.
Unknown enum/literal is `UNSUPPORTED_VALUE` with `UNSUPPORTED_CONTRACT_ENUM`.
Incorrect frame provenance is `FRAME_BINDING_INVALID` with
`CANONICAL_COVERAGE_BLOCKER`; invalid rectangle is `GEOMETRY_INVALID`;
dependency mismatch is `DEPENDENCY_BINDING_INVALID` with
`ALIGNMENT_REQUEST_IDENTITY_MISMATCH`; incorrect identity is
`IDENTITY_MISMATCH`.

Successful compilation and loading register only the returned exact object in
a weak-reference registry with its immutable canonical bytes and a recursive
identity signature.  Weakref cleanup removes its own entry only.  Duplicate
live registration is an internal `RuntimeError`; failed registration rolls
back.  `serialize_caption_preview` rejects a non-exact/unregistered object as
`NOT_MATERIALIZED`, then detects mutation, type substitution, identity/hash
drift, or changed envelope as `CONTENT_DRIFT`.  It returns the registered
bytes, never a recomputed permissive serialization.

## 9. Collision report constants, enums, and models

    V5_V6_COLLISION_REPORT_V1 = "V5-V6-COLLISION-REPORT-V1"
    V5_V6_COLLISION_REPORT_HASH_V1 = "V5-V6-COLLISION-REPORT-HASH-V1"
    V5_V6_COLLISION_FINDING_V1 = "V5-V6-COLLISION-FINDING-V1"
    V5_V6_COLLISION_FINDING_HASH_V1 = "V5-V6-COLLISION-FINDING-HASH-V1"

    class V5V6CollisionFindingKind(str, Enum):
        CROSS_TRACK_OCCLUSION = "CROSS_TRACK_OCCLUSION"
        SAFE_AREA_VIOLATION = "SAFE_AREA_VIOLATION"

    class V5V6CollisionSeverity(str, Enum):
        BLOCKER = "BLOCKER"

    class V5V6CollisionRejectionReason(str, Enum):
        STRUCTURE_INVALID = "STRUCTURE_INVALID"
        UNSUPPORTED_VALUE = "UNSUPPORTED_VALUE"
        DEPENDENCY_CONTENT_DRIFT = "DEPENDENCY_CONTENT_DRIFT"
        DEPENDENCY_BINDING_INVALID = "DEPENDENCY_BINDING_INVALID"
        FINDING_INVALID = "FINDING_INVALID"
        NON_CANONICAL_SERIALIZATION = "NON_CANONICAL_SERIALIZATION"
        IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
        CONTENT_DRIFT = "CONTENT_DRIFT"
        NOT_MATERIALIZED = "NOT_MATERIALIZED"

    @dataclass(frozen=True)
    class V5V6CollisionFinding:
        schema_version: str
        hash_scope_version: str
        v5_v6_collision_finding_id: str
        v5_v6_collision_finding_hash: str
        ordinal: int
        kind: V5V6CollisionFindingKind
        severity: V5V6CollisionSeverity
        primary_preview_scene_id: str
        secondary_preview_scene_id: str | None
        overlap_start_frame: int
        overlap_end_exclusive_frame: int
        overlap_rect: PreviewRect | None

    @dataclass(frozen=True)
    class V5V6CollisionReport:
        schema_version: str
        hash_scope_version: str
        v5_v6_collision_report_id: str
        v5_v6_collision_report_hash: str
        caption_preview_id: str
        caption_preview_hash: str
        finding_count: int
        blocker_count: int
        findings: tuple[V5V6CollisionFinding, ...]

`V5V6CollisionContractError(pointer, reason, issue_code=None)` is a
`ValueError`; its exact message is `V5/V6 collision report rejected: <REASON>`.
Pointers are `/`, `/caption_preview`, `/findings`, and `/findings/<uint32>`.

## 10. Collision derivation, ordering, and signatures

Signatures are:

    compile_v5_v6_collision_report(*, caption_preview: CaptionPreviewArtifact) -> V5V6CollisionReport
    load_v5_v6_collision_report(source: bytes, *, caption_preview: CaptionPreviewArtifact) -> V5V6CollisionReport
    serialize_v5_v6_collision_report(report: V5V6CollisionReport) -> bytes
    render_v5_v6_collision_diagnostic_svg(report: V5V6CollisionReport,
                                           *, caption_preview: CaptionPreviewArtifact) -> str

The report first serializes the exact preview.  Failure is
`DEPENDENCY_CONTENT_DRIFT`.  It considers only two classes of findings:

1. one `SAFE_AREA_VIOLATION` for every scene not contained by `safe_rect`,
   with primary scene set, secondary scene null, its own frame range, and its
   own rectangle as `overlap_rect`;
2. one `CROSS_TRACK_OCCLUSION` for every V5/V6 pair with positive spatial and
   temporal intersection, with primary the V5 scene, secondary the V6 scene,
   and exact half-open intersection range/rectangle.

No V5/V5 or V6/V6 pair is inspected.  No finding is deduplicated, repaired,
suppressed, or converted to a warning.  All findings are BLOCKER.  Ordering is
safe-area findings by combined scene ordinal, then cross-track findings by V5
ordinal followed by V6 ordinal.  Finding ordinal is contiguous from zero.
`finding_count == blocker_count == len(findings)`.

Finding projection omits its identity fields; hash/ID are SHA-256 and
`v5v6f_` plus first 32 hex characters.  Root projection omits root identity;
hash/ID are SHA-256 and `v5v6r_` plus first 32 hex characters.  Findings bind
their exact preview scene IDs, so the same geometry from another preview cannot
reuse an identity.

## 11. Collision load, serialization, and registry behavior

The report loader has the same strict bytes/parser requirements as section 8.
It derives the expected report from the genuine preview, then validates root
shape/literals, preview declarations, finding shapes/literals, finding
semantics, finding identities, root identity, and byte equality in that exact
order.  A report is accepted only if bytes equal its expected envelope.
Incorrect preview declaration is `DEPENDENCY_BINDING_INVALID`; unknown enums
are `UNSUPPORTED_VALUE`; malformed or reordered findings, an incorrect
intersection, same-track finding, edge-only finding, or non-BLOCKER severity
is `FINDING_INVALID`; identity errors are `IDENTITY_MISMATCH`.

The report has a separate weak registry and the identical rollback/cleanup,
exact-type, recursive mutation detection, and registered-byte serialization
rules of section 8.  No registry retains a whole video or a prior preview
beyond the live object reference.

## 12. Diagnostic SVG contract

Both SVG functions return deterministic, single-line UTF-8 SVG: markup is
ASCII and labels are XML-escaped Unicode. Normal NFC non-ASCII label text is
valid and must be preserved. Escape exactly `&`, `<`, `>`, `"`, and `'`;
reject labels containing controls, surrogates, or non-NFC text as
`CONTENT_DRIFT`.  SVG is 1000 by 1000 viewBox units; normalized coordinates
are converted by exact integer floor division by 1000.  It contains no style
sheet, script, URL, font family, external resource, timestamp, random ID, or
user-controlled markup.

Preview SVG order is safe rectangle, then scenes in scene order.  A V5 scene
uses fill `#E8A317`, V6 uses `#2C7BE5`; each contains a `data-track` and
`data-scene-id` attribute and a `<text>` semantic label.  Collision SVG adds
findings in finding order using fill `#D7263D`; it also includes the preview
scene rectangles in scene order.  The report function must reject an unrelated
preview via `DEPENDENCY_BINDING_INVALID` before producing SVG.

## 13. Literal REPLAY goldens

The focused fixture uses accepted canonical inputs whose frame projections are
as follows (all omitted accepted dependency fields are fixed fixture bytes):

    emphasis_frames = [{"source_kind":"EMPHASIS_EVENT","source_id":"emph_a",
      "ordinal":0,"start_word_ordinal":0,"end_exclusive_word_ordinal":2,
      "start_word_id":"word_0","end_word_id":"word_1","start_ms":100,
      "end_ms":900,"start_frame":3,"end_exclusive_frame":27}]
    caption_frames = [{"source_kind":"CAPTION_GROUP","source_id":"cgrp_a",
      "ordinal":0,"start_word_ordinal":0,"end_exclusive_word_ordinal":2,
      "start_word_id":"word_0","end_word_id":"word_1","start_ms":100,
      "end_ms":900,"start_frame":3,"end_exclusive_frame":27}]

The literal scene semantics, before test-calculated identity fields, are:

    {"track":"V5","ordinal":0,"source_id":"emph_a","start_frame":3,
     "end_exclusive_frame":27,"rect":{"left":80000,"top":80000,
     "right":920000,"bottom":260000},"semantic_proxy_label":"[EMPHASIS:STRONG]"}
    {"track":"V6","ordinal":1,"source_id":"cgrp_a","start_frame":3,
     "end_exclusive_frame":27,"rect":{"left":80000,"top":760000,
     "right":920000,"bottom":920000},"semantic_proxy_label":"Alpha beta"}

The accepted preview has zero collision findings. The policy-bearing
canonical envelope is exactly 2,195 UTF-8 bytes, with SHA-256
`c7d794557bcc304559117e4fbe0724bfd3e77c03180199ac277f0ee185fe6f73`,
root ID `cprev_d31b9e038999a4199c3c132ad9dc223c`, root hash
`d31b9e038999a4199c3c132ad9dc223c8dbb4cc7232a0c4caf824cded8d22277`,
and policy snapshot hash
`sha256:6c5c6c78ce8f3c4b760d7f6c4e28b8aa615cc28a9f00435ebf02eafadce693d9`.
The complete expanded literal JSON is:

    {"canvas_units":1000000,"caption_groups_hash":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","caption_groups_id":"cgs_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","caption_preview_hash":"d31b9e038999a4199c3c132ad9dc223c8dbb4cc7232a0c4caf824cded8d22277","caption_preview_id":"cprev_d31b9e038999a4199c3c132ad9dc223c","document_id":"document_a","emphasis_events_hash":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","emphasis_events_id":"emps_cccccccccccccccccccccccccccccccc","hash_scope_version":"CAPTION-PREVIEW-HASH-V1","layout_policy":{"policy_version":"CAPTION-PREVIEW-POLICY-V1","safe_rect":{"bottom":950000,"left":50000,"right":950000,"top":50000},"v5_rect":{"bottom":260000,"left":80000,"right":920000,"top":80000},"v6_rect":{"bottom":920000,"left":80000,"right":920000,"top":760000}},"layout_policy_snapshot_hash":"sha256:6c5c6c78ce8f3c4b760d7f6c4e28b8aa615cc28a9f00435ebf02eafadce693d9","narration_revision_hash":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","narration_revision_id":"revision_a","project_id":"project_a","safe_rect":{"bottom":950000,"left":50000,"right":950000,"top":50000},"scenes":[{"end_exclusive_frame":27,"hash_scope_version":"CAPTION-PREVIEW-HASH-V1","ordinal":0,"preview_scene_hash":"8b7f80efc5632ca946b3d6b4928582e10e4f62af123821b348746f5890f4653e","preview_scene_id":"pscn_8b7f80efc5632ca946b3d6b4928582e1","rect":{"bottom":260000,"left":80000,"right":920000,"top":80000},"schema_version":"CAPTION-PREVIEW-V1","semantic_proxy_label":"[EMPHASIS:STRONG]","source_id":"emph_a","start_frame":3,"track":"V5"},{"end_exclusive_frame":27,"hash_scope_version":"CAPTION-PREVIEW-HASH-V1","ordinal":1,"preview_scene_hash":"8cbe4cce8218c79f6dd455d317c20f3db40e3743577a35ab57c66cda13ab0340","preview_scene_id":"pscn_8cbe4cce8218c79f6dd455d317c20f3d","rect":{"bottom":920000,"left":80000,"right":920000,"top":760000},"schema_version":"CAPTION-PREVIEW-V1","semantic_proxy_label":"Alpha beta","source_id":"cgrp_a","start_frame":3,"track":"V6"}],"schema_version":"CAPTION-PREVIEW-V1","word_to_frame_hash":"dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd","word_to_frame_id":"w2f_dddddddddddddddddddddddddddddddd"}

    V5: pscn_8b7f80efc5632ca946b3d6b4928582e1 / 8b7f80efc5632ca946b3d6b4928582e10e4f62af123821b348746f5890f4653e
    V6: pscn_8cbe4cce8218c79f6dd455d317c20f3d / 8cbe4cce8218c79f6dd455d317c20f3db40e3743577a35ab57c66cda13ab0340
    root: cprev_d31b9e038999a4199c3c132ad9dc223c / d31b9e038999a4199c3c132ad9dc223c8dbb4cc7232a0c4caf824cded8d22277

The literal SVG golden is exactly 647 UTF-8 bytes, SHA-256
`1e96a7e7d022a2484aa59f9aa207f8e82e2a7c7bec222b1e2072b7b23f443b54`:

    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000" width="1000" height="1000"><rect data-kind="safe-area" x="50" y="50" width="900" height="900" fill="none" stroke="#111111"/><rect data-track="V5" data-scene-id="pscn_8b7f80efc5632ca946b3d6b4928582e1" x="80" y="80" width="840" height="180" fill="#E8A317"/><text data-scene-id="pscn_8b7f80efc5632ca946b3d6b4928582e1" x="80" y="80">[EMPHASIS:STRONG]</text><rect data-track="V6" data-scene-id="pscn_8cbe4cce8218c79f6dd455d317c20f3d" x="80" y="760" width="840" height="160" fill="#2C7BE5"/><text data-scene-id="pscn_8cbe4cce8218c79f6dd455d317c20f3d" x="80" y="760">Alpha beta</text></svg>

The adversarial collision fixture constructs a registered preview with V5
`[80000,920000) x [80000,260000)` and V6
`[80000,920000) x [200000,360000)`, both `[3,27)`.  Its literal finding
semantics are `CROSS_TRACK_OCCLUSION`, BLOCKER, range `[3,27)`, and rectangle
`[80000,920000) x [200000,260000)`.  The test owns a fully expanded canonical
report envelope/SVG, byte length, and SHA-256.  Separate literals prove that
temporal adjacency `[3,27)`/`[27,40)`, shared horizontal edge, shared vertical
edge, and corner-only contact emit no cross-track finding.

This collision fixture is not forged or privately registered. It invokes the
public compiler with an exact `CaptionPreviewLayoutPolicy` whose policy version
and safe/V5 rectangles equal the baseline and whose V6 rectangle is
`left=80_000, top=200_000, right=920_000, bottom=360_000`; all rectangles remain
inside the safe rectangle. It then invokes the public collision compiler on
that genuine returned preview. The full policy-bearing PASS and BLOCKED
envelopes, both SVGs, every ID/hash, byte length, and SHA-256 are literal
constants in the focused tests and are independently recomputed with a compact
sorted-key encoder. No private registry access is permitted by any test.

## 14. Required test matrix and quality gates

Focused tests must cover: exact exports; compile/load/serialize round trips;
complete preview/report/SVG literal goldens; deterministic order; all enum and
key/type errors; duplicate keys/BOM/floats/reordered bytes; exact dependencies;
dependency drift vs binding; every frame source binding; V5 proxy/no-text and
V6 exact display-text behavior; safe boundaries; all positive/edge/corner/time
intersection cases; same-track ignored; identity mutation; weak registry GC;
error pointer/reason/issue-code precedence; no forbidden imports; and bounded
large REPLAY fixtures.

Complexity is `O(C + E + S + F)`, where `C` caption frames, `E` emphasis
frames, `S=C+E` scenes, and `F` emitted findings.  The implementation must use
a deterministic sweep/index or equivalent bounded candidate enumeration, not
unconditional `O(C*E)` pair expansion.  Memory is `O(S+F)` and must not retain
per-video state after weakly registered objects are collected.  Focused tests,
the exact export test, and the existing non-FastAPI upstream contract suite
must pass using REPLAY only.

## 15. Acceptance boundary

Acceptance requires a reviewed specification, bounded implementation, one
independent audit, focused visual/oracle and upstream regression evidence, and
one documentation closure.  It establishes only canonical preview geometry
and deterministic V5/V6 collision reporting.  It does not publish timing
files, render captions, implement EDL/Remotion, or close Phase 2.
