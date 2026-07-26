# Phase 1 Thin Project API Contract Report

Date: 2026-07-26
Status: PASS
Scope: thin project HTTP, application-service, port, and process-lifetime adapter slice

## Eligibility Audit Addendum

The independent post-commit audit of
`22ae36d314fc57a8603cd888576110e3fd1476b9` found two public eligibility
fail-open cases that the original test matrix did not cover:

- a schema-valid real profile ID from another mode was accepted for
  `business-tech`; and
- the discovered, non-production `true-crime-legal` contract example was
  accepted by project creation.

The original implementation `PASS` below is therefore qualified with respect
to production domain/profile eligibility. A separate bounded hardening slice
adds an application-owned allowlist, makes `DOMAIN_PROFILE_MISMATCH` reachable
through a real request, hides discovered-but-ineligible packs behind
`DOMAIN_UNKNOWN`, and records its own test counts in
`phase1_project_api_eligibility_hardening_report.md`. The historical counts
and implementation evidence below remain scoped to the original commit.

## Revision Evidence

- Implementation base SHA:
  `d00657f30c0ffac71a84ea4217874b025e3558ab`
- Commit message:
  `feat: add thin project API contracts`
- Post-push SHA: pending
- The post-push SHA will be recorded by the independent post-commit audit or a
  later documentation harmonization task.

## Preflight

- Branch: `main`
- HEAD, `origin/main`, and live remote `main`:
  `d00657f30c0ffac71a84ea4217874b025e3558ab`
- Parent:
  `9587788aaef732fdc4f4b1f057e3280270a09420`
- Tracked diff before changes: 0
- Staged diff before changes: 0
- Untracked before changes: `norm_words_debug.json` only
- Baseline tag peeled target:
  `f0d7a3100b0855a84432f09ca22001d0913aa1aa`
- Shared schema sync check: PASS, 16 schemas
- Foundation OpenAPI check: PASS before implementation
- Locked Studio Python:
  `C:\tmp\kurgu_foundation_audit_py_20260726111716`
- Repository `node_modules`, `.venv`, `dist`, and `coverage`: absent

## Architecture Boundaries

The implemented request flow is:

```text
FastAPI route
  -> strict request DTO
  -> ProjectApplicationService
  -> DomainResolutionPort
  -> ContractValidationPort
  -> ProjectRepository
  -> explicit response DTO
```

- Routes do not import engine contracts, domain registries, filesystem,
  renderer, migrator, media, provider, or LLM modules.
- The application package imports neither FastAPI nor Pydantic.
- The repository stores application aggregates rather than HTTP DTOs.
- Schema selection and domain-pack roots are fixed by infrastructure wiring.
- WorkspaceLoader is not used because these endpoints accept no workspace
  document or filesystem path.

## File Inventory

- `studio-api/src/kurgu_studio_api/api/**`: centralized errors, handlers,
  versioned router, project routes, and DTOs
- `studio-api/src/kurgu_studio_api/application/**`: immutable models, errors,
  ports, and project service
- `studio-api/src/kurgu_studio_api/infrastructure/**`: contract/domain
  adapters, in-memory repository, clock/ID factory, and runtime wiring
- `studio-api/src/kurgu_studio_api/app.py`: fresh runtime and route registration
- `studio-api/tests/**`: 42 focused project API and boundary tests
- `tests/test_control_plane_openapi_foundation.py`: minimal three-path
  foundation evolution
- `shared-schemas/openapi/openapi.json`: generated runtime contract
- `studio-api/README.md`, `studio-api/pyproject.toml`, `.gitattributes`
- this report

## Endpoint Contract

Exactly three business endpoints are exposed:

```text
POST /api/v1/projects                       createProject
GET  /api/v1/projects/{project_id}/status   getProjectStatus
GET  /api/v1/projects/{project_id}/artifacts listProjectArtifacts
```

No health, readiness, job, render, update/delete, workspace-upload, or
artifact-write endpoint is present.

## Core-Only Resolution

- Request variant: `resolution_mode=core_only`
- Domain identity: `core-generic@0.0.0`
- Profile: canonical sample-derived `dpf_core_default`
- Policy: empty deterministic core policy
- Manifest hash: canonical zero hash used by the existing core-only sample
- Snapshot hash and ID: public `policy_snapshot_hash`
- Profile and snapshot: validated by fixed canonical schemas
- No domain-pack discovery is needed by this resolution path.

## Domain-Pack Resolution

- The application wiring discovers the configured repository domain-pack root.
- `DomainPackRegistry.get()` and `DomainPolicyResolver.resolve()` are used.
- The verified production request uses:
  `business-tech@0.1.0`, profile `dpf_business_default`.
- The resolved snapshot ID is:
  `dps_d18e9981c3f4bcca8e3f`.
- Unknown domain/version and invalid profile contracts fail closed.
- Profile domain/version cannot be supplied independently by the client; the
  server binds them to the selected outer domain, so contradictory nested
  identity fields are rejected as unknown request fields.

## Project and Artifact Contract Validation

- Project mappings use fixed `project.schema.json` validation.
- Successful projects use canonical `status=ready` and `schema_version=3.0.0`.
- Project IDs are server-generated and satisfy the canonical `prj_` pattern.
- Artifact mappings use fixed `artifact.schema.json` plus the public artifact
  graph validator before response projection.
- Artifact DTO fields are the canonical artifact fields; the canonical
  artifact contract contains no local path or provider URI field, so no
  lossy projection is needed.
- Invalid artifacts fail before insertion.

## Repository Semantics

- Persistence scope: `process_lifetime`
- State is instance-local; no module-level mutable repository exists.
- Collision check and insert are protected by an `RLock`.
- Collision returns structured `409 PROJECT_ID_COLLISION` without overwrite.
- Failed create leaves no project.
- Get and artifact-list results are defensive deep copies.
- New application instances do not share state.
- Restart, reopen, revision, recovery, disk durability, SQLite, and
  WorkspaceStore guarantees are explicitly absent.

## Structured Error Boundary

The single envelope contains a stable code, sanitized message, and structured
issues. Implemented public codes:

```text
REQUEST_VALIDATION_FAILED
CONTRACT_VALIDATION_FAILED
DOMAIN_CONFIGURATION_REQUIRED
DOMAIN_UNKNOWN
DOMAIN_PROFILE_MISMATCH
PROJECT_NOT_FOUND
PROJECT_ID_COLLISION
INTERNAL_ERROR
```

Request errors omit Pydantic input values. Engine source files, local paths,
exception repr/traceback, and raw request markers are not returned. HTTP
semantics are 404, 409, 422, and 500 as appropriate.

## OpenAPI

- OpenAPI version: `3.1.0`
- Exact path count: 3
- Stable unique operation IDs: 3
- Component schema count: 14
- Runtime A/B equality: PASS
- Runtime/committed byte equality: PASS
- Environment-dependent `servers`: absent
- Timestamp, hostname, cwd, local path, and Git SHA: absent
- Artifact bytes: 18,490
- SHA-256:
  `c64d9713dbaa7e7afbd1ad5eb07faf1da404e5871466a8012ddb5e3a00f05128`

No TypeScript client was generated.

## Tests and Quality Gates

- Focused project API tests:
  `42 passed, 1 existing warning`
- Shared schema/OpenAPI foundation:
  `18 passed`
- Studio toolchain smoke:
  `3 passed, 1 existing warning`
- Existing contract/migrator regression:
  `213 passed, 1 skipped`
- Full discovery:
  `332 passed, 1 skipped, 1 existing warning`
- Existing warning:
  Starlette deprecates the current HTTPX TestClient path.
- Changed/new Python in-memory AST/compile:
  30 PASS
- Current tracked JSON parse:
  111 PASS
- Canonical/distributed schema validation and byte parity:
  16 + 16 PASS
- Canonical relative `$ref` resolution:
  159 PASS through the retained foundation test
- Schema sync check: PASS
- OpenAPI write/check and A/B determinism: PASS
- `git diff --check`: PASS
- Full video render: not run, as required

## Security and Path Boundary

- New-scope private-key, credential URI, credential assignment, and sensitive
  query scan: 0
- Current/reachable credential-URI pattern hits are confined to the existing
  synthetic migrator security test.
- Routes expose no path, schema filename, domain-pack root, workspace root, or
  output directory input.
- API tests verify no raw marker, traceback, exception type, absolute
  repository path, source file, provider URI, or cache path leakage.
- No network, renderer, migrator, media, provider, LLM, SQLite, or subprocess
  surface was added to the production endpoint slice.

## Protected Paths

- Protected-path diff from the implementation base: 0
- Canonical `schema/v3/**`: unchanged
- Generated `shared-schemas/v3/**` and manifest: unchanged
- Manifest SHA-256 remains:
  `56e1f67edc925b25caeb1e40616bafdb6fae07ea69892749f0ce7a55537f9673`
- Engine contracts/domain/migration, V2, samples, docs, root requirements,
  locks, Studio UI, previous evidence, and baseline manifests: unchanged
- `norm_words_debug.json`: untracked and untouched

## Known Limitations and Next Gate

- Persistence is deliberately process-lifetime only.
- No artifact creation endpoint exists; new projects correctly return an empty
  artifact collection.
- No UI, generated TypeScript client, authentication, job/render progress,
  WorkspaceStore, SQLite, or production deployment boundary exists.
- The three previously identified shared-schema negative-regression additions
  remain separate backlog.
- The existing Starlette/TestClient warning remains non-blocking.

Implementation decision: PASS.

Next gate: post-commit independent audit of this project API contract slice.
Generated TypeScript client work remains pending until that audit accepts the
committed endpoint contract.
