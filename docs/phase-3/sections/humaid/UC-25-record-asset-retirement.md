# UC-25 Record asset retirement

- **Priority:** Essential
- **Parent group:** FR-05
- **Owner:** Humaid Al Ali
- **Primary actor:** Custodian
- **Supporting actors:** None

## Goal

Record evidenced execution of authorized donation, recycling or disposal.

## Preconditions

- The custodian is signed in and manages the asset.
- An Approved lifecycle proposal exists for the non-retired asset.

## Trigger

The custodian records execution of the approved retirement action in the synthetic prototype.

## Main flow

1. The custodian opens the approved donation, recycling or disposal action and checks the physical asset ID.
2. The system verifies execution authority, independent approval and the unchanged authorized proposal version.
3. The custodian records the execution date, simulated recipient or operator, method and supporting synthetic evidence.
4. The system validates evidence, confirms custody in the current owning department, and checks for outstanding loans, reservations, transfers and unresolved transit incidents.
5. The system presents the proposed retirement and retained historical records for confirmation.
6. The custodian confirms that the recorded scenario matches the authorized action.
7. The system atomically sets the lifecycle action to Executed and the asset to Retired and unlisted, then records the event and notifies permitted stakeholders.

## Alternative flows

- **Alternative at main step 1:** The selected authorization is for reuse, repair or refurbishment.
    1. The system does not offer retirement execution.
    2. It directs the custodian to the transfer or maintenance workflow linked to that action.
    - Outcome: End without retiring the asset.

## Exception flows

- **Exception at main step 4:** Evidence is missing, the unit is borrowed or an active movement remains unresolved.
    1. The system identifies the blocking condition and refuses retirement.
    2. The custodian resolves the underlying receipt, return or evidence issue before retrying.
    - Outcome: End with the asset state and custody unchanged.
- **Exception at main step 7:** Execution was already recorded.
    1. The system displays the existing execution record without adding another retirement or benefit event.
    - Outcome: End with one authoritative retirement record.

## Postconditions

**Success**

- The physical ID is Retired and unlisted with linked authorization and execution evidence; previous history remains accessible.

**Failure**

- No asset is retired without evidence or while custody is unresolved; no real external ownership transfer is asserted.

## Business rules

BR-01, BR-02, BR-07, BR-09, BR-10, BR-14, BR-16

## Functional requirements

- **P3-FR-25.1** The system shall require approved donation, recycling or disposal authority before recording retirement.
- **P3-FR-25.2** The system shall require execution evidence before setting an asset to Retired.
- **P3-FR-25.3** The system shall prevent duplicate retirement execution records for a physical asset ID.

## Acceptance check

An approved synthetic recycling action with execution evidence retires and unlists its ID. An outstanding loan or missing evidence blocks retirement. Repeating confirmation neither creates a second event nor duplicates benefit eligibility.
