param(
    [string]$ApiPython = "C:\Users\user\.codex\kurgu_studio_api_venv\Scripts\python.exe",
    [int]$ApiPort = 8000,
    [int]$UiPort = 5173
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not (Test-Path -LiteralPath $ApiPython)) { throw "FastAPI Python environment not found: $ApiPython" }
if (-not (Test-Path -LiteralPath (Join-Path $repoRoot "studio-ui\node_modules"))) { throw "Studio UI dependencies are not installed. Run npm ci in studio-ui." }

$env:PYTHONPATH = "$repoRoot;$repoRoot\studio-api\src"
Start-Process -FilePath $ApiPython -ArgumentList @("-m", "uvicorn", "kurgu_studio_api.app:create_app", "--factory", "--port", "$ApiPort") -WorkingDirectory $repoRoot -WindowStyle Hidden
Start-Process -FilePath "npm.cmd" -ArgumentList @("run", "dev", "--", "--port", "$UiPort") -WorkingDirectory (Join-Path $repoRoot "studio-ui") -WindowStyle Hidden
Write-Output "Studio started: API http://127.0.0.1:$ApiPort/health ; UI http://127.0.0.1:$UiPort"
