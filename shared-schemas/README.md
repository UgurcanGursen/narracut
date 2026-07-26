# Kurgu Shared Schemas

`schema/v3/` is the single canonical source for Kurgu V3 JSON Schema.
`shared-schemas/v3/` is a deterministic generated distribution for Studio
UI/client tooling and external contract consumers. Generated files in this
directory must not be edited by hand.

Canonical schema bytes are copied without parsing or reserialization, so every
`$id` and relative `$ref` remains unchanged. The Python engine and
`engine.contracts.SchemaCatalog` continue to load `schema/v3/` directly; this
package does not replace that lookup.

Generate or verify the distribution from the repository root:

```powershell
python -B scripts\sync_shared_schemas.py --write
python -B scripts\sync_shared_schemas.py --check
```

`--check` is read-only and fails on a missing, extra, or modified generated
schema or on manifest drift. `manifest.json` contains deterministic names,
relative paths, canonical `$id` values, and lowercase SHA-256 digests.

`openapi/openapi.json` is a separate generated artifact produced by the Studio
API exporter documented in `studio-api/README.md`. At this stage it contains
fixed application metadata and no endpoint contracts. A TypeScript client has
not been generated yet.
