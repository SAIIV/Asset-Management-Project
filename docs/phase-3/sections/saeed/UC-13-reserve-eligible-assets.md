# UC-13 Reserve eligible assets

- **Priority:** Essential
- **Parent group:** FR-04
- **Owner:** Saeed Alkaabi
- **Primary actor:** Custodian
- **Supporting actors:** Requester

## Goal

Allocate the requested quantity of distinct eligible units for review without granting approval.

## Preconditions

- The Custodian is authenticated and permitted to review the Submitted request.
- The request exists in Submitted state and has no active reservation.

## Trigger

The Custodian begins allocating assets to the submitted need.

## Main flow

1. The system retrieves the current request and verifies the Custodian's access to its review information.
2. The system refreshes the request's quantity, mandatory specifications, required date and permitted candidate assets.
3. The Custodian selects exactly the required number of distinct physical Asset IDs and confirms the proposed allocation.
4. Within one transaction, the system rechecks the request version, full quantity and each unit's permission, Available state, listed flag, Serviceable condition and mandatory specifications.
5. The system commits the complete Active reservation, every selected unit's Reserved state and the request's UnderReview state atomically.
6. The system records the allocation, shows its asset IDs and makes the request available for independent approval. Custody and owning departments remain unchanged.

## Alternative flows

- **Alternative at main step 3:** Fewer eligible units are available than requested.
    1. The Custodian leaves the request unallocated and informs the Requester.
    2. Only the Requester may revise the quantity through UC-11.
    - Outcome: Return to main step 2 after revision, or end Submitted and unreserved.

## Exception flows

- **Exception at main step 4:** Quantity is incomplete, an ID is repeated, or concurrent changes invalidate the request or a selected unit.
    1. The system rejects the entire allocation and reports the conflict.
    2. No subset is reserved.
    - Outcome: Return to main step 2 with refreshed information.

## Postconditions

**Success**

- The request is UnderReview with one complete reservation covering its quantity in distinct Reserved asset IDs.

**Failure**

- No partial allocation, approval or custody change is committed.

## Business rules

BR-01, BR-02, BR-03, BR-04, BR-05, BR-14

## Functional requirements

- **P3-FR-13.1** The system shall allocate exactly the requested quantity of distinct eligible Asset IDs.
- **P3-FR-13.2** The system shall commit the complete reservation and associated state changes atomically.
- **P3-FR-13.3** The system shall prevent reservation from creating a business approval or changing custody.

## Acceptance check

Two competing requests for the same final monitor cannot both reserve it. For quantity two, selecting the same ID twice or losing one candidate to a concurrent reservation creates no partial allocation.
