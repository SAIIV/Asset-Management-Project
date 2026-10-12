# UC-28 Generate a sustainability report

- **Priority:** Essential
- **Parent group:** FR-06
- **Owner:** Humaid Al Ali
- **Primary actor:** Sustainability Officer
- **Supporting actors:** None

## Goal

Report recorded reuse, repair and resource outcomes with transparent financial and environmental calculation evidence.

## Preconditions

- The sustainability officer is signed in with access to the selected departments' sustainability records.

## Trigger

The officer requests a sustainability report for a selected period.

## Main flow

1. The officer chooses department scope, period and required indicators.
2. The system validates the filters and retrieves completed qualifying events with their distinct asset IDs.
3. The officer reviews the associated mass evidence, dated environmental factors, units and financial assessments available for calculation.
4. The system validates provenance, deduplicates qualifying events and prevents repeated physical-mass credit within the same indicator and period.
5. The system calculates supported reuse, repair, waste-diversion, life-extension, savings and estimated carbon indicators.
6. The system displays values with formulas, denominators, evidence coverage and a distinction between recorded measurements and estimates.
7. The officer reviews the supporting records and exports the dated report with its assumptions and limitations.

## Alternative flows

- **Alternative at main step 5:** An indicator lacks required evidence, a valid denominator or a supported factor.
    1. The system marks that indicator unavailable and identifies the missing inputs.
    2. Other supported indicators remain visible, with incomplete coverage disclosed.
    - Outcome: Return to main step 6.

## Exception flows

- **Exception at main step 4:** An environmental factor has incompatible units or no identifiable source and date.
    1. The system excludes the factor, explains the failure and marks the affected indicator unavailable.
    2. It substitutes no guessed conversion or carbon result.
    - Outcome: Return to main step 5 for the remaining supported indicators.

## Postconditions

**Success**

- The report distinguishes supported results, estimates and unavailable indicators.

**Failure**

- Unsupported environmental or financial values are not reported as established outcomes.

## Business rules

BR-01, BR-03, BR-12, BR-13

## Functional requirements

- **P3-FR-28.1** The system shall derive sustainability indicators from uniquely identified qualifying events.
- **P3-FR-28.2** The system shall expose the source, date and unit of each environmental factor used.
- **P3-FR-28.3** The system shall label unsupported indicators unavailable.
- **P3-FR-28.4** The system shall distinguish measured inputs from estimated environmental results.

## Acceptance check

A completed synthetic reuse event appears once. Removing its supported carbon factor makes its carbon estimate unavailable while preserving its reuse count; an unconfirmed transfer contributes no completed-transfer benefit.
