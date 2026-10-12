# UC-30 Review the audit history

- **Priority:** Essential
- **Parent group:** FR-06
- **Owner:** Ali Alawadhi
- **Primary actor:** Auditor
- **Supporting actors:** None

## Goal

Trace authorized operational decisions and corrections without allowing the reviewer to rewrite history.

## Preconditions

- The auditor is signed in with a defined audit-access scope.

## Trigger

The auditor requests the history of an asset, request, transfer or other permitted record.

## Main flow

1. The auditor supplies a record identifier, event period and optional action filter.
2. The system validates the filters and checks the auditor's permitted record scope.
3. The system retrieves matching audit events in their recorded sequence.
4. The system displays event identity, time, responsible account, action, outcome and associated record versions.
5. The auditor selects an event to compare its permitted before-and-after values and linked approval or correction evidence.
6. The system presents the linked history without editable event controls.
7. The auditor exports the scoped history with its filters and generation time.

## Alternative flows

- **Alternative at main step 3:** No events match the valid filters.
    1. The system displays that no matching events were found and retains the filters for revision.
    - Outcome: End without inventing a history entry.
- **Alternative at main step 5:** The selected event has a subsequent correction.
    1. The system displays the original event and the separately attributed correction together.
    - Outcome: Return to main step 6.

## Exception flows

- **Exception at main step 2:** The supplied identifier belongs to a record outside the auditor's scope.
    1. The system denies access without displaying the restricted record's event details.
    2. Changing filters cannot override the access restriction.
    - Outcome: End without releasing the requested history.

## Postconditions

**Success**

- The auditor can trace permitted decisions and corrections while original events remain unchanged.

**Failure**

- Restricted history remains undisclosed; no audit entry is altered or deleted.

## Business rules

BR-01, BR-14

## Functional requirements

- **P3-FR-30.1** The system shall provide a scoped, chronological audit view for protected operational changes.
- **P3-FR-30.2** The system shall retain original audit events when corrections are recorded.
- **P3-FR-30.3** The system shall exclude credentials and unrestricted personal data from audit views and exports.

## Acceptance check

A synthetic asset correction displays both the original change and its attributed correction. Audit viewing offers no edit or delete operation, and a restricted department's history is denied.
