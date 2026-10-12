# UC-29 Read status notifications

- **Priority:** Essential
- **Parent group:** FR-06
- **Owner:** Ali Alawadhi
- **Primary actor:** Requester
- **Supporting actors:** None

## Goal

Allow each account role to review relevant workflow updates through its own protected inbox.

## Preconditions

- The requester is signed in; the same inbox behavior applies to other assigned roles.

## Trigger

The requester opens the notification inbox.

## Main flow

1. The system retrieves notifications addressed to the signed-in account.
2. The system displays each notification's event type, occurrence time, permitted summary and read status.
3. The requester selects a notification about an asset request or related workflow.
4. The system displays its recorded update and rechecks access to the linked operational record.
5. The requester opens the permitted record to inspect its current state.
6. The system displays the current record separately from the notification's historical event and marks the notification read.

## Alternative flows

- **Alternative at main step 4:** The linked workflow has changed since the notification occurred.
    1. The system retains the original event time and identifies that a newer state exists.
    2. The notification does not reinstate an earlier approval, reservation or assignment.
    - Outcome: Return to main step 5.
- **Alternative at main step 1:** The account has no notifications.
    1. The system displays an empty inbox without implying a workflow error.
    - Outcome: End with no notification selected.

## Exception flows

- **Exception at main step 4:** The account no longer has permission to open the linked record.
    1. The system denies the link and withholds currently restricted record details.
    2. It explains that the update cannot be opened with current access.
    - Outcome: End without exposing the restricted record.

## Postconditions

**Success**

- The requester reads an addressed notification and, where permitted, the current linked record.
- Only notification read status changes.

**Failure**

- No unrelated account's notification or restricted operational details are disclosed.

## Business rules

BR-01

## Functional requirements

- **P3-FR-29.1** The system shall deliver relevant request, approval, reservation, transfer, maintenance and lifecycle status events to their designated account inboxes.
- **P3-FR-29.2** The system shall restrict each inbox to its addressed account.
- **P3-FR-29.3** The system shall recheck record access when a notification link is opened.

## Acceptance check

A synthetic rejection notification opens the permitted request and remains historically identifiable after a later update. A different account cannot read it, and reading never changes the request's state.
