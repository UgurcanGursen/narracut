# Phase 13 Renderer Control-Plane Implementation Authorization Decision

Date: 2026-08-06
Contract: `docs/specifications/phase13_renderer_control_plane_integration_contract.md`

## Decision

**NOT AUTHORIZED.**

The control-plane specification is sound, but the repository has no canonical
server-side `RenderInputSnapshotV1` source that can satisfy its trusted
admission prerequisite for a real Studio project.

## Evidence

| Required input | Current Studio review snapshot | Result |
|---|---|---|
| Phase 12 executable-plan identity | Stored and hash-validated | Available |
| Phase 3 video/audio EDL IDs and hashes | Stored as `sequence_edls` references | Available as references only |
| Canonical video/audio EDL bytes and loaders | Not stored or resolved by Studio | Missing |
| Phase 4 `RenderProps` and fixture binding | Not stored or resolvable from the review snapshot | Missing |
| Trusted project/sequence render-input resolver | No application port or infrastructure adapter | Missing |

The accepted Phase 4 renderer is REPLAY fixture-bound. Its `build_render_props`
requires actual Phase 3 artifact objects plus a trusted `FixtureAssetResolver`;
`run_headless_preview` requires their canonical bytes and adapter-owned roots.
The current Phase 13 `ReviewSnapshotRecord` deliberately stores only a Phase
12 plan and a final EDL-bundle index, whose sequence rows contain identity
references rather than EDL bytes. Replacing this absence with a client path,
guessed fixture, direct engine import or unconditional unavailable endpoint
would violate the accepted contract or create a false implementation claim.

## Required next scope

Write a read-only **Phase 13 Canonical Render-Input Handoff Contract** before
authorizing renderer-control-plane code. It must define an immutable,
server-validated REPLAY handoff package from the accepted Phase 12/Phase 3
owners to the Studio resolver. The package must carry canonical EDL bytes,
their loaders/identity bindings, exact RenderProps/fixture-manifest binding and
project/sequence/domain-policy lineage. Its ingestion cannot be a browser path
or arbitrary JSON editor; the eventual Studio endpoint may only reference an
already validated package.

The handoff contract must remain separate from Phase 14 lifecycle/GC and Phase
15 transport. It must not authorize a renderer call, media acquisition, queue,
retry or UI implementation.

## Documentation impact matrix

| Document | Impact |
|---|---|
| `docs/MASTER_ROADMAP.md` | None; source ownership is unchanged |
| `docs/CURRENT_STATE.md` | Records the missing trusted input handoff |
| `docs/NEXT_ACTIONS.md` | Advances to the handoff specification only |
| `docs/KNOWN_LIMITATIONS.md` | Records the exact input limitation |
| `docs/PHASE_ACCEPTANCE.md` | Records non-authorization honestly |
| `docs/CHANGELOG.md` | Records the decision |
| `docs/ARCHITECTURE_DECISIONS.md` | None |
| `docs/QUALITY_BENCHMARKS.md` | None |
