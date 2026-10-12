# UC-22 Complete asset maintenance

- **Priority:** Essential
- **Parent group:** FR-05
- **Owner:** Ali Alawadhi
- **Primary actor:** Maintenance Officer
- **Supporting actors:** None

## Goal

Close maintenance and restore service only with inspection evidence.

## Preconditions

- The assigned Maintenance Officer is signed in.
- The maintenance job is InProgress and its asset is UnderMaintenance.

## Trigger

The officer records that the maintenance activity has finished.

## Main flow

1. The officer opens the job and reviews the fault and planned work.
2. The officer records work performed, completion time, actual nonnegative costs and a linked passing inspection with evidence.
3. The system validates the job version, required completion fields, inspection result and current custody.
4. The system displays the completion summary and the proposed post-maintenance state.
5. The officer confirms completion.
6. For the normal owner-held asset, the system marks the job Completed, sets condition Serviceable and restores Available while leaving the asset unlisted.
7. The system appends completion, preserves earlier evidence and notifies the custodian.

## Alternative flows

- **Alternative at main step 2:** The completed repair attempt failed its inspection.
    1. The officer records the failed result, work and actual costs.
    2. After validation and confirmation, the system marks the job Completed with an unsuccessful outcome while retaining UnderMaintenance and the failed condition.
    - Outcome: Return to main step 7; further work or a lifecycle proposal is required before reuse.
- **Alternative at main step 6:** The repaired unit remains in a borrower's confirmed custody.
    1. The system marks the job Completed, sets condition Serviceable and restores InUse rather than Available, leaving the asset unlisted.
    2. It retains the original owning department and outstanding loan.
    - Outcome: Return to main step 7.

## Exception flows

- **Exception at main step 3:** A passing outcome lacks an inspection or recorded cost is negative.
    1. The system refuses completion and identifies the missing or invalid value.
    - Outcome: Return to main step 2; no service restoration occurs.
- **Exception at main step 6:** The job has already been completed.
    1. The system displays the existing completion rather than duplicating costs or state changes.
    - Outcome: End with one completion record.

## Postconditions

**Success**

- The completed job has evidence and costs; its result determines availability without changing custody or publishing.

**Failure**

- Missing or failed inspection cannot silently return an unsafe asset to service.

## Business rules

BR-01, BR-03, BR-09, BR-14, BR-15

## Functional requirements

- **P3-FR-22.1** The system shall require passing inspection evidence before restoring service after maintenance.
- **P3-FR-22.2** The system shall retain UnderMaintenance after an unsuccessful repair.
- **P3-FR-22.3** The system shall preserve the loan and owning department when a borrowed asset is repaired.

## Acceptance check

A repaired owner-held synthetic asset becomes Available but unlisted. The same passing repair on a borrowed unit restores InUse. A failed inspection closes the attempt without clearing UnderMaintenance.
