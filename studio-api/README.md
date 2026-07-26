# Kurgu Studio API

This directory contains the Phase 1 thin Studio API project contract slice.
It has a real FastAPI application factory, strict request/response DTOs, an
HTTP-independent application service, replaceable ports, and three endpoints:

```text
POST /api/v1/projects
GET  /api/v1/projects/{project_id}/status
GET  /api/v1/projects/{project_id}/artifacts
```

The dependency set is isolated from the repository root `requirements.txt`.
It is intentionally limited to the thin API surface and public V3 contract
validation imports. WorkspaceStore, SQLite, renderer integration, durable
persistence, authentication, and internet-facing deployment are not provided.

## Application factory

`kurgu_studio_api.create_app()` returns a new FastAPI instance and a new
in-memory project repository on every call. Application metadata and OpenAPI
3.1 behavior are fixed rather than derived from the environment, current
directory, hostname, time, or Git state.

Project persistence is explicitly process-lifetime only. A successful create
can be read from the same app instance, but a new app instance or process
restart starts with an empty catalog. There is no reopen, revision, recovery,
atomic disk persistence, WorkspaceStore, or production persistence guarantee.
Every successful response reports:

```json
{"persistence_scope": "process_lifetime"}
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
or checks `shared-schemas/openapi/openapi.json`. The artifact contains exactly
the three project contracts above. It contains no health, job, render,
update/delete, artifact-write, or other endpoint.

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
