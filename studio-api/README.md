# Kurgu Studio API Toolchain

This directory is the Phase 1 thin Studio API dependency boundary. It does not
yet contain a FastAPI app factory, routes, DTOs, repository ports, or endpoint
implementation code.

The dependency set is isolated from the repository root `requirements.txt`.
It is intentionally limited to the future thin API surface and public V3
contract validation imports. WorkspaceStore, SQLite, renderer integration, and
durable persistence are out of scope for this provisioning gate.

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
$env:PYTHONPATH = (Get-Location).Path
& "$venv\Scripts\python.exe" studio-api\scripts\verify_toolchain.py
& "$venv\Scripts\python.exe" -B -m pytest -q studio-api\tests\test_toolchain_smoke.py -p no:cacheprovider
```

The smoke checks dependency imports, versions, a minimal FastAPI/TestClient
request, public engine contract imports, and canonical V3 schema validation.
