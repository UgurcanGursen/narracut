# Phase 1 Shared Schema and OpenAPI Foundation Report

Date: 2026-07-26
Status: PASS
Scope: deterministic shared schema distribution and routes-free OpenAPI generation foundation

## Revision Evidence

- Implementation base SHA:
  `9587788aaef732fdc4f4b1f057e3280270a09420`
- Proposed commit message:
  `feat: add shared schema and OpenAPI foundations`
- Post-push SHA: pending
- The post-push SHA will be recorded by the independent post-commit audit or a
  later documentation harmonization task. This report will not be amended
  solely to insert that SHA.

## Preflight

- Branch: `main`
- HEAD, `origin/main`, and live remote `main`:
  `9587788aaef732fdc4f4b1f057e3280270a09420`
- Tracked diff before changes: 0
- Staged diff before changes: 0
- Untracked before changes: `norm_words_debug.json` only
- Baseline tag peeled target:
  `f0d7a3100b0855a84432f09ca22001d0913aa1aa`
- The 13 control-plane toolchain files were present.
- Repository `node_modules`, `.venv`, `dist`, and `coverage` directories: 0
- Locked Studio venv recreated under:
  `C:\tmp\kurgu_shared_openapi_preflight_20260726_101843`
- Locked imports: FastAPI `0.140.0`, Pydantic `2.13.4`: PASS
- Initial SHA-256 inventory captured for 85 existing allowed/protected files.

## Canonical Ownership

`schema/v3/` remains the single canonical source. The Python engine and
`SchemaCatalog` continue to load that directory directly.

`shared-schemas/v3/` is a generated distribution only:

- no symlink is used;
- canonical files are copied byte-for-byte;
- `$id` and relative `$ref` values are not rewritten;
- generated schema files are documented as non-editable;
- no second engine lookup path or second source of truth is introduced.

## Schema and Distribution Inventory

- Canonical schema count: 16
- Distribution schema count: 16
- Filename inventory parity: PASS
- Canonical/distribution byte parity: PASS for all 16 schemas
- SHA-256 parity against `shared-schemas/manifest.json`: PASS
- Unique canonical `$id` count: 16
- Duplicate filename and duplicate `$id` fail-closed behavior: implemented
- Draft 2020-12 `check_schema`:
  16 canonical + 16 distributed schemas PASS
- Relative `$ref` occurrence/resolution count: 159 PASS
- `SchemaCatalog.schema_root`: canonical `schema/v3/` PASS

## Manifest Contract

`shared-schemas/manifest.json` contains:

- format version 1;
- relative canonical and distribution roots;
- schema count derived from the canonical inventory;
- filename-sorted entries;
- canonical/distribution relative paths;
- lowercase SHA-256 values;
- canonical `$id` values.

It contains no timestamp, hostname, username, current working directory, or
absolute local path. UTF-8, BOM-free, LF, two-space indentation, sorted JSON
keys, and final newline checks pass.

Manifest SHA-256:
`56e1f67edc925b25caeb1e40616bafdb6fae07ea69892749f0ce7a55537f9673`

## Schema Sync

Commands:

```text
python -B scripts/sync_shared_schemas.py --write
python -B scripts/sync_shared_schemas.py --check
```

Results:

- `--write`: PASS, 16 schemas
- `--check`: PASS, 16 schemas
- write A/B output equality: PASS
- missing generated schema detection: PASS
- extra/stale generated schema detection: PASS
- modified generated schema detection: PASS
- manifest drift detection: PASS
- stale output write behavior: fail-closed without deletion PASS
- individual file writes: fixed `C:\tmp` temporary file + atomic replace
- arbitrary CLI source/output selection: unavailable

## Shared npm Distribution Metadata

- Package name: `@kurgu/shared-schemas`
- Version: `0.1.0`
- Private/non-published: true
- Runtime/dev dependencies: none
- Export surfaces:
  `./manifest.json`, `./v3/*`, and `./openapi/openapi.json`
- Node self-reference resolution for all three export surfaces: PASS
- No npm install, lock regeneration, or client generation was performed.

## FastAPI Application Factory

Public symbol: `kurgu_studio_api.create_app`

- each call returns a fresh FastAPI instance;
- title, version, description, and OpenAPI version are fixed;
- OpenAPI version: `3.1.0`;
- application routes: 0;
- no health, project, status, artifact, or other fake endpoint;
- no global app instance or mutable application state;
- no engine, renderer, migrator, or domain logic import;
- no startup task, CORS, auth, server binding, or deployment configuration;
- import-time filesystem mutation: 0.

The package is used through `PYTHONPATH=<repo>\studio-api\src`; editable
installation and new build dependencies are not required.

## Deterministic OpenAPI

Commands, using the locked Studio Python:

```text
PYTHONPATH=<repo>\studio-api\src
python -B -m kurgu_studio_api.openapi_export --write
python -B -m kurgu_studio_api.openapi_export --check
```

Results:

- JSON parse: PASS
- OpenAPI: `3.1.0`
- `paths`: empty object
- environment-dependent `servers`: absent
- fake endpoints: absent
- UTF-8, BOM-free, LF, sorted keys, two-space indent, final newline: PASS
- committed/runtime byte equality: PASS
- generation A/B byte equality: PASS
- A hash:
  `c49dbb67e0b6dd4552798fa5e1292c0142d8ad1d9b5de7edd449baf4e49edebf`
- B hash:
  `c49dbb67e0b6dd4552798fa5e1292c0142d8ad1d9b5de7edd449baf4e49edebf`
- artifact size: 241 bytes
- arbitrary output path/import target: rejected

This is a generation foundation, not final Phase 1 endpoint acceptance
OpenAPI. No TypeScript client is generated because no real endpoint contract
exists yet.

## Tests and Quality Gates

- New targeted tests in locked Studio venv:
  `18 passed`
- Existing Studio toolchain smoke in locked Studio venv:
  `3 passed, 1 warning`
- Existing combined contract/migrator regression:
  `213 passed, 1 skipped`
- Full discovery with locked Studio `purelib`, Studio source, and repository root
  added to the root legacy environment:
  `290 passed, 1 skipped, 1 warning`
- Warning:
  existing `StarletteDeprecationWarning` for the current HTTPX TestClient path
- Changed Python in-memory compile/AST parse: 6 PASS
- Current tracked/generated JSON parse: 111 PASS
- Deterministic sync A/B: PASS
- Deterministic OpenAPI A/B: PASS
- `git diff --check`: PASS
- Full video render: not run, as required

The full-suite environment must use the locked venv's
`sysconfig.get_path("purelib")`, not the venv root, on `PYTHONPATH`.

## Security and Path Boundary

- New-scope credential-bearing URI/private-key/credential-assignment/sensitive
  query scan: 0
- Reachable-history credential-URI pattern hits are confined to the existing
  synthetic migrator security test file; no production or new-scope secret was
  found.
- Production `shell=True`, subprocess, eval/exec, network client, socket, and
  environment dump surface: 0
- User-selectable schema root, output root, app import, or filesystem path: 0
- Local absolute path in manifest/OpenAPI: 0
- Timestamp/hostname/cwd in manifest/OpenAPI: 0
- Registry auth/token material in the shared npm package: 0

## Protected Paths and Repository Mutation

- Protected-path diff from the implementation base: 0
- Canonical `schema/v3/**` content diff: 0
- `engine/contracts/**`, `engine/domain/**`, `engine/migration/**`,
  `domain-packs/**`, `samples/**`, `docs/**`, Studio UI files, root
  requirements, and prior evidence files: unchanged
- `studio-api/requirements.lock` SHA-256 unchanged:
  `f1d2721dddbda607f3c8c1f2fa9a07811efa32ded79b1fa81606e8eee3066d3d`
- `studio-ui/package-lock.json` SHA-256 unchanged:
  `5404b6f9cf7d32692be5c197468eecdfb3b5ce70303f203da2b25b4508c46d95`
- Repository dependency/output directories:
  no `node_modules`, `.venv`, `dist`, or `coverage`
- Existing ignored Python/pytest cache directories remained outside the commit
  scope; no new repository cache directory was created.
- `norm_words_debug.json` remains untracked and untouched.

The root `.gitattributes` update is the one extra tooling file required beyond
the enumerated tree. It fixes LF checkout behavior for both canonical
`schema/v3/**` and generated outputs on Windows, preserving cross-checkout byte
and manifest hash parity. It does not change any canonical schema blob.

## Limitations and Next Gate

- The app has no endpoint contracts.
- No application service, repository, WorkspaceStore, SQLite, UI source, or
  generated TypeScript client exists in this slice.
- The existing Starlette/TestClient deprecation warning remains non-blocking
  and was not opportunistically changed.

Foundation decision: PASS.

Project endpoint/application-service contract slice entry gate: READY.
Generated TypeScript client generation remains pending until real endpoint
contracts are present.
