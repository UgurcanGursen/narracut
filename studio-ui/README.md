# Kurgu Studio UI

This directory contains the Phase 1 React 19, TypeScript, and Vite Studio
shell. It creates a project through the thin Studio API, then reads the
project status and artifact collection returned by the real HTTP contracts.

The browser boundary is intentionally narrow:

```text
React component
  -> handwritten StudioApi facade
  -> generated operation
  -> bundled generated fetch client
  -> HTTP
  -> FastAPI
```

React source does not access repository files, shared-schema files, Python
modules, or backend functions. It does not call `fetch` directly. The
handwritten facade owns one generated HTTP client per instance and defaults to
same-origin requests.

## Generated client

`../shared-schemas/openapi/openapi.json` is the only client-generation input.
`@hey-api/openapi-ts@0.99.0` generates the committed files under
`src/generated/kurgu-api/`. The official bundled fetch client is used, so
there is no separate runtime client dependency.

Generated files must not be edited by hand:

```powershell
npm run generate:client
npm run check:client
```

Generation uses fixed input and output paths. The check command generates two
fresh copies under the system drive's `tmp` directory, compares their
inventories and bytes, compares the committed output, and exercises
missing/extra/modified/stale drift negatives without changing committed files.

## Clean validation

Install and validate only in a clean copy outside the repository:

```powershell
npm ci --ignore-scripts
npm run verify:toolchain
npm run check:client
npm run typecheck
npm test
npm run verify:http-boundary
npm run build
```

`npm test` excludes the live test. `npm run test:live` requires
`KURGU_STUDIO_API_BASE_URL` and a running local API. The live test is only for a
local FastAPI process: the URL must be loopback HTTP (`127.0.0.1`, `localhost`,
or `[::1]`) with an explicit port, including explicit default port `:80`, and
no path, query, fragment, or credentials. Remote endpoints are rejected before
any project-create request is made; this live guard does not change the
production Studio API facade's normal HTTP/HTTPS support. The test does not
start the API server; the external harness must start Uvicorn first.

## Local development

Run the locked Studio API on `127.0.0.1:8000` as documented in
`../studio-api/README.md`, then:

```powershell
npm run dev
```

Vite proxies same-origin `/api` requests to `http://127.0.0.1:8000`, so no
CORS change is required. No committed environment-specific server URL is used.

## Supported scope and limitations

The create form offers only:

- Core only
- Business & Technology (`business-tech@0.1.0`,
  `dpf_business_default`)

The `true-crime-legal` contract example is not a public project option.
Project IDs and workspace/output paths are server-owned and are not editable
in the UI.

Project persistence is process-lifetime in memory. Restarting the API clears
created projects. There is no WorkspaceStore, SQLite, durable reopen,
authentication, upload, render/job orchestration, progress stream, or
artifact-write operation in this shell. This local developer slice makes no
production internet-deployment claim.
