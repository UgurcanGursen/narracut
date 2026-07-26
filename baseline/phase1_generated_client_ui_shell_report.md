# Phase 1 Generated Client and Studio UI Shell Report

Date: 2026-07-26
Status: PASS / PENDING POST-COMMIT INDEPENDENT AUDIT
Scope: deterministic generated TypeScript client and HTTP-only React shell

## Revision Evidence

- Implementation base SHA:
  `f50b904b5fda9ec6c1d2604d937aab889a3da362`
- Base branch: `main`
- Base `origin/main` and live remote `main`: exact base SHA
- Proposed commit message:
  `feat: add generated client and Studio UI shell`
- Post-push SHA: pending
- Baseline tag peeled target:
  `f0d7a3100b0855a84432f09ca22001d0913aa1aa`

## Preflight

- Branch, HEAD, origin/main, live remote, parent/history: PASS
- Tracked diff: 0
- Staged diff: 0
- Untracked input: `norm_words_debug.json` only; untouched
- Schema sync: PASS, 16 schemas
- OpenAPI exporter check: PASS
- Focused Project API baseline: `55 passed, 1 existing warning`
- npm lock parse and clean-copy toolchain smoke: PASS
- Repository `node_modules`, `.venv`, `dist`, and `coverage`: absent
- Initial protected inventory: 263 files, aggregate SHA-256
  `cf3ec1977eccd33066a8b9b19f48ed8b458bbb2611bb819a98530c0522a6f747`

## Frozen OpenAPI Input

- Source: `shared-schemas/openapi/openapi.json`
- OpenAPI version: `3.1.0`
- Bytes: 18,490
- SHA-256:
  `c64d9713dbaa7e7afbd1ad5eb07faf1da404e5871466a8012ddb5e3a00f05128`
- Paths: 3
- Component schemas: 14
- Servers: absent
- Operations:
  `createProject`, `getProjectStatus`, `listProjectArtifacts`
- HTTP paths:
  `POST /api/v1/projects`,
  `GET /api/v1/projects/{project_id}/status`,
  `GET /api/v1/projects/{project_id}/artifacts`
- The request discriminator, title bounds, project path pattern, explicit
  success/error responses, nullable artifact fields, and required properties
  are generated from the committed document rather than copied into the
  handwritten facade.

The OpenAPI artifact, canonical schemas, distributed schemas, manifest, and
Studio API remained byte-identical.

## Generator Trial and Configuration

The installed `@hey-api/openapi-ts@0.99.0` package was inspected and exercised
under `C:\tmp` before repository implementation.

- CLI: `openapi-ts`
- Config API: `defineConfig`
- Programmatic generation API: `createClient`
- Final plugins:
  `@hey-api/typescript`, `@hey-api/sdk`, `@hey-api/client-fetch`
- SDK client: `@hey-api/client-fetch`
- Client config: `bundle: true`, `baseUrl: false`
- Logs: silent, log file disabled
- Output clean: enabled by generator and enforced by the controlled wrapper
- Canonical config: `studio-ui/openapi-ts.config.ts`

The first CLI trial demonstrated that a Windows relative input path could be
mistaken for an inferred server value when no OpenAPI server is present. The
final verified config explicitly disables generated base URL inference.

`scripts/client-generation.mjs` is the shared generation entrypoint.
`generate-client.mjs` permits only the committed output. The check script may
override output only to a child of its own system-drive `tmp` directory.
Neither public script accepts arbitrary paths or command-line arguments.

## Runtime Client Dependency Decision

The official client plugin bundles its fetch runtime into generated source.
Generated files have zero package runtime imports. No
`@hey-api/client-fetch` direct runtime dependency was added, and the existing
runtime dependency set remains React and React DOM only.

## Generated Inventory

Aggregate deterministic SHA-256:
`0ba1a9bb20d1bef1a01d366cfb5a5cb139aa9cc549db357630008a6809f80b1a`

| File | Bytes | SHA-256 |
|---|---:|---|
| `client.gen.ts` | 816 | `b325822184abc7aed91c42bb1ea0697bb8ae178833c3fca97f6ec498398c1377` |
| `client/client.gen.ts` | 7,759 | `8a17b0bf1540258734a128f176f6cb915c849b97d8064a613dba5ef8390e58d9` |
| `client/index.ts` | 861 | `949cc7333527c91928c32410c4a4a2dd2b90b99fe080eb8ce4505647852fbe1b` |
| `client/types.gen.ts` | 6,731 | `1a182888235bc21fa2efeb0409589ddf833317b8dd7db4855f198dfc1c47bb4a` |
| `client/utils.gen.ts` | 8,503 | `dce96188f7dfd8e9e5543199a42a5117e23042a7dd48e1ceaff9bb20898f8522` |
| `core/auth.gen.ts` | 1,056 | `4b4aca5bd9b2c43a112bb74617295278d84f86360ada71a8db57f09cd0c254f4` |
| `core/bodySerializer.gen.ts` | 2,488 | `a74163de6731f06f185948895cc4b5f8900e7d30ce76b9588717bad99ab165a7` |
| `core/params.gen.ts` | 4,248 | `097c75f6e269c6c8680641091832a69b38e8828e8ee8465318d32a177593330f` |
| `core/pathSerializer.gen.ts` | 4,295 | `6e80a19627d36fd2a9e8daee113713b2e047d107d42ead9b4a9ab344690b998c` |
| `core/queryKeySerializer.gen.ts` | 2,922 | `adc570c9357a08624cce81dc503abd8d8ff60a76d25bd4d3a4afbe349d82d1f0` |
| `core/serverSentEvents.gen.ts` | 7,204 | `df993567abbe3e5b477d81517fb967cf63cf40b7866957d5dc6cc03238cb1426` |
| `core/types.gen.ts` | 3,459 | `0c33c5e096608fc1f859d89bc17ce428e306c7aa3c2c30acd8affa5a734370af` |
| `core/utils.gen.ts` | 3,417 | `1b637c521d8136dfdbf8dfc4fcc8bb73e0c554466e4d2ca9c9086d4c712983c4` |
| `index.ts` | 877 | `43dfaefb94c762aaf0e6393d49d693898bd69e44b188459bed6c7b214fd91725` |
| `sdk.gen.ts` | 2,376 | `28ade8ad0891f3d5e6e042e7bdfcc7835d5eb2a6ede22032245625a6a684b329` |
| `types.gen.ts` | 7,655 | `5bbf02e77e4170cccf32609589f784a6f897f2fddf0bf09747e3df2b87409d9f` |

All 16 files are UTF-8, BOM-free, LF-only, and contain no timestamp, user-home
path, host, current directory, or source map. Eight generator-owned `any`
tokens occur in bundled runtime internals; handwritten production TypeScript
contains none.

## Determinism and Drift

- Fresh generation A/B inventory: byte-identical
- Fresh generation versus committed output: byte-identical
- Missing generated file negative: rejected
- Extra generated file negative: rejected
- Modified generated file negative: rejected
- Stale generated file negative: rejected
- Negative cases operated only on check-owned temporary copies
- `npm run check:client`: PASS

## Generated Operation and Type Contract

- Exact operation functions:
  `createProject`, `getProjectStatus`, `listProjectArtifacts`
- Request body and project path parameter: typed
- Core/domain-pack request: discriminated union retained
- Success responses: explicit generated types
- 404/409/422/500 error envelope types: generated
- Arbitrary operation URL/path input is not exposed by the facade
- Contract compile and frozen OpenAPI hash test: PASS

## StudioApi Facade

`src/api/studioApi.ts` is the only production importer of generated modules.
It invokes generated operation functions and creates a bundled generated
client per facade instance.

- Raw `fetch`: absent
- Repeated endpoint strings: absent
- Full DTO copies: absent
- Default base URL: empty/same-origin
- Explicit base URL: root-relative, HTTP, or HTTPS
- Rejected: filesystem paths, protocol-relative values, user-info, query,
  fragment, non-HTTP absolute protocols, and traversal
- Client config: instance-local; no generated singleton mutation
- Two-instance base URL isolation test: PASS

Structured API codes are mapped to fixed public messages. Unknown structured
errors, malformed bodies, parse failures, and network failures use bounded
generic messages. Raw request/response bodies, issue text, stack, path, and
exception detail are not surfaced or logged.

## React Shell

The single-screen shell provides:

- accessible project title and domain fields;
- exact Core only and Business & Technology choices;
- exact fixed business-tech version/profile payload;
- disabled empty-title and in-flight submit;
- real create, status, and artifact-list calls;
- project ID, canonical/create status, read-back status, version, resolved
  domain fields, policy snapshot, and persistence scope;
- artifact count, real list rows, and honest empty state;
- responsive local CSS with clear empty/busy/error/success states.

It does not expose client-controlled project IDs, domain IDs, versions,
profiles, paths, workspace/output fields, true-crime eligibility, fake
artifacts, render controls, job state, progress, upload, auth, or durable-save
claims.

The UI always displays:

> Project data is stored only for the lifetime of the current API process.
> Restarting the API clears this project.

## HTTP-Only Boundary

`scripts/verify-http-boundary.mjs` uses the TypeScript AST plus deterministic
file inventory. It checks five handwritten production TS/TSX files.

- Component/App generated imports: 0
- Component/App `@hey-api` or OpenAPI imports: 0
- Handwritten production raw `fetch`, XMLHttpRequest, WebSocket, EventSource,
  Axios, Node filesystem/path/process, child process, eval, Python/backend,
  repository traversal, file URI, Windows absolute path, and endpoint
  literals: 0
- Generated importers are limited to:
  `src/api/studioApi.ts` and
  `src/test/generatedClientContract.test.ts`
- `npm run verify:http-boundary`: PASS

## Frontend Tests and Build

- Strict TypeScript typecheck: PASS
- Unit/component/contract tests: `23 passed` in 3 files
- At least one component test uses:
  React -> real facade -> generated client -> mocked global fetch
- Core and business-tech payloads, exact methods/paths, status/artifact reads,
  error sanitization, relative/absolute base URLs, instance isolation,
  invalid protocols, empty title, double submit, persistence warning, empty
  artifacts, and prohibited UI controls are covered.
- Vite build: PASS, 32 modules transformed
- Temporary build output:
  `index.html` 0.49 kB,
  CSS 3.63 kB,
  JS 208.02 kB
- No build output was written to or committed in the repository.

## Live FastAPI HTTP

A locked Studio Python environment started
`kurgu_studio_api.app:create_app --factory` on `127.0.0.1` with an ephemeral
port. Bounded readiness probing preceded the separate live Vitest config.

The real generated client/facade performed:

- core-only create;
- project status read;
- artifact-list read;
- `persistence_scope == process_lifetime`;
- artifact count `0`.

Live test: `1 passed`. The owned Uvicorn process was confirmed terminated in
the orchestration `finally` path. No port or PID was written to the repository.

## npm, Audit, and Lock

- Node: `v24.11.1`
- npm: `11.6.2`
- Clean `npm ci --ignore-scripts` A: PASS, 167 packages
- Clean `npm ci --ignore-scripts` B: PASS, 167 packages
- `npm audit`: 0 vulnerabilities
- Toolchain exact-pin/import smoke: PASS
- Lockfile version: 3
- Direct dependencies: 14, all exact
- Lock package entries: 197
- Missing integrity entries: 0
- File/VCS/private registry/auth dependencies: 0
- Root package metadata parity: PASS
- Repository/A/B lock SHA-256:
  `5404b6f9cf7d32692be5c197468eecdfb3b5ce70303f203da2b25b4508c46d95`
- `npm install --package-lock-only --ignore-scripts` changed bytes: 0
- Existing `package-lock.json` therefore required no repository change.

## Python Regression

All accepted reruns used `PYTHONDONTWRITEBYTECODE=1`, cacheprovider disabled,
and unique `C:\tmp` basetemp roots where pytest fixtures required temporary
files.

- Focused Project API: `55 passed, 1 existing warning`
- Shared schema/OpenAPI foundation: `18 passed`
- Studio toolchain: `3 passed, 1 existing warning`
- Combined contract/migrator: `213 passed, 1 skipped`
- Full Python discovery: `345 passed, 1 skipped, 1 existing warning`
- Existing warning:
  Starlette/HTTPX TestClient deprecation

An initial foundation attempt reached 12 passing tests and then encountered the
known inaccessible default Windows pytest temp root. It was discarded and
rerun with a unique `C:\tmp` basetemp; the authoritative result is 18 passed.
No video render was run.

## Schema, Static, and Security Gates

- Schema sync: PASS
- OpenAPI exporter check: PASS
- Canonical/distributed byte parity: 16/16
- Canonical `$ref` count: 159
- Manifest SHA-256:
  `56e1f67edc925b25caeb1e40616bafdb6fae07ea69892749f0ce7a55537f9673`
- Existing tracked JSON parsed: 111
- New intended JSON configs parsed: 3
- `git diff --check`: PASS
- New UI user-home paths: 0
- New UI credential-bearing URIs: 0
- New UI high-confidence secret signatures: 0
- Generated package runtime imports: 0
- Repository source maps: 0
- Repository dependency/build/coverage directories: 0

Reachable-history high-confidence secret signatures are zero. A broad
credential-URI pattern finds only the pre-existing, protected synthetic
negative fixture in `tests/test_v2_to_v3_migrator.py` across six historical
commits; it is not a credential, production source, or changed file.

## Protected Paths and Mutation

- Final protected inventory: 263 files
- Final protected aggregate SHA-256:
  `cf3ec1977eccd33066a8b9b19f48ed8b458bbb2611bb819a98530c0522a6f747`
- Initial/final protected aggregate equality: PASS
- Backend, V2, requirements, schemas, manifest, OpenAPI, engine contracts,
  migration, domain packs, samples, docs, and previous evidence reports:
  unchanged
- `norm_words_debug.json`: untracked, untouched, and excluded from staging
- Repository dependency/build/cache artifacts: none

## Changed Files

- `.gitattributes`: one LF rule for this report
- `studio-ui/package.json`: explicit build/test/generation/boundary scripts
- `studio-ui/README.md`: truthful architecture, commands, scope, and limits
- `studio-ui/index.html`
- `studio-ui/openapi-ts.config.ts`
- `studio-ui/tsconfig.json`
- `studio-ui/tsconfig.app.json`
- `studio-ui/tsconfig.node.json`
- `studio-ui/vite.config.ts`
- `studio-ui/vitest.config.ts`
- `studio-ui/vitest.live.config.ts`
- `studio-ui/scripts/client-generation.mjs`
- `studio-ui/scripts/generate-client.mjs`
- `studio-ui/scripts/check-generated-client.mjs`
- `studio-ui/scripts/verify-http-boundary.mjs`
- `studio-ui/src/main.tsx`
- `studio-ui/src/App.tsx`
- `studio-ui/src/app.css`
- `studio-ui/src/vite-env.d.ts`
- `studio-ui/src/api/studioApi.ts`
- `studio-ui/src/api/studioApiError.ts`
- `studio-ui/src/api/studioApi.test.ts`
- `studio-ui/src/api/studioApi.live.test.ts`
- `studio-ui/src/components/ProjectConsole.tsx`
- `studio-ui/src/components/ProjectConsole.test.tsx`
- `studio-ui/src/test/setup.ts`
- `studio-ui/src/test/fixtures.ts`
- `studio-ui/src/test/generatedClientContract.test.ts`
- 16 generated files listed above
- `baseline/phase1_generated_client_ui_shell_report.md`

## Limitations and Next Gate

- Persistence remains process-lifetime and in memory.
- No WorkspaceStore, SQLite, durable reopen, authentication, upload,
  render/job/progress, artifact mutation, polling, SSE/WebSocket, router,
  state-management library, or production deployment boundary was added.
- Business-tech remains the only public domain pack; true-crime-legal remains
  a non-production contract example.
- This implementation does not close Phase 1.

Implementation decision: PASS.

Next gate: manual verification and post-commit independent generated
client/Studio UI audit, followed later by Phase 1 documentation/acceptance
harmonization and final closure audit.
