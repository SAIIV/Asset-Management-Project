# UC-05 Update an asset record

- **Priority:** Essential
- **Parent group:** FR-02
- **Owner:** Saeed Alkaabi
- **Primary actor:** Custodian
- **Supporting actors:** None

## Goal

Correct permitted asset information while protecting allocations, authoritative custody and the historical record.

## Preconditions

- The Custodian is authenticated.
- The asset record exists within the Custodian's assigned record scope.

## Trigger

The Custodian opens an asset for editing.

## Main flow

1. The system checks edit permission and displays the asset's current values, state and version.
2. The Custodian changes permitted descriptive information, specifications or recorded values and enters the reason for correction.
3. The system validates required fields and nonnegative amounts and determines whether the proposed change affects an allocation or protected life-cycle field.
4. The system rechecks the record version, current allocation status and the Custodian's permission before accepting the update.
5. The system saves the permitted changes without replacing the Asset ID or earlier operational events.
6. The system appends the actor, time, correction reason and old and new values, then displays the updated record.

## Alternative flows

- **Alternative at main step 3:** The proposed correction changes an allocated asset's material specifications or authoritative custody, ownership, location or condition.
    1. The system does not apply the direct edit.
    2. It identifies the relevant request-revision, cancellation, transfer or inspection workflow. Any permitted material change must follow that workflow, including invalidating affected approval and releasing reservations where required.
    - Outcome: End without the direct update; restart after the relevant workflow establishes an editable state.

## Exception flows

- **Exception at main step 4:** Another operation has changed the asset version or reserved it since the form was opened.
    1. The system rejects the stale submission and displays the current permitted values.
    2. The Custodian reviews the differences instead of overwriting the concurrent change.
    - Outcome: Return to main step 2.

## Postconditions

**Success**

- The permitted correction is saved with its change history; custody and allocation remain consistent.

**Failure**

- The attempted edit changes neither authoritative custody nor a concurrent reservation.

## Business rules

BR-01, BR-03, BR-06, BR-07, BR-09, BR-14

## Functional requirements

- **P3-FR-05.1** The system shall reject an asset update based on an outdated record version.
- **P3-FR-05.2** The system shall prevent direct edits from bypassing allocation, transfer or inspection controls.
- **P3-FR-05.3** The system shall preserve the previous values and correction reason for each committed asset update.

## Acceptance check

Correct an unallocated monitor's specification and retain both versions. If another session reserves that unit before saving, the stale edit fails and neither the reservation nor custody is overwritten.
