# UC-23 Propose a lifecycle action

- **Priority:** Essential
- **Parent group:** FR-05
- **Owner:** Humaid Al Ali
- **Primary actor:** Custodian
- **Supporting actors:** None

## Goal

Submit an evidenced lifecycle proposal for independent review.

## Preconditions

- The custodian is signed in and manages the asset.
- The non-retired asset has an existing record and accessible lifecycle history.

## Trigger

The custodian identifies a lifecycle action for consideration.

## Main flow

1. The custodian opens the asset and its condition, maintenance and transfer history.
2. The system checks proposal authority and displays existing lifecycle proposals and movement restrictions.
3. The custodian selects one action type and records a rationale, supporting evidence and any known cost or mass inputs with units and sources.
4. The system validates the action type, required rationale, evidence references and nonnegative supplied numerical inputs.
5. The system presents the proposed action and states that submission does not authorize execution or change asset ownership.
6. The custodian confirms submission.
7. The system creates a Proposed lifecycle action linked to the current asset version, records its author and timestamp, and notifies the authorized approver.

## Alternative flows

- **Alternative at main step 3:** An AI recommendation informed the proposal.
    1. The custodian reviews its rationale and limitations and explicitly chooses the proposed action.
    2. The system links the recommendation and its version trace; the custodian records reasons for any override.
    - Outcome: Return to main step 4; AI advice confers no approval authority.
- **Alternative at main step 3:** A cost, mass or benefit input is unknown.
    1. The custodian marks the input unavailable and states the evidence needed.
    2. The system keeps it missing rather than filling zero or inventing a benefit.
    - Outcome: Return to main step 4 with the limitation visible to the approver.

## Exception flows

- **Exception at main step 4:** The rationale is absent or a supplied cost or mass is negative.
    1. The system identifies the invalid fields and refuses submission.
    - Outcome: Return to main step 3.

## Postconditions

**Success**

- An attributable Proposed action exists for independent review; asset state, custody and ownership are unchanged.

**Failure**

- Invalid or unconfirmed advice cannot become an authorized action or retire the asset.

## Business rules

BR-01, BR-03, BR-10, BR-11, BR-12, BR-13, BR-14

## Functional requirements

- **P3-FR-23.1** The system shall retain an action type, rationale and proposer for each lifecycle proposal.
- **P3-FR-23.2** The system shall distinguish unavailable numerical inputs from recorded zero values.
- **P3-FR-23.3** The system shall keep lifecycle proposals separate from execution records.

## Acceptance check

A synthetic recycling proposal with rationale becomes Proposed without retiring the asset. Missing mass remains unavailable. An AI suggestion alone cannot submit or approve the proposal, and negative recorded mass is rejected.
