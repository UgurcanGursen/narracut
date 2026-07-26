# Next Actions

Aktif faz: Faz 0 CLOSED. Faz 1 CLOSED. Faz 2 - Temporal Annotation and
Word-Level Alignment Contract specification entry.

1. **NEXT RECOMMENDED TASK - Faz 2:** read-only specification and acceptance
   design for the Temporal Annotation and Word-Level Alignment Contract.

   Tasarim; canonical narration ve script/transcript inputlarini, word/segment
   timestamps, confidence, unaligned spans, transcript divergence,
   pronunciation/number normalization, sentence/paragraph/section mapping,
   manual correction contract, local aligner boundary, paid fallback boundary,
   deterministic replay, provenance, model/provider/version metadata, failure
   and quality thresholds, downstream EDL compatibility, Windows path/security
   boundary, sample fixtures ve acceptance tests'i kesinlestirmelidir.

   Bu bir implementation gorevi degildir: paid API zorunlu olmayacak,
   local-first varsayilan korunacak ve capability execution policy sonraki
   tasarimlarda fail-closed kalacaktir.

## Deferred, not current work

- WorkspaceStore, SQLite, durable persistence, project recovery ve packaging
  Faz 14-17 sorumluluklarindadir.
- Provider automation ve Independent Editorial Critic Pipeline future binding
  kararlaridir; Faz 2 specification gorevinde uygulanmaz.
- Provider revoke/rotation ayri security/operations follow-up olarak kalir.
