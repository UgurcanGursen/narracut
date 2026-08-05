# Phase 9 — Manual LLM Gateway, Research Engine and Claim Store Contract

## Status and boundary

This is the bounded Phase 9 implementation contract. It implements a
local-first, `REPLAY`/`MANUAL_UI` research boundary. It does not invoke a
commercial API, drive a ChatGPT/Claude/Gemini browser session, open a URL,
perform network discovery, implement a planner, select an EDL asset, or add a
Studio UI. `LOCAL_MODEL` and `API` are typed unavailable interfaces only.

The core is domain-neutral. Prompt text, claim-status tokens, source policy and
safe wording rules are loaded from the selected Domain Pack; no business-tech
prompt is embedded in the gateway.

## Task and package model

`LLMTaskV1` is an immutable task revision and has exactly:

```text
task_id, task_hash, logical_task_id, supersedes_task_id, task_type, project_id, input_manifest,
prompt_template_ref, context_artifacts, expected_output_schema,
backend_mode, status, attempt, parent_task_id, created_at, completed_at
```

`backend_mode` is the closed enum `replay|manual_ui|local_model|api`; only
`replay` and `manual_ui` are executable in Phase 9. `status` is
`created|package_ready|response_submitted|accepted|rejected|superseded`.
`task_type` is `source_discovery|source_extraction|claim_normalization|repair`.
IDs and hashes are deterministic canonical projections. The task hash covers
all fields except its own ID/hash, including the domain profile/policy snapshot
references in `input_manifest`; timestamps are supplied by the caller and are
therefore part of identity. A status/attempt/completion transition creates a
new revision with the same `logical_task_id` and `supersedes_task_id` equal to
the previous revision's `task_id`; it never mutates a hash-bound task. Repair
uses `parent_task_id` for the rejected task and is distinct from lifecycle
supersession. A response binds one exact immutable `task_id/task_hash`; a
later revision cannot reinterpret it.

`TaskPackageBuilder` writes only this exact tree under an explicitly supplied
workspace root:

```text
llm_tasks/<task_id>/
  README.md
  prompt.md
  input_manifest.json
  topic_or_scope.json
  domain_profile.json
  resolved_domain_policies.json
  relevant_sources.json
  relevant_claims.json
  expected_output.schema.json
  response/
```

Every JSON file is canonical UTF-8 JSON with no duplicate keys, floats or
unknown top-level fields. `input_manifest.json` has exactly `schema_version,
task_id,task_hash,logical_task_id,project_id,task_type,backend_mode,
policy_snapshot_id,policy_snapshot_hash,prompt_template_ref,prompt_hash,
readme_hash,context_artifact_refs,expected_output_schema_hash`. `topic_or_scope.json` has
exactly `topic,scope_tokens`; `domain_profile.json` and
`resolved_domain_policies.json` are the exact already-validated Domain Pack
objects; `relevant_sources.json` and `relevant_claims.json` are ordered lists
of closed persisted-record projections. `expected_output.schema.json` is the
versioned task-type schema below. `README.md`/`prompt.md` are UTF-8 and their
SHA-256 values are in the manifest. `prompt_template_ref` is a relative
Domain Pack prompt path and the resolved prompt bytes/hash are in the input
manifest. The builder rejects path traversal and never creates a package above
the supplied root. `MANUAL_UI` creates a package only; it never opens or
automates a browser. `REPLAY` resolves a checked-in response fixture by task
hash only.

## Response forms and validation

Each response is one canonical JSON object with exactly:

```text
schema_version, task_id, task_hash, task_type, policy_snapshot_id,
policy_snapshot_hash, result
```

The outer references must equal the pending task. Unknown fields, duplicate
JSON keys, floats, non-canonical bytes, mismatched task/policy identities and
cross-task responses reject. A response never overwrites a prior accepted
response; it is recorded as an attempt with an immutable content hash.

Discovery `result` has exactly `candidates`; candidates are ordered by
`canonical_url,candidate_id`. A candidate has exactly
`candidate_id,candidate_hash,canonical_url,source_type,source_label,
publication_date,authority_tokens,rationale_tokens`; its hash covers all
except ID/hash. A candidate has a
canonical `http`/`https` URL, source label, publication date, closed Phase 6
source type, authority tokens and a non-empty rationale. Duplicate URLs are
merged deterministically. Phase 9 does not claim a URL is reachable. A
deterministic `SourceCaptureIngress` may bind an accepted candidate to a
caller-supplied Phase 6 `ReplaySourcePackage` and its newly derived
`SourceCapturePlan`. It re-runs the closed Phase 6 adapter, requires equal
canonical URL and source type, and persists exact `document_text` and raw
SHA-256 only for accessible text/snapshot evidence. Thus a new topic advances
through a checked-in/manual REPLAY capture fixture without network/browser
action. An unbound candidate cannot enter extraction.

Extraction `result` has exactly `facts,quotes,numbers,uncertainties`; each
item has exactly `local_id,source_id,source_content_hash,source_span,text,
kind,tokens` (number additionally has `value,unit`; quote additionally has
`speaker`). Results bind every fact, number, quote and uncertainty to one
existing captured source and an exact half-open `source_span` within that source's
captured text. The importer rejects an absent source, out-of-bounds span,
quote text that differs from the captured span, invalid numbers/units, and
facts without provenance.

Claim-normalization `result` has exactly `claims`; each proposal has exactly
`canonical_text,claim_type,status,confidence_millionths,fact_local_ids,
contradicting_fact_local_ids,time_start,time_end,visual_potential_tokens,
safe_wording_tokens`. It may only reference imported facts and existing source
IDs. The deterministic `ClaimStore` supplies claim IDs. The model never
supplies a stable ID. Claim status, taxonomy, safety wording and allowed
source/authority tokens are Domain Pack policy inputs.

## Persistent store and lineage

`ClaimStore` is SQLite with append-only JSONL export. It persists immutable
task records, response attempts, sources, facts, claims, claim/source edges,
contradictions and chronology entries. Each persisted record has a stable ID,
canonical content hash, project ID, policy snapshot identity and parent task or
source lineage. A later write may supersede a record but cannot mutate its
previous bytes/hash.

Closed forms are:

```text
SourceRecordV1: source_id,source_hash,project_id,policy_snapshot_id,
policy_snapshot_hash,candidate_id,source_capture_plan_id,
source_capture_plan_hash,source_package_hash,canonical_url,source_type,
source_label,publication_date,content_hash,captured_text
FactRecordV1: fact_id,fact_hash,project_id,policy_snapshot_id,
policy_snapshot_hash,source_id,source_hash,task_id,task_hash,kind,text,
span_start,span_end,number_value,number_unit,speaker,tokens
ClaimRecordV1: claim_id,claim_hash,project_id,policy_snapshot_id,
policy_snapshot_hash,task_id,task_hash,canonical_text,claim_type,status,
confidence_millionths,fact_ids,contradicting_fact_ids,time_start,time_end,
visual_potential_tokens,safe_wording_tokens
```

Every hash covers every field except its own ID/hash. Edges, contradiction and
chronology records are exact forms:

```text
ClaimSourceEdgeV1: edge_id,edge_hash,project_id,policy_snapshot_id,
policy_snapshot_hash,claim_id,claim_hash,source_id,source_hash,fact_id,
fact_hash,relation
ContradictionRecordV1: contradiction_id,contradiction_hash,project_id,
policy_snapshot_id,policy_snapshot_hash,claim_id,claim_hash,
contradicting_claim_id,contradicting_claim_hash,kind,visible_wording_tokens
ChronologyRecordV1: chronology_id,chronology_hash,project_id,
policy_snapshot_id,policy_snapshot_hash,claim_id,claim_hash,date_value,
date_precision,ordinal,unknown_date
```

`relation` is `supports|contradicts`; contradiction `kind` and chronology
`date_precision`/wording tokens come from the selected Domain Pack policy.
Known chronology entries sort by `date_value,claim_id`; unknown-date entries
sort separately by `claim_id` and have null `date_value`. Every foreign
`*_id/*_hash` pair must equal one immutable SQLite record. Serializer/loaders
use canonical UTF-8 JSON, reject duplicate keys, non-canonical bytes, unknown
fields and identity drift, re-check every foreign binding, and export each
record kind to deterministic ID-sorted JSONL.

The source record references a Phase 6 `SourceCapturePlan`; candidate discovery
alone is not sufficient evidence. `SourceRanker` uses the resolved
`SourcePriorityPolicy` and has no domain switch. `ContradictionDetector` only
marks incompatible normalized claim values or statuses visible; it does not
resolve truth. `ChronologyBuilder` sorts explicit ISO dates and records items
with unknown dates separately rather than inventing an order.

## Repair flow

For a rejected response, `RepairTaskBuilder` emits a child `repair` task with:

```text
original_response.json
validation_errors.json
repair_prompt.md
expected_output.schema.json
```

The repair task retains the parent task/policy/context identities and lists
only deterministic validation errors. It does not broaden context, silently
repair an LLM result or accept a partial result.

## Acceptance scenarios

1. A business-tech `MANUAL_UI` discovery package is produced from a selected
   profile/policy snapshot without API keys or browser automation.
2. A checked-in `REPLAY` discovery response imports only canonical valid URLs,
   merges duplicates and obeys the Domain Pack source priority policy; a new
   candidate reaches extraction only through an equal Phase 6 REPLAY capture
   and captured-text binding.
3. Extraction rejects a fabricated source, invalid span, quote/span mismatch
   and unknown policy snapshot; valid facts/quotes/numbers persist with lineage.
4. Claim normalization produces store-owned stable IDs, preserves support and
   contradiction links, and rejects unknown facts/sources/statuses.
5. Contradiction and chronology views are deterministic and do not fabricate
   ordering or truth.
6. Rejected responses create a scoped repair package; accepted response,
   immutable task revision/supersession lineage and JSONL replay remain
   hash-verifiable.
7. A second example Domain Pack fixture can produce the same task package
   contract without a core source/claim/prompt branch.
