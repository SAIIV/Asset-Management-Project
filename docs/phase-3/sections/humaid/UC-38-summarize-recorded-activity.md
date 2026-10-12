# UC-38 Summarize recorded activity

- **Priority:** Essential
- **Parent group:** AI-05
- **Owner:** Humaid Al Ali
- **Primary actor:** Sustainability Officer
- **Supporting actors:** None

## Goal

Draft evidence-linked activity narratives separately from deterministic report calculations.

## Preconditions

- The sustainability officer is signed in with reporting access.
- An authorized generative-reporting configuration is available for synthetic inputs.

## Trigger

The officer requests a monthly activity report, sustainability update, management bulletin, high-demand-category summary, maintenance insight or recommended-action summary.

## Main flow

1. The officer selects the purpose, department scope and reporting period.
2. The system retrieves a permitted snapshot of supporting records and deterministic report results from UC-26 or UC-28.
3. The system records the source cutoff, missing inputs and any limitations affecting interpretation.
4. The generation service drafts a narrative, including supported activity patterns and clearly identified recommended actions.
5. The system reconciles generated numeric assertions with the deterministic results and checks the cited supporting records.
6. The system presents a labelled draft with its evidence references, uncertainty and model or prompt version.
7. The officer reviews the draft through UC-35 before saving an accepted narrative; the summary executes no operational action.

## Alternative flows

- **Alternative at main step 2:** The permitted reporting period contains no relevant records.
    1. The system prepares a factual no-records statement with the selected filters.
    2. It does not generate invented trends or substitute activity from another department.
    - Outcome: Return to main step 6 with a non-generated empty-period draft.

## Exception flows

- **Exception at main step 5:** A generated total, trend or factual assertion lacks supporting evidence.
    1. The system flags the unsupported passage and blocks acceptance of that draft.
    2. The officer may request regeneration from the same verified source snapshot.
    - Outcome: End without an accepted narrative.

## Postconditions

**Success**

- An evidence-linked, human-reviewed narrative is saved separately from its source calculations.

**Failure**

- Unsupported generated content is not accepted as a verified activity report.

## Business rules

BR-01, BR-11, BR-12, BR-13, BR-16

## Functional requirements

- **P3-FR-38.1** The system shall ground generated activity narratives in permitted recorded evidence.
- **P3-FR-38.2** The system shall reconcile every generated numeric assertion with deterministic report results.
- **P3-FR-38.3** The system shall identify generated narratives as drafts until authorized human review.
- **P3-FR-38.4** The system shall retain each narrative's source cutoff and model or prompt version.

## Acceptance check

A synthetic monthly summary reproduces supported totals and links its evidence. An invented saving blocks acceptance, missing carbon evidence remains unavailable, and a recommended repair creates no maintenance order.
