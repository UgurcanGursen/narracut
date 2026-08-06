# Phase 15 Master-Gap Reconciliation

Phase 15 is OPEN. The accepted run-evidence package establishes the truthful
decision substrate; it does not itself implement every validation layer in the
roadmap. This reconciliation assigns every remaining criterion to an owner and
selects the next bounded package.

| Roadmap criterion | Present evidence/owner | Remaining Phase 15 work | Status |
|---|---|---|---|
| Missing/not-implemented cannot be valid | local `run_evidence` gate | attach concrete validators as declared checks | PARTIAL |
| Enabled transport policy/outcomes | Phase 17 owns actual transport; Phase 15 ledger represents `UNSUPPORTED` | normalized outcome validator when a supported mode is selected | OPEN, no live transport now |
| Thresholds cannot drift | policy-hash ledger field | typed threshold/evidence adapter, not a new threshold | PARTIAL |
| Video/artifact evidence cannot contradict | Phase 4 receipt, Phase 14 registry | canonical evidence attachment and cross-reference validator | SELECTED NEXT |
| Root failure cause | accepted ledger reducer | apply to further adapters | PARTIAL |
| Challenge screen cannot succeed | Phase 6 REPLAY evidence data | source-outcome validator; no URL access | OPEN |
| Source-audio contamination blocks mix | Phase 8/11 eligibility policy | validation adapter over accepted eligibility/direction evidence; no media classifier | OPEN |
| Domain compatibility/blocked wording/new-pack extension | Phase 1/9/10/12 policies | canonical domain-policy validation attachment | OPEN |
| Orphan visibility/GC protected dependency | Phase 14 registry/plans | artifact integrity attachment and gate outcome | OPEN |
| Audio-boundary threshold warning/remix | Phase 3 boundary artifacts | boundary evidence adapter; automatic remix remains separately owned | OPEN |

## Selected next bounded package

`EvidenceAttachmentValidator`: canonical, fail-closed adapters that turn
already accepted Phase 4 render receipts, Phase 14 registry/admission evidence
and resolved Domain Pack snapshots into the first four required quality-check
observations. It must detect identity/project/policy contradictions and orphan
artifact references without reading arbitrary paths or changing renderer,
lifecycle or policy semantics.

It excludes source transport, actual media classification, pixel/audio decode,
threshold creation, retry, queue/worker, Studio/UI, Phase 16 and Phase 17.

The remaining rows stay visible and are not implicitly closed by this selected
package. The next task is a candidate contract and independent audit for this
bounded attachment validator.
