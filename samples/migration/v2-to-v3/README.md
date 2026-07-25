# V2 to V3 Migration Demo

This demo input is a byte-preserving copy of the Phase 0 offline production
fixture contract. It contains two narration blocks, four locked local stock
visuals, explicit offsets, deterministic asset hashes, and renderer-specific
settings that exercise structured migration-loss reporting.

Run from the repository root:

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
python -B -m engine.migration.cli migrate `
  --input samples/migration/v2-to-v3/input_v2.json `
  --output C:\tmp\kurgu-v2-to-v3-demo `
  --mode permissive `
  --resolution-mode core_only
```

The `expected/` directory contains the canonical byte-for-byte output:

- `workspace.json`
- `migration_result.json`
- `migration_report.md`
- `inspection_summary.txt`

The workspace uses aggregate layout. The migration succeeds with explicitly
reported loss because V2 audio-file, pause, subtitle, fit, and transition-out
renderer details have no Phase 1 canonical V3 destination.
