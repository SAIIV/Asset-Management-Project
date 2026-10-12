# UC-04 Register an asset

- **Priority:** Essential
- **Parent group:** FR-02
- **Owner:** Saeed Alkaabi
- **Primary actor:** Custodian
- **Supporting actors:** None

## Goal

Create a traceable record for an individual synthetic physical asset without publishing it or making it automatically requestable.

## Preconditions

- The Custodian is authenticated and assigned to a department.
- The necessary department, location and category references exist.

## Trigger

The Custodian selects asset registration.

## Main flow

1. The system verifies registration permission and presents the asset form with permitted reference choices.
2. The Custodian enters the asset name, category, owning department, custodian, location, condition and available specifications, identifying the physical unit being recorded.
3. The Custodian supplies any available optional purchase, value or supporting information and submits the registration.
4. The system validates mandatory fields, allowed assignments and nonnegative recorded monetary or mass values; omitted optional values remain unavailable rather than becoming zero.
5. For each physical unit, the system allocates a distinct Asset ID and saves a Draft with its listing flag unset.
6. The system appends the registration event and displays the new identifier and recorded details. Publication requires the separate publishing use case.

## Alternative flows

- **Alternative at main step 2:** The Custodian registers several equivalent physical units together.
    1. The Custodian enters a positive whole-number count and the identifying details required for each unit.
    2. The system prepares that number of individual records, each requiring its own distinct Asset ID; a shared description does not create pooled stock under one ID.
    - Outcome: Return to main step 3 for the batch submission.

## Exception flows

- **Exception at main step 4:** A mandatory field is missing, an assignment is outside scope, or a recorded amount is negative.
    1. The system highlights the failed checks and saves no invalid asset record.
    2. The Custodian corrects the submitted values.
    - Outcome: Return to main step 3.

## Postconditions

**Success**

- Each registered physical unit has a distinct Draft record and remains unlisted.

**Failure**

- Invalid registration creates no asset record and overwrites no existing asset.

## Business rules

BR-01, BR-03, BR-14, BR-16

## Functional requirements

- **P3-FR-04.1** The system shall assign a distinct Asset ID to every registered physical unit.
- **P3-FR-04.2** The system shall reject registration values that violate mandatory-field or scope checks.
- **P3-FR-04.3** The system shall create registered assets in Draft state with the listing flag unset.

## Acceptance check

Register three synthetic monitors in a batch and obtain three distinct unlisted Draft IDs. Submitting a negative value or a missing department creates no asset record.
