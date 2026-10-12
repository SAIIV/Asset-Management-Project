# UC-18 Return loaned assets

- **Priority:** Essential
- **Parent group:** FR-04
- **Owner:** Saeed Alkaabi
- **Primary actor:** Requester
- **Supporting actors:** Custodian, Maintenance Officer

## Goal

Restore original custody while preserving ownership and loan history.

## Preconditions

- The requester is signed in and holds loan custody.
- The original loan transfer is Received; selected units remain outstanding.

## Trigger

The requester initiates a return against the original loan.

## Main flow

1. The requester selects the outstanding loan and the complete set to be returned.
2. The system verifies current custody, original owning department and absence of a conflicting active transfer.
3. The requester records a proposed handover date, current condition and location.
4. The original custodian confirms the receiving arrangement.
5. The system creates a Scheduled return transfer linked to the original loan; it creates no new resource request.
6. The requester confirms dispatch evidence; the system sets Dispatched and InTransit, retaining borrower custody.
7. The original custodian checks all physical IDs, records inspection evidence and confirms receipt of the serviceable set.
8. The system sets Received, restores original custody and location, sets Available but unlisted, and records the return without changing ownership.

## Alternative flows

- **Alternative at main step 1:** The linked return is already Disputed.
    1. The system opens that return and retains its dispatch, dispute and custody history.
    2. Both parties record resolution evidence against the original expected IDs; the system creates no new return.
    - Outcome: Return to main step 7 for ID verification and receipt inspection.
- **Alternative at main step 7:** A returned unit is damaged or already carries a fault flag.
    1. The system records a dispute pending inspection and keeps previous custody.
    2. After a Maintenance Officer's disposition and both parties' evidenced resolution, the custodian confirms receipt into UnderMaintenance.
    - Outcome: Return to main step 8, replacing Available with UnderMaintenance for affected units; all remain unlisted.

## Exception flows

- **Exception at main step 2:** The unit belongs to another loan, was already returned or has a conflicting transfer.
    1. The system refuses the return and identifies the incompatible record.
    - Outcome: End without a duplicate return or custody change.
- **Exception at main step 7:** An expected unit is missing.
    1. The system records Disputed and preserves InTransit status and borrower custody until the discrepancy is resolved.
    - Outcome: End without confirming the complete return.

## Postconditions

**Success**

- The return is linked to its loan; receipt restores original custody without automatic publication.

**Failure**

- The loan history and owning department remain unchanged; unresolved returns do not erase borrower custody.

## Business rules

BR-01, BR-07, BR-09, BR-14, BR-15

## Functional requirements

- **P3-FR-18.1** The system shall link each return transfer to its original loan transfer.
- **P3-FR-18.2** The system shall preserve the original owning department throughout a loan and return.
- **P3-FR-18.3** The system shall leave returned assets unlisted until publication is explicitly authorized.

## Acceptance check

Returning a synthetic loan restores original custody only on receipt. Ownership never changes. A damaged return enters UnderMaintenance; attempting to return the same ID again creates no second return.
