# Phase 1 Secondary Provenance URI Security Fix

Date: 2026-07-25

## Result

The post-commit independent re-audit found that a safe primary `visual.url`
could cause lower-priority provenance fields to reach source-field coverage
without URI-context inspection. Scheme-less user-info could therefore avoid
`MIGRATION_SECRET_REDACTED` and publish in permissive mode.

Secondary provenance URI hardening: **PASS**.

WorkspaceStore entry gate: **PENDING_INDEPENDENT_REAUDIT**.

## Security principle and root cause

Target selection and source security acceptance are independent. Every known
URI/provenance source string is inspected even when it is secondary,
non-selected, fallback-only, or an unsupported open extension.

The root cause was `_account_remaining` calling the generic source inspector
without deterministic URI context. The fix derives context from the canonical
JSON pointer and passes it to the same central inspector used by primary
origin candidates.

## URI/provenance field inventory

Active visual contract fields:

- `url`
- `selected_asset_url`
- `logo_url`
- `query`

Exact open-extension provenance names:

- `uri`
- `url`
- `source_url`
- `provider_uri`
- `origin_uri`
- `resolved_path`
- `selected_asset_url`
- `logo_url`
- `query`

These are exact names rather than an unrestricted substring heuristic.

## Scheme-less user-info and false-positive boundary

URI-context inspection rejects username/password, username-only,
protocol-relative, whitespace-obfuscated, control-character, and
percent-encoded user-info. It remains field-context dependent: narration,
title, labels, and other editorial text are not treated as URIs merely because
they contain an email address or colon.

## Regression matrix and no-leak

`selected_asset_url`, `extra.resolved_path`, `logo_url`, and
`extra.provider_uri` are tested in both strict and permissive modes with a safe
competing primary URL. All eight combinations:

- return `FAILED`;
- produce `MIGRATION_SECRET_REDACTED`/`ERROR` at the exact source pointer;
- publish no workspace;
- keep target fingerprint/workspace ID empty;
- report `not_published`;
- return CLI exit code `3`;
- omit the raw reference from workspace, result, mapping, issue text, Markdown,
  summary, stdout, and stderr.

Safe secondary HTTPS values, a Windows/local resolved path, narration email,
and normal colon-bearing text do not create a security error.

## Verification

- Migrator suite: `126 passed`.
- Combined contract/migrator suite: `213 passed, 1 skipped`.
- Full suite: `269 passed, 1 skipped`.
- Demo A/B/committed expected equality: PASS for all four artifacts.
- Draft 2020-12 schema checks and reference resolution: PASS (`16` schemas,
  `159` references).
- Public loader samples: minimal, business-tech, and split-long-form PASS.
- Demo migration-result schema and public WorkspaceLoader validation: PASS.
- V2 production mutation: `0`.

## Persistence limitation

Migrator files remain individually atomic, while the four-artifact output set
is not a transaction. WorkspaceStore must provide staged revisions, manifest
and artifact hashes, an active-revision commit protocol, crash recovery,
mixed-generation prevention, previous-valid-revision preservation, and partial
staging cleanup.
