# V2 to V3 Migration Report

## Summary

- Source: `input_v2.json`
- Source format/version: `kurgu-v2-timeline` / `2.2`
- Target format/version: `kurgu-v3-workspace` / `3.0.0`
- Mode: `permissive`
- Resolution mode: `core_only`
- Status: **SUCCESS_WITH_LOSS**
- Source fingerprint: `sha256:bf4527509e69d7425a0100437444d4f48948d296edc178f5f33773c041a7aa21`
- Target fingerprint: `sha256:87dd15461eb9a70f2c8d336fe5f80272521ea1a2a9143981369ee58ed48d4b1f`
- Workspace ID: `wsp_bf4527509e69d7425a01`

## Classification counts

| Classification | Count |
|---|---:|
| EXACT | 0 |
| RENAMED | 0 |
| NORMALIZED | 35 |
| SPLIT | 0 |
| MERGED | 10 |
| DEFAULTED | 2 |
| DERIVED | 2 |
| PRESERVED_AS_EXTENSION | 0 |
| DROPPED | 18 |
| UNSUPPORTED | 2 |
| AMBIGUOUS | 0 |
| INVALID_SOURCE | 0 |

## Losses and issues

### MIGRATION_FIELD_UNSUPPORTED — WARNING

- Issue ID: `mig_f6aae425ee395817c6ff`
- Source: `/blocks/0/audio_file`
- Destination: `(none)`
- Classification: `UNSUPPORTED`
- Message: V2 block field 'audio_file' has no Phase 1 canonical destination.
- Resolution: Review the migration report.

### MIGRATION_FIELD_DROPPED — WARNING

- Issue ID: `mig_c7f5fcf8747955ea0e2f`
- Source: `/blocks/0/bgm_drop`
- Destination: `(none)`
- Classification: `DROPPED`
- Message: V2 block field 'bgm_drop' has no Phase 1 canonical destination.
- Resolution: Review the migration report.

### MIGRATION_FIELD_DROPPED — WARNING

- Issue ID: `mig_7d49f833fdb828d798b1`
- Source: `/blocks/0/pause_after`
- Destination: `(none)`
- Classification: `DROPPED`
- Message: V2 block field 'pause_after' has no Phase 1 canonical destination.
- Resolution: Review the migration report.

### MIGRATION_FIELD_DROPPED — WARNING

- Issue ID: `mig_b81dae9b2f03ef0513b5`
- Source: `/blocks/0/pause_before`
- Destination: `(none)`
- Classification: `DROPPED`
- Message: V2 block field 'pause_before' has no Phase 1 canonical destination.
- Resolution: Review the migration report.

### MIGRATION_FIELD_DROPPED — WARNING

- Issue ID: `mig_46dcba2f2203a3672101`
- Source: `/blocks/0/visuals/0/fit_mode`
- Destination: `(none)`
- Classification: `DROPPED`
- Message: V2 visual field 'fit_mode' has no Phase 1 canonical destination.
- Resolution: Review the migration report.

### MIGRATION_FIELD_DROPPED — WARNING

- Issue ID: `mig_e33b1e386ceccc8b72b2`
- Source: `/blocks/0/visuals/0/subtitle_policy`
- Destination: `(none)`
- Classification: `DROPPED`
- Message: V2 visual field 'subtitle_policy' has no Phase 1 canonical destination.
- Resolution: Review the migration report.

### MIGRATION_FIELD_DROPPED — WARNING

- Issue ID: `mig_fd4acbc1f79a9f0adb7b`
- Source: `/blocks/0/visuals/0/transition_out`
- Destination: `(none)`
- Classification: `DROPPED`
- Message: V2 visual field 'transition_out' has no Phase 1 canonical destination.
- Resolution: Review the migration report.

### MIGRATION_FIELD_DROPPED — WARNING

- Issue ID: `mig_4ea6e56b40131ed0b278`
- Source: `/blocks/0/visuals/1/fit_mode`
- Destination: `(none)`
- Classification: `DROPPED`
- Message: V2 visual field 'fit_mode' has no Phase 1 canonical destination.
- Resolution: Review the migration report.

### MIGRATION_FIELD_DEFAULTED — WARNING

- Issue ID: `mig_99f821523ea25792d4f0`
- Source: `/blocks/0/visuals/1/offset_end`
- Destination: `/sequences/0/edit_events/1`
- Classification: `DEFAULTED`
- Message: AUTO has no frame value in the Phase 1 semantic cue model.
- Resolution: Review the migration report.

### MIGRATION_FIELD_DROPPED — WARNING

- Issue ID: `mig_4e14cf9b55000ed1b8d9`
- Source: `/blocks/0/visuals/1/subtitle_policy`
- Destination: `(none)`
- Classification: `DROPPED`
- Message: V2 visual field 'subtitle_policy' has no Phase 1 canonical destination.
- Resolution: Review the migration report.

### MIGRATION_FIELD_DROPPED — WARNING

- Issue ID: `mig_c5da8a45b26ce9e44684`
- Source: `/blocks/0/visuals/1/transition_out`
- Destination: `(none)`
- Classification: `DROPPED`
- Message: V2 visual field 'transition_out' has no Phase 1 canonical destination.
- Resolution: Review the migration report.

### MIGRATION_FIELD_UNSUPPORTED — WARNING

- Issue ID: `mig_bece61ab49bef4707459`
- Source: `/blocks/1/audio_file`
- Destination: `(none)`
- Classification: `UNSUPPORTED`
- Message: V2 block field 'audio_file' has no Phase 1 canonical destination.
- Resolution: Review the migration report.

### MIGRATION_FIELD_DROPPED — WARNING

- Issue ID: `mig_8a6f447b779bfccf0744`
- Source: `/blocks/1/bgm_drop`
- Destination: `(none)`
- Classification: `DROPPED`
- Message: V2 block field 'bgm_drop' has no Phase 1 canonical destination.
- Resolution: Review the migration report.

### MIGRATION_FIELD_DROPPED — WARNING

- Issue ID: `mig_b3785da45157e18d8c40`
- Source: `/blocks/1/pause_after`
- Destination: `(none)`
- Classification: `DROPPED`
- Message: V2 block field 'pause_after' has no Phase 1 canonical destination.
- Resolution: Review the migration report.

### MIGRATION_FIELD_DROPPED — WARNING

- Issue ID: `mig_1102936f339f16ebc34e`
- Source: `/blocks/1/pause_before`
- Destination: `(none)`
- Classification: `DROPPED`
- Message: V2 block field 'pause_before' has no Phase 1 canonical destination.
- Resolution: Review the migration report.

### MIGRATION_FIELD_DROPPED — WARNING

- Issue ID: `mig_6fd2323749b8984f95dd`
- Source: `/blocks/1/visuals/0/fit_mode`
- Destination: `(none)`
- Classification: `DROPPED`
- Message: V2 visual field 'fit_mode' has no Phase 1 canonical destination.
- Resolution: Review the migration report.

### MIGRATION_FIELD_DROPPED — WARNING

- Issue ID: `mig_039b101a4068496de1b4`
- Source: `/blocks/1/visuals/0/subtitle_policy`
- Destination: `(none)`
- Classification: `DROPPED`
- Message: V2 visual field 'subtitle_policy' has no Phase 1 canonical destination.
- Resolution: Review the migration report.

### MIGRATION_FIELD_DROPPED — WARNING

- Issue ID: `mig_fa2fa572405f8e782921`
- Source: `/blocks/1/visuals/0/transition_out`
- Destination: `(none)`
- Classification: `DROPPED`
- Message: V2 visual field 'transition_out' has no Phase 1 canonical destination.
- Resolution: Review the migration report.

### MIGRATION_FIELD_DROPPED — WARNING

- Issue ID: `mig_74a84d31dbae41754b4a`
- Source: `/blocks/1/visuals/1/fit_mode`
- Destination: `(none)`
- Classification: `DROPPED`
- Message: V2 visual field 'fit_mode' has no Phase 1 canonical destination.
- Resolution: Review the migration report.

### MIGRATION_FIELD_DEFAULTED — WARNING

- Issue ID: `mig_32709f2e40697aa4e7b7`
- Source: `/blocks/1/visuals/1/offset_end`
- Destination: `/sequences/1/edit_events/1`
- Classification: `DEFAULTED`
- Message: AUTO has no frame value in the Phase 1 semantic cue model.
- Resolution: Review the migration report.

### MIGRATION_FIELD_DROPPED — WARNING

- Issue ID: `mig_a81335126e900895f34e`
- Source: `/blocks/1/visuals/1/subtitle_policy`
- Destination: `(none)`
- Classification: `DROPPED`
- Message: V2 visual field 'subtitle_policy' has no Phase 1 canonical destination.
- Resolution: Review the migration report.

### MIGRATION_FIELD_DROPPED — WARNING

- Issue ID: `mig_316054fd400a9df89c5e`
- Source: `/blocks/1/visuals/1/transition_out`
- Destination: `(none)`
- Classification: `DROPPED`
- Message: V2 visual field 'transition_out' has no Phase 1 canonical destination.
- Resolution: Review the migration report.

## Source to destination mapping

| Source | Destination | Classification | Transformation |
|---|---|---|---|
| `/` | `/project/project_id` | DERIVED | Derive from canonical source fingerprint. |
| `/` | `/workspace_id` | DERIVED | Derive from canonical source fingerprint. |
| `/blocks/0/audio_file` | `(report only)` | UNSUPPORTED | Record without inventing timing/renderer state. |
| `/blocks/0/bgm_drop` | `(report only)` | DROPPED | Record without inventing timing/renderer state. |
| `/blocks/0/block_id` | `/story/beats/0/beat_id` | NORMALIZED | Normalize to canonical beat_/seq_ namespaces. |
| `/blocks/0/fill_policy` | `/sequences/0/fallback_policy` | MERGED | Merge block and visual policies into one fail-closed policy. |
| `/blocks/0/narration` | `/sequences/0/narrative_goal` | NORMALIZED | Preserve the complete text as the aggregate editorial goal. |
| `/blocks/0/pause_after` | `(report only)` | DROPPED | Record without inventing timing/renderer state. |
| `/blocks/0/pause_before` | `(report only)` | DROPPED | Record without inventing timing/renderer state. |
| `/blocks/0/visuals/0/allow_generic_stock` | `/sequences/0/fallback_policy` | MERGED | Merge per-visual behavior into the sequence policy. |
| `/blocks/0/visuals/0/extra/asset_id` | `/assets/0/asset_id` | NORMALIZED | Normalize to canonical ast_/art_ namespaces. |
| `/blocks/0/visuals/0/extra/asset_mode` | `/assets/0/availability` | NORMALIZED | Map locked_local to local approved media. |
| `/blocks/0/visuals/0/extra/expected_sha256` | `/assets/0/content_hash` | NORMALIZED | Normalize the SHA-256 prefix and case. |
| `/blocks/0/visuals/0/extra/resolved_path` | `(report only)` | NORMALIZED | Normalize local paths/search terms to a portable URN; retain URIs. |
| `/blocks/0/visuals/0/fill_policy` | `/sequences/0/fallback_policy` | MERGED | Merge per-visual behavior into the sequence policy. |
| `/blocks/0/visuals/0/fit_mode` | `(report only)` | DROPPED | Record without inventing renderer/timing contracts. |
| `/blocks/0/visuals/0/offset_end` | `/sequences/0/edit_events/0` | NORMALIZED | Preserve an explicit semantic boundary or resolve AUTO by order. |
| `/blocks/0/visuals/0/offset_start` | `/sequences/0/edit_events/0/timing_ref` | NORMALIZED | Encode explicit offsets as semantic markers. |
| `/blocks/0/visuals/0/subtitle_policy` | `(report only)` | DROPPED | Record without inventing renderer/timing contracts. |
| `/blocks/0/visuals/0/transition_in` | `/sequences/0/edit_events/0/event_type` | NORMALIZED | Map hard cuts to cut; retain the visual event for other transitions. |
| `/blocks/0/visuals/0/transition_out` | `(report only)` | DROPPED | Record without inventing renderer/timing contracts. |
| `/blocks/0/visuals/0/type` | `/assets/0/asset_type` | NORMALIZED | Map the known V2 renderer type to canonical asset semantics. |
| `/blocks/0/visuals/1/allow_generic_stock` | `/sequences/0/fallback_policy` | MERGED | Merge per-visual behavior into the sequence policy. |
| `/blocks/0/visuals/1/extra/asset_id` | `/assets/1/asset_id` | NORMALIZED | Normalize to canonical ast_/art_ namespaces. |
| `/blocks/0/visuals/1/extra/asset_mode` | `/assets/1/availability` | NORMALIZED | Map locked_local to local approved media. |
| `/blocks/0/visuals/1/extra/expected_sha256` | `/assets/1/content_hash` | NORMALIZED | Normalize the SHA-256 prefix and case. |
| `/blocks/0/visuals/1/extra/resolved_path` | `(report only)` | NORMALIZED | Normalize local paths/search terms to a portable URN; retain URIs. |
| `/blocks/0/visuals/1/fill_policy` | `/sequences/0/fallback_policy` | MERGED | Merge per-visual behavior into the sequence policy. |
| `/blocks/0/visuals/1/fit_mode` | `(report only)` | DROPPED | Record without inventing renderer/timing contracts. |
| `/blocks/0/visuals/1/offset_end` | `/sequences/0/edit_events/1` | DEFAULTED | Preserve an explicit semantic boundary or resolve AUTO by order. |
| `/blocks/0/visuals/1/offset_start` | `/sequences/0/edit_events/1/timing_ref` | NORMALIZED | Encode explicit offsets as semantic markers. |
| `/blocks/0/visuals/1/subtitle_policy` | `(report only)` | DROPPED | Record without inventing renderer/timing contracts. |
| `/blocks/0/visuals/1/transition_in` | `/sequences/0/edit_events/1/event_type` | NORMALIZED | Map hard cuts to cut; retain the visual event for other transitions. |
| `/blocks/0/visuals/1/transition_out` | `(report only)` | DROPPED | Record without inventing renderer/timing contracts. |
| `/blocks/0/visuals/1/type` | `/assets/1/asset_type` | NORMALIZED | Map the known V2 renderer type to canonical asset semantics. |
| `/blocks/1/audio_file` | `(report only)` | UNSUPPORTED | Record without inventing timing/renderer state. |
| `/blocks/1/bgm_drop` | `(report only)` | DROPPED | Record without inventing timing/renderer state. |
| `/blocks/1/block_id` | `/story/beats/1/beat_id` | NORMALIZED | Normalize to canonical beat_/seq_ namespaces. |
| `/blocks/1/fill_policy` | `/sequences/1/fallback_policy` | MERGED | Merge block and visual policies into one fail-closed policy. |
| `/blocks/1/narration` | `/sequences/1/narrative_goal` | NORMALIZED | Preserve the complete text as the aggregate editorial goal. |
| `/blocks/1/pause_after` | `(report only)` | DROPPED | Record without inventing timing/renderer state. |
| `/blocks/1/pause_before` | `(report only)` | DROPPED | Record without inventing timing/renderer state. |
| `/blocks/1/visuals/0/allow_generic_stock` | `/sequences/1/fallback_policy` | MERGED | Merge per-visual behavior into the sequence policy. |
| `/blocks/1/visuals/0/extra/asset_id` | `/assets/2/asset_id` | NORMALIZED | Normalize to canonical ast_/art_ namespaces. |
| `/blocks/1/visuals/0/extra/asset_mode` | `/assets/2/availability` | NORMALIZED | Map locked_local to local approved media. |
| `/blocks/1/visuals/0/extra/expected_sha256` | `/assets/2/content_hash` | NORMALIZED | Normalize the SHA-256 prefix and case. |
| `/blocks/1/visuals/0/extra/resolved_path` | `(report only)` | NORMALIZED | Normalize local paths/search terms to a portable URN; retain URIs. |
| `/blocks/1/visuals/0/fill_policy` | `/sequences/1/fallback_policy` | MERGED | Merge per-visual behavior into the sequence policy. |
| `/blocks/1/visuals/0/fit_mode` | `(report only)` | DROPPED | Record without inventing renderer/timing contracts. |
| `/blocks/1/visuals/0/offset_end` | `/sequences/1/edit_events/0` | NORMALIZED | Preserve an explicit semantic boundary or resolve AUTO by order. |
| `/blocks/1/visuals/0/offset_start` | `/sequences/1/edit_events/0/timing_ref` | NORMALIZED | Encode explicit offsets as semantic markers. |
| `/blocks/1/visuals/0/subtitle_policy` | `(report only)` | DROPPED | Record without inventing renderer/timing contracts. |
| `/blocks/1/visuals/0/transition_in` | `/sequences/1/edit_events/0/event_type` | NORMALIZED | Map hard cuts to cut; retain the visual event for other transitions. |
| `/blocks/1/visuals/0/transition_out` | `(report only)` | DROPPED | Record without inventing renderer/timing contracts. |
| `/blocks/1/visuals/0/type` | `/assets/2/asset_type` | NORMALIZED | Map the known V2 renderer type to canonical asset semantics. |
| `/blocks/1/visuals/1/allow_generic_stock` | `/sequences/1/fallback_policy` | MERGED | Merge per-visual behavior into the sequence policy. |
| `/blocks/1/visuals/1/extra/asset_id` | `/assets/3/asset_id` | NORMALIZED | Normalize to canonical ast_/art_ namespaces. |
| `/blocks/1/visuals/1/extra/asset_mode` | `/assets/3/availability` | NORMALIZED | Map locked_local to local approved media. |
| `/blocks/1/visuals/1/extra/expected_sha256` | `/assets/3/content_hash` | NORMALIZED | Normalize the SHA-256 prefix and case. |
| `/blocks/1/visuals/1/extra/resolved_path` | `(report only)` | NORMALIZED | Normalize local paths/search terms to a portable URN; retain URIs. |
| `/blocks/1/visuals/1/fill_policy` | `/sequences/1/fallback_policy` | MERGED | Merge per-visual behavior into the sequence policy. |
| `/blocks/1/visuals/1/fit_mode` | `(report only)` | DROPPED | Record without inventing renderer/timing contracts. |
| `/blocks/1/visuals/1/offset_end` | `/sequences/1/edit_events/1` | DEFAULTED | Preserve an explicit semantic boundary or resolve AUTO by order. |
| `/blocks/1/visuals/1/offset_start` | `/sequences/1/edit_events/1/timing_ref` | NORMALIZED | Encode explicit offsets as semantic markers. |
| `/blocks/1/visuals/1/subtitle_policy` | `(report only)` | DROPPED | Record without inventing renderer/timing contracts. |
| `/blocks/1/visuals/1/transition_in` | `/sequences/1/edit_events/1/event_type` | NORMALIZED | Map hard cuts to cut; retain the visual event for other transitions. |
| `/blocks/1/visuals/1/transition_out` | `(report only)` | DROPPED | Record without inventing renderer/timing contracts. |
| `/blocks/1/visuals/1/type` | `/assets/3/asset_type` | NORMALIZED | Map the known V2 renderer type to canonical asset semantics. |
| `/version` | `/source_schema_version` | NORMALIZED | Convert the orchestration version marker to text. |

## Manual review

- `mig_f6aae425ee395817c6ff`: Review the migration report.
- `mig_c7f5fcf8747955ea0e2f`: Review the migration report.
- `mig_7d49f833fdb828d798b1`: Review the migration report.
- `mig_b81dae9b2f03ef0513b5`: Review the migration report.
- `mig_46dcba2f2203a3672101`: Review the migration report.
- `mig_e33b1e386ceccc8b72b2`: Review the migration report.
- `mig_fd4acbc1f79a9f0adb7b`: Review the migration report.
- `mig_4ea6e56b40131ed0b278`: Review the migration report.
- `mig_99f821523ea25792d4f0`: Review the migration report.
- `mig_4e14cf9b55000ed1b8d9`: Review the migration report.
- `mig_c5da8a45b26ce9e44684`: Review the migration report.
- `mig_bece61ab49bef4707459`: Review the migration report.
- `mig_8a6f447b779bfccf0744`: Review the migration report.
- `mig_b3785da45157e18d8c40`: Review the migration report.
- `mig_1102936f339f16ebc34e`: Review the migration report.
- `mig_6fd2323749b8984f95dd`: Review the migration report.
- `mig_039b101a4068496de1b4`: Review the migration report.
- `mig_fa2fa572405f8e782921`: Review the migration report.
- `mig_74a84d31dbae41754b4a`: Review the migration report.
- `mig_32709f2e40697aa4e7b7`: Review the migration report.
- `mig_a81335126e900895f34e`: Review the migration report.
- `mig_316054fd400a9df89c5e`: Review the migration report.

## Validation

- Workspace schema: `True`
- Workspace loader: `True`
- Migration result schema: `True`
