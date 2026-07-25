# Next Actions

Aktif faz: Faz 0 closed. Faz 1 - Editorial Domain Model ve V3 Workspace Schema IN_PROGRESS. V3 contract foundation PASS. Ayni anda en fazla bes is.

1. **NEXT RECOMMENDED TASK - Faz 1:** Secondary URI security fix post-commit
   independent re-audit; primary/secondary selection-independent fail-closed
   davranisi ve no-leak sonucunu salt-okunur dogrula.
2. Stock local-fallback path'i korunacaksa `v2.asset_manager.py` drawtext call-site icin explicit font contract hardening'i Faz 1 backlog'unda planla.
3. Provider revoke/rotation durumunu repo history replacement'tan ayri bir security takip maddesi olarak guncel tut.

## Faz 1 readiness

**CONTRACT FOUNDATION PASS / INTEGRITY HARDENING PASS / PUBLIC VALIDATION
BOUNDARY PASS / V2TOV3MIGRATOR PASS / STRUCTURED MIGRATION-LOSS REPORTING PASS /
MIGRATOR SECURITY HARDENING PASS / SECONDARY PROVENANCE URI HARDENING PASS /
WORKSPACESTORE ENTRY GATE
PENDING_INDEPENDENT_REAUDIT.** Faz 0 teknik acceptance ve management closure
PASS durumundadir. Re-audit PASS olmadan WorkspaceStore implementasyonuna
gecilmez. Production persistence, timing/frame, renderer integration ve Studio
API/UI isleri aciktir.
