# UC-33 Recommend a sustainable action

- **Priority:** Desirable
- **Parent group:** AI-03
- **Owner:** Humaid Al Ali
- **Primary actor:** Custodian
- **Supporting actors:** None

## Goal

Compare supported lifecycle options while keeping asset decisions and execution under authorized human control.

## Preconditions

- The custodian is signed in with access to the synthetic asset and its recorded lifecycle history.
- An authorized recommendation configuration is available.

## Trigger

The custodian requests sustainable-action advice for the asset.

## Main flow

1. The custodian selects the asset and specifies the decision to consider.
2. The system retrieves permitted condition, inspection, maintenance, age, demand and cost evidence.
3. The system validates available inputs and identifies safety or in-transit restrictions affecting possible actions.
4. The recommendation service compares supported options, including retention, reuse or transfer, repair, refurbishment, component recovery, donation, recycling and last-option disposal.
5. The system displays the advice with supporting facts, uncertainty, missing evidence and model or rule version.
6. The custodian reviews the recommendation and identifies an option for the appropriate human-controlled workflow.
7. The system records the advisory result without changing asset state, ownership, custody or authorization.

## Alternative flows

- **Alternative at main step 6:** The custodian chooses retention or component recovery.
    1. Retention records the review without automatically changing operational state.
    2. Component recovery is described for a subsequent authorized refurbishment or recycling proposal rather than executed by the recommendation.
    - Outcome: Return to main step 7.

## Exception flows

- **Exception at main step 4:** The service cannot support a recommendation from the available evidence.
    1. The system reports the limitation and identifies inspection or other information needed.
    2. It withholds unsupported financial or carbon benefits.
    - Outcome: End without a lifecycle decision or state change.

## Postconditions

**Success**

- A traceable advisory comparison is available for independent review and any later proposal.

**Failure**

- No unsafe release, unauthorized retirement or unsupported benefit follows from failed advice.

## Business rules

BR-01, BR-09, BR-10, BR-11, BR-13

## Functional requirements

- **P3-FR-33.1** The system shall explain sustainable-action recommendations using recorded evidence and disclosed uncertainty.
- **P3-FR-33.2** The system shall preserve human authorization requirements for every recommended lifecycle action.
- **P3-FR-33.3** The system shall withhold environmental estimates lacking supported calculation inputs.

## Acceptance check

Advice to recycle a synthetic asset does not retire it. Missing inspection evidence is disclosed, and an InTransit asset retains its transfer and authoritative custody despite a lifecycle suggestion.
