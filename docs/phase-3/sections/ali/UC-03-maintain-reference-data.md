# UC-03 Maintain reference data

- **Priority:** Essential
- **Parent group:** FR-02
- **Owner:** Ali Alawadhi
- **Primary actor:** Administrator
- **Supporting actors:** None

## Goal

Maintain the prototype's department, location and category choices while preserving the meaning of records that already use them.

## Preconditions

- The Administrator is authenticated.
- Reference-data management is available in the configured prototype.

## Trigger

The Administrator requests a new reference entry or a change to an existing entry.

## Main flow

1. The system checks the Administrator's reference-data permission and displays the selected reference group.
2. The Administrator selects an entry to edit, and the system displays its identifier, current values and active status.
3. The Administrator enters the revised label or permitted reference attributes and submits the change.
4. The system validates mandatory fields and linked references, then checks whether the change would break an existing asset or request reference.
5. The system saves the valid change against the existing reference identifier and records the old and new values in the audit history.
6. The system displays the updated entry and makes its active values available in subsequent forms without rewriting historical operational events.

## Alternative flows

- **Alternative at main step 2:** The Administrator chooses to add an entry instead of editing one.
    1. The system presents an empty entry form and allocates an identifier when the validated entry is saved.
    - Outcome: Return to main step 3.
- **Alternative at main step 3:** An entry should no longer be selected in new records.
    1. The Administrator requests deactivation rather than deletion.
    2. The system prepares to retain existing links and exclude the entry from new selections.
    - Outcome: Return to main step 4 to validate the proposed deactivation.

## Exception flows

- **Exception at main step 4:** A required field is blank or the proposed change would leave a broken reference.
    1. The system identifies the invalid field or dependency and rejects the change.
    - Outcome: Return to main step 3; no reference change is saved.

## Postconditions

**Success**

- The reference entry is usable as configured, and earlier linked records remain interpretable.

**Failure**

- Existing reference values and dependent records remain unchanged.

## Business rules

BR-01, BR-03, BR-14

## Functional requirements

- **P3-FR-03.1** The system shall restrict reference-data changes to authorized Administrators.
- **P3-FR-03.2** The system shall preserve identifiers referenced by existing operational records.
- **P3-FR-03.3** The system shall exclude inactive reference entries from new-record selections.

## Acceptance check

Deactivate a category used by a synthetic asset: its historical association remains visible, but a new registration cannot select it. A blank replacement label is rejected without changing the existing entry.
