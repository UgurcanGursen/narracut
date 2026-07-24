# Faz 0.2 — Numeric Equivalence Fix Report

Tarih: 24 Temmuz 2026
Başlangıç baseline: `81d6a75241f56b8918732edb6a776c4d5030a71c`

## Reproduced failure and root cause

`tests/test_adversarial_alignment.py::test_numeric_equivalent` production
değişikliğinden önce yeniden çalıştırıldı ve `score=0.0` ile başarısız oldu.

`v2.number_normalizer.canonicalize_numbers`, spoken cue için
`<NUM:17000000000>`; currency-qualified transcript için
`<NUM:USD:17000000000>` üretir. `v2.audio_engine.find_cue_time` içindeki
`_norm_text`, noktalama temizliğiyle bu canonical token'ların `<`, `:` ve `>`
işaretlerini kaldırıyordu. SequenceMatcher prefilter aday pencereyi eliyor;
sonraki numeric-aware local alignment hiç çalışmıyordu. Bu bir production
bug'ıdır, test beklentisi doğrudur.

## Production fix

`v2/audio_engine.py` içinde canonical numeric token parser'ı ve generic
equivalence helper'ı eklendi. `find_cue_time` canonical token'ları korur ve
aynı helper'ı candidate prefilter, dynamic-programming/backtracking alignment
ve semantic-number skoru için kullanır. Hiçbir değer veya ifade hard-code
edilmedi.

## Numeric equivalence contract

- Aynı `Decimal` numeric value eşdeğerdir.
- Plain number cue, aynı değerli currency-qualified transcript token'ını anchor
  olarak kullanabilir.
- Farklı numeric value, integer/decimal farkı, percentage/non-percentage ve iki
  farklı açık currency qualifier eşdeğer değildir.
- Çevre metin hâlâ seçilen anchor'ın zamanını belirler.

## Added positive and negative tests

Pozitif: unqualified cue/currency transcript, punctuation bağımsızlığı ve
surrounding-context timestamp seçimi. Negatif: farklı değer, `17.5` ile `17`,
ve USD/EUR gibi açık currency mismatch.

## Test results

- Reproduction: 1 failed before fix.
- Hedef alignment/audio grupları: `14 passed`.
- Tam suite: `41 passed, 1 failed`.
- Kalan tek failure:
  `tests/test_v2_core.py::TestV2Core::test_pexels_key_missing_fallback`; test
  string path beklerken production canonical metadata dict döndürür.
- `python -m py_compile v2/audio_engine.py tests/test_adversarial_alignment.py`:
  PASS.
- `git diff --check`: PASS.

## Regression assessment and remaining Phase 0 blockers

Değişiklik yalnız numeric cue alignment sözleşmesini etkiler; renderer,
delegation, schema, UI, domain pack veya Pexels production contract değiştirilmedi.
Faz 0 için kalan blocker'lar provider revoke/rotation teyidi, stale Pexels test
contract hizalaması, system `ffmpeg`/`ffprobe` preflight'ı ve isolated,
fail-closed offline full-render kanıtıdır.
