# UC-20 Report an asset fault

- **Priority:** Essential
- **Parent group:** FR-05
- **Owner:** Ali Alawadhi
- **Primary actor:** Requester
- **Supporting actors:** None

## Goal

Prevent unsafe allocation after a fault without rewriting custody or movement history.

## Preconditions

- The requester is signed in and has permitted access to a non-retired asset record.

## Trigger

The requester observes a fault and selects the asset's fault-report action.

## Main flow

1. The requester identifies the asset by its physical ID.
2. The system verifies access and displays its recorded condition and current workflow state.
3. The requester enters observed symptoms, observation time, location and available supporting evidence.
4. The system validates the asset reference and required observations without asking the requester to certify a repair diagnosis.
5. The requester confirms the report.
6. For the normal Available-asset path, the system records NeedsInspection, removes the listing and places the asset UnderMaintenance.
7. The system appends the fault event, preserves custody and notifies the responsible custodian and Maintenance Officer.

## Alternative flows

- **Alternative at main step 6:** The asset is Reserved.
    1. The system unlists the unit and sets UnderMaintenance.
    2. It releases the complete reservation, invalidates approval, returns the request to Submitted and cancels any pre-dispatch schedule.
    - Outcome: Return to main step 7, notifying the requester about reassignment.
- **Alternative at main step 6:** The asset is InUse, UnderMaintenance or Draft.
    1. The system retains custody and records NeedsInspection. InUse becomes UnderMaintenance; existing UnderMaintenance or Draft remains unchanged. Publication stays blocked.
    - Outcome: Return to main step 7.
- **Alternative at main step 6:** The asset is InTransit.
    1. The system records a blocking receipt incident and NeedsInspection.
    2. It preserves the transfer, InTransit status and previous authoritative custody.
    - Outcome: Return to main step 7; resolution follows UC-17 or UC-18.

## Exception flows

- **Exception at main step 4:** The description is empty.
    1. The system refuses submission and identifies the missing observation.
    - Outcome: Return to main step 3 without saving a fault record.

## Postconditions

**Success**

- The fault is attributable; the asset cannot remain eligible for normal allocation or unqualified receipt.

**Failure**

- An invalid report changes no authoritative record; existing faults and history remain intact.

## Business rules

BR-01, BR-05, BR-07, BR-09, BR-14

## Functional requirements

- **P3-FR-20.1** The system shall associate each fault report with one physical asset ID.
- **P3-FR-20.2** The system shall prevent a faulted unit from being dispatched as serviceable stock.
- **P3-FR-20.3** The system shall preserve authoritative custody when a fault is reported in transit.

## Acceptance check

Faulting one of two reserved synthetic units releases the whole reservation and returns the request to Submitted. Faulting a dispatched unit instead blocks receipt without rewriting custody or cancelling its history.
