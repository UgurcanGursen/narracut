# Kurgu Studio API

This directory contains the Phase 1 thin Studio API dependency boundary and
the minimal application/OpenAPI generation foundation. It has a real FastAPI
application factory, but no routes, DTOs, application services, repository
ports, or endpoint implementation code.

The dependency set is isolated from the repository root `requirements.txt`.
It is intentionally limited to the future thin API surface and public V3
contract validation imports. WorkspaceStore, SQLite, renderer integration, and
durable persistence are out of scope for this provisioning gate.

## Application factory

`kurgu_studio_api.create_app()` returns a new, routes-free FastAPI instance on
every call. Application metadata and OpenAPI 3.1 behavior are fixed rather than
derived from the environment, current directory, hostname, time, or Git state.

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
or checks `shared-schemas/openapi/openapi.json`. The artifact currently proves
only deterministic generation and fixed application metadata; it intentionally
contains no project, status, artifact, health, or other endpoint contract.

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
