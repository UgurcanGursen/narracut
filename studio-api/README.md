# Kurgu Studio API

This directory contains the Phase 13 local Studio control plane. It has a real
FastAPI application factory, strict request/response DTOs, HTTP-independent
application services and replaceable infrastructure ports. The public API
supports project create/list/reopen, Manual LLM task lifecycle, and read-only
hash-bound sequence review decisions.

```text
POST /api/v1/projects
GET  /api/v1/projects/{project_id}/status
GET  /api/v1/projects/{project_id}/artifacts
GET/POST /api/v1/projects/{project_id}/tasks
POST /api/v1/projects/{project_id}/tasks/{task_id}/response
POST /api/v1/projects/{project_id}/tasks/{task_id}/approve
POST /api/v1/projects/{project_id}/tasks/{task_id}/repair
GET  /api/v1/projects/{project_id}/review
GET/POST review snapshot and sequence decision endpoints
```

The dependency set is isolated from the repository root `requirements.txt`.
It is intentionally limited to the Studio API surface and public engine
contract imports. Authentication, internet-facing deployment, provider calls,
browser automation, renderer invocation, job queues and media transport are
not provided.

## Application factory

`kurgu_studio_api.create_app()` returns a new FastAPI instance with a local
SQLite project repository by default. Fresh application instances reopen the
same local Studio state. Tests can inject the in-memory repository through a
custom runtime to isolate a unit boundary. Application metadata and OpenAPI
3.1 behavior are fixed rather than derived from hostname, time or Git state.

Project persistence is explicitly reported by every project response:

```json
{"persistence_scope": "local_sqlite"}
```

## Public domain eligibility

Domain-pack registry discovery and public Project API eligibility are separate
boundaries. Discovery may load contract examples for internal contract
validation; it does not make those packs available to project creation.

The public API uses an immutable, application-owned allowlist. The currently
eligible domain-pack binding is:

```text
business-tech@0.1.0
  profile: dpf_business_default
```

Other domain/version combinations, including contract-example packs, are
reported as `DOMAIN_UNKNOWN` so the API does not reveal whether a non-eligible
pack was discovered. A validly formatted profile that is not bound to the
selected eligible pack returns `DOMAIN_PROFILE_MISMATCH`. The client cannot
extend the allowlist through request fields, environment variables, or a
configuration path.

`core_only` remains a separate supported mode using
`core-generic@0.0.0` and `dpf_core_default`; it does not depend on the
domain-pack eligibility allowlist.

The package is imported directly from `studio-api/src`; editable installation
is not required:

```powershell
$env:PYTHONPATH = "$(Get-Location)\studio-api\src"
& "$venv\Scripts\python.exe" -B -c "from kurgu_studio_api import create_app; print(create_app().openapi())"
```

## Deterministic OpenAPI

The committed OpenAPI artifact is generated from `create_app()`:

```powershell
$env:PYTHONPATH = "$(Get-Location)\studio-api\src"
& "$venv\Scripts\python.exe" -B -m kurgu_studio_api.openapi_export --write
& "$venv\Scripts\python.exe" -B -m kurgu_studio_api.openapi_export --check
```

The exporter accepts no app import target and no output path. It always writes
or checks `shared-schemas/openapi/openapi.json`. Task and review operations are
included; no health, provider, media-open, render, queue/retry or artifact
lifecycle-write endpoint is included.

## Clean venv install

```powershell
$venv = "C:\tmp\kurgu_control_plane_python_verify"
python -m venv $venv
& "$venv\Scripts\python.exe" -m pip install -r studio-api\requirements.lock
```

`requirements.lock` is a clean-environment resolved exact-version lock. It is
not a hash-secured package lock.

## Toolchain smoke

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYTHONPATH = "$(Get-Location);$(Get-Location)\studio-api\src"
& "$venv\Scripts\python.exe" studio-api\scripts\verify_toolchain.py
& "$venv\Scripts\python.exe" -B -m pytest -q studio-api\tests\test_toolchain_smoke.py -p no:cacheprovider
```

The smoke checks dependency imports, versions, a minimal FastAPI/TestClient
request, public engine contract imports, and canonical V3 schema validation.

## Run the local API

Using the locked environment:

```powershell
$env:PYTHONPATH = "$(Get-Location);$(Get-Location)\studio-api\src"
& "$venv\Scripts\python.exe" -B -m uvicorn `
  "kurgu_studio_api.app:create_app" --factory
```

This local command does not add authentication or make an internet-facing
deployment claim. Studio UI source and a generated TypeScript client do not
exist in this slice.
