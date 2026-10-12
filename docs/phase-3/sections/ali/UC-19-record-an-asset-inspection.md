# UC-19 Record an asset inspection

- **Priority:** Essential
- **Parent group:** FR-05
- **Owner:** Ali Alawadhi
- **Primary actor:** Maintenance Officer
- **Supporting actors:** None

## Goal

Record inspection evidence and safety consequences without silently resolving transfers or maintenance jobs.

## Preconditions

- The Maintenance Officer is signed in and has access to the asset.
- A non-retired asset record exists.

## Trigger

The officer records an inspection performed on a synthetic asset scenario.

## Main flow

1. The officer opens the asset and starts a new inspection record.
2. The system displays its current state, custody, condition and linked maintenance or transfer records.
3. The officer records the date, checks, findings, Serviceable condition and passing evidence.
4. The system validates the asset ID, required inspection fields and evidence references.
5. The officer reviews and confirms the inspection.
6. The system appends the inspection and updates condition to Serviceable without automatically completing maintenance, resolving a dispute or publishing the asset.
7. The system records the inspector and timestamp and makes the result available to permitted workflow participants.

## Alternative flows

- **Alternative at main step 3:** Inspection fails or records NeedsInspection or Unserviceable.
    1. After validation, the officer confirms failed checks and evidence; the system saves the reported condition and unlists the asset.
    2. Available, Reserved or InUse units enter UnderMaintenance without changing custody.
    3. For Reserved, it releases the whole reservation, restores other released serviceable units to Available, cancels the pre-dispatch schedule, invalidates approval and returns the request to Submitted.
    4. For InTransit, it preserves custody and state and records a blocking incident.
    - Outcome: Return to main step 7 after recording the safety action.
- **Alternative at main step 1:** An earlier inspection contains an error.
    1. The officer identifies the earlier record and a correction reason.
    2. The system links the new inspection as a correction rather than replacing historical evidence.
    - Outcome: Return to main step 2.

## Exception flows

- **Exception at main step 4:** The result lacks required evidence or contains an invalid asset reference.
    1. The system marks the missing or invalid fields and saves no inspection outcome.
    - Outcome: Return to main step 3.

## Postconditions

**Success**

- The inspection is attributable and immutable; the appropriate safety restriction is recorded.

**Failure**

- Invalid inspection inputs do not certify serviceability or alter custody.

## Business rules

BR-01, BR-09, BR-14

## Functional requirements

- **P3-FR-19.1** The system shall retain inspection findings, evidence, inspector and timestamp.
- **P3-FR-19.2** The system shall block service availability following a failed inspection.
- **P3-FR-19.3** The system shall preserve the original record when an inspection is corrected.

## Acceptance check

Failing inspection on a reserved synthetic ID returns its request to Submitted and prevents dispatch. Failing an InTransit ID preserves custody and opens an incident. A later passing inspection alone does not publish it.
