# UC-14 Review a resource request

- **Priority:** Essential
- **Parent group:** FR-04
- **Owner:** Saeed Alkaabi
- **Primary actor:** Approver
- **Supporting actors:** None

## Goal

Make an accountable decision on a reserved resource request without approving the approver's own request.

## Preconditions

- The approver is signed in.
- The request exists in UnderReview and is within the approver's assigned department scope.

## Trigger

The approver opens a request awaiting a decision.

## Main flow

1. The approver selects the request from the review queue.
2. The system checks current approval authority and verifies that the approver is not the requester.
3. The system presents the purpose, quantity, mandatory specifications, required date, transfer type and reserved physical asset IDs.
4. The approver selects approval and records the decision rationale.
5. The system verifies the full set is Reserved by this request, with Serviceable condition, listing, permissions, mandatory specifications and unchanged request details still valid.
6. The system records the approval, approver, timestamp and approved version atomically and sets the request to Approved.
7. The system notifies the requester and custodian and displays the decision record.

## Alternative flows

- **Alternative at main step 4:** The approver rejects the request.
    1. The approver supplies a rejection reason.
    2. The system sets Rejected, releases all active reservations and returns eligible reserved assets to Available.
    - Outcome: End with rejection recorded and affected users notified.
- **Alternative at main step 4:** The approver requests a correction.
    1. The approver identifies the information requiring revision.
    2. The system returns the request to Submitted and releases its reservations.
    - Outcome: End awaiting requester revision and subsequent reservation and review.

## Exception flows

- **Exception at main step 2:** The approver is the requester or lacks current authority.
    1. The system denies the decision and records the denied attempt.
    - Outcome: End without approving or changing the request.
- **Exception at main step 5:** A reserved unit is no longer eligible.
    1. The system invalidates the affected reservation set and returns the request to Submitted for reassignment.
    - Outcome: End without approval; no partial allocation remains.

## Postconditions

**Success**

- One version-specific approval is recorded; all required units remain reserved.

**Failure**

- No unauthorized approval exists; the reason for rejection or failed validation is retained.

## Business rules

BR-01, BR-02, BR-05, BR-06, BR-08, BR-14

## Functional requirements

- **P3-FR-14.1** The system shall prevent a requester from approving their own request.
- **P3-FR-14.2** The system shall bind approval to the reviewed request version.
- **P3-FR-14.3** The system shall release reservations when a request is rejected or returned for revision.

## Acceptance check

For a synthetic two-unit request, an independent authorized approver can approve two eligible reserved IDs. Self-approval fails. Rejection releases both reservations and retains its reason.
