# UC-07 Withdraw an asset listing

- **Priority:** Essential
- **Parent group:** FR-02
- **Owner:** Saeed Alkaabi
- **Primary actor:** Custodian
- **Supporting actors:** None

## Goal

Remove an unallocated asset from discovery without deleting the physical asset record, its custody or its operational history.

## Preconditions

- The Custodian is authenticated and assigned to the asset.
- The asset is listed, Available and has no active reservation when the withdrawal is initiated.

## Trigger

The Custodian chooses to withdraw the listing.

## Main flow

1. The system retrieves the asset and checks the Custodian's permission to withdraw its listing.
2. The system displays the Asset ID and explains that withdrawal removes discovery availability but does not retire or delete the asset.
3. The Custodian supplies the withdrawal reason and confirms the action.
4. The system rechecks the record version and absence of an active reservation or transfer before changing the listing flag.
5. The system sets the listing flag to unlisted while retaining Available state, the owning department, current custody and existing history.
6. The system records the actor, time and withdrawal reason and confirms removal from subsequent catalogue results and candidate allocations.

## Alternative flows

- **Alternative at main step 3:** The Custodian decides the item should remain discoverable.
    1. The Custodian cancels the withdrawal before confirmation.
    2. The system returns to the unchanged asset record.
    - Outcome: End without withdrawing the listing.
- **Alternative at main step 4:** Another authorized operation has already withdrawn the same listing without allocating the asset.
    1. The system displays the current unlisted status and retains the original withdrawal event.
    - Outcome: End successfully without another state change.

## Exception flows

- **Exception at main step 4:** A concurrent reservation or transfer now exists.
    1. The system rejects the direct withdrawal and preserves the allocation.
    2. It directs the Custodian to the applicable pre-dispatch request or transfer workflow rather than silently removing the reserved asset.
    - Outcome: End unsuccessfully; allocation remains authoritative.

## Postconditions

**Success**

- The asset is unlisted but remains recorded, Available and traceable.

**Failure**

- No active allocation, custody value or asset history is lost.

## Business rules

BR-01, BR-04, BR-05, BR-08, BR-14

## Functional requirements

- **P3-FR-07.1** The system shall prevent listing withdrawal from silently cancelling an active allocation.
- **P3-FR-07.2** The system shall retain the asset record and custody after listing withdrawal.
- **P3-FR-07.3** The system shall exclude an unlisted asset from subsequent catalogue matching.

## Acceptance check

Withdraw one listed synthetic chair: catalogue search omits it while its ID and history remain accessible to the authorized Custodian. A reservation committed before withdrawal causes the withdrawal to fail without releasing that reservation.
