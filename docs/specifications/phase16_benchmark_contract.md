# Phase 16 Deterministic Benchmark Contract

## Inputs

One report consumes canonical, already materialized Phase 10 sequence-plan
records, Phase 3 video/audio EDL artifacts and a resolved immutable
`DomainPolicySnapshot`. It optionally consumes a prior canonical report and a
manually curated reference profile. It never reads a video file or downloads a
reference.

## Closed measurements

The reducer produces integer counts and rational rates for: sequence/chapter
structure, duration, edit-event density, evidence/claim density, template
capability distribution, asset-brief distribution, static-duration proxy,
audio-track/event distribution and boundary-policy distribution.

`source_treatment_distribution`, `stock_ratio`, `chart_ratio`, `quote_card_ratio`,
`kinetic_text_density`, actual source-audio usage and external-reference
measurements must be represented as `UNAVAILABLE` unless a canonical input
proves them. An unavailable value cannot produce a positive quality delta.

## Identity and comparison

The report binds project, domain id, pack version, policy snapshot, input
artifact IDs/hashes and metric-schema version. Candidate, prior and reference
profiles must have the same domain tuple; cross-domain comparison fails closed.
The delta reducer reports numeric difference only, never an overall subjective
winner. Reference profiles may contain editorial composition ranges but no
brand, author, image, transcript or source-media identity.

## Terminal outcomes

- malformed or forged input: no report;
- domain/policy mismatch: `BENCHMARK_DOMAIN_MISMATCH`;
- missing required composition input: `BENCHMARK_INPUT_UNAVAILABLE`;
- unavailable non-derived measurement: canonical `UNAVAILABLE` value;
- valid derived report: canonical bytes and deterministic deltas.

No external-media ingestion, UI production label, provider, transport,
renderer, queue/retry or Phase 17 behavior is included.
