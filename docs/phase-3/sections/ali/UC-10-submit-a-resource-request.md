# UC-10 Submit a resource request

- **Priority:** Essential
- **Parent group:** FR-03
- **Owner:** Ali Alawadhi
- **Primary actor:** Requester
- **Supporting actors:** None

## Goal

Record a departmental resource need with explicit quantity and compatibility requirements for subsequent custodian review.

## Preconditions

- The Requester is authenticated and assigned to a requesting department.
- The category and department references used by request forms exist.

## Trigger

The Requester chooses to create a resource request.

## Main flow

1. The system checks request-creation permission and displays the request form with permitted department choices.
2. The Requester enters the purpose, category, mandatory specifications, positive whole-number quantity, destination, required date and whether the need is a loan or permanent internal transfer.
3. The Requester separates optional preferences from mandatory constraints and confirms submission.
4. The system validates mandatory fields, quantity, date format and departmental authority without treating a preferred candidate as guaranteed stock.
5. The system creates the request in Submitted state with a distinct Request ID and no active reservation or approval.
6. The system records submission, makes the request available to the permitted review workflow and shows the Requester its identifier and current status.

## Alternative flows

- **Alternative at main step 3:** The Requester wants to retain incomplete work without submitting it.
    1. The Requester chooses to save a draft.
    2. The system records a Draft visible within the Requester's permitted scope and does not place it in the submitted review workflow.
    - Outcome: End with a saved Draft, not a Submitted request.

## Exception flows

- **Exception at main step 4:** Quantity is zero, negative or fractional, or another mandatory value is invalid.
    1. The system identifies the failed validation and retains the entered form for correction.
    2. No Submitted request or reservation is created.
    - Outcome: Return to main step 2.

## Postconditions

**Success**

- The Submitted request defines its full need and awaits review without allocating assets.

**Failure**

- Invalid input does not create a Submitted request or alter asset availability.

## Business rules

BR-01, BR-03, BR-05, BR-14, BR-15

## Functional requirements

- **P3-FR-10.1** The system shall require a positive whole-number quantity before request submission.
- **P3-FR-10.2** The system shall distinguish mandatory specifications from optional request preferences.
- **P3-FR-10.3** The system shall create a successfully submitted request without allocating physical asset IDs.

## Acceptance check

Submit a synthetic two-monitor loan request and verify Submitted status with zero reserved units. A quantity of 1.5 is rejected, and saving incomplete work creates only a Draft.
