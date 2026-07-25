# Phase 1 Migrator Security and Failure-Semantics Hardening

Date: 2026-07-25

## Scope and result

The independent post-commit audit identified three actionable migration
boundary defects: credential-bearing URIs could reach canonical artifacts,
failed migrations retained unpublished target identity, and unknown BGM/SFX
children were accepted as generic structured loss. All three are hardened and
covered by regression tests.

Security-hardening status: **PASS**.

WorkspaceStore entry gate: **PENDING_INDEPENDENT_REAUDIT**.

## URI threat model

Migration source references are untrusted. Inspection occurs before a raw
reference is normalized, copied into an origin URI, encoded as a portable URN,
or included in mapping/report text. The standard-library-only boundary covers:

- URI username, password, and user-info;
- control characters and newlines;
- credential-like malformed URIs;
- query and fragment keys normalized case-insensitively with separators
  removed;
- token, authorization, API-key, client-secret, password, credential,
  signature, AWS, Google signed-URL, and API-gateway key families;
- generic credential values and secret-bearing open extension URI values.

The global word `key` is not classified as secret. Safe parameters such as
`view`, `language`, `monkey`, and `public_key` remain usable.

Detection produces `MIGRATION_SECRET_REDACTED` with severity `ERROR`. It does
not sanitize and continue: strict and permissive migrations both fail, no
workspace is published, and the raw value is absent from workspace, canonical
result, mapping, Markdown report, inspection summary, CLI stdout, and CLI
stderr. The source SHA-256 fingerprint remains allowed because it does not
contain or reproduce source plaintext.

## Failure metadata

`FAILED` results now set `target_fingerprint` and `workspace_id` to `null`.
Workspace schema/loader success flags are false for an unpublished candidate.
The Markdown report says `Workspace published: no` and uses `not published`
for target identity. The inspection summary uses
`target_workspace_id: not_published` and omits `workspace.json` from its output
list. The Draft 2020-12 result schema enforces null target identity for modern
failed results while preserving its `$id` and legacy compatibility branch.

## BGM/SFX source coverage

The allowlists come from the active `v2.models` contract:

- BGM: `enabled`, `track_id`, `gain_db`, `fade_in`, `fade_out`;
- SFX: `enabled`, `asset_id`, `trigger_cue`, `gain_db`, `max_duration`.

Known fields retain explicit `UNSUPPORTED` loss behavior. Unknown or nested
unknown fields produce `MIGRATION_UNACCOUNTED_SOURCE_FIELD`, severity `ERROR`,
and fail in both modes. The documented open `extra` extension behavior remains
structured `UNSUPPORTED` loss.

The existing deterministic leaf inventory remains authoritative: the demo
accounts for all 67 source leaves exactly once, including null/false/zero/empty
values, list indexes, and JSON Pointer escaping.

## Verification

- Migrator suite: `111 passed`.
- Combined contract/migrator suite: `198 passed, 1 skipped`.
- Full suite: `254 passed, 1 skipped`.
- Demo A/B and committed expected byte equality: PASS for all four artifacts.
- Public WorkspaceLoader, migration-result schema, core-only, domain-pack,
  stable-ID collision, and strict/permissive regressions remain covered.
- Root `main.py`, `v2/`, `requirements.txt`, Phase 0 fixtures/evidence, and
  `scripts/verify_phase0_offline_render.py` are outside the change set.

## Persistence and snapshot limitations

Migrator output uses atomic replacement for each individual file. The
four-artifact set is **not a transaction**: a process or write failure can
leave mixed generations. It is not a production persistence boundary.

WorkspaceStore must provide:

- a staged revision directory;
- hash verification for every artifact;
- a revision manifest;
- file close/fsync durability;
- a commit marker or atomic active-revision pointer;
- crash recovery;
- prevention of mixed-generation artifact sets;
- preservation of the previous valid revision;
- partial staging cleanup.

Aggregate workspaces use the embedded policy snapshot as authoritative.
`policy_snapshot_ref` is a logical/informational identity in aggregate mode.
For split workspaces it remains a real external document reference.

## Remaining technical debt

The migration mapping module remains large. A broad mapping/ID/coverage refactor
is deliberately deferred. WorkspaceStore transaction semantics and independent
post-commit re-audit remain open.
