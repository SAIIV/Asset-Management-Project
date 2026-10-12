# UC-16 Release reserved assets

- **Priority:** Essential
- **Parent group:** FR-04
- **Owner:** Saeed Alkaabi
- **Primary actor:** Custodian
- **Supporting actors:** None

## Goal

Record dispatch only when every physical unit and the current approval permit the planned movement.

## Preconditions

- The custodian is signed in and assigned to the source department.
- The transfer is Scheduled and has not previously been dispatched.

## Trigger

The custodian prepares the scheduled asset set for handover.

## Main flow

1. The custodian opens the Scheduled transfer.
2. The system verifies release authority and displays the required physical IDs and receiving details.
3. The custodian checks each unit against its ID and records handover evidence, dispatch time and recipient details.
4. The system rechecks approval, full reservation, serviceability, mandatory specifications and the required date against current records.
5. The system displays the complete dispatch record and warns that cancellation will no longer be available after dispatch.
6. The custodian confirms the handover.
7. The system atomically sets the transfer to Dispatched, consumes its reservations and sets all units to InTransit while retaining authoritative custody.
8. The system records the dispatch event and notifies the requester to confirm receipt.

## Alternative flows

- **Alternative at main step 3:** One physical ID does not match the reserved set.
    1. The system identifies the mismatch.
    2. The custodian locates the correct unit rather than substituting an unapproved asset.
    - Outcome: Return to main step 3; no partial release is recorded.

## Exception flows

- **Exception at main step 4:** A unit is faulted or another material approval condition has changed.
    1. The system blocks the entire dispatch and invalidates the approval.
    2. It releases reservations, returns the request to Submitted and cancels the pre-dispatch transfer; faulted units remain unavailable.
    - Outcome: End awaiting reassignment and independent approval.
- **Exception at main step 4:** The required date has passed.
    1. The system blocks dispatch pending recorded date revalidation.
    - Outcome: End without changing custody or consuming reservations.

## Postconditions

**Success**

- All specified units are InTransit under one recorded dispatch; the request is not yet Fulfilled.

**Failure**

- No partial dispatch is committed; unauthorized or ineligible release is blocked.

## Business rules

BR-01, BR-05, BR-06, BR-07, BR-08, BR-09, BR-14

## Functional requirements

- **P3-FR-16.1** The system shall revalidate approval and asset eligibility immediately before dispatch.
- **P3-FR-16.2** The system shall commit dispatch for the complete reserved set atomically.
- **P3-FR-16.3** The system shall retain previous authoritative custody until receipt confirmation.

## Acceptance check

Dispatching two eligible synthetic units sets both InTransit and consumes both reservations. Faulting either unit before confirmation blocks the complete dispatch; neither unit receives a partial dispatch record.
