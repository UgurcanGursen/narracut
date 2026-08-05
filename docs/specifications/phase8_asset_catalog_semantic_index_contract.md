# Phase 8 — Asset Ingestion, Catalog and Semantic Index Contract

Status: Accepted specification — bounded implementation authorized by an
independent read-only audit (0 blocker / 0 major / 0 minor). This does not
close Phase 8.

## Boundary

This package establishes a fail-closed, local `REPLAY` asset ingress and
semantic catalog. It accepts caller-supplied bytes only through an exact asset
package manifest; it never opens a URL, invokes a provider SDK, drives a
browser, invokes an LLM, creates a queue, chooses an asset for an EDL, or
mutates an existing Phase 3/4/5/6/7 artifact. Provider acquisition, license
negotiation, remote retries/rate limits, UI review, semantic search ranking,
audio mixing and automatic rendering are explicitly out of scope.

Core owns asset identity, byte provenance, media facts, visual-family evidence,
duplicate/reuse decisions and typed semantic containers. The selected Domain
Pack owns allowed role tokens, visual grammar, avoid-context tokens and source
audio policy. Core contains no category enum such as `server_room`, no provider
brand branch and no `if domain == ...` behavior.

## Input and identity

`AssetIngestionPackageV1` contains, in canonical order:

```text
package_id / package_hash
project_id / sequence_id | null
policy_snapshot_id / policy_snapshot_hash
asset_bytes
source_descriptor
media_probe_evidence
fingerprint_evidence
semantic_declaration
selected_ranges
```

`asset_bytes` is exact immutable local bytes. `source_hash` is raw SHA-256 of
those bytes. No path, URL, filename, EXIF text or caller-declared hash can
replace it. Package hash covers every field except its own ID/hash. IDs derive
from their SHA-256 projection. The compiler owns an opaque, short-lived
materialization handle for the exact bytes; a later replay must resolve that
handle and re-hash the recovered bytes. A forged, stale, missing or changed
materialization rejects.

`source_descriptor` is closed and contains `provider_id`, `source_uri`,
`license_mode`, ordered `allowed_uses`, `origin_kind=local_replay`, and an
optional normalized attribution. `provider_id` and all semantic strings are
opaque normalized tokens, not core enums. `source_uri` is an opaque URI/URN:
the compiler neither opens nor resolves it.

## Media and semantic model

`AssetRecordV1` is the canonical catalog output. It has:

```text
asset_id / asset_hash / source_hash / source_byte_length
source_descriptor
media_type = image | video | document | audio
media_facts = duration_ms|null, width|null, height|null, fps_numerator|null,
              fps_denominator|null, codec|null, has_audio
visual_family_id
subjects[], actions[], setting, mood, semantic_tags[], avoid_contexts[]
domain_roles[], domain_sensitivity_tags[]
selected_ranges[]
source_audio_eligibility
fingerprint_evidence
duplicate_of_asset_id|null / duplicate_of_asset_hash|null
```

All lists are ordered, unique normalized tokens. `duration_ms` and dimensions
are non-negative integers; video FPS is a reduced rational pair and is absent
for non-video media. Media facts are accepted only if their exact structured
`MediaProbeEvidenceV1` is a trusted REPLAY fixture projection bound to the raw
bytes hash. Phase 8 does not claim to decode arbitrary production media.

`AssetBriefV1` has a stable ID/hash and contains an editorial role, subject,
action, setting, ordered `avoid_contexts`, preferred asset-type tokens, selected
Domain Pack snapshot ID/hash and resolved visual-policy hash. It is a request,
not an asset selection. Its role/avoid tokens must be permitted by the resolved
policy. A missing policy or unknown token rejects; no silent generic-stock
fallback exists.

`SourceAudioEligibilityV1` is closed:

```text
eligible | ineligible | review_required | not_applicable
```

It records ordered reason tokens, evidence IDs and the policy snapshot. It is
catalog metadata only; it cannot create an audio EDL event before Phase 11.

## Fingerprints, families and duplicate decisions

`FingerprintEvidenceV1` binds the source hash to ordered multi-frame perceptual
fingerprint tokens, ordered local-feature tokens and a same-source key. Tokens
are fixed-length lowercase SHA-256 hashes of deterministic REPLAY fixture
features; core does not infer or fabricate visual similarity. Empty fingerprint
sets are permitted only for `document` and `audio` and must be explicit.

The compiler derives a `visual_family_id` from the policy snapshot, media type,
and ordered fingerprint evidence only. Semantic declarations never divide a
visually identical family. A caller cannot supply a family ID. `AssetCatalogV1`
is an immutable ordered set of records and a
`DuplicateDecisionV1` per candidate:

```text
same_source | exact_bytes | perceptual_match | local_feature_match |
selected_range_overlap | distinct
```

The first five decisions block catalog insertion; `distinct` permits insertion.
Selected ranges are
media-local millisecond intervals, ordered and non-overlapping. Reuse cooldown
and chapter family budget are represented by a policy-bound `AssetReusePlanV1`;
the compiler rejects a same-family reuse inside a cooldown or over a family
budget. It does not choose a replacement asset.

## Policy resolution

Exactly one `asset_catalog_policy` is resolved from:

```text
resolved_policy.policy_bundles[].policy.visual.asset_catalog_policy
```

It has a version, allowed asset-brief roles, allowed preferred-type tokens,
allowed avoid-context tokens, source-audio eligibility reason tokens, generic
stock provider tokens, reuse cooldown frames and chapter family budget. Lists
are unique, normalized and opaque. A policy cannot declare a hard-coded core
category. The business-tech pack may provide its first tokens; a future legal
pack changes policy only, never the catalog renderer/compiler.

## Catalog receipt and tests

Catalog compilation emits an ordered receipt dependency graph:

```text
policy snapshot -> ingestion package -> asset record -> catalog ->
duplicate decision -> reuse plan -> receipt
```

Every dependency has an ID/hash, no duplicate/self/cyclic edge is allowed.
`SUCCESS` requires all outputs; `FAILURE` has no outputs and one closed error
code. Serialization is compact canonical UTF-8 JSON; BOM, duplicate keys,
floats, noncanonical ordering, extra/missing fields and mutation drift reject.

Required REPLAY tests cover image/video/document/audio records; raw-byte hash
mutation; policy snapshot drift; role/avoid denial; missing probe/fingerprint
evidence; same-source/exact/perceptual/local-feature/range duplicate arms;
family derivation; cooldown/budget denial; source-audio metadata; catalog and
receipt dependency mutation; and a business-tech policy fixture without a
domain-specific core branch.

## Acceptance

1. Every catalog record has exact bytes provenance, semantic metadata and a
   derived visual family ID.
2. Duplicate and selected-range reuse cannot silently enter the catalog.
3. `avoid` and AssetBrief policy restrictions fail closed.
4. Generic-stock ratio and source-audio eligibility are explicit catalog data.
5. The same core accepts a future legal/timeline asset declaration through a
   different policy snapshot, without a renderer/catalog fork.
6. No live provider, browser, API, queue, UI or Phase 9+ feature is added.

## Normative closed forms and lifecycle corrections

This section is normative and supersedes any earlier ambiguous package,
duplicate, reuse or receipt wording.

### Binary ingress and package projection

`AssetIngestionInputV1` is an in-memory exact-type object with `asset_bytes` as
exact `bytes`; it is never JSON serialized. The compiler computes:

```text
source_hash = "sha256:" + SHA256(asset_bytes)
source_byte_length = len(asset_bytes)
```

and registers the bytes under an owned opaque materialization handle. A stale,
subclassed, replaced or byte-mutated input rejects. `AssetIngestionPackageV1`
is the serializable projection and has exactly:

```text
schema_version, package_id, package_hash, project_id, sequence_id,
policy_snapshot_id, policy_snapshot_hash, source_hash, source_byte_length,
source_descriptor, media_probe_evidence, fingerprint_evidence,
semantic_declaration, selected_ranges, source_audio_eligibility
```

It does not contain raw bytes. Its package hash covers all fields except
`package_id/package_hash`; load/replay receives both canonical package bytes and
the separately materialized exact bytes, then rederives `source_hash` and byte
length before every other check. Compact canonical UTF-8 JSON is therefore
unambiguous and binary content cannot be injected through a JSON string.

`MediaProbeEvidenceV1` has exactly `probe_id, probe_hash, fixture_id,
fixture_hash, source_hash, media_type, duration_ms, width, height,
fps_numerator, fps_denominator, codec, has_audio`. `fixture_id/hash` identify a
checked-in REPLAY probe fixture; its hash is SHA-256 of the canonical facts
projection. The probe hash covers every field except its own ID/hash and must
equal a resolver-provided trusted fixture with the same source hash and facts.
No caller-provided probe is trusted merely because it has a matching shape.

`SemanticDeclarationV1` has exactly `subjects, actions, setting, mood,
semantic_tags, avoid_contexts, domain_roles, domain_sensitivity_tags`. Each
array is an ordered unique normalized opaque token tuple; `setting/mood` are
normalized token or null. All fields enter AssetRecord identity. The source
audio object has exactly `status, reason_tokens, evidence_ids,
policy_snapshot_id, policy_snapshot_hash`; status is the closed enum above,
lists are ordered unique normalized IDs/tokens, and every evidence ID must be
a package/probe/fingerprint identity declared by this compilation.

`SourceDescriptorV1` has exactly `descriptor_id, descriptor_hash, provider_id,
source_uri, license_mode, allowed_uses, origin_kind, attribution`. The
descriptor hash covers every field except its own ID/hash. `provider_id`,
`license_mode`, every allowed-use token and `origin_kind` are normalized opaque
tokens; `origin_kind` is exactly `local_replay` in this phase. `source_uri` is
a non-empty opaque URI/URN string and `attribution` is a normalized string or
null. `allowed_uses` is an ordered unique token list. License text, a local
path and an unbounded provider response are never accepted in this object.

`FingerprintEvidenceV1` has exactly `evidence_id, evidence_hash, source_hash,
perceptual_frame_hashes, local_feature_hashes, same_source_key`. Its hash
covers every field except its own ID/hash. `same_source_key` is the lower-case
`sha256:` projection of the canonical tuple `(provider_id, source_uri,
origin_kind)` from the package's `SourceDescriptorV1`; it is not a
caller-controlled provider key and it must not equal the `source_hash` merely
by declaration. Thus `same_source` can detect differently materialized bytes
from the same declared origin, while `exact_bytes` compares raw `source_hash`
only. Each fingerprint list is an ordered unique lower-case
`sha256:<64-hex>` token list. Image/video records require at least one
perceptual-frame or local-feature token; document/audio records must declare
both lists empty. The evidence resolver accepts only the checked-in REPLAY
fixture whose identity, hash, source hash, descriptor projection and same-source
key all match the package.

`SelectedRangeV1` has exactly `range_id, range_hash, source_hash, timebase,
start_inclusive, end_exclusive`. Its hash covers every field except its own
ID/hash. `timebase` is exactly `media_ms_v1`, both bounds are non-negative
integers and `end_exclusive` is strictly greater than `start_inclusive`.
Ranges are allowed only for `video` and `audio`, must be within the trusted
probe duration and are sorted by `(start_inclusive, end_exclusive, range_id)`
without overlap within a record. Image/document records require an empty range
list. A selected-range duplicate requires the same raw `source_hash`, identical
`timebase`, and an interval intersection; no heuristic or unknown timebase may
produce a pass.

`AssetRecordV1` has exactly the fields listed in the canonical-output table
above, with `asset_id`, `asset_hash`, `source_descriptor`, `media_facts`,
`fingerprint_evidence`, `source_audio_eligibility` and the optional
duplicate-of pair represented by their complete closed forms. Its asset hash
covers every field except `asset_id/asset_hash`. `asset_id` derives from that
projection; neither a caller-supplied ID nor a source URL is an identity
substitute. In Phase 8 the duplicate-of pair is always null; a non-null value
requires a later schema-versioned migration and is rejected here.

`AssetBriefV1` has exactly `brief_id, brief_hash, editorial_role, subject,
action, setting, avoid_contexts, preferred_asset_type_tokens,
policy_snapshot_id, policy_snapshot_hash, resolved_visual_policy_hash`.
Its hash covers every field except its own ID/hash. `subject/action/setting`
are normalized token or null; its token lists are ordered and unique. A brief
without an exact policy triple or whose non-null role/avoid/type token is not
allowed by that policy is invalid.

### Policy token surface

`AssetCatalogPolicyV1` has exactly `policy_id, policy_hash, version,
allowed_asset_brief_roles, allowed_preferred_type_tokens,
allowed_avoid_context_tokens, allowed_domain_role_tokens,
allowed_domain_sensitivity_tokens, source_audio_reason_tokens,
generic_stock_provider_tokens, reuse_cooldown_frames,
chapter_family_budget`. Its hash covers every field except `policy_id` and
`policy_hash`; the resolved policy snapshot must include this exact hash.
`reuse_cooldown_frames` and `chapter_family_budget` are non-negative integers.
The policy object requires unique normalized lists:

```text
allowed_asset_brief_roles, allowed_preferred_type_tokens,
allowed_avoid_context_tokens, allowed_domain_role_tokens,
allowed_domain_sensitivity_tokens, source_audio_reason_tokens,
generic_stock_provider_tokens
```

The compiler validates every corresponding semantic declaration and brief field
against these lists. This is the sole Domain Pack authority for such tokens.

### Duplicate lifecycle

`DuplicateDecisionV1` has exactly `decision_id, decision_hash,
candidate_package_id, candidate_package_hash, candidate_source_hash,
decision_kind, matched_asset_id, matched_asset_hash, matched_source_hash,
matched_fingerprint_ids, overlapping_selected_ranges`. `decision_kind` is the
closed enum already listed. `distinct` requires every matched field to be null
or empty; every other kind requires one existing immutable catalog record and
the precise compared evidence. `AssetRecordV1` has nullable
`duplicate_of_asset_id/duplicate_of_asset_hash`, reserved for a later explicit
migration; Phase 8 writes the pair only as null. Blocked duplicate candidates
do not become catalog records.

The decision kind is selected by this fixed precedence, which is part of the
decision hash: `selected_range_overlap` (same raw source and intersecting
declared ranges), then `exact_bytes` (same raw source hash), then
`same_source` (same canonical origin key but different source hash), then
`perceptual_match`, then `local_feature_match`, otherwise `distinct`. A
candidate with no declared selected ranges cannot receive the first outcome.
This makes every duplicate arm independently testable while never allowing an
earlier broad match to hide a selected-range reuse.

The compiler receives an existing immutable `AssetCatalogV1`, evaluates the
candidate before insertion, then returns `AssetCatalogMutationV1`:

```text
candidate package -> duplicate decision -> accepted record or blocked result ->
new catalog -> reuse analysis -> generic-stock ratio -> receipt
```

`AssetCatalogV1` is ordered by asset ID, has no duplicate source hash or asset
ID, and records every blocked candidate decision separately. Selected-range
overlap compares only records with identical source hash and the same media
timebase; unknown timebase never silently passes a range comparison.

`AssetCatalogV1` has exactly `catalog_id, catalog_hash, project_id,
policy_snapshot_id, policy_snapshot_hash, records, blocked_decisions`. Its
catalog hash covers every field except its own ID/hash. Records are sorted by
asset ID and blocked decisions by decision ID. `AssetCatalogMutationV1` has
exactly `mutation_id, mutation_hash, input_catalog_id, input_catalog_hash,
candidate_package_id, candidate_package_hash, duplicate_decision,
result_kind, accepted_asset_record, output_catalog_id, output_catalog_hash`.
`result_kind` is closed: `accepted|blocked_duplicate`. It has an accepted
record only for `accepted`, and that record must appear exactly once in the
output catalog; a blocked decision must appear exactly once in its output
catalog and has no accepted record. A valid `blocked_duplicate` is an explicit
successful decision, not a silent fallback: its output catalog is the input
records plus the new immutable blocked-decision log entry. Mutation hash covers
every field except its own ID/hash.

### Bounded reuse and generic-stock analysis

Phase 8 does not select an EDL asset. It may validate a caller-supplied,
REPLAY-only `AssetReuseContextV1` with exactly `context_id, context_hash,
catalog_id, catalog_hash, chapter_id, frame_rate, instances[]`; each instance
has `asset_id, asset_hash, visual_family_id, sequence_id, start_frame,
end_exclusive_frame, ordinal`. This context is an analysis input, not an EDL
mutation. `AssetReusePlanV1` contains its identity,
the context identity, policy identity, ordered violations, family counts and
the computed generic-stock ratio. Cooldown compares adjacent same-family
instances in this context’s rational frame grid; budget compares each family’s
instance count against the policy’s chapter budget. Absent context yields an
explicit `not_evaluated` reuse plan, never a passing plan.

`GenericStockRatioV1` has `ratio_id, ratio_hash, catalog_id, catalog_hash,
provider_token_set_hash, status, numerator, denominator, numerator_asset_ids`.
`status` is closed: `available|unavailable_empty_catalog`. The
numerator is the ordered unique catalog asset IDs whose provider token occurs
in `generic_stock_provider_tokens`; denominator is the catalog record count.
Zero denominator is permitted only with `status=unavailable_empty_catalog` and
an explicit `0/0` state, not a float or a quiet zero. This aggregate and the
reuse plan are receipt dependencies.

`AssetReuseContextV1` hash covers all listed fields except its ID/hash pair and
must reference the exact provisional output catalog that is being considered
for publication. Before cooldown/budget analysis, every instance must resolve
to exactly one record in that catalog with equal `asset_id`, `asset_hash` and
derived `visual_family_id`; missing, unknown or mismatched instances reject.
`frame_rate` is an exact reduced rational `numerator/denominator`, each frame
bound is a non-negative integer, and `end_exclusive_frame` must be greater than
`start_frame`. Instances are sorted by `(ordinal, sequence_id, start_frame,
asset_id)` and ordinals are unique. `AssetReusePlanV1` has exactly `plan_id, plan_hash, status,
context_id, context_hash, policy_id, policy_hash, family_counts, violations,
generic_stock_ratio_id, generic_stock_ratio_hash`. Status is closed:
`evaluated|not_evaluated`; the latter requires null context IDs and empty
counts/violations. Violations are closed records containing a violation ID,
kind (`cooldown|chapter_family_budget`), family ID, involved instance ordinals,
observed value and policy limit. An evaluated plan never reports success when
there is a violation. A `not_evaluated` plan is valid only for an
`ingestion_only` outcome: it cannot publish a catalog as reuse-gate-passed and
its receipt must include `reuse_gate_status=not_evaluated`. An evaluated,
violation-free plan is required for `reuse_gate_status=passed` publication;
any violation produces the atomic `reuse_denied` failure described below.

`GenericStockRatioV1` additionally derives its `ratio_hash` from every listed
field except `ratio_id/ratio_hash`; `provider_token_set_hash` is the SHA-256
projection of the resolved policy's ordered provider-token list. Its
`numerator_asset_ids` is sorted by asset ID and has length exactly equal to its
numerator. For `available`, denominator is positive and numerator is in
`[0, denominator]`; for `unavailable_empty_catalog`, denominator and numerator
are both zero and the asset-ID list is empty.

`CatalogReceiptV1` has exactly `receipt_id, receipt_hash, status, outcome_kind,
reuse_gate_status, error_code, dependency_nodes, dependency_edges`.
`status` is `SUCCESS|FAILURE`; `outcome_kind` is
`ingestion_only|reuse_gate_evaluated`; `reuse_gate_status` is
`not_evaluated|passed|denied`; and error code is null only for `SUCCESS`.
`ingestion_only` requires `not_evaluated`; `reuse_gate_evaluated` requires
`passed` on success or `denied` on a reuse failure. Dependency node records are
`(kind, id, hash)` and edges are `(from_kind, from_id, to_kind, to_id)`, both ordered canonically.
On `FAILURE`, dependency nodes and edges are empty and `error_code` is one of
`invalid_input|materialization_unavailable|untrusted_replay_evidence|
policy_denied|reuse_denied|integrity_mismatch`. A valid duplicate block has a
`SUCCESS` receipt with an explicit blocked mutation instead. A failure does
not publish an output catalog or an accepted record; a reuse violation is
therefore checked against a provisional candidate catalog and atomically
prevents publication.

The final ordered receipt is therefore:

```text
policy snapshot -> materialized ingestion input -> package -> duplicate decision
-> accepted/block result -> catalog mutation -> reuse plan -> generic-stock ratio
-> receipt
```
