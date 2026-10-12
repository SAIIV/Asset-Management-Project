# UC-17 Confirm asset receipt

- **Priority:** Essential
- **Parent group:** FR-04
- **Owner:** Saeed Alkaabi
- **Primary actor:** Requester
- **Supporting actors:** Custodian, Maintenance Officer

## Goal

Establish evidenced custody of the complete delivery, including controlled acceptance of damaged units.

## Preconditions

- The requester is signed in as the recorded receiver.
- A Dispatched or Disputed transfer exists with its original dispatch evidence.

## Trigger

The requester records the result of receiving the delivery.

## Main flow

1. The requester opens the transfer and reviews the dispatched physical IDs.
2. The system verifies receiving authority and displays incidents and previous custody.
3. The requester checks every unit and enters receipt time, location, condition and supporting evidence.
4. The system validates the complete ID set, serviceable condition and absence of unresolved incidents.
5. The requester confirms acceptance of the complete delivery.
6. The system atomically sets Received, updates custody and location, sets the units InUse and marks the request Fulfilled; a permanent transfer also changes owning department, whereas a loan does not.
7. The system preserves dispatch and receipt events and notifies the source custodian.

## Alternative flows

- **Alternative at main step 3:** Units are missing, different or damaged.
    1. The requester records the discrepancy and evidence.
    2. The system sets Disputed and preserves InTransit status and previous custody for the transfer set.
    - Outcome: End pending an evidenced resolution; the request remains unfulfilled.
- **Alternative at main step 4:** A recorded dispute has been resolved.
    1. The receiver and dispatching custodian confirm the resolution and complete ID set.
    2. For damage, a Maintenance Officer records an inspection and disposition permitting receipt into UnderMaintenance.
    3. The requester confirms receipt; the system applies step 6, but damaged units remain unlisted and UnderMaintenance rather than InUse.
    - Outcome: Return to main step 7 with the original dispute and timestamps retained.

## Exception flows

- **Exception at main step 4:** An incident remains unresolved or resolution evidence is missing.
    1. The system blocks receipt confirmation and identifies the outstanding evidence.
    - Outcome: End with InTransit status and previous custody unchanged.

## Postconditions

**Success**

- All IDs have confirmed receipt; ownership follows the transfer type and unsafe units remain unavailable.

**Failure**

- Unresolved delivery discrepancies never silently change custody or fulfil the request.

## Business rules

BR-01, BR-07, BR-09, BR-14, BR-15

## Functional requirements

- **P3-FR-17.1** The system shall update custody only after authorized receipt confirmation.
- **P3-FR-17.2** The system shall preserve previous custody while a delivery dispute remains unresolved.
- **P3-FR-17.3** The system shall require an inspection disposition before accepting damaged units into UnderMaintenance.

## Acceptance check

A two-unit delivery missing one ID stays Disputed and unfulfilled. After evidenced resolution, both IDs receive custody updates; an accepted damaged unit is UnderMaintenance and unlisted, not serviceable stock.
