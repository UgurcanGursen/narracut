# Phase 7 — Data Visualization and Metric Engine Contract

Status: Candidate specification — implementation is not authorized.

## Boundary

Phase 7 creates evidence-bound declarative visual arguments. Core owns exact
numeric semantics, typed topology, animation, and render receipt verification.
The selected Domain Pack owns allowed, banned and preferred visualizations.
Live data ingress, conversions, asset catalog, geocoding, a new scheduler, UI,
queue/retry and the Phase 9 claim store are out of scope. Legacy V3
`chart_data`, V4 `CHART_REVEAL`, and Phase 5 metric templates are not canonical
Phase 7 artifacts.

## Evidence and exact values

The sole evidence arm is `SourceCaptureEvidenceBindingV1`:

```text
binding_kind = source_capture_region
source_capture_plan_id / source_capture_plan_hash / source_package_hash
region_dom_path / evidence_text
numeric_lexeme / unit_lexeme / period_lexeme
```

Compiler revalidates the Phase 6 capture plan. Only
`accessible|text_found|snapshot_available` with
`no_fallback|snapshot_evidence` is allowed. The region/text must equal the
capture crop manifest. `numeric_lexeme` grammar is
`^-?(0|[1-9][0-9]*)(\.[0-9]{1,12})?$`; its parsed, normalized result must equal
the declared `ExactDecimalV1`. `unit_lexeme` is exact ISO-4217 for currency,
`%` for percent, `ratio` for ratio, or a policy-declared count/custom label.
`period_lexeme` equals the declared period label (or an interval endpoint).
All three lexemes occur exactly once in evidence text. Missing, ambiguous,
semantic-mismatch, text-only/challenge/manual-pending, or forged capture input
rejects. Opaque references are forbidden until a future explicit Phase 9 arm.

`ExactDecimalV1` is the only number: signed integer `coefficient`, integer
`scale` 0..12, value = coefficient × 10^-scale. Zero is `(0,0)` and nonzero
coefficient has no trailing zero. Float, numeric strings, NaN, Infinity,
rounding and implicit conversion reject. Unit is
`currency|percent|count|ratio|custom`; currency is uppercase ISO-4217 or null.
Every series has one unit/currency pair; comparison requires an identical pair.

`PeriodV1` has unique `period_id`, contiguous 1-based `ordinal`, `label`, and
`kind=instant|interval`; intervals carry exact start/end labels. Expected value
hashes cover decimal, unit/currency, period and all evidence bindings.

## Artifact field matrix

`VisualizationArtifactV1` is an immutable container with identity, title,
editorial role, policy snapshot, source captions, and ordered `items[]`. Every
item has `item_id,kind,label,source_caption_id`; its closed payload is:

| Kind | Exact payload |
|---|---|
| `chart` | `chart_kind` = `line|bar|area|stacked|comparison|waterfall|timeline`, plus ordered series (`series_id,label,unit,currency,datapoints[]`) and points (`point_id,ExactDecimalV1,PeriodV1,evidence[]`) |
| `metric` | `metric_id,chart_context_id,ExactDecimalV1,unit,currency,PeriodV1,evidence[]`; context is an existing same-container chart item |
| `timeline` | evidence-bound nodes (`node_id,label,ExactDecimalV1,unit,currency,PeriodV1,evidence[]`) and ordered chronological edges (`edge_id,from_node_id,to_node_id,ordinal,label|null`) |
| `relationship_graph` | evidence-bound nodes and ordered `edge_id,kind,from_node_id,to_node_id,ordinal,label|null` edges; kind is policy token |
| `evidence_chain` | evidence-bound nodes and ordered edges of kind `supports|qualifies|contradicts` |
| `map` | coordinate-free evidence-bound topology and edges of kind `adjacent|contains|flows_to`; no lat/long, geocoder or tile |

All IDs are unique, edges reference existing nodes, all matrix fields enter the
canonical projection, and self-edge/cycle rejects absent explicit policy.
`SourceCaptionV1` carries capture IDs/hashes, source label, date and region;
it is mandatory for each item and visibly rendered. Metrics cannot become an
independent slide because they share this container and a chart context.

## Animation and renderer integration

Stages are only `axis_reveal|label_reveal|line_draw|bar_grow|value_callout|
before_after|series_focus|metric_count|equation_morph`. Each has a stable ID,
existing targets and exact WordToFrame word/frame span. Manual timing is
forbidden. The stage span is contained in its exact V4 event interval; stages
are ordered and non-overlapping per target/span. One chart supports three
distinct point/series focus stages.

`VisualizationFrameBindingV1` explicitly maps global WordToFrame coordinates
to sequence-local V4 coordinates. It carries start/end word IDs, WordToFrame
and Video EDL IDs and hashes, `sequence_start_frame`, global word start/end
frames, and local render start/end frames. The only legal conversion is
`local = global - VideoEdlArtifact.sequence_start_frame`; local endpoints must
be nonnegative and contained in the bound V4 interval. Compiler rederives every
local value from exact upstream artifacts; manual offsets and other timebases
are forbidden. This complete binding is inside the render-plan hash projection.

`VisualizationEdlBindingV1` binds an existing V4 event ID/hash/interval/track
and `CHART_REVEAL` directive ID/hash without rescheduling Phase 3. The existing
Phase 4 `sequence-preview-v1` and immutable RenderProps are not changed.
Instead Phase 7 owns additive `visualization-replay-v1` Remotion composition
and strict Python/Node parser. The Node ingress accepts only a closed
`VISUALIZATION-REPLAY-PROPS-V1` projection derived from verified Python
artifact/plan/metadata values; it does not alter or replace Phase 4
RenderProps. The REPLAY compiler renders deterministic SVG evidence for a
requested V4-local frame and receipt. It makes no claim of automatic injection
into Phase 4 preview.

## Domain policy

Exactly one policy is resolved at
`resolved_policy.policy_bundles[].policy.visual.visualization_policy`:

```text
policy_version = VISUALIZATION-POLICY-V1
allowed_kinds / allowed_chart_kinds / banned_chart_kinds
preferred_chart_kinds / required_evidence_binding_kinds / theme_id
```

Lists are unique enum values; allowed/banned are disjoint and preferred is a
subset of allowed. Missing/duplicate policy, banned or unsupported kind rejects.
Core and renderer contain no domain-name branch.

Policy additionally has `count_unit_labels`, `custom_unit_labels`, and
`allowed_relationship_edge_kinds`: unique nonempty labels/tokens. Count/custom
lexemes must be in the corresponding list; relationship edges must be in the
last list. Evidence-chain and map retain their fixed closed edge enums.

The normative topology matrix is `TopologyNodeV1 = node_id,label,evidence[]`
with nodes sorted by ID and `TopologyEdgeV1 = edge_id,edge_kind,from_node_id,
to_node_id,ordinal,label`, where label is null or normalized string and edges
have contiguous 1-based order. Relationship graph uses allowed policy tokens;
evidence chain uses `supports|qualifies|contradicts`; map uses
`adjacent|contains|flows_to`. All node/edge fields and evidence enter artifact
identity projection.

## Metadata, receipt and tests

Rendered metadata is canonical and hash-bound, not a self-reported flag. It
contains artifact/plan IDs and hashes, V4 event/directive IDs and hashes,
ordered rendered elements (ID, exact value projection, label), stage IDs,
source-caption IDs, rendered values/SVG hashes and frame geometry. Compiler
rederives it from artifact+plan and rejects any difference.

Receipt has `receipt_id/hash`, `artifact_type=visualization_render_receipt`,
ordered dependency IDs+hashes (artifact, plan, WordToFrame, RenderProps,
metadata, SVG), and a closed success/failure union. Duplicate/self/cyclic or
untyped dependencies reject.

`SourceCaptionCollectionV1` has a collection ID/hash and captions sorted by
`source_caption_id`, derived from item ID plus exact capture binding, label,
date and region. Each item references one caption. Receipt dependency order is
fixed: visualization artifact, render plan, WordToFrame, Video EDL, RenderProps,
caption collection, metadata, SVG artifact. `SUCCESS` requires all dependencies
and output IDs/hashes non-null with null rejection code; `FAILURE` requires
null outputs and one non-null stable rejection code. Duplicate, self or cyclic
dependency, or any other nullability state rejects.

REPLAY tests require a byte hash of the actual isolated `visualization-replay-v1`
selected-frame PNG output, stage start/mid/end distinct SVG or PNG evidence,
visible source-caption oracle, and mutation tests for value/unit/period/evidence
event/stage/metadata/receipt. Input echo is insufficient.

## Acceptance

1. Word-frame binding; no manual timing.
2. Exact rendered values/series/source caption through metadata and SVG receipt.
3. Three distinct chart focus stages.
4. Metric/chart share artifact/context/evidence.
5. Revenue chart and future legal timeline use the same core; policy changes
   permissions/preferences without renderer fork.
6. Bad type/unit/decimal/evidence/capture/metadata/receipt/stage rejects.
7. Fixtures cover line, bar, area, stacked, comparison, waterfall,
   chart-timeline, metric, standalone timeline, graph, evidence-chain and map.
