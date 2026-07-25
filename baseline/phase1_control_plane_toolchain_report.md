# Phase 1 Control-Plane Toolchain Report

Date: 2026-07-26
Status: PASS
Scope: dependency/toolchain provisioning only

## Preflight

- Branch: `main`
- HEAD: `3b1ff1001f0722209d76a2120efb471df35de342`
- origin/main: `3b1ff1001f0722209d76a2120efb471df35de342`
- Tracked diff before changes: 0
- Staged diff before changes: 0
- Untracked before changes: `norm_words_debug.json` only
- Baseline tag peeled target:
  `f0d7a3100b0855a84432f09ca22001d0913aa1aa`
- Protected production paths were not changed: `main.py`, `v2/**`,
  `requirements.txt`, `schema/v3/**`, `engine/contracts/**`,
  `engine/migration/**`, `domain-packs/**`, `samples/**`, existing `tests/**`,
  docs, baseline manifest/dependency graph, Phase 0 evidence, and migration
  expected outputs.

## Environment

- Python: `3.13.1`
- Global pip: `25.0`
- Global pip check: PASS
- Node: `v24.11.1`
- npm: `11.6.2`
- npm registry: `https://registry.npmjs.org/`
- pnpm inventory only: `11.17.0`
- yarn: not installed
- Global FastAPI/Uvicorn/Starlette: not installed
- Global HTTPX/Pydantic/pytest/jsonschema:
  `httpx==0.28.1`, `pydantic==2.13.4`, `pytest==9.1.1`,
  `jsonschema==4.26.0`

## Python Dependency Decision

Runtime direct dependencies are exact pinned in `studio-api/pyproject.toml`:

- `fastapi==0.140.0`: thin Studio API framework
- `uvicorn==0.51.0`: future ASGI runtime
- `pydantic==2.13.4`: future DTO/model boundary, aligned with existing global
  baseline
- `jsonschema[format]==4.26.0`: canonical V3 contract validation dependency

Test/dev direct dependencies:

- `httpx==0.28.1`: FastAPI TestClient dependency, aligned with existing global
  baseline
- `pytest==9.1.1`: smoke and future API test runner

The lock intentionally excludes legacy render/media/provider dependencies such
as MoviePy, FFmpeg wrappers, TTS, Playwright, and provider packages.

## Python Resolved Lock

`studio-api/requirements.lock` is an exact-version clean-environment resolved
lock, not a hash-secured package lock. It contains 38 application/test packages
and excludes bootstrap tools such as pip, setuptools, and wheel.

Key resolved versions:

- `fastapi==0.140.0`
- `starlette==1.3.1`
- `pydantic==2.13.4`
- `pydantic-core==2.46.4`
- `httpx==0.28.1`
- `httpcore==1.0.9`
- `uvicorn==0.51.0`
- `jsonschema==4.26.0`
- `jsonschema-specifications==2025.9.1`
- `referencing==0.37.0`
- `pytest==9.1.1`

Clean resolution root pattern:

- `C:\tmp\kurgu_control_plane_python_<timestamp>`

Lock-only verification root pattern:

- `C:\tmp\kurgu_control_plane_python_lock_<timestamp>`

## Python Compatibility

- `pip check`: PASS
- Import smoke: PASS for FastAPI, Starlette, Pydantic, HTTPX, Uvicorn, pytest,
  and jsonschema.
- Minimal FastAPI/TestClient request: PASS, HTTP 200 with deterministic JSON.
- Public engine contract imports: PASS for `SchemaCatalog`, `WorkspaceLoader`,
  `DomainPackRegistry`, `DomainPolicyResolver`, `DomainPackError`, and
  `policy_snapshot_hash`.
- Canonical schema smoke: PASS using `schema/v3` and the minimal V3 sample.
- Domain-pack registry initialization/discovery smoke: PASS.
- Known compatibility warning: Starlette emits a deprecation warning for the
  current `httpx` TestClient path. Runtime behavior and tests pass; the warning
  should be revisited during the actual FastAPI implementation slice.

## Python Reproducibility

- Environment A: direct resolver install, `pip check`, FastAPI/TestClient smoke,
  public contract import smoke, canonical schema smoke: PASS.
- Environment B: lock-only install from `studio-api/requirements.lock`, `pip
  check`, verify script, and pytest smoke: PASS.
- `studio-api/scripts/verify_toolchain.py`: PASS.
- `studio-api/tests/test_toolchain_smoke.py`: `3 passed, 1 warning`.

## Node Dependency Decision

Package manager: npm only.

Runtime direct dependencies:

- `react==19.2.8`
- `react-dom==19.2.8`

Development direct dependencies:

- `typescript==6.0.3`
- `vite==8.1.5`
- `@vitejs/plugin-react==6.0.4`
- `@types/react==19.2.17`
- `@types/react-dom==19.2.3`
- `@types/node==26.1.1`
- `vitest==4.1.10`
- `jsdom==29.1.1`
- `@testing-library/react==16.3.2`
- `@testing-library/jest-dom==7.0.0`
- `@testing-library/user-event==14.6.1`
- `@hey-api/openapi-ts==0.99.0`

`typescript==7.0.2` was rejected after real smoke testing because
`@hey-api/openapi-ts==0.99.0` failed import-time compatibility against it.
`typescript==6.0.3` matches the generator's compatible peer/dev line and passed.

`js-yaml==4.3.0` is pinned through npm `overrides` to keep the
`@hey-api/openapi-ts` dependency chain audit-clean without changing generator
class.

## Node Verification

Clean install root patterns:

- `C:\tmp\kurgu_control_plane_node_a_final_<timestamp>`
- `C:\tmp\kurgu_control_plane_node_b_final_<timestamp>`

Results:

- `npm ci --ignore-scripts` A: PASS
- `npm ci --ignore-scripts` B: PASS
- `npm audit`: PASS, 0 vulnerabilities
- `npm ls --depth=0`: exit PASS. npm reports two optional/native packages as
  extraneous in the full optional install; omitting optional dependencies breaks
  Vite/Rolldown native binding availability, so the accepted smoke path keeps
  optional dependencies installed.
- `npm run verify:toolchain` A: PASS
- `npm run verify:toolchain` B: PASS
- React/React DOM imports: PASS
- TypeScript import/version: PASS
- Vite API import: PASS
- React Vite plugin import: PASS
- Vitest import: PASS
- jsdom import: PASS
- Testing Library imports: PASS
- `@hey-api/openapi-ts` package import and CLI/bin availability: PASS

## Lock Stability

- `studio-ui/package-lock.json` was generated by npm, not by hand.
- Second-generation stability after resolver normalization:
  `5404B6F9CF7D32692BE5C197468EECDFB3B5CE70303F203DA2B25B4508C46D95`
  before and after `npm install --package-lock-only --ignore-scripts`.
- No pnpm, yarn, or bun lockfile was created.
- No repository `node_modules`, `dist`, or coverage directory was created.

## Parsing and Static Checks

- `studio-api/pyproject.toml` parse: PASS
- `studio-ui/package.json` parse: PASS
- `studio-ui/package-lock.json` parse: PASS
- `studio-api/requirements.lock` exact-pin syntax and alphabetical ordering:
  PASS
- New Python files compile with `python -B -m py_compile`: PASS

## Regression Tests

- Existing targeted contract/migrator regression:
  `213 passed, 1 skipped`
- Full suite with locked Studio API dependencies on `PYTHONPATH`:
  `272 passed, 1 skipped, 1 warning`
- No full video render was run.

## Security and Path Scan

- No package token, auth header, credential-bearing registry URI, or environment
  secret value was written.
- npm install was performed with `--ignore-scripts`; the smoke path did not
  require lifecycle script execution.
- `package-lock.json` contains normal public registry tarball URLs and integrity
  hashes only.
- `requirements.lock` contains exact package/version pins only.
- Current-tree secret/path scan result is recorded as PASS by the final task
  guard.

## Produced Artifacts

- `studio-api/pyproject.toml`
- `studio-api/requirements.lock`
- `studio-api/README.md`
- `studio-api/.gitignore`
- `studio-api/scripts/verify_toolchain.py`
- `studio-api/tests/test_toolchain_smoke.py`
- `studio-ui/package.json`
- `studio-ui/package-lock.json`
- `studio-ui/README.md`
- `studio-ui/.gitignore`
- `studio-ui/scripts/verify-toolchain.mjs`
- `.gitattributes`
- `baseline/phase1_control_plane_toolchain_report.md`

`.gitattributes` is a tooling-only addition required to keep the new toolchain
files and this report LF-normalized on Windows checkouts.

## Final Decision

Toolchain provisioning gate: PASS.

Faz 1 remains OPEN/IN_PROGRESS. This gate does not implement Studio API
endpoints, React UI source, shared schema distribution, generated OpenAPI, or
generated TypeScript client code.

Next gate: deterministic `shared-schemas/` distribution and OpenAPI skeleton
implementation slice.
