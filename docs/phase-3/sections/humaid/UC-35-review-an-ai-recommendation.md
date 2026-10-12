# UC-35 Review an AI recommendation

- **Priority:** Essential
- **Parent group:** AI-01 to AI-05
- **Owner:** Humaid Al Ali
- **Primary actor:** Custodian or permitted originating role
- **Supporting actors:** None

## Goal

Record a human decision about AI advice and enforce the permissions of any resulting operation.

## Preconditions

- The reviewer is signed in and may inspect the selected recommendation.
- A stored AI output identifies its source records and configuration version.

## Trigger

The reviewer opens an AI output for a decision.

## Main flow

1. The system displays the recommendation, supporting facts, uncertainty and source versions.
2. The reviewer compares the advice with the permitted operational evidence.
3. The reviewer selects acceptance and identifies the intended next operation.
4. The system rechecks the reviewer's role, current source versions and the target operation's validation rules.
5. The system displays the proposed result and obtains explicit confirmation from the reviewer.
6. The system records the attributed review decision and submits any requested record change through its ordinary authorized workflow.
7. The system displays the review outcome separately from the outcome of the requested operational action.

## Alternative flows

- **Alternative at main step 3:** The reviewer rejects the advice.
    1. The system records rejection and the review reason while retaining the original output.
    - Outcome: End with no requested operational change.
- **Alternative at main step 3:** The reviewer chooses an override.
    1. The reviewer supplies the replacement choice and a reason.
    2. The system preserves the original advice beside the proposed override.
    - Outcome: Return to main step 4.

## Exception flows

- **Exception at main step 4:** The target record changed or the reviewer lacks the required operational permission.
    1. The system blocks the requested action and explains the failed check.
    2. Changed evidence requires a fresh review before another attempt.
    - Outcome: End without applying the stale or unauthorized action.

## Postconditions

**Success**

- An attributed human decision is recorded; any resulting change follows its own authorization.

**Failure**

- Accepting advice does not override failed eligibility, approval separation or access checks.

## Business rules

BR-01, BR-02, BR-11, BR-14

## Functional requirements

- **P3-FR-35.1** The system shall preserve the original AI output with the attributed human review decision.
- **P3-FR-35.2** The system shall require a recorded reason for a human override.
- **P3-FR-35.3** The system shall revalidate a resulting operational action independently of AI acceptance.

## Acceptance check

An override retains the original recommendation and its reason. Accepting a match for a newly unavailable asset creates no reservation, and accepting retirement advice cannot replace independent lifecycle approval.
