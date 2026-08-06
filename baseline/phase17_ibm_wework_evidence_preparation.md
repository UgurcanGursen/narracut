# Phase 17 IBM + WeWork Product-Gate Evidence Preparation

Date: 2026-08-06

## Scope and status

This is a preparation record for the two real business-tech projects required
by Phase 17. It records publicly accessible factual-source candidates and
individually licensed media candidates found without browser automation,
provider credentials, paid APIs, access-control bypass or downloaded third-
party media.

It is **not** a source import, a claim acceptance record, a benchmark-analysis
record, a timing result, a render run or product-gate acceptance. Every URL
must be opened again at manual capture/import time; the resulting local file
hash, access date, license text and provenance must be stored in the project.

## Selected real-project briefs

| Project ID | Working title | Target length | Editorial question | Boundary |
|---|---|---:|---|---|
| `prj_ibm_reinvention` | `IBM: krizden entegre çözümlere ve hibrit buluta` | 12–15 min | A large technology company can survive a crisis, but which strategic changes are directly supported by primary evidence? | Do not turn recovery into a single-cause hero narrative; distinguish historical context, disclosed transaction facts and inference. |
| `prj_wework_collapse` | `WeWork: büyüme anlatısından borç ve kira riski krizine` | 12–15 min | Which public disclosures document the move from expansion narrative to restructuring, and what remains interpretation? | Do not diagnose intent or illegality; distinguish company disclosure, filing fact and editorial inference. |

Both projects require a `MANUAL_UI` research package before a script is
accepted. No draft below is a substitute for the Phase 9/10 task/import/
validation lifecycle.

## Public factual-source candidates

| Project | Candidate | Primary/public status | Permitted use in this phase | Capture rule |
|---|---|---|---|---|
| IBM | [IBM-hosted historical PDF](https://public.dhe.ibm.com/software/solutions/pdfs/g325-1931-00.pdf) | IBM-hosted historical material; its text describes IBM's 1993 loss and near-breakup context | Candidate for historical chronology; every numeric claim must cite exact page/section during MANUAL_UI extraction | Import only the manually selected file; hash it; record publication metadata and page anchors. |
| IBM | [IBM / Red Hat transaction announcement](https://uk.newsroom.ibm.com/2019-07-09-IBM-Closes-Landmark-Acquisition-of-Red-Hat-for-34-Billion-Defines-Open-Hybrid-Cloud-Future) | Official company announcement, dated 2019-07-09 | Candidate for the disclosed closing and stated transaction value only | Treat the company framing as an interested source; pair it with an independent or filing source for material causal claims. |
| WeWork | [WeWork 2023 Q3 Form 10-Q](https://www.sec.gov/Archives/edgar/data/1813756/000181375623000067/wework2023q310q.htm) | SEC-hosted issuer filing | Candidate for issuer-disclosed financial, lease and restructuring facts | Preserve the exact filing URL, accession context, section heading and access date. |
| WeWork | [WeWork 2023-11-06 Form 8-K](https://www.sec.gov/Archives/edgar/data/1813756/000119312523271902/d522028d8k.htm) | SEC-hosted issuer filing | Candidate for the Chapter 11 filing date and the disclosed restructuring facts | Quote only verified filing language; do not infer causes or stakeholder intent from the filing alone. |

The current set is an initial source spine, not sufficient research coverage.
The MANUAL_UI discovery task must add at least one independent, publicly
accessible corroborating source for each project before claim normalization.

## Individually licensed media candidates

These candidates are for manually selected local asset import only. They are
not downloaded by the application and do not grant rights over corporate
logos, screenshots, footage or unrelated media.

| Project | Candidate media | License observed on source page | Intended editorial role | Import constraint |
|---|---|---|---|---|
| IBM | [IBM System/360 image](https://commons.wikimedia.org/wiki/File:IBM_System_360.png) | Public domain declaration on the file page | Historical computing context, clearly labelled as historical context | Re-check the file page and preserve the source URL/license text with the imported byte hash. |
| IBM | [IBM Building photograph](https://commons.wikimedia.org/wiki/File:IBM_Building_by_Matthew_Bisanz.jpg) | CC BY-SA on the file page | Establishing shot only; it cannot prove a business claim | Generate required attribution and share-alike review record before use. |
| WeWork | [WeWork Denver Triangle Building photograph](https://commons.wikimedia.org/wiki/File:WeWorkDenverTriangleBuilding.jpg) | CC0 1.0 declaration on the file page | Establishing shot only | Preserve source URL and public-domain declaration in the local license manifest. |
| WeWork | [WeWork Buenos Aires building photograph](https://commons.wikimedia.org/wiki/File:WeWork_office_building_Buenos_Aires_001_hnapel.jpg) | CC BY-SA 4.0 on the file page | Geographic-expansion context only, with location caption | Generate required attribution and share-alike review record before use. |

Do not use a corporate logo as a default asset merely because it is discoverable
on Commons. Trademark and jurisdictional review is a distinct product/legal
decision. Generic B-roll must likewise have an individual source page and
license record; search-result snippets are never provenance.

## Benchmark-reference status

The three required external benchmark references are **not yet accepted**.
Publicly viewable third-party videos can be watched for editorial analysis, but
their availability does not grant reuse rights and a search result does not
prove their full runtime, provenance or composition. Before acceptance, record
for each reference: canonical URL, channel/publisher, access date, observed
runtime, purpose of analysis, a no-reuse declaration, and the resulting
brand-free composition observations. No reference video will be downloaded or
used as project media.

## Non-REPLAY timing path decision

`WhisperX` is the current **candidate** local timing producer: its public
repository declares BSD-2-Clause licensing and describes word-level timestamps
through forced alignment. It makes no paid API call in the proposed mode.

It is not selected as a trusted producer yet. The current canonical
`engine/contracts/alignment_result.py` only publishes `REPLAY_VERIFIED`
results and explicitly rejects non-REPLAY adapter execution. Product-gate work
therefore requires a bounded P17 timing-adapter contract and implementation
with all of the following before either project can count toward DDL-02/DDL-09:

1. pinned tool, model and license inventory;
2. local process boundary with timeout, memory/concurrency cap, cancellation
   and structured failure artifact;
3. byte-hashed narration input and raw result lineage;
4. transcript-divergence, missing-word, overlap and confidence rejection;
5. a small manually checked calibration corpus plus project-specific spot
   checks; and
6. an accepted non-REPLAY timing artifact consumed by the existing temporal
   compiler without weakening `REPLAY` checks.

## Next evidence sequence

1. Create the two `MANUAL_UI` source-discovery packages from the selected
   project briefs, using the source candidates only as initial context.
2. Implement and validate the bounded local timing adapter before any real
   project is claimed as end-to-end.
3. Manually import licensed local assets through `LocalMediaStore`; capture
   hashes, license labels and provenance.
4. Complete research, claim, planner, EDL, timing, render, export and reopen
   runs for both projects.
5. Run the three-reference analysis and Phase 15 evidence gates, then reconcile
   DDL-01, DDL-02, DDL-03 and DDL-09 without treating a missing artifact as a
   passing fallback.
