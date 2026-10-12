# UC-27 Record benefit calculation inputs

- **Priority:** Essential
- **Parent group:** FR-06
- **Owner:** Humaid Al Ali
- **Primary actor:** Finance Officer
- **Supporting actors:** None

## Goal

Record traceable financial evidence for completed qualifying activity so later reports can calculate benefits without unsupported assumptions.

## Preconditions

- The finance officer is signed in with access to benefit records for the relevant department.

## Trigger

The finance officer opens a completed event for benefit assessment.

## Main flow

1. The finance officer selects the completed event and identifies its physical asset IDs.
2. The system checks event completion, department access and existing benefit claims for the same qualifying activity.
3. The finance officer enters the avoided-purchase baseline, repair and transfer costs in AED, evidence references and assessment date.
4. The system validates the amounts and supporting references and displays the proposed calculation inputs.
5. The finance officer confirms whether the evidence supports an actual avoided purchase and supplies the assessment reason.
6. The system saves a versioned benefit-input record linked to the event and records who confirmed the assessment.
7. The system displays the recorded inputs and their availability for subsequent financial reporting.

## Alternative flows

- **Alternative at main step 4:** A baseline or required cost is unknown.
    1. The system records the missing field as unavailable, together with the reason.
    2. The finance officer saves an incomplete assessment without confirming an avoided-purchase value.
    - Outcome: End with financial benefit unavailable for this event.

## Exception flows

- **Exception at main step 6:** Another assessment has already claimed the same qualifying event.
    1. The system rejects duplicate creation and displays the existing permitted assessment.
    2. A correction must create a traceable revision rather than a second claim.
    - Outcome: End without adding duplicate benefit.

## Postconditions

**Success**

- Financial inputs have evidence references and a recorded assessment status.

**Failure**

- No duplicate claim or unsupported completed calculation is created.

## Business rules

BR-01, BR-03, BR-12, BR-14

## Functional requirements

- **P3-FR-27.1** The system shall link each benefit assessment to its qualifying event and distinct asset IDs.
- **P3-FR-27.2** The system shall accept only nonnegative AED baseline values and costs.
- **P3-FR-27.3** The system shall exclude duplicate claims from benefit totals.
- **P3-FR-27.4** The system shall preserve unknown calculation inputs as unavailable rather than substitute zero.

## Acceptance check

Validated inputs of AED 800 avoided purchase, AED 150 repair and AED 50 transfer support AED 600 benefit. Other currencies are rejected. A missing baseline produces unavailable benefit, and repeating the event cannot increase the total.
