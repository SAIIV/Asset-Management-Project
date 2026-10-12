# UC-12 Cancel a resource request

- **Priority:** Essential
- **Parent group:** FR-04
- **Owner:** Saeed Alkaabi
- **Primary actor:** Requester
- **Supporting actors:** None

## Goal

End an owned request before dispatch while consistently releasing its physical allocations and retaining its decision history.

## Preconditions

- The Requester is authenticated and owns the request within their permitted department scope.
- The request is Draft, Submitted, UnderReview or Approved when cancellation is initiated.

## Trigger

The Requester selects cancellation of the request.

## Main flow

1. The system checks cancellation permission and retrieves the request with its reservations and linked transfers.
2. The system shows the affected asset IDs and any planned transfer, explaining that cancellation cannot erase completed dispatch or receipt.
3. The Requester enters a cancellation reason and confirms the action.
4. The system rechecks the current request and transfer states and confirms that none of the linked assets has been dispatched.
5. The system atomically sets the request to Cancelled, releases Active reservations, restores affected Reserved units to Available and cancels linked Draft or Scheduled transfers.
6. The system records the cancellation and notifies the relevant Custodian and reviewer, preserving earlier approvals, custody and listing flags.

## Alternative flows

- **Alternative at main step 2:** The request has no reservation or linked transfer.
    1. The system displays that cancellation will affect only the request and its review status.
    - Outcome: Return to main step 3; step 5 has no asset allocations to release.

## Exception flows

- **Exception at main step 4:** A linked transfer has already been Dispatched or Received, including dispatch occurring during confirmation.
    1. The system rejects cancellation without releasing allocations or reversing custody.
    2. It directs the Requester to the applicable receipt, dispute or loan-return workflow, preserving the dispatched transfer and its history.
    - Outcome: End unsuccessfully without cancelling the request.

## Postconditions

**Success**

- The request is Cancelled and no pre-dispatch allocation remains active.

**Failure**

- The cancellation attempt does not erase dispatch evidence, receipt evidence or authoritative custody.

## Business rules

BR-01, BR-05, BR-07, BR-08, BR-14

## Functional requirements

- **P3-FR-12.1** The system shall reject request cancellation after any linked transfer has been dispatched.
- **P3-FR-12.2** The system shall release the request's Active reservations atomically with pre-dispatch cancellation.
- **P3-FR-12.3** The system shall preserve earlier request and approval history after cancellation.

## Acceptance check

Cancel an Approved request with two Reserved units and a Scheduled transfer: both units become Available, the transfer becomes Cancelled and custody is unchanged. The same operation after dispatch is rejected without returning stock to availability.
