# Phase 10 — Hierarchical Story, Narrative and Editorial Planner Contract

## Status, purpose and boundary

This is the frozen candidate contract for Phase 10.  It is a bounded,
`REPLAY`/`MANUAL_UI`-first planning layer over the accepted Phase 9 research
store.  It is not an authorization to implement a provider API, browser bot,
Studio UI, queue, final renderer, or a new domain pack.

The planner turns immutable approved claims into a hierarchy:

```text
global outline -> chapter brief -> narrative beats -> sequence plan ->
deterministic assembly request
```

The LLM never writes a final Workspace, EDL, asset URL, concrete asset ID,
frame number, track assignment, or renderer input.  It proposes bounded
planner artifacts only.  Core code owns IDs, hashes, ordering, validation and
assembly.  Existing `chapter.schema.json`, `beat.schema.json` and
`sequence.schema.json` remain unchanged during Phase 10A–E.

## Dependencies and source of truth

- Phase 9 `ClaimStore` is the only accepted claim/source/chronology ingress.
- Phase 8 catalog supplies a read-only set of eligible asset families; a plan
  may request an `AssetBrief`, never select an asset.
- Phase 5 registry supplies read-only template capabilities and policy; a
  plan may express a preferred capability, never build `TemplateRenderPlan`.
- Phase 3 remains the sole owner of concrete cues, track allocation and EDL
  compilation.  Phase 10 creates an assembly request for it, not an EDL.
- The immutable selected Domain Pack profile and policy snapshot bind every
  task and artifact.  A changed pack/profile requires an explicit migration;
  it never rewrites an existing plan.

## Domain Pack planner policy

The selected pack must resolve one typed `planner_policy` from a policy bundle:

```text
policy_version
allowed_core_beat_kinds
allowed_domain_beat_subtypes
allowed_editorial_roles
allowed_visual_role_tokens
allowed_safe_wording_tokens
min_sequence_duration_seconds
max_sequence_duration_seconds
max_claims_per_sequence
max_asset_briefs_per_sequence
min_edit_events_per_sequence
max_edit_events_per_sequence
```

The core kinds are closed and domain-neutral:

```text
hook context promise rise reveal contradiction mechanism example consequence
counterargument payoff chapter_reset final_question reconstruct_timeline
compare_accounts introduce_entity
```

The resolver rejects an absent, duplicate, malformed or snapshot-mismatched
policy.  There is no `if domain == ...` branch and no silent core default.

## Immutable artifacts

Every record has `schema_version`, stable ID, canonical content hash,
`project_id`, `policy_snapshot_id`, `policy_snapshot_hash`, parent IDs and a
status.  IDs/hashes are assigned by deterministic services, never by an LLM.

```text
GlobalOutlineV1
  outline_id, central_question, hook, chapter_order, major_reveals,
  counterarguments, payoff, final_question

ChapterBriefV1
  chapter_id, outline_id, order, goal, entry_state, exit_state, claim_ids,
  required_evidence_ids, main_reveal, counterpoint, visual_opportunity_tokens,
  continuity_handoff, estimated_duration_seconds

NarrativeBeatV1
  beat_id, chapter_id, order, core_kind, domain_subtype, editorial_role,
  claim_ids, narration_intent, safe_wording_tokens, estimated_duration_seconds

SequencePlanV1
  plan_id, chapter_id, beat_id, order, narration_intent, claim_ids,
  evidence_ids, preferred_template_capability_ids, asset_briefs,
  edit_event_intents, text_emphasis_intents, audio_direction_tokens,
  incoming_continuity_state, outgoing_continuity_state

AssetBriefV1
  brief_id, visual_role, evidence_ids, purpose, preferred_type_tokens,
  avoid_family_ids, fallback_mode

PlannerAssemblyRequestV1
  request_id, ordered_sequence_plan_ids, continuity_manifest_hash,
  source_claim_store_hash, asset_catalog_hash, template_capability_hash
```

`AssetBriefV1` uses only Phase 8 policy-approved role/type tokens and an
explicit fallback mode.  `fallback_mode` is `fail_closed` or
`require_review`; generic stock is never implicit.  An evidence-bearing brief
must reference existing source/claim evidence.

## Gateway and task packages

Phase 10 adds a versioned planner task family alongside, not by mutating, the
closed Phase 9 research task enum:

```text
PHASE10-PLANNER-TASK-V1
outline | chapter_brief | narrative_beats | sequence_plan | repair
```

The implementation must reuse Phase 9 canonical package, backend, response
binding, immutable revision and scoped-repair mechanics through an adapter;
it must not duplicate provider/browser code.  Each task includes only the
minimum context: its parent artifact, relevant persisted claims/evidence, the
two prior continuity states, denied asset families, template capabilities and
the resolved Domain Pack policy.  Full project history is forbidden.

`REPLAY` and `MANUAL_UI` are executable; `LOCAL_MODEL` and `API` remain typed
unavailable in this phase.  A response is accepted only after exact schema,
task, policy, parent, claim/evidence and capability validation.  Failure
produces a repair package scoped to deterministic validation errors.

## Validation and deterministic assembly

Local validators must reject: unknown or cross-project claim/evidence IDs;
unsupported beat/template/visual tokens; duration outside policy bounds;
missing evidence for an evidence role; generic-stock fallback; duplicate or
non-contiguous order; insufficient/excess edit-event intents; and broken
continuity handoff.

The assembler sorts accepted `SequencePlanV1` records by the explicit outline,
chapter, beat and sequence order; checks immutable dependency hashes and emits
only `PlannerAssemblyRequestV1`.  Translation of that request into existing
V3 Chapter/Beat/Sequence/EDL artifacts is a separately typed, fail-closed
adapter and must not be introduced until its input/output contract is audited.

## Acceptance gates

1. A business-tech and contract-only dummy-pack fixture produce the same task
   package structure without a core domain branch.
2. An outline, one chapter, beats and one 30–90 second sequence plan complete
   through `MANUAL_UI`/`REPLAY` without API credentials or browser automation.
3. A malformed response repairs only the affected artifact; an unrelated
   approved sequence remains byte-identical.
4. Unknown/cross-project claims, unsupported policy tokens, invalid duration,
   implicit generic stock and invalid continuity all fail closed.
5. Planner context excludes unrelated history and is hash-verifiable.
6. Deterministic assembly is stable across two identical replays and does not
   create a concrete EDL or renderer input.

## Implementation order

1. Independently audit this contract; resolve blockers without implementing.
2. Add typed planner policy and a contract-only dummy fixture; regenerate
   affected Domain Pack snapshots.
3. Add planner artifact schemas/models/store and focused replay tests.
4. Add the Phase 9 gateway adapter and validator/repair tests.
5. Add deterministic assembly request only; defer V3/EDL translation to a
   separately audited compatibility contract.
