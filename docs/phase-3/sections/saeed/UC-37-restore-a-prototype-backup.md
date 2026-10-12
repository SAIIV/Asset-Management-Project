# UC-37 Restore a prototype backup

- **Priority:** Essential
- **Parent group:** FR-01
- **Owner:** Saeed Alkaabi
- **Primary actor:** Administrator
- **Supporting actors:** None

## Goal

Recover a consistent synthetic snapshot through controlled maintenance while retaining recovery evidence.

## Preconditions

- The administrator is signed in with restoration permission.
- A prototype backup is available for selection.

## Trigger

The administrator requests restoration of a selected backup.

## Main flow

1. The administrator identifies the backup, recovery reason and intended snapshot date.
2. The system validates backup identity, compatibility and integrity before offering restoration.
3. The administrator confirms the recovery scope and activates controlled maintenance mode.
4. The system blocks operational writes and preserves the current state and audit history in a protected recovery archive.
5. The system restores the selected records and linked files into a staging environment.
6. The system checks referential consistency, file availability and access configuration in the restored snapshot.
7. The administrator reviews the result and confirms activation of the validated restored state.
8. The system records recovery, resumes operations and displays the restored cutoff and archive reference.

## Alternative flows

- **Alternative at main step 7:** The administrator chooses a validation-only exercise.
    1. The system records the validation result without replacing the active state.
    2. The previous environment resumes operation.
    - Outcome: End with the active operational state unchanged.

## Exception flows

- **Exception at main step 6:** Restored records or files fail consistency checks.
    1. The system rejects staged activation and retains the environment and audit archive.
    2. Operations resume only after integrity is confirmed.
    - Outcome: End without activating an invalid snapshot.
- **Exception at main step 8:** Activation fails.
    1. The system retains maintenance mode and recovers the protected pre-restore state before allowing writes.
    - Outcome: End after validated rollback; record the failure.

## Postconditions

**Success**

- Restoration activates the validated snapshot with an explicit cutoff; validation-only records its result without activation.
- Pre-restore audit evidence remains protected.

**Failure**

- A failed restore does not silently replace the working environment or erase audit evidence.

## Business rules

BR-01, BR-14, BR-16

## Functional requirements

- **P3-FR-37.1** The system shall restrict restoration to administrators with restoration permission.
- **P3-FR-37.2** The system shall block operational writes during recovery activation.
- **P3-FR-37.3** The system shall validate restored records and linked files before activation.
- **P3-FR-37.4** The system shall preserve pre-restore audit history in a protected recovery archive.

## Acceptance check

A synthetic snapshot restores its linked records and files. A backup missing a required file cannot become active, a requester cannot initiate recovery, and pre-restore audit evidence remains retrievable.
