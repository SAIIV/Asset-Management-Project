# UC-09 Inspect asset details

- **Priority:** Essential
- **Parent group:** FR-03
- **Owner:** Ali Alawadhi
- **Primary actor:** Requester
- **Supporting actors:** None

## Goal

Read the current permitted information for a physical unit and understand whether it can satisfy a resource need.

## Preconditions

- The Requester is authenticated.
- The Requester has an Asset ID from a catalogue result or a permitted linked request.

## Trigger

The Requester opens the asset's details.

## Main flow

1. The system receives the selected Asset ID and retrieves the current record.
2. The system checks whether the Requester may view that record and which fields or linked documents are within the account's scope.
3. The system presents the identifier, name, category, specifications, condition, current state and permitted department and location information.
4. The system displays permitted supporting information and whether the asset currently meets catalogue eligibility; viewing does not guarantee a later reservation.
5. The Requester reads the details, completing the inspection. Resource-request submission is a separate UC-10 action; viewing changes no operational state.

## Alternative flows

- **Alternative at main step 3:** The asset is no longer Available but the Requester retains access through an existing request.
    1. The system shows its current state rather than the previous search result's status.
    2. The system does not offer the unit as newly available or reveal unrelated requests associated with it.
    - Outcome: Return to main step 4.
- **Alternative at main step 4:** An optional specification or supporting document was not recorded.
    1. The system identifies the information as unavailable without inventing a value or interpreting absence as a favourable condition.
    - Outcome: Return to main step 5.

## Exception flows

- **Exception at main step 2:** The Asset ID is inaccessible to this account or no longer resolves to a viewable record.
    1. The system declines to disclose the record and returns a neutral unavailable response.
    - Outcome: End unsuccessfully without exposing restricted fields.

## Postconditions

**Success**

- The Requester sees current information within their access rights.

**Failure**

- No asset state changes and no unauthorized record information is revealed.

## Business rules

BR-01, BR-04

## Functional requirements

- **P3-FR-09.1** The system shall check record-level access before displaying asset details.
- **P3-FR-09.2** The system shall display the asset's current state rather than rely on a stale search result.
- **P3-FR-09.3** The system shall withhold asset fields and documents outside the viewer's permission scope.

## Acceptance check

After a searched asset becomes Reserved, an authorized linked Requester sees Reserved rather than Available. A direct request for a prohibited asset ID exposes neither its details nor its restricted attachments.
