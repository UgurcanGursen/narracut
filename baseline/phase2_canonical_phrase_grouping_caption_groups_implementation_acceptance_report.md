# Phase 2 Canonical Phrase Grouping and Caption Groups Implementation Acceptance

Date: 2026-08-04

## Decision

```text
IMPLEMENTATION_ACCEPTANCE_DECISION=ACCEPT
IMPLEMENTATION_ACCEPTED=YES
IMPLEMENTATION_STATUS=CLOSED
IMPLEMENTATION_REMOTE_CLOSED=YES
NEXT_ACTION=POST_CAPTION_GROUPS_SCOPE_RECONCILIATION
NEXT_IMPLEMENTATION_ALLOWED=NO
PHASE2_CLOSED=NO
TOTAL_PHASE2_SLICE_COUNT=UNKNOWN
PHASE2_COMPLETION_PERCENTAGE=NOT_STATED
```

The bounded Canonical Phrase Grouping and Caption Groups implementation is
accepted. This accepts only the pure in-memory deterministic contract and its
exact additive public surface. It does not accept filesystem publication,
emphasis, frame mapping, presentation/layout, renderer integration, provider
execution, an alignment report, or Phase 2 overall.

## Accepted identities

```text
ACCEPTED_SPECIFICATION=docs/specifications/phase2_canonical_phrase_grouping_caption_groups_contract.md
SPECIFICATION_SHA256=c0e8925e598bac0414c1c7b96adf256ed0f4072d2196efedf3b90b0961859baf
SPECIFICATION_UTF8_BYTES=43985
IMPLEMENTATION_AUTHORIZATION_COMMIT=d54fcb0bf37bdffaeee6d0d4bc6b64520bffcb75
ORIGINAL_IMPLEMENTATION_COMMIT=d8c600c6851cb26728e6dab1485e6447cd8c3c0b
AUDIT_REPAIR_COMMIT=8b77c4d5bbd6f176d11a92f6a491a707e7b47ac6
FINAL_REMOTE_HEAD=8b77c4d5bbd6f176d11a92f6a491a707e7b47ac6
```

The original implementation changed exactly the four authorized paths:

```text
engine/contracts/caption_groups.py
engine/contracts/__init__.py
tests/test_caption_groups.py
tests/test_alignment_request.py
```

The bounded audit repair changed exactly:

```text
engine/contracts/caption_groups.py
tests/test_caption_groups.py
```

No specification, schema, roadmap, upstream contract, provider, runtime,
renderer, UI, or artifact-publication implementation changed in either code
commit.

## Audit chain

The first independent read-only implementation audit returned `FIX_REQUIRED`:

```text
BLOCKER=0
MAJOR=2
MINOR=0
INFO=0
```

- `CGS-IMPL-AUD-001`: canonical non-object JSON roots were classified as
  `NON_CANONICAL_SERIALIZATION` instead of `STRUCTURE_INVALID`.
- `CGS-IMPL-AUD-002`: mandatory oracle coverage was incomplete and group
  golden evidence used production projection helpers without literal expected
  bytes.

Commit `8b77c4d5bbd6f176d11a92f6a491a707e7b47ac6` repaired both findings. The
targeted independent read-only re-audit returned `PASS`:

```text
CGS_IMPL_AUD_001_STATUS=CLOSED
CGS_IMPL_AUD_002_STATUS=CLOSED
NEW_BLOCKING_FINDING_COUNT=0
FINAL_BLOCKER_MAJOR_MINOR_INFO=0/0/0/0
IMPLEMENTATION_ACCEPTANCE_READY=YES
```

The final audit independently confirmed the exact two-path repair boundary,
remote parity, canonical root classification, malformed-wire classification,
literal group golden bytes, all 45 loader-oracle rows, all 10 coverage/timing
rows, all 5 confidence rows, precedence, registry behavior, no-leak/import
scope, grouping properties, and protected-file isolation.

## Verification evidence

Final local and independent gates agreed:

```text
focused caption-groups + export oracle: 1137 passed
seven Phase 2 upstream/contract modules: 1575 passed
top-level non-FastAPI suite: 1855 passed, 1 skipped
```

The full repository collection was attempted and stopped during collection in
two FastAPI-dependent test areas because the active Python environment lacks
`fastapi`. This is an environment/dependency limitation, not a caption-groups
regression. No passing result is claimed for the unexecuted full collection.

Golden evidence:

```text
group 0 projection bytes=650
group 0 envelope bytes=797
group 1 projection bytes=653
group 1 envelope bytes=800
artifact projection bytes=2152
artifact hash=12670fe861389bfe8e25f05a126c7ea355c361c2b2848e9b02a216ed83baaec7
artifact ID=cgs_12670fe861389bfe8e25f05a126c7ea3
artifact envelope bytes=2300
artifact envelope SHA256=fec81a32ef81b7ac4fb785b059d1f713edb90ea91197f72cd8a22992941da942
```

Grouping was independently verified for sentence lengths `1..1000` and legal
partitions `4..24`. The implementation retains the required `O(W + T)`
indexing model and performs no filesystem, network, provider, database,
thread, subprocess, clock, random, UI, renderer, frame, emphasis, or V2 work.

## Accepted public surface

The exact additive surface remains 13 symbols:

```text
CAPTION_GROUP_V1
CAPTION_GROUP_HASH_V1
CAPTION_GROUPS_V1
CAPTION_GROUPS_HASH_V1
PHRASE_GROUPING_POLICY_V1
CaptionGroupWordCountPolicy
CaptionGroupingRejectionReason
CaptionGroup
CaptionGroupsArtifact
CaptionGroupsContractError
compile_caption_groups
load_caption_groups
serialize_caption_groups
```

No stable issue-code delta or private export was introduced.

## Remaining Phase 2 boundary

The accepted implementation returns canonical bytes but does not write
`timing/caption_groups.json`. It does not implement emphasis events,
word-to-frame compilation, `AlignmentReport`, caption layout/wrapping,
V5/V6 collision/preview evidence, renderer or EDL integration, provider
execution, or production readiness.

The next task is read-only reconciliation of the remaining Master Roadmap
Phase 2 deliverables and acceptance criteria. No new implementation is
authorized by this acceptance decision.

## Documentation impact matrix

| Document | Impact |
|---|---|
| `docs/MASTER_ROADMAP.md` | None; unchanged authoritative roadmap. |
| `docs/CURRENT_STATE.md` | Records accepted implementation and next reconciliation. |
| `docs/NEXT_ACTIONS.md` | Sets one read-only scope-reconciliation task. |
| `docs/KNOWN_LIMITATIONS.md` | Retains publication/downstream/environment gaps. |
| `docs/PHASE_ACCEPTANCE.md` | Records bounded acceptance without closing Phase 2. |
| `docs/CHANGELOG.md` | Records audit, repair, tests, and acceptance. |

## Repository safety

`norm_words_debug.json` was excluded from every repository status/diff check
and was not read, statted, hashed, diffed, modified, deleted, or staged.
