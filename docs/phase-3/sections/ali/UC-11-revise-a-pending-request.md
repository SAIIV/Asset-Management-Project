# UC-11 Revise a pending request

- **Priority:** Essential
- **Parent group:** FR-03
- **Owner:** Ali Alawadhi
- **Primary actor:** Requester
- **Supporting actors:** None

## Goal

Correct a pending need without allowing an earlier allocation or review to authorize changed details.

## Preconditions

- The Requester is authenticated and owns the request within their department scope.
- The request is Submitted or UnderReview and no linked transfer has been dispatched.

## Trigger

The Requester chooses to revise the pending request.

## Main flow

1. The system verifies revision permission and retrieves the current request version and allocation information.
2. The system confirms that the request is Submitted and has no active reservation before opening its editable fields.
3. The Requester changes the permitted fields, records a revision reason and submits.
4. The system validates the revised fields and rechecks that the request remains Submitted, unreserved and unchanged by another operation.
5. The system saves the new revision in Submitted state and preserves the previous request details and revision reason in its history.
6. The system confirms the revision; subsequent allocation must use the revised requirements.

## Alternative flows

- **Alternative at main step 2:** The request is UnderReview with an active reservation.
    1. The Requester confirms returning the request for revision.
    2. The system atomically releases the reservation, restores Reserved units to Available and returns the request to Submitted without changing custody.
    3. The system records the return and notifies the reviewer.
    - Outcome: Return to main step 3 after successful release.

## Exception flows

- **Exception at main step 4:** A concurrent operation reserved or approved the request, or the revised quantity is invalid.
    1. The system rejects the revision and displays the current state or validation error.
    2. It does not overwrite the concurrent operation or retain an approval for changed details.
    - Outcome: End without saving the revision; a permitted fresh revision may be started.

## Postconditions

**Success**

- The revised request is Submitted and has no active reservation.

**Failure**

- No changed requirement is committed against an active allocation; a completed preliminary release remains recorded.

## Business rules

BR-01, BR-03, BR-06, BR-08, BR-14

## Functional requirements

- **P3-FR-11.1** The system shall save request revisions only in Submitted state without an active reservation.
- **P3-FR-11.2** The system shall release an UnderReview request's reservation before making its details editable.
- **P3-FR-11.3** The system shall retain earlier request details after a revision.

## Acceptance check

Revise an UnderReview two-unit request: both reservations are released before editing, custody is unchanged and the new version is Submitted. A request concurrently approved during editing cannot be overwritten.
