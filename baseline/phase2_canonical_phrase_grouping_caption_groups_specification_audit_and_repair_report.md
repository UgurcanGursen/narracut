# Phase 2 Canonical Phrase Grouping and Caption Groups Specification Audit and Repair

Date: 2026-08-04

Status: Original audit FIX_REQUIRED; bounded repair remote closed; targeted
re-audit required

## Audited candidate

- Original specification commit:
  `171078ca1c50a43ac9a395fe135e6bc044079b28`
- Audit repository HEAD:
  `3632bc94cdbc82c71c81a40dfe76c600c024be15`
- Original SHA-256:
  `d379e02e84883a08da66fd6289ca973d0f49a89f007bf68a524c7981dc7cbd46`
- Original UTF-8 byte length: `35784`
- Independent verdict: `FIX_REQUIRED`
- Finding counts: BLOCKER `0`, MAJOR `1`, MINOR `0`, INFO `0`
- Specification acceptance ready: `NO`

## Finding CGS-SPEC-AUD-001

Severity: MAJOR

The original error oracle left multiple valid pointer/reason/issue-code choices
through phrases such as “applicable issue code”, alternative range codes, and a
catch-all “first differing field” row. Two conforming implementations could
therefore reject the same malformed/multi-fault envelope differently.

The grouping algorithm, sentence-length/remainder properties, scope,
upstream-model compatibility, canonical encoding, and FX-CGS-01 golden values
all passed the independent audit. The repair was bounded solely to the error
contract and mandatory oracle tests.

## Bounded repair

- Repair commit: `5bd2401544693a9a0bfe9e3e9d398f96b786cb27`
- Parent: `3632bc94cdbc82c71c81a40dfe76c600c024be15`
- Subject: `docs: repair caption groups error oracle`
- Corrected specification SHA-256:
  `c0e8925e598bac0414c1c7b96adf256ed0f4072d2196efedf3b90b0961859baf`
- Corrected UTF-8 byte length: `43985`
- Exact changed path:
  `docs/specifications/phase2_canonical_phrase_grouping_caption_groups_contract.md`
- HEAD, `origin/main`, and live remote all equal the repair commit.

The correction:

- replaces alternative coverage/timing/confidence outcomes with closed tables;
- splits range reversal, empty/out-of-bounds, gap, overlap, and final-coverage
  conditions into fixed rows;
- fixes root/group structure, enum, dependency, range, policy, display, timing,
  confidence, identity, and loader-source outcomes;
- makes table/stage/index/model precedence normative;
- removes the catch-all “applicable code / first differing field” branch;
- removes unused issue codes and adds the actually used
  `TIMESTAMP_OUT_OF_BOUNDS`; and
- requires exact multi-fault oracle regression coverage.

## Manual repair verification

- Exactly one specification path changed: PASS.
- `git diff --check`: PASS.
- UTF-8/LF, no BOM/NUL/CR, numbered sections `1..24`: PASS.
- Ambiguous audit tokens removed: PASS.
- Embedded group/root golden JSON, lengths, hashes, and IDs unchanged and
  independently recomputed: PASS.
- Production, tests, fixtures, schemas, roadmap, APIs, and commercial services:
  unchanged/not used.

Manual verification is not a substitute for the required independent targeted
re-audit. The specification is not accepted and implementation is not
authorized.

## Next gate

Perform a targeted independent read-only re-audit of corrected blob
`c0e8925e...` at repair commit `5bd2401...`. The re-audit must verify closure of
`CGS-SPEC-AUD-001`, regression of the previously passing algorithm/golden/scope
dimensions, and zero new blocking findings.

## Documentation impact matrix

| Path | Impact |
|---|---|
| `docs/CURRENT_STATE.md` | Records FIX_REQUIRED, bounded repair, and targeted re-audit gate. |
| `docs/NEXT_ACTIONS.md` | Sets one targeted read-only re-audit task. |
| `docs/KNOWN_LIMITATIONS.md` | Keeps acceptance/implementation closed pending re-audit. |
| `docs/PHASE_ACCEPTANCE.md` | Records audit and repair without acceptance. |
| `docs/CHANGELOG.md` | Records exact audit/repair identities. |
| `docs/MASTER_ROADMAP.md` | Reviewed; unchanged. |
| Production, tests, fixtures, schemas | Unchanged. |

```text
ORIGINAL_SPECIFICATION_AUDIT=FIX_REQUIRED
CGS_SPEC_AUD_001_STATUS=REPAIRED_PENDING_TARGETED_REAUDIT
CORRECTED_SPECIFICATION_COMMIT=5bd2401544693a9a0bfe9e3e9d398f96b786cb27
CORRECTED_SPECIFICATION_SHA256=c0e8925e598bac0414c1c7b96adf256ed0f4072d2196efedf3b90b0961859baf
CORRECTED_SPECIFICATION_UTF8_BYTES=43985
SPECIFICATION_ACCEPTED=NO
IMPLEMENTATION_AUTHORIZED=NO
NEXT_ACTION=TARGETED_INDEPENDENT_READ_ONLY_REAUDIT
PHASE2_CLOSED=NO
TOTAL_PHASE2_SLICE_COUNT=UNKNOWN
PHASE2_COMPLETION_PERCENTAGE=NOT_STATED
```
