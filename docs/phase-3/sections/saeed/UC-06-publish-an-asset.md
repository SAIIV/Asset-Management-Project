# UC-06 Publish an asset

- **Priority:** Essential
- **Parent group:** FR-02
- **Owner:** Saeed Alkaabi
- **Primary actor:** Custodian
- **Supporting actors:** None

## Goal

Make a permitted, serviceable physical asset discoverable and eligible for a future reservation without allocating it to anyone.

## Preconditions

- The Custodian is authenticated.
- The asset record exists within the Custodian's assigned scope.

## Trigger

The Custodian requests publication of the asset.

## Main flow

1. The system retrieves the current asset record and checks the Custodian's publication permission.
2. The system presents the proposed listing, including its Asset ID, specifications, condition, department and location.
3. The Custodian reviews the listing and confirms publication.
4. The system verifies mandatory publication fields, Serviceable condition, Draft or Available state, absence of active allocation and any required return-to-service inspection evidence.
5. The system atomically sets the asset to Available and its listing flag to listed, preserving its owning department and custody.
6. The system records the publication event and confirms that the asset can appear in permitted catalogue searches. A reservation still requires a separate successful allocation.

## Alternative flows

- **Alternative at main step 2:** The asset is already listed and remains eligible.
    1. The system displays its existing publication status and current listing.
    2. It treats the repeated publication request as having no additional state effect.
    - Outcome: End successfully with the original listing retained and no duplicate asset.
- **Alternative at main step 3:** The Custodian identifies an incorrect description before confirmation.
    1. The Custodian leaves publication and corrects the record through UC-05.
    - Outcome: End without publication; restart UC-06 after the correction.

## Exception flows

- **Exception at main step 4:** The asset is unserviceable, lacks a required field, or has become reserved.
    1. The system states the blocking condition and declines publication.
    - Outcome: End unsuccessfully without changing state, listing, allocation or custody.

## Postconditions

**Success**

- The single physical unit is Available and listed, but not reserved.

**Failure**

- The existing asset and allocation states remain unchanged.

## Business rules

BR-01, BR-03, BR-04, BR-05, BR-09, BR-14

## Functional requirements

- **P3-FR-06.1** The system shall publish only an authorized, serviceable, unallocated asset with valid mandatory fields.
- **P3-FR-06.2** The system shall set a successfully published asset to Available with its listing flag set.
- **P3-FR-06.3** The system shall preserve custody when publishing an asset.

## Acceptance check

Publish a complete Serviceable Draft monitor and find its ID in an authorized search. Publication of an Unserviceable unit fails; repeating a successful publication does not create another unit.
