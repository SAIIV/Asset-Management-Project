# UC-15 Schedule an asset transfer

- **Priority:** Essential
- **Parent group:** FR-04
- **Owner:** Saeed Alkaabi
- **Primary actor:** Custodian
- **Supporting actors:** None

## Goal

Arrange the authorized movement of the complete reserved asset set without changing custody prematurely.

## Preconditions

- The custodian is signed in and manages the source assets.
- An Approved request exists and has not been dispatched.

## Trigger

The custodian chooses to schedule the approved request.

## Main flow

1. The custodian opens the approved request and its reserved asset list.
2. The system checks source-department authority and displays the approved destination, quantity and loan or permanent-transfer type.
3. The custodian enters the planned handover date, collection point, receiving account and, for a loan, the agreed return date.
4. The system validates the dates, complete active reservation, approved version and absence of another active transfer for each ID.
5. The system displays a Draft transfer summary showing every physical ID and the unchanged current custody.
6. The custodian confirms the schedule.
7. The system saves the transfer as Scheduled and notifies the requester; the assets remain Reserved.

## Alternative flows

- **Alternative at main step 1:** A Scheduled transfer already exists and has not been dispatched.
    1. The system opens the existing transfer rather than creating a duplicate.
    2. The custodian requests a revised logistical schedule; the system retains the previous schedule in history.
    - Outcome: Return to main step 3 for validation and confirmation.
- **Alternative at main step 4:** The proposed change alters approved quantity, destination department, specifications or transfer type.
    1. The system prevents scheduling against the old approval.
    2. On confirmed revision, it cancels the pre-dispatch schedule, releases reservations and returns the request to Submitted.
    - Outcome: End awaiting revised request approval.

## Exception flows

- **Exception at main step 4:** The required date has passed or the reservation is incomplete.
    1. The system identifies the failed check and refuses the schedule.
    2. The custodian initiates date revalidation or reassignment through the request workflow.
    - Outcome: End without a dispatchable transfer.

## Postconditions

**Success**

- One Scheduled transfer references the complete approved reservation; ownership and custody are unchanged.

**Failure**

- No invalid schedule becomes dispatchable; previously recorded history remains available.

## Business rules

BR-01, BR-05, BR-06, BR-07, BR-08, BR-15

## Functional requirements

- **P3-FR-15.1** The system shall associate a scheduled transfer with its approved request and reserved asset IDs.
- **P3-FR-15.2** The system shall preserve custody when a transfer is scheduled.
- **P3-FR-15.3** The system shall retain the previous schedule when a pre-dispatch schedule changes.

## Acceptance check

Scheduling two reserved synthetic units produces one Scheduled transfer without changing custody. A changed destination department requires resubmission; a repeated scheduling attempt cannot create a second active transfer.
