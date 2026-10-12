# UC-24 Authorize a lifecycle action

- **Priority:** Essential
- **Parent group:** FR-05
- **Owner:** Humaid Al Ali
- **Primary actor:** Approver
- **Supporting actors:** None

## Goal

Independently accept or reject a specific lifecycle proposal while keeping execution a separate evidenced action.

## Preconditions

- The approver is signed in.
- A Proposed lifecycle action exists within the approver's assigned review scope.

## Trigger

The approver opens the lifecycle proposal for a decision.

## Main flow

1. The approver selects the proposal and its linked asset.
2. The system verifies current business approval authority and that the approver did not propose the action.
3. The system displays the action, rationale, supporting inspections, known costs, missing inputs and any AI advice separately from evidence.
4. The approver selects approval and records the decision rationale.
5. The system verifies the reviewed proposal version and identifies the permitted next workflow for the selected action.
6. The system sets the lifecycle action to Approved and records the approver, decision time and authorized version without changing the asset state.
7. The system notifies the custodian: reuse follows the request and transfer workflow, repair or refurbishment follows maintenance, and donation, recycling or disposal requires retirement execution evidence.

## Alternative flows

- **Alternative at main step 4:** The approver rejects the proposal.
    1. The approver enters a rejection reason.
    2. The system sets Rejected and notifies the custodian without altering the asset.
    - Outcome: End with an attributable rejection.
- **Alternative at main step 4:** Evidence is insufficient for a decision.
    1. The approver identifies the missing evidence and requests clarification.
    2. The system retains Proposed status and records the clarification request.
    - Outcome: End awaiting additional evidence; there is no execution authority.

## Exception flows

- **Exception at main step 2:** The approver is the proposer or has only Administrator privileges.
    1. The system denies approval and records the attempted action.
    - Outcome: End with the proposal still unapproved.
- **Exception at main step 5:** Material proposal details changed after review.
    1. The system blocks the decision against the stale version and presents the revised evidence.
    - Outcome: Return to main step 3 for a fresh review.

## Postconditions

**Success**

- One independent version-specific authorization exists; execution and its evidence remain outstanding.

**Failure**

- No self-approval, administrative bypass or unsupported retirement occurs.

## Business rules

BR-01, BR-02, BR-10, BR-11, BR-14

## Functional requirements

- **P3-FR-24.1** The system shall prevent a lifecycle proposer from approving their own proposal.
- **P3-FR-24.2** The system shall record the proposal version authorized by the approver.
- **P3-FR-24.3** The system shall require a separate execution record after lifecycle approval.

## Acceptance check

An independent Approver can authorize a synthetic disposal proposal but the asset does not become Retired. Self-approval and an Administrator without Approver authority fail. A repair approval routes to maintenance instead of retirement.
