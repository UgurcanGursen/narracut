# Kurgu Studio UI Toolchain

This directory is the Phase 1 React + TypeScript + Vite dependency boundary.
It does not yet contain the React shell, Vite app source, generated OpenAPI
client, or UI tests.

The package manager for this workspace is npm only. `package-lock.json` is the
canonical Node lockfile; pnpm and yarn are intentionally not used.

## Clean npm install

```powershell
$copy = "C:\tmp\kurgu_control_plane_node_verify"
New-Item -ItemType Directory -Path $copy
Copy-Item studio-ui\package.json, studio-ui\package-lock.json -Destination $copy
Copy-Item studio-ui\scripts -Destination $copy -Recurse
Push-Location $copy
npm ci --ignore-scripts
npm run verify:toolchain
Pop-Location
```

`node_modules/`, `dist/`, coverage, cache output, and local environment override
files must not be committed.

OpenAPI/client generation is a later Phase 1 gate after the canonical OpenAPI
artifact exists.
