# Phase 15 Source Audio Direction Implementation Authorization

Date: 2026-08-06
Decision: **AUTHORIZED — bounded local implementation only**

## Authorized change

Implement `SourceAudioDirectionValidator` exactly as specified in
`docs/specifications/phase15_source_audio_direction_contract.md`:

- a local Phase 15 validator over exact Phase 8 asset records, exact Phase 11
  audio-direction plans and one immutable Domain Pack snapshot;
- additive closed `source_audio_direction` evidence-reference support and
  `source_audio_safety` quality-check support in the Phase 15 ledger;
- canonical plan evidence binding, Phase 11 service recomputation and focused
  deterministic tests.

## Required outcomes

- no forged/missing/nonmatching input can yield PASS;
- contaminated or otherwise Phase-11-denied source speech is non-passing;
- source-speech direction preserves existing pause plus hard-duck/mute policy;
- non-speech PASS is explicitly only a direction-policy result;
- canonical JSONL and quality reducer remain fail closed for unknown tokens.

## Not authorized

Live source/asset/timing transport, provider calls, browser automation,
retry/queue/worker, media decode/classification, mixing/remixing, FFmpeg,
renderer or EDL mutation, Studio/UI, Phase 16, Phase 17, boundary analysis,
final-narration/domain-extension validation, host-wide orphan scans and Phase
15 Master closure.

## Documentation impact matrix

| Document | Impact | Action |
|---|---|---|
| `docs/CURRENT_STATE.md` | Implementation authorization state | Updated |
| `docs/CHANGELOG.md` | Authorization recorded | Updated |
| `docs/NEXT_ACTIONS.md` | One implementation task selected | Updated |
| `docs/KNOWN_LIMITATIONS.md` | Existing limitations remain accurate | Inspected, unchanged |
| `docs/PHASE_ACCEPTANCE.md` | No implementation acceptance yet | Inspected, unchanged |
| `docs/QUALITY_BENCHMARKS.md` | No benchmark impact | Inspected, unchanged |
| `docs/ARCHITECTURE_DECISIONS.md` | No ADR impact | Inspected, unchanged |
| `docs/MASTER_ROADMAP.md` | No roadmap edit | Inspected, unchanged |
