# Phase 2 Caption Preview + V5/V6 Collision Specification Acceptance and Implementation Authorization

Decision date: 2026-08-04

## Decision identity

- Decision base `HEAD` and `origin/main`:
  `7aa6bdf43252b9d10c4d5db5cb0d2d5b882317f5`.
- Accepted specification:
  `docs/specifications/phase2_caption_preview_v5_v6_collision_contract.md`.
- Accepted UTF-8 byte length: `26542`.
- Accepted SHA-256:
  `515655084320700f01a6dd00deca16c843f4f28a514441488060f22e396638e7`.
- Final targeted independent audit: `PASS`.
- Findings: `BLOCKER=0 / MAJOR=0 / MINOR=0`.

## Decision

The bounded Phase 2 Caption Preview + V5/V6 Collision specification is
**ACCEPTED** and its implementation is **AUTHORIZED**.

Authorization is limited to:

```text
engine/contracts/caption_preview.py
engine/contracts/v5_v6_collision.py
tests/test_caption_preview.py
tests/test_v5_v6_collision.py
engine/contracts/__init__.py
tests/test_alignment_request.py
```

## Accepted boundary

- Inputs are limited to accepted `CaptionGroupsArtifact`,
  `EmphasisEventsArtifact`, and `WordToFrameArtifact`.
- V5 is a semantic proxy box; it does not claim to render real kinetic glyph
  text. V6 carries exact accepted caption display text.
- Geometry is sparse, normalized integer policy data. SVG is a pure in-memory
  diagnostic, not a bitmap or production renderer.
- Only positive V5/V6 spatiotemporal occlusion and safe-area violations are
  reported. Edge/corner touch is not a collision. There is no same-track
  scheduler, auto-repair, EDL, Remotion, V2 renderer, filesystem, UI, network,
  provider, or Phase 3/4 work.
- The policy-bearing preview golden independently parses as canonical JSON:
  `2195` bytes, SHA-256
  `c7d794557bcc304559117e4fbe0724bfd3e77c03180199ac277f0ee185fe6f73`,
  root `cprev_d31b9e…`.

## Implementation acceptance gate

The future implementation must pass focused literal/identity, genuine
dependency, Unicode/XML escaping, mutation/registry, half-open geometry,
safe-area, PASS/BLOCKED, adversarial parser, sparse complexity, upstream, and
broad non-FastAPI gates; then receive a fresh independent read-only audit.

```text
PHASE2_CAPTION_PREVIEW_COLLISION_SPECIFICATION_ACCEPTED=YES
PHASE2_CAPTION_PREVIEW_COLLISION_IMPLEMENTATION_AUTHORIZED=YES
IMPLEMENTATION_START_ALLOWED=YES
IMPLEMENTATION_ACCEPTANCE=OPEN
PHASE2_CLOSED=NO
```
