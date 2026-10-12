# UC-21 Plan asset maintenance

- **Priority:** Essential
- **Parent group:** FR-05
- **Owner:** Ali Alawadhi
- **Primary actor:** Maintenance Officer
- **Supporting actors:** None

## Goal

Schedule and start authorized maintenance while keeping affected assets unavailable.

## Preconditions

- The Maintenance Officer is signed in with asset access.
- A fault, inspection finding or approved repair or refurbishment action exists; the asset is UnderMaintenance or Available and Serviceable.

## Trigger

The officer plans or starts work for the recorded maintenance need.

## Main flow

1. The officer selects the supporting fault, inspection or lifecycle authorization.
2. For the UnderMaintenance asset, the system displays existing jobs and prepares an Open record.
3. The officer enters the work, responsible Maintenance Officer, dates and any estimated cost with its basis.
4. The system validates dates, assigned role, nonnegative costs and absence of conflicting active work.
5. The officer confirms the work plan.
6. The system saves the job as Scheduled, links its supporting evidence and keeps the asset UnderMaintenance and unlisted.
7. The system records the planner and timestamp and notifies the assigned officer and custodian.

## Alternative flows

- **Alternative at main step 2:** The assigned officer starts an existing Scheduled job.
    1. The system rechecks assignment, job version and UnderMaintenance status.
    2. The officer records the actual start time; the system changes that job to InProgress without duplication.
    - Outcome: Return to main step 7.
- **Alternative at main step 2:** An Open or Scheduled job already addresses the same need.
    1. The officer opens that job instead of creating a duplicate.
    2. The system retains its prior schedule and the reason for revision.
    - Outcome: Return to main step 3.
- **Alternative at main step 2:** An Available, Serviceable asset has approved repair or refurbishment authority.
    1. The system verifies current owning-department custody and no outstanding loan, reservation, active transfer or unresolved incident.
    2. It records the authorized maintenance hold, unlists the asset, sets UnderMaintenance and prepares the Open job.
    - Outcome: Return to main step 3.
- **Alternative at main step 5:** The planned job is no longer required.
    1. The officer records a cancellation reason.
    2. The system marks the job Cancelled without clearing the fault or making the asset available.
    - Outcome: End with cancellation history retained.

## Exception flows

- **Exception at main step 2:** The requested maintenance hold or start fails an authority, custody or conflict check.
    1. The system refuses the transition without creating a duplicate job or changing asset state.
    - Outcome: End awaiting resolution of the blocking condition.
- **Exception at main step 4:** The assigned account lacks the role, dates are inconsistent or a supplied cost is negative.
    1. The system identifies each failed validation and does not schedule the job.
    - Outcome: Return to main step 3.

## Postconditions

**Success**

- One attributed maintenance plan exists with an owner, dates and evidence; the asset stays unavailable.

**Failure**

- No invalid or conflicting job is scheduled; cancellation does not certify serviceability.

## Business rules

BR-01, BR-03, BR-09, BR-14

## Functional requirements

- **P3-FR-21.1** The system shall link each maintenance plan to its asset and recorded maintenance need.
- **P3-FR-21.2** The system shall require an assigned Maintenance Officer before scheduling work.
- **P3-FR-21.3** The system shall preserve the asset's safety restriction when maintenance is cancelled.

## Acceptance check

Approved refurbishment of an unallocated synthetic unit sets UnderMaintenance and unlists it. Starting its Scheduled job sets InProgress once. An outstanding loan blocks the new hold; cancellation never restores availability.
